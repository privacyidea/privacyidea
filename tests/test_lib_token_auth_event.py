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

from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType, AUTH_EVENT_TYPE_KEY
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import (set_policy, SCOPE, delete_policy)
from privacyidea.lib.token import (get_tokens, init_token,
                                   check_token_list, check_user_pass,
                                   remove_token)
from privacyidea.lib.user import (User)
from .base import MyTestCase, FakeFlaskG, FakeAudit


class AuthEventClassificationTestCase(MyTestCase):
    """
    check_user_pass / check_token_list classify the request outcome and stash it
    in reply_dict[AUTH_EVENT_TYPE_KEY]. This covers that classification matrix with
    a single user owning a single token, so the per-request precedence reduction is
    unambiguous.
    """
    serial = "AUTHEVT_HOTP"
    pin = "pin"

    def setUp(self):
        super().setUp()
        self.setUp_user_realms()
        self.user = User("cornelius", self.realm1)
        # Ensure the user owns exactly one token, regardless of earlier test state.
        for token in get_tokens(user=self.user):
            remove_token(token.token.serial)
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": self.pin}, user=self.user)

    def tearDown(self):
        if get_tokens(serial=self.serial):
            remove_token(self.serial)
        super().tearDown()

    def _event(self, passw, user=None, options=None):
        _res, reply = check_user_pass(self.user if user is None else user, passw, options=options or {})
        return reply.get(AUTH_EVENT_TYPE_KEY)

    def test_01_login_success(self):
        # OTP for counter 0 of the standard test key
        self.assertEqual(AuthEventType.LOGIN_SUCCESS, self._event(self.pin + "755224"))

    def test_02_pin_fail(self):
        self.assertEqual(AuthEventType.PIN_FAIL, self._event("wrongpin755224"))

    def test_03_mfa_fail(self):
        # PIN correct, OTP wrong
        self.assertEqual(AuthEventType.MFA_FAIL, self._event(self.pin + "000000"))

    def test_04_password_fail_userstore(self):
        from privacyidea.lib.policy import PolicyClass
        set_policy("authevt_otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        fake_g = FakeFlaskG()
        fake_g.policy_object = PolicyClass()
        fake_g.audit_object = FakeAudit()
        fake_g.client_ip = "10.0.0.1"
        # OTPPIN=userstore: the PIN part is the userstore password; a wrong one is PASSWORD_FAIL.
        # auth_otppin needs g in the options to evaluate the OTPPIN policy.
        tokens = get_tokens(user=self.user)
        _res, reply = check_token_list(tokens, "wrongpassword000000", user=self.user, options={"g": fake_g})
        self.assertEqual(AuthEventType.PASSWORD_FAIL, reply.get(AUTH_EVENT_TYPE_KEY))
        delete_policy("authevt_otppin")

    def test_05_no_token(self):
        remove_token(self.serial)
        self.assertEqual(AuthEventType.NO_TOKEN, self._event("whatever"))

    def test_06_user_unknown(self):
        # No matching token for an empty/unresolvable user -> USER_UNKNOWN
        for token in get_tokens():
            remove_token(token.token.serial)
        self.assertEqual(AuthEventType.USER_UNKNOWN, self._event("whatever", user=User()))

    def test_07_challenge_triggered_then_answered(self):
        set_policy("authevt_cr", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        try:
            # PIN only -> a challenge is triggered
            _res, reply = check_user_pass(self.user, self.pin, options={})
            self.assertEqual(AuthEventType.CHALLENGE_TRIGGERED, reply.get(AUTH_EVENT_TYPE_KEY))
            transaction_id = reply.get("transaction_id")

            # Wrong response -> challenge answered fail
            _res, reply = check_user_pass(self.user, "000000", options={"transaction_id": transaction_id})
            self.assertEqual(AuthEventType.CHALLENGE_ANSWERED_FAIL, reply.get(AUTH_EVENT_TYPE_KEY))

            # Correct response (counter 0) -> challenge answered ok
            _res, reply = check_user_pass(self.user, "755224", options={"transaction_id": transaction_id})
            self.assertEqual(AuthEventType.CHALLENGE_ANSWERED_OK, reply.get(AUTH_EVENT_TYPE_KEY))
        finally:
            delete_policy("authevt_cr")
