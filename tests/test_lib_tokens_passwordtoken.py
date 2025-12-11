"""
This test file tests the lib.tokens.passwordtoken
This depends on lib.tokenclass
"""
import logging

from testfixtures import log_capture

from privacyidea.lib.token import init_token, remove_token, import_tokens, get_tokens
from privacyidea.lib.tokens.passwordtoken import PasswordTokenClass
from privacyidea.lib.tokens.passwordtoken import log as pwt_log
from privacyidea.models import Token
from .base import MyTestCase


class PasswordTokenTestCase(MyTestCase):
    """
    Test the token on the database level
    """
    password = "topsecret"
    serial1 = "ser1"

    # add_user, get_user, reset, set_user_identifiers

    @log_capture(level=logging.DEBUG)
    def test_01_create_token(self, capture):
        pwt_log.setLevel(logging.DEBUG)
        db_token = Token(self.serial1, tokentype="pw")
        db_token.save()
        token = PasswordTokenClass(db_token)
        token.update({"otpkey": self.password})
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "pw", token.token.tokentype)
        self.assertTrue(token.type == "pw", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PW", class_prefix)
        self.assertTrue(token.get_class_type() == "pw", token)
        log_msg = str(capture)
        self.assertNotIn(self.password, log_msg, log_msg)
        pwt_log.setLevel(logging.INFO)

    def test_02_check_password(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = PasswordTokenClass(db_token)

        r = token.check_otp(self.password)
        self.assertTrue(r == 0, r)

        r = token.check_otp("wrong pw")
        self.assertTrue(r == -1, r)

        # check pin+otp:
        token.set_pin(self.serial1, "secretpin")
        r = token.authenticate("secretpin{0!s}".format(self.password))
        self.assertTrue(r, r)

    def test_03_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = PasswordTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "Password Token", info)

        info = token.get_class_info("title")
        self.assertTrue(info == "Password Token", info)

    def test_04_password_token_export(self):
        # Set up the PasswordTokenClass for testing
        passwordtoken = init_token(param={'serial': "PASS12345678", 'type': 'pw', 'otpkey': '12345'})
        passwordtoken.set_description("this is a password token export test")
        passwordtoken.add_tokeninfo("hashlib", "sha256")

        # Test that all expected keys are present in the exported dictionary
        exported_data = passwordtoken.export_token()

        expected_keys = ["serial", "type", "description", "otpkey", "issuer"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["hashlib", "tokenkind"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "PASS12345678")
        self.assertEqual(exported_data["type"], "pw")
        self.assertEqual(exported_data["description"], "this is a password token export test")
        self.assertEqual(exported_data["info_list"]["hashlib"], "sha256")
        self.assertEqual(exported_data["otpkey"], '12345')
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")

        # Clean up
        remove_token(passwordtoken.token.serial)

    def test_05_password_token_import(self):
        # Define the token data to be imported
        token_data = [{
            "serial": "PASS12345678",
            "type": "pw",
            "description": "this is a password token import test",
            "otpkey": "topsecret",
            "info_list": {"hashlib": "sha256", "tokenkind": "software"},
            "issuer": "privacyIDEA"
        }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        passwordtoken = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(passwordtoken.token.serial, token_data[0]["serial"])
        self.assertEqual(passwordtoken.type, token_data[0]["type"])
        self.assertEqual(passwordtoken.token.description, token_data[0]["description"])
        self.assertEqual(passwordtoken.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(passwordtoken.get_tokeninfo("hashlib"), token_data[0]["info_list"]["hashlib"])
        self.assertEqual(passwordtoken.get_tokeninfo("tokenkind"), token_data[0]["info_list"]["tokenkind"])

        # check that the token works
        r = passwordtoken.check_otp(self.password)
        self.assertTrue(r == 0, r)

        # Clean up
        remove_token(passwordtoken.token.serial)
