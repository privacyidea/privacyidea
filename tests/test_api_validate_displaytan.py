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


class DisplayTANTestCase(MyApiTestCase):

    def test_00_run_complete_workflow(self):
        # This is a standard workflow of a display TAN token.

        # Import OCRA Token file
        IMPORTFILE = "tests/testdata/ocra.csv"
        with self.app.test_request_context('/token/load/ocra.csv',
                                           method="POST",
                                           data={"type": "oathcsv",
                                                 "file": (IMPORTFILE,
                                                          "oath.csv")},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")['n_imported']
            self.assertTrue(value == 1, result)

        from privacyidea.lib.token import set_pin
        set_pin("ocra1234", "test")

        # Issue a challenge response
        challenge = "83507112  ~320,00~1399458665_G6HNVF"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "ocra1234",
                                                 "pass": "test",
                                                 "hashchallenge": 1,
                                                 "challenge": challenge}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            hex_challenge = detail.get("attributes").get("challenge")
            self.assertEqual(hex_challenge, "7196501689c356046867728f4feb74458dcfd079")

        # Issue an authentication request
        otpvalue = "90065298"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "ocra1234",
                                                 "pass": otpvalue,
                                                 "transaction_id":
                                                     transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)

        # The second request will fail
        otpvalue = "90065298"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "ocra1234",
                                                 "pass": otpvalue,
                                                 "transaction_id":
                                                     transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)

        # Get another challenge with a random nonce
        challenge = "83507112  ~320,00~"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "ocra1234",
                                                 "pass": "test",
                                                 "hashchallenge": 1,
                                                 "addrandomchallenge": 20,
                                                 "challenge": challenge}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            hex_challenge = detail.get("attributes").get("challenge")
            self.assertEqual(len(hex_challenge), 40)

        remove_token("ocra1234")
