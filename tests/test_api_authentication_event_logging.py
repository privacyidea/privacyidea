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
End-to-end tests that authenticating records the correct authentication-log events.

The lib layer classifies each request outcome (stashed in reply_dict) and the API layer persists exactly one row per
request, populates client_label and never leaks the internal classification key. The shared contract
(:class:`_AuthLogContractTests`) is asserted identically against both /validate/check and /auth; /validate/triggerchallenge
has its own class. The /authenticationlog/ read/delete API is covered separately in test_api_authentication_log.py.
"""
import datetime
from typing import TYPE_CHECKING

from flask import Response

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, AUTH_EVENT_TYPE_KEY
from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE, PolicyAction, AUTHORIZED
from privacyidea.lib.token import init_token, remove_token, get_one_token, revoke_token
from privacyidea.lib.user import User
from privacyidea.models.utils import utc_now
from .authlog_utils import AuthLogTestCase, assert_authentication_log, assert_authentication_log_entry


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
