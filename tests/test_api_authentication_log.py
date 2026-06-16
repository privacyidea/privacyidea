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
from privacyidea.lib.token import init_token, remove_token, get_tokens, get_one_token, revoke_token
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

    def test_disabled_token_logs_no_usable_token(self):
        # The user has a token, but it is disabled, so it cannot be used -> NO_USABLE_TOKEN 
        token = get_one_token(serial=self.serial)
        token.enable(False)
        body = self._check({"user": "cornelius", "pass": "pin123456"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=User("cornelius", self.realm1))

    def test_maxfail_token_logs_no_usable_token(self):
        # The user's only token has its fail counter exceeded, so it cannot be used -> NO_USABLE_TOKEN.
        token = get_one_token(serial=self.serial)
        for _ in range(token.get_max_failcount() + 1):
            token.inc_failcount()
        body = self._check({"user": "cornelius", "pass": "pin123456"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=User("cornelius", self.realm1))

    def test_revoked_token_logs_no_usable_token(self):
        # All of the user's tokens are revoked: check_token_list raises TOKEN_LOCKED (ERR1007) before it can classify
        # the request. The API catches that, records NO_USABLE_TOKEN for the log, and re-raises so the error response
        # is unchanged.
        revoke_token(self.serial)
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": "pin755224"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res.json)
            self.assertEqual(1007, res.json["result"]["error"]["code"], res.json)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=User("cornelius", self.realm1))

    def test_unknown_user_logs_user_unknown(self):
        # An unknown user is rejected by the auth_user_does_not_exist policy decorator;
        # the API catches that and still logs USER_UNKNOWN (high-signal for stuffing).
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "doesnotexist", "realm": self.realm1, "pass": "whatever"}):
            res = self.app.full_dispatch_request()
            self.assertFalse(res.json["result"]["status"], res.json)
        entries = assert_authentication_log([AuthEventType.USER_UNKNOWN])
        assert_authentication_log_entry(entries[AuthEventType.USER_UNKNOWN],
                                        user=User("doesnotexist", self.realm1))

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
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("doesnotexist", self.realm1))

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
                                        serials={self.serial}, client_label="myapp")

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
                                        serials={self.serial}, client_label="myapp")

    # --- otppin=none: only the token is verified, no first factor (end-to-end through check_user_pass) ---

    def test_otppin_none_wrong_otp_is_token_only_fail(self):
        # otppin=none: no first factor, only the token. A wrong OTP (empty PIN) is TOKEN_ONLY_FAIL, not MFA_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            body = self._check({"user": "cornelius", "pass": "000000", "client_id": "myapp"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.TOKEN_ONLY_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.TOKEN_ONLY_FAIL], user=User("cornelius", self.realm1),
                                        serials={self.serial}, client_label="myapp")

    def test_otppin_none_correct_otp_is_login_success(self):
        # otppin=none: the correct OTP (empty PIN) succeeds -> LOGIN_SUCCESS, with no stale token-only failure.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            body = self._check({"user": "cornelius", "pass": "755224", "client_id": "myapp"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=User("cornelius", self.realm1),
                                        serials={self.serial}, client_label="myapp")

    def test_otppin_none_pin_given_is_pin_fail(self):
        # otppin=none but a PIN is supplied anyway: the PIN check fails, the OTP is never checked, so this is a
        # rejected first-factor attempt -> PIN_FAIL (matches PIN brute-force), not TOKEN_ONLY_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            body = self._check({"user": "cornelius", "pass": "somepin755224", "client_id": "myapp"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=User("cornelius", self.realm1),
                                        client_label="myapp")

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
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)

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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)

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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)

    def test_challenge_stale_transaction_answered_fail(self):
        # A transaction_id with no live challenge for the token (expired, cleaned up or for another token) is still a
        # failed challenge answer -> CHALLENGE_ANSWERED_FAIL (not PIN_FAIL).
        body = self._check({"user": "cornelius", "transaction_id": "9" * 20, "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        # TODO: Should we have the serial here in the log?
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), transaction_id="9" * 20)

    def test_challenge_answered_correct_logs_success(self):
        # Trigger, then answer with the correct OTP -> CHALLENGE_ANSWERED_OK
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            body = self._check({"user": "cornelius", "transaction_id": transaction_id, "pass": "755224"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.LOGIN_SUCCESS],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)

    # --- Enroll via multi challenge ---

    def test_enroll_via_multichallenge_logs_enrollment_triggered(self):
        # The user authenticates successfully with the existing token; and triggers an enrollment challenge for a token
        # type the user does not have yet (totp) in the post-policy.
        set_policy("authlog_enroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            self.assertTrue(body["detail"].get("enroll_via_multichallenge"), body)
            transaction_id = body["detail"]["transaction_id"]
            enrolled_serial = body["detail"]["serial"]
        finally:
            delete_policy("authlog_enroll")
        entries = assert_authentication_log([AuthEventType.ENROLLMENT_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={enrolled_serial},
                                        transaction_id=transaction_id)
        remove_token(enrolled_serial)

    def test_enroll_via_multichallenge_completion_logs_login_success(self):
        # Trigger a totp enrollment, then complete it by answering with the new token's OTP. The trigger row is
        # ENROLLMENT_TRIGGERED, the completion is a LOGIN_SUCCESS via the freshly enrolled token, both correlated by
        # the enrollment transaction_id.
        set_policy("authlog_enroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            transaction_id = body["detail"]["transaction_id"]
            enrolled_serial = body["detail"]["serial"]
            otp = get_one_token(serial=enrolled_serial).get_otp()[2]
            body = self._check({"user": "cornelius", "transaction_id": transaction_id, "pass": otp})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_enroll")
        entries = assert_authentication_log([AuthEventType.ENROLLMENT_TRIGGERED, AuthEventType.LOGIN_SUCCESS],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={enrolled_serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), serials={enrolled_serial},
                                        transaction_id=transaction_id)
        remove_token(enrolled_serial)

    def test_enroll_via_multichallenge_cancel_logs_login_success(self):
        # With enroll_via_multichallenge_optional, cancelling the enrollment completes the already-authenticated
        # login -> LOGIN_SUCCESS (correlated to ENROLLMENT_TRIGGERED by the enrollment transaction_id).
        set_policy("authlog_enroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        set_policy("authlog_enroll_optional", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL}=true")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            transaction_id = body["detail"]["transaction_id"]
            serial = body["detail"]["serial"]
            body = self._check({"transaction_id": transaction_id, "cancel_enrollment": True})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_enroll")
            delete_policy("authlog_enroll_optional")
        # The cancellation removed the enrollment token; the user is resolved from it before deletion.
        entries = assert_authentication_log([AuthEventType.ENROLLMENT_TRIGGERED, AuthEventType.LOGIN_SUCCESS],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED], serials={serial},
                                        user=User("cornelius", self.realm1), transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), transaction_id=transaction_id)

    def test_enroll_via_multichallenge_cancel_not_allowed_logs_canceled_fail(self):
        # Without enroll_via_multichallenge_optional, cancellation is rejected -> ENROLLMENT_CANCELED_FAIL.
        set_policy("authlog_enroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            transaction_id = body["detail"]["transaction_id"]
            enrolled_serial = body["detail"]["serial"]
            body = self._check({"transaction_id": transaction_id, "cancel_enrollment": True})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_enroll")
        entries = assert_authentication_log(
            [AuthEventType.ENROLLMENT_TRIGGERED, AuthEventType.ENROLLMENT_CANCELED_FAIL],
            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED], serials={enrolled_serial},
                                        user=User("cornelius", self.realm1), transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_CANCELED_FAIL],
                                        user=User("cornelius", self.realm1), transaction_id=transaction_id)
        remove_token(enrolled_serial)  # still exists because the enrollment was not cancelled

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
        # serial + otponly verifies only the token (no PIN/password), so a wrong value is TOKEN_ONLY_FAIL.
        body = self._check({"serial": self.serial, "pass": "000000", "otponly": "1"})
        self.assertFalse(body["result"]["value"], body)

        entries = assert_authentication_log([AuthEventType.TOKEN_ONLY_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.TOKEN_ONLY_FAIL], user=User("cornelius", self.realm1))

    def test_serial_pass_success(self):
        # serial + pin+otp (no otponly) goes through check_serial_pass -> check_token_list -> LOGIN_SUCCESS.
        body = self._check({"serial": self.serial, "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), serials={self.serial})

    def test_serial_pass_wrong_otp_is_mfa_fail(self):
        # serial + correct PIN, wrong OTP -> MFA_FAIL (same matrix as the standard path).
        body = self._check({"serial": self.serial, "pass": "pin000000"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL],
                                        user=User("cornelius", self.realm1), serials={self.serial})


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
                                        user=User("cornelius", self.realm1), serials={self.second_serial})

    def test_multiple_tokens_challenge_triggered_logs_all_serials(self):
        # Both tokens are challenge-response and share the PIN, so one request with just the PIN triggers a
        # challenge on both. The single CHALLENGE_TRIGGERED row records both serials, comma-joined.
        self._add_second_token(pin="pin")
        self._enable_challenge_response()
        try:
            body = self._check({"user": "cornelius", "pass": "pin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            transaction_id = body["detail"]["transaction_id"]
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        entry = entries[AuthEventType.CHALLENGE_TRIGGERED]
        assert_authentication_log_entry(entry, user=User("cornelius", self.realm1),
                                        serials={self.serial, self.second_serial}, transaction_id=transaction_id)


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
        # A wrong /auth login (local admin) falls through to userstore auth against the default realm, so realm1 is
        # recorded. The testadmin user does not exist in realm1's resolver, so resolver and uid are absent.
        self._auth({"username": self.testadmin, "password": "wrong"}, status=401)
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL],
                                        user=User(self.testadmin, self.realm1))

        self._clear_log()
        # A successful local-admin login uses User() (empty), so no identity fields are recorded.
        body = self._auth({"username": self.testadmin, "password": self.testadminpw})
        self.assertTrue(body["result"]["value"]["token"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS])

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
                                        user=User("cornelius", self.realm1), serials={self.serial})

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
                                        user=User("cornelius", self.realm1), serials={self.serial})

    # --- otppin=none via /auth: only the token is verified, no first factor ---

    def test_auth_otppin_none_wrong_otp_is_token_only_fail(self):
        # otppin=none: no first factor. A wrong OTP (empty PIN) is TOKEN_ONLY_FAIL, not MFA_FAIL.
        self._enable_privacyidea_login()
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            self._login("000000", status=401)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.TOKEN_ONLY_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.TOKEN_ONLY_FAIL],
                                        user=User("cornelius", self.realm1), serials={self.serial})

    def test_auth_otppin_none_correct_otp_is_login_success(self):
        # otppin=none: the correct OTP (empty PIN) succeeds -> LOGIN_SUCCESS, with no stale token-only failure.
        self._enable_privacyidea_login()
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            body = self._login("755224")
            self.assertTrue(body["result"]["value"]["token"], body)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), serials={self.serial})

    def test_auth_otppin_none_pin_given_is_pin_fail(self):
        # otppin=none but a PIN is supplied anyway: the PIN check fails, the OTP is never checked, so this is a
        # rejected first-factor attempt -> PIN_FAIL (matches PIN brute-force), not TOKEN_ONLY_FAIL.
        self._enable_privacyidea_login()
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            self._login("somepin755224", status=401)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=User("cornelius", self.realm1))

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
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)

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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)

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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)

    def test_auth_challenge_stale_transaction_answered_fail(self):
        self._enable_privacyidea_login()
        try:
            self._login("pin755224", status=401, transaction_id="9" * 20)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=User("cornelius", self.realm1), transaction_id="9" * 20)

    def test_auth_challenge_answered_correct_logs_final_success(self):
        self._enable_privacyidea_login()
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_auth_challenge()
            body = self._login("755224", transaction_id=transaction_id)
            self.assertTrue(body["result"]["value"]["token"], body)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.LOGIN_SUCCESS],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)


