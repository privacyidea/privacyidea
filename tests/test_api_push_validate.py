# SPDX-FileCopyrightText: 2020 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import time
from base64 import b32encode
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.backends import default_backend
import datetime
import logging

from testfixtures import LogCapture

from .base import MyApiTestCase
from privacyidea.lib.user import User
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   get_one_token, enable_token)
from privacyidea.lib.tokenclass import ClientMode, RolloutState
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.tokens.pushtoken import (PushAction, strip_pem_headers, POLL_ONLY,
                                              DEFAULT_CHALLENGE_TEXT, PushMode)
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.smsprovider.FirebaseProvider import FirebaseConfig
from privacyidea.lib.utils import to_bytes, to_unicode, AUTH_RESPONSE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.realm import set_realm, set_default_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from . import ldap3mock

PWFILE = "tests/testdata/passwords"
HOSTSFILE = "tests/testdata/hosts"
DICT_FILE = "tests/testdata/dictionary"
FIREBASE_FILE = "tests/testdata/firebase-test.json"
CLIENT_FILE = "tests/testdata/google-services.json"
FB_CONFIG_VALS = {
    FirebaseConfig.JSON_CONFIG: FIREBASE_FILE}
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
    smartphone_public_key_pem_urlsafe = strip_pem_headers(smartphone_public_key_pem).replace("+", "-").replace("/", "_")
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
        set_policy("push1", action=f"{PushAction.WAIT}=20", scope=SCOPE.AUTH)
        set_policy("push2", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={self.firebase_config_name},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL},"
                          f"{PushAction.TTL}={TTL}")
        # Create push config
        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
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
            augmented_pubkey = f"-----BEGIN RSA PUBLIC KEY-----\n{detail.get('public_key')}\n-----END RSA PUBLIC KEY-----\n"
            parsed_server_pubkey = serialization.load_pem_public_key(
                to_bytes(augmented_pubkey),
                default_backend())
            self.assertIsInstance(parsed_server_pubkey, RSAPublicKey)
            pubkey = detail.get("public_key")

            # Now check, what is in the token in the database
            tokens = get_tokens(serial=serial)
            self.assertEqual(len(tokens), 1)
            token_obj = tokens[0]
            self.assertEqual(token_obj.token.rollout_state, "enrolled")
            self.assertTrue(token_obj.token.active)
            tokeninfo = token_obj.get_tokeninfo()
            self.assertEqual(tokeninfo.get("public_key_smartphone"), self.smartphone_public_key_pem_urlsafe)
            self.assertEqual(tokeninfo.get("firebase_token"), "firebaseT")
            self.assertEqual(tokeninfo.get("public_key_server").strip().strip("-BEGIN END RSA PUBLIC KEY-").strip(),
                             pubkey)
            # The token should also contain the firebase config
            self.assertEqual(tokeninfo.get(PushAction.FIREBASE_CONFIG), self.firebase_config_name)

        # create spass token for user
        init_token({"serial": "spass01", "type": "spass", "pin": "otppin"},
                   user=User("selfservice", self.realm1))

        # check, if the user has two tokens, now
        tokens = get_tokens(user=User("selfservice", self.realm1))
        self.assertEqual(2, len(tokens))
        self.assertEqual("push", tokens[0].type)
        self.assertEqual("spass", tokens[1].type)
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
        set_policy("push1", action=f"{PushAction.WAIT}=20", scope=SCOPE.AUTH)
        set_policy("push2", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={self.firebase_config_name},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("chalresp", action=f"{PolicyAction.CHALLENGERESPONSE}=hotp", scope=SCOPE.AUTH)
        # Create push config
        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
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
            augmented_pubkey = f"-----BEGIN RSA PUBLIC KEY-----\n{detail.get('public_key')}\n-----END RSA PUBLIC KEY-----\n"
            parsed_server_pubkey = serialization.load_pem_public_key(
                to_bytes(augmented_pubkey),
                default_backend())
            self.assertIsInstance(parsed_server_pubkey, RSAPublicKey)
            pubkey = detail.get("public_key")

            # Now check, what is in the token in the database
            tokens = get_tokens(serial=serial)
            self.assertEqual(len(tokens), 1)
            token_obj = tokens[0]
            self.assertEqual(token_obj.token.rollout_state, "enrolled")
            self.assertTrue(token_obj.token.active)
            tokeninfo = token_obj.get_tokeninfo()
            self.assertEqual(tokeninfo.get("public_key_smartphone"), self.smartphone_public_key_pem_urlsafe)
            self.assertEqual(tokeninfo.get("firebase_token"), "firebaseT")
            self.assertEqual(tokeninfo.get("public_key_server").strip().strip("-BEGIN END RSA PUBLIC KEY-").strip(),
                             pubkey)
            # The token should also contain the firebase config
            self.assertEqual(tokeninfo.get(PushAction.FIREBASE_CONFIG), self.firebase_config_name)

        # create HOTP token for user
        init_token({"serial": "hotp01", "type": "hotp", "pin": "otppin",
                    "otpkey": self.otpkey},
                   user=User("selfservice", self.realm1))

        # disable the push token
        enable_token(self.serial_push, False)
        # check, if the user has two tokens, now
        tokens = get_tokens(user=User("selfservice", self.realm1))
        self.assertEqual(2, len(tokens))
        self.assertEqual("push", tokens[0].type)
        self.assertFalse(tokens[0].is_active())
        self.assertEqual("hotp", tokens[1].type)

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

    def test_03_unfinished_enrolled_push_token(self):
        """
        * The user has a push token where the enrollment process was not completed

        A /validate/check request is sent with this PIN.
        """
        # set policy
        set_policy("push2", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={self.firebase_config_name},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        # Create push config
        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
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
            self.assertEqual(detail.get("rollout_state"), "clientwait")
            self.assertTrue("pushurl" in detail)
            # check that the new URL contains the serial number
            self.assertTrue("&serial=PIPU" in detail.get("pushurl").get("value"))
            self.assertFalse("otpkey" in detail)

        # We skip the 2nd step of the enrollment!
        # But we activate the token on purpose!
        enable_token(self.serial_push)

        # authenticate with push
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "realm": self.realm1,
                                                 "pass": "otppin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            data = res.json
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual(detail.get("message"), "Token is not yet enrolled")

        remove_token(self.serial_push)
        delete_policy("push2")

    @ldap3mock.activate
    def test_10_enroll_push(self):
        from .test_api_validate import LDAPDirectory

        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = {'LDAPURI': 'ldap://localhost',
                  'LDAPBASE': 'o=test',
                  'BINDDN': 'cn=manager,ou=example,o=test',
                  'BINDPW': 'ldaptest',
                  'LOGINNAMEATTRIBUTE': 'cn',
                  'LDAPSEARCHFILTER': '(cn=*)',
                  'USERINFO': '{ "username": "cn",'
                              '"phone" : "telephoneNumber", '
                              '"mobile" : "mobile"'
                              ', "email" : "mail", '
                              '"surname" : "sn", '
                              '"givenname" : "givenName" }',
                  'UIDTYPE': 'DN',
                  "resolver": "catchall",
                  "type": "ldapresolver"}

        r = save_resolver(params)
        self.assertTrue(r > 0)

        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # 1. set policies.
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)

        set_policy("pol_tokenlabel", scope=SCOPE.ENROLL, action=f"{PolicyAction.TOKENLABEL}=Pushy")

        # 2. authenticate user via passthru
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "pass": "alicepw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        # Set Policy scope:auth, action:enroll_via_multichallenge=push
        set_policy("pol_multienroll", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=push")
        # Set Policy scope:enrollment, action:push_config
        set_policy("pol_push2", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={self.firebase_config_name},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL},"
                          f"{PushAction.SSL_VERIFY}=1,"
                          f"{PushAction.TTL}={TTL}")
        # Create push config
        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                           "myFB", FB_CONFIG_VALS)
        self.assertTrue(r > 0)
        # Now we should get an authentication Challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "pass": "alicepw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(result.get("authentication"), "CHALLENGE")
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue("Please scan the QR code!" in detail.get("message"), detail.get("message"))
            self.assertTrue(detail.get(PolicyAction.ENROLL_VIA_MULTICHALLENGE))
            self.assertFalse(detail.get(PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL))
            # Get image and client_mode
            self.assertEqual(ClientMode.POLL, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(ClientMode.POLL, detail.get("multi_challenge")[0].get("client_mode"))
            self.assertIn("image", detail)
            self.assertIn("link", detail)
            link = detail.get("link")
            self.assertTrue(link.startswith("otpauth://pipush"))
            serial = detail.get("serial")

        # The Application starts polling, if the token is enrolled
        with self.app.test_request_context('/validate/polltransaction',
                                           method='GET',
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            # The token is not yet enrolled.
            self.assertFalse(result.get("value"))

        # The smartphone finalizes the rollout
        tok = get_one_token(serial=serial)
        enrollment_credential = tok.get_tokeninfo("enrollment_credential")
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
            augmented_pubkey = f"-----BEGIN RSA PUBLIC KEY-----\n{detail.get('public_key')}\n-----END RSA PUBLIC KEY-----\n"
            parsed_server_pubkey = serialization.load_pem_public_key(
                to_bytes(augmented_pubkey),
                default_backend())
            self.assertIsInstance(parsed_server_pubkey, RSAPublicKey)
            pubkey = detail.get("public_key")

            # Now check, what is in the token in the database
            toks = get_tokens(serial=serial)
            self.assertEqual(len(toks), 1)
            token_obj = toks[0]
            self.assertEqual(token_obj.token.rollout_state, "enrolled")
            self.assertTrue(token_obj.token.active)
            tokeninfo = token_obj.get_tokeninfo()
            self.assertEqual(tokeninfo.get("public_key_smartphone"), self.smartphone_public_key_pem_urlsafe)
            self.assertEqual(tokeninfo.get("firebase_token"), "firebaseT")
            self.assertEqual(tokeninfo.get("public_key_server").strip().strip("-BEGIN END RSA PUBLIC KEY-").strip(),
                             pubkey)
            # The token should also contain the firebase config
            self.assertEqual(tokeninfo.get(PushAction.FIREBASE_CONFIG), self.firebase_config_name)

        # The Application polls, if the token is readily enrolled
        with self.app.test_request_context('/validate/polltransaction',
                                           method='GET',
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            # Now, the token is enrolled.
            self.assertTrue(result.get("value"))

        # The Application sends /validate/check to finalize the authentication/enrollment
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        delete_policy("pol_push2")
        remove_token(serial)
        delete_realm("ldaprealm")
        delete_resolver("catchall")

    def test_15_push_with_require_presence(self):
        self.setUp_user_realms()
        # Setup PUSH policies
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        # Add the require_presence policy
        set_policy("push_require_presence", scope=SCOPE.AUTH,
                   action=f"{PushAction.REQUIRE_PRESENCE}=1")
        # Create push token for user
        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "push_pin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            detail = res.json.get("detail")
            enrollment_credential = detail.get("enrollment_credential")

        # 2nd step: as performed by the smartphone
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            detail = res.json.get("detail")
            # Now the smartphone gets a public key from the server
            self.assertIn("public_key", detail, detail)
            self.assertEqual(RolloutState.ENROLLED, detail.get("rollout_state"), detail)

        #############################################################
        # Run authentication with push token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            # Get the challenge data
            transaction_id = detail.get("transaction_id")
            challenge_messages = [m.strip() for m in detail.get("message").split(",")]
            challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
            # The correct answer is always appended to the available options
            # Updated to use JSON structure
            challenge_data = challenge.get_data()
            self.assertIsInstance(challenge_data, dict)
            self.assertEqual(challenge_data.get("type"), "push")
            self.assertEqual(challenge_data.get("mode"), PushMode.REQUIRE_PRESENCE)
            presence_answer = challenge_data.get("correct_answer")
            # Check that we get a presence required message
            challenge_text = DEFAULT_CHALLENGE_TEXT + f" Please press: {presence_answer}"
            self.assertTrue(challenge_text in challenge_messages)

        # We do poll only, so we need to poll
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        sign_string = f"{self.serial_push}|{timestamp}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        # now check that we receive the challenge when polling
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           query_string={"serial": self.serial_push,
                                                         "timestamp": timestamp,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result").get("value")
            self.assertEqual("Do you want to confirm the login?", value[0].get("question"))
            nonce = value[0].get("nonce")
        # Answer the challenge without presence option
        sign_string = f"{nonce}|{self.serial_push}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with LogCapture(level=logging.WARNING) as lc:
            with self.app.test_request_context('/ttype/push',
                                               method='POST',
                                               query_string={"serial": self.serial_push,
                                                             "timestamp": timestamp,
                                                             "signature": b32encode(sig)}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                self.assertTrue(res.json.get("result").get("status"), res.json)
                # This fails since no presence_answer was given
                self.assertFalse(res.json.get("result").get("value"), res.json)
                lc.check_present(("privacyidea.lib.tokens.pushtoken", "WARNING",
                                  "'push_require_presence' Policy is set but the presence "
                                  "answer is not present in the smartphone request!"))
        # Finalize authentication fails since the challenge has not been answered
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": "",
                                                 "transaction_id": transaction_id},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertFalse(res.json.get("result").get("value"), res.json)
            self.assertEqual("Response did not match the challenge.",
                             res.json.get("detail").get("message"), res.json)
            self.assertEqual(AUTH_RESPONSE.REJECT,
                             res.json.get("result").get("authentication"), res.json)

        # Answer the Challenge with the wrong presence_answer
        # Shift the presence answer character one to the right
        wrong_answer = chr(((ord(presence_answer) + 1 - 65) % 26) + 65)
        sign_string = f"{nonce}|{self.serial_push}|{wrong_answer}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           query_string={"serial": self.serial_push,
                                                         "timestamp": timestamp,
                                                         "presence_answer": wrong_answer,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            # This fails since the wrong presence_answer was given
            self.assertFalse(res.json.get("result").get("value"), res.json)
        # Finalize authentication still fails since the wrong answer is given
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": "",
                                                 "transaction_id": transaction_id},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertFalse(res.json.get("result").get("value"), res.json)
            self.assertEqual("Response did not match the challenge.",
                             res.json.get("detail").get("message"), res.json)
            self.assertEqual(AUTH_RESPONSE.REJECT,
                             res.json.get("result").get("authentication"), res.json)

        # Answer the Challenge with the correct answer
        sign_string = f"{nonce}|{self.serial_push}|{presence_answer}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           query_string={"serial": self.serial_push,
                                                         "timestamp": timestamp,
                                                         "presence_answer": presence_answer,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertTrue(res.json.get("result").get("value"), res.json)
        # Finalize authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": "",
                                                 "transaction_id": transaction_id},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            self.assertEqual(AUTH_RESPONSE.ACCEPT,
                             res.json.get("result").get("authentication"), res.json)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_require_presence")

    def test_16_push_require_presence_with_push_wait(self):
        self.setUp_user_realms()
        # Setup PUSH policies
        set_policy("pol_push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        # Add the require_presence policy
        set_policy("pol_push_require_presence", scope=SCOPE.AUTH,
                   action=f"{PushAction.REQUIRE_PRESENCE}=1")
        # Add the push_wait policy (set timeout to 1 second to avoid blocking the tests)
        set_policy("pol_push_wait", scope=SCOPE.AUTH,
                   action=f"{PushAction.WAIT}=1")
        # Create push token for user
        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "push_pin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            detail = res.json.get("detail")
            enrollment_credential = detail.get("enrollment_credential")

        # 2nd step: as performed by the smartphone
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            detail = res.json.get("detail")
            # Now the smartphone gets a public key from the server
            self.assertIn("public_key", detail, detail)
            self.assertEqual(RolloutState.ENROLLED, detail.get("rollout_state"), detail)

        #############################################################
        # Run authentication with push token and with push_wait
        with LogCapture(level=logging.WARNING) as lc:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "selfservice",
                                                     "pass": "push_pin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                detail = res.json.get("detail")
                self.assertTrue(res.json.get("result").get("status"), res.json)
                self.assertFalse(res.json.get("result").get("value"), res.json)
                self.assertEqual(AUTH_RESPONSE.REJECT,
                                 res.json.get("result").get("authentication"), res.json)
                self.assertEqual("wrong otp value", detail.get("message"), detail)
                lc.check_present(("privacyidea.lib.tokens.pushtoken", "WARNING",
                                  "Unable to use 'require_presence' policy with 'push_wait'. "
                                  "Disabling 'require_presence' policy!"))

        remove_token(self.serial_push)
        delete_policy("pol_push_config")
        delete_policy("pol_push_require_presence")
        delete_policy("pol_push_wait")

    def test_17_push_code_to_phone(self):
        """
        Test the push token in code_to_phone mode.
        This is a 2-step process:
        1. A challenge is created and pushed to the smartphone. The smartphone confirms by signing
           the challenge. After confirmation, a short display_code is generated and returned to the
           smartphone for display.
        2. The user enters the display_code from the smartphone into the client, which sends it via
           /validate/check to complete the authentication.
        """

        self.setUp_user_realms()
        # Setup PUSH policies
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("push_mode_code_to_phone", scope=SCOPE.AUTH,
                   action=f"{PushAction.PUSH_CODE_TO_PHONE}=1")

        expected_message = 'test message'
        set_policy("code_to_phone_message", scope=SCOPE.AUTH,
                   action=f"{PushAction.PUSH_CODE_TO_PHONE_MESSAGE}={expected_message}")
        # Create push token for user init step 1
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "push_pin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            detail = res.json.get("detail")
            enrollment_credential = detail.get("enrollment_credential")

        # init 2nd step
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            detail = res.json.get("detail")
            self.assertIn("public_key", detail, detail)
            self.assertEqual(RolloutState.ENROLLED, detail.get("rollout_state"), detail)

        # trigger challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            detail = res.json.get("detail")
            # Get the challenge data
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)
            # The result should be a challenge
            self.assertEqual(AUTH_RESPONSE.CHALLENGE, res.json.get("result").get("authentication"), res.json)
            # The client_mode should be INTERACTIVE so the client shows an input field
            multi_challenge = detail.get("multi_challenge", [{}])
            self.assertEqual(ClientMode.INTERACTIVE, multi_challenge[0].get("client_mode"))

            # Check that the challenge data has the correct structure for 2-step code_to_phone
            challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
            challenge_data = challenge.get_data()
            self.assertIsInstance(challenge_data, dict)
            self.assertEqual("push", challenge_data.get("type"))
            self.assertEqual(PushMode.CODE_TO_PHONE, challenge_data.get("mode"))
            # Smartphone has not responded yet and no display_code has been created yet
            self.assertFalse(challenge_data.get("smartphone_confirmed"))
            self.assertNotIn("display_code", challenge_data)

        # Step 1b: Smartphone polls for the challenge
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        sign_string = f"{self.serial_push}|{timestamp}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        # Poll to get the challenge (should show as standard challenge, no display_code)
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           query_string={"serial": self.serial_push,
                                                         "timestamp": timestamp,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result").get("value")
            self.assertTrue(len(value) > 0)
            # No display_code should be present (smartphone just confirms)
            self.assertNotIn("display_code", value[0])
            # Get the nonce for signing
            challenge_nonce = value[0].get("nonce")

        # Step 1c: Smartphone confirms by signing the challenge
        sign_data = f"{challenge_nonce}|{self.serial_push}"
        sig = self.smartphone_private_key.sign(sign_data.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": self.serial_push,
                                                 "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            # The response should contain the display_code for the smartphone to display
            detail = res.json.get("detail")
            display_code = detail.get("display_code")
            self.assertTrue(display_code)
            self.assertEqual(2, len(display_code))
            # Check that there is a second message for showing the code to the user on the phone
            self.assertIn("message", detail)
            self.assertEqual(expected_message, detail["message"])

        # Verify challenge data was updated
        challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
        challenge_data = challenge.get_data()
        self.assertTrue(challenge_data.get("smartphone_confirmed"))
        self.assertEqual(display_code, challenge_data.get("display_code"))

        # Step 2: Finalize authentication with the display_code
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": display_code,
                                                 "transaction_id": transaction_id},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            self.assertEqual(AUTH_RESPONSE.ACCEPT,
                             res.json.get("result").get("authentication"), res.json)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")
        delete_policy("code_to_phone_message")

    def test_18_push_code_to_phone_fail(self):
        """
        Test the push token in code_to_phone mode with a wrong display_code.
        """

        self.setUp_user_realms()
        # Setup PUSH policies
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("push_mode_code_to_phone", scope=SCOPE.AUTH,
                   action=f"{PushAction.PUSH_CODE_TO_PHONE}=1")
        # Create push token for user
        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "push_pin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            detail = res.json.get("detail")
            enrollment_credential = detail.get("enrollment_credential")

        # 2nd step: as performed by the smartphone
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            detail = res.json.get("detail")
            # Now the smartphone gets a public key from the server
            self.assertIn("public_key", detail, detail)
            self.assertEqual(RolloutState.ENROLLED, detail.get("rollout_state"), detail)

        # Verify failcount before, should be 0
        token = get_tokens(serial=self.serial_push)[0]
        self.assertEqual(0, token.token.failcount)

        #############################################################
        # Run authentication with push token - Step 1: create challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            detail = res.json.get("detail")
            # Get the challenge data
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)
            # The result should be a challenge
            self.assertEqual(AUTH_RESPONSE.CHALLENGE,
                             res.json.get("result").get("authentication"), res.json)

            # Check that the challenge data has the correct structure
            challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
            challenge_data = challenge.get_data()
            self.assertIsInstance(challenge_data, dict)
            self.assertEqual(challenge_data.get("type"), "push")
            self.assertEqual(challenge_data.get("mode"), PushMode.CODE_TO_PHONE)
            self.assertFalse(challenge_data.get("smartphone_confirmed"))

        # Step 1b: Smartphone polls for the challenge
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        sign_string = f"{self.serial_push}|{timestamp}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           query_string={"serial": self.serial_push,
                                                         "timestamp": timestamp,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result").get("value")
            challenge_nonce = value[0].get("nonce")

        # Step 1c: Smartphone confirms
        sign_data = f"{challenge_nonce}|{self.serial_push}"
        sig = self.smartphone_private_key.sign(sign_data.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": self.serial_push,
                                                 "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            detail = res.json.get("detail")
            display_code = detail.get("display_code")
            self.assertTrue(display_code)

        # Finalize authentication with the WRONG display_code
        wrong_code = "00" if display_code != "00" else "01"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": wrong_code,
                                                 "transaction_id": transaction_id},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertFalse(res.json.get("result").get("value"), res.json)
            self.assertEqual(AUTH_RESPONSE.REJECT,
                             res.json.get("result").get("authentication"), res.json)

            # Check failcounter after, has been increased
            token = get_tokens(serial=self.serial_push)[0]
            self.assertEqual(1, token.token.failcount)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")

    def test_18a_push_code_to_phone_before_smartphone_confirms(self):
        """
        Test that entering a display_code before the smartphone has confirmed the challenge
        results in a REJECT.
        """
        self.setUp_user_realms()
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("push_mode_code_to_phone", scope=SCOPE.AUTH,
                   action=f"{PushAction.PUSH_CODE_TO_PHONE}=1")

        # Create and enroll push token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "push_pin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            enrollment_credential = res.json.get("detail").get("enrollment_credential")

        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

        # Create challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)
            self.assertEqual(AUTH_RESPONSE.CHALLENGE,
                             res.json.get("result").get("authentication"), res.json)

        # Verify smartphone has NOT confirmed yet
        challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
        challenge_data = challenge.get_data()
        self.assertFalse(challenge_data.get("smartphone_confirmed"))

        # Try to finalize authentication with a code BEFORE the smartphone confirms
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": "42",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"), res.json)
            self.assertFalse(res.json.get("result").get("value"), res.json)
            self.assertEqual(AUTH_RESPONSE.REJECT,
                             res.json.get("result").get("authentication"), res.json)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")

    def test_18b_push_code_to_phone_smartphone_declines(self):
        """
        Test that if the smartphone declines the challenge in code_to_phone mode,
        the authentication is rejected.
        """
        self.setUp_user_realms()
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("push_mode_code_to_phone", scope=SCOPE.AUTH,
                   action=f"{PushAction.PUSH_CODE_TO_PHONE}=1")

        # Create and enroll push token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "push_pin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            enrollment_credential = res.json.get("detail").get("enrollment_credential")

        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

        # Create challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)

        # Smartphone polls for the challenge
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        sign_string = f"{self.serial_push}|{timestamp}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           query_string={"serial": self.serial_push,
                                                         "timestamp": timestamp,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result").get("value")
            challenge_nonce = value[0].get("nonce")

        # Smartphone DECLINES the challenge
        sign_data = f"{challenge_nonce}|{self.serial_push}|decline"
        sig = self.smartphone_private_key.sign(sign_data.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": self.serial_push,
                                                 "signature": b32encode(sig),
                                                 "decline": "1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            # Decline is accepted
            self.assertTrue(res.json.get("result").get("value"), res.json)
            # No display_code should be returned for a declined challenge
            detail = res.json.get("detail") or {}
            self.assertNotIn("display_code", detail)

        # Verify challenge was not confirmed
        challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
        challenge_data = challenge.get_data()
        self.assertFalse(challenge_data.get("smartphone_confirmed"))

        # Trying to authenticate with any code should fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": "42",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertFalse(res.json.get("result").get("value"), res.json)
            self.assertEqual(AUTH_RESPONSE.REJECT,
                             res.json.get("result").get("authentication"), res.json)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")

    def test_19_push_code_to_phone_with_require_presence(self):
        """
        Test that if both code_to_phone and require_presence are enabled, require_presence takes
        precedence: challenge mode is REQUIRE_PRESENCE, client_mode is POLL (not INTERACTIVE),
        /polltransaction reports the correct status, and the full auth flow completes successfully.
        """
        self.setUp_user_realms()
        # Setup PUSH policies
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("push_mode_code_to_phone", scope=SCOPE.AUTH, action=f"{PushAction.PUSH_CODE_TO_PHONE}=1")
        set_policy("push_require_presence", scope=SCOPE.AUTH, action=f"{PushAction.REQUIRE_PRESENCE}=1")

        # Enrollment step 1
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "push_pin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            detail = res.json.get("detail")
            enrollment_credential = detail.get("enrollment_credential")

        # Enrollment step 2 (smartphone)
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

        # Trigger challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)
            self.assertEqual(AUTH_RESPONSE.CHALLENGE, res.json.get("result").get("authentication"), res.json)
            # require_presence takes precedence: client_mode must be POLL, not INTERACTIVE
            multi_challenge = detail.get("multi_challenge", [{}])
            self.assertEqual(ClientMode.POLL, multi_challenge[0].get("client_mode"))
            # Challenge data must be in REQUIRE_PRESENCE mode with no display_code
            challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
            challenge_data = challenge.get_data()
            self.assertIsInstance(challenge_data, dict)
            self.assertEqual(challenge_data.get("type"), "push")
            self.assertEqual(challenge_data.get("mode"), PushMode.REQUIRE_PRESENCE)
            self.assertNotIn("display_code", challenge_data)
            presence_answer = challenge_data.get("correct_answer")

        # /polltransaction: challenge not yet answered
        with self.app.test_request_context('/validate/polltransaction',
                                           method='GET',
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertFalse(res.json.get("result").get("value"), res.json)
            self.assertEqual("pending", res.json.get("detail").get("challenge_status"), res.json)

        # Smartphone polls for the challenge
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        sign_string = f"{self.serial_push}|{timestamp}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           query_string={"serial": self.serial_push,
                                                         "timestamp": timestamp,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result").get("value")
            self.assertTrue(len(value) > 0)
            # Presence options must be present; no display_code (not code_to_phone mode)
            self.assertIn("require_presence", value[0])
            self.assertNotIn("display_code", value[0])
            nonce = value[0].get("nonce")

        # Smartphone answers with the correct presence_answer
        sign_string = f"{nonce}|{self.serial_push}|{presence_answer}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           query_string={"serial": self.serial_push,
                                                         "timestamp": timestamp,
                                                         "presence_answer": presence_answer,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            # No display_code should be returned — this is require_presence, not code_to_phone
            self.assertNotIn("display_code", res.json.get("detail") or {})

        # /polltransaction: challenge is now answered
        with self.app.test_request_context('/validate/polltransaction',
                                           method='GET',
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            self.assertEqual("accept", res.json.get("detail").get("challenge_status"), res.json)

        # Finalize authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": "",
                                                 "transaction_id": transaction_id},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            self.assertEqual(AUTH_RESPONSE.ACCEPT,
                             res.json.get("result").get("authentication"), res.json)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")
        delete_policy("push_require_presence")

    def test_20_push_code_to_phone_with_push_wait(self):
        """
        Test that if both code_to_phone and push_wait are enabled, push_wait takes precedence.
        """
        self.setUp_user_realms()
        push_wait_time_seconds = 5
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("push_mode_code_to_phone", scope=SCOPE.AUTH, action=f"{PushAction.PUSH_CODE_TO_PHONE}=1")
        set_policy("push_wait", scope=SCOPE.AUTH, action=f"{PushAction.WAIT}={push_wait_time_seconds}")

        # Create Token Init
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": "push_pin",
                                                 "user": "selfservice",
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            detail = res.json.get("detail")
            enrollment_credential = detail.get("enrollment_credential")

        # Complete Creation
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

        # Authentication
        start_time = time.time()
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            # Check that we actually waited
            self.assertGreater(time.time() - start_time, push_wait_time_seconds-1)
            result = res.json.get("result")
            # The challenge was not answered in time, so we get reject
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(AUTH_RESPONSE.REJECT, result.get("authentication"))

            # Check the challenge data as well
            challenge = get_challenges()[0]
            challenge_data = challenge.get_data()
            self.assertIsInstance(challenge_data, dict)
            self.assertEqual(challenge_data.get("type"), "push")
            # STANDARD takes precedence because push_wait disables code_to_phone
            self.assertEqual(challenge_data.get("mode"), PushMode.STANDARD)
            self.assertNotIn("display_code", challenge_data)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")
        delete_policy("push_wait")
