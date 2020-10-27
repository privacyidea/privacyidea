# -*- coding: utf-8 -*-

"""
This test file tests the lib.tokens.4eyestoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.foureyestoken import FourEyesTokenClass
from privacyidea.lib.token import init_token, check_serial_pass, remove_token
from privacyidea.lib.user import User


class FourEyesTokenTestCase(MyTestCase):

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_convert_realm(self):
        r = FourEyesTokenClass.convert_realms("realm1:2,realm2:1")
        self.assertEqual(r, {"realm1": 2,
                             "realm2": 1})

        r = FourEyesTokenClass.convert_realms("realm1,realm2:1")
        self.assertEqual(r, {"realm2": 1})

    def test_02_create_token(self):
        r = init_token({"4eyes": "realm1:1,realm2:2",
                        "type": "4eyes",
                        "separator": "|"})
        self.assertEqual(r.type, "4eyes")
        self.assertEqual(r.get_tokeninfo("4eyes"), "realm1:1,realm2:2")
        self.assertEqual(r.get_tokeninfo("separator"), "|")

        realms = r._get_realms()
        self.assertEqual(realms, {"realm1": 1, "realm2": 2})

        self.assertEqual(r._get_separator(), "|")

    def test_03_authenticate(self):
        self.setUp_user_realms()

        init_token({"type": "pw",
                    "otpkey": "password1",
                    "pin": "pin1",
                    "serial": "pwserial1"},
                   user=User("cornelius", self.realm1))

        init_token({"type": "pw",
                    "otpkey": "password2",
                    "pin": "pin2",
                    "serial": "pwserial2"},
                   user=User("cornelius", self.realm1))

        init_token({"type": "pw",
                    "otpkey": "password3",
                    "pin": "pin3",
                    "serial": "pwserial3"},
                   user=User("cornelius", self.realm1))

        tok = init_token({"serial": "eye1",
                          "type": "4eyes",
                          "4eyes": "{0!s}:2".format(self.realm1),
                          "separator": " "})

        r = check_serial_pass("eye1", "pin1password1 pin2password2")
        self.assertEqual(r[0], True)

        # This triggers the challenge for the next token
        r = check_serial_pass("eye1", "pin1password1")
        self.assertEqual(r[0], False)
        self.assertTrue("transaction_id" in r[1])
        self.assertEqual(r[1].get("message"), 'Please authenticate with another token from either realm: realm1.')

        # check false separator
        r = check_serial_pass("eye1", "pin1password1:pin2password2")
        self.assertFalse(r[0])
        self.assertEqual(r[1].get("foureyes"), "Only found 0 tokens in realm {0!s}".format(self.realm1))

        # check authentication also works if the 4eyes-token is in the same realm
        tok.add_user(User('cornelius', self.realm1))
        r = check_serial_pass("eye1", "pin3password3 pin2password2")
        self.assertTrue(r[0])
        self.assertEqual(r[1].get('message'), 'matching 1 tokens')

        # cleanup
        remove_token(serial='pwserial1')
        remove_token(serial='pwserial2')
        remove_token(serial='pwserial3')
        remove_token(serial='eye1')
