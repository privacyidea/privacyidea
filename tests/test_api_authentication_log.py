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

import datetime

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType, AUTH_EVENT_TYPE_KEY
from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE, PolicyAction
from privacyidea.lib.token import init_token, remove_token, get_tokens
from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.utils import utc_now
from .authlog_utils import assert_authentication_log, assert_authentication_log_entry
from .base import MyApiTestCase


class AuthLogTestCase(MyApiTestCase):
    """
    Shared fixture for the authentication-log end-to-end tests: the lib layer
    classifies the request outcome (stashed in reply_dict) and the API layer
    persists exactly one row per request, populates client_label, and never leaks
    the internal classification key into the response.

    Each request type (/validate/check, /auth, /validate/triggerchallenge) is
    tested in its own subclass below.
    """

    serial = "AUTHLOG_HOTP"

    def setUp(self):
        super().setUp()
        self.setUp_user_realms()
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": "pin"},
                   user=User("cornelius", self.realm1))
        self._clear_log()

    def tearDown(self):
        if get_tokens(serial=self.serial):
            remove_token(self.serial)
        self._clear_log()
        super().tearDown()

    @staticmethod
    def _clear_log():
        db.session.query(AuthenticationLog).delete()
        db.session.commit()

    @staticmethod
    def _enable_challenge_response():
        set_policy("authlog_cr", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")


class ValidateCheckAuthLogTestCase(AuthLogTestCase):
    """Authentication-log coverage for /validate/check (user, serial and challenge flows)."""

    def _check(self, data, headers=None):
        with self.app.test_request_context('/validate/check', method='POST', data=data, headers=headers or {}):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def _trigger_challenge(self):
        body = self._check({"user": "cornelius", "pass": "pin"})
        self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
        return body["detail"]["transaction_id"]

    # --- Generic ---

    def test_client_label_falls_back_to_user_agent(self):
        self._check({"user": "cornelius", "pass": "pin755224"}, headers={"User-Agent": "pytest-UA"})
        logs = get_authentication_logs()
        self.assertEqual(1, len(logs), logs)
        self.assertEqual("pytest-UA", logs[0].client_label)

    def test_no_token_logs_no_token(self):
        # A resolvable user without a usable token -> NO_TOKEN (set in check_user_pass)
        remove_token(self.serial)
        body = self._check({"user": "cornelius", "pass": "pin123456"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.NO_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_TOKEN], user=User("cornelius", self.realm1))

    def test_unknown_user_logs_user_unknown(self):
        # An unknown user is rejected by the auth_user_does_not_exist policy decorator;
        # the API catches that and still logs USER_UNKNOWN (high-signal for stuffing).
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "doesnotexist", "pass": "whatever"}):
            res = self.app.full_dispatch_request()
            self.assertFalse(res.json["result"]["status"], res.json)
        entries = assert_authentication_log([AuthEventType.USER_UNKNOWN])
        # TODO: What should be logged here for the user?
        assert_authentication_log_entry(entries[AuthEventType.USER_UNKNOWN], user=None,
                                        other_info={"login": "doesnotexist"})

    def test_pass_on_no_user_logs_login_success(self):
        # An unknown user accepted by a PASSONNOUSER policy is a successful login.
        set_policy(name="passonnouser", scope=SCOPE.AUTH, action=PolicyAction.PASSONNOUSER,
                   realm=self.realm1)
        try:
            body = self._check({"user": "doesnotexist", "realm": self.realm1, "pass": "secret"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("passonnouser")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        # TODO: What should be logged here for the user?
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=None)
        # self.assertIsNone(entries[AuthEventType.LOGIN_SUCCESS].uid)

    # --- Normal auth: a single request with PIN/password + OTP concatenated ---

    def test_normal_auth_login_success(self):
        # OTP for counter 0 of the standard test key
        body = self._check({"user": "cornelius", "pass": "pin755224", "client_id": "myapp"})
        self.assertTrue(body["result"]["value"], body)
        # The internal classification key must never reach the client
        self.assertNotIn(AUTH_EVENT_TYPE_KEY, body["detail"])

        # Exactly one LOGIN_SUCCESS row carrying the resolved user, the token serial, and client label
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=User("cornelius", self.realm1),
                                        serial=self.serial, client_label="myapp")

    def test_normal_auth_password_fail(self):
        # otppin=userstore: the PIN part is the userstore password; a wrong one is PASSWORD_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        try:
            body = self._check({"user": "cornelius", "pass": "wrongpassword755224", "client_id": "myapp"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL], user=User("cornelius", self.realm1),
                                        client_label="myapp")

    def test_normal_auth_pin_fail(self):
        # Wrong token PIN (otppin=token, the default) -> PIN_FAIL
        body = self._check({"user": "cornelius", "pass": "wrongpin755224", "client_id": "myapp"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=User("cornelius", self.realm1),
                                        client_label="myapp")

    def test_normal_auth_wrong_otp_is_mfa_fail(self):
        # PIN correct, OTP wrong
        body = self._check({"user": "cornelius", "pass": "pin000000", "client_id": "myapp"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL], user=User("cornelius", self.realm1),
                                        serial=self.serial, client_label="myapp")

    # --- Challenge response ---

    def test_challenge_triggered(self):
        # A challenge-response token issues a challenge -> CHALLENGE_TRIGGERED
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED], transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_challenge_wrong_otp_answered_fail(self):
        # Trigger, then answer with a wrong OTP -> CHALLENGE_ANSWERED_FAIL
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            body = self._check({"user": "cornelius", "transaction_id": transaction_id, "pass": "000000"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_challenge_expired_answered_fail(self):
        # Trigger, expire the challenge in the DB, then answer with the correct OTP -> CHALLENGE_ANSWERED_FAIL
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            for challenge in get_challenges(transaction_id=transaction_id):
                challenge.expiration = utc_now() - datetime.timedelta(minutes=10)
                challenge.save()
            body = self._check({"user": "cornelius", "transaction_id": transaction_id, "pass": "755224"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_challenge_stale_transaction_answered_fail(self):
        # A transaction_id with no live challenge for the token (expired, cleaned up or for another token) is still a
        # failed challenge answer -> CHALLENGE_ANSWERED_FAIL (not PIN_FAIL).
        body = self._check({"user": "cornelius", "transaction_id": "9" * 20, "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        # TODO: Should we have the serial here in the log?
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1))

    def test_challenge_answered_ok(self):
        # Trigger, then answer with the correct OTP -> CHALLENGE_ANSWERED_OK
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            body = self._check({"user": "cornelius", "transaction_id": transaction_id, "pass": "755224"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_OK],
                                  transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_OK],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    # --- Serial auth (serial provided instead of user) ---
    # TODO: Serial should be added to logs (context) if passed as request parameter

    def test_serial_otponly_success(self):
        # serial + otponly validates only the OTP (no PIN); a correct value is LOGIN_SUCCESS.
        # This classification is set by the API handler (check_otp), not the lib layer.
        body = self._check({"serial": self.serial, "pass": "755224", "otponly": "1"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=User("cornelius", self.realm1))

    def test_serial_otp_only_fail(self):
        # serial + otponly validates only the OTP (no PIN), so a wrong value is OTP_FAIL.
        body = self._check({"serial": self.serial, "pass": "000000", "otponly": "1"})
        self.assertFalse(body["result"]["value"], body)

        entries = assert_authentication_log([AuthEventType.OTP_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.OTP_FAIL], user=User("cornelius", self.realm1))

    def test_serial_pass_success(self):
        # serial + pin+otp (no otponly) goes through check_serial_pass -> check_token_list -> LOGIN_SUCCESS.
        body = self._check({"serial": self.serial, "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_serial_pass_wrong_otp_is_mfa_fail(self):
        # serial + correct PIN, wrong OTP -> MFA_FAIL (same matrix as the standard path).
        body = self._check({"serial": self.serial, "pass": "pin000000"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL],
                                        user=User("cornelius", self.realm1), serial=self.serial)


class MultiTokenAuthLogTestCase(AuthLogTestCase):
    """Authentication-log coverage for a user that owns more than one token."""

    second_serial = "AUTHLOG_HOTP2"

    def tearDown(self):
        if get_tokens(serial=self.second_serial):
            remove_token(self.second_serial)
        super().tearDown()

    def _check(self, data, headers=None):
        with self.app.test_request_context('/validate/check', method='POST', data=data, headers=headers or {}):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def _add_second_token(self, pin):
        # A second HOTP token for the same user, sharing the first token's OTP key.
        init_token({"serial": self.second_serial, "type": "hotp", "otpkey": self.otpkey, "pin": pin},
                   user=User("cornelius", self.realm1))

    def test_multiple_tokens_success_logs_only_matching_serial(self):
        # The second token has a distinct PIN, so "pin2<otp>" matches only it. The log must record that single
        # serial, not every token the user owns.
        self._add_second_token(pin="pin2")
        body = self._check({"user": "cornelius", "pass": "pin2755224"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), serial=self.second_serial)

    def test_multiple_tokens_challenge_triggered_logs_all_serials(self):
        # Both tokens are challenge-response and share the PIN, so one request with just the PIN triggers a
        # challenge on both. The single CHALLENGE_TRIGGERED row records both serials, comma-joined.
        self._add_second_token(pin="pin")
        self._enable_challenge_response()
        try:
            body = self._check({"user": "cornelius", "pass": "pin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        entry = entries[AuthEventType.CHALLENGE_TRIGGERED]
        assert_authentication_log_entry(entry, user=User("cornelius", self.realm1), serial=entry.serial)
        self.assertEqual({self.serial, self.second_serial}, set(entry.serial.split(",")))


class AuthEndpointAuthLogTestCase(AuthLogTestCase):
    """Authentication-log coverage for the /auth WebUI login endpoint."""

    def _auth(self, data, status=200):
        with self.app.test_request_context('/auth', method='POST', data=data):
            response = self.app.full_dispatch_request()
            self.assertEqual(status, response.status_code, response.json)
            return response.json

    @staticmethod
    def _enable_privacyidea_login():
        # WebUI login against privacyIDEA: the user logs in with their token (PIN+OTP),
        # so the /auth login runs the full check_user_pass classification matrix.
        set_policy("authlog_login_mode", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")

    def _login(self, password, status=200, transaction_id=None):
        data = {"username": "cornelius", "realm": self.realm1, "password": password}
        if transaction_id:
            data["transaction_id"] = transaction_id
        return self._auth(data, status=status)

    def _trigger_auth_challenge(self):
        body = self._login("pin")
        self.assertFalse(body["result"]["value"], body)
        return body["detail"]["transaction_id"]

    def test_auth_endpoint_logs_login(self):
        # A wrong /auth login (local admin, userstore mode) is logged as PASSWORD_FAIL
        self._auth({"username": self.testadmin, "password": "wrong"}, status=401)
        assert_authentication_log([AuthEventType.PASSWORD_FAIL])

        self._clear_log()
        # A successful /auth login is logged as LOGIN_SUCCESS
        body = self._auth({"username": self.testadmin, "password": self.testadminpw})
        self.assertTrue(body["result"]["value"]["token"], body)
        assert_authentication_log([AuthEventType.LOGIN_SUCCESS])

    # --- Normal auth (LOGINMODE=privacyIDEA, login with PIN+OTP) ---

    def test_auth_login_success(self):
        self._enable_privacyidea_login()
        try:
            body = self._login("pin755224")
            self.assertTrue(body["result"]["value"]["token"], body)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_auth_password_fail(self):
        # otppin=userstore: the PIN part is the userstore password; a wrong one is PASSWORD_FAIL.
        self._enable_privacyidea_login()
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        try:
            self._login("wrongpassword755224", status=401)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL], user=User("cornelius", self.realm1))

    def test_auth_pin_fail(self):
        self._enable_privacyidea_login()
        try:
            self._login("wrongpin755224", status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=User("cornelius", self.realm1))

    def test_auth_wrong_otp_is_mfa_fail(self):
        self._enable_privacyidea_login()
        try:
            self._login("pin000000", status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    # --- Challenge response (LOGINMODE=privacyIDEA + challenge_response) ---

    def test_auth_challenge_triggered(self):
        self._enable_privacyidea_login()
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_auth_challenge()
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED], transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_auth_challenge_wrong_otp_answered_fail(self):
        self._enable_privacyidea_login()
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_auth_challenge()
            self._login("000000", status=401, transaction_id=transaction_id)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_auth_challenge_expired_answered_fail(self):
        self._enable_privacyidea_login()
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_auth_challenge()
            for challenge in get_challenges(transaction_id=transaction_id):
                challenge.expiration = utc_now() - datetime.timedelta(minutes=10)
                challenge.save()
            self._login("755224", status=401, transaction_id=transaction_id)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_auth_challenge_stale_transaction_answered_fail(self):
        self._enable_privacyidea_login()
        try:
            self._login("pin755224", status=401, transaction_id="9" * 20)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1))

    def test_auth_challenge_answered_ok(self):
        self._enable_privacyidea_login()
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_auth_challenge()
            body = self._login("755224", transaction_id=transaction_id)
            self.assertTrue(body["result"]["value"]["token"], body)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_OK],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_OK],
                                        user=User("cornelius", self.realm1), serial=self.serial)


class TriggerChallengeAuthLogTestCase(AuthLogTestCase):
    """Authentication-log coverage for the admin /validate/triggerchallenge endpoint."""

    def test_triggerchallenge_logs_challenge_triggered(self):
        with self.app.test_request_context('/validate/triggerchallenge', method='POST',
                                           data={"user": "cornelius"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertGreaterEqual(res.json["result"]["value"], 1, res.json)

        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serial=self.serial)

    def test_triggerchallenge_without_token_logs_no_token(self):
        # No challenge-capable token for the user -> nothing is triggered -> NO_TOKEN
        remove_token(self.serial)
        with self.app.test_request_context('/validate/triggerchallenge', method='POST',
                                           data={"user": "cornelius"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(0, res.json["result"]["value"], res.json)

        entries = assert_authentication_log([AuthEventType.NO_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_TOKEN], user=User("cornelius", self.realm1))
