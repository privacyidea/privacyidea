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
        "count_mode": "PER_REQUEST",
        "counter_types_to_track": ["PIN_FAIL", "MFA_FAIL"],
        "conditions": [
            {"condition_type": "USER_REALM", "operator": "IN", "value": ["sales", "support"]},
        ],
        "stages": [
            {
                "failure_threshold": 5,
                "priority": 1,
                "error_message": "Your account is locked. Please try again in about {duration}.",
                "actions": [
                    {"action_type": "LOCK_USER", "action_value": {"lock_duration_seconds": 600},
                     "retrigger_above_threshold": True},
                    {"action_type": "EMAIL_ADMIN", "action_value": {"smtp_identifier": "..."},
                     "retrigger_above_threshold": False},
                ],
            },
        ],
    }

``count_mode`` is a :class:`~privacyidea.lib.conditional_access.authentication_event_types.CountMode` name whose valid
values depend on the target (see ``_COUNT_MODES_BY_TARGET``): both targets count event volume per ``authentication_log``
row (``PER_REQUEST``) or per whole authentication attempt (``PER_ATTEMPT``); a ``source_ip`` policy may additionally
count distinct targeted accounts (``DISTINCT_USERS``, the spraying / enumeration signal). When omitted it defaults to
the target's default (``PER_REQUEST`` for ``user``, ``DISTINCT_USERS`` for ``source_ip``). ``counter_types_to_track``
values must be
:class:`~privacyidea.lib.conditional_access.authentication_event_types.AuthEventType` names and ``action_type`` values
must be :class:`~privacyidea.lib.conditional_access.engine.LockoutAction` names; anything else is a
:class:`~privacyidea.lib.error.ParameterError` (fail-closed - a typo must not silently create a policy that never
matches or an action that never fires).

A stage's optional ``error_message`` is the text an end user sees when a request is turned away by that stage. It is
opt-in and there is no default: without one the rejection stays generic, so privacyIDEA never volunteers that an
account is locked or an IP blocked unless an admin chose to say so. ``{duration}`` is substituted with the remaining
time at rejection; on a permanent restriction it renders as "permanently". Every other brace expression is left exactly
as written - braces in prose need no escaping - so only the length is validated here.

