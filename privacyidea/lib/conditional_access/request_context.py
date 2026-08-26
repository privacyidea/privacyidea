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
__doc__ = """Per-request buffer of the conditional-access work this request will do.

One logical authentication produces its authentication-log row from any of a dozen call sites, and two post-policies
may afterwards *correct* that row. Rather than have each of them write (and re-write) independently, they stage a
:class:`~privacyidea.lib.conditional_access.authentication_log.PendingAuthEvent` here and the rows are written
together - the same shape the audit log uses with ``g.audit_object``.

The buffer lives on ``g``, so it is per app context (and thus per request) exactly like the conditional-access
session it writes on.
"""
import logging
import secrets
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from flask import has_request_context

from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType,
                                                                           CA_ENFORCEMENT_EVENT_TYPES)
from privacyidea.lib.conditional_access.authentication_log import (PendingAuthEvent, update_authentication_events,
                                                                   write_authentication_events)
from privacyidea.lib.conditional_access.context import CAContext
from privacyidea.lib.conditional_access.outcome_log import record_outcomes
from privacyidea.lib.framework import get_request_local_store
from privacyidea.lib.user import User
from privacyidea.models import ConditionalAccessOutcome

if TYPE_CHECKING:
    # Only for the annotation below: importing the engine at module level would risk an import-order cycle
    # during app startup, which is why run_post_eval imports it inside the function instead.
    from privacyidea.lib.conditional_access.engine import StageMessage

log = logging.getLogger(__name__)

# Key the context is cached under in the app-context-local store.
_CONTEXT_KEY = "conditional_access_context"

# The key under which a challenge records the authentication attempt it was triggered for. Written by
# :func:`~privacyidea.lib.token.auth.create_challenge`, read back by :meth:`ConditionalAccessContext.continue_attempt`.
ATTEMPT_ID_CHALLENGE_KEY = "attempt_id"


@dataclass
class AuthPrincipal:
    """
    Who this request is authenticating, recorded once and used by both the log rows and the policy evaluation.

    *user* alone is not enough to describe every principal, which is why the other two fields exist. A resolved user
    carries ``(resolver, uid, realm, login)``; an **unresolved** one (an unknown login) still carries login and realm
    with resolver empty and uid ``None``, which is exactly what the log stores. A **local database admin**, however,
    has no user object at all - the login is not kept there - so it arrives as *username*, and *internal_admin* marks
    it so the row's ``user_role`` says ``admin-internal`` rather than ``user``.

    *user* defaults to an empty :class:`~privacyidea.lib.user.User` rather than ``None`` so the engine can always
    read ``.resolver`` / ``.uid`` off it; an empty one is simply never "resolved" and so never locked.

    This tracks the **most recently logged** identity, and deliberately does not reach back into events already
    staged. Each event captures the identity it was logged *for*.
    """
    user: User = field(default_factory=User)
    username: str | None = None
    internal_admin: bool = False


@dataclass(frozen=True)
class PostEvaluation:
    """
    What the post-response evaluation left for the current response to say.

    :ivar messages: the user-facing wording the triggered stages carry, most severe first. Empty when nothing was
        triggered *and* when what was triggered carries no wording - silent by default holds here as everywhere.
    :ivar restricted: whether this request left a restriction in force. Independent of :attr:`messages`, and that
        is the whole reason it exists: a silent restriction produces no wording, yet the request still has to be
        answered as the rejection it now is, exactly like every request the pre-check refuses after it.
    """
    messages: list["StageMessage"] = field(default_factory=list)
    restricted: bool = False


