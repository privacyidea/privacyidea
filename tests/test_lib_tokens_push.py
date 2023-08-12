# -*- coding: utf-8 -*-
from flask import Request
from werkzeug.test import EnvironBuilder
from datetime import datetime, timedelta
from pytz import utc

from .base import MyTestCase, FakeFlaskG
from privacyidea.lib.error import ParameterError, privacyIDEAError, PolicyError
from privacyidea.lib.user import (User)
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.tokens.pushtoken import (PushTokenClass, PUSH_ACTION,
                                              DEFAULT_CHALLENGE_TEXT, strip_key,
                                              PUBLIC_KEY_SMARTPHONE, PRIVATE_KEY_SERVER,
                                              PUBLIC_KEY_SERVER,
                                              PushAllowPolling, POLLING_ALLOWED, POLL_ONLY)
from privacyidea.lib.smsprovider.FirebaseProvider import FIREBASE_CONFIG
from privacyidea.lib.token import get_tokens, remove_token, init_token
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.crypto import geturandom
from privacyidea.models import Token, Challenge
from privacyidea.lib.policy import (SCOPE, set_policy, delete_policy, ACTION,
                                    LOGINMODE, PolicyClass)
from privacyidea.lib.utils import to_bytes, b32encode_and_unicode, to_unicode
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway, delete_smsgateway
from privacyidea.lib.error import ConfigAdminError
from base64 import b32decode, b32encode
import json
import responses
import mock
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from google.oauth2 import service_account
from threading import Timer
import time

PWFILE = "tests/testdata/passwords"
FIREBASE_FILE = "tests/testdata/firebase-test.json"
CLIENT_FILE = "tests/testdata/google-services.json"

REGISTRATION_URL = "http://test/ttype/push"
TTL = 10
FB_CONFIG_VALS = {
    FIREBASE_CONFIG.JSON_CONFIG: FIREBASE_FILE}


def _create_credential_mock():
    c = service_account.Credentials('a', 'b', 'c')
    return mock.MagicMock(spec=c, expired=False, expiry=None,
                          access_token='my_new_bearer_token')


def _check_firebase_params(request):
    payload = json.loads(request.body)
    # check the signature in the payload!
    data = payload.get("message").get("data")

    sign_string = "{nonce}|{url}|{serial}|{question}|{title}|{sslverify}".format(**data)
    token_obj = get_tokens(serial=data.get("serial"))[0]
    pem_pubkey = token_obj.get_tokeninfo(PUBLIC_KEY_SERVER)
    pubkey_obj = load_pem_public_key(to_bytes(pem_pubkey), backend=default_backend())
    signature = b32decode(data.get("signature"))
    # If signature does not match it will raise InvalidSignature exception
    pubkey_obj.verify(signature, sign_string.encode("utf8"),
                      padding.PKCS1v15(),
                      hashes.SHA256())
    headers = {'request-id': '728d329e-0e86-11e4-a748-0c84dc037c13'}
    return 200, headers, json.dumps({})


