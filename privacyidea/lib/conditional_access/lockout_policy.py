# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
CRUD layer for conditional-access lockout policies.

The engine (:mod:`privacyidea.lib.conditional_access.engine`) only *reads*
:class:`~privacyidea.models.lockout_policy.LockoutPolicy` rows; this module is
the write path used by the REST API (``/conditionalaccess``) and anything else
that needs to create, edit or delete policies. All input validation lives
here, so the API layer stays a thin request/response wrapper.

A policy is passed around as a plain dict::

    {
        "name": "Brute Force Lockout",
        "time_window_seconds": 600,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": "user",
        "counter_types_to_track": ["PIN_FAIL", "MFA_FAIL"],
        "stages": [
            {
                "failure_threshold": 5,
                "priority": 1,
                "actions": [
                    {"action_type": "LOCK_USER", "action_value": {"lock_duration_seconds": 600}},
                    {"action_type": "EMAIL_ADMIN", "action_value": {"smtp_identifier": "..."}},
                ],
            },
        ],
    }

``counter_types_to_track`` values must be
:class:`~privacyidea.lib.conditional_access.authentication_event_types.AuthEventType`
names and ``action_type`` values must be
:class:`~privacyidea.lib.conditional_access.engine.LockoutAction` names; anything
else is a :class:`~privacyidea.lib.error.ParameterError` (fail-closed - a typo
must not silently create a policy that never matches or an action that never
fires).
"""
import logging
from dataclasses import dataclass, field

from sqlalchemy import select

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.engine import LockoutAction, LockoutTarget
from privacyidea.lib.error import ParameterError, ResourceNotFoundError
from privacyidea.lib.log import log_with
from privacyidea.models import db
from privacyidea.models.lockout_policy import (LockoutPolicy, LockoutPolicyStage,
                                               LockoutStageAction)

log = logging.getLogger(__name__)

# name is Unicode(255) in the model; checked here so an over-long name is a
# clean ParameterError instead of a DB-dependent truncation or error.
MAX_NAME_LENGTH = 255


@dataclass
class StageActionDefinition:
    """One validated stage action (see :func:`_validate_stages`)."""
    action_type: str
    action_value: object = None


@dataclass
class StageDefinition:
    """
    One validated stage with its actions, as produced by
    :func:`_validate_stages` and consumed by :func:`_build_stages`. Using a
    dataclass (instead of a bare ``dict``) makes the shape explicit and lets
    the type checker verify the hand-off between validation and ORM building.
    """
    failure_threshold: int
    priority: int
    actions: list[StageActionDefinition] = field(default_factory=list)


def lockout_policy_to_dict(policy: LockoutPolicy) -> dict:
    """
    Serialize a :class:`~privacyidea.models.lockout_policy.LockoutPolicy` with
    its stages and actions into the plain-dict shape documented in the module
    docstring (plus the ``id`` of each row).
    """
    # The scalar columns (id, name, time_window_seconds, enabled, dry_run,
    # priority) map straight through; counter_types_to_track (an association
    # proxy) and stages (a relationship) are not table columns, so they are
    # serialized explicitly.
    result = {column: getattr(policy, column) for column in policy.__table__.columns.keys()}
    result["counter_types_to_track"] = list(policy.counter_types_to_track)
    result["stages"] = [
        {
            "id": stage.id,
            "failure_threshold": stage.failure_threshold,
            "priority": stage.priority,
            "actions": [
                {
                    "id": action.id,
                    "action_type": action.action_type,
                    "action_value": action.action_value,
                } for action in stage.actions
            ],
        } for stage in policy.stages
    ]
    return result


def _get_policy(policy_id: int) -> LockoutPolicy:
    """
    Fetch one policy row or raise :class:`ResourceNotFoundError`.
    """
    policy = db.session.get(LockoutPolicy, policy_id)
    if not policy:
        raise ResourceNotFoundError(f"The lockout policy with id {policy_id} does not exist.")
    return policy


def _validate_name(name, exclude_id: int | None = None) -> str:
    """
    Validate the policy name (non-empty string, length, uniqueness).

    :param exclude_id: on update, the id of the policy being renamed, so its own
        current name does not count as a collision.
    :return: the stripped name
    """
    if not isinstance(name, str) or not name.strip():
        raise ParameterError("The policy name must be a non-empty string.")
    name = name.strip()
    if len(name) > MAX_NAME_LENGTH:
        raise ParameterError(f"The policy name must not exceed {MAX_NAME_LENGTH} characters.")
    existing = db.session.scalar(select(LockoutPolicy).where(LockoutPolicy.name == name))
    if existing and existing.id != exclude_id:
        raise ParameterError(f"A lockout policy with the name '{name}' already exists.")
    return name


def _validate_positive_int(value, field: str) -> int:
    """
    Validate a strictly positive integer field. bool is explicitly rejected
    (it is an int subclass, but ``priority=true`` is a caller mistake).
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ParameterError(f"'{field}' must be a positive integer.")
    return value


