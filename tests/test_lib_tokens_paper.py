"""
This test file tests the lib.tokens.papertoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.papertoken import PaperTokenClass
from privacyidea.lib.token import init_token
from privacyidea.models import Token

OTPKEY = "3132333435363738393031323334353637383930"


class PaperTokenTestCase(MyTestCase):
    serial1 = "ser1"

    # set_user, get_user, reset, set_user_identifiers
    
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
