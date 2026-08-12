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
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.sql import ColumnElement

from privacyidea.lib import _
from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType,
                                                                           CA_ENFORCEMENT_EVENT_TYPES,
                                                                           CountMode)
from privacyidea.lib.conditional_access.authentication_log import _naive_utc
from privacyidea.lib.conditional_access.outcome_log import outcome_for_stage
from privacyidea.lib.conditional_access.session import get_ca_session, guarded_write
from privacyidea.models import (AuthenticationLog, BlockList, ConditionalAccessOutcome, LockoutPolicy,
                                LockoutPolicyCounterType, LockoutPolicyStage, LockoutStageAction, UserLockoutState)
from privacyidea.models.utils import utc_now

if TYPE_CHECKING:
    from privacyidea.lib.user import User

log = logging.getLogger(__name__)


class LockoutAction(str, Enum):
    """
    Action types a :class:`~privacyidea.models.lockout_policy.LockoutPolicyStage`
    can execute when its failure threshold is met.

    :attr:`LOCK_USER`, :attr:`PERMANENT_LOCK_USER`, :attr:`EMAIL_ADMIN`,
    :attr:`EMAIL_USER`, :attr:`BLOCK_IP` and :attr:`PERMANENT_BLOCK_IP` are
    post-response side effects executed by :func:`evaluate_lockout_policies`.
    :attr:`ALLOW` and :attr:`DENY` decide the *current* request and are therefore
    handled by the pre-auth decision step (:func:`evaluate_access_decision`)
    instead. The action table stores the string value, so the enum can grow
    without a schema change.

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
    ALLOW = "ALLOW"
    DENY = "DENY"

    def __str__(self) -> str:
        return self.value


class AccessDecision(str, Enum):
    """
    The verdict of the pre-auth conditional-access decision step
    (:func:`evaluate_access_decision`) for a single request.

    :attr:`DENY` rejects the current request outright (no persistent state is
    written); :attr:`ALLOW` permits it and short-circuits any lower-priority
    DENY policy, but does **not** bypass the credential check; :attr:`CONTINUE`
    is the default ("no decision policy matched") and lets the normal flow
    proceed. These map to the :attr:`LockoutAction.ALLOW` / :attr:`LockoutAction.DENY`
    stage actions, which - unlike the lockout/email/block actions - decide the
    current request and so are handled here, before authentication, rather than
    in the post-response engine.
    """
    ALLOW = "ALLOW"
    DENY = "DENY"
    CONTINUE = "CONTINUE"

    def __str__(self) -> str:
        return self.value


class LockoutTarget(str, Enum):
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
    3.10, mirroring :class:`LockoutAction`.
    """
    USER = "user"
    SOURCE_IP = "source_ip"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RestrictionStatus:
    """
    The state of an active conditional-access restriction on a single identity:
    a user lock (:func:`get_user_lockout`) or a source-IP block
    (:func:`get_ip_block`). Both return this same shape so callers (e.g. the
    ``/auth`` rejection messages) can treat them uniformly.

    :ivar permanent: ``True`` for a restriction that only an admin reset clears.
    :ivar expires_at: naive-UTC expiry of a timed restriction, or ``None`` when
        permanent.
    :ivar seconds_remaining: whole seconds until a timed restriction expires
        (``>= 0``), or ``None`` when permanent.
    """
    permanent: bool
    expires_at: "datetime | None"
    seconds_remaining: "int | None"


@dataclass
class LockoutEvaluation:
    """
    What one post-response evaluation produced: the notices to surface on the current response, and the outcomes to
    record as the request's conditional-access history.

    The engine returns these instead of writing the history itself. It has no access to the id of the
    authentication-log row (it runs before the row exists on the pre-auth path, and never sees it on the other), and
    keeping the write out of here is what leaves the engine free of Flask and of the request lifecycle - see
    :mod:`privacyidea.lib.conditional_access.outcome_log`.

    Also used as the per-policy result inside :func:`_evaluate_policy`, since "what this produced" is the same shape
    for one policy and for all of them.
    """
    notices: list[str] = field(default_factory=list)
    outcomes: list[ConditionalAccessOutcome] = field(default_factory=list)


@dataclass
class AccessDecisionResult:
    """
    The verdict of the pre-auth decision step plus the outcomes it produced.

    A ``DENY`` yields an outcome (enforced or dry-run); an ``ALLOW`` yields none, because the default-allow idiom - an
    ``ALLOW`` at threshold 0, which matches every request - would otherwise write one row per authentication.

    One type for a single policy's contribution (:func:`_policy_access_decision`) and for the whole evaluation
    (:func:`evaluate_access_decision`), the way :class:`LockoutEvaluation` serves one policy and all of them. Hence the
    default: :attr:`AccessDecision.CONTINUE` reads "this policy has no opinion" for the one and "no policy decided" for
    the other - which is what ``CONTINUE`` already means, so nothing needs a separate ``None`` to say it.
    """
    decision: AccessDecision = AccessDecision.CONTINUE
    outcomes: list[ConditionalAccessOutcome] = field(default_factory=list)


def _resolved(user: "User") -> bool:
    """
    Return ``True`` only for a fully resolved user, i.e. one with a complete
    ``(resolver, uid, realm)`` identity tuple. The lockout state and the
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
                      since_last_success: bool = False) -> int:
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
    :return: the number of matching events
    """
    return _count_events([AuthenticationLog.resolver == resolver,
                          AuthenticationLog.uid == uid,
                          AuthenticationLog.realm == realm],
                         event_types, window_seconds, window_end, since_last_success)


