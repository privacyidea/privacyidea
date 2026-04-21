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


class MultiChallengeEnrollTest(MyApiTestCase):

    # Note: Testing the enrollment of the push token is done in test_api_push_validate.py,
    # passkey in test_api_passkey_validate.py
    # container in the container tests

    def setUp(self):
        super(MultiChallengeEnrollTest, self).setUp()

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

    @ldap3mock.activate
    @log_capture(level=logging.DEBUG)
    def test_01_enroll_HOTP(self, capture):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        logging.getLogger('privacyidea').setLevel(logging.DEBUG)
        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # 1. set policies.
        # Policy scope:auth, action:enroll_via_multichallenge=hotp
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)

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

        # Set enroll policy
        set_policy("pol_multienroll", scope=SCOPE.AUTH,
                   action="{0!s}=hotp".format(PolicyAction.ENROLL_VIA_MULTICHALLENGE))

        # Set force_app_pin
        set_policy("pol_forcepin", scope=SCOPE.ENROLL,
                   action="hotp_{0!s}=True".format(PolicyAction.FORCE_APP_PIN))
        # Set token default
        set_privacyidea_config("hotp.hashlib", "sha256")
        # Now we should get an authentication Challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "pass": "alicepw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(result.get("authentication"), "CHALLENGE")
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue("Please scan the QR code and enter the OTP value!" in detail.get("message"),
                            detail.get("message"))
            self.assertTrue(detail.get(PolicyAction.ENROLL_VIA_MULTICHALLENGE))
            self.assertFalse(detail.get(PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL))
            # Get image and client_mode
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("client_mode"), detail)
            # Check, that multi_challenge is also contained.
            chal = detail.get("multi_challenge")[0]
            self.assertEqual(ClientMode.INTERACTIVE, chal.get("client_mode"), detail)
            self.assertIn("image", detail, detail)
            self.assertIn("link", detail)
            link = detail.get("link")
            self.assertTrue(link.startswith("otpauth://hotp"), link)
            self.assertEqual(1, len(detail.get("messages")))
            self.assertEqual("Please scan the QR code and enter the OTP value!", detail.get("messages")[0])
            serial = detail.get("serial")

        # 3. scan the qrcode / Get the OTP value
        token_obj = get_tokens(serial=serial)[0]
        otp = token_obj._calc_otp(1)

        # 4. run the 2nd authentication with the OTP value and the transaction_id
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": otp}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        log_msg = str(capture)
        self.assertNotIn('alicepw', log_msg, log_msg)
        self.assertNotIn('ldappw', log_msg, log_msg)
        self.assertIn('HIDDEN', log_msg, log_msg)
        # Verify that the force_pin enrollment policy worked for validate-check-enrollment
        self.assertIn(
            'Exiting get_init_tokenlabel_parameters with result {\'force_app_pin\': True, \'app_force_unlock\': \'pin\'}',
            log_msg, log_msg)
        logging.getLogger('privacyidea').setLevel(logging.INFO)
        """
        Verify that the QR code was generated with SHA256, this is in the log file.
        It will be indicated by this text:
        Entering create_google_authenticator_url with arguments () and keywords ... 'hash_algo': 'sha256'
        """
        sha256regexp = re.compile(r"Entering create_google_authenticator_url with arguments.*'hash_algo': 'sha256'")
        self.assertTrue(sha256regexp.search(log_msg), log_msg)

        # Check SHA256 of the token.
        self.assertEqual("sha256", token_obj.get_tokeninfo("hashlib"))

        # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        delete_policy("pol_forcepin")
        set_privacyidea_config("hotp.hashlib", "sha1")
        remove_token(serial)

    @ldap3mock.activate
    @log_capture(level=logging.DEBUG)
    def test_02_enroll_TOTP(self, capture):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        logging.getLogger('privacyidea.lib.tokens.totptoken').setLevel(logging.DEBUG)
        logging.getLogger('privacyidea.lib.apps').setLevel(logging.DEBUG)
        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # 1. set policies.
        # Policy scope:auth, action:enroll_via_multichallenge=totp
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)

        # 2. authenticate user via passthru
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "pass": "alicepw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        # Set enroll policy
        set_policy("pol_multienroll", scope=SCOPE.AUTH,
                   action="{0!s}=totp".format(PolicyAction.ENROLL_VIA_MULTICHALLENGE))

        # Set totp_hashlib=sha256 user policy
        set_policy("pol_sha256", scope=SCOPE.USER,
                   action="totp_hashlib=sha256")

        # Now we should get an authentication Challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "pass": "alicepw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(result.get("authentication"), "CHALLENGE")
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue("Please scan the QR code and enter the OTP value!" in detail.get("message"),
                            detail.get("message"))
            # Get image and client_mode
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("multi_challenge")[0].get("client_mode"))
            self.assertIn("image", detail)
            self.assertIn("link", detail)
            link = detail.get("link")
            self.assertTrue(link.startswith("otpauth://totp"), link)
            serial = detail.get("serial")

        # 3. scan the qrcode / Get the OTP value
        token_obj = get_tokens(serial=serial)[0]
        counter = int(time.time() / 30)
        otp = token_obj._calc_otp(counter)
        # Capture the log for later hash validation
        log_msg = str(capture)

        # 4a. fail to authenticate with a wrong OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": "123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(result.get("authentication"), "REJECT")

        # 4. run the 2nd authentication with the OTP value and the transaction_id
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": otp}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        sha256regexp = re.compile(r"Entering create_google_authenticator_url with arguments.*'hash_algo': 'sha256'")
        self.assertTrue(sha256regexp.search(log_msg), log_msg)
        # Check SHA256 of the token.
        self.assertEqual("sha256", token_obj.get_tokeninfo("hashlib"))
        # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        delete_policy("pol_sha256")
        remove_token(serial)

    @ldap3mock.activate
    @smtpmock.activate
    def test_03_enroll_EMail(self):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # mock email sending
        smtpmock.setdata(response={"alice@example.com": (200, 'OK')})
        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # 1. set policies.
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)

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

        # Set Policy scope:auth, action:enroll_via_multichallenge=email
        set_policy("pol_multienroll", scope=SCOPE.AUTH,
                   action="{0!s}=email".format(PolicyAction.ENROLL_VIA_MULTICHALLENGE))
        # Challenge header and footer should not disturb the enrollment text
        set_policy("pol_challengetext_head", scope=SCOPE.AUTH,
                   action="{0!s}=challenge-head".format(PolicyAction.CHALLENGETEXT_HEADER))
        set_policy("pol_challengetext_foot", scope=SCOPE.AUTH,
                   action="{0!s}=challenge-foot".format(PolicyAction.CHALLENGETEXT_FOOTER))
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
            self.assertTrue("Please enter your new email address!" in detail.get("message"), detail.get("message"))
            # Get image and client_mode
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("multi_challenge")[0].get("client_mode"))
            self.assertIn("image", detail)
            serial = detail.get("serial")

        # 3. Enter a correct email address and finalize the token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": "alice@example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(result.get("authentication"), "CHALLENGE")
            transaction_id = detail.get("transaction_id")

        # The email was sent, with the OTP value
        token_obj = get_tokens(serial=serial)[0]
        otp = token_obj._calc_otp(1)

        # 4. run the 2nd authentication with the OTP value and the transaction_id
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": otp}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        remove_token(serial)

    @ldap3mock.activate
    @smtpmock.activate
    def test_03_fail_to_enroll_EMail(self):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # mock email sending
        smtpmock.setdata(response={"alice@example.com": (200, 'OK')})
        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # 1. set policies.
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)

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

        # Set Policy scope:auth, action:enroll_via_multichallenge=email
        set_policy("pol_multienroll", scope=SCOPE.AUTH,
                   action="{0!s}=email".format(PolicyAction.ENROLL_VIA_MULTICHALLENGE))
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
            self.assertTrue("Please enter your new email address!" in detail.get("message"), detail.get("message"))
            # Get image and client_mode
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("multi_challenge")[0].get("client_mode"))
            self.assertIn("image", detail)

        # 3. Enter an invalid email address and finalize the token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": "alice@example.c"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(result.get("error").get("message"), "ERR401: The email address is not valid!")

        # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        # Check that the user has no token
        toks = get_tokens(user=User("alice", "ldaprealm"), tokentype="email")
        self.assertEqual(0, len(toks))

    @ldap3mock.activate
    @responses.activate
    def test_04_enroll_SMS(self):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # mock http response
        setup_sms_gateway()

        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # 1. set policies.
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)

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

        # Set Policy scope:auth, action:enroll_via_multichallenge=email
        set_policy("pol_multienroll", scope=SCOPE.AUTH,
                   action="{0!s}=sms".format(PolicyAction.ENROLL_VIA_MULTICHALLENGE))
        # Set an individual text
        set_policy("pol_multienroll_text", scope=SCOPE.AUTH,
                   action="{0!s}='Phone number enter you must!'".format(PolicyAction.ENROLL_VIA_MULTICHALLENGE_TEXT))
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
            self.assertTrue("Phone number enter you must!" in detail.get("message"), detail.get("message"))
            # Get image and client_mode
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("multi_challenge")[0].get("client_mode"))
            self.assertIn("image", detail)
            serial = detail.get("serial")

        # 3. Enter the phone number and finalize the token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": "99555555"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(result.get("authentication"), "CHALLENGE")
            transaction_id = detail.get("transaction_id")

        # The SMS was sent, with the OTP value
        token_obj = get_tokens(serial=serial)[0]
        otp = token_obj._calc_otp(1)

        # 4. run the 2nd authentication with the OTP value and the transaction_id
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": otp}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        delete_policy("pol_multienroll_text")
        remove_token(serial)

    @ldap3mock.activate
    @smtpmock.activate
    def test_05_enroll_EMail_3rdparty_validator(self):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # mock email sending
        smtpmock.setdata(response={"alice@example.com": (200, 'OK')})
        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # 1. set policies.
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)
        set_policy("pol_validator", scope=SCOPE.ENROLL,
                   action="{0!s}=tests.testdata.gmailvalidator".format(PolicyAction.EMAILVALIDATION))

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

        # Set Policy scope:auth, action:enroll_via_multichallenge=email
        set_policy("pol_multienroll", scope=SCOPE.AUTH,
                   action="{0!s}=email".format(PolicyAction.ENROLL_VIA_MULTICHALLENGE))
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
            self.assertTrue("Please enter your new email address!" in detail.get("message"), detail.get("message"))
            # Get image and client_mode
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(ClientMode.INTERACTIVE, detail.get("multi_challenge")[0].get("client_mode"))
            self.assertIn("image", detail)

        # 3. Enter an inncorrect email address and finalize the token
        # The validator expects a gmail email address and the enrollment will fail.
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "transaction_id": transaction_id,
                                                 "pass": "alice@example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(result.get("error").get("message"), "ERR401: The email address is not valid!")

            # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        delete_policy("pol_validator")
        # Check that the user has no token
        toks = get_tokens(user=User("alice", "ldaprealm"), tokentype="email")
        self.assertEqual(0, len(toks))

    def test_06_max_token_policy(self):
        """
        There are 5 policies that can limit the number of tokens a user can have, which will deny
        enroll_via_multichallenge. 4 policies are checked via check_max_token_user:
        - max_token_per_user
        - max_active_token_per_user
        - {type}_max_token_per_user
        - {type_max_active_token_per_user
        And 1 via check_max_token_realm:
        - max_token_per_realm
        Test that each of these functions correctly deny the enrollment of a token.
        """
        self.setUp_user_realms()
        user = User("hans", "realm1")
        spass = "12"
        token1 = init_token({"type": "spass", "pin": spass}, user)
        self.assertTrue(token1.get_serial().startswith("PISP"))
        # Check that we do not have a failed audit entry if the policy is set
        set_policy("max_token_per_user", scope=SCOPE.ENROLL, action=f"{PolicyAction.MAXTOKENUSER}=1")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user.login, "realm": user.realm, "pass": spass}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result").get("status"))
            self.assertTrue(res.json.get("result").get("value"))
            self.assertEqual(res.json.get("result").get("authentication"), "ACCEPT")
            self.assertNotIn("transaction_id", res.json.get("detail"))
            self.assertNotIn("multi_challenge", res.json.get("detail"))
        # Check that we have the proper log message (action_detail) in the audit
        audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
        self.assertIsNotNone(audit_entry)
        self.assertFalse(audit_entry["action_detail"], audit_entry)
        self.assertEqual(audit_entry["authentication"], AUTH_RESPONSE.ACCEPT, audit_entry)
        self.assertEqual(audit_entry["success"], 1, audit_entry)
        delete_policy("max_token_per_user")

        set_policy("enroll_via_multichallenge", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=hotp")

        set_policy("max_token_per_user", scope=SCOPE.ENROLL, action=f"{PolicyAction.MAXTOKENUSER}=1")
        self._authenticate_no_token_enrolled(user, spass)
        delete_policy("max_token_per_user")

        set_policy("max_active_token_per_user", scope=SCOPE.ENROLL, action=f"{PolicyAction.MAXACTIVETOKENUSER}=1")
        self._authenticate_no_token_enrolled(user, spass)
        delete_policy("max_active_token_per_user")

        set_policy("hotp_max_token_per_user", scope=SCOPE.ENROLL, action=f"{PolicyAction.MAXTOKENUSER}=0")
        self._authenticate_no_token_enrolled(user, spass)
        delete_policy("hotp_max_token_per_user")

        set_policy("max_token_per_realm", scope=SCOPE.ENROLL, action=f"{PolicyAction.MAXTOKENREALM}=1")
        self._authenticate_no_token_enrolled(user, spass)
        delete_policy("max_token_per_realm")

        # Test that the max token policies are not checked if there is no need to enroll a new token
        token2 = init_token({"type": "hotp", "genkey": True}, user)
        with mock.patch("privacyidea.api.lib.prepolicy.check_max_token_user") as mock_check_max_token_user, mock.patch(
                "privacyidea.api.lib.prepolicy.check_max_token_realm") as mock_check_max_token_realm:
            self._authenticate_no_token_enrolled(user, spass, check_audit=False)
            self.assertEqual(0, mock_check_max_token_user.call_count)
            self.assertEqual(0, mock_check_max_token_realm.call_count)
        # Check that we do not have a log message (action_detail) regarding the max tokens in the audit
        audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
        self.assertIsNotNone(audit_entry)
        self.assertFalse(audit_entry["action_detail"].startswith("ERR303: The number of "), audit_entry)
        self.assertEqual(audit_entry["authentication"], AUTH_RESPONSE.ACCEPT, audit_entry)
        self.assertEqual(audit_entry["success"], 1, audit_entry)

        delete_policy("enroll_via_multichallenge")
        remove_token(token1.get_serial())
        remove_token(token2.get_serial())

    @ldap3mock.activate
    def test_07_enroll_TOTP_default_params(self):
        """
        Test that the correct system defaults are used for the token and in the enroll url.
        There are three possibilities: Use the system default (sha1, 30 seconds), set the defaults in the
        configurations, or use a user policy to enforce a specific hashlib and time step. The policy take
        precedence over the system defaults.
        """
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # set policies: passthru and enroll_via_multichallenge
        set_policy("policy", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.PASSTHRU}=userstore,{PolicyAction.ENROLL_VIA_MULTICHALLENGE}=totp")

        def check_token_init(hashlib, time_step):
            # authenticate user via passthru triggers enrollment
            with self.app.test_request_context("/validate/check",
                                               method="POST",
                                               data={"user": "alice",
                                                     "pass": "alicepw"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertTrue(result.get("status"))
                self.assertFalse(result.get("value"))
                self.assertEqual(result.get("authentication"), "CHALLENGE")

                detail = res.json.get("detail")
                self.assertIn("image", detail)
                self.assertIn("link", detail)

                # check enroll url
                enroll_url = detail.get("link")
                if hashlib == "sha1":
                    self.assertNotIn("&algorithm", enroll_url)
                else:
                    self.assertIn(f"&algorithm={hashlib.upper()}", enroll_url)
                self.assertIn(f"&period={time_step}", enroll_url)

                # check token info
                serial = detail.get("serial")
                token = get_one_token(serial=serial)
                self.assertEqual(hashlib, token.get_tokeninfo(key="hashlib"))
                self.assertEqual(time_step, token.get_tokeninfo(key="timeStep"))

                token.delete_token()

        # System default
        check_token_init("sha1", "30")

        # Set system default to sha256 and 60 seconds
        set_privacyidea_config("totp.hashlib", "sha256", "public", "")
        set_privacyidea_config("totp.timeStep", "60", "public", "")
        check_token_init("sha256", "60")

        # Set user policy
        set_policy("user_policy", SCOPE.USER, {"totp_hashlib": "sha512", "totp_timestep": "30"})
        check_token_init("sha512", "30")
        delete_policy("user_policy")

        delete_policy("policy")

    def _authenticate_no_token_enrolled(self, user: User, otp, check_audit=True):
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user.login, "realm": user.realm, "pass": otp}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertIn("result", data)
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "ACCEPT")
            self.assertIn("detail", data)
            detail = data.get("detail")
            self.assertNotIn("transaction_id", detail)
            self.assertNotIn("multi_challenge", detail)
        if check_audit:
            # Check that we have the proper log message (action_detail) in the audit
            audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
            self.assertIsNotNone(audit_entry)
            self.assertTrue(audit_entry["action_detail"].startswith("ERR303: The number of "), audit_entry)
            self.assertEqual(audit_entry["authentication"], AUTH_RESPONSE.ACCEPT, audit_entry)
            self.assertEqual(audit_entry["success"], 1, audit_entry)

    @ldap3mock.activate
    def test_08_enroll_smartphone_success(self):
        """
        Test one full authentication flow with the enrollment of a smartphone container using a template with the
        passthru policy.
            1. validate/check with username and password
                -> authentication accepted due to passthru policy
                -> container is created and registration data is contained in the response as multi challenge
                   the authentication is changed to challenge
            2. validate/polltransaction/{transaction_id}
                -> challenge status is still pending
            3. Finalize registration for the smartphone (mock)
            4. validate/polltransaction/{transaction_id}
                -> challenge status is now accept
            5. validate/check with username, empty password and transaction_id
                -> authentication accepted due to answered challenge for smartphone container
        """
        template_options = {"tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True}]}
        create_container_template(container_type="smartphone", template_name="test", options=template_options)
        set_policy("enroll_via_multichallenge", scope=SCOPE.AUTH,
                   action={PolicyAction.ENROLL_VIA_MULTICHALLENGE: "smartphone",
                           PolicyAction.ENROLL_VIA_MULTICHALLENGE_TEMPLATE: "test",
                           PolicyAction.PASSTHRU: True})
        set_policy("registration", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/"})

        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        logging.getLogger('privacyidea').setLevel(logging.DEBUG)
        # create realm
        set_realm("ldaprealm", resolvers=[{'name': "catchall"}])
        set_default_realm("ldaprealm")

        # Authenticate user via passthru
        with self.app.test_request_context('/validate/check', method='POST', data={"user": "alice", "pass": "alicepw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual("CHALLENGE", result.get("authentication"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertIn("Please scan the QR code to register the container", detail.get("message"))
            # Get image and client_mode
            self.assertEqual(ClientMode.POLL, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            challenge = detail.get("multi_challenge")[0]
            self.assertEqual(ClientMode.POLL, challenge.get("client_mode"))
            self.assertIn("image", detail)
            self.assertIn("link", detail)
            link = detail.get("link")
            self.assertTrue(link.startswith("pia://container"))
            # used default message
            self.assertIn("message", detail)
            self.assertIn("Please scan the QR code to register the container", detail.get("message"))
            serial = detail.get("serial")
            container = find_container_by_serial(serial)
            self.assertEqual("smartphone", container.type)
            self.assertEqual("poll", detail.get("client_mode"))
            # check that tokens for container are created
            tokens = container.tokens
            self.assertSetEqual({"totp", "hotp"}, {token.type for token in tokens})

        # Poll transaction
        with self.app.test_request_context(f"/validate/polltransaction/{transaction_id}", method='GET',
                                           data={"user": "alice"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"])
            self.assertFalse(result["value"])
            self.assertEqual("pending", res.json["detail"].get("challenge_status"))

        # Mock smartphone finalizing the registration
        mock_smph = MockSmartphone()
        scope = "https://pi.net/container/register/finalize"
        # these are invalid values, but we mock the signature verification to evaluate to true anyway
        params = mock_smph.register_finalize("123456", datetime.datetime.now(), scope, container.serial)
        with mock.patch('privacyidea.lib.containerclass.verify_ecc',
                        return_value={"valid": True, "hash_algorithm": "SHA256"}):
            container.finalize_registration(params)

        # Poll transaction
        with self.app.test_request_context(f"/validate/polltransaction/{transaction_id}", method='GET',
                                           data={"user": "alice"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"])
            self.assertTrue(result["value"])
            self.assertEqual("accept", res.json["detail"].get("challenge_status"))

        # Validate Check
        with self.app.test_request_context('/validate/check', method='POST', data={"user": "alice", "pass": "",
                                                                                   "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(AUTH_RESPONSE.ACCEPT, result.get("authentication"))
