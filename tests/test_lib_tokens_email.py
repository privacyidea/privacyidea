"""
This test file tests the lib.tokens.smstoken
"""
PWFILE = "tests/testdata/passwords"
TEMPLATE_FILE = "tests/testdata/emailtemplate.html"

from .base import MyTestCase, FakeFlaskG
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import (User)
from privacyidea.lib.utils import is_true
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.tokens.emailtoken import EmailTokenClass, EMAILACTION
from privacyidea.models import (Token, Config, Challenge)
from privacyidea.lib.config import (set_privacyidea_config, set_prepend_pin,
                                    delete_privacyidea_config)
from privacyidea.lib.policy import set_policy, SCOPE, PolicyClass
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
import datetime
from dateutil.tz import tzlocal
import smtpmock
import mock


class EmailTokenTestCase(MyTestCase):
    """
    Test the Email Token
    """
    email = "pi_tester@privacyidea.org"
    otppin = "topsecret"
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    serial1 = "SE123456"
    serial2 = "SE000000"
    otpkey = "3132333435363738393031323334353637383930"

    success_body = "ID 12345"

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
        db_token = Token(self.serial1, tokentype="email")
        db_token.save()
        token = EmailTokenClass(db_token)
        token.update({"email": self.email})
        token.save()
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "email", token.token)
        self.assertTrue(token.type == "email", token.type)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PIEM", class_prefix)
        self.assertTrue(token.get_class_type() == "email", token)

        # create token with dynamic email
        db_token = Token(self.serial2, tokentype="email")
        db_token.save()
        token = EmailTokenClass(db_token)
        token.update({"dynamic_email": True})
        token.save()
        self.assertTrue(is_true(token.get_tokeninfo("dynamic_email")))
        self.assertTrue(token.token.serial == self.serial2, token)
        self.assertTrue(token.token.tokentype == "email", token.token)
        self.assertTrue(token.type == "email", token.type)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PIEM", class_prefix)
        self.assertTrue(token.get_class_type() == "email", token)
        token.set_user(User(login="cornelius",
                            realm=self.realm1))

    def test_02_set_user(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        self.assertTrue(token.token.tokentype == "email",
                        token.token.tokentype)
        self.assertTrue(token.type == "email", token.type)

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

    def test_04_base_methods(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)

        # get class info
        cli = token.get_class_info()
        self.assertTrue(cli.get("type") == "email", cli.get("type"))
        cli = token.get_class_info("type")
        self.assertTrue(cli == "email", cli)

    def test_06_set_pin(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        token.set_pin("hallo")
        (ph1, pseed) = token.get_pin_hash_seed()
        # check the database
        token.set_pin("blubber")
        ph2 = token.token.pin_hash
        self.assertTrue(ph1 != ph2)
        token.set_pin_hash_seed(ph1, pseed)

    def test_07_enable(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        token.enable(False)
        self.assertTrue(token.token.active is False)
        token.enable()
        self.assertTrue(token.token.active)

    def test_05_get_set_realms(self):
        set_realm(self.realm2)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        realms = token.get_realms()
        self.assertTrue(len(realms) == 1, realms)
        token.set_realms([self.realm1, self.realm2])
        realms = token.get_realms()
        self.assertTrue(len(realms) == 2, realms)

    def test_99_delete_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        token.delete_token()

        db_token = Token.query.filter_by(serial=self.serial1).first()
        self.assertTrue(db_token is None, db_token)

    def test_08_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        token.set_hashlib("sha1")
        ti = token.get_tokeninfo()
        self.assertTrue("hashlib" in ti, ti)

    def test_09_failcount(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        start = token.token.failcount
        end = token.inc_failcount()
        self.assertTrue(end == start + 1, (end, start))

    def test_10_get_hashlib(self):
        # check if functions are returned
        for hl in ["sha1", "md5", "sha256", "sha512",
                   "sha224", "sha384", "", None]:
            self.assertTrue(hasattr(EmailTokenClass.get_hashlib(hl),
                                    '__call__'),
                            EmailTokenClass.get_hashlib(hl))

    def test_11_tokeninfo(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
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
        token = EmailTokenClass(db_token)

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
        token = EmailTokenClass(db_token)
        token.update({"otpkey": self.otpkey,
                      "pin": "test",
                      "otplen": 6,
                      "email": self.email})
        # OTP does not exist
        self.assertTrue(token.check_otp_exist("222333") == -1)
        # OTP does exist
        res = token.check_otp_exist("969429")
        self.assertTrue(res == 3, res)

    def test_14_split_pin_pass(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)

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
        token = EmailTokenClass(db_token)
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
        token = EmailTokenClass(db_token)
        token.set_pin(self.otppin)

        r = token.is_challenge_request(self.otppin)
        self.assertTrue(r)

    @smtpmock.activate
    def test_18_challenge_request(self):
        smtpmock.setdata(response={"pi_tester@privacyidea.org": (200, 'OK')})
        transactionid = "123456098712"
        # send the email with the old configuration
        set_privacyidea_config("email.mailserver", "localhost")
        set_privacyidea_config("email.username", "user")
        set_privacyidea_config("email.username", "password")
        set_privacyidea_config("email.tls", True)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)
        c = token.create_challenge(transactionid)
        self.assertTrue(c[0], c)
        otp = c[1]
        self.assertTrue(c[3].get("state"), transactionid)

        # check for the challenges response
        r = token.check_challenge_response(passw=otp)
        self.assertTrue(r, r)

    @smtpmock.activate
    def test_18a_challenge_request_dynamic(self):
        smtpmock.setdata(response={"pi_tester@privacyidea.org": (200, 'OK')})
        transactionid = "123456098712"
        # send the email with the old configuration
        set_privacyidea_config("email.mailserver", "localhost")
        set_privacyidea_config("email.username", "user")
        set_privacyidea_config("email.username", "password")
        set_privacyidea_config("email.tls", True)
        db_token = Token.query.filter_by(serial=self.serial2).first()
        token = EmailTokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)
        c = token.create_challenge(transactionid)
        self.assertTrue(c[0], c)
        otp = c[1]
        self.assertTrue(c[3].get("state"), transactionid)

        # check for the challenges response
        r = token.check_challenge_response(passw=otp)
        self.assertTrue(r, r)

    def test_18b_challenge_request_dynamic_multivalue(self):
        db_token = Token.query.filter_by(serial=self.serial2).first()
        token = EmailTokenClass(db_token)
        # if the email is a multi-value attribute, the first address should be chosen
        new_user_info = token.user.info.copy()
        new_user_info['email'] = ['email1@example.com', 'email2@example.com']
        with mock.patch('privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.getUserInfo') as mock_user_info:
            mock_user_info.return_value = new_user_info
            self.assertEqual(token._email_address, 'email1@example.com')


    @smtpmock.activate
    def test_19_emailtext(self):
        # create a EMAILTEXT policy:
        p = set_policy(name="emailtext",
                       action="{0!s}={1!s}".format(EMAILACTION.EMAILTEXT, "'Your <otp>'"),
                       scope=SCOPE.AUTH)
        self.assertTrue(p > 0)

        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}
        smtpmock.setdata(response={"pi_tester@privacyidea.org": (200, "OK")})
        transactionid = "123456098713"
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        c = token.create_challenge(transactionid, options=options)
        self.assertTrue(c[0], c)
        display_message = c[1]
        self.assertTrue(c[3].get("state"), transactionid)
        self.assertEqual(display_message, "Enter the OTP from the Email:")
        _, mimetype = token._get_email_text_or_subject(options, EMAILACTION.EMAILTEXT)
        self.assertEqual(mimetype, "plain")

        # Test AUTOEMAIL
        p = set_policy(name="autoemail",
                       action=EMAILACTION.EMAILAUTO,
                       scope=SCOPE.AUTH)
        self.assertTrue(p > 0)

        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        r = token.check_otp("287922", options=options)
        self.assertTrue(r > 0, r)

        # create a EMAILTEXT policy with template
        p = set_policy(name="emailtext",
                       action="{0!s}=file:{1!s}".format(EMAILACTION.EMAILTEXT, TEMPLATE_FILE),
                       scope=SCOPE.AUTH)
        self.assertTrue(p > 0)

        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}
        smtpmock.setdata(response={"pi_tester@privacyidea.org": (200, "OK")})
        transactionid = "123456098714"
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        email_text, mimetype = token._get_email_text_or_subject(options, EMAILACTION.EMAILTEXT)
        self.assertTrue("<p>Hello,</p>" in email_text)
        self.assertEqual(mimetype, "html")
        c = token.create_challenge(transactionid, options=options)
        self.assertTrue(c[0], c)
        display_message = c[1]
        self.assertTrue(c[3].get("state"), transactionid)
        self.assertEqual(display_message, "Enter the OTP from the Email:")

    @smtpmock.activate
    def test_20_sending_email_exception(self):
        smtpmock.setdata(exception=True)
        transactionid = "123456098714"
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        c = token.create_challenge(transactionid)
        self.assertFalse(c[0])
        self.assertTrue("The PIN was correct, but the EMail could not "
                        "be sent" in c[1])

    @smtpmock.activate
    def test_21_test_email_config(self):
        from privacyidea.lib.tokens.emailtoken import TEST_SUCCESSFUL
        smtpmock.setdata(response={"user@example.com": (200, "OK")})
        r = EmailTokenClass.test_config({"email.mailserver": "mail.example.com",
                                         "email.mailfrom": "pi@example.com",
                                         "email.recipient": "user@example.com"})
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], TEST_SUCCESSFUL)

    @smtpmock.activate
    def test_22_new_email_config(self):
        smtpmock.setdata(response={"pi_tester@privacyidea.org": (200, 'OK')})
        transactionid = "123456098717"
        # send the email with the new configuration
        r = add_smtpserver(identifier="myServer", server="1.2.3.4")
        set_privacyidea_config("email.identifier", "myServer")
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = EmailTokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)
        c = token.create_challenge(transactionid)
        self.assertTrue(c[0], c)
        otp = c[1]
        self.assertTrue(c[3].get("state"), transactionid)

        # check for the challenges response
        r = token.check_challenge_response(passw=otp)
        self.assertTrue(r, r)
        delete_smtpserver("myServer")
        delete_privacyidea_config("email.identifier")
