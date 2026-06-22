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
from typing import TYPE_CHECKING

import mock
from flask import Response

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, AUTH_EVENT_TYPE_KEY
from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs, log_authentication_event
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
    second_serial = "AUTHLOG_HOTP2"
    username = "cornelius"
    pin = "pin"

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.user = User(self.username, self.realm1)
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": self.pin},
                   user=self.user)
        self._clear_log()

    def tearDown(self) -> None:
        for serial in (self.serial, self.second_serial):
            if get_tokens(serial=serial):
                remove_token(serial)
        self._clear_log()
        super().tearDown()

    @staticmethod
    def _clear_log() -> None:
        db.session.query(AuthenticationLog).delete()
        db.session.commit()

    @staticmethod
    def _enable_challenge_response() -> None:
        set_policy("authlog_cr", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")

    def _add_second_token(self, pin: str) -> None:
        # A second HOTP token for the same user, sharing the first token's OTP key.
        init_token({"serial": self.second_serial, "type": "hotp", "otpkey": self.otpkey, "pin": pin},
                   user=self.user)

    def _post(self, path: str, data: dict, headers: dict | None = None) -> Response:
        with self.app.test_request_context(path, method='POST', data=data, headers=headers or {}):
            return self.app.full_dispatch_request()

    def _check(self, data: dict, headers: dict | None = None) -> dict:
        # /validate/check convenience for tests that inspect the body directly; always HTTP 200.
        response = self._post('/validate/check', data, headers)
        self.assertEqual(200, response.status_code, response.json)
        return response.json


# For the type checker only, the mixin is a subclass of its cooperating fixture, so that self.serial, self.assertEqual,
# self._post, etc. resolve. At runtime the base is object: the mixin must NOT be a TestCase, or it would be collected
# and run with its abstract hooks raising NotImplementedError.
if TYPE_CHECKING:
    _ContractHost = AuthLogTestCase
else:
    _ContractHost = object


class _AuthLogContractTests(_ContractHost):
    """
    Endpoint-agnostic authentication-log contract, shared by /validate/check and /auth.

    Both endpoints funnel through ``check_user_pass`` -> ``check_token_list`` and must classify each outcome the same
    way; they differ only in transport (the success/failure status code and where the outcome is read). Each test here
    is written once and discovered on both concrete subclasses below, so it runs against both endpoints. Three hooks
    isolate what differs -- how the endpoint is called and how success/failure is asserted; the auth-log assertions,
    the actual point of these tests, stay identical.

    Both subclasses dispatch through ``full_dispatch_request`` and so the hooks exchange a single common type, the
    Flask :class:`~flask.Response`. This is a plain mixin, not a TestCase, so it is not collected on its own.
    """

    def _authenticate(self, password: str, headers: dict | None = None, **params) -> Response:
        """Authenticate ``self.user`` with *password*, optional request *headers* (e.g. a User-Agent) and any extra
        request *params* (e.g. ``transaction_id``, ``client_id``), and return the response for
        :meth:`_assert_succeeded` / :meth:`_assert_failed`."""
        raise NotImplementedError

    def _assert_succeeded(self, response: Response) -> None:
        raise NotImplementedError

    def _assert_failed(self, response: Response) -> None:
        raise NotImplementedError

    def _trigger_challenge(self) -> str:
        """Issue a challenge for ``self.user`` (PIN only) and return its transaction_id."""
        raise NotImplementedError

    # --- Transport: client label and the internal classification key ---

    def test_client_label_falls_back_to_user_agent(self):
        # With no client_id, the log's client_label falls back to the User-Agent header.
        self._authenticate(f"{self.pin}755224", headers={"User-Agent": "pytest-UA"})
        logs = get_authentication_logs()
        self.assertEqual(1, len(logs), logs)
        self.assertEqual("pytest-UA", logs[0].client_label)

    def test_client_id_sets_client_label(self):
        # An explicit client_id is recorded as the client label on the log row.
        self._assert_succeeded(self._authenticate(f"{self.pin}755224", client_id="myapp"))
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={self.serial}, client_label="myapp")

    def test_classification_key_not_leaked(self):
        # The internal classification key must never reach the client.
        response = self._authenticate(f"{self.pin}755224")
        self._assert_succeeded(response)
        self.assertNotIn(AUTH_EVENT_TYPE_KEY, response.json.get("detail") or {})

    # --- No / unusable token ---

    def test_no_token_logs_no_token(self):
        # A resolvable user without a usable token -> NO_TOKEN (set in check_user_pass)
        remove_token(self.serial)
        self._assert_failed(self._authenticate(f"{self.pin}123456"))
        entries = assert_authentication_log([AuthEventType.NO_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_TOKEN], user=self.user)

    def test_disabled_token_logs_no_usable_token(self):
        # The user has a token, but it is disabled, so it cannot be used -> NO_USABLE_TOKEN
        get_one_token(serial=self.serial).enable(False)
        self._assert_failed(self._authenticate(f"{self.pin}123456"))
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

    def test_maxfail_token_logs_no_usable_token(self):
        # The user's only token has its fail counter exceeded, so it cannot be used -> NO_USABLE_TOKEN.
        token = get_one_token(serial=self.serial)
        for _ in range(token.get_max_failcount() + 1):
            token.inc_failcount()
        self._assert_failed(self._authenticate(f"{self.pin}123456"))
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

    def test_pass_on_no_token_logs_login_success(self):
        # A user with no tokens accepted by PASSONNOTOKEN is a successful login.
        remove_token(self.serial)
        set_policy("passonnotoken", scope=SCOPE.AUTH, action=PolicyAction.PASSONNOTOKEN)
        try:
            self._assert_succeeded(self._authenticate("anypassword"))
        finally:
            delete_policy("passonnotoken")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user)

    def test_passthru_logs_login_success(self):
        # PASSTHRU=userstore: a user with no tokens who supplies the correct userstore password is accepted.
        remove_token(self.serial)
        set_policy("authlog_passthru", scope=SCOPE.AUTH, action=f"{PolicyAction.PASSTHRU}=userstore")
        try:
            self._assert_succeeded(self._authenticate("test"))
        finally:
            delete_policy("authlog_passthru")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user)

    # --- Normal auth: a single request with PIN/password + OTP concatenated ---

    def test_login_success(self):
        # OTP for counter 0 of the standard test key
        self._assert_succeeded(self._authenticate(f"{self.pin}755224"))
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={self.serial})

    def test_password_fail(self):
        # otppin=userstore: the PIN part is the userstore password; a wrong one is PASSWORD_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        try:
            self._assert_failed(self._authenticate("wrongpassword755224"))
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL], user=self.user)

    def test_pin_fail(self):
        # Wrong token PIN (otppin=token, the default) -> PIN_FAIL
        self._assert_failed(self._authenticate("wrongpin755224"))
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user)

    def test_wrong_otp_is_mfa_fail(self):
        # PIN correct, OTP wrong
        self._assert_failed(self._authenticate(f"{self.pin}000000"))
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL], user=self.user,
                                        serials={self.serial})

    # --- otppin=none: only the token is verified, no first factor (end-to-end through check_user_pass) ---

    def test_otppin_none_wrong_otp_is_token_only_fail(self):
        # otppin=none: no first factor, only the token. A wrong OTP (empty PIN) is TOKEN_ONLY_FAIL, not MFA_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            self._assert_failed(self._authenticate("000000"))
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.TOKEN_ONLY_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.TOKEN_ONLY_FAIL], user=self.user,
                                        serials={self.serial})

    def test_otppin_none_correct_otp_is_login_success(self):
        # otppin=none: the correct OTP (empty PIN) succeeds -> LOGIN_SUCCESS, with no stale token-only failure.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            self._assert_succeeded(self._authenticate("755224"))
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={self.serial})

    def test_otppin_none_pin_given_is_pin_fail(self):
        # otppin=none but a PIN is supplied anyway: the PIN check fails, the OTP is never checked, so this is a
        # rejected first-factor attempt -> PIN_FAIL (matches PIN brute-force), not TOKEN_ONLY_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            self._assert_failed(self._authenticate("somepin755224"))
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user)

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
            self._assert_failed(self._authenticate("000000", transaction_id=transaction_id))
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
            self._assert_failed(self._authenticate("755224", transaction_id=transaction_id))
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
        self._assert_failed(self._authenticate(f"{self.pin}755224", transaction_id="9" * 20))
        entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        # TODO: Should we have the serial here in the log?
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                        user=self.user, transaction_id="9" * 20)

    def test_challenge_answered_correct_logs_success(self):
        # Trigger, then answer with the correct OTP -> LOGIN_SUCCESS
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            self._assert_succeeded(self._authenticate("755224", transaction_id=transaction_id))
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

    # --- Authorization policies (NOT_AUTHORIZED) ---

    def test_authmaxfail_logs_not_authorized(self):
        # AUTHMAXFAIL=2/1m: after 2 failed auths the next request is blocked before credentials are checked.
        set_policy("authlog_maxfail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXFAIL}=2/1m")
        try:
            for _ in range(2):
                self._authenticate("wrongpin000000")
            self._clear_log()
            self._assert_failed(self._authenticate(f"{self.pin}755224"))
        finally:
            delete_policy("authlog_maxfail")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user)

    def test_authmaxsuccess_logs_not_authorized(self):
        # AUTHMAXSUCCESS=1/1m: after 1 successful auth the next request is blocked before credentials are checked.
        set_policy("authlog_maxsuccess", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXSUCCESS}=1/1m")
        try:
            self._assert_succeeded(self._authenticate(f"{self.pin}755224"))
            self._clear_log()
            self._assert_failed(self._authenticate(f"{self.pin}287082"))
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
            self._assert_failed(self._authenticate(f"{self.pin}755224"))
        finally:
            delete_policy("authlog_lastauth")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user,
                                        serials={self.serial})

    # --- Multiple tokens for one user ---

    def test_multiple_tokens_success_logs_only_matching_serial(self):
        # The second token has a distinct PIN, so "pin2<otp>" matches only it. The log must record that single
        # serial, not every token the user owns.
        self._add_second_token(pin="pin2")
        self._assert_succeeded(self._authenticate("pin2755224"))
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                        user=self.user, serials={self.second_serial})

    def test_multiple_tokens_challenge_triggered_logs_all_serials(self):
        # Both tokens are challenge-response and share the PIN, so one request with just the PIN triggers a
        # challenge on both. The single CHALLENGE_TRIGGERED row records both serials, comma-joined.
        self._add_second_token(pin=self.pin)
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED], transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={self.serial, self.second_serial}, transaction_id=transaction_id)

    # --- previous_transaction_id: a challenge answer that immediately triggers a fresh challenge links the rows
    #     (CHALLENGE_CONTINUED carrying previous_transaction_id). Both endpoints classify and link these the same. ---

    def _assert_challenge(self, response: Response) -> dict:
        # An intermediate challenge looks the same on both endpoints: HTTP 200 with a falsy result value (a /auth
        # failure would be 401). Return its detail dict so the caller can read transaction_id / message.
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(response.json["result"]["value"], response.json)
        return response.json["detail"]

    def test_questionnaire_sets_previous_transaction_id(self):
        # Questionnaire with question_number=2: PIN triggers question 1 (first_transaction_id), answering question 1
        # triggers question 2 (second_transaction_id), answering question 2 is a LOGIN_SUCCESS. The middle step has
        # previous_transaction_id=first_transaction_id because it answered the first challenge and created a new one.
        questions_and_answers = {"Question1": "Answer1", "Question2": "Answer2", "Question3": "Answer3",
                                 "Question4": "Answer4", "Question5": "Answer5"}
        questionnaire_serial = "AUTHLOG_QUESTIONNAIRE"
        init_token({"type": "question", "questions": questions_and_answers, "pin": "questpin",
                    "serial": questionnaire_serial}, user=self.user)
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            detail = self._assert_challenge(self._authenticate("questpin"))
            first_transaction_id = detail["transaction_id"]
            first_question = detail["message"]

            detail = self._assert_challenge(
                self._authenticate(questions_and_answers[first_question], transaction_id=first_transaction_id))
            second_transaction_id = detail["transaction_id"]
            second_question = detail["message"]
            self.assertNotEqual(first_transaction_id, second_transaction_id)

            self._assert_succeeded(
                self._authenticate(questions_and_answers[second_question], transaction_id=second_transaction_id))
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
            detail = self._assert_challenge(self._authenticate("foureyespin"))
            first_transaction_id = detail["transaction_id"]

            detail = self._assert_challenge(
                self._authenticate("firstadminpin" + self.valid_otp_values[0], transaction_id=first_transaction_id))
            second_transaction_id = detail["transaction_id"]
            self.assertNotEqual(first_transaction_id, second_transaction_id)

            self._assert_succeeded(
                self._authenticate("secondadminpin" + self.valid_otp_values[0], transaction_id=second_transaction_id))
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
                    "serial": questionnaire_serial}, user=self.user)
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            first_transaction_id = self._assert_challenge(self._authenticate("questpin"))["transaction_id"]
            self._assert_failed(self._authenticate("WRONG_ANSWER", transaction_id=first_transaction_id))
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
                    "serial": questionnaire_serial}, user=self.user)
        set_policy("authlog_question_number", scope=SCOPE.AUTH, action="question_number=2")
        try:
            detail = self._assert_challenge(self._authenticate("questpin"))
            first_transaction_id = detail["transaction_id"]
            first_question = detail["message"]

            detail = self._assert_challenge(
                self._authenticate(questions_and_answers[first_question], transaction_id=first_transaction_id))
            second_transaction_id = detail["transaction_id"]

            self._assert_failed(self._authenticate("WRONG_ANSWER", transaction_id=second_transaction_id))
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