class TriggerChallengeAuthLogTestCase(AuthLogTestCase):
    """Authentication-log coverage for the admin /validate/triggerchallenge endpoint."""

    def test_triggerchallenge_logs_challenge_triggered(self):
        with self.app.test_request_context('/validate/triggerchallenge', method='POST',
                                           data={"user": "cornelius"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertGreaterEqual(res.json["result"]["value"], 1, res.json)
            transaction_id = res.json["detail"]["transaction_id"]

        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("cornelius", self.realm1), serials={self.serial},
                                        transaction_id=transaction_id)

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


class PreviousTransactionIdAuthLogTestCase(AuthLogTestCase):
    """
    Authentication-log coverage for ``previous_transaction_id``.

    The column is populated when answering one challenge immediately triggers another — that is, when
    ``has_further_challenge()`` returns True and a fresh transaction_id is created by the token layer while the
    answered challenge's transaction_id is still present in the request. The questionnaire token and the 4-eyes token
    are the canonical examples.
    """

    def _check(self, data):
        with self.app.test_request_context('/validate/check', method='POST', data=data):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def test_questionnaire_sets_previous_transaction_id(self):
        # Questionnaire with question_number=2: PIN triggers question 1 (first_transaction_id), answering question 1
        # triggers question 2 (second_transaction_id), answering question 2 is a LOGIN_SUCCESS. The middle step has
        # previous_transaction_id=first_transaction_id because it answered the first challenge and created a new one.
        questions_and_answers = {"Question1": "Answer1", "Question2": "Answer2", "Question3": "Answer3",
                                  "Question4": "Answer4", "Question5": "Answer5"}
        questionnaire_serial = "AUTHLOG_QUESTIONNAIRE"
        init_token({"type": "question", "questions": questions_and_answers, "pin": "questpin",
                    "serial": questionnaire_serial},
                   user=User("cornelius", self.realm1))
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            body = self._check({"user": "cornelius", "pass": "questpin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            first_transaction_id = body["detail"]["transaction_id"]
            first_question = body["detail"]["message"]

            body = self._check({"user": "cornelius", "pass": questions_and_answers[first_question],
                                 "transaction_id": first_transaction_id})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            second_transaction_id = body["detail"]["transaction_id"]
            second_question = body["detail"]["message"]
            self.assertNotEqual(first_transaction_id, second_transaction_id)

            body = self._check({"user": "cornelius", "pass": questions_and_answers[second_question],
                                 "transaction_id": second_transaction_id})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_question_number")
            remove_token(questionnaire_serial)

        entries = assert_authentication_log([
            AuthEventType.CHALLENGE_TRIGGERED,
            AuthEventType.CHALLENGE_CONTINUED,
            AuthEventType.LOGIN_SUCCESS,
        ])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=User("cornelius", self.realm1),
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=User("cornelius", self.realm1),
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id,
                                        previous_transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=User("cornelius", self.realm1),
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id)

    def test_foureyes_sets_previous_transaction_id(self):
        # 4-eyes with realm1 count=2: PIN triggers the initial challenge (first_transaction_id), the first admin
        # authenticates which satisfies one of two required tokens and creates a new challenge
        # (second_transaction_id, previous=first_transaction_id), the second admin authenticates to satisfy the
        # second required token and completes the flow (LOGIN_SUCCESS).
        required_realms = {"realm1": {"selected": True, "count": 2}}
        foureyes_serial = "AUTHLOG_FOUREYES"
        first_admin_serial = "AUTHLOG_FIRST_ADMIN"
        second_admin_serial = "AUTHLOG_SECOND_ADMIN"
        init_token({"type": "4eyes", "4eyes": required_realms, "pin": "foureyespin", "serial": foureyes_serial},
                   user=User("cornelius", self.realm1))
        init_token({"serial": first_admin_serial, "type": "hotp", "otpkey": self.otpkey, "pin": "firstadminpin"},
                   user=User("hans", self.realm1))
        init_token({"serial": second_admin_serial, "type": "hotp", "otpkey": self.otpkey, "pin": "secondadminpin"},
                   user=User("selfservice", self.realm1))
        try:
            body = self._check({"user": "cornelius", "pass": "foureyespin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            first_transaction_id = body["detail"]["transaction_id"]

            body = self._check({"user": "cornelius",
                                 "pass": "firstadminpin" + self.valid_otp_values[0],
                                 "transaction_id": first_transaction_id})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            second_transaction_id = body["detail"]["transaction_id"]
            self.assertNotEqual(first_transaction_id, second_transaction_id)

            body = self._check({"user": "cornelius",
                                 "pass": "secondadminpin" + self.valid_otp_values[0],
                                 "transaction_id": second_transaction_id})
            self.assertTrue(body["result"]["value"], body)
        finally:
            remove_token(foureyes_serial)
            remove_token(first_admin_serial)
            remove_token(second_admin_serial)

        entries = assert_authentication_log([
            AuthEventType.CHALLENGE_TRIGGERED,
            AuthEventType.CHALLENGE_CONTINUED,
            AuthEventType.LOGIN_SUCCESS,
        ])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=User("cornelius", self.realm1),
                                        serials={foureyes_serial}, transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=User("cornelius", self.realm1),
                                        serials={foureyes_serial}, transaction_id=second_transaction_id,
                                        previous_transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=User("cornelius", self.realm1),
                                        serials={foureyes_serial}, transaction_id=second_transaction_id)

    def test_questionnaire_fail_on_intermediate_challenge(self):
        # Answering the first question wrong gives CHALLENGE_ANSWERED_FAIL with no previous_transaction_id —
        # no new challenge was created, so there is nothing to link back to.
        questions_and_answers = {"Question1": "Answer1", "Question2": "Answer2", "Question3": "Answer3",
                                  "Question4": "Answer4", "Question5": "Answer5"}
        questionnaire_serial = "AUTHLOG_QUESTIONNAIRE"
        init_token({"type": "question", "questions": questions_and_answers, "pin": "questpin",
                    "serial": questionnaire_serial},
                   user=User("cornelius", self.realm1))
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            body = self._check({"user": "cornelius", "pass": "questpin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            first_transaction_id = body["detail"]["transaction_id"]

            body = self._check({"user": "cornelius", "pass": "WRONG_ANSWER",
                                 "transaction_id": first_transaction_id})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_question_number")
            remove_token(questionnaire_serial)

        entries = assert_authentication_log([
            AuthEventType.CHALLENGE_TRIGGERED,
            AuthEventType.CHALLENGE_ANSWERED_FAIL,
        ])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=User("cornelius", self.realm1),
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=User("cornelius", self.realm1),
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id)

    def test_questionnaire_fail_on_last_challenge(self):
        # Answering the first question correctly triggers the second (CHALLENGE_CONTINUED with
        # previous_transaction_id set). Answering the second question wrong gives CHALLENGE_ANSWERED_FAIL
        # with no previous_transaction_id — failure paths never populate it.
        questions_and_answers = {"Question1": "Answer1", "Question2": "Answer2", "Question3": "Answer3",
                                  "Question4": "Answer4", "Question5": "Answer5"}
        questionnaire_serial = "AUTHLOG_QUESTIONNAIRE"
        init_token({"type": "question", "questions": questions_and_answers, "pin": "questpin",
                    "serial": questionnaire_serial},
                   user=User("cornelius", self.realm1))
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            body = self._check({"user": "cornelius", "pass": "questpin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            first_transaction_id = body["detail"]["transaction_id"]
            first_question = body["detail"]["message"]

            body = self._check({"user": "cornelius", "pass": questions_and_answers[first_question],
                                 "transaction_id": first_transaction_id})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            second_transaction_id = body["detail"]["transaction_id"]

            body = self._check({"user": "cornelius", "pass": "WRONG_ANSWER",
                                 "transaction_id": second_transaction_id})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_question_number")
            remove_token(questionnaire_serial)

        entries = assert_authentication_log([
            AuthEventType.CHALLENGE_TRIGGERED,
            AuthEventType.CHALLENGE_CONTINUED,
            AuthEventType.CHALLENGE_ANSWERED_FAIL,
        ])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=User("cornelius", self.realm1),
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=User("cornelius", self.realm1),
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id,
                                        previous_transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=User("cornelius", self.realm1),
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id)

    def test_challenge_response_then_enroll_sets_previous_transaction_id(self):
        # Answering an HOTP challenge response correctly triggers a TOTP enrollment via post-policy. The enrollment
        # step is reclassified from LOGIN_SUCCESS to ENROLLMENT_TRIGGERED and inherits previous_transaction_id from
        # the answered HOTP challenge — the reclassify call only updates event_type/serial/transaction_id, leaving
        # previous_transaction_id intact.
        self._enable_challenge_response()
        set_policy("authlog_enroll", scope=SCOPE.AUTH, action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        enrolled_serial = None
        try:
            body = self._check({"user": "cornelius", "pass": "pin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            hotp_transaction_id = body["detail"]["transaction_id"]

            body = self._check({"user": "cornelius", "pass": self.valid_otp_values[0],
                                 "transaction_id": hotp_transaction_id})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            self.assertTrue(body["detail"].get("enroll_via_multichallenge"), body)
            enrollment_transaction_id = body["detail"]["transaction_id"]
            enrolled_serial = body["detail"]["serial"]
            self.assertNotEqual(hotp_transaction_id, enrollment_transaction_id)

            totp_otp = get_one_token(serial=enrolled_serial).get_otp()[2]
            body = self._check({"user": "cornelius", "pass": totp_otp,
                                 "transaction_id": enrollment_transaction_id})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_cr")
            delete_policy("authlog_enroll")
            if enrolled_serial:
                remove_token(enrolled_serial)

        entries = assert_authentication_log([
            AuthEventType.CHALLENGE_TRIGGERED,
            AuthEventType.ENROLLMENT_TRIGGERED,
            AuthEventType.LOGIN_SUCCESS,
        ])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=User("cornelius", self.realm1),
                                        serials={self.serial}, transaction_id=hotp_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED], user=User("cornelius", self.realm1),
                                        serials={enrolled_serial}, transaction_id=enrollment_transaction_id,
                                        previous_transaction_id=hotp_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=User("cornelius", self.realm1),
                                        serials={enrolled_serial}, transaction_id=enrollment_transaction_id)
