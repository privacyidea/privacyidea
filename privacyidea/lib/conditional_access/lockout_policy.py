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
:class:`~privacyidea.lib.conditional_access.authentication_error_codes.AuthEventType`
names and ``action_type`` values must be
:class:`~privacyidea.lib.conditional_access.engine.LockoutAction` names; anything
else is a :class:`~privacyidea.lib.error.ParameterError` (fail-closed - a typo
must not silently create a policy that never matches or an action that never
fires).
"""
import logging

from sqlalchemy import select

from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
from privacyidea.lib.conditional_access.engine import LockoutAction
from privacyidea.lib.error import ParameterError, ResourceNotFoundError
from privacyidea.lib.log import log_with
from privacyidea.models import db
from privacyidea.models.lockout_policy import (LockoutPolicy, LockoutPolicyStage,
                                               LockoutStageAction)

log = logging.getLogger(__name__)

# name is Unicode(255) in the model; checked here so an over-long name is a
# clean ParameterError instead of a DB-dependent truncation or error.
MAX_NAME_LENGTH = 255


def lockout_policy_to_dict(policy: LockoutPolicy) -> dict:
    """
    Serialize a :class:`~privacyidea.models.lockout_policy.LockoutPolicy` with
    its stages and actions into the plain-dict shape documented in the module
    docstring (plus the ``id`` of each row).
    """
    return {
        "id": policy.id,
        "name": policy.name,
        "time_window_seconds": policy.time_window_seconds,
        "enabled": policy.enabled,
        "dry_run": policy.dry_run,
        "priority": policy.priority,
        "counter_types_to_track": list(policy.counter_types_to_track),
        "stages": [
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
        ],
    }


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


def _validate_counter_types(counter_types) -> list[str]:
    """
    Validate the tracked counter types: a non-empty list of unique
    :class:`AuthEventType` values.
    """
    if not isinstance(counter_types, list) or not counter_types:
        raise ParameterError("'counter_types_to_track' must be a non-empty list of authentication event types.")
    valid_types = {event_type.value for event_type in AuthEventType}
    seen = []
    for counter_type in counter_types:
        if counter_type not in valid_types:
            raise ParameterError(f"Unknown counter type '{counter_type}'. "
                                 f"Valid types: {', '.join(sorted(valid_types))}.")
        if counter_type in seen:
            raise ParameterError(f"Duplicate counter type '{counter_type}'.")
        seen.append(counter_type)
    return seen


def _validate_stages(stages) -> list[dict]:
    """
    Validate the stage definitions: a non-empty list of dicts, each with a
    unique positive ``failure_threshold``, an optional positive ``priority``
    (default 1) and a list of actions whose ``action_type`` is a valid
    :class:`LockoutAction`. ``action_value`` may be any JSON-serializable value
    (its action-specific interpretation happens in the engine); unknown keys in
    a stage or action dict are rejected so typos fail loudly.

    :return: normalized list of stage dicts (without ids)
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
            normalized_actions.append({"action_type": action_type,
                                       "action_value": action.get("action_value")})
        normalized.append({"failure_threshold": threshold, "priority": priority,
                           "actions": normalized_actions})
    return normalized


def _build_stages(stage_dicts: list[dict]) -> list[LockoutPolicyStage]:
    """
    Turn validated stage dicts into (unpersisted) ORM objects.
    """
    return [
        LockoutPolicyStage(
            failure_threshold=stage["failure_threshold"],
            priority=stage["priority"],
            actions=[LockoutStageAction(action_type=action["action_type"], action_value=action["action_value"])
                     for action in stage["actions"]],
        ) for stage in stage_dicts
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
                          priority: int = 1) -> int:
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
    counter_types = _validate_counter_types(counter_types_to_track)
    stage_dicts = _validate_stages(stages)

    policy = LockoutPolicy(name=name, time_window_seconds=time_window_seconds,
                           enabled=bool(enabled), dry_run=bool(dry_run), priority=priority,
                           counter_types_to_track=counter_types,
                           stages=_build_stages(stage_dicts))
    db.session.add(policy)
    db.session.commit()
    log.info(f"Created lockout policy '{name}' (id {policy.id}).")
    return policy.id


@log_with(log)
def update_lockout_policy(policy_id: int, name: str | None = None,
                          time_window_seconds: int | None = None,
                          counter_types_to_track: list[str] | None = None,
                          stages: list[dict] | None = None, enabled: bool | None = None,
                          dry_run: bool | None = None, priority: int | None = None) -> int:
    """
    Update a lockout policy. Only the given (non-``None``) fields are changed.

    ``counter_types_to_track`` and ``stages`` are **replaced as a whole** when
    given - the delete-orphan cascade drops the previous child rows. Replacing
    the stages resets any ``last_stage_triggered`` references in
    ``user_lockout_state``/``block_list`` to ``NULL`` (FK ``SET NULL``), which
    simply re-arms the de-dup for the edited policy; existing locks and blocks
    themselves stay in force.

    All fields are validated before anything is written.

    :return: the id of the updated policy
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
    if counter_types_to_track is not None:
        counter_types_to_track = _validate_counter_types(counter_types_to_track)
    if stages is not None:
        stages = _validate_stages(stages)

    if name is not None:
        policy.name = name
    if time_window_seconds is not None:
        policy.time_window_seconds = time_window_seconds
    if priority is not None:
        policy.priority = priority
    if enabled is not None:
        policy.enabled = bool(enabled)
    if dry_run is not None:
        policy.dry_run = bool(dry_run)
    if counter_types_to_track is not None:
        policy.counter_types_to_track = counter_types_to_track
    if stages is not None:
        policy.stages = _build_stages(stages)
    db.session.commit()
    log.info(f"Updated lockout policy '{policy.name}' (id {policy.id}).")
    return policy.id


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
