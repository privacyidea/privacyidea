"""
This test file tests the lib.tokenclass

The lib.tokenclass depends on the DB model and lib.user
"""
import binascii
import datetime
import logging
import time
from unittest import mock

from testfixtures import LogCapture

from privacyidea.lib.config import (set_privacyidea_config, set_prepend_pin, delete_privacyidea_config)
from privacyidea.lib.policy import (PolicyClass, set_policy, delete_policy, SCOPE)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.token import init_token, remove_token, import_tokens, get_tokens
from privacyidea.lib.autoresync import AUTORESYNC_KEY, AutoResyncResult
from privacyidea.lib.tokens.HMAC import HmacOtp
from privacyidea.lib.tokens.totptoken import TotpTokenClass
from privacyidea.lib.user import (User)
from privacyidea.models import Token, Config, Challenge
from .base import MyTestCase, FakeAudit, FakeFlaskG

PWFILE = "tests/testdata/passwords"


class TOTPTokenTestCase(MyTestCase):
    """
    Test the token on the database level
    """
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    serial1 = "SE123456"
    otpkey = "3132333435363738393031323334353637383930"

    """
    47251644    942826
    47251645    063321
    47251646    306773
    47251647    722053
    47251648    032819
    47251649    705493
    47251650    589836
    """

    # add_user, get_user, reset, set_user_identifiers

    def test_00_create_user_realm(self):
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1, [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)

        user_str = f"{user!s}"
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = f"{user!r}"
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="totp")
        db_token.save()
        token = TotpTokenClass(db_token)
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "totp", token.token.tokentype)
        self.assertTrue(token.type == "totp", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "TOTP", class_prefix)
        self.assertTrue(token.get_class_type() == "totp", token)

    def test_02_set_user(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        self.assertTrue(token.token.tokentype == "totp",
                        token.token.tokentype)
        self.assertTrue(token.type == "totp", token.type)

        token.add_user(User(login="cornelius",
                            realm=self.realm1))
        self.assertEqual(token.token.first_owner.resolver, self.resolvername1)
        self.assertEqual(token.token.first_owner.user_id, "1000")

        user_object = token.user
        self.assertTrue(user_object.login == "cornelius",
                        user_object)
        self.assertTrue(user_object.resolver == self.resolvername1,
                        user_object)

    def test_03_reset_failcounter(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.token.failcount = 10
        token.reset()
        self.assertTrue(token.token.failcount == 0,
                        token.token.failcount)

    def test_04_base_methods(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)

        c = token.create_challenge("transactionid")
        self.assertTrue(c[0], c)
        self.assertTrue("transactionid" in c[2], c)

        # set the description
        token.set_description("something new")
        self.assertTrue(token.token.description == "something new",
                        token.token)

        # set defaults
        token.set_defaults()
        self.assertTrue(token.token.otplen == 6)
        self.assertTrue(token.token.sync_window == 1000)

        token.resync("1234", "3456")

        token.token.count_window = 17
        self.assertTrue(token.get_otp_count_window() == 17)

        token.token.count = 18
        self.assertTrue(token.get_otp_count() == 18)

        token.token.active = False
        self.assertTrue(token.is_active() is False)

        token.token.failcount = 7
        self.assertTrue(token.get_failcount() == 7)
        token.set_failcount(8)
        self.assertTrue(token.token.failcount == 8)

        token.token.maxfail = 12
        self.assertTrue(token.get_max_failcount() == 12)

        self.assertEqual(token.get_user_id(), token.token.first_owner.user_id)

        self.assertTrue(token.get_serial() == "SE123456", token.token.serial)
        self.assertTrue(token.get_tokentype() == "totp",
                        token.token.tokentype)

        token.set_so_pin("sopin")
        token.set_user_pin("userpin")
        token.set_otpkey(self.otpkey)
        token.set_otplen(8)
        token.set_otp_count(1000)
        self.assertTrue(len(token.token.so_pin) == 32,
                        token.token.so_pin)
        self.assertTrue(len(token.token.user_pin) == 32,
                        token.token.user_pin)
        self.assertEqual(len(token.token.key_enc), 96, token.token.key_enc)
        self.assertTrue(token.get_otplen() == 8)
        self.assertTrue(token.token.count == 1000,
                        token.token.count)

        token.set_maxfail(1000)
        self.assertTrue(token.token.maxfail == 1000)

        token.set_count_window(52)
        self.assertTrue(token.get_count_window() == 52)

        token.set_sync_window(53)
        self.assertTrue(token.get_sync_window() == 53)

    def test_06_set_pin(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.set_pin("hallo")
        (ph1, pseed) = token.get_pin_hash_seed()
        # check the database
        token.set_pin("blubber")
        ph2 = token.token.pin_hash
        self.assertTrue(ph1 != ph2)
        token.set_pin_hash_seed(ph1, pseed)

    def test_07_enable(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.enable(False)
        self.assertTrue(token.token.active is False)
        token.enable()
        self.assertTrue(token.token.active)

    def test_05_get_set_realms(self):
        set_realm(self.realm2)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        realms = token.get_realms()
        self.assertTrue(len(realms) == 1, realms)
        token.set_realms([self.realm1, self.realm2])
        realms = token.get_realms()
        self.assertTrue(len(realms) == 2, realms)

    def test_99_delete_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.delete_token()

        db_token = Token.query.filter_by(serial=self.serial1).first()
        self.assertTrue(db_token is None, db_token)

    def test_08_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.set_hashlib("sha1")
        ti = token.get_tokeninfo()
        self.assertTrue("hashlib" in ti, ti)

    def test_09_failcount(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        start = token.token.failcount
        end = token.inc_failcount()
        self.assertTrue(end == start + 1, (end, start))

    def test_10_get_hashlib(self):
        # check if functions are returned
        for hl in ["sha1", "md5", "sha256", "sha512",
                   "sha224", "sha384", "", None]:
            self.assertTrue(hasattr(TotpTokenClass.get_hashlib(hl),
                                    '__call__'),
                            TotpTokenClass.get_hashlib(hl))

    def test_11_tokeninfo(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.add_tokeninfo("key1", "value2")
        info1 = token.get_tokeninfo()
        self.assertTrue("key1" in info1, info1)
        token.add_tokeninfo("key2", "value3")
        info2 = token.get_tokeninfo()
        self.assertTrue("key2" in info2, info2)
        token.set_tokeninfo(info1)
        info2 = token.get_tokeninfo()
        self.assertTrue("key2" not in info2, info2)
        self.assertTrue(token.get_tokeninfo("key1") == "value2",
                        info2)

        # auth counter
        token.set_count_auth_success_max(200)
        token.set_count_auth_max(1000)
        token.set_count_auth_success(100)
        token.inc_count_auth_success()
        token.set_count_auth(200)
        token.inc_count_auth()
        self.assertTrue(token.get_count_auth_success_max() == 200)
        self.assertTrue(token.get_count_auth_success() == 101)
        self.assertTrue(token.get_count_auth_max() == 1000)
        self.assertTrue(token.get_count_auth() == 201)

        self.assertTrue(token.check_auth_counter())
        token.set_count_auth_max(10)
        self.assertFalse(token.check_auth_counter())
        token.set_count_auth_max(1000)
        token.set_count_auth_success_max(10)
        self.assertFalse(token.check_auth_counter())

    def test_12_inc_otp_counter(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)

        token.set_otp_count(10)
        self.assertTrue(token.token.count == 10, token.token.count)
        # increase counter by 1
        token.inc_otp_counter()
        self.assertTrue(token.token.count == 11, token.token.count)
        # increase counter to 21
        Config(Key="DefaultResetFailCount", Value=True).save()
        token.inc_otp_counter(counter=20)
        self.assertTrue(token.token.count == 21, token.token.count)

    @mock.patch('time.time', mock.MagicMock(return_value=1686902767))
    def test_98_get_otp(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "pin": "test",
                      "otplen": 6,
                      "timeShift": 0})
        counter = token._time2counter(time.time(), timeStepping=30)
        otp_now = token._calc_otp(counter)
        otp = token.get_otp()
        res = token.check_otp_exist(otp[2])
        self.assertEqual(res, counter)
        self.assertEqual(otp[2], otp_now)

    def test_13_check_otp(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "pin": "test",
                      "otplen": 6})
        token.set_otp_count(47251644)
        # OTP does not exist
        self.assertTrue(token.check_otp("222333") == -1)
        # OTP does exist
        res = token.check_otp("722053", options={"initTime": 47251645 * 30})
        # Found the counter 47251647
        self.assertEqual(47251647, res)
        with LogCapture(level=logging.INFO) as lc:
            self.assertEqual(-1, token.check_otp("1234567"))
            lc.check_present(
                ('privacyidea.lib.decorators', 'INFO',
                 f'OTP value for token {token.token.serial} (type: {token.type}) '
                 f'has wrong length (7 != 6)'))
            self.assertEqual(-1, token.check_otp("12345"))
            lc.check_present(
                ('privacyidea.lib.decorators', 'INFO',
                 f'OTP value for token {token.token.serial} (type: {token.type}) '
                 f'has wrong length (5 != 6)'))

    def test_14_split_pin_pass(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)

        token.token.otplen = 6
        # postpend pin
        set_prepend_pin(False)
        _res, pin, value = token.split_pin_pass("222333test")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(value == "222333", value)
        # prepend pin
        set_prepend_pin()
        _res, pin, value = token.split_pin_pass("test222333")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(value == "222333", value)

    def test_15_check_pin(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.set_pin("test")
        self.assertTrue(token.check_pin("test"))
        self.assertFalse(token.check_pin("wrong pin"))

    def test_16_init_detail(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.add_init_details("otpkey", "11223344556677889900")
        detail = token.get_init_detail()
        self.assertTrue("otpkey" in detail, detail)
        # but the otpkey must not be written to token.token.info (DB)
        # As this only writes the OTPkey to the internal init_details dict
        self.assertTrue("otpkey" not in token.token.get_info(),
                        token.token.get_info())

        # Now get the Google Authenticator URL, which we only
        # get, if a user is specified.
        detail = token.get_init_detail(user=User("cornelius",
                                                 self.realm1))
        self.assertTrue("otpkey" in detail, detail)
        otpkey = detail.get("otpkey")
        self.assertTrue("img" in otpkey, otpkey)
        self.assertTrue("googleurl" in detail, detail)
        # some other stuff.
        self.assertRaises(Exception, token.set_init_details, "invalid value")
        token.set_init_details({"detail1": "value1"})
        self.assertTrue("detail1" in token.get_init_details(),
                        token.get_init_details())

    def test_17_update_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        # Wrong genkey is replaced with genkey=True
        token.update({"description": "new desc",
                      "genkey": "17"})
        self.assertEqual("new desc", token.token.description)
        # genkey and otpkey used at the same time
        token.update({"otpkey": self.otpkey,
                      "genkey": "1"})

        token.update({"otpkey": self.otpkey,
                      "pin": "654321",
                      "otplen": 6})
        self.assertTrue(token.check_pin("654321"))
        self.assertTrue(token.token.otplen == 6)
        # update hashlib
        token.update({"otpkey": self.otpkey,
                      "hashlib": "sha1"})
        self.assertTrue(token.get_tokeninfo("hashlib") == "sha1",
                        token.get_tokeninfo())

        # save pin encrypted
        token.update({"genkey": 1,
                      "pin": "secret",
                      "encryptpin": "true"})
        # check if the PIN is encrypted
        self.assertTrue(token.token.pin_hash.startswith("@@"),
                        token.token.pin_hash)

        # update token without otpkey generates one
        token.update({"description": "test"})
        self.assertEqual("test", token.token.description)

        # update time settings
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6,
                      "timeShift": 10,
                      "timeWindow": 180,
                      "timeStep": 30
                      })

    def test_18_challenges(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        resp = token.is_challenge_response(user=User(login="cornelius",
                                                     realm=self.realm1),
                                           passw="test123456")
        self.assertFalse(resp, resp)

        transaction_id = "123456789"
        chall = Challenge(self.serial1, transaction_id=transaction_id, challenge="Who are you?")
        chall.save()
        resp = token.is_challenge_response(user=User(login="cornelius",
                                                     realm=self.realm1),
                                           passw="test123456",
                                           options={"transaction_id": transaction_id})
        self.assertTrue(resp, resp)

        # test if challenge is valid
        chall.is_valid()

    def test_19_pin_otp_functions(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        db_token.set_pin("test")
        token = TotpTokenClass(db_token)
        # check OTP according to RFC 4226
        token.update({"otpkey": self.otpkey})
        self.assertTrue(db_token.otplen == 6, 6)
        set_prepend_pin()
        res, pin, otp = token.split_pin_pass("test123456")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(otp == "123456", otp)
        self.assertTrue(token.check_pin(pin), pin)
        # get the OTP value for counter 1417549521
        res = token.get_otp(time_seconds=1417549521)
        self.assertTrue(res[0] == 1, res)
        self.assertTrue(res[2] == "227747", res)

        check = token.check_otp("722053", counter=47251647)
        # The OTP 722053 is of counter 47251647
        self.assertTrue(check == 47251647, check)
        # The tokenclass saves the counter to the database
        self.assertTrue(token.token.count == 47251647, token.token.count)

        check = token.check_otp("705493", counter=47251648)
        # The OTP 705493 is of counter 47251649, but it matches also.
        self.assertTrue(check == 47251649, check)

        # successful authentication
        res = token.authenticate("test589836")
        # This is the OTP value of the counter=47251650
        self.assertTrue(res == (True, 47251650, None), res)

        # try the same OTP value again will fail!
        res = token.authenticate("test589836")
        # This is the OTP value of the counter=47251650
        self.assertTrue(res == (True, -1, None), res)

        res = token.get_multi_otp()
        self.assertTrue(res[0] is False, res)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6,
                      "timeShift": 0})
        token.token.count = 0
        res = token.get_multi_otp(count=5)
        self.assertTrue(res[0], res)
        self.assertTrue(res[1] == "OK", res)
        self.assertTrue(len(res[2].get("otp")) == 5, res[2].get("otp"))

        # Simulate the server time
        res = token.get_multi_otp(count=5, timestamp=47251644 * 30)
        self.assertTrue(res[0], res)
        self.assertTrue(res[1] == "OK", res)
        self.assertTrue(len(res[2].get("otp")) == 5, res[2].get("otp"))
        self.assertTrue(47251648 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47251647 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47251646 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47251645 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47251644 in res[2].get("otp"), res[2].get("otp"))

        # Simulate the server time
        res = token.get_multi_otp(count=5, curTime=datetime.datetime(2014, 12, 12))
        self.assertTrue(res[0], res)
        self.assertTrue(res[1] == "OK", res)
        self.assertTrue(len(res[2].get("otp")) == 5, res[2].get("otp"))
        self.assertTrue(47278080 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47278081 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47278082 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47278083 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47278084 in res[2].get("otp"), res[2].get("otp"))

        # do some failing otp checks
        token.token.otplen = 5
        self.assertTrue(token.check_otp("705493", counter=47251648) == -1, res)
        token.token.otplen = 6

        # Previous OTP value used again
        token.token.otplen = 6
        # The OTP for this counter was already presented to the server
        token.token.count = 47251648
        # 47251647 -> 722053
        res = token.check_otp("722053", options={"initTime": 47251649 * 30})
        self.assertTrue(res == -1, res)

        # simple OTPs of current time
        ret, _, dct = token.get_multi_otp(1)
        self.assertTrue(ret)
        self.assertGreater(list(dct["otp"].keys())[0], 47251648)
        ret, _, dct = token.get_multi_otp(1, curTime=datetime.datetime.now())
        self.assertTrue(ret)
        self.assertGreater(list(dct["otp"].keys())[0], 47251648)

    def test_20_check_challenge_response(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        db_token.set_pin("test")
        token = TotpTokenClass(db_token)
        r = token.check_challenge_response(user=None,
                                           passw="123454")
        # check empty challenges
        self.assertTrue(r == -1, r)

        # create a challenge and match the transaction_id
        c = Challenge(self.serial1, transaction_id="mytransaction",
                      challenge="Blah, what now?")
        # save challenge to the database
        c.save()
        r = token.check_challenge_response(user=None,
                                           passw="123454",
                                           options={"state": "mytransaction"})
        # The challenge matches, but the OTP does not match!
        self.assertTrue(r == -1, r)

        # test the challenge janitor
        c1 = Challenge(self.serial1, transaction_id="t1", validitytime=0)
        c1.save()
        c2 = Challenge(self.serial1, transaction_id="t2", validitytime=0)
        c2.save()
        c3 = Challenge(self.serial1, transaction_id="t3", validitytime=100)
        c3.save()
        c4 = Challenge(self.serial1, transaction_id="t4", validitytime=100)
        c4.save()
        num = Challenge.query.filter(Challenge.serial == self.serial1).count()
        self.assertTrue(num >= 5, num)
        # We pass the third challenge as the valid challenge.
        # So 3 challenges will be deleted.
        token.challenge_janitor()
        # Now see if those challenges are deleted
        num1 = Challenge.query.filter(Challenge.transaction_id == "t1").count()
        num2 = Challenge.query.filter(Challenge.transaction_id == "t2").count()
        num3 = Challenge.query.filter(Challenge.transaction_id == "t3").count()
        num4 = Challenge.query.filter(Challenge.transaction_id == "t4").count()
        self.assertTrue(num1 == 0)
        self.assertTrue(num2 == 0)
        self.assertTrue(num3 == 1)
        self.assertTrue(num4 == 1)

    def test_21_get_class_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        ti = token.get_class_info()
        self.assertTrue(ti.get("type") == "totp", ti)
        self.assertTrue("policy" in ti, ti)
        self.assertTrue("title" in ti, ti)
        self.assertTrue("user" in ti, ti)

    def test_22_autosync(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        set_privacyidea_config("AutoResync", True)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.token.count = 47251640
        token.set_sync_window(10)
        # counter = 47251649 => otp = 705493, is out of sync
        r = token.check_otp("705493", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertTrue(r == -1, r)
        self.assertEqual(AutoResyncResult.STARTED, token.auth_details.get(AUTORESYNC_KEY))
        # counter = 47251650 => otp = 389836, will be autosynced.
        r = token.check_otp("589836", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertTrue(r == 47251650, r)
        self.assertEqual(AutoResyncResult.SUCCESSFUL, token.auth_details.get(AUTORESYNC_KEY))

        # counter = 47251640 => otp = 166325 is an old OTP value
        # counter = 47251641 => otp = 432730 is an old OTP value
        # Autoresync with two times the same old OTP value must not work out! An old value does not start one.
        token.auth_details.clear()
        r = token.check_otp("166325", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertTrue(r == -1, r)
        r = token.check_otp("166325", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertTrue(r == -1, r)
        self.assertNotIn(AUTORESYNC_KEY, token.auth_details)
        # Autoresync with two consecutive old OTP values must not work out!
        r = token.check_otp("166325", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertTrue(r == -1, r)
        r = token.check_otp("432730", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertTrue(r == -1, r)
        self.assertNotIn(AUTORESYNC_KEY, token.auth_details)

        # Autosync with a gap in the next otp value will fail, if the time window allows no gap
        token.token.count = 47251640
        token.write_tokeninfo("timeWindow", 30)
        # Just try some bullshit config value
        set_privacyidea_config("AutoResyncTimeout", "totally not a number")
        # counter = 47251648 => otp = 032819, is out of sync
        time_before = int(time.time())
        r = token.check_otp("032819", window=30,
                            options={"initTime": 47251645 * 30})
        time_after = int(time.time())
        self.assertTrue(r == -1, r)
        # The invalid AutoResyncTimeout falls back to 300 seconds
        due_date = int(token.get_tokeninfo("dueDate"))
        self.assertLessEqual(time_before + 300, due_date)
        self.assertGreaterEqual(time_after + 300, due_date)
        # counter = 47251650 => otp = 589836, will NOT _autosync
        r = token.check_otp("589836", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertTrue(r == -1, r)
        self.assertEqual(AutoResyncResult.FAILED, token.auth_details.get(AUTORESYNC_KEY))

        # Another request stores the resynced counter and its time shift first, so this one records no resync and
        # keeps that time shift
        token.token.count = 47251640
        r = token.check_otp("705493", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertEqual(-1, r)
        token.auth_details.clear()
        token.write_tokeninfo("timeShift", -150)
        with mock.patch.object(TotpTokenClass, "advance_otp_count", return_value=False):
            r = token.check_otp("589836", window=30,
                                options={"initTime": 47251645 * 30})
        self.assertEqual(-1, r)
        self.assertNotIn(AUTORESYNC_KEY, token.auth_details)
        self.assertEqual(-150, token.timeshift)

        # A value after the dueDate starts a new autoresync, which the next value completes
        token.token.count = 47251640
        set_privacyidea_config("AutoResyncTimeout", 300)
        # counter = 47251649 => otp = 705493, is out of sync
        r = token.check_otp("705493", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertEqual(-1, r)
        self.assertTrue(token.has_pending_autoresync())
        token.write_tokeninfo("dueDate", int(time.time()) - 1)
        self.assertFalse(token.has_pending_autoresync())
        token.auth_details.clear()
        # counter = 47251650 => otp = 589836, is the next value, but the dueDate is over
        r = token.check_otp("589836", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertEqual(-1, r)
        self.assertEqual(AutoResyncResult.STARTED, token.auth_details.get(AUTORESYNC_KEY))
        self.assertEqual("47251650", token.get_tokeninfo("otp1c"))
        # counter = 47251651 => otp = 227747, will be autosynced
        r = token.check_otp("227747", window=30,
                            options={"initTime": 47251646 * 30})
        self.assertEqual(47251651, r)
        self.assertEqual(AutoResyncResult.SUCCESSFUL, token.auth_details.get(AUTORESYNC_KEY))
        self.assertNotIn("otp1c", token.get_tokeninfo())
        self.assertNotIn("dueDate", token.get_tokeninfo())

        # A stored counter without a dueDate is expired, so the next value starts a new autoresync
        token.token.count = 47251640
        token.write_tokeninfo("otp1c", 47251648)
        token.auth_details.clear()
        # counter = 47251649 => otp = 705493, is the next value, but no dueDate is stored
        r = token.check_otp("705493", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertEqual(-1, r)
        self.assertEqual(AutoResyncResult.STARTED, token.auth_details.get(AUTORESYNC_KEY))
        self.assertEqual("47251649", token.get_tokeninfo("otp1c"))
        self.assertIn("dueDate", token.get_tokeninfo())
        token.remove_tokeninfo("otp1c")
        token.remove_tokeninfo("dueDate")

        # A timeout shorter than three time steps of 30 seconds is extended to them
        token.token.count = 47251640
        set_privacyidea_config("AutoResyncTimeout", 0)
        self.assertEqual(90, token.get_autoresync_timeout())
        # counter = 47251649 => otp = 705493, is out of sync
        time_before = int(time.time())
        r = token.check_otp("705493", window=30,
                            options={"initTime": 47251644 * 30})
        time_after = int(time.time())
        self.assertEqual(-1, r)
        due_date = int(token.get_tokeninfo("dueDate"))
        self.assertLessEqual(time_before + 90, due_date)
        self.assertGreaterEqual(time_after + 90, due_date)
        # counter = 47251650 => otp = 589836, will be autosynced
        r = token.check_otp("589836", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertEqual(47251650, r)
        self.assertEqual(AutoResyncResult.SUCCESSFUL, token.auth_details.get(AUTORESYNC_KEY))
        set_privacyidea_config("AutoResyncTimeout", 120)
        self.assertEqual(120, token.get_autoresync_timeout())
        # With a time step of 60 seconds, the minimum is three time steps of 60 seconds
        token.write_tokeninfo("timeStep", 60)
        self.assertEqual(180, token.get_autoresync_timeout())
        set_privacyidea_config("AutoResyncTimeout", 0)
        self.assertEqual(180, token.get_autoresync_timeout())
        token.write_tokeninfo("timeStep", 30)
        delete_privacyidea_config("AutoResyncTimeout")

        # No _autosync
        set_privacyidea_config("AutoResync", False)
        token.token.count = 47251640
        token.auth_details.clear()
        token.set_sync_window(10)
        # counter = 47251649 => otp = 705493, is out of sync
        r = token.check_otp("705493", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertTrue(r == -1, r)
        # counter = 47251650 => otp = 389836, will not get autosynced.
        r = token.check_otp("589836", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertTrue(r == -1, r)
        self.assertNotIn(AUTORESYNC_KEY, token.auth_details)
        # Later tests get the default time window
        token.remove_tokeninfo("timeWindow")

    def test_23_resync(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.set_sync_window(1000)
        # 705493 -> 47251649
        # 589836 -> 47251650
        # So the token might be at time 47251650,
        # but the server time is 47251600

        # The server time is 2000*30 seconds further, the resync will fail
        # 47253650 - 47251650 = 2000 ticks away
        token.token.count = 47251400
        r = token.resync("705493", "589836",
                         options={"initTime": 47253650 * 30})
        self.assertFalse(r)
        # Successful resync
        token.token.count = 47251400
        # The server time is 200*30 seconds further
        # 47251850 - 47251650 = 200 ticks away
        r = token.resync("705493", "589836",
                         options={"initTime": 47251850 * 30})
        self.assertTrue(r is True, r)
        # resync fails
        token.token.count = 0
        self.assertFalse(token.resync("399871", "123456"))
        # resync fails, the two correct OTP values are outside of the sync
        # window
        token.token.count = 0
        token.set_sync_window(5)
        self.assertFalse(token.resync("399871", "520489"))

    def test_24_challenges(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TotpTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.set_pin("test")
        token.token.count = 0
        token.set_sync_window(10)
        token.set_count_window(5)
        self.assertTrue(token.is_challenge_request("test"))

    def test_25_sha256_token(self):
        # taken from https://tools.ietf.org/html/rfc6238#appendix-B
        # sha256 with a 20 byte seed
        serial = "sha25T"
        db_token = Token(serial, tokentype="totp")
        db_token.save()
        token = TotpTokenClass(db_token)
        token.set_otpkey(binascii.hexlify(b"12345678901234567890"))
        token.set_hashlib("sha256")
        token.set_otplen(8)
        token.save()
        # get it from the database again
        # |  1111111111 |  2005-03-18  | 00000000023523ED | 67062674 | SHA256 |
        db_token = Token.query.filter_by(serial=serial).first()
        token = TotpTokenClass(db_token)
        r = token.check_otp("67062674", options={"initTime": 1111111111})
        # The value of the RFC belongs to the 32 byte seed: the 20 byte seed gives another OTP value
        self.assertEqual(-1, r)

        # sha256 with a 32 byte seed
        serial = "sha256"
        db_token = Token(serial, tokentype="totp")
        db_token.save()
        token = TotpTokenClass(db_token)
        token.set_otpkey(binascii.hexlify(b"12345678901234567890123456789012"))
        token.set_hashlib("sha256")
        token.set_otplen(8)
        token.save()
        db_token = Token.query.filter_by(serial=serial).first()
        token = TotpTokenClass(db_token)
        r = token.check_otp("67062674", options={"initTime": 1111111111})
        self.assertEqual(0x00000000023523ED, r)

        # sha512 with a 20 byte seed
        serial = "sha512"
        db_token = Token(serial, tokentype="totp")
        db_token.save()
        token = TotpTokenClass(db_token)
        token.set_otpkey(binascii.hexlify(b"12345678901234567890"))
        token.set_hashlib("sha512")
        token.set_otplen(8)
        token.save()
        db_token = Token.query.filter_by(serial=serial).first()
        token = TotpTokenClass(db_token)
        r = token.check_otp("99943326", options={"initTime": 1111111111})
        # The value of the RFC belongs to the 64 byte seed
        self.assertEqual(-1, r)

        # sha512 with a 64byte seed
        serial = "sha512b"
        db_token = Token(serial, tokentype="totp")
        db_token.save()
        token = TotpTokenClass(db_token)
        token.set_otpkey(binascii.hexlify(
            b"1234567890123456789012345678901234567890123456789012345678901234"))
        token.set_hashlib("sha512")
        token.set_otplen(8)
        token.save()
        db_token = Token.query.filter_by(serial=serial).first()
        token = TotpTokenClass(db_token)
        r = token.check_otp("93441116", options={"initTime": 1234567890})
        self.assertEqual(0x000000000273EF07, r)

    def test_26_get_setting_type(self):
        r = TotpTokenClass.get_setting_type("totp.hashlib")
        self.assertEqual(r, "public")
        r = TotpTokenClass.get_setting_type("totp.blabla")
        self.assertEqual(r, "")

    def test_26_is_previous_otp(self):
        # check if the OTP was used previously
        serial = "previous"
        db_token = Token(serial, tokentype="totp")
        db_token.save()
        token = TotpTokenClass(db_token)
        token.set_otpkey(self.otpkey)
        token.set_hashlib("sha1")
        token.set_otplen(6)
        # Authenticate with the current OTP value
        counter = token._time2counter(time.time(), timeStepping=30)
        otp_now = token._calc_otp(counter)
        r = token.check_otp(otp_now, window=180)
        self.assertEqual(r, counter)
        # Now we try several is_previous_otp and the timeShift must stay the same!
        ts0 = float(token.get_tokeninfo("timeShift"))
        self.assertTrue(-181 < ts0 < 181)
        # Too old
        r = token.is_previous_otp(token._calc_otp(counter - 3))
        self.assertEqual(r, False)
        ts = float(token.get_tokeninfo("timeShift"))
        self.assertEqual(ts, ts0)
        # The same OTP value
        r = token.is_previous_otp(otp_now)
        self.assertEqual(r, True)
        ts = float(token.get_tokeninfo("timeShift"))
        self.assertEqual(ts, ts0)
        # Future value
        r = token.is_previous_otp(token._calc_otp(counter + 8))
        self.assertEqual(r, False)
        ts = float(token.get_tokeninfo("timeShift"))
        self.assertEqual(ts, ts0)

    def test_27_get_default_settings(self):
        params = {}
        g = FakeFlaskG()
        g.audit_object = FakeAudit()
        g.logged_in_user = {"user": "hans",
                            "realm": "default",
                            "role": "user"}
        set_policy("pol1", scope=SCOPE.USER, action="totp_hashlib=sha256,"
                                                    "totp_timestep=60,"
                                                    "totp_otplen=8")
        g.policy_object = PolicyClass()
        p = TotpTokenClass.get_default_settings(g, params)
        self.assertEqual(p.get("otplen"), "8")
        self.assertEqual(p.get("hashlib"), "sha256")
        self.assertEqual(p.get("timeStep"), "60")
        delete_policy("pol1")

        # the same should work for admins
        g.logged_in_user = {"user": "admin",
                            "realm": "super",
                            "role": "admin"}
        set_policy("pol1", scope=SCOPE.ADMIN, action="totp_hashlib=sha512,"
                                                     "totp_timestep=60,"
                                                     "totp_otplen=8")
        g.policy_object = PolicyClass()
        p = TotpTokenClass.get_default_settings(g, params)
        self.assertEqual(p.get("otplen"), "8")
        self.assertEqual(p.get("hashlib"), "sha512")
        self.assertEqual(p.get("timeStep"), "60")
        # test check if there is no logged in user
        g.logged_in_user = None
        p = TotpTokenClass.get_default_settings(g, params)
        self.assertEqual(p, {})
        delete_policy("pol1")

    def test_28_totp_token_export(self):
        # Set up the TOTP token for testing
        totptoken = init_token(param={'serial': "TOTP12345678", 'type': 'totp', 'otpkey': '12345', "otplen": '8'})
        totptoken.set_description("this is a totp token export test")
        totptoken.write_tokeninfo("hashlib", "sha256")

        # Test that all expected keys are present in the exported dictionary
        exported_data = totptoken.export_token()

        expected_keys = ["serial", "type", "description", "count", "otplen", "otpkey"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["hashlib", "tokenkind", "timeWindow", "timeStep", "timeShift"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        exported_data = totptoken.export_token()
        self.assertEqual(exported_data["serial"], "TOTP12345678")
        self.assertEqual(exported_data["type"], "totp")
        self.assertEqual(exported_data["description"], "this is a totp token export test")
        self.assertEqual(exported_data["info_list"]["hashlib"], "sha256")
        self.assertEqual(exported_data["otplen"], 8)
        self.assertEqual(exported_data["otpkey"], '12345')
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")

        # Clean up
        remove_token(totptoken.token.serial)

    def test_29_totp_token_import(self):
        # Define the token data to be imported
        token_data = [{
            "serial": "TOTP12345678",
            "type": "totp",
            "description": "this is a totp token import test",
            "otpkey": self.otpkey,
            "otplen": 8,
            "issuer": "privacyIDEA",
            "count": 0,
            "info_list": {"hashlib": "sha256", "timeShift": 0, "timeStep": 60, "timeWindow": 180,
                          "tokenkind": "software"}
        }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        totptoken = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(totptoken.token.serial, token_data[0]["serial"])
        self.assertEqual(totptoken.type, token_data[0]["type"])
        self.assertEqual(totptoken.token.description, token_data[0]["description"])
        self.assertEqual(totptoken.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(totptoken.get_tokeninfo("hashlib"), "sha256")
        self.assertEqual(totptoken.token.otplen, token_data[0]["otplen"])
        self.assertEqual(totptoken.get_tokeninfo("tokenkind"), "software")
        self.assertEqual(totptoken.get_tokeninfo("timeWindow"), "180")
        self.assertEqual(totptoken.get_tokeninfo("timeStep"), "60")
        self.assertEqual(totptoken.get_tokeninfo("timeShift"), "0")

        # Check that token works
        with mock.patch('time.time') as MockTime:
            MockTime.return_value = 1692662723.0  # 2023-08-22T00:55:23+00:00
            # Current OTP works
            # Found the counter 470184
            self.assertEqual(28211045, totptoken.check_otp('34965900'))

        # Clean up
        remove_token(totptoken.token.serial)

    def test_30_autoresync_hooks(self):
        # TOTP checks the sync window in both directions, a counter up to the token counter is used already and
        # the autoresync is not implemented a second time
        token = init_token({"type": "totp", "serial": "TOTPHOOKS", "otpkey": self.otpkey})
        self.addCleanup(remove_token, "TOTPHOOKS")
        token.set_sync_window(10)
        hmac2otp = HmacOtp(token.token.get_otpkey(), 5, 6, token.get_hashlib(token.hashlib))
        # counter 8 is ahead, counter 2 is behind the counter 5
        self.assertEqual(8, token._check_sync_window(hmac2otp, "399871"))
        self.assertEqual(2, token._check_sync_window(hmac2otp, "359152"))
        token.token.count = 7
        self.assertTrue(token._is_used_counter(6))
        self.assertTrue(token._is_used_counter(7))
        self.assertFalse(token._is_used_counter(8))
        self.assertNotIn("_autosync", TotpTokenClass.__dict__)

    # The autoresync with skipped codes. The token counter is COUNT, the server time step is NOW and all values the
    # tests present are out of the normal window, but in the sync window.
    COUNT = 47251640
    NOW = COUNT + 3
    FIRST = NOW + 3

    def _autoresync_token(self, serial="TOTPSKIP", enable=True, **params):
        token = init_token({"type": "totp", "serial": serial, "otpkey": self.otpkey, **params})
        self.addCleanup(remove_token, serial)
        if enable:
            set_privacyidea_config("AutoResync", True)
            self.addCleanup(delete_privacyidea_config, "AutoResync")
        self.addCleanup(delete_privacyidea_config, "AutoResyncTimeout")
        token.set_sync_window(100)
        token.token.count = self.COUNT
        token.token.save()
        return token

    def _present(self, token, counter, now=None):
        """Present the OTP value of the counter to the token at the given time step and return the result"""
        hmac2otp = HmacOtp(token.token.get_otpkey(), counter, 6, token.get_hashlib(token.hashlib))
        token.auth_details.clear()
        return token.check_otp(hmac2otp.generate(counter), window=token.timestep,
                               options={"initTime": (now or self.NOW) * token.timestep})

    def test_31_autoresync_skipped_codes(self):
        token = self._autoresync_token()
        self.assertEqual(6, token._max_autoresync_gap())

        # The exact successor
        self.assertEqual(-1, self._present(token, self.FIRST))
        self.assertEqual(AutoResyncResult.STARTED, token.auth_details.get(AUTORESYNC_KEY))
        self.assertEqual(self.FIRST + 1, self._present(token, self.FIRST + 1))
        self.assertEqual(AutoResyncResult.SUCCESSFUL, token.auth_details.get(AUTORESYNC_KEY))

        # A skipped code completes the autoresync, the counter and the time shift come from the second value
        token.token.count = self.COUNT
        self.assertEqual(-1, self._present(token, self.FIRST))
        second = self.FIRST + 3
        before = int(time.time())
        self.assertEqual(second, self._present(token, second))
        self.assertEqual(AutoResyncResult.SUCCESSFUL, token.auth_details.get(AUTORESYNC_KEY))
        self.assertEqual(second, token.token.count)
        self.assertAlmostEqual(second * 30 - before, token.timeshift, delta=5)
        self.assertNotIn("otp1c", token.get_tokeninfo())
        self.assertNotIn("dueDate", token.get_tokeninfo())

        # The gap of the cap succeeds, one more fails and removes the first value
        token.token.count = self.COUNT
        self.assertEqual(-1, self._present(token, self.FIRST))
        self.assertEqual(self.FIRST + 6, self._present(token, self.FIRST + 6))
        token.token.count = self.COUNT
        self.assertEqual(-1, self._present(token, self.FIRST))
        self.assertEqual(-1, self._present(token, self.FIRST + 7))
        self.assertEqual(AutoResyncResult.FAILED, token.auth_details.get(AUTORESYNC_KEY))
        self.assertNotIn("otp1c", token.get_tokeninfo())
        self.assertNotIn("dueDate", token.get_tokeninfo())

        # The same or an older value than the first one fails
        for second in (self.FIRST, self.FIRST - 1):
            self.assertEqual(-1, self._present(token, self.FIRST))
            self.assertEqual(-1, self._present(token, second))
            self.assertEqual(AutoResyncResult.FAILED, token.auth_details.get(AUTORESYNC_KEY))
            self.assertNotIn("otp1c", token.get_tokeninfo())

    def test_32_autoresync_gap_cap(self):
        # (timeWindow, AutoResyncTimeout, timeStep, cap)
        for number, (window, timeout, step, cap) in enumerate([(180, None, 30, 6), (180, 3600, 30, 6), (300, 10, 30, 3),
                                           (300, 100, 30, 3), (360, 3600, 60, 6), (300, 3600, 60, 5),
                                           (10, None, 30, 1)]):
            with self.subTest(window=window, timeout=timeout, step=step):
                token = self._autoresync_token(f"TOTPCAP{number}", timeWindow=window, timeStep=step)
                if timeout is not None:
                    set_privacyidea_config("AutoResyncTimeout", timeout)
                else:
                    delete_privacyidea_config("AutoResyncTimeout")
                self.assertEqual(cap, token._max_autoresync_gap())
                self.assertTrue(token._is_next_counter(10, 10 + cap))
                self.assertFalse(token._is_next_counter(10, 10 + cap + 1))
                self.assertFalse(token._is_next_counter(10, 10))
                self.assertFalse(token._is_next_counter(10, 9))

        # An invalid AutoResyncTimeout falls back to 300 seconds
        token = self._autoresync_token()
        set_privacyidea_config("AutoResyncTimeout", "no number")
        self.assertEqual(6, token._max_autoresync_gap())

    def test_33_autoresync_used_values(self):
        token = self._autoresync_token()
        # A first value that was used already does not start an autoresync
        self.assertEqual(-1, self._present(token, self.COUNT - 2))
        self.assertNotIn(AUTORESYNC_KEY, token.auth_details)
        self.assertNotIn("otp1c", token.get_tokeninfo())
        self.assertNotIn("dueDate", token.get_tokeninfo())
        self.assertEqual(-1, self._present(token, self.COUNT))
        self.assertNotIn("otp1c", token.get_tokeninfo())
        self.assertNotIn(AUTORESYNC_KEY, token.auth_details)

        # A used first value, stored by an older version, fails the autoresync. A used second value
        # can not be tested on its own: since otp2c > otp1c, a used otp2c always implies a used otp1c.
        token.write_tokeninfo("otp1c", self.COUNT - 1)
        token.write_tokeninfo("dueDate", int(time.time()) + 600)
        self.assertEqual(-1, self._present(token, self.COUNT + 1))
        self.assertEqual(AutoResyncResult.FAILED, token.auth_details.get(AUTORESYNC_KEY))
        self.assertNotIn("otp1c", token.get_tokeninfo())

        # A second value outside the sync window fails
        self.assertEqual(-1, self._present(token, self.FIRST))
        self.assertEqual(-1, self._present(token, self.NOW + 101))
        self.assertNotEqual(AutoResyncResult.SUCCESSFUL, token.auth_details.get(AUTORESYNC_KEY))
        self.assertEqual(self.COUNT, token.token.count)

    def test_34_autoresync_deadline_and_switch(self):
        token = self._autoresync_token()
        self.assertEqual(-1, self._present(token, self.FIRST))
        # The deadline is exclusive, a value at the dueDate starts a new autoresync
        token.write_tokeninfo("dueDate", int(time.time()))
        self.assertEqual(-1, self._present(token, self.FIRST + 1))
        self.assertEqual(AutoResyncResult.STARTED, token.auth_details.get(AUTORESYNC_KEY))
        self.assertEqual(str(self.FIRST + 1), token.get_tokeninfo("otp1c"))
        # A dueDate in the future completes it
        token.write_tokeninfo("dueDate", int(time.time()) + 100)
        self.assertEqual(self.FIRST + 2, self._present(token, self.FIRST + 2))

        # A stored counter without a dueDate restarts
        token.token.count = self.COUNT
        token.write_tokeninfo("otp1c", self.FIRST)
        self.assertEqual(-1, self._present(token, self.FIRST + 1))
        self.assertEqual(AutoResyncResult.STARTED, token.auth_details.get(AUTORESYNC_KEY))
        token.remove_tokeninfo("otp1c")
        token.remove_tokeninfo("dueDate")

        # Without the AutoResync nothing is stored
        delete_privacyidea_config("AutoResync")
        self.assertEqual(-1, self._present(token, self.FIRST))
        self.assertNotIn(AUTORESYNC_KEY, token.auth_details)
        self.assertNotIn("otp1c", token.get_tokeninfo())

    def test_35_autoresync_deadline_with_clock(self):
        token = self._autoresync_token()
        timeout = token.get_autoresync_timeout()
        self.assertEqual(300, timeout)
        start = 1700000000

        # The second value one second before the deadline completes the autoresync
        with mock.patch("privacyidea.lib.tokens.hotptoken.time.time", return_value=start):
            self.assertEqual(-1, self._present(token, self.FIRST))
            self.assertEqual(start + timeout, int(token.get_tokeninfo("dueDate")))
        with mock.patch("privacyidea.lib.tokens.hotptoken.time.time", return_value=start + timeout - 1):
            self.assertTrue(token.has_pending_autoresync())
            self.assertEqual(self.FIRST + 1, self._present(token, self.FIRST + 1))
        self.assertEqual(AutoResyncResult.SUCCESSFUL, token.auth_details.get(AUTORESYNC_KEY))

        # The second value at the deadline starts a new autoresync
        token.token.count = self.COUNT
        with mock.patch("privacyidea.lib.tokens.hotptoken.time.time", return_value=start):
            self.assertEqual(-1, self._present(token, self.FIRST))
            self.assertEqual(start + timeout, int(token.get_tokeninfo("dueDate")))
        with mock.patch("privacyidea.lib.tokens.hotptoken.time.time", return_value=start + timeout):
            self.assertFalse(token.has_pending_autoresync())
            self.assertEqual(-1, self._present(token, self.FIRST + 1))
            self.assertEqual(AutoResyncResult.STARTED, token.auth_details.get(AUTORESYNC_KEY))
            self.assertEqual(str(self.FIRST + 1), token.get_tokeninfo("otp1c"))
            self.assertEqual(start + 2 * timeout, int(token.get_tokeninfo("dueDate")))

    def test_36_autoresync_configuration_change_while_pending(self):
        token = self._autoresync_token()
        start = 1700000000

        # A smaller time window lowers the cap of a pair that is pending already
        with mock.patch("privacyidea.lib.tokens.hotptoken.time.time", return_value=start):
            self.assertEqual(-1, self._present(token, self.FIRST))
        self.assertEqual(6, token._max_autoresync_gap())
        token.write_tokeninfo("timeWindow", 60)
        self.assertEqual(2, token._max_autoresync_gap())
        with mock.patch("privacyidea.lib.tokens.hotptoken.time.time", return_value=start + 1):
            self.assertEqual(-1, self._present(token, self.FIRST + 3))
        self.assertEqual(AutoResyncResult.FAILED, token.auth_details.get(AUTORESYNC_KEY))
        self.assertNotIn("otp1c", token.get_tokeninfo())
        self.assertNotIn("dueDate", token.get_tokeninfo())
        token.write_tokeninfo("timeWindow", 180)

        # A longer AutoResyncTimeout does not extend the dueDate of a pair that is pending already
        token.token.count = self.COUNT
        with mock.patch("privacyidea.lib.tokens.hotptoken.time.time", return_value=start):
            self.assertEqual(-1, self._present(token, self.FIRST))
        due_date = int(token.get_tokeninfo("dueDate"))
        self.assertEqual(start + 300, due_date)
        set_privacyidea_config("AutoResyncTimeout", 3600)
        self.assertEqual(3600, token.get_autoresync_timeout())
        self.assertEqual(due_date, int(token.get_tokeninfo("dueDate")))
        with mock.patch("privacyidea.lib.tokens.hotptoken.time.time", return_value=due_date):
            self.assertEqual(-1, self._present(token, self.FIRST + 1))
            self.assertEqual(AutoResyncResult.STARTED, token.auth_details.get(AUTORESYNC_KEY))
            self.assertEqual(due_date + 3600, int(token.get_tokeninfo("dueDate")))
