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
End-to-end tests for the conditional-access lockout engine at the
``/validate/check`` view: the pre-check that rejects an already-locked user
before any token logic runs, and the full loop where repeated failures trip a
policy stage and lock the user.
"""
from datetime import datetime, timedelta

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import (get_authentication_logs, log_authentication_event)
from privacyidea.lib.conditional_access.engine import (LockoutAction, LockoutTarget,
                                                       is_user_locked, is_ip_blocked)
from privacyidea.lib.conditional_access.lockout_policy import create_lockout_policy
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.token import init_token, remove_token, get_tokens
from privacyidea.lib.user import User
from privacyidea.models import db, Challenge
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.lockout_policy import (
    BlockList,
    LockoutPolicy,
    LockoutPolicyCounterType,
    LockoutPolicyStage,
    LockoutStageAction,
    UserLockoutState,
)
from privacyidea.models.utils import utc_now
from . import smtpmock
from .base import MyApiTestCase


def _counter_types(counter_type):
    """Normalize a single AuthEventType (or string) or an iterable of them into
    the list-of-strings shape stored in ``LockoutPolicy.counter_types_to_track``."""
    values = counter_type if isinstance(counter_type, (list, tuple)) else [counter_type]
    return [str(t) for t in values]


def _seed_ip_spray(user: "User", event_type: AuthEventType, source_ip: str, n_users: int,
                   timestamp: datetime | None = None):
    """Seed *n_users* distinct users failing from *source_ip* (the spraying shape a
    source_ip BLOCK_IP policy keys on: one IP hitting many accounts). The users are
    synthetic (uid/username ``spray0``..) in *user*'s resolver/realm - only the distinct
    ``(username, realm, resolver)`` count matters, they need not resolve; the distinct
    ``username`` per user mirrors the resolved row a real request writes."""
    timestamp = timestamp if timestamp is not None else utc_now()
    for i in range(n_users):
        db.session.add(AuthenticationLog(
            event_type=str(event_type), resolver=user.resolver, uid=f"spray{i}",
            realm=user.realm, username=f"spray{i}", source_ip=source_ip, timestamp=timestamp))
    db.session.commit()


class ConditionalAccessValidateTestCase(MyApiTestCase):
    serial = "CA_HOTP"

    def setUp(self):
        super().setUp()
        self.setUp_user_realms()
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": "pin"},
                   user=User("cornelius", self.realm1))
        self.user = User("cornelius", self.realm1)
        self._clear()

    def tearDown(self):
        if get_tokens(serial=self.serial):
            remove_token(self.serial)
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear() -> None:
        for model in (UserLockoutState, BlockList, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicyCounterType, LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _check(self, data: dict, remote_addr: str | None = None) -> dict:
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/validate/check', method='POST', data=data, **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def _lock_user(self, lock_expires_at) -> None:
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=lock_expires_at))
        db.session.commit()

    @staticmethod
    def _make_lock_policy(*, counter_type, threshold: int, duration: int, window: int = 3600) -> None:
        create_lockout_policy(
            name="ca_lock", time_window_seconds=window,
            counter_types_to_track=_counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER), "action_value": duration}]}],
            target=LockoutTarget.USER)

    @staticmethod
    def _make_block_ip_policy(*, counter_type, threshold: int, duration: int, window: int = 3600) -> None:
        create_lockout_policy(
            name="ca_blockip", time_window_seconds=window,
            counter_types_to_track=_counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.BLOCK_IP), "action_value": duration}]}],
            target=LockoutTarget.SOURCE_IP)

    @staticmethod
    def _make_decision_policy(*, name: str, counter_type, threshold: int, action,
                              priority: int = 1, window: int = 3600) -> None:
        create_lockout_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=_counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(action), "action_value": None}]}],
            target=LockoutTarget.USER, priority=priority)

    def _failcount(self) -> int:
        return get_tokens(serial=self.serial)[0].token.failcount

    # --- pre-check ------------------------------------------------------------

    def test_locked_user_rejected_without_token_logic(self):
        # Safety check: confirm these credentials are valid *before* locking, so the
        # rejection below is provably the conditional-access lock and not a bad OTP.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        logs_after_success = len(get_authentication_logs())

        self._lock_user(utc_now() + timedelta(seconds=600))
        self.assertEqual(0, self._failcount())

        # The very same request is now rejected while the user is locked.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["status"], body)
        self.assertFalse(body["result"]["value"], body)
        # Generic response: no detail leaks the reason.
        self.assertFalse(body.get("detail"), body)
        # No token logic ran: the fail counter did not move and no valid OTP was consumed.
        self.assertEqual(0, self._failcount())
        # The pre-check rejects before classification, so it writes no new authentication-log row.
        self.assertEqual(logs_after_success, len(get_authentication_logs()))

    def test_expired_lock_does_not_reject(self):
        self._lock_user(utc_now() - timedelta(seconds=10))
        # An expired lock is not a lock: a valid authentication still succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    # --- full loop ------------------------------------------------------------

    def test_user_locked_after_threshold_failures(self):
        # 3 wrong OTPs (correct PIN) within the window -> MFA_FAIL -> 10-minute lock.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)

        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)

        # The three MFA_FAIL events tripped the stage and locked the user.
        self.assertEqual(3, len(get_authentication_logs()))
        self.assertEqual([AuthEventType.MFA_FAIL] * 3,
                         [entry.event_type for entry in get_authentication_logs()])
        self.assertTrue(is_user_locked(self.user))

        # The next request is rejected by the pre-check: no further token logic, no new log row.
        logs_before = len(get_authentication_logs())
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(logs_before, len(get_authentication_logs()))

    def test_lockout_write_does_not_corrupt_transaction(self):
        # Regression: conditional_access_posteval wrapped the engine (which commits
        # its own writes) in db.session.begin_nested() + commit. Under SQLAlchemy
        # 2.x the engine's first inner commit closes the transaction, so the next
        # DB operation still inside the savepoint context raised InvalidRequestError
        # ("Can't operate on closed transaction inside context manager") on every
        # request that wrote more than once. The helper swallowed it as a warning.
        # Two policies tripping in one request force that second write; assert the
        # post-eval helper's logger stays quiet through the full /validate/check flow.
        # A per-user lock (threshold 1) and a source-IP block (threshold 3 distinct
        # users) are set so cornelius's single failing request - as the third distinct
        # user on the pre-sprayed IP - trips BOTH at once.
        ip = "203.0.113.9"
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=1, duration=600)
        self._make_block_ip_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=900)
        _seed_ip_spray(self.user, AuthEventType.MFA_FAIL, ip, n_users=2)
        with self.assertNoLogs("privacyidea.api.lib.utils", level="WARNING"):
            body = self._check({"user": "cornelius", "pass": "pin000000"}, remote_addr=ip)
            self.assertFalse(body["result"]["value"], body)
        # Both policies' writes landed and the transaction was never corrupted.
        self.assertTrue(is_user_locked(self.user))
        self.assertTrue(is_ip_blocked(ip))

    def test_user_locked_again_after_lock_expires(self):
        # Once the lock has run out, further failures must be able to re-lock the
        # user. Regression: the stage de-dup used to swallow every re-trigger for
        # a full policy window after the lock was written, leaving a dead zone of
        # (window - lock_duration) after expiry in which the user could fail
        # without limit and never be locked again.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        for _ in range(3):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))

        # The lock runs out while the original failures are still in the window.
        state = db.session.get(UserLockoutState,
                               (self.user.resolver, self.user.uid, self.user.realm))
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # The next failure trips the stage again (the count is already over the
        # threshold) and must re-lock - the expired lock must not de-dup it away.
        body = self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(body["result"]["value"], body)
        self.assertTrue(is_user_locked(self.user))

    def test_below_threshold_does_not_lock(self):
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(is_user_locked(self.user))
        # A subsequent valid authentication still succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    def test_successful_login_resets_failure_count(self):
        # A completed login clears the accumulated failures: the lock then counts
        # only failures made *after* the success, so a legitimate user who just
        # logged in is not re-locked by a single later typo.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        # Two failures (below the threshold), then a valid authentication.
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

        # Two more failures: without the reset this would be 4 >= 3 and lock; with
        # the reset only these two post-login failures count, so the user stays open.
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(is_user_locked(self.user))

        # A third post-login failure reaches the threshold and locks.
        self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))

    # --- BLOCK_IP -------------------------------------------------------------

    def test_blocked_ip_rejected_without_token_logic(self):
        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True,
                                 block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertEqual(0, self._failcount())

        # Even valid credentials must be rejected while the source IP is blocked.
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertTrue(body["result"]["status"], body)
        self.assertFalse(body["result"]["value"], body)
        # Generic response: no detail leaks the reason.
        self.assertFalse(body.get("detail"), body)
        # No token logic ran and the pre-check wrote no authentication-log row.
        self.assertEqual(0, self._failcount())
        self.assertEqual(0, len(get_authentication_logs()))

        # The block is per-IP: the same user from a clean IP still authenticates
        # (the valid OTP was never consumed by the rejected request above).
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="198.51.100.9")
        self.assertTrue(body["result"]["value"], body)

    def test_ip_blocked_after_spraying_distinct_users(self):
        # An IP that fails against many DISTINCT users (spraying) trips a BLOCK_IP
        # stage and is blocked - a single user's own repeated failures never would.
        self._make_block_ip_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        attacker_ip = "203.0.113.7"
        # Two other users already sprayed from this IP (below the threshold of 3).
        _seed_ip_spray(self.user, AuthEventType.MFA_FAIL, attacker_ip, n_users=2)
        # cornelius is the third distinct user: his failing request trips the block.
        body = self._check({"user": "cornelius", "pass": "pin000000"}, remote_addr=attacker_ip)
        self.assertFalse(body["result"]["value"], body)

        self.assertTrue(is_ip_blocked(attacker_ip))
        # The user themselves is not locked - only the IP was blocked.
        self.assertFalse(is_user_locked(self.user))

        # The next request from that IP is rejected by the pre-check (no new log row),
        # even with valid credentials.
        logs_before = len(get_authentication_logs())
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr=attacker_ip)
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(logs_before, len(get_authentication_logs()))

    def test_escalation_to_permanent_lock_after_lock_expiry(self):
        # Escalation across two user policies: a temp lock at threshold 2, then a
        # PERMANENT_LOCK_USER at the higher threshold 3. This pins the INTENTIONAL
        # behaviour (per the chosen design): attempts made WHILE the user is
        # temp-locked are rejected at the pre-check and never counted, so the
        # escalation only happens once the lock expires and the user fails again.
        # A policy's priority does NOT preempt the temp lock - lock/block policies
        # both fire when both thresholds are met, regardless of priority.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=2, duration=60)
        create_lockout_policy(
            name="ca_permlock", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.MFA_FAIL),
            stages=[{"failure_threshold": 3, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.PERMANENT_LOCK_USER), "action_value": None}]}],
            target=LockoutTarget.USER, priority=99)
        key = (self.user.resolver, self.user.uid, self.user.realm)

        # Two failures -> temp-locked, not yet permanently locked (count 2 < 3).
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))
        self.assertIsNotNone(db.session.get(UserLockoutState, key).lock_expires_at)  # timed

        # Hammering DURING the lock is rejected at the pre-check: no new log rows,
        # the count stays frozen at 2, so it never escalates to the permanent lock.
        logs_locked = len(get_authentication_logs())
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertEqual(logs_locked, len(get_authentication_logs()))
        self.assertIsNotNone(db.session.get(UserLockoutState, key).lock_expires_at)  # still timed

        # Expire the lock; the next failure reaches count 3 and escalates - the user
        # is now permanently locked (lock_expires_at is None).
        state = db.session.get(UserLockoutState, key)
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        body = self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(body["result"]["value"], body)
        state = db.session.get(UserLockoutState, key)
        self.assertIsNotNone(state)
        self.assertTrue(state.is_locked)
        self.assertIsNone(state.lock_expires_at)
        self.assertTrue(is_user_locked(self.user))

    # --- ALLOW / DENY ---------------------------------------------------------

    def test_deny_policy_rejects_after_threshold(self):
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=3, action=LockoutAction.DENY)
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertEqual(3, len(get_authentication_logs()))

        # The 4th request - even with a valid OTP - is denied pre-auth: a stateless
        # reject that persists no lock and writes no new authentication-log row.
        logs_before = len(get_authentication_logs())
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(body.get("detail"), body)
        self.assertEqual(logs_before, len(get_authentication_logs()))
        self.assertFalse(is_user_locked(self.user))

    def test_allow_policy_does_not_block_valid_auth(self):
        # A default-allow policy (threshold 0) must not interfere with a valid login.
        self._make_decision_policy(name="ca_allow", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=LockoutAction.ALLOW)
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    def test_allow_overrides_lower_priority_deny(self):
        # A higher-precedence ALLOW exception (lower priority number) lets a valid
        # login through despite a DENY with a higher number whose threshold is met.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=3, action=LockoutAction.DENY, priority=10)
        self._make_decision_policy(name="ca_allow", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=LockoutAction.ALLOW, priority=1)
        for _ in range(3):
            self._check({"user": "cornelius", "pass": "pin000000"})
        # The DENY threshold is met, but the higher-priority ALLOW wins -> valid auth succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    # --- precedence: user lock > IP block > ALLOW/DENY decision -----------------
    # The pre-checks run in a fixed, intentional order: the persistent user lock
    # first, the persistent IP block second, the stateless ALLOW/DENY decision
    # last. Consequences pinned here: an ALLOW exception can never override an
    # already-persisted lock or block, and a DENY whose threshold is lower than a
    # LOCK_USER threshold shadows the lock (DENY'd requests write no log row, so
    # the failure count freezes below the lock threshold).

    def test_allow_cannot_override_existing_lock(self):
        # The user lock is checked before the ALLOW/DENY decision, so even a
        # maximum-priority default-allow exception cannot unlock a locked user.
        self._lock_user(utc_now() + timedelta(seconds=600))
        self._make_decision_policy(name="ca_allow", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=LockoutAction.ALLOW, priority=1)
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(body.get("detail"), body)
        # Rejected by the lock pre-check: no token logic, no authentication-log row.
        self.assertEqual(0, self._failcount())
        self.assertEqual(0, len(get_authentication_logs()))

    def test_allow_cannot_override_ip_block(self):
        # The IP block is also checked before the ALLOW/DENY decision.
        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True,
                                 block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self._make_decision_policy(name="ca_allow", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=LockoutAction.ALLOW, priority=1)
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(0, len(get_authentication_logs()))

    def test_deny_with_lower_threshold_shadows_lock_policy(self):
        # A DENY threshold below a LOCK_USER threshold catches first: once met,
        # every further request is rejected pre-auth without writing a log row,
        # so the failure count freezes at the DENY threshold and the persistent
        # lock never engages. Intentional: the stateless DENY self-heals as the
        # failures age out of its window, whereas the lock would persist.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=3, action=LockoutAction.DENY)
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=5, duration=600)

        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertEqual(3, len(get_authentication_logs()))

        # Further failing attempts are denied by the pre-check: the log count
        # stays at 3, so the LOCK_USER threshold of 5 is never reached.
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertEqual(3, len(get_authentication_logs()))
        self.assertFalse(is_user_locked(self.user))

    # --- /validate/triggerchallenge -------------------------------------------

    def _trigger_challenge(self, remote_addr: str | None = None) -> dict:
        if not getattr(self, "at", None):
            self.authenticate()
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/validate/triggerchallenge', method='POST',
                                           data={"user": "cornelius"},
                                           headers={"Authorization": self.at}, **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def test_triggerchallenge_locked_user_rejected(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        body = self._trigger_challenge()
        # Generic failure (no challenge triggered) and no token logic ran.
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(body.get("detail"), body)
        # The pre-check rejects before classification, so it writes no log row and,
        # crucially, no challenge is created in the DB even though no transaction id
        # is returned.
        self.assertEqual(0, len(get_authentication_logs()))
        self.assertEqual(0, db.session.query(Challenge).count())

    def test_triggerchallenge_blocked_ip_rejected(self):
        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True,
                                 block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        body = self._trigger_challenge(remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(0, len(get_authentication_logs()))

    def test_triggerchallenge_denied_by_policy_rejected(self):
        # A default-deny policy (threshold 0) rejects every request pre-auth.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.PIN_FAIL,
                                   threshold=0, action=LockoutAction.DENY)
        body = self._trigger_challenge()
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(0, len(get_authentication_logs()))

    def test_triggerchallenge_no_token_event_feeds_engine(self):
        # With no challenge-capable token, triggering classifies NO_TOKEN; a policy
        # tracking NO_TOKEN locks the user via the post-eval seam.
        remove_token(self.serial)
        self._make_lock_policy(counter_type=AuthEventType.NO_TOKEN, threshold=1, duration=600)
        self.assertFalse(is_user_locked(self.user))
        body = self._trigger_challenge()
        self.assertEqual(0, body["result"]["value"], body)
        self.assertListEqual([AuthEventType.NO_TOKEN],
                             [entry.event_type for entry in get_authentication_logs()])
        self.assertTrue(is_user_locked(self.user))

    # --- /validate/polltransaction --------------------------------------------

    def _poll(self, transaction_id: str, remote_addr: str | None = None) -> dict:
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context(f'/validate/polltransaction/{transaction_id}',
                                           method='GET', **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def _create_hotp_challenge(self) -> str:
        """Trigger a real challenge for cornelius' HOTP token (owned by cornelius)
        via /validate/check and return its transaction_id."""
        set_policy(name="ca_cr", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        try:
            body = self._check({"user": "cornelius", "pass": "pin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            return body["detail"]["transaction_id"]
        finally:
            delete_policy("ca_cr")

    def test_polltransaction_blocked_ip_rejected(self):
        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True,
                                 block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        # The IP-block pre-check fires regardless of whether the transaction exists.
        body = self._poll("9" * 20, remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        # Generic reject: no challenge_status detail is leaked.
        self.assertFalse(body.get("detail"), body)

    def test_polltransaction_locked_owner_rejected(self):
        transaction_id = self._create_hotp_challenge()
        self._lock_user(utc_now() + timedelta(seconds=600))
        # The poll resolves the challenge's token owner (cornelius), who is locked.
        body = self._poll(transaction_id)
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(body.get("detail"), body)

    def test_polltransaction_does_not_write_authentication_log(self):
        # Polling must not write an authentication-log row: the smartphone's answer
        # is logged at /ttype/push, so logging here too would double-count. Only the
        # trigger row from creating the challenge should exist.
        transaction_id = self._create_hotp_challenge()
        logs_before = len(get_authentication_logs())
        body = self._poll(transaction_id)
        self.assertEqual("pending", body["detail"]["challenge_status"], body)
        self.assertEqual(logs_before, len(get_authentication_logs()))

    # The /ttype/push authentication-path pre-check (locked owner / blocked IP
    # rejected, enrollment NOT gated) is covered end-to-end with real signed push
    # answers in tests/test_api_push_validate.py (test_18e / test_18f), since the
    # pre-check now lives in the push token's _api_endpoint_post auth branch.

    # --- serial-only lock-evasion (resolve owner before the pre-check) ---------

    def test_locked_user_rejected_via_serial(self):
        # A serial-only request (no user= parameter) is gated on the token owner:
        # the owner is resolved from the serial before the pre-check, so a locked
        # user is rejected even without a user parameter.
        # Confirm the credentials are valid first, so the rejection is provably the lock.
        body = self._check({"serial": self.serial, "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        logs_after_success = len(get_authentication_logs())

        self._lock_user(utc_now() + timedelta(seconds=600))
        body = self._check({"serial": self.serial, "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(body.get("detail"), body)
        # Rejected before any token work: no new log row and the fail counter is unmoved.
        self.assertEqual(logs_after_success, len(get_authentication_logs()))
        self.assertEqual(0, self._failcount())


class ConditionalAccessAuthTestCase(MyApiTestCase):
    """The WebUI JWT login (/auth) is gated by the same lockout engine."""

    def setUp(self):
        super().setUp()
        self.setUp_user_realms()
        self.user = User("cornelius", self.realm1)
        self._clear()

    def tearDown(self):
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        for model in (UserLockoutState, BlockList, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicyCounterType, LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _auth(self, username, password, remote_addr=None):
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/auth', method='POST',
                                           data={"username": username, "password": password}, **kwargs):
            return self.app.full_dispatch_request()

    @staticmethod
    def _make_password_policy(*, threshold, duration=600, window=3600):
        create_lockout_policy(
            name="ca_pw", time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER), "action_value": duration}]}],
            target=LockoutTarget.USER)

    @staticmethod
    def _make_decision_policy(*, name, threshold, action, priority=1, window=3600):
        create_lockout_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(action), "action_value": None}]}],
            target=LockoutTarget.USER, priority=priority)

    @staticmethod
    def _make_block_ip_policy(*, threshold, duration=600, window=3600):
        create_lockout_policy(
            name="ca_block_ip", time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.BLOCK_IP), "action_value": duration}]}],
            target=LockoutTarget.SOURCE_IP)

    def test_locked_user_rejected_at_auth(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        # Correct userstore password, but the user is locked -> 401 that states the lockout.
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(4031, res.json["result"]["error"]["code"], res.json)
        # The message tells the user about the (timed) lockout instead of "Wrong credentials".
        message = res.json["result"]["error"]["message"]
        self.assertIn("locked", message.lower(), message)
        self.assertIn("minute", message.lower(), message)
        self.assertNotIn("Wrong credentials", message, message)
        # The WebUI gets a coarse severity hint so it can color a timed lock differently.
        self.assertEqual("temporary", res.json["detail"]["restriction"], res.json)
        # Rejected before classification -> no authentication-log row.
        self.assertEqual(0, len(get_authentication_logs()))

    def test_permanently_locked_user_message_at_auth(self):
        # A permanent lock (no expiry) points the user at the administrator.
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=None))
        db.session.commit()
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(4031, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        self.assertIn("locked", message.lower(), message)
        self.assertIn("administrator", message.lower(), message)
        self.assertNotIn("minute", message.lower(), message)
        self.assertEqual("permanent", res.json["detail"]["restriction"], res.json)

    def test_blocked_ip_rejected_at_auth(self):
        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True,
                                 block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        # Correct userstore password, but the source IP is blocked -> 401 whose message
        # names the block, the offending IP and the remaining time (like the user lock).
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(4031, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        self.assertIn("blocked", message.lower(), message)
        self.assertIn("203.0.113.7", message, message)
        self.assertIn("minute", message.lower(), message)
        self.assertNotIn("account", message.lower(), message)
        self.assertNotIn("Wrong credentials", message, message)
        self.assertEqual("temporary", res.json["detail"]["restriction"], res.json)
        # Rejected before classification -> no authentication-log row.
        self.assertEqual(0, len(get_authentication_logs()))

    def test_permanently_blocked_ip_message_at_auth(self):
        # A permanent block (no expiry) points the user at the administrator, no minutes.
        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True, block_expires_at=None))
        db.session.commit()
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(4031, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        self.assertIn("blocked", message.lower(), message)
        self.assertIn("203.0.113.7", message, message)
        self.assertIn("administrator", message.lower(), message)
        self.assertNotIn("minute", message.lower(), message)
        self.assertNotIn("Wrong credentials", message, message)
        self.assertEqual("permanent", res.json["detail"]["restriction"], res.json)

    def test_hide_specific_error_message_strips_restriction_hint(self):
        # With hide_specific_error_message the lockout becomes a generic failure and the
        # restriction hint must be stripped, so neither the message nor the detail leaks
        # that the account is (permanently) locked.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=None))
        db.session.commit()
        set_policy(name="ca_hide", scope=SCOPE.AUTH, action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}")
        try:
            res = self._auth("cornelius", "test")
            self.assertEqual(401, res.status_code, res)
            message = res.json["result"]["error"]["message"]
            self.assertNotIn("locked", message.lower(), message)
            self.assertNotIn("administrator", message.lower(), message)
            self.assertNotIn("restriction", (res.json.get("detail") or {}), res.json)
        finally:
            delete_policy("ca_hide")

    def test_ip_block_trip_message_at_auth(self):
        # The failure that trips the BLOCK_IP stage (by crossing the distinct-user
        # threshold) already tells the user about the block instead of "Wrong
        # credentials".
        self._make_block_ip_policy(threshold=3)
        ip = "203.0.113.7"
        # Below the threshold, a failure is just a plain wrong-credentials rejection.
        res = self._auth("cornelius", "wrongpass", remote_addr=ip)
        self.assertEqual(401, res.status_code, res)
        self.assertIn("Wrong credentials", res.json["result"]["error"]["message"], res.json)
        # Two other users spray the same IP: with cornelius that is 3 distinct users.
        _seed_ip_spray(self.user, AuthEventType.PASSWORD_FAIL, ip, n_users=2)
        # cornelius's next failure crosses the distinct-user threshold -> IP blocked.
        res = self._auth("cornelius", "wrongpass", remote_addr=ip)
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertIn("blocked", message.lower(), message)
        self.assertIn(ip, message, message)
        self.assertIn("minute", message.lower(), message)
        self.assertNotIn("Wrong credentials", message, message)
        # The user themselves is not locked - only the IP was blocked.
        self.assertFalse(is_user_locked(self.user))

    def test_deny_policy_rejects_at_auth(self):
        # After enough prior PASSWORD_FAILs the next login is denied pre-auth, even with
        # the correct password. The message states it was a conditional-access decision
        # (without naming the policy); no new log row and no persisted lock.
        self._make_decision_policy(name="ca_deny", threshold=3, action=LockoutAction.DENY)
        for _ in range(3):
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
        logs_before = len(get_authentication_logs())
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(4031, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        self.assertIn("denied", message.lower(), message)
        self.assertIn("conditional-access policy", message.lower(), message)
        self.assertNotIn("Wrong credentials", message, message)
        self.assertNotIn("locked", message.lower(), message)
        self.assertEqual(logs_before, len(get_authentication_logs()))
        self.assertFalse(is_user_locked(self.user))

    # --- precedence: user lock > IP block > ALLOW/DENY decision -----------------
    # The /auth pre-checks run in the same fixed, intentional order as
    # /validate/check: persistent user lock first, persistent IP block second,
    # the stateless ALLOW/DENY decision last. Here the order is directly
    # observable through the distinct 401 messages ("account" for the lock, the
    # IP for the block, "conditional-access" for the decision).

    def _lock_user(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()

    def _block_ip(self, ip):
        db.session.add(BlockList(ip=ip, is_blocked=True,
                                 block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()

    def test_lock_checked_before_deny_at_auth(self):
        # Both a persistent lock and an always-met DENY stage: the lock is checked
        # first, so the 401 states the account lockout, not the policy denial.
        self._lock_user()
        self._make_decision_policy(name="ca_deny", threshold=0, action=LockoutAction.DENY)
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertIn("account", message.lower(), message)
        self.assertNotIn("conditional-access", message.lower(), message)

    def test_ip_block_checked_before_deny_at_auth(self):
        # Both a persistent IP block and an always-met DENY stage: the block is
        # checked first, so the 401 names the blocked IP, not the policy denial.
        self._block_ip("203.0.113.7")
        self._make_decision_policy(name="ca_deny", threshold=0, action=LockoutAction.DENY)
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertIn("203.0.113.7", message, message)
        self.assertNotIn("conditional-access", message.lower(), message)

    def test_lock_checked_before_ip_block_at_auth(self):
        # Both a persistent lock and a persistent IP block: the lock is checked
        # first, so the 401 states the account lockout, not the IP block.
        self._lock_user()
        self._block_ip("203.0.113.7")
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertIn("account", message.lower(), message)
        self.assertNotIn("203.0.113.7", message, message)

    def test_allow_cannot_override_lock_at_auth(self):
        # The lock is checked before the ALLOW/DENY decision, so a
        # maximum-priority default-allow exception cannot unlock a locked user.
        self._lock_user()
        self._make_decision_policy(name="ca_allow", threshold=0,
                                   action=LockoutAction.ALLOW, priority=1)
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertIn("account", res.json["result"]["error"]["message"].lower(), res.json)

    def test_permanent_ip_block_message_wins_over_timed_lock(self):
        # Escalation case: the user is temp-locked (1 min) AND their IP is now
        # permanently blocked. The rejection must report the permanent block - the
        # longer-lasting (binding) restriction - not "try again in a minute", which
        # would be misleading since waiting it out cannot help.
        self._lock_user()  # timed user lock, 600s
        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True, block_expires_at=None))
        db.session.commit()
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertIn("blocked", message.lower(), message)
        self.assertIn("203.0.113.7", message, message)
        self.assertIn("administrator", message.lower(), message)
        self.assertNotIn("minute", message.lower(), message)
        self.assertNotIn("account", message.lower(), message)

    def test_permanent_lock_message_wins_over_timed_ip_block(self):
        # Symmetric: a permanent user lock outranks a timed IP block.
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=None))
        self._block_ip("203.0.113.7")  # timed block, 600s
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertIn("account", message.lower(), message)
        self.assertIn("administrator", message.lower(), message)
        self.assertNotIn("minute", message.lower(), message)
        self.assertNotIn("203.0.113.7", message, message)

    def test_user_locked_after_password_failures(self):
        self._make_password_policy(threshold=3)
        for _ in range(3):
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
        self.assertTrue(is_user_locked(self.user))

        # The correct password is now also rejected, proving the lock (not a credential check).
        logs_before = len(get_authentication_logs())
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(logs_before, len(get_authentication_logs()))

    @smtpmock.activate
    def test_email_notice_surfaced_in_auth_rejection(self):
        # When an EMAIL_* action fires on the failing request, its notice is appended to the
        # rejection message so the login screen shows it, just like a lockout message.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            create_lockout_policy(
                name="ca_mail", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
                stages=[{"failure_threshold": 2, "priority": 1,
                         "actions": [{"action_type": str(LockoutAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "lockoutmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "alert", "body": "alert"}}]}],
                target=LockoutTarget.USER)

            # 1st failure is below the threshold: plain rejection, no email, no notice.
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
            self.assertNotIn("notified", res.json["result"]["error"]["message"].lower())

            # 2nd failure trips the stage: the email is sent and its notice rides back on the 401.
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
            message = res.json["result"]["error"]["message"]
            self.assertIn("Wrong credentials", message, message)
            self.assertIn("administrator has been notified", message.lower(), message)
            self.assertEqual(["soc@example.com"], smtpmock.get_sent_recipient())
            # An EMAIL-only stage writes no lock state, so the pre-check still lets the user in.
            self.assertFalse(is_user_locked(self.user))
        finally:
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_lockout_message_and_email_notice_combined(self):
        # A stage that both locks the user (timed) and emails the admin: the rejection on the
        # locking request leads with the lockout message and appends the email notice.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            create_lockout_policy(
                name="ca_lockmail", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
                stages=[{"failure_threshold": 2, "priority": 1,
                         "actions": [{"action_type": str(LockoutAction.LOCK_USER), "action_value": 600},
                                     {"action_type": str(LockoutAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "lockoutmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "s", "body": "b"}}]}],
                target=LockoutTarget.USER)

            self._auth("cornelius", "wrongpass")  # 1st failure: below the threshold
            res = self._auth("cornelius", "wrongpass")  # 2nd: trips the stage -> lock + email
            self.assertEqual(401, res.status_code, res)
            message = res.json["result"]["error"]["message"]
            # Reads "Your account is temporarily locked ... in about N minute(s). Your
            # administrator has been notified by email."
            self.assertIn("temporarily locked", message.lower(), message)
            self.assertIn("minute", message.lower(), message)
            self.assertIn("administrator has been notified", message.lower(), message)
            self.assertNotIn("Wrong credentials", message, message)
            self.assertTrue(is_user_locked(self.user))
        finally:
            delete_smtpserver("lockoutmail")
