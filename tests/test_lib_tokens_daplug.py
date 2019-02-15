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
from privacyidea.lib.tokens.daplugtoken import (DaplugTokenClass, _digi2daplug)
from privacyidea.models import (Token,
                                 Config,
                                 Challenge)
from privacyidea.lib.config import (set_privacyidea_config, set_prepend_pin)
import datetime
from dateutil.tz import tzlocal


class DaplugTokenTestCase(MyTestCase):
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
        db_token = Token(self.serial1, tokentype="daplug")
        db_token.save()
        token = DaplugTokenClass(db_token)
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "daplug",
                        token.token.tokentype)
        self.assertTrue(token.type == "daplug", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "DPLG", class_prefix)
        self.assertTrue(token.get_class_type() == "daplug", token)

    def test_02_set_user(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        self.assertTrue(token.token.tokentype == "daplug",
                        token.token.tokentype)
        self.assertTrue(token.type == "daplug", token.type)

        token.add_user(User(login="cornelius",
                            realm=self.realm1))
        self.assertEqual(token.token.owners.first().resolver, self.resolvername1)
        self.assertEqual(token.token.owners.first().user_id, "1000")

        user_object = token.user
        self.assertTrue(user_object.login == "cornelius",
                        user_object)
        self.assertTrue(user_object.resolver == self.resolvername1,
                        user_object)

    def test_03_reset_failcounter(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        token.token.failcount = 10
        token.reset()
        self.assertTrue(token.token.failcount == 0,
                        token.token.failcount)

    def test_04_base_methods(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        self.assertTrue(token.check_otp(_digi2daplug("123456"), 1, 10) == -1)

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

        token.resync(_digi2daplug("1234"), _digi2daplug("3456"))

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

        self.assertEqual(token.get_user_id(), token.token.owners.first().user_id)

        self.assertTrue(token.get_serial() == "SE123456", token.token.serial)
        self.assertTrue(token.get_tokentype() == "daplug",
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
        token = DaplugTokenClass(db_token)
        token.set_pin("hallo")
        (ph1, pseed) = token.get_pin_hash_seed()
        # check the database
        token.set_pin("blubber")
        ph2 = token.token.pin_hash
        self.assertTrue(ph1 != ph2)
        token.set_pin_hash_seed(ph1, pseed)

    def test_07_enable(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        token.enable(False)
        self.assertTrue(token.token.active is False)
        token.enable()
        self.assertTrue(token.token.active)

    def test_05_get_set_realms(self):
        set_realm(self.realm2)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        realms = token.get_realms()
        self.assertTrue(len(realms) == 1, realms)
        token.set_realms([self.realm1, self.realm2])
        realms = token.get_realms()
        self.assertTrue(len(realms) == 2, realms)

    def test_99_delete_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        token.delete_token()

        db_token = Token.query.filter_by(serial=self.serial1).first()
        self.assertTrue(db_token is None, db_token)

    def test_08_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        token.set_hashlib("sha1")
        ti = token.get_tokeninfo()
        self.assertTrue("hashlib" in ti, ti)

    def test_09_failcount(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        start = token.token.failcount
        end = token.inc_failcount()
        self.assertTrue(end == start + 1, (end, start))

    def test_10_get_hashlib(self):
        # check if functions are returned
        for hl in ["sha1", "md5", "sha256", "sha512",
                   "sha224", "sha384", "", None]:
            self.assertTrue(hasattr(DaplugTokenClass.get_hashlib(hl),
                                    '__call__'),
                            DaplugTokenClass.get_hashlib(hl))

    def test_11_tokeninfo(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
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
        self.assertEqual("2014-12-30T16:00+0200", end)
        self.assertRaises(Exception,
                          token.set_validity_period_end, "wrong date")
        # handle validity start date
        token.set_validity_period_start("2013-12-30T16:00+0200")
        start = token.get_validity_period_start()
        self.assertEqual("2013-12-30T16:00+0200", start)
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
        token = DaplugTokenClass(db_token)

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
        token = DaplugTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "pin": "test",
                      "otplen": 6})
        # OTP does not exist
        self.assertEquals(token.check_otp_exist(_digi2daplug("222333")), -1)
        # OTP does exist
        res = token.check_otp_exist(_digi2daplug("969429"))
        self.assertEquals(res, 3, res)

    def test_14_split_pin_pass(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)

        token.token.otplen = 6
        # postpend pin
        set_prepend_pin(False)
        _res, pin, value = token.split_pin_pass(_digi2daplug("222333")+"test")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(value == _digi2daplug("222333"), value)
        # prepend pin
        set_prepend_pin(True)
        _res, pin, value = token.split_pin_pass("test"+_digi2daplug("222333"))
        self.assertTrue(pin == "test", pin)
        self.assertTrue(value == _digi2daplug("222333"), value)

    def test_15_check_pin(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
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
        token = DaplugTokenClass(db_token)
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
        token = DaplugTokenClass(db_token)
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
        token = DaplugTokenClass(db_token)
        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test"+_digi2daplug("123456"))
        self.assertFalse(resp, resp)
        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test"+_digi2daplug("123456"),
                                            options={"transaction_id":
                                                         "123456789"})
        self.assertTrue(resp, resp)

        # test if challenge is valid
        C = Challenge("S123455", transaction_id="tid", challenge="Who are you?")
        C.save()

    def test_19_pin_otp_functions(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        db_token.set_pin("test")
        token = DaplugTokenClass(db_token)
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
        res, pin, otp = token.split_pin_pass("test"+_digi2daplug("123456"))
        self.assertTrue(pin == "test", pin)
        self.assertTrue(otp == _digi2daplug("123456"), otp)
        self.assertTrue(token.check_pin(pin), pin)
        check = token.check_otp(_digi2daplug("755224"), counter=0, window=10)
        self.assertTrue(check == 0, check)
        self.assertTrue(token.check_otp(_digi2daplug("287082"), counter=1,
                                        window=10) == 1)
        # The 6th counter:
        self.assertTrue(token.check_otp(_digi2daplug("287922"), counter=2,
                                        window=10) == 6)
        # The tokenclass itself saves the counter to the database
        self.assertTrue(token.token.count == 7, token.token.count)

        # successful authentication
        res = token.authenticate("test"+_digi2daplug("399871"))
        # This is the OTP value of the counter=8
        self.assertTrue(res == (True, 8, None), res)

        token.set_otp_count(0)
        # get the OTP value for counter 0
        res = token.get_otp()
        self.assertTrue(res[0] == 1, res)
        self.assertTrue(res[1] == -1, res)
        self.assertTrue(res[2] == _digi2daplug("755224"), res)
        res = token.get_multi_otp()
        self.assertTrue(res[0] is False, res)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.token.count = 0
        res = token.get_multi_otp(count=5)
        self.assertTrue(res[0], res)
        self.assertTrue(res[1] == "OK", res)
        self.assertTrue(res[2].get("otp").get(1) == _digi2daplug("287082"),
                        res[2])
        self.assertTrue(res[2].get("type") == "daplug", res)

        # do some failing otp checks
        token.token.otplen = "invalid otp counter"
        self.assertRaises(Exception, token.check_otp, _digi2daplug("123456"))
        token.token.otplen = 0

    def test_20_check_challenge_response(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        db_token.set_pin("test")
        token = DaplugTokenClass(db_token)
        r = token.check_challenge_response(user=None,
                                           passw=_digi2daplug("123454"))
        # check empty challenges
        self.assertTrue(r == -1, r)

        # create a challenge and match the transaction_id
        c = Challenge(self.serial1, transaction_id="mytransaction",
                      challenge="Blah, what now?")
        # save challenge to the database
        c.save()
        r = token.check_challenge_response(user=None,
                                           passw=_digi2daplug("123454"),
                                           options={"state": "mytransaction"})
        # The challenge matches, but the OTP does not match!
        self.assertTrue(r == -1, r)

    def test_21_get_class_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        ti = token.get_class_info()
        self.assertTrue(ti.get("type") == "daplug", ti)
        ti = token.get_class_info("type")
        self.assertTrue(ti == "daplug", ti)

    def test_22_autosync(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        set_privacyidea_config("AutoResync", True)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.token.count = 0
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8, is out of sync
        r = token.check_otp(anOtpVal=_digi2daplug("399871"))
        self.assertTrue(r == -1, r)
        # counter = 9, will be autosynced.
        r = token.check_otp(anOtpVal=_digi2daplug("520489"))
        self.assertTrue(r == 9, r)

        # Autosync with a gap in the next otp value will fail
        token.token.count = 0
        # Just try some bullshit config value
        set_privacyidea_config("AutoResyncTimeout", "totally not a number")
        # counter = 7, is out of sync
        r = token.check_otp(anOtpVal=_digi2daplug("162583"))
        self.assertTrue(r == -1, r)
        # counter = 9, will NOT _autosync
        r = token.check_otp(anOtpVal=_digi2daplug("520489"))
        self.assertTrue(r == -1, r)

        # Autosync fails, if dueDate is over
        token.token.count = 0
        set_privacyidea_config("AutoResyncTimeout", 0)
        # counter = 8, is out of sync
        r = token.check_otp(anOtpVal=_digi2daplug("399871"))
        self.assertTrue(r == -1, r)
        # counter = 9, is the next value, but duedate is over.
        r = token.check_otp(anOtpVal=_digi2daplug("520489"))
        self.assertTrue(r == -1, r)

        # No _autosync
        set_privacyidea_config("AutoResync", False)
        token.token.count = 0
        # counter = 8, is out of sync
        r = token.check_otp(anOtpVal=_digi2daplug("399871"))
        self.assertTrue(r == -1, r)
        # counter = 9, will not be autosynced
        r = token.check_otp(anOtpVal=_digi2daplug("520489"))
        self.assertTrue(r == -1, r)

    def test_23_resync(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.token.count = 0
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8: 399871
        # counter = 9: 520489
        # Successful resync
        r = token.resync(_digi2daplug("399871"), _digi2daplug("520489"))
        self.assertTrue(r is True, r)
        # resync fails
        token.token.count = 0
        self.assertFalse(token.resync(_digi2daplug("399871"), _digi2daplug(
            "123456")))
        # resync fails, the two correct OTP values are outside of the sync
        # window
        token.token.count = 0
        token.set_sync_window(5)
        self.assertFalse(token.resync(_digi2daplug("399871"), _digi2daplug(
            "520489")))

    def test_24_challenges(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = DaplugTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "otplen": 6})
        token.set_pin("test")
        token.token.count = 0
        token.set_sync_window(10)
        token.set_count_window(5)
        self.assertTrue(token.is_challenge_request("test"))
