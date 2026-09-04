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
CRUD layer for conditional-access policies.

The engine (:mod:`privacyidea.lib.conditional_access.engine`) only *reads*
:class:`~privacyidea.models.conditional_access_policy.ConditionalAccessPolicy` rows; this module is
the write path used by the REST API (``/conditionalaccess``) and anything else
that needs to create, edit or delete policies. All input validation lives
here, so the API layer stays a thin request/response wrapper.

A policy is passed around as a plain dict::

    {
        "name": "Brute Force Lock",
        "time_window_seconds": 600,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": "user",
        "count_mode": "PER_REQUEST",
        "reset_on_success": True,
        "counter_types_to_track": ["PIN_FAIL", "MFA_FAIL"],
        "conditions": [
            {"condition_type": "USER_REALM", "operator": "IN", "value": ["sales", "support"]},
        ],
        "stages": [
            {
                "failure_threshold": 5,
                "error_message": "Your account is locked. Please try again in about {duration}.",
                "actions": [
                    {"action_type": "LOCK_USER", "action_value": {"duration_seconds": 600},
                     "retrigger_above_threshold": True},
                    {"action_type": "EMAIL_ADMIN",
                     "action_value": {"smtp_identifier": "mailserver", "subject": "...", "body": "..."},
                     "retrigger_above_threshold": False},
                ],
            },
        ],
    }

``count_mode`` is a :class:`~privacyidea.lib.conditional_access.authentication_event_types.CountMode` name whose valid
values depend on the target (see ``_COUNT_MODES_BY_TARGET``): both targets count event volume per ``authentication_log``
row (``PER_REQUEST``) or per whole authentication attempt (``PER_ATTEMPT``); a ``source_ip`` policy may additionally
count distinct targeted accounts (``DISTINCT_USERS``, the spraying / enumeration signal). When omitted it defaults to
the target's default (``PER_REQUEST`` for ``user``, ``DISTINCT_USERS`` for ``source_ip``).

``reset_on_success`` (default ``True``) decides whether a completed login clears the events counted so far, so the
stage thresholds apply to consecutive failures since that login rather than to every failure in the raw window.
Turning it off is how a threshold comes to mean "this many failures in the window" outright. It governs every count
the policy makes, the pre-auth ``DENY`` decision included. It applies to a ``user`` policy only: a
``source_ip`` policy aggregates a signal across accounts, where one account's legitimate login must not clear it, so
setting it on a ``source_ip`` policy is a :class:`~privacyidea.lib.error.ParameterError` rather than an ignored
setting (the default there is ``False``).

``counter_types_to_track``
values must be
:class:`~privacyidea.lib.conditional_access.authentication_event_types.AuthEventType` names and ``action_type`` values
must be :class:`~privacyidea.lib.conditional_access.engine.ConditionalAccessAction` names; anything else is a
:class:`~privacyidea.lib.error.ParameterError` (fail-closed - a typo must not silently create a policy that never
matches or an action that never fires). Within one stage an action may appear only once - except
``EMAIL_ADMIN``/``EMAIL_USER`` (:data:`REPEATABLE_ACTIONS`), where a second copy is how one stage notifies a
second set of recipients - and no stage may hold two actions of the same mutually exclusive group
(:data:`_EXCLUSIVE_ACTION_GROUPS`: timed vs permanent lock, timed vs permanent block).

``action_value`` is validated under that same rule, against what the engine actually reads (see
:data:`_ACTION_VALUE_VALIDATORS`):

* ``LOCK_USER`` / ``BLOCK_IP`` - a positive number of seconds: an integer, a numeric string, or an object with
  ``duration_seconds`` (``duration`` is an accepted alias). There is no default; without a duration the engine
  skips the action rather than locking permanently.
* ``EMAIL_ADMIN`` / ``EMAIL_USER`` - an object with a non-empty ``subject`` and ``body``, optionally
  ``mimetype`` (``plain``/``html``) and - for ``EMAIL_ADMIN`` - ``recipient_group``.
  ``smtp_identifier`` names the SMTP server that sends it and may be left blank until one is configured, which
  is the one thing the engine needs that the write path does not insist on.
* ``PERMANENT_LOCK_USER`` / ``PERMANENT_BLOCK_IP`` / ``DENY`` - no value. These never expire and never read
  one, so a duration on them would only describe an expiry that does not happen.

A stage's optional ``error_message`` is the text an end user sees when a request is turned away by that stage. It is
opt-in: without one the rejection carries only the generic "Authentication failed.", so privacyIDEA never volunteers
that an account is locked or an IP blocked unless an admin chose to say so - either by writing this field, or by
setting the ``show_default_ca_error_message`` policy, which fills in the default wording for the stage's actions
(:data:`DEFAULT_ERROR_MESSAGES`). ``{duration}`` is substituted with the remaining
time at rejection, and only where there is one: on a permanent lock, a ``DENY`` or a notify-only stage it
is left as written, like any other tag that is not substituted. Every other brace expression is left exactly
as written - braces in prose need no escaping - so only the length is validated here.

