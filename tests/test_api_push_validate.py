# -*- coding: utf-8 -*-
from .base import MyApiTestCase
from privacyidea.lib.user import User
from privacyidea.lib.token import get_tokens, init_token, remove_token
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.tokens.pushtoken import PUSH_ACTION, strip_key
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.smsprovider.FirebaseProvider import FIREBASE_CONFIG
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.backends import default_backend
from privacyidea.lib.utils import to_bytes, to_unicode
from cryptography.hazmat.primitives.asymmetric import rsa
from privacyidea.lib.policy import ACTION

PWFILE = "tests/testdata/passwords"
HOSTSFILE = "tests/testdata/hosts"
DICT_FILE = "tests/testdata/dictionary"
FIREBASE_FILE = "tests/testdata/firebase-test.json"
CLIENT_FILE = "tests/testdata/google-services.json"
FB_CONFIG_VALS = {
    FIREBASE_CONFIG.API_KEY: "1",
    FIREBASE_CONFIG.APP_ID: "2",
    FIREBASE_CONFIG.PROJECT_NUMBER: "3",
    FIREBASE_CONFIG.PROJECT_ID: "test-123456",
    FIREBASE_CONFIG.JSON_CONFIG: FIREBASE_FILE}
REGISTRATION_URL = "http://test/ttype/push"
TTL = "10"


