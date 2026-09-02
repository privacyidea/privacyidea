# (c) NetKnights GmbH 2026,  https://netknights.it
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
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

import ipaddress
import logging
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import ColumnElement

from privacyidea.lib import _
from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType,
                                                                           CA_ENFORCEMENT_EVENT_TYPES,
                                                                           CountMode)
from privacyidea.lib.conditional_access.authentication_log import _naive_utc
from privacyidea.lib.conditional_access.conditions import (condition_sql_filters,
                                                           conditions_match_row,
                                                           policy_conditions_are_scopable,
                                                           policy_matches_context)
from privacyidea.lib.conditional_access.context import CAContext
from privacyidea.lib.conditional_access.outcome_log import outcome_for_stage
from privacyidea.lib.conditional_access.session import get_ca_session, guarded_write
from privacyidea.models import (AuthenticationLog, BlockList, ConditionalAccessOutcome, ConditionalAccessPolicy,
                                ConditionalAccessPolicyCounterType, ConditionalAccessPolicyStage,
                                ConditionalAccessStageAction, UserLockState)
from privacyidea.models.utils import utc_now

if TYPE_CHECKING:
    from privacyidea.lib.user import User

log = logging.getLogger(__name__)


# --- What this module is ----------------------------------------------------------------------------------------------
# The conditional-access engine: it decides whether a request may proceed, then reacts to how that request turned
# out. Two entry points, one per phase of a request:
#
#   evaluate_access_decision()  - pre-auth, before any credential check. Counts the subject's prior events and
#                                 answers DENY / CONTINUE. A DENY refuses this one request and persists
#                                 nothing, so it lifts by itself as the failures age out of the window.
#   evaluate_conditional_access_policies() - post-response, once this request's authentication_log row exists so the
#                                 count includes it. Runs the actions of the single triggered stage: lock, block, email.
#
# Callers gate in a fixed order - locked user, then blocked source IP, then the DENY decision (see
# api/lib/conditional_access.py). A subject is exempted from a policy by an applicability condition on that policy
# (USER_REALM NOT_IN [...]), which excludes it from evaluation entirely.
#
# What a policy counts: its tracked event types, summed, over its window, for one subject. A `user` policy keys on
# the resolved (resolver, uid, realm); a `source_ip` policy keys on the IP and applies even when nobody resolves,
# which is what catches spraying. CountMode decides what "one" means - a row, a whole challenge-response attempt,
# or a distinct targeted account. Only the lock path forgives failures older than the last successful login; the
# pre-auth decision and every source_ip mode deliberately do not.
#
# What trips: stages, each with a failure threshold. Only the highest matching stage of a policy fires, and each of
# its actions decides for itself - once at the exact threshold by default, or on every request at or above it.
#
# Policies run by ascending priority and the first one to decide wins. A `dry_run` policy still produces outcomes
# but changes nothing, which is how an admin measures a policy before enforcing it.
#
# This module writes no history: it returns ConditionalAccessOutcome objects because it never sees the id of the
# authentication-log row they belong to. Its own state writes go through guarded_write, one row per block.
# ----------------------------------------------------------------------------------------------------------------------


class ConditionalAccessAction(str, Enum):
    """
    Action types a :class:`~privacyidea.models.conditional_access_policy.ConditionalAccessPolicyStage`
    can execute when its failure threshold is met.

    :attr:`LOCK_USER`, :attr:`PERMANENT_LOCK_USER`, :attr:`EMAIL_ADMIN`,
    :attr:`EMAIL_USER`, :attr:`BLOCK_IP` and :attr:`PERMANENT_BLOCK_IP` are
    post-response side effects executed by :func:`evaluate_conditional_access_policies`.
    :attr:`DENY` decides the *current* request and is therefore handled by the
    pre-auth decision step (:func:`evaluate_access_decision`) instead. The action
    table stores the string value, so the enum can grow without a schema change.

    An exemption is expressed as an applicability condition on the policy being
    exempted from (``USER_REALM NOT_IN [...]``), not as an action: conditions are
    the only scoping mechanism, and a policy whose conditions do not match is
    skipped in both phases, so the exemption covers the lock, block and email
    actions as well as the :attr:`DENY`.

    The ``PERMANENT_*`` variants ignore ``action_value`` and never expire (only an
    admin reset clears them); the timed :attr:`LOCK_USER` / :attr:`BLOCK_IP` read
    a duration from ``action_value`` and a missing/invalid one is a skipped
    misconfiguration (never silently permanent).

    ``str`` is used instead of ``StrEnum`` (3.11+) for compatibility with Python
    3.10, mirroring
    :class:`~privacyidea.lib.conditional_access.authentication_event_types.AuthEventType`.
    """
    LOCK_USER = "LOCK_USER"
    PERMANENT_LOCK_USER = "PERMANENT_LOCK_USER"
    EMAIL_ADMIN = "EMAIL_ADMIN"
    EMAIL_USER = "EMAIL_USER"
    BLOCK_IP = "BLOCK_IP"
    PERMANENT_BLOCK_IP = "PERMANENT_BLOCK_IP"
    DENY = "DENY"

    def __str__(self) -> str:
        return self.value


#: Every action that has something to tell the user, most severe first - the one ordering there is. It ranks the
#: messages a request produced (:func:`rank_and_deduplicate`) and orders the suggestions the policy editor offers
#: (:data:`~privacyidea.lib.conditional_access.policy.DEFAULT_ERROR_MESSAGES`), so an action reads the same
#: wherever it is met. An action that turns nobody away has nothing to say, so it has no entry.
ACTION_SEVERITY: tuple[ConditionalAccessAction, ...] = (
    ConditionalAccessAction.PERMANENT_LOCK_USER,
    ConditionalAccessAction.PERMANENT_BLOCK_IP,
    ConditionalAccessAction.LOCK_USER,
    ConditionalAccessAction.BLOCK_IP,
    ConditionalAccessAction.DENY,
    ConditionalAccessAction.EMAIL_USER,
    ConditionalAccessAction.EMAIL_ADMIN,
)

#: Severity rank of each action, mirroring
#: :data:`~privacyidea.lib.conditional_access.authentication_event_types._EVENT_RANK`.
_ACTION_RANK: dict[ConditionalAccessAction, int] = {action: rank for rank, action in enumerate(ACTION_SEVERITY)}

#: The actions that only report something, rather than restricting anything. Used to compose the default error message
#: for what a stage did (see :func:`~privacyidea.lib.conditional_access.policy.compose_default_error_message`).
NOTIFYING_ACTIONS = frozenset({ConditionalAccessAction.EMAIL_USER, ConditionalAccessAction.EMAIL_ADMIN})


def most_severe_action(action_types: Iterable[str]) -> ConditionalAccessAction | None:
    """
    The most severe of *action_types* by :data:`ACTION_SEVERITY`, or ``None`` when none of them ranks - an
    action with nothing to say, or one added to :class:`ConditionalAccessAction` without an entry there. So a
    caller never has to know which actions are covered.
    """
    carried = {str(action_type) for action_type in action_types}
    return next((action for action in ACTION_SEVERITY if action.value in carried), None)


class AccessDecision(str, Enum):
    """
    The verdict of the pre-auth conditional-access decision step
    (:func:`evaluate_access_decision`) for a single request.

    :attr:`DENY` rejects the current request outright (no persistent state is
    written); :attr:`CONTINUE` is the default ("no policy denied this request")
    and lets the normal flow proceed. It maps to the
    :attr:`ConditionalAccessAction.DENY` stage action, which - unlike the
    lock/email/block actions - decides the current request and so is handled
    here, before authentication, rather than in the post-response engine.

    Two states rather than a bool, because "no policy had an opinion" and "a
    policy said yes" are worth telling apart in the logs, and because the enum can
    grow if another standing verdict is ever added.
    """
    DENY = "DENY"
    CONTINUE = "CONTINUE"

    def __str__(self) -> str:
        return self.value


class ConditionalAccessTarget(str, Enum):
    """
    The identity a policy counts, thresholds, and enforces against.

    :attr:`USER` (the default) counts one user's failures over the window and
    locks that user. :attr:`SOURCE_IP` counts a single source IP's activity -
    by default the *distinct users* it fails against (spraying), or plain request
    / attempt volume in the other count modes - and blocks that IP. The value
    drives what the threshold keys on and what the action targets (so the allowed
    actions differ by target, enforced in the CRUD layer); the count *mode* within
    a target is a separate axis (see :class:`CountMode`).

    ``str`` is used instead of ``StrEnum`` (3.11+) for compatibility with Python
    3.10, mirroring :class:`ConditionalAccessAction`.
    """
    USER = "user"
    SOURCE_IP = "source_ip"

    def __str__(self) -> str:
        return self.value


#: The action that restricts a given target for a given duration - and so the action a stored restriction is
#: described by. A row remembers its subject and its expiry but not which action wrote it; it does not need to,
#: because those two facts name the action exactly.
RESTRICTION_ACTIONS: dict[tuple[ConditionalAccessTarget, bool], ConditionalAccessAction] = {
    (ConditionalAccessTarget.USER, False): ConditionalAccessAction.LOCK_USER,
    (ConditionalAccessTarget.USER, True): ConditionalAccessAction.PERMANENT_LOCK_USER,
    (ConditionalAccessTarget.SOURCE_IP, False): ConditionalAccessAction.BLOCK_IP,
    (ConditionalAccessTarget.SOURCE_IP, True): ConditionalAccessAction.PERMANENT_BLOCK_IP,
}

#: The targets a restricting action writes to, so a stage that sets out to enforce is described from the row that
#: ends up in force rather than by the action that aimed at it (see :func:`_restrictions_in_force`).
RESTRICTED_TARGET_BY_ACTION: dict[ConditionalAccessAction, ConditionalAccessTarget] = {
    action: target for (target, _permanent), action in RESTRICTION_ACTIONS.items()
}


@dataclass(frozen=True)
class RestrictionStatus:
    """
    The state of an active conditional-access restriction on a single identity:
    a user lock (:func:`get_user_lock`) or a source-IP block
    (:func:`get_ip_block`). Both return this same shape so callers (e.g. the
    ``/auth`` rejection messages) can treat them uniformly.

    :ivar permanent: ``True`` for a restriction that only an admin reset clears.
    :ivar expires_at: naive-UTC expiry of a timed restriction, or ``None`` when
        permanent.
    :ivar seconds_remaining: whole seconds until a timed restriction expires
        (``>= 0``), or ``None`` when permanent.
    :ivar target: whose restriction it is. Part of describing one, and what lets a row with no error message of its
        own be described by the default error message for its shape: the row does not record which action wrote it,
        but target and :attr:`permanent` together name that action exactly.
    :ivar error_message: the message template stored on the restriction when it was applied, or
        ``None`` to say nothing. Rendered with :func:`render_error_message`; kept as the template
        rather than finished text so ``{duration}`` reflects the time left *now*, not at lock time.
        A permanent restriction has no time left, so that tag is left as written.
    """
    permanent: bool
    expires_at: "datetime | None"
    seconds_remaining: "int | None"
    target: "ConditionalAccessTarget"
    error_message: "str | None" = None


# The one tag substituted into a stored error message. Everything else - "{}", "{whatever}" - is left
# exactly as written, so an admin can use braces in ordinary prose without escaping them.
DURATION_TAG = "{duration}"


