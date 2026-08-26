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
each records a :class:`~privacyidea.lib.conditional_access.request_context.RejectionShape` on the request, so the
response hook can answer a restriction this very request wrote in the same shape - down to the fields the endpoint
does not have. ``/ttype/push`` is where that bites: it renders with ``rid`` 1, so it reports no ``authentication``
verdict, and an ordinary failed answer there carries no ``detail`` at all, so a silent rejection carries none either -
the opposite of ``/validate/*``, where every failure has one and a silent rejection needs the generic message to have
one too.

A restriction reads the same whichever request meets it. The request that *writes* a lock is answered exactly as the
requests the lock then refuses - the whole response, not just the wording, and whether or not a stage configured any
(see :func:`rejection_message`). The failure's own details go with it, since the credential that request happened to
carry no longer decides anything. The cost is that a silent lock is detectable at the moment it trips, because the
response changes shape.

A stage that only *notified* is the exception throughout: it refused nothing, so the credential failure is still the
reason and keeps its own id, message and details, with the notification appended (see
:func:`compose_failure_message`).

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

:func:`surface_conditional_access_message` claims nothing - it runs from ``after_request``, after all three.
"""
import functools
import json
import logging
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from flask import request, g, Response

from privacyidea.api.lib.utils import (GENERIC_AUTH_FAILURE, log_authentication, build_ca_context,
                                      send_error, send_result, get_optional_one_of)
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.engine import (get_user_lockout, get_ip_block, evaluate_access_decision,
                                                       render_error_message, restriction_messages, AccessDecision,
                                                       LockoutAction, RestrictionStatus, StageMessage)
from privacyidea.lib.conditional_access.lockout_policy import default_error_message
from privacyidea.lib.conditional_access.request_context import (ConditionalAccessContext, RejectionShape,
                                                                 get_ca_context, peek_ca_context)
from privacyidea.lib.error import AuthError, Error
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import Match, SCOPE
from privacyidea.lib.user import User
from privacyidea.lib.utils import AUTH_RESPONSE

log = logging.getLogger(__name__)

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
    so an ALLOW cannot override them. Every restriction in force that carries one is reported, while the
    authentication log is classified by the binding one (:func:`_binding_event_type`), because that row holds one
    classification per request. A DENY refuses this single request without persisting state; ALLOW / CONTINUE
    return ``None`` and the request continues. ``g.client_ip`` is the source IP checked.

    Reads clear an expired row as they go, so a lock that has run out is not treated as one.
    """
    # Resolved once per request and kept on the context, which is the single place it lives: this pre-check reads
    # it back below, and the post-response evaluation reads the same value, so both halves of one request word a
    # rejection the same way.
    context = get_ca_context()
    context.use_default_error_message = show_default_ca_error_message(user)
    lockout = get_user_lockout(user, clear_expired=True)
    ip_block = get_ip_block(g.client_ip, clear_expired=True)
    binding = _binding_event_type(lockout, ip_block)
    if binding:
        subject = f"locked user {user!r}" if binding is AuthEventType.USER_LOCKED else f"blocked IP {g.client_ip!r}"
        log.info(f"Rejecting {request.path} for {subject}.")
        # Every restriction in force that carries an error message is reported, not only the binding one: an
        # account lock and an address block are independent facts, resolved differently, so telling the user
        # about one leaves them to discover the other by failing again. Worded the same on both, it is said once
        # (restriction_messages de-duplicates).
        messages = restriction_messages(lockout, ip_block, use_default_error_message=context.use_default_error_message)
        return Rejection(binding, _audit_reason(lockout, ip_block),
                         " ".join(message.text for message in messages) or None,
                         _additional_event_types(binding, lockout, ip_block))
    decision = evaluate_access_decision(build_ca_context(user))
    # A DENY decision is part of this request's history, but no authentication-log row exists yet to record it against
    # (and a dry-run DENY lets the request continue, so its row comes later). The context holds the outcomes until the
    # request stages the event they belong to - which, for an enforced DENY, is the row the caller writes next.
    context.add_outcomes(decision.outcomes)
    if decision.decision == AccessDecision.DENY:
        log.info(f"Denying {request.path} for {user!r} by conditional-access policy.")
        # A DENY persists nothing, so its error message comes straight off the deciding stage - or, with none, off
        # the default error message for a denial.
        template = decision.error_message
        if not template and context.use_default_error_message:
            template = default_error_message(LockoutAction.DENY)
        return Rejection(AuthEventType.ACCESS_DENIED, "Rejected: denied by conditional-access policy",
                         render_error_message(template))
    return None


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
        reading as a number. See :func:`_rejected_value`, which keeps the same promise on the other path.
    """
    shape = RejectionShape(value=rejection_value)
    rejection = conditional_access_rejection(user, shape)
    if rejection is None:
        return None
    # Rendered by the one renderer both moments of one request use, so the response that *writes* a restriction
    # cannot be a different shape from the ones the restriction then refuses.
    return _rejection_response(get_ca_context(), _rejection_wording(shape, rejection.message))


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
    :param shape: how this endpoint answers a refusal (see :class:`~privacyidea.lib.conditional_access.
        request_context.RejectionShape`). Recorded whether or not this request is refused: should a *later* stage
        restrict it, the response hook has to answer in the same shape, and by then the endpoint is no longer
        identifiable.
    :return: the :class:`Rejection` to render, or ``None`` to continue with the normal flow
    """
    get_ca_context().rejection_shape = shape
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


def _rejected_value(value: Any) -> Any:
    """
    What ``result.value`` becomes on a request conditional access refused, in the type the endpoint uses.

    ``False`` almost everywhere, because that is what the value already is on a failed authentication. Not on
    ``/validate/triggerchallenge``, where it is the *number of challenges triggered*: answering that endpoint with
    a boolean would change the type of a field its callers may be reading as a number, so it gets ``0``. Anything
    already falsy is left exactly as it stands.

    ``bool`` is a subclass of ``int``, hence the second check - without it every ``True`` would become ``0``.
    """
    if not value:
        return value
    return 0 if isinstance(value, int) and not isinstance(value, bool) else False


def _rejection_wording(shape: RejectionShape, message: str | None, detail_stripped: bool = False) -> str | None:
    """
    What a rejection says on the endpoint *shape* describes, given the wording the restrictions carry.

    A configured message is said everywhere. A silent restriction is the interesting half: where an ordinary
    failure carries a ``detail`` it says what every other failed authentication says, because a response *without*
    one could only have come from conditional access; where an ordinary failure carries none - ``/ttype/push``, or
    a response ``no_detail_on_fail`` has already stripped - it says nothing, because there the generic message
    would be that same tell.

    :param message: the wording the restrictions in force carry, or ``None`` for the normal, silent case
    :param detail_stripped: whether a post-policy removed the detail this endpoint would otherwise have carried
    :return: the wording, or ``None`` when the rejection carries no detail at all
    """
    if message:
        return message
    return None if detail_stripped or not shape.carries_detail else str(GENERIC_AUTH_FAILURE)


def rejection_message(shape: RejectionShape, messages: list[StageMessage],
                      detail_stripped: bool = False) -> str | None:
    """
    What a request that has just been restricted says: the wording of the restrictions now in force, rendered as
    :func:`_rejection_wording` renders every rejection on this endpoint.

    Deliberately the same answer :func:`conditional_access_precheck` gives every request after this one. A
    restriction reads the same whether this request wrote it or an earlier one did, so the request that trips a
    lock cannot be told apart from the requests the lock then refuses - which is the property that makes a lock
    say one thing rather than two.

    :param messages: the wording the restrictions carry; empty is the normal, silent case
    """
    return _rejection_wording(shape, " ".join(message.text for message in messages) or None, detail_stripped)


def compose_failure_message(existing: str | None, messages: list[StageMessage]) -> str:
    """
    What a failed authentication should say when conditional access has something to *add* to it.

    Only ever the notification case. A stage that merely notified refused nothing, so the credential failure is
    still why the request was turned away and its own reason stays the lead; the notification follows it. A
    restriction is the other case entirely and is not composed at all - it *is* the answer, see
    :func:`rejection_message`.

    :param existing: the error message the failure already carried, if any
    :param messages: what conditional access did - **never empty**. A caller with nothing to report leaves its own
        error message alone rather than asking here, which is also what lets this always answer with a sentence.
    """
    joined = " ".join(message.text for message in messages)
    return f"{existing.rstrip('.')}. {joined}" if existing else joined


def _rejection_response(context: "ConditionalAccessContext", message: str | None) -> Response:
    """
    The response a refused request gets, in the shape the endpoint's gate recorded
    (:class:`~privacyidea.lib.conditional_access.request_context.RejectionShape`).

    The one renderer, used by the pre-check and by the response hook alike, so a rejection cannot come out shaped
    differently depending on which moment produced it. The hook's other case - a restriction on a response that is
    already a *failure* of this endpoint's own - edits that body in place instead, keeping the ``threadid`` it
    already carries; everything a renderer would decide is decided here.

    Nothing is carried over from a body this replaces: a rejection says the wording and no more, and an error's
    own code and detail describe the attempt the rejection overtook.

    :param context: this request's buffer, holding the rejection shape its gate recorded
    :param message: the wording, or ``None`` where this endpoint's failures carry no detail (see
        :func:`_rejection_wording`)
    """
    shape = context.rejection_shape
    if shape.as_error:
        # /auth, the one entry point whose failed authentication is an error response - so its rejection is one
        # too, carrying the generic authentication id and never the endpoint's own. The status stays as the error
        # handler set it, which is the 401 every failed login there returns.
        rejection = send_error(message, error_code=Error.AUTHENTICATE, details={})
        rejection.status_code = 401
        return rejection
    # An empty detail is dropped by prepare_result, which is exactly what an endpoint carrying none needs.
    return send_result(shape.value, rid=shape.rid, details={"message": message} if message else {})


def surface_conditional_access_message(response):
    """
    Report on the response what conditional access just did to this request.

    Called from :func:`~privacyidea.api.before_after.after_request`: the last point that can still shape a body,
    and - unlike a decorator - one that also runs for a response an *error handler* built. Being central also means
    no gated endpoint can forget to opt in.

    Reads the buffer with :func:`~privacyidea.lib.conditional_access.request_context.peek_ca_context` rather than
    creating one. This runs on every response of every blueprint, and "has no buffer" is exactly the question to
    ask - a request that authenticated nothing has none - answered in a single lookup. Creating one would allocate a
    buffer for every administrative request and leave teardown work to undo.

    Running after the post-policies rather than among them is what makes ``hide_specific_error_message`` and
    ``no_detail_on_fail`` a non-issue here: they have already had their say, so a notification composes onto
    whatever survived them - the generic failure when masking is on, the token's own reason when it is not - and
    needs no claim to protect it. The gates still claim, their responses being built where those actions can reach
    them.

    A stage can be tripped by any event a policy tracks, a challenge trigger included, and a restriction written on
    such a request refuses it like any other. What a rejection says never depends on what the request happened to be
    doing when it was refused. A stage that only notified changes none of that: it refused nothing, so its message
    is appended and everything the response carried - a challenge included - stays.

    Withdrawing a challenge from the response is not invalidating it: the row is left to expire unanswered, and the
    client is never told the ``transaction_id``, so it could not use it anyway. The next request carries it into the
    pre-check, which refuses it with the same wording.
    """
    context = peek_ca_context()
    if context is None or not response or not response.is_json:
        return response
    content = response.json
    try:
        context.flush()
        # Anything already in force was refused by the pre-check, which returns its own response, so this
        # evaluation is the whole story and nothing has to be read back. A request the pre-check did refuse still
        # reaches here; run_post_eval declines to evaluate conditional access's own rejections, so there is
        # nothing to add and the gate's wording stands.
        evaluation = context.run_post_eval()
        result = content.get("result") or {}
        detail = content.get("detail") or {}
        # An error-shaped body means the view raised and an error handler built this response.
        errored = "error" in result
        if evaluation.restricted:
            # An error body never met the post-policies, so a detail missing *there* says nothing about them. On
            # any other response one that is gone was stripped by no_detail_on_fail, and a silent restriction then
            # has nothing to say - the pre-check answers such a request with no detail either.
            message = rejection_message(context.rejection_shape, evaluation.messages,
                                        detail_stripped=not errored and "detail" not in content)
            if errored:
                # Answered the way this endpoint answers a refusal rather than as the error it was about to be.
                # That error must not survive: "ERR1007: the token is locked" states the very reason a rejection
                # withholds, and would sit beside the wording meant to replace it.
                return _rejection_response(context, message)
            # Answered as the pre-check answers every request after this one. Keyed on the restriction rather than
            # on having something to say, because a silent lock refuses this request too - and rather than on the
            # response looking like a failure, because ``result.value`` is a *count* on
            # /validate/triggerchallenge, where a request that triggers a challenge and trips a lock in one breath
            # reads as a success.
            #
            # The rest of the detail describes what the rejection overtook: the token attempt that failed, or the
            # challenge about to be handed out. The threadid stays - it identifies the request rather than
            # describing it.
            detail = {"threadid": detail["threadid"]} if "threadid" in detail else {}
            # A refusal now, whatever it was on its way to being: a falsy value in the type this endpoint uses,
            # and REJECT - but only where the endpoint reports an authentication verdict at all. /ttype/push
            # renders with rid 1 and has no such field, and a rejection there must not be the one response that
            # grows one.
            result["value"] = _rejected_value(result.get("value"))
            if context.rejection_shape.reports_authentication:
                result["authentication"] = AUTH_RESPONSE.REJECT
        elif errored:
            # Only a restriction overtakes an error. A notification refused nothing, so the error it merely
            # coincided with is still why the request failed, and speaks for itself.
            return response
        elif evaluation.messages and not result.get("value"):
            # A stage that only notified, on a response that did fail.
            message = compose_failure_message(detail.get("message"), evaluation.messages)
        else:
            # Nothing happened, or a notification on a response that did not fail: the message is failure-only and
            # never shown on a successful authentication.
            return response
        content["result"] = result
        if message is None:
            # A rejection with nothing to say on an endpoint whose failures carry no detail: it says what one of
            # those says, which is nothing at all (see _rejection_wording).
            content.pop("detail", None)
        else:
            detail["message"] = message
            content["detail"] = detail
        response.set_data(json.dumps(content))
    except Exception as ex:
        # Never break an authentication response over the error message of its own rejection.
        log.warning(f"Could not surface the conditional-access message on this response: {ex!r}")
    return response


def conditional_access_gate(identity_resolver: Callable[[], User] | None = None,
                            rejection_value: Any = False) -> Callable[[Callable], Callable]:
    """
    View decorator that runs :func:`conditional_access_precheck` before anything else acts on the request. If the
    pre-check rejects it, that response is returned immediately and neither the pre-policies nor the endpoint run.

    **Keep it listed above every pre-policy and below the response decorators**, which is where every gated
    endpoint has it. Above the pre-policies because nothing may run for a locked user, a blocked source IP or a
    denied request before it is refused - the same rule ``/auth`` states at
    :func:`conditional_access_login_gate`.

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

def _binding_event_type(lockout: RestrictionStatus | None,
                        ip_block: RestrictionStatus | None) -> AuthEventType | None:
    """
    How a request refused by both a lock and a block is classified: by the restriction that lasts longest, a
    permanent one outranking any timed one. On a tie the user lock wins, matching the lock-before-block order
    of the pre-check.

    Needed because the authentication log records one ``event_type`` per request - the value an admin filters
    on - so one of the two has to stand for the rejection. What the *user* is told is a separate question with a
    separate answer: every restriction that carries one is reported (see :func:`_evaluate_rejection`).

    :param lockout: the :class:`RestrictionStatus` from :func:`get_user_lockout`, or ``None``
    :param ip_block: the :class:`RestrictionStatus` from :func:`get_ip_block`, or ``None``
    :return: the :class:`AuthEventType` to file the rejection under, or ``None`` if neither is in force
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
    the generic failure, so a locked account is indistinguishable from a wrong password: an ``AuthError`` has to
    carry some message, which is the one thing this path cannot borrow from ``/validate``, where the rejection
    simply carries no detail.

    An unresolved user / local DB admin has no ``(resolver, uid, realm)`` identity tuple and is therefore never locked.
    ``internal_admin`` comes from the flag ``before_request`` already resolved, so a blocked local admin is recorded as
    ``admin-internal`` rather than falling back to ``user``.
    """
    get_ca_context().rejection_shape = RejectionShape(as_error=True)
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
