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

from privacyidea.lib import _
from privacyidea.lib.conditional_access.authentication_log import _naive_utc
from privacyidea.models import AuthenticationLog, BlockList, LockoutPolicy, UserLockoutState, db
from privacyidea.models.utils import utc_now

if TYPE_CHECKING:
    from privacyidea.lib.user import User

log = logging.getLogger(__name__)


class LockoutAction(str, Enum):
    """
    Action types a :class:`~privacyidea.models.lockout_policy.LockoutPolicyStage`
    can execute when its failure threshold is met.

    :attr:`LOCK_USER`, :attr:`PERMANENT_LOCK_USER`, :attr:`EMAIL_ADMIN`,
    :attr:`EMAIL_USER` and :attr:`BLOCK_IP` are post-response side effects
    executed by :func:`evaluate_lockout_policies`. :attr:`ALLOW` and
    :attr:`DENY` decide the *current* request and are therefore handled by the
    pre-auth decision step (:func:`evaluate_access_decision`) instead. The
    action table stores the string value, so the enum can grow without a
    schema change.

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


def get_ip_block(source_ip: str | None, now: datetime | None = None) -> dict | None:
    """
    Return information about *source_ip*'s **current** block by the ``BLOCK_IP``
    action, or ``None`` if the IP is not currently blocked. This is the IP
    counterpart of :func:`get_user_lockout` and is meant for the authentication
    pre-check hot path.

    Like :func:`get_user_lockout` it is a **pure read**: it never writes, so a
    stale ``is_blocked=True`` row whose ``block_expires_at`` lies in the past
    simply reads as *not blocked* (it is overwritten by the next block or by a
    cleanup job). A row with ``block_expires_at IS NULL`` is a permanent block.

    The remaining time is surfaced so the WebUI login (``/auth``) can tell the
    user how long the block lasts, just like the user lock (maskable via the
    ``hide_specific_error_message`` policy); the machine-facing ``/validate``
    endpoints keep the generic failure response.

    :param source_ip: the client IP to check; a falsy value is never blocked
    :param now: the reference time; defaults to :func:`utc_now`
    :return: ``None`` if not blocked, else a dict with keys ``permanent`` (bool),
        ``expires_at`` (naive-UTC :class:`datetime` or ``None`` if permanent) and
        ``seconds_remaining`` (whole seconds until a timed block expires, ``>= 0``,
        or ``None`` if permanent)
    """
    if not source_ip:
        return None
    state = db.session.get(BlockList, source_ip)
    if not state or not state.is_blocked:
        return None
    if state.block_expires_at is None:
        # Permanent block; only an admin reset clears it.
        return {"permanent": True, "expires_at": None, "seconds_remaining": None}
    now = _naive_utc(now) if now is not None else utc_now()
    if state.block_expires_at <= now:
        return None
    remaining = int((state.block_expires_at - now).total_seconds())
    return {"permanent": False, "expires_at": state.block_expires_at, "seconds_remaining": remaining}


def is_ip_blocked(source_ip: str | None, now: datetime | None = None) -> bool:
    """
    Return whether *source_ip* is currently blocked by the ``BLOCK_IP`` action.
    Thin boolean wrapper over :func:`get_ip_block` for the authentication
    pre-check hot path; see that function for the expiry and permanent-block
    semantics.

    :param source_ip: the client IP to check; a falsy value is never blocked
    :param now: the reference time; defaults to :func:`utc_now`
    :return: ``True`` if the IP is currently blocked
    """
    return get_ip_block(source_ip, now=now) is not None


def evaluate_access_decision(user: "User", source_ip: str | None = None,
                             now: datetime | None = None) -> "AccessDecision":
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
    its ``counter_type_to_track`` are counted over its window, and the
    highest-priority stage whose threshold is met supplies the decision. A
    ``DENY`` stage therefore rejects this single request without persisting any
    state — a stateless, self-healing reject that lifts on its own as the
    failures age out of the window (contrast the durable :attr:`LockoutAction.LOCK_USER`).
    A stage with ``failure_threshold`` 0 always matches, so an ``ALLOW`` stage at
    threshold 0 acts as a default-allow / allowlist exception.

    Policies are evaluated highest ``priority`` first and the first one that
    yields a decision wins, so a higher-priority ALLOW overrides a lower-priority
    DENY and vice versa. ``dry_run`` policies are logged but never enforced.

    Like the rest of the engine the decision is keyed on the resolved
    ``(resolver, uid, realm)`` user, so an unresolved user (unknown login,
    local admin) is never denied here. ``source_ip`` is accepted for signature
    symmetry with :func:`evaluate_lockout_policies` but is not evaluated:
    IP-scoped decisions (e.g. against password spraying) are not implemented.

    :param user: the authenticating user; an unresolved user yields ``CONTINUE``
    :param source_ip: the resolved client IP (reserved for IP-scoped decisions)
    :param now: the reference time; defaults to :func:`utc_now`
    :return: the :class:`AccessDecision` for this request
    """
    if not _resolved(user):
        return AccessDecision.CONTINUE
    now = _naive_utc(now) if now is not None else utc_now()
    policies = db.session.scalars(
        select(LockoutPolicy)
        .where(LockoutPolicy.enabled.is_(True))
        .order_by(LockoutPolicy.priority.desc())
    ).all()
    for policy in policies:
        decision = _policy_access_decision(policy, user, now)
        if decision is not None:
            return decision
    return AccessDecision.CONTINUE


