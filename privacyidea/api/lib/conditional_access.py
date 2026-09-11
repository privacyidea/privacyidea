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

Both entry points **decide** identically - :func:`_evaluate_rejection` is the whole decision - and differ only in how a
rejection reaches the client:

* :func:`conditional_access_gate` guards ``/validate/*`` and **returns** the rejection as a :class:`~flask.Response`:
  an ordinary ``200`` carrying ``result.value`` false and no error object, like any other failed authentication there.
* :func:`conditional_access_login_gate` guards the JWT login ``/auth`` and **raises** an :class:`AuthError` the login
  screen renders, so a human is told what is in force instead of "Wrong credentials" for ten minutes. Its id is
  :attr:`~privacyidea.lib.error.Error.AUTHENTICATE` (``403``). An ``AuthError`` needs some message, so
  with nothing configured it falls back to the generic failure rather than to silence.
* :func:`conditional_access_rejection` serves the caller that can do neither, ``/ttype/push``, which hands its result
  back as a ``(bool, dict)`` pair and renders the answer itself.

Silent is the default on all three: a rejection says what an admin configured on the triggering stage, and with
nothing configured only what every other failed authentication says.

What "like any other failed authentication" *is* differs per endpoint, which is the one thing a gate has to hand on:
each passes a :class:`RejectionShape` saying how its endpoint answers a refusal, down to the fields the endpoint
does not have. ``/ttype/push`` is where that bites: it renders
with ``rid`` 1, so it reports no ``authentication`` verdict, and an ordinary failed answer there carries no
``detail`` at all, so a silent rejection carries none either - the opposite of ``/validate/*``, where every failure
has one and a silent rejection needs the generic message to have one too.

Only a request refused *here*, before its credentials are checked, is told anything at all. The post-response
evaluation reports nothing: a request that trips a stage gets the answer it had coming - its own failure, its own
challenge, its own success - and the restriction it wrote applies from the next request, which these gates then
refuse. A lock therefore reaches a user in one shape only, and a silent one is not detectable at the moment it
trips.

Both classify their rejection in the authentication log, since that row is the only thing an admin can filter for: the
request is turned away before anything else logs an outcome for it. Both link it to the transaction the request
carries, if any, so the rejection lands on the attempt it refused to process. ``/auth`` additionally records the
``internal_admin`` flag, being the only entry point where a local admin authenticates.

``hide_specific_error_message`` and ``no_detail_on_fail`` do not discard a configured message. Those actions suppress
what privacyIDEA volunteers *by default* - which factor failed, why the token refused; a conditional-access message is
the opposite, since an admin either wrote it or turned it on by policy. So a gate claims its error message
(:meth:`~privacyidea.lib.conditional_access.request_context.ConditionalAccessContext.claim_message`) and all three
places that would otherwise mask it read it back through
:func:`~privacyidea.lib.conditional_access.request_context.claimed_ca_message`:
:func:`~privacyidea.api.before_after.auth_error` on ``/auth``, and both actions on ``/validate/*``. Only the message
survives; the rest of the detail is collapsed, which is what those actions are for and costs a rejection nothing.
"""
import functools
import logging
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from flask import request, g, Response

from privacyidea.api.lib.utils import (GENERIC_AUTH_FAILURE, log_authentication, build_ca_context,
                                      send_result, get_optional_one_of)
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.engine import (get_user_lock, get_ip_block, evaluate_access_decision,
                                                       render_error_message, restriction_messages, AccessDecision,
                                                       ConditionalAccessAction, RestrictionStatus)
from privacyidea.lib.conditional_access.policy import default_error_message
from privacyidea.lib.conditional_access.session import release_ca_connection
from privacyidea.lib.conditional_access.request_context import get_ca_context
from privacyidea.lib.error import AuthError, Error
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import Match, SCOPE
from privacyidea.lib.user import User

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RejectionShape:
    """
    How one endpoint answers a request conditional access refuses.

    Passed by whichever gate guards the endpoint, because looking like an ordinary failed authentication is the
    whole requirement and what one looks like differs per endpoint.

    :ivar value: what ``result.value`` says. ``False`` everywhere except ``/validate/triggerchallenge``, where the
        value is the number of challenges triggered and a boolean would change the type of a field its callers may
        be reading as a number.
    :ivar rid: the response id this endpoint renders with. ``prepare_result`` adds ``result.authentication`` only
        for ``rid > 1``, so a rejection at ``/ttype/push`` - which renders with ``1`` - must not grow a field the
        endpoint never carries.
    :ivar carries_detail: whether an ordinary failed authentication here carries a ``detail`` at all. On
        ``/validate/*`` every failure does, so a silent rejection carries the generic failure to have one too; at
        ``/ttype/push`` none does, so a silent rejection carries none either - the generic message would be exactly
        the tell that including it on ``/validate`` avoids.
    """
    value: Any = False
    rid: int = 2
    carries_detail: bool = True


#: How ``/ttype/push`` answers a refused challenge answer. The push token renders its own response through
#: ``prepare_result`` with ``rid`` 1, so it carries no ``result.authentication``, and an ordinary failed answer there
#: carries no ``detail`` at all - both of which a rejection has to match to be indistinguishable from one.
PUSH_ANSWER_REJECTION = RejectionShape(rid=1, carries_detail=False)


def _rejected_transaction_id() -> str | None:
    """
    The transaction this request belongs to, if it carries one.

    Passed to the authentication-log row so ``attempt_id`` resolves as usual and the rejection lands on the attempt
    it refused to process, rather than starting one of its own. Both entry points can carry a transaction: a
    ``/validate`` challenge answer, and a passkey or push login answering its challenge at ``/auth``.
    """
    return get_optional_one_of(request.all_data, ["transaction_id", "state"])


@dataclass(frozen=True)
class Rejection:
    """
    What conditional access turns a request away with, before either gate decides how to deliver it.

    :ivar event_type: how the authentication log classifies the rejection
    :ivar audit_info: the free-text reason for the audit entry
    :ivar message: the error message the triggering stage configured, or ``None`` to stay generic
    :ivar other_info: extra fields for the authentication-log row, or ``None``
    """
    event_type: AuthEventType
    audit_info: str
    message: str | None
    other_info: dict | None = None


def _evaluate_rejection(user: User) -> "Rejection | None":
    """
    Whether conditional access turns this request away, and what to say when it does - the whole decision, shared
    by both entry points so neither can answer it differently from the other.

    A lock or block already in force refuses the request before the conditional-access DENY decision is evaluated,
    so no policy can override them. Every restriction in force that carries one is reported, while the
    authentication log is classified by the binding one (:func:`_binding_event_type`), because that row holds one
    classification per request. A DENY refuses this single request without persisting state; CONTINUE ("no policy
    had an opinion") returns ``None`` and the request continues. The source IP checked is ``g.client_ip``, read
    with ``g.get`` for the reason :func:`~privacyidea.api.lib.utils.build_ca_context` documents: an ``AuthError``
    raised early in ``before_request`` can leave it unset, and a missing source IP means no block and no
    source_ip-target policy rather than a 500 on an authentication.

    Reads clear an expired row as they go, so a lock that has run out is not treated as one.

    The conditional-access connection is released on the way out: this is the only read the pre-check
    does, and holding it for the rest of a request it let through occupies a second connection out of
    ``db.session``'s pool (see :func:`~privacyidea.lib.conditional_access.session.release_ca_connection`).
    """
    try:
        # Resolved once per request and kept on the context, which is the single place it lives: this pre-check is
        # its only reader, a restriction being described only on the requests it refuses.
        context = get_ca_context()
        context.use_default_error_message = show_default_ca_error_message(user)
        source_ip = g.get("client_ip")
        user_lock = get_user_lock(user, clear_expired=True)
        ip_block = get_ip_block(source_ip, clear_expired=True)
        binding = _binding_event_type(user_lock, ip_block)
        if binding:
            subject = f"locked user {user!r}" if binding is AuthEventType.USER_LOCKED else f"blocked IP {source_ip!r}"
            log.info(f"Rejecting {request.path} for {subject}.")
            # Every restriction in force that carries an error message is reported, not only the binding one: an
            # account lock and an address block are independent facts, resolved differently, so telling the user
            # about one leaves them to discover the other by failing again. Worded the same on both, it is said once
            # (restriction_messages de-duplicates).
            messages = restriction_messages(user_lock, ip_block,
                                            use_default_error_message=context.use_default_error_message)
            return Rejection(binding, _audit_reason(user_lock, ip_block),
                             " ".join(message.text for message in messages) or None,
                             _additional_event_types(binding, user_lock, ip_block))
        decision = evaluate_access_decision(build_ca_context(user))
        # A DENY decision is part of this request's history, but no authentication-log row exists yet to record it
        # against (and a dry-run DENY lets the request continue, so its row comes later). The context holds the
        # outcomes until the request stages the event they belong to - which, for an enforced DENY, is the row the
        # caller writes next.
        context.add_outcomes(decision.outcomes)
        if decision.decision == AccessDecision.DENY:
            log.info(f"Denying {request.path} for {user!r} by conditional-access policy.")
            # A DENY persists nothing, so its error message comes straight off the deciding stage - or, with none, off
            # the default error message for a denial.
            template = decision.error_message
            if not template and context.use_default_error_message:
                template = default_error_message(ConditionalAccessAction.DENY)
            return Rejection(AuthEventType.ACCESS_DENIED, "Rejected: denied by conditional-access policy",
                             render_error_message(template))
        return None
    finally:
        release_ca_connection()


# --- /validate/*: return the rejection as a response ---------------------------------------------------------------

def conditional_access_precheck(user: User, rejection_value: Any = False) -> Response | None:
    """
    Reject a request pre-auth (before any token logic and before the failcounter /
    max_auth checks) when conditional-access policies forbid it. Returns the failure
    :class:`~flask.Response` to be returned to the client, or ``None`` to continue
    with the normal flow.

    The decision is :func:`_evaluate_rejection`; this renders it for a machine-facing
    client. The response says only what an admin configured on the triggering stage; with
    nothing configured it carries the ordinary failure and reveals no more - not that the
    user is locked, that the source IP is blocked, or that a policy denied access. It says
    *something* either way, because a response with no detail at all would be a tell in
    itself: every other failure carries one. The real reason is recorded in the audit log
    and, for the admin, as this request's authentication-log row - the only place an admin
    can filter for it, since the request is turned away before anything else logs an
    outcome for it.

    :param user: the identity to gate on
    :param rejection_value: what ``result.value`` says on a rejection. ``False`` everywhere except
        ``/validate/triggerchallenge``, where the value is the *number of challenges triggered* rather than a
        boolean - answering that endpoint with ``False`` would change the type of a field its callers may be
        reading as a number.
    """
    shape = RejectionShape(value=rejection_value)
    rejection = conditional_access_rejection(user, shape)
    if rejection is None:
        return None
    return _rejection_response(shape, _rejection_wording(shape, rejection.message))


def conditional_access_rejection(user: User, shape: RejectionShape) -> Rejection | None:
    """
    Whether conditional access turns this request away, plus everything that has to happen when it does *except*
    rendering the answer: the audit entry, the authentication-log row, and claiming the error message so
    ``hide_specific_error_message`` shows it rather than its own.

    For callers that cannot return a :class:`~flask.Response`. :func:`conditional_access_precheck` is the one for
    those that can; ``/ttype/push`` is the one that cannot, since the push token hands its result back to
    :func:`~privacyidea.api.ttype.token` as a ``(bool, dict)`` pair that ``prepare_result`` renders.

    Rendering is the caller's because "what an ordinary failure looks like" differs per endpoint, and looking like
    one is the whole requirement. On ``/validate/*`` every failure carries a ``detail``, so a silent rejection
    carries the generic message rather than nothing. On ``/ttype/push`` an ordinary failed answer carries no
    detail at all, so a silent rejection must carry none either - putting the generic message there would be
    exactly the tell that including it on ``/validate`` avoids. Only wording an admin configured is surfaced
    unconditionally, on both.

    :param user: the identity to gate on
    :param shape: how this endpoint answers a refusal (see :class:`RejectionShape`)
    :return: the :class:`Rejection` to render, or ``None`` to continue with the normal flow
    """
    rejection = _evaluate_rejection(user)
    if rejection is None:
        return None
    g.audit_object.log({"success": False, "info": rejection.audit_info})
    # Staged like any other event, so request teardown writes it. A rejection row *replaces* the row the request
    # would have written anyway, which is why every gated endpoint wants one: they all log an authentication event
    # when they succeed. The one endpoint that does not - /validate/polltransaction - is not gated at all.
    log_authentication(rejection.event_type, request, user=user, other_info=rejection.other_info,
                       transaction_id=_rejected_transaction_id())
    if rejection.message:
        # Claimed before the post-policies run, so hide_specific_error_message shows this error message rather than
        # its own. A rejection *is* the whole message, so there is no failure reason it could carry past the mask.
        get_ca_context().claim_message(rejection.message)
    return rejection


def _rejection_wording(shape: RejectionShape, message: str | None) -> str | None:
    """
    What a rejection says on the endpoint *shape* describes, given the wording the restrictions carry.

    A configured message is said everywhere. A silent restriction is the interesting half: where an ordinary
    failure carries a ``detail`` it says what every other failed authentication says, because a response *without*
    one could only have come from conditional access; where an ordinary failure carries none - ``/ttype/push`` -
    it says nothing, because there the generic message would be that same tell.

    :param message: the wording the restrictions in force carry, or ``None`` for the normal, silent case
    :return: the wording, or ``None`` when the rejection carries no detail at all
    """
    if message:
        return message
    return None if not shape.carries_detail else str(GENERIC_AUTH_FAILURE)


def _rejection_response(shape: RejectionShape, message: str | None) -> Response:
    """
    The response a refused request gets, in the shape its endpoint's gate describes
    (:class:`RejectionShape`).

    Nothing of the request it refuses survives: a rejection says the wording and no more, the credentials it
    carried having never been checked.

    Only the endpoints that *return* their rejection render one here. ``/auth`` raises its own
    :class:`AuthError` instead (see :func:`_reject_restricted_login`), which the error handler renders as the
    ``401`` every failed login there returns.

    :param shape: how this endpoint answers a refusal
    :param message: the wording, or ``None`` where this endpoint's failures carry no detail (see
        :func:`_rejection_wording`)
    """
    # An empty detail is dropped by prepare_result, which is exactly what an endpoint carrying none needs.
    return send_result(shape.value, rid=shape.rid, details={"message": message} if message else {})


def conditional_access_gate(identity_resolver: Callable[[], User] | None = None,
                            rejection_value: Any = False) -> Callable[[Callable], Callable]:
    """
    View decorator that runs :func:`conditional_access_precheck` before the pre-policies below it and the endpoint
    act on the request. If the pre-check rejects it, that response is returned immediately and neither runs.

    **Keep it listed above every pre-policy and below the response decorators**, which is where every gated
    endpoint has it. Above the pre-policies because nothing may run for a locked user, a blocked source IP or a
    denied request before it is refused - the same rule ``/auth`` states at
    :func:`conditional_access_login_gate`. The exception is a pre-policy that rewrites the identity: ``set_realm``
    and ``mangle`` on ``/validate/check`` assign a new ``request.User``, and everything downstream authenticates,
    logs and counts as that one - so they run first, or the gate would check an identity that never authenticates.

    Below the response decorators because this gate *returns* its rejection rather than raising one: a failed
    authentication on ``/validate/*`` is an ordinary ``200`` carrying ``result.value`` false, not an error
    response, so returning is what keeps a refused request shaped like every other failure these endpoints
    produce. A returned response still has to travel back out through whatever is listed above the gate, so
    listing it over the response decorators would skip them - on ``/validate/check`` that means
    ``no_detail_on_fail`` never stripping the rejection, and ``construct_radius_response`` never converting a
    ``/radiuscheck`` one into the empty-body reply every other failure there gets.

    :param identity_resolver: an optional zero-argument callable returning the
        :class:`~privacyidea.lib.user.User` the pre-check should gate on. When
        omitted, ``request.User`` is used. Endpoints that must resolve the
        identity differently (a serial/credential-id request, or a transaction
        owner) pass their own resolver.
    :param rejection_value: passed through to the pre-check; see there for the one endpoint that sets it.
    """
    def decorator(wrapped_function: Callable) -> Callable:
        @functools.wraps(wrapped_function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = identity_resolver() if identity_resolver is not None else request.User
            rejection = conditional_access_precheck(user, rejection_value=rejection_value)
            if rejection is not None:
                return rejection
            return wrapped_function(*args, **kwargs)
        return wrapper
    return decorator


# --- what a rejection is made of, shared by both gates ---------------------------------------------------------------

def _binding_event_type(user_lock: RestrictionStatus | None,
                        ip_block: RestrictionStatus | None) -> AuthEventType | None:
    """
    How a request refused by both a lock and a block is classified: by the restriction that lasts longest, a
    permanent one outranking any timed one. On a tie the user lock wins, matching the lock-before-block order
    of the pre-check.

    Needed because the authentication log records one ``event_type`` per request - the value an admin filters
    on - so one of the two has to stand for the rejection. What the *user* is told is a separate question with a
    separate answer: every restriction that carries one is reported (see :func:`_evaluate_rejection`).

    :param user_lock: the :class:`RestrictionStatus` from :func:`get_user_lock`, or ``None``
    :param ip_block: the :class:`RestrictionStatus` from :func:`get_ip_block`, or ``None``
    :return: the :class:`AuthEventType` to file the rejection under, or ``None`` if neither is in force
    """

    def _remaining_time(state: RestrictionStatus | None) -> float | None:
        if not state:
            return None
        return float("inf") if state.permanent else state.seconds_remaining

    lock_remaining = _remaining_time(user_lock)
    block_remaining = _remaining_time(ip_block)
    if lock_remaining is None and block_remaining is None:
        return None
    if block_remaining is not None and (lock_remaining is None or block_remaining > lock_remaining):
        return AuthEventType.IP_BLOCKED
    return AuthEventType.USER_LOCKED


def _audit_reason(user_lock: RestrictionStatus | None, ip_block: RestrictionStatus | None) -> str:
    """
    Why this request was refused, for the audit log: every restriction in force, and whether each is permanent.

    Unlike the authentication log's single ``event_type`` this is free text, so it does not have to choose - and
    the admin reading it is the one person who should see the whole picture rather than the binding half of it.
    """
    parts = []
    if user_lock is not None:
        parts.append("account is permanently locked" if user_lock.permanent else "account is temporarily locked")
    if ip_block is not None:
        parts.append("source IP is permanently blocked" if ip_block.permanent else "source IP is temporarily blocked")
    return f"Rejected: {' and '.join(parts)}"


def _additional_event_types(binding: AuthEventType, user_lock: RestrictionStatus | None,
                            ip_block: RestrictionStatus | None) -> dict | None:
    """
    The event types the row could not record, for the entry's ``other_info``.

    The authentication log holds one classification per request, so a request refused by both a lock and a
    block is filed under whichever binds (:func:`_binding_event_type`) - and the other would otherwise leave no
    trace on the row at all, while the user was told about both. Recording it here keeps the row honest: it is
    not queryable the way ``event_type`` is, but an admin reading the entry sees the whole reason.

    :return: ``{"additional_event_types": [...]}`` when more than one restriction is in force, else ``None``
    """
    if user_lock is None or ip_block is None:
        return None
    other = AuthEventType.IP_BLOCKED if binding is AuthEventType.USER_LOCKED else AuthEventType.USER_LOCKED
    return {"additional_event_types": [str(other)]}


def show_default_ca_error_message(user: User) -> bool:
    """
    Whether this request may be told what conditional access did to it, when no stage wrote one of its own.

    The ``show_default_ca_error_message`` policy is the simplified form of writing the default error message
    onto every stage by hand, so a stage's own message still wins over it.

    A source-IP block refuses requests before any user is resolved, so this matches against an empty user rather
    than ``None``: ``None`` tells the matcher to *ignore* the user, realm and resolver attributes, which would
    let a policy restricted to one realm apply to a request belonging to no realm at all. An empty user fails
    those conditions instead, which is what having no user to match against should mean.

    The client IP is matched either way - :meth:`Match.user` passes ``g.client_ip`` itself - so a policy scoped
    to a client still applies to a rejection that has no user.
    """
    return Match.user(g, scope=SCOPE.CONDITIONAL_ACCESS, action=PolicyAction.SHOW_DEFAULT_CA_ERROR_MESSAGE,
                      user_object=user if user and user.login else User()).any()


# --- /auth: raise the rejection as an AuthError ---------------------------------------------------------------------

def _reject_restricted_login(user: User) -> None:
    """
    Reject an ``/auth`` login pre-auth (before any credential check) when conditional-access policies forbid it.
    Raises :class:`AuthError` when the login must be rejected and returns ``None`` otherwise.

    The decision is :func:`_evaluate_rejection`; this renders it for a human at the login screen. The rejection says
    whatever error message the admin configured for the restrictions in force - every one of them, so a user
    facing both a lock and a block is not left to discover the second by failing again. With none it falls back to
    the generic failure, so a locked account is indistinguishable from a wrong password in everything a human or a
    client reads: an ``AuthError`` has to carry some message, which is the one thing this path cannot borrow from
    ``/validate``, where the rejection simply carries no detail. The error *id* does differ - see the
    ``Error.AUTHENTICATE`` note at the raise below - and ``hide_specific_error_message`` remaps every failed
    login here to that same id, closing the difference for a deployment that wants it closed.

    An unresolved user / local DB admin has no ``(resolver, uid, realm)`` identity tuple and is therefore never locked.
    ``internal_admin`` comes from the flag ``before_request`` already resolved, so a blocked local admin is recorded as
    ``admin-internal`` rather than falling back to ``user``.
    """
    rejection = _evaluate_rejection(user)
    if rejection is None:
        return
    g.audit_object.log({"success": False, "info": rejection.audit_info})
    # Staged rather than written, so request teardown records it even though the AuthError below unwinds the view -
    # and staged after _evaluate_rejection, so an enforced DENY's buffered outcome lands on this row.
    log_authentication(rejection.event_type, request, user=user, other_info=rejection.other_info,
                       transaction_id=_rejected_transaction_id(),
                       internal_admin=g.get("resolved_user", {}).get("is_local_admin", False))
    if rejection.message:
        # Only when there is error message of our own: a generic rejection is the ordinary failure and should be
        # masked with every other one.
        get_ca_context().claim_message(rejection.message)
    # AUTHENTICATE rather than AUTHENTICATE_WRONG_CREDENTIALS: the credential this request carried may well have
    # been correct - it was never checked. A rejection is refused for a reason of conditional access's own, so it
    # takes the generic authentication-failure id and claims nothing about the credential.
    raise AuthError(rejection.message or GENERIC_AUTH_FAILURE, id=Error.AUTHENTICATE)


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
