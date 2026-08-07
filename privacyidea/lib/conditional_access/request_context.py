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
from dataclasses import dataclass, field
from typing import Any

from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType,
                                                                           CA_ENFORCEMENT_EVENT_TYPES)
from privacyidea.lib.conditional_access.authentication_log import (PendingAuthEvent, update_authentication_events,
                                                                   write_authentication_events)
from privacyidea.lib.conditional_access.outcome_log import record_outcomes
from privacyidea.lib.framework import get_request_local_store
from privacyidea.lib.user import User
from privacyidea.models import ConditionalAccessOutcome

log = logging.getLogger(__name__)

# Key the context is cached under in the app-context-local store.
_CONTEXT_KEY = "conditional_access_context"


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
        # Outcomes produced before any event was staged, i.e. by the pre-auth decision. The first event staged after
        # them takes them over (see stage), because that is the row they belong to.
        self.pending_outcomes: list[ConditionalAccessOutcome] = []
        # The classification the engine has already been run for, so a repeated call is skipped but a *corrected*
        # outcome is not (see run_post_eval).
        self._evaluated_as = None

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

    def attempt_id_for_transaction(self, transaction_id: str) -> str | None:
        """
        The ``attempt_id`` of a staged event carrying *transaction_id*, newest first, or ``None`` if this request
        staged none.

        Lets an attempt be correlated within the request that created it, without depending on the row having been
        written yet - the authentication-log lookup only sees committed rows.
        """
        for event in reversed(self.pending):
            if event.transaction_id == transaction_id and event.attempt_id:
                return event.attempt_id
        return None

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

        An outcome is only meaningful next to the request it belongs to, so one whose event has no row (the write failed)
        stays on the event and is retried by the next flush. The list is emptied in place: assigning to the event would
        mark it "changed" and provoke a pointless UPDATE of columns that did not move.
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

        With nothing staged this is a no-op: a caller with no event of its own must stage one instead.
        """
        event = self.latest
        if event is None:
            return
        event.event_type = event_type
        for name, value in fields.items():
            setattr(event, name, value)

    def run_post_eval(self) -> list[str]:
        """
        Let the conditional-access engine react to what this request logged, and return the user-facing notices its
        actions produced.

        Nothing has to be scheduled: staging an authentication event *is* the signal, and everything the engine needs
        is already recorded - the classification comes from the latest staged event, the principal and source IP from
        the request's :class:`AuthPrincipal` and :attr:`source_ip`. That removes the second copy of those values that
        a separate "schedule" step would keep, and with it any chance of the two disagreeing after a
        :meth:`reclassify`.

        Only the latest event is evaluated, which is one evaluation per request. Where a request stages several
        (``push_wait``: the challenge trigger, then the terminal outcome) the earlier ones are still counted - counts
        are taken over the stored rows - they just do not each provoke their own evaluation.

        Runs **once per distinct classification**, not merely once: an endpoint that needs the notices in its own
        response can run it early (``/auth`` does) and request teardown will not repeat the same evaluation. Should a
        post-policy correct the outcome in between, however, teardown *does* evaluate again - otherwise the engine
        would be left having judged a classification that no longer holds.

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

        What the engine decided is recorded as this request's conditional-access history, against the row of the event
        it judged - which exists because :meth:`flush` ran first. Recording is guarded internally, so a failure there
        costs the history entry and nothing else.

        The event types conditional access writes for its own rejections are skipped: evaluating them would let a lock
        feed itself, since a locked user's rejected requests would keep the count above the threshold forever. They are
        also absent from the trackable vocabulary, so no policy could match one anyway - this saves the query and keeps
        the guarantee readable where the evaluation happens
        (:data:`~privacyidea.lib.conditional_access.authentication_event_types.CA_ENFORCEMENT_EVENT_TYPES`).
        """
        event = self.latest
        if event is None or event.event_type == self._evaluated_as:
            return []
        if event.event_type in CA_ENFORCEMENT_EVENT_TYPES:
            log.debug(f"Not evaluating conditional-access policies for {event.event_type}: this request was rejected "
                      f"by conditional access itself.")
            return []
        self._evaluated_as = event.event_type
        # Deferred import: the engine pulls in the ORM models, so importing it at module level would risk an
        # import-order cycle during app startup.
        from privacyidea.lib.conditional_access.engine import evaluate_lockout_policies
        try:
            evaluation = evaluate_lockout_policies(self.principal.user, event.event_type, source_ip=self.source_ip)
        except Exception as ex:
            log.warning(f"Conditional-access policy evaluation failed: {ex!r}")
            return []
        record_outcomes(evaluation.outcomes, event.row_id)
        return evaluation.notices

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