def count_distinct_users_for_ip(source_ip: str, event_types: list[str],
                                window_seconds: int, window_end: datetime | None = None) -> int:
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
        evaluation so this count shares it with the de-dup window and the new
        block's expiry.
    :return: the number of distinct targeted accounts
    """
    window_end = _naive_utc(window_end) if window_end is not None else utc_now()
    window_start = window_end - timedelta(seconds=window_seconds)
    type_values = [str(t) for t in event_types]
    distinct_accounts = (select(AuthenticationLog.username, AuthenticationLog.realm, AuthenticationLog.resolver)
                         .where(AuthenticationLog.source_ip == source_ip,
                                AuthenticationLog.event_type.in_(type_values),
                                AuthenticationLog.timestamp >= window_start,
                                AuthenticationLog.timestamp <= window_end)
                         .distinct()
                         .subquery())
    return get_ca_session().scalar(select(func.count()).select_from(distinct_accounts)) or 0


def _count_matching_attempts(rows: Sequence[AuthenticationLog], tracked_types: set[str],
                             since_last_success: bool = False) -> int:
    """
    Reduce authentication-log rows to one representative event per attempt and count the attempts whose
    representative is in *tracked_types*.

    All rows sharing an ``attempt_id`` are one authentication attempt. Its representative — the event that classifies
    the whole attempt — is :attr:`AuthEventType.LOGIN_SUCCESS` if the attempt ever logged in (a completed success is
    terminal: a later stray answer replayed on the same, now-answered challenge maps to the same ``attempt_id`` but
    must not undo the success), otherwise the **latest** event by row ``id``. Row ``id`` is the insertion order, which
    orders the multichallenge steps correctly independent of event type — e.g. a wrong answer *then* a continue reads
    as in-progress (latest = the continue), while a continue *then* a wrong answer reads as failed (latest = the fail),
    which an event-type ranking could not distinguish.

    Comparisons rely on :class:`AuthEventType` being a ``str`` subclass, so the stored ``event_type`` strings match
    the enum members directly — no conversion needed.

    :param rows: the authentication-log rows of the attempts to reduce
    :param tracked_types: the event types a representative must be in to count the attempt
    :param since_last_success: only count attempts whose latest row is newer than the last ``LOGIN_SUCCESS`` row
    :return: the number of attempts whose representative event is in *tracked_types*
    """
    latest: dict[str, AuthenticationLog] = {}
    succeeded: set[str] = set()
    last_success_id = -1
    # First pass: aggregate every row into its attempt — the attempt's latest (highest-id) row, whether it succeeded,
    # and the newest LOGIN_SUCCESS row id (the reset point for since_last_success).
    for row in rows:
        if row.event_type in CA_ENFORCEMENT_EVENT_TYPES:
            # A row conditional access wrote for its own rejection is not an outcome *of* the attempt and must not
            # classify one: the representative is the latest row by id, so a rejection correlated into an existing
            # attempt (a client retrying an answered transaction while locked) would displace a tracked failure with an
            # untracked type and *remove* an attempt that had already been counted - which would stop an escalation
            # from reaching its next stage once the lock expired.
            continue
        if row.event_type == AuthEventType.LOGIN_SUCCESS:
            succeeded.add(row.attempt_id)
            last_success_id = max(last_success_id, row.id)
        current = latest.get(row.attempt_id)
        if current is None or row.id > current.id:
            latest[row.attempt_id] = row
    cutoff_id = last_success_id if since_last_success else -1
    matches = 0
    # Second pass: over the distinct attempts, resolve each representative event and count the ones that match — and,
    # when flooring, only those whose latest row is newer than the last successful login.
    for attempt_id, row in latest.items():
        representative = AuthEventType.LOGIN_SUCCESS if attempt_id in succeeded else row.event_type
        if representative in tracked_types and row.id > cutoff_id:
            matches += 1
    return matches


def _count_attempts(subject: Sequence[ColumnElement[bool]], event_types: list[str], window_seconds: int,
                    window_end: datetime | None = None, since_last_success: bool = False) -> int:
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
    """
    window_end = _naive_utc(window_end) if window_end is not None else utc_now()
    window_start = window_end - timedelta(seconds=window_seconds)
    rows = get_ca_session().scalars(
        select(AuthenticationLog)
        .where(*subject,
               AuthenticationLog.timestamp >= window_start,
               AuthenticationLog.timestamp <= window_end,
               AuthenticationLog.event_type.notin_(sorted(str(event) for event in CA_ENFORCEMENT_EVENT_TYPES)))).all()
    return _count_matching_attempts(rows, set(event_types), since_last_success=since_last_success)


def count_user_attempts(resolver: str, uid: str, realm: str, event_types: list[str],
                        window_seconds: int, window_end: datetime | None = None,
                        since_last_success: bool = False) -> int:
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
    :return: the number of matching attempts
    """
    return _count_attempts([AuthenticationLog.resolver == resolver,
                            AuthenticationLog.uid == uid,
                            AuthenticationLog.realm == realm],
                           event_types, window_seconds, window_end, since_last_success)


def count_ip_events(source_ip: str, event_types: list[str], window_seconds: int,
                    window_end: datetime | None = None) -> int:
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
    :return: the number of matching events
    """
    return _count_events([AuthenticationLog.source_ip == source_ip], event_types, window_seconds, window_end)


def count_ip_attempts(source_ip: str, event_types: list[str],
                      window_seconds: int, window_end: datetime | None = None) -> int:
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
    :return: the number of matching attempts
    """
    return _count_attempts([AuthenticationLog.source_ip == source_ip], event_types, window_seconds, window_end)


def _policy_count(policy: LockoutPolicy, user: "User", window_end: datetime,
                  since_last_success: bool = False) -> int:
    """
    Count a user-target policy's events (``PER_REQUEST``) or attempts (``PER_ATTEMPT``) over its window, per the
    policy's :attr:`~privacyidea.models.lockout_policy.LockoutPolicy.count_mode`. (Source-IP policies dispatch
    separately via :func:`_policy_count_ip`.)

    :param policy: the policy whose ``time_window_seconds`` and ``counter_types_to_track`` are counted over
    :param user: the resolved user to count for
    :param window_end: the instant the window ends (reference time)
    :param since_last_success: True to floor the count at the user's last completed login in the window (a successful
        login resets the counter). Applies to both user modes — ``PER_REQUEST`` floors at the last ``LOGIN_SUCCESS``
        row, ``PER_ATTEMPT`` at the last successful attempt. (Source-IP ``DISTINCT_USERS`` deliberately never resets,
        which is why it is a separate mode and does not go through here.)
    :return: the event count (``PER_REQUEST``) or the attempt count (``PER_ATTEMPT``)
    """
    if policy.count_mode == CountMode.PER_ATTEMPT:
        return count_user_attempts(user.resolver, user.uid, user.realm,
                                   policy.counter_types_to_track, policy.time_window_seconds,
                                   window_end=window_end, since_last_success=since_last_success)
    return count_user_events(user.resolver, user.uid, user.realm,
                             policy.counter_types_to_track, policy.time_window_seconds,
                             window_end=window_end, since_last_success=since_last_success)


def _policy_count_ip(policy: LockoutPolicy, source_ip: str, window_end: datetime) -> int:
    """
    Count a source-IP-target policy's subject over its window, per the policy's
    :attr:`~privacyidea.models.lockout_policy.LockoutPolicy.count_mode`: distinct targeted accounts
    (``DISTINCT_USERS``, the default and spraying/enumeration signal), individual events (``PER_REQUEST``) or whole
    attempts (``PER_ATTEMPT``, the two volume modes = plain per-IP rate limiting). None of the three resets on a
    successful login - a legit login by one account must not clear a signal aggregated across the whole IP - so there
    is no ``since_last_success`` parameter, unlike the user path (:func:`_policy_count`).

    :param policy: the policy whose ``time_window_seconds`` and ``counter_types_to_track`` are counted over
    :param source_ip: the client IP to count for
    :param window_end: the instant the window ends (reference time)
    :return: the distinct-account count (``DISTINCT_USERS``), event count (``PER_REQUEST``) or attempt count
        (``PER_ATTEMPT``)
    """
    if policy.count_mode == CountMode.PER_REQUEST:
        return count_ip_events(source_ip, policy.counter_types_to_track,
                               policy.time_window_seconds, window_end=window_end)
    if policy.count_mode == CountMode.PER_ATTEMPT:
        return count_ip_attempts(source_ip, policy.counter_types_to_track,
                                 policy.time_window_seconds, window_end=window_end)
    return count_distinct_users_for_ip(source_ip, policy.counter_types_to_track,
                                       policy.time_window_seconds, window_end=window_end)


def get_user_lockout(user: "User", now: datetime | None = None, *,
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
    never deleted. The delete is defensive (see :func:`_delete_user_lockout_state`).

    A row with ``lock_expires_at IS NULL`` is a permanent lock.

    :param user: the user to check; an unresolved user is never locked
    :param now: the reference time; defaults to :func:`utc_now`
    :param clear_expired: delete the row if it is a stale (timed, expired) lock;
        off by default to keep this a pure read for non-auth callers
    :return: ``None`` if not locked, else a :class:`RestrictionStatus`
    """
    if not _resolved(user):
        return None
    state = get_ca_session().get(UserLockoutState, (user.resolver, user.uid, user.realm))
    if not state:
        return None
    if state.lock_expires_at is None:
        # Permanent lock; only an admin reset clears it.
        return RestrictionStatus(permanent=True, expires_at=None, seconds_remaining=None)
    now = _naive_utc(now) if now is not None else utc_now()
    if state.lock_expires_at <= now:
        # If explicitly requested, drop expired rows
        if clear_expired:
            _delete_user_lockout_state(state)
        return None
    remaining = int((state.lock_expires_at - now).total_seconds())
    return RestrictionStatus(permanent=False, expires_at=state.lock_expires_at,
                             seconds_remaining=remaining)


