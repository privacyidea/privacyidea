# coding: utf-8
"""
This test file tests the lib.tokens.radiustoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.radiustoken import RadiusTokenClass
from privacyidea.models import Token
from privacyidea.lib.error import ParameterError
from privacyidea.lib.config import set_privacyidea_config
from . import radiusmock
from privacyidea.lib.token import init_token
from privacyidea.lib.radiusserver import add_radius

DICT_FILE="tests/testdata/dictionary"


class RadiusTokenTestCase(MyTestCase):

    otppin = "topsecret"
    serial1 = "ser1"
    params1 = {"radius.server": "my.other.radiusserver:1812",
               "radius.local_checkpin": True,
               "radius.user": "user1",
               "radius.secret": "testing123",
               "radius.dictfile": "tests/testdata/dictfile"}
    serial2 = "use1"
    params2 = {"radius.server": "my.other.radiusserver:1812",
               "radius.local_checkpin": False,
               "radius.user": "user1",
               "radius.secret": "testing123",
               "radius.dictfile": "tests/testdata/dictfile"}
    serial3 = "serial3"
    params3 = {"radius.server": "my.other.radiusserver:1812"}

    success_body = {"detail": {"message": "matching 1 tokens",
                               "serial": "PISP0000AB00",
                               "type": "spass"},
                    "id": 1,
                    "jsonrpc": "2.0",
                    "result": {"status": True,
                               "value": True
                    },
                    "version": "privacyIDEA unknown"
    }

    fail_body = {"detail": {"message": "wrong otp value"},
                    "id": 1,
                    "jsonrpc": "2.0",
                    "result": {"status": True,
                               "value": False
                    },
                    "version": "privacyIDEA unknown"
    }

    def test_01_create_token(self):
        db_token = Token(self.serial3, tokentype="radius")
        db_token.save()
        token = RadiusTokenClass(db_token)
        # Missing radius.user parameter
        self.assertRaises(ParameterError, token.update, self.params3)

        db_token = Token(self.serial2, tokentype="radius")
        db_token.save()
        token = RadiusTokenClass(db_token)
        token.update(self.params2)
        token.set_pin(self.otppin)

        db_token = Token(self.serial1, tokentype="radius")
        db_token.save()
        token = RadiusTokenClass(db_token)
        token.update(self.params1)
        token.set_pin(self.otppin)

        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "radius",
                        token.token.tokentype)
        self.assertTrue(token.type == "radius", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PIRA", class_prefix)
        self.assertTrue(token.get_class_type() == "radius", token)


    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "RADIUS Token",
                        "{0!s}".format(info.get("title")))

        info = token.get_class_info("title")
        self.assertTrue(info == "RADIUS Token", info)

    def test_03_check_pin_local(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)

        r = token.check_pin_local
        self.assertTrue(r, r)

    @radiusmock.activate
    def test_04_do_request_success(self):
        radiusmock.setdata(success=True)
        set_privacyidea_config("radius.dictfile", DICT_FILE)
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)
        otpcount = token.check_otp("123456")
        self.assertTrue(otpcount >= 0, otpcount)


    @radiusmock.activate
    def test_05_do_request_fail(self):
        radiusmock.setdata(success=False)
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)
        otpcount = token.check_otp("123456")
        self.assertTrue(otpcount == -1, otpcount)

    @radiusmock.activate
    def test_08_authenticate_local_pin(self):
        radiusmock.setdata(success=True)
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)
        # wrong PIN
        r = token.authenticate("wrong"+"123456")
        self.assertFalse(r[0], r)
        self.assertTrue(r[1] == -1, r)
        self.assertTrue(r[2].get("message") == "Wrong PIN", r)
        # right PIN
        r = token.authenticate(self.otppin+"123456")
        self.assertTrue(r[0], r)
        self.assertTrue(r[1] >= 0, r)
        self.assertTrue(r[2].get("message") == "matching 1 tokens", r)

    @radiusmock.activate
    def test_09_authenticate_radius_pin(self):
        radiusmock.setdata(success=True)
        db_token = Token.query.filter(Token.serial == self.serial2).first()
        token = RadiusTokenClass(db_token)
        token.set_pin("")
        r = token.authenticate("radiusPIN123456")
        self.assertTrue(r[0], r)
        self.assertTrue(r[1] >= 0, r)
        self.assertTrue(r[2].get("message") == "matching 1 tokens", r)

    @radiusmock.activate
    def test_10_authenticate_system_radius_settings(self):
        set_privacyidea_config("radius.server", "my.other.radiusserver:1812")
        set_privacyidea_config("radius.secret", "testing123")
        radiusmock.setdata(success=True)
        token = init_token({"type": "radius",
                            "radius.system_settings": True,
                            "radius.user": "user1",
                            "radius.server": "",
                            "radius.secret": ""})
        r = token.authenticate("radiuspassword")
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2].get("message"), "matching 1 tokens")

    @radiusmock.activate
    def test_11_RADIUS_request(self):
        set_privacyidea_config("radius.dictfile", DICT_FILE)
        radiusmock.setdata(success=True)
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "radius.identifier": "myserver",
                            "radius.user": "user1"})
        r = token.authenticate("radiuspassword")
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2].get("message"), "matching 1 tokens")

    @radiusmock.activate
    def test_12_non_ascii(self):
        set_privacyidea_config("radius.dictfile", DICT_FILE)
        radiusmock.setdata(success=True)
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "radius.identifier": "myserver",
                            "radius.user": u"nönäscii"})
        r = token.authenticate(u"passwörd")
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2].get("message"), "matching 1 tokens")
