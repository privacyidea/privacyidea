"""
This test file tests the lib.tokenclass

The lib.tokenclass depends on the DB model and lib.user
"""
PWFILE = "tests/testdata/passwords"

from .base import MyTestCase
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import (User)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.tokens.totptoken import TotpTokenClass
from privacyidea.lib.policy import (PolicyClass, set_policy, delete_policy,
                                    SCOPE, ACTION)
from privacyidea.models import (Token,
                                 Config,
                                 Challenge)
from privacyidea.lib.config import (set_privacyidea_config, set_prepend_pin)
import datetime
import binascii


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
    
    # set_user, get_user, reset, set_user_identifiers
    
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
        
        token.set_user(User(login="cornelius",
                            realm=self.realm1))
        self.assertTrue(token.token.resolver_type == "passwdresolver",
                        token.token.resolver_type)
        self.assertTrue(token.token.resolver == self.resolvername1,
                        token.token.resolver)
        self.assertTrue(token.token.user_id == "1000",
                        token.token.user_id)
        
        user_object = token.user
        self.assertTrue(user_object.login == "cornelius",
                        user_object)
        self.assertTrue(user_object.resolver == self.resolvername1,
                        user_object)
        
        token.set_user_identifiers(2000, self.resolvername1, "passwdresolver")
        self.assertTrue(int(token.token.user_id) == 2000, token.token.user_id)

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
        
        self.assertTrue(token.get_user_id() == token.token.user_id)
        
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
        self.assertTrue(len(token.token.key_enc) == 192,
                        token.token.key_enc)
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
        
        # handle validity end date
        token.set_validity_period_end("30/12/14 16:00")
        end = token.get_validity_period_end()
        self.assertTrue(end == "30/12/14 16:00", end)
        self.assertRaises(Exception,
                          token.set_validity_period_end, "wrong date")
        # handle validity start date
        token.set_validity_period_start("30/12/13 16:00")
        start = token.get_validity_period_start()
        self.assertTrue(start == "30/12/13 16:00", start)
        self.assertRaises(Exception,
                          token.set_validity_period_start, "wrong date")
        
        self.assertFalse(token.check_validity_period())
        
        # check validity period
        # +5 days
        end_date = datetime.datetime.now() + datetime.timedelta(5)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # - 5 days
        start_date = datetime.datetime.now() - datetime.timedelta(5)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertTrue(token.check_validity_period())
        
        # check before start date
        # +5 days
        end_date = datetime.datetime.now() + datetime.timedelta(5)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # + 2 days
        start_date = datetime.datetime.now() + datetime.timedelta(2)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertFalse(token.check_validity_period())
        
        # check after enddate
        # -1 day
        end_date = datetime.datetime.now() - datetime.timedelta(1)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # - 10 days
        start_date = datetime.datetime.now() - datetime.timedelta(10)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertFalse(token.check_validity_period())

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
        r = token.get_QRimage_data({"googleurl": detail.get("googleurl").get(
            "value")})
        self.assertTrue('otpauth://totp/SE123456?secret=CERDGRCVMZ3YRGIA'
                        '&counter=1' in r[0], r[0])
        self.assertRaises(Exception, token.set_init_details, "unvalid value")
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
        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test123456",
                                            options={"transaction_id": "123456789"})
        self.assertTrue(resp, resp)

        # test if challenge is valid
        C = Challenge("S123455", transaction_id="tid", challenge="Who are you?")
        C.save()

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
        self.assertTrue(res[2] == "589836", res)

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
                      "otplen": 6})
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

        # simple get_otp of current time
        r = token.get_otp()
        self.assertTrue(r > 47251648, r)
        r = token.get_otp(current_time=datetime.datetime.now())
        self.assertTrue(r > 47251648, r)

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
        token.token.count = 47251400
        token.set_sync_window(1000)
        # Successful resync
        # 705493 -> 47251649
        # 589836 -> 47251650
        # So the token might be at time 47251650,
        # but the server time is 47251600
        r = token.resync("705493", "589836",
                         options={"initTime": 47251650 * 30})
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
        serial = "sha25T"
        db_token = Token(serial, tokentype="hotp")
        db_token.save()
        token = TotpTokenClass(db_token)
        token.set_otpkey(binascii.hexlify("12345678901234567890"))
        token.set_hashlib("sha256")
        token.set_otplen(8)
        token.set_otp_count(0x00000000023523ED - 2)
        token.save()
        # get it from the database again
        # |  1111111111 |  2005-03-18  | 00000000023523ED | 67062674 | SHA256 |
        db_token = Token.query.filter_by(serial=serial).first()
        token = TotpTokenClass(db_token)
        r = token.check_otp("67062674", options={"initTime": 1111111111})
        self.assertTrue(r)

    def test_26_get_setting_type(self):
        r = TotpTokenClass.get_setting_type("totp.hashlib")
        self.assertEqual(r, "public")
        r = TotpTokenClass.get_setting_type("totp.blabla")
        self.assertEqual(r, "")

    def test_27_get_default_settings(self):
        params = {}
        logged_in_user = {"user": "hans",
                          "realm": "default",
                          "role": "user"}
        set_policy("pol1", scope=SCOPE.USER, action="totp_hashlib=sha256,"
                                                    "totp_timestep=60,"
                                                    "totp_otplen=8")
        pol = PolicyClass()
        p = TotpTokenClass.get_default_settings(params,
                                                logged_in_user=logged_in_user,
                                                policy_object=pol)
        self.assertEqual(p.get("otplen"), "8")
        self.assertEqual(p.get("totp.hashlib"), "sha256")
        self.assertEqual(p.get("timeStep"), "60")
        delete_policy("pol1")

