"""
This test file tests the lib.tokens.4eyestoken
This depends on lib.tokenclass
"""
import logging

from testfixtures import log_capture

from privacyidea.lib.token import init_token, check_serial_pass, remove_token, import_tokens, get_tokens
from privacyidea.lib.tokens.foureyestoken import FourEyesTokenClass
from privacyidea.lib.tokens.foureyestoken import log as foureyes_log
from privacyidea.lib.user import User
from .base import MyTestCase


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
        self.assertIsInstance(r, FourEyesTokenClass)

        realms = r._get_realms()
        self.assertEqual(realms, {"realm1": 1, "realm2": 2})

        self.assertEqual(r._get_separator(), "|")

    @log_capture(level=logging.DEBUG)
    def test_03_authenticate(self, capture):
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

        foureyes_log.setLevel(logging.DEBUG)
        r = check_serial_pass("eye1", "pin1password1 pin2password2")
        self.assertTrue(r[0], r)
        log_msg = str(capture)
        self.assertNotIn('pin1password1', log_msg, log_msg)
        self.assertNotIn('pin2password2', log_msg, log_msg)

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

    def test_04_foureyes_token_export(self):
        # Set up the FourEyeTokenClass for testing
        foureyetoken = init_token(param={
            'serial': "FOUR12345678",
            'type': '4eyes',
            'otpkey': '12345',
            'separator': ":",
            '4eyes': "realm1,realm2"
        })

        foureyetoken.set_description("this is a four-eye token export test")
        foureyetoken.add_tokeninfo("hashlib", "sha256")

        # Test that all expected keys are present in the exported dictionary
        exported_data = foureyetoken.export_token()
        expected_keys = [
            "serial", "type", "description", "otpkey", "issuer"
        ]

        for key in expected_keys:
            self.assertIn(key, exported_data)

        expected_tokeninfo_keys = ["4eyes", "separator", "hashlib", "tokenkind"]
        for key in expected_tokeninfo_keys:
            self.assertIn(key, exported_data["info_list"])

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "FOUR12345678")
        self.assertEqual(exported_data["type"], "4eyes")
        self.assertEqual(exported_data["description"], "this is a four-eye token export test")
        self.assertEqual(exported_data["info_list"]["hashlib"], "sha256")
        self.assertEqual(exported_data["otpkey"], '12345')
        self.assertEqual(exported_data["info_list"]["separator"], ":")
        self.assertEqual(exported_data["info_list"]["4eyes"], "realm1,realm2")
        self.assertEqual(exported_data["info_list"]["tokenkind"], "virtual")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")

        # Clean up
        remove_token(foureyetoken.token.serial)

    def test_05_foureyes_token_import(self):
        # Define the token data to be imported
        token_data = [{
            "serial": "FOUR12345678",
            "type": "4eyes",
            "description": "this is a four-eye token import test",
            "otpkey": "12345",
            "issuer": "privacyIDEA",
            "info_list": {"separator": "|", "4eyes": "realm1:2", "hashlib": "sha256", "tokenkind": "virtual"}
        }]

        # Import the token

        result = import_tokens(token_data)
        self.assertIn("FOUR12345678", result.successful_tokens, result)

        # Retrieve the imported token
        foureyetoken = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(foureyetoken.token.serial, token_data[0]["serial"])
        self.assertEqual(foureyetoken.type, token_data[0]["type"])
        self.assertEqual(foureyetoken.token.description, token_data[0]["description"])
        self.assertEqual(foureyetoken.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(foureyetoken.get_tokeninfo("separator"), token_data[0]["info_list"]["separator"])
        self.assertEqual(foureyetoken.get_tokeninfo("4eyes"), token_data[0]["info_list"]["4eyes"])
        self.assertEqual(foureyetoken.get_tokeninfo("hashlib"), token_data[0]["info_list"]["hashlib"])
        self.assertEqual(foureyetoken.get_tokeninfo("tokenkind"), token_data[0]["info_list"]["tokenkind"])
        self.assertEqual(foureyetoken.export_token()["issuer"], token_data[0]["issuer"])

        self.setUp_user_realms()
        foureyetoken.add_user(User("cornelius", self.realm1))

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

        r = check_serial_pass("FOUR12345678", "pin1password1|pin2password2")
        self.assertEqual(r[0], True)

        # This triggers the challenge for the next token
        r = check_serial_pass("FOUR12345678", "pin2password2")
        self.assertEqual(r[0], False)
        self.assertTrue("transaction_id" in r[1])
        self.assertEqual(r[1].get("message"),
                         'Please authenticate with another token from either realm: realm1.')

        # Clean up
        remove_token(foureyetoken.token.serial)
