"""
This test file tests the applications definitions standalone
lib/applications/*
"""
from privacyidea.lib.error import ParameterError
from .base import MyTestCase
from privacyidea.lib.applications import MachineApplicationBase
from privacyidea.lib.applications.ssh import (MachineApplication as
                                              SSHApplication)
from privacyidea.lib.applications.luks import (MachineApplication as
                                               LUKSApplication)
from privacyidea.lib.applications.offline import (MachineApplication as
                                                  OfflineApplication,
                                                  REFILLTOKEN_LENGTH)
from privacyidea.lib.applications import (get_auth_item,
                                          is_application_allow_bulk_call,
                                          get_application_types)
from privacyidea.lib.token import init_token, get_tokens
from privacyidea.lib.user import User
import passlib.hash
import mock


SSHKEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDO1rx377" \
         "cmSSs/89j/0u5aEiXa7bYArHn7zFNCBaVnDUiK9JDNkpWB" \
         "j2ucbmOpDKWzH0Vl3in21E8BaRlq9BobASG0qlEqlnwrYwlH" \
         "+vcYp6td4QBoh3sOelzhyrJFug9dnfe8o70r3IL4HIbdQOdh1" \
         "b8Ogi7aL01V/eVE9RgGfTNHUzuYRMUL3si4dtqbCsSjFZ6dN1mm" \
         "Vhos9cSphPr7pQEbq8xW0uxzOGrFDY9g1NSOleA8bOjsCT9k+3X" \
         "4R700iVGvpzWkKopcWrzXJDIa3yxylAMOM0c3uO9U3NLfRsucvc" \
         "Q5Cs8S6ctM308cua3t5WaBOsr3RyoXs+cHIPIkXnJHg03HsnWON" \
         "aGxl8VPymC9s3P0zVwm2jMFxJD9WbCqep7Dwc5unxLOSKidKrnNflQ" \
         "iMyiIv+5dY5lhc0YTJdktC2Scse64ac2E7ldjG3bJuKSIWAz8Sd" \
         "1km4ZJWWIx8NlpC9AfbHcgMyFUDniV1EtFIaSQLPspIkthzIMq" \
         "PTpKblzdRZP37mPu/FpwfYG4S+F34dCmJ4BipslsVcqgCFJQHo" \
         "AYAJc4NDq5IRDQqXH2KybHpSLATnbSY7zjVD+evJeU994yTa" \
         "XTFi5hBmd0aWTC+ph79mmEtu3dokA2YbLa7uWkAIXvX/HHauGLM" \
         "TyCOpYi1BxN47c/kccxyNgjPw== user@example.com"
OTPKEY = "3132333435363738393031323334353637383930"


class SSHApplicationTestCase(MyTestCase):

    def test_01_get_options(self):
        # Can run as class
        options = SSHApplication.get_options()
        self.assertIn("user", options)
        self.assertIn("service_id", options)
        self.assertEqual("str", options.get("user").get("type"))
        self.assertEqual("str", options.get("service_id").get("type"))

    def test_02_get_auth_item(self):
        serial = "ssh1"
        # create realm
        self.setUp_user_realms()
        user = User("cornelius", realm=self.realm1)
        # create ssh token
        init_token({"serial": serial, "type": "sshkey", "sshkey": SSHKEY},
                   user=user)

        auth_item = SSHApplication.get_authentication_item("sshkey", serial)
        self.assertEqual(auth_item.get("sshkey"), SSHKEY)
        self.assertEqual(auth_item.get("username"), "cornelius")

        # Get with no matching user
        with mock.patch("logging.Logger.debug") as mock_log:
            auth_item = SSHApplication.get_authentication_item("sshkey", serial, filter_param={"user": "Idefix"})
            self.assertFalse(auth_item)
            mock_log.assert_called_with('The requested user Idefix does '
                                        'not match the user option (Idefix) of the SSH application.')

    def test_03_get_auth_item_unsupported(self):
        # unsupported token type
        auth_item = SSHApplication.get_authentication_item("unsupported", "s")
        self.assertEqual(auth_item, {})


