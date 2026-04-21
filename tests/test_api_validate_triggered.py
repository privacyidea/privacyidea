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


class TriggeredPoliciesTestCase(MyApiTestCase):

    def setUp(self):
        super(TriggeredPoliciesTestCase, self).setUp()
        self.setUp_user_realms()

    def test_00_two_policies(self):
        set_policy("otppin", scope=SCOPE.AUTH, action="{0!s}=none".format(PolicyAction.OTPPIN))
        set_policy("lastauth", scope=SCOPE.AUTHZ, action="{0!s}=1s".format(PolicyAction.LASTAUTH))

        # Create a Spass token
        init_token({"serial": "triggtoken", "type": "spass"})

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "triggtoken", "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        # This authentication triggered the policy "otppin"
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"policies": "*otppin*"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 1)

        # Now wait a second and try to authenticate. Authentication should fail
        # due to policy "lastauth". Thus the policies "otppin" and "lastauth" are
        # triggered
        time.sleep(1.5)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "triggtoken", "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))

        # This authentication triggered the policy "otppin" and "lastauth"
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"policies": "*lastauth*"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get("count"), 1)
            # Both policies have triggered
            audit_policies = json_response.get("result").get("value").get("auditdata")[0].get("policies").split(",")
            self.assertEqual({"otppin", "lastauth"}, set(audit_policies))

        # clean up
        remove_token("triggtoken")
        delete_policy("otppin")
        delete_policy("lastauth")
