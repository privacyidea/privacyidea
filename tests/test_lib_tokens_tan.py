"""
This test file tests the lib.tokens.papertoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.tantoken import TanTokenClass
from privacyidea.lib.token import init_token
from privacyidea.models import Token

OTPKEY = "3132333435363738393031323334353637383930"


class TanTokenTestCase(MyTestCase):
    serial1 = "ser1"

    # set_user, get_user, reset, set_user_identifiers
    
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