# The actions each target may carry. A user-targeted policy locks/notifies the
# user (and may decide the request via ALLOW/DENY); a source-IP policy blocks
# the IP or alerts the admin - LOCK_USER/EMAIL_USER would have no user to act on,
# and ALLOW/DENY are user-keyed pre-auth decisions not evaluated for IP targets.
_ACTIONS_BY_TARGET = {
    LockoutTarget.USER: {LockoutAction.LOCK_USER, LockoutAction.PERMANENT_LOCK_USER,
                         LockoutAction.EMAIL_USER, LockoutAction.EMAIL_ADMIN,
                         LockoutAction.DENY, LockoutAction.ALLOW},
    LockoutTarget.SOURCE_IP: {LockoutAction.BLOCK_IP, LockoutAction.PERMANENT_BLOCK_IP,
                              LockoutAction.EMAIL_ADMIN},
}


def _validate_target(target) -> "LockoutTarget":
    """
    Validate the policy target and return the matching :class:`LockoutTarget`
    member (accepts either ``"user"`` or ``LockoutTarget.USER``). Persisting the
    member to the ``Unicode`` column stores its value; the follow-up validation
    consumes the member directly.
    """
    try:
        return LockoutTarget(target)
    except ValueError:
        valid = ", ".join(sorted(t.value for t in LockoutTarget))
        raise ParameterError(f"Unknown target '{target}'. Valid targets: {valid}.")


def _validate_target_actions(stage_defs: list["StageDefinition"], target: "LockoutTarget") -> None:
    """
    Reject any stage action that is not allowed for *target* (see
    :data:`_ACTIONS_BY_TARGET`) - e.g. ``LOCK_USER`` on a ``source_ip`` policy.
    """
    allowed = _ACTIONS_BY_TARGET[target]
    invalid = sorted({action.action_type for stage in stage_defs for action in stage.actions
                      if action.action_type not in allowed})
    if invalid:
        raise ParameterError(f"Action(s) {', '.join(invalid)} are not allowed for target '{target}'. "
                             f"Allowed: {', '.join(sorted(allowed))}.")


def _validate_counter_types(counter_types) -> list[str]:
    """
    Validate the tracked counter types: a non-empty list of
    :class:`AuthEventType` values.

    A counter type repeated in the list is de-duplicated (order preserved)
    rather than rejected - tracking the same event type twice has no effect on
    evaluation, so a copy-paste duplicate should not fail the whole request.
    """
    if not isinstance(counter_types, list) or not counter_types:
        raise ParameterError("'counter_types_to_track' must be a non-empty list of authentication event types.")
    valid_types = {event_type.value for event_type in AuthEventType}
    seen = []
    for counter_type in counter_types:
        if counter_type not in valid_types:
            raise ParameterError(f"Unknown counter type '{counter_type}'. "
                                 f"Valid types: {', '.join(sorted(valid_types))}.")
        if counter_type not in seen:
            seen.append(counter_type)
    return seen


