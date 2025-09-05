"""
This test file tests the lib.tokens.papertoken
This depends on lib.tokenclass
"""
import logging

from testfixtures import LogCapture

from privacyidea.lib.token import init_token, remove_token, import_tokens, get_tokens
from privacyidea.lib.tokens.papertoken import PaperTokenClass
from privacyidea.models import Token
from .base import MyTestCase

OTPKEY = "3132333435363738393031323334353637383930"


class PaperTokenTestCase(MyTestCase):
    serial1 = "ser1"

    # add_user, get_user, reset, set_user_identifiers

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="paper")
        db_token.save()
        token = PaperTokenClass(db_token)
        token.update({})
        self.assertEqual(token.token.serial, self.serial1)
        self.assertEqual(token.token.tokentype, "paper")
        self.assertEqual(token.type, "paper")
        class_prefix = token.get_class_prefix()
        self.assertEqual(class_prefix, "PPR")
        self.assertEqual(token.get_class_type(), "paper")

    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = PaperTokenClass(db_token)

        info = token.get_class_info()
        self.assertEqual(info.get("title"), "Paper Token")

        info = token.get_class_info("title")
        self.assertEqual(info, "Paper Token")

    def test_03_get_init_details(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = PaperTokenClass(db_token)
        token.update({})

        # if no otpkey was given, an OTP key is created.
        init_detail = token.get_init_detail()
        self.assertTrue("otps" in init_detail)

    def test_04_get_init_details_with_key(self):
        token = init_token({"type": "paper",
                            "otpkey": OTPKEY})
        init_detail = token.get_init_detail()
        self.assertTrue("otps" in init_detail)
        otps = init_detail.get("otps")
        self.assertEqual(otps.get(0), "755224")
        self.assertEqual(otps.get(1), "287082")
        self.assertEqual(otps.get(2), "359152")

        # test authenticating
        r = token.check_otp("755224")
        self.assertEqual(r, 0)
        r = token.check_otp("287082")
        self.assertEqual(r, 1)
        r = token.check_otp("359152")
        self.assertEqual(r, 2)

        # A previous OTP value will fail to authenticate
        r = token.check_otp("755224")
        self.assertEqual(r, -1)
        with LogCapture(level=logging.INFO) as lc:
            self.assertEqual(-1, token.check_otp("12345"))
            lc.check_present(
                ('privacyidea.lib.decorators', 'INFO',
                 f'OTP value for token {token.token.serial} (type: {token.type}) '
                 f'has wrong length (5 != 6)'))
            self.assertEqual(-1, token.check_otp("1234567"))
            lc.check_present(
                ('privacyidea.lib.decorators', 'INFO',
                 f'OTP value for token {token.token.serial} (type: {token.type}) '
                 f'has wrong length (7 != 6)'))

    def test_05_paper_token_export(self):
        # Set up the PaperTokenClass for testing
        papertoken = init_token(param={'serial': "PAPER12345678", 'type': 'paper'})
        papertoken.set_description("this is a paper token export test")
        papertoken.add_tokeninfo("hashlib", "sha256")

        # Test that all expected keys are present in the exported dictionary
        exported_data = papertoken.export_token()
        expected_keys = ["serial", "type", "description", "count", "otplen", "otpkey", "issuer"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["hashlib", "tokenkind"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "PAPER12345678")
        self.assertEqual(exported_data["type"], "paper")
        self.assertEqual(exported_data["description"], "this is a paper token export test")
        self.assertEqual(exported_data["info_list"]["hashlib"], "sha256")
        self.assertEqual(exported_data["otpkey"], papertoken.token.get_otpkey().getKey().decode("utf-8"))
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")

        # Clean up
        remove_token(papertoken.token.serial)

    def test_06_paper_token_import(self):
        # Define the token data to be imported
        token_data = [{
            "serial": "PAPER12345678",
            "type": "paper",
            "description": "this is a paper token import test",
            "otpkey": OTPKEY,
            "info_list": {"hashlib": "sha512", "tokenkind": "software"},
            "issuer": "privacyIDEA"
        }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        papertoken = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(papertoken.token.serial, token_data[0]["serial"])
        self.assertEqual(papertoken.type, token_data[0]["type"])
        self.assertEqual(papertoken.token.description, token_data[0]["description"])
        self.assertEqual(papertoken.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(papertoken.get_tokeninfo("hashlib"), token_data[0]["info_list"]["hashlib"])
        self.assertEqual(papertoken.get_tokeninfo("tokenkind"), token_data[0]["info_list"]["tokenkind"])

        # Check that the token works
        r = papertoken.check_otp('125165')
        self.assertEqual(r, 0)

        # Clean up
        remove_token(papertoken.token.serial)
