"""
This test file tests the lib.tokens.passwordtoken
This depends on lib.tokenclass
"""
from privacyidea.lib.token import init_token, import_tokens, get_tokens
from privacyidea.lib.tokens.registrationtoken import DEFAULT_LENGTH
from privacyidea.lib.tokens.registrationtoken import RegistrationTokenClass
from privacyidea.models import Token
from .base import MyTestCase


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

    def test_01b_create_token_with_policy(self):
        token = init_token({"type": "registration",
                            "registration.length": "15",
                            "registration.contents": "-sc"})
        init_detail = token.get_init_detail()
        registrationcode = init_detail.get("registrationcode")
        # the registrationcode should only contain 15 digits
        self.assertEqual(15, len(registrationcode))
        self.assertTrue(int(registrationcode))
        token = init_token({"type": "registration"})
        init_detail = token.get_init_detail()
        registrationcode = init_detail.get("registrationcode")
        self.assertEqual(DEFAULT_LENGTH, len(registrationcode))

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

        # check if the token is deleted after post_success
        token.post_success()
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        self.assertEqual(db_token, None)

    def test_04_registration_token_export(self):
        # Set up the RegistrationTokenClass for testing
        token = init_token({"type": "registration",
                            "serial": self.serial1,
                            "description": "this is a registration token export test",
                            "otp_len": 24
                            })

        # Test that all expected keys are present in the exported dictionary
        exported_data = token.export_token()
        expected_keys = ["serial", "type", "description", "issuer", "otpkey", "otplen"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["tokenkind"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "ser1")
        self.assertEqual(exported_data["type"], "registration")
        self.assertEqual(exported_data["description"], "this is a registration token export test")
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")
        self.assertEqual(exported_data["otplen"], 24)
        self.assertEqual(exported_data["otpkey"], token.token.get_otpkey().getKey().decode("utf-8"))

        # Clean up
        token.delete_token()

    def test_05_registration_token_import(self):
        # Define the token data to be imported
        token_data = [{'description': 'this is a registration token export test',
                       'issuer': 'privacyIDEA',
                       'otpkey': ')%56YBF(1NAaX?k0hS,S}+bI',
                       'otplen': 24,
                       'serial': 'ser1',
                       'type': 'registration',
                       'info_list': {'tokenkind': 'software'}
                       }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        token = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(token.token.serial, token_data[0]["serial"])
        self.assertEqual(token.type, token_data[0]["type"])
        self.assertEqual(token.token.description, token_data[0]["description"])
        self.assertEqual(token.get_tokeninfo("tokenkind"), "software")
        self.assertEqual(token.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(token.token.otplen, 24)
        self.assertIsNotNone(token.get_tokeninfo(key="import_date"))

        # cheak that the token can be used
        detail = token.get_init_detail()
        r = token.check_otp(detail.get("registrationcode"))
        self.assertTrue(r == 0, r)

        # Clean up
        token.delete_token()
