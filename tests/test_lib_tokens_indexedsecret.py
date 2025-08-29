"""
This test file tests the lib.tokens.smstoken
"""
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE, PolicyClass
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.token import init_token, remove_token, import_tokens, get_tokens
from privacyidea.lib.tokens.indexedsecrettoken import IndexedSecretTokenClass, PIIXACTION
from privacyidea.lib.user import (User)
from privacyidea.models import Token
from .base import MyTestCase, FakeFlaskG, FakeAudit

PWFILE = "tests/testdata/passwords"


class IndexedSecretTokenTestCase(MyTestCase):
    """
    Test the IndexedSecret Token
    """
    email = "pi_tester@privacyidea.org"
    otppin = "topsecret"
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    serial1 = "SE123456"
    serial2 = "SE000000"
    otpkey = "3132333435363738393031323334353637383930"

    success_body = "ID 12345"

    def test_00_create_user_realm(self):
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1, [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def test_01_create_token(self):
        my_secret = "mySecretInformation"
        db_token = Token(self.serial1, tokentype="indexedsecret")
        db_token.save()
        token = IndexedSecretTokenClass(db_token)
        token.update({"otpkey": my_secret})
        token.save()
        serial = token.get_serial()
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "indexedsecret", token.token)
        self.assertTrue(token.type == "indexedsecret", token.type)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PIIX", class_prefix)
        self.assertTrue(token.get_class_type() == "indexedsecret", token)

        # Create a challenge
        r, message, transaction_id, reply_dict = token.create_challenge()
        attribute = reply_dict.get("attributes")
        self.assertTrue(r)
        self.assertIn("Please enter the position", message)

        password_list = [my_secret[x - 1] for x in attribute.get("random_positions")]
        password = "".join(password_list)
        # Wrong transaction_id
        r = token.check_challenge_response(passw=password, options={"transaction_id": "wrong"})
        self.assertEqual(-1, r)

        # wrong password - wrong length
        r = token.check_challenge_response(passw="wrong", options={"transaction_id": transaction_id})
        self.assertEqual(-1, r)

        # wrong password - wrong contents
        r = token.check_challenge_response(passw="XX", options={"transaction_id": transaction_id})
        self.assertEqual(-1, r)

        # Successful authentication, we can also pass the transaction_id in the state.
        r = token.check_challenge_response(passw=password, options={"state": transaction_id})
        self.assertEqual(1, r)

        db_token.delete()

    def test_02_init_token(self):
        # Create the tokenclass via init_token
        my_secret = "mysimplesecret"
        t = init_token({"type": "indexedsecret",
                        "otpkey": my_secret,
                        "serial": "PIIX1234"})
        self.assertEqual(t.token.tokentype, "indexedsecret")
        self.assertEqual(t.token.serial, "PIIX1234")

        remove_token("PIIX1234")

    def test_03_challenge_text_position_count(self):
        # test challenge text and position count
        my_secret = "mysimplesecret"
        set_policy("pol1", scope=SCOPE.AUTH, action="indexedsecret_{0!s}=5".format(PIIXACTION.COUNT))
        set_policy("pol2", scope=SCOPE.AUTH,
                   action="indexedsecret_challenge_text=Hier sind die Positionen: {0!s}")

        t = init_token({"type": "indexedsecret",
                        "otpkey": my_secret,
                        "serial": "PIIX1234"})
        g = FakeFlaskG()
        g.audit_object = FakeAudit
        g.policy_object = PolicyClass()

        # Create a challenge
        r, message, transaction_id, reply_dict = t.create_challenge(options={"g": g})
        attribute = reply_dict.get("attributes")
        # The challenge text from the policy is used.
        self.assertIn("Hier sind die Positionen:", message)
        password_list = [my_secret[x - 1] for x in attribute.get("random_positions")]
        password = "".join(password_list)
        # The password has length 5, due to the pol2
        self.assertEqual(5, len(password))
        # Successful auth
        r = t.check_challenge_response(passw=password, options={"transaction_id": transaction_id})
        self.assertEqual(1, r)

        delete_policy("pol1")
        delete_policy("pol2")
        remove_token("PIIX1234")

    def test_04_indexedsecret_token_export(self):
        # Set up the indexedsecret token for testing
        token = init_token(
            param={'serial': self.serial1, 'type': 'indexedsecret', 'otpkey': self.otpkey, "otplen": '8'})
        token.set_description("this is a indexedsecret token export test")
        token.add_tokeninfo("hashlib", "sha256")

        # Test that all expected keys are present in the exported dictionary
        exported_data = token.export_token()

        expected_keys = ["serial", "type", "description", "otpkey"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["hashlib", "tokenkind"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        exported_data = token.export_token()
        self.assertEqual(exported_data["serial"], 'SE123456')
        self.assertEqual(exported_data["type"], "indexedsecret")
        self.assertEqual(exported_data["description"], "this is a indexedsecret token export test")
        self.assertEqual(exported_data["info_list"]["hashlib"], "sha256")
        self.assertEqual(exported_data["otpkey"], self.otpkey)
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")

        # Clean up
        remove_token(token.token.serial)

    def test_05_indexedsecret_token_import(self):
        # Define the token data to be imported
        token_data = [{
            "serial": "SE123456",
            "type": "indexedsecret",
            "description": "this is a indexedsecret token import test",
            "otpkey": self.otpkey,
            "issuer": "privacyIDEA",
            "info_list": {"hashlib": "sha256", "tokenkind": "software"}
        }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        token = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(token.token.serial, token_data[0]["serial"])
        self.assertEqual(token.type, token_data[0]["type"])
        self.assertEqual(token.token.description, token_data[0]["description"])
        self.assertEqual(token.token.get_otpkey().getKey().decode("utf-8"), token_data[0]["otpkey"])
        self.assertEqual(token.get_tokeninfo("hashlib"), "sha256")
        self.assertEqual(token.get_tokeninfo("tokenkind"), "software")

        # Clean up
        remove_token(token.token.serial)