``conditions`` is the *applicability* axis, orthogonal to the counting one: it restricts which requests the policy
applies to at all, while the counter types and thresholds decide what trips it. It is optional - a policy without
conditions applies to every request - and is validated against the registries in
:mod:`~privacyidea.lib.conditional_access.conditions` under the same fail-closed rule, since a condition naming an
unknown realm or a misspelled role would otherwise silently never match.
"""

import logging
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from privacyidea.lib import _, lazy_gettext
from privacyidea.lib.conditional_access.authentication_event_types import (
    TRACKABLE_EVENT_TYPES,
    CountMode,
)
from privacyidea.lib.conditional_access.conditions import CONDITION_TYPES
from privacyidea.lib.conditional_access.engine import (ACTION_SEVERITY, ADMIN_RECIPIENT_GROUPS,
                                                       ConditionalAccessAction, ConditionalAccessTarget,
                                                       NOTIFYING_ACTIONS, parse_lock_duration_seconds)
from privacyidea.lib.error import ConflictError, ParameterError, ResourceNotFoundError
from privacyidea.lib.log import log_with
from privacyidea.models import db
from privacyidea.models.conditional_access_policy import (ConditionalAccessPolicy, ConditionalAccessPolicyCondition,
                                               ConditionalAccessPolicyStage, ConditionalAccessStageAction)

log = logging.getLogger(__name__)

# The model column is Unicode(255); checked here so an over-long name raises a clean ParameterError
# instead of a DB-dependent truncation.
MAX_NAME_LENGTH = 255

# Same for a user-facing error message, which is Unicode(500) wherever it is stored - on a stage, and
# on the lock/block state rows that copy it. Shared, so any path taking one as input validates alike.
MAX_ERROR_MESSAGE_LENGTH = 500

# DENY is a standing pre-auth decision, so it defaults to re-triggering while the count stays at or above the
# threshold; the post-response lock/email/block actions default to firing once. A set because both the threshold-0 rule
# and the retrigger default ask "is this a standing verdict?".
DECISION_ACTIONS = frozenset({ConditionalAccessAction.DENY})

# The actions a stage may carry more than once. Only the notifications: repeating EMAIL_ADMIN with a
# different recipient_group (or a different subject and body) is the one case where a second copy of an
# action does something the first cannot - see
# :func:`~privacyidea.lib.conditional_access.engine._send_lockout_email`, which resolves its recipients per
# action. Every other action writes one piece of state or one verdict, so a second copy either does nothing
# or silently overwrites the first.
REPEATABLE_ACTIONS = frozenset({ConditionalAccessAction.EMAIL_ADMIN, ConditionalAccessAction.EMAIL_USER})

# Actions that contradict each other within one stage: the timed and permanent variants write the same
# lock resp. block row, and the upsert refuses to downgrade a permanent restriction to a timed one, so
# which of the two wins depends on the order the rows happen to come back in - ConditionalAccessPolicyStage.actions
# carries no order_by.
_EXCLUSIVE_ACTION_GROUPS = (
    frozenset({ConditionalAccessAction.LOCK_USER, ConditionalAccessAction.PERMANENT_LOCK_USER}),
    frozenset({ConditionalAccessAction.BLOCK_IP, ConditionalAccessAction.PERMANENT_BLOCK_IP}),
)


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
    actions: list[StageActionDefinition] = field(default_factory=list)
    name: str | None = None
    error_message: str | None = None


def conditional_access_policy_to_dict(policy: ConditionalAccessPolicy) -> dict:
    """
    Serialize a :class:`~privacyidea.models.conditional_access_policy.ConditionalAccessPolicy` with
    its stages and actions into the plain-dict shape documented in the module
    docstring (plus the ``id`` of each row).
    """
    # Scalar columns (id, name, time_window_seconds, enabled, dry_run, priority) map straight through, while
    # counter_types_to_track and stages are not table columns, so both are serialized explicitly below.
    result = {column: getattr(policy, column) for column in policy.__table__.columns.keys()}
    result["counter_types_to_track"] = list(policy.counter_types_to_track)
    # An empty list means the policy applies to everyone; conditions carry no id because updates replace them wholesale.
    # They serialize in condition_type order (canonical for an ANDed set), so identical conditions diff cleanly.
    result["conditions"] = [
        {
            "condition_type": condition.condition_type,
            "operator": condition.operator,
            "value": condition.value,
        } for condition in policy.conditions
    ]
    # Stages are listed in ascending failure_threshold order for display, the reverse of the engine's evaluation
    # order, so this sorts explicitly rather than relying on policy.stages' relationship order.
    result["stages"] = [
        {
            "id": stage.id,
            "name": stage.name,
            "error_message": stage.error_message,
            "failure_threshold": stage.failure_threshold,
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


def _get_policy(policy_id: int) -> ConditionalAccessPolicy:
    """
    Fetch one policy row or raise :class:`ResourceNotFoundError`.
    """
    policy = db.session.get(ConditionalAccessPolicy, policy_id)
    if not policy:
        raise ResourceNotFoundError(f"The conditional-access policy with id {policy_id} does not exist.")
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
    existing = db.session.scalar(select(ConditionalAccessPolicy).where(ConditionalAccessPolicy.name == name))
    if existing and existing.id != exclude_id:
        raise ParameterError(f"A conditional-access policy with the name '{name}' already exists.")
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
    existing = db.session.scalar(select(ConditionalAccessPolicy).where(ConditionalAccessPolicy.priority == priority))
    if existing and existing.id != exclude_id:
        raise ParameterError(
            f"A conditional-access policy with priority {priority} already exists ('{existing.name}'); "
            f"priorities must be unique."
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


def validate_error_message(error_message: str | None) -> str | None:
    """
    Validate an optional user-facing error message - the text surfaced to the end user
    when a request is turned away. ``None`` or an empty/blank string
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
        raise ParameterError(_("The error message must be a string."))
    stripped = error_message.strip()
    if not stripped:
        return None
    if len(stripped) > MAX_ERROR_MESSAGE_LENGTH:
        # .format, not an f-string: gettext extracts the literal msgid, so the
        # placeholder has to survive into the translated string.
        raise ParameterError(_("The error message must not exceed {length} characters.").format(
            length=MAX_ERROR_MESSAGE_LENGTH))
    return stripped


# The actions each target permits: a user policy locks/notifies the user, a source-IP policy blocks the IP or alerts
# the admin (LOCK_USER/EMAIL_USER have no user to act on); both may also refuse the request pre-auth via DENY.
_ACTIONS_BY_TARGET = {
    ConditionalAccessTarget.USER: {
        ConditionalAccessAction.LOCK_USER,
        ConditionalAccessAction.PERMANENT_LOCK_USER,
        ConditionalAccessAction.EMAIL_USER,
        ConditionalAccessAction.EMAIL_ADMIN,
        ConditionalAccessAction.DENY,
    },
    ConditionalAccessTarget.SOURCE_IP: {
        ConditionalAccessAction.BLOCK_IP,
        ConditionalAccessAction.PERMANENT_BLOCK_IP,
        ConditionalAccessAction.EMAIL_ADMIN,
        ConditionalAccessAction.DENY,
    },
}


