"""
This test file tests the lib.tokens.papertoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.tantoken import TanTokenClass
from privacyidea.lib.token import init_token, get_tokens_paginate, import_token
from privacyidea.models import Token

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
        # This are example values that are imported from a file and end up at
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
