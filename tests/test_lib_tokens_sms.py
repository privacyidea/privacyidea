"""
This test file tests the lib.tokens.smstoken
"""
PWFILE = "tests/testdata/passwords"

from .base import MyTestCase, FakeFlaskG
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import (User)
from privacyidea.lib.utils import is_true
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.tokens.smstoken import SmsTokenClass, SMSACTION
from privacyidea.models import (Token, Config, Challenge)
from privacyidea.lib.config import (set_privacyidea_config, set_prepend_pin)
from privacyidea.lib.policy import set_policy, SCOPE, PolicyClass
import datetime
import mock
import responses


class SMSTokenTestCase(MyTestCase):
    """
    Test the token on the database level
    """
    phone1 = "+49 123456789"
    otppin = "topsecret"
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    serial1 = "SE123456"
    serial2 = "SE222222"
    otpkey = "3132333435363738393031323334353637383930"

    SMSHttpUrl = "http://smsgateway.com/sms_send_api.cgi"
    SMSProviderConfig = '''{"URL": "http://smsgateway.com/sms_send_api.cgi",
                   "PARAMETER": {"from": "0170111111",
                                 "password": "yoursecret",
                                 "sender": "name",
                                 "account": "company_ltd"},
                   "SMS_TEXT_KEY": "text",
                   "SMS_PHONENUMBER_KEY": "destination",
                   "HTTP_Method": "POST",
                   "PROXY": "http://username:password@your-proxy:8080",
                   "RETURN_SUCCESS": "ID"
    }'''
    success_body = "ID 12345"


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
        db_token = Token(self.serial1, tokentype="sms")
        db_token.save()
        token = SmsTokenClass(db_token)
        token.update({"phone": self.phone1})
        token.save()
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "sms", token.token)
        self.assertTrue(token.type == "sms", token.type)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PISM", class_prefix)
        self.assertTrue(token.get_class_type() == "sms", token)

        db_token = Token(self.serial2, tokentype="sms")
        db_token.save()
        token = SmsTokenClass(db_token)
        token.update({"dynamic_phone": True})
        token.save()
        self.assertTrue(token.token.serial == self.serial2, token)
        self.assertTrue(token.token.tokentype == "sms", token.token)
        self.assertTrue(is_true(token.get_tokeninfo("dynamic_phone")))
        self.assertTrue(token.type == "sms", token.type)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PISM", class_prefix)
        self.assertTrue(token.get_class_type() == "sms", token)
        token.set_user(User(login="cornelius",
                            realm=self.realm1))

    def test_02_set_user(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        self.assertTrue(token.token.tokentype == "sms",
                        token.token.tokentype)
        self.assertTrue(token.type == "sms", token.type)

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
        token = SmsTokenClass(db_token)
        token.token.failcount = 10
        token.reset()
        self.assertTrue(token.token.failcount == 0,
                        token.token.failcount)

    def test_04_base_methods(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)

        # get class info
        cli = token.get_class_info()
        self.assertTrue(cli.get("type") == "sms", cli.get("type"))
        cli = token.get_class_info("type")
        self.assertTrue(cli == "sms", cli)

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
        self.assertTrue(token.get_tokentype() == "sms",
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
        token = SmsTokenClass(db_token)
        token.set_pin("hallo")
        (ph1, pseed) = token.get_pin_hash_seed()
        # check the database
        token.set_pin("blubber")
        ph2 = token.token.pin_hash
        self.assertTrue(ph1 != ph2)
        token.set_pin_hash_seed(ph1, pseed)

    def test_07_enable(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        token.enable(False)
        self.assertTrue(token.token.active is False)
        token.enable()
        self.assertTrue(token.token.active)

    def test_05_get_set_realms(self):
        set_realm(self.realm2)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        realms = token.get_realms()
        self.assertTrue(len(realms) == 1, realms)
        token.set_realms([self.realm1, self.realm2])
        realms = token.get_realms()
        self.assertTrue(len(realms) == 2, realms)

    def test_99_delete_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        token.delete_token()

        db_token = Token.query.filter_by(serial=self.serial1).first()
        self.assertTrue(db_token is None, db_token)

    def test_08_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        token.set_hashlib("sha1")
        ti = token.get_tokeninfo()
        self.assertTrue("hashlib" in ti, ti)

    def test_09_failcount(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        start = token.token.failcount
        end = token.inc_failcount()
        self.assertTrue(end == start + 1, (end, start))

    def test_10_get_hashlib(self):
        # check if functions are returned
        for hl in ["sha1", "md5", "sha256", "sha512",
                   "sha224", "sha384", "", None]:
            self.assertTrue(hasattr(SmsTokenClass.get_hashlib(hl),
                                    '__call__'),
                            SmsTokenClass.get_hashlib(hl))

    def test_11_tokeninfo(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
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
        token = SmsTokenClass(db_token)

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
        token = SmsTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "pin": "test",
                      "otplen": 6,
                      "phone": self.phone1})
        # OTP does not exist
        self.assertTrue(token.check_otp_exist("222333") == -1)
        # OTP does exist
        res = token.check_otp_exist("969429")
        self.assertTrue(res == 3, res)

    def test_14_split_pin_pass(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)

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
        token = SmsTokenClass(db_token)
        # test the encrypted pin
        token.set_pin("encrypted", encrypt=True)
        self.assertTrue(token.check_pin("encrypted"))
        self.assertFalse(token.check_pin("wrong pin"))

        # test the hashed pin
        token.set_pin("test")
        self.assertTrue(token.check_pin("test"))
        self.assertFalse(token.check_pin("wrong pin"))

    def test_17_challenge_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        token.set_pin(self.otppin)

        r = token.is_challenge_request(self.otppin)
        self.assertTrue(r)

    @responses.activate
    def test_18_challenge_request(self):
        responses.add(responses.POST,
                      self.SMSHttpUrl,
                      body=self.success_body)
        transactionid = "123456098712"
        set_privacyidea_config("sms.providerConfig", self.SMSProviderConfig)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)
        c = token.create_challenge(transactionid)
        self.assertTrue(c[0], c)
        otp = c[1]
        self.assertTrue(c[3].get("state"), transactionid)

        # check for the challenges response
        r = token.check_challenge_response(passw=otp,
                                           options={"transaction_id":
                                                        transactionid})
        self.assertTrue(r, r)

    @responses.activate
    def test_18a_challenge_request_dynamic(self):
        # Send a challenge request for an SMS token with a dynamic phone number
        responses.add(responses.POST,
                      self.SMSHttpUrl,
                      body=self.success_body)
        transactionid = "123456098712"
        set_privacyidea_config("sms.providerConfig", self.SMSProviderConfig)
        db_token = Token.query.filter_by(serial=self.serial2).first()
        token = SmsTokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)
        c = token.create_challenge(transactionid)
        self.assertTrue(c[0], c)
        otp = c[1]
        self.assertTrue(c[3].get("state"), transactionid)

        # check for the challenges response
        r = token.check_challenge_response(passw=otp,
                                           options={"transaction_id":
                                                        transactionid})
        self.assertTrue(r, r)

    @responses.activate
    def test_18b_challenge_request_dynamic_multivalue(self):
        responses.add(responses.POST,
                      self.SMSHttpUrl,
                      body=self.success_body)
        transactionid = "123456098712"
        set_privacyidea_config("sms.providerConfig", self.SMSProviderConfig)
        db_token = Token.query.filter_by(serial=self.serial2).first()
        token = SmsTokenClass(db_token)
        # if the email is a multi-value attribute, the first address should be chosen
        new_user_info = token.user.info.copy()
        new_user_info['mobile'] = ['1234', '5678']
        with mock.patch('privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.getUserInfo') as mock_user_info:
            mock_user_info.return_value = new_user_info
            c = token.create_challenge(transactionid)
            self.assertTrue(c[0], c)
            self.assertIn('destination=1234', responses.calls[0].request.body)
            self.assertNotIn('destination=5678', responses.calls[0].request.body)

    @responses.activate
    def test_19_smstext(self):
        # create a SMSTEXT policy:
        p = set_policy(name="smstext",
                       action="{0!s}={1!s}".format(SMSACTION.SMSTEXT, "'Your <otp>'"),
                       scope=SCOPE.AUTH)
        self.assertTrue(p > 0)

        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        responses.add(responses.POST,
                      self.SMSHttpUrl,
                      body=self.success_body)
        set_privacyidea_config("sms.providerConfig", self.SMSProviderConfig)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        c = token.create_challenge(options=options)
        self.assertTrue(c[0], c)
        display_message = c[1]
        self.assertEqual(display_message, "Enter the OTP from the SMS:")
        self.assertEqual(c[3].get("state"), None)

        # check for the challenges response
        # r = token.check_challenge_response(passw="287922")
        # self.assertTrue(r, r)

        # Test AUTOSMS
        p = set_policy(name="autosms",
                       action=SMSACTION.SMSAUTO,
                       scope=SCOPE.AUTH)
        self.assertTrue(p > 0)

        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        r = token.check_otp("287922", options=options)
        self.assertTrue(r > 0, r)

    def test_21_failed_loading(self):
        transactionid = "123456098712"
        set_privacyidea_config("sms.providerConfig", "noJSON")
        set_privacyidea_config("sms.provider",
                               "privacyidea.lib.smsprovider."
                               "HttpSMSProvider.HttpSMSProviderWRONG")
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)

        c = token.create_challenge(transactionid)
        self.assertFalse(c[0], c)
        self.assertTrue("The PIN was correct, but" in c[1], c[1])

        set_privacyidea_config("sms.provider",
                               "privacyidea.lib.smsprovider."
                               "HttpSMSProvider.HttpSMSProvider")
        c = token.create_challenge(transactionid)
        self.assertFalse(c[0], c)
        self.assertTrue("Failed to load sms.providerConfig" in c[1], c[1])