# The default error message for a stage's ``error_message``, per action. Used for two things, which is the point
# of having one table: the policy editor suggests from it, and the runtime falls back to it for a stage that
# carries no error message of its own when the ``show_default_ca_error_message`` policy is on. So an action reads
# the same wherever it is met, and an admin who edits the suggestion is editing the thing they would otherwise
# have got by default. The severity order is not repeated here - it is ``ACTION_SEVERITY``, the one ordering
# there is.
#
# lazy_gettext, not _(): module-level constants are evaluated at import, long before a request and its
# locale exist; ``str()`` at serialization resolves them per admin. That only decides what an admin starts
# editing from - the stored message is a literal shown to the end user in whatever language it was written.
DEFAULT_ERROR_MESSAGES: dict[str, object] = {
    ConditionalAccessAction.PERMANENT_LOCK_USER:
        lazy_gettext("Your account has been locked. Please contact your administrator."),
    ConditionalAccessAction.PERMANENT_BLOCK_IP:
        lazy_gettext("Access from your IP address has been blocked. Please contact your administrator."),
    ConditionalAccessAction.LOCK_USER:
        lazy_gettext("Your account is temporarily locked. Please try again in about {duration}."),
    ConditionalAccessAction.BLOCK_IP:
        lazy_gettext("Access from your IP address is temporarily blocked. Please try again in about {duration}."),
    ConditionalAccessAction.DENY:
        lazy_gettext("Access has been denied."),
    ConditionalAccessAction.EMAIL_USER:
        lazy_gettext("A notification email has been sent to your email address."),
    ConditionalAccessAction.EMAIL_ADMIN:
        lazy_gettext("Your administrator has been notified by email."),
}


def default_error_message(action: str) -> str | None:
    """
    The default error message for *action*, translated against the request locale, or ``None`` where it has none.

    ``None`` covers any action without error message - one that turns nobody away, or one added later - so a caller
    falling back to this never has to know which actions are covered.
    """
    message = DEFAULT_ERROR_MESSAGES.get(action)
    return str(message) if message else None


def compose_default_error_message(action_types: Sequence[str]) -> str | None:
    """
    The default error message for a stage that only reported something, given the *action_types* that ran:
    one sentence per action, most severe first.

    Notifications only. A restriction is described from the row it left behind (see
    :func:`~privacyidea.lib.conditional_access.engine._restrictions_in_force`), so composing one here would tell
    the user twice - and with a ``{duration}`` this side cannot substitute. ``None`` when none of the actions has
    an error message, which keeps such a stage silent.
    """
    carried = set(action_types)
    sentences = [default_error_message(action) for action in ACTION_SEVERITY
                 if action in NOTIFYING_ACTIONS and action in carried]
    return " ".join(sentences) if sentences else None


def get_default_error_messages() -> list[dict[str, str]]:
    """
    The suggested stage error messages, ordered by :data:`~privacyidea.lib.conditional_access.engine.
    ACTION_SEVERITY`, as ``[{"action_type": ..., "message": ...}]``. Translated on each call against the
    request locale.

    An authoring aid for the policy editor, which composes one suggestion for a stage carrying several actions:
    one sentence per action, kept in this order. That is the concatenation the runtime performs too - a request
    reports one sentence per thing that happened to it, ranked the same way - so the wording the editor offers is
    the wording a user would be shown, and the client needs no rule of its own beyond the order it is given.

    The same table backs the runtime fallback under ``show_default_ca_error_message`` (:func:`default_error_message`,
    :func:`compose_default_error_message`), so an admin who edits a suggestion is editing the thing they would
    otherwise have got by default.

    Deliberately not scoped by target: the binding is action to message, and a client picks the entry
    whose action the stage actually carries, so error message for an action a target cannot hold simply never
    matches.
    """
    return [{"action_type": action.value, "message": default_error_message(action)}
            for action in ACTION_SEVERITY if action in DEFAULT_ERROR_MESSAGES]


def get_target_constraints() -> dict[str, dict[str, list]]:
    """
    The per-target policy constraints, as ``{target_value: {"actions": [...], "count_modes": [...],
    "repeatable_actions": [...], "exclusive_action_groups": [[...], ...]}}``: for each target the stage actions it
    allows (:data:`_ACTIONS_BY_TARGET`), the count modes it supports (:data:`_COUNT_MODES_BY_TARGET`), which of its
    actions may appear more than once in one stage (:data:`REPEATABLE_ACTIONS`) and which of its actions contradict
    each other within one stage (:data:`_EXCLUSIVE_ACTION_GROUPS`), all sorted.

    The last two are served rather than left for the client to hard-code, for the same reason the condition-type
    registry is: a rule the editor enforces should come from the one place that defines it. They are filtered to
    the actions the target allows, so a group that cannot arise for this target (the lock pair under
    ``source_ip``, the block pair under ``user``) is not offered as a rule the editor could never apply.
    """
    constraints = {}
    for target in ConditionalAccessTarget:
        actions = _ACTIONS_BY_TARGET[target]
        constraints[target.value] = {
            "actions": sorted(action.value for action in actions),
            "count_modes": sorted(mode.value for mode in _COUNT_MODES_BY_TARGET[target]),
            "repeatable_actions": sorted(action.value for action in REPEATABLE_ACTIONS & actions),
            "exclusive_action_groups": [sorted(action.value for action in group)
                                        for group in _EXCLUSIVE_ACTION_GROUPS if len(group & actions) > 1],
        }
    return constraints


