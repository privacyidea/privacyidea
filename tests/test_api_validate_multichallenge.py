# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import datetime
import json
import logging
import re
import time
from base64 import b32encode
from datetime import timezone
from urllib.parse import quote

import mock
import responses
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from dateutil.tz import tzlocal
from passlib.hash import argon2
from testfixtures import Replace, test_datetime
from testfixtures import log_capture

from privacyidea.lib import _
from privacyidea.lib.applications.offline import REFILLTOKEN_LENGTH
from privacyidea.lib.authcache import _hash_password
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import (set_privacyidea_config,
                                    get_inc_fail_count_on_false_pin,
                                    delete_privacyidea_config, SYSCONF)
from privacyidea.lib.container import init_container, find_container_by_serial, create_container_template
from privacyidea.lib.error import Error
from privacyidea.lib.event import delete_event
from privacyidea.lib.event import set_event
from privacyidea.lib.machine import attach_token, detach_token
from privacyidea.lib.machineresolver import save_resolver as save_machine_resolver
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy, AUTHORIZED
from privacyidea.lib.radiusserver import add_radius
from privacyidea.lib.realm import set_realm, set_default_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, get_resolver_list, delete_resolver
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   reset_token, enable_token, revoke_token,
                                   set_pin, get_one_token, unassign_token)
from privacyidea.lib.tokenclass import (ClientMode, FAILCOUNTER_EXCEEDED,
                                        FAILCOUNTER_CLEAR_TIMEOUT, DATE_FORMAT,
                                        AUTH_DATE_FORMAT)
from privacyidea.lib.tokens.passwordtoken import DEFAULT_LENGTH as DEFAULT_LENGTH_PW
from privacyidea.lib.tokens.pushtoken import PushAction, POLL_ONLY, strip_pem_headers
from privacyidea.lib.tokens.registrationtoken import DEFAULT_LENGTH as DEFAULT_LENGTH_REG
from privacyidea.lib.tokens.registrationtoken import RegistrationTokenClass
from privacyidea.lib.tokens.smstoken import SmsTokenClass
from privacyidea.lib.tokens.totptoken import HotpTokenClass
from privacyidea.lib.tokens.yubikeytoken import YubikeyTokenClass
from privacyidea.lib.user import (User)
from privacyidea.lib.users.custom_user_attributes import InternalCustomUserAttributes
from privacyidea.lib.utils import AUTH_RESPONSE
from privacyidea.lib.utils import to_unicode
from privacyidea.models import (Token, Policy, Challenge, AuthCache, db, TokenOwner, Realm, CustomUserAttribute,
                                NodeName)
from . import smtpmock, ldap3mock, radiusmock
from .base import MyApiTestCase
from .test_lib_tokencontainer import MockSmartphone

from .api_validate_common import LDAPDirectory, OTPs, HOSTSFILE, DICT_FILE, setup_sms_gateway