class PushAPITestCase(MyApiTestCase):
    """
    test the api.validate endpoints
    """

    server_private_key = rsa.generate_private_key(public_exponent=65537,
                                                  key_size=4096,
                                                  backend=default_backend())
    server_private_key_pem = to_unicode(server_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()))
    server_public_key_pem = to_unicode(server_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo))

    # We now allow white spaces in the firebase config name
    firebase_config_name = "my firebase config"

    smartphone_private_key = rsa.generate_private_key(public_exponent=65537,
                                                      key_size=4096,
                                                      backend=default_backend())
    smartphone_public_key = smartphone_private_key.public_key()
    smartphone_public_key_pem = to_unicode(smartphone_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo))
    # The smartphone sends the public key in URLsafe and without the ----BEGIN header
    smartphone_public_key_pem_urlsafe = strip_key(smartphone_public_key_pem).replace("+", "-").replace("/", "_")
    serial_push = "PIPU001"

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_push_token_reorder_list(self):
        """
        * Policy push_wait
        * The user has two tokens. SPASS and Push with the same PIN.

        A /validate/check request is sent with this PIN.
        The PIN could trigger a challenge response with the Push, but since the
        token list is reordered and the Spass token already successfully authenticates,
        the push token is not evaluated anymore.
        """
        # set policy
        set_policy("push1", action="{0!s}=20".format(PUSH_ACTION.WAIT), scope=SCOPE.AUTH)
        set_policy("push2", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       PUSH_ACTION.FIREBASE_CONFIG, self.firebase_config_name,
                       PUSH_ACTION.REGISTRATION_URL, REGISTRATION_URL,
                       PUSH_ACTION.TTL, TTL))
        # Create push config
        r = set_smsgateway(self.firebase_config_name,
                           u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                           "myFB", FB_CONFIG_VALS)
        self.assertTrue(r > 0)

        # create push token for user
        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "otppin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(detail.get("rollout_state"), "clientwait")
            self.assertTrue("pushurl" in detail)
            # check that the new URL contains the serial number
            self.assertTrue("&serial=PIPU" in detail.get("pushurl").get("value"))
            self.assertTrue("appid=" in detail.get("pushurl").get("value"))
            self.assertTrue("appidios=" in detail.get("pushurl").get("value"))
            self.assertTrue("apikeyios=" in detail.get("pushurl").get("value"))
            self.assertFalse("otpkey" in detail)
            enrollment_credential = detail.get("enrollment_credential")

        # 2nd step: as performed by the smartphone
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": serial,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            # still the same serial number
            self.assertEqual(serial, detail.get("serial"))
            self.assertEqual(detail.get("rollout_state"), "enrolled")
            # Now the smartphone gets a public key from the server
            augmented_pubkey = "-----BEGIN RSA PUBLIC KEY-----\n{}\n-----END RSA PUBLIC KEY-----\n".format(
                detail.get("public_key"))
            parsed_server_pubkey = serialization.load_pem_public_key(
                to_bytes(augmented_pubkey),
                default_backend())
            self.assertIsInstance(parsed_server_pubkey, RSAPublicKey)
            pubkey = detail.get("public_key")

            # Now check, what is in the token in the database
            toks = get_tokens(serial=serial)
            self.assertEqual(len(toks), 1)
            token_obj = toks[0]
            self.assertEqual(token_obj.token.rollout_state, u"enrolled")
            self.assertTrue(token_obj.token.active)
            tokeninfo = token_obj.get_tokeninfo()
            self.assertEqual(tokeninfo.get("public_key_smartphone"), self.smartphone_public_key_pem_urlsafe)
            self.assertEqual(tokeninfo.get("firebase_token"), u"firebaseT")
            self.assertEqual(tokeninfo.get("public_key_server").strip().strip("-BEGIN END RSA PUBLIC KEY-").strip(),
                             pubkey)
            # The token should also contain the firebase config
            self.assertEqual(tokeninfo.get(PUSH_ACTION.FIREBASE_CONFIG), self.firebase_config_name)

        # create spass token for user
        init_token({"serial": "spass01", "type": "spass", "pin": "otppin"},
                   user=User("selfservice", self.realm1))

        # check, if the user has two tokens, now
        toks = get_tokens(user=User("selfservice", self.realm1))
        self.assertEqual(2, len(toks))
        self.assertEqual("push", toks[0].type)
        self.assertEqual("spass", toks[1].type)
        # authenticate with spass
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "realm": self.realm1,
                                                 "pass": "otppin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            data = res.json
            self.assertTrue(data.get("result").get("value"))
            # successful auth with spass
            self.assertEqual("spass", data.get("detail").get("type"))

        remove_token(self.serial_push)
        remove_token("spass01")
        delete_policy("push1")
        delete_policy("push2")

    def test_02_push_token_do_not_wait_if_disabled(self):
        """
        * Policy push_wait
        * The user has two tokens. HOTP chal-resp and Push with the same PIN.
        * But in this case, the push token is disabled.
        * The user should get the response immediately.

        A /validate/check request is sent with this PIN.
        The PIN will only trigger the HOTP, push will not wait, since it is disabled.
        """
        # set policy
        set_policy("push1", action="{0!s}=20".format(PUSH_ACTION.WAIT), scope=SCOPE.AUTH)
        set_policy("push2", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s}".format(
                       PUSH_ACTION.FIREBASE_CONFIG, self.firebase_config_name,
                       PUSH_ACTION.REGISTRATION_URL, REGISTRATION_URL))
        set_policy("chalresp", action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE), scope=SCOPE.AUTH)
        # Create push config
        r = set_smsgateway(self.firebase_config_name,
                           u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                           "myFB", FB_CONFIG_VALS)
        self.assertTrue(r > 0)

        # create push token for user
        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "otppin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(detail.get("rollout_state"), "clientwait")
            self.assertTrue("pushurl" in detail)
            # check that the new URL contains the serial number
            self.assertTrue("&serial=PIPU" in detail.get("pushurl").get("value"))
            self.assertTrue("appid=" in detail.get("pushurl").get("value"))
            self.assertTrue("appidios=" in detail.get("pushurl").get("value"))
            self.assertTrue("apikeyios=" in detail.get("pushurl").get("value"))
            self.assertFalse("otpkey" in detail)
            enrollment_credential = detail.get("enrollment_credential")

        # 2nd step: as performed by the smartphone
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": serial,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            # still the same serial number
            self.assertEqual(serial, detail.get("serial"))
            self.assertEqual(detail.get("rollout_state"), "enrolled")
            # Now the smartphone gets a public key from the server
            augmented_pubkey = "-----BEGIN RSA PUBLIC KEY-----\n{}\n-----END RSA PUBLIC KEY-----\n".format(
                detail.get("public_key"))
            parsed_server_pubkey = serialization.load_pem_public_key(
                to_bytes(augmented_pubkey),
                default_backend())
            self.assertIsInstance(parsed_server_pubkey, RSAPublicKey)
            pubkey = detail.get("public_key")

            # Now check, what is in the token in the database
            toks = get_tokens(serial=serial)
            self.assertEqual(len(toks), 1)
            token_obj = toks[0]
            self.assertEqual(token_obj.token.rollout_state, u"enrolled")
            self.assertTrue(token_obj.token.active)
            tokeninfo = token_obj.get_tokeninfo()
            self.assertEqual(tokeninfo.get("public_key_smartphone"), self.smartphone_public_key_pem_urlsafe)
            self.assertEqual(tokeninfo.get("firebase_token"), u"firebaseT")
            self.assertEqual(tokeninfo.get("public_key_server").strip().strip("-BEGIN END RSA PUBLIC KEY-").strip(),
                             pubkey)
            # The token should also contain the firebase config
            self.assertEqual(tokeninfo.get(PUSH_ACTION.FIREBASE_CONFIG), self.firebase_config_name)

        # create HOTP token for user
        init_token({"serial": "hotp01", "type": "hotp", "pin": "otppin",
                    "otpkey": self.otpkey},
                   user=User("selfservice", self.realm1))

        from privacyidea.lib.token import enable_token
        # disable the push token
        enable_token(self.serial_push, False)
        # check, if the user has two tokens, now
        toks = get_tokens(user=User("selfservice", self.realm1))
        self.assertEqual(2, len(toks))
        self.assertEqual("push", toks[0].type)
        self.assertFalse(toks[0].is_active())
        self.assertEqual("hotp", toks[1].type)

        # authenticate with hotp
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "realm": self.realm1,
                                                 "pass": "otppin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            data = res.json
            self.assertFalse(data.get("result").get("value"))
            # This is the auth-request for the HOTP token
            detail = data.get("detail")
            multi_challenge = detail.get("multi_challenge")
            self.assertEqual(multi_challenge[0].get("type"), "hotp")
            self.assertEqual(multi_challenge[0].get("serial"), "hotp01")
            self.assertEqual("interactive", multi_challenge[0].get("client_mode"))

        remove_token(self.serial_push)
        remove_token("hotp01")
        delete_policy("push1")
        delete_policy("push2")
        delete_policy("chalresp")
