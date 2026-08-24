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

from privacyidea.lib.conditional_access.conditions import ConditionOperator, ConditionType
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, CountMode
from privacyidea.lib.conditional_access.authentication_log import AuthLogUserRole, get_authentication_logs
from privacyidea.lib.conditional_access.engine import (LockoutAction, LockoutTarget,
                                                       is_user_locked, is_ip_blocked)
from privacyidea.lib.conditional_access.lockout_policy import create_lockout_policy
from privacyidea.lib.conditional_access.outcome_log import get_outcomes
from privacyidea.lib.conditional_access.session import get_ca_session
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, AUTHORIZED, set_policy, delete_policy
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.token import init_token, remove_token, get_tokens
from privacyidea.lib.user import User
from privacyidea.models import db, Challenge, ConditionalAccessOutcome
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.lockout_policy import (
    BlockList,
    LockoutPolicy,
    LockoutPolicyCondition,
    LockoutPolicyCounterType,
    LockoutPolicyStage,
    LockoutStageAction,
    UserLockoutState,
)
from privacyidea.models.utils import utc_now
from . import smtpmock
from .authlog_utils import assert_authentication_log, assert_authentication_log_entry
from .base import MyApiTestCase


def _rows_since(before: int) -> list[str]:
    """
    The event types of the authentication-log rows written since there were *before* of them, in order.

    A conditional-access rejection classifies the request it turned away (USER_LOCKED / IP_BLOCKED / ACCESS_DENIED),
    which is what these tests assert on: the row is the only place an admin can filter for the reason, since the
    request is refused before anything else logs an outcome for it.

    Used where a test's earlier phases make the *whole* log tedious to restate; where the full log is short and
    knowable, :func:`~tests.authlog_utils.assert_authentication_log` is the better tool - it pins the complete ordered
    list plus attempt_id chaining, and pairs with
    :func:`~tests.authlog_utils.assert_authentication_log_entry`, which asserts every column of a row (so the columns
    a rejection must *not* carry are proven empty).
    """
    return [entry.event_type for entry in get_authentication_logs()[before:]]


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

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": "pin"},
                   user=User("cornelius", self.realm1))
        self.user = User("cornelius", self.realm1)
        self._clear()

    def tearDown(self) -> None:
        if get_tokens(serial=self.serial):
            remove_token(self.serial)
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear() -> None:
        for model in (ConditionalAccessOutcome, UserLockoutState, BlockList, LockoutStageAction,
                      LockoutPolicyStage, LockoutPolicyCondition, LockoutPolicyCounterType, LockoutPolicy,
                      AuthenticationLog, Challenge):
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
                                        realm=self.user.realm, lock_expires_at=lock_expires_at))
        db.session.commit()

    @staticmethod
    def _make_lock_policy(*, counter_type, threshold: int, duration: int, window: int = 3600,
                          dry_run: bool = False, priority: int = 1) -> None:
        create_lockout_policy(
            name="ca_lock", time_window_seconds=window,
            counter_types_to_track=_counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER_TEMPORARY), "action_value": duration}]}],
            target=LockoutTarget.USER, dry_run=dry_run, priority=priority)

    @staticmethod
    def _make_block_ip_policy(*, counter_type, threshold: int, duration: int, window: int = 3600,
                              priority: int = 1) -> None:
        create_lockout_policy(
            name="ca_blockip", time_window_seconds=window,
            counter_types_to_track=_counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.BLOCK_IP), "action_value": duration}]}],
            target=LockoutTarget.SOURCE_IP, priority=priority)

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

        # mock a user lock
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
        # The rejection is what classifies this request: no token logic ran, so nothing else would log an outcome.
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS, AuthEventType.USER_LOCKED],
                                            same_attempt=False)
        # Every other column is asserted empty, which is the "a rejection row carries nothing else" decision: no
        # serial, no client label, and no other_info repeating an expiry the lock's own outcome already records.
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    def test_expired_lock_does_not_reject(self):
        self._lock_user(utc_now() - timedelta(seconds=10))
        # An expired lock is not a lock: a valid authentication still succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        # The stale row carries no state; the pre-check opts into cleanup, so this
        # next login drops it (rather than leaving it for the bulk purge).
        self.assertIsNone(db.session.get(UserLockoutState, (self.user.resolver, self.user.uid, self.user.realm)))

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

        # The next request is rejected by the pre-check: no further token logic, and the rejection classifies it.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.MFA_FAIL] * 3 + [AuthEventType.USER_LOCKED],
                                            same_attempt=False)
        assert_authentication_log_entry(entries.all[-1], user=self.user)

    def test_dry_run_lock_policy_persists_outcome_but_never_locks(self):
        # A dry-run LOCK_USER_TEMPORARY policy never locks the user, but the triggering request's own
        # authentication_log row records what the policy would have done.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600, dry_run=True)

        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)

        entries = get_authentication_logs()
        self.assertEqual([AuthEventType.MFA_FAIL] * 3, [entry.event_type for entry in entries])
        # Never actually enforced.
        self.assertFalse(is_user_locked(self.user))

        # The triggering (third) request's row carries the dry-run outcome, end to end: the engine returned an outcome
        # and the request context recorded it against the row it judged.
        outcomes = get_outcomes(entries[-1].id)
        self.assertEqual(1, len(outcomes))
        outcome = outcomes[0]
        self.assertTrue(outcome.dry_run)
        self.assertEqual("ca_lock", outcome.policy_name)
        self.assertEqual(3, outcome.threshold)
        self.assertEqual(3, outcome.event_count)
        self.assertEqual(str(LockoutAction.LOCK_USER_TEMPORARY), outcome.action_type)
        # The expiry the lock would have had, so a dry run reads like the enforced one.
        self.assertIn("expires_at", outcome.info)
        # The earlier rows, which did not trip the threshold, carry nothing.
        self.assertListEqual([], list(get_outcomes(entries[0].id)))

        # The user can still authenticate normally afterward -- never actually locked.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    def test_lockout_write_does_not_corrupt_transaction(self):
        # Regression: the engine's writes used to run on the shared request session, wrapped in
        # db.session.begin_nested() + commit. Under SQLAlchemy 2.x the first inner commit closes the
        # transaction, so the next DB operation still inside the savepoint context raised InvalidRequestError.
        # They now run on the conditional-access session, one guarded transaction per write
        # ("Can't operate on closed transaction inside context manager") on every
        # request that wrote more than once. The helper swallowed it as a warning.
        # Two policies tripping in one request force that second write; assert the
        # post-eval helper's logger stays quiet through the full /validate/check flow.
        # A per-user lock (threshold 1) and a source-IP block (threshold 3 distinct
        # users) are set so cornelius's single failing request - as the third distinct
        # user on the pre-sprayed IP - trips BOTH at once.
        ip = "203.0.113.9"
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=1, duration=600, priority=1)
        self._make_block_ip_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=900, priority=2)
        _seed_ip_spray(self.user, AuthEventType.MFA_FAIL, ip, n_users=2)
        with self.assertNoLogs("privacyidea.api.lib.utils", level="WARNING"):
            body = self._check({"user": "cornelius", "pass": "pin000000"}, remote_addr=ip)
            self.assertFalse(body["result"]["value"], body)
        # Both policies' writes landed and the transaction was never corrupted.
        self.assertTrue(is_user_locked(self.user))
        self.assertTrue(is_ip_blocked(ip))

    def test_lock_fires_once_at_exact_threshold(self):
        # A LOCK action fires once, at its exact threshold. After the lock expires,
        # further failures push the count ABOVE the threshold, so the threshold-3
        # stage does not re-fire (re-locking a higher count needs its own stage).
        # A successful login resets the count, and climbing back to exactly 3
        # re-locks. This replaces the earlier "re-lock on any further failure"
        # behaviour, per the exact-threshold trigger semantics.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        for _ in range(3):
            self.assertFalse(is_user_locked(self.user))
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))

        # The lock runs out while the original failures are still in the window.
        state = db.session.get(UserLockoutState,
                               (self.user.resolver, self.user.uid, self.user.realm))
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # A further failure pushes the count to 4, past the threshold-3 stage, so
        # it does not re-fire: the user stays unlocked.
        body = self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(is_user_locked(self.user))

        # A successful login resets the counter; climbing back to exactly 3 re-locks.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        for _ in range(3):
            self.assertFalse(is_user_locked(self.user))
            self._check({"user": "cornelius", "pass": "pin000000"})
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
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertEqual(0, self._failcount())

        # Even valid credentials must be rejected while the source IP is blocked.
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertTrue(body["result"]["status"], body)
        self.assertFalse(body["result"]["value"], body)
        # Generic response: no detail leaks the reason.
        self.assertFalse(body.get("detail"), body)
        # No token logic ran; the rejection itself is what the log records, with the blocked IP on the row.
        self.assertEqual(0, self._failcount())
        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=self.user,
                                        source_ip="203.0.113.7")

        # The block is per-IP: the same user from a clean IP still authenticates
        # (the valid OTP was never consumed by the rejected request above).
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="198.51.100.9")
        self.assertTrue(body["result"]["value"], body)

    def test_expired_block_does_not_reject(self):
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() - timedelta(seconds=10)))
        db.session.commit()
        # An expired block is not a block: a valid authentication still succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertTrue(body["result"]["value"], body)
        # The stale row carries no state; the pre-check opts into cleanup, so this
        # next request from the IP drops it (rather than leaving it for the bulk purge).
        self.assertIsNone(db.session.get(BlockList, "203.0.113.7"))

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

        # The next request from that IP is rejected by the pre-check, even with valid credentials.
        logs_before = len(get_authentication_logs())
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr=attacker_ip)
        self.assertFalse(body["result"]["value"], body)
        self.assertListEqual([AuthEventType.IP_BLOCKED], _rows_since(logs_before))

    def test_escalation_to_permanent_lock_after_lock_expiry(self):
        # Escalation across two user policies: a temp lock at threshold 2, then a
        # LOCK_USER_PERMANENT at the higher threshold 3. This pins the INTENTIONAL
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
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER_PERMANENT), "action_value": None}]}],
            target=LockoutTarget.USER, priority=99)
        key = (self.user.resolver, self.user.uid, self.user.realm)

        # Two failures -> temp-locked, not yet permanently locked (count 2 < 3).
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))
        self.assertIsNotNone(db.session.get(UserLockoutState, key).lock_expires_at)  # timed

        # Hammering DURING the lock is rejected at the pre-check. Each rejection is logged, but as USER_LOCKED -
        # a type no policy may track - so the tracked MFA_FAIL count stays frozen at 2 and never escalates to the
        # permanent lock. This is the property that makes the rejection rows forensic only.
        logs_locked = len(get_authentication_logs())
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertListEqual([AuthEventType.USER_LOCKED] * 3, _rows_since(logs_locked))
        self.assertEqual(2, len([entry for entry in get_authentication_logs()
                                 if entry.event_type == AuthEventType.MFA_FAIL]))
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

        # The 4th request - even with a valid OTP - is denied pre-auth: a stateless reject that persists no lock,
        # classified as ACCESS_DENIED.
        logs_before = len(get_authentication_logs())
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(body.get("detail"), body)
        self.assertListEqual([AuthEventType.ACCESS_DENIED], _rows_since(logs_before))
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
    # LOCK_USER_TEMPORARY threshold shadows the lock (DENY'd requests write no log row, so
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
        # Rejected by the lock pre-check: no token logic, and the log says which restriction did it.
        self.assertEqual(0, self._failcount())
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    def test_allow_cannot_override_ip_block(self):
        # The IP block is also checked before the ALLOW/DENY decision.
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self._make_decision_policy(name="ca_allow", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=LockoutAction.ALLOW, priority=1)
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=self.user, source_ip="203.0.113.7")

    def test_deny_with_lower_threshold_shadows_lock_policy(self):
        # A DENY threshold below a LOCK_USER_TEMPORARY threshold catches first: once met,
        # every further request is rejected pre-auth without writing a log row,
        # so the failure count freezes at the DENY threshold and the persistent
        # lock never engages. Intentional: the stateless DENY self-heals as the
        # failures age out of its window, whereas the lock would persist.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=3, action=LockoutAction.DENY, priority=1)
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=5, duration=600, priority=2)

        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertEqual(3, len(get_authentication_logs()))

        # Further failing attempts are denied by the pre-check. They are logged as ACCESS_DENIED, which no policy
        # may track, so the tracked MFA_FAIL count stays at 3 and the LOCK_USER_TEMPORARY threshold of 5 is never reached.
        logs_before = len(get_authentication_logs())
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertListEqual([AuthEventType.ACCESS_DENIED] * 3, _rows_since(logs_before))
        self.assertEqual(3, len([entry for entry in get_authentication_logs()
                                 if entry.event_type == AuthEventType.MFA_FAIL]))
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
        # The rejection classifies the request, and - crucially - no challenge is created in the DB even though no
        # transaction id is returned.
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)
        self.assertEqual(0, db.session.query(Challenge).count())

    def test_triggerchallenge_blocked_ip_rejected(self):
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        body = self._trigger_challenge(remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=self.user, source_ip="203.0.113.7")

    def test_triggerchallenge_denied_by_policy_rejected(self):
        # A default-deny policy (threshold 0) rejects every request pre-auth.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.PIN_FAIL,
                                   threshold=0, action=LockoutAction.DENY)
        body = self._trigger_challenge()
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.ACCESS_DENIED])
        assert_authentication_log_entry(entries[AuthEventType.ACCESS_DENIED], user=self.user)

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
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        # The IP-block pre-check fires regardless of whether the transaction exists.
        body = self._poll("9" * 20, remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        # Generic reject: no challenge_status detail is leaked.
        self.assertFalse(body.get("detail"), body)
        # And no row, unlike every other gated endpoint (log_rejection=False): a poll carries no authentication event,
        # so a rejection row would not replace one - it would add one per poll, for a client that cannot tell from the
        # generic response why it is failing.
        self.assertListEqual([], _rows_since(0))
        self.assertEqual(0, get_ca_session().query(ConditionalAccessOutcome).count())

    def test_polltransaction_locked_owner_rejected(self):
        transaction_id = self._create_hotp_challenge()
        self._lock_user(utc_now() + timedelta(seconds=600))
        logs_before = len(get_authentication_logs())
        # The poll resolves the challenge's token owner (cornelius), who is locked.
        body = self._poll(transaction_id)
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(body.get("detail"), body)
        # Still no row: see test_polltransaction_blocked_ip_rejected.
        self.assertListEqual([], _rows_since(logs_before))

    def test_enforced_deny_records_its_outcome_on_the_rejection_row(self):
        # The two halves of this feature meeting: the pre-check writes the ACCESS_DENIED row, and the DENY outcome the
        # engine returned - buffered on the context, because at decision time no row existed - is recorded against it.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=LockoutAction.DENY)
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)

        entries = get_authentication_logs()
        self.assertListEqual([AuthEventType.ACCESS_DENIED], [entry.event_type for entry in entries])
        outcomes = get_outcomes(entries[0].id)
        self.assertEqual(1, len(outcomes))
        self.assertEqual(str(LockoutAction.DENY), outcomes[0].action_type)
        self.assertEqual("ca_deny", outcomes[0].policy_name)
        self.assertFalse(outcomes[0].dry_run)

    def test_a_rejection_is_not_fed_back_into_the_engine(self):
        # A rejection must not be evaluated: counting it would let the lock feed itself. The row exists, no policy
        # tracks its type, and the lock is unchanged by the rejected request.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=1, duration=600)
        self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))
        locked_until = db.session.get(UserLockoutState, (self.user.resolver, self.user.uid,
                                                        self.user.realm)).lock_expires_at

        logs_before = len(get_authentication_logs())
        self._check({"user": "cornelius", "pass": "pin000000"})

        self.assertListEqual([AuthEventType.USER_LOCKED], _rows_since(logs_before))
        # The lock was neither refreshed nor escalated by its own rejection.
        self.assertEqual(locked_until, db.session.get(UserLockoutState, (self.user.resolver, self.user.uid,
                                                                        self.user.realm)).lock_expires_at)

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

    # --- /validate/initialize --------------------------------------------------

    def _initialize(self, remote_addr: str | None = None) -> dict:
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/validate/initialize', method='POST',
                                           data={"type": "passkey"}, **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def _set_relying_party_id(self) -> None:
        """The relying-party id the passkey challenge needs; without it the endpoint fails before creating one, which
        would let a gate test pass for the wrong reason."""
        set_policy("ca_rp_id", scope=SCOPE.ENROLL, action=f"{FIDO2PolicyAction.RELYING_PARTY_ID}=example.com")
        self.addCleanup(delete_policy, "ca_rp_id")

    def test_initialize_blocked_ip_rejected(self):
        self._set_relying_party_id()
        # Positive control: unblocked, the endpoint initializes a challenge and writes a *trackable* row - userless
        # (the passkey flow resolves nobody) but carrying the source IP, which is what a source-IP policy counts.
        body = self._initialize(remote_addr="203.0.113.7")
        self.assertIn("passkey", body["detail"], body)
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=None,
                                        source_ip="203.0.113.7",
                                        transaction_id=body["detail"]["transaction_id"])
        challenges_before = db.session.query(Challenge).count()

        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        body = self._initialize(remote_addr="203.0.113.7")
        # Generic reject, and the body never ran: no challenge payload leaks and no challenge is created.
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(body.get("detail"), body)
        self.assertEqual(challenges_before, db.session.query(Challenge).count())
        # The rejection *replaces* the CHALLENGE_TRIGGERED row this request would have written: only the first call's
        # row remains, and the second contributes an untrackable IP_BLOCKED one.
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.IP_BLOCKED],
                                            same_attempt=False)
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=None, source_ip="203.0.113.7")

    def test_initialize_cannot_feed_the_counter_that_blocked_it(self):
        # /validate/initialize writes a trackable CHALLENGE_TRIGGERED row.
        self._set_relying_party_id()
        create_lockout_policy(
            name="ca_initialize_rate", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.CHALLENGE_TRIGGERED),
            stages=[{"failure_threshold": 2, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.BLOCK_IP), "action_value": 600}]}],
            target=LockoutTarget.SOURCE_IP, count_mode=str(CountMode.PER_REQUEST), priority=1)

        # The first call is counted: one trackable CHALLENGE_TRIGGERED row, below the threshold.
        body = self._initialize(remote_addr="203.0.113.7")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=None,
                                        source_ip="203.0.113.7",
                                        transaction_id=body["detail"]["transaction_id"])
        self.assertFalse(is_ip_blocked("203.0.113.7"))

        # The second reaches the threshold, so its post-eval writes the block. Two separate requests, hence two
        # attempts (same_attempt=False).
        body = self._initialize(remote_addr="203.0.113.7")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED] * 2, same_attempt=False)
        assert_authentication_log_entry(entries.all[1], user=None, source_ip="203.0.113.7",
                                        transaction_id=body["detail"]["transaction_id"])
        self.assertTrue(is_ip_blocked("203.0.113.7"))

        for _ in range(3):
            self._initialize(remote_addr="203.0.113.7")
        # Every further call is turned away and classified IP_BLOCKED, which is untrackable by construction: no third
        # CHALLENGE_TRIGGERED row ever joins the two that produced the block, so the count that blocked this IP cannot
        # be refreshed by the block's own traffic.
        assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED] * 2 + [AuthEventType.IP_BLOCKED] * 3,
                                  same_attempt=False)

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
        # Rejected before any token work: the fail counter is unmoved and the rejection classifies the request.
        self.assertListEqual([AuthEventType.USER_LOCKED], _rows_since(logs_after_success))
        self.assertEqual(0, self._failcount())

    # --- deferred write: one row per request, written at teardown ---------------

    def test_one_row_per_request_when_a_post_policy_corrects_the_outcome(self):
        # The authorized=deny post-policy runs after check() classified the request. Since the row is only written at
        # teardown, the correction amends the staged event instead of adding or re-writing a row: exactly one row, and
        # it carries the corrected classification.
        set_policy("authz_deny", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "cornelius", "pass": "pin755224"}):
                response = self.app.full_dispatch_request()
                # authorized=deny raises ValidateError, which the error handler maps to 400.
                self.assertEqual(400, response.status_code, response)
        finally:
            delete_policy("authz_deny")

        entries = get_authentication_logs()
        self.assertEqual(1, len(entries))
        self.assertEqual(str(AuthEventType.NOT_AUTHORIZED), entries[0].event_type)

    def test_engine_evaluates_the_corrected_outcome_only(self):
        # Two policies, one tracking the pre-authz outcome and one the corrected one. Only the corrected outcome may
        # be evaluated.
        create_lockout_policy(
            name="ca_on_success", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.LOGIN_SUCCESS),
            stages=[{"failure_threshold": 1, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER_PERMANENT), "action_value": None}]}],
            target=LockoutTarget.USER, priority=1)
        set_policy("authz_deny", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "cornelius", "pass": "pin755224"}):
                self.app.full_dispatch_request()
        finally:
            delete_policy("authz_deny")

        # The row says NOT_AUTHORIZED, so the LOGIN_SUCCESS policy never saw a matching event and did not lock.
        self.assertFalse(is_user_locked(self.user))

    def test_a_conditional_access_rejection_is_not_reclassified_by_authz_deny(self):
        # The gate is the innermost decorator, so authorized=deny still runs on its rejection response. The rejection
        # row is the only record of *why* the request was refused, and relabelling it to NOT_AUTHORIZED would also
        # take the refused request past the CA_ENFORCEMENT_EVENT_TYPES guard and into the lockout counters - a lock
        # feeding itself. So the rejection stands and the post-policy logs nothing of its own.
        self._lock_user(utc_now() + timedelta(seconds=600))
        set_policy("authz_deny", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "cornelius", "pass": "pin755224"}):
                self.app.full_dispatch_request()
        finally:
            delete_policy("authz_deny")

        entries = get_authentication_logs()
        self.assertEqual(1, len(entries))
        self.assertEqual(str(AuthEventType.USER_LOCKED), entries[0].event_type)

    def test_row_is_written_even_when_the_view_raises(self):
        # Teardown runs whether or not the request succeeded, so a request that ends in an error still logs its event.
        body = self._check({"user": "cornelius", "pass": "wrongpin000000"})
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(1, len(get_authentication_logs()))