def _policy_access_decision(policy: LockoutPolicy, user: "User",
                            now: datetime) -> "AccessDecision | None":
    """
    The ALLOW/DENY decision a single policy contributes pre-auth, or ``None`` if
    this policy does not decide the request (no stage met, the met stage carries
    only lockout-style actions, or the policy is in dry-run).
    """
    count = count_user_events(user.resolver, user.uid, user.realm,
                              policy.counter_type_to_track, policy.time_window_seconds, now=now)
    triggered_stage = next((stage for stage in policy.stages
                            if count >= stage.failure_threshold), None)
    if triggered_stage is None:
        return None
    decision = _stage_access_decision(triggered_stage)
    if decision is None:
        # The met stage only locks / emails / blocks; that is handled
        # post-response, not as a pre-auth decision.
        return None
    if policy.dry_run:
        log.info(f"[dry-run] policy {policy.name!r} would return {decision} for {user!r}: "
                 f"{count} {policy.counter_type_to_track} event(s) in "
                 f"{policy.time_window_seconds}s.")
        return None
    log.info(f"Policy {policy.name!r} returns access decision {decision} for {user!r}: "
             f"{count} {policy.counter_type_to_track} event(s) in {policy.time_window_seconds}s.")
    return decision


def _stage_access_decision(stage) -> "AccessDecision | None":
    """
    Extract the pre-auth ALLOW/DENY decision from a triggered stage's actions, or
    ``None`` if the stage carries no ALLOW/DENY action. If a stage is
    misconfigured with both, DENY wins (fail closed).
    """
    has_allow = False
    for action in stage.actions:
        try:
            action_type = LockoutAction(action.action_type)
        except ValueError:
            continue
        if action_type == LockoutAction.DENY:
            return AccessDecision.DENY
        if action_type == LockoutAction.ALLOW:
            has_allow = True
    return AccessDecision.ALLOW if has_allow else None


