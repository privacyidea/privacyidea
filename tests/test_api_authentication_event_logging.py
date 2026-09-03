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
(:class:`_AuthLogContractTests`) is asserted identically against both /validate/check and /auth;
/validate/triggerchallenge has its own class. The /authenticationlog/ read/delete API is covered separately in
test_api_authentication_log.py.
"""
import datetime
from typing import TYPE_CHECKING

import mock

from flask import Response

from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType, AUTH_EVENT_TYPE_KEY,
                                                                          AuthEventReason)
from privacyidea.lib.auth import create_db_admin, delete_db_admin
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs, AuthLogUserRole
from privacyidea.lib.conditional_access.request_context import ATTEMPT_ID_CHALLENGE_KEY
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE, PolicyAction, AUTHORIZED
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.token import init_token, remove_token, get_one_token, revoke_token
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import Challenge, db
from .authlog_utils import AuthLogTestCase, assert_authentication_log, assert_authentication_log_entry


# The type checker treats _ContractHost as the fixture class, so self.serial, self.assertEqual, self._post, etc.
# resolve; at runtime the base is plain object, because a TestCase base here would be collected and run, raising
# NotImplementedError from the abstract hooks.
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

    # The request path :meth:`_authenticate` posts to, i.e. the endpoint the log must name.
    endpoint_path: str

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
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user, serials={self.serial},
                                        client_label="myapp", endpoint=self.endpoint_path)

    def test_endpoint_records_the_request_path(self):
        # Which endpoint authenticated is a column of its own, so a row can be read (and filtered) by it.
        self._assert_succeeded(self._authenticate(f"{self.pin}755224"))
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user, serials={self.serial},
                                        endpoint=self.endpoint_path)

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
        assert_authentication_log_entry(entries[AuthEventType.NO_TOKEN], user=self.user, endpoint=self.endpoint_path)

    def test_disabled_token_logs_no_usable_token(self):
        # The user has a token, but it is disabled, so it cannot be used -> NO_USABLE_TOKEN
        get_one_token(serial=self.serial).enable(False)
        self._assert_failed(self._authenticate(f"{self.pin}123456"))
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        # NO_USABLE_TOKEN is the same event for five different token states, so the reason is what makes the row
        # actionable - and it is recorded per serial as well, for a user whose tokens failed differently.
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                        reason=AuthEventReason.TOKEN_DISABLED,
                                        reasons={self.serial: AuthEventReason.TOKEN_DISABLED},
                                        endpoint=self.endpoint_path)

    def test_maxfail_token_logs_no_usable_token(self):
        # The user's only token has its fail counter exceeded, so it cannot be used -> NO_USABLE_TOKEN.
        token = get_one_token(serial=self.serial)
        for _ in range(token.get_max_failcount() + 1):
            token.inc_failcount()
        self._assert_failed(self._authenticate(f"{self.pin}123456"))
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                        reason=AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED,
                                        reasons={self.serial: AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED},
                                        endpoint=self.endpoint_path)

    def test_disabled_type_that_filters_itself_still_reports_disabled(self):
        # push and passkey express "disabled" through use_for_authentication, so they never reach check_all - which
        # would have named the state. The generic "not applicable to this request" would misdirect the admin.
        remove_token(self.serial)
        init_token({"serial": "AUTHLOG_PUSH", "type": "push", "genkey": 1}, user=self.user)
        try:
            get_one_token(serial="AUTHLOG_PUSH").enable(False)
            self._assert_failed(self._authenticate(f"{self.pin}123456"))
            entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
            assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                            reason=AuthEventReason.TOKEN_DISABLED,
                                            reasons={"AUTHLOG_PUSH": AuthEventReason.TOKEN_DISABLED},
                                            endpoint=self.endpoint_path)
        finally:
            remove_token("AUTHLOG_PUSH")

    def test_pass_on_no_token_logs_login_success(self):
        # A user with no tokens accepted by PASSONNOTOKEN is a successful login.
        remove_token(self.serial)
        set_policy("passonnotoken", scope=SCOPE.AUTH, action=PolicyAction.PASSONNOTOKEN)
        try:
            self._assert_succeeded(self._authenticate("anypassword"))
        finally:
            delete_policy("passonnotoken")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        endpoint=self.endpoint_path)

    def test_passthru_logs_login_success(self):
        # PASSTHRU=userstore: a user with no tokens who supplies the correct userstore password is accepted.
        remove_token(self.serial)
        set_policy("authlog_passthru", scope=SCOPE.AUTH, action=f"{PolicyAction.PASSTHRU}=userstore")
        try:
            self._assert_succeeded(self._authenticate("test"))
        finally:
            delete_policy("authlog_passthru")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        endpoint=self.endpoint_path)

    # --- Normal auth: a single request with PIN/password + OTP concatenated ---

    def test_login_success(self):
        # OTP for counter 0 of the standard test key
        self._assert_succeeded(self._authenticate(f"{self.pin}755224"))
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user, serials={self.serial},
                                        endpoint=self.endpoint_path)

    def test_password_fail(self):
        # otppin=userstore: the PIN part is the userstore password; a wrong one is PASSWORD_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        try:
            self._assert_failed(self._authenticate("wrongpassword755224"))
        finally:
            delete_policy("authlog_otppin")
        # PASSWORD_FAIL already names the credential that failed, so the row carries no reason of its own.
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL], user=self.user, reason=[],
                                        endpoint=self.endpoint_path)

    def test_force_challenge_response_keeps_the_userstore_classification(self):
        # force_challenge_response skips the authentication attempt, but is_challenge_request already ran check_pin -
        # so auth_otppin has classified the wrong user store password. The row must not blame the token PIN.
        # challenge_response has to be enabled too: challenge_response_allowed short-circuits is_challenge_request to
        # False for a type that may not do challenge-response, and then check_pin never runs.
        self._enable_challenge_response()
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        set_policy("authlog_force_cr", scope=SCOPE.AUTH, action=f"{PolicyAction.FORCE_CHALLENGE_RESPONSE}=hotp")
        try:
            self._assert_failed(self._authenticate("wrongpassword755224"))
        finally:
            delete_policy("authlog_cr")
            delete_policy("authlog_otppin")
            delete_policy("authlog_force_cr")
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL], user=self.user, reason=[],
                                        endpoint=self.endpoint_path)

    def test_challenge_response_does_not_turn_a_wrong_otp_into_a_password_failure(self):
        # check_pin runs twice per request with challenge-response enabled: is_challenge_request asks with the whole
        # password+OTP string, which fails the user store, and authenticate then asks again with the split password,
        # which passes. The first, stale failure must not outlive the second - a correct password with a wrong OTP is
        # MFA_FAIL / WRONG_OTP, and recording PASSWORD_FAIL would also feed the wrong OTP to a lockout policy
        # counting password failures (the shipped Password Brute-Force template does).
        self._enable_challenge_response()
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        try:
            self._assert_failed(self._authenticate("test000000"))
        finally:
            delete_policy("authlog_otppin")
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL], user=self.user, serials={self.serial},
                                        reason=AuthEventReason.WRONG_OTP, endpoint=self.endpoint_path,
                                        reasons={self.serial: AuthEventReason.WRONG_OTP})

    def test_pin_fail(self):
        # Wrong token PIN (otppin=token, the default) -> PIN_FAIL, which names the credential itself, so no reason.
        self._assert_failed(self._authenticate("wrongpin755224"))
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user, reason=[],
                                        endpoint=self.endpoint_path)

    def test_wrong_otp_is_mfa_fail(self):
        # PIN correct, OTP wrong
        self._assert_failed(self._authenticate(f"{self.pin}000000"))
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL], user=self.user, serials={self.serial},
                                        reason=AuthEventReason.WRONG_OTP, endpoint=self.endpoint_path,
                                        reasons={self.serial: AuthEventReason.WRONG_OTP})

    # --- otppin=none: only the token is verified, no first factor (end-to-end through check_user_pass) ---

    def test_otppin_none_wrong_otp_is_token_only_fail(self):
        # otppin=none: no first factor, only the token. A wrong OTP (empty PIN) is TOKEN_ONLY_FAIL, not MFA_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            self._assert_failed(self._authenticate("000000"))
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.TOKEN_ONLY_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.TOKEN_ONLY_FAIL], user=self.user, serials={self.serial},
                                        reason=AuthEventReason.WRONG_OTP, endpoint=self.endpoint_path,
                                        reasons={self.serial: AuthEventReason.WRONG_OTP})

    def test_otppin_none_correct_otp_is_login_success(self):
        # otppin=none: the correct OTP (empty PIN) succeeds -> LOGIN_SUCCESS, with no stale token-only failure.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            self._assert_succeeded(self._authenticate("755224"))
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user, serials={self.serial},
                                        endpoint=self.endpoint_path)

    def test_otppin_none_pin_given_is_pin_fail(self):
        # otppin=none but a PIN is supplied anyway: the PIN check fails, the OTP is never checked, so this is a
        # rejected first-factor attempt -> PIN_FAIL (matches PIN brute-force), not TOKEN_ONLY_FAIL.
        set_policy("authlog_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none")
        try:
            self._assert_failed(self._authenticate("somepin755224"))
        finally:
            delete_policy("authlog_otppin")
        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user, endpoint=self.endpoint_path)

    # --- Challenge response ---

    def test_challenge_triggered(self):
        # A challenge-response token issues a challenge -> CHALLENGE_TRIGGERED
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED], transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        endpoint=self.endpoint_path)

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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        endpoint=self.endpoint_path)
        # The challenge was there, the answer was not right: distinct from a transaction that holds no challenge.
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        reason=AuthEventReason.CHALLENGE_WRONG_RESPONSE,
                                        reasons={self.serial: AuthEventReason.CHALLENGE_WRONG_RESPONSE},
                                        endpoint=self.endpoint_path)

    def test_a_token_that_refuses_the_answer_without_naming_a_state(self):
        # The fitness check is check_all, so a token that lost its fitness between the trigger and the answer
        # normally names the state itself. TOKEN_NOT_FIT_FOR_CHALLENGE is the fallback for a token type that refuses
        # without naming one - patched here, since no shipped type does that, and the row would otherwise blame the
        # answer for something the token decided.
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            with mock.patch.object(TokenClass, "is_fit_for_challenge", return_value=False):
                self._assert_failed(self._authenticate("755224", transaction_id=transaction_id))
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        endpoint=self.endpoint_path)
        # The response matched, so the reason is the token's refusal rather than a wrong answer.
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        reason=AuthEventReason.TOKEN_NOT_FIT_FOR_CHALLENGE,
                                        reasons={self.serial: AuthEventReason.TOKEN_NOT_FIT_FOR_CHALLENGE},
                                        endpoint=self.endpoint_path)

    def test_challenge_expired_answered_fail(self):
        # Trigger, expire the challenge in the DB, then answer with the correct OTP -> CHALLENGE_ANSWERED_FAIL
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            self._expire_challenges(transaction_id)
            self._assert_failed(self._authenticate("755224", transaction_id=transaction_id))
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        endpoint=self.endpoint_path)
        # The OTP was right and the challenge was still stored, only lapsed: a timeout, not a wrong answer and not
        # an unknown transaction.
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        reason=AuthEventReason.CHALLENGE_EXPIRED,
                                        reasons={self.serial: AuthEventReason.CHALLENGE_EXPIRED},
                                        endpoint=self.endpoint_path)

    def test_challenge_stale_transaction_answered_fail(self):
        # A transaction_id with no live challenge for the token (expired, cleaned up or for another token) is still a
        # failed challenge answer -> CHALLENGE_ANSWERED_FAIL (not PIN_FAIL).
        self._assert_failed(self._authenticate(f"{self.pin}755224", transaction_id="9" * 20))
        entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        # TODO: Should we have the serial here in the log?
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
                                        transaction_id="9" * 20, reason=AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION,
                                        reasons={self.serial: AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION},
                                        endpoint=self.endpoint_path)

    def test_unknown_transaction_is_dropped_from_the_row_next_to_a_live_wrong_response(self):
        # A second token that never issued this transaction also reports CHALLENGE_UNKNOWN_TRANSACTION for it, but
        # the first token did have a live challenge and the answer was simply wrong for it - the credentials could
        # still have been right, just for the wrong transaction, so pairing both on the row would read as two
        # separate problems rather than one. The row's main reason therefore names only the live finding
        # (CHALLENGE_WRONG_RESPONSE); the per-serial detail keeps both, since which token said what is still worth
        # recording there.
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
        finally:
            delete_policy("authlog_cr")
        self._add_second_token(pin=self.pin)
        self._assert_failed(self._authenticate("000000", transaction_id=transaction_id))
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_FAIL],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        reason=AuthEventReason.CHALLENGE_WRONG_RESPONSE,
                                        reasons={self.serial: AuthEventReason.CHALLENGE_WRONG_RESPONSE,
                                                 self.second_serial: AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION},
                                        endpoint=self.endpoint_path)

    def test_answering_a_challenge_with_a_disabled_token_reports_disabled(self):
        # The token is dropped by check_all before the answer is even looked at, so this is NO_USABLE_TOKEN - and the
        # reason names the state rather than the challenge. (The is_fit_for_challenge branch, which reports
        # TOKEN_NOT_FIT_FOR_CHALLENGE, is only reachable when a token's state changes *within* one request: that
        # method is check_all itself, with no override anywhere.)
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            token = get_one_token(serial=self.serial)
            token.enable(False)
            token.save()
            self._assert_failed(self._authenticate("755224", transaction_id=transaction_id))
        finally:
            delete_policy("authlog_cr")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.NO_USABLE_TOKEN],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                        serials={self.serial},
                                        transaction_id=transaction_id, reason=AuthEventReason.TOKEN_DISABLED,
                                        reasons={self.serial: AuthEventReason.TOKEN_DISABLED},
                                        endpoint=self.endpoint_path)

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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user, serials={self.serial},
                                        transaction_id=transaction_id, endpoint=self.endpoint_path)

    # --- attempt_id: grouping the rows of one logical authentication attempt ---
    # Single-flow grouping is already asserted by assert_authentication_log(same_attempt=True) in every test above;
    # these two additionally cover a genuinely multi-attempt log and a wrong-then-right retry on one challenge.

    def test_attempt_id_distinct_for_separate_attempts(self):
        # Two independent single-request logins are two attempts and get two different attempt_ids.
        self._assert_succeeded(self._authenticate(f"{self.pin}755224"))
        self._assert_succeeded(self._authenticate(f"{self.pin}287082"))
        first, second = assert_authentication_log([AuthEventType.LOGIN_SUCCESS, AuthEventType.LOGIN_SUCCESS],
                                                  same_attempt=False).all
        self.assertNotEqual(first.attempt_id, second.attempt_id)

    def test_attempt_id_groups_challenge_retry(self):
        # A wrong answer followed by the correct one on the same challenge is still one attempt: trigger, wrong answer
        # and success share one attempt_id, since a later success does not start a new attempt (asserted here by the
        # default same_attempt check).
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            self._assert_failed(self._authenticate("000000", transaction_id=transaction_id))
            self._assert_succeeded(self._authenticate("755224", transaction_id=transaction_id))
        finally:
            delete_policy("authlog_cr")
        assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED,
                                   AuthEventType.CHALLENGE_ANSWERED_FAIL,
                                   AuthEventType.LOGIN_SUCCESS],
                                  transaction_id=transaction_id)

    def test_attempt_id_is_carried_by_the_challenge(self):
        # The grouping lives in the triggered challenge's own data, not the authentication log, so the answer still
        # joins its attempt even after the trigger row is deleted; a successful answer needs this too, since the token
        # logic deletes the challenge it answers.
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED], transaction_id=transaction_id)
            attempt_id = entries[AuthEventType.CHALLENGE_TRIGGERED].attempt_id
            challenges = get_challenges(transaction_id=transaction_id)
            self.assertEqual(1, len(challenges))
            self.assertEqual(attempt_id, challenges[0].get_data()[ATTEMPT_ID_CHALLENGE_KEY])
            self._clear_log()
            self._assert_succeeded(self._authenticate("755224", transaction_id=transaction_id))
        finally:
            delete_policy("authlog_cr")
        success = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        self.assertEqual(attempt_id, success[AuthEventType.LOGIN_SUCCESS].attempt_id)

    def test_uncontinuable_transaction_is_logged(self):
        # A transaction whose challenge records no attempt starts a new attempt and logs a debug line saying so, the
        # only signal if before_request's resolution order ever breaks; the converse (a live challenge staying silent)
        # is covered by test_attempt_id_is_carried_by_the_challenge.
        with self.assertLogs("privacyidea.api.lib.utils", level="DEBUG") as captured:
            self._assert_failed(self._authenticate("755224", transaction_id="9999999999999999999"))
        self.assertTrue(any("has no challenge recording an authentication attempt" in line
                            for line in captured.output), captured.output)
        assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])

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
        # The reason names which of the two limits was hit, which NOT_AUTHORIZED alone does not say. The deciding
        # policy is only named in the audit log: the checks hand their reply_dict to the client, so it carries
        # nothing internal.
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user,
                                        reason=AuthEventReason.AUTH_MAX_FAIL, endpoint=self.endpoint_path)

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
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user,
                                        reason=AuthEventReason.AUTH_MAX_SUCCESS, endpoint=self.endpoint_path)

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
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user, serials={self.serial},
                                        reason=AuthEventReason.LAST_AUTH_TOO_OLD, policies=["authlog_lastauth"],
                                        endpoint=self.endpoint_path)

    # --- Multiple tokens for one user ---

    def test_multiple_tokens_success_logs_only_matching_serial(self):
        # The second token has a distinct PIN, so "pin2<otp>" matches only it. The log must record that single
        # serial, not every token the user owns.
        self._add_second_token(pin="pin2")
        self._assert_succeeded(self._authenticate("pin2755224"))
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={self.second_serial}, endpoint=self.endpoint_path)

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
                                        serials={self.serial, self.second_serial}, transaction_id=transaction_id,
                                        endpoint=self.endpoint_path)

    def test_the_row_lists_every_reason_while_every_token_keeps_its_own(self):
        # Two tokens, unusable for two different reasons. The row carries both - each is a separate piece of advice
        # for the admin and each is filterable on its own - in the order AuthEventReason declares them, which is what
        # makes the list deterministic rather than a statement about which matters more. Which token failed for which
        # reason stays in the per-serial map.
        self._add_second_token(pin=self.pin)
        first = get_one_token(serial=self.serial)
        first.enable(False)
        # enable() only assigns; the second token's failcount writes below would otherwise be the only thing saved.
        first.save()
        second = get_one_token(serial=self.second_serial)
        for _ in range(second.get_max_failcount() + 1):
            second.inc_failcount()

        self._assert_failed(self._authenticate(f"{self.pin}755224"))

        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                        reason=[AuthEventReason.TOKEN_DISABLED,
                                                AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED],
                                        reasons={self.serial: AuthEventReason.TOKEN_DISABLED,
                                                 self.second_serial: AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED},
                                        endpoint=self.endpoint_path)

    def test_the_row_lists_every_reason_when_a_challenge_answer_finds_no_usable_token(self):
        # The same contract on the challenge-response path: both tokens issued a challenge, then became unusable for
        # two different reasons before the answer arrived. check_all drops each of them before the answer is looked
        # at, so the row is NO_USABLE_TOKEN and carries both findings - answering a transaction does not collapse
        # them into whichever token was dropped first.
        self._add_second_token(pin=self.pin)
        self._enable_challenge_response()
        try:
            transaction_id = self._trigger_challenge()
            first = get_one_token(serial=self.serial)
            first.enable(False)
            # enable() only assigns; the second token's failcount writes below would otherwise be the only thing saved.
            first.save()
            second = get_one_token(serial=self.second_serial)
            for _ in range(second.get_max_failcount() + 1):
                second.inc_failcount()

            self._assert_failed(self._authenticate("755224", transaction_id=transaction_id))
        finally:
            delete_policy("authlog_cr")

        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.NO_USABLE_TOKEN],
                                            transaction_id=transaction_id)
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                        serials={self.serial, self.second_serial},
                                        transaction_id=transaction_id,
                                        reason=[AuthEventReason.TOKEN_DISABLED,
                                                AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED],
                                        reasons={self.serial: AuthEventReason.TOKEN_DISABLED,
                                                 self.second_serial: AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED},
                                        endpoint=self.endpoint_path)

    def test_reason_explains_the_event_the_row_carries(self):
        # An unrelated token past its failcounter must not become the reason of a request that failed on a wrong PIN:
        # the row is classified PIN_FAIL, which the token that produced it recorded no reason for (the event already
        # names the credential), so the row carries none rather than borrowing the exhausted token's finding. That
        # finding is still in the per-serial map, where it belongs.
        self._add_second_token(pin=self.pin)
        second = get_one_token(serial=self.second_serial)
        for _ in range(second.get_max_failcount() + 1):
            second.inc_failcount()

        self._assert_failed(self._authenticate("wrongpin755224"))

        entries = assert_authentication_log([AuthEventType.PIN_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.PIN_FAIL], user=self.user, reason=[],
                                        reasons={self.second_serial: AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED},
                                        endpoint=self.endpoint_path)

    def test_a_successful_login_carries_no_reason(self):
        # A second, unusable token must not put a reason on the row of a login that succeeded: the reason explains a
        # failure, and the finding of a token that lost to a succeeding one would only be noise there.
        self._add_second_token(pin=self.pin)
        get_one_token(serial=self.second_serial).enable(False)

        self._assert_succeeded(self._authenticate(f"{self.pin}755224"))

        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        entry = entries[AuthEventType.LOGIN_SUCCESS]
        self.assertEqual([], list(entry.reasons), entry.reasons)
        self.assertIsNone(entry.other_info, entry.other_info)

    # --- multichallenge correlation: a challenge answer that immediately triggers a fresh challenge (a new
    #     transaction_id) still belongs to one logical attempt. All of its rows share one attempt_id (recovered
    #     across the transaction change), which is what assert_authentication_log verifies. ---

    def _assert_challenge(self, response: Response) -> dict:
        # An intermediate challenge looks the same on both endpoints: HTTP 200 with a falsy result value (a /auth
        # failure would be 401). Return its detail dict so the caller can read transaction_id / message.
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(response.json["result"]["value"], response.json)
        return response.json["detail"]

    def test_questionnaire_multichallenge_correlates_by_attempt_id(self):
        # Questionnaire with question_number=2: the PIN triggers question 1 (first_transaction_id), answering it
        # triggers question 2 (second_transaction_id), and answering that is LOGIN_SUCCESS; the three rows span two
        # transaction_ids but share one attempt_id.
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

        # The attempt spans two transaction_ids; assert_authentication_log verifies all three rows still share one
        # attempt_id (recovered across the transaction change).
        entries = assert_authentication_log([
            AuthEventType.CHALLENGE_TRIGGERED,
            AuthEventType.CHALLENGE_CONTINUED,
            AuthEventType.LOGIN_SUCCESS,
        ])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id,
                                        endpoint=self.endpoint_path)

    def test_foureyes_multichallenge_correlates_by_attempt_id(self):
        # 4-eyes with realm1 count=2: the PIN triggers the initial challenge (first_transaction_id), the first admin's
        # auth satisfies one of two tokens and creates a new challenge (second_transaction_id), and the second admin's
        # auth completes the flow (LOGIN_SUCCESS); the rows span two transaction_ids but share one attempt_id.
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
                                        serials={foureyes_serial}, transaction_id=first_transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=self.user,
                                        serials={foureyes_serial}, transaction_id=second_transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user, serials={foureyes_serial},
                                        transaction_id=second_transaction_id, endpoint=self.endpoint_path)

    def test_questionnaire_fail_on_intermediate_challenge(self):
        # Answering the first question wrong gives CHALLENGE_ANSWERED_FAIL: no new challenge was created, but the row
        # still shares the attempt's attempt_id.
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
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id,
                                        endpoint=self.endpoint_path)
        # The user's HOTP token holds no challenge in this transaction, but the questionnaire token did and its
        # answer was simply wrong - the credentials could still have been right, just for the wrong transaction, so
        # the row's main reason names only that live finding. Which token said what is still kept in the detail.
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id,
                                        endpoint=self.endpoint_path,
                                        reason=AuthEventReason.CHALLENGE_WRONG_RESPONSE,
                                        reasons={self.serial: AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION,
                                                 questionnaire_serial: AuthEventReason.CHALLENGE_WRONG_RESPONSE})

    def test_questionnaire_fail_on_last_challenge(self):
        # Answering the first question correctly triggers the second (CHALLENGE_CONTINUED). Answering the second
        # question wrong gives CHALLENGE_ANSWERED_FAIL. All rows share one attempt_id across the two transaction_ids.
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
                                        serials={questionnaire_serial}, transaction_id=first_transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_CONTINUED], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id,
                                        endpoint=self.endpoint_path)
        # Same as the intermediate-challenge case above: the HOTP token's unknown-transaction finding is dropped from
        # the row's main reason next to the questionnaire token's live wrong answer, but kept in the detail.
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=self.user,
                                        serials={questionnaire_serial}, transaction_id=second_transaction_id,
                                        endpoint=self.endpoint_path,
                                        reason=AuthEventReason.CHALLENGE_WRONG_RESPONSE,
                                        reasons={self.serial: AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION,
                                                 questionnaire_serial: AuthEventReason.CHALLENGE_WRONG_RESPONSE})


class ValidateCheckAuthLogTestCase(_AuthLogContractTests, AuthLogTestCase):
    """The shared contract plus /validate/check-only cases: transport details, divergent error paths, serial flows,
    enrollment and authorization."""

    # --- contract hooks ---

    endpoint_path = "/validate/check"

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
        # All of the user's tokens are revoked, so check_token_list raises TOKEN_LOCKED (ERR1007) before it can classify
        # the request. The API catches that, records NO_USABLE_TOKEN for the log, and re-raises so the error response is
        # unchanged.
        revoke_token(self.serial)
        res = self._post('/validate/check', {"user": self.username, "pass": f"{self.pin}755224"})
        self.assertEqual(400, res.status_code, res.json)
        self.assertEqual(1007, res.json["result"]["error"]["code"], res.json)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        # The raise happens before check_token_list can classify, so the reason is recorded where the event is.
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                        reason=AuthEventReason.TOKEN_REVOKED, endpoint=self.endpoint_path)

    def test_unknown_user_logs_user_unknown(self):
        # An unknown user is rejected by the auth_user_does_not_exist policy decorator;
        # the API catches that and still logs USER_UNKNOWN (high-signal for stuffing).
        res = self._post('/validate/check', {"user": "doesnotexist", "realm": self.realm1, "pass": "whatever"})
        self.assertFalse(res.json["result"]["status"], res.json)
        entries = assert_authentication_log([AuthEventType.USER_UNKNOWN])
        assert_authentication_log_entry(entries[AuthEventType.USER_UNKNOWN], user=User("doesnotexist", self.realm1),
                                        endpoint=self.endpoint_path)

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
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=User("doesnotexist", self.realm1),
                                        endpoint=self.endpoint_path)

    # --- Enroll via multi challenge ---

    def test_enroll_via_multichallenge_trigger_and_completion(self):
        # Authenticating with the existing token triggers a post-policy enrollment challenge for a token type (totp) the
        # user doesn't have yet -> ENROLLMENT_TRIGGERED; answering with the freshly enrolled token's OTP completes the
        # login -> LOGIN_SUCCESS, and both rows are correlated by the enrollment transaction_id.
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
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED], user=self.user,
                                        serials={enrolled_serial}, transaction_id=transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        serials={enrolled_serial}, transaction_id=transaction_id,
                                        endpoint=self.endpoint_path)
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
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED], serials={serial}, user=self.user,
                                        transaction_id=transaction_id, endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        transaction_id=transaction_id, endpoint=self.endpoint_path)

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
                                        user=self.user, transaction_id=transaction_id, endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_CANCELED_FAIL], user=self.user,
                                        transaction_id=transaction_id, endpoint=self.endpoint_path)
        remove_token(enrolled_serial)  # still exists because the enrollment was not cancelled

    def test_enroll_triggered_via_challenge_response(self):
        # Answering the HOTP challenge correctly triggers a TOTP enrollment via post-policy, which reclassifies that row
        # from LOGIN_SUCCESS to ENROLLMENT_TRIGGERED (updating its event_type/serial/transaction_id); all rows share one
        # attempt_id across the two transaction_ids.
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
                                        serials={self.serial}, transaction_id=hotp_transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.ENROLLMENT_TRIGGERED], user=self.user,
                                        serials={enrolled_serial}, transaction_id=enrollment_transaction_id,
                                        endpoint=self.endpoint_path)
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user, serials={enrolled_serial},
                                        transaction_id=enrollment_transaction_id, endpoint=self.endpoint_path)

    # --- Serial auth (serial provided instead of user) ---
    # TODO: Serial should be added to logs (context) if passed as request parameter

    def test_serial_otponly_success(self):
        # serial + otponly validates only the OTP (no PIN); a correct value is LOGIN_SUCCESS.
        # This classification is set by the API handler (check_otp), not the lib layer.
        body = self._check({"serial": self.serial, "pass": "755224", "otponly": "1"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user,
                                        endpoint=self.endpoint_path)

    def test_serial_otp_only_fail(self):
        # serial + otponly verifies only the token (no PIN/password), so a wrong value is TOKEN_ONLY_FAIL.
        body = self._check({"serial": self.serial, "pass": "000000", "otponly": "1"})
        self.assertFalse(body["result"]["value"], body)

        entries = assert_authentication_log([AuthEventType.TOKEN_ONLY_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.TOKEN_ONLY_FAIL], user=self.user,
                                        endpoint=self.endpoint_path)

    def test_serial_pass_success(self):
        # serial + pin+otp (no otponly) goes through check_serial_pass -> check_token_list -> LOGIN_SUCCESS.
        body = self._check({"serial": self.serial, "pass": f"{self.pin}755224"})
        self.assertTrue(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=self.user, serials={self.serial},
                                        endpoint=self.endpoint_path)

    def test_serial_addressed_request_carries_the_reason(self):
        # The serial path classifies the event itself rather than through the shared details handling, so it has to
        # carry the reason too - it silently dropped it once.
        token = get_one_token(serial=self.serial)
        for _ in range(token.get_max_failcount() + 1):
            token.inc_failcount()

        body = self._check({"serial": self.serial, "pass": f"{self.pin}755224"})
        self.assertFalse(body["result"]["value"], body)

        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                        reason=AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED,
                                        reasons={self.serial: AuthEventReason.TOKEN_FAILCOUNT_EXCEEDED},
                                        endpoint=self.endpoint_path)

    def test_serial_pass_wrong_otp_is_mfa_fail(self):
        # serial + correct PIN, wrong OTP -> MFA_FAIL (same matrix as the standard path).
        body = self._check({"serial": self.serial, "pass": f"{self.pin}000000"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.MFA_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.MFA_FAIL], user=self.user, serials={self.serial},
                                        endpoint=self.endpoint_path, reason=AuthEventReason.WRONG_OTP,
                                        reasons={self.serial: AuthEventReason.WRONG_OTP})

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
        # authorized=deny runs in the AUTHZ scope, after authentication has already succeeded: the token genuinely
        # authenticated, so its serial is retained on the reclassified NOT_AUTHORIZED entry.
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user, serials={self.serial},
                                        reason=AuthEventReason.AUTHORIZATION_DENIED, policies=["authlog_deny"],
                                        endpoint=self.endpoint_path)

    def test_is_authorized_deny_keeps_the_token_reasons_it_overrode(self):
        # The reclassification merges its detail instead of assigning it: the policy that denied the request and the
        # per-token finding that led there both belong on the row. Assigning would silently drop the latter.
        # The row's *reason* is the policy alone - that is why this request was refused, whatever the tokens did -
        # while the wrong OTP stays in the per-serial detail, which answers the separate question "what happened to
        # each token on the way there".
        set_policy("authlog_deny", scope=SCOPE.AUTHZ,
                   action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            res = self._post('/validate/check', {"user": self.username, "pass": f"{self.pin}000000"})
            self.assertEqual(400, res.status_code, res.json)
        finally:
            delete_policy("authlog_deny")
        entries = assert_authentication_log([AuthEventType.NOT_AUTHORIZED])
        assert_authentication_log_entry(entries[AuthEventType.NOT_AUTHORIZED], user=self.user, serials={self.serial},
                                        reason=AuthEventReason.AUTHORIZATION_DENIED, policies=["authlog_deny"],
                                        reasons={self.serial: AuthEventReason.WRONG_OTP}, endpoint=self.endpoint_path)


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

    endpoint_path = "/auth"

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

    def test_auth_endpoint_logs_failed_local_admin(self):
        # A local admin with a wrong password is recorded as the internal admin failing (PASSWORD_FAIL,
        # admin-internal role, its login as username, no realm/resolver/uid)
        self._auth({"username": self.testadmin, "password": "wrong"}, status=401)
        entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
        entry = entries[AuthEventType.PASSWORD_FAIL]
        assert_authentication_log_entry(entry, user=User(self.testadmin), user_role=AuthLogUserRole.ADMIN_INTERNAL,
                                        endpoint=self.endpoint_path)
        # A local admin has no user store entry, so the reason classified for the *user* attempt this turned out not
        # to be must not survive: WRONG_USERSTORE_PASSWORD would name a credential nobody checked.
        self.assertEqual([], list(entry.reasons), entry.reasons)
        self.assertIsNone(entry.other_info, entry.other_info)

    def test_auth_endpoint_failed_login_prefers_realm_user_over_local_admin(self):
        # Edge case: a username that is BOTH a local admin and a user in the default realm. A wrong password is
        # attributed to the realm user (resolved identity, regular role), not the internal admin
        create_db_admin(self.username, "twin@test.tld", "adminpw")
        try:
            self._auth({"username": self.username, "password": "wrong"}, status=401)
            entries = assert_authentication_log([AuthEventType.PASSWORD_FAIL])
            assert_authentication_log_entry(entries[AuthEventType.PASSWORD_FAIL], user=User(self.username, self.realm1),
                                            endpoint=self.endpoint_path)
        finally:
            delete_db_admin(self.username)

    def test_logs_local_admin_username(self):
        # A successful internal-admin login records the admin's login name as the username and the admin-internal role;
        # it has no User object, so no resolver/uid/realm identity fields are recorded.
        response = self._auth({"username": self.testadmin, "password": self.testadminpw}, status=200)
        self.assertTrue(response.json["result"]["value"]["token"], response.json)
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS], user=User(self.testadmin),
                                        user_role=AuthLogUserRole.ADMIN_INTERNAL, endpoint=self.endpoint_path)

    def test_auth_endpoint_logs_external_admin_role(self):
        # A user in a superuser realm (adminrealm) is an external (admin-realm) admin, recorded as admin-external.
        set_realm("adminrealm", [{"name": self.resolvername1}])
        try:
            body = self._auth({"username": "selfservice@adminrealm", "password": "test"}, status=200)
            self.assertEqual("admin", body.json["result"]["value"]["role"], body.json)
            entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
            assert_authentication_log_entry(entries[AuthEventType.LOGIN_SUCCESS],
                                            user=User("selfservice", "adminrealm"),
                                            user_role=AuthLogUserRole.ADMIN_EXTERNAL, endpoint=self.endpoint_path)
        finally:
            delete_realm("adminrealm")

    def test_revoked_token_logs_no_usable_token(self):
        # All of the user's tokens are revoked, so check_user_pass raises TOKEN_LOCKED before it can classify the
        # request. /auth keeps its generic "Wrong credentials" (4031) response, but the log still records
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
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], user=self.user,
                                        endpoint=self.endpoint_path, reason=AuthEventReason.TOKEN_REVOKED)

    def test_unknown_user_logs_user_unknown(self):
        # An unknown user on /auth fails with the generic "Wrong credentials" (4031), but the log must record
        # USER_UNKNOWN (high-signal for credential stuffing), as /validate/check does.
        self._enable_privacyidea_login()
        try:
            self._auth({"username": "doesnotexist", "realm": self.realm1, "password": "whatever"}, status=401)
        finally:
            delete_policy("authlog_login_mode")
        entries = assert_authentication_log([AuthEventType.USER_UNKNOWN])
        assert_authentication_log_entry(entries[AuthEventType.USER_UNKNOWN], user=User("doesnotexist", self.realm1),
                                        endpoint=self.endpoint_path)


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
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=self.user,
                                        serials={self.serial}, transaction_id=transaction_id,
                                        endpoint='/validate/triggerchallenge')

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
        assert_authentication_log_entry(entries[AuthEventType.NO_TOKEN], user=self.user,
                                        endpoint='/validate/triggerchallenge')


class InitializeAuthLogTestCase(AuthLogTestCase):
    """
    Authentication-log coverage for /validate/initialize, which starts a usernameless passkey authentication.

    Every branch classifies itself and the endpoint stages the row in a finally, so an initialization that failed is
    recorded as a failed attempt instead of leaving the log silent. All rows here are userless: the passkey flow
    resolves nobody until the assertion comes back.
    """
    rp_id = "example.com"

    def setUp(self) -> None:
        super().setUp()
        self._clear_challenges()

    def tearDown(self) -> None:
        self._clear_challenges()
        super().tearDown()

    @staticmethod
    def _clear_challenges() -> None:
        # Around each test, like the base fixture's _clear_log: a usernameless FIDO2 challenge has no owner and is
        # never consumed, so it would otherwise outlive its test and reach whatever counts challenges next.
        db.session.query(Challenge).delete()
        db.session.commit()

    def _set_relying_party_id(self) -> None:
        set_policy("authlog_rp_id", scope=SCOPE.ENROLL,
                   action=f"{FIDO2PolicyAction.RELYING_PARTY_ID}={self.rp_id}")
        self.addCleanup(delete_policy, "authlog_rp_id")

    def _initialize(self, data: dict) -> Response:
        with self.app.test_request_context('/validate/initialize', method='POST', data=data):
            return self.app.full_dispatch_request()

    def test_initialize_logs_challenge_triggered(self):
        self._set_relying_party_id()
        response = self._initialize({"type": "passkey"})
        self.assertEqual(200, response.status_code, response.json)
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        transaction_id=response.json["detail"]["transaction_id"],
                                        endpoint='/validate/initialize')

    def test_initialize_missing_type_logs_invalid_token_type(self):
        # The type parameter is required, so get_required raises before any branch of ours could classify - the row is
        # owed to the upfront classification rather than to a branch of its own.
        self._set_relying_party_id()
        response = self._initialize({})
        self.assertEqual(400, response.status_code, response.json)
        entries = assert_authentication_log([AuthEventType.INVALID_TOKEN_TYPE])
        assert_authentication_log_entry(entries[AuthEventType.INVALID_TOKEN_TYPE], endpoint='/validate/initialize')

    def test_initialize_unsupported_type_logs_invalid_token_type(self):
        # A type that exists but that this endpoint cannot initialize.
        self._set_relying_party_id()
        response = self._initialize({"type": "hotp"})
        self.assertEqual(400, response.status_code, response.json)
        entries = assert_authentication_log([AuthEventType.INVALID_TOKEN_TYPE])
        assert_authentication_log_entry(entries[AuthEventType.INVALID_TOKEN_TYPE], endpoint='/validate/initialize')

    def test_initialize_disabled_token_type_logs_no_usable_token(self):
        # An admin disabling passkey leaves nothing to authenticate with, which is how a disabled token type is
        # classified on the serial path too.
        self._set_relying_party_id()
        set_policy("authlog_disabled", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.DISABLED_TOKEN_TYPES}=passkey")
        self.addCleanup(delete_policy, "authlog_disabled")
        response = self._initialize({"type": "passkey"})
        self.assertEqual(403, response.status_code, response.json)
        entries = assert_authentication_log([AuthEventType.NO_USABLE_TOKEN])
        assert_authentication_log_entry(entries[AuthEventType.NO_USABLE_TOKEN], endpoint='/validate/initialize')

    def test_initialize_without_relying_party_id_logs_challenge_trigger_fail(self):
        # With no relying-party-id policy the server can't build the challenge at all; the fault is the server's, not a
        # client credential failure, so this is CHALLENGE_TRIGGER_FAIL, not MFA_FAIL, and it's deliberately absent from
        # the shipped rate-limit templates so a server config gap can't get clients blocked.
        response = self._initialize({"type": "passkey"})
        self.assertEqual(403, response.status_code, response.json)
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGER_FAIL])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGER_FAIL], endpoint='/validate/initialize')
        self.assertEqual(0, db.session.query(Challenge).count())
