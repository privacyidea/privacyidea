# -*- coding: utf-8 -*-
PWFILE = "tests/testdata/passwords"
FIREBASE_FILE = "tests/testdata/firebase-test.json"
CLIENT_FILE = "tests/testdata/google-services.json"

from .base import MyTestCase
from privacyidea.lib.error import ParameterError
from privacyidea.lib.user import (User)
from privacyidea.lib.tokens.pushtoken import PushTokenClass, PUSH_ACTION, DEFAULT_CHALLENGE_TEXT, strip_key
from privacyidea.lib.smsprovider.FirebaseProvider import FIREBASE_CONFIG
from privacyidea.lib.token import get_tokens, remove_token
from privacyidea.lib.tokens.pushtoken import PUBLIC_KEY_SERVER
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.crypto import geturandom
from privacyidea.models import Token
from privacyidea.lib.policy import (SCOPE, set_policy)
from privacyidea.lib.utils import to_bytes, b32encode_and_unicode, to_unicode
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway, SMSError
from privacyidea.lib.error import ConfigAdminError
from base64 import b32decode
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


class myAccessTokenInfo(object):
    def __init__(self, access_token):
        self.access_token = access_token
        self.expires_in = 3600


class myCredentials(object):
    def __init__(self, access_token_info):
        self.access_token_info = access_token_info

    def get_access_token(self):
        return self.access_token_info