def _validate_target(target) -> "ConditionalAccessTarget":
    """
    Validate the policy target and return the matching :class:`ConditionalAccessTarget`
    member (accepts either ``"user"`` or ``ConditionalAccessTarget.USER``). Persisting the
    member to the ``Unicode`` column stores its value; the follow-up validation
    consumes the member directly.
    """
    try:
        return ConditionalAccessTarget(target)
    except ValueError:
        valid = ", ".join(sorted(t.value for t in ConditionalAccessTarget))
        raise ParameterError(f"Unknown target '{target}'. Valid targets: {valid}.")


def _validate_target_actions(stage_defs: list["StageDefinition"], target: "ConditionalAccessTarget") -> None:
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


# Count modes each target may use, and its default; both support the volume modes (per-request, per-attempt).
# source_ip also offers DISTINCT_USERS, the spraying/enumeration signal, defaulting to it as the characteristic threat.
_COUNT_MODES_BY_TARGET = {
    ConditionalAccessTarget.USER: {CountMode.PER_REQUEST, CountMode.PER_ATTEMPT},
    ConditionalAccessTarget.SOURCE_IP: {CountMode.DISTINCT_USERS, CountMode.PER_REQUEST, CountMode.PER_ATTEMPT},
}
_DEFAULT_COUNT_MODE_BY_TARGET = {
    ConditionalAccessTarget.USER: CountMode.PER_REQUEST,
    ConditionalAccessTarget.SOURCE_IP: CountMode.DISTINCT_USERS,
}


def _validate_count_mode(count_mode, target: "ConditionalAccessTarget") -> str:
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


def _validate_reset_on_success(reset_on_success, target: "ConditionalAccessTarget") -> bool:
    """
    Validate the policy's ``reset_on_success`` for *target* and return it as a plain bool.

    A ``None`` *reset_on_success* yields the target's default: ``True`` for a ``user`` policy, ``False`` for a
    ``source_ip`` one, which never resets - it aggregates a signal across accounts, where one account's legitimate
    login must not clear it (see :func:`~privacyidea.lib.conditional_access.engine._policy_count_ip`). Asking a
    ``source_ip`` policy for it anyway is a :class:`ParameterError` rather than a silently ignored setting, so a
    stored policy never claims a behaviour it does not have.
    """
    if target == ConditionalAccessTarget.SOURCE_IP:
        if reset_on_success is not None and bool(reset_on_success):
            raise ParameterError(
                "reset_on_success is not available for target 'source_ip': a source-IP policy counts across "
                "accounts and never resets on a successful login."
            )
        return False
    return True if reset_on_success is None else bool(reset_on_success)


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


# The ``action_value`` keys each action type accepts, as the engine reads them.
#
# The timed restrictions take a duration; the email actions take the SMTP settings
# :func:`~privacyidea.lib.conditional_access.engine._send_lockout_email` reads. ``identifier`` is the
# accepted alias for ``smtp_identifier``.
_DURATION_KEYS = ("duration_seconds", "duration")
_EMAIL_KEYS = frozenset({"smtp_identifier", "identifier", "recipient_group", "subject", "body",
                         "mimetype"})
# The email fields with no sensible default: without them the engine has nothing to send and skips.
_EMAIL_REQUIRED_TEXT = ("subject", "body")
_EMAIL_MIMETYPES = frozenset({"plain", "html"})


def _validate_duration_action_value(action_type: str, action_value) -> None:
    """
    Validate the ``action_value`` of a timed restriction (``LOCK_USER``, ``BLOCK_IP``): a positive number of
    seconds, given as an integer, a numeric string, or an object carrying ``duration_seconds`` (or ``duration``).

    The check *is* the engine's own parser
    (:func:`~privacyidea.lib.conditional_access.engine.parse_lock_duration_seconds`), so anything storable is
    something the engine can act on. That matters more than the exact shapes accepted: a duration the engine
    cannot parse is not a lock that fires late, it is a lock that never fires at all - the action is skipped
    with a log line and the admin sees a saved policy doing nothing.

    An unknown key inside the object is rejected before the parse, so the near-miss that motivates all of this
    (``lock_duration_seconds``, which nothing reads) is reported by name instead of as a generic "no duration".
    """
    if isinstance(action_value, dict):
        unknown = set(action_value) - set(_DURATION_KEYS)
        if unknown:
            raise ParameterError(f"Unknown key(s) in the action_value of '{action_type}': "
                                 f"{', '.join(sorted(unknown))}. Valid keys: {', '.join(sorted(_DURATION_KEYS))}.")
    if parse_lock_duration_seconds(action_value) is None:
        raise ParameterError(f"Action '{action_type}' needs a positive duration in seconds: give 'action_value' "
                             f"a positive integer, or an object with 'duration_seconds'. Got {action_value!r}.")


