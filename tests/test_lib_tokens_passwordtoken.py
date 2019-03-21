"""
This test file tests the lib.tokens.passwordtoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.passwordtoken import PasswordTokenClass
from privacyidea.models import Token


class PasswordTokenTestCase(MyTestCase):
    """
    Test the token on the database level
    """
    password = "topsecret"
    serial1 = "ser1"

    # add_user, get_user, reset, set_user_identifiers
    
    def test_01_create_token(self):
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
