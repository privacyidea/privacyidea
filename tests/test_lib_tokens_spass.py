"""
This test file tests the lib.tokens.spasstoken
This depends on lib.tokenclass
"""
import json
import logging
from testfixtures import LogCapture

from privacyidea.lib.token import remove_token, get_tokens, import_tokens, init_token
from .base import MyTestCase
from privacyidea.lib.tokens.spasstoken import SpassTokenClass
from privacyidea.models import Token


class SpassTokenTestCase(MyTestCase):

    otppin = "topsecret"
    serial1 = "ser1"

    # add_user, get_user, reset, set_user_identifiers

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="spass")
        db_token.save()
        token = SpassTokenClass(db_token)
        token.update({})
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "spass", token.token.tokentype)
        self.assertTrue(token.type == "spass", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PISP", class_prefix)
        self.assertTrue(token.get_class_type() == "spass", token)

    def test_02_check_password(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = SpassTokenClass(db_token)

        r = token.check_otp("")
        self.assertTrue(r == 0, r)

        r = token.check_otp("wrong pw")
        self.assertTrue(r == 0, r)

        # check pin+otp:
        token.set_pin(self.otppin)
        logging.getLogger('privacyidea.lib.tokens.spasstoken').setLevel(logging.DEBUG)
        with LogCapture(level=logging.DEBUG) as lc:
            r = token.authenticate(self.otppin)
            self.assertTrue(r, r)
            for log_record in lc.actual():
                self.assertNotIn(self.otppin, log_record[2], log_record)

    def test_03_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = SpassTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "Simple Pass Token", info)

        info = token.get_class_info("title")
        self.assertTrue(info == "Simple Pass Token", info)

    def test_04_spass_token_export(self):
        # Set up the SPassTokenClass for testing
        spasstoken = init_token(param={'serial': "SPASS12345678", 'type': 'spass', 'otpkey': '12345'})
        spasstoken.set_description("this is an spass token export test")
        spasstoken.add_tokeninfo("hashlib", "sha256")

        # Test that all expected keys are present in the exported dictionary
        exported_data = spasstoken.export_token()
        expected_keys = [
            "serial", "type", "description", "otpkey", "issuer"
        ]
        for key in expected_keys:
            self.assertIn(key, exported_data)

        expected_tokeninfo_keys = ["hashlib", "tokenkind"]
        for key in expected_tokeninfo_keys:
            self.assertIn(key, exported_data["tokeninfo"])

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "SPASS12345678")
        self.assertEqual(exported_data["type"], "spass")
        self.assertEqual(exported_data["description"], "this is an spass token export test")
        self.assertEqual(exported_data["tokeninfo"]["hashlib"], "sha256")
        self.assertEqual(exported_data["otpkey"], '12345')
        self.assertEqual(exported_data["tokeninfo"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")

        # Clean up
        remove_token(spasstoken.token.serial)

    def test_05_spass_token_import(self):
        # Define the token data to be imported
        token_data = [{
            "serial": "SPASS12345678",
            "type": "spass",
            "description": "this is an spass token import test",
            "otpkey": "12345",
            "issuer": "privacyIDEA",
            "tokeninfo": {"hashlib": "sha256", "tokenkind": "software"}
        }]

        # Import the token
        import_tokens(json.dumps(token_data))

        # Retrieve the imported token
        spasstoken = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(spasstoken.token.serial, token_data[0]["serial"])
        self.assertEqual(spasstoken.type, token_data[0]["type"])
        self.assertEqual(spasstoken.token.description, token_data[0]["description"])
        self.assertEqual(spasstoken.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(spasstoken.get_tokeninfo("hashlib"), token_data[0]["tokeninfo"]["hashlib"])
        self.assertEqual(spasstoken.get_tokeninfo("tokenkind"), token_data[0]["tokeninfo"]["tokenkind"])
        self.assertEqual(spasstoken.export_token()["issuer"], token_data[0]["issuer"])

        # Check that the token works
        r = spasstoken.check_otp("")
        self.assertTrue(r == 0, r)

        # Clean up
        remove_token(spasstoken.token.serial)