def is_user_locked(user: "User", now: datetime | None = None, *, clear_expired: bool = False) -> bool:
    """
    Return whether *user* is currently locked. Thin boolean wrapper over
    :func:`get_user_lockout` for the authentication pre-check hot path; see that
    function for the expiry, permanent-lock, and *clear_expired* semantics.

    :param user: the user to check; an unresolved user is never locked
    :param now: the reference time; defaults to :func:`utc_now`
    :param clear_expired: delete the row if it is a stale (timed, expired) lock
    :return: ``True`` if the user is currently locked
    """
    return get_user_lockout(user, now=now, clear_expired=clear_expired) is not None


# Built-in never-block networks: blocking loopback would lock out a same-host
# reverse proxy — and when OVERRIDECLIENT is unset every client is seen as that
# proxy — turning one BLOCK_IP action into a self-inflicted outage. Admins extend
# this via the CONDITIONAL_ACCESS_NEVER_BLOCK system config (proxy / load-balancer
# / NAT / management CIDRs).
_DEFAULT_NEVER_BLOCK_NETWORKS = ("127.0.0.0/8", "::1/128")


def _never_block_networks() -> "list[ipaddress._BaseNetwork]":
    """
    The never-block networks: the built-in loopback defaults plus the CIDRs (or
    bare IPs) configured in the ``CONDITIONAL_ACCESS_NEVER_BLOCK`` system config.
    Invalid config entries are logged and ignored rather than breaking the engine.
    """
    # Lazy import: config is loaded very early in app startup; importing it at
    # module load would risk an import-order cycle.
    from privacyidea.lib.config import get_from_config, SYSCONF
    networks = [ipaddress.ip_network(cidr) for cidr in _DEFAULT_NEVER_BLOCK_NETWORKS]
    configured = get_from_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK) or ""
    for entry in re.split(r"[,\s]+", configured.strip()):
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            log.warning(f"Ignoring invalid network {entry!r} in {SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK}.")
    return networks


def is_ip_never_block(source_ip: str | None) -> bool:
    """
    Return whether *source_ip* must never be blocked by the conditional-access
    engine: it is loopback (built-in) or matches the ``CONDITIONAL_ACCESS_NEVER_BLOCK``
    system config. A falsy or unparsable IP is treated as never-block as well —
    fail safe: never block an address the engine cannot positively identify.
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
    counterpart of :func:`get_user_lockout` and is meant for the authentication
    pre-check hot path.

    By default this is a **pure read**: a stale row whose ``block_expires_at`` lies
    in the past simply reads as *not blocked* and is left in place.

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
    :param clear_expired: delete the row if it is a stale (timed, expired) block;
        off by default to keep this a pure read for non-auth callers
    :return: ``None`` if not blocked, else a :class:`RestrictionStatus`
    """
    if not source_ip:
        return None
    state = get_ca_session().get(BlockList, source_ip)
    if not state:
        return None
    # A block row exists; honor the never-block allowlist so adding an IP to it
    # immediately stops enforcing any (e.g. stale or mistaken) block on that IP.
    if is_ip_never_block(source_ip):
        return None
    if state.block_expires_at is None:
        # Permanent block; only an admin reset clears it.
        return RestrictionStatus(permanent=True, expires_at=None, seconds_remaining=None)
    now = _naive_utc(now) if now is not None else utc_now()
    if state.block_expires_at <= now:
        if clear_expired:
            _delete_ip_block(state)
        return None
    remaining = int((state.block_expires_at - now).total_seconds())
    return RestrictionStatus(permanent=False, expires_at=state.block_expires_at,
                             seconds_remaining=remaining)


def is_ip_blocked(source_ip: str | None, now: datetime | None = None, *, clear_expired: bool = False) -> bool:
    """
    Return whether *source_ip* is currently blocked by the ``BLOCK_IP`` action.
    Thin boolean wrapper over :func:`get_ip_block` for the authentication
    pre-check hot path; see that function for the expiry, permanent-block, and
    *clear_expired* semantics.

    :param source_ip: the client IP to check; a falsy value is never blocked
    :param now: the reference time; defaults to :func:`utc_now`
    :param clear_expired: delete the row if it is a stale (timed, expired) block
    :return: ``True`` if the IP is currently blocked
    """
    return get_ip_block(source_ip, now=now, clear_expired=clear_expired) is not None