def _validate_email_action_value(action_type: str, action_value) -> None:
    """
    Validate the ``action_value`` of an ``EMAIL_ADMIN`` / ``EMAIL_USER`` action: the object of SMTP settings
    :func:`~privacyidea.lib.conditional_access.engine._send_lockout_email` reads, with a non-empty ``subject``
    and ``body``.

    ``smtp_identifier`` is deliberately **not** required, even though the engine needs it to send: the SMTP
    server is a separate configuration object that may legitimately not exist yet, which is why the shipped
    ``MFA_BRUTEFORCE`` template ships it blank for the admin to fill in
    (:mod:`~privacyidea.lib.conditional_access.policy_template`) and why the editor flags a blank or
    stale identifier inline rather than refusing to save. ``subject`` and ``body`` have no such excuse - nothing
    else can supply them.

    ``recipient_group`` is validated for ``EMAIL_USER`` too rather than rejected as a stray key: switching an
    action from ``EMAIL_ADMIN`` carries the whole object over, and dropping a key on a type switch would be a
    silent edit of what the admin wrote.
    """
    if not isinstance(action_value, dict):
        raise ParameterError(f"The action_value of '{action_type}' must be an object with the email settings "
                             f"(smtp_identifier, subject, body).")
    unknown = set(action_value) - _EMAIL_KEYS
    if unknown:
        raise ParameterError(f"Unknown key(s) in the action_value of '{action_type}': "
                             f"{', '.join(sorted(unknown))}. Valid keys: {', '.join(sorted(_EMAIL_KEYS))}.")
    for key, value in action_value.items():
        if value is not None and not isinstance(value, str):
            raise ParameterError(f"'{key}' in the action_value of '{action_type}' must be a string.")
    for key in _EMAIL_REQUIRED_TEXT:
        if not (action_value.get(key) or "").strip():
            raise ParameterError(f"Action '{action_type}' needs a non-empty '{key}' in its action_value.")
    mimetype = (action_value.get("mimetype") or "").strip()
    if mimetype and mimetype not in _EMAIL_MIMETYPES:
        raise ParameterError(f"Unknown mimetype '{mimetype}' for action '{action_type}'. "
                             f"Valid values: {', '.join(sorted(_EMAIL_MIMETYPES))}.")
    recipient_group = (action_value.get("recipient_group") or "").strip()
    if recipient_group and "@" not in recipient_group and recipient_group.lower() not in ADMIN_RECIPIENT_GROUPS:
        raise ParameterError(f"Unknown recipient_group '{recipient_group}' for action '{action_type}'. Use one of "
                             f"{', '.join(sorted(ADMIN_RECIPIENT_GROUPS))}, or a comma-separated list of email "
                             f"addresses.")


def _validate_no_action_value(action_type: str, action_value) -> None:
    """
    Validate the ``action_value`` of an action that takes none: the ``PERMANENT_*`` restrictions and the
    ``DENY`` decision, all of which the engine executes without ever reading it.

    A value is rejected rather than ignored because the one an admin would plausibly write is a duration, and a
    duration on ``PERMANENT_LOCK_USER`` reads as an expiry that never comes: the lock the admin thinks lifts in
    ten minutes holds until someone unlocks it by hand.
    """
    if action_value is not None:
        raise ParameterError(f"Action '{action_type}' takes no action_value; got {action_value!r}.")


# What each action type's ``action_value`` must look like, keyed by action type. Kept **total** over
# :class:`~privacyidea.lib.conditional_access.engine.ConditionalAccessAction` (asserted in the tests, like
# :data:`_ACTIONS_BY_TARGET`): a new action type has to declare what it accepts rather than inheriting
# "anything goes" from a missing entry, which is the very state this table exists to end.
_ACTION_VALUE_VALIDATORS = {
    str(ConditionalAccessAction.LOCK_USER): _validate_duration_action_value,
    str(ConditionalAccessAction.BLOCK_IP): _validate_duration_action_value,
    str(ConditionalAccessAction.EMAIL_ADMIN): _validate_email_action_value,
    str(ConditionalAccessAction.EMAIL_USER): _validate_email_action_value,
    str(ConditionalAccessAction.PERMANENT_LOCK_USER): _validate_no_action_value,
    str(ConditionalAccessAction.PERMANENT_BLOCK_IP): _validate_no_action_value,
    str(ConditionalAccessAction.DENY): _validate_no_action_value,
}


def _validate_threshold_for_actions(threshold: int, actions: list[StageActionDefinition]) -> None:
    """
    Check a stage's ``failure_threshold`` against what its actions do.

    A threshold counts failures, so 1 is the lowest meaningful value for anything
    that reacts to a count. "Lock the user after 0 failures" is not a rule, it is
    a typo, so :attr:`ConditionalAccessAction.LOCK_USER`, ``BLOCK_IP``, the ``PERMANENT_*``
    variants and the ``EMAIL_*`` actions all require at least 1.

    ``DENY`` is the exception, because it does not react to a count at all - it
    states a standing verdict, and re-triggers by default, so at threshold 0 it
    applies to every request the policy covers. That is the lockdown idiom: refuse
    everything the policy covers, whatever the subject has done.

    Scope such a policy with conditions - a ``USER_ROLE NOT_IN [admin-internal]``
    carve-out is the break-glass pattern - because a ``DENY`` writes no state, so no
    ``pi-manage conditionalaccess`` reset command can lift it; recovering from an
    unscoped one means disabling the policy in the database.

    A stage with no actions at all is refused at 0 as well: at any other threshold
    it is merely inert, but at 0 it is indistinguishable from an unfinished rule.

    :raises ParameterError: if the threshold is 0 and the stage has no actions, or
        any action that is not a standing decision
    """
    if threshold > 0:
        return
    offenders = sorted({action.action_type for action in actions if action.action_type not in DECISION_ACTIONS})
    if not actions or offenders:
        listed = ", ".join(offenders) if offenders else "no action"
        raise ParameterError(
            f"A failure_threshold of 0 is only allowed on a stage whose every action is one of "
            f"{', '.join(sorted(DECISION_ACTIONS))} - those state a standing verdict instead of counting "
            f"failures; this stage has {listed}. Use a threshold of 1 or more."
        )


