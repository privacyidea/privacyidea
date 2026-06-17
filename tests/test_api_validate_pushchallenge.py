# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import datetime
from base64 import b32encode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from passlib.hash import argon2

from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.token import (remove_token)
from privacyidea.lib.tokens.pushtoken import PushAction, strip_pem_headers
from privacyidea.lib.user import (User)
from privacyidea.lib.utils import to_unicode
from .authlog_utils import assert_authentication_log, assert_authentication_log_entry
from .base import MyApiTestCase


class PushChallengeTags(MyApiTestCase):
    serial = "hotp1"

    """
    for test 3
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
    user = "selfservice"

    def setUp(self):
        self.setUp_user_realms()

    def test_01_push_challenge_tags(self):
        # Test the challenge tags of a push token
        pin = "otppin"
        REGISTRATION_URL = "http://test/ttype/push"
        TTL = "10"

        # set policy
        from privacyidea.lib.tokens.pushtoken import POLL_ONLY
        set_policy("push2", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       PushAction.FIREBASE_CONFIG, POLL_ONLY,
                       PushAction.REGISTRATION_URL, REGISTRATION_URL,
                       PushAction.TTL, TTL))

        set_policy("push1", scope=SCOPE.AUTH,
                   action=PushAction.MOBILE_TEXT + "=Login von UserAgent: {ua_string} via {client_ip}/{tokentype}.")

        # create push token for user with PIN
        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": pin,
                                                 "user": self.user,
                                                 "realm": self.realm1,
                                                 "serial": self.serial_push,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            serial = detail.get("serial")
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
            serial = detail.get("serial")
            enrollment_credential = detail.get("enrollment_credential")

        # Run authentication with push token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.user,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertEqual("Please confirm the authentication on your mobile device!", detail.get("message"))

        # The PIN step created the push challenge -> CHALLENGE_TRIGGERED for the user and token
        auth_log_entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED], transaction_id=transaction_id)
        assert_authentication_log_entry(auth_log_entries[AuthEventType.CHALLENGE_TRIGGERED],
                                        user=User(self.user, self.realm1), serials={serial},
                                        transaction_id=transaction_id)

        # We do poll only, so we need to poll
        ts = datetime.datetime.utcnow().isoformat()
        sign_string = "{serial}|{timestamp}".format(serial=serial, timestamp=ts)
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                               padding.PKCS1v15(),
                                               hashes.SHA256())
        # now check that we receive the challenge when polling
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           query_string={"serial": serial,
                                                         "timestamp": ts,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual("Login von UserAgent:  via None/push.", value[0].get("question"))

        remove_token(self.serial_push)
        delete_policy("push2")
        delete_policy("push1")
