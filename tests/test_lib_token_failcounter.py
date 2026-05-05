# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the token fail-counter: increment, reset, and max-fail policy."""
import datetime

from dateutil.tz import tzlocal

from privacyidea.lib.config import (set_privacyidea_config, delete_privacyidea_config)
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import (set_policy, SCOPE, PolicyClass)
from privacyidea.lib.token import (init_token,
                                   unassign_token, check_token_list, check_user_pass,
                                   remove_token)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.tokenclass import (FAILCOUNTER_EXCEEDED,
                                        FAILCOUNTER_CLEAR_TIMEOUT)
from privacyidea.lib.user import (User)
from privacyidea.models import (db)
from .base import MyTestCase, FakeAudit, FakeFlaskG

PWFILE = "tests/testdata/passwords"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKE2 = "31323334353637383930313233343536373839AA"
CHANGED_KEY = '31323334353637383930313233343536373839AA'


class TokenFailCounterTestCase(MyTestCase):
    """
    Test the lib.token on an interface level
    """

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_failcounter_max_hotp(self):
        # Check if we can not authenticate with a token that has the maximum
        # failcounter
        user = User(login="cornelius", realm=self.realm1)
        token = init_token({"serial": "test47", "pin": "test47",
                            "type": "hotp", "otpkey": OTPKEY},
                           user=user)

        """                        Truncated
           Count    Hexadecimal    Decimal        HOTP
           0        4c93cf18       1284755224     755224
           1        41397eea       1094287082     287082
           2         82fef30        137359152     359152
           3        66ef7655       1726969429     969429
           4        61c5938a       1640338314     338314
           5        33c083d4        868254676     254676
           6        7256c032       1918287922     287922
           7         4e5b397         82162583     162583
           8        2823443f        673399871     399871
           9        2679dc69        645520489     520489
           10                                     403154
           11                                     481090
           12                                     868912
           13                                     736127
        """
        res, reply = check_user_pass(user, "test47287082")
        self.assertTrue(res)
        # Set the failcounter to maximum failcount
        token.set_failcount(10)
        db.session.commit()
        # Authentication must fail, since the failcounter is reached
        res, reply = check_user_pass(user, "test47359152")
        self.assertFalse(res)
        self.assertEqual("Failcounter exceeded", reply.get("message"))

        remove_token("test47")

    def test_02_failcounter_max_totp(self):
        # Check if we can not authenticate with a token that has the maximum
        # failcounter
        user = User(login="cornelius", realm=self.realm1)
        pin = "testTOTP"
        token = init_token({"serial": pin, "pin": pin,
                            "type": "totp", "otpkey": OTPKEY},
                           user=user)
        """
        47251644    942826
        47251645    063321
        47251646    306773
        47251647    722053
        47251648    032819
        47251649    705493
        47251650    589836
        """
        res, reply = check_user_pass(user, pin + "942826",
                                     options={"initTime": 47251644 * 30})
        self.assertTrue(res)
        # Set the failcounter to maximum failcount
        token.set_failcount(10)
        db.session.commit()
        # Authentication must fail, since the failcounter is reached
        res, reply = check_user_pass(user, pin + "032819",
                                     options={"initTime": 47251648 * 30})
        self.assertFalse(res)
        self.assertEqual("Failcounter exceeded", reply.get("message"))

        remove_token(pin)

    def test_03_inc_failcounter_of_all_tokens(self):
        # If a user has more than one token and authenticates with wrong OTP
        # PIN, the failcounter on all tokens should be increased
        user = User(login="cornelius", realm=self.realm1)
        pin1 = "pin1"
        pin2 = "pin2"
        token1 = init_token({"serial": pin1, "pin": pin1,
                             "type": "hotp", "genkey": 1}, user=user)
        token2 = init_token({"serial": pin2, "pin": pin2,
                             "type": "hotp", "genkey": 1}, user=user)

        # Authenticate with pin1 will increase first failcounter
        res, reply = check_user_pass(user, pin1 + "000000")
        self.assertEqual(res, False)
        self.assertEqual(reply.get("message"), "wrong otp value")

        self.assertEqual(token1.token.failcount, 1)
        self.assertEqual(token2.token.failcount, 0)

        # Authenticate with a wrong PIN will increase all failcounters
        res, reply = check_user_pass(user, "XXX" + "000000")
        self.assertEqual(res, False)
        self.assertEqual(reply.get("message"), "wrong otp pin")

        self.assertEqual(token1.token.failcount, 2)
        self.assertEqual(token2.token.failcount, 1)
        remove_token(pin1)
        remove_token(pin2)

    def test_04_reset_all_failcounters(self):
        set_policy("reset_all", scope=SCOPE.AUTH,
                   action=PolicyAction.RESETALLTOKENS)

        user = User(login="cornelius", realm=self.realm1)
        pin1 = "pin1"
        pin2 = "pin2"
        token1 = init_token({"serial": pin1, "pin": pin1,
                             "type": "spass"}, user=user)
        token2 = init_token({"serial": pin2, "pin": pin2,
                             "type": "spass"}, user=user)

        token1.inc_failcount()
        token2.inc_failcount()
        token2.inc_failcount()
        self.assertEqual(token1.token.failcount, 1)
        self.assertEqual(token2.token.failcount, 2)

        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        g.client_ip = None
        g.serial = None
        options = {"g": g}

        check_token_list([token1, token2], pin1, user=user,
                         options=options, allow_reset_all_tokens=True)

        self.assertEqual(token1.token.failcount, 0)
        self.assertEqual(token2.token.failcount, 0)

        # check with tokens without users
        unassign_token(pin1)
        unassign_token(pin1)
        # After unassigning we need to set the PIN again
        token1.set_pin(pin1)
        token2.set_pin(pin2)
        token1.inc_failcount()
        token2.inc_failcount()
        token2.inc_failcount()
        self.assertEqual(token1.token.failcount, 1)
        self.assertEqual(token2.token.failcount, 2)

        check_token_list([token1, token2], pin1, options=options,
                         allow_reset_all_tokens=True)

        self.assertEqual(token1.token.failcount, 0)
        self.assertEqual(token2.token.failcount, 0)

        # Clean up
        remove_token(pin1)
        remove_token(pin2)

    def test_05_reset_failcounter(self):
        tok = init_token({"type": "hotp",
                          "serial": "test05",
                          "otpkey": self.otpkey})
        # Set failcounter clear timeout to 1 minute
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 1)
        tok.token.count = 10
        tok.set_pin("hotppin")
        tok.set_failcount(10)
        exceeded_timestamp = datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=1)
        tok.add_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_timestamp.strftime(DATE_FORMAT))

        # OTP value #11
        res, reply = check_token_list([tok], "hotppin481090")
        self.assertTrue(res)
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 0)
        remove_token("test05")

    def test_06_reset_failcounter_out_of_sync(self):
        # Reset fail counter of a token that is out of sync
        # The fail counter will reset, even if the token is out of sync, since the
        # autoresync is handled in the tokenclass.authenticate.
        tok = init_token({"type": "hotp",
                          "serial": "test06",
                          "otpkey": self.otpkey})

        set_privacyidea_config("AutoResyncTimeout", "300")
        set_privacyidea_config("AutoResync", 1)

        tok.set_pin("hotppin")
        tok.set_count_window(2)

        res, reply = check_token_list([tok], "hotppin{0!s}".format(self.valid_otp_values[0]))
        self.assertTrue(res)

        # Now we set the failoucnter and the exceeded time.
        tok.set_failcount(10)
        exceeded_timestamp = datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=1)
        tok.add_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_timestamp.strftime(DATE_FORMAT))
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 1)

        # authentication with otp value #3 will fail
        res, reply = check_token_list([tok], "hotppin{0!s}".format(self.valid_otp_values[3]))
        self.assertFalse(res)

        # authentication with otp value #4 will resync and succeed
        res, reply = check_token_list([tok], "hotppin{0!s}".format(self.valid_otp_values[4]))
        self.assertTrue(res)
        self.assertEqual(tok.get_failcount(), 0)

        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 0)
        delete_privacyidea_config("AutoResyncTimeout")
        delete_privacyidea_config("AutoResync")
        remove_token("test06")

    def test_07_reset_failcounter_failed_auth(self):
        tok = init_token({"type": "hotp",
                          "serial": "test07",
                          "otpkey": self.otpkey})
        # Set failcounter clear timeout to 1 minute
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 1)
        tok.token.count = 10
        tok.set_pin("hotppin")
        tok.set_failcount(10)
        exceeded_timestamp = datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=1)
        tok.add_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_timestamp.strftime(DATE_FORMAT))

        # correct PIN + wrong OTP value resets the failcounter
        res, _ = check_token_list([tok], "hotppin123456")
        self.assertFalse(res)
        self.assertEqual(1, tok.get_failcount())
        self.assertIsNone(tok.get_tokeninfo(FAILCOUNTER_EXCEEDED))

        # also completely invalid auth resets the failcounter
        tok.set_failcount(10)
        tok.add_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_timestamp.strftime(DATE_FORMAT))
        res, _ = check_token_list([tok], "hotppin123456")
        self.assertFalse(res)
        self.assertEqual(1, tok.get_failcount())
        self.assertIsNone(tok.get_tokeninfo(FAILCOUNTER_EXCEEDED))

        # after nine more invalid auth requests, the token is locked again
        for i in range(2, 11):
            res, reply = check_token_list([tok], "pin123456")
            self.assertFalse(res)
            self.assertEqual(i, tok.get_failcount())
            self.assertEqual("wrong otp pin", reply.get("message"))
        otp = tok.get_otp()[2]
        res, reply = check_token_list([tok], "hotppin" + otp)
        self.assertFalse(res)
        self.assertEqual(10, tok.get_failcount())
        self.assertEqual("Failcounter exceeded", reply.get("message"))

        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 0)

        res, reply = check_token_list([tok], "hotppin" + otp)
        self.assertFalse(res)

        remove_token("test07")