def _render_duration(restriction: "RestrictionStatus") -> str:
    """
    The remaining time of a timed *restriction* as a rough, user-facing phrase.

    Deliberately coarse: a lock is a thing to come back after, not to count down, and a precise figure
    would only tell an attacker exactly when to retry.
    """
    seconds = max(0, restriction.seconds_remaining or 0)
    # Round up, and never below one minute: "in about 0 minutes" would invite an immediate retry.
    minutes = max(1, -(-seconds // 60))
    if minutes < 60:
        return _("{minutes} minute(s)").format(minutes=minutes)
    return _("{hours} hour(s)").format(hours=-(-minutes // 60))


@dataclass(frozen=True)
class StageMessage:
    """
    One user-facing message a triggered stage produced, already rendered.

    :ivar text: what to show; ``{duration}`` is substituted here, where the duration just written is known.
    :ivar action: the action this message is about, which ranks it (:data:`ACTION_SEVERITY`) so a caller showing
        several leads with the one the user can do least about. Read off the one thing that happened rather than
        derived a second time. Whether the message *replaces* the failure's reason or is appended to it is a
        separate question, answered by whether the request was restricted at all - see
        :attr:`~privacyidea.lib.conditional_access.request_context.PostEvaluation.restricted`.
    """
    text: str
    action: ConditionalAccessAction


def render_error_message(error_message: str | None,
                         restriction: "RestrictionStatus | None" = None) -> str | None:
    """
    The user-facing text for *error_message*, or ``None`` when there is none and the caller should stay
    generic.

    ``{duration}`` only means something where there is a remaining time, so it is substituted only
    against a timed restriction. Everywhere else - a permanent lock or block, a ``DENY``, a stage that
    merely notified - it is left exactly as written, like any other tag we do not substitute. That is a
    misconfiguration rather than a case to handle: a countdown was written for something that does not
    count down.

    A plain string replacement, not :func:`_safe_format`: with a single tag there is nothing to parse,
    a stray brace in the admin's prose cannot make the substitution fail (``format_map`` would raise on
    a bare ``{}`` and return the template untouched, silently dropping the duration), and no attribute
    traversal is reachable from admin-supplied text.

    Call this only when the request is actually being turned away. An expired or absent lock is not a
    rejection at all - there is nothing to tell the user - so passing ``None`` to mean "not locked"
    would log a missing duration for a login that is about to succeed.

    :param error_message: the stored template, or ``None``
    :param restriction: the restriction in force, when there is one; ``None`` for a decision or a
        notification, which turn a request away without leaving anything behind
    """
    if not error_message:
        return None
    if DURATION_TAG not in error_message:
        return error_message
    if restriction is None or restriction.permanent or restriction.seconds_remaining is None:
        # debug: the editor is where this is caught, and the line repeats on every rejected request from
        # a caller we do not control - at any louder level a permanently locked account would let someone
        # else choose our log volume.
        log.debug(f"Leaving {DURATION_TAG} unsubstituted: it was configured for a restriction that has no "
                  f"remaining time.")
        return error_message
    return error_message.replace(DURATION_TAG, _render_duration(restriction))


def rank_and_deduplicate(messages: list["StageMessage"]) -> list["StageMessage"]:
    """
    The messages to show, ordered by :data:`ACTION_SEVERITY` and with each distinct sentence kept once.

    Ranked before de-duplicating, so where an admin configured the same sentence on a notify-only stage and on a
    locking one, the copy kept is the one labelled with the severer action - and a reader of the result sees the
    ranking the stage earned. The sort is stable, so messages of equal severity stay in the order they were
    collected in. A message about an action with no rank sorts last, so an oversight in :data:`ACTION_SEVERITY`
    costs the order rather than the message.

    Used by both paths that describe a restriction - the post-response evaluation and the pre-check that refuses
    the requests after it - so the same state cannot be worded differently depending on which one answers.
    """
    seen: set[str] = set()
    unique: list[StageMessage] = []
    for message in sorted(messages, key=lambda message: _ACTION_RANK.get(message.action, len(ACTION_SEVERITY))):
        if message.text not in seen:
            seen.add(message.text)
            unique.append(message)
    return unique


def restriction_messages(*restrictions: "RestrictionStatus | None",
                         use_default_error_message: bool = False) -> list["StageMessage"]:
    """
    The error message of each of *restrictions* that carries any, ranked and de-duplicated.

    Silent by default: a restriction carrying no error message produces none, and ``None`` (nothing in force)
    contributes nothing at all. With *use_default_error_message* the wording for the restriction's shape stands
    in for a missing one, which is what the ``show_default_ca_error_message`` policy buys - an admin gets the same
    sentence they would have got by writing the suggestion onto every stage by hand. Silent is not the same as
    generic: producing no message is what leaves a rejection indistinguishable from any other failure, and what
    the response then says instead is the caller's question to answer.

    Both paths that describe a restriction come through here, so the error message cannot depend on which one
    answered: the pre-check that refuses a request already restricted, and the evaluation that just restricted
    it.
    """
    # Deferred: policy imports the action/target enums from here, so importing it at module level
    # would close a cycle. Same reason as run_post_eval's import of this module.
    from privacyidea.lib.conditional_access.policy import default_error_message

    messages = []
    for restriction in restrictions:
        if not restriction:
            continue
        # The row records what is in force, not which action put it there - and those two facts name it exactly.
        action = RESTRICTION_ACTIONS[(restriction.target, restriction.permanent)]
        template = restriction.error_message
        if not template and use_default_error_message:
            template = default_error_message(action)
        text = render_error_message(template, restriction)
        if text:
            messages.append(StageMessage(text, action))
    return rank_and_deduplicate(messages)


@dataclass
class ConditionalAccessEvaluation:
    """
    What one post-response evaluation produced: the user-facing messages to surface on the current response, and the
    outcomes to record as the request's conditional-access history.

    Each message is a :class:`StageMessage`, already rendered and ordered by :data:`ACTION_SEVERITY` so a caller
    showing several leads with the one the user can do least about. Wording for a restriction is rendered from the
    row now in force, not by the stage that wrote it: several policies can restrict the same subject in one request
    and only one row survives them. Notification error message comes from the stage, the only place it exists.

    The engine returns these instead of writing the history itself. It has no access to the id of the
    authentication-log row (it runs before the row exists on the pre-auth path, and never sees it on the other), and
    keeping the write out of here is what leaves the engine free of Flask and of the request lifecycle - see
    :mod:`privacyidea.lib.conditional_access.outcome_log`.

    Also used as the per-policy result inside :func:`_evaluate_policy`, since "what this produced" is the same shape
    for one policy and for all of them.
    """
    messages: list[StageMessage] = field(default_factory=list)
    outcomes: list[ConditionalAccessOutcome] = field(default_factory=list)
    #: Which rows this evaluation left a restriction on, so the caller describes what ended up in force there -
    #: see :func:`_restrictions_in_force`. A restricting action that never wrote anything is not in here: the
    #: caller answers a request as a rejection on the strength of this set.
    enforced_targets: set[ConditionalAccessTarget] = field(default_factory=set)


@dataclass
class AccessDecisionResult:
    """
    The verdict of the pre-auth decision step plus the outcomes it produced.

    A ``DENY`` yields an outcome (enforced or dry-run); a ``CONTINUE`` yields none, since a policy with no opinion has
    nothing to record.

    One type for a single policy's contribution (:func:`_policy_access_decision`) and for the whole evaluation
    (:func:`evaluate_access_decision`), the way :class:`ConditionalAccessEvaluation` serves one policy and all of
    them. Hence the default: :attr:`AccessDecision.CONTINUE` reads "this policy has no opinion" for the one and
    "no policy decided" for the other - which is what ``CONTINUE`` already means, so nothing needs a separate
    ``None`` to say it.
    """
    decision: AccessDecision = AccessDecision.CONTINUE
    outcomes: list[ConditionalAccessOutcome] = field(default_factory=list)
    # The error message of the stage that denied, read straight off it: a DENY decides this one request and
    # persists nothing, so unlike a lock there is no state row to copy it to and nothing to go stale.
    # None for ALLOW and CONTINUE, which turn no request away.
    error_message: "str | None" = None


def _resolved(user: "User") -> bool:
    """
    Return ``True`` only for a fully resolved user, i.e. one with a complete
    ``(resolver, uid, realm)`` identity tuple. The lock state and the
    authentication-log count are both keyed by that tuple, so an unresolved user
    (e.g. ``USER_UNKNOWN``, which has ``uid=None``) is never counted or locked
    here. TODO replace later with #5170
    """
    return bool(user and user.uid and user.resolver and user.realm)


def _types_label(types: "list[str]") -> str:
    """Render a policy's tracked counter types for log messages, e.g.
    ``PASSWORD_FAIL, TOKEN_ONLY_FAIL`` (or ``(none)`` for an empty list)."""
    return ", ".join(types) if types else "(none)"


def _count_events(subject: Sequence[ColumnElement[bool]], event_types: list[str], window_seconds: int,
                  window_end: datetime | None = None, since_last_success: bool = False) -> int:
    """
    Count the ``authentication_log`` rows matching *subject* and *event_types* within the sliding window
    ``[window_end - window_seconds, window_end]`` (``PER_REQUEST``).

    *subject* is the list of SQLAlchemy WHERE conditions that identify whose rows to count - e.g.
    ``[AuthenticationLog.source_ip == ip]`` or the ``(resolver, uid, realm)`` equality triple; it is spread into every
    ``WHERE`` (including the last-success lookup) so the index the caller documents is used.

    With *since_last_success* the count is floored at the subject's most recent completed login
    (:attr:`AuthEventType.LOGIN_SUCCESS`) inside the window: failures preceding a successful login no longer count, so
    a success clears the slate. ``> last_success`` excludes the success row itself (a different event_type anyway, but
    the strict bound also keeps a same-instant failure from being masked by the success). The forensic log is
    untouched - only the *counted* range is narrowed.
    """
    window_end = _naive_utc(window_end) if window_end is not None else utc_now()
    window_start = window_end - timedelta(seconds=window_seconds)
    type_values = [str(t) for t in event_types]
    lower_bound = AuthenticationLog.timestamp >= window_start
    if since_last_success:
        last_success = get_ca_session().scalar(
            select(func.max(AuthenticationLog.timestamp))
            .where(*subject,
                   AuthenticationLog.event_type == str(AuthEventType.LOGIN_SUCCESS),
                   AuthenticationLog.timestamp >= window_start,
                   AuthenticationLog.timestamp <= window_end))
        if last_success is not None:
            lower_bound = AuthenticationLog.timestamp > last_success
    stmt = (select(func.count())
            .select_from(AuthenticationLog)
            .where(*subject,
                   AuthenticationLog.event_type.in_(type_values),
                   lower_bound,
                   AuthenticationLog.timestamp <= window_end))
    return get_ca_session().scalar(stmt) or 0


def count_user_events(resolver: str, uid: str, realm: str,
                      event_types: list[str],
                      window_seconds: int, window_end: datetime | None = None,
                      since_last_success: bool = False,
                      extra_filters: "Sequence | None" = None) -> int:
    """
    Count the ``authentication_log`` rows for one user identity and event
    type(s) within a sliding time window ``[window_end - window_seconds, window_end]``.

    *event_types* is a list of :class:`AuthEventType` values; events matching
    **any** of them are counted together (one combined count), so a policy
    tracking ``[PASSWORD_FAIL, TOKEN_ONLY_FAIL]`` trips on the total of both
    rather than on either in isolation.

    The ``WHERE`` column order matches the composite index
    ``ix_authlog_user_event_time`` so this is an index range scan (the ``IN``
    over the event types still uses the same composite index).

    With *since_last_success* the count is floored at the user's most recent
    completed login (:attr:`AuthEventType.LOGIN_SUCCESS`) inside the window:
    failures that precede a successful login no longer count, so a successful
    authentication clears the slate. This makes the lock fire on *consecutive*
    failures since the last login rather than on every failure that happens to
    fall in the raw window (a legitimate user who just logged in is not re-locked
    by stale failures on the next single typo). The forensic log is untouched —
    only the *counted* range is narrowed.

    :param resolver: resolver name of the user
    :param uid: resolver-local user id
    :param realm: realm name of the user
    :param event_types: the list of :class:`AuthEventType` values to
        count; rows matching any of them are counted together
    :param window_seconds: width of the look-back window in seconds
    :param window_end: the instant the window ends; defaults to :func:`utc_now`.
        An aware value is normalized to naive UTC to match the stored
        ``timestamp`` column.
    :param since_last_success: only count events after the most recent
        ``LOGIN_SUCCESS`` in the window (a successful login resets the counter)
    :param extra_filters: extra SQLAlchemy predicates ANDed into the ``WHERE``, narrowing which
        rows count to the ones a policy's conditions describe (see
        :func:`~privacyidea.lib.conditional_access.conditions.condition_sql_filters`). ``None`` or
        empty counts every row of the subject.
    :return: the number of matching events
    """
    return _count_events([AuthenticationLog.resolver == resolver,
                          AuthenticationLog.uid == uid,
                          AuthenticationLog.realm == realm,
                          *(extra_filters or ())],
                         event_types, window_seconds, window_end, since_last_success)


def count_distinct_users_for_ip(source_ip: str, event_types: list[str], window_seconds: int,
                                window_end: datetime | None = None,
                                extra_filters: "Sequence | None" = None) -> int:
    """
    Count the number of **distinct accounts** a single *source_ip* targeted with any of *event_types* within the
    sliding window ``[window_end - window_seconds, window_end]``. This is the password-spraying / enumeration signal:
    one source IP hitting many different accounts, where per-user counting never trips because each account only sees a
    failure or two.

    An account is keyed by the ``(username, realm, resolver)`` triple - the **attempted** login, not the internal
    ``uid`` - so it counts the same for a resolved user and for an unresolved one: an attacker guessing thousands of
    *nonexistent* usernames (credential stuffing / user enumeration) is counted as thousands of distinct accounts,
    whereas keying on ``(resolver, uid, realm)`` would collapse every unresolved attempt into the single
    ``(NULL, NULL, NULL)`` identity and never trip. A request that carries no user at all (e.g. an initial
    usernameless passkey authentication) has a ``NULL`` username and collapses into a single group - harmless, since
    those are not an account-targeting signal.

    Known limitation: a serial-only authentication against a token that has *no user assigned* also produces a
    ``NULL``-username row, so brute-forcing many such userless tokens from one IP collapses into that same single
    group and is not seen here. That is deliberate - there is no account being targeted: a single userless token is
    bounded by its own fail counter, and the many-tokens case is raw volume, left to generic rate-limiting rather
    than to this distinct-account signal.

    Unlike :func:`count_user_events` there is **no** ``since_last_success`` reset: a successful login by one account
    must not clear a spraying signal aggregated across all accounts of the IP.

    A portable ``COUNT(*)`` over a ``SELECT DISTINCT`` subquery is used. The ``WHERE`` matches
    ``ix_authlog_ip_event_time`` (source_ip, event_type, timestamp) so the subquery is an index range scan; the
    ``DISTINCT`` over the three account columns is a cheap sort/hash over that small per-IP result set.

    :param source_ip: the client IP whose distinct targeted accounts are counted
    :param event_types: the list of :class:`AuthEventType` values to
        count; rows matching any of them contribute
    :param window_seconds: width of the look-back window in seconds
    :param window_end: the instant the window ends; defaults to :func:`utc_now`.
        The engine passes the single reference instant captured for the whole
        evaluation so this count shares it with the new block's expiry.
:param extra_filters: extra SQLAlchemy predicates ANDed into the ``WHERE``, narrowing which
        rows count to the ones a policy's conditions describe (see
        :func:`~privacyidea.lib.conditional_access.conditions.condition_sql_filters`). ``None`` or
        empty counts every row of the subject.
    :return: the number of distinct targeted accounts
    """
    window_end = _naive_utc(window_end) if window_end is not None else utc_now()
    window_start = window_end - timedelta(seconds=window_seconds)
    type_values = [str(t) for t in event_types]
    distinct_accounts = (select(AuthenticationLog.username, AuthenticationLog.realm, AuthenticationLog.resolver)
                         .where(AuthenticationLog.source_ip == source_ip,
                                AuthenticationLog.event_type.in_(type_values),
                                AuthenticationLog.timestamp >= window_start,
                                AuthenticationLog.timestamp <= window_end,
                                *(extra_filters or ()))
                         .distinct()
                         .subquery())
    return get_ca_session().scalar(select(func.count()).select_from(distinct_accounts)) or 0


def _count_matching_attempts(rows: Sequence[AuthenticationLog], tracked_types: set[str],
                             since_last_success: bool = False,
                             row_filter: "Callable[[AuthenticationLog], bool] | None" = None) -> int:
    """
    Reduce authentication-log rows to one representative event per attempt and count the attempts whose
    representative is in *tracked_types*.

    All rows sharing an ``attempt_id`` are one authentication attempt. Its representative — the event that classifies
    the whole attempt — is the :attr:`AuthEventType.LOGIN_SUCCESS` row if the attempt ever logged in (a completed
    success is terminal: a later stray answer replayed on the same, now-answered challenge maps to the same
    ``attempt_id`` but must not undo the success), otherwise the **latest** row by ``id``. Row ``id`` is the insertion
    order, which orders the multichallenge steps correctly independent of event type — e.g. a wrong answer *then* a
    continue reads as in-progress (latest = the continue), while a continue *then* a wrong answer reads as failed
    (latest = the fail), which an event-type ranking could not distinguish.

    The representative is carried as the *row*, not just its event type, because *row_filter* has to be asked of the
    event that classifies the attempt. For a succeeded attempt those are two different rows — the type comes from the
    success while the latest row may be that stray replay — and a policy tracking ``LOGIN_SUCCESS`` (a rate limit
    tracking every type) would otherwise classify by one row and filter by another.

    Comparisons rely on :class:`AuthEventType` being a ``str`` subclass, so the stored ``event_type`` strings match
    the enum members directly — no conversion needed.

    :param rows: the authentication-log rows of the attempts to reduce
    :param tracked_types: the event types a representative must be in to count the attempt
    :param since_last_success: only count attempts whose latest row is newer than the last ``LOGIN_SUCCESS`` row
    :param row_filter: an optional ``(row) -> bool`` applied to each attempt's representative row; an attempt whose
        representative it rejects does not count. ``None`` counts every reduced attempt. This is where a policy's
        conditions scope a ``PER_ATTEMPT`` count (see
        :func:`~privacyidea.lib.conditional_access.conditions.conditions_match_row`) — they cannot be applied to
        *rows* before this reduction without corrupting it.
    :return: the number of matching attempts
    """
    latest: dict[str, AuthenticationLog] = {}
    success: dict[str, AuthenticationLog] = {}
    last_success_id = -1
    # First pass: for each row, track its attempt's latest row, its latest success row, and the newest LOGIN_SUCCESS
    # id (the since_last_success reset point).
    for row in rows:
        if row.event_type in CA_ENFORCEMENT_EVENT_TYPES:
            # A row conditional access wrote for its own rejection must never classify the attempt: as the latest row
            # it would replace a real tracked failure with an untracked type and drop an already-counted attempt,
            # stalling an escalation once the lock expires.
            continue
        if row.event_type == AuthEventType.LOGIN_SUCCESS:
            last_success_id = max(last_success_id, row.id)
            won = success.get(row.attempt_id)
            if won is None or row.id > won.id:
                success[row.attempt_id] = row
        current = latest.get(row.attempt_id)
        if current is None or row.id > current.id:
            latest[row.attempt_id] = row
    cutoff_id = last_success_id if since_last_success else -1
    matches = 0
    # Second pass: for each attempt, count it if its representative's event type matches, it is newer than the last
    # success when flooring, and the row filter admits it.
    for attempt_id, row in latest.items():
        representative = success.get(attempt_id) or row
        if representative.event_type not in tracked_types or row.id <= cutoff_id:
            continue
        if row_filter is not None and not row_filter(representative):
            continue
        matches += 1
    return matches


def _count_attempts(subject: Sequence[ColumnElement[bool]], event_types: list[str], window_seconds: int,
                    window_end: datetime | None = None, since_last_success: bool = False,
                    row_filter: "Callable[[AuthenticationLog], bool] | None" = None) -> int:
    """
    Count whole authentication *attempts* matching *subject* whose representative event is in *event_types*, within the
    sliding window ``[window_end - window_seconds, window_end]`` (``PER_ATTEMPT``).

    Every in-window row of the subject is fetched, **whatever its event type** (a non-tracked ``LOGIN_SUCCESS`` must be
    able to supersede a tracked failure within its attempt), then grouped by ``attempt_id`` and reduced to one
    representative each (see :func:`_count_matching_attempts`). Only the *subject* + *timestamp* predicate hits the
    index, so callers document the matching ``*_time`` index. The rows are the small in-window set for one subject, so
    fetching full :class:`AuthenticationLog` objects (rather than columns) is negligible and keeps the reduction working
    on named attributes.

    The one exception is :data:`CA_ENFORCEMENT_EVENT_TYPES`: those rows classify a request conditional access itself
    rejected, they can never be an attempt's representative (see :func:`_count_matching_attempts`), and excluding them
    here rather than in Python means they cost neither a row over the wire nor an ORM object. It is an extra predicate
    on the same index range scan, not a different plan.

    *subject* deliberately carries no condition predicates - unlike the row counters, which take them as
    ``extra_filters``. Narrowing the ``WHERE`` here would hide rows from the reduction rather than from the count, and
    an attempt reduced from a subset of its own rows is misclassified, not narrowed. Conditions arrive as *row_filter*
    instead and are applied to the reduced representative (see :func:`_count_matching_attempts`).
    """
    window_end = _naive_utc(window_end) if window_end is not None else utc_now()
    window_start = window_end - timedelta(seconds=window_seconds)
    rows = get_ca_session().scalars(
        select(AuthenticationLog)
        .where(*subject,
               AuthenticationLog.timestamp >= window_start,
               AuthenticationLog.timestamp <= window_end,
               AuthenticationLog.event_type.notin_(sorted(str(event) for event in CA_ENFORCEMENT_EVENT_TYPES)))).all()
    return _count_matching_attempts(rows, set(event_types), since_last_success=since_last_success,
                                    row_filter=row_filter)


def count_user_attempts(resolver: str, uid: str, realm: str, event_types: list[str],
                        window_seconds: int, window_end: datetime | None = None,
                        since_last_success: bool = False,
                        row_filter: "Callable[[AuthenticationLog], bool] | None" = None) -> int:
    """
    Count whole authentication *attempts* (not individual ``authentication_log`` rows) for one user identity whose
    representative event matches *event_types*, within a sliding time window ``[window_end - window_seconds,
    window_end]``. This is the
    :attr:`~privacyidea.lib.conditional_access.authentication_event_types.CountMode.PER_ATTEMPT` counterpart of
    :func:`count_user_events`, so a multi-request challenge / multichallenge login counts once. The ``WHERE``
    (resolver, uid, realm, timestamp) matches the ``ix_authlog_user_time`` index.

    :param resolver: resolver name of the user
    :param uid: resolver-local user id
    :param realm: realm name of the user
    :param event_types: the event types an attempt's representative must match (a list; may hold a single entry)
    :param window_seconds: width of the look-back window in seconds
    :param window_end: the instant the window ends; defaults to :func:`utc_now`. An aware value is normalized to
        naive UTC.
    :param since_last_success: only count attempts after the user's most recent completed login in the window (a
        successful login resets the counter); see :func:`_count_matching_attempts`
    :param row_filter: an optional ``(row) -> bool`` narrowing the count to the attempts a policy's conditions
        describe. It takes a row predicate rather than the ``extra_filters`` SQL predicates the event counters take:
        the conditions must be applied to the *reduced* representative, never to the rows the reduction reads (see
        :func:`_count_attempts`). ``None`` counts every attempt of the subject.
    :return: the number of matching attempts
    """
    return _count_attempts([AuthenticationLog.resolver == resolver,
                            AuthenticationLog.uid == uid,
                            AuthenticationLog.realm == realm],
                           event_types, window_seconds, window_end, since_last_success,
                           row_filter=row_filter)


def count_ip_events(source_ip: str, event_types: list[str], window_seconds: int,
                    window_end: datetime | None = None, extra_filters: "Sequence | None" = None) -> int:
    """
    Count the ``authentication_log`` rows a single *source_ip* produced with any of *event_types* within the sliding
    window ``[window_end - window_seconds, window_end]``. This is the
    :attr:`~privacyidea.lib.conditional_access.authentication_event_types.CountMode.PER_REQUEST` counterpart of
    :func:`count_distinct_users_for_ip`: raw per-IP request volume rather than the distinct-accounts signal - the IP
    analogue of :func:`count_user_events` keyed on the source IP instead of the ``(resolver, uid, realm)`` triple.

    Unlike the user counter there is **no** ``since_last_success`` reset: a successful login by one account must not
    clear a volume signal aggregated across everything the IP sent (same reasoning as
    :func:`count_distinct_users_for_ip`). Every matching row counts regardless of user, so userless serial attempts -
    the documented blind spot of the distinct-accounts signal - do contribute here.

    The ``WHERE`` matches ``ix_authlog_ip_event_time`` (source_ip, event_type, timestamp) so this is an index range
    scan.

    ``since_last_success`` is intentionally not exposed: the shared core supports it, but enabling it for an IP would
    reset the whole IP's counter on *any* one account's successful login (e.g. one legitimate user behind a NAT
    clearing the volume signal for everyone behind it) - a real semantic decision, not just wiring.

    :param source_ip: the client IP whose events are counted
    :param event_types: the list of :class:`AuthEventType` values to count; rows matching any of them are counted
        together
    :param window_seconds: width of the look-back window in seconds
    :param window_end: the instant the window ends; defaults to :func:`utc_now`. An aware value is normalized to naive
        UTC.
    :param extra_filters: extra SQLAlchemy predicates ANDed into the ``WHERE``, narrowing which
        rows count to the ones a policy's conditions describe (see
        :func:`~privacyidea.lib.conditional_access.conditions.condition_sql_filters`). ``None`` or
        empty counts every row of the subject.
    :return: the number of matching events
    """
    return _count_events([AuthenticationLog.source_ip == source_ip, *(extra_filters or ())],
                         event_types, window_seconds, window_end)


def count_ip_attempts(source_ip: str, event_types: list[str], window_seconds: int,
                      window_end: datetime | None = None,
                      row_filter: "Callable[[AuthenticationLog], bool] | None" = None) -> int:
    """
    Count whole authentication *attempts* (not individual ``authentication_log`` rows) a single *source_ip* produced
    whose representative event matches *event_types*, within the sliding window ``[window_end - window_seconds,
    window_end]``. The
    :attr:`~privacyidea.lib.conditional_access.authentication_event_types.CountMode.PER_ATTEMPT` counterpart of
    :func:`count_ip_events`, so a multi-request challenge / multichallenge login counts once - the IP analogue of
    :func:`count_user_attempts`.

    As with :func:`count_ip_events` there is **no** ``since_last_success`` reset (see that function for why it is not
    exposed for an IP). The ``WHERE`` (source_ip, timestamp) matches the ``ix_authlog_ip_time`` index.

    :param source_ip: the client IP whose attempts are counted
    :param event_types: the event types an attempt's representative must match
    :param window_seconds: width of the look-back window in seconds
    :param window_end: the instant the window ends; defaults to :func:`utc_now`. An aware value is normalized to naive
        UTC.
    :param row_filter: an optional ``(row) -> bool`` narrowing the count to the attempts a policy's conditions
        describe. It takes a row predicate rather than the ``extra_filters`` SQL predicates the event counters take:
        the conditions must be applied to the *reduced* representative, never to the rows the reduction reads (see
        :func:`_count_attempts`). ``None`` counts every attempt of the subject.
    :return: the number of matching attempts
    """
    return _count_attempts([AuthenticationLog.source_ip == source_ip],
                           event_types, window_seconds, window_end, row_filter=row_filter)


def _count_scoping(policy: ConditionalAccessPolicy) -> "tuple[list | None, Callable[[AuthenticationLog], bool] | None]":
    """
    The policy's conditions as the two things a counter can consume: SQL predicates for the row counters, and a row
    predicate for the attempt counters.

    Both express the same conditions and are gated by the same rule
    (:func:`~privacyidea.lib.conditional_access.conditions.policy_conditions_are_scopable`) - a policy that cannot
    have *all* of its conditions honoured counts unscoped either way, rather than half-scoped. They differ only in
    *where* they can be applied: a row counter narrows its ``WHERE``, while an attempt counter must reduce whole
    attempts first and apply the conditions to the reduced representative (see :func:`_count_attempts` for why
    filtering rows there would misclassify attempts rather than narrow the count).

    :param policy: the policy whose conditions are translated
    :return: ``(sql_filters, row_filter)``, both ``None`` when the policy's conditions cannot scope a count
    """
    if not policy_conditions_are_scopable(policy):
        return None, None
    return condition_sql_filters(policy), lambda row: conditions_match_row(policy, row)


def _policy_count(policy: ConditionalAccessPolicy, user: "User", window_end: datetime,
                  since_last_success: bool = False) -> int:
    """
    Count a user-target policy's events (``PER_REQUEST``) or attempts (``PER_ATTEMPT``) over its window, per the
    policy's :attr:`~privacyidea.models.conditional_access_policy.ConditionalAccessPolicy.count_mode`, scoped to the
    rows the policy's conditions describe (:func:`_count_scoping`). (Source-IP policies dispatch separately via
    :func:`_policy_count_ip`.)

    :param policy: the policy whose ``time_window_seconds`` and ``counter_types_to_track`` are counted over
    :param user: the resolved user to count for
    :param window_end: the instant the window ends (reference time)
    :param since_last_success: True to floor the count at the user's last completed login in the window (a successful
        login resets the counter); both callers - the pre-auth decision and the post-response evaluation - pass the
        policy's :attr:`~privacyidea.models.conditional_access_policy.ConditionalAccessPolicy.reset_on_success`.
        Applies to both user modes —
        ``PER_REQUEST`` floors at the last ``LOGIN_SUCCESS`` row, ``PER_ATTEMPT`` at the last successful attempt.
        (Source-IP ``DISTINCT_USERS`` deliberately never resets, which is why it is a separate mode and does not go
        through here.)
    :return: the event count (``PER_REQUEST``) or the attempt count (``PER_ATTEMPT``)
    """
    sql_filters, row_filter = _count_scoping(policy)
    if policy.count_mode == CountMode.PER_ATTEMPT:
        return count_user_attempts(user.resolver, user.uid, user.realm,
                                   policy.counter_types_to_track, policy.time_window_seconds,
                                   window_end=window_end, since_last_success=since_last_success,
                                   row_filter=row_filter)
    return count_user_events(user.resolver, user.uid, user.realm,
                             policy.counter_types_to_track, policy.time_window_seconds,
                             window_end=window_end, since_last_success=since_last_success,
                             extra_filters=sql_filters)


def _policy_count_ip(policy: ConditionalAccessPolicy, source_ip: str, window_end: datetime) -> int:
    """
    Count a source-IP-target policy's subject over its window, per the policy's
    :attr:`~privacyidea.models.conditional_access_policy.ConditionalAccessPolicy.count_mode`: distinct targeted accounts
    (``DISTINCT_USERS``, the default and spraying/enumeration signal), individual events (``PER_REQUEST``) or whole
    attempts (``PER_ATTEMPT``, the two volume modes = plain per-IP rate limiting), scoped to what the policy's
    conditions describe (:func:`_count_scoping`). None of the three resets on a successful login - a legit login by
    one account must not clear a signal aggregated across the whole IP - so there is no ``since_last_success``
    parameter, unlike the user path (:func:`_policy_count`).

    :param policy: the policy whose ``time_window_seconds`` and ``counter_types_to_track`` are counted over
    :param source_ip: the client IP to count for
    :param window_end: the instant the window ends (reference time)
    :return: the distinct-account count (``DISTINCT_USERS``), event count (``PER_REQUEST``) or attempt count
        (``PER_ATTEMPT``)
    """
    sql_filters, row_filter = _count_scoping(policy)
    if policy.count_mode == CountMode.PER_REQUEST:
        return count_ip_events(source_ip, policy.counter_types_to_track,
                               policy.time_window_seconds, window_end=window_end,
                               extra_filters=sql_filters)
    if policy.count_mode == CountMode.PER_ATTEMPT:
        return count_ip_attempts(source_ip, policy.counter_types_to_track,
                                 policy.time_window_seconds, window_end=window_end,
                                 row_filter=row_filter)
    return count_distinct_users_for_ip(source_ip, policy.counter_types_to_track,
                                       policy.time_window_seconds, window_end=window_end,
                                       extra_filters=sql_filters)


def get_user_lock(user: "User", now: datetime | None = None, *,
                  clear_expired: bool = False) -> "RestrictionStatus | None":
    """
    Return information about *user*'s **current** lock, or ``None`` if the user
    is not currently locked. Intended for the authentication pre-check hot path.

    By default this is a **pure read**: a stale row whose ``lock_expires_at`` lies
    in the past simply reads as *not locked* and is left in place.

    With *clear_expired* the observed stale row is deleted on the spot. An expired
    timed lock carries no enforced state — it already reads as *not locked* and the
    authentication log is the historical record — so dropping it here, where the
    row is already loaded and known expired, cleans it up on the user's next login
    without a second lookup. The authentication pre-checks opt in; nothing that
    merely inspects a user's status does. Permanent and still-active locks are
    never deleted. The delete is defensive (see :func:`_delete_user_lock_state`).

    A row with ``lock_expires_at IS NULL`` is a permanent lock.

    :param user: the user to check; an unresolved user is never locked
    :param now: the reference time; defaults to :func:`utc_now`
    :param clear_expired: delete the row if it is a stale (timed, expired) lock;
        off by default to keep this a pure read for non-auth callers
    :return: ``None`` if not locked, else a :class:`RestrictionStatus`
    """
    if not _resolved(user):
        return None
    state = get_ca_session().get(UserLockState, (user.resolver, user.uid, user.realm))
    if not state:
        return None
    if state.lock_expires_at is None:
        # Permanent lock; only an admin reset clears it.
        return RestrictionStatus(permanent=True, expires_at=None, seconds_remaining=None,
                                 target=ConditionalAccessTarget.USER, error_message=state.error_message)
    now = _naive_utc(now) if now is not None else utc_now()
    if state.lock_expires_at <= now:
        if clear_expired:
            _delete_user_lock_state(state)
        return None
    remaining = int((state.lock_expires_at - now).total_seconds())
    return RestrictionStatus(permanent=False, expires_at=state.lock_expires_at,
                             seconds_remaining=remaining, target=ConditionalAccessTarget.USER,
                             error_message=state.error_message)


def is_user_locked(user: "User", now: datetime | None = None, *, clear_expired: bool = False) -> bool:
    """
    Return whether *user* is currently locked. Thin boolean wrapper over
    :func:`get_user_lock` for the authentication pre-check hot path; see that
    function for the expiry, permanent-lock, and *clear_expired* semantics.

    :param user: the user to check; an unresolved user is never locked
    :param now: the reference time; defaults to :func:`utc_now`
    :param clear_expired: delete the row if it is a stale (timed, expired) lock
    :return: ``True`` if the user is currently locked
    """
    return get_user_lock(user, now=now, clear_expired=clear_expired) is not None


# Built-in never-block networks: with OVERRIDECLIENT unset, every client appears as the same-host reverse proxy, so
# blocking loopback would turn one BLOCK_IP action into a self-inflicted outage. PI_CONDITIONAL_ACCESS_NEVER_BLOCK
# extends this list with admin-configured proxy, load-balancer, NAT, or management CIDRs.
_DEFAULT_NEVER_BLOCK_NETWORKS = ("127.0.0.0/8", "::1/128")

#: App-config key holding the never-block allowlist, set in pi.cfg or through the
#: PRIVACYIDEA_-prefixed environment variable of the same name. This lives in the
#: server configuration and not in the system config on purpose: it is the safety
#: net that keeps an admin from locking themselves out, so it must not be reachable
#: through the very API an attacker (or a mistaken BLOCK_IP policy) could be attacking.
NEVER_BLOCK_CONFIG_KEY = "PI_CONDITIONAL_ACCESS_NEVER_BLOCK"


def _never_block_networks() -> "list[ipaddress._BaseNetwork]":
    """
    The never-block networks: the built-in loopback defaults plus the CIDRs (or
    bare IPs) configured as ``PI_CONDITIONAL_ACCESS_NEVER_BLOCK`` in the server
    configuration (``pi.cfg`` or the environment).
    The setting is either a list of entries or a single comma/whitespace-separated
    string. A malformed setting is logged and ignored rather than breaking the
    engine: this runs on every authentication, so a typo in the configuration must
    degrade to the loopback defaults, not answer 500 to every request.
    """
    # Lazy import: framework pulls in the app context machinery; importing it at
    # module load would risk an import-order cycle.
    from privacyidea.lib.framework import get_app_config_value
    networks = [ipaddress.ip_network(cidr) for cidr in _DEFAULT_NEVER_BLOCK_NETWORKS]
    configured = get_app_config_value(NEVER_BLOCK_CONFIG_KEY) or []
    if isinstance(configured, str):
        configured = re.split(r"[,\s]+", configured.strip())
    elif not isinstance(configured, (list, tuple, set, frozenset)):
        # Anything else is a pi.cfg mistake. Only these types are accepted rather than
        # "any iterable": an ip_network object, for one, iterates over its 16.7M hosts.
        log.warning(f"Ignoring {NEVER_BLOCK_CONFIG_KEY}: expected a list or a string, "
                    f"got {type(configured).__name__}.")
        configured = []
    for entry in configured:
        entry = str(entry).strip()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            log.warning(f"Ignoring invalid network {entry!r} in {NEVER_BLOCK_CONFIG_KEY}.")
    return networks


def is_ip_never_block(source_ip: str | None) -> bool:
    """
    Return whether *source_ip* must never be blocked by the conditional-access
    engine: it is loopback (built-in) or matches the ``PI_CONDITIONAL_ACCESS_NEVER_BLOCK``
    allowlist from the server configuration. A falsy or unparsable IP is treated as never-block as
    well — fail safe: never block an address the engine cannot positively identify.
    """
    if not source_ip:
        return True
    try:
        ip = ipaddress.ip_address(source_ip)
    except ValueError:
        log.warning(f"Could not parse source IP {source_ip!r}; treating it as never-block.")
        return True
    return any(ip in network for network in _never_block_networks())


def get_ip_block(source_ip: str | None, now: datetime | None = None, *,
                 clear_expired: bool = False) -> "RestrictionStatus | None":
    """
    Return information about *source_ip*'s **current** block by the ``BLOCK_IP``
    action, or ``None`` if the IP is not currently blocked. This is the IP
    counterpart of :func:`get_user_lock` and is meant for the authentication
    pre-check hot path.

    By default this is a **pure read**: a row that is not enforced — its
    ``block_expires_at`` lies in the past, or the IP is on the never-block
    allowlist — simply reads as *not blocked* and is left in place.

    With *clear_expired* the observed stale row is deleted on the spot, an expired
    timed block carries no enforced state (the authentication log is the record),
    so dropping it here — where the row is already loaded and known expired — cleans
    it up the next time that IP is seen, without a second lookup. The authentication
    pre-checks opt in. Permanent and still-active blocks are never deleted. The delete
    is defensive (see :func:`_delete_ip_block`). A row with ``block_expires_at IS NULL`` is a
    permanent block.

    The remaining time is surfaced so the WebUI login (``/auth``) can tell the
    user how long the block lasts, just like the user lock (maskable via the
    ``hide_specific_error_message`` policy); the machine-facing ``/validate``
    endpoints keep the generic failure response.

    :param source_ip: the client IP to check; a falsy value is never blocked
    :param now: the reference time; defaults to :func:`utc_now`
    :param clear_expired: delete the row if it no longer restricts anything - a stale
        (timed, expired) block, or any block on a never-block IP; off by default to keep
        this a pure read for non-auth callers
    :return: ``None`` if not blocked, else a :class:`RestrictionStatus`
    """
    if not source_ip:
        return None
    state = get_ca_session().get(BlockList, source_ip)
    if not state:
        return None
    # A block row exists, but the never-block allowlist is honored here too, so adding an IP to it immediately stops
    # enforcing any stale or mistaken block on that IP. With clear_expired the row itself is dropped here — the
    # allowlist can never be outvoted, so the record is dead weight and the auth pre-check is the one caller that
    # reliably sees the IP again.
    if is_ip_never_block(source_ip):
        if clear_expired:
            log.info(f"Removing the block for IP {source_ip!r}: it is on the never-block allowlist.")
            _delete_ip_block(state)
        return None
    if state.block_expires_at is None:
        # Permanent block; only an admin reset clears it.
        return RestrictionStatus(permanent=True, expires_at=None, seconds_remaining=None,
                                 target=ConditionalAccessTarget.SOURCE_IP, error_message=state.error_message)
    now = _naive_utc(now) if now is not None else utc_now()
    if state.block_expires_at <= now:
        if clear_expired:
            _delete_ip_block(state)
        return None
    remaining = int((state.block_expires_at - now).total_seconds())
    return RestrictionStatus(permanent=False, expires_at=state.block_expires_at,
                             seconds_remaining=remaining, target=ConditionalAccessTarget.SOURCE_IP,
                             error_message=state.error_message)


def is_ip_blocked(source_ip: str | None, now: datetime | None = None, *, clear_expired: bool = False) -> bool:
    """
    Return whether *source_ip* is currently blocked by the ``BLOCK_IP`` action.
    Thin boolean wrapper over :func:`get_ip_block` for the authentication
    pre-check hot path; see that function for the expiry, permanent-block, and
    *clear_expired* semantics.

    :param source_ip: the client IP to check; a falsy value is never blocked
    :param now: the reference time; defaults to :func:`utc_now`
    :param clear_expired: delete the row if it is a stale (timed, expired) block or a
        block on a never-block IP
    :return: ``True`` if the IP is currently blocked
    """
    return get_ip_block(source_ip, now=now, clear_expired=clear_expired) is not None


def evaluate_access_decision(context: CAContext, now: datetime | None = None) -> "AccessDecisionResult":
    """
    Pre-auth conditional-access decision for the current request: should it be
    denied, or left to the normal flow?

    This runs **before** the credential check, and after the persistent
    :func:`is_user_locked` / :func:`is_ip_blocked` pre-checks. It handles only the
    :attr:`ConditionalAccessAction.DENY` action; the lock/email/block actions are
    post-response side effects handled by :func:`evaluate_conditional_access_policies`.

    Because there is no event for the current request yet, the decision is keyed
    on the user's **prior** event history: for each enabled policy the events of
    its ``counter_types_to_track`` are counted (combined across all tracked
    types) over its window, and the matching stage with the highest threshold
    supplies the decision. A ``DENY`` action therefore rejects this single request
    without persisting any state — a stateless, self-healing reject that lifts on
    its own as the failures age out of the window (contrast the durable
    :attr:`ConditionalAccessAction.LOCK_USER`). With the policy's
    ``reset_on_success`` the count is floored at the user's last completed
    login, so a ``DENY`` also lifts on a successful authentication and not only
    with the passage of time. Because ``DENY`` defaults to re-triggering
    (``count >= threshold``), a stage with ``failure_threshold`` 0 always matches,
    which is the lockdown idiom - scope it with conditions.

    Policies are evaluated by ascending ``priority`` (a lower number means higher
    precedence, matching privacyIDEA's policy engine) and the first one that denies
    wins, which is what decides *which* policy is named as having refused the
    request. ``dry_run`` policies are logged but never enforced.

    A subject is exempted by an applicability condition on this policy
    (``USER_REALM NOT_IN [...]``, ``USER_ROLE NOT_IN [...]``): a policy whose
    conditions do not match is never evaluated for that request.

    Both targets can deny here: a ``user`` policy is keyed on the resolved
    ``(resolver, uid, realm)`` user (an unresolved user - unknown login, local
    admin - is never decided by a user policy), while a ``source_ip`` policy is
    keyed on the context's source IP and therefore applies even when the user is
    unresolved (the spraying/enumeration case). A never-block source IP is exempt
    from an IP ``DENY``, mirroring the ``BLOCK_IP`` allowlist.

    :param context: what is known about the request under evaluation (see
        :class:`~privacyidea.lib.conditional_access.context.CAContext`); a
        ``user`` policy needs its user resolved, a ``source_ip`` policy its
        source IP
    :param now: the reference time; defaults to :func:`utc_now`
    :return: the :class:`AccessDecisionResult` for this request: the decision, plus the outcomes to record on
        whichever authentication-log row this request ends up writing
    """
    now = _naive_utc(now) if now is not None else utc_now()
    policies = get_ca_session().scalars(
        select(ConditionalAccessPolicy)
        .options(selectinload(ConditionalAccessPolicy.conditions))
        .where(ConditionalAccessPolicy.enabled.is_(True))
        .order_by(ConditionalAccessPolicy.priority.asc())
    ).all()
    outcomes: list[ConditionalAccessOutcome] = []
    for policy in policies:
        contribution = _policy_access_decision(policy, context, now)
        outcomes.extend(contribution.outcomes)
        if contribution.decision != AccessDecision.CONTINUE:
            # The first policy that decides wins, so no lower-priority policy is even consulted - and the outcomes
            # collected so far are exactly those of the policies that had something to say.
            return AccessDecisionResult(contribution.decision, outcomes, contribution.error_message)
    return AccessDecisionResult(outcomes=outcomes)


def _policy_access_decision(policy: ConditionalAccessPolicy, context: CAContext,
                            now: datetime) -> "AccessDecisionResult":
    """
    What a single policy contributes to the pre-auth decision: whether it denies the request, and the outcome to
    record for it.

    The decision is :attr:`AccessDecision.CONTINUE` when this policy does not deny the request: wrong or absent
    subject, no ``DENY`` action's threshold condition is met, or the policy is in dry run - a dry-run policy is never
    enforced, but it still yields its outcome, which is how an admin measures what enforcing it would do.

    Each ``DENY`` action decides for itself via :func:`_action_threshold_met`: it
    defaults to re-triggering (``count >= threshold``, so the refusal stands while
    the failures are high), which is what makes it a self-healing reject. An admin
    can switch it to fire-once, in which case it only refuses the request at the
    exact threshold count. The stage with the highest threshold whose ``DENY``
    action is met supplies the decision.
    """
    # Applicability is checked first: a policy whose conditions exclude this request contributes no decision and
    # costs no counting query.
    if not policy_matches_context(policy, context):
        return AccessDecisionResult()
    # Counts here are scoped to the policy's conditions via _count_scoping, exactly like the post-response path.
    # Both paths must count the same subject over the same window, or a policy could deny based on one history and
    # act on another.
    if policy.target == ConditionalAccessTarget.SOURCE_IP:
        # IP-scoped: decides on the source IP regardless of user resolution; a never-block IP is never denied here
        # either, mirroring the BLOCK_IP allowlist.
        if not context.source_ip or is_ip_never_block(context.source_ip):
            return AccessDecisionResult()
        count = _policy_count_ip(policy, context.source_ip, now)
        subject_label = f"source IP {context.source_ip}"
    else:
        # User-scoped: keyed on the resolved user, so an unresolved user is never decided by a user policy. The
        # count honours the policy's reset_on_success, exactly as the post-response path does.
        if not _resolved(context.user):
            return AccessDecisionResult()
        count = _policy_count(policy, context.user, now, since_last_success=policy.reset_on_success)
        subject_label = repr(context.user)
    deciding_stage = next((stage for stage in policy.stages if _stage_denies(stage, count)), None)
    if deciding_stage is None:
        return AccessDecisionResult()
    decision = AccessDecision.DENY
    types = _types_label(policy.counter_types_to_track)
    outcomes = [outcome_for_stage(policy, deciding_stage, ConditionalAccessAction.DENY, count, dry_run=policy.dry_run)]
    # A denial is the only decision left and it is what turns the request away, so the wording it carries is
    # always this stage's.
    error_message = deciding_stage.error_message
    if policy.dry_run:
        # A dry-run policy never decides the request, but the pre-auth decision runs before the log row exists, so
        # the caller buffers this outcome and records it once that row is written (see ConditionalAccessContext.stage).
        log.info(f"[dry-run] policy {policy.name!r} would return {decision} for {subject_label}: "
                 f"{count} event(s) of {types} in {policy.time_window_seconds}s.")
        return AccessDecisionResult(outcomes=outcomes)
    log.info(f"Policy {policy.name!r} returns access decision {decision} for {subject_label}: "
             f"{count} event(s) of {types} in {policy.time_window_seconds}s.")
    return AccessDecisionResult(decision, outcomes, error_message)


def _stage_denies(stage: ConditionalAccessPolicyStage, count: int) -> bool:
    """
    Whether *stage* refuses the request at *count*: it carries a ``DENY`` action
    whose per-action threshold condition is met. An unparsable action type is
    skipped rather than treated as a refusal.
    """
    for action in stage.actions:
        try:
            action_type = ConditionalAccessAction(action.action_type)
        except ValueError:
            continue
        if action_type != ConditionalAccessAction.DENY:
            continue
        if _action_threshold_met(action, stage.failure_threshold, count):
            return True
    return False


def _restrictions_in_force(context: CAContext, targets: set[ConditionalAccessTarget]) -> list[StageMessage]:
    """
    The error message of the restrictions in force on the targets an evaluation restricted, one message per row.

    Read back rather than rendered by the stage that aimed at it. Several policies can restrict the same subject
    in one request and a stage can carry several restricting actions, but only one row survives them all - so the
    stage that wrote the weaker restriction would otherwise describe a lock that is not in force, and two
    policies locking the same user would tell the user twice. Reading the row also means ``{duration}`` counts
    down the expiry that actually stands, whatever the upserts decided to keep, and that a write declined as
    weakening still leaves the user told about the restriction that stands instead of about nothing.

    Silent by default holds here as everywhere: a row carrying no error message produces none. A target whose
    write failed outright is not passed here at all - it restricted nothing, so there is no row to describe and no
    request to refuse (see :func:`_execute_stage_actions`).

    :param targets: the targets this evaluation restricted, so an untouched row is never read
    """
    statuses = []
    if ConditionalAccessTarget.USER in targets and context.user is not None:
        statuses.append(get_user_lock(context.user))
    if ConditionalAccessTarget.SOURCE_IP in targets and context.source_ip:
        statuses.append(get_ip_block(context.source_ip))
    return restriction_messages(*statuses, use_default_error_message=context.use_default_error_message)


def evaluate_conditional_access_policies(context: CAContext, event_type: AuthEventType | None,
                                         now: datetime | None = None) -> "ConditionalAccessEvaluation":
    """
    Evaluate every enabled conditional-access policy that tracks *event_type* and execute
    the actions of the triggered stage, if any. This runs post-response, *after*
    the request's ``authentication_log`` row has been written (so the count
    includes it).

    Each action decides for itself whether it fires. By default an action fires
    once, when the failure count reaches its stage's threshold exactly: an action
    at threshold 8 runs on the 8th failure and not again on the 9th. An action with
    ``retrigger_above_threshold`` fires whenever the count is at or above the
    threshold, so a single stage can email once at threshold 8 while keeping the
    user locked for every further failure (see :func:`_action_threshold_met`). The
    count climbs by one per tracked failure and, for a policy with
    ``reset_on_success``, resets after a successful login (see
    :func:`count_user_events`), so a fresh burst re-triggers the fire-once
    actions too.

    The persistent side effects (lock state) are consulted by the *next* inbound
    request via the pre-check, which reads the error message back off the row they wrote. A stage that only
    notified leaves no such row, so its message is returned here instead, for the caller to surface on
    the response this evaluation belongs to. Any error is the caller's to swallow; this
    function itself only guards individual DB writes (see
    :func:`_upsert_user_lock_state`).

    Alongside the messages, every action that actually ran (or, in dry run, would have run) is returned as a
    :class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome` for the caller to record as this
    request's history.
    The engine deliberately does not write them: it never sees the id of the authentication-log row they belong to.

    :param context: what is known about the request under evaluation (see
        :class:`~privacyidea.lib.conditional_access.context.CAContext`);
        ``user``-target policies need its user resolved, ``source_ip``-target
        policies act on its source IP regardless, and the ``BLOCK_IP`` action
        blocks that IP
    :param event_type: the classified outcome of the request
        (:class:`AuthEventType`)
    :param now: the reference time; defaults to :func:`utc_now`
    :return: a :class:`ConditionalAccessEvaluation` holding the de-duplicated, order-preserving user-facing
        messages produced by executed actions, and the outcomes to record (both empty if nothing was triggered)
    """
    if not event_type:
        return ConditionalAccessEvaluation()
    now = _naive_utc(now) if now is not None else utc_now()
    event_type = str(event_type)
    # Selects only enabled policies tracking the current event type via an indexed equality filter on the normalized
    # conditional_access_policy_counter_types table; (policy_id, counter_type) is unique, so a policy matches at most
    # once. _evaluate_policy then computes the combined count over all of a matched policy's tracked types.
    policies = get_ca_session().scalars(
        select(ConditionalAccessPolicy)
        .options(selectinload(ConditionalAccessPolicy.conditions))
        .join(ConditionalAccessPolicy.counter_types)
        .where(ConditionalAccessPolicy.enabled.is_(True),
               ConditionalAccessPolicyCounterType.counter_type == event_type)
        .order_by(ConditionalAccessPolicy.priority.asc())
    ).all()
    messages: list[StageMessage] = []
    outcomes: list[ConditionalAccessOutcome] = []
    enforced: set[ConditionalAccessTarget] = set()
    for policy in policies:
        # Each policy is evaluated inside its own guard, so a broken policy cannot disable every policy ordered
        # behind it. The only unguarded step is the policy query above, which runs before any action, so a retry
        # always starts clean.
        try:
            evaluation = _evaluate_policy(policy, context, event_type, now)
        except Exception as ex:
            log.warning(f"Conditional-access policy {policy.name!r} failed to evaluate: {ex!r}; skipping it.")
            continue
        messages.extend(evaluation.messages)
        outcomes.extend(evaluation.outcomes)
        enforced |= evaluation.enforced_targets
    # Every restriction is described once, from the row left in force, ahead of the notifications the stages
    # carry: two policies locking the same user leave one lock, and so must say so once.
    messages = _restrictions_in_force(context, enforced) + messages
    # Ranked and de-duplicated by rank_and_deduplicate, which is stable, so messages of equal severity stay in
    # policy-priority order. The outcomes are *not* de-duplicated - each is a distinct thing that happened, and
    # two policies locking the same user are two facts worth keeping apart.
    #
    # enforced_targets is carried out of here, not just used above: it is the only thing that says this request was
    # restricted at all, and a *silent* restriction produces no message to infer it from. The caller needs it to
    # answer such a request as the rejection it now is.
    return ConditionalAccessEvaluation(messages=rank_and_deduplicate(messages), outcomes=outcomes,
                                       enforced_targets=enforced)


def _action_threshold_met(action: ConditionalAccessStageAction, threshold: int, count: int) -> bool:
    """
    Whether *action* fires at the given failure *count*, for its stage's
    *threshold*.

    Default (``retrigger_above_threshold`` unset): the action fires only when the
    count equals the threshold exactly, so it triggers once as the count climbs
    past it. With ``retrigger_above_threshold`` the action fires whenever the count
    is at or above the threshold (the classic re-triggering lock). The flag is
    per action, so one stage can e.g. email once at its threshold while keeping the
    user locked as long as the count stays at or above it.
    """
    if action.retrigger_above_threshold:
        return count >= threshold
    return count == threshold


def _stage_pending_actions(stage: ConditionalAccessPolicyStage, count: int) -> list[ConditionalAccessStageAction]:
    """The actions of *stage* whose per-action condition is met at *count*."""
    return [action for action in stage.actions
            if _action_threshold_met(action, stage.failure_threshold, count)]


def _evaluate_policy(policy: ConditionalAccessPolicy, context: CAContext, event_type: str,
                     now: datetime) -> "ConditionalAccessEvaluation":
    """
    Evaluate a single policy: count the user's events over the policy window,
    find the triggered stage, then execute the stage's *pending* actions (or, in
    dry-run, only log what they would have done).

    Each action decides for itself whether it fires (see
    :func:`_action_threshold_met`): by default an action triggers once, when the
    count equals the stage's ``failure_threshold``; an action with
    ``retrigger_above_threshold`` fires whenever the count is at or above the
    threshold. So one stage can, for example, email once at threshold 8 while
    keeping the user locked for every further failure at 8 or more.

    :return: a :class:`ConditionalAccessEvaluation` with the user-facing messages produced by the executed actions
        and the outcomes describing what was done (both empty if no stage triggered; in dry run there are outcomes
        but no messages, since nothing ran)
    """
    # Applicability is checked first: a policy whose conditions exclude this request neither counts nor acts, and
    # costs no counting query.
    if not policy_matches_context(policy, context):
        return ConditionalAccessEvaluation()
    # A policy's conditions scope what is counted, not just whether it applies (see _count_scoping); matches_missing
    # and the SQL filter treat a missing value the same way, so the gate and the count never disagree.
    # This matters for a source-IP policy, whose rows span many identities and roles and would otherwise count the
    # whole IP's history; for a user policy the filters add little, since the subject already pins one identity's
    # realm and role.
    # A policy whose conditions cannot all be expressed as predicates counts unscoped.
    window = policy.time_window_seconds
    user = context.user
    source_ip = context.source_ip
    if policy.target == ConditionalAccessTarget.SOURCE_IP:
        if not source_ip:
            # An IP-targeted policy cannot count or act without a source IP.
            log.debug(f"Skipping source-IP policy {policy.name!r}: the request carries no source IP.")
            return ConditionalAccessEvaluation()
        # Counts per the policy's mode: distinct targeted accounts (spraying) or plain per-IP volume; no mode resets
        # on success, since one account's login must not clear a signal aggregated across the whole IP (see
        # _policy_count_ip).
        count = _policy_count_ip(policy, source_ip, now)
        subject_label = f"source IP {source_ip}"
    else:
        if not _resolved(user):
            # A user-target policy is keyed on the resolved (resolver, uid, realm)
            # user, so an unresolved user (unknown login, local admin) is never
            # locked. Source-IP policies above still run for such requests.
            return ConditionalAccessEvaluation()
        # With the policy's reset_on_success (the default) the lock counts consecutive
        # failures since the user's last completed login: a successful authentication
        # clears the slate, so a legitimate user is not re-locked by stale pre-login
        # failures on their next single typo. Without it every tracked event in the raw
        # window counts, which is what an admin wants when the threshold is meant to
        # measure total failures rather than a run of them. The pre-auth DENY decision
        # counts the same way (see _policy_access_decision).
        # The count is the *combined* total over all of the policy's tracked types,
        # not just the current request's event_type, so a policy tracking several
        # failure types trips on their sum.
        count = _policy_count(policy, user, now, since_last_success=policy.reset_on_success)
        subject_label = repr(user)

    # Picks the triggered stage: the highest-threshold stage with at least one action whose per-action condition is
    # met (see _action_threshold_met).
    # By default an action fires once, exactly at the threshold (a threshold-8 email sends on the 8th failure, not
    # again at 9); retrigger_above_threshold keeps it firing while the count stays at or above the threshold.
    # Stages are ordered by descending threshold, so the most severe stage with a pending action wins and only that
    # stage's actions run (one stage per policy per request); contrast the pre-auth DENY decision in
    # _policy_access_decision.
    triggered_stage = next((stage for stage in policy.stages
                            if _stage_pending_actions(stage, count)), None)
    if triggered_stage is None:
        return ConditionalAccessEvaluation()
    pending_actions = _stage_pending_actions(triggered_stage, count)

    if policy.dry_run:
        log.info(f"[dry-run] policy {policy.name!r} would trigger stage {triggered_stage.id} "
                 f"(threshold {triggered_stage.failure_threshold}) for {subject_label}: "
                 f"{count} event(s) of {_types_label(policy.counter_types_to_track)} in {window}s.")
        # One outcome is recorded per action that would have run, carrying the expiry it would have written, so the
        # history shows what enforcing this policy would have done (a misconfigured LOCK_USER/BLOCK_IP duration
        # surfaces as a missing expiry).
        # DENY is excluded here since it is already recorded pre-auth by _policy_access_decision; recording it
        # again would double-count the same decision.
        outcomes = [outcome_for_stage(policy, triggered_stage, action.action_type, count, dry_run=True,
                                      expires_at=_action_expiry(action, now))
                    for action in pending_actions
                    if action.action_type != ConditionalAccessAction.DENY]
        return ConditionalAccessEvaluation(outcomes=outcomes)

    log.info(f"Policy {policy.name!r} triggered stage {triggered_stage.id} "
             f"(threshold {triggered_stage.failure_threshold}) for {subject_label}: "
             f"{count} event(s) of {_types_label(policy.counter_types_to_track)} in {window}s.")
    tags = _base_action_tags(policy, triggered_stage, context, event_type, count, now)
    return _execute_stage_actions(policy, triggered_stage, pending_actions, context, now, count, tags)


def _action_expiry(stage_action: ConditionalAccessStageAction, now: datetime) -> datetime | None:
    """
    When the restriction written by *stage_action* ends, or ``None`` when there is nothing to expire.

    ``None`` covers three different cases, which the action type tells apart: a ``PERMANENT_*`` action (never expires),
    an action that creates no restriction at all (``EMAIL_*``, ``DENY``), and a timed action whose configured
    duration is missing or invalid - which is a misconfiguration the enforced path skips and logs, and which a dry-run
    outcome surfaces as "would have locked, but for how long is not configured".
    """
    if stage_action.action_type not in (ConditionalAccessAction.LOCK_USER, ConditionalAccessAction.BLOCK_IP):
        return None
    duration = _lock_duration_seconds(stage_action.action_value)
    return now + timedelta(seconds=duration) if duration is not None else None


def _lock_duration_seconds(action_value: Any) -> int | None:
    """
    Parse the ``LOCK_USER`` lock duration (in seconds) from a stage action's
    JSON ``action_value``. Accepts a plain integer, a numeric string, or a dict
    carrying ``duration_seconds`` / ``duration``. Returns ``None`` for anything
    that is not a positive integer number of seconds.
    """
    if isinstance(action_value, bool):
        # bool is an int subclass; a boolean is never a valid duration.
        return None
    if isinstance(action_value, dict):
        action_value = action_value.get("duration_seconds", action_value.get("duration"))
    try:
        seconds = int(action_value)
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


class _SafeFormatDict(dict):
    """A ``str.format_map`` mapping that leaves unknown ``{placeholders}`` as-is
    instead of raising ``KeyError``, so an admin's typo in a template never turns
    a notification into an exception."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _safe_format(template: str, tags: dict) -> str:
    """
    Substitute ``{tag}`` placeholders in *template* from *tags*. Unknown
    placeholders are left untouched and malformed templates are returned verbatim
    — rendering an admin-supplied string must never raise.
    """
    try:
        return template.format_map(_SafeFormatDict(tags))
    except Exception:
        return template


def _base_action_tags(policy: ConditionalAccessPolicy, stage: ConditionalAccessPolicyStage, context: CAContext,
                      event_type: str, count: int, now: datetime) -> dict:
    """
    Build the ``{tag}`` substitution context available to EMAIL_* templates. Only
    fields already loaded on the request are included here; the resolver-backed
    user attributes (email, givenname, surname) are added lazily in
    :func:`_send_action_email`, so a non-email action never triggers a resolver
    lookup.

    There is exactly one canonical name per value — no aliases — so a template
    references each value unambiguously. The names match privacyIDEA's existing
    notification vocabulary (:func:`~privacyidea.lib.utils.create_tag_dict`): the
    login is ``{username}`` and the request IP is ``{client_ip}``. (Showing the
    available tags in the policy editor and rejecting unknown ``{tags}`` when a
    template is saved belong to the policy CRUD/editor layer, not here.)
    """
    user = context.user
    return {
        "username": user.login if user else "",
        "realm": (user.realm if user else "") or "",
        "resolver": (user.resolver if user else "") or "",
        "client_ip": context.source_ip or "",
        "count": count,
        "threshold": stage.failure_threshold,
        "event_type": event_type,
        "stage_id": stage.id,
        "policy": policy.name,
        "time": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def _resolve_admin_recipients(recipient_group: str | None) -> list[str]:
    """
    Resolve the EMAIL_ADMIN ``recipient_group`` to a list of email addresses.

    Supported values:

    * ``None`` / ``"internal_admins"`` / ``"admins"`` / ``"all"`` — every
      internal DB admin (the ``admin`` table) that has an email address set
    * any value containing ``"@"`` — treated as an explicit comma-separated list
      of email addresses

    An unknown group yields an empty list (the caller logs and skips).
    """
    group = (str(recipient_group).strip() if recipient_group else "internal_admins")
    if "@" in group:
        return [addr.strip() for addr in group.split(",") if addr.strip()]
    if group.lower() in ("internal_admins", "admins", "all"):
        # Imported lazily to keep the engine's hot path free of lib.auth's heavy token/container imports and avoid
        # import-time coupling.
        from privacyidea.lib.auth import get_all_db_admins
        return [admin.email for admin in get_all_db_admins() if admin.email]
    log.warning(f"Unknown EMAIL_ADMIN recipient_group {recipient_group!r}; "
                f"expected 'internal_admins' or a comma-separated email list.")
    return []


def _send_action_email(action_type: "ConditionalAccessAction", stage_action: ConditionalAccessStageAction,
                       user: "User | None", tags: dict) -> bool:
    """
    Send the EMAIL_ADMIN / EMAIL_USER notification for a triggered stage action.

    The stage action's ``action_value`` is a JSON object carrying
    ``smtp_identifier`` (the SMTP server configuration to use), ``subject`` and
    ``body`` (both rendered with ``{tag}`` substitution), an optional ``mimetype``
    (``plain``/``html``) and, for EMAIL_ADMIN, an optional ``recipient_group``.
    EMAIL_USER sends to the user's own email address. A missing field or a user
    without an email address is logged and skipped; this runs post-response and
    must never raise.

    *user* is ``None`` when the request carried no user to resolve - the normal case for a source-IP
    policy firing on spraying or enumeration traffic, which is exactly the traffic an EMAIL_ADMIN
    alert exists to report. The user-derived tags then render empty (as they already do in
    :func:`_base_action_tags`) and EMAIL_USER finds no recipient and skips, but the admin alert is
    still sent.

    Anything the user is told about it comes from the stage's own ``error_message``, so this reports
    only whether the mail went out.

    :return: whether the email was sent; ``False`` for a misconfiguration, no recipient, or a delivery
        failure.
    """
    email_config = stage_action.action_value if isinstance(stage_action.action_value, dict) else {}
    identifier = email_config.get("smtp_identifier") or email_config.get("identifier")
    subject, body = email_config.get("subject"), email_config.get("body")
    if not identifier or not subject or not body:
        log.warning(f"{action_type} action {stage_action.id}: needs smtp_identifier, subject and body in "
                    f"action_value; skipping.")
        return False

    # Resolver-backed attributes are fetched once, only now that an email is sent.
    info = (user.info if user else None) or {}
    render_tags = {**tags, "email": info.get("email") or "",
                   "givenname": info.get("givenname") or "", "surname": info.get("surname") or ""}

    if action_type == ConditionalAccessAction.EMAIL_USER:
        recipients = [info["email"]] if info.get("email") else []
        if not recipients:
            log.warning(f"EMAIL_USER action {stage_action.id}: user {user!r} has no email address; skipping.")
            return False
    else:  # EMAIL_ADMIN
        recipients = _resolve_admin_recipients(email_config.get("recipient_group"))
        if not recipients:
            log.warning(f"EMAIL_ADMIN action {stage_action.id}: no recipients for "
                        f"recipient_group={email_config.get('recipient_group')!r}; skipping.")
            return False

    from privacyidea.lib.smtpserver import send_email_identifier
    sent = send_email_identifier(identifier, recipients,
                                 _safe_format(str(subject), render_tags),
                                 _safe_format(str(body), render_tags),
                                 mimetype=email_config.get("mimetype", "plain"))
    if sent:
        log.info(f"{action_type} for {user!r} sent to {len(recipients)} recipient(s) via {identifier!r}.")
        return True
    log.warning(f"{action_type} for {user!r} could not be delivered via {identifier!r}.")
    return False


def _execute_stage_actions(policy: ConditionalAccessPolicy, stage: ConditionalAccessPolicyStage,
                           actions: Sequence[ConditionalAccessStageAction], context: CAContext,
                           now: datetime, count: int, tags: dict) -> "ConditionalAccessEvaluation":
    """
    Execute the given *actions* of a triggered *stage* (the stage's pending
    actions, i.e. those whose per-action threshold condition is met). Each action
    is guarded independently: an unknown type, a misconfiguration, or a failing
    side effect (e.g. an unreachable mail server) is logged and skipped so it can
    never break the authentication flow or prevent the other actions from running.

    An outcome is recorded **only for an action that actually did something**, which is why this is the function that
    produces them: it is the one place that knows whether the lock was written, whether the mail went out, and which
    expiry ended up in the state row. A skipped action - unknown type, no valid duration, no recipient, a never-block
    IP, an undeliverable mail, a permanent lock that must not be downgraded - is logged and left out of the history, so
    every stored outcome is a thing that happened rather than a thing that was configured.

    The never-block allowlist is checked per action, in :func:`_upsert_ip_block`, not for the stage as a whole: a
    ``BLOCK_IP`` against an exempt address is skipped and not recorded, while an ``EMAIL_ADMIN`` on the same stage
    still runs and is still recorded. The stage tripped; only the block is withheld.

    :param policy: the triggering policy, for the outcomes
    :param count: the count that tripped the stage, for the outcomes
    :return: a :class:`ConditionalAccessEvaluation` with this stage's message when it only notified, one outcome
        per action that ran, and the targets those actions restricted (all empty if every action was skipped).
    """
    outcomes: list[ConditionalAccessOutcome] = []
    # Which rows this stage left a restriction on - noted for an action that actually restricted one, not for one
    # that was configured to. The caller answers a request as a rejection on the strength of this set, so an action
    # whose write never happened - no valid duration, no source IP, a failed write - must not put a target here
    # that no later request would be refused by.
    #
    # A write *declined as weakening* wrote nothing either, and the row it declined to weaken is still described:
    # only a stronger restriction in force declines one, and that one was written either by an earlier action here
    # or by another policy in this same evaluation - which recorded the target. (It cannot have been in force
    # beforehand: the pre-check would have refused the request, and a rejection is never evaluated.) The union
    # evaluate_conditional_access_policies collects therefore holds it, and the message comes from whatever stands
    # on that row - never from the action that aimed at it.
    enforced: set[ConditionalAccessTarget] = set()
    # Whether the stage *aimed* at a restriction or a denial, which is a different question from what it achieved
    # and is why these two are not read off `enforced`. The stage's one error message describes whatever the stage
    # does; for those two the description belongs elsewhere - the row in force, or the pre-auth decision step - so
    # the stage says nothing from here either way. A write that was declined or skipped leaves nothing to describe,
    # not a lock-shaped sentence to append to the failure as though it were a notification.
    restricts = False
    decides = False

    user = context.user
    source_ip = context.source_ip

    def record(action_type: str, expires_at: datetime | None = None) -> None:
        """Note that *action_type* ran, with the expiry it wrote (if any), and what it restricted."""
        outcomes.append(outcome_for_stage(policy, stage, action_type, count, expires_at=expires_at))
        target = RESTRICTED_TARGET_BY_ACTION.get(action_type)
        if target is not None:
            enforced.add(target)

    for action in actions:
        try:
            action_type = ConditionalAccessAction(action.action_type)
        except ValueError:
            log.warning(f"Unknown conditional-access action type {action.action_type!r} on stage {stage.id}; skipping.")
            continue
        restricts = restricts or action_type in RESTRICTED_TARGET_BY_ACTION
        decides = decides or action_type is ConditionalAccessAction.DENY

        try:
            if action_type == ConditionalAccessAction.LOCK_USER:
                duration = _lock_duration_seconds(action.action_value)
                if duration is None:
                    log.warning(f"LOCK_USER action {action.id} on stage {stage.id} has no valid duration "
                                f"({action.action_value!r}); skipping.")
                    continue
                lock_expires_at = now + timedelta(seconds=duration)
                if _upsert_user_lock_state(user, lock_expires_at=lock_expires_at,
                                           error_message=stage.error_message, policy_name=policy.name):
                    record(action_type, expires_at=lock_expires_at)
            elif action_type == ConditionalAccessAction.PERMANENT_LOCK_USER:
                if _upsert_user_lock_state(user, lock_expires_at=None,
                                           error_message=stage.error_message, policy_name=policy.name):
                    record(action_type)
            elif action_type in (ConditionalAccessAction.EMAIL_ADMIN, ConditionalAccessAction.EMAIL_USER):
                if _send_action_email(action_type, action, user, tags):
                    record(action_type)
            elif action_type in (ConditionalAccessAction.BLOCK_IP, ConditionalAccessAction.PERMANENT_BLOCK_IP):
                # BLOCK_IP on a per-user policy blocks only the source IP of the request that tripped it; it is not
                # a password-spraying detector (failures from one IP across many users).
                if not source_ip:
                    log.warning(f"{action_type} action {action.id} on stage {stage.id}: this request "
                                f"has no source IP; skipping.")
                    continue
                if action_type == ConditionalAccessAction.PERMANENT_BLOCK_IP:
                    # Permanent block; action_value is ignored (mirrors PERMANENT_LOCK_USER).
                    block_expires_at = None
                else:
                    duration = _lock_duration_seconds(action.action_value)
                    if duration is None:
                        log.warning(f"BLOCK_IP action {action.id} on stage {stage.id} has no valid duration "
                                    f"({action.action_value!r}); skipping.")
                        continue
                    block_expires_at = now + timedelta(seconds=duration)
                if _upsert_ip_block(source_ip, block_expires_at=block_expires_at,
                                    error_message=stage.error_message, policy_name=policy.name):
                    record(action_type, expires_at=block_expires_at)
            elif action_type == ConditionalAccessAction.DENY:
                # DENY decides the current request pre-auth (see evaluate_access_decision), so there is nothing to
                # do or record here — the decision is already recorded as its own outcome in
                # _policy_access_decision.
                log.debug(f"{action_type} is a pre-auth access decision; skipping in the "
                          f"post-response engine.")
            else:
                log.info(f"Conditional-access action {action_type} is recognized but not implemented yet; skipping.")
        except Exception as ex:
            log.warning(f"Conditional-access action {action_type} (id {action.id}) on stage {stage.id} "
                        f"failed: {ex!r}; skipping.")
    if not outcomes:
        # Nothing ran, so there is nothing to report - whatever the stage was configured to say.
        rendered = None
    elif stage.error_message:
        # One free-text field for whatever the stage does, so it is rendered wherever that thing is described: a
        # restriction from the row it left behind (_restrictions_in_force), a denial by the pre-auth decision step
        # that makes it. Either way, repeating it here would tell the user twice - or tell them about a denial
        # that did not turn this request away.
        rendered = None if restricts or decides else render_error_message(stage.error_message)
    elif context.use_default_error_message:
        # The default error message is per action rather than per stage, so nothing is described twice and no
        # such rule is needed: compose_default_error_message carries only what reports something, and leaves any
        # restriction to its row. That is what lets a stage that locks *and* emails describe both.
        # Deferred for the same reason as in restriction_messages: policy imports this module.
        from privacyidea.lib.conditional_access.policy import compose_default_error_message
        rendered = render_error_message(
            compose_default_error_message([outcome.action_type for outcome in outcomes]))
    else:
        rendered = None
    # Ranked by the most severe thing the stage actually did, so a caller showing several messages leads with that.
    action = most_severe_action(outcome.action_type for outcome in outcomes)
    messages = [StageMessage(rendered, action)] if rendered and action else []
    return ConditionalAccessEvaluation(messages=messages, outcomes=outcomes, enforced_targets=enforced)


def _delete_user_lock_state(state: UserLockState) -> None:
    """
    Delete a stale :class:`UserLockState` row.

    Used by :func:`get_user_lock` to drop a timed lock the auth pre-check finds
    already expired: the row is no longer enforced and the authentication log is
    the record, so it carries nothing worth keeping. The write is defensive — a
    failure is logged and rolled back so cleaning up can never break the
    authentication response that is still in flight.
    """
    with guarded_write("the deletion of the expired user lock state "
                       f"({state.resolver!r}, {state.uid!r}, {state.realm!r})"):
        get_ca_session().delete(state)


def _delete_ip_block(state: BlockList) -> None:
    """
    Delete a :class:`BlockList` row that no longer restricts anything. The IP
    counterpart of :func:`_delete_user_lock_state`: used by :func:`get_ip_block`
    to drop a timed block the auth pre-check finds already expired, or a block on an
    IP that has since been added to the never-block allowlist. Defensive — a failure
    is logged and rolled back so cleaning up can never break the authentication
    response that is still in flight.
    """
    with guarded_write(f"the deletion of the unenforced IP block {state.ip!r}"):
        get_ca_session().delete(state)


def _upsert_user_lock_state(user: "User", *, lock_expires_at: datetime | None, error_message: str | None,
                            policy_name: str | None = None) -> bool:
    """
    Create or update the :class:`UserLockState` row for *user*.

    The write is defensive: a failure is logged and rolled back so that writing
    the lock state can never break the authentication response that already
    completed.

    Only a **strictly stronger** lock is written. A permanent lock is not downgraded to a timed one, a timed lock
    is not shortened, and a write that merely restates the lock in force changes nothing. Several policies can lock
    the same user in one request (:func:`evaluate_conditional_access_policies` runs every policy tracking the
    event), and a stage can carry more than one lock action; without this rule the last write would win regardless
    of severity, so a one-hour lock followed by a ten-minute one would leave the user locked for ten minutes.

    Restating matters for the *error message*, which travels with the expiry. Policies run in priority order, so the
    first to lock a subject is the highest-priority one that did, and a later policy writing the same lock again
    would otherwise replace its wording - with its own, or with none at all, silently overriding an admin who chose
    to say something. Since the restriction is unchanged, the wording describing it stands, and the policy whose
    message was not applied is logged.

    :return: whether the lock was written. ``False`` when the write failed, or when it was declined because a
        stronger lock is already in force - the caller uses this to record the action in the history only if it
        actually changed something.
    """
    declined = False
    with guarded_write(f"the user lock state for {user!r}") as write:
        session = get_ca_session()
        state = session.get(UserLockState, (user.resolver, user.uid, user.realm))
        if state is None:
            state = UserLockState(resolver=user.resolver, uid=user.uid, realm=user.realm)
            session.add(state)
        elif state.lock_expires_at == lock_expires_at:
            log.info(f"Policy {policy_name!r} restates the lock already in force for {user!r}; the error message of "
                     "the higher-priority policy that wrote it stands.")
            declined = True
        elif state.lock_expires_at is None and lock_expires_at is not None:
            log.info(f"Not downgrading the existing permanent lock for {user!r} to a timed lock.")
            declined = True
        elif lock_expires_at is not None and lock_expires_at < state.lock_expires_at:
            log.info(f"Not shortening the existing lock for {user!r}: it already runs until "
                     f"{state.lock_expires_at}.")
            declined = True
        if not declined:
            state.username = user.login
            state.lock_expires_at = lock_expires_at
            # Written together with the expiry, so the error message always describes the lock now in force. Only a
            # write that strengthens the lock gets here, and its error message comes with it.
            state.error_message = error_message
    return write.succeeded and not declined


def _upsert_ip_block(source_ip: str, *, block_expires_at: datetime | None, error_message: str | None,
                     policy_name: str | None = None) -> bool:
    """
    Create or update the :class:`BlockList` row for *source_ip*.

    The IP counterpart of :func:`_upsert_user_lock_state`: the write is
    defensive (a failure is logged and rolled back so that blocking an IP can
    never break the authentication response that already completed) and a block
    is never weakened - neither downgraded from permanent to timed, nor
    shortened.

    Never-block IPs (loopback and the ``PI_CONDITIONAL_ACCESS_NEVER_BLOCK``
    allowlist) are skipped: blocking shared infrastructure (a reverse proxy, NAT egress, or
    a load balancer) would lock out everyone behind it.

    :return: whether the block was written. ``False`` for a never-block IP, for a write declined because a
        stronger block is already in force, and for a failed write - so the caller records the action in the
        history only if it did something.
    """
    if is_ip_never_block(source_ip):
        log.info(f"Not blocking IP {source_ip!r}: it is on the conditional-access never-block list.")
        return False
    declined = False
    with guarded_write(f"the IP block for {source_ip!r}") as write:
        session = get_ca_session()
        state = session.get(BlockList, source_ip)
        if state is None:
            state = BlockList(ip=source_ip)
            session.add(state)
        elif state.block_expires_at == block_expires_at:
            log.info(f"Policy {policy_name!r} restates the block already in force for IP {source_ip!r}; the error "
                     f"message of the higher-priority policy that wrote it stands.")
            declined = True
        elif state.block_expires_at is None and block_expires_at is not None:
            log.info(f"Not downgrading the existing permanent block for IP {source_ip!r} to a timed block.")
            declined = True
        elif block_expires_at is not None and block_expires_at < state.block_expires_at:
            log.info(f"Not shortening the existing block for IP {source_ip!r}: it already runs until "
                     f"{state.block_expires_at}.")
            declined = True
        if not declined:
            state.block_expires_at = block_expires_at
            # See _upsert_user_lock_state: written together with the expiry.
            state.error_message = error_message
    return write.succeeded and not declined
