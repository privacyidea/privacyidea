"""
This test file tests the lib.tokens.papertoken
This depends on lib.tokenclass
"""
import logging

from testfixtures import LogCapture

from privacyidea.lib.token import init_token, import_token, remove_token, import_tokens, get_tokens
from privacyidea.lib.tokens.tantoken import TanTokenClass
from privacyidea.models import Token
from .base import MyTestCase

OTPKEY = "3132333435363738393031323334353637383930"


class TanTokenTestCase(MyTestCase):
    serial1 = "ser1"

    # add_user, get_user, reset, set_user_identifiers

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="tan")
        db_token.save()
        token = TanTokenClass(db_token)
        token.update({})
        self.assertEqual(token.token.serial, self.serial1)
        self.assertEqual(token.token.tokentype, "tan")
        self.assertEqual(token.type, "tan")
        class_prefix = token.get_class_prefix()
        self.assertEqual(class_prefix, "PITN")
        self.assertEqual(token.get_class_type(), "tan")

    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = TanTokenClass(db_token)

        info = token.get_class_info()
        self.assertEqual(info.get("title"), "TAN Token")

        info = token.get_class_info("title")
        self.assertEqual(info, "TAN Token")

    def test_03_get_init_details(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = TanTokenClass(db_token)
        token.update({})

        # if no otpkey was given, an OTP key is created.
        init_detail = token.get_init_detail()
        self.assertTrue("otps" in init_detail)

    def test_04_get_init_details_with_key(self):
        token = init_token({"type": "tan",
                            "otpkey": OTPKEY})
        init_detail = token.get_init_detail()
        self.assertTrue("otps" in init_detail)
        otps = init_detail.get("otps")
        self.assertEqual(otps.get(0), "755224")
        self.assertEqual(otps.get(1), "287082")
        self.assertEqual(otps.get(2), "359152")

        # test authenticating in arbitrary order
        r = token.check_otp("287082")
        self.assertEqual(r, 1)
        r = token.check_otp("359152")
        self.assertEqual(r, 1)
        r = token.check_otp("755224")
        self.assertEqual(r, 1)
        # previous OTP
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

    def test_05_import(self):
        params = TanTokenClass.get_import_csv(["se1", "121212", "tan",
                                               "tan1 tan2  tan3    tan4    tan5"])
        self.assertEqual(params.get("serial"), "se1")
        self.assertEqual(params.get("type"), "tan")
        self.assertEqual(params.get("tans").split(), ["tan1", "tan2", "tan3", "tan4", "tan5"])

        # test init token
        tok = init_token(params)
        self.assertEqual(tok.token.tokentype, "tan")

        d = tok.get_as_dict()
        self.assertTrue("tan.tan0" not in d.get("info"), d.get("info"))
        self.assertEqual(d.get("info", {}).get("tan.count"), 5)

        # check all tans
        r = tok.check_otp("tan2")
        self.assertEqual(r, 1)
        r = tok.check_otp("tan2")
        self.assertEqual(r, -1)
        r = tok.check_otp("tan5")
        self.assertEqual(r, 1)
        r = tok.check_otp("tan4")
        self.assertEqual(r, 1)
        r = tok.check_otp("tan3")
        self.assertEqual(r, 1)

        d = tok.get_as_dict()
        self.assertEqual(d.get("info", {}).get("tan.count"), 1)

        # Check the authentication of a TAN token with a PIN
        tok.set_pin("test")
        r = tok.authenticate("testtan1")
        self.assertEqual(r, (True, 1, None))

        # check if the otplen of the TAN token is 4, the length of the first TAN
        self.assertEqual(tok.token.otplen, 4)

    def test_10_import_tan(self):
        # These are example values that are imported from a file and end up at
        # lib/token.import_token
        serial = "ABC123"
        params = {'hashlib': 'sha1',
                  'type': 'tan',
                  'user': {},
                  'serial': 'ABC123',
                  'tans': '123465 798111',
                  'otpkey': ''}

        tok = import_token(serial, params)
        self.assertEqual("tan", tok.type)

        d = tok.get_as_dict()
        self.assertEqual(d.get("info", {}).get("tan.count"), 2)
        # check tans:
        r = tok.check_otp("798111")
        self.assertEqual(r, 1)
        r = tok.check_otp("798111")
        self.assertEqual(r, -1)
        r = tok.check_otp("123465")
        self.assertEqual(r, 1)

    def test_11_tan_token_export(self):
        # Set up the TANTokenClass for testing
        token = init_token(param={'serial': "PITN0000B9CE", 'type': 'tan'})
        token.set_description("this is a tan token export test")
        token.add_tokeninfo("hashlib", "sha256")

        # Test that all expected keys are present in the exported dictionary
        exported_data = token.export_token()
        expected_keys = ["serial", "type", "description", "count", "otplen", "otpkey", "issuer"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["hashlib", "tokenkind"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "PITN0000B9CE")
        self.assertEqual(exported_data["type"], "tan")
        self.assertEqual(exported_data["description"], "this is a tan token export test")
        self.assertEqual(exported_data["info_list"]["hashlib"], "sha256")
        self.assertEqual(exported_data["otpkey"], token.token.get_otpkey().getKey().decode("utf-8"))
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")

        # Clean up
        remove_token(token.token.serial)

    def test_12_paper_token_import(self):
        # Define the token data to be imported
        token_data = [{
            "serial": "PITN0000B9CE",
            "type": "paper",
            "description": "this is a paper token import test",
            "otpkey": OTPKEY,
            "info_list": {'hashlib': 'sha256',
                          'tan.tan0': '3224ea1f:1f234536a59c4998c43d3d18247e210be9a42e38e43c71ab5de8e8879068dde0',
                          'tan.tan1': '2de3b273:417b3ca840815c976b0d78b540011fc738081772bf60940a70d2f09111165896',
                          'tan.tan10': '2d61bc1a:5310cfda92e6dc5e33be36e55bc204084e61068e97c869343ab0c77b06aa9c58',
                          'tan.tan11': '8a728e30:62ff370f0919562ce673cf3f346a64addbb7a37284eba9da8a4a84800aa49f17',
                          'tan.tan12': '9312d86b:e1ee5961f29fd8d9a4dfde467b129840ceb44c7a9059c09189ef967229558f19',
                          'tokenkind': 'software'},
            "issuer": "privacyIDEA"
        }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        token = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(token.token.serial, token_data[0]["serial"])
        self.assertEqual(token.type, token_data[0]["type"])
        self.assertEqual(token.token.description, token_data[0]["description"])
        self.assertEqual(token.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(token.get_tokeninfo("hashlib"), token_data[0]["info_list"]["hashlib"])
        self.assertEqual(token.get_tokeninfo("tokenkind"), token_data[0]["info_list"]["tokenkind"])

        # Check that the token works
        r = token.check_otp('875740')
        self.assertEqual(r, 0)

        # Clean up
        remove_token(token.token.serial)