class MultiChallenge(MyApiTestCase):
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

    def setUp(self):
        self.setUp_user_realms()

    def test_00_pin_change_via_validate_chalresp(self):
        # Test PIN change after challenge response authentication
        # Create policy change pin on first use
        set_policy("first_use", scope=SCOPE.ENROLL, action=PolicyAction.CHANGE_PIN_FIRST_USE)
        set_policy("via_validate", scope=SCOPE.AUTH, action=PolicyAction.CHANGE_PIN_VIA_VALIDATE)
        set_policy("hotp_chalresp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(PolicyAction.CHALLENGERESPONSE))
        set_policy("enroll", scope=SCOPE.ADMIN, action=["enrollHOTP", PolicyAction.ENROLLPIN])

        with self.app.test_request_context('/token/init', method='POST',
                                           data={"user": "cornelius", "pin": "test",
                                                 "serial": self.serial, "otpkey": self.otpkey},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))

        # 1st authentication creates a PIN change challenge via challenge response
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            details = res.json['detail']
            transaction_id = details.get("transaction_id")

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            details = res.json['detail']
            self.assertFalse(result.get("value"))
            transaction_id = details.get("transaction_id")
            self.assertEqual("Please enter a new PIN", details.get("message"))

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "newpin",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            details = res.json['detail']
            transaction_id = details.get("transaction_id")
            self.assertEqual("Please enter the new PIN again", details.get("message"))

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "newpin",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))
            details = res.json['detail']
            self.assertEqual("PIN successfully set.", details.get("message"))
            self.assertTrue(result.get("value"))

        # Now try to authenticate with the "newpin"
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "newpin{0!s}".format(self.valid_otp_values[2])}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))

        remove_token(self.serial)
        delete_policy("first_use")
        delete_policy("via_validate")
        delete_policy("hotp_chalresp")
        delete_policy("enroll")

    def test_01_pin_change_via_validate_single_shot(self):
        # Test PIN change after authentication with a single shot authentication
        # Create policy change pin on first use
        set_policy("first_use", scope=SCOPE.ENROLL, action=PolicyAction.CHANGE_PIN_FIRST_USE)
        set_policy("via_validate", scope=SCOPE.AUTH, action=PolicyAction.CHANGE_PIN_VIA_VALIDATE)
        set_policy("hotp_chalresp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(PolicyAction.CHALLENGERESPONSE))
        set_policy("enroll", scope=SCOPE.ADMIN, action=["enrollHOTP", PolicyAction.ENROLLPIN])

        with self.app.test_request_context('/token/init', method='POST',
                                           data={"user": "cornelius", "pin": "test",
                                                 "serial": self.serial, "otpkey": self.otpkey},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))

        # 1st authentication creates a PIN change challenge via challenge response
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "test{0!s}".format(self.valid_otp_values[1])}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            details = res.json['detail']
            transaction_id = details.get("transaction_id")
            self.assertEqual("Please enter a new PIN", details.get("message"))

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "newpin",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            details = res.json['detail']
            transaction_id = details.get("transaction_id")
            self.assertEqual("Please enter the new PIN again", details.get("message"))

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "newpin",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))
            details = res.json['detail']
            self.assertEqual("PIN successfully set.", details.get("message"))
            self.assertTrue(result.get("value"))

        # Now try to authenticate with the "newpin"
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "newpin{0!s}".format(self.valid_otp_values[2])}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))

        remove_token(self.serial)
        delete_policy("first_use")
        delete_policy("via_validate")
        delete_policy("hotp_chalresp")
        delete_policy("enroll")

    def test_02_challenge_text_header(self):
        # Test PIN change after authentication with a single shot authentication
        # Create policy change pin on first use
        set_policy("first_use", scope=SCOPE.ENROLL, action=PolicyAction.CHANGE_PIN_FIRST_USE)
        set_policy("via_validate", scope=SCOPE.AUTH, action=PolicyAction.CHANGE_PIN_VIA_VALIDATE)
        set_policy("hotp_chalresp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(PolicyAction.CHALLENGERESPONSE))
        challenge_header = "Choose one: <ul>"
        set_policy("challenge_header", scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(PolicyAction.CHALLENGETEXT_HEADER, challenge_header))
        set_policy("enroll", scope=SCOPE.ADMIN, action=["enrollHOTP", PolicyAction.ENROLLPIN])

        with self.app.test_request_context('/token/init', method='POST',
                                           data={"user": "cornelius", "pin": "test",
                                                 "serial": self.serial, "otpkey": self.otpkey},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))

        # 1st authentication creates a PIN change challenge via challenge response
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "test{0!s}".format(self.valid_otp_values[1])}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            details = res.json['detail']
            # check that the challenge header is contained in the message
            self.assertEqual("{0!s}<li>Please enter a new PIN</li>\n".format(challenge_header),
                             details.get("message"))

        remove_token(self.serial)
        delete_policy("first_use")
        delete_policy("via_validate")
        delete_policy("hotp_chalresp")
        delete_policy("challenge_header")
        delete_policy("enroll")

    def test_03_preferred_client_mode(self):
        REGISTRATION_URL = "http://test/ttype/push"
        TTL = "10"

        # set policy
        from privacyidea.lib.tokens.pushtoken import POLL_ONLY
        set_policy("push2", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       PushAction.FIREBASE_CONFIG, POLL_ONLY,
                       PushAction.REGISTRATION_URL, REGISTRATION_URL,
                       PushAction.TTL, TTL))

        pin = "otppin"
        # create push token for user with PIN
        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push",
                                                 "pin": pin,
                                                 "user": "selfservice",
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

        # create hotp token for the user with same PIN
        init_token({"serial": "CR2A",
                    "type": "hotp",
                    "otpkey": "31323334353637383930313233343536373839AA",
                    "pin": pin}, user=User("selfservice", self.realm1))
        set_policy("test49", scope=SCOPE.AUTH,
                   action="{0!s}=hotp totp, {1!s}=  poll   webauthn ".format(
                       PolicyAction.CHALLENGERESPONSE, PolicyAction.PREFERREDCLIENTMODE))

        # authenticate with PIN to trigger challenge-response
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "realm": self.realm1,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("preferred_client_mode"), 'poll', detail)

        delete_policy("test49")
        delete_policy("push2")
        remove_token(serial)
        remove_token("CR2A")

    def test_04_preferred_client_mode_default(self):
        OTPKEY2 = "31323334353637383930313233343536373839"
        user = User("multichal", self.realm1)
        pin = "test49"
        init_token({"serial": "CR2AAA",
                    "type": "hotp",
                    "otpkey": OTPKEY2,
                    "pin": pin}, user)
        init_token({"serial": "CR2B",
                    "type": "hotp",
                    "otpkey": self.otpkey,
                    "pin": pin}, user)
        set_policy("test49", scope=SCOPE.AUTH, action="{0!s}=hotp".format(
            PolicyAction.CHALLENGERESPONSE))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "realm": self.realm1,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("preferred_client_mode"), 'interactive')

        delete_policy("test49")
        remove_token("CR2AAA")
        remove_token("CR2B")

    def test_05_preferred_client_mode_no_accepted_values(self):
        self.setUp_user_realms()
        OTPKEY2 = "31323334353637383930313233343536373839"
        user = User("multichal", self.realm1)
        pin = "test49"
        init_token({"serial": "CR2AAA",
                    "type": "hotp",
                    "otpkey": OTPKEY2,
                    "pin": pin}, user)
        init_token({"serial": "CR2B",
                    "type": "hotp",
                    "otpkey": self.otpkey,
                    "pin": pin}, user)
        set_policy("test49", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        # both tokens will be a valid challenge response token!
        set_policy("test", scope=SCOPE.AUTH, action=f"{PolicyAction.PREFERREDCLIENTMODE}=wrong falsch Chigau sbagliato")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "realm": self.realm1,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("preferred_client_mode"), 'interactive')

        delete_policy("test49")
        delete_policy("test")
        remove_token("CR2AAA")
        remove_token("CR2B")

    def test_06_preferred_client_mode_for_user(self):
        """
        Test that the preferred token type is set for the user in validate check after a successful authentication.
        In second authentication the preferred token type is used to set the preferred client mode.
        """
        REGISTRATION_URL = "http://test/ttype/push"
        TTL = "10"
        user = User("selfservice", self.realm1)

        # set policy
        set_policy("push", scope=SCOPE.ENROLL, action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                                                      f"{PushAction.REGISTRATION_URL}={REGISTRATION_URL},"
                                                      f"{PushAction.TTL}={TTL}")

        pin = "otppin"
        # create push token for user with PIN
        # 1st step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "push", "pin": pin, "user": "selfservice",
                                                 "realm": self.realm1, "serial": self.serial_push, "genkey": True},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            enrollment_credential = detail.get("enrollment_credential")
        # 2nd step: as performed by the smartphone
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           data={"enrollment_credential": enrollment_credential, "serial": serial,
                                                 "pubkey": self.smartphone_public_key_pem_urlsafe,
                                                 "fbtoken": "firebaseT"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # create hotp token for the user with same PIN
        hotp = init_token({"type": "hotp", "genkey": True, "pin": pin}, user=user)

        # set policy for challenge response and client mode per user
        set_policy("auth", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGERESPONSE}=hotp totp, {PolicyAction.CLIENT_MODE_PER_USER}")

        # ---- auth with PUSH ----
        # authenticate with PIN to trigger challenge-response: first auth, custom user attribute not set
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "realm": self.realm1, "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            # custom user attribute not set yet: use default
            self.assertEqual("interactive", detail.get("preferred_client_mode"))
            self.assertIsNone(user.attributes.get(InternalCustomUserAttributes.LAST_USED_TOKEN))

        # answer challenge: custom user attribute shall be set
        # We do poll only, so we need to poll
        timestamp = datetime.datetime.now(timezone.utc).isoformat()
        sign_string = f"{serial}|{timestamp}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'), padding.PKCS1v15(), hashes.SHA256())
        # now check that we receive the challenge when polling
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           query_string={"serial": serial,
                                                         "timestamp": timestamp,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            nonce = result.get("value")[0].get("nonce")
        # Answer challenge
        sign_string = f"{nonce}|{serial}"
        sig = self.smartphone_private_key.sign(sign_string.encode('utf8'), padding.PKCS1v15(), hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='POST',
                                           query_string={"serial": serial,
                                                         "timestamp": timestamp,
                                                         "signature": b32encode(sig)}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
        # finalize authentication: custom user attribute shall be set here for the next authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "realm": self.realm1,
                                                 "pass": "", "transaction_id": transaction_id},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            preferred_token_types = user.attributes.get(
                f"{InternalCustomUserAttributes.LAST_USED_TOKEN}_privacyidea-cp")
            self.assertEqual("push", preferred_token_types)

        # authenticate with PIN to trigger challenge-response: second auth, custom user attribute set
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "realm": self.realm1, "pass": pin},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            # custom user attribute set from last auth to poll
            self.assertEqual("poll", detail.get("preferred_client_mode"))

        # ---- Auth from another application ----
        # authenticate from another application: custom user attribute not set, use default
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "realm": self.realm1, "pass": pin},
                                           headers={"user_agent": "privacyIDEA-Keycloak"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            # custom user attribute not set for this application: use default
            self.assertEqual("interactive", detail.get("preferred_client_mode"))

        # ---- Auth with HOTP ----
        # authenticate with another token (hotp): trigger challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "realm": self.realm1, "pass": pin},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            # custom user attribute set from last auth to poll
            self.assertEqual("poll", detail.get("preferred_client_mode"))
        # finish authentication with hotp token
        _, _, otp, _ = hotp.get_otp()
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "realm": self.realm1, "pass": otp,
                                                 "transaction_id": transaction_id},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            # custom user attribute changed to interactive
            preferred_token_types = user.attributes.get(
                f"{InternalCustomUserAttributes.LAST_USED_TOKEN}_privacyidea-cp")
            self.assertEqual("hotp", preferred_token_types)
        # authenticate with PIN to trigger challenge-response: second auth, custom user attribute set
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice", "realm": self.realm1, "pass": pin},
                                           headers={"user_agent": "privacyidea-cp/2.0"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            detail = res.json.get("detail")
            # custom user attribute set from last auth to poll
            self.assertEqual("interactive", detail.get("preferred_client_mode"))

        delete_policy("auth")
        delete_policy("push")
        remove_token(serial)
        hotp.delete_token()

    def test_07_preferred_client_mode_for_user_sms(self):
        """
        Test that the preferred token type is set for the user in validate check after a successful authentication with
        sms token.
        """
        user = User("selfservice", self.realm1)
        pin = "1234"

        # create sms and totp token for the user with same PIN
        sms = init_token({"type": "sms", "genkey": True, "phone": "123456", "pin": pin}, user=user)
        totp = init_token({"type": "totp", "genkey": True, "pin": pin}, user=user)

        # set policy for challenge response and client mode per user
        set_policy("auth", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGERESPONSE}=hotp totp sms, {PolicyAction.CLIENT_MODE_PER_USER}")

        # authenticate with PIN to trigger challenge-response: first auth, custom user attribute not set
        with mock.patch.object(SmsTokenClass, '_send_sms', return_value=(True, "SMS sent successfully")):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "selfservice", "realm": self.realm1, "pass": pin}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                detail = res.json.get("detail")
                transaction_id = detail.get("transaction_id")
                # custom user attribute not set yet: use default
                self.assertEqual("interactive", detail.get("preferred_client_mode"))
                self.assertIsNone(user.attributes.get(InternalCustomUserAttributes.LAST_USED_TOKEN))

            # answer challenge with sms otp: custom user attribute shall be set
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "selfservice", "realm": self.realm1,
                                                     "pass": sms.get_otp()[2], "transaction_id": transaction_id},
                                               headers={"user_agent": "privacyidea-cp/2.0"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                preferred_token_types = user.attributes.get(
                    f"{InternalCustomUserAttributes.LAST_USED_TOKEN}_privacyidea-cp")
                self.assertEqual("sms", preferred_token_types)

            # authenticate with PIN to trigger challenge-response: second auth, custom user attribute set
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "selfservice", "realm": self.realm1, "pass": pin},
                                               headers={"user_agent": "privacyidea-cp/2.0"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                detail = res.json.get("detail")
                # custom user attribute set from last auth to interactive
                self.assertEqual("interactive", detail.get("preferred_client_mode"))

        delete_policy("auth")
        sms.delete_token()
        totp.delete_token()