def _validate_stages(stages) -> list[StageDefinition]:
    """
    Validate the stage definitions: a non-empty list of dicts, each with a unique
    ``failure_threshold``, an optional user-facing ``error_message`` and a list of actions whose ``action_type`` is a
    valid :class:`~privacyidea.lib.conditional_access.engine.ConditionalAccessAction`; unknown keys in a stage or
    action dict are rejected so typos fail loudly.

    ``action_value`` is validated per action type against what the engine reads
    (:data:`_ACTION_VALUE_VALIDATORS`): a positive duration for the timed
    ``LOCK_USER``/``BLOCK_IP``, the SMTP settings object for the ``EMAIL_*``
    actions, and no value at all for the ``PERMANENT_*`` restrictions and the
    ``DENY`` decision. This is fail-closed for the same reason the
    counter types and conditions are: an action the engine cannot act on is
    skipped at runtime with nothing but a log line, so a policy that cannot do
    what it says must not be storable. The value itself is stored **unchanged** -
    a duration written as ``"600"`` reads back as ``"600"`` - so the round-trip
    stays an honest record of what the admin sent.

    Each stage's action set is checked as a whole by
    :func:`_validate_stage_action_combination`: an action may appear only once per
    stage unless it is one of the :data:`REPEATABLE_ACTIONS`, and no stage may
    hold two actions of the same mutually exclusive group.

    A threshold counts failures, so it starts at 1. The exception is a stage whose
    every action is a standing ``DENY``: threshold 0 then means "always", the
    lockdown idiom. Any action that reacts to a count is refused at 0 - see
    :func:`_validate_threshold_for_actions`.

    :return: normalized list of :class:`StageDefinition` (without ids)
    """
    if not isinstance(stages, list) or not stages:
        raise ParameterError("'stages' must be a non-empty list of stage definitions.")
    valid_actions = {action.value for action in ConditionalAccessAction}
    allowed_stage_keys = {"name", "error_message", "failure_threshold", "actions"}
    allowed_action_keys = {"action_type", "action_value", "retrigger_above_threshold"}
    normalized = []
    thresholds = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise ParameterError("Each stage must be a dictionary.")
        unknown = set(stage) - allowed_stage_keys - {"id"}
        if unknown:
            raise ParameterError(f"Unknown stage key(s): {', '.join(sorted(unknown))}.")
        # Range-checked here, then checked against the stage's actions once those are known: only an all-DENY
        # stage may use 0 (see _validate_threshold_for_actions).
        threshold = stage.get("failure_threshold")
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 0:
            raise ParameterError("'failure_threshold' must be a non-negative integer.")
        if threshold in thresholds:
            raise ParameterError(f"Duplicate failure_threshold {threshold}: thresholds must be unique within a policy.")
        thresholds.add(threshold)
        name = _validate_stage_name(stage.get("name"))
        error_message = validate_error_message(stage.get("error_message"))
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
            _ACTION_VALUE_VALIDATORS[action_type](action_type, action.get("action_value"))
            # retrigger_above_threshold is a per-action flag, coerced like the policy-level enabled/dry_run booleans;
            # left unset it stays None, and _build_stages resolves it to the action-aware default.
            retrigger_raw = action.get("retrigger_above_threshold")
            retrigger = None if retrigger_raw is None else bool(retrigger_raw)
            normalized_actions.append(
                StageActionDefinition(
                    action_type=action_type,
                    action_value=action.get("action_value"),
                    retrigger_above_threshold=retrigger,
                )
            )
        _validate_threshold_for_actions(threshold, normalized_actions)
        _validate_stage_action_combination(normalized_actions, threshold)
        normalized.append(
            StageDefinition(failure_threshold=threshold, name=name,
                            error_message=error_message, actions=normalized_actions)
        )
    return normalized


def _validate_stage_action_combination(actions: list[StageActionDefinition], threshold: int) -> None:
    """
    Reject an action set one stage cannot meaningfully hold: the same non-repeatable action twice (see
    :data:`REPEATABLE_ACTIONS`), or two actions from the same mutually exclusive group (see
    :data:`_EXCLUSIVE_ACTION_GROUPS`).

    Both shapes are configuration that cannot do what it reads as. A stage carrying ``LOCK_USER`` twice locks
    for whichever of the two durations happens to be applied last; one carrying both the timed and the
    permanent variant resolves by row order, which is not defined. Rejecting them here is the same fail-closed
    stance the rest of this module takes, and the same reason the duplicate ``failure_threshold`` check lives
    in :func:`_validate_stages`: a policy whose stage contradicts itself must not be storable.

    Only *submitted* stages are judged - the check sits inside :func:`_validate_stages` rather than beside
    :func:`_validate_target_actions`, which deliberately re-reads the stored stages on update. A policy
    written before this rule existed therefore stays renameable and switchable; re-sending its stages is what
    re-checks them.

    The stage is named by its ``failure_threshold``, which is unique within a policy and identifies a stage
    across an update - stages are replaced wholesale, so their ids are not stable.
    """
    seen = []
    for action in actions:
        action_type = action.action_type
        if action_type in seen and action_type not in REPEATABLE_ACTIONS:
            raise ParameterError(
                f"Duplicate action '{action_type}' in the stage with failure_threshold {threshold}: a stage can "
                f"carry it only once. Repeatable: {', '.join(sorted(REPEATABLE_ACTIONS))}."
            )
        seen.append(action_type)
    present = set(seen)
    for group in _EXCLUSIVE_ACTION_GROUPS:
        conflict = group & present
        if len(conflict) > 1:
            raise ParameterError(
                f"Action(s) {', '.join(sorted(conflict))} cannot be combined in the stage with failure_threshold "
                f"{threshold}: they are mutually exclusive."
            )


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


def _build_conditions(condition_defs: list[ConditionDefinition]) -> list[ConditionalAccessPolicyCondition]:
    """Turn validated :class:`ConditionDefinition` objects into (unpersisted) ORM objects."""
    return [
        ConditionalAccessPolicyCondition(condition_type=condition.condition_type,
                               operator=condition.operator, value=condition.value)
        for condition in condition_defs
    ]


def _default_retrigger(action: StageActionDefinition) -> bool:
    """The action's ``retrigger_above_threshold``, defaulted by action type when unset."""
    if action.retrigger_above_threshold is None:
        return action.action_type in DECISION_ACTIONS
    return action.retrigger_above_threshold