class ValidateCheckAuthLogTestCase(_AuthLogContractTests, AuthLogTestCase):
    """The shared contract plus /validate/check-only cases: transport details, divergent error paths, serial flows,
    enrollment and authorization."""

    # --- contract hooks ---

    def _authenticate(self, password: str, headers: dict | None = None, **params) -> Response:
        return self._post('/validate/check', {"user": self.username, "pass": password, **params}, headers)

    def _assert_succeeded(self, response: Response) -> None:
        self.assertTrue(response.json["result"]["value"], response.json)

    def _assert_failed(self, response: Response) -> None:
        self.assertFalse(response.json["result"]["value"], response.json)

    def _trigger_challenge(self) -> str:
        body = self._authenticate(self.pin).json
        self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
        return body["detail"]["transaction_id"]

    # --- Paths that diverge from /auth in return type / error code ---

    def test_revoked_token_logs_no_usable_token(self):
        # All of the user's tokens are revoked: check_token_list raises TOKEN_LOCKED (ERR1007) before it can classify
        # the request. The API catches that, records NO_USABLE_TOKEN for the log, and re-raises so the error response
        # is unchanged.
        revoke_token(self.serial)
        res = self._post('/validate/check', {"user": self.username, "pass": f"{self.pin}755224"})
        self.assertEqual(400, res.status_code, res.json)
        self.assertEqual(1007, res.json["result"]["error"]["code"], res.json)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user)

    def test_unknown_user_logs_user_unknown(self):
        # An unknown user is rejected by the auth_user_does_not_exist policy decorator;
        # the API catches that and still logs USER_UNKNOWN (high-signal for stuffing).
        res = self._post('/validate/check', {"user": "doesnotexist", "realm": self.realm1, "pass": "whatever"})
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

    # --- Enroll via multi challenge ---

    def test_enroll_via_multichallenge_trigger_and_completion(self):
        # The user authenticates with the existing token, which triggers an enrollment challenge for a token type the
        # user does not have yet (totp) in the post-policy -> ENROLLMENT_TRIGGERED. Answering with the freshly enrolled
        # token's OTP completes the login -> LOGIN_SUCCESS. Both rows are correlated by the enrollment transaction_id.
        set_policy("authlog_enroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")
        try:
            body = self._check({"user": self.username, "pass": f"{self.pin}755224"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            self.assertTrue(body["detail"].get("enroll_via_multichallenge"), body)
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

    def test_enroll_triggered_via_challenge_response(self):
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

    # --- Authorization policies (NOT_AUTHORIZED) — /validate/check-only; the shared authz cases live in the mixin ---

    def test_is_authorized_deny_logs_not_authorized(self):
        # authorized=deny_access: a successful auth is reclassified to NOT_AUTHORIZED and the response is 400.
        set_policy("authlog_deny", scope=SCOPE.AUTHZ,
                   action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            res = self._post('/validate/check', {"user": self.username, "pass": f"{self.pin}755224"})
            self.assertEqual(400, res.status_code, res.json)
        finally:
            delete_policy("authlog_deny")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user)


class AuthEndpointAuthLogTestCase(_AuthLogContractTests, AuthLogTestCase):
    """The shared contract plus /auth-only cases: local-admin login, divergent error codes and authorization."""

    @staticmethod
    def _enable_privacyidea_login() -> None:
        # WebUI login against privacyIDEA: the user logs in with their token (PIN+OTP),
        # so the /auth login runs the full check_user_pass classification matrix.
        set_policy("authlog_login_mode", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")

    def _auth(self, data: dict, status: int | None = None, headers: dict | None = None) -> Response:
        response = self._post('/auth', data, headers)
        if status is not None:
            self.assertEqual(status, response.status_code, response.json)
        return response

    # --- contract hooks ---

    def _authenticate(self, password: str, headers: dict | None = None, **params) -> Response:
        # /auth only runs the check_user_pass classification matrix when LOGINMODE=privacyIDEA; enable it per call.
        self._enable_privacyidea_login()
        try:
            return self._auth({"username": self.username, "realm": self.realm1, "password": password, **params},
                              headers=headers)
        finally:
            delete_policy("authlog_login_mode")

    def _assert_succeeded(self, response: Response) -> None:
        self.assertEqual(200, response.status_code, response.json)
        self.assertTrue(response.json["result"]["value"]["token"], response.json)

    def _assert_failed(self, response: Response) -> None:
        self.assertEqual(401, response.status_code, response.json)

    def _trigger_challenge(self) -> str:
        response = self._authenticate(self.pin)
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(response.json["result"]["value"], response.json)
        return response.json["detail"]["transaction_id"]

    # --- /auth-only cases ---

    def test_auth_endpoint_logs_login(self):
        # A wrong /auth login (local admin) falls through to userstore auth against the default realm, so realm1 is
        # recorded. The testadmin user does not exist in realm1's resolver, so resolver and uid are absent.
        self._auth({"username": self.testadmin, "password": "wrong"}, status=401)
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL],
                                        user=User(self.testadmin, self.realm1))

        self._clear_log()
        # A successful local-admin login uses User() (empty), so no identity fields are recorded.
        response = self._auth({"username": self.testadmin, "password": self.testadminpw}, status=200)
        self.assertTrue(response.json["result"]["value"]["token"], response.json)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS])

    def test_revoked_token_logs_no_usable_token(self):
        # All of the user's tokens are revoked: check_user_pass raises TOKEN_LOCKED before it can classify the
        # request. /auth keeps its generic "Wrong credentials" (4031) response, but the log must still record
        # NO_USABLE_TOKEN.
        revoke_token(self.serial)
        self._enable_privacyidea_login()
        try:
            res = self._auth({"username": self.username, "realm": self.realm1, "password": f"{self.pin}755224"},
                             status=401)
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