def _validate_stages(stages) -> list[StageDefinition]:
    """
    Validate the stage definitions: a non-empty list of dicts, each with a
    unique positive ``failure_threshold``, an optional positive ``priority``
    (default 1) and a list of actions whose ``action_type`` is a valid
    :class:`LockoutAction`. ``action_value`` may be any JSON-serializable value
    (its action-specific interpretation happens in the engine); unknown keys in
    a stage or action dict are rejected so typos fail loudly.

    :return: normalized list of :class:`StageDefinition` (without ids)
    """
    if not isinstance(stages, list) or not stages:
        raise ParameterError("'stages' must be a non-empty list of stage definitions.")
    valid_actions = {action.value for action in LockoutAction}
    allowed_stage_keys = {"failure_threshold", "priority", "actions"}
    allowed_action_keys = {"action_type", "action_value"}
    normalized = []
    thresholds = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise ParameterError("Each stage must be a dictionary.")
        unknown = set(stage) - allowed_stage_keys - {"id"}
        if unknown:
            raise ParameterError(f"Unknown stage key(s): {', '.join(sorted(unknown))}.")
        threshold = _validate_positive_int(stage.get("failure_threshold"), "failure_threshold")
        if threshold in thresholds:
            raise ParameterError(f"Duplicate failure_threshold {threshold}: thresholds must be unique within a policy.")
        thresholds.add(threshold)
        priority = _validate_positive_int(stage.get("priority", 1), "priority")
        actions = stage.get("actions", [])
        if not isinstance(actions, list):
            raise ParameterError("'actions' must be a list of action definitions.")
        normalized_actions = []
        for action in actions:
            if not isinstance(action, dict):
                raise ParameterError("Each action must be a dictionary.")
            unknown = set(action) - allowed_action_keys - {"id"}
            if unknown:
                raise ParameterError(f"Unknown action key(s): {', '.join(sorted(unknown))}.")
            action_type = action.get("action_type")
            if action_type not in valid_actions:
                raise ParameterError(f"Unknown action type '{action_type}'. "
                                     f"Valid types: {', '.join(sorted(valid_actions))}.")
            normalized_actions.append(StageActionDefinition(action_type=action_type,
                                                            action_value=action.get("action_value")))
        normalized.append(StageDefinition(failure_threshold=threshold, priority=priority,
                                          actions=normalized_actions))
    return normalized


def _build_stages(stage_defs: list[StageDefinition]) -> list[LockoutPolicyStage]:
    """
    Turn validated :class:`StageDefinition` objects into (unpersisted) ORM objects.
    """
    return [
        LockoutPolicyStage(
            failure_threshold=stage.failure_threshold,
            priority=stage.priority,
            actions=[LockoutStageAction(action_type=action.action_type, action_value=action.action_value)
                     for action in stage.actions],
        ) for stage in stage_defs
    ]


@log_with(log)
def list_lockout_policies(enabled: bool | None = None) -> list[dict]:
    """
    Return all lockout policies as dicts, highest priority first (the engine's
    evaluation order), name as tie-breaker.

    :param enabled: if given, only return policies with this enabled state
    """
    stmt = select(LockoutPolicy).order_by(LockoutPolicy.priority.desc(), LockoutPolicy.name)
    if enabled is not None:
        stmt = stmt.where(LockoutPolicy.enabled == enabled)
    policies = db.session.scalars(stmt).all()
    return [lockout_policy_to_dict(policy) for policy in policies]


@log_with(log)
def get_lockout_policy(policy_id: int) -> dict:
    """
    Return one lockout policy as a dict.

    :raises ResourceNotFoundError: if no policy with this id exists
    """
    return lockout_policy_to_dict(_get_policy(policy_id))


@log_with(log)
def create_lockout_policy(name: str, time_window_seconds: int, counter_types_to_track: list[str],
                          stages: list[dict], enabled: bool = True, dry_run: bool = False,
                          priority: int = 1, target: str = "user") -> int:
    """
    Create a lockout policy with its stages and actions in one transaction.

    See the module docstring for the parameter shapes; everything is validated
    here and a :class:`ParameterError` is raised on any invalid input before
    anything is written.

    :return: the id of the new policy
    """
    name = _validate_name(name)
    time_window_seconds = _validate_positive_int(time_window_seconds, "time_window_seconds")
    priority = _validate_positive_int(priority, "priority")
    lockout_target = _validate_target(target)
    counter_types = _validate_counter_types(counter_types_to_track)
    stage_defs = _validate_stages(stages)
    _validate_target_actions(stage_defs, lockout_target)

    policy = LockoutPolicy(name=name, time_window_seconds=time_window_seconds,
                           enabled=bool(enabled), dry_run=bool(dry_run), priority=priority,
                           target=lockout_target, counter_types_to_track=counter_types,
                           stages=_build_stages(stage_defs))
    db.session.add(policy)
    db.session.commit()
    log.info(f"Created lockout policy '{name}' (id {policy.id}).")
    return policy.id


