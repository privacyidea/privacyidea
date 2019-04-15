"""
This test file tests the lib.tokens.passwordtoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.registrationtoken import RegistrationTokenClass
from privacyidea.models import Token


class RegistrationTokenTestCase(MyTestCase):
    serial1 = "ser1"

    # add_user, get_user, reset, set_user_identifiers
    
    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="registration")
        db_token.save()
        token = RegistrationTokenClass(db_token)
        token.update({})
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "registration",
                        token.token.tokentype)
        self.assertTrue(token.type == "registration", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "REG", class_prefix)
        self.assertTrue(token.get_class_type() == "registration", token)

    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RegistrationTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "Registration Code Token", info)

        info = token.get_class_info("title")
        self.assertTrue(info == "Registration Code Token", info)

    def test_03_check_password(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RegistrationTokenClass(db_token)

        r = token.check_otp("wrong pw")
        self.assertTrue(r == -1, r)

        detail = token.get_init_detail()
        r = token.check_otp(detail.get("registrationcode"))
        self.assertTrue(r == 0, r)

        # check if the token sill exists after check_otp
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        self.assertNotEqual(db_token, None)

        # check if the token is deleted after inc_success
        token.inc_count_auth_success()
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        self.assertEqual(db_token, None)

