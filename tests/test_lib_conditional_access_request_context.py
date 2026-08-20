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
Unit tests for the per-request conditional-access buffer
(:mod:`privacyidea.lib.conditional_access.request_context`).
"""
import mock
from flask import has_request_context
from sqlalchemy import select

from privacyidea.lib.challenge import delete_challenges
from privacyidea.lib.conditional_access.authentication_event_types import (CA_ENFORCEMENT_EVENT_TYPES, AuthEventType)
from privacyidea.lib.conditional_access.engine import (LockoutAction, LockoutEvaluation, MessageKind,
                                                       StageMessage)
from privacyidea.lib.conditional_access.outcome_log import get_outcomes
from privacyidea.lib.conditional_access.authentication_log import (AuthLogUserRole, PendingAuthEvent,
                                                                  get_authentication_logs,
                                                                  write_authentication_events)
from privacyidea.lib.conditional_access.context import CAContext
from privacyidea.lib.conditional_access.request_context import (ATTEMPT_ID_CHALLENGE_KEY, AuthPrincipal,
                                                              ConditionalAccessContext, current_attempt_id,
                                                              get_ca_context)
from privacyidea.lib.conditional_access.session import close_ca_session, get_ca_session
from privacyidea.lib.token import create_challenge
from privacyidea.lib.user import User
from privacyidea.models import ConditionalAccessOutcome, db
from privacyidea.models.authentication_log import AuthenticationLog, authentication_log_column_length
from .base import MyTestCase


class ConditionalAccessContextTestCase(MyTestCase):

    def setUp(self):
        self._clear()

    def tearDown(self):
        close_ca_session()
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        db.session.rollback()
        db.session.execute(ConditionalAccessOutcome.__table__.delete())
        db.session.execute(AuthenticationLog.__table__.delete())
        db.session.commit()

    @staticmethod
    def _event(username, event_type=AuthEventType.LOGIN_SUCCESS):
        return PendingAuthEvent(event_type=event_type, username=username)

    def test_01_context_is_cached_per_app_context(self):
        context = get_ca_context()
        self.assertIs(context, get_ca_context())
        with self.app.app_context():
            self.assertIsNot(context, get_ca_context())

    def test_02_staging_does_not_write(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))

        self.assertTrue(context.has_data)
        self.assertIsNone(event.row_id)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_03_stage_returns_the_event_handle(self):
        context = ConditionalAccessContext()
        event = self._event("alice")
        self.assertIs(event, context.stage(event))

    def test_04_flush_writes_and_records_row_ids(self):
        context = ConditionalAccessContext()
        first = context.stage(self._event("alice"))
        second = context.stage(self._event("bob"))

        self.assertTrue(context.flush())

        self.assertIsNotNone(first.row_id)
        self.assertIsNotNone(second.row_id)
        # Written in staging order, so the row ids reconstruct the sequence.
        self.assertLess(first.row_id, second.row_id)
        self.assertListEqual(["alice", "bob"], [entry.username for entry in get_authentication_logs()])

    def test_05_flush_is_idempotent(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        context.flush()
        row_id = event.row_id

        self.assertTrue(context.flush())

        self.assertEqual(row_id, event.row_id)
        self.assertEqual(1, len(get_authentication_logs()))

    def test_06_flush_only_writes_the_unwritten_events(self):
        context = ConditionalAccessContext()
        first = context.stage(self._event("alice"))
        context.flush()
        second = context.stage(self._event("bob"))

        self.assertListEqual([second], context.unwritten)
        context.flush()

        self.assertListEqual([], context.unwritten)
        self.assertListEqual(["alice", "bob"], [entry.username for entry in get_authentication_logs()])
        self.assertLess(first.row_id, second.row_id)

    def test_07_flush_with_nothing_staged_is_a_noop(self):
        context = ConditionalAccessContext()
        self.assertTrue(context.flush())
        self.assertFalse(context.has_data)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_08_failed_flush_leaves_the_events_unwritten(self):
        # event_type is NOT NULL, so this entry cannot be inserted.
        context = ConditionalAccessContext()
        event = context.stage(PendingAuthEvent(event_type=None, username="alice"))

        self.assertFalse(context.flush())

        self.assertIsNone(event.row_id)
        self.assertListEqual([event], context.unwritten)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_09_all_events_of_one_flush_share_a_transaction(self):
        # A failing event must take its whole flush with it, rather than leaving a partial sequence behind.
        context = ConditionalAccessContext()
        good = context.stage(self._event("alice"))
        bad = context.stage(PendingAuthEvent(event_type=None, username="broken"))

        self.assertFalse(context.flush())

        self.assertIsNone(good.row_id)
        self.assertIsNone(bad.row_id)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_10_amending_a_staged_event_before_the_flush_writes_the_new_value(self):
        # What lets a post-policy correct a classification without a second UPDATE.
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice", AuthEventType.LOGIN_SUCCESS))
        event.event_type = AuthEventType.NOT_AUTHORIZED

        context.flush()

        entries = get_authentication_logs()
        self.assertEqual(1, len(entries))
        self.assertEqual(str(AuthEventType.NOT_AUTHORIZED), entries[0].event_type)

    def test_11_truncation_is_applied_at_flush_time(self):
        # Values are held raw and cut when the row is built, so a value lengthened after staging is still truncated.
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        oversized = "X" * (authentication_log_column_length["resolver"] + 50)
        event.resolver = oversized

        context.flush()

        entry = db.session.scalars(select(AuthenticationLog)).one()
        self.assertEqual(authentication_log_column_length["resolver"], len(entry.resolver))
        self.assertEqual(oversized[authentication_log_column_length["resolver"]:],
                         entry.other_info["truncated"]["resolver"])

    def test_12_write_authentication_events_with_no_events_succeeds(self):
        self.assertTrue(write_authentication_events([]))

    def test_13_amending_a_written_event_marks_it_changed(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        context.flush()

        self.assertTrue(event.written)
        self.assertFalse(event.changed)

        event.event_type = AuthEventType.NOT_AUTHORIZED

        self.assertTrue(event.changed)
        self.assertListEqual([event], context.amended)
        self.assertListEqual([], context.unwritten)

    def test_14_amending_before_the_write_does_not_mark_it_changed(self):
        # Only an assignment made after the row exists needs an UPDATE; before that it just lands in the INSERT.
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        event.event_type = AuthEventType.NOT_AUTHORIZED

        self.assertFalse(event.changed)
        context.flush()

        self.assertListEqual([], context.amended)
        self.assertEqual(1, len(get_authentication_logs()))

    def test_15_flush_updates_the_stored_row_of_an_amended_event(self):
        # The point of the whole exercise: a post-policy correcting the classification after the row was written
        # still ends up in the database, and does not add a second row.
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice", AuthEventType.LOGIN_SUCCESS))
        context.flush()
        row_id = event.row_id

        event.event_type = AuthEventType.NOT_AUTHORIZED
        event.serial = "SER123"
        self.assertTrue(context.flush())

        entries = get_authentication_logs()
        self.assertEqual(1, len(entries))
        self.assertEqual(row_id, entries[0].id)
        self.assertEqual(str(AuthEventType.NOT_AUTHORIZED), entries[0].event_type)
        self.assertEqual("SER123", entries[0].serial)
        self.assertFalse(event.changed)

    def test_16_flush_is_idempotent_after_an_update(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        context.flush()
        event.username = "renamed"
        context.flush()

        self.assertTrue(context.flush())
        self.assertListEqual(["renamed"], [entry.username for entry in get_authentication_logs()])

    def test_17_failed_update_keeps_the_event_changed_for_a_retry(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        context.flush()

        # event_type is NOT NULL, so writing this amendment fails.
        event.event_type = None
        self.assertFalse(context.flush())
        self.assertTrue(event.changed)

        # The stored row still holds the last value that could be written.
        self.assertListEqual([str(AuthEventType.LOGIN_SUCCESS)],
                             [entry.event_type for entry in get_authentication_logs()])

        # A later flush retries it, and now succeeds.
        event.event_type = AuthEventType.NOT_AUTHORIZED
        self.assertTrue(context.flush())
        self.assertFalse(event.changed)
        self.assertListEqual([str(AuthEventType.NOT_AUTHORIZED)],
                             [entry.event_type for entry in get_authentication_logs()])

    def test_18_amending_applies_truncation_like_a_fresh_row(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        context.flush()

        oversized = "Y" * (authentication_log_column_length["resolver"] + 30)
        event.resolver = oversized
        context.flush()

        entry = db.session.scalars(select(AuthenticationLog)).one()
        self.assertEqual(authentication_log_column_length["resolver"], len(entry.resolver))
        self.assertEqual(oversized[authentication_log_column_length["resolver"]:],
                         entry.other_info["truncated"]["resolver"])

    def test_19_update_of_a_deleted_row_is_survived(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        context.flush()
        db.session.execute(AuthenticationLog.__table__.delete())
        db.session.commit()

        event.username = "renamed"

        self.assertTrue(context.flush())
        self.assertFalse(event.changed)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_20_post_eval_uses_the_events_current_classification(self):
        # The evaluation reads the classification off the event, so a reclassification cannot leave it evaluating an
        # outcome that no longer holds - there is no second copy to keep in step.
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice", AuthEventType.LOGIN_SUCCESS))
        context.principal = AuthPrincipal(user=User("cornelius", self.realm1))
        context.source_ip = "10.0.0.1"
        context.flush()

        context.reclassify(AuthEventType.NOT_AUTHORIZED)
        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            evaluate.return_value = LockoutEvaluation()
            context.run_post_eval()

        # The engine is handed the classification and the subject only - the subject as a CAContext describing the
        # identity the row states; the outcomes it returns are recorded by the context against the row it judged.
        evaluate.assert_called_once_with(CAContext(user=context.principal.user, source_ip="10.0.0.1",
                                                  user_role=event.user_role),
                                         AuthEventType.NOT_AUTHORIZED)

    def test_20a_post_eval_takes_the_user_role_off_the_event(self):
        # The role a policy's conditions match on comes from the event, not from a second lookup: it was determined
        # when the event was staged, from the verified internal_admin flag - which is the only way a local database
        # admin is classified as admin-internal at all, and what a break-glass condition keys on.
        context = ConditionalAccessContext()
        event = context.stage(self._event("admin"))
        event.user_role = str(AuthLogUserRole.ADMIN_INTERNAL)
        context.principal = AuthPrincipal(username="admin", internal_admin=True)

        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            evaluate.return_value = LockoutEvaluation()
            context.run_post_eval()

        ca_context = evaluate.call_args.args[0]
        self.assertEqual(str(AuthLogUserRole.ADMIN_INTERNAL), ca_context.user_role)
        # A local admin has no user object, so the context carries no user and no user-target policy can lock it.
        self.assertIsNone(ca_context.user)

    def test_21_reclassify_applies_only_the_fields_given(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        event.serial = "TOK001"

        context.reclassify(AuthEventType.ENROLLMENT_TRIGGERED, transaction_id="txn-1")

        self.assertEqual(AuthEventType.ENROLLMENT_TRIGGERED, event.event_type)
        self.assertEqual("txn-1", event.transaction_id)
        # Not passed, so untouched rather than cleared.
        self.assertEqual("TOK001", event.serial)

    def test_22_reclassify_without_a_staged_event_is_a_noop(self):
        # Nothing to correct: a caller with no event of its own has to stage one.
        context = ConditionalAccessContext()
        context.reclassify(AuthEventType.NOT_AUTHORIZED)
        self.assertFalse(context.has_data)

    def test_22a_reclassify_leaves_an_immediate_event_alone(self):
        # A push_wait timeout suppresses the terminal event, so the challenge trigger written on the spot is the only
        # staged event. Reclassifying it would destroy that record; the caller has to stage its own event instead.
        context = ConditionalAccessContext()
        trigger = context.stage(self._event("alice", AuthEventType.CHALLENGE_TRIGGERED))
        trigger.immediate = True

        self.assertIsNone(context.amendable)
        context.reclassify(AuthEventType.NOT_AUTHORIZED)
        self.assertEqual(AuthEventType.CHALLENGE_TRIGGERED, trigger.event_type)

    def test_22b_an_event_written_by_an_early_flush_stays_amendable(self):
        # /auth flushes in-view before evaluating; that must not stop a later stage from correcting the outcome.
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice", AuthEventType.LOGIN_SUCCESS))
        context.flush()

        self.assertIs(event, context.amendable)
        context.reclassify(AuthEventType.NOT_AUTHORIZED)
        self.assertEqual(AuthEventType.NOT_AUTHORIZED, event.event_type)

    def test_22c_reclassify_leaves_a_conditional_access_rejection_alone(self):
        # The gate is the innermost decorator, so the post-policies still run on its rejection response. That row is
        # the only record of why the request was refused, and relabelling it would also slip the refused request past
        # the CA_ENFORCEMENT_EVENT_TYPES guard in run_post_eval and into the lockout counters.
        for event_type in CA_ENFORCEMENT_EVENT_TYPES:
            with self.subTest(event_type=event_type):
                context = ConditionalAccessContext()
                rejection = context.stage(self._event("alice", event_type))

                self.assertTrue(context.rejected_by_conditional_access)
                self.assertIsNone(context.amendable)
                context.reclassify(AuthEventType.NOT_AUTHORIZED)
                self.assertEqual(event_type, rejection.event_type)

    def test_22d_an_ordinary_outcome_is_not_a_conditional_access_rejection(self):
        context = ConditionalAccessContext()
        context.stage(self._event("alice", AuthEventType.LOGIN_SUCCESS))
        self.assertFalse(context.rejected_by_conditional_access)

    def test_23_post_eval_without_a_staged_event_does_nothing(self):
        # Staging an event is the signal to evaluate, so a request that logged nothing evaluates nothing.
        context = ConditionalAccessContext()
        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            self.assertListEqual([], context.run_post_eval())
        evaluate.assert_not_called()

    def test_24_post_eval_does_not_repeat_the_same_classification(self):
        # /auth runs it in-view for the messages; request teardown must not repeat that same evaluation.
        context = ConditionalAccessContext()
        context.stage(self._event("alice"))
        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            evaluate.return_value = LockoutEvaluation(messages=[StageMessage("a message", MessageKind.NOTIFICATION)])
            self.assertListEqual([StageMessage("a message", MessageKind.NOTIFICATION)], context.run_post_eval())
            self.assertListEqual([], context.run_post_eval())
        self.assertEqual(1, evaluate.call_count)

    def test_24b_post_eval_runs_again_for_a_corrected_classification(self):
        # The guard is "once per classification", not "once": if a post-policy corrects the outcome after an endpoint
        # already evaluated in-view, teardown has to evaluate the correction - otherwise the engine is left having
        # judged an outcome that no longer holds.
        context = ConditionalAccessContext()
        context.stage(self._event("alice", AuthEventType.LOGIN_SUCCESS))
        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            evaluate.return_value = LockoutEvaluation()
            context.run_post_eval()
            context.reclassify(AuthEventType.NOT_AUTHORIZED)
            context.run_post_eval()
            # ... and still not a third time for the same corrected outcome.
            context.run_post_eval()

        self.assertListEqual([AuthEventType.LOGIN_SUCCESS, AuthEventType.NOT_AUTHORIZED],
                             [call.args[1] for call in evaluate.call_args_list])

    def test_25_engine_error_is_swallowed(self):
        # The evaluation only writes state the *next* request consults, so a failure must never surface on the
        # response that already completed.
        context = ConditionalAccessContext()
        context.stage(self._event("alice"))
        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies",
                        side_effect=RuntimeError("engine boom")):
            self.assertListEqual([], context.run_post_eval())

    def test_25b_a_failed_evaluation_is_retried_at_teardown(self):
        # /auth evaluates in-view and teardown evaluates again. A classification counts as evaluated only once the
        # engine returned, so a transient failure in the early call does not cost the evaluation entirely.
        context = ConditionalAccessContext()
        context.stage(self._event("alice"))
        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies",
                        side_effect=RuntimeError("engine boom")):
            self.assertListEqual([], context.run_post_eval())

        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            evaluate.return_value = LockoutEvaluation(
                messages=[StageMessage("locked", MessageKind.TIMED_RESTRICTION)], outcomes=[])
            self.assertListEqual([StageMessage("locked", MessageKind.TIMED_RESTRICTION)], context.run_post_eval())
        evaluate.assert_called_once()

    def test_26_evaluation_counts_over_a_committed_read_view(self):
        # What keeps the counts off a stale snapshot: finalize() flushes before evaluating, and that commit ends the
        # read transaction the pre-checks opened. Without it, MySQL/MariaDB REPEATABLE READ would hide from the count
        # rows a concurrent request committed since - which is why no explicit read-view reset is needed here.
        context = ConditionalAccessContext()
        context.stage(self._event("alice"))
        get_ca_session().execute(select(AuthenticationLog)).all()
        self.assertTrue(get_ca_session().in_transaction())

        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            evaluate.return_value = LockoutEvaluation()
            context.finalize()

        evaluate.assert_called_once()
        # The flush committed, so the counting started from a fresh transaction rather than the pre-check's snapshot.
        self.assertFalse(context.unwritten)

    # --- conditional-access outcomes: the outcomes a request produces ----------

    @staticmethod
    def _make_outcome(action_type: str = LockoutAction.LOCK_USER) -> ConditionalAccessOutcome:
        return ConditionalAccessOutcome(action_type=str(action_type), policy_name="p", threshold=3,
                                        event_count=3)

    def test_30_pre_auth_outcomes_wait_for_the_first_staged_event(self):
        # The pre-auth decision runs before anything is logged, so its outcomes have no row yet. They are buffered on
        # the context and taken over by the next event staged, which is the row they belong to.
        context = ConditionalAccessContext()
        context.add_outcomes([self._make_outcome()])
        self.assertEqual(1, len(context.pending_outcomes))

        event = context.stage(self._event("alice"))
        self.assertListEqual([], context.pending_outcomes)
        self.assertEqual(1, len(event.outcomes))

        self.assertTrue(context.flush())
        self.assertListEqual([str(LockoutAction.LOCK_USER)],
                             [outcome.action_type for outcome in get_outcomes(event.row_id)])

    def test_31_recorded_outcomes_are_not_written_twice(self):
        # flush() is idempotent and runs again at teardown, so an outcome already stored must be dropped from the event.
        context = ConditionalAccessContext()
        context.add_outcomes([self._make_outcome()])
        event = context.stage(self._event("alice"))
        context.flush()
        self.assertListEqual([], event.outcomes)

        context.flush()
        self.assertEqual(1, len(get_outcomes(event.row_id)))

    def test_32_outcomes_survive_a_failed_write_for_the_next_flush(self):
        # A failed history write must not lose the outcomes: they stay on the event and the next flush retries them.
        context = ConditionalAccessContext()
        context.add_outcomes([self._make_outcome()])
        event = context.stage(self._event("alice"))
        with mock.patch("privacyidea.lib.conditional_access.request_context.record_outcomes", return_value=False):
            self.assertFalse(context.flush())
        self.assertEqual(1, len(event.outcomes))

        self.assertTrue(context.flush())
        self.assertEqual(1, len(get_outcomes(event.row_id)))

    def test_33_outcomes_of_a_request_that_logs_nothing_are_dropped(self):
        # A request with no authentication event has no row to hang an outcome on - and nothing to miss: the decision is
        # derived from prior events, so the next request that does log one re-derives it.
        context = ConditionalAccessContext()
        context.add_outcomes([self._make_outcome()])
        context.finalize()

        self.assertEqual(0, get_ca_session().query(ConditionalAccessOutcome).count())

    def test_33b_post_eval_skips_an_event_conditional_access_wrote_itself(self):
        # Evaluating a rejection would let a lock feed itself: while the user is locked every rejected request would add
        # to the count. No policy could match one anyway (they are not in the trackable vocabulary), so this only saves
        # the query - but it keeps the guarantee where the evaluation happens.
        context = ConditionalAccessContext()
        context.stage(self._event("alice", AuthEventType.USER_LOCKED))
        context.flush()

        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            self.assertListEqual([], context.run_post_eval())
        evaluate.assert_not_called()

    def test_34_post_eval_records_what_the_engine_returned(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        context.flush()
        with mock.patch("privacyidea.lib.conditional_access.engine.evaluate_lockout_policies") as evaluate:
            evaluate.return_value = LockoutEvaluation(messages=[StageMessage("a message", MessageKind.NOTIFICATION)],
                                                      outcomes=[self._make_outcome(LockoutAction.PERMANENT_LOCK_USER)])
            self.assertListEqual([StageMessage("a message", MessageKind.NOTIFICATION)], context.run_post_eval())

        outcomes = get_outcomes(event.row_id)
        self.assertListEqual([str(LockoutAction.PERMANENT_LOCK_USER)], [outcome.action_type for outcome in outcomes])

    def test_40_an_unreadable_challenge_leaves_the_attempt_unresolved(self):
        # Correlating an attempt must never break the authentication it describes. A challenge store that raises leaves
        # the request without an adopted attempt, and it goes on to start one of its own.
        context = ConditionalAccessContext()
        with mock.patch("privacyidea.lib.challenge.get_challenges", side_effect=RuntimeError("challenge boom")):
            context.continue_attempt("1234567890")

        self.assertFalse(context.attempt_resolved)
        self.assertTrue(context.attempt_id)

    def test_41_no_attempt_id_outside_a_request(self):
        # A pi-manage command or a periodic task runs inside an app context but not a request, and must not be handed
        # an attempt id: the buffer lives on g, which such a run holds throughout, so every challenge it created would
        # be stamped with the *same* id and read back as one authentication attempt.
        serial = "CA_ATTEMPT_NO_REQUEST"
        self.assertFalse(has_request_context())
        self.assertIsNone(current_attempt_id())
        try:
            first = create_challenge(serial)
            second = create_challenge(serial)
            self.assertNotIn(ATTEMPT_ID_CHALLENGE_KEY, first.get_data())
            self.assertNotIn(ATTEMPT_ID_CHALLENGE_KEY, second.get_data())
        finally:
            delete_challenges(serial=serial)

    def test_42_a_request_gets_an_attempt_id(self):
        # The converse of test_41: inside a request there is an attempt to attribute a challenge to, and it is the
        # one the request's buffer holds.
        with self.app.test_request_context("/validate/check"):
            attempt_id = current_attempt_id()
            self.assertTrue(attempt_id)
            self.assertEqual(attempt_id, get_ca_context().attempt_id)