def _build_stages(stage_defs: list[StageDefinition]) -> list[ConditionalAccessPolicyStage]:
    """
    Turn validated :class:`StageDefinition` objects into (unpersisted) ORM objects.

    An action whose ``retrigger_above_threshold`` is ``None`` (not chosen by the
    admin) gets the action-aware default: the :data:`DECISION_ACTIONS` are
    standing pre-auth decisions that apply while the count stays at or above the
    threshold, so they re-trigger; the post-response effects (lock/email/block)
    fire once, at the exact threshold.
    """
    return [
        ConditionalAccessPolicyStage(
            name=stage.name,
            error_message=stage.error_message,
            failure_threshold=stage.failure_threshold,
            actions=[
                ConditionalAccessStageAction(
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
def list_conditional_access_policies(enabled: bool | None = None) -> list[dict]:
    """
    Return all conditional-access policies as dicts, lowest priority number first (the
    engine's evaluation order: a lower number means higher precedence, matching
    privacyIDEA's policy engine).

    :param enabled: if given, only return policies with this enabled state
    """
    stmt = select(ConditionalAccessPolicy).order_by(ConditionalAccessPolicy.priority.asc())
    if enabled is not None:
        stmt = stmt.where(ConditionalAccessPolicy.enabled == enabled)
    policies = db.session.scalars(stmt).all()
    return [conditional_access_policy_to_dict(policy) for policy in policies]


@log_with(log)
def get_conditional_access_policy(policy_id: int) -> dict:
    """
    Return one conditional-access policy as a dict.

    :raises ResourceNotFoundError: if no policy with this id exists
    """
    return conditional_access_policy_to_dict(_get_policy(policy_id))


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
    :func:`update_conditional_access_policy` and so are only backstopped here; the message
    therefore names every uniqueness rule rather than guessing which one fired.
    The original error is chained, so the traceback still identifies the
    constraint.
    """
    try:
        yield
    except IntegrityError as ex:
        db.session.rollback()
        raise ParameterError(
            "The conditional-access policy conflicts with existing data: name and priority must be unique "
            "across policies, and counter types and stage thresholds unique within a policy."
        ) from ex


@log_with(log)
def create_conditional_access_policy(
    name: str,
    time_window_seconds: int,
    counter_types_to_track: list[str],
    stages: list[dict],
    target: str,
    priority: int,
    enabled: bool = True,
    dry_run: bool = False,
    reset_on_success: bool | None = None,
    count_mode: str | None = None,
    conditions: list[dict] | None = None,
) -> int:
    """
    Create a conditional-access policy with its stages and actions in one transaction.

    See the module docstring for the parameter shapes; everything is validated
    here and a :class:`ParameterError` is raised on any invalid input before
    anything is written. ``target`` is required (no silent default) so the
    target/action compatibility is always a deliberate choice. ``priority`` is
    likewise required (no default) and must be unique across policies, so the
    caller always picks a deliberate, unambiguous precedence.
    ``count_mode`` and ``reset_on_success`` default to the target's default when not given (see
    :func:`_validate_count_mode` and :func:`_validate_reset_on_success`).
    ``conditions`` restricts which requests the policy applies to; omitted (or
    empty) it applies to every request.

    :return: the id of the new policy
    """
    name = _validate_name(name)
    time_window_seconds = _validate_positive_int(time_window_seconds, "time_window_seconds")
    priority = _validate_priority(priority)
    conditional_access_target = _validate_target(target)
    count_mode = _validate_count_mode(count_mode, conditional_access_target)
    reset_on_success = _validate_reset_on_success(reset_on_success, conditional_access_target)
    counter_types = _validate_counter_types(counter_types_to_track)
    stage_defs = _validate_stages(stages)
    _validate_target_actions(stage_defs, conditional_access_target)
    # Checked with `is None`, not `or []`: only an omitted conditions parameter means "applies to everyone";
    # any other falsy value is a 400, not silently "no conditions" - which would widen the policy to every request.
    condition_defs = _validate_conditions([] if conditions is None else conditions)

    policy = ConditionalAccessPolicy(
        name=name,
        time_window_seconds=time_window_seconds,
        enabled=bool(enabled),
        dry_run=bool(dry_run),
        reset_on_success=reset_on_success,
        priority=priority,
        target=conditional_access_target,
        counter_types_to_track=counter_types,
        count_mode=count_mode,
        stages=_build_stages(stage_defs),
        conditions=_build_conditions(condition_defs),
    )
    db.session.add(policy)
    with _unique_conflict_as_400():
        db.session.commit()
    log.info(f"Created conditional-access policy '{name}' (id {policy.id}).")
    return policy.id


@log_with(log)
def update_conditional_access_policy(
    policy_id: int,
    name: str | None = None,
    time_window_seconds: int | None = None,
    counter_types_to_track: list[str] | None = None,
    stages: list[dict] | None = None,
    enabled: bool | None = None,
    dry_run: bool | None = None,
    reset_on_success: bool | None = None,
    priority: int | None = None,
    target: str | None = None,
    count_mode: str | None = None,
    conditions: list[dict] | None = None,
) -> tuple[int, list[str]]:
    """
    Update a conditional-access policy. Only the given (non-``None``) fields are changed.

    ``counter_types_to_track``, ``stages`` and ``conditions`` are **replaced as a
    whole** when given - the delete-orphan cascade drops the previous child rows.
    Passing an empty ``conditions`` list therefore removes every condition, which
    widens the policy to apply to all requests. Locks and blocks this policy has
    already written stay in force: live state is independent of the policy config.

    ``target`` may be changed, but the resulting ``(target, stages)`` combination
    must stay action-compatible (e.g. a ``source_ip`` policy cannot carry
    ``LOCK_USER``); an incompatible change raises :class:`ParameterError`. The same
    holds for ``(target, count_mode)``. ``reset_on_success`` is likewise target-bound: asking for it on a
    ``source_ip`` policy is a :class:`ParameterError`, while switching an existing resetting policy to that target
    clears the flag (and reports it as changed), since the policy no longer resets.
    Existing locks/blocks written before the change are timed and expire on their
    own, so no stale state is left enforced.

    All fields are validated before anything is written. Only the fields the caller
    *sends* are validated, which is what keeps a policy stored before a validation
    rule existed - or written straight through the ORM - from being frozen: its
    ``enabled``/``dry_run`` flags and its name stay changeable, and re-sending
    ``stages`` is the repair path that re-checks them.

    :return: a ``(policy_id, changed_fields)`` tuple, where ``changed_fields`` is
        the list of field names that were provided (and thus written), so the
        caller can record them in the audit log
    :raises ResourceNotFoundError: if no policy with this id exists
    """
    policy = _get_policy(policy_id)
    # Validates everything up front, so an invalid stage list cannot leave a half-applied rename behind.
    if name is not None:
        name = _validate_name(name, exclude_id=policy.id)
    if time_window_seconds is not None:
        time_window_seconds = _validate_positive_int(time_window_seconds, "time_window_seconds")
    if priority is not None:
        priority = _validate_priority(priority, exclude_id=policy.id)
    conditional_access_target = _validate_target(target) if target is not None else None
    if counter_types_to_track is not None:
        counter_types_to_track = _validate_counter_types(counter_types_to_track)
    if stages is not None:
        stages = _validate_stages(stages)
    if conditions is not None:
        conditions = _validate_conditions(conditions)
    # target and stages must stay mutually compatible.
    if conditional_access_target is not None or stages is not None:
        effective_target = (conditional_access_target if conditional_access_target is not None
                            else ConditionalAccessTarget(policy.target))
        effective_stages = stages if stages is not None else policy.stages
        _validate_target_actions(effective_stages, effective_target)
    # target and count_mode must stay mutually compatible: switching the target can invalidate the stored mode (e.g.
    # a user policy's PER_REQUEST is not valid once it becomes a source_ip policy), so validate the effective pair.
    if conditional_access_target is not None or count_mode is not None:
        effective_target = (conditional_access_target if conditional_access_target is not None
                            else ConditionalAccessTarget(policy.target))
        effective_mode = count_mode if count_mode is not None else policy.count_mode
        validated_mode = _validate_count_mode(effective_mode, effective_target)
        if count_mode is not None:
            count_mode = validated_mode
    # target and reset_on_success likewise. Asking for the reset on a source_ip target is rejected, so a policy never
    # stores a setting it does not honour. A target switch that only *inherits* a stored reset is not such a request:
    # the flag is cleared along with the switch (and reported as changed, so the audit shows it), because a policy
    # that no longer resets must not keep saying it does.
    if conditional_access_target is not None or reset_on_success is not None:
        effective_target = (conditional_access_target if conditional_access_target is not None
                            else ConditionalAccessTarget(policy.target))
        if reset_on_success is not None:
            reset_on_success = _validate_reset_on_success(reset_on_success, effective_target)
        elif effective_target == ConditionalAccessTarget.SOURCE_IP and policy.reset_on_success:
            reset_on_success = False

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
        if conditional_access_target is not None:
            policy.target = conditional_access_target
            changed_fields.append("target")
        if enabled is not None:
            policy.enabled = bool(enabled)
            changed_fields.append("enabled")
        if dry_run is not None:
            policy.dry_run = bool(dry_run)
            changed_fields.append("dry_run")
        if reset_on_success is not None:
            policy.reset_on_success = reset_on_success
            changed_fields.append("reset_on_success")
        if count_mode is not None:
            policy.count_mode = count_mode
            changed_fields.append("count_mode")
        if counter_types_to_track is not None:
            # Deletes the existing rows and flushes before inserting the replacements, so a flush never holds two rows
            # with the same (policy_id, counter_type), even when a replacement reuses a counter type.
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
            # Same split-flush replacement, keeping the (policy_id, condition_type) unique constraint when a
            # condition type is reused across the update.
            policy.conditions = []
            db.session.flush()
            policy.conditions = _build_conditions(conditions)
            changed_fields.append("conditions")
        db.session.commit()
    log.info(
        f"Updated conditional-access policy '{policy.name}' (id {policy.id}); "
        f"changed fields: {', '.join(changed_fields) or 'none'}."
    )
    return policy.id, changed_fields


@log_with(log)
def reorder_conditional_access_policies(policy_ids: list[int], expected_priorities: list[int] | None = None) -> None:
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
            names = ", ".join(f"'{name}'" for name in stale)
            raise ConflictError(
                "The submitted expected priorities do not match the current "
                f"priorities of these conditional-access policies: {names}."
            )
    # The values these policies hold, lowest first: reassigned in the requested order.
    priorities = sorted(policy.priority for policy in policies)
    with _unique_conflict_as_400():
        # Parks every policy on a value that can't collide with a live one (ids unique, priorities >= 1), then
        # assigns the new ones, since uniqueness is checked per statement; the flushes force that statement order.
        for policy in policies:
            policy.priority = -policy.id
        db.session.flush()
        for policy, priority in zip(policies, priorities):
            policy.priority = priority
        db.session.flush()
        db.session.commit()
    log.info(f"Reordered {len(policies)} conditional-access policies.")


@log_with(log)
def delete_conditional_access_policy(policy_id: int) -> int:
    """
    Delete a conditional-access policy with all its stages and actions.

    Existing locks/blocks written by this policy stay in force: live state is
    independent of the policy config.

    :return: the id of the deleted policy
    :raises ResourceNotFoundError: if no policy with this id exists
    """
    policy = _get_policy(policy_id)
    name = policy.name
    db.session.delete(policy)
    db.session.commit()
    log.info(f"Deleted conditional-access policy '{name}' (id {policy_id}).")
    return policy_id


@log_with(log)
def enable_conditional_access_policy(policy_id: int, enable: bool = True) -> int:
    """
    Enable or disable a conditional-access policy.

    :return: the id of the policy
    :raises ResourceNotFoundError: if no policy with this id exists
    """
    policy = _get_policy(policy_id)
    policy.enabled = bool(enable)
    db.session.commit()
    log.info(f"{'Enabled' if enable else 'Disabled'} conditional-access policy '{policy.name}' (id {policy.id}).")
    return policy.id
