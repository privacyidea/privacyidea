# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Decisions of the authentication in ``lib/token/auth.py`` that are not about the authentication log: which tokens take
part in an authentication and what it does to them.
"""
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.token import enable_token, init_token, remove_token
from privacyidea.lib.token.auth import check_otp, check_realm_pass, check_user_pass, create_challenges_from_tokens
from privacyidea.lib.user import User
from .base import MyTestCase

# RFC 4226, appendix D: the OTP values of this key for the counters 0, 1, 2
OTPKEY = "3132333435363738393031323334353637383930"
OTP_VALUES = ["755224", "287082", "359152"]


class TokenAuthDecisionTestCase(MyTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.user = User("cornelius", self.realm1)

    def test_01_the_token_type_option_restricts_the_tokens(self):
        init_token({"type": "spass", "pin": "spasspin", "serial": "AUTHSPASS"}, user=self.user)
        init_token({"type": "hotp", "otpkey": OTPKEY, "pin": "hotppin", "serial": "AUTHHOTP"}, user=self.user)
        try:
            self.assertTrue(check_user_pass(self.user, "spasspin")[0])
            self.assertTrue(check_user_pass(self.user, "spasspin", options={"token_type": "spass"})[0])
            result, reply = check_user_pass(self.user, "spasspin", options={"token_type": "hotp"})
            self.assertFalse(result, reply)
        finally:
            remove_token("AUTHSPASS")
            remove_token("AUTHHOTP")

    def test_02_no_challenge_for_a_token_that_can_not_authenticate(self):
        token = init_token({"type": "hotp", "otpkey": OTPKEY, "pin": "hotppin", "serial": "AUTHCHAL"}, user=self.user)
        try:
            # Past its failcounter, as /validate/triggerchallenge would find it: it only leaves out disabled, revoked
            # and locked tokens
            token.token.failcount = token.token.maxfail
            token.token.save()
            reply = {}
            create_challenges_from_tokens([token], reply, {})
            self.assertListEqual([], reply["multi_challenge"], reply)
            self.assertListEqual([], get_challenges(serial="AUTHCHAL"))

            token.token.failcount = 0
            token.token.save()
            reply = {}
            create_challenges_from_tokens([token], reply, {})
            self.assertEqual(1, len(reply["multi_challenge"]), reply)
        finally:
            remove_token("AUTHCHAL")

    def test_03_the_check_of_a_realm_uses_active_tokens_only(self):
        init_token({"type": "spass", "pin": "realmpin", "serial": "AUTHREALM"}, user=self.user)
        try:
            enable_token("AUTHREALM", enable=False)
            result, reply = check_realm_pass(self.realm1, "realmpin")
            self.assertFalse(result, reply)
            enable_token("AUTHREALM")
            self.assertTrue(check_realm_pass(self.realm1, "realmpin")[0])
        finally:
            remove_token("AUTHREALM")

    def test_04_a_correct_otp_value_resets_the_failcounter(self):
        token = init_token({"type": "hotp", "otpkey": OTPKEY, "serial": "AUTHOTPONLY"}, user=self.user)
        try:
            token.token.failcount = 3
            token.token.save()
            result, reply = check_otp("AUTHOTPONLY", OTP_VALUES[0])
            self.assertTrue(result, reply)
            self.assertEqual(0, token.token.failcount)
        finally:
            remove_token("AUTHOTPONLY")
