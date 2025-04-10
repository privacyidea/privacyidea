import json
import time
from base64 import b32decode, b32encode
from datetime import datetime, timedelta, timezone
from threading import Timer

import mock
import responses
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from flask import Request
from google.oauth2 import service_account
from pytz import utc
from werkzeug.test import EnvironBuilder

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.error import ConfigAdminError
from privacyidea.lib.error import ParameterError, privacyIDEAError, PolicyError
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.policy import (SCOPE, set_policy, delete_policy, ACTION,
                                    LOGINMODE, PolicyClass)
from privacyidea.lib.smsprovider.FirebaseProvider import FIREBASE_CONFIG
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway, delete_smsgateway
from privacyidea.lib.token import get_tokens, remove_token, init_token
from privacyidea.lib.tokenclass import CHALLENGE_SESSION
from privacyidea.lib.tokens.pushtoken import (PushTokenClass, PUSH_ACTION,
                                              DEFAULT_CHALLENGE_TEXT, strip_key,
                                              PUBLIC_KEY_SMARTPHONE, PRIVATE_KEY_SERVER,
                                              PUBLIC_KEY_SERVER, AVAILABLE_PRESENCE_OPTIONS_ALPHABETIC,
                                              AVAILABLE_PRESENCE_OPTIONS_NUMERIC,
                                              PushAllowPolling, POLLING_ALLOWED, POLL_ONLY)
from privacyidea.lib.user import (User)
from privacyidea.lib.utils import to_bytes, b32encode_and_unicode, to_unicode, AUTH_RESPONSE
from privacyidea.models import Token, Challenge
from .base import MyTestCase, FakeFlaskG

PWFILE = "tests/testdata/passwords"
FIREBASE_FILE = "tests/testdata/firebase-test.json"
CLIENT_FILE = "tests/testdata/google-services.json"

REGISTRATION_URL = "http://test/ttype/push"
TTL = 10
FB_CONFIG_VALS = {
    FIREBASE_CONFIG.JSON_CONFIG: FIREBASE_FILE}


def _create_credential_mock():
    c = service_account.Credentials("a", "b", "c")
    return mock.MagicMock(spec=c, expired=False, expiry=None, access_token='my_new_bearer_token')


def _check_firebase_params(request):
    payload = json.loads(request.body)
    # check the signature in the payload!
    data = payload.get("message").get("data")

    sign_string = "{nonce}|{url}|{serial}|{question}|{title}|{sslverify}".format(**data)
    token = get_tokens(serial=data.get("serial"))[0]
    pem_public_key = token.get_tokeninfo(PUBLIC_KEY_SERVER)
    public_key = load_pem_public_key(to_bytes(pem_public_key), backend=default_backend())
    signature = b32decode(data.get("signature"))
    # If signature does not match it will raise InvalidSignature exception
    public_key.verify(signature, sign_string.encode("utf8"), padding.PKCS1v15(), hashes.SHA256())
    headers = {"request-id": "728d329e-0e86-11e4-a748-0c84dc037c13"}
    return 200, headers, json.dumps({})


