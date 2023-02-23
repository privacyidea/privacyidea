# -*- coding: utf-8 -*-
from .base import MyApiTestCase
from privacyidea.lib.user import (User)
from privacyidea.lib.config import (set_privacyidea_config)
from privacyidea.lib.token import (get_tokens, init_token, remove_token)
from privacyidea.lib.policy import (SCOPE, set_policy, delete_policy)
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway, delete_smsgateway
from privacyidea.lib.smsprovider.FirebaseProvider import FIREBASE_CONFIG
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from privacyidea.lib.utils import to_bytes, to_unicode
from privacyidea.lib.tokens.pushtoken import (PUSH_ACTION,
                                              strip_key,
                                              PUBLIC_KEY_SMARTPHONE, PRIVATE_KEY_SERVER,
                                              PUBLIC_KEY_SERVER,
                                              POLL_ONLY)
from privacyidea.lib.utils import b32encode_and_unicode
from datetime import datetime, timedelta
from pytz import utc
from base64 import b32decode, b32encode
import mock
import responses
from google.oauth2 import service_account
from .test_lib_tokens_push import _create_credential_mock


PWFILE = "tests/testdata/passwords"
HOSTSFILE = "tests/testdata/hosts"
DICT_FILE = "tests/testdata/dictionary"
FIREBASE_FILE = "tests/testdata/firebase-test.json"
CLIENT_FILE = "tests/testdata/google-services.json"
FB_CONFIG_VALS = {
    FIREBASE_CONFIG.JSON_CONFIG: FIREBASE_FILE}
REGISTRATION_URL = "http://test/ttype/push"
TTL = "10"


