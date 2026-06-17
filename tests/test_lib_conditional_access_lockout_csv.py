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
Snapshot regression tests for the conditional-access lockout configuration.

Two configurations are pinned here, each as its own test case:

* :class:`CurrentLockoutConfigTestCase` — the configuration four enabled
  policies — *Brute Force PIN Lockout* (LOCK_USER), *Email Notification Test*
  (EMAIL_ADMIN), *Brute Force IP Block* (BLOCK_IP) and *Permanent IP Block*
  (PERMANENT_BLOCK_IP) — all tracking the single type ``["PIN_FAIL"]``. So a user
  gets a 60s ``LOCK_USER`` timeout after 5 ``PIN_FAIL`` events, and ``NO_TOKEN``
  events do not lock.

* :class:`PreviousLockoutConfigTestCase` — a single enabled policy,
  *Brute Force PIN Lockout*, tracking ``["PIN_FAIL", "NO_TOKEN"]``. Here a
  user gets a timeout for **either** ``PIN_FAIL`` **or** ``NO_TOKEN`` (their
  combined count trips the threshold).

``counter_types_to_track`` is a JSON list in both. The configuration is encoded as
fixtures rather than read from the CSV/DB at run time (the CSVs live outside the
repo and the dev DB must never be touched by the suite); each ``SNAPSHOT`` is a
faithful transcription of the corresponding rows.
"""
from datetime import timedelta
from email import message_from_string

from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
from privacyidea.lib.conditional_access.engine import (
    LockoutAction,
    evaluate_lockout_policies,
    is_user_locked,
    is_ip_blocked,
)
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.lockout_policy import (
    BlockList,
    LockoutPolicy,
    LockoutPolicyStage,
    LockoutStageAction,
    UserLockoutState,
)
from privacyidea.models.utils import utc_now
from . import smtpmock
from .base import MyTestCase

EMAIL_ADMIN_VALUE = {
    "smtp_identifier": "localtest",
    "recipient_group": "admin@localhost",
    "subject": "[privacyIDEA] lockout: {user} -> {count} {event_type} (stage {stage_id})",
    "body": ("User {user}@{realm} (resolver {resolver}) from {source_ip} tripped policy "
             "{policy!r} stage {stage_id}: {count}/{threshold} {event_type} events in the "
             "window at {time}."),
    "mimetype": "plain",
}


class _LockoutSnapshotBase(MyTestCase):
    """
    Shared fixtures for the lockout-configuration snapshots. Subclasses set
    :attr:`SNAPSHOT` to the list of policy rows to materialise in setUp.
    """
    #: One policy row per entry: name, types, window, enabled, dry_run, priority,
    #: threshold, action, value (one stage with one action each, matching the
    #: CSV/DB layout).
    SNAPSHOT: list = []

    def setUp(self):
        self.setUp_user_realms()
        # "cornelius" resolves to a non-empty uid in the test resolver, i.e. a
        # fully resolved (resolver, uid, realm) identity the engine acts on.
        self.user = User("cornelius", self.realm1, self.resolvername1)
        self._clear()
        self._build_snapshot()

    def tearDown(self):
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        for model in (UserLockoutState, BlockList, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _build_snapshot(self):
        for row in self.SNAPSHOT:
            policy = LockoutPolicy(
                name=row["name"], counter_types_to_track=[str(t) for t in row["types"]],
                time_window_seconds=row["window"], enabled=row["enabled"],
                dry_run=row["dry_run"], priority=row["priority"])
            db.session.add(policy)
            db.session.commit()
            stage = LockoutPolicyStage(policy_id=policy.id,
                                       failure_threshold=row["threshold"], priority=1)
            db.session.add(stage)
            db.session.commit()
            db.session.add(LockoutStageAction(stage_id=stage.id,
                                              action_type=str(row["action"]),
                                              action_value=row["value"]))
            db.session.commit()

    # --- fixtures -------------------------------------------------------------

    def _seed_events(self, event_type, count, timestamp=None):
        timestamp = timestamp if timestamp is not None else utc_now()
        for _ in range(count):
            db.session.add(AuthenticationLog(
                event_type=str(event_type), resolver=self.user.resolver, uid=self.user.uid,
                realm=self.user.realm, timestamp=timestamp))
        db.session.commit()

    def _state(self):
        return db.session.get(UserLockoutState,
                              (self.user.resolver, self.user.uid, self.user.realm))

    def _enabled_policy_names(self):
        return {p.name for p in LockoutPolicy.query.filter_by(enabled=True)}


class CurrentLockoutConfigTestCase(_LockoutSnapshotBase):
    """
    The configuration four enabled policies, with the PIN-lockout policy
    tracking ``PIN_FAIL`` as a single-element JSON list.
    """
    SNAPSHOT = [
        dict(name="Brute Force PIN Lockout", types=[AuthEventType.PIN_FAIL],
             window=3600, enabled=True, dry_run=False, priority=10, threshold=5,
             action=LockoutAction.LOCK_USER, value=60),
        dict(name="Email Notification Test", types=[AuthEventType.PIN_FAIL],
             window=600, enabled=True, dry_run=False, priority=20, threshold=6,
             action=LockoutAction.EMAIL_ADMIN, value=EMAIL_ADMIN_VALUE),
        dict(name="Brute Force IP Block", types=[AuthEventType.PIN_FAIL],
             window=3600, enabled=True, dry_run=False, priority=10, threshold=7,
             action=LockoutAction.BLOCK_IP, value=60),
        dict(name="Permanent IP Block", types=[AuthEventType.PIN_FAIL],
             window=3600, enabled=True, dry_run=False, priority=4, threshold=7,
             action=LockoutAction.PERMANENT_BLOCK_IP, value=None),
    ]

    def test_exactly_four_policies_are_enabled(self):
        self.assertEqual(
            {"Brute Force PIN Lockout", "Email Notification Test",
             "Brute Force IP Block", "Permanent IP Block"}, self._enabled_policy_names())
        # The PIN-lockout policy tracks the single type, as a JSON list.
        policy = LockoutPolicy.query.filter_by(name="Brute Force PIN Lockout").one()
        self.assertEqual(["PIN_FAIL"], policy.counter_types_to_track)

    def test_five_pin_fails_lock_the_user_with_a_timeout(self):
        # Only the LOCK_USER policy (threshold 5) trips here; email (6) and the
        # IP blocks (7) need more failures. Deterministic clock so the 60s
        # timeout can be asserted exactly.
        now = utc_now()
        self._seed_events(AuthEventType.PIN_FAIL, 5, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL, source_ip="203.0.113.5", now=now)
        state = self._state()
        self.assertIsNotNone(state)
        self.assertTrue(state.is_locked)
        # A timeout, not a permanent lock: lock_expires_at is set and 60s out.
        self.assertIsNotNone(state.lock_expires_at)
        self.assertEqual(now + timedelta(seconds=60), state.lock_expires_at)
        self.assertTrue(is_user_locked(self.user, now=now))
        self.assertFalse(is_ip_blocked("203.0.113.5", now=now))

    def test_four_pin_fails_do_not_lock(self):
        self._seed_events(AuthEventType.PIN_FAIL, 4)
        evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL)
        self.assertIsNone(self._state())
        self.assertFalse(is_user_locked(self.user))

    def test_no_token_does_not_lock(self):
        # The PIN-lockout policy tracks PIN_FAIL only, so NO_TOKEN failures never
        # lock the user (no enabled policy tracks NO_TOKEN).
        self._seed_events(AuthEventType.NO_TOKEN, 8)
        evaluate_lockout_policies(self.user, AuthEventType.NO_TOKEN, source_ip="203.0.113.5")
        self.assertIsNone(self._state())
        self.assertFalse(is_user_locked(self.user))

    @smtpmock.activate
    def test_sixth_pin_fail_emails_the_admin(self):
        smtpmock.setdata(response={})
        # The EMAIL_ADMIN action references this SMTP server identifier.
        add_smtpserver(identifier="localtest", server="1.2.3.4", tls=False)
        try:
            self._seed_events(AuthEventType.PIN_FAIL, 6)
            evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL, source_ip="203.0.113.5")
            # recipient_group "admin@localhost" contains "@" -> an explicit list.
            self.assertEqual(["admin@localhost"], smtpmock.get_sent_recipient())
            self.assertIsNotNone(message_from_string(smtpmock.get_sent_message()))
            # The LOCK_USER policy (threshold 5) trips on the same request.
            self.assertTrue(is_user_locked(self.user))
        finally:
            delete_smtpserver("localtest")

    def test_seventh_pin_fail_blocks_the_source_ip_permanently(self):
        # At 7 PIN_FAILs both IP-block policies trip: BLOCK_IP (timed 60s) and
        # PERMANENT_BLOCK_IP. The permanent block is the binding one (a timed
        # block is never allowed to downgrade / override the permanent one).
        self._seed_events(AuthEventType.PIN_FAIL, 7)
        evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL, source_ip="203.0.113.50")
        block = db.session.get(BlockList, "203.0.113.50")
        self.assertIsNotNone(block)
        self.assertTrue(block.is_blocked)
        self.assertIsNone(block.block_expires_at)  # permanent
        self.assertTrue(is_ip_blocked("203.0.113.50"))
        # The user is also locked (LOCK_USER, threshold 5) — a timeout, not permanent.
        state = self._state()
        self.assertIsNotNone(state)
        self.assertTrue(state.is_locked)
        self.assertIsNotNone(state.lock_expires_at)

    def test_password_fail_does_not_trigger_any_policy(self):
        # No enabled policy tracks PASSWORD_FAIL -> nothing happens.
        self._seed_events(AuthEventType.PASSWORD_FAIL, 8)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip="203.0.113.50")
        self.assertIsNone(self._state())
        self.assertEqual(0, db.session.query(BlockList).count())


class PreviousLockoutConfigTestCase(_LockoutSnapshotBase):
    """
    A single enabled policy tracking ``PIN_FAIL`` **and** ``NO_TOKEN``
    as a JSON list, so a timeout fires for either type (or their combined count).
    """
    SNAPSHOT = [
        dict(name="Brute Force PIN Lockout",
             types=[AuthEventType.PIN_FAIL, AuthEventType.NO_TOKEN],
             window=3600, enabled=True, dry_run=False, priority=10, threshold=5,
             action=LockoutAction.LOCK_USER, value=60),
    ]

    def test_exactly_one_policy_is_enabled(self):
        self.assertEqual({"Brute Force PIN Lockout"}, self._enabled_policy_names())
        policy = LockoutPolicy.query.filter_by(name="Brute Force PIN Lockout").one()
        self.assertEqual(["PIN_FAIL", "NO_TOKEN"], policy.counter_types_to_track)

    def test_five_pin_fails_lock_the_user_with_a_timeout(self):
        now = utc_now()
        self._seed_events(AuthEventType.PIN_FAIL, 5, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL, now=now)
        state = self._state()
        self.assertIsNotNone(state)
        self.assertTrue(state.is_locked)
        self.assertEqual(now + timedelta(seconds=60), state.lock_expires_at)
        self.assertTrue(is_user_locked(self.user, now=now))

    def test_five_no_token_events_lock_the_user_with_a_timeout(self):
        # The distinguishing behaviour of this snapshot: NO_TOKEN is tracked too,
        # so 5 NO_TOKEN events also produce a 60s timeout.
        now = utc_now()
        self._seed_events(AuthEventType.NO_TOKEN, 5, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.NO_TOKEN, now=now)
        state = self._state()
        self.assertIsNotNone(state)
        self.assertTrue(state.is_locked)
        self.assertEqual(now + timedelta(seconds=60), state.lock_expires_at)
        self.assertTrue(is_user_locked(self.user, now=now))

    def test_combined_pin_and_no_token_reach_the_threshold(self):
        # The policy counts both tracked types together: 3 + 2 = 5 reaches the
        # threshold even though neither type alone does.
        self._seed_events(AuthEventType.PIN_FAIL, 3)
        self._seed_events(AuthEventType.NO_TOKEN, 2)
        # The current request is one of the tracked types.
        evaluate_lockout_policies(self.user, AuthEventType.NO_TOKEN)
        self.assertTrue(is_user_locked(self.user))

    def test_four_failures_do_not_lock(self):
        self._seed_events(AuthEventType.PIN_FAIL, 2)
        self._seed_events(AuthEventType.NO_TOKEN, 2)
        evaluate_lockout_policies(self.user, AuthEventType.NO_TOKEN)
        self.assertIsNone(self._state())
        self.assertFalse(is_user_locked(self.user))

    def test_password_fail_does_not_lock(self):
        # PASSWORD_FAIL is not one of the tracked types -> no lock.
        self._seed_events(AuthEventType.PASSWORD_FAIL, 8)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL)
        self.assertIsNone(self._state())
