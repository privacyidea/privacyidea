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
"""
The API-layer conditional-access gates: what turns an inbound request away before any credential check, for both
authenticating entry points, plus the messages that tell a human why.

There is one gate per entry point because they reject differently, not because they decide differently:

* :func:`conditional_access_gate` guards ``/validate/*``. A machine-facing client gets a generic failure that leaks
  no reason at all - the reason lives in the audit log and in the request's authentication-log row, for the admin.
* :func:`conditional_access_login_gate` guards the JWT login ``/auth``. A human at the login screen is told what is
  in force and roughly how long it lasts, so the WebUI can explain the wait instead of showing "Wrong credentials"
  for ten minutes. That is also why the message builders live here: the same lock must be described identically
  whether it refused the login up front or was written by the failure of this very login
  (:func:`login_restriction`).

Both end in the same place - :func:`~privacyidea.lib.conditional_access.engine.evaluate_access_decision` and the
lock/block readers - and both classify their rejection in the authentication log, since that row is the only thing an
admin can filter for: the request is turned away before anything else logs an outcome for it.

TODO: the two should not differ in *whether* they explain themselves. Surfacing the reason belongs under an explicit
policy of its own, settable per endpoint, rather than being hard-coded per entry point as it is here - ``/auth``
already has ``hide_specific_error_message`` (applied to its :class:`AuthError` by
:func:`~privacyidea.api.before_after.auth_error`) while ``/validate/*`` has no way to opt *in*. Unifying that is a
separate issue, which is why the two gates are still separate functions with duplicated structure.
"""
import functools
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from flask import request, g, Response
from flask_babel import _

from privacyidea.api.lib.utils import (log_authentication, build_ca_context, send_result, get_optional_one_of)
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.engine import (get_user_lockout, get_ip_block, evaluate_access_decision,
                                                      AccessDecision, RestrictionStatus, is_user_locked, is_ip_blocked)
from privacyidea.lib.conditional_access.request_context import get_ca_context
from privacyidea.lib.error import AuthError, Error
from privacyidea.lib.user import User

log = logging.getLogger(__name__)


# --- /validate/*: reject generically, leaking no reason -------------------------------------------------------------

def conditional_access_precheck(user: User, log_rejection: bool = True) -> Response | None:
    """
    Reject a request pre-auth (before any token logic and before the failcounter /
    max_auth checks) when conditional-access policies forbid it. Returns a generic
    failure :class:`~flask.Response` to be returned to the client, or ``None`` to
    continue with the normal flow.

    The rejection is deliberately generic and leaks no reason: the machine-facing
    API response never reveals that the user is locked, the source IP is blocked,
    or a policy denied access — the real reason is recorded in the audit log and,
    for the admin, as this request's authentication-log row.

    A currently-locked user is rejected first, then a source IP blocked by a
    ``BLOCK_IP`` action. The pre-auth conditional-access DENY decision is evaluated
    last, after the lock/block pre-checks (so an ALLOW cannot override them); a
    DENY rejects this single request without persisting state, while
    ALLOW / CONTINUE fall through. ``g.client_ip`` is the source IP checked.

    Each rejection also **classifies the request** in the authentication log
    (:class:`~privacyidea.lib.conditional_access.authentication_event_types.AuthEventType`:
    ``USER_LOCKED`` / ``IP_BLOCKED`` / ``ACCESS_DENIED``), because the reason is otherwise nowhere an admin can filter
    for: the request is turned away before anything else logs an outcome for it.

    :param user: the identity to gate on
    :param log_rejection: write that authentication-log row. A rejection row **replaces** the row the request would
        have written anyway and must never create one where there would be none, so a caller whose endpoint logs no
        authentication event when it succeeds passes ``False``. Exactly one does: ``/validate/polltransaction``, where
        a poll carries no new authentication event and the response is generic - so a client polling in a loop cannot
        tell why it fails and would otherwise fill the log at its polling frequency.
    """

    def reject(event_type: AuthEventType, audit_info: str) -> Response:
        """Classify the request in the authentication log (unless opted out) and return the generic failure."""
        if log_rejection:
            # Staged like any other event, so teardown writes it, and attempt_id still links this rejection into the
            # attempt it refused when the request carries a transaction id.
            log_authentication(event_type, request, user=user,
                               transaction_id=get_optional_one_of(request.all_data, ["transaction_id", "state"]))
        g.audit_object.log({"success": False, "info": audit_info})
        return send_result(False, rid=2, details={})

    if is_user_locked(user, clear_expired=True):
        log.info(f"Rejecting authentication for locked user {user!r}.")
        return reject(AuthEventType.USER_LOCKED, "Rejected: account is temporarily locked")
    if is_ip_blocked(g.client_ip, clear_expired=True):
        log.info(f"Rejecting authentication from blocked IP {g.client_ip!r}.")
        return reject(AuthEventType.IP_BLOCKED, "Rejected: source IP is blocked")
    decision = evaluate_access_decision(build_ca_context(user))
    # The DENY decision belongs to this request's history before any log row exists, so the context buffers its outcomes
    # until the request stages an event - the row written just below for an enforced DENY, or a later row if this is a
    # dry run that lets the request continue.
    get_ca_context().add_outcomes(decision.outcomes)
    if decision.decision == AccessDecision.DENY:
        log.info(f"Denying authentication for {user!r} by conditional-access policy.")
        return reject(AuthEventType.ACCESS_DENIED, "Rejected: denied by conditional-access policy")
    return None


