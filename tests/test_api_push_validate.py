# SPDX-FileCopyrightText: 2020 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import datetime
import logging
import threading
import time
from base64 import b32encode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from testfixtures import LogCapture

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.realm import set_realm, set_default_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.smsprovider.FirebaseProvider import FirebaseConfig
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   get_one_token, enable_token)
from privacyidea.lib.tokenclass import ClientMode
from privacyidea.lib.tokenrolloutstate import RolloutState
from privacyidea.lib.tokens.pushtoken import (PushAction, strip_pem_headers, POLL_ONLY,
                                              DEFAULT_CHALLENGE_TEXT, PushMode)
from privacyidea.lib.user import User
from privacyidea.lib.utils import to_bytes, to_unicode, AUTH_RESPONSE
from privacyidea.models import db, Challenge
from privacyidea.models.authentication_log import AuthenticationLog
from . import ldap3mock
from .authlog_utils import assert_authentication_log, assert_authentication_log_entry
from .base import MyApiTestCase

PWFILE = "tests/testdata/passwords"
HOSTSFILE = "tests/testdata/hosts"
DICT_FILE = "tests/testdata/dictionary"
FIREBASE_FILE = "tests/testdata/firebase-test.json"
CLIENT_FILE = "tests/testdata/google-services.json"
FB_CONFIG_VALS = {
    FirebaseConfig.JSON_CONFIG: FIREBASE_FILE}
REGISTRATION_URL = "http://test/ttype/push"
TTL = "10"