def evaluate_access_decision(user: "User", source_ip: str | None = None,
                             now: datetime | None = None) -> "AccessDecisionResult":
    """
    Pre-auth conditional-access decision for the current request: should it be
    denied, explicitly allowed, or left to the normal flow?

    This runs **before** the credential check (and, per the chosen precedence,
    *after* the persistent :func:`is_user_locked` / :func:`is_ip_blocked`
    pre-checks, so an :attr:`AccessDecision.ALLOW` can never override a lock or
    block). It handles only the :attr:`LockoutAction.ALLOW` /
    :attr:`LockoutAction.DENY` actions; the lockout/email/block actions are
    post-response side effects handled by :func:`evaluate_lockout_policies`.

    Because there is no event for the current request yet, the decision is keyed
    on the user's **prior** event history: for each enabled policy the events of
    its ``counter_types_to_track`` are counted (combined across all tracked
    types) over its window, and the highest-priority stage with a matching
    ALLOW/DENY action supplies the decision. A
    ``DENY`` action therefore rejects this single request without persisting any
    state — a stateless, self-healing reject that lifts on its own as the
    failures age out of the window (contrast the durable :attr:`LockoutAction.LOCK_USER`).
    Because ALLOW/DENY actions default to re-triggering (``count >= threshold``), a
    stage with ``failure_threshold`` 0 always matches, so an ``ALLOW`` action at
    threshold 0 acts as a default-allow / allowlist exception.

    Policies are evaluated by ascending ``priority`` (a lower number means higher
    precedence, matching privacyIDEA's policy engine) and the first one that
    yields a decision wins, so an ALLOW with a lower priority number overrides a
    DENY with a higher number and vice versa. ``dry_run`` policies are logged but
    never enforced.

    Both targets decide here: a ``user`` policy is keyed on the resolved
    ``(resolver, uid, realm)`` user (an unresolved user - unknown login, local
    admin - is never decided by a user policy), while a ``source_ip`` policy is
    keyed on *source_ip* and therefore applies even when the user is unresolved
    (the spraying/enumeration case). A never-block source IP is exempt from an IP
    ``DENY``, mirroring the ``BLOCK_IP`` allowlist.

    :param user: the authenticating user; only ``user``-target policies need it
    :param source_ip: the resolved client IP; ``source_ip``-target policies decide on it
    :param now: the reference time; defaults to :func:`utc_now`
    :return: the :class:`AccessDecisionResult` for this request: the decision, plus the outcomes to record on
        whichever authentication-log row this request ends up writing
    """
    now = _naive_utc(now) if now is not None else utc_now()
    policies = get_ca_session().scalars(
        select(LockoutPolicy)
        .where(LockoutPolicy.enabled.is_(True))
        .order_by(LockoutPolicy.priority.asc())
    ).all()
    outcomes: list[ConditionalAccessOutcome] = []
    for policy in policies:
        contribution = _policy_access_decision(policy, user, source_ip, now)
        outcomes.extend(contribution.outcomes)
        if contribution.decision != AccessDecision.CONTINUE:
            # The first policy that decides wins, so no lower-priority policy is even consulted - and the outcomes
            # collected so far are exactly those of the policies that had something to say.
            return AccessDecisionResult(contribution.decision, outcomes)
    return AccessDecisionResult(outcomes=outcomes)


def _policy_access_decision(policy: LockoutPolicy, user: "User", source_ip: str | None,
                            now: datetime) -> "AccessDecisionResult":
    """
    What a single policy contributes to the pre-auth decision: its ALLOW/DENY verdict, and the outcome to record for it.

    The decision is :attr:`AccessDecision.CONTINUE` when this policy does not decide the request: wrong or absent
    subject, no ALLOW/DENY action's threshold condition is met, or the policy is in dry run - a dry-run policy is never
    enforced, but it still yields its outcome, which is how an admin measures what enforcing it would do.

    Each ALLOW/DENY action decides for itself via :func:`_action_threshold_met`:
    such actions default to re-triggering (``count >= threshold``, so the decision
    stands while the failures are high), which is what makes ``ALLOW`` at threshold
    0 a default-allow and ``DENY`` a self-healing reject. An admin can switch a
    decision action to fire-once, in which case it only decides the request at the
    exact threshold count. The highest-priority stage with a met ALLOW/DENY action
    supplies the decision.

    Only a ``DENY`` produces an outcome. An ``ALLOW`` at threshold 0 is the documented default-allow idiom and matches
    every request of every user it covers, so recording it would add a row to every authentication.
    """
    if policy.target == LockoutTarget.SOURCE_IP:
        # IP-scoped: decide on the source IP regardless of user resolution. A
        # never-block IP is never denied by an IP policy (mirrors the BLOCK_IP
        # allowlist), so it contributes no decision.
        if not source_ip or is_ip_never_block(source_ip):
            return AccessDecisionResult()
        count = _policy_count_ip(policy, source_ip, now)
        subject_label = f"source IP {source_ip}"
    else:
        # User-scoped: keyed on the resolved user, so an unresolved user is never
        # decided by a user policy.
        if not _resolved(user):
            return AccessDecisionResult()
        count = _policy_count(policy, user, now)
        subject_label = repr(user)
    decision, deciding_stage = None, None
    for stage in policy.stages:
        decision = _stage_access_decision(stage, count)
        if decision is not None:
            deciding_stage = stage
            break
    if decision is None:
        return AccessDecisionResult()
    types = _types_label(policy.counter_types_to_track)
    # Only a DENY is recorded; see the docstring for why an ALLOW is not.
    outcomes = ([outcome_for_stage(policy, deciding_stage, LockoutAction.DENY, count, dry_run=policy.dry_run)]
                if decision == AccessDecision.DENY else [])
    if policy.dry_run:
        # A dry-run policy never decides the request. The outcome still travels back: the pre-auth decision runs
        # before this request's authentication-log row exists, so the caller buffers it and it is recorded once that
        # row is written (see ConditionalAccessContext.stage).
        log.info(f"[dry-run] policy {policy.name!r} would return {decision} for {subject_label}: "
                 f"{count} event(s) of {types} in {policy.time_window_seconds}s.")
        return AccessDecisionResult(outcomes=outcomes)
    log.info(f"Policy {policy.name!r} returns access decision {decision} for {subject_label}: "
             f"{count} event(s) of {types} in {policy.time_window_seconds}s.")
    return AccessDecisionResult(decision, outcomes)