``conditions`` is the *applicability* axis, orthogonal to the counting one: it restricts which requests the policy
applies to at all, while the counter types and thresholds decide what trips it. It is optional - a policy without
conditions applies to every request - and is validated against the registries in
:mod:`~privacyidea.lib.conditional_access.conditions` under the same fail-closed rule, since a condition naming an
unknown realm or a misspelled role would otherwise silently never match.
"""

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from privacyidea.lib import _
from privacyidea.lib.conditional_access.authentication_event_types import (
    TRACKABLE_EVENT_TYPES,
    CountMode,
)
from privacyidea.lib.conditional_access.conditions import CONDITION_TYPES
from privacyidea.lib.conditional_access.engine import LockoutAction, LockoutTarget
from privacyidea.lib.error import ConflictError, ParameterError, ResourceNotFoundError
from privacyidea.lib.log import log_with
from privacyidea.models import db
from privacyidea.models.lockout_policy import (LockoutPolicy, LockoutPolicyCondition,
                                               LockoutPolicyStage, LockoutStageAction)

log = logging.getLogger(__name__)

# name is Unicode(255) in the model; checked here so an over-long name is a
# clean ParameterError instead of a DB-dependent truncation or error.
MAX_NAME_LENGTH = 255

# Same for a stage's error message, which is Unicode(500) in the model.
MAX_STAGE_ERROR_MESSAGE_LENGTH = 500

# The pre-auth ALLOW/DENY actions: standing decisions that apply while the count
# stays at or above the threshold, so they default to re-triggering (the
# post-response lock/email/block effects default to fire-once).
DECISION_ACTIONS = frozenset({str(LockoutAction.ALLOW), str(LockoutAction.DENY)})


@dataclass
class StageActionDefinition:
    """
    One validated stage action (see :func:`_validate_stages`).

    ``retrigger_above_threshold`` left at ``None`` means "not chosen": it is
    resolved to the action-aware default in :func:`_build_stages` (re-trigger for
    the :data:`DECISION_ACTIONS`, fire-once for the post-response effects).
    """

    action_type: str
    action_value: object = None
    retrigger_above_threshold: bool | None = None


@dataclass
class ConditionDefinition:
    """One validated applicability condition (see :func:`_validate_conditions`)."""
    condition_type: str
    operator: str
    value: list[str]


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
    name: str | None = None
    error_message: str | None = None


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
    # Conditions restrict which requests the policy applies to; an empty list means
    # it applies to everyone. Unlike a stage, a condition carries no id here: nothing
    # addresses one (no foreign key points at the table, and within a policy the
    # condition type is already unique), and an update replaces them wholesale, so an
    # id would only be a value that churns on every write. They are served in
    # condition_type order - a canonical order for an ANDed set, so the same
    # conditions always serialize identically and a client can diff the response.
    result["conditions"] = [
        {
            "condition_type": condition.condition_type,
            "operator": condition.operator,
            "value": condition.value,
        } for condition in policy.conditions
    ]
    # Stages are ordered for display by ascending failure_threshold (the stage
    # that triggers first comes first). This is independent of the engine's
    # evaluation order (highest priority first, see the model relationship),
    # which is why we sort here rather than relying on policy.stages order.
    result["stages"] = [
        {
            "id": stage.id,
            "name": stage.name,
            "error_message": stage.error_message,
            "failure_threshold": stage.failure_threshold,
            "priority": stage.priority,
            "actions": [
                {
                    "id": action.id,
                    "action_type": action.action_type,
                    "action_value": action.action_value,
                    "retrigger_above_threshold": action.retrigger_above_threshold,
                }
                for action in stage.actions
            ],
        }
        for stage in sorted(policy.stages, key=lambda stage: stage.failure_threshold)
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


def _validate_priority(priority, exclude_id: int | None = None) -> int:
    """
    Validate the policy priority: a strictly positive integer that is unique
    across all policies. A shared priority would leave the evaluation order (and
    thus which policy wins an allow/deny decision) undefined, so a collision is
    rejected rather than silently tie-broken.

    :param exclude_id: on update, the id of the policy being changed, so its own
        current priority does not count as a collision.
    :return: the validated priority
    """
    priority = _validate_positive_int(priority, "priority")
    existing = db.session.scalar(select(LockoutPolicy).where(LockoutPolicy.priority == priority))
    if existing and existing.id != exclude_id:
        raise ParameterError(
            f"A lockout policy with priority {priority} already exists ('{existing.name}'); priorities must be unique."
        )
    return priority


def _validate_positive_int(value, field: str) -> int:
    """
    Validate a strictly positive integer field. bool is explicitly rejected
    (it is an int subclass, but ``priority=true`` is a caller mistake).
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ParameterError(f"'{field}' must be a positive integer.")
    return value


def _validate_stage_name(name) -> str | None:
    """
    Validate the optional stage name. ``None`` or an empty/blank string means
    "no name" and returns ``None``; a non-empty value must be a string within
    the length limit.
    """
    if name is None:
        return None
    if not isinstance(name, str):
        raise ParameterError("The stage name must be a string.")
    name = name.strip()
    if not name:
        return None
    if len(name) > MAX_NAME_LENGTH:
        raise ParameterError(f"The stage name must not exceed {MAX_NAME_LENGTH} characters.")
    return name


def _validate_stage_error_message(error_message: str | None) -> str | None:
    """
    Validate the optional stage error message - the text surfaced to the end user
    when a request is turned away by this stage. ``None`` or an empty/blank string
    means "say nothing" and returns ``None``, which is the default: a rejection
    reveals no conditional-access detail unless an admin writes it here.

    Only the length is checked. Brace expressions are deliberately *not*
    validated: ``{duration}`` is the one tag substituted at rejection time and
    everything else - ``{}``, ``{whatever}`` - is left literal, so an admin can
    write braces in ordinary prose without escaping them. The WebUI hints at an
    unrecognized tag; it is not an error here.
    """
    if error_message is None:
        return None
    if not isinstance(error_message, str):
        raise ParameterError(_("The stage error message must be a string."))
    stripped = error_message.strip()
    if not stripped:
        return None
    if len(stripped) > MAX_STAGE_ERROR_MESSAGE_LENGTH:
        # .format, not an f-string: gettext extracts the literal msgid, so the
        # placeholder has to survive into the translated string.
        raise ParameterError(_("The stage error message must not exceed {length} characters.").format(
            length=MAX_STAGE_ERROR_MESSAGE_LENGTH))
    return stripped


