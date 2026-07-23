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
from email import message_from_string

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.engine import (
    AccessDecision,
    LockoutAction,
    LockoutTarget,
    count_user_events,
    count_distinct_users_for_ip,
    evaluate_access_decision,
    evaluate_lockout_policies,
    is_user_locked,
    is_ip_blocked,
    is_ip_never_block,
    get_ip_block,
    _lock_duration_seconds,
    _safe_format,
    _resolve_admin_recipients,
)
from privacyidea.lib.conditional_access.lockout_policy import create_lockout_policy
from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config, SYSCONF
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.user import User
from privacyidea.models import Admin, db
from privacyidea.models.lockout_policy import (
    BlockList,
    LockoutPolicy,
    LockoutPolicyStage,
    LockoutStageAction,
    UserLockoutState,
)
from privacyidea.models.utils import utc_now
from . import smtpmock
from .conditional_access_lockout_base import LockoutTestCase


class LockoutEngineTestCase(LockoutTestCase):

    def _make_policy(self, *, name, counter_type, window=3600, enabled=True, dry_run=False,
                     priority=1, target=LockoutTarget.USER,
                     stages=((3, 1, LockoutAction.LOCK_USER, 600),)):
        """
        Create a policy through the real CRUD path (:func:`create_lockout_policy`)
        and return ``(policy, stages)`` re-fetched from the DB.

        :param stages: iterable of (failure_threshold, stage_priority, action_type, action_value)
        """
        counter_types = counter_type if isinstance(counter_type, (list, tuple)) else [counter_type]
        stage_dicts = [
            {"failure_threshold": threshold, "priority": stage_priority,
             "actions": [{"action_type": action_type, "action_value": action_value}]}
            for threshold, stage_priority, action_type, action_value in stages
        ]
        policy_id = create_lockout_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=[str(t) for t in counter_types],
            stages=stage_dicts, target=target, enabled=enabled, dry_run=dry_run, priority=priority)
        policy = db.session.get(LockoutPolicy, policy_id)
        return policy, list(policy.stages)

    # --- count_distinct_users_for_ip (spraying signal) ------------------------

    def test_count_distinct_users_for_ip_counts_users_not_rows(self):
        ip = "10.0.0.1"
        # 3 users, 2 failures each from the same IP -> 3 distinct users, not 6 rows.
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3, per_user=2)
        self.assertEqual(3, count_distinct_users_for_ip(ip, [AuthEventType.PASSWORD_FAIL], 300))

    def test_count_distinct_users_for_ip_filters_ip_and_type(self):
        self._seed_ip_events("10.0.0.1", AuthEventType.PASSWORD_FAIL, n_users=4)
        # A different IP and a different event type must not contribute.
        self._seed_ip_events("10.0.0.2", AuthEventType.PASSWORD_FAIL, n_users=5)
        self._seed_ip_events("10.0.0.1", AuthEventType.MFA_FAIL, n_users=7)
        self.assertEqual(4, count_distinct_users_for_ip("10.0.0.1", [AuthEventType.PASSWORD_FAIL], 300))

    def test_count_distinct_users_for_ip_window_boundary(self):
        ip = "10.0.0.1"
        now = utc_now()
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=2, timestamp=now)
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3,
                             timestamp=now - timedelta(seconds=7200))
        self.assertEqual(2, count_distinct_users_for_ip(ip, [AuthEventType.PASSWORD_FAIL], 300, window_end=now))

    # --- source_ip target evaluation (spraying) -------------------------------

    def test_spraying_policy_blocks_ip(self):
        ip = "203.0.113.7"
        self._make_policy(name="spray", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP,
                          stages=((20, 1, LockoutAction.BLOCK_IP, {"duration_seconds": 3600}),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=20)
        self.assertFalse(is_ip_blocked(ip))
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        self.assertTrue(is_ip_blocked(ip))

    def test_spraying_policy_below_threshold_does_not_block(self):
        ip = "203.0.113.8"
        self._make_policy(name="spray", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP,
                          stages=((20, 1, LockoutAction.BLOCK_IP, {"duration_seconds": 3600}),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=19)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        self.assertFalse(is_ip_blocked(ip))

    def test_spraying_policy_without_source_ip_is_skipped(self):
        self._make_policy(name="spray", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP,
                          stages=((1, 1, LockoutAction.BLOCK_IP, {"duration_seconds": 3600}),))
        self._seed_ip_events("203.0.113.9", AuthEventType.PASSWORD_FAIL, n_users=5)
        # No source IP on the current request -> the IP-targeted policy cannot act.
        self.assertEqual([], evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=None))

    # --- count_user_events ----------------------------------------------------

    def test_count_user_events_window_boundary(self):
        now = utc_now()
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now)
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now - timedelta(seconds=7200))
        # Only the two recent events fall inside the 1h window.
        self.assertEqual(2, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600, window_end=now))
        # Widening the window picks up the old one as well.
        self.assertEqual(3, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 100000, window_end=now))

    def test_count_user_events_excludes_future_rows(self):
        now = utc_now()
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now - timedelta(seconds=60))
        # A row time-stamped after `now` (clock skew, a concurrent insert, or an
        # explicitly historical `now`) must not be counted: the window ends at `now`.
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now + timedelta(seconds=60))
        self.assertEqual(2, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600, window_end=now))

    def test_count_user_events_filters_event_type_and_user(self):
        self._seed_events(AuthEventType.MFA_FAIL, 2)
        self._seed_events(AuthEventType.PIN_FAIL, 5)
        self.assertEqual(2, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600))
        # A different user identity is not counted.
        self.assertEqual(0, count_user_events("other", "999", self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600))

    def test_count_user_events_since_last_success_floors_at_login(self):
        now = utc_now()
        # Two failures, then a successful login, then one more failure.
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now - timedelta(seconds=300))
        self._seed_events(AuthEventType.LOGIN_SUCCESS, 1, timestamp=now - timedelta(seconds=200))
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now - timedelta(seconds=100))
        args = (self.user.resolver, self.user.uid, self.user.realm, [AuthEventType.MFA_FAIL], 3600)
        # Without the reset, all three failures are in the window.
        self.assertEqual(3, count_user_events(*args, window_end=now))
        # With the reset, only the failure after the successful login counts.
        self.assertEqual(1, count_user_events(*args, window_end=now, since_last_success=True))

    def test_count_user_events_since_last_success_no_login_counts_all(self):
        now = utc_now()
        self._seed_events(AuthEventType.MFA_FAIL, 3, timestamp=now - timedelta(seconds=100))
        # No LOGIN_SUCCESS in the window -> the floor does not apply, count is unchanged.
        self.assertEqual(3, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600, window_end=now,
                                              since_last_success=True))

    def test_count_user_events_since_last_success_ignores_login_outside_window(self):
        now = utc_now()
        # The successful login is older than the window, so it must not floor the count.
        self._seed_events(AuthEventType.LOGIN_SUCCESS, 1, timestamp=now - timedelta(seconds=7200))
        self._seed_events(AuthEventType.MFA_FAIL, 3, timestamp=now - timedelta(seconds=100))
        self.assertEqual(3, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600, window_end=now,
                                              since_last_success=True))

    def test_count_user_events_combined_types(self):
        # A list of event types is counted together (OR-sum), not per type; an
        # untracked type does not contribute.
        self._seed_events(AuthEventType.PASSWORD_FAIL, 2)
        self._seed_events(AuthEventType.TOKEN_ONLY_FAIL, 3)
        self._seed_events(AuthEventType.MFA_FAIL, 4)
        args = (self.user.resolver, self.user.uid, self.user.realm)
        self.assertEqual(5, count_user_events(
            *args, [AuthEventType.PASSWORD_FAIL, AuthEventType.TOKEN_ONLY_FAIL], 3600))
        # A single-element list counts just that type.
        self.assertEqual(2, count_user_events(*args, [AuthEventType.PASSWORD_FAIL], 3600))

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

    # --- is_ip_blocked --------------------------------------------------------

    def test_is_ip_blocked_no_row(self):
        self.assertFalse(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_timed_future(self):
        db.session.add(BlockList(ip="203.0.113.5", is_blocked=True,
                                 block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertTrue(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_timed_expired(self):
        db.session.add(BlockList(ip="203.0.113.5", is_blocked=True,
                                 block_expires_at=utc_now() - timedelta(seconds=600)))
        db.session.commit()
        self.assertFalse(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_permanent(self):
        db.session.add(BlockList(ip="203.0.113.5", is_blocked=True, block_expires_at=None))
        db.session.commit()
        self.assertTrue(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_flag_false(self):
        # A future expiry but is_blocked=False (admin lifted it) means not blocked.
        db.session.add(BlockList(ip="203.0.113.5", is_blocked=False,
                                 block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertFalse(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_empty_ip(self):
        # A request without a resolvable source IP is never blocked.
        self.assertFalse(is_ip_blocked(None))
        self.assertFalse(is_ip_blocked(""))

    # --- get_ip_block ---------------------------------------------------------

    def test_get_ip_block_none_when_not_blocked(self):
        self.assertIsNone(get_ip_block("203.0.113.5"))
        self.assertIsNone(get_ip_block(None))

    def test_get_ip_block_timed_reports_remaining(self):
        now = utc_now()
        db.session.add(BlockList(ip="203.0.113.5", is_blocked=True,
                                 block_expires_at=now + timedelta(seconds=600)))
        db.session.commit()
        block = get_ip_block("203.0.113.5", now=now)
        self.assertEqual(False, block.permanent, block)
        self.assertEqual(600, block.seconds_remaining, block)
        self.assertIsNotNone(block.expires_at, block)

    def test_get_ip_block_expired_reads_as_unblocked(self):
        db.session.add(BlockList(ip="203.0.113.5", is_blocked=True,
                                 block_expires_at=utc_now() - timedelta(seconds=1)))
        db.session.commit()
        self.assertIsNone(get_ip_block("203.0.113.5"))

    def test_get_ip_block_permanent(self):
        db.session.add(BlockList(ip="203.0.113.5", is_blocked=True, block_expires_at=None))
        db.session.commit()
        block = get_ip_block("203.0.113.5")
        self.assertEqual(True, block.permanent, block)
        self.assertIsNone(block.seconds_remaining, block)
        self.assertIsNone(block.expires_at, block)

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

    def test_evaluate_combined_count_across_tracked_types(self):
        # A policy tracking several types locks on the *combined* count: 2 + 1 = 3
        # reaches the threshold even though neither type alone does.
        self._make_policy(name="combo",
                          counter_type=[AuthEventType.PASSWORD_FAIL, AuthEventType.MFA_FAIL])
        self._seed_events(AuthEventType.PASSWORD_FAIL, 2)
        self._seed_events(AuthEventType.MFA_FAIL, 1)
        # The current request is an MFA_FAIL — one of the tracked types.
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_evaluate_untracked_current_event_skips_policy(self):
        # The policy only reacts when the *current* event type is one it tracks,
        # even if enough events of its tracked types already exist.
        self._make_policy(name="combo",
                          counter_type=[AuthEventType.PASSWORD_FAIL, AuthEventType.PIN_FAIL])
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3)
        # MFA_FAIL is not tracked by this policy -> skipped, no lock.
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())
        # A tracked type triggers it.
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL)
        self.assertTrue(is_user_locked(self.user))

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

    def test_successful_login_resets_lock_counter(self):
        # A completed login clears the accumulated failures: the threshold then
        # applies to failures *after* the login, so a single later typo does not
        # re-lock a user who already authenticated successfully.
        now = utc_now()
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3, timestamp=now - timedelta(seconds=300))
        self._seed_events(AuthEventType.LOGIN_SUCCESS, 1, timestamp=now - timedelta(seconds=200))

        # One failure after the successful login: 1 < 3 -> not locked, the three
        # pre-login failures no longer count.
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now - timedelta(seconds=100))
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, now=now)
        self.assertIsNone(self._state())
        self.assertFalse(is_user_locked(self.user))

        # Two more post-login failures reach the threshold again (1 + 2 = 3) -> locked.
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now - timedelta(seconds=50))
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, now=now)
        self.assertTrue(is_user_locked(self.user))

    def test_dedup_does_not_survive_lock_expiry(self):
        # The de-dup throttles repeats within ONE incident; an expired lock ends
        # the incident. Regression: the de-dup used to key only on (stage,
        # last_updated within window), so once the lock ran out the user could
        # fail freely for the rest of the window without ever being re-locked.
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

        # The lock runs out while the original failures are still in the window.
        state = self._state()
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # The next failure trips the same stage again and must re-lock the user.
        self._seed_events(AuthEventType.MFA_FAIL, 1)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_dedup_does_not_survive_admin_unlock(self):
        # An admin lifting the lock (is_locked=False) ends the incident just like
        # an expiry: the next in-window failure is a new incident and must re-lock.
        # Regression: the de-dup used to ignore is_locked, so after an admin unlock
        # the same stage stayed suppressed for the rest of the window.
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

        # Admin lifts the lock without deleting the row (last_stage / last_updated remain).
        state = self._state()
        state.is_locked = False
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # The next failure trips the same stage again and must re-lock the user.
        self._seed_events(AuthEventType.MFA_FAIL, 1)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

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
        # A corrupt/legacy row with an unknown action type must be skipped by the
        # engine, not raise. The CRUD rejects such a value, so this invalid state
        # is built directly (simulating a bad DB row) rather than via the lib.
        policy = LockoutPolicy(name="weird", counter_types_to_track=["MFA_FAIL"],
                               time_window_seconds=3600, enabled=True, dry_run=False,
                               priority=1, target=str(LockoutTarget.USER))
        db.session.add(policy)
        db.session.commit()
        stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=3, priority=1)
        db.session.add(stage)
        db.session.commit()
        db.session.add(LockoutStageAction(stage_id=stage.id, action_type="TELEPORT_USER", action_value=None))
        db.session.commit()
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        # Unknown action types are logged and skipped, not raised.
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    # --- never-block allowlist ------------------------------------------------

    def test_loopback_is_never_block_by_default(self):
        self.assertTrue(is_ip_never_block("127.0.0.1"))
        self.assertTrue(is_ip_never_block("127.5.6.7"))
        self.assertTrue(is_ip_never_block("::1"))

    def test_normal_ip_is_not_never_block(self):
        self.assertFalse(is_ip_never_block("203.0.113.7"))

    def test_empty_or_unparseable_ip_is_never_block(self):
        # Fail safe: never block an address the engine cannot positively identify.
        self.assertTrue(is_ip_never_block(None))
        self.assertTrue(is_ip_never_block(""))
        self.assertTrue(is_ip_never_block("not-an-ip"))

    def test_configured_cidr_is_never_block(self):
        set_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK, "203.0.113.0/24, 198.51.100.5")
        try:
            self.assertTrue(is_ip_never_block("203.0.113.7"))
            self.assertTrue(is_ip_never_block("198.51.100.5"))
            self.assertFalse(is_ip_never_block("198.51.100.6"))
            # The built-in loopback default still applies alongside the config.
            self.assertTrue(is_ip_never_block("127.0.0.1"))
        finally:
            delete_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK)

    def test_invalid_config_entry_ignored(self):
        set_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK, "garbage, 203.0.113.0/24")
        try:
            self.assertTrue(is_ip_never_block("203.0.113.7"))
            self.assertFalse(is_ip_never_block("198.51.100.5"))
        finally:
            delete_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK)

    def test_block_ip_action_skips_never_block_ip(self):
        # A BLOCK_IP action must never write a block for a never-block IP (loopback).
        self._make_policy(name="blockloop", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.BLOCK_IP, 900),))
        self._seed_ip_events("127.0.0.1", AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip="127.0.0.1")
        self.assertEqual(0, db.session.query(BlockList).count())
        self.assertFalse(is_ip_blocked("127.0.0.1"))

    def test_allowlisted_ip_block_row_is_not_enforced(self):
        # Even with an existing block row, an allowlisted IP reads as not blocked, so
        # adding an IP to the allowlist immediately lifts a stale or mistaken block.
        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True,
                                 block_expires_at=utc_now() + timedelta(seconds=900)))
        db.session.commit()
        self.assertTrue(is_ip_blocked("203.0.113.7"))
        set_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK, "203.0.113.0/24")
        try:
            self.assertFalse(is_ip_blocked("203.0.113.7"))
            self.assertIsNone(get_ip_block("203.0.113.7"))
        finally:
            delete_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK)

    # --- BLOCK_IP action ------------------------------------------------------

    def test_block_ip_action_blocks_source_ip(self):
        ip = "203.0.113.7"
        _, stages = self._make_policy(
            name="blockip", counter_type=AuthEventType.PASSWORD_FAIL,
            target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.BLOCK_IP, 900),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        block = self._block(ip)
        self.assertIsNotNone(block)
        self.assertTrue(block.is_blocked)
        self.assertIsNotNone(block.block_expires_at)
        self.assertGreater(block.block_expires_at, utc_now())
        # The originating stage and policy name are recorded for de-dup / auditing.
        self.assertEqual(stages[0].id, block.last_stage_triggered)
        self.assertEqual("blockip", block.reason)
        self.assertTrue(is_ip_blocked(ip))
        # A BLOCK_IP-only stage writes no user lock.
        self.assertIsNone(self._state())

    def test_block_ip_action_without_source_ip_skipped(self):
        # No source IP on the request -> the source-IP policy cannot act; skipped, not raised.
        self._make_policy(name="blocknoip", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.BLOCK_IP, 900),))
        self._seed_ip_events("203.0.113.7", AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=None)
        self.assertEqual(0, db.session.query(BlockList).count())

    def test_block_ip_action_invalid_duration_skipped(self):
        ip = "203.0.113.7"
        self._make_policy(name="blockbaddur", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.BLOCK_IP, None),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        self.assertIsNone(self._block(ip))

    def test_block_ip_does_not_downgrade_permanent_block(self):
        ip = "203.0.113.7"
        # Pre-existing permanent block (block_expires_at is None).
        db.session.add(BlockList(ip=ip, is_blocked=True, block_expires_at=None))
        db.session.commit()
        self._make_policy(name="blocktimed", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.BLOCK_IP, 900),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        # The permanent block must remain permanent (block_expires_at stays None).
        self.assertIsNone(self._block(ip).block_expires_at)
        self.assertTrue(is_ip_blocked(ip))

    def test_permanent_block_ip_action(self):
        ip = "203.0.113.7"
        # Mirror of PERMANENT_LOCK_USER: a permanent IP block (block_expires_at None).
        self._make_policy(name="permblock", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=((3, 1, LockoutAction.PERMANENT_BLOCK_IP, None),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        block = self._block(ip)
        self.assertIsNotNone(block)
        self.assertTrue(block.is_blocked)
        self.assertIsNone(block.block_expires_at)
        self.assertTrue(is_ip_blocked(ip))

    def test_permanent_block_ip_ignores_action_value(self):
        ip = "203.0.113.7"
        # action_value is irrelevant for the permanent variant: even a "valid"
        # duration does not make it timed.
        self._make_policy(name="permblockdur", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=((3, 1, LockoutAction.PERMANENT_BLOCK_IP, 900),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        self.assertIsNone(self._block(ip).block_expires_at)

    def test_permanent_block_ip_without_source_ip_skipped(self):
        # Like BLOCK_IP, a request with no source IP is logged and skipped, not raised.
        self._make_policy(name="permblocknoip", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=((3, 1, LockoutAction.PERMANENT_BLOCK_IP, None),))
        self._seed_ip_events("203.0.113.7", AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=None)
        self.assertEqual(0, db.session.query(BlockList).count())

    def test_block_ip_dedup_suppresses_repeat_within_window(self):
        # An IP-blocking stage de-dups on its BlockList row: a repeat trigger
        # within the window must not re-run the action.
        ip = "203.0.113.7"
        self._make_policy(name="blockip", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.BLOCK_IP, 900),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        # Tamper with the expiry, then re-evaluate within the window: the de-dup
        # must skip the action and leave our sentinel untouched.
        sentinel = utc_now() + timedelta(seconds=99999)
        block = self._block(ip)
        block.block_expires_at = sentinel
        db.session.commit()
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        self.assertEqual(sentinel, self._block(ip).block_expires_at)

    def test_block_ip_dedup_does_not_survive_block_expiry(self):
        # Mirror of test_dedup_does_not_survive_lock_expiry for the IP dimension:
        # an expired block ends the incident, so the next failure re-fires and
        # refreshes the block.
        ip = "203.0.113.7"
        self._make_policy(name="blockip", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.BLOCK_IP, 900),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        # The block runs out while the failures are still in the window.
        block = self._block(ip)
        block.block_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_ip_blocked(ip))
        # A further distinct user re-fires the same stage and must re-block the IP.
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=1, start=3)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip)
        self.assertTrue(is_ip_blocked(ip))

    def test_source_ip_policy_fires_for_unresolved_user(self):
        # A source-IP policy must still act when the current request's user is
        # unresolved (unknown username) - that is the spraying/enumeration case.
        # A user-target policy in the same run stays a no-op for the unknown user.
        ip = "203.0.113.60"
        self._make_policy(name="spray", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP,
                          stages=((3, 1, LockoutAction.BLOCK_IP, {"duration_seconds": 3600}),))
        self._make_policy(name="userlock", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=((3, 1, LockoutAction.LOCK_USER, 60),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(User(), AuthEventType.PASSWORD_FAIL, source_ip=ip)
        self.assertTrue(is_ip_blocked(ip), "source-IP policy did not fire for an unresolved user")
        self.assertEqual(0, db.session.query(UserLockoutState).count(),
                         "user policy wrote lock state for an unresolved user")

    # --- multiple policies on one request -------------------------------------

    def test_multiple_policies_fire_together(self):
        # Several enabled policies of different targets trip on one request: a
        # per-user timed lock (user target, threshold 5) plus a timed and a
        # permanent IP block (source_ip target, threshold 7). All apply, and the
        # permanent block wins over the timed one regardless of evaluation order
        # (cross-policy, same request).
        ip = "203.0.113.50"
        self._make_policy(name="lock", counter_type=AuthEventType.PIN_FAIL, priority=10,
                          stages=((5, 1, LockoutAction.LOCK_USER, 60),))
        self._make_policy(name="blocktimed", counter_type=AuthEventType.PIN_FAIL, priority=10,
                          target=LockoutTarget.SOURCE_IP, stages=((7, 1, LockoutAction.BLOCK_IP, 60),))
        self._make_policy(name="blockperm", counter_type=AuthEventType.PIN_FAIL, priority=4,
                          target=LockoutTarget.SOURCE_IP,
                          stages=((7, 1, LockoutAction.PERMANENT_BLOCK_IP, None),))
        # 5 failures for the current user (trips the per-user lock) plus 7 distinct
        # users from the IP (trips both IP-block policies).
        self._seed_events(AuthEventType.PIN_FAIL, 5)
        self._seed_ip_events(ip, AuthEventType.PIN_FAIL, n_users=7)
        evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL, source_ip=ip)
        # user locked with a timeout
        state = self._state()
        self.assertIsNotNone(state)
        self.assertTrue(state.is_locked)
        self.assertIsNotNone(state.lock_expires_at)
        # IP blocked permanently: the timed block did not downgrade the permanent one
        block = self._block(ip)
        self.assertIsNotNone(block)
        self.assertTrue(block.is_blocked)
        self.assertIsNone(block.block_expires_at)
        self.assertTrue(is_ip_blocked(ip))

    # --- evaluate_access_decision (ALLOW / DENY) ------------------------------

    def test_access_decision_no_policies_is_continue(self):
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user))

    def test_access_decision_deny_when_threshold_met(self):
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user))
        # DENY is stateless: it persists no lockout state.
        self.assertIsNone(self._state())

    def test_access_decision_below_threshold_is_continue(self):
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 2)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user))

    def test_access_decision_denies_on_combined_count(self):
        # The pre-auth decision also counts all tracked types together: 2 + 2 = 4
        # crosses the threshold of 3, so the request is denied.
        self._make_policy(name="deny",
                          counter_type=[AuthEventType.PASSWORD_FAIL, AuthEventType.MFA_FAIL],
                          stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 2)
        self._seed_events(AuthEventType.MFA_FAIL, 2)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user))

    def test_access_decision_does_not_reset_on_success(self):
        # Unlike the lock, the DENY decision counts every failure in the raw
        # window: a successful login in between does NOT clear it (it self-heals
        # only as the failures age out). Pins the "lock only" reset scope.
        now = utc_now()
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3, timestamp=now - timedelta(seconds=300))
        self._seed_events(AuthEventType.LOGIN_SUCCESS, 1, timestamp=now - timedelta(seconds=200))
        # The three pre-login failures still trigger DENY despite the login.
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user, now=now))

    def test_access_decision_allow_threshold_zero_is_default_allow(self):
        # A stage with threshold 0 always matches -> default allow, no events needed.
        self._make_policy(name="allow", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=((0, 1, LockoutAction.ALLOW, None),))
        self.assertEqual(AccessDecision.ALLOW, evaluate_access_decision(self.user))

    def test_access_decision_higher_priority_allow_overrides_deny(self):
        # An ALLOW policy at higher precedence (lower priority number) wins over a
        # DENY with a higher number.
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL, priority=10,
                          stages=((3, 1, LockoutAction.DENY, None),))
        self._make_policy(name="allow", counter_type=AuthEventType.PASSWORD_FAIL, priority=1,
                          stages=((0, 1, LockoutAction.ALLOW, None),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.ALLOW, evaluate_access_decision(self.user))

    def test_access_decision_higher_priority_deny_overrides_allow(self):
        self._make_policy(name="allow", counter_type=AuthEventType.PASSWORD_FAIL, priority=10,
                          stages=((0, 1, LockoutAction.ALLOW, None),))
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL, priority=1,
                          stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user))

    def test_access_decision_ignores_lockout_only_stage(self):
        # A LOCK_USER stage is a post-response side effect, not a pre-auth decision.
        self._make_policy(name="lock", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=((3, 1, LockoutAction.LOCK_USER, 600),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user))

    def test_access_decision_dry_run_not_enforced(self):
        self._make_policy(name="drydeny", counter_type=AuthEventType.PASSWORD_FAIL, dry_run=True,
                          stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user))

    def test_access_decision_disabled_policy_skipped(self):
        self._make_policy(name="offdeny", counter_type=AuthEventType.PASSWORD_FAIL, enabled=False,
                          stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user))

    def test_access_decision_unresolved_user_is_continue(self):
        self._make_policy(name="allow", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=((0, 1, LockoutAction.ALLOW, None),))
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(User()))

    def test_access_decision_both_actions_on_stage_denies(self):
        # A stage misconfigured with both ALLOW and DENY fails closed (DENY wins).
        _, stages = self._make_policy(name="both", counter_type=AuthEventType.PASSWORD_FAIL,
                                      stages=((3, 1, LockoutAction.ALLOW, None),))
        db.session.add(LockoutStageAction(stage_id=stages[0].id,
                                          action_type=str(LockoutAction.DENY), action_value=None))
        db.session.commit()
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user))

    # --- evaluate_access_decision, source-IP target ---------------------------

    def test_access_decision_source_ip_deny(self):
        # An IP that sprayed >= threshold distinct users is denied pre-auth.
        ip = "203.0.113.30"
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user, source_ip=ip))

    def test_access_decision_source_ip_deny_for_unresolved_user(self):
        # IP decisions fire regardless of whether the current user resolved -
        # that is the point of an IP-scoped DENY (spraying/enumeration).
        ip = "203.0.113.31"
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(User(), source_ip=ip))

    def test_access_decision_source_ip_below_threshold_continues(self):
        ip = "203.0.113.32"
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=2)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user, source_ip=ip))

    def test_access_decision_source_ip_never_block_is_exempt(self):
        # A never-block IP (loopback) is never denied by an IP policy, mirroring BLOCK_IP.
        ip = "127.0.0.1"
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user, source_ip=ip))

    def test_access_decision_source_ip_without_ip_continues(self):
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP, stages=((3, 1, LockoutAction.DENY, None),))
        self._seed_ip_events("203.0.113.33", AuthEventType.PASSWORD_FAIL, n_users=5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user, source_ip=None))

    # --- _lock_duration_seconds -----------------------------------------------

    def test_lock_duration_parsing(self):
        self.assertEqual(600, _lock_duration_seconds(600))
        self.assertEqual(600, _lock_duration_seconds("600"))
        self.assertEqual(300, _lock_duration_seconds({"duration_seconds": 300}))
        self.assertEqual(120, _lock_duration_seconds({"duration": 120}))
        for invalid in (None, 0, -5, True, False, "abc", {}, {"foo": 1}):
            self.assertIsNone(_lock_duration_seconds(invalid), invalid)

    # --- EMAIL_ADMIN / EMAIL_USER actions -------------------------------------

    @smtpmock.activate
    def test_email_user_action_sends_to_user(self):
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailuser", counter_type=AuthEventType.MFA_FAIL,
                stages=((3, 1, LockoutAction.EMAIL_USER,
                         {"smtp_identifier": "lockoutmail",
                          "subject": "Locked: {username}",
                          "body": "{username}@{realm} locked after {count} failures."}),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, source_ip="10.0.0.9")

            user_email = self.user.info.get("email")
            self.assertTrue(user_email, "test user must resolve to an email address")
            self.assertEqual([user_email], smtpmock.get_sent_recipient())
            parsed = message_from_string(smtpmock.get_sent_message())
            # {tags} are substituted in both subject and body.
            self.assertEqual("Locked: cornelius", parsed["Subject"])
            body = parsed.get_payload(decode=True).decode("utf-8")
            self.assertEqual(f"cornelius@{self.user.realm} locked after 3 failures.", body)
            # A pure notification action writes no lockout state.
            self.assertIsNone(self._state())
        finally:
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_admin_action_sends_to_internal_admins(self):
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        db.session.add(Admin(username="ca_adm1", email="adm1@example.com"))
        db.session.add(Admin(username="ca_adm2", email="adm2@example.com"))
        db.session.add(Admin(username="ca_noemail", email=None))
        db.session.commit()
        try:
            self._make_policy(
                name="mailadmin", counter_type=AuthEventType.MFA_FAIL,
                stages=((3, 1, LockoutAction.EMAIL_ADMIN,
                         {"smtp_identifier": "lockoutmail",
                          "recipient_group": "internal_admins",
                          "subject": "{username} locked",
                          "body": "{count} failures in realm {realm}."}),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
            # Both admins with an email are notified in one message; the email-less admin is skipped.
            recipients = set(smtpmock.get_sent_recipient())
            self.assertTrue({"adm1@example.com", "adm2@example.com"}.issubset(recipients), recipients)
        finally:
            Admin.query.filter(
                Admin.username.in_(["ca_adm1", "ca_adm2", "ca_noemail"])).delete(synchronize_session=False)
            db.session.commit()
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_admin_explicit_recipient_list(self):
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailadmin2", counter_type=AuthEventType.MFA_FAIL,
                stages=((3, 1, LockoutAction.EMAIL_ADMIN,
                         {"smtp_identifier": "lockoutmail",
                          "recipient_group": "soc@example.com, ciso@example.com",
                          "subject": "alert", "body": "alert"}),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
            self.assertEqual(["soc@example.com", "ciso@example.com"], smtpmock.get_sent_recipient())
        finally:
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_action_missing_config_is_skipped(self):
        # No subject/body in action_value -> the action is logged and skipped, never sent or raised.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailbad", counter_type=AuthEventType.MFA_FAIL,
                stages=((3, 1, LockoutAction.EMAIL_USER, {"smtp_identifier": "lockoutmail"}),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
            self.assertIsNone(smtpmock.get_sent_message())
        finally:
            delete_smtpserver("lockoutmail")

    def test_email_failure_does_not_break_other_actions(self):
        # A stage that both locks the user and emails them: the email points at an
        # unknown SMTP server, so sending raises. Per-action guarding must keep the
        # LOCK_USER write intact.
        _, stages = self._make_policy(
            name="lockandmail", counter_type=AuthEventType.MFA_FAIL,
            stages=((3, 1, LockoutAction.LOCK_USER, 600),))
        db.session.add(LockoutStageAction(
            stage_id=stages[0].id, action_type=str(LockoutAction.EMAIL_USER),
            action_value={"smtp_identifier": "does-not-exist", "subject": "x", "body": "x"}))
        db.session.commit()
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        # Must not raise even though the mail action fails.
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
        state = self._state()
        self.assertIsNotNone(state)
        self.assertTrue(state.is_locked)

    @smtpmock.activate
    def test_email_action_returns_login_notice(self):
        # A sent EMAIL_* action returns a user-facing notice for the login screen.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailnotice", counter_type=AuthEventType.MFA_FAIL,
                stages=((3, 1, LockoutAction.EMAIL_ADMIN,
                         {"smtp_identifier": "lockoutmail", "recipient_group": "soc@example.com",
                          "subject": "s", "body": "b"}),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            notices = evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL)
            self.assertEqual(["Your administrator has been notified by email."], notices)
        finally:
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_action_custom_login_notice_with_tags(self):
        # An admin-supplied login_notice template overrides the default and is {tag}-rendered.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailnotice2", counter_type=AuthEventType.MFA_FAIL,
                stages=((3, 1, LockoutAction.EMAIL_USER,
                         {"smtp_identifier": "lockoutmail", "subject": "s", "body": "b",
                          "login_notice": "We emailed {username} about {count} failures."}),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            self.assertEqual(["We emailed cornelius about 3 failures."],
                             evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL))
        finally:
            delete_smtpserver("lockoutmail")

    def test_no_login_notice_for_non_email_action(self):
        # A LOCK_USER-only stage locks the user but produces no login-screen notice.
        self._make_policy(name="lockonly", counter_type=AuthEventType.MFA_FAIL,
                          stages=((3, 1, LockoutAction.LOCK_USER, 600),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        self.assertEqual([], evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL))
        self.assertTrue(self._state().is_locked)

    # --- _safe_format / _resolve_admin_recipients -----------------------------

    def test_safe_format_leaves_unknown_tags_and_never_raises(self):
        self.assertEqual("hi cornelius", _safe_format("hi {user}", {"user": "cornelius"}))
        # Unknown placeholder is left verbatim instead of raising KeyError.
        self.assertEqual("{missing} kept", _safe_format("{missing} kept", {"user": "x"}))
        # A malformed template is returned unchanged rather than raising.
        self.assertEqual("oops {", _safe_format("oops {", {}))

    def test_resolve_admin_recipients_explicit_and_unknown(self):
        self.assertEqual(["a@x.com", "b@y.com"],
                         _resolve_admin_recipients("a@x.com, b@y.com"))
        # An unknown, non-email group resolves to no recipients.
        self.assertEqual([], _resolve_admin_recipients("marketing"))