class AuthenticationLogApiTestCase(AuthLogTestCase):
    """The /authenticationlog/ API: admin GET (pagination, filtering, realm/resolver visibility, the policy gate),
    admin DELETE (filtered bulk delete), and user-scope GET. All share the same blueprint and seed fixtures."""

    OTHER_REALM = "otherrealm"

    def _seed(self, include_no_realm=False):
        # LOGIN_SUCCESS + MFA_FAIL in realm1 and a LOGIN_SUCCESS in another realm; optionally a null-realm row
        # (e.g. USER_UNKNOWN). Returns the created ids by key.
        ids = {
            "realm1_login": log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1",
                                                     realm=self.realm1),
            "realm1_fail": log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="2",
                                                    realm=self.realm1),
            "other_login": log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="3",
                                                    realm=self.OTHER_REALM),
        }
        if include_no_realm:
            ids["no_realm"] = log_authentication_event(event_type=AuthEventType.USER_UNKNOWN)
        db.session.commit()
        return ids

    def _get(self, query_string=None, status=200):
        with self.app.test_request_context('/authenticationlog/', method='GET', query_string=query_string or {},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    def _delete(self, query_string=None, status=200):
        with self.app.test_request_context("/authenticationlog/", method="DELETE", query_string=query_string or {},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    def _user_get(self, query_string=None, status=200):
        with self.app.test_request_context("/authenticationlog/", method="GET", query_string=query_string or {},
                                           headers={"Authorization": self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    @staticmethod
    def _returned_ids(value):
        return {entry["id"] for entry in value["auth_logs"]}

    @staticmethod
    def _remaining_ids():
        return {entry.id for entry in get_authentication_logs()}

    # --- admin GET ---

    def test_requires_admin(self):
        with self.app.test_request_context('/authenticationlog/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)

    def test_returns_paginated_page(self):
        self._seed(include_no_realm=True)
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
        self._seed(include_no_realm=True)
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
        self._seed(include_no_realm=True)
        value = self._get({"page_size": 50})["result"]["value"]
        entry = value["auth_logs"][0]
        self.assertIn("event_type", entry)
        self.assertIn("realm", entry)
        # timestamp is serialized as an ISO 8601 string, not a datetime
        self.assertIsInstance(entry["timestamp"], str)
        datetime.datetime.fromisoformat(entry["timestamp"])

    def test_filter_by_event_type(self):
        self._seed(include_no_realm=True)
        value = self._get({"event_type": AuthEventType.MFA_FAIL})["result"]["value"]
        self.assertEqual(1, value["count"])
        self.assertEqual(AuthEventType.MFA_FAIL, value["auth_logs"][0]["event_type"])

    def test_policy_gate_denies_without_action(self):
        # Admin policies exist but none grant authentication_log_read -> the admin is denied.
        set_policy("authlog_other", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        try:
            body = self._get(status=403)
            self.assertFalse(body["result"]["status"], body)
        finally:
            delete_policy("authlog_other")

    def test_realm_scoped_policy_restricts_visible_entries(self):
        ids = self._seed(include_no_realm=True)
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
                                 realm=self.OTHER_REALM)  # matches neither
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
        ids = self._seed(include_no_realm=True)  # realm1 x2, OTHER_REALM x1, null-realm x1
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

    def test_include_own_adds_admins_own_entries(self):
        # A helpdesk admin in the superuser realm "adminrealm" has a real (username, realm), so include_own works.
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
            # Without include_own: only the realm1 entry.
            self.assertEqual({in_scope}, helpdesk_get({"page_size": 50}))
            # With include_own: the realm1 entry plus the admin's own adminrealm entry.
            self.assertEqual({in_scope, own}, helpdesk_get({"page_size": 50, "include_own": "1"}))
        finally:
            delete_policy("authlog_realm")
            delete_realm("adminrealm")


    # --- admin DELETE ---

    def test_delete_requires_admin(self):
        with self.app.test_request_context("/authenticationlog/", method="DELETE",
                                           query_string={"event_type": AuthEventType.MFA_FAIL}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)

    def test_delete_without_filter_is_rejected(self):
        self._seed()
        self._delete(status=400)
        self.assertEqual(3, len(get_authentication_logs()))

    def test_delete_by_filter(self):
        ids = self._seed()
        body = self._delete({"event_type": AuthEventType.MFA_FAIL})
        self.assertEqual(1, body["result"]["value"])
        # Exactly the MFA_FAIL row is gone; the two LOGIN_SUCCESS rows remain.
        self.assertEqual({ids["realm1_login"], ids["other_login"]}, self._remaining_ids())

    def test_delete_older_than_end(self):
        self._seed()
        past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).isoformat()
        future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=1)).isoformat()
        # Nothing is older than a minute ago
        self.assertEqual(0, self._delete({"end": past})["result"]["value"])
        self.assertEqual(3, len(get_authentication_logs()))
        # Everything is older than a minute from now
        self.assertEqual(3, self._delete({"end": future})["result"]["value"])
        self.assertEqual(0, len(get_authentication_logs()))

    def test_delete_policy_gate_denies(self):
        # Admin policies exist but none grant authentication_log_delete -> denied and nothing is deleted.
        self._seed()
        set_policy("authlog_other", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        try:
            self._delete({"event_type": AuthEventType.MFA_FAIL}, status=403)
        finally:
            delete_policy("authlog_other")
        self.assertEqual(3, len(get_authentication_logs()))

    def test_delete_realm_restriction(self):
        ids = self._seed()
        set_policy("authlog_delete_realm", scope=SCOPE.ADMIN,
                   action=PolicyAction.AUTHENTICATION_LOG_DELETE, realm=self.realm1)
        try:
            # Deleting all LOGIN_SUCCESS only affects realm1; the realm1 MFA_FAIL and the other realm's row survive.
            count = self._delete({"event_type": AuthEventType.LOGIN_SUCCESS})["result"]["value"]
            self.assertEqual(1, count)
            self.assertEqual({ids["realm1_fail"], ids["other_login"]}, self._remaining_ids())
        finally:
            delete_policy("authlog_delete_realm")

    def test_delete_resolver_restriction(self):
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver=self.resolvername1, uid="1",
                                 realm=self.realm1)  # in scope -> deleted
        other = log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="otherresolver", uid="2",
                                         realm=self.realm1)
        db.session.commit()
        set_policy("authlog_delete_resolver", scope=SCOPE.ADMIN,
                   action=PolicyAction.AUTHENTICATION_LOG_DELETE, resolver=self.resolvername1)
        try:
            # Deleting all MFA_FAIL only removes the scoped resolver's row; the other resolver's row survives.
            count = self._delete({"event_type": AuthEventType.MFA_FAIL})["result"]["value"]
            self.assertEqual(1, count)
            self.assertEqual({other}, self._remaining_ids())
        finally:
            delete_policy("authlog_delete_resolver")


    # --- user-scope GET (a normal user sees only their own entries) ---

    def test_user_sees_only_own_entries(self):
        # Log in the self-service user "selfservice" in realm1 (-> self.at_user); that login writes its own auth-log
        # entry, so clear the log to test on controlled entries only.
        self.authenticate_selfservice_user()
        self._clear_log()
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
        self.authenticate_selfservice_user()  # -> self.at_user
        set_policy("user_other", scope=SCOPE.USER, action=PolicyAction.DISABLE)
        try:
            body = self._user_get(status=403)
            self.assertFalse(body["result"]["status"], body)
        finally:
            delete_policy("user_other")
