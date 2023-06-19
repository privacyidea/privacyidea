"""
This test file tests the lib.tokenclass

The lib.tokenclass depends on the DB model and lib.user
"""
PWFILE = "tests/testdata/passwords"

from .base import MyTestCase, FakeAudit, FakeFlaskG
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import (User)
from privacyidea.lib.tokens.totptoken import TotpTokenClass
from privacyidea.lib.policy import (PolicyClass, set_policy, delete_policy, SCOPE)
from unittest import mock
from privacyidea.models import (Token,
                                 Config,
                                 Challenge)
from privacyidea.lib.config import (set_privacyidea_config, set_prepend_pin)
import datetime
import binascii
import time


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
        self.assertTrue(token.check_otp_exist("222333") == -1)
        # OTP does exist
        res = token.check_otp_exist("722053", options={"initTime": 47251645 *
                                                                   30})
        # Found the counter 47251647
        self.assertTrue(res == 47251647, res)

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
        # Failed update: genkey wrong
        self.assertRaises(Exception,
                          token.update,
                          {"description": "new desc",
                           "genkey": "17"})
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
        
        # update token without otpkey raises an error
        self.assertRaises(Exception, token.update, {"description": "test"})

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
        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test123456")
        self.assertFalse(resp, resp)

        transaction_id = "123456789"
        C = Challenge(self.serial1, transaction_id=transaction_id, challenge="Who are you?")
        C.save()
        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test123456",
                                            options={"transaction_id": transaction_id})
        self.assertTrue(resp, resp)

        # test if challenge is valid
        C.is_valid()

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
        res = token.get_multi_otp(count=5, curTime=datetime.datetime(2014,
                                                                     12,12))
        self.assertTrue(res[0], res)
        self.assertTrue(res[1] == "OK", res)
        self.assertTrue(len(res[2].get("otp")) == 5, res[2].get("otp"))
        self.assertTrue(47278080 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47278081 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47278082 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47278083 in res[2].get("otp"), res[2].get("otp"))
        self.assertTrue(47278084 in res[2].get("otp"), res[2].get("otp"))

        # do some failing otp checks
        token.token.otplen = "invalid otp counter"
        self.assertRaises(Exception, token.check_otp, "123456")
        token.token.otplen = 0

        # Previous OTP value used again
        token.token.otplen = 6
        #token.token.count = 47251640
        # The OTP for this counter was already presented to the server
        token.token.count = 47251648
        # 47251647 -> 722053
        res = token.check_otp("722053", options={"initTime": 47251649 * 30})
        #self.assertTrue(res == 47251647, res)
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
        num = Challenge.query.filter(Challenge.serial==self.serial1).count()
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
        r = token.check_otp(anOtpVal="705493", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertTrue(r == -1, r)
        # counter = 47251650 => otp = 389836, will be autosynced.
        r = token.check_otp(anOtpVal="589836", window=30,
                            options={"initTime": 47251645 * 30 })
        self.assertTrue(r == 47251650, r)

        # counter = 47251640 => otp = 166325 is an old OTP value
        # counter = 47251641 => otp = 432730 is an old OTP value
        # Autoresync with two times the same old OTP value must not work out!
        r = token.check_otp(anOtpVal="166325", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertTrue(r == -1, r)
        r = token.check_otp(anOtpVal="166325", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertTrue(r == -1, r)
        # Autoresync with two consecutive old OTP values must not work out!
        r = token.check_otp(anOtpVal="166325", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertTrue(r == -1, r)
        r = token.check_otp(anOtpVal="432730", window=30,
                            options={"initTime": 47251645 * 30})
        self.assertTrue(r == -1, r)

        # Autosync with a gap in the next otp value will fail
        token.token.count = 47251640
        # Just try some bullshit config value
        set_privacyidea_config("AutoResyncTimeout", "totally not a number")
        # counter = 47251648 => otp = 032819, is out of sync
        r = token.check_otp(anOtpVal="032819", window=30,
                            options={"initTime": 47251645 * 30 })
        self.assertTrue(r == -1, r)
        # counter = 47251650 => otp = 589836, will NOT _autosync
        r = token.check_otp(anOtpVal="589836", window=30,
                            options={"initTime": 47251645 * 30 })
        self.assertTrue(r == -1, r)

        # TOTP has no dueDate / AutoResyncTimeout

        # No _autosync
        set_privacyidea_config("AutoResync", False)
        token.token.count = 47251640
        token.set_sync_window(10)
        # counter = 47251649 => otp = 705493, is out of sync
        r = token.check_otp(anOtpVal="705493", window=30,
                            options={"initTime": 47251644 * 30})
        self.assertTrue(r == -1, r)
        # counter = 47251650 => otp = 389836, will not get autosynced.
        r = token.check_otp(anOtpVal="589836", window=30,
                            options={"initTime": 47251645 * 30 })
        self.assertTrue(r == -1, r)

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
        self.assertTrue(r)

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
        self.assertTrue(r)

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
        self.assertTrue(r)

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
        self.assertTrue(r)

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
