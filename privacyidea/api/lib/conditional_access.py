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

* :func:`conditional_access_gate` guards ``/validate/*``. A machine-facing client is told whatever the stage that
  applied the restriction configured, and by default that is nothing at all - the reason then lives only in the
  audit log and in the request's authentication-log row, for the admin.
* :func:`conditional_access_login_gate` guards the JWT login ``/auth``. A human at the login screen is told what is
  in force, if an admin configured wording for it, instead of showing "Wrong credentials" for ten minutes. A lock
  already in force is described from its own row (:func:`_restriction_messages`); one written by the failure of this
  very login comes back rendered with the evaluation, so neither path has to read the other's work.

Both end in the same place - :func:`~privacyidea.lib.conditional_access.engine.evaluate_access_decision` and the
lock/block readers - and both classify their rejection in the authentication log, since that row is the only thing an
admin can filter for: the request is turned away before anything else logs an outcome for it.

TODO: both gates now say only what an admin opted into on the stage, but ``hide_specific_error_message`` discards it
on both - on ``/auth`` through :func:`~privacyidea.api.before_after.auth_error`, on ``/validate/*`` through the
postpolicy of the same name. That policy exists to suppress what privacyIDEA volunteers *by default*, so having it
also throw away wording an admin deliberately configured (silently, with nothing to say it happened) is the thing to
decouple. A separate issue, which is why the two gates are still separate functions with duplicated structure.
"""
import functools
import json
import logging
from collections.abc import Callable
from typing import Any

from flask import request, g, Response

from privacyidea.api.lib.utils import (GENERIC_AUTH_FAILURE, log_authentication, build_ca_context,
                                      send_result, get_optional_one_of)
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.engine import (get_user_lockout, get_ip_block, evaluate_access_decision,
                                                       render_error_message, AccessDecision, RestrictionStatus,
                                                       MessageKind, StageMessage)
from privacyidea.lib.conditional_access.request_context import get_ca_context
from privacyidea.lib.error import AuthError, Error
from privacyidea.lib.user import User

log = logging.getLogger(__name__)



# --- /validate/*: reject with the configured wording, or generically --------------------------------------------------

def conditional_access_precheck(user: User, log_rejection: bool = True) -> Response | None:
    """
    Reject a request pre-auth (before any token logic and before the failcounter /
    max_auth checks) when conditional-access policies forbid it. Returns the failure
    :class:`~flask.Response` to be returned to the client, or ``None`` to continue
    with the normal flow.

    The rejection says only what an admin configured on the stage that applied the
    restriction, and silence is the default: with no wording the response reveals
    nothing - not that the user is locked, that the source IP is blocked, or that a
    policy denied access - and is byte for byte the failure this endpoint returned
    before stage messages existed. Either way the real reason is recorded in the
    audit log and, for the admin, as this request's authentication-log row.

    A lock or block already in force rejects the request before the conditional-access
    DENY decision is evaluated, so an ALLOW cannot override them; every restriction in
    force that carries wording is reported, while the authentication log is classified
    by the binding one (:func:`_binding_event_type`). A DENY rejects this single request
    without persisting state, while ALLOW / CONTINUE fall through. ``g.client_ip`` is the
    source IP checked.

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

    def reject(event_type: AuthEventType, audit_info: str, message: str | None = None,
               other_info: dict | None = None) -> Response:
        """Classify the request in the authentication log (unless opted out) and return the failure."""
        if log_rejection:
            # Staged like any other event, so request teardown writes it; attempt_id resolves as usual, which links the
            # rejection into the attempt it refused to process when the request carries that transaction.
            log_authentication(event_type, request, user=user, other_info=other_info,
                               transaction_id=get_optional_one_of(request.all_data, ["transaction_id", "state"]))
        g.audit_object.log({"success": False, "info": audit_info})
        # Without a configured message the response keeps its empty detail, byte for byte what it has always been, so
        # a rejected request is indistinguishable from any other failure.
        return send_result(False, rid=2, details={"message": message} if message else {})

    lockout = get_user_lockout(user, clear_expired=True)
    ip_block = get_ip_block(g.client_ip, clear_expired=True)
    binding = _binding_event_type(lockout, ip_block)
    if binding:
        # Every restriction in force is reported; the event type follows the binding one, because the log
        # needs a single classification.
        if binding is AuthEventType.USER_LOCKED:
            log.info(f"Rejecting authentication for locked user {user!r}.")
        else:
            log.info(f"Rejecting authentication from blocked IP {g.client_ip!r}.")
        return reject(binding, _audit_reason(lockout, ip_block),
                      " ".join(_restriction_messages(lockout, ip_block)) or None,
                      _additional_event_types(binding, lockout, ip_block))
    decision = evaluate_access_decision(build_ca_context(user))
    # A DENY decision is part of this request's history, but no authentication-log row exists yet to record it against
    # (and a dry-run DENY lets the request continue, so its row comes later). The context holds the outcomes until the
    # request stages the event they belong to - which, for an enforced DENY, is the row written just below.
    get_ca_context().add_outcomes(decision.outcomes)
    if decision.decision == AccessDecision.DENY:
        log.info(f"Denying authentication for {user!r} by conditional-access policy.")
        return reject(AuthEventType.ACCESS_DENIED, "Rejected: denied by conditional-access policy",
                      render_error_message(decision.error_message))
    return None


def compose_failure_message(existing: str | None, messages: list[StageMessage]) -> str | None:
    """
    What a failed authentication should say, given what conditional access just did to it.

    A restriction *replaces* the reason: the request may well have carried a wrong password, but the lock now in
    force is the more useful thing to tell the user. A stage that only notified is *appended* instead, because
    the credential failure is still why the request was refused. ``None`` when there is nothing to add, leaving
    the caller's own wording alone.
    """
    if not messages:
        return None
    joined = " ".join(message.text for message in messages)
    if any(message.kind is not MessageKind.NOTIFICATION for message in messages):
        return joined
    return f"{existing.rstrip('.')}. {joined}" if existing else joined


def surface_conditional_access_message(request, response):
    """
    Response hook that reports on a failed authentication what conditional access just did to it.

    Registered with ``postrequest``, not ``postpolicy``: nothing here is policy-driven, it runs on every failed
    response. That decorator lives in ``api.lib.postpolicy`` despite the name, and ``sign_response`` uses it the
    same way - a pre-existing misfiling, not a hint that this is a policy.

    Without this the engine runs at request teardown, after the body is built, so the request that *trips* a
    stage would still be answered with the ordinary failure ("wrong otp pin") while every later one carried
    the stage's wording. The lock is written, and any ``EMAIL_*`` action is sent, during this very request -
    so this is the response that should say so, exactly as ``/auth`` already does.

    Running the evaluation here does not duplicate the one at teardown: it is guarded per classification
    (``ConditionalAccessContext.run_post_eval``), so whichever runs first does the work and the other returns
    nothing. Both are needed. Only this one can shape the body, because teardown runs after the response is
    built; and only teardown is guaranteed, because a decorator is skipped entirely when the view raises and an
    error handler builds the response instead. The flush first is what makes this request's own event part of
    the count. A restriction now in force replaces the message, since it is the more useful thing to say; a stage
    that only notified is appended to whatever the failure already reported, because the credential failure is
    still the reason it was refused.
    """
    if not response or not response.is_json:
        return response
    content = response.json
    if content.get("result", {}).get("value"):
        # A success has nothing to report: the message is only ever shown on a failed authentication.
        return response
    try:
        context = get_ca_context()
        context.flush()
        # Everything in force was written by this request - anything already in force was refused by the
        # pre-check, which returns its own response - so the evaluation is the whole story and nothing has to
        # be read back. A request the pre-check did refuse still passes through here, since it returns rather
        # than raises and this hook wraps it; run_post_eval declines to evaluate its own rejections, so there
        # is nothing to compose and the gate's wording is left alone.
        message = compose_failure_message(content.get("detail", {}).get("message"), context.run_post_eval())
        if message:
            detail = content.get("detail") or {}
            detail["message"] = message
            content["detail"] = detail
            response.set_data(json.dumps(content))
    except Exception as ex:
        # Never break an authentication response over the wording of its own rejection.
        log.warning(f"Could not surface the conditional-access message on this response: {ex!r}")
    return response


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

def _restriction_message(restriction: RestrictionStatus) -> str | None:
    """
    The wording to show for *restriction*, or ``None`` to stay generic.

    Nothing is volunteered: privacyIDEA never says that an account is locked or an address blocked unless an admin
    wrote that message on the stage that applied it. The text is stored on the restriction itself, so it survives the
    policy being edited or deleted; ``{duration}`` is substituted against the time left right now.
    """
    return render_error_message(restriction.error_message, restriction)


def _binding_event_type(lockout: RestrictionStatus | None,
                        ip_block: RestrictionStatus | None) -> AuthEventType | None:
    """
    How a request refused by both a lock and a block is classified: by the restriction that lasts longest, a
    permanent one outranking any timed one. On a tie the user lock wins, matching the lock-before-block order
    of the pre-check.

    Needed because the authentication log records one ``event_type`` per request - the value an admin filters
    on - so one of the two has to stand for the refusal. What the *user* is told is a separate question with a
    separate answer: every restriction that carries wording is reported (:func:`_restriction_messages`).

    :param lockout: the :class:`RestrictionStatus` from :func:`get_user_lockout`, or ``None``
    :param ip_block: the :class:`RestrictionStatus` from :func:`get_ip_block`, or ``None``
    :return: the :class:`AuthEventType` to file the refusal under, or ``None`` if neither is in force
    """

    def _remaining_time(state: RestrictionStatus | None) -> float | None:
        if not state:
            return None
        return float("inf") if state.permanent else state.seconds_remaining

    lock_remaining = _remaining_time(lockout)
    block_remaining = _remaining_time(ip_block)
    if lock_remaining is None and block_remaining is None:
        return None
    if block_remaining is not None and (lock_remaining is None or block_remaining > lock_remaining):
        return AuthEventType.IP_BLOCKED
    return AuthEventType.USER_LOCKED


def _audit_reason(lockout: RestrictionStatus | None, ip_block: RestrictionStatus | None) -> str:
    """
    Why this request was refused, for the audit log: every restriction in force, and whether each is permanent.

    Unlike the authentication log's single ``event_type`` this is free text, so it does not have to choose - and
    the admin reading it is the one person who should see the whole picture rather than the binding half of it.
    """
    parts = []
    if lockout is not None:
        parts.append("account is permanently locked" if lockout.permanent else "account is temporarily locked")
    if ip_block is not None:
        parts.append("source IP is permanently blocked" if ip_block.permanent else "source IP is temporarily blocked")
    return f"Rejected: {' and '.join(parts)}"


def _additional_event_types(binding: AuthEventType, lockout: RestrictionStatus | None,
                            ip_block: RestrictionStatus | None) -> dict | None:
    """
    The event types the row could not record, for the entry's ``other_info``.

    The authentication log holds one classification per request, so a request refused by both a lock and a
    block is filed under whichever binds (:func:`_binding_event_type`) - and the other would otherwise leave no
    trace on the row at all, while the user was told about both. Recording it here keeps the row honest: it is
    not queryable the way ``event_type`` is, but an admin reading the entry sees the whole reason.

    :return: ``{"additional_event_types": [...]}`` when more than one restriction is in force, else ``None``
    """
    if lockout is None or ip_block is None:
        return None
    other = AuthEventType.IP_BLOCKED if binding is AuthEventType.USER_LOCKED else AuthEventType.USER_LOCKED
    return {"additional_event_types": [str(other)]}


def _restriction_messages(lockout: RestrictionStatus | None,
                          ip_block: RestrictionStatus | None) -> list[str]:
    """
    The wording of every restriction in force, most severe first, skipping those that carry none.

    Both are reported rather than only the binding one. They are independent facts - an account lock and an
    address block are resolved differently - so telling the user about one leaves them to discover the other by
    failing again.
    """
    ordered = sorted((state for state in (lockout, ip_block) if state is not None),
                     key=lambda state: 0 if state.permanent else 1)
    return [message for message in (_restriction_message(state) for state in ordered) if message]


def _raise_restricted(lockout: RestrictionStatus | None, ip_block: RestrictionStatus | None) -> None:
    """
    Refuse this login because a restriction is in force, telling the user what every restriction that carries
    wording says (see :func:`_restriction_messages`). With no wording at all the rejection is the ordinary
    wrong-credentials failure, so a locked account is indistinguishable from a wrong password.
    """
    messages = _restriction_messages(lockout, ip_block)
    raise AuthError(" ".join(messages) if messages else GENERIC_AUTH_FAILURE, id=Error.AUTHENTICATE_WRONG_CREDENTIALS)


def _reject_restricted_login(user: User) -> None:
    """
    Reject an ``/auth`` login pre-auth (before any credential check) when conditional-access policies forbid it.
    Raises :class:`AuthError` when the request must be rejected and returns ``None`` otherwise.

    A currently-locked user or a blocked source IP is rejected first. The rejection says whatever wording the admin
    configured for the restrictions in force - every one of them, so a user facing both a lock and a block is not left
    to discover the second by failing again - and stays generic when none carries any. An unresolved user / local DB
    admin has no ``(resolver, uid, realm)`` identity tuple and is therefore never locked.

    The pre-auth conditional-access DENY decision is evaluated after the lock/block pre-checks so an ALLOW cannot
    override them. A DENY rejects this single login with the deciding stage's wording, or generically without one.
    ALLOW / CONTINUE fall through silently.

    Every rejection also classifies the login in the authentication log (``USER_LOCKED`` / ``IP_BLOCKED`` /
    ``ACCESS_DENIED``), which is the only place an admin can filter for the reason: the login is turned away before
    anything else logs an outcome for it. With both a lock and a block in force the event type follows the binding one
    (:func:`_binding_event_type`), since the log records one classification per request. ``internal_admin`` comes
    from the flag ``before_request`` already resolved, so a blocked local admin is recorded as ``admin-internal``
    rather than falling back to ``user``.
    """
    lockout = get_user_lockout(user, clear_expired=True)
    ip_block = get_ip_block(g.client_ip, clear_expired=True)
    binding = _binding_event_type(lockout, ip_block)

    def log_rejection(event_type: AuthEventType, other_info: dict | None = None) -> None:
        """Classify this login in the authentication log. Staged, so request teardown writes it even though the
        AuthError below unwinds the view."""
        log_authentication(event_type, request, user=user, other_info=other_info,
                           internal_admin=g.get("resolved_user", {}).get("is_local_admin", False))

    if binding:
        if binding is AuthEventType.USER_LOCKED:
            log.info(f"Rejecting /auth login for locked user {user!r}.")
        else:
            log.info(f"Rejecting /auth login from blocked IP {g.client_ip!r}.")
        g.audit_object.log({"info": _audit_reason(lockout, ip_block)})
        log_rejection(binding, _additional_event_types(binding, lockout, ip_block))
        _raise_restricted(lockout, ip_block)
    decision = evaluate_access_decision(build_ca_context(user))
    # The decision belongs to this request's history, but its authentication-log row does not exist yet: the context
    # keeps the outcomes until the login stages its event (a dry-run DENY lets the login continue and land on that row).
    get_ca_context().add_outcomes(decision.outcomes)
    if decision.decision == AccessDecision.DENY:
        log.info(f"Denying /auth login for {user!r} by conditional-access policy.")
        g.audit_object.log({"info": "Rejected: denied by conditional-access policy"})
        # Staged after add_outcomes above, so this is the row the buffered DENY outcome is recorded against.
        log_rejection(AuthEventType.ACCESS_DENIED)
        # A DENY persists nothing, so its wording comes straight off the deciding stage. Without one the
        # rejection is indistinguishable from any other failed login, which is the point.
        raise AuthError(render_error_message(decision.error_message) or GENERIC_AUTH_FAILURE,
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
