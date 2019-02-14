"""
This test file tests the lib.tokens.spasstoken
This depends on lib.tokenclass
"""

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
        r = token.authenticate(self.otppin)
        self.assertTrue(r, r)

    def test_03_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = SpassTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "Simple Pass Token", info)

        info = token.get_class_info("title")
        self.assertTrue(info == "Simple Pass Token", info)