def _stage_access_decision(stage: LockoutPolicyStage, count: int) -> "AccessDecision | None":
    """
    Extract the pre-auth ALLOW/DENY decision from a stage's actions whose
    per-action threshold condition is met at *count*, or ``None`` if no such
    ALLOW/DENY action applies. If both an ALLOW and a DENY apply, DENY wins (fail
    closed).
    """
    has_allow = False
    for action in stage.actions:
        try:
            action_type = LockoutAction(action.action_type)
        except ValueError:
            continue
        if action_type not in (LockoutAction.ALLOW, LockoutAction.DENY):
            continue
        if not _action_threshold_met(action, stage.failure_threshold, count):
            continue
        if action_type == LockoutAction.DENY:
            return AccessDecision.DENY
        has_allow = True
    return AccessDecision.ALLOW if has_allow else None


def evaluate_lockout_policies(user: "User", event_type: AuthEventType | None, source_ip: str | None = None,
                              now: datetime | None = None) -> "LockoutEvaluation":
    """
    Evaluate every enabled lockout policy that tracks *event_type* and execute
    the actions of the triggered stage, if any. This runs post-response, *after*
    the request's ``authentication_log`` row has been written (so the count
    includes it).

    Each action decides for itself whether it fires. By default an action fires
    once, when the failure count reaches its stage's threshold exactly: an action
    at threshold 8 runs on the 8th failure and not again on the 9th. An action with
    ``retrigger_above_threshold`` fires whenever the count is at or above the
    threshold, so a single stage can email once at threshold 8 while keeping the
    user locked for every further failure (see :func:`_action_threshold_met`). The
    count climbs by one per tracked failure and resets after a successful login
    (see :func:`count_user_events`), so a fresh burst re-triggers the fire-once
    actions too.

    The persistent side effects (lock state) are consulted by the *next* inbound
    request via the pre-check. In addition, an executed ``EMAIL_*`` action yields
    a short user-facing notice (e.g. "Your administrator has been notified by
    email."); those notices are returned so the caller can surface them on the
    current response — the login screen shows them next to the rejection, exactly
    as it shows a lockout message. Any error is the caller's to swallow; this
    function itself only guards individual DB writes (see
    :func:`_upsert_user_lockout_state`).

    Alongside the notices, every action that actually ran (or, in dry run, would have run) is returned as a
    :class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome` for the caller to record as this
    request's history.
    The engine deliberately does not write them: it never sees the id of the authentication-log row they belong to.

    :param user: the authenticating user; ``user``-target policies need it
        resolved, ``source_ip``-target policies act on the IP regardless
    :param event_type: the classified outcome of the request
        (:class:`AuthEventType`)
    :param source_ip: the resolved client IP; the ``BLOCK_IP`` action blocks it
    :param now: the reference time; defaults to :func:`utc_now`
    :return: a :class:`LockoutEvaluation` holding the de-duplicated, order-preserving user-facing notices produced by
        executed actions, and the outcomes to record (both empty if nothing was triggered)
    """
    if not event_type:
        return LockoutEvaluation()
    now = _naive_utc(now) if now is not None else utc_now()
    event_type = str(event_type)
    # Select only the enabled policies that track the current event type, via an
    # indexed equality filter on the normalized lockout_policy_counter_types
    # table (policy_id, counter_type) is unique, so a policy matches at
    # most once. The combined count over *all* of a matched policy's tracked types
    # is then computed in _evaluate_policy.
    policies = get_ca_session().scalars(
        select(LockoutPolicy)
        .join(LockoutPolicy.counter_types)
        .where(LockoutPolicy.enabled.is_(True),
               LockoutPolicyCounterType.counter_type == event_type)
        .order_by(LockoutPolicy.priority.asc())
    ).all()
    notices: list[str] = []
    outcomes: list[ConditionalAccessOutcome] = []
    for policy in policies:
        # Guarded per policy, for two reasons. One policy's failure must not cost the others theirs - a broken policy
        # would otherwise disable every policy ordered behind it. And it keeps the actions this call already executed
        # from being repeated: the caller evaluates a classification again when an earlier attempt did not return
        # (see ConditionalAccessContext.run_post_eval), and a stage whose actions leave no live state - an EMAIL-only
        # stage writes neither a lock nor a block - has nothing for the de-dup below to recognize on the second pass.
        # With the loop guarded, the only failure that still escapes is the policy query above, which runs before any
        # action does, so the retry always starts from a clean slate.
        try:
            evaluation = _evaluate_policy(policy, user, event_type, source_ip, now)
        except Exception as ex:
            log.warning(f"Lockout policy {policy.name!r} failed to evaluate: {ex!r}; skipping it.")
            continue
        notices.extend(evaluation.notices)
        outcomes.extend(evaluation.outcomes)
    # De-duplicate the notices while preserving order: several policies tracking the same user can emit the same one
    # in a single request. The outcomes are *not* de-duplicated - each is a distinct thing that happened, and two
    # policies locking the same user are two facts worth keeping apart.
    seen: set[str] = set()
    unique: list[str] = []
    for notice in notices:
        if notice not in seen:
            seen.add(notice)
            unique.append(notice)
    return LockoutEvaluation(notices=unique, outcomes=outcomes)


def _action_threshold_met(action: LockoutStageAction, threshold: int, count: int) -> bool:
    """
    Whether *action* fires at the given failure *count*, for its stage's
    *threshold*.

    Default (``retrigger_above_threshold`` unset): the action fires only when the
    count equals the threshold exactly, so it triggers once as the count climbs
    past it. With ``retrigger_above_threshold`` the action fires whenever the count
    is at or above the threshold (the classic re-triggering lockout). The flag is
    per action, so one stage can e.g. email once at its threshold while keeping the
    user locked as long as the count stays at or above it.
    """
    if action.retrigger_above_threshold:
        return count >= threshold
    return count == threshold


def _stage_pending_actions(stage: LockoutPolicyStage, count: int) -> list[LockoutStageAction]:
    """The actions of *stage* whose per-action condition is met at *count*."""
    return [action for action in stage.actions
            if _action_threshold_met(action, stage.failure_threshold, count)]


