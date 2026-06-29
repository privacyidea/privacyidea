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

import mock

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType, AUTH_EVENT_TYPE_KEY
from privacyidea.lib.conditional_access.authentication_log import (get_authentication_logs, log_authentication_event,
                                                                   AuthLogUserRole)
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE, PolicyAction, AUTHORIZED
from privacyidea.lib.realm import set_realm, delete_realm
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
    username = "cornelius"
    pin = "pin"

    def setUp(self):
        super().setUp()
        self.setUp_user_realms()
        self.user = User(self.username, self.realm1)
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": self.pin},
                   user=self.user)
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
        body = self._check({"user": self.username, "pass": self.pin})
        self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
        return body["detail"]["transaction_id"]

    # --- Generic ---

    def test_client_label_falls_back_to_user_agent(self):
        self._check({"user": self.username, "pass": f"{self.pin}755224"}, headers={"User-Agent": "pytest-UA"})
        logs = get_authentication_logs()
        self.assertEqual(1, len(logs), logs)
        self.assertEqual("pytest-UA", logs[0].client_label)

    def test_no_token_logs_no_token(self):
        # A resolvable user without a usable token -> NO_TOKEN (set in check_user_pass)
        remove_token(self.serial)
        body = self._check({"user": self.username, "pass": f"{self.pin}123456"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.NO_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_TOKEN], user=self.user)

    def test_disabled_token_logs_no_usable_token(self):
        # The user has a token, but it is disabled, so it cannot be used -> NO_USABLE_TOKEN 
        token = get_one_token(serial=self.serial)
        token.enable(False)
        body = self._check({"user": self.username, "pass": f"{self.pin}123456"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

    def test_maxfail_token_logs_no_usable_token(self):
        # The user's only token has its fail counter exceeded, so it cannot be used -> NO_USABLE_TOKEN.
        token = get_one_token(serial=self.serial)
        for _ in range(token.get_max_failcount() + 1):
            token.inc_failcount()
        body = self._check({"user": self.username, "pass": f"{self.pin}123456"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

    def test_revoked_token_logs_no_usable_token(self):
        # All of the user's tokens are revoked: check_token_list raises TOKEN_LOCKED (ERR1007) before it can classify
        # the request. The API catches that, records NO_USABLE_TOKEN for the log, and re-raises so the error response
        # is unchanged.
        revoke_token(self.serial)
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": self.username, "pass": f"{self.pin}755224"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res.json)
            self.assertEqual(1007, res.json["result"]["error"]["code"], res.json)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

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

    def test_pass_on_no_token_logs_login_success(self):
        # A user with no tokens accepted by PASSONNOTOKEN is a successful login.
        remove_token(self.serial)
        set_policy("passonnotoken", scope=SCOPE.AUTH, action=PolicyAction.PASSONNOTOKEN)
        try:
            body = self._check({"user": self.username, "pass": "anypassword"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("passonnotoken")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user)

    def test_passthru_logs_login_success(self):
        # PASSTHRU=userstore: a user with no tokens who supplies the correct userstore password is accepted.
        remove_token(self.serial)
        set_policy("authlog_passthru", scope=SCOPE.AUTH, action=f"{PolicyAction.PASSTHRU}=userstore")
        try:
            body = self._check({"user": self.username, "pass": "test"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_passthru")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user)

    # --- Normal auth: a single request with PIN/password + OTP concatenated ---

    def test_normal_auth_login_success(self):
        # OTP for counter 0 of the standard test key
        body = self._check({"user": self.username, "pass": f"{self.pin}755224", "client_id": "myapp"})
        self.assertTrue(body["result"]["value"], body)
        # The internal classification key must never reach the client
        self.assertNotIn(AUTH_EVENT_TYPE_KEY, body["detail"])

        # Exactly one LOGIN_SUCCESS row carrying the resolved user, the token serial, and client label
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={self.serial}, client_label="myapp")

    def test_normal_auth_password_fail(self):
        # otppin=userstore: the PIN part is the userstore password; a wrong one is PASSWORD_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        try:
            body = self._check({"user": self.username, "pass": "wrongpassword755224", "client_id": "myapp"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL], user=self.user,
                                        client_label="myapp")

    def test_normal_auth_pin_fail(self):
        # Wrong token PIN (otppin=token, the default) -> PIN_FAIL
        body = self._check({"user": self.username, "pass": "wrongpin755224", "client_id": "myapp"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user,
                                        client_label="myapp")

    def test_normal_auth_wrong_otp_is_mfa_fail(self):
        # PIN correct, OTP wrong
        body = self._check({"user": self.username, "pass": f"{self.pin}000000", "client_id": "myapp"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL], user=self.user,
                                        serials={self.serial}, client_label="myapp")

    # --- otppin=none: only the token is verified, no first factor (end-to-end through check_user_pass) ---

    def test_otppin_none_wrong_otp_is_token_only_fail(self):
        # otppin=none: no first factor, only the token. A wrong OTP (empty PIN) is TOKEN_ONLY_FAIL, not MFA_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            body = self._check({"user": self.username, "pass": "000000", "client_id": "myapp"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.TOKEN_ONLY_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.TOKEN_ONLY_FAIL], user=self.user,
                                        serials={self.serial}, client_label="myapp")

    def test_otppin_none_correct_otp_is_login_success(self):
        # otppin=none: the correct OTP (empty PIN) succeeds -> LOGIN_SUCCESS, with no stale token-only failure.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            body = self._check({"user": self.username, "pass": "755224", "client_id": "myapp"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={self.serial}, client_label="myapp")

    def test_otppin_none_pin_given_is_pin_fail(self):
        # otppin=none but a PIN is supplied anyway: the PIN check fails, the OTP is never checked, so this is a
        # rejected first-factor attempt -> PIN_FAIL (matches PIN brute-force), not TOKEN_ONLY_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            body = self._check({"user": self.username, "pass": "somepin755224", "client_id": "myapp"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user,
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
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)

    def test_challenge_wrong_otp_answered_fail(self):
        # Trigger, then answer with a wrong OTP -> CHALLENGE_ANSWERED_FAIL
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            body = self._check({"user": self.username, "transaction_id": transaction_id, "pass": "000000"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)

    def test_challenge_expired_answered_fail(self):
        # Trigger, expire the challenge in the DB, then answer with the correct OTP -> CHALLENGE_ANSWERED_FAIL
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            for challenge in get_challenges(transaction_id=transaction_id):
                challenge.expiration = utc_now() - datetime.timedelta(minutes=10)
                challenge.save()
            body = self._check({"user": self.username, "transaction_id": transaction_id, "pass": "755224"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)

    def test_challenge_stale_transaction_answered_fail(self):
        # A transaction_id with no live challenge for the token (expired, cleaned up or for another token) is still a
        # failed challenge answer -> CHALLENGE_ANSWERED_FAIL (not PIN_FAIL).
        body = self._check({"user": self.username, "transaction_id": "9" * 20, "pass": f"{self.pin}755224"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        # TODO: Should we have the serial here in the log?
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=self.user, transaction_id="9" * 20)

    def test_challenge_answered_correct_logs_success(self):
        # Trigger, then answer with the correct OTP -> CHALLENGE_ANSWERED_OK
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            body = self._check({"user": self.username, "transaction_id": transaction_id, "pass": "755224"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.LOGIN_SUCCESS],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)

    # --- Enroll via multi challenge ---

    def test_enroll_via_multichallenge_logs_enrollment_triggered(self):
        # The user authenticates successfully with the existing token; and triggers an enrollment challenge for a token
        # type the user does not have yet (totp) in the post-policy.
        set_policy("authlog_enroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        try:
            body = self._check({"user": self.username, "pass": f"{self.pin}755224"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            self.assertTrue(body["detail"].get("enroll_via_multichallenge"), body)
            transaction_id = body["detail"]["transaction_id"]
            enrolled_serial = body["detail"]["serial"]
        finally:
            delete_policy("authlog_enroll")
        entries = assert_authentication_log([AuthEventType.ENROLLMENT_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED],
                                        user=self.user, serials={enrolled_serial},
                                        transaction_id=transaction_id)
        remove_token(enrolled_serial)

    def test_enroll_via_multichallenge_completion_logs_login_success(self):
        # Trigger a totp enrollment, then complete it by answering with the new token's OTP. The trigger row is
        # ENROLLMENT_TRIGGERED, the completion is a LOGIN_SUCCESS via the freshly enrolled token, both correlated by
        # the enrollment transaction_id.
        set_policy("authlog_enroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        try:
            body = self._check({"user": self.username, "pass": f"{self.pin}755224"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            transaction_id = body["detail"]["transaction_id"]
            enrolled_serial = body["detail"]["serial"]
            otp = get_one_token(serial=enrolled_serial).get_otp()[2]
            body = self._check({"user": self.username, "transaction_id": transaction_id, "pass": otp})
            self.assertTrue(body["result"]["value"], body)
        finally:
            delete_policy("authlog_enroll")
        entries = assert_authentication_log([AuthEventType.ENROLLMENT_TRIGGERED, AuthEventType.LOGIN_SUCCESS],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED],
                                        user=self.user, serials={enrolled_serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=self.user, serials={enrolled_serial},
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
            body = self._check({"user": self.username, "pass": f"{self.pin}755224"})
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
                                        user=self.user, transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=self.user, transaction_id=transaction_id)

    def test_enroll_via_multichallenge_cancel_not_allowed_logs_canceled_fail(self):
        # Without enroll_via_multichallenge_optional, cancellation is rejected -> ENROLLMENT_CANCELED_FAIL.
        set_policy("authlog_enroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        try:
            body = self._check({"user": self.username, "pass": f"{self.pin}755224"})
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
                                        user=self.user, transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_CANCELED_FAIL],
                                        user=self.user, transaction_id=transaction_id)
        remove_token(enrolled_serial)  # still exists because the enrollment was not cancelled

    # --- Serial auth (serial provided instead of user) ---
    # TODO: Serial should be added to logs (context) if passed as request parameter

    def test_serial_otponly_success(self):
        # serial + otponly validates only the OTP (no PIN); a correct value is LOGIN_SUCCESS.
        # This classification is set by the API handler (check_otp), not the lib layer.
        body = self._check({"serial": self.serial, "pass": "755224", "otponly": "1"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user)

    def test_serial_otp_only_fail(self):
        # serial + otponly verifies only the token (no PIN/password), so a wrong value is TOKEN_ONLY_FAIL.
        body = self._check({"serial": self.serial, "pass": "000000", "otponly": "1"})
        self.assertFalse(body["result"]["value"], body)

        entries = assert_authentication_log([AuthEventType.TOKEN_ONLY_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.TOKEN_ONLY_FAIL], user=self.user)

    def test_serial_pass_success(self):
        # serial + pin+otp (no otponly) goes through check_serial_pass -> check_token_list -> LOGIN_SUCCESS.
        body = self._check({"serial": self.serial, "pass": f"{self.pin}755224"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=self.user, serials={self.serial})

    def test_serial_pass_wrong_otp_is_mfa_fail(self):
        # serial + correct PIN, wrong OTP -> MFA_FAIL (same matrix as the standard path).
        body = self._check({"serial": self.serial, "pass": f"{self.pin}000000"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL],
                                        user=self.user, serials={self.serial})

    # --- Authorization policies (NOT_AUTHORIZED) ---

    def test_authmaxfail_logs_not_authorized(self):
        # AUTHMAXFAIL=2/20s: after 2 failed auths the next request is blocked before credentials are checked.
        set_policy("authlog_maxfail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXFAIL}=2/20s")
        try:
            for _ in range(2):
                self._check({"user": self.username, "pass": "wrongpin000000"})
            self._clear_log()
            body = self._check({"user": self.username, "pass": f"{self.pin}755224"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_maxfail")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user)

    def test_authmaxsuccess_logs_not_authorized(self):
        # AUTHMAXSUCCESS=1/20s: after 1 successful auth the next request is blocked before credentials are checked.
        set_policy("authlog_maxsuccess", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXSUCCESS}=1/20s")
        try:
            body = self._check({"user": self.username, "pass": f"{self.pin}755224"})
            self.assertTrue(body["result"]["value"], body)
            self._clear_log()
            body = self._check({"user": self.username, "pass": f"{self.pin}287082"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_maxsuccess")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user)

    def test_lastauth_exceeded_logs_not_authorized(self):
        # LASTAUTH=1d: a token whose last successful auth was 2 days ago is blocked -> NOT_AUTHORIZED.
        set_policy("authlog_lastauth", scope=SCOPE.AUTHZ, action=f"{PolicyAction.LASTAUTH}=1d")
        try:
            token = get_one_token(serial=self.serial)
            token.add_tokeninfo(PolicyAction.LASTAUTH,
                                (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).isoformat())
            body = self._check({"user": self.username, "pass": f"{self.pin}755224"})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_lastauth")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user,
                                        serials={self.serial})

    def test_is_authorized_deny_logs_not_authorized(self):
        # authorized=deny_access: a successful auth is reclassified to NOT_AUTHORIZED and the response is 400.
        set_policy("authlog_deny", scope=SCOPE.AUTHZ,
                   action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": self.username, "pass": f"{self.pin}755224"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(400, res.status_code, res.json)
        finally:
            delete_policy("authlog_deny")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        # authorized=deny runs in the AUTHZ scope, after authentication has already succeeded: the token genuinely
        # authenticated, so its serial is retained on the reclassified NOT_AUTHORIZED entry.
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user,
                                        serials={self.serial})


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
                   user=self.user)

    def test_multiple_tokens_success_logs_only_matching_serial(self):
        # The second token has a distinct PIN, so "pin2<otp>" matches only it. The log must record that single
        # serial, not every token the user owns.
        self._add_second_token(pin="pin2")
        body = self._check({"user": self.username, "pass": "pin2755224"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=self.user, serials={self.second_serial})

    def test_multiple_tokens_challenge_triggered_logs_all_serials(self):
        # Both tokens are challenge-response and share the PIN, so one request with just the PIN triggers a
        # challenge on both. The single CHALLENGE_TRIGGERED row records both serials, comma-joined.
        self._add_second_token(pin=self.pin)
        self._enable_challenge_response()
        try:
            body = self._check({"user": self.username, "pass": self.pin})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            transaction_id = body["detail"]["transaction_id"]
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        entry = entries[AuthEventType.CHALLENGE_TRIGGERED]
        assert_authentication_log_entry(entry, user=self.user,
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
        data = {"username": self.username, "realm": self.realm1, "password": password}
        if transaction_id:
            data["transaction_id"] = transaction_id
        return self._auth(data, status=status)

    def _trigger_auth_challenge(self):
        body = self._login(self.pin)
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
        # A successful internal-admin login uses User() (empty), so no identity fields are recorded; the role is
        # admin-internal.
        body = self._auth({"username": self.testadmin, "password": self.testadminpw})
        self.assertTrue(body["result"]["value"]["token"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user_role=AuthLogUserRole.ADMIN_INTERNAL)

    def test_auth_endpoint_logs_external_admin_role(self):
        # A user in a superuser realm (adminrealm) is an external (admin-realm) admin, recorded as admin-external.
        set_realm("adminrealm", [{"name": self.resolvername1}])
        try:
            body = self._auth({"username": "selfservice@adminrealm", "password": "test"})
            self.assertEqual("admin", body["result"]["value"]["role"], body)
            entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
            assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                            user=User("selfservice", "adminrealm"),
                                            user_role=AuthLogUserRole.ADMIN_EXTERNAL)
        finally:
            delete_realm("adminrealm")

    def test_no_token_logs_no_token(self):
        # A resolvable user without a usable token -> NO_TOKEN (set in check_user_pass)
        remove_token(self.serial)
        self._enable_privacyidea_login()
        try:
            self._login(f"{self.pin}123456", status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.NO_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_TOKEN], user=self.user)

    def test_disabled_token_logs_no_usable_token(self):
        # The user has a token, but it is disabled, so it cannot be used -> NO_USABLE_TOKEN
        token = get_one_token(serial=self.serial)
        token.enable(False)
        self._enable_privacyidea_login()
        try:
            self._login(f"{self.pin}123456", status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

    def test_maxfail_token_logs_no_usable_token(self):
        # The user's only token has its fail counter exceeded, so it cannot be used -> NO_USABLE_TOKEN.
        token = get_one_token(serial=self.serial)
        for _ in range(token.get_max_failcount() + 1):
            token.inc_failcount()
        self._enable_privacyidea_login()
        try:
            self._login(f"{self.pin}123456", status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

    def test_revoked_token_logs_no_usable_token(self):
        # All of the user's tokens are revoked: check_user_pass raises TOKEN_LOCKED before it can classify the
        # request. /auth keeps its generic "Wrong credentials" (4031) response, but the log must still record
        # NO_USABLE_TOKEN.
        revoke_token(self.serial)
        self._enable_privacyidea_login()
        try:
            with self.app.test_request_context('/auth', method='POST',
                                               data={"username": self.username, "realm": self.realm1,
                                                     "password": f"{self.pin}755224"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res.json)
                self.assertEqual(4031, res.json["result"]["error"]["code"], res.json)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

    def test_unknown_user_logs_user_unknown(self):
        # An unknown user on /auth fails with the generic "Wrong credentials" (4031), but the log must record
        # USER_UNKNOWN (high-signal for credential stuffing), as /validate/check does.
        self._enable_privacyidea_login()
        try:
            self._auth({"username": "doesnotexist", "realm": self.realm1, "password": "whatever"}, status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.USER_UNKNOWN])
        assert_authentication_log_entry(entries[AuthEventType.USER_UNKNOWN],
                                        user=User("doesnotexist", self.realm1))

    def test_pass_on_no_token_logs_login_success(self):
        # A user with no tokens accepted by PASSONNOTOKEN is a successful login.
        remove_token(self.serial)
        self._enable_privacyidea_login()
        set_policy("passonnotoken", scope=SCOPE.AUTH, action=PolicyAction.PASSONNOTOKEN)
        try:
            body = self._login("anypassword")
            self.assertTrue(body["result"]["value"]["token"], body)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("passonnotoken")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user)

    def test_auth_passthru_logs_login_success(self):
        # PASSTHRU=userstore: a user with no tokens who supplies the correct userstore password is accepted.
        self._enable_privacyidea_login()
        remove_token(self.serial)
        set_policy("authlog_passthru", scope=SCOPE.AUTH, action=f"{PolicyAction.PASSTHRU}=userstore")
        try:
            body = self._login("test")
            self.assertTrue(body["result"]["value"]["token"], body)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_passthru")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user)

    # --- Normal auth (LOGINMODE=privacyIDEA, login with PIN+OTP) ---

    def test_auth_login_success(self):
        self._enable_privacyidea_login()
        try:
            body = self._login(f"{self.pin}755224")
            self.assertTrue(body["result"]["value"]["token"], body)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=self.user, serials={self.serial})

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
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL], user=self.user)

    def test_auth_pin_fail(self):
        self._enable_privacyidea_login()
        try:
            self._login("wrongpin755224", status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user)

    def test_auth_wrong_otp_is_mfa_fail(self):
        self._enable_privacyidea_login()
        try:
            self._login(f"{self.pin}000000", status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL],
                                        user=self.user, serials={self.serial})

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
                                        user=self.user, serials={self.serial})

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
                                        user=self.user, serials={self.serial})

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
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user)

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
                                        user=self.user, serials={self.serial},
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
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=self.user, serials={self.serial},
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
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)

    def test_auth_challenge_stale_transaction_answered_fail(self):
        self._enable_privacyidea_login()
        try:
            self._login(f"{self.pin}755224", status=401, transaction_id="9" * 20)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=self.user, transaction_id="9" * 20)

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
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)

    # --- Authorization policies (NOT_AUTHORIZED) ---

    def test_auth_authmaxfail_logs_not_authorized(self):
        # AUTHMAXFAIL=2/1m on /auth: after 2 failed logins the auth_timelimit prepolicy blocks the next request.
        self._enable_privacyidea_login()
        set_policy("authlog_maxfail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXFAIL}=2/1m")
        try:
            for _ in range(2):
                self._login("wrongpin000000", status=401)
            self._clear_log()
            self._login(f"{self.pin}755224", status=401)
        finally:
            delete_policy("authlog_login_mode")
            delete_policy("authlog_maxfail")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user)


class TriggerChallengeAuthLogTestCase(AuthLogTestCase):
    """Authentication-log coverage for the admin /validate/triggerchallenge endpoint."""

    def test_triggerchallenge_logs_challenge_triggered(self):
        with self.app.test_request_context('/validate/triggerchallenge', method='POST',
                                           data={"user": self.username},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertGreaterEqual(res.json["result"]["value"], 1, res.json)
            transaction_id = res.json["detail"]["transaction_id"]

        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=self.user, serials={self.serial},
                                        transaction_id=transaction_id)

    def test_triggerchallenge_without_token_logs_no_token(self):
        # No challenge-capable token for the user -> nothing is triggered -> NO_TOKEN
        remove_token(self.serial)
        with self.app.test_request_context('/validate/triggerchallenge', method='POST',
                                           data={"user": self.username},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(0, res.json["result"]["value"], res.json)

        entries = assert_authentication_log([AuthEventType.NO_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_TOKEN], user=self.user)


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
                   user=self.user)
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            body = self._check({"user": self.username, "pass": "questpin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            first_transaction_id = body["detail"]["transaction_id"]
            first_question = body["detail"]["message"]

            body = self._check({"user": self.username, "pass": questions_and_answers[first_question],
                                 "transaction_id": first_transaction_id})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            second_transaction_id = body["detail"]["transaction_id"]
            second_question = body["detail"]["message"]
            self.assertNotEqual(first_transaction_id, second_transaction_id)

            body = self._check({"user": self.username, "pass": questions_and_answers[second_question],
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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id,
                                        previous_transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
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
                   user=self.user)
        init_token({"serial": first_admin_serial, "type": "hotp", "otpkey": self.otpkey, "pin": "firstadminpin"},
                   user=User("hans", self.realm1))
        init_token({"serial": second_admin_serial, "type": "hotp", "otpkey": self.otpkey, "pin": "secondadminpin"},
                   user=User("selfservice", self.realm1))
        try:
            body = self._check({"user": self.username, "pass": "foureyespin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            first_transaction_id = body["detail"]["transaction_id"]

            body = self._check({"user": self.username,
                                 "pass": "firstadminpin" + self.valid_otp_values[0],
                                 "transaction_id": first_transaction_id})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            second_transaction_id = body["detail"]["transaction_id"]
            self.assertNotEqual(first_transaction_id, second_transaction_id)

            body = self._check({"user": self.username,
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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={foureyes_serial}, transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=self.user,
                                        serials={foureyes_serial}, transaction_id=second_transaction_id,
                                        previous_transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={foureyes_serial}, transaction_id=second_transaction_id)

    def test_questionnaire_fail_on_intermediate_challenge(self):
        # Answering the first question wrong gives CHALLENGE_ANSWERED_FAIL with no previous_transaction_id —
        # no new challenge was created, so there is nothing to link back to.
        questions_and_answers = {"Question1": "Answer1", "Question2": "Answer2", "Question3": "Answer3",
                                  "Question4": "Answer4", "Question5": "Answer5"}
        questionnaire_serial = "AUTHLOG_QUESTIONNAIRE"
        init_token({"type": "question", "questions": questions_and_answers, "pin": "questpin",
                    "serial": questionnaire_serial},
                   user=self.user)
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            body = self._check({"user": self.username, "pass": "questpin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            first_transaction_id = body["detail"]["transaction_id"]

            body = self._check({"user": self.username, "pass": "WRONG_ANSWER",
                                 "transaction_id": first_transaction_id})
            self.assertFalse(body["result"]["value"], body)
        finally:
            delete_policy("authlog_question_number")
            remove_token(questionnaire_serial)

        entries = assert_authentication_log([
            AuthEventType.CHALLENGE_TRIGGERED,
            AuthEventType.CHALLENGE_ANSWERED_FAIL,
        ])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
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
                   user=self.user)
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            body = self._check({"user": self.username, "pass": "questpin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            first_transaction_id = body["detail"]["transaction_id"]
            first_question = body["detail"]["message"]

            body = self._check({"user": self.username, "pass": questions_and_answers[first_question],
                                 "transaction_id": first_transaction_id})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            second_transaction_id = body["detail"]["transaction_id"]

            body = self._check({"user": self.username, "pass": "WRONG_ANSWER",
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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id,
                                        previous_transaction_id=first_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
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
            body = self._check({"user": self.username, "pass": self.pin})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            hotp_transaction_id = body["detail"]["transaction_id"]

            body = self._check({"user": self.username, "pass": self.valid_otp_values[0],
                                 "transaction_id": hotp_transaction_id})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            self.assertTrue(body["detail"].get("enroll_via_multichallenge"), body)
            enrollment_transaction_id = body["detail"]["transaction_id"]
            enrolled_serial = body["detail"]["serial"]
            self.assertNotEqual(hotp_transaction_id, enrollment_transaction_id)

            totp_otp = get_one_token(serial=enrolled_serial).get_otp()[2]
            body = self._check({"user": self.username, "pass": totp_otp,
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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={self.serial}, transaction_id=hotp_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED], user=self.user,
                                        serials={enrolled_serial}, transaction_id=enrollment_transaction_id,
                                        previous_transaction_id=hotp_transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={enrolled_serial}, transaction_id=enrollment_transaction_id)


class AuthenticationLogReadAPITestCase(AuthLogTestCase):
    """GET /authenticationlog/ — pagination, filtering, realm restriction, and the admin policy gate."""

    OTHER_REALM = "otherrealm"

    def _seed_entries(self):
        # 2 in realm1, 1 in another realm, 1 with no realm (e.g. USER_UNKNOWN). Returns the created ids by key.
        ids = {
            "realm1_login": log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1",
                                                     realm=self.realm1),
            "realm1_fail": log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="2",
                                                    realm=self.realm1),
            "other_login": log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="3",
                                                    realm=self.OTHER_REALM),
            "no_realm": log_authentication_event(event_type=AuthEventType.USER_UNKNOWN),
        }
        db.session.commit()
        return ids

    def _get(self, query_string=None, status=200):
        with self.app.test_request_context('/authenticationlog/', method='GET', query_string=query_string or {},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    @staticmethod
    def _returned_ids(value):
        return {entry["id"] for entry in value["auth_logs"]}

    def test_requires_admin(self):
        with self.app.test_request_context('/authenticationlog/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)

    def test_returns_paginated_page(self):
        self._seed_entries()
        value = self._get({"page": 1, "page_size": 2})["result"]["value"]
        self.assertEqual(4, value["count"])
        self.assertEqual(2, len(value["auth_logs"]))
        self.assertEqual(1, value["current"])
        self.assertIsNone(value["prev"])
        self.assertEqual(2, value["next"])

        last = self._get({"page": 2, "page_size": 2})["result"]["value"]
        self.assertEqual(1, last["prev"])
        self.assertIsNone(last["next"])

    def test_invalid_paging_params_fall_back_to_defaults(self):
        # A bad page / page_size must not reach the query as a negative offset or empty limit: non-positive and
        # non-numeric values fall back to the defaults (page 1, default page_size) instead.
        self._seed_entries()
        for bad in ({"page": 0}, {"page": -3}, {"page": "abc"}):
            value = self._get(bad)["result"]["value"]
            self.assertEqual(1, value["current"], bad)
            self.assertEqual(4, value["count"], bad)
            self.assertEqual(4, len(value["auth_logs"]), bad)
            self.assertIsNone(value["prev"], bad)
        for bad in ({"page_size": 0}, {"page_size": -10}, {"page_size": "abc"}):
            value = self._get(bad)["result"]["value"]
            self.assertEqual(4, len(value["auth_logs"]), bad)

    def test_serialized_entry_shape(self):
        self._seed_entries()
        value = self._get({"page_size": 50})["result"]["value"]
        entry = value["auth_logs"][0]
        self.assertIn("event_type", entry)
        self.assertIn("realm", entry)
        # timestamp is serialized as an ISO 8601 string, not a datetime
        self.assertIsInstance(entry["timestamp"], str)
        datetime.datetime.fromisoformat(entry["timestamp"])

    def test_filter_by_event_type(self):
        self._seed_entries()
        value = self._get({"event_type": AuthEventType.MFA_FAIL})["result"]["value"]
        self.assertEqual(1, value["count"])
        self.assertEqual(AuthEventType.MFA_FAIL, value["auth_logs"][0]["event_type"])

    def test_filter_by_event_type_csv_list(self):
        self._seed_entries()
        value = self._get({"event_type": f"{AuthEventType.MFA_FAIL},{AuthEventType.USER_UNKNOWN}"})["result"]["value"]
        self.assertEqual(2, value["count"])
        self.assertSetEqual({AuthEventType.MFA_FAIL, AuthEventType.USER_UNKNOWN},
                            {entry["event_type"] for entry in value["auth_logs"]})

    def test_filter_by_event_type_wildcard(self):
        self._seed_entries()
        # the two LOGIN_SUCCESS rows match the LOGIN* prefix; MFA_FAIL and USER_UNKNOWN do not
        value = self._get({"event_type": "LOGIN*"})["result"]["value"]
        self.assertEqual(2, value["count"])
        self.assertSetEqual({AuthEventType.LOGIN_SUCCESS}, {entry["event_type"] for entry in value["auth_logs"]})

    def test_filter_by_user_role(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1", realm=self.realm1,
                                 user_role=AuthLogUserRole.USER)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="2", realm=self.realm1,
                                 user_role=AuthLogUserRole.ADMIN_INTERNAL)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="3", realm=self.realm1,
                                 user_role=AuthLogUserRole.ADMIN_EXTERNAL)
        db.session.commit()

        self.assertEqual(1, self._get({"user_role": AuthLogUserRole.USER})["result"]["value"]["count"])
        # The shared 'admin-' prefix lets one wildcard filter match either admin kind.
        value = self._get({"user_role": "admin*"})["result"]["value"]
        self.assertEqual(2, value["count"])
        self.assertSetEqual({AuthLogUserRole.ADMIN_INTERNAL, AuthLogUserRole.ADMIN_EXTERNAL},
                            {entry["user_role"] for entry in value["auth_logs"]})

    def test_filter_case_insensitive(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1", realm=self.realm1,
                                 username="Alice")
        db.session.commit()

        # The flag enforces a case-insensitive match regardless of the DB collation. The unflagged default follows
        # the collation (case-sensitive on SQLite, case-insensitive on a MySQL/MariaDB *_ci collation), so it is not
        # asserted here.
        self.assertEqual(1, self._get({"username": "alice", "case_insensitive": "1"})["result"]["value"]["count"])
        self.assertEqual(1, self._get({"username": "Alice"})["result"]["value"]["count"])

    def test_filter_by_client_label(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1", realm=self.realm1,
                                 client_label="vpn")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="2", realm=self.realm1,
                                 client_label="webui")
        db.session.commit()

        value = self._get({"client_label": "vpn"})["result"]["value"]
        self.assertEqual(1, value["count"])
        self.assertEqual("vpn", value["auth_logs"][0]["client_label"])

    def test_policy_gate_denies_without_action(self):
        # Admin policies exist but none grant authentication_log_read -> the admin is denied.
        set_policy("authlog_other", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        try:
            body = self._get(status=403)
            self.assertFalse(body["result"]["status"], body)
        finally:
            delete_policy("authlog_other")

    def test_realm_scoped_policy_restricts_visible_entries(self):
        ids = self._seed_entries()
        # Policy scoped to realm1: the admin sees exactly the realm1 rows, not the other realm or the null-realm row.
        set_policy("authlog_realm", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   realm=self.realm1)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual({ids["realm1_login"], ids["realm1_fail"]}, self._returned_ids(value))
        finally:
            delete_policy("authlog_realm")

    def test_resolver_scoped_policy_restricts_visible_entries(self):
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                            uid="1", realm=self.realm1)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="otherresolver", uid="2",
                                 realm=self.realm1)
        db.session.commit()
        set_policy("authlog_resolver", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   resolver=self.resolvername1)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual({in_scope}, self._returned_ids(value))
        finally:
            delete_policy("authlog_resolver")

    def test_multiple_policies_union_scopes(self):
        # P1 scopes realm1, P2 scopes resolver1 -> the admin sees (realm1) OR (resolver1).
        matches_p1 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="otherresolver",
                                              uid="1", realm=self.realm1)
        matches_p2 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                              uid="2", realm=self.OTHER_REALM)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="otherresolver", uid="3",
                                 realm=self.OTHER_REALM)                             # matches neither
        db.session.commit()
        set_policy("authlog_p1", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, realm=self.realm1)
        set_policy("authlog_p2", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   resolver=self.resolvername1)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual({matches_p1, matches_p2}, self._returned_ids(value))
        finally:
            delete_policy("authlog_p1")
            delete_policy("authlog_p2")

    def test_unscoped_policy_grants_all_even_alongside_a_scoped_one(self):
        # If any applicable policy has no target scope, the admin is unrestricted -- even when another policy is
        # scoped. (The scoped policy alone would have limited the result to realm1's 2 rows.)
        ids = self._seed_entries()  # realm1 x2, OTHER_REALM x1, null-realm x1
        set_policy("authlog_scoped", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, realm=self.realm1)
        set_policy("authlog_all", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual(set(ids.values()), self._returned_ids(value))
        finally:
            delete_policy("authlog_scoped")
            delete_policy("authlog_all")

    def test_unscoped_policy_builds_no_visibility_filter(self):
        # Efficiency: an unscoped policy grants everything, so no realm/resolver/user filter is built at all -- the
        # lib is called with visibility_scopes=None, not scopes that merely happen to match every row.
        with mock.patch("privacyidea.api.authentication_log.get_authentication_logs_paginate") as paginate_mock:
            paginate_mock.return_value.to_dict.return_value = {}
            # Only a scoped policy -> the lib receives concrete scopes.
            set_policy("authlog_scoped", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                       realm=self.realm1)
            self._get()
            self.assertIsNotNone(paginate_mock.call_args.kwargs["visibility_scopes"])
            # Adding an unscoped policy of the same action -> no filter is built at all.
            set_policy("authlog_all", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ)
            try:
                self._get()
                self.assertIsNone(paginate_mock.call_args.kwargs["visibility_scopes"])
            finally:
                delete_policy("authlog_scoped")
                delete_policy("authlog_all")

    def test_admins_own_entries_always_included(self):
        # A helpdesk admin in the superuser realm "adminrealm" has a real (username, realm), so their own entries
        # are always added to the policy scope.
        set_realm("adminrealm", [{"name": self.resolvername1}])
        with self.app.test_request_context("/auth", method="POST",
                                           data={"username": "selfservice@adminrealm", "password": "test"}):
            helpdesk_token = self.app.full_dispatch_request().json["result"]["value"]["token"]
        # The login above logged its own auth event; clear so the test works on controlled entries only.
        self._clear_log()
        # One in-scope (realm1) entry and the admin's own entry (username=selfservice, realm=adminrealm).
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                            uid="1", realm=self.realm1)
        own = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="2",
                                       realm="adminrealm", username="selfservice")
        db.session.commit()
        set_policy("authlog_realm", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, realm=self.realm1)

        def helpdesk_get(query_string):
            with self.app.test_request_context("/authenticationlog/", method="GET", query_string=query_string,
                                               headers={"Authorization": helpdesk_token}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res.json)
                return {entry["id"] for entry in res.json["result"]["value"]["auth_logs"]}
        try:
            # The realm1 entry (policy scope) plus the admin's own adminrealm entry are both returned.
            self.assertEqual({in_scope, own}, helpdesk_get({"page_size": 50}))
        finally:
            delete_policy("authlog_realm")
            delete_realm("adminrealm")


class AuthenticationLogUserReadAPITestCase(AuthLogTestCase):
    """GET /authenticationlog/ for a normal user: only their own entries, gated by the user-scope policy."""

    def setUp(self):
        super().setUp()
        # Log in the self-service user "selfservice" in realm1 (-> self.at_user, role "user").
        self.authenticate_selfservice_user()
        # That login wrote its own auth-log entry; start the test from a clean log.
        self._clear_log()

    def _user_get(self, query_string=None, status=200):
        with self.app.test_request_context("/authenticationlog/", method="GET", query_string=query_string or {},
                                           headers={"Authorization": self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    def test_user_sees_only_own_entries(self):
        own = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="1",
                                       realm=self.realm1, username="selfservice")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="2",
                                 realm=self.realm1, username="hans")  # another user, same realm
        log_authentication_event(event_type=AuthEventType.USER_UNKNOWN)  # no identity
        db.session.commit()
        set_policy("authlog_user", scope=SCOPE.USER, action=PolicyAction.AUTHENTICATION_LOG_READ)
        try:
            value = self._user_get({"page_size": 50})["result"]["value"]
            self.assertEqual({own}, {entry["id"] for entry in value["auth_logs"]})
        finally:
            delete_policy("authlog_user")

    def test_user_denied_without_action(self):
        # A user-scope policy exists but does not grant authentication_log_read -> the user is denied.
        set_policy("user_other", scope=SCOPE.USER, action=PolicyAction.DISABLE)
        try:
            body = self._user_get(status=403)
            self.assertFalse(body["result"]["status"], body)
        finally:
            delete_policy("user_other")