def conditional_access_gate(identity_resolver: Callable[[], User] | None = None,
                            log_rejection: bool = True) -> Callable[[Callable], Callable]:
    """
    View decorator that runs :func:`conditional_access_precheck` before the
    decorated endpoint body (and, when placed above them, before the endpoint's
    pre-policies). If the pre-check rejects the request, its generic-failure
    response is returned immediately and the endpoint never runs.

    :param identity_resolver: an optional zero-argument callable returning the
        :class:`~privacyidea.lib.user.User` the pre-check should gate on. When
        omitted, ``request.User`` is used. Endpoints that must resolve the
        identity differently (a serial/credential-id request, or a transaction
        owner) pass their own resolver.
    :param log_rejection: passed through to the pre-check; see there for when an
        endpoint has to opt out.
    """
    def decorator(wrapped_function: Callable) -> Callable:
        @functools.wraps(wrapped_function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = identity_resolver() if identity_resolver is not None else request.User
            rejection = conditional_access_precheck(user, log_rejection=log_rejection)
            if rejection is not None:
                return rejection
            return wrapped_function(*args, **kwargs)
        return wrapper
    return decorator


# --- /auth: a rejection that explains itself ------------------------------------------------------------------------

def _lockout_error_message(lockout: RestrictionStatus) -> str:
    """
    Build the user-facing message for a login rejected by the conditional-access
    lockout. *lockout* is the :class:`RestrictionStatus` returned by
    :func:`~privacyidea.lib.conditional_access.engine.get_user_lockout`: a
    permanent lock points the user at the administrator, a timed lock states the
    approximate remaining time (rounded up to whole minutes, at least one).
    """
    if lockout.permanent:
        return _("Your account has been permanently locked. Please contact your administrator.")
    # Ceiling remaining minutes
    minutes = max(1, -(-lockout.seconds_remaining // 60))
    return _("Your account is temporarily locked due to too many failed login attempts. "
             "Please try again in about {minutes} minute(s).").format(minutes=minutes)


def _blocked_ip_error_message(client_ip: str | None, block: RestrictionStatus) -> str:
    """
    Build the user-facing message for a login rejected because the source IP is
    blocked by a conditional-access ``BLOCK_IP`` action. *block* is the
    :class:`RestrictionStatus` returned by
    :func:`~privacyidea.lib.conditional_access.engine.get_ip_block`:
    a permanent block points the user at the administrator, a timed block states
    the approximate remaining time (rounded up to whole minutes, at least one).
    """
    if block.permanent:
        return _("Authentication failure. Your IP ({ip}) has been permanently blocked. "
                 "Please contact your administrator.").format(ip=client_ip)
    # Ceiling remaining minutes
    minutes = max(1, -(-block.seconds_remaining // 60))
    return _("Authentication failure. Your IP ({ip}) has been blocked. "
             "Please try again in about {minutes} minute(s).").format(ip=client_ip, minutes=minutes)


def _restriction_kind(state: RestrictionStatus) -> str:
    """
    Classify a lock/block as ``"permanent"`` or ``"temporary"`` for the WebUI.

    Surfaced in the rejection's ``detail`` so the login screen can style a
    permanent (only-an-admin-can-clear-it) restriction differently from a
    recoverable timed one. It is a coarse hint, not the specific message, and is
    dropped when the ``hide_specific_error_message`` policy is active (see
    :func:`~privacyidea.api.before_after.auth_error`), so it never leaks more than
    the message itself would.
    """
    return "permanent" if state.permanent else "temporary"


def _binding_restriction(lockout: RestrictionStatus | None, ip_block: RestrictionStatus | None) -> str | None:
    """
    When both a user lockout and a source-IP block are in force, decide which one
    to report to the user. The binding constraint is the one that lasts longest (a
    permanent restriction outranks any timed one), so that is what we surface:
    telling a permanently-blocked user to "try again in 1 minute" because a shorter
    user lock also happens to be active would be misleading. This is exactly the
    case when a temporary lock escalates into a permanent IP block on the same
    request. On a tie the user lock wins, matching the lock-before-block order of
    the pre-check.

    :param lockout: the :class:`RestrictionStatus` from :func:`get_user_lockout`, or ``None``
    :param ip_block: the :class:`RestrictionStatus` from :func:`get_ip_block`, or ``None``
    :return: ``"lock"`` or ``"block"`` for the restriction to report, or ``None``
        if neither is in force
    """

    def _remaining(state: RestrictionStatus | None) -> float | None:
        if not state:
            return None
        return float("inf") if state.permanent else state.seconds_remaining

    lock_rem = _remaining(lockout)
    block_rem = _remaining(ip_block)
    if lock_rem is None and block_rem is None:
        return None
    if block_rem is not None and (lock_rem is None or block_rem > lock_rem):
        return "block"
    return "lock"


@dataclass(frozen=True)
class LoginRestriction:
    """
    How a login refused by a conditional-access restriction is described to the user.

    :ivar message: the user-facing reason, naming the restriction and how long it lasts.
    :ivar kind: the coarse severity hint for the WebUI, see :func:`_restriction_kind`.
    """
    message: str
    kind: str


def login_restriction(user: User, client_ip: str | None) -> LoginRestriction | None:
    """
    How to describe the lock or block in force *now*, or ``None`` if neither is.

    Used on the failed-credentials path, after the engine has evaluated this login: when the login that just failed is
    what tripped the stage, the lock or block it wrote is already in force, and saying so is more useful than "Wrong
    credentials". A pure read - unlike the pre-auth gate it does not clear a stale row, because the engine has just
    written this one.
    """
    lockout = get_user_lockout(user)
    ip_block = get_ip_block(client_ip)
    restriction = _binding_restriction(lockout, ip_block)
    if restriction == "block":
        return LoginRestriction(_blocked_ip_error_message(client_ip, ip_block), _restriction_kind(ip_block))
    if restriction == "lock":
        return LoginRestriction(_lockout_error_message(lockout), _restriction_kind(lockout))
    return None


def _reject_restricted_login(user: User) -> None:
    """
    Reject an ``/auth`` login pre-auth (before any credential check) when conditional-access policies forbid it.
    Raises :class:`AuthError` when the request must be rejected and returns ``None`` otherwise.

    A currently-locked user or a blocked source IP is rejected first. The rejection states the restriction (how long it
    lasts, or that it is permanent) so the user understands why login fails. An unresolved user / local DB admin has no
    ``(resolver, uid, realm)`` identity tuple and is therefore never locked. When both apply (e.g. a temporary lock
    that escalated into a permanent IP block), the longer-lasting one is surfaced so we never tell a
    permanently-blocked user to "try again in a minute".

    The pre-auth conditional-access DENY decision is evaluated after the lock/block pre-checks so an ALLOW cannot
    override them. A DENY rejects this single login with a message stating it was a conditional-access decision (the
    policy is not named). ALLOW / CONTINUE fall through silently.

    Every rejection also classifies the login in the authentication log (``USER_LOCKED`` / ``IP_BLOCKED`` /
    ``ACCESS_DENIED``), which is the only place an admin can filter for the reason: the login is turned away before
    anything else logs an outcome for it. The event type follows the restriction actually reported, so the log and the
    message a user saw cannot disagree. ``internal_admin`` comes from the flag ``before_request`` already resolved, so
    a blocked local admin is recorded as ``admin-internal`` rather than falling back to ``user``.
    """
    lockout = get_user_lockout(user, clear_expired=True)
    ip_block = get_ip_block(g.client_ip, clear_expired=True)
    restriction = _binding_restriction(lockout, ip_block)

    def log_rejection(event_type: AuthEventType) -> None:
        """Classify this login in the authentication log. Staged, so request teardown writes it even though the
        AuthError below unwinds the view."""
        log_authentication(event_type, request, user=user,
                           internal_admin=g.get("resolved_user", {}).get("is_local_admin", False))

    if restriction == "block":
        log.info(f"Rejecting /auth login from blocked IP {g.client_ip!r}.")
        g.audit_object.log({"info": "Rejected: source IP is blocked"})
        log_rejection(AuthEventType.IP_BLOCKED)
        raise AuthError(_blocked_ip_error_message(g.client_ip, ip_block),
                        id=Error.AUTHENTICATE_WRONG_CREDENTIALS,
                        details={"restriction": _restriction_kind(ip_block)})
    if restriction == "lock":
        log.info(f"Rejecting /auth login for locked user {user!r}.")
        g.audit_object.log({"info": "Rejected: account is temporarily locked"})
        log_rejection(AuthEventType.USER_LOCKED)
        raise AuthError(_lockout_error_message(lockout),
                        id=Error.AUTHENTICATE_WRONG_CREDENTIALS,
                        details={"restriction": _restriction_kind(lockout)})
    decision = evaluate_access_decision(build_ca_context(user))
    # The decision belongs to this request's history before its log row exists, so the context keeps its outcomes until
    # the login stages an event; a dry-run DENY lets the login continue and lands on that later row.
    get_ca_context().add_outcomes(decision.outcomes)
    if decision.decision == AccessDecision.DENY:
        log.info(f"Denying /auth login for {user!r} by conditional-access policy.")
        g.audit_object.log({"info": "Rejected: denied by conditional-access policy"})
        # Staged after add_outcomes above, so this is the row the buffered DENY outcome is recorded against.
        log_rejection(AuthEventType.ACCESS_DENIED)
        raise AuthError(_("Authentication failure. Access has been denied by a conditional-access policy."),
                        id=Error.AUTHENTICATE_WRONG_CREDENTIALS)


def conditional_access_login_gate() -> Callable[[Callable], Callable]:
    """
    View decorator that refuses a restricted ``/auth`` login before the view body and before every other decorator
    listed below it.

    It has to be a decorator rather than the first statement of the view, because the pre-policies run before the view
    body and one of them writes an authentication-log row: a tripped ``auth_timelimit`` logs a *trackable*
    NOT_AUTHORIZED (see :func:`~privacyidea.api.lib.prepolicy.auth_timelimit`). Checked from inside the view, the lock
    would be applied only after that row existed, so a locked user's rejected logins would keep feeding the very
    counters that locked them - the one path by which a lock could refresh itself. **Keep it listed above the
    pre-policies**; decorators run top-down, and that ordering is the whole point.

    Deliberately not a ``@prepolicy``: this is not a policy function and has no ``action`` to evaluate - it gates the
    request rather than enriching ``request.all_data`` from a policy, which is what the pre-policy contract is for.

    The audit subject is logged here, not in the view: a login this rejects never reaches the view, and an audit entry
    naming no user would not say *who* was turned away.

    Everything it reads is ready by then - ``/auth``'s ``before_request`` sets ``g.audit_object``, ``g.client_ip`` and
    ``g.resolved_user`` and resolves ``request.User`` - and the :class:`AuthError` it raises is handled by the
    ``jwtauth`` error handler exactly as one raised from the view would be.
    """

    def decorator(wrapped_function: Callable) -> Callable:
        @functools.wraps(wrapped_function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = request.User or User()
            g.audit_object.log({"user": user.login, "realm": user.realm})
            _reject_restricted_login(user)
            return wrapped_function(*args, **kwargs)

        return wrapper

    return decorator