@log_with(log)
def update_lockout_policy(policy_id: int, name: str | None = None,
                          time_window_seconds: int | None = None,
                          counter_types_to_track: list[str] | None = None,
                          stages: list[dict] | None = None, enabled: bool | None = None,
                          dry_run: bool | None = None, priority: int | None = None,
                          target: str | None = None) -> tuple[int, list[str]]:
    """
    Update a lockout policy. Only the given (non-``None``) fields are changed.

    ``counter_types_to_track`` and ``stages`` are **replaced as a whole** when
    given - the delete-orphan cascade drops the previous child rows. Replacing
    the stages resets any ``last_stage_triggered`` references in
    ``user_lockout_state``/``block_list`` to ``NULL`` (FK ``SET NULL``), which
    simply re-arms the de-dup for the edited policy; existing locks and blocks
    themselves stay in force.

    ``target`` may be changed, but the resulting ``(target, stages)`` combination
    must stay action-compatible (e.g. a ``source_ip`` policy cannot carry
    ``LOCK_USER``); an incompatible change raises :class:`ParameterError`.
    Existing locks/blocks written before the change are timed and expire on their
    own, so no stale state is left enforced.

    All fields are validated before anything is written.

    :return: a ``(policy_id, changed_fields)`` tuple, where ``changed_fields`` is
        the list of field names that were provided (and thus written), so the
        caller can record them in the audit log
    :raises ResourceNotFoundError: if no policy with this id exists
    """
    policy = _get_policy(policy_id)
    # Validate everything first: an invalid stage list must not leave a
    # half-applied rename behind (nothing is flushed before the commit below,
    # but keeping validation up front makes that invariant obvious).
    if name is not None:
        name = _validate_name(name, exclude_id=policy.id)
    if time_window_seconds is not None:
        time_window_seconds = _validate_positive_int(time_window_seconds, "time_window_seconds")
    if priority is not None:
        priority = _validate_positive_int(priority, "priority")
    lockout_target = _validate_target(target) if target is not None else None
    if counter_types_to_track is not None:
        counter_types_to_track = _validate_counter_types(counter_types_to_track)
    if stages is not None:
        stages = _validate_stages(stages)
    # target and stages must stay mutually compatible .
    if lockout_target is not None or stages is not None:
        effective_target = lockout_target if lockout_target is not None else LockoutTarget(policy.target)
        effective_stages = stages if stages is not None else policy.stages
        _validate_target_actions(effective_stages, effective_target)

    changed_fields = []
    if name is not None:
        policy.name = name
        changed_fields.append("name")
    if time_window_seconds is not None:
        policy.time_window_seconds = time_window_seconds
        changed_fields.append("time_window_seconds")
    if priority is not None:
        policy.priority = priority
        changed_fields.append("priority")
    if lockout_target is not None:
        policy.target = lockout_target
        changed_fields.append("target")
    if enabled is not None:
        policy.enabled = bool(enabled)
        changed_fields.append("enabled")
    if dry_run is not None:
        policy.dry_run = bool(dry_run)
        changed_fields.append("dry_run")
    if counter_types_to_track is not None:
        policy.counter_types_to_track = counter_types_to_track
        changed_fields.append("counter_types_to_track")
    if stages is not None:
        policy.stages = _build_stages(stages)
        changed_fields.append("stages")
    db.session.commit()
    log.info(f"Updated lockout policy '{policy.name}' (id {policy.id}); "
             f"changed fields: {', '.join(changed_fields) or 'none'}.")
    return policy.id, changed_fields


@log_with(log)
def delete_lockout_policy(policy_id: int) -> int:
    """
    Delete a lockout policy with all its stages and actions.

    Existing locks/blocks written by this policy stay in force (live state is
    independent of the policy config); their ``last_stage_triggered`` FK is set
    to ``NULL``.

    :return: the id of the deleted policy
    :raises ResourceNotFoundError: if no policy with this id exists
    """
    policy = _get_policy(policy_id)
    name = policy.name
    db.session.delete(policy)
    db.session.commit()
    log.info(f"Deleted lockout policy '{name}' (id {policy_id}).")
    return policy_id


@log_with(log)
def enable_lockout_policy(policy_id: int, enable: bool = True) -> int:
    """
    Enable or disable a lockout policy.

    :return: the id of the policy
    :raises ResourceNotFoundError: if no policy with this id exists
    """
    policy = _get_policy(policy_id)
    policy.enabled = bool(enable)
    db.session.commit()
    log.info(f"{'Enabled' if enable else 'Disabled'} lockout policy '{policy.name}' (id {policy.id}).")
    return policy.id
