"""
This test file tests the lib.tokens.recoverytoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.recoverytoken import RecoveryTokenClass
from privacyidea.models import Token
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
import smtpmock
from privacyidea.lib.error import privacyIDEAError
from privacyidea.lib.smtpserver import add_smtpserver
from privacyidea.lib.config import set_privacyidea_config


class RecoveryTokenTestCase(MyTestCase):
    serial1 = "ser1"


    # set_user, get_user, reset, set_user_identifiers

    def test_00_init_users(self):
        self.setUp_user_realms()

    @smtpmock.activate
    def test_01_create_token(self):
        smtpmock.setdata(response={"user@localhost.localdomain": (200, "OK")})

        # missing configuration
        self.assertRaises(privacyIDEAError, init_token,
                          {"type": "recovery", "serial": self.serial1},
                          user=User("cornelius", self.realm1))

        # recover password with "recovery.identifier"
        r = add_smtpserver(identifier="myserver", server="1.2.3.4")
        self.assertTrue(r > 0)
        set_privacyidea_config("recovery.identifier", "myserver")
        token = init_token({"type": "recovery",
                            "serial": self.serial1},
                           user=User("cornelius", self.realm1))
        self.assertTrue(token.token.tokentype == "recovery",
                        token.token.tokentype)
        self.assertTrue(token.type == "recovery", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "REC", class_prefix)
        self.assertTrue(token.get_class_type() == "recovery", token)

    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RecoveryTokenClass(db_token)

        info = token.get_class_info()
        self.assertEqual(info.get("title"), "Password Recovery Token")

        info = token.get_class_info("title")
        self.assertEqual(info, "Password Recovery Token")

    def test_03_check_recoverycode(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RecoveryTokenClass(db_token)

        r = token.check_otp("wrong pw")
        self.assertTrue(r == -1, r)

        detail = token.get_init_detail()
        recoverycode = detail.get("registrationcode")
        r = token.check_otp(recoverycode)
        print(recoverycode)
        self.assertEqual(r, -1)

        # Check recovery code
        r = token.check_recovery_code(recoverycode)
        self.assertEqual(r, 0)
        # check if the token is deleted
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        self.assertEqual(db_token, None)