class PushTokenTestCase(MyTestCase):
    serial1 = "PUSH00001"

    server_private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096, backend=default_backend())
    server_private_key_pem = to_unicode(server_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption())
    )
    server_public_key_pem = to_unicode(server_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    )

    # We now allow white spaces in the firebase config name
    firebase_config_name = "my firebase config"

    smartphone_private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096, backend=default_backend())
    smartphone_public_key = smartphone_private_key.public_key()
    smartphone_public_key_pem = to_unicode(smartphone_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    # The smartphone sends the public key in URLsafe and without the ----BEGIN header
    smartphone_public_key_pem_urlsafe = strip_key(smartphone_public_key_pem).replace("+", "-").replace("/", "_")

    def _create_push_token(self):
        token_param = {"type": "push", "genkey": 1}
        token_param.update(FB_CONFIG_VALS)
        token = init_token(param=token_param)
        token.add_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG, self.firebase_config_name)
        token.add_tokeninfo(PUBLIC_KEY_SMARTPHONE, self.smartphone_public_key_pem_urlsafe)
        token.add_tokeninfo("firebase_token", "firebaseT")
        token.add_tokeninfo(PUBLIC_KEY_SERVER, self.server_public_key_pem)
        token.add_tokeninfo(PRIVATE_KEY_SERVER, self.server_private_key_pem, "password")
        token.del_tokeninfo("enrollment_credential")
        token.token.rollout_state = "enrolled"
        token.token.active = True
        return token

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
        augmented_pubkey = f"-----BEGIN RSA PUBLIC KEY-----\n{detail.get('public_key')}\n-----END RSA PUBLIC KEY-----\n"
        parsed_stripped_server_pubkey = serialization.load_pem_public_key(
            to_bytes(augmented_pubkey),
            default_backend())
        self.assertEqual(parsed_server_pubkey.public_numbers(), parsed_stripped_server_pubkey.public_numbers())
        remove_token(self.serial1)

    def test_01a_enroll_with_app_pin(self):
        token_param = {"type": "push", "genkey": 1}
        token_param.update(FB_CONFIG_VALS)
        token = init_token(param=token_param)
        detail = token.get_init_detail(params={PUSH_ACTION.FIREBASE_CONFIG: POLL_ONLY,
                                               PUSH_ACTION.REGISTRATION_URL: "https://privacyidea.com/enroll",
                                               ACTION.FORCE_APP_PIN: True})
        self.assertIn("pin=True", detail["pushurl"]["value"])
        remove_token(token.get_serial())

    def test_02a_lib_enroll(self):
        r = set_smsgateway(self.firebase_config_name,
                           "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider",
                           "myFB", FB_CONFIG_VALS)
        self.assertTrue(r > 0)
        set_policy("push1", scope=SCOPE.ENROLL,
                   action=f"{PUSH_ACTION.FIREBASE_CONFIG}={self.firebase_config_name}")
        token = self._create_push_token()
        remove_token(token.get_serial())

    @responses.activate
    def test_03a_api_authenticate_fail(self):
        # This tests failure to communicate to the firebase service
        self.setUp_user_realms()
        # create FireBase Service and policies
        set_smsgateway(self.firebase_config_name,
                       "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider",
                       "myFB", FB_CONFIG_VALS)
        set_policy("push1", scope=SCOPE.ENROLL,
                   action=f"{PUSH_ACTION.FIREBASE_CONFIG}={self.firebase_config_name},"
                          f"{PUSH_ACTION.REGISTRATION_URL}={REGISTRATION_URL},"
                          f"{PUSH_ACTION.TTL}={TTL}")
        # create push token
        token = self._create_push_token()
        serial = token.get_serial()
        # set PIN
        token.set_pin("pushpin")
        token.add_user(User("cornelius", self.realm1))

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch("privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials"
                        ".from_service_account_file") as mock_service_account:
            # alternative: side_effect instead of return_value
            mock_service_account.return_value = _create_credential_mock()

            # add responses, to simulate the failing communication (status 500)
            responses.add(responses.POST, "https://fcm.googleapis.com/v1/projects/test-123456/messages:send",
                          body="""{}""",
                          status=500,
                          content_type="application/json")

            # Send the first authentication request to trigger the challenge
            with mock.patch("logging.Logger.warning") as mock_log:
                with self.app.test_request_context("/validate/check",
                                                   method="POST",
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
                    mock_log.assert_called_with(f"Failed to submit message to Firebase service for token {serial}.")
                    # Check that the user was informed about the need to poll
                    detail = res.json.get("detail")
                    self.assertEqual("Please confirm the authentication on your mobile device! "
                                     "Use the polling feature of your privacyIDEA Authenticator App "
                                     "to check for a new Login request.", detail.get("message"))

            # Our ServiceAccountCredentials mock has been called once, because
            # no access token has been fetched before
            mock_service_account.assert_called_once()
            self.assertIn(FIREBASE_FILE, get_app_local_store()["firebase_token"])

            # By default, polling is allowed for push tokens so the corresponding
            # challenge should be available in the challenge table, even though
            # the request to firebase failed.
            challenges = get_challenges(serial=token.token.serial)
            self.assertEqual(len(challenges), 1, challenges)
            challenges[0].delete()

            # Do the same with the parameter "exception", so that we receive an Error on HTTP
            with self.app.test_request_context("/validate/check",
                                               method="POST",
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
            challenges = get_challenges(serial=token.token.serial)
            self.assertEqual(len(challenges), 1, challenges)
            challenges[0].delete()

            # Now disable polling and check that no challenge is created
            # disallow polling through a policy
            set_policy("push_poll", SCOPE.AUTH,
                       action=f"{PUSH_ACTION.ALLOW_POLLING}={PushAllowPolling.DENY}")

            with mock.patch("logging.Logger.warning") as mock_log:
                with self.app.test_request_context("/validate/check",
                                                   method="POST",
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
                    mock_log.assert_called_with(f"Failed to submit message to Firebase service for token {serial}.")
            self.assertEqual(len(get_challenges(serial=token.token.serial)), 0)
            # disallow polling the specific token through a policy
            set_policy("push_poll", SCOPE.AUTH,
                       action=f"{PUSH_ACTION.ALLOW_POLLING}={PushAllowPolling.TOKEN}")
            token.add_tokeninfo(POLLING_ALLOWED, False)
            with mock.patch("logging.Logger.warning") as mock_log:
                with self.app.test_request_context("/validate/check",
                                                   method="POST",
                                                   data={"user": "cornelius",
                                                         "realm": self.realm1,
                                                         "pass": "pushpin"}):
                    res = self.app.full_dispatch_request()
                    self.assertEqual(200, res.status_code)
                    result = res.json.get("result")
                    self.assertTrue(result.get("status"))
                    self.assertFalse(result.get("value"))
                    self.assertEqual("CHALLENGE", result.get("authentication"))
                    # Check that the warning was written to the log file.
                    mock_log.assert_called_with(f"Failed to submit message to Firebase service for token {serial}.")
            self.assertEqual(len(get_challenges(serial=token.token.serial)), 0)

            # Do the same with the parameter "exception", so that we receive an Error on HTTP
            with self.app.test_request_context("/validate/check",
                                               method="POST",
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
            # We also add the presence_required policy.
            set_policy("push_presence", SCOPE.AUTH,
                       action=f"{PUSH_ACTION.REQUIRE_PRESENCE}=1")
            responses.replace(responses.POST,
                              "https://fcm.googleapis.com/v1/projects/test-123456/messages:send",
                              body="""{}""",
                              content_type="application/json")
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                self.assertTrue(res.json.get("result").get("status"))
            self.assertEqual(len(get_challenges(serial=token.token.serial)), 1)
            challenges = get_challenges(serial=token.token.serial)[0]
            # Check in the challenge for a require_presence value, this indicates, that the challenges was created
            self.assertIn(challenges.data.split(',').pop(), AVAILABLE_PRESENCE_OPTIONS_ALPHABETIC)
            challenges.delete()

        remove_token(serial=serial)
        delete_smsgateway(self.firebase_config_name)
        delete_policy("push_poll")
        delete_policy("push1")
        delete_policy("push_presence")

    @responses.activate
    def test_03b_api_authenticate_client(self):
        # Test the /validate/check endpoints without the smartphone endpoint /ttype/push
        self.setUp_user_realms()
        # create FireBase Service and policies
        set_smsgateway(self.firebase_config_name,
                       "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider",
                       "myFB", FB_CONFIG_VALS)
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PUSH_ACTION.FIREBASE_CONFIG}={self.firebase_config_name}")
        # create push token
        token = self._create_push_token()
        serial = token.get_serial()
        # set PIN
        token.set_pin("pushpin")
        token.add_user(User("cornelius", self.realm1))

        cached_fbtoken = {
            "firebase_token": {FB_CONFIG_VALS[FIREBASE_CONFIG.JSON_CONFIG]: _create_credential_mock()}}
        self.app.config.setdefault("_app_local_store", {}).update(cached_fbtoken)
        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch("privacyidea.lib.smsprovider.FirebaseProvider.service_account"
                        ".Credentials.from_service_account_file") as mock_service_account:
            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, "https://fcm.googleapis.com/v1/projects"
                                          "/test-123456/messages:send",
                          body="""{}""",
                          content_type="application/json")

            # Send the first authentication request to trigger the challenge
            with self.app.test_request_context("/validate/check",
                                               method="POST",
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                json_response = res.json
                self.assertFalse(json_response.get("result").get("value"))
                self.assertTrue(json_response.get("result").get("status"))
                self.assertEqual(json_response.get("detail").get("serial"), token.token.serial)
                self.assertTrue("transaction_id" in json_response.get("detail"))
                transaction_id = json_response.get("detail").get("transaction_id")
                self.assertEqual(json_response.get("detail").get("message"), DEFAULT_CHALLENGE_TEXT)

            # Our ServiceAccountCredentials mock has not been called because we use a cached token
            mock_service_account.assert_not_called()
            self.assertIn(FIREBASE_FILE, get_app_local_store()["firebase_token"])
            # remove cached Credentials
            get_app_local_store().pop("firebase_token")

        # The mobile device has not communicated with the backend, yet.
        # The user is not authenticated!
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            json_response = res.json
            # Result-Value is false, the user has not answered the challenge, yet
            self.assertFalse(json_response.get("result").get("value"))

        # As the challenge has not been answered yet, the /validate/polltransaction endpoint returns false
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           query_string={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # Now the smartphone communicates with the backend and the challenge in the database table
        # is marked as answered successfully.
        challenges = get_challenges(serial=token.token.serial, transaction_id=transaction_id)
        challenges[0].set_otp_status(True)

        # As the challenge has been answered, the /validate/polltransaction endpoint returns true
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertTrue(res.json["result"]["value"])

        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "state": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            json_response = res.json
            # Result-Value is True, since the challenge is marked resolved in the DB
        self.assertTrue(json_response.get("result").get("value"))

        # As the challenge does not exist anymore, the /validate/polltransaction endpoint returns false
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])
        self.assertEqual(get_challenges(serial=token.token.serial), [])

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        # Do single shot auth with waiting
        # Also mock time.time to be 4000 seconds in the future (exceeding the validity of myAccessTokenInfo),
        # so that we fetch a new auth token
        with mock.patch("privacyidea.lib.smsprovider.FirebaseProvider.time") as mock_time:
            mock_time.time.return_value = time.time() + 4000

            with mock.patch(
                    "privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials"
                    ".from_service_account_file") as mock_service_account:
                # alternative: side_effect instead of return_value
                mock_service_account.return_value = _create_credential_mock()

                # add responses, to simulate the communication to firebase
                responses.add(responses.POST, "https://fcm.googleapis.com/v1/projects/test-123456/messages:send",
                              body="""{}""",
                              content_type="application/json")

                # In two seconds we need to run an update on the challenge table.
                Timer(2, self._mark_challenge_as_accepted).start()

                set_policy("push1", scope=SCOPE.AUTH, action=f"{PUSH_ACTION.WAIT}=20")
                # Send the first authentication request to trigger the challenge
                with self.app.test_request_context("/validate/check",
                                                   method="POST",
                                                   data={"user": "cornelius",
                                                         "realm": self.realm1,
                                                         "pass": "pushpin"}):
                    res = self.app.full_dispatch_request()
                    self.assertEqual(200, res.status_code)
                    json_response = res.json
                    # We successfully authenticated! YEAH!
                    self.assertTrue(json_response.get("result").get("value"))
                    self.assertTrue(json_response.get("result").get("status"))
                    self.assertEqual(json_response.get("detail").get("serial"), token.token.serial)
                delete_policy("push1")

            # Our ServiceAccountCredentials mock has been called once because we fetched a new token
            mock_service_account.assert_called_once()
            self.assertIn(FIREBASE_FILE, get_app_local_store()["firebase_token"])
            self.assertEqual(get_app_local_store()["firebase_token"][FIREBASE_FILE].access_token,
                             "my_new_bearer_token")

        # Authentication fails, if the push notification is not accepted within the configured time
        with mock.patch("privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials"
                        ".from_service_account_file") as mock_service_account:
            # alternative: side_effect instead of return_value
            mock_service_account.return_value = _create_credential_mock()

            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, "https://fcm.googleapis.com/v1/projects/test-123456/messages:send",
                          body="""{}""",
                          content_type="application/json")

            set_policy("push1", scope=SCOPE.AUTH, action=f"{PUSH_ACTION.WAIT}=1")
            # Send the first authentication request to trigger the challenge
            with self.app.test_request_context("/validate/check",
                                               method="POST",
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                json_response = res.json
                # We fail to authenticate! Oh No!
                self.assertFalse(json_response.get("result").get("value"))
                self.assertTrue(json_response.get("result").get("status"))
                self.assertEqual(json_response.get("detail").get("serial"), token.token.serial)
            delete_policy("push1")
        delete_policy('push_config')
        remove_token(serial=serial)

    def _mark_challenge_as_accepted(self):
        # We simply mark all challenges as successfully answered!
        with self.app.test_request_context():
            challenges = get_challenges()
            for challenge in challenges:
                challenge.set_otp_status(True)
                challenge.save()

    @responses.activate
    def test_04_api_authenticate_smartphone(self):
        # Test the /validate/check endpoints and the smartphone endpoint /ttype/push
        # for authentication

        ## Create rolled out push token
        self.setUp_user_realms()
        # create FireBase Service and policies
        set_smsgateway(self.firebase_config_name,
                       'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                       "myFB", FB_CONFIG_VALS)
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

        # Correct signature for the wrong challenge should result in failure
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
        remove_token(serial=serial)

    def test_04_decline_auth_request(self):
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

        # The challenge is still in the database, but it is marked as declined
        challenge = challengeobject_list[0]
        self.assertEqual(CHALLENGE_SESSION.DECLINED, challenge.session)

        with self.app.test_request_context('/validate/polltransaction', method='GET',
                                           query_string={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])
            self.assertEqual(res.json["detail"]["challenge_status"], "declined", res.json["detail"]["challenge_status"])
        remove_token(serial=serial)

    def test_05_strip_key(self):
        stripped_pubkey = strip_key(self.smartphone_public_key_pem)
        self.assertIn("-BEGIN PUBLIC KEY-", self.smartphone_public_key_pem)
        self.assertNotIn("-BEGIN PUBLIC KEY_", stripped_pubkey)
        self.assertNotIn("-", stripped_pubkey)
        self.assertEqual(strip_key(stripped_pubkey), stripped_pubkey)
        self.assertEqual(strip_key("\n\n" + stripped_pubkey + "\n\n"), stripped_pubkey)

    @responses.activate
    def test_06a_api_auth(self):
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
                                                     # this will be overwritten by pushtoken_disable_wait
                                                     PUSH_ACTION.WAIT: "10",
                                                     "password": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                jsonresp = res.json
                self.assertFalse(jsonresp.get("result").get("value"))
                self.assertTrue(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp["result"]["authentication"], AUTH_RESPONSE.CHALLENGE)
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
            self.assertIsInstance(res.json["result"]["value"], dict, res.json)
            self.assertIn("role", res.json["result"]["value"], res.json)
            self.assertIn("rights", res.json["result"]["value"], res.json)
            self.assertEqual(res.json["result"]["authentication"], AUTH_RESPONSE.ACCEPT, res.json)

        delete_policy("push1")
        delete_policy("webui")
        remove_token(serial=serial)

    @responses.activate
    def test_06b_api_auth_presence(self):
        """
        Test that the require-presence option works with multiple push token triggered and also with a different
        token type triggered as well.
        """
        self.setUp_user_realms()
        # Create Firebase Service and policies
        set_smsgateway(self.firebase_config_name,
                       'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                       "myFB", FB_CONFIG_VALS)
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PUSH_ACTION.FIREBASE_CONFIG}={self.firebase_config_name}")

        user = User("cornelius", self.realm1)

        # Create push token
        push_token1 = self._create_push_token()
        push_token2 = self._create_push_token()
        totp_token = init_token({"type": "totp", "genkey": 1})
        tokens = [push_token1, push_token2, totp_token]
        serials = [token.get_serial() for token in tokens]

        # Set the same PINs, so that both get triggered
        push_token1.set_pin("pushpin")
        push_token1.add_user(user)
        push_token2.set_pin("pushpin")
        push_token2.add_user(user)
        totp_token.set_pin("pushpin")
        totp_token.add_user(user)

        # Set policies
        set_policy("webui", scope=SCOPE.WEBUI, action=f"{ACTION.LOGINMODE}={LOGINMODE.PRIVACYIDEA}")
        set_policy("push_require_presence", scope=SCOPE.AUTH, action=f"{PUSH_ACTION.REQUIRE_PRESENCE}=1")
        set_policy("totp_challenge_response", scope=SCOPE.AUTH, action=f"{ACTION.CHALLENGERESPONSE}=totp")

        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                        '.from_service_account_file') as fb_service_account:
            # Alternative: side_effect instead of return_value
            fb_service_account.from_json_keyfile_name.return_value = _create_credential_mock()

            # Add the responses to simulate the communication with firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          body="""{}""",
                          content_type="application/json")

            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "cornelius",
                                                     "realm": self.realm1,
                                                     # This will be overwritten by pushtoken_disable_wait
                                                     PUSH_ACTION.WAIT: "10",
                                                     "password": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                response_json = res.json
                self.assertFalse(response_json.get("result").get("value"))
                self.assertTrue(response_json.get("result").get("status"))
                self.assertEqual(response_json["result"]["authentication"],
                                 AUTH_RESPONSE.CHALLENGE, response_json)
                self.assertTrue(response_json.get("detail").get("serial") in serials)
                self.assertIn("transaction_id", response_json.get("detail"))

                # Three challenges should be triggered, both push challenges with the same message!
                multi_challenge = response_json.get("detail").get("multi_challenge")
                self.assertEqual(len(multi_challenge), 3)
                push_challenges = [c for c in multi_challenge if c.get("type") == "push"]
                self.assertEqual(len(push_challenges), 2)
                self.assertEqual(push_challenges[0].get("message"), push_challenges[1].get("message"))

                # Get the challenge from the database
                transaction_id = response_json.get("detail").get("transaction_id")
                challenge_messages = [m.strip() for m in response_json.get("detail").get("message").split(",")]
                challenges = get_challenges(serial=push_token1.token.serial, transaction_id=transaction_id)
                challenge = challenges[0]
                # The correct answer is always appended to the available options
                presence_answer = challenge.get_data().split(',').pop()
                challenge_text = DEFAULT_CHALLENGE_TEXT + f" Please press: {presence_answer}"
                self.assertTrue(challenge_text in challenge_messages)

        self.assertTrue(presence_answer is not None)
        self.assertTrue(presence_answer in AVAILABLE_PRESENCE_OPTIONS_ALPHABETIC)

        # This is the smartphone answer:
        # Create the signature
        sign_data = f"{challenge.challenge}|{push_token1.token.serial}|{presence_answer}"
        signature = b32encode_and_unicode(
            self.smartphone_private_key.sign(sign_data.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()))

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
                                           data={"serial": push_token1.token.serial,
                                                 "nonce": challenge,
                                                 "signature": signature,
                                                 "presence_answer": presence_answer}):
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
            self.assertIsInstance(res.json["result"]["value"], dict, res.json)
            self.assertEqual(res.json["result"]["authentication"],
                             AUTH_RESPONSE.ACCEPT, res.json)

        remove_token(push_token1.get_serial())
        remove_token(push_token2.get_serial())
        remove_token(totp_token.get_serial())
        delete_policy("webui")
        delete_policy("push_require_presence")
        delete_policy("totp_challenge_response")

    @responses.activate
    def test_06c_api_auth_presence_numeric(self):
        self.setUp_user_realms()
        # Create Firebase Service and policies
        set_smsgateway(self.firebase_config_name,
                       'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                       "myFB", FB_CONFIG_VALS)
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PUSH_ACTION.FIREBASE_CONFIG}={self.firebase_config_name}")
        set_policy("push_numeric", scope=SCOPE.AUTH,
                   action=f"{PUSH_ACTION.PRESENCE_OPTIONS}=NUMERIC")
        # Create push token
        token_object = self._create_push_token()

        # Set PIN
        token_object.set_pin("pushpin")
        token_object.add_user(User("cornelius", self.realm1))

        # Set a loginmode policy
        set_policy("webui", scope=SCOPE.WEBUI,
                   action=f"{ACTION.LOGINMODE}={LOGINMODE.PRIVACYIDEA}")
        # Set a policy to require presence
        set_policy("push_require_presence", scope=SCOPE.AUTH, action=f"{PUSH_ACTION.REQUIRE_PRESENCE}=1")
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                        '.from_service_account_file') as fb_service_account:
            # Alternative: side_effect instead of return_value
            fb_service_account.from_json_keyfile_name.return_value = _create_credential_mock()

            # Add the responses to simulate the communication with firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          body="""{}""",
                          content_type="application/json")

            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "cornelius",
                                                     "realm": self.realm1,
                                                     # This will be overwritten by pushtoken_disable_wait
                                                     PUSH_ACTION.WAIT: "10",
                                                     "password": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                # Get the challenge from the database

                response_json = res.json
                self.assertFalse(response_json.get("result").get("value"))
                self.assertTrue(response_json.get("result").get("status"))
                self.assertEqual(response_json["result"]["authentication"],
                                 AUTH_RESPONSE.CHALLENGE, response_json)
                self.assertEqual(response_json.get("detail").get("serial"), token_object.token.serial)
                self.assertIn("transaction_id", response_json.get("detail"))
                transaction_id = response_json.get("detail").get("transaction_id")
                challenges = get_challenges(serial=token_object.token.serial, transaction_id=transaction_id)
                challenge_object = challenges[0]
                # The correct answer is always appended to the available options
                presence_answer = challenge_object.get_data().split(',').pop()
                challenge_text = DEFAULT_CHALLENGE_TEXT + f" Please press: {presence_answer}"
                self.assertEqual(response_json.get("detail").get("message"), challenge_text)

        self.assertTrue(presence_answer is not None)
        self.assertTrue(presence_answer in AVAILABLE_PRESENCE_OPTIONS_NUMERIC)

        # This is the smartphone answer:
        # Create the signature
        sign_data = f"{challenge_object.challenge}|{token_object.token.serial}|{presence_answer}"
        signature = b32encode_and_unicode(
            self.smartphone_private_key.sign(sign_data.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()))

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
                                           data={"serial": token_object.token.serial,
                                                 "nonce": challenge_object,
                                                 "signature": signature,
                                                 "presence_answer": presence_answer}):
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
            self.assertIsInstance(res.json["result"]["value"], dict, res.json)
            self.assertEqual(res.json["result"]["authentication"],
                             AUTH_RESPONSE.ACCEPT, res.json)

        remove_token(token_object.get_serial())
        delete_policy("webui")
        delete_policy("push_require_presence")
        delete_policy("push_numeric")

    @responses.activate
    def test_06d_api_auth_presence_custom(self):
        self.setUp_user_realms()
        custom_presence_options = "0A:1B:2C:3D:4E:5F:6G:7H:8I:9J"
        custom_options_list = custom_presence_options.split(":")
        # create FireBase Service and policies
        set_smsgateway(self.firebase_config_name,
                       'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                       "myFB", FB_CONFIG_VALS)
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PUSH_ACTION.FIREBASE_CONFIG}={self.firebase_config_name}")
        set_policy("push_custom", scope=SCOPE.AUTH,
                   action=f"{PUSH_ACTION.PRESENCE_OPTIONS}=CUSTOM")
        set_policy("push_custom_options", scope=SCOPE.AUTH,
                   action=f"{PUSH_ACTION.PRESENCE_CUSTOM_OPTIONS}={custom_presence_options}")
        # create push token
        token = self._create_push_token()

        # set PIN
        token.set_pin("pushpin")
        token.add_user(User("cornelius", self.realm1))

        # Set a loginmode policy
        set_policy("webui", scope=SCOPE.WEBUI,
                   action=f"{ACTION.LOGINMODE}={LOGINMODE.PRIVACYIDEA}")
        # Set a policy to require presence
        set_policy("push_require_presence", scope=SCOPE.AUTH, action=f"{PUSH_ACTION.REQUIRE_PRESENCE}=1")
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account.Credentials'
                        '.from_service_account_file') as mock_service_account:
            # alternative: side_effect instead of return_value
            mock_service_account.from_json_keyfile_name.return_value = _create_credential_mock()

            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          body="""{}""",
                          content_type="application/json")

            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "cornelius",
                                                     "realm": self.realm1,
                                                     # this will be overwritten by pushtoken_disable_wait
                                                     PUSH_ACTION.WAIT: "10",
                                                     "password": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                # Get the challenge from the database

                json_response = res.json
                self.assertFalse(json_response.get("result").get("value"))
                self.assertTrue(json_response.get("result").get("status"))
                self.assertEqual(json_response["result"]["authentication"],
                                 AUTH_RESPONSE.CHALLENGE, res.json)
                self.assertEqual(json_response.get("detail").get("serial"), token.token.serial)
                self.assertIn("transaction_id", json_response.get("detail"))
                transaction_id = json_response.get("detail").get("transaction_id")
                challenges = get_challenges(serial=token.token.serial, transaction_id=transaction_id)
                challenge = challenges[0]
                nonce = challenge.challenge
                # The correct answer is always appended to the available options
                presence_answer = challenge.get_data().split(',').pop()
                challenge_text = DEFAULT_CHALLENGE_TEXT + f" Please press: {presence_answer}"
                self.assertEqual(json_response.get("detail").get("message"), challenge_text)

        self.assertIsNotNone(presence_answer)
        self.assertIn(presence_answer, custom_options_list)
        # This is what the smartphone answers.
        # create the signature:
        sign_data = f"{nonce}|{token.token.serial}|{presence_answer}"
        signature = b32encode_and_unicode(
            self.smartphone_private_key.sign(sign_data.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()))

        # We still cannot log in
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": self.realm1,
                                                 "password": "",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            self.assertFalse(res.json['result']['status'])

        # Answer the challenge
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": token.token.serial,
                                                 "nonce": challenge,
                                                 "signature": signature,
                                                 "presence_answer": presence_answer}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
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
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json['result']['status'])
            self.assertIsInstance(res.json["result"]["value"], dict, res.json)
            self.assertEqual(res.json["result"]["authentication"],
                             AUTH_RESPONSE.ACCEPT, res.json)

        remove_token(token.get_serial())
        delete_policy("webui")
        delete_policy("push_require_presence")

    def test_06e_require_presence_text_replace(self):
        # Set a loginmode policy
        set_policy("webui", scope=SCOPE.WEBUI, action=f"{ACTION.LOGINMODE}={LOGINMODE.PRIVACYIDEA}")
        # Set a policy to require presence
        set_policy("push_require_presence", scope=SCOPE.AUTH, action=f"{PUSH_ACTION.REQUIRE_PRESENCE}=1")
        set_policy("text", scope=SCOPE.AUTH, action="challenge_text=the answer is {presence_answer}")

        self.setUp_user_realms()
        token = self._create_push_token()
        token.add_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG, POLL_ONLY)
        token.set_pin("pushpin")
        token.add_user(User("cornelius", self.realm1))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": self.realm1,
                                                 "password": "pushpin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertFalse(res.json.get("result").get("value"))
            self.assertTrue(res.json.get("result").get("status"))
            self.assertEqual(res.json.get("detail").get("serial"), token.token.serial)
            self.assertIn("transaction_id", res.json.get("detail"))
            transaction_id = res.json.get("detail").get("transaction_id")
            challenges = get_challenges(serial=token.token.serial, transaction_id=transaction_id)
            challenge = challenges[0]
            # The correct answer is always appended to the available options
            presence_answer = challenge.get_data().split(",").pop()
            challenge_text = f"the answer is {presence_answer}"
            self.assertEqual(challenge_text, res.json.get("detail").get("message"))
        delete_policy("text")
        delete_policy("push_require_presence")
        delete_policy("webui")
        remove_token(token.get_serial())

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
        builder = EnvironBuilder(method='PUT', headers={})

        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01'}
        self.assertRaisesRegex(privacyIDEAError,
                               'Method PUT not allowed in \'api_endpoint\' '
                               'for push token.',
                               PushTokenClass.api_endpoint, request, g)

        # check for parameter error in POST request
        builder = EnvironBuilder(method='POST', headers={})

        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01'}
        self.assertRaisesRegex(ParameterError, 'Missing parameters!', PushTokenClass.api_endpoint, request, g)

        # check for missing parameter in GET request
        builder = EnvironBuilder(method='GET', headers={})

        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01', 'timestamp': '2019-10-05T22:13:23+0100'}
        self.assertRaisesRegex(ParameterError, 'Missing parameter: \'signature\'',
                               PushTokenClass.api_endpoint, request, g)

        # check for invalid timestamp (very old)
        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01',
                            'timestamp': '2019-10-05T22:13:23+0100',
                            'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Timestamp 2019-10-05T22:13:23\+0100 not in valid range.',
                               PushTokenClass.api_endpoint, request, g)

        # check for invalid timestamp (recent but too early)
        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01',
                            'timestamp': (datetime.now(utc) - timedelta(minutes=2)).isoformat(),
                            'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Timestamp .* not in valid range.',
                               PushTokenClass.api_endpoint, request, g)

        # check for invalid timestamp (recent but too late)
        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01',
                            'timestamp': (datetime.now(utc) + timedelta(minutes=2)).isoformat(),
                            'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Timestamp .* not in valid range.',
                               PushTokenClass.api_endpoint, request, g)

        # check for broken timestamp
        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01',
                            'timestamp': '2019-broken-timestamp',
                            'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not parse timestamp .*\. ISO-Format required.',
                               PushTokenClass.api_endpoint, request, g)

        # check for timestamp of wrong type
        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01',
                            'timestamp': datetime.now(timezone.utc),
                            'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not parse timestamp .*\. ISO-Format required.',
                               PushTokenClass.api_endpoint, request, g)

        # check for timezone unaware timestamp (we assume UTC then)
        request = Request(builder.get_environ())
        request.all_data = {'serial': 'SPASS01',
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'signature': 'unknown'}
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not verify signature!',
                               PushTokenClass.api_endpoint, request, g)

        # create a push token
        token_param = {'type': 'push', 'genkey': 1}
        token_param.update(FB_CONFIG_VALS)
        token = init_token(param=token_param)
        serial = token.get_serial()
        # now we need to perform the second rollout step
        builder = EnvironBuilder(method='POST', headers={})
        request = Request(builder.get_environ())
        request.all_data = {"enrollment_credential": token.get_tokeninfo("enrollment_credential"),
                            "serial": serial,
                            "pubkey": self.smartphone_public_key_pem_urlsafe,
                            "fbtoken": "firebaseT"}
        res = PushTokenClass.api_endpoint(request, g)
        self.assertEqual(res[0], 'json', res)
        self.assertTrue(res[1]['result']['value'], res)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['detail']['rollout_state'], 'enrolled', res)

        remove_token(serial)

    def test_11_api_endpoint_update_fbtoken(self):
        g = FakeFlaskG()
        # create a push token
        token_param = {'type': 'push', 'genkey': 1}
        token_param.update(FB_CONFIG_VALS)
        token = init_token(param=token_param)
        serial = token.get_serial()

        # Run enrollment step 2
        token.update({"enrollment_credential": token.get_tokeninfo("enrollment_credential"),
                      "serial": serial,
                      "fbtoken": "firebasetoken1",
                      "pubkey": self.smartphone_public_key_pem_urlsafe})
        self.assertEqual(token.token.get('rollout_state'), 'enrolled', token)
        self.assertEqual(token.get_tokeninfo('firebase_token'), 'firebasetoken1', token)

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
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'), padding.PKCS1v15(), hashes.SHA256())
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

        self.assertEqual(token.token.get('rollout_state'), 'enrolled', token)
        self.assertEqual(token.get_tokeninfo('firebase_token'), req_data['new_fb_token'], token)
        token.delete_token()

    def test_15_poll_endpoint(self):
        g = FakeFlaskG()
        set_policy("push1", scope=SCOPE.ENROLL,
                   action=f"{PUSH_ACTION.FIREBASE_CONFIG}={self.firebase_config_name},"
                          f"{PUSH_ACTION.REGISTRATION_URL}={REGISTRATION_URL},"
                          f"{PUSH_ACTION.TTL}={TTL}")
        g.policy_object = PolicyClass()
        # set up the Firebase Gateway
        r = set_smsgateway(self.firebase_config_name,
                           'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                           "myFB", FB_CONFIG_VALS)
        self.assertGreater(r, 0)

        # create a new push token
        token = self._create_push_token()
        serial = token.get_serial()

        # this is the default timestamp for polling in this test
        timestamp = datetime(2020, 6, 19, 13, 27, tzinfo=utc)

        # create a poll request
        # first create a signature
        timestamp_str = timestamp.isoformat()
        sign_string = f"{serial}|{timestamp_str}"
        signature = self.smartphone_private_key.sign(sign_string.encode('utf8'), padding.PKCS1v15(), hashes.SHA256())

        builder = EnvironBuilder(method='GET', headers={})
        request = Request(builder.get_environ())
        request.all_data = {'serial': serial,
                            'timestamp': timestamp_str,
                            'signature': b32encode(signature)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(request, g)
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
        transaction_id = db_challenge.get_transaction_id()
        self.assertGreater(len(get_challenges(transaction_id=transaction_id)), 0)

        # now check that we receive the challenge when polling
        # since we mock the time we can use the same request data
        with mock.patch('privacyidea.models.datetime') as mock_dt1, \
                mock.patch('privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(request, g)
        self.assertTrue(res[1]['result']['status'], res)
        server_challenge = res[1]['result']['value'][0]
        self.assertEqual(server_challenge['nonce'], challenge, server_challenge)
        self.assertIn('signature', server_challenge, server_challenge)
        # check that the signature matches
        sign_string = "{nonce}|{url}|{serial}|{question}|{title}|{sslverify}".format(**server_challenge)
        parsed_stripped_server_pubkey = serialization.load_pem_public_key(
            to_bytes(self.server_public_key_pem),
            default_backend())
        parsed_stripped_server_pubkey.verify(b32decode(server_challenge['signature']),
                                             sign_string.encode('utf8'),
                                             padding.PKCS1v15(),
                                             hashes.SHA256())
        self.assertFalse(db_challenge.get_otp_status()[1], str(db_challenge))

        # Now mark the challenge as answered so we receive an empty list
        db_challenge.set_otp_status(True)
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(request, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # disallow polling through a policy
        set_policy('push_poll', SCOPE.AUTH, action=f'{PUSH_ACTION.ALLOW_POLLING}={PushAllowPolling.DENY}')
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(PolicyError,
                                   r'Polling not allowed!',
                                   PushTokenClass.api_endpoint, request, g)

        # disallow polling based on a per token configuration
        set_policy('push_poll', SCOPE.AUTH, action=f'{PUSH_ACTION.ALLOW_POLLING}={PushAllowPolling.TOKEN}')
        # If no tokeninfo is set, allow polling
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(request, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # now set the tokeninfo POLLING_ALLOWED to 'False'
        token.add_tokeninfo(POLLING_ALLOWED, 'False')
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(PolicyError, r'Polling not allowed!', PushTokenClass.api_endpoint, request, g)

        # Explicitly allow polling for this token
        token.add_tokeninfo(POLLING_ALLOWED, 'True')
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(request, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # If polling for this token is denied but the overall configuration
        # allows polling, the tokeninfo is ignored
        token.add_tokeninfo(POLLING_ALLOWED, 'False')
        set_policy('push_poll', SCOPE.AUTH,
                   action=f'{PUSH_ACTION.ALLOW_POLLING}={PushAllowPolling.ALLOW}')
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(request, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # this should also work if there is no ALLOW_POLLING policy
        delete_policy('push_poll')
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            res = PushTokenClass.api_endpoint(request, g)
        self.assertTrue(res[1]['result']['status'], res)
        self.assertEqual(res[1]['result']['value'], [], res[1]['result']['value'])

        # check for a non-existing serial
        unknown_serial = 'unknown_serial_01'
        # we shouldn't run into a signature check so we don't create one
        request.all_data = {'serial': unknown_serial,
                            'timestamp': timestamp_str,
                            'signature': b32encode(b'no signature check')}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, request, g)

        # serial exists but signature is wrong
        wrong_signature = bytearray(signature)
        wrong_signature[0] += 1
        request.all_data = {'serial': serial,
                            'timestamp': timestamp_str,
                            'signature': b32encode(wrong_signature)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, request, g)

        # check for a wrongly created signature (inverted timestamp, serial)
        sign_string2 = f"{timestamp_str}|{serial}"
        wrong_signature2 = self.smartphone_private_key.sign(sign_string2.encode('utf8'), padding.PKCS1v15(),
                                                            hashes.SHA256())
        request.all_data = {'serial': serial,
                            'timestamp': timestamp_str,
                            'signature': b32encode(wrong_signature2)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, request, g)

        # the serial exists but does not belong to a push token
        token2 = init_token(param={'type': 'hotp', 'genkey': 1})
        serial2 = token2.get_serial()
        # we shouldn't run into the signature check here
        request.all_data = {'serial': serial2,
                            'timestamp': datetime.now(tz=utc).isoformat(),
                            'signature': b32encode(b"signature not needed")}
        # poll for challenges
        self.assertRaisesRegex(privacyIDEAError,
                               r'Could not verify signature!',
                               PushTokenClass.api_endpoint, request, g)

        # wrongly configured push token (no firebase config)
        token.del_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG)
        # We are missing a registration URL, thus polling of challenges fails
        delete_policy("push1")
        request.all_data = {'serial': serial,
                            'timestamp': timestamp_str,
                            'signature': b32encode(signature)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, request, g)

        # unknown firebase configuration
        token.add_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG, 'my unknown firebase config')
        request.all_data = {'serial': serial,
                            'timestamp': timestamp_str,
                            'signature': b32encode(signature)}
        # poll for challenges
        with mock.patch('privacyidea.models.datetime') as mock_dt1, mock.patch(
                'privacyidea.lib.tokens.pushtoken.datetime') as mock_dt2:
            mock_dt1.utcnow.return_value = timestamp.replace(tzinfo=None) + timedelta(seconds=15)
            mock_dt2.now.return_value = timestamp + timedelta(seconds=15)
            self.assertRaisesRegex(privacyIDEAError,
                                   r'Could not verify signature!',
                                   PushTokenClass.api_endpoint, request, g)

        # cleanup
        token.delete_token()
        token2.delete_token()
        delete_smsgateway(self.firebase_config_name)

    @responses.activate
    def test_20_api_authenticate_two_tokens(self):
        # Test the /validate/check endpoints, user has two push tokens, require presence
        self.setUp_user_realms()
        # create FireBase Service and policies
        set_smsgateway(self.firebase_config_name,
                       'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                       "myFB", FB_CONFIG_VALS)
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PUSH_ACTION.FIREBASE_CONFIG}={self.firebase_config_name}")
        # create push token
        token1 = self._create_push_token()
        serial1 = token1.get_serial()
        # create 2nd push token
        token2 = self._create_push_token()
        serial2 = token2.get_serial()
        self.assertNotEqual(serial1, serial2)
        # set PIN
        token1.set_pin("pushpin")
        token1.add_user(User("cornelius", self.realm1))
        token2.set_pin("pushpin")
        token2.add_user(User("cornelius", self.realm1))

        # set the policy for require presence
        set_policy('push_presence', SCOPE.AUTH, action=f'{PUSH_ACTION.REQUIRE_PRESENCE}=1')

        cached_fbtoken = {
            'firebase_token': {
                FB_CONFIG_VALS[FIREBASE_CONFIG.JSON_CONFIG]: _create_credential_mock()}}
        self.app.config.setdefault('_app_local_store', {}).update(cached_fbtoken)
        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.service_account'
                        '.Credentials.from_service_account_file') as mock_service_account:
            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects'
                                          '/test-123456/messages:send',
                          body="""{}""",
                          content_type="application/json")

            # Send the first authentication request to trigger the challenge. For two tokens
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                json_response = res.json
                self.assertFalse(json_response.get("result").get("value"))
                self.assertTrue(json_response.get("result").get("status"))
                multi_challenge = json_response.get("detail").get("multi_challenge")
                # Ensure, that both messages are the same, i.e. the user is requested to press the same button
                self.assertEqual(multi_challenge[0].get("message"), multi_challenge[1].get("message"),
                                 multi_challenge)
                self.assertIn("Please press:", multi_challenge[0].get("message"))
                transaction_id = json_response.get("detail").get("transaction_id")

            # Our ServiceAccountCredentials mock has not been called because we use a cached token
            mock_service_account.assert_not_called()
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
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            # Result-Value is false, the user has not answered the challenge, yet
            self.assertFalse(json_response.get("result").get("value"))

        # As the challenge has not been answered yet, the /validate/polltransaction endpoint returns false
        with self.app.test_request_context('/validate/polltransaction', method='GET',
                                           query_string={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # Now the smartphone communicates with the backend and the challenge in the database table
        # is marked as answered successfully.
        challenges = get_challenges(serial=token1.token.serial, transaction_id=transaction_id)
        challenges[0].set_otp_status(True)

        # As the challenge has been answered, the /validate/polltransaction endpoint returns true
        with self.app.test_request_context('/validate/polltransaction', method='GET',
                                           query_string={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertTrue(res.json["result"]["value"])

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "state": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            json_response = res.json
            # Result-Value is True, since the challenge is marked resolved in the DB
        self.assertTrue(json_response.get("result").get("value"))

        # As the challenge does not exist anymore, the /validate/polltransaction endpoint returns false
        with self.app.test_request_context('/validate/polltransaction', method='GET',
                                           query_string={'transaction_id': transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])
        self.assertEqual(get_challenges(serial=token1.token.serial), [])

        delete_policy("push_config")
        delete_policy("push_presence")
        remove_token(serial1)
        remove_token(serial2)