def clear_log():
    db.session.query(AuthenticationLog).delete()
    db.session.commit()


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
            self.assertEqual(detail.get("rollout_state"), RolloutState.CLIENTWAIT)
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
            self.assertEqual(detail.get("rollout_state"), RolloutState.ENROLLED)
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
            self.assertEqual(token_obj.token.rollout_state, RolloutState.ENROLLED)
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
            self.assertEqual(detail.get("rollout_state"), RolloutState.CLIENTWAIT)
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
            self.assertEqual(detail.get("rollout_state"), RolloutState.ENROLLED)
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
            self.assertEqual(token_obj.token.rollout_state, RolloutState.ENROLLED)
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
            self.assertEqual(detail.get("rollout_state"), RolloutState.CLIENTWAIT)
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
            self.assertEqual(detail.get("rollout_state"), RolloutState.ENROLLED)
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
            self.assertEqual(token_obj.token.rollout_state, RolloutState.ENROLLED)
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

        user = User("selfservice", self.realm1)

        # The PIN trigger creates the challenge -> CHALLENGE_TRIGGERED (carries the user).
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # We do poll only, so we need to poll (polling does not create an auth-log entry)
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

        # Answer the challenge without presence option: the smartphone /ttype confirm fails (missing presence
        # answer) -> CHALLENGE_ANSWERED_FAIL
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Finalize fails since the challenge has not been answered -> CHALLENGE_ANSWERED_FAIL
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        client_label="privacyidea-cp/2.0", transaction_id=transaction_id)

        # Answer with the wrong presence_answer: the smartphone /ttype confirm fails -> CHALLENGE_ANSWERED_FAIL
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Finalize still fails since the wrong answer was given -> CHALLENGE_ANSWERED_FAIL
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        client_label="privacyidea-cp/2.0", transaction_id=transaction_id)

        # Answer with the correct presence answer: the smartphone /ttype confirm succeeds -> CHALLENGE_ANSWERED_OK
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Finalize now succeeds -> LOGIN_SUCCESS
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        client_label="privacyidea-cp/2.0", transaction_id=transaction_id)

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
        clear_log()
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

        # require_presence is disabled by push_wait, so this is a standard push_wait that times out: recorded only as
        # CHALLENGE_TRIGGERED, not an MFA_FAIL.
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("selfservice", self.realm1),
                                        serials={self.serial_push},
                                        transaction_id=get_challenges()[0].transaction_id)

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
        individual_message = "Please confirm on your smartphone and enter the code here."
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("push_mode_code_to_phone", scope=SCOPE.AUTH,
                   action=f"{PushAction.PUSH_CODE_TO_PHONE}=1")
        set_policy("push_challenge_text", scope=SCOPE.AUTH,
                   action=f"{PushAction.CHALLENGE_TEXT}={individual_message}")

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

        user = User("selfservice", self.realm1)

        # trigger challenge -> CHALLENGE_TRIGGERED
        clear_log()
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            detail = res.json.get("detail")
            # Check the message
            self.assertEqual(individual_message, detail.get("message"), res.json)
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Step 1b: Smartphone polls for the challenge (polling creates no auth-log entry)
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

        # Step 1c: Smartphone confirms by signing the challenge -> CHALLENGE_TRIGGERED
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_CONTINUED])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Verify challenge data was updated
        challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
        challenge_data = challenge.get_data()
        self.assertTrue(challenge_data.get("smartphone_confirmed"))
        self.assertEqual(display_code, challenge_data.get("display_code"))

        # Step 2: Finalize authentication with the display_code -> CHALLENGE_ANSWERED_OK
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        client_label="privacyidea-cp/2.0", transaction_id=transaction_id)

        # Verify backwards-compat fallback: with the push-specific policy removed,
        # the generic challenge_text policy is honored on the next challenge.
        delete_policy("push_challenge_text")
        generic_message = "Generic challenge text fallback."
        set_policy("generic_challenge_text", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGETEXT}={generic_message}")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(generic_message, res.json.get("detail").get("message"), res.json)

        # Verify precedence: when both policies are set, push_challenge_text wins.
        set_policy("push_challenge_text", scope=SCOPE.AUTH,
                   action=f"{PushAction.CHALLENGE_TEXT}={individual_message}")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(individual_message, res.json.get("detail").get("message"), res.json)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")
        delete_policy("code_to_phone_message")
        delete_policy("generic_challenge_text")
        delete_policy("push_challenge_text")

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

        user = User("selfservice", self.realm1)

        # Step 1: create challenge -> CHALLENGE_TRIGGERED
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Step 1b: Smartphone polls for the challenge (polling creates no auth-log entry)
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

        # Step 1c: Smartphone confirms -> CHALLENGE_TRIGGERED
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_CONTINUED])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Finalize authentication with the WRONG display_code -> CHALLENGE_ANSWERED_FAIL
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        client_label="privacyidea-cp/2.0", transaction_id=transaction_id)

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
        clear_log()
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

        # check auth log entries
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(auth_log_entries.all[0], user=User("selfservice", self.realm1),
                                        serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Try to finalize authentication with a code BEFORE the smartphone confirms
        clear_log()
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

        # check auth log entries
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(auth_log_entries.all[0], user=User("selfservice", self.realm1),
                                        serials={self.serial_push},
                                        transaction_id=transaction_id)

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

        user = User("selfservice", self.realm1)

        # Create challenge -> CHALLENGE_TRIGGERED
        clear_log()
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Smartphone polls for the challenge (polling creates no auth-log entry)
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

        # Smartphone DECLINES the challenge -> CHALLENGE_DECLINED
        clear_log()
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
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_DECLINED])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Verify challenge was not confirmed
        challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
        challenge_data = challenge.get_data()
        self.assertFalse(challenge_data.get("smartphone_confirmed"))

        # Trying to authenticate with any code should fail -> CHALLENGE_ANSWERED_FAIL
        clear_log()
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "pass": "42",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertFalse(res.json.get("result").get("value"), res.json)
            self.assertEqual(AUTH_RESPONSE.REJECT,
                             res.json.get("result").get("authentication"), res.json)
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(auth_log_entries.all[0], user=user, serials={self.serial_push},
                                        transaction_id=transaction_id)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")

    def test_18c_authentication_log_push_states(self):
        """
        Full authentication-log coverage for the push flow. The PIN step at
        /validate/check logs CHALLENGE_TRIGGERED; /ttype/push (the only point
        reached for every smartphone response) logs the answer
        (CHALLENGE_ANSWERED_OK / CHALLENGE_DECLINED / CHALLENGE_ANSWERED_FAIL);
        the finalizing /validate/check collects the answered challenge.

        The smartphone request does not send a transaction_id, but /ttype/push
        recovers it from the answered challenge (or, on a failed signature, from
        the single open challenge) so its rows correlate to the rest of the
        attempt; it also resolves the token owner so the rows carry the user.
        The log is cleared per scenario and the whole ordered event list,
        including the transaction_id, is asserted.
        """
        self.setUp_user_realms()
        user = User("selfservice", self.realm1)
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")

        with self.app.test_request_context('/token/init', method='POST',
                                           data={"type": "push", "pin": "push_pin",
                                                 "user": "selfservice", "realm": self.realm1,
                                                 "serial": self.serial_push, "genkey": 1},
                                           headers={'Authorization': self.at}):
            result = self.app.full_dispatch_request()
            enrollment_credential = result.json.get("detail").get("enrollment_credential")
        with self.app.test_request_context('/ttype/push', method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            self.assertEqual(200, self.app.full_dispatch_request().status_code)

        def clear_log_and_challenges():
            db.session.query(AuthenticationLog).delete()
            db.session.query(Challenge).delete()
            db.session.commit()

        def trigger_and_poll():
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "selfservice", "pass": "push_pin"}):
                result = self.app.full_dispatch_request()
                tid = result.json["detail"]["transaction_id"]
            timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
            poll_sig = self.smartphone_private_key.sign(f"{self.serial_push}|{timestamp}".encode("utf8"),
                                                        padding.PKCS1v15(), hashes.SHA256())
            with self.app.test_request_context('/ttype/push', method='GET',
                                               query_string={"serial": self.serial_push,
                                                             "timestamp": timestamp,
                                                             "signature": b32encode(poll_sig)}):
                result = self.app.full_dispatch_request()
                return tid, result.json["result"]["value"][0]["nonce"]

        def sign_and_post(sign_data, extra_data=None):
            signature = self.smartphone_private_key.sign(sign_data.encode("utf8"),
                                                         padding.PKCS1v15(), hashes.SHA256())
            data = {"serial": self.serial_push, "signature": b32encode(signature)}
            data.update(extra_data or {})
            with self.app.test_request_context('/ttype/push', method='POST', data=data):
                return self.app.full_dispatch_request()

        def finalize(transaction_id):
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "selfservice", "pass": "",
                                                     "transaction_id": transaction_id}):
                return self.app.full_dispatch_request()

        # Accept: PIN step triggers, the phone confirms, the client collects the result.
        clear_log_and_challenges()
        transaction_id, nonce = trigger_and_poll()
        sign_and_post(f"{nonce}|{self.serial_push}")
        finalize(transaction_id)
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED,
                                                  AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND,
                                                  AuthEventType.LOGIN_SUCCESS])
        # All three rows correlate to the attempt via the same transaction_id: the PIN trigger and the
        # /validate/check collection echo the request parameter, the /ttype/push confirm recovers it from the
        # answered challenge.
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=user, serials={self.serial_push}, transaction_id=transaction_id)
        # CHALLENGE_ANSWERED_OK occurs twice, so assert each occurrence by position:
        # .all[1] is the smartphone confirm at /ttype/push, .all[2] is the client collecting the result at
        # /validate/check. Both carry the user.
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND], user=user,
                                        serials={self.serial_push},
                                        transaction_id=transaction_id)
        assert_authentication_log_entry(auth_log_entries[AuthEventType.LOGIN_SUCCESS], user=user,
                                        serials={self.serial_push},
                                        transaction_id=transaction_id)

        # Decline: the phone declines -> CHALLENGE_DECLINED at /ttype/push, correlated by transaction_id.
        clear_log_and_challenges()
        transaction_id, nonce = trigger_and_poll()
        sign_and_post(f"{nonce}|{self.serial_push}|decline", extra_data={"decline": "1"})
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED,
                                                  AuthEventType.CHALLENGE_DECLINED])
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_TRIGGERED], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id)
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_DECLINED], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id)

        # Bad signature: verification fails -> CHALLENGE_ANSWERED_FAIL at /ttype/push. No challenge matched the
        # signature, so the transaction_id is recovered via the single-open-challenge fallback.
        clear_log_and_challenges()
        transaction_id, _ = trigger_and_poll()
        sign_and_post(f"wrong|{self.serial_push}")
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED,
                                                  AuthEventType.CHALLENGE_ANSWERED_FAIL])
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_TRIGGERED], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id)
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_ANSWERED_FAIL], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id)
        self.assertEqual(transaction_id, auth_log_entries[AuthEventType.CHALLENGE_ANSWERED_FAIL].transaction_id)

        remove_token(self.serial_push)
        delete_policy("push_config")

    def test_19_push_code_to_phone_with_require_presence(self):
        """
        Test that if both code_to_phone and require_presence are enabled, require_presence takes
        precedence: challenge mode is REQUIRE_PRESENCE, client_mode is POLL (not INTERACTIVE),
        /polltransaction reports the correct status, and the full auth flow completes successfully.
        """
        self.setUp_user_realms()
        user = User("selfservice", self.realm1)
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
        clear_log()
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

        # check auth log
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_TRIGGERED], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id)

        # /polltransaction: challenge not yet answered
        with self.app.test_request_context('/validate/polltransaction',
                                           method='GET',
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertFalse(res.json.get("result").get("value"), res.json)
            self.assertEqual("pending", res.json.get("detail").get("challenge_status"), res.json)
        # no new auth log entry
        assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])

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
        # no new auth log entry
        assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])

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
        auth_log_entries = assert_authentication_log(
            [AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND])
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id)

        # /polltransaction: challenge is now answered
        with self.app.test_request_context('/validate/polltransaction',
                                           method='GET',
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            self.assertEqual("accept", res.json.get("detail").get("challenge_status"), res.json)
        # polling should not write to the auth log
        assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND])

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
        # Now login is completed
        auth_log_entries = assert_authentication_log(
            [AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND,
             AuthEventType.LOGIN_SUCCESS])
        assert_authentication_log_entry(auth_log_entries[AuthEventType.LOGIN_SUCCESS], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id,
                                        client_label="privacyidea-cp/2.0")

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
        clear_log()
        start_time = time.time()
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "push_pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            # Check that we actually waited
            self.assertGreater(time.time() - start_time, push_wait_time_seconds - 1)
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

        # check auth log: a timed-out push_wait is recorded only as CHALLENGE_TRIGGERED
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User("selfservice", self.realm1),
                                        serials={self.serial_push},
                                        transaction_id=get_challenges()[0].transaction_id)

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_mode_code_to_phone")
        delete_policy("push_wait")

    def test_21_push_wait_smartphone_confirms(self):
        """
        push_wait success path: the smartphone confirms the challenge while
        /validate/check is still blocking in the wait loop.

        push_wait makes /validate/check block synchronously and poll the
        challenge from the DB once a second (pushtoken.authenticate). For the
        success branch to fire, the challenge must be answered *during* that
        blocking call, so the smartphone /ttype/push confirm is issued from a
        background thread (the file-based test DB lets the second thread see the
        same challenge). The thread waits for the wait-loop to create the
        challenge, reads the nonce by polling, then confirms.
        """
        self.setUp_user_realms()
        user = User("selfservice", self.realm1)
        push_wait_seconds = 10
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        set_policy("push_wait", scope=SCOPE.AUTH, action=f"{PushAction.WAIT}={push_wait_seconds}")

        # Enroll the push token
        with self.app.test_request_context('/token/init', method='POST',
                                           data={"type": "push", "pin": "push_pin",
                                                 "user": "selfservice", "realm": self.realm1,
                                                 "serial": self.serial_push, "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            enrollment_credential = res.json.get("detail").get("enrollment_credential")
        with self.app.test_request_context('/ttype/push', method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": self.serial_push,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            self.assertEqual(200, self.app.full_dispatch_request().status_code)

        # The background "smartphone": wait for the wait-loop to create the challenge, then confirm it.
        confirm_errors = []
        captured = {}

        def smartphone_confirm():
            try:
                deadline = time.time() + push_wait_seconds
                nonce = None
                while time.time() < deadline and not nonce:
                    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
                    poll_sig = self.smartphone_private_key.sign(f"{self.serial_push}|{timestamp}".encode("utf8"),
                                                                padding.PKCS1v15(), hashes.SHA256())
                    with self.app.test_request_context('/ttype/push', method='GET',
                                                       query_string={"serial": self.serial_push,
                                                                     "timestamp": timestamp,
                                                                     "signature": b32encode(poll_sig)}):
                        value = self.app.full_dispatch_request().json.get("result").get("value")
                        if value:
                            nonce = value[0].get("nonce")
                    if not nonce:
                        time.sleep(0.2)
                self.assertIsNotNone(nonce, "smartphone never received the challenge to confirm")
                # Capture the transaction_id now, while the challenge is open: the /validate/check never returns it.
                # Needs its own app context as this runs in a separate thread.
                with self.app.app_context():
                    captured["transaction_id"] = get_challenges(serial=self.serial_push)[0].transaction_id
                confirm_sig = self.smartphone_private_key.sign(f"{nonce}|{self.serial_push}".encode("utf8"),
                                                               padding.PKCS1v15(), hashes.SHA256())
                with self.app.test_request_context('/ttype/push', method='POST',
                                                   data={"serial": self.serial_push,
                                                         "signature": b32encode(confirm_sig)}):
                    push_answered_response = self.app.full_dispatch_request()
                    self.assertTrue(push_answered_response.json.get("result").get("value"), push_answered_response.json)
            except Exception as exx:  # surface failures from the thread to the main assertion below
                confirm_errors.append(exx)

        clear_log()
        worker = threading.Thread(target=smartphone_confirm)
        worker.start()
        # This call blocks in the push_wait loop until the smartphone thread confirms.
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "selfservice", "pass": "push_pin"},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("value"), res.json)
            self.assertEqual(AUTH_RESPONSE.ACCEPT, res.json.get("result").get("authentication"), res.json)
        worker.join(timeout=push_wait_seconds + 5)
        self.assertFalse(worker.is_alive(), "smartphone confirm thread did not finish")
        self.assertEqual([], confirm_errors, f"smartphone thread failed: {confirm_errors}")

        # check auth log
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED,
                                                  AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND,
                                                  AuthEventType.LOGIN_SUCCESS])
        transaction_id = captured["transaction_id"]
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_TRIGGERED], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id,
                                        client_label="privacyidea-cp/2.0")
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND],
                                        user=user, serials={self.serial_push}, transaction_id=transaction_id)
        assert_authentication_log_entry(auth_log_entries[AuthEventType.LOGIN_SUCCESS], user=user,
                                        serials={self.serial_push}, transaction_id=transaction_id,
                                        client_label="privacyidea-cp/2.0")

        remove_token(self.serial_push)
        delete_policy("push_config")
        delete_policy("push_wait")