class ConditionalAccessContext:
    """
    The conditional-access work of one request: who is authenticating, and the authentication-log rows it will write.

    Rows are held as a list rather than a single row because one request can legitimately produce several: a
    ``push_wait`` login logs the challenge trigger and then the terminal outcome within the same blocking request.
    They are written in staging order, so the log reconstructs the sequence.
    """

    def __init__(self) -> None:
        self.pending: list[PendingAuthEvent] = []
        self.principal = AuthPrincipal()
        self.source_ip: str | None = None
        # The attempt this request belongs to, once it is known (see attempt_id).
        self._attempt_id: str | None = None
        # Outcomes produced before any event was staged, i.e. by the pre-auth decision. The first event staged after
        # them takes them over (see stage), because that is the row they belong to.
        self.pending_outcomes: list[ConditionalAccessOutcome] = []
        # The classification the engine has already been run for, so a repeated call is skipped but a *corrected*
        # outcome is not (see run_post_eval).
        self._evaluated_as = None
        # The wording conditional access claims for this response, so the masking actions show it (see claim_message).
        self.own_message: str | None = None
        # Whether a rejection with no error message of its own falls back to the default wording for what it did
        # (see CAContext). Resolved once by the gate, where policies can be matched, and read again at
        # post-response evaluation so both halves of one request answer the same way.
        self.use_default_error_message = False
        # How this endpoint answers a refused request, recorded by whichever gate guards it so the response hook can
        # answer a *restricted* request the same way - even when the view raised and the body to replace is an error.
        # ``rejection_value`` is what ``result.value`` says (a count on /validate/triggerchallenge, hence not simply
        # False); ``rejects_with_error`` marks /auth, the one entry point whose failed authentication is an error
        # response rather than a 200 carrying false.
        self.rejection_value: Any = False
        self.rejects_with_error = False

    def claim_message(self, message: str) -> None:
        """
        Claim *message* as conditional access's own wording for this response, so ``hide_specific_error_message``
        and ``no_detail_on_fail`` show it instead of their own generic text (see :func:`claimed_ca_message`).

        Only the gates claim: their responses are built inside the decorator stack, where those two actions can
        still reach them. The ``after_request`` hook needs no claim, since it runs after both.
        """
        self.own_message = message

    @property
    def has_data(self) -> bool:
        """Whether anything has been staged at all (written or not). Mirrors ``audit_object.has_data``."""
        return bool(self.pending)

    @property
    def unwritten(self) -> list[PendingAuthEvent]:
        """The staged events that have no row yet, in staging order."""
        return [event for event in self.pending if not event.written]

    @property
    def amended(self) -> list[PendingAuthEvent]:
        """The staged events whose row exists but no longer matches the event, in staging order."""
        return [event for event in self.pending if event.changed]

    @property
    def latest(self) -> PendingAuthEvent | None:
        """
        The most recently staged event, or ``None`` if nothing was staged.

        This is the event a later request stage amends: it classifies the request's outcome, and where a request
        stages several (``push_wait``: the challenge trigger, then the terminal outcome) the last one is the terminal
        one.
        """
        return self.pending[-1] if self.pending else None

    @property
    def amendable(self) -> PendingAuthEvent | None:
        """
        The staged event a later request stage may correct, or ``None`` if there is none.

        That is :attr:`latest`, with two exceptions - both events that record something other than the outcome the
        request's token logic reached, and that a later stage must therefore not overwrite. A caller that finds
        nothing amendable stages its own event instead.

        An ``immediate`` event records something that *happened* at that point - the ``push_wait`` challenge trigger,
        which a concurrent ``/ttype/push`` has to be able to read. It matters where the terminal event is suppressed
        (a ``push_wait`` timeout): the trigger is then the only staged event, and reclassifying it would destroy the
        trigger record instead of logging the corrected outcome.

        A :data:`~privacyidea.lib.conditional_access.authentication_event_types.CA_ENFORCEMENT_EVENT_TYPES` event
        records that conditional access turned the request away before any token logic ran - the one place an admin
        can see *why* it was refused. The post-policies still run on the gate's rejection response (the gate is the
        innermost decorator), so without this they would relabel that row: the reason would be lost, and the
        relabelled event would pass the matching guard in :meth:`run_post_eval` and let the lock feed itself.
        """
        event = self.latest
        if event is None or event.immediate or event.event_type in CA_ENFORCEMENT_EVENT_TYPES:
            return None
        return event

    @property
    def rejected_by_conditional_access(self) -> bool:
        """
        Whether conditional access itself turned this request away (see :data:`CA_ENFORCEMENT_EVENT_TYPES`).

        The gate is the innermost decorator, so the post-policies still run on its rejection response and would
        otherwise classify a request that never reached any token logic. There is nothing for them to say about it:
        the request was refused for a reason already recorded, and logging their own outcome on top would both bury
        that reason and hand the lockout counters an attempt the lock itself produced.
        """
        event = self.latest
        return event is not None and event.event_type in CA_ENFORCEMENT_EVENT_TYPES

    @property
    def attempt_id(self) -> str:
        """
        The id correlating everything this request contributes to one logical authentication attempt.

        An attempt spans as many requests as the flow needs - a challenge trigger, a wrong answer, the retry that
        succeeds - and every authentication-log row of those requests carries this id, so a policy can count
        *attempts* rather than rows. It is minted on first use and then fixed for the rest of the request, so the
        challenge the request triggers and the rows it logs cannot disagree about which attempt they belong to.

        A request continuing an earlier attempt takes that attempt's id over first (:meth:`continue_attempt`); one
        that continues nothing starts a new attempt here.
        """
        if self._attempt_id is None:
            # 128 bit, so ids do not collide silently across the retained authentication log.
            self._attempt_id = secrets.token_hex(16)
        return self._attempt_id

    @property
    def attempt_resolved(self) -> bool:
        """
        Whether this request has settled on an attempt yet, without settling on one by asking.

        Reading :attr:`attempt_id` mints an id as a side effect, so this is the only way to tell "we joined a known
        attempt" from "we are about to start a new one" - the difference between a correctly correlated row and a
        silently orphaned one.
        """
        return self._attempt_id is not None

    def continue_attempt(self, transaction_id: str | None) -> None:
        """
        Join the attempt the challenge *transaction_id* was triggered for, so this request's rows are grouped with it
        instead of starting an attempt of their own.

        The attempt id is stored in the challenge's own data when the challenge is created
        (:func:`~privacyidea.lib.token.auth.create_challenge`), which is why this reads the challenge rather than the
        authentication log: the grouping travels with the very thing the client hands back, so no row has to be
        committed - nor the log indexed by ``transaction_id`` - for an attempt to be recovered.

        Because a *successfully* answered challenge is deleted by the token logic, this has to run before that logic:
        the endpoints that answer a challenge do it in ``before_request``. A caller that only learns the transaction
        afterwards calls it itself - the out-of-band ``/ttype/push`` answer, which identifies its challenge by
        signature and leaves it in place, and any request whose own row is the first to name the transaction.

        A no-op once this request has settled on an attempt, so the earliest (and therefore most specific) caller
        wins. Also a no-op when the transaction has no challenge left - expired, cleaned up, or never existed - in
        which case :attr:`attempt_id` mints a fresh id and the row is at worst grouped as its own attempt rather than
        left ungrouped.
        """
        if self._attempt_id is not None or not transaction_id:
            return
        # Deferred import: lib.challenge pulls in the ORM models and the challenge cache, so importing it at module
        # level would risk an import-order cycle during app startup.
        from privacyidea.lib.challenge import get_challenges
        try:
            for challenge in get_challenges(transaction_id=transaction_id):
                attempt_id = challenge.get_data().get(ATTEMPT_ID_CHALLENGE_KEY)
                if attempt_id:
                    self._attempt_id = attempt_id
                    return
        except Exception as ex:
            # Correlating an attempt must never break the authentication it is describing.
            log.debug(f"Could not read the attempt id of transaction {transaction_id}: {ex!r}")

    def add_outcomes(self, outcomes: list[ConditionalAccessOutcome]) -> None:
        """
        Buffer what conditional access decided *before* this request logged anything - the pre-auth DENY decision,
        enforced or dry-run.

        There is no row to record them against yet, and for a rejected request there will not be one until the
        pre-check stages its own event. So they wait here and the next staged event takes them over (:meth:`stage`).
        A request that never stages an event drops them, which is correct: with no authentication event there is
        nothing the outcome could belong to, and the decision will be re-derived on the next request that does log one.
        """
        self.pending_outcomes.extend(outcomes)

    def stage(self, event: PendingAuthEvent) -> PendingAuthEvent:
        """
        Add *event* to this request's buffer and return it, so the caller can keep the handle - a later stage can
        still amend the event, and its ``row_id`` becomes available once it is written.

        Any outcomes buffered by :meth:`add_outcomes` are handed to this event, so they are written as soon as its row
        id is known.
        """
        if self.pending_outcomes:
            event.outcomes.extend(self.pending_outcomes)
            self.pending_outcomes.clear()
        self.pending.append(event)
        return event

    def flush(self) -> bool:
        """
        Bring the database in line with everything staged: insert the events that have no row yet, oldest first,
        re-write the rows of events amended since they were written, and record the conditional-access outcomes waiting
        on a row id.

        Idempotent, so it is safe to call at any point and again at request teardown: an event that is already stored
        and unchanged is skipped, and outcomes already recorded are dropped from the event. Guarded internally - a
        failure is logged and swallowed, and the affected events keep their "needs writing" state so a later flush
        retries them.

        :return: whether everything staged is now stored as the events describe it
        """
        inserted = write_authentication_events(self.unwritten)
        updated = update_authentication_events(self.amended)
        recorded = self._record_outcomes()
        return inserted and updated and recorded

    def _record_outcomes(self) -> bool:
        """
        Write the outcomes carried by staged events whose row now exists, and clear them so a later flush does not
        record them twice.

        An outcome is only meaningful next to the request it belongs to, so one whose event has no row (the write
        failed) stays on the event and is retried by the next flush. The list is emptied in place: assigning to the
        event would mark it "changed" and provoke a pointless UPDATE of columns that did not move.
        """
        recorded = True
        for event in self.pending:
            if not event.outcomes or event.row_id is None:
                continue
            if record_outcomes(event.outcomes, event.row_id):
                event.outcomes.clear()
            else:
                recorded = False
        return recorded

    def reclassify(self, event_type: AuthEventType, **fields: Any) -> None:
        """
        Correct the outcome of this request: assign *event_type* (and any other *fields*) to the staged event.

        Nothing else has to be updated - the policy evaluation reads the classification straight off the event (see
        :meth:`run_post_eval`), so correcting the event is all there is to it. *fields* are applied only when given, so
        a post-policy that has no serial of its own does not clear the logged one.

        With nothing :attr:`amendable` this is a no-op: a caller with no event of its own must stage one instead.
        """
        event = self.amendable
        if event is None:
            return
        event.event_type = event_type
        for name, value in fields.items():
            setattr(event, name, value)

    def run_post_eval(self) -> PostEvaluation:
        """
        Let the conditional-access engine react to what this request logged, and report back what the current
        response has to say about it: the wording the triggered stages carry, and whether this request left a
        restriction in force (see :class:`PostEvaluation`).

        Nothing has to be scheduled: staging an authentication event *is* the signal, and everything the engine needs
        is already recorded - the classification comes from the latest staged event, the principal and source IP from
        the request's :class:`AuthPrincipal` and :attr:`source_ip`. That removes the second copy of those values that
        a separate "schedule" step would keep, and with it any chance of the two disagreeing after a
        :meth:`reclassify`.

        Only the latest event is evaluated, which is one evaluation per request. Where a request stages several
        (``push_wait``: the challenge trigger, then the terminal outcome) the earlier ones are still counted - counts
        are taken over the stored rows - they just do not each provoke their own evaluation.

        Runs **once per distinct classification**, not merely once: an endpoint that needs the messages in its own
        response can run it early (``/auth`` does) and request teardown will not repeat the same evaluation. Should a
        post-policy correct the outcome in between, however, teardown *does* evaluate again - otherwise the engine
        would be left having judged a classification that no longer holds. A classification counts as evaluated only
        once the engine returned, so an early call that failed is retried at teardown rather than swallowed.

        The evaluation counts events over the authentication log, so it must run **after** :meth:`flush` - otherwise
        the count would miss the very event that triggered it. That ordering also keeps the counts from reading a stale
        snapshot: the pre-checks opened a read transaction, and under MySQL/MariaDB's REPEATABLE READ it would hide
        rows a concurrent request committed since - but the flush commits, and a commit ends the transaction, so the
        counts start from a fresh view on every backend. Should a caller ever reach here *without* a preceding commit,
        that no longer holds and the read view has to be ended explicitly first.

        Every error is swallowed: this only writes state that the *next* request consults and must never affect the
        response that already completed.

        What the engine decided comes back as outcomes, and they are recorded here against the row of the event it
        judged - a dry-run policy's included, since that records what it *would* have done. The row id is available
        because :meth:`flush` ran first; had the row not been written, the outcomes are dropped with a log message
        rather than stored without the request they belong to.

        The :class:`~privacyidea.lib.conditional_access.context.CAContext` a policy's conditions are matched against is
        assembled here rather than by :func:`~privacyidea.api.lib.utils.build_ca_context`: everything it needs is
        already recorded, so this stays Flask-free and - more importantly - the conditions are evaluated against
        exactly the identity the row states. ``user_role`` is taken off the event for that reason: it was determined
        when the event was staged, from the ``internal_admin`` flag the caller verified, which a local database admin
        cannot be classified without.

        The event types conditional access writes for its own rejections are skipped: evaluating them would let a lock
        feed itself, since a locked user's rejected requests would keep the count above the threshold forever. They are
        also absent from the trackable vocabulary, so no policy could match one anyway - this saves the query and keeps
        the guarantee readable where the evaluation happens
        (:data:`~privacyidea.lib.conditional_access.authentication_event_types.CA_ENFORCEMENT_EVENT_TYPES`).
        """
        event = self.latest
        if event is None or event.event_type == self._evaluated_as:
            return PostEvaluation()
        if event.event_type in CA_ENFORCEMENT_EVENT_TYPES:
            log.debug(f"Not evaluating conditional-access policies for {event.event_type}: this request was rejected "
                      f"by conditional access itself.")
            return PostEvaluation()
        # Deferred import: the engine pulls in the ORM models, so importing it at module level would risk an
        # import-order cycle during app startup.
        from privacyidea.lib.conditional_access.engine import evaluate_lockout_policies
        context = CAContext(user=self.principal.user or None, source_ip=self.source_ip,
                            user_role=event.user_role, use_default_error_message=self.use_default_error_message)
        try:
            evaluation = evaluate_lockout_policies(context, event.event_type)
        except Exception as ex:
            log.warning(f"Conditional-access policy evaluation failed: {ex!r}")
            return PostEvaluation()
        # Marked evaluated only now: a failure above leaves the classification unevaluated, so the teardown call is
        # the retry rather than a skipped second attempt.
        self._evaluated_as = event.event_type
        record_outcomes(evaluation.outcomes, event.row_id)
        return PostEvaluation(messages=evaluation.messages, restricted=bool(evaluation.enforced_targets))

    def finalize(self) -> None:
        """
        Write everything staged and then evaluate the policies against it. Called from request teardown; both halves
        are guarded, so this never raises.
        """
        self.flush()
        self.run_post_eval()


