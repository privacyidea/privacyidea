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
Unit tests for the conditional-access outcome log
(:mod:`privacyidea.lib.conditional_access.outcome_log`): turning the engine's outcomes into
``conditional_access_outcome`` rows, and the contract that every outcome belongs to an authentication-log row.
"""
from datetime import timedelta, timezone
from typing import Any

from unittest import mock

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import log_authentication_event
from privacyidea.lib.conditional_access.engine import LockoutAction
from privacyidea.lib.conditional_access.outcome_log import get_outcomes, outcome_for_stage, record_outcomes
from privacyidea.lib.conditional_access.session import get_ca_session
from privacyidea.models import ConditionalAccessOutcome, LockoutPolicy, LockoutPolicyStage, db
from privacyidea.models.conditional_access_outcome import conditional_access_outcome_column_length
from privacyidea.models.utils import utc_now

from .base import MyTestCase


def _outcome(**overrides: Any) -> ConditionalAccessOutcome:
    """An outcome carrying everything the engine always knows, so a test only states what it is about."""
    fields = {"action_type": str(LockoutAction.LOCK_USER_TEMPORARY), "policy_name": "Brute Force PIN Lockout",
              "threshold": 5, "event_count": 6}
    return ConditionalAccessOutcome(**{**fields, **overrides})


class OutcomeLogTestCase(MyTestCase):

    def tearDown(self):
        db.session.query(ConditionalAccessOutcome).delete()
        db.session.commit()
        super().tearDown()

    @staticmethod
    def _policy_and_stage() -> tuple[LockoutPolicy, LockoutPolicyStage]:
        """
        The configuration the factory copies from, as transient objects: it reads four fields and touches no session, so
        a database fixture would only add cleanup no assertion depends on.
        """
        return (LockoutPolicy(id=7, name="Brute Force PIN Lockout"),
                LockoutPolicyStage(failure_threshold=5, name="Second strike"))

    def _auth_log_row(self) -> int:
        return log_authentication_event(event_type=AuthEventType.MFA_FAIL, username="cornelius", realm="realm1",
                                       resolver="resolver1", uid="1000", source_ip="10.0.0.1")

    def test_records_one_row_per_outcome_in_order(self):
        event_id = self._auth_log_row()
        self.assertTrue(record_outcomes([_outcome(), _outcome(action_type=str(LockoutAction.EMAIL_ADMIN))], event_id))

        outcomes = get_outcomes(event_id)
        self.assertListEqual([str(LockoutAction.LOCK_USER_TEMPORARY), str(LockoutAction.EMAIL_ADMIN)],
                         [outcome.action_type for outcome in outcomes])
        self.assertListEqual([event_id, event_id], [outcome.auth_log_id for outcome in outcomes])

    def test_every_field_of_an_outcome_round_trips(self):
        event_id = self._auth_log_row()
        info = {"expires_at": "2026-08-07T12:34:56+00:00"}
        record_outcomes([_outcome(dry_run=True, stage_name="Second strike", info=info)], event_id)

        outcome = get_outcomes(event_id)[0]
        self.assertEqual(str(LockoutAction.LOCK_USER_TEMPORARY), outcome.action_type)
        self.assertTrue(outcome.dry_run)
        self.assertEqual("Brute Force PIN Lockout", outcome.policy_name)
        self.assertEqual(5, outcome.threshold)
        self.assertEqual(6, outcome.event_count)
        self.assertEqual("Second strike", outcome.stage_name)
        self.assertEqual(info, outcome.info)

    def test_outcome_for_stage_records_the_expiry_in_info(self):
        # expires_at is a typed factory parameter, but it is action-specific data stored in the row's `info` field.
        # It is serialized there as an aware ISO-8601 string, because a JSON column cannot hold a datetime object.
        policy, stage = self._policy_and_stage()
        expires_at = utc_now() + timedelta(seconds=600)

        outcome = outcome_for_stage(policy, stage, LockoutAction.LOCK_USER_TEMPORARY, 6, expires_at=expires_at)
        self.assertDictEqual({"expires_at": expires_at.replace(tzinfo=timezone.utc).isoformat()}, outcome.info)
        # An aware value is left as it is rather than re-stamped.
        aware = expires_at.replace(tzinfo=timezone.utc)
        self.assertDictEqual({"expires_at": aware.isoformat()},
                         outcome_for_stage(policy, stage, LockoutAction.BLOCK_IP_TEMPORARY, 6, expires_at=aware).info)

    def test_outcome_for_stage_leaves_info_empty_without_an_expiry(self):
        # An action with nothing of its own to record leaves the column NULL rather than an empty dict.
        policy, stage = self._policy_and_stage()
        outcome = outcome_for_stage(policy, stage, LockoutAction.EMAIL_ADMIN, 6)
        self.assertIsNone(outcome.info)

    def test_outcome_for_stage_copies_what_the_history_must_keep(self):
        # The policy name and stage name are denormalized copies so history stays readable after a rename or deletion;
        # the id is not copied: a deleted id can be reused by another policy, which would misattribute the history.
        policy, stage = self._policy_and_stage()
        outcome = outcome_for_stage(policy, stage, LockoutAction.LOCK_USER_TEMPORARY, 6, dry_run=True)

        self.assertEqual(policy.name, outcome.policy_name)
        self.assertFalse(hasattr(outcome, "policy_id"), "the outcome must not carry a policy id")
        self.assertEqual(stage.failure_threshold, outcome.threshold)
        self.assertEqual(stage.name, outcome.stage_name)
        self.assertEqual(6, outcome.event_count)
        self.assertTrue(outcome.dry_run)
        # Transient until recorded: the engine has no row to point at.
        self.assertIsNone(outcome.auth_log_id)
        self.assertIsNone(outcome.id)

    def test_an_enforced_outcome_is_not_flagged_as_dry_run(self):
        event_id = self._auth_log_row()
        record_outcomes([_outcome()], event_id)
        self.assertFalse(get_outcomes(event_id)[0].dry_run)

    def test_recording_twice_appends_rather_than_replaces(self):
        # A request can be re-evaluated (a post-policy correcting the classification reruns the engine),
        # so the first evaluation's history must survive the second.
        event_id = self._auth_log_row()
        record_outcomes([_outcome()], event_id)
        record_outcomes([_outcome(action_type=str(LockoutAction.LOCK_USER_PERMANENT))], event_id)

        self.assertListEqual([str(LockoutAction.LOCK_USER_TEMPORARY), str(LockoutAction.LOCK_USER_PERMANENT)],
                         [outcome.action_type for outcome in get_outcomes(event_id)])

    def test_no_outcomes_is_a_successful_no_op(self):
        event_id = self._auth_log_row()
        self.assertTrue(record_outcomes([], event_id))
        self.assertListEqual([], list(get_outcomes(event_id)))

    def test_outcomes_without_an_auth_log_row_are_dropped(self):
        # Every outcome belongs to the request that caused it, so a parentless outcome would be a fact about nobody.
        # A missing row is either legitimate (a poll logs no event) or a bug, but neither is fixed by storing an orphan.
        self.assertFalse(record_outcomes([_outcome()], None))
        self.assertEqual(0, get_ca_session().query(ConditionalAccessOutcome).count())

    def test_a_failing_write_is_swallowed_and_reported(self):
        # Writing history must never break the response that produced it, so a failure is logged and reported to the
        # caller, which is what lets the request context keep the outcomes for a later retry.
        event_id = self._auth_log_row()
        with mock.patch.object(get_ca_session(), "commit", side_effect=Exception("db down")):
            self.assertFalse(record_outcomes([_outcome()], event_id))
        self.assertListEqual([], list(get_outcomes(event_id)))

    def test_the_same_outcomes_can_be_retried_after_a_failed_write(self):
        # The outcomes are the engine's own objects, so a retry reuses them; a rollback expunges them from the session,
        # leaving them transient, which lets the request context keep them and retry on the next flush.
        event_id = self._auth_log_row()
        outcomes = [_outcome()]
        with mock.patch.object(get_ca_session(), "commit", side_effect=Exception("db down")):
            self.assertFalse(record_outcomes(outcomes, event_id))

        self.assertTrue(record_outcomes(outcomes, event_id))
        self.assertListEqual([str(LockoutAction.LOCK_USER_TEMPORARY)],
                             [outcome.action_type for outcome in get_outcomes(event_id)])

    def test_recording_the_same_outcome_object_twice_stores_it_once(self):
        # Once stored, an outcome is persistent, so re-handing it to the writer never duplicates the row.
        event_id = self._auth_log_row()
        outcomes = [_outcome()]
        record_outcomes(outcomes, event_id)
        record_outcomes(outcomes, event_id)
        self.assertEqual(1, len(get_outcomes(event_id)))

    def test_get_outcomes_only_returns_the_requested_row(self):
        first, second = self._auth_log_row(), self._auth_log_row()
        record_outcomes([_outcome()], first)
        record_outcomes([_outcome(action_type=str(LockoutAction.BLOCK_IP_TEMPORARY))], second)

        self.assertListEqual([str(LockoutAction.LOCK_USER_TEMPORARY)], [outcome.action_type for outcome in get_outcomes(first)])
        self.assertListEqual([str(LockoutAction.BLOCK_IP_TEMPORARY)], [outcome.action_type for outcome in get_outcomes(second)])

    def test_column_lengths_mirror_the_columns_they_copy(self):
        # The outcome stores copies of the policy configuration, each column as wide as its source.
        # That is why the writer does not truncate: a name that fits where an admin typed it fits here too.
        self.assertEqual(LockoutPolicy.__table__.c.name.type.length,
                         conditional_access_outcome_column_length["policy_name"])
        self.assertEqual(LockoutPolicyStage.__table__.c.name.type.length,
                         conditional_access_outcome_column_length["stage_name"])
