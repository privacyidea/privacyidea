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

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from privacyidea.lib.conditional_access.authentication_log import _naive_utc
from privacyidea.models import AuthenticationLog, LockoutPolicy, UserLockoutState, db
from privacyidea.models.utils import utc_now

if TYPE_CHECKING:
    from privacyidea.lib.user import User

log = logging.getLogger(__name__)


class LockoutAction(str, Enum):
    """
    Action types a :class:`~privacyidea.models.lockout_policy.LockoutPolicyStage`
    can execute when its failure threshold is met.

    Only :attr:`LOCK_USER` and :attr:`PERMANENT_LOCK_USER` are implemented in
    V1; the remaining members are reserved so the action table can grow without
    a schema change (the column stores the string value).

    ``str`` is used instead of ``StrEnum`` (3.11+) for compatibility with Python
    3.10, mirroring
    :class:`~privacyidea.lib.conditional_access.authentication_error_codes.AuthEventType`.
    """
    LOCK_USER = "LOCK_USER"
    PERMANENT_LOCK_USER = "PERMANENT_LOCK_USER"
    EMAIL_ADMIN = "EMAIL_ADMIN"
    EMAIL_USER = "EMAIL_USER"
    BLOCK_IP = "BLOCK_IP"
    ALLOW = "ALLOW"
    DENY = "DENY"

    def __str__(self) -> str:
        return self.value


def _resolved(user: "User") -> bool:
    """
    Return ``True`` only for a fully resolved user, i.e. one with a complete
    ``(resolver, uid, realm)`` identity tuple. The lockout state and the
    authentication-log count are both keyed by that tuple, so an unresolved user
    (e.g. ``USER_UNKNOWN``, which has ``uid=None``) is never counted or locked
    here.
    """
    return bool(user and user.uid and user.resolver and user.realm)


def count_user_events(resolver: str, uid: str, realm: str, event_type: str,
                      window_seconds: int, now: datetime | None = None) -> int:
    """
    Count the ``authentication_log`` rows for one user identity and event type
    within a sliding time window ending *now*.

    The ``WHERE`` column order matches the composite index
    ``ix_authlog_user_event_time`` so this is an index range scan.

    :param resolver: resolver name of the user
    :param uid: resolver-local user id
    :param realm: realm name of the user
    :param event_type: the :class:`AuthEventType` value to count
    :param window_seconds: width of the look-back window in seconds
    :param now: window end; defaults to :func:`utc_now`. An aware value is
        normalized to naive UTC to match the stored ``timestamp`` column.
    :return: the number of matching events
    """
    now = _naive_utc(now) if now is not None else utc_now()
    window_start = now - timedelta(seconds=window_seconds)
    stmt = (select(func.count())
            .select_from(AuthenticationLog)
            .where(AuthenticationLog.resolver == resolver,
                   AuthenticationLog.uid == uid,
                   AuthenticationLog.realm == realm,
                   AuthenticationLog.event_type == str(event_type),
                   AuthenticationLog.timestamp >= window_start))
    return db.session.scalar(stmt) or 0


def get_user_lockout(user: "User", now: datetime | None = None) -> dict | None:
    """
    Return information about *user*'s **current** lock, or ``None`` if the user
    is not currently locked. This is a **pure read** intended for the
    authentication pre-check hot path: it never writes, so a stale
    ``is_locked=True`` row whose ``lock_expires_at`` lies in the past simply
    reads as *not locked* (it is overwritten by the next lock or by a cleanup
    job).

    A row with ``lock_expires_at IS NULL`` is a permanent lock.

    :param user: the user to check; an unresolved user is never locked
    :param now: the reference time; defaults to :func:`utc_now`
    :return: ``None`` if not locked, else a dict with keys ``permanent`` (bool),
        ``expires_at`` (naive-UTC :class:`datetime` or ``None`` if permanent) and
        ``seconds_remaining`` (whole seconds until a timed lock expires, ``>= 0``,
        or ``None`` if permanent)
    """
    if not _resolved(user):
        return None
    state = db.session.get(UserLockoutState, (user.resolver, user.uid, user.realm))
    if not state or not state.is_locked:
        return None
    if state.lock_expires_at is None:
        # Permanent lock; only an admin reset clears it.
        return {"permanent": True, "expires_at": None, "seconds_remaining": None}
    now = _naive_utc(now) if now is not None else utc_now()
    if state.lock_expires_at <= now:
        return None
    remaining = int((state.lock_expires_at - now).total_seconds())
    return {"permanent": False, "expires_at": state.lock_expires_at, "seconds_remaining": remaining}


def is_user_locked(user: "User", now: datetime | None = None) -> bool:
    """
    Return whether *user* is currently locked. Thin boolean wrapper over
    :func:`get_user_lockout` for the authentication pre-check hot path; see that
    function for the expiry and permanent-lock semantics.

    :param user: the user to check; an unresolved user is never locked
    :param now: the reference time; defaults to :func:`utc_now`
    :return: ``True`` if the user is currently locked
    """
    return get_user_lockout(user, now=now) is not None


