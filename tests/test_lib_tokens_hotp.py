# -*- coding: utf-8 -*-

"""
This test file tests the lib.tokenclass

The lib.tokenclass depends on the DB model and lib.user
"""
import warnings

from .base import MyTestCase, FakeFlaskG, FakeAudit
from privacyidea.lib.error import ParameterError
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import (User)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.utils import b32encode_and_unicode
from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.models import (Token,
                                 Config,
                                 Challenge)
from privacyidea.lib.config import (set_privacyidea_config, set_prepend_pin)
from privacyidea.lib.policy import (PolicyClass, SCOPE, set_policy,
                                    delete_policy)
import binascii
import datetime
import hashlib
from dateutil.tz import tzlocal

from passlib.crypto.digest import pbkdf2_hmac

PWFILE = "tests/testdata/passwords"


class HOTPTokenTestCase(MyTestCase):
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

    # add_user, get_user, reset, set_user_identifiers

    def test_00_create_user_realm(self):
        rid = save_resolver({"resolver": self.resolvername1,
                               "type": "passwdresolver",
                               "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="hotp")
        db_token.save()
        token = HotpTokenClass(db_token)
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "hotp", token.token)
        self.assertTrue(token.type == "hotp", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "OATH", class_prefix)
        self.assertTrue(token.get_class_type() == "hotp", token)

    def test_02_set_user(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        self.assertTrue(token.token.tokentype == "hotp",
                        token.token.tokentype)
        self.assertTrue(token.type == "hotp", token.type)

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
        token = HotpTokenClass(db_token)
        token.token.failcount = 10
        token.reset()
        self.assertTrue(token.token.failcount == 0,
                        token.token.failcount)

    def test_04_base_methods(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
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
        self.assertTrue(token.get_tokentype() == "hotp",
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
        token = HotpTokenClass(db_token)
        token.set_pin("hallo")
        (ph1, pseed) = token.get_pin_hash_seed()
        # check the database
        token.set_pin("blubber")
        ph2 = token.token.pin_hash
        self.assertTrue(ph1 != ph2)
        token.set_pin_hash_seed(ph1, pseed)

    def test_07_enable(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        token.enable(False)
        self.assertTrue(token.token.active is False)
        token.enable()
        self.assertTrue(token.token.active)

    def test_05_get_set_realms(self):
        set_realm(self.realm2)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        realms = token.get_realms()
        self.assertTrue(len(realms) == 1, realms)
        token.set_realms([self.realm1, self.realm2])
        realms = token.get_realms()
        self.assertTrue(len(realms) == 2, realms)

    def test_99_delete_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        token.delete_token()

        db_token = Token.query.filter_by(serial=self.serial1).first()
        self.assertTrue(db_token is None, db_token)

    def test_08_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        token.set_hashlib("sha1")
        ti = token.get_tokeninfo()
        self.assertTrue("hashlib" in ti, ti)

    def test_09_failcount(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        start = token.token.failcount
        end = token.inc_failcount()
        self.assertTrue(end == start + 1, (end, start))

    def test_10_get_hashlib(self):
        # check if functions are returned
        for hl in ["sha1", "md5", "sha256", "sha512",
                   "sha224", "sha384", "", None]:
            self.assertTrue(hasattr(HotpTokenClass.get_hashlib(hl),
                                    '__call__'),
                            HotpTokenClass.get_hashlib(hl))

    def test_11_tokeninfo(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
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

        # handle validity end date
        token.set_validity_period_end("2014-12-30T16:00+0200")
        end = token.get_validity_period_end()
        self.assertTrue(end == "2014-12-30T16:00+0200", end)
        self.assertRaises(Exception,
                          token.set_validity_period_end, "wrong date")
        # handle validity start date
        token.set_validity_period_start("2013-12-30T16:00+0200")
        start = token.get_validity_period_start()
        self.assertTrue(start == "2013-12-30T16:00+0200", start)
        self.assertRaises(Exception,
                          token.set_validity_period_start, "wrong date")

        self.assertFalse(token.check_validity_period())

        # check validity period
        # +5 days
        end_date = datetime.datetime.now(tzlocal()) + datetime.timedelta(5)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # - 5 days
        start_date = datetime.datetime.now(tzlocal()) - datetime.timedelta(5)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertTrue(token.check_validity_period())

        # check before start date
        # +5 days
        end_date = datetime.datetime.now(tzlocal()) + datetime.timedelta(5)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # + 2 days
        start_date = datetime.datetime.now(tzlocal()) + datetime.timedelta(2)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertFalse(token.check_validity_period())

        # check after enddate
        # -1 day
        end_date = datetime.datetime.now(tzlocal()) - datetime.timedelta(1)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # - 10 days
        start_date = datetime.datetime.now(tzlocal()) - datetime.timedelta(10)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertFalse(token.check_validity_period())

    def test_12_inc_otp_counter(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)

        token.set_otp_count(10)
        self.assertTrue(token.token.count == 10, token.token.count)
        # increase counter by 1
        token.inc_otp_counter()
        self.assertTrue(token.token.count == 11, token.token.count)
        # increase counter to 21
        Config(Key="DefaultResetFailCount", Value=True).save()
        token.inc_otp_counter(counter=20)
        self.assertTrue(token.token.count == 21, token.token.count)

    def test_13_check_otp(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "pin": "test",
                      "otplen": 6})
        # OTP does not exist
        self.assertTrue(token.check_otp_exist("222333") == -1)
        # OTP does exist
        res = token.check_otp_exist("969429")
        self.assertTrue(res == 3, res)
        # check is_previous_otp
        r = token.is_previous_otp("969429")
        self.assertTrue(r)

    def test_14_split_pin_pass(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)

        token.token.otplen = 6
        # postpend pin
        set_prepend_pin(False)
        _res, pin, value = token.split_pin_pass("222333test")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(value == "222333", value)
        # prepend pin
        set_prepend_pin(True)
        _res, pin, value = token.split_pin_pass("test222333")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(value == "222333", value)

    def test_15_check_pin(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        # test the encrypted pin
        token.set_pin("encrypted", encrypt=True)
        self.assertTrue(token.check_pin("encrypted"))
        self.assertFalse(token.check_pin("wrong pin"))

        # test the hashed pin
        token.set_pin("test")
        self.assertTrue(token.check_pin("test"))
        self.assertFalse(token.check_pin("wrong pin"))

    def test_16_init_detail(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
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
        token = HotpTokenClass(db_token)
        # Failed update: genkey wrong
        self.assertRaises(Exception,
                          token.update,
                          {"description": "new desc",
                           "genkey": "17"})
        # genkey and otpkey used at the same time
        token.update({"otpkey": self.otpkey,
                      "genkey": "1"})
        self.assertTrue(token.token.otplen == 6)

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

        # update token without otpkey raises an error
        self.assertRaises(Exception, token.update, {"description": "test"})

    def test_18_challenges(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        transaction_id = "123456789"
        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test123456")
        self.assertFalse(resp, resp)

        C = Challenge(self.serial1, transaction_id=transaction_id, challenge="Who are you?")
        C.save()
        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test123456",
                                            options={"transaction_id": transaction_id})
        self.assertTrue(resp, resp)
        # test if challenge is valid
        self.assertTrue(C.is_valid())

    def test_19_pin_otp_functions(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        db_token.set_pin("test")
        token = HotpTokenClass(db_token)
        # check OTP according to RFC 4226
        """
                             Truncated
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
        """
        token.update({"otpkey": self.otpkey})
        self.assertTrue(db_token.otplen == 6, 6)
        set_prepend_pin()
        res, pin, otp = token.split_pin_pass("test123456")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(otp == "123456", otp)
        self.assertTrue(token.check_pin(pin), pin)
        check = token.check_otp("755224", counter=0, window=10)
        self.assertTrue(check == 0, check)
        self.assertTrue(token.check_otp("287082", counter=1, window=10) == 1)
        # The 6th counter:
        self.assertTrue(token.check_otp("287922", counter=2, window=10) == 6)
        # The tokenclass itself saves the counter to the database
        self.assertTrue(token.token.count == 7, token.token.count)

        # successful authentication
        res = token.authenticate("test399871")
        # This is the OTP value of the counter=8
        self.assertTrue(res == (True, 8, None), res)

        # try the same otp value again, will fail!
        res = token.authenticate("test399871")
        # This is the OTP value of the counter=8
        self.assertTrue(res == (True, -1, None), res)

        token.set_otp_count(0)
        # get the OTP value for counter 0
        res = token.get_otp()
        self.assertTrue(res[0] == 1, res)
        self.assertTrue(res[1] == -1, res)
        self.assertTrue(res[2] == "755224", res)
        res = token.get_multi_otp()
        self.assertTrue(res[0] is False, res)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.token.count = 0
        res = token.get_multi_otp(count=5)
        self.assertTrue(res[0], res)
        self.assertTrue(res[1] == "OK", res)
        self.assertTrue(res[2].get("otp").get(1) == "287082", res)
        self.assertTrue(res[2].get("type") == "hotp", res)

        # do some failing otp checks
        token.token.otplen = "invalid otp counter"
        self.assertRaises(Exception, token.check_otp, "123456")
        token.token.otplen = 0

    def test_20_check_challenge_response(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        db_token.set_pin("test")
        token = HotpTokenClass(db_token)
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

    def test_21_get_class_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        ti = token.get_class_info()
        self.assertTrue(ti.get("type") == "hotp", ti)
        self.assertTrue("policy" in ti, ti)
        self.assertTrue("title" in ti, ti)
        self.assertTrue("user" in ti, ti)

    def test_22_autosync(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        set_privacyidea_config("AutoResync", True)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.token.count = 0
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8, is out of sync
        r = token.check_otp(anOtpVal="399871")
        self.assertTrue(r == -1, r)
        # counter = 9, will be autosynced.
        r = token.check_otp(anOtpVal="520489")
        self.assertTrue(r == 9, r)
        # counter = 10, has also to authenticate! The counter of the token is
        #  set.
        r = token.check_otp(anOtpVal="403154")
        self.assertTrue(r == 10, r)
        self.assertEqual(token.token.count, 11)

        # Autosync with a gap in the next otp value will fail
        token.token.count = 0
        # Just try some bullshit config value
        set_privacyidea_config("AutoResyncTimeout", "totally not a number")
        # counter = 7, is out of sync
        r = token.check_otp(anOtpVal="162583")
        self.assertTrue(r == -1, r)
        # counter = 9, will NOT _autosync
        r = token.check_otp(anOtpVal="520489")
        self.assertTrue(r == -1, r)

        # Autosync fails, if dueDate is over
        token.token.count = 0
        set_privacyidea_config("AutoResyncTimeout", 0)
        # counter = 8, is out of sync
        r = token.check_otp(anOtpVal="399871")
        self.assertTrue(r == -1, r)
        # counter = 9, is the next value, but duedate is over.
        r = token.check_otp(anOtpVal="520489")
        self.assertTrue(r == -1, r)

        # No _autosync
        set_privacyidea_config("AutoResync", False)
        token.token.count = 0
        # counter = 8, is out of sync
        r = token.check_otp(anOtpVal="399871")
        self.assertTrue(r == -1, r)
        # counter = 9, will not be autosynced
        r = token.check_otp(anOtpVal="520489")
        self.assertTrue(r == -1, r)

    def test_23_resync(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = HotpTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.token.count = 0
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8: 399871
        # counter = 9: 520489
        # Successful resync
        r = token.resync("399871", "520489")
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
        token = HotpTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.set_pin("test")
        token.token.count = 0
        token.set_sync_window(10)
        token.set_count_window(5)
        self.assertTrue(token.is_challenge_request("test"))

    def test_25_sha256_token(self):
        # taken from https://tools.ietf.org/html/rfc6238#appendix-B
        serial = "sha25T"
        db_token = Token(serial, tokentype="hotp")
        db_token.save()
        token = HotpTokenClass(db_token)
        token.set_otpkey(binascii.hexlify(b"12345678901234567890"))
        token.set_hashlib("sha256")
        token.set_otplen(8)
        token.save()
        # get it from the database again
        #    59     |  1970-01-01  | 0000000000000001 | 46119246 | SHA256 |
        db_token = Token.query.filter_by(serial=serial).first()
        token = HotpTokenClass(db_token)
        r = token.check_otp("46119246")
        self.assertTrue(r)
        # 00000000023523ED | 67062674 | SHA256 |
        token.set_otp_count(0x00000000023523ED - 1)
        token.save()
        token.check_otp("67062674")

    def test_26_is_previous_otp(self):
        # check if the OTP was used previously
        serial = "previous"
        db_token = Token(serial, tokentype="hotp")
        db_token.save()
        token = HotpTokenClass(db_token)
        token.set_otpkey(self.otpkey)
        token.set_otplen(6)
        token.save()
        """
                          Truncated
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
        """
        r = token.check_otp("969429")
        self.assertEqual(r, 3)
        # Too old
        r = token.is_previous_otp("755224")
        self.assertEqual(r, False)
        # The very previous OTP, that was just used in check_otp
        r = token.is_previous_otp("969429")
        self.assertEqual(r, True)
        # Future value
        r = token.is_previous_otp("254676")
        self.assertEqual(r, False)
        r = token.check_otp("254676")
        self.assertEqual(r, 5)

    def test_27_get_default_settings(self):
        params = {}
        g = FakeFlaskG()
        g.audit_object = FakeAudit()
        g.logged_in_user = {"user": "hans",
                          "realm": "default",
                          "role": "user"}
        set_policy("pol1", scope=SCOPE.USER, action="hotp_hashlib=sha256,"
                                                    "hotp_otplen=8")
        g.policy_object = PolicyClass()
        p = HotpTokenClass.get_default_settings(g, params)
        self.assertEqual(p.get("otplen"), "8")
        self.assertEqual(p.get("hashlib"), "sha256")
        delete_policy("pol1")
        # the same should work for an admin user
        g.logged_in_user = {"user": "admin",
                            "realm": "super",
                            "role": "admin"}
        set_policy("pol1", scope=SCOPE.ADMIN, action="hotp_hashlib=sha512,"
                                                     "hotp_otplen=8")
        g.policy_object = PolicyClass()
        p = HotpTokenClass.get_default_settings(g, params)
        self.assertEqual(p.get("otplen"), "8")
        self.assertEqual(p.get("hashlib"), "sha512")
        # test check if there is no logged in user
        g.logged_in_user = None
        p = HotpTokenClass.get_default_settings(g, params)
        self.assertEqual(p, {})
        delete_policy("pol1")

    def test_28_2step_generation_default(self):
        serial = "2step"
        db_token = Token(serial, tokentype="hotp")
        db_token.save()
        token = HotpTokenClass(db_token)
        token.update({"2stepinit": "1"})
        # fetch the server component for later tests
        server_component = binascii.unhexlify(token.token.get_otpkey().getKey())
        # generate a 8-byte client component
        client_component = b'abcdefgh'
        # construct a secret
        token.update({"otpkey": binascii.hexlify(client_component)})
        # check the generated secret
        secret = binascii.unhexlify(token.token.get_otpkey().getKey())
        # check the correct lengths
        self.assertEqual(len(server_component), 20)
        self.assertEqual(len(client_component), 8)
        self.assertEqual(len(secret), 20)
        # check the secret has been generated according to the specification
        expected_secret = pbkdf2_hmac('sha1', binascii.hexlify(server_component),
                                      client_component, 10000, 20)
        self.assertEqual(secret, expected_secret)

    def test_29_2step_generation_custom(self):
        serial = "2step2"
        db_token = Token(serial, tokentype="hotp")
        db_token.save()
        token = HotpTokenClass(db_token)
        token.update({
            "2stepinit": "1",
            "2step_serversize": "40",
            "2step_difficulty": "12345",
            "2step_clientsize": "12",
            "hashlib": "sha512",
        })
        self.assertEqual(token.token.rollout_state, "clientwait")
        self.assertEqual(token.get_tokeninfo("2step_clientsize"), "12")
        self.assertEqual(token.get_tokeninfo("2step_difficulty"), "12345")
        # fetch the server component for later tests
        server_component = binascii.unhexlify(token.token.get_otpkey().getKey())
        # too short
        self.assertRaises(ParameterError, token.update, {
            "otpkey": binascii.hexlify(b"="*8)
        })
        # generate a 12-byte client component
        client_component = b'abcdefghijkl'
        # construct a secret
        token.update({
            "otpkey": binascii.hexlify(client_component),
            # the following values are ignored
            "2step_serversize": "23",
            "2step_difficulty": "666666",
            "2step_clientsize": "13"
            })
        # check the generated secret
        secret = binascii.unhexlify(token.token.get_otpkey().getKey())
        # check the correct lengths
        self.assertEqual(len(server_component), 40)
        self.assertEqual(len(client_component), 12)
        self.assertEqual(len(secret), 64) # because of SHA-512
        # check the secret has been generated according to the specification
        expected_secret = pbkdf2_hmac('sha1', binascii.hexlify(server_component),
                                      client_component, 12345, len(secret))
        self.assertEqual(secret, expected_secret)
        self.assertTrue(token.token.active)

    def test_30_2step_otpkeyformat(self):
        serial = "2step3"
        db_token = Token(serial, tokentype="hotp")
        db_token.save()
        token = HotpTokenClass(db_token)
        token.update({
            "2stepinit": "1",
            "2step_clientsize": "12",
            "hashlib": "sha512",
        })
        self.assertEqual(token.token.rollout_state, "clientwait")
        self.assertEqual(token.get_tokeninfo("2step_clientsize"), "12")
        # fetch the server component for later tests
        server_component = binascii.unhexlify(token.token.get_otpkey().getKey())
        # generate a 12-byte client component
        client_component = b'abcdefghijkl'
        checksum = hashlib.sha1(client_component).digest()[:4]
        # wrong checksum
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=DeprecationWarning)
            self.assertRaisesRegex(
                ParameterError,
                "Incorrect checksum",
                token.update,
                {
                    "otpkey": b32encode_and_unicode(b"\x37" + checksum[1:] + client_component).strip("="),
                    "otpkeyformat": "base32check",
                })
        # construct a secret
        token.update({
            "otpkey": b32encode_and_unicode(checksum + client_component).strip("="),
            "otpkeyformat": "base32check",
            # the following values are ignored
            "2step_serversize": "23",
            "2step_difficulty": "666666",
            "2step_clientsize": "13"
            })
        # check the generated secret
        secret = binascii.unhexlify(token.token.get_otpkey().getKey())
        # check the correct lengths
        self.assertEqual(len(server_component), 64) # because of SHA-512
        self.assertEqual(len(client_component), 12)
        self.assertEqual(len(secret), 64) # because of SHA-512
        # check the secret has been generated according to the specification
        expected_secret = pbkdf2_hmac('sha1', binascii.hexlify(server_component),
                                      client_component, 10000, len(secret))
        self.assertEqual(secret, expected_secret)
        self.assertTrue(token.token.active)