class ConditionalAccessAuthTestCase(MyApiTestCase):
    """The WebUI JWT login (/auth) is gated by the same lockout engine."""

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.user = User("cornelius", self.realm1)
        self._clear()

    def tearDown(self) -> None:
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        for model in (ConditionalAccessOutcome, UserLockoutState, BlockList, LockoutStageAction,
                      LockoutPolicyStage, LockoutPolicyCondition, LockoutPolicyCounterType, LockoutPolicy,
                      AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _auth(self, username, password, remote_addr=None):
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/auth', method='POST',
                                           data={"username": username, "password": password}, **kwargs):
            return self.app.full_dispatch_request()

    @staticmethod
    def _make_password_policy(*, threshold, duration=600, window=3600, priority=1):
        create_lockout_policy(
            name="ca_pw", time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER_TEMPORARY), "action_value": duration}]}],
            target=LockoutTarget.USER, priority=priority)

    @staticmethod
    def _make_dry_run_password_policy(*, threshold, duration=600, window=3600, priority=1):
        create_lockout_policy(
            name="ca_pw_dry", time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER_TEMPORARY), "action_value": duration}]}],
            target=LockoutTarget.USER, dry_run=True, priority=priority)

    def test_dry_run_outcome_persisted_on_auth_login(self):
        # /auth evaluates in-view rather than at request teardown (it surfaces the engine's notices in its own
        # response), so it flushes the staged row first - the outcome needs that row to exist. Without it a
        # dry-run policy tripped by a WebUI login records nothing.
        self._make_dry_run_password_policy(threshold=2)

        for _ in range(2):
            res = self._auth("cornelius", "wrongpassword")
            self.assertEqual(401, res.status_code, res)

        entries = get_authentication_logs()
        self.assertEqual([AuthEventType.PASSWORD_FAIL] * 2, [entry.event_type for entry in entries])
        # Dry-run never enforces, so the login stays refused on credentials only.
        self.assertFalse(is_user_locked(self.user))

        # The triggering (second) request's row carries the outcome. /auth flushes in-view and evaluates right after,
        # so this also covers recording against a row that was written earlier in the same request.
        outcomes = get_outcomes(entries[-1].id)
        self.assertEqual(1, len(outcomes))
        self.assertTrue(outcomes[0].dry_run)
        self.assertEqual("ca_pw_dry", outcomes[0].policy_name)
        self.assertEqual(2, outcomes[0].threshold)
        self.assertEqual(str(LockoutAction.LOCK_USER_TEMPORARY), outcomes[0].action_type)

    @staticmethod
    def _make_decision_policy(*, name, threshold, action, priority=1, window=3600):
        create_lockout_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(action), "action_value": None}]}],
            target=LockoutTarget.USER, priority=priority)

    @staticmethod
    def _make_block_ip_policy(*, threshold, duration=600, window=3600, priority=1):
        create_lockout_policy(
            name="ca_block_ip", time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.BLOCK_IP), "action_value": duration}]}],
            target=LockoutTarget.SOURCE_IP, priority=priority)

    def test_locked_user_rejected_at_auth(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
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
        # The login is classified by its rejection, so the log says why it failed even though no credential was checked.
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    def test_lock_is_checked_before_the_auth_timelimit_prepolicy(self):
        # The pre-check must run ahead of every other pre-policy, because auth_timelimit writes a *trackable*
        # NOT_AUTHORIZED row when its limit is hit (prepolicy.auth_timelimit). While the pre-check sat in the view
        # body, that row was written first, so a locked user's rejected logins kept feeding the counters that locked
        # them - the one way a lock could refresh itself from inside the lock.
        set_policy("ca_maxfail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXFAIL}=2/1m")
        self.addCleanup(delete_policy, "ca_maxfail")
        # Two failed logins put the classic time limit over its threshold (it counts the audit log).
        for _ in range(2):
            self.assertEqual(401, self._auth("cornelius", "wrongpassword").status_code)

        # Positive control: with no lock in force the time limit is what refuses the next login, proving it is armed -
        # otherwise the assertion below would hold for the wrong reason.
        self._clear_authentication_log()
        self.assertEqual(401, self._auth("cornelius", "test").status_code)
        self.assertListEqual([AuthEventType.NOT_AUTHORIZED], _rows_since(0))

        # Same tripped time limit, but now the user is locked: the lock is what refuses the login, and the row records
        # the lock rather than the time limit.
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self._clear_authentication_log()
        self.assertEqual(401, self._auth("cornelius", "test").status_code)
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    @staticmethod
    def _clear_authentication_log() -> None:
        # Only the authentication log, never the audit log: the classic AUTHMAXFAIL counts from the audit log, so
        # clearing that would un-trip the very policy under test.
        db.session.query(AuthenticationLog).delete()
        db.session.commit()

    def test_permanently_locked_user_message_at_auth(self):
        # A permanent lock (no expiry) points the user at the administrator.
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
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
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
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
        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=self.user,
                                        source_ip="203.0.113.7")

    def test_blocked_local_admin_is_recorded_as_such(self):
        # The role has to survive the pre-check, which runs before /auth decides its admin/user branch: it reads the
        # flag before_request already resolved (g.resolved_user). Without that, a blocked *local admin* - the recovery
        # account, and the one identity an operator would hunt for after locking themselves out with an IP policy -
        # would be filed under regular users. A local admin has no resolver/uid/realm, only a login name.
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()

        res = self._auth(self.testadmin, self.testadminpw, remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)

        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=User(self.testadmin),
                                        source_ip="203.0.113.7", user_role=AuthLogUserRole.ADMIN_INTERNAL)

    def test_permanently_blocked_ip_message_at_auth(self):
        # A permanent block (no expiry) points the user at the administrator, no minutes.
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=None))
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
                                        realm=self.user.realm, lock_expires_at=None))
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
        self.assertListEqual([AuthEventType.ACCESS_DENIED], _rows_since(logs_before))
        self.assertFalse(is_user_locked(self.user))

    # --- precedence: user lock > IP block > ALLOW/DENY decision -----------------
    # The /auth pre-checks run in the same fixed, intentional order as
    # /validate/check: persistent user lock first, persistent IP block second,
    # the stateless ALLOW/DENY decision last. Here the order is directly
    # observable through the distinct 401 messages ("account" for the lock, the
    # IP for the block, "conditional-access" for the decision).

    def _lock_user(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()

    def _block_ip(self, ip):
        db.session.add(BlockList(ip=ip, block_expires_at=utc_now() + timedelta(seconds=600)))
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
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=None))
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
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
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

        # The correct password is now also rejected, proving the lock (not a credential check) - and the log records
        # the lock as the reason rather than a password failure.
        logs_before = len(get_authentication_logs())
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertListEqual([AuthEventType.USER_LOCKED], _rows_since(logs_before))

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
                target=LockoutTarget.USER, priority=1)

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
                         "actions": [{"action_type": str(LockoutAction.LOCK_USER_TEMPORARY), "action_value": 600},
                                     {"action_type": str(LockoutAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "lockoutmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "s", "body": "b"}}]}],
                target=LockoutTarget.USER, priority=1)

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

    def test_endpoint_condition_confines_a_pre_auth_deny_to_one_endpoint(self):
        # An ENDPOINT condition is only worth anything if the endpoint reaches the engine on every way
        # in, so this asserts it end to end: a blanket source-IP DENY conditioned on /auth turns the
        # WebUI login away while the same IP's /validate/check traffic is untouched.
        create_lockout_policy(
            name="ca_deny_auth_only", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": 0, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.DENY), "action_value": None}]}],
            conditions=[{"condition_type": str(ConditionType.ENDPOINT),
                         "operator": str(ConditionOperator.IN),
                         "value": ["/auth"]}],
            target=LockoutTarget.SOURCE_IP, priority=1)

        res = self._auth("cornelius", "test", remote_addr="10.0.0.6")
        self.assertEqual(401, res.status_code, res.json)
        self.assertIn("conditional-access", res.json["result"]["error"]["message"])

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": "test"},
                                           environ_base={"REMOTE_ADDR": "10.0.0.6"}):
            response = self.app.full_dispatch_request()
        # The policy does not apply here, so the request is answered on its own merits (no token, hence
        # a plain failure) rather than turned away by conditional access.
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(response.json["result"]["value"], response.json)

    def test_break_glass_local_admin_is_exempt_from_pre_auth_deny(self):
        # A blanket source-IP DENY that exempts local admins, written the obvious
        # way. It must be a source_ip target: a user-target policy already skips a
        # local admin because their User() never resolves, so the role would not be
        # consulted at all. Loopback is on the never-block list, hence 10.0.0.5.
        create_lockout_policy(
            name="ca_deny_ip", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": 0, "priority": 1,
                     "actions": [{"action_type": str(LockoutAction.DENY), "action_value": None}]}],
            conditions=[{"condition_type": str(ConditionType.USER_ROLE),
                         "operator": str(ConditionOperator.NOT_IN),
                         "value": [str(AuthLogUserRole.ADMIN_INTERNAL)]}],
            target=LockoutTarget.SOURCE_IP, priority=1)

        # The local DB admin gets in: pre-auth the role is admin-internal, taken
        # from g.resolved_user (before_request already looked the name up), so the
        # NOT_IN condition does not match and the policy does not apply.
        res = self._auth(self.testadmin, self.testadminpw, remote_addr="10.0.0.5")
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"]["token"], res.json)

        # A regular user from the same IP is not exempt and is denied.
        res = self._auth("cornelius", "test", remote_addr="10.0.0.5")
        self.assertEqual(401, res.status_code, res.json)
        self.assertIn("conditional-access", res.json["result"]["error"]["message"])