def _evaluate_policy(policy: LockoutPolicy, user: "User", event_type: str,
                     source_ip: str | None, now: datetime) -> "LockoutEvaluation":
    """
    Evaluate a single policy: count the user's events over the policy window,
    find the triggered stage, de-duplicate, then execute the stage's *pending*
    actions (or, in dry-run, only log what they would have done).

    Each action decides for itself whether it fires (see
    :func:`_action_threshold_met`): by default an action triggers once, when the
    count equals the stage's ``failure_threshold``; an action with
    ``retrigger_above_threshold`` fires whenever the count is at or above the
    threshold. So one stage can, for example, email once at threshold 8 while
    keeping the user locked for every further failure at 8 or more.

    :return: a :class:`LockoutEvaluation` with the user-facing notices produced by the executed actions and the
        outcomes describing what was done (both empty if no stage triggered or the stage was de-duplicated away; in
        dry run there are outcomes but no notices, since nothing ran)
    """
    window = policy.time_window_seconds
    if policy.target == LockoutTarget.SOURCE_IP:
        if not source_ip:
            # An IP-targeted policy cannot count or act without a source IP.
            log.debug(f"Skipping source-IP policy {policy.name!r}: the request carries no source IP.")
            return LockoutEvaluation()
        # Count per the policy's mode: distinct targeted accounts (spraying) or plain per-IP volume. No
        # since-last-success reset in any mode — a legit login by one account must not clear a signal aggregated
        # across the whole IP (see _policy_count_ip).
        count = _policy_count_ip(policy, source_ip, now)
        subject_label = f"source IP {source_ip}"
    else:
        if not _resolved(user):
            # A user-target policy is keyed on the resolved (resolver, uid, realm)
            # user, so an unresolved user (unknown login, local admin) is never
            # locked. Source-IP policies above still run for such requests.
            return LockoutEvaluation()
        # The lock counts consecutive failures since the user's last completed login:
        # a successful authentication clears the slate, so a legitimate user is not
        # re-locked by stale pre-login failures on their next single typo. (The DENY
        # decision deliberately does not reset on success — see _policy_access_decision.)
        # The count is the *combined* total over all of the policy's tracked types,
        # not just the current request's event_type, so a policy tracking several
        # failure types trips on their sum.
        count = _policy_count(policy, user, now, since_last_success=True)
        subject_label = repr(user)

    # Pick the triggered stage: the highest-priority stage that has at least one
    # action whose per-action condition is met (see _action_threshold_met). By
    # default an action fires only at the exact threshold, so each fire-once action
    # triggers once as the count climbs past it (a threshold-8 email is sent when
    # the 8th failure lands, not again at 9); a re-triggering action keeps firing
    # while the count stays at or above the threshold. Stages are ordered
    # highest-priority first by the relationship, so the most severe stage with a
    # pending action wins; only that one stage's pending actions run (one stage per
    # policy per request). (Contrast the pre-auth ALLOW/DENY decision - see
    # _policy_access_decision.)
    triggered_stage = next((stage for stage in policy.stages
                            if _stage_pending_actions(stage, count)), None)
    if triggered_stage is None:
        return LockoutEvaluation()
    pending_actions = _stage_pending_actions(triggered_stage, count)

    if policy.dry_run:
        # Dry-run never reads or writes the de-dup state, so it logs on every
        # in-window request that would trip the stage.
        log.info(f"[dry-run] policy {policy.name!r} would trigger stage {triggered_stage.id} "
                 f"(threshold {triggered_stage.failure_threshold}) for {subject_label}: "
                 f"{count} event(s) of {_types_label(policy.counter_types_to_track)} in {window}s.")
        # One outcome per action that would have run, carrying the expiry it would have written - which is the whole
        # point of dry run: the history shows what enforcing this policy would have done to real traffic. A LOCK_USER
        # or BLOCK_IP whose duration is misconfigured records no expiry, so dry run surfaces that too.
        # ALLOW/DENY are left out: they decide the request pre-auth and are recorded there (_policy_access_decision),
        # so recording them again here would double-count the same decision.
        outcomes = [outcome_for_stage(policy, triggered_stage, action.action_type, count, dry_run=True,
                                        expires_at=_action_expiry(action, now))
                    for action in pending_actions
                    if action.action_type not in (LockoutAction.ALLOW, LockoutAction.DENY)]
        return LockoutEvaluation(outcomes=outcomes)

    dedup_window_start = now - timedelta(seconds=window)
    # De-dup: with exact-threshold triggering a stage normally fires once as the
    # count climbs past it, but a sliding window can let the count fall back to
    # and re-reach the same threshold; this skips a stage that already fired
    # within the window for this user, or (for IP-blocking stages) for this
    # source IP. An incident *ends* when its lock/block is lifted — whether by
    # expiry OR by an admin deleting the row — so
    # re-reaching the threshold afterwards is a fresh incident that must execute
    # again. Otherwise an expired or admin-lifted lock would leave a dead zone in
    # which the offender could re-reach the threshold without being re-locked /
    # re-blocked.
    user_state = get_ca_session().get(UserLockoutState, (user.resolver, user.uid, user.realm))
    user_incident_active = (user_state is not None
                            and (user_state.lock_expires_at is None
                                 or user_state.lock_expires_at > now))
    user_dedup = (user_incident_active
                  and user_state.last_stage_triggered == triggered_stage.id
                  and user_state.locked_at is not None
                  and user_state.locked_at >= dedup_window_start)
    # An IP-blocking stage de-dups on its BlockList row, mirroring the user
    # de-dup. Without this such a stage has no de-dup at all (it never writes
    # UserLockoutState): the count re-reaching the threshold would re-fire it,
    # refreshing the block and re-running any sibling actions.
    ip_dedup = False
    if source_ip and any(a.action_type in (LockoutAction.BLOCK_IP, LockoutAction.PERMANENT_BLOCK_IP)
                         for a in pending_actions):
        ip_state = get_ca_session().get(BlockList, source_ip)
        ip_incident_active = (ip_state is not None
                              and (ip_state.block_expires_at is None
                                   or ip_state.block_expires_at > now))
        ip_dedup = (ip_incident_active
                    and ip_state.last_stage_triggered == triggered_stage.id
                    and ip_state.blocked_at is not None
                    and ip_state.blocked_at >= dedup_window_start)
    if user_dedup or ip_dedup:
        log.debug(f"De-dup: stage {triggered_stage.id} already triggered within the window for "
                  f"{user!r}; skipping actions.")
        # Nothing ran, so nothing is recorded: the history must not imply a second lock.
        return LockoutEvaluation()

    log.info(f"Policy {policy.name!r} triggered stage {triggered_stage.id} "
             f"(threshold {triggered_stage.failure_threshold}) for {subject_label}: "
             f"{count} event(s) of {_types_label(policy.counter_types_to_track)} in {window}s.")
    tags = _base_action_tags(policy, triggered_stage, user, event_type, count, source_ip, now)
    return _execute_stage_actions(policy, triggered_stage, pending_actions, user, source_ip, now, count, tags)


