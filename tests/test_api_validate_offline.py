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


class AValidateOfflineTestCase(MyApiTestCase):
    """
    Test api.validate endpoints that are responsible for offline auth.
    """

    def _resend_and_check_unspecific_error(self, status_code: int):
        set_policy(name="hide_specific_error_message", scope=SCOPE.TOKEN,
                   action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE_FOR_OFFLINE_REFILL}=true")
        try:
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, status_code, res)
            data = res.json
            self.assertEqual(data["result"]["error"]["code"], Error.VALIDATE)
            self.assertEqual(data["result"]["error"]["message"], "Failed offline token refill")
        finally:
            delete_policy("hide_specific_error_message")

    def test_00_create_realms(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # create a  token and assign it to the user
        db_token = Token(self.serials[0], tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        self.assertTrue(token.token.serial == self.serials[0], token)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin("pin")
        self.assertEqual(token.token.first_owner.user_id, "1000")

    def test_01_validate_offline(self):
        # create offline app
        # tokenobj = get_tokens(self.serials[0])[0]
        mr_obj = save_machine_resolver({"name": "testresolver",
                                        "type": "hosts",
                                        "filename": HOSTSFILE,
                                        "type.filename": "string",
                                        "desc.filename": "the filename with the "
                                                         "hosts",
                                        "pw": "secret",
                                        "type.pw": "password"})
        self.assertTrue(mr_obj > 0)
        # Attach the offline app to pippin
        attach_token(self.serials[0], "offline", hostname="pippin",
                     resolver_name="testresolver", options={"count": 100})

        # first online validation
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("otplen"), 6)
            auth_items = res.json.get("auth_items")
            offline = auth_items.get("offline")[0]
            # Check the number of OTP values
            self.assertEqual(len(offline.get("response")), 100)
            self.assertEqual(offline.get("username"), "cornelius")
            refilltoken_1 = offline.get("refilltoken")
            self.assertEqual(len(refilltoken_1), 2 * REFILLTOKEN_LENGTH)
            # check the token counter
            tok = get_tokens(serial=self.serials[0])[0]
            self.assertEqual(tok.token.count, 102)

        # first refill with the 5th value
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin338314",
                                                 "refilltoken": refilltoken_1},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            auth_items = res.json.get("auth_items")
            offline = auth_items.get("offline")[0]
            # Check the number of OTP values
            self.assertEqual(len(offline.get("response")), 3)
            self.assertTrue("102" in offline.get("response"))
            self.assertTrue("103" in offline.get("response"))
            self.assertTrue("104" in offline.get("response"))
            refilltoken_2 = offline.get("refilltoken")
            self.assertEqual(len(refilltoken_2), 2 * REFILLTOKEN_LENGTH)
            # check the token counter
            tok = get_tokens(serial=self.serials[0])[0]
            self.assertEqual(tok.token.count, 105)
            # The refilltoken changes each time
            self.assertNotEqual(refilltoken_1, refilltoken_2)

        # refill with wrong refill token fails
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin520489",
                                                 "refilltoken": 'a' * 2 * REFILLTOKEN_LENGTH},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            data = res.json
            self.assertEqual(data.get("result").get("error").get("message"),
                             "ERR905: Token is not an offline token or refill token is incorrect")

            self._resend_and_check_unspecific_error(400)

        # Disable token. Refill should fail.
        enable_token(self.serials[0], False)
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin520489",
                                                 "refilltoken": refilltoken_2},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            error = result.get("error")
            self.assertEqual(905, error.get("code"))
            self.assertEqual("ERR905: The token is not valid.", error.get("message"))

            self._resend_and_check_unspecific_error(400)

        # Enable token again
        enable_token(self.serials[0], True)

        # 2nd refill with 10th value
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin520489",
                                                 "refilltoken": refilltoken_2},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            auth_items = res.json.get("auth_items")
            offline = auth_items.get("offline")[0]
            # Check the number of OTP values
            self.assertEqual(len(offline.get("response")), 5)
            self.assertTrue("105" in offline.get("response"))
            self.assertTrue("106" in offline.get("response"))
            self.assertTrue("107" in offline.get("response"))
            self.assertTrue("108" in offline.get("response"))
            self.assertTrue("109" in offline.get("response"))
            refilltoken_3 = offline.get("refilltoken")
            self.assertEqual(len(refilltoken_3), 2 * REFILLTOKEN_LENGTH)
            # check the token counter
            tok = get_tokens(serial=self.serials[0])[0]
            self.assertEqual(tok.token.count, 110)
            # The refilltoken changes each time
            self.assertNotEqual(refilltoken_2, refilltoken_3)
            self.assertNotEqual(refilltoken_1, refilltoken_3)

        # A refill with a totally wrong OTP value fails
        token_obj = get_tokens(serial=self.serials[0])[0]
        old_counter = token_obj.token.count
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin000000",
                                                 "refilltoken": refilltoken_3},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            data = res.json
            self.assertTrue(res.status_code == 400, res)
            self.assertEqual(data.get("result").get("error").get("message"),
                             "ERR401: You provided a wrong OTP value.")

            self._resend_and_check_unspecific_error(400)

        # The failed refill should not modify the token counter!
        self.assertEqual(old_counter, token_obj.token.count)

        # A refill with a wrong serial number fails
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": 'ABCDEF123',
                                                 "pass": "pin000000",
                                                 "refilltoken": refilltoken_3},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            data = res.json
            self.assertTrue(res.status_code == 400, res)
            self.assertEqual(data.get("result").get("error").get("message"),
                             "ERR905: The token does not exist")

            self._resend_and_check_unspecific_error(400)

        # Detach the token, refill should then fail
        detach_token(self.serials[0], "offline", "pippin")
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin520489",
                                                 "refilltoken": refilltoken_3},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            data = res.json
            self.assertTrue(res.status_code == 400, res)
            self.assertEqual(data.get("result").get("error").get("message"),
                             "ERR905: Token is not an offline token or refill token is incorrect")

            self._resend_and_check_unspecific_error(400)