class LUKSApplicationTestCase(MyTestCase):

    def test_01_get_options(self):
        # Can run as class
        options = LUKSApplication.get_options()
        self.assertIn("slot", options)
        self.assertIn("partition", options)
        self.assertEqual("int", options.get("slot").get("type"))
        self.assertEqual("str", options.get("partition").get("type"))

    def test_02_get_auth_item(self):
        serial = "UBOM12345"
        # create realm
        self.setUp_user_realms()
        user = User("cornelius", realm=self.realm1)
        # create ssh token
        init_token({"serial": serial, "type": "totp", "otpkey": OTPKEY},
                   user=user)

        auth_item = LUKSApplication.get_authentication_item("totp", serial)
        self.assertEqual(len(auth_item.get("challenge")), 64, auth_item)
        self.assertIsInstance(auth_item.get('challenge'), str, auth_item)
        self.assertEqual(len(auth_item.get("response")), 40, auth_item)

        auth_item = LUKSApplication.get_authentication_item("totp", serial,
                                                            challenge="123456")
        self.assertEqual(auth_item.get("challenge"), "123456")
        self.assertEqual(auth_item.get("response"),
                         "76d624a5fdf8d84f3d19e781f0313e48c1e69165")

    def test_03_get_auth_item_unsupported(self):
        # unsupported token type
        auth_item = LUKSApplication.get_authentication_item("unsupported", "s")
        self.assertEqual(auth_item, {})


class OfflineApplicationTestCase(MyTestCase):

    def test_01_get_options(self):
        # Can run as class
        options = OfflineApplication.get_options()
        self.assertIn("count", options)
        self.assertIn("rounds", options)
        self.assertEqual("str", options.get("count").get("type"))
        self.assertEqual("str", options.get("rounds").get("type"))

    def test_02_get_auth_item(self):
        serial = "OATH1"
        # create realm
        self.setUp_user_realms()
        user = User("cornelius", realm=self.realm1)
        # create ssh token
        init_token({"serial": serial, "type": "hotp", "otpkey": OTPKEY},
                   user=user)
        # authenticate online initially
        tok = get_tokens(serial=serial)[0]
        res = tok.check_otp("359152") # count = 2
        self.assertEqual(res, 2)
        # check intermediate counter value
        self.assertEqual(tok.token.count, 3)

        auth_item = OfflineApplication.get_authentication_item("hotp", serial)
        refilltoken = auth_item.get("refilltoken")
        self.assertEqual(len(refilltoken), REFILLTOKEN_LENGTH * 2)
        self.assertTrue(passlib.hash.\
                        pbkdf2_sha512.verify("969429", # count = 3
                                             auth_item.get("response").get(3)))
        self.assertTrue(passlib.hash.\
                        pbkdf2_sha512.verify("399871", # count = 8
                                             auth_item.get("response").get(8)))
        # The token now contains the refill token information:
        self.assertEqual(refilltoken, tok.get_tokeninfo("refilltoken"))

        # After calling auth_item the token counter should be increased
        # 3, because we used the otp value with count = 2 initially
        # 100, because we obtained 100 offline OTPs
        self.assertEqual(tok.token.count, 3 + 100)
        # Assert that we cannot authenticate with the last offline OTP we got
        self.assertEqual(len(auth_item.get("response")), 100)
        self.assertTrue(passlib.hash.\
                        pbkdf2_sha512.verify("629694", # count = 102
                                             auth_item.get("response").get(102)))
        res = tok.check_otp("629694") # count = 102
        self.assertEqual(res, -1)
        res = tok.check_otp("378717")  # count = 103
        self.assertEqual(res, 103)
        # check illegal API usage
        self.assertRaises(ParameterError,
                          OfflineApplication.get_offline_otps, tok, 'foo', -1)
        self.assertEqual(OfflineApplication.get_offline_otps(tok, 'foo', 0), {})

    def test_03_get_auth_item_unsupported(self):
        # unsupported token type
        auth_item = OfflineApplication.get_authentication_item("unsupported",
                                                               "s")
        self.assertEqual(auth_item, {})


class BaseApplicationTestCase(MyTestCase):

    def test_01_create_base_application(self):
        base_app = MachineApplicationBase()
        self.assertEqual(base_app.get_name(), "base")
        self.assertEqual(base_app.get_authentication_item("hotp", "serial"),
                         "nothing")
        options = base_app.get_options()
        self.assertEqual(options["optionA"].get("type"), "bool")
        self.assertTrue(options["optionA"].get("required"))

    def test_02_get_auth_item(self):
        auth_item = get_auth_item("base", "hotp", "serial")
        self.assertEqual(auth_item, "nothing")

    def test_03_allow_bulk_call(self):
        bulk = is_application_allow_bulk_call(
            "privacyidea.lib.applications.base")
        self.assertFalse(bulk)

    def test_04_get_application_types(self):
        apps = get_application_types()
        self.assertTrue("luks" in apps)
        self.assertTrue("ssh" in apps)
        self.assertIn("service_id", apps["ssh"]["options"])
        self.assertIn("user", apps["ssh"]["options"])
        self.assertIn("slot", apps["luks"]["options"])
        self.assertIn("partition", apps["luks"]["options"])