def get_ca_context() -> ConditionalAccessContext:
    """
    Return this app context's :class:`ConditionalAccessContext`, creating it on first use.
    """
    store = get_request_local_store()
    context = store.get(_CONTEXT_KEY)
    if context is None:
        context = ConditionalAccessContext()
        store[_CONTEXT_KEY] = context
    return context


def continue_attempt(transaction_id: str | None) -> None:
    """
    Let this request join the attempt the challenge *transaction_id* was triggered for
    (:meth:`ConditionalAccessContext.continue_attempt`).

    For ``before_request``, which has to do this ahead of the token logic. A request that carries no transaction
    continues nothing, and is not given a buffer just to establish that.
    """
    if transaction_id:
        get_ca_context().continue_attempt(transaction_id)


def current_attempt_id() -> str | None:
    """
    The attempt id of the request in progress, or ``None`` when there is no request to attribute anything to.

    For :func:`~privacyidea.lib.token.auth.create_challenge`, which stamps it into every challenge so a later request
    answering that challenge can rejoin the attempt.

    An attempt is a property of one HTTP request, so this deliberately tests for a **request** context rather than
    merely an app context. A ``pi-manage`` command or a periodic task runs inside an app context and would otherwise be
    handed an attempt id - and since the buffer lives on ``g``, which such a task holds for its whole run, every
    challenge it created would be stamped with the *same* id and read back as one authentication attempt. Outside a
    request there is no attempt to speak of, so the challenge carries none and a request answering it starts its own.
    """
    if not has_request_context():
        return None
    return get_ca_context().attempt_id