def evaluate_lockout_policies(user: "User", event_type, source_ip: str | None = None,
                              now: datetime | None = None) -> None:
    """
    Evaluate every enabled lockout policy that tracks *event_type* and execute
    the actions of the triggered stage, if any. This is step 5 of the
    authentication request workflow and runs *after* the request's
    ``authentication_log`` row has been written (so the count includes it).

    Side effects only — the result of this call is consulted by the *next*
    inbound request via the pre-check, never by the current response. Any error
    is the caller's to swallow; this function itself only guards individual DB
    writes (see :func:`_upsert_user_lockout_state`).

    :param user: the authenticating user; ignored unless fully resolved
    :param event_type: the classified outcome of the request
        (:class:`AuthEventType`)
    :param source_ip: the resolved client IP (reserved for IP-scoped actions)
    :param now: the reference time; defaults to :func:`utc_now`
    """
    if not event_type:
        return
    if not _resolved(user):
        log.debug(f"Skipping lockout evaluation for unresolved user {user!r}.")
        return
    now = _naive_utc(now) if now is not None else utc_now()
    event_type = str(event_type)
    policies = db.session.scalars(
        select(LockoutPolicy)
        .where(LockoutPolicy.enabled.is_(True),
               LockoutPolicy.counter_type_to_track == event_type)
        .order_by(LockoutPolicy.priority.desc())
    ).all()
    for policy in policies:
        _evaluate_policy(policy, user, event_type, source_ip, now)


def _evaluate_policy(policy: LockoutPolicy, user: "User", event_type: str,
                     source_ip: str | None, now: datetime) -> None:
    """
    Evaluate a single policy: count the user's events over the policy window,
    find the highest-priority stage whose threshold is met, de-duplicate, then
    execute the stage's actions (or, in dry-run, only log them).
    """
    window = policy.time_window_seconds
    count = count_user_events(user.resolver, user.uid, user.realm, event_type, window, now=now)

    # Stages are ordered highest-priority first by the relationship; the first
    # stage whose threshold is met wins, so the most severe matching stage is
    # picked when several thresholds are crossed.
    triggered_stage = next((stage for stage in policy.stages
                            if count >= stage.failure_threshold), None)
    if triggered_stage is None:
        return

    if policy.dry_run:
        # Dry-run never reads or writes the de-dup state, so it logs on every
        # in-window request that would trip the stage.
        log.info(f"[dry-run] policy {policy.name!r} would trigger stage {triggered_stage.id} "
                 f"(threshold {triggered_stage.failure_threshold}) for {user!r}: "
                 f"{count} {event_type} event(s) in {window}s.")
        return

    state = db.session.get(UserLockoutState, (user.resolver, user.uid, user.realm))
    if (state is not None and state.last_stage_triggered == triggered_stage.id
            and state.last_updated is not None
            and state.last_updated >= now - timedelta(seconds=window)):
        log.debug(f"De-dup: stage {triggered_stage.id} already triggered within the window for "
                  f"{user!r}; skipping actions.")
        return

    log.info(f"Policy {policy.name!r} triggered stage {triggered_stage.id} "
             f"(threshold {triggered_stage.failure_threshold}) for {user!r}: "
             f"{count} {event_type} event(s) in {window}s.")
    _execute_stage_actions(triggered_stage, user, source_ip, now)


def _lock_duration_seconds(action_value) -> int | None:
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


def _execute_stage_actions(stage, user: "User", source_ip: str | None, now: datetime) -> None:
    """
    Execute every action of a triggered stage. Unknown or not-yet-implemented
    action types are logged and skipped so a misconfiguration never breaks the
    authentication flow.
    """
    for action in stage.actions:
        try:
            action_type = LockoutAction(action.action_type)
        except ValueError:
            log.warning(f"Unknown lockout action type {action.action_type!r} on stage {stage.id}; skipping.")
            continue

        if action_type == LockoutAction.LOCK_USER:
            duration = _lock_duration_seconds(action.action_value)
            if duration is None:
                log.warning(f"LOCK_USER action {action.id} on stage {stage.id} has no valid duration "
                            f"({action.action_value!r}); skipping.")
                continue
            _upsert_user_lockout_state(user, is_locked=True,
                                       lock_expires_at=now + timedelta(seconds=duration),
                                       stage_id=stage.id)
        elif action_type == LockoutAction.PERMANENT_LOCK_USER:
            _upsert_user_lockout_state(user, is_locked=True, lock_expires_at=None, stage_id=stage.id)
        else:
            log.info(f"Lockout action {action_type} is recognized but not implemented in V1; skipping.")


def _upsert_user_lockout_state(user: "User", *, is_locked: bool,
                               lock_expires_at: datetime | None, stage_id: int) -> None:
    """
    Create or update the :class:`UserLockoutState` row for *user*.

    The write is defensive: a failure is logged and rolled back so that writing
    the lockout state can never break the authentication response that already
    completed. An existing **permanent** lock is never downgraded to a timed
    lock.
    """
    try:
        state = db.session.get(UserLockoutState, (user.resolver, user.uid, user.realm))
        if state is None:
            state = UserLockoutState(resolver=user.resolver, uid=user.uid, realm=user.realm)
            db.session.add(state)
        elif state.is_locked and state.lock_expires_at is None and lock_expires_at is not None:
            log.info(f"Not downgrading the existing permanent lock for {user!r} to a timed lock.")
            return
        state.is_locked = is_locked
        state.lock_expires_at = lock_expires_at
        state.last_stage_triggered = stage_id
        db.session.commit()
    except Exception as ex:
        log.warning(f"Failed to write the user lockout state for {user!r}: {ex!r}")
        db.session.rollback()