def evaluate_lockout_policies(user: "User", event_type, source_ip: str | None = None,
                              now: datetime | None = None) -> list[str]:
    """
    Evaluate every enabled lockout policy that tracks *event_type* and execute
    the actions of the triggered stage, if any. This runs post-response, *after*
    the request's ``authentication_log`` row has been written (so the count
    includes it).

    The persistent side effects (lock state) are consulted by the *next* inbound
    request via the pre-check. In addition, an executed ``EMAIL_*`` action yields
    a short user-facing notice (e.g. "Your administrator has been notified by
    email."); those notices are returned so the caller can surface them on the
    current response — the login screen shows them next to the rejection, exactly
    as it shows a lockout message. Any error is the caller's to swallow; this
    function itself only guards individual DB writes (see
    :func:`_upsert_user_lockout_state`).

    :param user: the authenticating user; ignored unless fully resolved
    :param event_type: the classified outcome of the request
        (:class:`AuthEventType`)
    :param source_ip: the resolved client IP; the ``BLOCK_IP`` action blocks it
    :param now: the reference time; defaults to :func:`utc_now`
    :return: the de-duplicated, order-preserving list of user-facing notices
        produced by executed actions (empty if nothing was triggered/notified)
    """
    if not event_type:
        return []
    if not _resolved(user):
        log.debug(f"Skipping lockout evaluation for unresolved user {user!r}.")
        return []
    now = _naive_utc(now) if now is not None else utc_now()
    event_type = str(event_type)
    policies = db.session.scalars(
        select(LockoutPolicy)
        .where(LockoutPolicy.enabled.is_(True),
               LockoutPolicy.counter_type_to_track == event_type)
        .order_by(LockoutPolicy.priority.desc())
    ).all()
    notices: list[str] = []
    for policy in policies:
        notices.extend(_evaluate_policy(policy, user, event_type, source_ip, now))
    # De-duplicate while preserving order: several policies tracking the same
    # user can emit the same notice in one request.
    seen: set[str] = set()
    unique: list[str] = []
    for notice in notices:
        if notice not in seen:
            seen.add(notice)
            unique.append(notice)
    return unique


def _evaluate_policy(policy: LockoutPolicy, user: "User", event_type: str,
                     source_ip: str | None, now: datetime) -> list[str]:
    """
    Evaluate a single policy: count the user's events over the policy window,
    find the highest-priority stage whose threshold is met, de-duplicate, then
    execute the stage's actions (or, in dry-run, only log them).

    :return: the user-facing notices produced by the executed actions (empty if
        no stage triggered, in dry-run, or when de-duplicated away).
    """
    window = policy.time_window_seconds
    count = count_user_events(user.resolver, user.uid, user.realm, event_type, window, now=now)

    # Stages are ordered highest-priority first by the relationship; the first
    # stage whose threshold is met wins, so the most severe matching stage is
    # picked when several thresholds are crossed.
    triggered_stage = next((stage for stage in policy.stages
                            if count >= stage.failure_threshold), None)
    if triggered_stage is None:
        return []

    if policy.dry_run:
        # Dry-run never reads or writes the de-dup state, so it logs on every
        # in-window request that would trip the stage.
        log.info(f"[dry-run] policy {policy.name!r} would trigger stage {triggered_stage.id} "
                 f"(threshold {triggered_stage.failure_threshold}) for {user!r}: "
                 f"{count} {event_type} event(s) in {window}s.")
        return []

    state = db.session.get(UserLockoutState, (user.resolver, user.uid, user.realm))
    if (state is not None and state.last_stage_triggered == triggered_stage.id
            and state.last_updated is not None
            and state.last_updated >= now - timedelta(seconds=window)):
        log.debug(f"De-dup: stage {triggered_stage.id} already triggered within the window for "
                  f"{user!r}; skipping actions.")
        return []

    log.info(f"Policy {policy.name!r} triggered stage {triggered_stage.id} "
             f"(threshold {triggered_stage.failure_threshold}) for {user!r}: "
             f"{count} {event_type} event(s) in {window}s.")
    tags = _base_action_tags(policy, triggered_stage, user, event_type, count, source_ip, now)
    return _execute_stage_actions(triggered_stage, user, source_ip, now, tags)


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


class _SafeFormatDict(dict):
    """A ``str.format_map`` mapping that leaves unknown ``{placeholders}`` as-is
    instead of raising ``KeyError``, so an admin's typo in a template never turns
    a notification into an exception."""

    def __missing__(self, key):
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