class PushTokenTestCase(MyTestCase):

    serial1 = "PUSH00001"

    # We now allow white spaces in the firebase config name
    firebase_config_name = "my firebase config"

    smartphone_private_key = rsa.generate_private_key(public_exponent=65537,
                                                      key_size=4096,
                                                      backend=default_backend())
    smartphone_public_key = smartphone_private_key.public_key()
    smartphone_public_key_pem = to_unicode(
            smartphone_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo))
    # The smartphone sends the public key in URLsafe and without the ----BEGIN header
    smartphone_public_key_pem_urlsafe = strip_key(smartphone_public_key_pem).replace("+", "-").replace("/", "_")

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
                     FIREBASE_CONFIG.TTL: 10,
                     FIREBASE_CONFIG.API_KEY: "1",
                     FIREBASE_CONFIG.APP_ID: "2",
                     FIREBASE_CONFIG.PROJECT_NUMBER: "3",
                     FIREBASE_CONFIG.PROJECT_ID: "4"}

        # Wrong JSON file
        self.assertRaises(ConfigAdminError, set_smsgateway,
                          "fb1", u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                          fb_config)

        # Wrong Project number
        fb_config[FIREBASE_CONFIG.JSON_CONFIG] = FIREBASE_FILE
        self.assertRaises(ConfigAdminError, set_smsgateway,
                          "fb1", u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                          fb_config)

        # Missing APP_ID
        self.assertRaises(ConfigAdminError, set_smsgateway,
                          "fb1", u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                          {FIREBASE_CONFIG.REGISTRATION_URL: "http://test/ttype/push",
                           FIREBASE_CONFIG.JSON_CONFIG: CLIENT_FILE,
                           FIREBASE_CONFIG.TTL: 10,
                           FIREBASE_CONFIG.API_KEY: "1",
                           FIREBASE_CONFIG.PROJECT_NUMBER: "3",
                           FIREBASE_CONFIG.PROJECT_ID: "4"})

        # Missing API_KEY_IOS
        self.assertRaises(ConfigAdminError, set_smsgateway,
                          "fb1", u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                          {FIREBASE_CONFIG.REGISTRATION_URL: "http://test/ttype/push",
                           FIREBASE_CONFIG.JSON_CONFIG: CLIENT_FILE,
                           FIREBASE_CONFIG.TTL: 10,
                           FIREBASE_CONFIG.APP_ID_IOS: "1",
                           FIREBASE_CONFIG.PROJECT_NUMBER: "3",
                           FIREBASE_CONFIG.PROJECT_ID: "4"})

        # Everything is fine
        fb_config[FIREBASE_CONFIG.PROJECT_ID] = "test-123456"
        r = set_smsgateway("fb1", u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                           fb_config)
        self.assertTrue(r > 0)

        detail = token.get_init_detail(params={"firebase_config": self.firebase_config_name})
        self.assertEqual(detail.get("serial"), self.serial1)
        self.assertEqual(detail.get("rollout_state"), "clientwait")
        enrollment_credential = detail.get("enrollment_credential")
        self.assertTrue("pushurl" in detail)
        self.assertFalse("otpkey" in detail)

        # Run enrollment step 2
        token.update({"enrollment_credential": enrollment_credential,
                      "serial": self.serial1,
                      "fbtoken": "firebasetoken",
                      "pubkey": self.smartphone_public_key_pem_urlsafe})
        self.assertEqual(token.get_tokeninfo("firebase_token"), "firebasetoken")
        self.assertEqual(token.get_tokeninfo("public_key_smartphone"), self.smartphone_public_key_pem_urlsafe)
        self.assertTrue(token.get_tokeninfo("public_key_server").startswith(u"-----BEGIN RSA PUBLIC KEY-----\n"),
                        token.get_tokeninfo("public_key_server"))
        parsed_server_pubkey = serialization.load_pem_public_key(
            to_bytes(token.get_tokeninfo("public_key_server")),
            default_backend())
        self.assertIsInstance(parsed_server_pubkey, RSAPublicKey)
        self.assertTrue(token.get_tokeninfo("private_key_server").startswith(u"-----BEGIN RSA PRIVATE KEY-----\n"),
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

    def test_02_api_enroll(self):
        self.authenticate()

        # Failed enrollment due to missing policy
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertNotEqual(res.status_code,  200)
            error = json.loads(res.data.decode("utf8")).get("result").get("error")
            self.assertEqual(error.get("message"), "Missing enrollment policy for push token: push_firebase_configuration")
            self.assertEqual(error.get("code"), 303)

        r = set_smsgateway(self.firebase_config_name, u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                           {FIREBASE_CONFIG.REGISTRATION_URL: "http://test/ttype/push",
                            FIREBASE_CONFIG.TTL: 10,
                            FIREBASE_CONFIG.API_KEY: "1",
                            FIREBASE_CONFIG.APP_ID: "2",
                            FIREBASE_CONFIG.PROJECT_NUMBER: "3",
                            FIREBASE_CONFIG.PROJECT_ID: "test-123456",
                            FIREBASE_CONFIG.JSON_CONFIG: FIREBASE_FILE})
        self.assertTrue(r > 0)
        set_policy("push1", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PUSH_ACTION.FIREBASE_CONFIG,
                                               self.firebase_config_name))

        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,  200)
            detail = json.loads(res.data.decode('utf8')).get("detail")
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

        # 2nd step. Failing with wrong serial number
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"serial": "wrongserial",
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 404, res)
            status = json.loads(res.data.decode('utf8')).get("result").get("status")
            self.assertFalse(status)
            error = json.loads(res.data.decode('utf8')).get("result").get("error")
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
            status = json.loads(res.data.decode('utf8')).get("result").get("status")
            self.assertFalse(status)
            error = json.loads(res.data.decode('utf8')).get("result").get("error")
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
            detail = json.loads(res.data.decode('utf8')).get("detail")
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
            self.assertEqual(tokeninfo.get("public_key_server").strip().strip("-BEGIN END RSA PUBLIC KEY-").strip(), pubkey)
            # The token should also contain the firebase config
            self.assertEqual(tokeninfo.get(PUSH_ACTION.FIREBASE_CONFIG), self.firebase_config_name)

    @responses.activate
    def test_03_api_authenticate_fail(self):
        # This tests the failed to communicate to the firebase service
        self.setUp_user_realms()

        # get enrolled push token
        toks = get_tokens(tokentype="push")
        self.assertEqual(len(toks), 1)
        tokenobj = toks[0]

        # set PIN
        tokenobj.set_pin("pushpin")
        tokenobj.add_user(User("cornelius", self.realm1))

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.ServiceAccountCredentials') as mySA:
            # alternative: side_effect instead of return_value
            mySA.from_json_keyfile_name.return_value = myCredentials(myAccessTokenInfo("my_bearer_token"))

            # add responses, to simulate the failing communication (status 500)
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          body="""{}""",
                          status=500,
                          content_type="application/json")

            # Send the first authentication request to trigger the challenge
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 400, res)
                jsonresp = json.loads(res.data.decode('utf8'))
                self.assertFalse(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp.get("result").get("error").get("code"), 401)
                self.assertEqual(jsonresp.get("result").get("error").get("message"), "ERR401: Failed to submit "
                                                                                     "message to firebase service.")               

    @responses.activate
    def test_03_api_authenticate_client(self):
        # Test the /validate/check endpoints without the smartphone endpoint /ttype/push
        self.setUp_user_realms()

        # get enrolled push token
        toks = get_tokens(tokentype="push")
        self.assertEqual(len(toks), 1)
        tokenobj = toks[0]

        # set PIN
        tokenobj.set_pin("pushpin")
        tokenobj.add_user(User("cornelius", self.realm1))

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.ServiceAccountCredentials') as mySA:
            # alternative: side_effect instead of return_value
            mySA.from_json_keyfile_name.return_value = myCredentials(myAccessTokenInfo("my_bearer_token"))

            # add responses, to simulate the communication to firebase
            responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
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
                jsonresp = json.loads(res.data.decode('utf8'))
                self.assertFalse(jsonresp.get("result").get("value"))
                self.assertTrue(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp.get("detail").get("serial"), tokenobj.token.serial)
                self.assertTrue("transaction_id" in jsonresp.get("detail"))
                transaction_id = jsonresp.get("detail").get("transaction_id")
                self.assertEqual(jsonresp.get("detail").get("message"), DEFAULT_CHALLENGE_TEXT)

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
            jsonresp = json.loads(res.data.decode('utf8'))
            # Result-Value is false, the user has not answered the challenge, yet
            self.assertFalse(jsonresp.get("result").get("value"))

        # Now the smartphone communicates with the backend and the challenge in the database table
        # is marked as answered successfully.
        challengeobject_list = get_challenges(serial=tokenobj.token.serial,
                                              transaction_id=transaction_id)
        challengeobject_list[0].set_otp_status(True)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "state": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            jsonresp = json.loads(res.data.decode('utf8'))
            # Result-Value is True, since the challenge is marked resolved in the DB
        self.assertTrue(jsonresp.get("result").get("value"))

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

        def check_firebase_params(request):
            payload = json.loads(request.body)
            # check the signature in the payload!
            data = payload.get("message").get("data")

            sign_string = u"{nonce}|{url}|{serial}|{question}|{title}|{sslverify}".format(**data)
            token_obj = get_tokens(serial=data.get("serial"))[0]
            pem_pubkey = token_obj.get_tokeninfo(PUBLIC_KEY_SERVER)
            pubkey_obj = load_pem_public_key(to_bytes(pem_pubkey), backend=default_backend())
            signature = b32decode(data.get("signature"))
            # If signature does not match it will raise InvalidSignature exception
            pubkey_obj.verify(signature, sign_string.encode("utf8"),
                              padding.PKCS1v15(),
                              hashes.SHA256())
            headers = {'request-id': '728d329e-0e86-11e4-a748-0c84dc037c13'}
            return (200, headers, json.dumps({}))

        # We mock the ServiceAccountCredentials, since we can not directly contact the Google API
        with mock.patch('privacyidea.lib.smsprovider.FirebaseProvider.ServiceAccountCredentials') as mySA:
            # alternative: side_effect instead of return_value
            mySA.from_json_keyfile_name.return_value = myCredentials(myAccessTokenInfo("my_bearer_token"))

            # add responses, to simulate the communication to firebase
            responses.add_callback(responses.POST, 'https://fcm.googleapis.com/v1/projects/test-123456/messages:send',
                          callback=check_firebase_params,
                          content_type="application/json")

            # Send the first authentication request to trigger the challenge
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "pass": "pushpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                jsonresp = json.loads(res.data.decode('utf8'))
                self.assertFalse(jsonresp.get("result").get("value"))
                self.assertTrue(jsonresp.get("result").get("status"))
                self.assertEqual(jsonresp.get("detail").get("serial"), tokenobj.token.serial)
                self.assertTrue("transaction_id" in jsonresp.get("detail"))
                transaction_id = jsonresp.get("detail").get("transaction_id")
                self.assertEqual(jsonresp.get("detail").get("message"), DEFAULT_CHALLENGE_TEXT)

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
            self.assertEquals(res.status_code, 400)

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
            jsonresp = json.loads(res.data.decode('utf8'))
            # Result-Value is True
            self.assertTrue(jsonresp.get("result").get("value"))

    def test_05_strip_key(self):
        stripped_pubkey = strip_key(self.smartphone_public_key_pem)
        self.assertIn("-BEGIN PUBLIC KEY-", self.smartphone_public_key_pem)
        self.assertNotIn("-BEGIN PUBLIC KEY_", stripped_pubkey)
        self.assertNotIn("-", stripped_pubkey)
        self.assertEqual(strip_key(stripped_pubkey), stripped_pubkey)
        self.assertEqual(strip_key("\n\n" + stripped_pubkey + "\n\n"), stripped_pubkey)
