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
Unit tests for the conditional-access lockout policy engine
(:mod:`privacyidea.lib.conditional_access.engine`): the failure-count query, the
pre-check lock test, and the policy-evaluation workflow (stage selection,
de-duplication, dry-run, and the LOCK_USER / PERMANENT_LOCK_USER actions).
"""
from datetime import timedelta

from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
from privacyidea.lib.conditional_access.engine import (
    LockoutAction,
    count_user_events,
    evaluate_lockout_policies,
    is_user_locked,
    _lock_duration_seconds,
)
from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.lockout_policy import (
    LockoutPolicy,
    LockoutPolicyStage,
    LockoutStageAction,
    UserLockoutState,
)
from privacyidea.models.utils import utc_now
from .base import MyTestCase


class LockoutEngineTestCase(MyTestCase):

    def setUp(self):
        self.setUp_user_realms()
        # "cornelius" resolves to a non-empty uid in the test resolver ("root" has an
        # empty uid there), so it is a fully resolved (resolver, uid, realm) identity.
        self.user = User("cornelius", self.realm1, self.resolvername1)
        self._clear()

    def tearDown(self):
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        for model in (UserLockoutState, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    # --- fixtures -------------------------------------------------------------

    def _seed_events(self, event_type, count, timestamp=None, user=None):
        """Insert *count* authentication-log rows for *user* with an explicit timestamp."""
        user = user or self.user
        timestamp = timestamp if timestamp is not None else utc_now()
        for _ in range(count):
            db.session.add(AuthenticationLog(
                event_type=str(event_type), resolver=user.resolver, uid=user.uid,
                realm=user.realm, timestamp=timestamp))
        db.session.commit()

    def _make_policy(self, *, name, counter_type, window=3600, enabled=True, dry_run=False,
                     priority=1, stages=((3, 1, LockoutAction.LOCK_USER, 600),)):
        """
        Build a policy with its stages and one action per stage.

        :param stages: iterable of (failure_threshold, stage_priority, action_type, action_value)
        """
        policy = LockoutPolicy(name=name, counter_type_to_track=str(counter_type),
                               time_window_seconds=window, enabled=enabled, dry_run=dry_run,
                               priority=priority)
        db.session.add(policy)
        db.session.commit()
        made_stages = []
        for threshold, stage_priority, action_type, action_value in stages:
            stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=threshold,
                                       priority=stage_priority)
            db.session.add(stage)
            db.session.commit()
            db.session.add(LockoutStageAction(stage_id=stage.id, action_type=str(action_type),
                                              action_value=action_value))
            db.session.commit()
            made_stages.append(stage)
        return policy, made_stages

    def _state(self, user=None):
        user = user or self.user
        return db.session.get(UserLockoutState, (user.resolver, user.uid, user.realm))

    # --- count_user_events ----------------------------------------------------

    def test_count_user_events_window_boundary(self):
        now = utc_now()
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now)
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now - timedelta(seconds=7200))
        # Only the two recent events fall inside the 1h window.
        self.assertEqual(2, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              AuthEventType.MFA_FAIL, 3600, now=now))
        # Widening the window picks up the old one as well.
        self.assertEqual(3, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              AuthEventType.MFA_FAIL, 100000, now=now))

    def test_count_user_events_filters_event_type_and_user(self):
        self._seed_events(AuthEventType.MFA_FAIL, 2)
        self._seed_events(AuthEventType.PIN_FAIL, 5)
        self.assertEqual(2, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              AuthEventType.MFA_FAIL, 3600))
        # A different user identity is not counted.
        self.assertEqual(0, count_user_events("other", "999", self.user.realm,
                                              AuthEventType.MFA_FAIL, 3600))

    # --- is_user_locked -------------------------------------------------------

    def test_is_user_locked_no_row(self):
        self.assertFalse(is_user_locked(self.user))

    def test_is_user_locked_timed_future(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertTrue(is_user_locked(self.user))

    def test_is_user_locked_timed_expired(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=utc_now() - timedelta(seconds=600)))
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

    def test_is_user_locked_permanent(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True, lock_expires_at=None))
        db.session.commit()
        self.assertTrue(is_user_locked(self.user))

    def test_is_user_locked_flag_false(self):
        # A future expiry but is_locked=False means not locked.
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=False,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

    def test_is_user_locked_unresolved_user(self):
        self.assertFalse(is_user_locked(User()))

    # --- evaluate_lockout_policies --------------------------------------------

    def test_evaluate_triggers_lock(self):
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        state = self._state()
        self.assertIsNotNone(state)
        self.assertTrue(state.is_locked)
        self.assertIsNotNone(state.lock_expires_at)
        self.assertGreater(state.lock_expires_at, utc_now())
        self.assertTrue(is_user_locked(self.user))

    def test_evaluate_below_threshold_does_not_lock(self):
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 2)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    def test_evaluate_no_op_for_unresolved_user(self):
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        # No event_type / no resolved user must be a no-op without raising.
        evaluate_lockout_policies(self.user, None)
        evaluate_lockout_policies(User(), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    def test_evaluate_disabled_policy_skipped(self):
        self._make_policy(name="off", counter_type=AuthEventType.MFA_FAIL, enabled=False)
        self._seed_events(AuthEventType.MFA_FAIL, 5)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    def test_evaluate_non_matching_event_type_skipped(self):
        self._make_policy(name="mfa", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.PIN_FAIL, 5)
        evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL)
        self.assertIsNone(self._state())

    def test_stage_priority_selection(self):
        # priority 2 -> threshold 15 (severe), priority 1 -> threshold 5.
        _, stages = self._make_policy(
            name="tiers", counter_type=AuthEventType.MFA_FAIL,
            stages=((15, 2, LockoutAction.LOCK_USER, 1800),
                    (5, 1, LockoutAction.LOCK_USER, 600)))
        severe_stage, mild_stage = stages[0], stages[1]

        self._seed_events(AuthEventType.MFA_FAIL, 6)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        # 6 >= 5 but < 15 -> the milder stage is the highest-priority one that matches.
        self.assertEqual(mild_stage.id, self._state().last_stage_triggered)

        # Cross the severe threshold; the severe stage now wins and re-fires (different stage).
        self._seed_events(AuthEventType.MFA_FAIL, 9)  # total 15
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertEqual(severe_stage.id, self._state().last_stage_triggered)

    def test_dedup_suppresses_repeat_within_window(self):
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        # Tamper with the expiry, then re-evaluate the same stage within the window:
        # the de-dup must skip the action and leave our value untouched.
        sentinel = utc_now() + timedelta(seconds=99999)
        state = self._state()
        state.lock_expires_at = sentinel
        db.session.commit()
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertEqual(sentinel, self._state().lock_expires_at)

    def test_dedup_refires_after_window(self):
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL, window=3600)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        # Backdate last_updated beyond the window so the de-dup no longer applies, and move the
        # expiry to a sentinel; re-evaluation must re-fire and overwrite the sentinel.
        sentinel = utc_now() + timedelta(seconds=99999)
        state = self._state()
        state.lock_expires_at = sentinel
        state.last_updated = utc_now() - timedelta(seconds=4000)
        db.session.commit()
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertLess(self._state().lock_expires_at, sentinel)

    def test_dry_run_writes_no_state(self):
        self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        self._seed_events(AuthEventType.MFA_FAIL, 5)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())
        self.assertFalse(is_user_locked(self.user))

    def test_permanent_lock_action(self):
        self._make_policy(name="perm", counter_type=AuthEventType.MFA_FAIL,
                          stages=((3, 1, LockoutAction.PERMANENT_LOCK_USER, None),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        state = self._state()
        self.assertTrue(state.is_locked)
        self.assertIsNone(state.lock_expires_at)
        self.assertTrue(is_user_locked(self.user))

    def test_permanent_lock_not_downgraded_to_timed(self):
        # Pre-existing permanent lock (set by a higher-severity stage).
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=None, last_stage_triggered=None))
        db.session.commit()
        # A timed LOCK_USER policy now tries to lock the same user.
        self._make_policy(name="timed", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        # The permanent lock must remain permanent (lock_expires_at stays None).
        self.assertIsNone(self._state().lock_expires_at)
        self.assertTrue(is_user_locked(self.user))

    def test_invalid_duration_action_skipped(self):
        self._make_policy(name="baddur", counter_type=AuthEventType.MFA_FAIL,
                          stages=((3, 1, LockoutAction.LOCK_USER, None),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    def test_unknown_action_type_skipped(self):
        self._make_policy(name="weird", counter_type=AuthEventType.MFA_FAIL,
                          stages=((3, 1, "TELEPORT_USER", None),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        # Unknown action types are logged and skipped, not raised.
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    # --- _lock_duration_seconds -----------------------------------------------

    def test_lock_duration_parsing(self):
        self.assertEqual(600, _lock_duration_seconds(600))
        self.assertEqual(600, _lock_duration_seconds("600"))
        self.assertEqual(300, _lock_duration_seconds({"duration_seconds": 300}))
        self.assertEqual(120, _lock_duration_seconds({"duration": 120}))
        for invalid in (None, 0, -5, True, False, "abc", {}, {"foo": 1}):
            self.assertIsNone(_lock_duration_seconds(invalid), invalid)