def _base_action_tags(policy: LockoutPolicy, stage, user: "User", event_type: str,
                      count: int, source_ip: str | None, now: datetime) -> dict:
    """
    Build the ``{tag}`` substitution context available to EMAIL_* templates. Only
    fields already loaded on the request are included here; the resolver-backed
    user attributes (email, givenname, surname) are added lazily in
    :func:`_send_lockout_email`, so a non-email action never triggers a resolver
    lookup.
    """
    return {
        "user": user.login,
        "username": user.login,
        "realm": user.realm or "",
        "resolver": user.resolver or "",
        "source_ip": source_ip or "",
        "client_ip": source_ip or "",
        "count": count,
        "threshold": stage.failure_threshold,
        "event_type": event_type,
        "stage_id": stage.id,
        "policy": policy.name,
        "time": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def _resolve_admin_recipients(recipient_group) -> list[str]:
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


def _login_notice(action_type: "LockoutAction", cfg: dict, render_tags: dict) -> str:
    """
    Build the short message shown to the user on the login screen once an
    ``EMAIL_*`` action has been sent, mirroring how a lockout rejection is
    surfaced. An admin can override it per action with a ``login_notice``
    template in ``action_value`` (``{tag}`` substitution applies); otherwise a
    default keyed by the action type is used. The wording never reveals the
    recipient address.
    """
    custom = cfg.get("login_notice")
    if custom:
        return _safe_format(str(custom), render_tags)
    if action_type == LockoutAction.EMAIL_USER:
        return _("A notification email has been sent to your email address.")
    return _("Your administrator has been notified by email.")


def _send_lockout_email(action_type: "LockoutAction", action, user: "User", tags: dict) -> str | None:
    """
    Send the EMAIL_ADMIN / EMAIL_USER notification for a triggered stage action.

    The ``action_value`` is a JSON object carrying ``smtp_identifier`` (the SMTP
    server configuration to use), ``subject`` and ``body`` (both rendered with
    ``{tag}`` substitution), an optional ``mimetype`` (``plain``/``html``), an
    optional ``login_notice`` (overrides the message surfaced on the login
    screen) and, for EMAIL_ADMIN, an optional ``recipient_group``. EMAIL_USER
    sends to the user's own email address. A missing field or a user without an
    email address is logged and skipped; this runs post-response and must never
    raise.

    :return: the user-facing login-screen notice if the email was sent, else
        ``None`` (misconfiguration, no recipient, or delivery failure).
    """
    cfg = action.action_value if isinstance(action.action_value, dict) else {}
    identifier = cfg.get("smtp_identifier") or cfg.get("identifier")
    subject, body = cfg.get("subject"), cfg.get("body")
    if not identifier or not subject or not body:
        log.warning(f"{action_type} action {action.id}: needs smtp_identifier, subject and body in "
                    f"action_value; skipping.")
        return

    # Resolver-backed attributes are fetched once, only now that an email is sent.
    info = user.info or {}
    render_tags = {**tags, "email": info.get("email") or "",
                   "givenname": info.get("givenname") or "", "surname": info.get("surname") or ""}

    if action_type == LockoutAction.EMAIL_USER:
        recipients = [info["email"]] if info.get("email") else []
        if not recipients:
            log.warning(f"EMAIL_USER action {action.id}: user {user!r} has no email address; skipping.")
            return
    else:  # EMAIL_ADMIN
        recipients = _resolve_admin_recipients(cfg.get("recipient_group"))
        if not recipients:
            log.warning(f"EMAIL_ADMIN action {action.id}: no recipients for "
                        f"recipient_group={cfg.get('recipient_group')!r}; skipping.")
            return

    from privacyidea.lib.smtpserver import send_email_identifier
    sent = send_email_identifier(identifier, recipients,
                                 _safe_format(str(subject), render_tags),
                                 _safe_format(str(body), render_tags),
                                 mimetype=cfg.get("mimetype", "plain"))
    if sent:
        log.info(f"{action_type} for {user!r} sent to {len(recipients)} recipient(s) via {identifier!r}.")
        return _login_notice(action_type, cfg, render_tags)
    log.warning(f"{action_type} for {user!r} could not be delivered via {identifier!r}.")
    return None


def _execute_stage_actions(stage, user: "User", source_ip: str | None, now: datetime,
                           tags: dict) -> list[str]:
    """
    Execute every action of a triggered stage. Each action is guarded
    independently: an unknown type, a misconfiguration, or a failing side effect
    (e.g. an unreachable mail server) is logged and skipped so it can never break
    the authentication flow or prevent the stage's other actions from running.

    :return: the user-facing notices produced by executed ``EMAIL_*`` actions
        (empty if the stage has no email action or none was delivered).
    """
    notices: list[str] = []
    for action in stage.actions:
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
                _upsert_user_lockout_state(user, is_locked=True,
                                           lock_expires_at=now + timedelta(seconds=duration),
                                           stage_id=stage.id)
            elif action_type == LockoutAction.PERMANENT_LOCK_USER:
                _upsert_user_lockout_state(user, is_locked=True, lock_expires_at=None, stage_id=stage.id)
            elif action_type in (LockoutAction.EMAIL_ADMIN, LockoutAction.EMAIL_USER):
                notice = _send_lockout_email(action_type, action, user, tags)
                if notice:
                    notices.append(notice)
            elif action_type == LockoutAction.BLOCK_IP:
                # Failures are counted per user, so this blocks the source IP
                # of the request that tripped a *per-user* policy. It does not
                # detect password spraying (failures from one IP across many
                # users); BLOCK_IP simply blocks the offending request's IP.
                if not source_ip:
                    log.warning(f"BLOCK_IP action {action.id} on stage {stage.id}: this request has "
                                f"no source IP; skipping.")
                    continue
                duration = _lock_duration_seconds(action.action_value)
                if duration is None:
                    log.warning(f"BLOCK_IP action {action.id} on stage {stage.id} has no valid duration "
                                f"({action.action_value!r}); skipping.")
                    continue
                _upsert_ip_block(source_ip, block_expires_at=now + timedelta(seconds=duration),
                                 stage_id=stage.id, reason=tags.get("policy"))
            elif action_type in (LockoutAction.ALLOW, LockoutAction.DENY):
                # ALLOW/DENY decide the current request pre-auth (see
                # evaluate_access_decision); they are not post-response side
                # effects, so there is nothing to do here.
                log.debug(f"{action_type} is a pre-auth access decision; skipping in the "
                          f"post-response engine.")
            else:
                log.info(f"Lockout action {action_type} is recognized but not implemented yet; skipping.")
        except Exception as ex:
            log.warning(f"Lockout action {action_type} (id {action.id}) on stage {stage.id} "
                        f"failed: {ex!r}; skipping.")
    return notices


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


def _upsert_ip_block(source_ip: str, *, block_expires_at: datetime | None, stage_id: int,
                     reason: str | None = None) -> None:
    """
    Create or update the :class:`BlockList` row for *source_ip*.

    The IP counterpart of :func:`_upsert_user_lockout_state`: the write is
    defensive (a failure is logged and rolled back so that blocking an IP can
    never break the authentication response that already completed) and an
    existing **permanent** block is never downgraded to a timed one.
    """
    try:
        state = db.session.get(BlockList, source_ip)
        if state is None:
            state = BlockList(ip=source_ip)
            db.session.add(state)
        elif state.is_blocked and state.block_expires_at is None and block_expires_at is not None:
            log.info(f"Not downgrading the existing permanent block for IP {source_ip!r} to a timed block.")
            return
        state.is_blocked = True
        state.block_expires_at = block_expires_at
        state.last_stage_triggered = stage_id
        state.reason = reason
        db.session.commit()
    except Exception as ex:
        log.warning(f"Failed to write the IP block for {source_ip!r}: {ex!r}")
        db.session.rollback()
