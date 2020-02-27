"""
This test file tests the lib.tokens.smstoken
"""

from .base import MyTestCase
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import (User)
from privacyidea.lib.tokens.indexedsecrettoken import IndexedSecretTokenClass
from privacyidea.models import Token
from privacyidea.lib.token import init_token, remove_token

PWFILE = "tests/testdata/passwords"


class IndexedSecretTokenTestCase(MyTestCase):
    """
    Test the Email Token
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

        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1])
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
        r, message, transaction_id, attribute = token.create_challenge()
        self.assertTrue(r)
        self.assertIn("Please enter the position", message)

        password_list = [my_secret[x-1] for x in attribute.get("random_positions")]
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
        t = init_token({"type": "indexedsecret",
                        "otpkey": "MySecret",
                        "serial": "PIIX1234"})
        self.assertEqual(t.token.tokentype, "indexedsecret")
        self.assertEqual(t.token.serial, "PIIX1234")

        remove_token("PIIX1234")