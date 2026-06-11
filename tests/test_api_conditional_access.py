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
from datetime import timedelta

from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs
from privacyidea.lib.conditional_access.engine import LockoutAction, is_user_locked, is_ip_blocked
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.token import init_token, remove_token, get_tokens
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
from .base import MyApiTestCase


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
    def _clear():
        for model in (UserLockoutState, BlockList, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _check(self, data, remote_addr=None):
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/validate/check', method='POST', data=data, **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def _lock_user(self, lock_expires_at):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=lock_expires_at))
        db.session.commit()

    def _make_lock_policy(self, *, counter_type, threshold, duration, window=3600):
        policy = LockoutPolicy(name="ca_lock", counter_type_to_track=str(counter_type),
                               time_window_seconds=window, enabled=True, priority=1)
        db.session.add(policy)
        db.session.commit()
        stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=threshold, priority=1)
        db.session.add(stage)
        db.session.commit()
        db.session.add(LockoutStageAction(stage_id=stage.id,
                                          action_type=str(LockoutAction.LOCK_USER),
                                          action_value=duration))
        db.session.commit()

    def _make_block_ip_policy(self, *, counter_type, threshold, duration, window=3600):
        policy = LockoutPolicy(name="ca_blockip", counter_type_to_track=str(counter_type),
                               time_window_seconds=window, enabled=True, priority=1)
        db.session.add(policy)
        db.session.commit()
        stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=threshold, priority=1)
        db.session.add(stage)
        db.session.commit()
        db.session.add(LockoutStageAction(stage_id=stage.id,
                                          action_type=str(LockoutAction.BLOCK_IP),
                                          action_value=duration))
        db.session.commit()

    def _make_decision_policy(self, *, name, counter_type, threshold, action, priority=1, window=3600):
        policy = LockoutPolicy(name=name, counter_type_to_track=str(counter_type),
                               time_window_seconds=window, enabled=True, priority=priority)
        db.session.add(policy)
        db.session.commit()
        stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=threshold, priority=1)
        db.session.add(stage)
        db.session.commit()
        db.session.add(LockoutStageAction(stage_id=stage.id, action_type=str(action),
                                          action_value=None))
        db.session.commit()

    def _failcount(self):
        return get_tokens(serial=self.serial)[0].token.failcount

    # --- pre-check ------------------------------------------------------------

    def test_locked_user_rejected_without_token_logic(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        self.assertEqual(0, self._failcount())

        # Even valid credentials must be rejected while the user is locked.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["status"], body)
        self.assertFalse(body["result"]["value"], body)
        # Generic response: no detail leaks the reason.
        self.assertFalse(body.get("detail"), body)
        # No token logic ran: the fail counter did not move and no valid OTP was consumed.
        self.assertEqual(0, self._failcount())
        # The pre-check rejects before classification, so it writes no authentication-log row.
        self.assertEqual(0, len(get_authentication_logs()))

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

    def test_below_threshold_does_not_lock(self):
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(is_user_locked(self.user))
        # A subsequent valid authentication still succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

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

    def test_ip_blocked_after_threshold_failures(self):
        # Repeated failures from one IP trip a BLOCK_IP stage; that IP is then blocked.
        self._make_block_ip_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        attacker_ip = "203.0.113.7"
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"}, remote_addr=attacker_ip)
            self.assertFalse(body["result"]["value"], body)

        self.assertEqual(3, len(get_authentication_logs()))
        self.assertTrue(is_ip_blocked(attacker_ip))
        # The user themselves is not locked - only the IP was blocked.
        self.assertFalse(is_user_locked(self.user))

        # The next request from that IP is rejected by the pre-check (no new log row),
        # even with valid credentials.
        logs_before = len(get_authentication_logs())
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr=attacker_ip)
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(logs_before, len(get_authentication_logs()))

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
        # A higher-priority ALLOW exception lets a valid login through despite a
        # lower-priority DENY whose threshold is met.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=3, action=LockoutAction.DENY, priority=1)
        self._make_decision_policy(name="ca_allow", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=LockoutAction.ALLOW, priority=10)
        for _ in range(3):
            self._check({"user": "cornelius", "pass": "pin000000"})
        # The DENY threshold is met, but the higher-priority ALLOW wins -> valid auth succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)


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
                      LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _auth(self, username, password, remote_addr=None):
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/auth', method='POST',
                                           data={"username": username, "password": password}, **kwargs):
            return self.app.full_dispatch_request()

    def _make_password_policy(self, *, threshold, duration=600, window=3600):
        policy = LockoutPolicy(name="ca_pw", counter_type_to_track=str(AuthEventType.PASSWORD_FAIL),
                               time_window_seconds=window, enabled=True, priority=1)
        db.session.add(policy)
        db.session.commit()
        stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=threshold, priority=1)
        db.session.add(stage)
        db.session.commit()
        db.session.add(LockoutStageAction(stage_id=stage.id,
                                          action_type=str(LockoutAction.LOCK_USER),
                                          action_value=duration))
        db.session.commit()

    def _make_deny_policy(self, *, threshold, window=3600):
        policy = LockoutPolicy(name="ca_deny", counter_type_to_track=str(AuthEventType.PASSWORD_FAIL),
                               time_window_seconds=window, enabled=True, priority=1)
        db.session.add(policy)
        db.session.commit()
        stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=threshold, priority=1)
        db.session.add(stage)
        db.session.commit()
        db.session.add(LockoutStageAction(stage_id=stage.id, action_type=str(LockoutAction.DENY),
                                          action_value=None))
        db.session.commit()

    def _make_block_ip_policy(self, *, threshold, duration=600, window=3600):
        policy = LockoutPolicy(name="ca_block_ip", counter_type_to_track=str(AuthEventType.PASSWORD_FAIL),
                               time_window_seconds=window, enabled=True, priority=1)
        db.session.add(policy)
        db.session.commit()
        stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=threshold, priority=1)
        db.session.add(stage)
        db.session.commit()
        db.session.add(LockoutStageAction(stage_id=stage.id, action_type=str(LockoutAction.BLOCK_IP),
                                          action_value=duration))
        db.session.commit()

    def test_locked_user_rejected_at_auth(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, is_locked=True,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        # Correct userstore password, but the user is locked -> 401 that now states the lockout.
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(4031, res.json["result"]["error"]["code"], res.json)
        # The message tells the user about the (timed) lockout instead of "Wrong credentials".
        message = res.json["result"]["error"]["message"]
        self.assertIn("locked", message.lower(), message)
        self.assertIn("minute", message.lower(), message)
        self.assertNotIn("Wrong credentials", message, message)
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

    def test_ip_block_trip_message_at_auth(self):
        # The failure that trips the BLOCK_IP stage already tells the user about
        # the block instead of "Wrong credentials".
        self._make_block_ip_policy(threshold=3)
        for _ in range(2):
            res = self._auth("cornelius", "wrongpass", remote_addr="203.0.113.7")
            self.assertEqual(401, res.status_code, res)
            self.assertIn("Wrong credentials", res.json["result"]["error"]["message"], res.json)
        res = self._auth("cornelius", "wrongpass", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertIn("blocked", message.lower(), message)
        self.assertIn("203.0.113.7", message, message)
        self.assertIn("minute", message.lower(), message)
        self.assertNotIn("Wrong credentials", message, message)
        # The user themselves is not locked - only the IP was blocked.
        self.assertFalse(is_user_locked(self.user))

    def test_deny_policy_rejects_at_auth(self):
        # After enough prior PASSWORD_FAILs the next login is denied pre-auth, even with
        # the correct password - generically, with no new log row and no persisted lock.
        self._make_deny_policy(threshold=3)
        for _ in range(3):
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
        logs_before = len(get_authentication_logs())
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(4031, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        self.assertIn("Wrong credentials", message, message)
        self.assertNotIn("locked", message.lower(), message)
        self.assertEqual(logs_before, len(get_authentication_logs()))
        self.assertFalse(is_user_locked(self.user))

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
            policy = LockoutPolicy(name="ca_mail", counter_type_to_track=str(AuthEventType.PASSWORD_FAIL),
                                   time_window_seconds=3600, enabled=True, priority=1)
            db.session.add(policy)
            db.session.commit()
            stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=2, priority=1)
            db.session.add(stage)
            db.session.commit()
            db.session.add(LockoutStageAction(
                stage_id=stage.id, action_type=str(LockoutAction.EMAIL_ADMIN),
                action_value={"smtp_identifier": "lockoutmail", "recipient_group": "soc@example.com",
                              "subject": "alert", "body": "alert"}))
            db.session.commit()

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
            policy = LockoutPolicy(name="ca_lockmail", counter_type_to_track=str(AuthEventType.PASSWORD_FAIL),
                                   time_window_seconds=3600, enabled=True, priority=1)
            db.session.add(policy)
            db.session.commit()
            stage = LockoutPolicyStage(policy_id=policy.id, failure_threshold=2, priority=1)
            db.session.add(stage)
            db.session.commit()
            db.session.add(LockoutStageAction(stage_id=stage.id, action_type=str(LockoutAction.LOCK_USER),
                                              action_value=600))
            db.session.add(LockoutStageAction(
                stage_id=stage.id, action_type=str(LockoutAction.EMAIL_ADMIN),
                action_value={"smtp_identifier": "lockoutmail", "recipient_group": "soc@example.com",
                              "subject": "s", "body": "b"}))
            db.session.commit()

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