class TtypeAPITestCase(MyApiTestCase):
    """
    test the api.ttype endpoints
    """

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_tiqr(self):
        init_token({"serial": "TIQR1",
                    "type": "tiqr"}, User("cornelius", self.realm1))
        with self.app.test_request_context('/ttype/tiqr',
                                           method='POST',
                                           data={"action": "metadata",
                                                 "serial": "TIQR1",
                                                 "session": "12345"}):
            res = self.app.full_dispatch_request()
            data = res.json
            identity = data.get("identity")
            service = data.get("service")
            self.assertEqual(identity.get("displayName"), "Cornelius ")
            self.assertEqual(service.get("displayName"), "privacyIDEA")

    def test_02_u2f(self):
        set_privacyidea_config("u2f.appId", "https://puck.az.intern")
        with self.app.test_request_context('/ttype/u2f',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'application/fido.trusted-apps+json')
            data = res.json
            self.assertTrue("trustedFacets" in data)

        # Check the audit log.
        with self.app.test_request_context('/audit/?action=*GET /ttype/*',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            result = json_response.get("result")
            auditdata = result.get("value").get("auditdata")
            self.assertTrue(len(auditdata) > 0)
            self.assertEqual(auditdata[0].get("token_type"), "u2f")

    def test_03_wrong(self):
        # Test the ttype endpoint for wrong ttype, here /ttype/wrong
        init_token({"serial": "TIQR1",
                    "type": "tiqr"}, User("cornelius", self.realm1))
        with self.app.test_request_context('/ttype/wrong',
                                           method='POST',
                                           data={"action": "metadata",
                                                 "serial": "TIQR1",
                                                 "session": "12345"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res.status_code)

class TtypePushAPITestCase(MyApiTestCase):
    """
    test /ttype/push
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

    def _create_push_token(self):
        tparams = {'type': 'push', 'genkey': 1}
        tparams.update(FB_CONFIG_VALS)
        tok = init_token(param=tparams)
        tok.add_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG, self.firebase_config_name)
        tok.add_tokeninfo(PUBLIC_KEY_SMARTPHONE, self.smartphone_public_key_pem_urlsafe)
        tok.add_tokeninfo('firebase_token', 'firebaseT')
        tok.add_tokeninfo(PUBLIC_KEY_SERVER, self.server_public_key_pem)
        tok.add_tokeninfo(PRIVATE_KEY_SERVER, self.server_private_key_pem, 'password')
        tok.del_tokeninfo("enrollment_credential")
        tok.token.rollout_state = "enrolled"
        tok.token.active = True
        return tok

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_api_enroll_push(self):
        self.authenticate()

        # Failed enrollment due to missing policy
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertNotEqual(res.status_code, 200)
            error = res.json.get("result").get("error")
            self.assertEqual(error.get("message"),
                             "Missing enrollment policy for push token: push_firebase_configuration")
            self.assertEqual(error.get("code"), 303)

        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                           "myFB", FB_CONFIG_VALS)
        self.assertTrue(r > 0)
        set_policy("push1", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       PUSH_ACTION.FIREBASE_CONFIG, self.firebase_config_name,
                       PUSH_ACTION.REGISTRATION_URL, REGISTRATION_URL,
                       PUSH_ACTION.TTL, TTL))

        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
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

        # 2nd step. Failing with wrong serial number
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": "wrongserial",
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 404, res)
            status = res.json.get("result").get("status")
            self.assertFalse(status)
            error = res.json.get("result").get("error")
            self.assertEqual(error.get("message"),
                             "No token with this serial number in the rollout state 'clientwait'.")

        # 2nd step. Fails with missing enrollment credential
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT",
                                                 "enrollment_credential": "WRonG"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            status = res.json.get("result").get("status")
            self.assertFalse(status)
            error = res.json.get("result").get("error")
            self.assertEqual(error.get("message"),
                             "ERR905: Invalid enrollment credential. You are not authorized to finalize this token.")

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
            self.assertIsInstance(parsed_server_pubkey, rsa.RSAPublicKey)
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
            self.assertEqual(tokeninfo.get(PUSH_ACTION.FIREBASE_CONFIG), self.firebase_config_name)
            # remove the token
            remove_token(serial)

    def test_02_api_push_poll(self):
        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                           "myFB", FB_CONFIG_VALS)
        self.assertGreater(r, 0)

        # create a new push token
        tokenobj = self._create_push_token()
        serial = tokenobj.get_serial()

        # set PIN
        tokenobj.set_pin("pushpin")
        tokenobj.add_user(User("cornelius", self.realm1))

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                        '.from_service_account_file') as mySA:
            # alternative: side_effect instead of return_value
            mySA.return_value = _create_credential_mock()

            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          body="""{}""",
                          content_type="application/json")

            # Send the first authentication request to trigger the challenge.
            # No push notification is submitted to firebase, but a challenge is created anyway
            with mock.patch("logging.Logger.warning") as mock_log:
                with self.app.test_request_context('/validate/check',
                                                   method='POST',
                                                   data={"user": "cornelius",
                                                         "realm": self.realm1,
                                                         "pass": "pushpin"}):
                    res = self.app.full_dispatch_request()
                    self.assertTrue(res.status_code == 200, res)
                    result = res.json.get("result")
                    self.assertTrue(result.get("status"))
                    self.assertFalse(result.get("value"))
                    self.assertEqual("CHALLENGE", result.get("authentication"))
                    # Check that the warning was written to the log file.
                    mock_log.assert_called_with("Failed to submit message to Firebase service for token {0!s}."
                                                .format(serial))

        # first create a signature
        ts = datetime.utcnow().isoformat()
        sign_string = "{serial}|{timestamp}".format(serial=serial, timestamp=ts)
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        # now check that we receive the challenge when polling
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           data={"serial": serial,
                                                 "timestamp": ts,
                                                 "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()

            # check that the serial was set in flask g (via before_request in ttype.py)
            self.assertTrue(self.app_context.g.serial, serial)
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'])
            chall = res.json['result']['value'][0]
            self.assertTrue(chall)

            challenge = chall["nonce"]
            # This is what the smartphone answers.
            # create the signature:
            sign_data = "{0!s}|{1!s}".format(challenge, serial)
            signature = b32encode_and_unicode(
                self.smartphone_private_key.sign(sign_data.encode("utf-8"),
                                                 padding.PKCS1v15(),
                                                 hashes.SHA256()))

            # Answer the challenge
            with self.app.test_request_context('/ttype/push',
                                               method='POST',
                                               data={"serial": serial,
                                                     "nonce": challenge,
                                                     "signature": signature}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                self.assertTrue(res.json['result']['status'])
                self.assertTrue(res.json['result']['value'])

    def test_03_api_enroll_push_poll_only(self):
        """Enroll a poll-only push token"""
        self.authenticate()
        # Set policy for poll only
        set_policy("push1", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       PUSH_ACTION.FIREBASE_CONFIG, POLL_ONLY,
                       PUSH_ACTION.REGISTRATION_URL, REGISTRATION_URL,
                       PUSH_ACTION.TTL, TTL))

        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(detail.get("rollout_state"), "clientwait")
            self.assertIn("pushurl", detail)
            # check that the new URL contains the serial number
            self.assertIn("&serial=PIPU", detail.get("pushurl").get("value"))
            # The firebase settings are NOT contained in the QR Code, since we do poll_only
            # poll_only
            self.assertNotIn("appid=", detail.get("pushurl").get("value"))
            self.assertNotIn("appidios=", detail.get("pushurl").get("value"))
            self.assertNotIn("apikeyios=", detail.get("pushurl").get("value"))
            self.assertNotIn("otpkey", detail)
            enrollment_credential = detail.get("enrollment_credential")

        # 2nd step: as performed by the smartphone. Also in POLL_ONLY the smartphone needs to send
        #           an empty "fbtoken"
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential,
                                                 "serial": serial,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": ""}):
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
            self.assertIsInstance(parsed_server_pubkey, rsa.RSAPublicKey)
            pubkey = detail.get("public_key")

            # Now check, what is in the token in the database
            toks = get_tokens(serial=serial)
            self.assertEqual(len(toks), 1)
            token_obj = toks[0]
            self.assertEqual(token_obj.token.rollout_state, "enrolled")
            self.assertTrue(token_obj.token.active)
            tokeninfo = token_obj.get_tokeninfo()
            self.assertEqual(tokeninfo.get("public_key_smartphone"), self.smartphone_public_key_pem_urlsafe)
            self.assertEqual(tokeninfo.get("firebase_token"), "")
            self.assertEqual(tokeninfo.get("public_key_server").strip().strip("-BEGIN END RSA PUBLIC KEY-").strip(),
                             pubkey)
            # The token should also contain the firebase config
            self.assertEqual(tokeninfo.get(PUSH_ACTION.FIREBASE_CONFIG), POLL_ONLY)

        # remove the token
        remove_token(serial)
        # remove the policy
        delete_policy("push1")