# The actions each target may carry. A user-targeted policy locks/notifies the
# user; a source-IP policy blocks the IP or alerts the admin - LOCK_USER /
# EMAIL_USER would have no user to act on. Both targets may decide the request
# pre-auth via ALLOW/DENY (keyed on the user, resp. the source IP).
_ACTIONS_BY_TARGET = {
    LockoutTarget.USER: {
        LockoutAction.LOCK_USER,
        LockoutAction.PERMANENT_LOCK_USER,
        LockoutAction.EMAIL_USER,
        LockoutAction.EMAIL_ADMIN,
        LockoutAction.DENY,
        LockoutAction.ALLOW,
    },
    LockoutTarget.SOURCE_IP: {
        LockoutAction.BLOCK_IP,
        LockoutAction.PERMANENT_BLOCK_IP,
        LockoutAction.EMAIL_ADMIN,
        LockoutAction.DENY,
        LockoutAction.ALLOW,
    },
}


def get_actions_by_target() -> dict[str, list[str]]:
    """
    The stage actions each target permits, as ``{target_value: [action_value, ...]}``
    (see :data:`_ACTIONS_BY_TARGET`).
    """
    return {target.value: sorted(action.value for action in actions) for target, actions in _ACTIONS_BY_TARGET.items()}


def get_target_constraints() -> dict[str, dict[str, list[str]]]:
    """
    The per-target policy constraints, as ``{target_value: {"actions": [...], "count_modes": [...]}}`` - for each
    target the stage actions it allows (:data:`_ACTIONS_BY_TARGET`) and the count modes it supports
    (:data:`_COUNT_MODES_BY_TARGET`), both sorted. Actions and count modes are the two things constrained by the
    target.
    """
    return {
        target.value: {
            "actions": sorted(action.value for action in _ACTIONS_BY_TARGET[target]),
            "count_modes": sorted(mode.value for mode in _COUNT_MODES_BY_TARGET[target]),
        }
        for target in LockoutTarget
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
    invalid = sorted(
        {action.action_type for stage in stage_defs for action in stage.actions if action.action_type not in allowed}
    )
    if invalid:
        raise ParameterError(
            f"Action(s) {', '.join(invalid)} are not allowed for target '{target}'. "
            f"Allowed: {', '.join(sorted(allowed))}."
        )


# The count modes each target may use, and the default when the caller does not specify one. Both targets support the
# volume modes (per request or per whole attempt); a ``source_ip`` target additionally offers ``DISTINCT_USERS`` - the
# distinct targeted accounts (spraying / enumeration) signal - and defaults to it, since that is the characteristic
# per-IP threat, while the volume modes give plain per-IP rate limiting. Mirrors the per-target ``_ACTIONS_BY_TARGET``
# registration.
_COUNT_MODES_BY_TARGET = {
    LockoutTarget.USER: {CountMode.PER_REQUEST, CountMode.PER_ATTEMPT},
    LockoutTarget.SOURCE_IP: {CountMode.DISTINCT_USERS, CountMode.PER_REQUEST, CountMode.PER_ATTEMPT},
}
_DEFAULT_COUNT_MODE_BY_TARGET = {
    LockoutTarget.USER: CountMode.PER_REQUEST,
    LockoutTarget.SOURCE_IP: CountMode.DISTINCT_USERS,
}


def _validate_count_mode(count_mode, target: "LockoutTarget") -> str:
    """
    Validate the policy's :class:`CountMode` for *target* and return its canonical string value.

    A ``None`` *count_mode* yields the target's default (see :data:`_DEFAULT_COUNT_MODE_BY_TARGET`), so a caller need
    not know which mode a target expects. Otherwise the mode must be a known :class:`CountMode` (accepted as either a
    mode string from the API or a member) *and* allowed for *target* (see :data:`_COUNT_MODES_BY_TARGET`) - e.g.
    ``DISTINCT_USERS`` on a ``user`` policy is rejected. Both accepted
    forms normalize to the plain string stored on the model, so the stored value's type does not depend on the caller.
    """
    if count_mode is None:
        return _DEFAULT_COUNT_MODE_BY_TARGET[target].value
    try:
        mode = CountMode(count_mode)
    except ValueError:
        valid_modes = ", ".join(mode.value for mode in CountMode)
        raise ParameterError(f"Unknown count_mode '{count_mode}'. Valid modes: {valid_modes}.")
    allowed = _COUNT_MODES_BY_TARGET[target]
    if mode not in allowed:
        raise ParameterError(
            f"count_mode '{mode}' is not allowed for target '{target}'. "
            f"Allowed: {', '.join(sorted(m.value for m in allowed))}."
        )
    return mode.value


def _validate_counter_types(counter_types) -> list[str]:
    """
    Validate the tracked counter types: a non-empty list of :class:`AuthEventType` values. The same vocabulary
    applies in both :class:`CountMode`\\ s - the mode changes only whether these events are counted per log row or
    per whole attempt, not what may be tracked.

    A counter type repeated in the list is de-duplicated (order preserved) rather than rejected - tracking the same
    event type twice has no effect on evaluation, so a copy-paste duplicate should not fail the whole request.
    """
    if not isinstance(counter_types, list) or not counter_types:
        raise ParameterError("'counter_types_to_track' must be a non-empty list of authentication event types.")
    valid_types = {event_type.value for event_type in TRACKABLE_EVENT_TYPES}
    seen = []
    for counter_type in counter_types:
        if counter_type not in valid_types:
            raise ParameterError(
                f"Unknown counter type '{counter_type}'. Valid types: {', '.join(sorted(valid_types))}."
            )
        if counter_type not in seen:
            seen.append(counter_type)
    return seen


def _validate_stages(stages) -> list[StageDefinition]:
    """
    Validate the stage definitions: a non-empty list of dicts, each with a
    unique non-negative ``failure_threshold``, an optional positive ``priority``
    (default 1), an optional user-facing ``error_message`` and a list of actions whose ``action_type`` is a valid
    :class:`LockoutAction`. ``action_value`` may be any JSON-serializable value
    (its action-specific interpretation happens in the engine); unknown keys in
    a stage or action dict are rejected so typos fail loudly.

    :return: normalized list of :class:`StageDefinition` (without ids)
    """
    if not isinstance(stages, list) or not stages:
        raise ParameterError("'stages' must be a non-empty list of stage definitions.")
    valid_actions = {action.value for action in LockoutAction}
    allowed_stage_keys = {"name", "error_message", "failure_threshold", "priority", "actions"}
    allowed_action_keys = {"action_type", "action_value", "retrigger_above_threshold"}
    normalized = []
    thresholds = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise ParameterError("Each stage must be a dictionary.")
        unknown = set(stage) - allowed_stage_keys - {"id"}
        if unknown:
            raise ParameterError(f"Unknown stage key(s): {', '.join(sorted(unknown))}.")
        # A threshold of 0 always matches (e.g. an ALLOW allowlist / default-allow
        # stage); higher thresholds fire at count >= threshold. So 0 is valid.
        threshold = stage.get("failure_threshold")
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 0:
            raise ParameterError("'failure_threshold' must be a non-negative integer.")
        if threshold in thresholds:
            raise ParameterError(f"Duplicate failure_threshold {threshold}: thresholds must be unique within a policy.")
        thresholds.add(threshold)
        name = _validate_stage_name(stage.get("name"))
        error_message = _validate_stage_error_message(stage.get("error_message"))
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
                raise ParameterError(
                    f"Unknown action type '{action_type}'. Valid types: {', '.join(sorted(valid_actions))}."
                )
            # retrigger_above_threshold is a per-action checkbox (coerced like the
            # policy-level enabled/dry_run booleans). An omitted flag stays None
            # and is resolved to the action-aware default by :func:`_build_stages`.
            retrigger_raw = action.get("retrigger_above_threshold")
            retrigger = None if retrigger_raw is None else bool(retrigger_raw)
            normalized_actions.append(
                StageActionDefinition(
                    action_type=action_type,
                    action_value=action.get("action_value"),
                    retrigger_above_threshold=retrigger,
                )
            )
        normalized.append(
            StageDefinition(failure_threshold=threshold, priority=priority, name=name,
                            error_message=error_message, actions=normalized_actions)
        )
    return normalized


def _validate_conditions(conditions) -> list[ConditionDefinition]:
    """
    Validate a policy's applicability conditions: a list of dicts, each naming a
    known :class:`~privacyidea.lib.conditional_access.conditions.ConditionType`,
    an operator that type permits, and a non-empty list of values.

    An **empty list is valid** and means "no restrictions": the policy applies to
    every request, which is how a policy without conditions behaves and how an
    admin removes conditions on update.

    Everything is rejected rather than coerced, because every one of these
    mistakes produces a policy that silently never matches - which for a ``DENY``
    policy is a restriction that quietly stops protecting anything:

    * an unknown condition type or operator, or an operator the type does not
      permit;
    * a value that is not a non-empty list, or holds a non-string;
    * a value outside the type's current vocabulary (an unknown realm, a
      misspelled role) - checked here, at write time, where it can be reported.
      Evaluation never does this: a realm deleted *after* the policy was written
      must simply stop matching, never raise on the authentication path;
    * the same condition type twice, which the database rejects anyway and which
      could only express a contradiction, since conditions are ANDed.

    Duplicates within one condition's value list are dropped rather than rejected -
    listing a realm twice changes nothing about the outcome.

    :return: normalized list of :class:`ConditionDefinition` (without ids)
    """
    if not isinstance(conditions, list):
        raise ParameterError("'conditions' must be a list of condition definitions.")
    allowed_keys = {"condition_type", "operator", "value"}
    normalized = []
    seen = set()
    for condition in conditions:
        if not isinstance(condition, dict):
            raise ParameterError("Each condition must be a dictionary.")
        unknown = set(condition) - allowed_keys
        if unknown:
            raise ParameterError(f"Unknown condition key(s): {', '.join(sorted(unknown))}.")
        condition_type = condition.get("condition_type")
        spec = CONDITION_TYPES.get(condition_type)
        if spec is None:
            raise ParameterError(f"Unknown condition type '{condition_type}'. "
                                 f"Valid types: {', '.join(sorted(CONDITION_TYPES))}.")
        operator = condition.get("operator")
        if operator not in spec.operators:
            raise ParameterError(f"Operator '{operator}' is not allowed for condition type "
                                 f"'{condition_type}'. Allowed: {', '.join(sorted(spec.operators))}.")
        if condition_type in seen:
            raise ParameterError(f"Duplicate condition '{condition_type}': a policy can carry it only once.")
        seen.add(condition_type)
        normalized.append(ConditionDefinition(condition_type=condition_type, operator=operator,
                                              value=_validate_condition_value(condition.get("value"), spec)))
    return normalized


def _validate_condition_value(value, spec) -> list[str]:
    """
    Validate one condition's value list against its condition type *spec*: a
    non-empty list of strings drawn from the type's vocabulary, with duplicates
    removed (order preserved).

    Values are matched against the vocabulary **exactly**. Both sides are already
    canonical - realm names are lower-cased when a realm is created, and the
    choices come from that same source - so a value that differs only in case is a
    typo, and reporting it here beats quietly rewriting what the admin wrote.

    Every operator in use takes a list; when a scalar operator is added, the
    accepted shape becomes operator-dependent and this is where that branches.
    """
    if not isinstance(value, (list, tuple)) or not value:
        raise ParameterError(f"The value of condition '{spec.name}' must be a non-empty list.")
    choices = spec.choices() if spec.choices else None
    validated = []
    for entry in value:
        if not isinstance(entry, str):
            raise ParameterError(f"The values of condition '{spec.name}' must be strings.")
        entry = entry.strip()
        if choices is not None and entry not in choices:
            raise ParameterError(f"Unknown value '{entry}' for condition '{spec.name}'. "
                                 f"Valid values: {', '.join(sorted(choices))}.")
        if entry not in validated:
            validated.append(entry)
    return validated


def _build_conditions(condition_defs: list[ConditionDefinition]) -> list[LockoutPolicyCondition]:
    """Turn validated :class:`ConditionDefinition` objects into (unpersisted) ORM objects."""
    return [
        LockoutPolicyCondition(condition_type=condition.condition_type,
                               operator=condition.operator, value=condition.value)
        for condition in condition_defs
    ]


def _default_retrigger(action: StageActionDefinition) -> bool:
    """The action's ``retrigger_above_threshold``, defaulted by action type when unset."""
    if action.retrigger_above_threshold is None:
        return str(action.action_type) in DECISION_ACTIONS
    return action.retrigger_above_threshold


def _build_stages(stage_defs: list[StageDefinition]) -> list[LockoutPolicyStage]:
    """
    Turn validated :class:`StageDefinition` objects into (unpersisted) ORM objects.

    An action whose ``retrigger_above_threshold`` is ``None`` (not chosen by the
    admin) gets the action-aware default: the :data:`DECISION_ACTIONS` are
    standing pre-auth decisions that apply while the count stays at or above the
    threshold, so they re-trigger; the post-response effects (lock/email/block)
    fire once, at the exact threshold.
    """
    return [
        LockoutPolicyStage(
            name=stage.name,
            error_message=stage.error_message,
            failure_threshold=stage.failure_threshold,
            priority=stage.priority,
            actions=[
                LockoutStageAction(
                    action_type=action.action_type,
                    action_value=action.action_value,
                    retrigger_above_threshold=_default_retrigger(action),
                )
                for action in stage.actions
            ],
        )
        for stage in stage_defs
    ]


@log_with(log)
def list_lockout_policies(enabled: bool | None = None) -> list[dict]:
    """
    Return all lockout policies as dicts, lowest priority number first (the
    engine's evaluation order: a lower number means higher precedence, matching
    privacyIDEA's policy engine).

    :param enabled: if given, only return policies with this enabled state
    """
    stmt = select(LockoutPolicy).order_by(LockoutPolicy.priority.asc())
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


@contextmanager
def _unique_conflict_as_400():
    """
    Turn a unique-constraint violation from the wrapped DB writes into a clean
    :class:`ParameterError` (a 400, not a 500).

    The app-level name/priority uniqueness checks race with concurrent writers:
    two requests can both pass validation and only collide when the write hits
    the database (at a ``flush`` or the ``commit``). Rolling back is the job that
    matters here - without it the session stays poisoned and every later query in
    the request raises - so *any* IntegrityError is handled. The per-policy child
    constraints (counter type, stage threshold) are ordered around by the split flushes in
    :func:`update_lockout_policy` and so are only backstopped here; the message
    therefore names every uniqueness rule rather than guessing which one fired.
    The original error is chained, so the traceback still identifies the
    constraint.
    """
    try:
        yield
    except IntegrityError as ex:
        db.session.rollback()
        raise ParameterError(
            "The lockout policy conflicts with existing data: name and priority must be unique "
            "across policies, and counter types and stage thresholds unique within a policy."
        ) from ex


@log_with(log)
def create_lockout_policy(
    name: str,
    time_window_seconds: int,
    counter_types_to_track: list[str],
    stages: list[dict],
    target: str,
    priority: int,
    enabled: bool = True,
    dry_run: bool = False,
    count_mode: str | None = None,
    conditions: list[dict] | None = None,
) -> int:
    """
    Create a lockout policy with its stages and actions in one transaction.

    See the module docstring for the parameter shapes; everything is validated
    here and a :class:`ParameterError` is raised on any invalid input before
    anything is written. ``target`` is required (no silent default) so the
    target/action compatibility is always a deliberate choice. ``priority`` is
    likewise required (no default) and must be unique across policies, so the
    caller always picks a deliberate, unambiguous precedence.
    ``count_mode`` defaults to the target's default when not given (see :func:`_validate_count_mode`).
    ``conditions`` restricts which requests the policy applies to; omitted (or
    empty) it applies to every request.

    :return: the id of the new policy
    """
    name = _validate_name(name)
    time_window_seconds = _validate_positive_int(time_window_seconds, "time_window_seconds")
    priority = _validate_priority(priority)
    lockout_target = _validate_target(target)
    count_mode = _validate_count_mode(count_mode, lockout_target)
    counter_types = _validate_counter_types(counter_types_to_track)
    stage_defs = _validate_stages(stages)
    _validate_target_actions(stage_defs, lockout_target)
    # `is None`, not `or []`: only an *omitted* conditions parameter means "applies to everyone". Any other
    # value goes through _validate_conditions, so a falsy non-list (0, False, {}) is a 400 rather than
    # being silently read as "no conditions" - which would widen an access-control policy to every request
    # on malformed input. Mirrors the `is not None` discipline of update_lockout_policy.
    condition_defs = _validate_conditions([] if conditions is None else conditions)

    policy = LockoutPolicy(
        name=name,
        time_window_seconds=time_window_seconds,
        enabled=bool(enabled),
        dry_run=bool(dry_run),
        priority=priority,
        target=lockout_target,
        counter_types_to_track=counter_types,
        count_mode=count_mode,
        stages=_build_stages(stage_defs),
        conditions=_build_conditions(condition_defs),
    )
    db.session.add(policy)
    with _unique_conflict_as_400():
        db.session.commit()
    log.info(f"Created lockout policy '{name}' (id {policy.id}).")
    return policy.id


@log_with(log)
def update_lockout_policy(
    policy_id: int,
    name: str | None = None,
    time_window_seconds: int | None = None,
    counter_types_to_track: list[str] | None = None,
    stages: list[dict] | None = None,
    enabled: bool | None = None,
    dry_run: bool | None = None,
    priority: int | None = None,
    target: str | None = None,
    count_mode: str | None = None,
    conditions: list[dict] | None = None,
) -> tuple[int, list[str]]:
    """
    Update a lockout policy. Only the given (non-``None``) fields are changed.

    ``counter_types_to_track``, ``stages`` and ``conditions`` are **replaced as a
    whole** when given - the delete-orphan cascade drops the previous child rows.
    Passing an empty ``conditions`` list therefore removes every condition, which
    widens the policy to apply to all requests. Locks and blocks this policy has
    already written stay in force: live state is independent of the policy config.

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
        priority = _validate_priority(priority, exclude_id=policy.id)
    lockout_target = _validate_target(target) if target is not None else None
    if counter_types_to_track is not None:
        counter_types_to_track = _validate_counter_types(counter_types_to_track)
    if stages is not None:
        stages = _validate_stages(stages)
    if conditions is not None:
        conditions = _validate_conditions(conditions)
    # target and stages must stay mutually compatible.
    if lockout_target is not None or stages is not None:
        effective_target = lockout_target if lockout_target is not None else LockoutTarget(policy.target)
        effective_stages = stages if stages is not None else policy.stages
        _validate_target_actions(effective_stages, effective_target)
    # target and count_mode must stay mutually compatible: switching the target can invalidate the stored mode (e.g.
    # a user policy's PER_REQUEST is not valid once it becomes a source_ip policy), so validate the effective pair.
    if lockout_target is not None or count_mode is not None:
        effective_target = lockout_target if lockout_target is not None else LockoutTarget(policy.target)
        effective_mode = count_mode if count_mode is not None else policy.count_mode
        validated_mode = _validate_count_mode(effective_mode, effective_target)
        if count_mode is not None:
            count_mode = validated_mode

    changed_fields = []
    # A name/priority collision can race past the app-level checks and surface at
    # the first flush or the commit; convert it to a clean ParameterError (400).
    with _unique_conflict_as_400():
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
        if count_mode is not None:
            policy.count_mode = count_mode
            changed_fields.append("count_mode")
        if counter_types_to_track is not None:
            # Delete the existing rows and flush before inserting the replacements,
            # so a single flush never holds two rows with the same
            # (policy_id, counter_type). This keeps a replacement that reuses a
            # counter type within the (policy_id, counter_type) unique constraint.
            policy.counter_types = []
            db.session.flush()
            policy.counter_types_to_track = counter_types_to_track
            changed_fields.append("counter_types_to_track")
        if stages is not None:
            # Same split-flush replacement, keeping the (policy_id, failure_threshold)
            # unique constraint when a threshold is reused across the update.
            policy.stages = []
            db.session.flush()
            policy.stages = _build_stages(stages)
            changed_fields.append("stages")
        if conditions is not None:
            # Same split-flush replacement, keeping the
            # (policy_id, condition_type) unique constraint when a condition type
            # is reused across the update.
            policy.conditions = []
            db.session.flush()
            policy.conditions = _build_conditions(conditions)
            changed_fields.append("conditions")
        db.session.commit()
    log.info(
        f"Updated lockout policy '{policy.name}' (id {policy.id}); "
        f"changed fields: {', '.join(changed_fields) or 'none'}."
    )
    return policy.id, changed_fields


@log_with(log)
def reorder_lockout_policies(policy_ids: list[int], expected_priorities: list[int] | None = None) -> None:
    """
    Rearrange the evaluation order of the given policies.

    The listed policies take the priority values that this very set of policies
    already holds, in ascending order: the first id gets the lowest of those
    values (highest precedence), the last id the highest. Only the *ownership* of
    the values changes, so the set of priorities in the table is an invariant.
    That is what makes this safe whatever numbering the admin uses - contiguous
    ``1,2,3`` reorders exactly like gapped ``10,20,30``, nothing is renumbered,
    no value is ever exhausted and the uniqueness constraint is never strained.

    Any subset may be passed, and policies not listed keep their priority. Only
    the policies that actually move need to be sent: the rows whose position
    changes are the permutation's support, which is a union of cycles, so the
    values they collectively hold are the same before and after - sending just
    them yields exactly the same result as sending everything. A single swap is
    therefore two ids, and two admins rearranging disjoint parts of the list do
    not conflict at all. Passing an already-sorted order is a no-op, which makes
    the operation idempotent.

    *expected_priorities* is an optional per-id assertion, aligned with
    *policy_ids*: the priority each policy is expected to hold right now. It
    turns a concurrent rearrangement from a silent overwrite into a clean
    :class:`ConflictError`, and because it covers only the submitted policies it
    fires solely when someone changed a row this caller is about to move.

    :param policy_ids: the policies to rearrange, in the wanted evaluation order
    :param expected_priorities: the priorities the caller last saw for those
        policies, in the same order; omit to write unconditionally
    :raises ParameterError: if *policy_ids* is not a list of distinct ids, or the
        assertion does not line up with it
    :raises ResourceNotFoundError: if any id does not exist
    :raises ConflictError: if a policy no longer holds its asserted priority
    """
    if not isinstance(policy_ids, (list, tuple)) or not policy_ids:
        raise ParameterError("'policy_ids' must be a non-empty list of policy ids.")
    ids = [_validate_positive_int(policy_id, "policy id") for policy_id in policy_ids]
    if len(set(ids)) != len(ids):
        raise ParameterError("'policy_ids' must not contain the same policy twice.")
    if expected_priorities is not None:
        if not isinstance(expected_priorities, (list, tuple)) or len(expected_priorities) != len(ids):
            raise ParameterError("'expected_priorities' must have one entry per policy id.")
        expected_priorities = [
            _validate_positive_int(priority, "expected priority") for priority in expected_priorities
        ]
    policies = [_get_policy(policy_id) for policy_id in ids]
    if expected_priorities is not None:
        stale = [policy.name for policy, expected in zip(policies, expected_priorities) if policy.priority != expected]
        if stale:
            # Raise error for mismatching policy priorities.
            names = ", ".join(f"'{name}'" for name in stale)
            raise ConflictError(
                "The submitted expected priorities do not match the current "
                f"priorities of these lockout policies: {names}."
            )
    # The values these policies hold, lowest first: reassigned in the requested order.
    priorities = sorted(policy.priority for policy in policies)
    with _unique_conflict_as_400():
        # Park every policy on a value that cannot collide with a live one (ids are
        # unique and priorities are validated >= 1) before assigning the new ones: the
        # uniqueness constraint is checked per statement, so writing the final values
        # straight away would collide with whichever policy still holds them. The
        # flushes force the statement order rather than leaving it to the unit of work.
        for policy in policies:
            policy.priority = -policy.id
        db.session.flush()
        for policy, priority in zip(policies, priorities):
            policy.priority = priority
        db.session.flush()
        db.session.commit()
    log.info(f"Reordered {len(policies)} lockout policies.")


@log_with(log)
def delete_lockout_policy(policy_id: int) -> int:
    """
    Delete a lockout policy with all its stages and actions.

    Existing locks/blocks written by this policy stay in force: live state is
    independent of the policy config.

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