def _action_expiry(stage_action: LockoutStageAction, now: datetime) -> datetime | None:
    """
    When the restriction written by *stage_action* ends, or ``None`` when there is nothing to expire.

    ``None`` covers three different cases, which the action type tells apart: a ``PERMANENT_*`` action (never expires),
    an action that creates no restriction at all (``EMAIL_*``, ``ALLOW``/``DENY``), and a timed action whose configured
    duration is missing or invalid - which is a misconfiguration the enforced path skips and logs, and which a dry-run
    outcome surfaces as "would have locked, but for how long is not configured".
    """
    if stage_action.action_type not in (LockoutAction.LOCK_USER, LockoutAction.BLOCK_IP):
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


def _base_action_tags(policy: LockoutPolicy, stage: LockoutPolicyStage, user: "User", event_type: str,
                      count: int, source_ip: str | None, now: datetime) -> dict:
    """
    Build the ``{tag}`` substitution context available to EMAIL_* templates. Only
    fields already loaded on the request are included here; the resolver-backed
    user attributes (email, givenname, surname) are added lazily in
    :func:`_send_lockout_email`, so a non-email action never triggers a resolver
    lookup.

    There is exactly one canonical name per value — no aliases — so a template
    references each value unambiguously. The names match privacyIDEA's existing
    notification vocabulary (:func:`~privacyidea.lib.utils.create_tag_dict`): the
    login is ``{username}`` and the request IP is ``{client_ip}``. (Showing the
    available tags in the policy editor and rejecting unknown ``{tags}`` when a
    template is saved belong to the policy CRUD/editor layer, not here.)
    """
    return {
        "username": user.login,
        "realm": user.realm or "",
        "resolver": user.resolver or "",
        "client_ip": source_ip or "",
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
        # Imported lazily: keeps the engine's hot path free of lib.auth's heavy
        # token/container imports and avoids any import-time coupling.
        from privacyidea.lib.auth import get_all_db_admins
        return [admin.email for admin in get_all_db_admins() if admin.email]
    log.warning(f"Unknown EMAIL_ADMIN recipient_group {recipient_group!r}; "
                f"expected 'internal_admins' or a comma-separated email list.")
    return []


def _login_notice(action_type: "LockoutAction", email_config: dict, render_tags: dict) -> str:
    """
    Build the short message shown to the user on the login screen once an
    ``EMAIL_*`` action has been sent, mirroring how a lockout rejection is
    surfaced. An admin can override it per action with a ``login_notice``
    template in ``action_value`` (``{tag}`` substitution applies); otherwise a
    default keyed by the action type is used. The wording never reveals the
    recipient address.
    """
    custom = email_config.get("login_notice")
    if custom:
        return _safe_format(str(custom), render_tags)
    if action_type == LockoutAction.EMAIL_USER:
        return _("A notification email has been sent to your email address.")
    return _("Your administrator has been notified by email.")


def _send_lockout_email(action_type: "LockoutAction", stage_action: LockoutStageAction,
                        user: "User", tags: dict) -> str | None:
    """
    Send the EMAIL_ADMIN / EMAIL_USER notification for a triggered stage action.

    The stage action's ``action_value`` is a JSON object carrying
    ``smtp_identifier`` (the SMTP server configuration to use), ``subject`` and
    ``body`` (both rendered with ``{tag}`` substitution), an optional ``mimetype``
    (``plain``/``html``), an optional ``login_notice`` (overrides the message
    surfaced on the login screen) and, for EMAIL_ADMIN, an optional
    ``recipient_group``. EMAIL_USER sends to the user's own email address. A
    missing field or a user without an email address is logged and skipped; this
    runs post-response and must never raise.

    :return: the user-facing login-screen notice if the email was sent, else
        ``None`` (misconfiguration, no recipient, or delivery failure).
    """
    email_config = stage_action.action_value if isinstance(stage_action.action_value, dict) else {}
    identifier = email_config.get("smtp_identifier") or email_config.get("identifier")
    subject, body = email_config.get("subject"), email_config.get("body")
    if not identifier or not subject or not body:
        log.warning(f"{action_type} action {stage_action.id}: needs smtp_identifier, subject and body in "
                    f"action_value; skipping.")
        return

    # Resolver-backed attributes are fetched once, only now that an email is sent.
    info = user.info or {}
    render_tags = {**tags, "email": info.get("email") or "",
                   "givenname": info.get("givenname") or "", "surname": info.get("surname") or ""}

    if action_type == LockoutAction.EMAIL_USER:
        recipients = [info["email"]] if info.get("email") else []
        if not recipients:
            log.warning(f"EMAIL_USER action {stage_action.id}: user {user!r} has no email address; skipping.")
            return
    else:  # EMAIL_ADMIN
        recipients = _resolve_admin_recipients(email_config.get("recipient_group"))
        if not recipients:
            log.warning(f"EMAIL_ADMIN action {stage_action.id}: no recipients for "
                        f"recipient_group={email_config.get('recipient_group')!r}; skipping.")
            return

    from privacyidea.lib.smtpserver import send_email_identifier
    sent = send_email_identifier(identifier, recipients,
                                 _safe_format(str(subject), render_tags),
                                 _safe_format(str(body), render_tags),
                                 mimetype=email_config.get("mimetype", "plain"))
    if sent:
        log.info(f"{action_type} for {user!r} sent to {len(recipients)} recipient(s) via {identifier!r}.")
        return _login_notice(action_type, email_config, render_tags)
    log.warning(f"{action_type} for {user!r} could not be delivered via {identifier!r}.")
    return None


def _execute_stage_actions(policy: LockoutPolicy, stage: LockoutPolicyStage,
                           actions: Sequence[LockoutStageAction], user: "User", source_ip: str | None,
                           now: datetime, count: int, tags: dict) -> "LockoutEvaluation":
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

    :param policy: the triggering policy, for the outcomes
    :param count: the count that tripped the stage, for the outcomes
    :return: a :class:`LockoutEvaluation` with the user-facing notices produced by executed ``EMAIL_*`` actions and one
        outcome per action that ran (both empty if every action was skipped).
    """
    notices: list[str] = []
    outcomes: list[ConditionalAccessOutcome] = []

    def record(action_type: str, expires_at: datetime | None = None) -> None:
        """Note that *action_type* ran, with the expiry it wrote (if any)."""
        outcomes.append(outcome_for_stage(policy, stage, action_type, count, expires_at=expires_at))

    for action in actions:
        try:
            action_type = LockoutAction(action.action_type)
        except ValueError:
            log.warning(f"Unknown lockout action type {action.action_type!r} on stage {stage.id}; skipping.")
            continue

        try:
            if action_type == LockoutAction.LOCK_USER:
                duration = _lock_duration_seconds(action.action_value)
                if duration is None:
                    log.warning(f"LOCK_USER action {action.id} on stage {stage.id} has no valid duration "
                                f"({action.action_value!r}); skipping.")
                    continue
                lock_expires_at = now + timedelta(seconds=duration)
                if _upsert_user_lockout_state(user, lock_expires_at=lock_expires_at, stage_id=stage.id):
                    record(action_type, expires_at=lock_expires_at)
            elif action_type == LockoutAction.PERMANENT_LOCK_USER:
                if _upsert_user_lockout_state(user, lock_expires_at=None, stage_id=stage.id):
                    record(action_type)
            elif action_type in (LockoutAction.EMAIL_ADMIN, LockoutAction.EMAIL_USER):
                notice = _send_lockout_email(action_type, action, user, tags)
                if notice:
                    # A notice is returned exactly when the mail was accepted, so it doubles as "this action ran".
                    notices.append(notice)
                    record(action_type)
            elif action_type in (LockoutAction.BLOCK_IP, LockoutAction.PERMANENT_BLOCK_IP):
                # Failures are counted per user, so this blocks the source IP
                # of the request that tripped a *per-user* policy. It does not
                # detect password spraying (failures from one IP across many
                # users); it simply blocks the offending request's IP.
                if not source_ip:
                    log.warning(f"{action_type} action {action.id} on stage {stage.id}: this request "
                                f"has no source IP; skipping.")
                    continue
                if action_type == LockoutAction.PERMANENT_BLOCK_IP:
                    # Permanent block; action_value is ignored (mirrors PERMANENT_LOCK_USER).
                    block_expires_at = None
                else:
                    duration = _lock_duration_seconds(action.action_value)
                    if duration is None:
                        log.warning(f"BLOCK_IP action {action.id} on stage {stage.id} has no valid duration "
                                    f"({action.action_value!r}); skipping.")
                        continue
                    block_expires_at = now + timedelta(seconds=duration)
                if _upsert_ip_block(source_ip, block_expires_at=block_expires_at, stage_id=stage.id):
                    record(action_type, expires_at=block_expires_at)
            elif action_type in (LockoutAction.ALLOW, LockoutAction.DENY):
                # ALLOW/DENY decide the current request pre-auth (see
                # evaluate_access_decision); they are not post-response side
                # effects, so there is nothing to do here - and nothing to record: the decision is already an outcome
                # of its own from _policy_access_decision.
                log.debug(f"{action_type} is a pre-auth access decision; skipping in the "
                          f"post-response engine.")
            else:
                log.info(f"Lockout action {action_type} is recognized but not implemented yet; skipping.")
        except Exception as ex:
            log.warning(f"Lockout action {action_type} (id {action.id}) on stage {stage.id} "
                        f"failed: {ex!r}; skipping.")
    return LockoutEvaluation(notices=notices, outcomes=outcomes)


def _delete_user_lockout_state(state: UserLockoutState) -> None:
    """
    Delete a stale :class:`UserLockoutState` row.

    Used by :func:`get_user_lockout` to drop a timed lock the auth pre-check finds
    already expired: the row is no longer enforced and the authentication log is
    the record, so it carries nothing worth keeping. The write is defensive — a
    failure is logged and rolled back so cleaning up can never break the
    authentication response that is still in flight.
    """
    with guarded_write("the deletion of the expired user lockout state "
                       f"({state.resolver!r}, {state.uid!r}, {state.realm!r})"):
        get_ca_session().delete(state)


def _delete_ip_block(state: BlockList) -> None:
    """
    Delete a stale :class:`BlockList` row. The IP counterpart of
    :func:`_delete_user_lockout_state`: used by :func:`get_ip_block` to drop a
    timed block the auth pre-check finds already expired. Defensive — a failure is
    logged and rolled back so cleaning up can never break the authentication
    response that is still in flight.
    """
    with guarded_write(f"the deletion of the expired IP block {state.ip!r}"):
        get_ca_session().delete(state)


def _upsert_user_lockout_state(user: "User", *, lock_expires_at: datetime | None, stage_id: int) -> bool:
    """
    Create or update the :class:`UserLockoutState` row for *user*.

    The write is defensive: a failure is logged and rolled back so that writing
    the lockout state can never break the authentication response that already
    completed. An existing **permanent** lock is never downgraded to a timed
    lock.

    :return: whether the lock was written. ``False`` when the write failed, or when it was declined because a stronger
        (permanent) lock is already in force - the caller uses this to record the action in the history only if it
        actually changed something.
    """
    downgrade_declined = False
    with guarded_write(f"the user lockout state for {user!r}") as write:
        session = get_ca_session()
        state = session.get(UserLockoutState, (user.resolver, user.uid, user.realm))
        if state is None:
            state = UserLockoutState(resolver=user.resolver, uid=user.uid, realm=user.realm)
            session.add(state)
        elif state.lock_expires_at is None and lock_expires_at is not None:
            log.info(f"Not downgrading the existing permanent lock for {user!r} to a timed lock.")
            downgrade_declined = True
        if not downgrade_declined:
            state.username = user.login
            state.lock_expires_at = lock_expires_at
            state.last_stage_triggered = stage_id
    return write.succeeded and not downgrade_declined


def _upsert_ip_block(source_ip: str, *, block_expires_at: datetime | None, stage_id: int) -> bool:
    """
    Create or update the :class:`BlockList` row for *source_ip*.

    The IP counterpart of :func:`_upsert_user_lockout_state`: the write is
    defensive (a failure is logged and rolled back so that blocking an IP can
    never break the authentication response that already completed) and an
    existing **permanent** block is never downgraded to a timed one.

    Never-block IPs (loopback and the ``CONDITIONAL_ACCESS_NEVER_BLOCK`` config)
    are skipped: blocking shared infrastructure (a reverse proxy, NAT egress, or
    a load balancer) would lock out everyone behind it.

    :return: whether the block was written. ``False`` for a never-block IP, for a declined downgrade of a permanent
        block, and for a failed write - so the caller records the action in the history only if it did something.
    """
    if is_ip_never_block(source_ip):
        log.info(f"Not blocking IP {source_ip!r}: it is on the conditional-access never-block list.")
        return False
    downgrade_declined = False
    with guarded_write(f"the IP block for {source_ip!r}") as write:
        session = get_ca_session()
        state = session.get(BlockList, source_ip)
        if state is None:
            state = BlockList(ip=source_ip)
            session.add(state)
        elif state.block_expires_at is None and block_expires_at is not None:
            log.info(f"Not downgrading the existing permanent block for IP {source_ip!r} to a timed block.")
            downgrade_declined = True
        if not downgrade_declined:
            state.block_expires_at = block_expires_at
            state.last_stage_triggered = stage_id
    return write.succeeded and not downgrade_declined