def claimed_ca_message() -> str | None:
    """
    The error message conditional access claims for this response (or ``AuthError``), or ``None`` when it wrote none.

    ``hide_specific_error_message`` and ``no_detail_on_fail`` exist to suppress what privacyIDEA volunteers *by
    default* - which factor failed, why the token refused. A conditional-access message is the opposite: an admin
    either wrote it on the stage or turned it on by policy. The two are separate concerns, so both actions show
    this wording rather than their own generic text, and suppress everything else as usual - which costs a
    rejection nothing, since it has nothing else to say.

    Read with :func:`peek_ca_context`, so asking the question on a request that never touched conditional access
    does not bring a buffer into existence.
    """
    context = peek_ca_context()
    return context.own_message if context else None


def peek_ca_context() -> ConditionalAccessContext | None:
    """
    Return this app context's buffer if one was created, else ``None`` - without creating one.

    For request teardown, which has to flush whatever a request staged but should not bring a buffer into existence
    for the many requests that never log an authentication event.
    """
    return get_request_local_store().get(_CONTEXT_KEY)


def reset_ca_context() -> None:
    """
    Discard this app context's buffer, staged events and all, so the next :func:`get_ca_context` starts empty.

    A real request gets a fresh ``g`` and therefore a fresh buffer; this exists for the test suite, which pushes one
    app context per test class and would otherwise carry one test's staged events into the next. Deliberately
    *discards* rather than flushes: leftovers from a test body are not rows anybody asked to persist.
    """
    get_request_local_store().pop(_CONTEXT_KEY, None)