class PushTokenTestCase(MyTestCase):

    serial1 = "PUSH00001"

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

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="push")
        db_token.save()
        token = PushTokenClass(db_token)
        self.assertEqual(token.token.serial, self.serial1)
        self.assertEqual(token.token.tokentype, "push")
        self.assertEqual(token.type, "push")
        class_prefix = token.get_class_prefix()
        self.assertEqual(class_prefix, "PIPU")
        self.assertEqual(token.get_class_type(), "push")

        # Test to do the 2nd step, although the token is not yet in clientwait
        self.assertRaises(ParameterError, token.update, {"otpkey": "1234", "pubkey": "1234", "serial": self.serial1})

        # Run enrollment step 1
        token.update({"genkey": 1})

        # Now the token is in the state clientwait, but insufficient parameters would still fail
        self.assertRaises(ParameterError, token.update, {"otpkey": "1234"})
        self.assertRaises(ParameterError, token.update, {"otpkey": "1234", "pubkey": "1234"})

        # Unknown config
        self.assertRaises(ParameterError, token.get_init_detail, params={"firebase_config": "bla"})

        fb_config = {FIREBASE_CONFIG.REGISTRATION_URL: "http://test/ttype/push",
                     FIREBASE_CONFIG.JSON_CONFIG: CLIENT_FILE,
                     FIREBASE_CONFIG.TTL: 10}

        # Wrong JSON file
        self.assertRaises(ConfigAdminError, set_smsgateway,
                          "fb1", 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                          fb_config)

        # Everything is fine
        fb_config[FIREBASE_CONFIG.JSON_CONFIG] = FIREBASE_FILE
        r = set_smsgateway("fb1", 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                           fb_config)
        self.assertTrue(r > 0)

        detail = token.get_init_detail(params={"firebase_config": self.firebase_config_name,
                                               "push_registration_url": "https://privacyidea.com/enroll"})
        self.assertEqual(detail.get("serial"), self.serial1)
        self.assertEqual(detail.get("rollout_state"), "clientwait")
        enrollment_credential = detail.get("enrollment_credential")
        self.assertTrue("pushurl" in detail)
        self.assertNotIn('pin=True', detail['pushurl']['value'])
        self.assertFalse("otpkey" in detail)

        # Run enrollment step 2
        token.update({"enrollment_credential": enrollment_credential,
                      "serial": self.serial1,
                      "fbtoken": "firebasetoken",
                      "pubkey": self.smartphone_public_key_pem_urlsafe})
        self.assertEqual(token.get_tokeninfo("firebase_token"), "firebasetoken")
        self.assertEqual(token.get_tokeninfo("public_key_smartphone"), self.smartphone_public_key_pem_urlsafe)
        self.assertTrue(token.get_tokeninfo("public_key_server").startswith("-----BEGIN RSA PUBLIC KEY-----\n"),
                        token.get_tokeninfo("public_key_server"))
        parsed_server_pubkey = serialization.load_pem_public_key(
            to_bytes(token.get_tokeninfo("public_key_server")),
            default_backend())
        self.assertIsInstance(parsed_server_pubkey, RSAPublicKey)
        self.assertTrue(token.get_tokeninfo("private_key_server").startswith("-----BEGIN RSA PRIVATE KEY-----\n"),
                        token.get_tokeninfo("private_key_server"))
        parsed_server_privkey = serialization.load_pem_private_key(
            to_bytes(token.get_tokeninfo("private_key_server")),
            None,
            default_backend())
        self.assertIsInstance(parsed_server_privkey, RSAPrivateKey)

        detail = token.get_init_detail()
        self.assertEqual(detail.get("rollout_state"), "enrolled")
        augmented_pubkey = "-----BEGIN RSA PUBLIC KEY-----\n{}\n-----END RSA PUBLIC KEY-----\n".format(
            detail.get("public_key"))
        parsed_stripped_server_pubkey = serialization.load_pem_public_key(
            to_bytes(augmented_pubkey),
            default_backend())
        self.assertEqual(parsed_server_pubkey.public_numbers(), parsed_stripped_server_pubkey.public_numbers())
        remove_token(self.serial1)

    def test_01a_enroll_with_app_pin(self):
        tparams = {'type': 'push', 'genkey': 1}
        tparams.update(FB_CONFIG_VALS)
        tok = init_token(param=tparams)
        detail = tok.get_init_detail(params={PUSH_ACTION.FIREBASE_CONFIG: POLL_ONLY,
                                             PUSH_ACTION.REGISTRATION_URL: "https://privacyidea.com/enroll",
                                             ACTION.FORCE_APP_PIN: True})
        self.assertIn('pin=True', detail['pushurl']['value'])
        remove_token(tok.get_serial())

    def test_02a_lib_enroll(self):
        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                           "myFB", FB_CONFIG_VALS)
        self.assertTrue(r > 0)
        set_policy("push1", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PUSH_ACTION.FIREBASE_CONFIG,
                                               self.firebase_config_name))
        token_obj = self._create_push_token()
        remove_token(token_obj.get_serial())

    @responses.activate
    def test_03a_api_authenticate_fail(self):
        # This tests failure to communicate to the firebase service
        self.setUp_user_realms()
        # create FireBase Service and policies
        set_smsgateway(self.firebase_config_name,
                       'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                       "myFB", FB_CONFIG_VALS)
        set_policy("push1", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       PUSH_ACTION.FIREBASE_CONFIG,
                       self.firebase_config_name,
                       PUSH_ACTION.REGISTRATION_URL, REGISTRATION_URL,
                       PUSH_ACTION.TTL, TTL))
        # create push token
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

            # add responses, to simulate the failing communication (status 500)
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          body="""{}""",
                          status=500,
                          content_type="application/json")

            # Send the first authentication request to trigger the challenge
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
                    # Check that the user was informed about the need to poll
                    detail = res.json.get("detail")
                    self.assertEqual("Please confirm the authentication on your mobile device! "
                                     "Use the polling feature of your privacyIDEA Authenticator App "
                                     "to check for a new Login request.", detail.get("message"))

            # Our ServiceAccountCredentials mock has been called once, because
            # no access token has been fetched before
            mySA.assert_called_once()
            self.assertIn(FIREBASE_FILE, get_app_local_store()["firebase_token"])

            # By default, polling is allowed for push tokens so the corresponding
            # challenge should be available in the challenge table, even though
            # the request to firebase failed.
            chals = get_challenges(serial=tokenobj.token.serial)
            self.assertEqual(len(chals), 1, chals)
            chals[0].delete()

            # Do the same with the parameter "exception", so that we receive an Error on HTTP
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "exception": 1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(400, res.status_code)
                result = res.json.get("result")
                self.assertFalse(result.get("status"))
                error = result.get("error")
                self.assertEqual(401, error.get("code"))
                self.assertEqual("ERR401: Failed to submit message to Firebase service.", error.get("message"))

            # Remove the created challenge
            chals = get_challenges(serial=tokenobj.token.serial)
            self.assertEqual(len(chals), 1, chals)
            chals[0].delete()

            # Now disable polling and check that no challenge is created
            # disallow polling through a policy
            set_policy('push_poll', SCOPE.AUTH,
                       action='{0!s}={1!s}'.format(PUSH_ACTION.ALLOW_POLLING,
                                                   PushAllowPolling.DENY))

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
            self.assertEqual(len(get_challenges(serial=tokenobj.token.serial)), 0)
            # disallow polling the specific token through a policy
            set_policy('push_poll', SCOPE.AUTH,
                       action='{0!s}={1!s}'.format(PUSH_ACTION.ALLOW_POLLING,
                                                   PushAllowPolling.TOKEN))
            tokenobj.add_tokeninfo(POLLING_ALLOWED, False)
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
            self.assertEqual(len(get_challenges(serial=tokenobj.token.serial)), 0)

            # Do the same with the parameter "exception", so that we receive an Error on HTTP
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "exception": 1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(400, res.status_code)
                result = res.json.get("result")
                self.assertFalse(result.get("status"))
                error = result.get("error")
                self.assertEqual(401, error.get("code"))
                self.assertEqual("ERR401: Failed to submit message to Firebase service.", error.get("message"))

            # Check that the challenge is created if the request to firebase
            # succeeded even though polling is disabled
            # add responses, to simulate the successful communication to firebase
            responses.replace(responses.POST,
                              'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                              body="""{}""",
                              content_type="application/json")
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                jsonresp = res.json
                self.assertTrue(jsonresp.get("result").get("status"))
            self.assertEqual(len(get_challenges(serial=tokenobj.token.serial)), 1)
            get_challenges(serial=tokenobj.token.serial)[0].delete()

        remove_token(serial=serial)
        delete_smsgateway(self.firebase_config_name)
        delete_policy('push_poll')
        delete_policy('push1')

    @responses.activate
    def test_03b_api_authenticate_client(self):
        # Test the /validate/check endpoints without the smartphone endpoint /ttype/push
        self.setUp_user_realms()
        # create FireBase Service and policies
        set_smsgateway(self.firebase_config_name,
                       'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                       "myFB", FB_CONFIG_VALS)
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PUSH_ACTION.FIREBASE_CONFIG,
                                               self.firebase_config_name))
        # create push token
        tokenobj = self._create_push_token()
        serial = tokenobj.get_serial()
        # set PIN
        tokenobj.set_pin("pushpin")
        tokenobj.add_user(User("cornelius", self.realm1))

        cached_fbtoken = {
            'firebase_token': {
                FB_CONFIG_VALS[FIREBASE_CONFIG.JSON_CONFIG]: _create_credential_mock()}}
        self.app.config.setdefault('_app_local_store', {}).update(cached_fbtoken)
        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account'
                        '.Credentials.from_service_account_file') as mySA:
            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects'
                                          '/test-123456/messages:send',
                          body="""{}""",
                          content_type="application/json")

            # Send the first authentication request to trigger the challenge
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                jsonresp = res.json
                self.assertFalse(jsonresp.get("result").get("value"))
                self.assertTrue(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp.get("detail").get("serial"), tokenobj.token.serial)
                self.assertTrue("transaction_id" in jsonresp.get("detail"))
                transaction_id = jsonresp.get("detail").get("transaction_id")
                self.assertEqual(jsonresp.get("detail").get("message"), DEFAULT_CHALLENGE_TEXT)

            # Our ServiceAccountCredentials mock has not been called because we use a cached token
            mySA.assert_not_called()
            self.assertIn(FIREBASE_FILE, get_app_local_store()["firebase_token"])
            # remove cached Credentials
            get_app_local_store().pop("firebase_token")

        # The mobile device has not communicated with the backend, yet.
        # The user is not authenticated!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            jsonresp = res.json
            # Result-Value is false, the user has not answered the challenge, yet
            self.assertFalse(jsonresp.get("result").get("value"))

        # As the challenge has not been answered yet, the /validate/polltransaction endpoint returns false
        with self.app.test_request_context('/validate/polltransaction', method='GET',
                                           data={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # Now the smartphone communicates with the backend and the challenge in the database table
        # is marked as answered successfully.
        challengeobject_list = get_challenges(serial=tokenobj.token.serial,
                                              transaction_id=transaction_id)
        challengeobject_list[0].set_otp_status(True)

        # As the challenge has been answered, the /validate/polltransaction endpoint returns true
        with self.app.test_request_context('/validate/polltransaction', method='GET',
                                           data={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertTrue(res.json["result"]["value"])

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "state": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            jsonresp = res.json
            # Result-Value is True, since the challenge is marked resolved in the DB
        self.assertTrue(jsonresp.get("result").get("value"))

        # As the challenge does not exist anymore, the /validate/polltransaction endpoint returns false
        with self.app.test_request_context('/validate/polltransaction', method='GET',
                                           data={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])
        self.assertEqual(get_challenges(serial=tokenobj.token.serial), [])

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        # Do single shot auth with waiting
        # Also mock time.time to be 4000 seconds in the future (exceeding the validity of myAccessTokenInfo),
        # so that we fetch a new auth token
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.time') as mock_time:
            mock_time.time.return_value = time.time() + 4000

            with mock.patch(
                    'privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                    '.from_service_account_file') as mySA:
                # alternative: side_effect instead of return_value
                mySA.return_value = _create_credential_mock()

                # add responses, to simulate the communication to firebase
                responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                              body="""{}""",
                              content_type="application/json")

                # In two seconds we need to run an update on the challenge table.
                Timer(2, self.mark_challenge_as_accepted).start()

                set_policy("push1", scope=SCOPE.AUTH, action="{0!s}=20".format(PUSH_ACTION.WAIT))
                # Send the first authentication request to trigger the challenge
                with self.app.test_request_context('/validate/check',
                                                   method='POST',
                                                   data={"user": "cornelius",
                                                         "realm": self.realm1,
                                                         "pass": "pushpin"}):
                    res = self.app.full_dispatch_request()
                    self.assertTrue(res.status_code == 200, res)
                    jsonresp = res.json
                    # We successfully authenticated! YEAH!
                    self.assertTrue(jsonresp.get("result").get("value"))
                    self.assertTrue(jsonresp.get("result").get("status"))
                    self.assertEqual(jsonresp.get("detail").get("serial"), tokenobj.token.serial)
                delete_policy("push1")

            # Our ServiceAccountCredentials mock has been called once because we fetched a new token
            mySA.assert_called_once()
            self.assertIn(FIREBASE_FILE, get_app_local_store()["firebase_token"])
            self.assertEqual(get_app_local_store()["firebase_token"][FIREBASE_FILE].access_token,
                             "my_new_bearer_token")

        # Authentication fails, if the push notification is not accepted within the configured time
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                        '.from_service_account_file') as mySA:
            # alternative: side_effect instead of return_value
            mySA.return_value = _create_credential_mock()

            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          body="""{}""",
                          content_type="application/json")

            set_policy("push1", scope=SCOPE.AUTH, action="{0!s}=1".format(PUSH_ACTION.WAIT))
            # Send the first authentication request to trigger the challenge
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                jsonresp = res.json
                # We fail to authenticate! Oh No!
                self.assertFalse(jsonresp.get("result").get("value"))
                self.assertTrue(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp.get("detail").get("serial"), tokenobj.token.serial)
            delete_policy("push1")
        delete_policy('push_config')

    def mark_challenge_as_accepted(self):
        # We simply mark all challenges as successfully answered!
        with self.app.test_request_context():
            challenges = get_challenges()
            for chal in challenges:
                chal.set_otp_status(True)
                chal.save()

    @responses.activate
    def test_04_api_authenticate_smartphone(self):
        # Test the /validate/check endpoints and the smartphone endpoint /ttype/push
        # for authentication

        # get enrolled push token
        toks = get_tokens(tokentype="push")
        self.assertEqual(len(toks), 1)
        tokenobj = toks[0]

        # set PIN
        tokenobj.set_pin("pushpin")
        tokenobj.add_user(User("cornelius", self.realm1))

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                        '.from_service_account_file') as mySA:
            # alternative: side_effect instead of return_value
            mySA.from_json_keyfile_name.return_value = _create_credential_mock()

            # add responses, to simulate the communication to firebase
            responses.add_callback(
                responses.POST,
                'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                callback=_check_firebase_params,
                content_type="application/json")

            # Send the first authentication request to trigger the challenge
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                jsonresp = res.json
                self.assertFalse(jsonresp.get("result").get("value"))
                self.assertTrue(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp.get("detail").get("serial"), tokenobj.token.serial)
                self.assertTrue("transaction_id" in jsonresp.get("detail"))
                transaction_id = jsonresp.get("detail").get("transaction_id")
                self.assertEqual(jsonresp.get("detail").get("message"), DEFAULT_CHALLENGE_TEXT)

            # Our ServiceAccountCredentials mock has not been called because we use a cached token
            self.assertEqual(len(mySA.from_json_keyfile_name.mock_calls), 0)
            self.assertIn(FIREBASE_FILE, get_app_local_store()["firebase_token"])

        # The challenge is sent to the smartphone via the Firebase service, so we do not know
        # the challenge from the /validate/check API.
        # So lets read the challenge from the database!

        challengeobject_list = get_challenges(serial=tokenobj.token.serial,
                                              transaction_id=transaction_id)
        challenge = challengeobject_list[0].challenge

        # Incomplete request fails with HTTP400
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": challenge}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        # This is what the smartphone answers.
        # create the signature:
        sign_data = "{0!s}|{1!s}".format(challenge, tokenobj.token.serial)
        signature = b32encode_and_unicode(
            self.smartphone_private_key.sign(sign_data.encode("utf-8"),
                                             padding.PKCS1v15(),
                                             hashes.SHA256()))
        # Try an invalid signature first
        wrong_sign_data = "{}|{}".format(challenge, tokenobj.token.serial[1:])
        wrong_signature = b32encode_and_unicode(
            self.smartphone_private_key.sign(wrong_sign_data.encode("utf-8"),
                                             padding.PKCS1v15(),
                                             hashes.SHA256()))
        # Signed the wrong data
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": challenge,
                                                 "signature": wrong_signature}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'])
            self.assertFalse(res.json['result']['value'])

        # Correct signature, wrong challenge
        wrong_challenge = b32encode_and_unicode(geturandom())
        wrong_sign_data = "{}|{}".format(wrong_challenge, tokenobj.token.serial)
        wrong_signature = b32encode_and_unicode(
            self.smartphone_private_key.sign(wrong_sign_data.encode("utf-8"),
                                             padding.PKCS1v15(),
                                             hashes.SHA256()))
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": wrong_challenge,
                                                 "signature": wrong_signature}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'])
            self.assertFalse(res.json['result']['value'])

        # Correct signature, empty nonce
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": "",
                                                 "signature": signature}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'])
            self.assertFalse(res.json['result']['value'])

        # Correct signature, wrong private key
        wrong_key = rsa.generate_private_key(public_exponent=65537,
                                             key_size=4096,
                                             backend=default_backend())
        wrong_sign_data = "{}|{}".format(challenge, tokenobj.token.serial)
        wrong_signature = b32encode_and_unicode(
            wrong_key.sign(wrong_sign_data.encode("utf-8"),
                           padding.PKCS1v15(),
                           hashes.SHA256()))
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": challenge,
                                                 "signature": wrong_signature}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'])
            self.assertFalse(res.json['result']['value'])

        # Result value is still false
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "state": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertFalse(res.json['result']['value'])

        # Now the correct request
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": challenge,
                                                 "signature": signature}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'])
            self.assertTrue(res.json['result']['value'])

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "state": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            jsonresp = res.json
            # Result-Value is True
            self.assertTrue(jsonresp.get("result").get("value"))


    def test_04_decline_auth_request(self):
        # get enrolled push token
        toks = get_tokens(tokentype="push")
        self.assertEqual(len(toks), 1)
        tokenobj = toks[0]

        # set PIN
        tokenobj.set_pin("pushpin")
        tokenobj.add_user(User("cornelius", self.realm1))

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                        '.from_service_account_file') as mySA:
            # alternative: side_effect instead of return_value
            mySA.from_json_keyfile_name.return_value = _create_credential_mock()

            # add responses, to simulate the communication to firebase
            responses.add_callback(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                                   callback=_check_firebase_params,
                                   content_type="application/json")

            # Send the first authentication request to trigger the challenge
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                jsonresp = res.json
                self.assertFalse(jsonresp.get("result").get("value"))
                self.assertTrue(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp.get("detail").get("serial"), tokenobj.token.serial)
                self.assertTrue("transaction_id" in jsonresp.get("detail"))
                transaction_id = jsonresp.get("detail").get("transaction_id")

            # Our ServiceAccountCredentials mock has not been called because we use a cached token
            self.assertEqual(len(mySA.from_json_keyfile_name.mock_calls), 0)
            self.assertIn(FIREBASE_FILE, get_app_local_store()["firebase_token"])

        # The challenge is sent to the smartphone via the Firebase service, so we do not know
        # the challenge from the /validate/check API.
        # So lets read the challenge from the database!

        challengeobject_list = get_challenges(serial=tokenobj.token.serial,
                                              transaction_id=transaction_id)
        challenge = challengeobject_list[0].challenge

        sign_data = "{0!s}|{1!s}|decline".format(challenge, tokenobj.token.serial)
        signature = b32encode_and_unicode(
            self.smartphone_private_key.sign(sign_data.encode("utf-8"),
                                             padding.PKCS1v15(),
                                             hashes.SHA256()))

        # Simulate the decline request to a pre privacyIDEA 3.8 system.
        # It will ignore the "decline" parameter, so we do not add it in the
        # request. The request should fail due to an invalid signature
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": challenge,
                                                 "signature": signature}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            rj = res.json
            self.assertTrue(rj['result']['status'])
            self.assertFalse(rj['result']['value'])
        # Now decline the auth request for real
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": challenge,
                                                 "decline": 1,
                                                 "signature": signature}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'])
            self.assertTrue(res.json['result']['value'])

        challengeobject_list = get_challenges(serial=tokenobj.token.serial,
                                              transaction_id=transaction_id)
        self.assertEqual(1, len(challengeobject_list))

        with self.app.test_request_context('/validate/polltransaction', method='GET',
                                           data={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])
            self.assertEqual(res.json["detail"]["challenge_status"], "declined", res.json["detail"]["challenge_status"])




    def test_05_strip_key(self):
        stripped_pubkey = strip_key(self.smartphone_public_key_pem)
        self.assertIn("-BEGIN PUBLIC KEY-", self.smartphone_public_key_pem)
        self.assertNotIn("-BEGIN PUBLIC KEY_", stripped_pubkey)
        self.assertNotIn("-", stripped_pubkey)
        self.assertEqual(strip_key(stripped_pubkey), stripped_pubkey)
        self.assertEqual(strip_key("\n\n" + stripped_pubkey + "\n\n"), stripped_pubkey)

    @responses.activate
    def test_06_api_auth(self):
        self.setUp_user_realms()

        # get enrolled push token
        toks = get_tokens(tokentype="push")
        self.assertEqual(len(toks), 1)
        tokenobj = toks[0]

        # set PIN
        tokenobj.set_pin("pushpin")
        tokenobj.add_user(User("cornelius", self.realm1))

        # Set a loginmode policy
        set_policy("webui", scope=SCOPE.WEBUI,
                   action="{}={}".format(ACTION.LOGINMODE, LOGINMODE.PRIVACYIDEA))
        # Set a PUSH_WAIT action which will be ignored by privacyIDEA
        set_policy("push1", scope=SCOPE.AUTH, action="{0!s}=20".format(PUSH_ACTION.WAIT))
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                        '.from_service_account_file') as mySA:
            # alternative: side_effect instead of return_value
            mySA.from_json_keyfile_name.return_value = _create_credential_mock()

            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          body="""{}""",
                          content_type="application/json")

            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "cornelius",
                                                     "realm": self.realm1,
                                                     # this will be overwritted by pushtoken_disable_wait
                                                     PUSH_ACTION.WAIT: "10",
                                                     "password": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                jsonresp = res.json
                self.assertTrue(jsonresp.get("result").get("value"))
                self.assertTrue(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp.get("detail").get("serial"), tokenobj.token.serial)
                self.assertIn("transaction_id", jsonresp.get("detail"))
                transaction_id = jsonresp.get("detail").get("transaction_id")
                self.assertEqual(jsonresp.get("detail").get("message"), DEFAULT_CHALLENGE_TEXT)

        # Get the challenge from the database
        challengeobject_list = get_challenges(serial=tokenobj.token.serial,
                                              transaction_id=transaction_id)
        challenge = challengeobject_list[0].challenge
        # This is what the smartphone answers.
        # create the signature:
        sign_data = "{0!s}|{1!s}".format(challenge, tokenobj.token.serial)
        signature = b32encode_and_unicode(
            self.smartphone_private_key.sign(sign_data.encode("utf-8"),
                                             padding.PKCS1v15(),
                                             hashes.SHA256()))

        # We still cannot log in
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": self.realm1,
                                                 "password": "",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            self.assertFalse(res.json['result']['status'])

        # Answer the challenge
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": tokenobj.token.serial,
                                                 "nonce": challenge,
                                                 "signature": signature}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'])
            self.assertTrue(res.json['result']['value'])

        # We can now log in
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": self.realm1,
                                                 "password": "",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json['result']['status'])

        remove_token(tokenobj.get_serial())
        delete_policy("push1")
        delete_policy("webui")

    def test_07_check_timestamp(self):
        timestamp_fmt = 'broken_timestamp_010203'
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not parse timestamp {0!s}. ISO-Format '
                               r'required.'.format(timestamp_fmt),
                               PushTokenClass._check_timestamp_in_range, timestamp_fmt, 10)
        timestamp = datetime(2020, 11, 13, 13, 27, tzinfo=utc)
        with mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt:
            mock_dt.now.return_value = timestamp + timedelta(minutes=9)
            PushTokenClass._check_timestamp_in_range(timestamp.isoformat(), 10)
        with mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt:
            mock_dt.now.return_value = timestamp - timedelta(minutes=9)
            PushTokenClass._check_timestamp_in_range(timestamp.isoformat(), 10)
        with mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt:
            mock_dt.now.return_value = timestamp + timedelta(minutes=9)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Timestamp {0!s} not in valid '
                                   r'range.'.format(timestamp.isoformat().replace('+', r'\+')),
                                   PushTokenClass._check_timestamp_in_range,
                                   timestamp.isoformat(), 8)
        with mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt:
            mock_dt.now.return_value = timestamp - timedelta(minutes=9)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Timestamp {0!s} not in valid '
                                   r'range.'.format(timestamp.isoformat().replace('+', r'\+')),
                                   PushTokenClass._check_timestamp_in_range,
                                   timestamp.isoformat(), 8)

    def test_10_api_endpoint(self):
        # first check for unused request methods
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        builder = EnvironBuilder(method='PUT',
                                 headers={})

        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01'}
        self.assertRaisesRegex(privacyIDEAError,
                               'Method PUT not allowed in \'api_endpoint\' '
                               'for push token.',
                               PushTokenClass.api_endpoint, req, g)

        # check for parameter error in POST request
        builder = EnvironBuilder(method='POST',
                                 headers={})

        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01'}
        self.assertRaisesRegex(ParameterError, 'Missing parameters!',
                               PushTokenClass.api_endpoint, req, g)

        # check for missing parameter in GET request
        builder = EnvironBuilder(method='GET',
                                 headers={})

        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01', 'timestamp': '2019-10-05T22:13:23+0100'}
        self.assertRaisesRegex(ParameterError, 'Missing parameter: \'signature\'',
                               PushTokenClass.api_endpoint, req, g)

        # check for invalid timestamp (very old)
        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01',
                        'timestamp': '2019-10-05T22:13:23+0100',
                        'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Timestamp 2019-10-05T22:13:23\+0100 not in valid range.',
                               PushTokenClass.api_endpoint, req, g)

        # check for invalid timestamp (recent but too early)
        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01',
                        'timestamp': (datetime.now(utc)
                                      - timedelta(minutes=2)).isoformat(),
                        'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Timestamp .* not in valid range.',
                               PushTokenClass.api_endpoint, req, g)

        # check for invalid timestamp (recent but too late)
        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01',
                        'timestamp': (datetime.now(utc)
                                      + timedelta(minutes=2)).isoformat(),
                        'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Timestamp .* not in valid range.',
                               PushTokenClass.api_endpoint, req, g)

        # check for broken timestamp
        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01',
                        'timestamp': '2019-broken-timestamp',
                        'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not parse timestamp .*\. ISO-Format required.',
                               PushTokenClass.api_endpoint, req, g)

        # check for timestamp of wrong type
        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01',
                        'timestamp': datetime.utcnow(),
                        'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not parse timestamp .*\. ISO-Format required.',
                               PushTokenClass.api_endpoint, req, g)

        # check for timezone unaware timestamp (we assume UTC then)
        req = Request(builder.get_environ())
        req.all_data = {'serial': 'SPASS01',
                        'timestamp': datetime.utcnow().isoformat(),
                        'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not verify signature!',
                               PushTokenClass.api_endpoint, req, g)

        # create a push token
        tparams = {'type': 'push', 'genkey': 1}
        tparams.update(FB_CONFIG_VALS)
        tok = init_token(param=tparams)
        serial = tok.get_serial()
        # now we need to perform the second rollout step
        builder = EnvironBuilder(method='POST',
                                 headers={})
        req = Request(builder.get_environ())
        req.all_data = {"enrollment_credential": tok.get_tokeninfo("enrollment_credential"),
                        "serial": serial,
                        "pubkey": self.smartphone_public_key_pem_urlsafe,
                        "fbtoken": "firebaseT"}
        res = PushTokenClass.api_endpoint(req, g)
        self.assertEqual(res[0], 'json', res)
        self.assertTrue(res[1]['result']['value'], res)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['detail']['rollout_state'], 'enrolled', res)

        remove_token(serial)

    def test_11_api_endpoint_update_fbtoken(self):
        g = FakeFlaskG()
        # create a push token
        tparams = {'type': 'push', 'genkey': 1}
        tparams.update(FB_CONFIG_VALS)
        tok = init_token(param=tparams)
        serial = tok.get_serial()

        # Run enrollment step 2
        tok.update({"enrollment_credential": tok.get_tokeninfo("enrollment_credential"),
                    "serial": serial,
                    "fbtoken": "firebasetoken1",
                    "pubkey": self.smartphone_public_key_pem_urlsafe})
        self.assertEqual(tok.token.get('rollout_state'), 'enrolled', tok)
        self.assertEqual(tok.get_tokeninfo('firebase_token'), 'firebasetoken1', tok)

        req_data = {'new_fb_token': 'firebasetoken2',
                    'serial': serial,
                    'timestamp': datetime.now(tz=utc).isoformat()}

        # now we perform the firebase token update with a broken signature
        builder = EnvironBuilder(method='POST',
                                 headers={})
        req = Request(builder.get_environ())
        req.all_data = req_data
        req.all_data.update({'signature': 'bad-signature'})
        self.assertRaisesRegex(privacyIDEAError, 'Could not verify signature!',
                               PushTokenClass.api_endpoint, req, g)

        # Create a correct signature
        sign_string = "{new_fb_token}|{serial}|{timestamp}".format(**req_data)
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        req_data.update({'signature': b32encode(sig)})

        # and perform the firebase token update
        builder = EnvironBuilder(method='POST',
                                 headers={})
        req = Request(builder.get_environ())
        req.all_data = req_data
        res = PushTokenClass.api_endpoint(req, g)
        self.assertEqual(res[0], 'json', res)
        self.assertTrue(res[1]['result']['value'], res)
        self.assertTrue(res[1]['result']['status'], res)

        self.assertEqual(tok.token.get('rollout_state'), 'enrolled', tok)
        self.assertEqual(tok.get_tokeninfo('firebase_token'), req_data['new_fb_token'], tok)
        tok.delete_token()

    def test_15_poll_endpoint(self):
        g = FakeFlaskG()
        set_policy("push1", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       PUSH_ACTION.FIREBASE_CONFIG,
                       self.firebase_config_name,
                       PUSH_ACTION.REGISTRATION_URL, REGISTRATION_URL,
                       PUSH_ACTION.TTL, TTL))
        g.policy_object = PolicyClass()
        # set up the Firebase Gateway
        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                           "myFB", FB_CONFIG_VALS)
        self.assertGreater(r, 0)

        # create a new push token
        tok = self._create_push_token()
        serial = tok.get_serial()

        # this is the default timestamp for polling in this test
        timestamp = datetime(2020, 6, 19, 13, 27, tzinfo=utc)

        # create a poll request
        # first create a signature
        ts = timestamp.isoformat()
        sign_string = "{serial}|{timestamp}".format(serial=serial, timestamp=ts)
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())

        builder = EnvironBuilder(method='GET',
                                 headers={})
        req = Request(builder.get_environ())
        req.all_data = {'serial': serial,
                        'timestamp': ts,
                        'signature': b32encode(sig)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(req, g)
        self.assertTrue(res[1]['result']['status'], res)
        # No challenge created yet
        self.assertEqual(res[1]['result']['value'], [], res[1]['result'])

        # we need to create a challenge which we can check for with polling
        # use a given time for the challenge (15 seconds before the poll)
        challenge_timestamp = timestamp - timedelta(seconds=15)
        with mock.patch('privacyidea.models.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = challenge_timestamp.replace(tzinfo=None)
            challenge = b32encode_and_unicode(geturandom())
            db_challenge = Challenge(serial, challenge=challenge)
            db_challenge.save()
        tid = db_challenge.get_transaction_id()
        self.assertGreater(len(get_challenges(transaction_id=tid)), 0)

        # now check that we receive the challenge when polling
        # since we mock the time we can use the same request data
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(req, g)
        self.assertTrue(res[1]['result']['status'], res)
        chall = res[1]['result']['value'][0]
        self.assertEqual(chall['nonce'], challenge, chall)
        self.assertIn('signature', chall, chall)
        # check that the signature matches
        sign_string = "{nonce}|{url}|{serial}|{question}|{title}|{sslverify}".format(**chall)
        parsed_stripped_server_pubkey = serialization.load_pem_public_key(
            to_bytes(self.server_public_key_pem),
            default_backend())
        parsed_stripped_server_pubkey.verify(b32decode(chall['signature']),
                                             sign_string.encode('utf8'),
                                             padding.PKCS1v15(),
                                             hashes.SHA256())
        self.assertFalse(db_challenge.get_otp_status()[1], str(db_challenge))

        # Now mark the challenge as answered so we receive an empty list
        db_challenge.set_otp_status(True)
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(req, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # disallow polling through a policy
        set_policy('push_poll', SCOPE.AUTH,
                   action='{0!s}={1!s}'.format(PUSH_ACTION.ALLOW_POLLING,
                                               PushAllowPolling.DENY))
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(PolicyError,
                                   r'Polling not allowed!',
                                   PushTokenClass.api_endpoint, req, g)

        # disallow polling based on a per token configuration
        set_policy('push_poll', SCOPE.AUTH,
                   action='{0!s}={1!s}'.format(PUSH_ACTION.ALLOW_POLLING,
                                               PushAllowPolling.TOKEN))
        # If no tokeninfo is set, allow polling
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(req, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # now set the tokeninfo POLLING_ALLOWED to 'False'
        tok.add_tokeninfo(POLLING_ALLOWED, 'False')
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(PolicyError,
                                   r'Polling not allowed!',
                                   PushTokenClass.api_endpoint, req, g)

        # Explicitly allow polling for this token
        tok.add_tokeninfo(POLLING_ALLOWED, 'True')
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(req, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # If polling for this token is denied but the overall configuration
        # allows polling, the tokeninfo is ignored
        tok.add_tokeninfo(POLLING_ALLOWED, 'False')
        set_policy('push_poll', SCOPE.AUTH,
                   action='{0!s}={1!s}'.format(PUSH_ACTION.ALLOW_POLLING,
                                               PushAllowPolling.ALLOW))
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(req, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # this should also work if there is no ALLOW_POLLING policy
        delete_policy('push_poll')
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(req, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # check for a non-existing serial
        unknown_serial = 'unknown_serial_01'
        # we shouldn't run into a signature check so we don't create one
        req.all_data = {'serial': unknown_serial,
                        'timestamp': ts,
                        'signature': b32encode(b'no signature check')}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, req, g)

        # serial exists but signature is wrong
        sig_fail = bytearray(sig)
        sig_fail[0] += 1
        req.all_data = {'serial': serial,
                        'timestamp': ts,
                        'signature': b32encode(sig_fail)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, req, g)

        # check for a wrongly created signature (inverted timestamp, serial)
        sign_string2 = "{timestamp}|{serial}".format(serial=serial, timestamp=ts)
        sig_fail2 = self.smartphone_private_key.sign(sign_string2.encode('utf8'),
                                                     padding.PKCS1v15(),
                                                     hashes.SHA256())
        req.all_data = {'serial': serial,
                        'timestamp': ts,
                        'signature': b32encode(sig_fail2)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, req, g)

        # the serial exists but does not belong to a push token
        tok2 = init_token(param={'type': 'hotp', 'genkey': 1})
        serial2 = tok2.get_serial()
        # we shouldn't run into the signature check here
        req.all_data = {'serial': serial2,
                        'timestamp': datetime.utcnow().isoformat(),
                        'signature': b32encode(b"signature not needed")}
        # poll for challenges
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not verify signature!',
                               PushTokenClass.api_endpoint, req, g)

        # wrongly configured push token (no firebase config)
        tok.del_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG)
        # We are missing a registration URL, thus polling of challenges fails
        delete_policy("push1")
        req.all_data = {'serial': serial,
                        'timestamp': ts,
                        'signature': b32encode(sig)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, req, g)

        # unknown firebase configuration
        tok.add_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG, 'my unknown firebase config')
        req.all_data = {'serial': serial,
                        'timestamp': ts,
                        'signature': b32encode(sig)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1,\
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, req, g)

        # cleanup
        tok.delete_token()
        tok2.delete_token()
        delete_smsgateway(self.firebase_config_name)
