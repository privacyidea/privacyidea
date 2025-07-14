"""
This test file tests the lib.tokens.smstoken
"""
import json
import logging

from .base import MyTestCase, FakeFlaskG, FakeAudit
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.user import User
from privacyidea.lib.utils import is_true
from privacyidea.lib.token import init_token, remove_token, import_tokens, get_tokens
from privacyidea.lib.tokens.smstoken import SmsTokenClass, SMSACTION
from privacyidea.models import Token, Config
from privacyidea.lib.config import set_privacyidea_config, set_prepend_pin
from privacyidea.lib.policy import set_policy, SCOPE, PolicyClass
from privacyidea.lib import _
import mock
import responses
from testfixtures import log_capture

PWFILE = "tests/testdata/passwords"


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
        token.add_user(User(login="cornelius",
                            realm=self.realm1))

    def test_02_set_user(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        self.assertTrue(token.token.tokentype == "sms",
                        token.token.tokentype)
        self.assertTrue(token.type == "sms", token.type)

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

        self.assertEqual(token.get_user_id(), token.token.first_owner.user_id)

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

    def test_05_get_set_realms(self):
        set_realm(self.realm2)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        realms = token.get_realms()
        self.assertTrue(len(realms) == 1, realms)
        token.set_realms([self.realm1, self.realm2])
        realms = token.get_realms()
        self.assertTrue(len(realms) == 2, realms)

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
        self.assertFalse(token.token.active)
        token.enable()
        self.assertTrue(token.token.active)
        # we need to safe the token explicitly here to persist it to the db
        token.save()

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
        self.assertTrue(c[3]["attributes"]["state"], transactionid)

        # check for the challenges response
        r = token.check_challenge_response(passw=otp,
                                           options={"transaction_id": transactionid})
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
        self.assertTrue(c[3]["attributes"]["state"], transactionid)

        # check for the challenges response
        r = token.check_challenge_response(passw=otp,
                                           options={"transaction_id": transactionid})
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
        # The single quotes in the smstext "'Your <otp>'" is legacy and results in
        # the string without single quotes "Your <otp>".
        smstext_tests = {"'Your <otp>'": r"Your [0-9]{6}",
                         "Your <otp>": r"Your [0-9]{6}",
                         "{user} has the OTP: {otp}": r"Cornelius has the OTP: [0-9]{6}"}
        for pol_text, result_text in smstext_tests.items():
            # create a SMSTEXT policy:
            p = set_policy(name="smstext",
                           action="{0!s}={1!s}".format(SMSACTION.SMSTEXT, pol_text),
                           scope=SCOPE.AUTH)
            self.assertTrue(p > 0)

            g = FakeFlaskG()
            P = PolicyClass()
            g.audit_object = FakeAudit()
            g.policy_object = P
            options = {"g": g,
                       "user": User("cornelius", self.realm1)}

            responses.add(responses.POST,
                          self.SMSHttpUrl,
                          body=self.success_body)
            set_privacyidea_config("sms.providerConfig", self.SMSProviderConfig)
            db_token = Token.query.filter_by(serial=self.serial1).first()
            token = SmsTokenClass(db_token)
            c = token.create_challenge(options=options)
            self.assertTrue(c[0], c)
            display_message = c[1]
            self.assertEqual(display_message, _("Enter the OTP from the SMS:"))
            self.assertEqual(c[3].get("state"), None)

            smstext = token._get_sms_text(options)
            self.assertEqual(pol_text.strip("'"), smstext)
            r, message = token._send_sms(smstext, options)
            self.assertRegex(message, result_text)

        # Test AUTOSMS
        p = set_policy(name="autosms",
                       action=SMSACTION.SMSAUTO,
                       scope=SCOPE.AUTH)
        self.assertTrue(p > 0)

        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        g.audit_object = FakeAudit()
        options = {"g": g}

        r = token.check_otp(self.valid_otp_values[5 + len(smstext_tests)], options=options)
        self.assertTrue(r > 0, r)

    @ log_capture(level=logging.WARN)
    def test_21_failed_loading(self, capture):
        token = init_token({'type': 'sms', 'phone': self.phone1})
        transactionid = "123456098712"
        set_privacyidea_config("sms.providerConfig", "noJSON")
        set_privacyidea_config("sms.provider",
                               "privacyidea.lib.smsprovider."
                               "HttpSMSProvider.HttpSMSProviderWRONG")

        with mock.patch("logging.Logger.error") as mock_log:
            c = token.create_challenge(transactionid)
            self.assertFalse(c[0], c)
            self.assertTrue(c[1].startswith("The PIN was correct, but"), c[1])
            expected = "Failed to load SMSProvider: ImportError" \
                       "('privacyidea.lib.smsprovider.HttpSMSProvider has no attribute HttpSMSProviderWRONG'"
            mock_log.mock_called()
            mocked_str = mock_log
            self.assertTrue(mocked_str.startswith(expected), mocked_str)
        capture.clear()

        with mock.patch("logging.Logger.error") as mock_log:
            set_privacyidea_config("sms.provider",
                                   "privacyidea.lib.smsprovider."
                                   "HttpSMSProvider.HttpSMSProvider")
            c = token.create_challenge(transactionid)
            self.assertFalse(c[0], c)
            self.assertTrue(c[1].startswith("The PIN was correct, but"), c[1])
            expected = "Failed to load sms.providerConfig: " \
                       "JSONDecodeError('Expecting value: line 1 column 1 (char 0)')"
            mock_log.mock_called()
            mocked_str = mock_log
            self.assertTrue(mocked_str.startswith(expected), mocked_str)
        capture.clear()

        # test with the parameter exception=1
        self.assertRaises(Exception, token.create_challenge, transactionid, {"exception": "1"})

        remove_token(token.get_serial())

    def test_22_sms_token_export(self):
        # Set up the SMSTokenClass for testing
        smstoken = init_token(
            param={'serial': "SMS12345678", 'type': 'sms', 'otpkey': '12345', "phone": "+49123456789"})
        smstoken.set_description("this is a sms token export test")
        smstoken.add_tokeninfo("hashlib", "sha256")

        # Test that all expected keys are present in the exported dictionary
        exported_data = smstoken.export_token()

        expected_keys = ["serial", "type", "description", "otpkey", "issuer"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["phone", "hashlib", "tokenkind"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["tokeninfo"].keys()))

        # Test that the exported values match the token's data
        exported_data = smstoken.export_token()
        self.assertEqual(exported_data["serial"], "SMS12345678")
        self.assertEqual(exported_data["type"], "sms")
        self.assertEqual(exported_data["tokeninfo"]["phone"], "+49123456789")
        self.assertEqual(exported_data["description"], "this is a sms token export test")
        self.assertEqual(exported_data["tokeninfo"]["hashlib"], "sha256")
        self.assertEqual(exported_data["otpkey"], '12345')
        self.assertEqual(exported_data["tokeninfo"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")

        # Clean up
        remove_token(smstoken.token.serial)

    def test_23_sms_token_import(self):
        # Define the token data to be imported
        token_data = [{
            "serial": "SMS12345678",
            "type": "sms",
            "description": "this is a sms token import test",
            "otpkey": self.otpkey,
            "tokeninfo": {"phone": "+49123456789", "hashlib": "sha256", "tokenkind": "software"},
            "issuer": "privacyIDEA"
        }]

        # Import the token
        import_tokens(json.dumps(token_data))

        # Retrieve the imported token
        smstoken = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(smstoken.token.serial, token_data[0]["serial"])
        self.assertEqual(smstoken.type, token_data[0]["type"])
        self.assertEqual(smstoken.token.description, token_data[0]["description"])
        self.assertEqual(smstoken.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(smstoken.get_tokeninfo("phone"), token_data[0]["tokeninfo"]["phone"])
        self.assertEqual(smstoken.get_tokeninfo("hashlib"), token_data[0]["tokeninfo"]["hashlib"])
        self.assertEqual(smstoken.get_tokeninfo("tokenkind"), token_data[0]["tokeninfo"]["tokenkind"])

        # Check that token works
        self.assertEqual(0, smstoken.check_otp('875740'))

        # Clean up
        remove_token(smstoken.token.serial)

    def test_99_delete_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = SmsTokenClass(db_token)
        token.delete_token()

        db_token = Token.query.filter_by(serial=self.serial1).first()
        self.assertTrue(db_token is None, db_token)
