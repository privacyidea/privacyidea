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
from privacyidea.lib.tokens.pushtoken import (PushAction, POLL_ONLY, strip_pem_headers,
                                              DEFAULT_MOBILE_TEXT)
from privacyidea.lib.tokens.registrationtoken import DEFAULT_LENGTH as DEFAULT_LENGTH_REG
from privacyidea.lib.tokens.registrationtoken import RegistrationTokenClass
from privacyidea.lib.tokens.smstoken import SmsTokenClass
from privacyidea.lib.tokens.totptoken import HotpTokenClass
from privacyidea.lib.tokens.yubikeytoken import YubikeyTokenClass
from privacyidea.lib.user import (User)
from privacyidea.lib.users.internal_user_attributes import InternalUserAttributes
from privacyidea.lib.utils import AUTH_RESPONSE
from privacyidea.lib.utils import to_unicode
from privacyidea.models import (Token, Policy, Challenge, AuthCache, db, TokenOwner, Realm, CustomUserAttribute,
                                NodeName)
from . import smtpmock, ldap3mock, radiusmock
from .base import MyApiTestCase
from .test_lib_tokencontainer import MockSmartphone

from .api_validate_common import LDAPDirectory, OTPs, HOSTSFILE, DICT_FILE, setup_sms_gateway


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
    registration_url = "http://test/ttype/push"
    ttl = "10"

    def setUp(self):
        self.setUp_user_realms()

    def _enroll_poll_only_push_token(self, pin):
        """
        Enroll a poll only push token for the user and return its serial.
        """
        set_policy("push2", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},"
                          f"{PushAction.REGISTRATION_URL}={self.registration_url},"
                          f"{PushAction.TTL}={self.ttl}")

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
            self.assertEqual(200, res.status_code)
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
            self.assertEqual(200, res.status_code, res)
            serial = res.json.get("detail").get("serial")

        return serial

    def _get_question_of_challenge(self, pin, serial):
        """
        Trigger a challenge and return the question the smartphone receives when polling.
        """
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.user,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            detail = res.json.get("detail")
            self.assertEqual("Please confirm the authentication on your mobile device!", detail.get("message"))

        # We do poll only, so we need to poll
        timestamp = datetime.datetime.utcnow().isoformat()
        sign_string = f"{serial}|{timestamp}"
        signature = self.smartphone_private_key.sign(sign_string.encode('utf8'),
                                                     padding.PKCS1v15(),
                                                     hashes.SHA256())
        with self.app.test_request_context('/ttype/push',
                                           method='GET',
                                           query_string={"serial": serial,
                                                         "timestamp": timestamp,
                                                         "signature": b32encode(signature)}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result").get("value")
            return value[0].get("question")

    def test_01_push_challenge_tags(self):
        # Test the challenge tags of a push token
        pin = "otppin"
        serial = self._enroll_poll_only_push_token(pin)

        set_policy("push1", scope=SCOPE.AUTH,
                   action=PushAction.MOBILE_TEXT + "=Login von UserAgent: {ua_string} via {client_ip}/{tokentype}.")

        # A polling request contains no client information, so the user agent and the
        # client IP are not available for the tags
        self.assertEqual("Login von UserAgent:  via /push.", self._get_question_of_challenge(pin, serial))

        remove_token(self.serial_push)
        delete_policy("push2")
        delete_policy("push1")

    def test_02_push_challenge_text_that_can_not_be_formatted(self):
        # A text with an unknown tag, a positional field or an unbalanced brace falls
        # back to the default message instead of failing the authentication
        pin = "otppin"
        serial = self._enroll_poll_only_push_token(pin)

        for text in ["Please confirm the login of {unknown_tag}",
                     "Please confirm the login of {0}",
                     "Please confirm the login with a 50{ discount"]:
            set_policy("push1", scope=SCOPE.AUTH, action=f"{PushAction.MOBILE_TEXT}={text}")
            self.assertEqual(str(DEFAULT_MOBILE_TEXT), self._get_question_of_challenge(pin, serial), text)

        remove_token(self.serial_push)
        delete_policy("push2")
        delete_policy("push1")
