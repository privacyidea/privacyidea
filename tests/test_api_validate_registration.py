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


class RegistrationValidity(MyApiTestCase):

    def setUp(self):
        super(RegistrationValidity, self).setUp()
        self.setUp_user_realms()

    def test_00_registrationtoken_with_validity_period(self):
        r = init_token({"type": "registration"},
                       user=User("cornelius", self.realm1))
        password = r.init_details.get("otpkey")

        # The enddate is 17 minutes in the past
        end_date = datetime.datetime.now() - datetime.timedelta(minutes=17)
        end_date_str = end_date.strftime(DATE_FORMAT)
        r.set_validity_period_end(end_date_str)
        # now check if authentication fails
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": quote(password)}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Outside validity period", detail.get("message"), (detail, password))


class RegistrationAndPasswordToken(MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()

    def test_00_registration_tokens(self):
        # Registration tokens always do a genkey, even if we do not set it
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'registration'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            detail = data.get("detail")
            regcode = detail.get("registrationcode")
            self.assertEqual(DEFAULT_LENGTH_REG, len(regcode))
            # Check if a number is contained
            self.assertRegex(regcode, "[0-9]+")
            # Check if a character is contained
            self.assertRegex(regcode, "[a-zA-Z]+")

        # now check if authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": quote(regcode)}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("ACCEPT", data.get("result").get("authentication"), (data, regcode))

        # Create a reg token with explicitly setting genkey
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'registration',
                                                 'genkey': 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            detail = data.get("detail")
            regcode = detail.get("registrationcode")

        # now check the authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": quote(regcode)}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("ACCEPT", data.get("result").get("authentication"), (data, regcode))

        # create a reg token, where the otpkey is ignored
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'registration',
                                                 'otpkey': "hallo"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            detail = data.get("detail")
            regcode = detail.get("registrationcode")
            self.assertEqual(DEFAULT_LENGTH_REG, len(regcode))
            self.assertNotEqual("hallo", regcode)

        # now check the authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": quote(regcode)}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("ACCEPT", data.get("result").get("authentication"), (data, regcode))

        # The registration code was generated. The passed otpkey was NOT used.
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("REJECT", data.get("result").get("authentication"), data)

    def test_01_password_tokens(self):
        set_policy("enroll", scope=SCOPE.ADMIN, action=["enrollPW", PolicyAction.ENROLLPIN])
        # always generate a key if non is given
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'pw'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            serial = res.json.get("detail").get("serial")
            remove_token(serial)
            db.session.expunge_all()

        # Try setting an explicit password
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'pw',
                                                 'otpkey': 'topsecret',
                                                 'pin': 'test'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            detail = data.get("detail")
            serial = detail.get("serial")

        # now check the authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "testtopsecret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("ACCEPT", data.get("result").get("authentication"), data)
        # delete token
        remove_token(serial)
        db.session.expunge_all()

        # Try getting a generated password
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'pw',
                                                 'genkey': 1,
                                                 'pin': 'test'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            detail = data.get("detail")
            serial = detail.get("serial")
            password = detail.get("password")
            self.assertEqual(DEFAULT_LENGTH_PW, len(password))
            # Check if a number is contained
            self.assertRegex(password, "[0-9]+")
            # Check if a character is contained
            self.assertRegex(password, "[a-zA-Z]+")

        # now check the authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": quote("test{0!s}".format(password))}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("ACCEPT", data.get("result").get("authentication"), (data, password))
        # delete token
        remove_token(serial)
        delete_policy("enroll")

    def test_02_application_specific_password_token(self):
        set_policy("enroll", scope=SCOPE.ADMIN, action=["enrollAPPLSPEC", PolicyAction.ENROLLPIN])
        # always generate a key if non is give
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'applspec',
                                                 'service_id': 'thunderbird'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json.get("result"))
            serial = res.json.get("detail").get("serial")
            remove_token(serial)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'genkey': '1',
                                                 'type': 'applspec'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code)
            data = res.json
            error = data.get("result").get("error")
            self.assertEqual(905, error.get("code"))
            self.assertEqual("ERR905: Missing parameter: service_id", error.get("message"), data)

        # Now pass all necessary parameters
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'applspec',
                                                 'genkey': '1',
                                                 'service_id': 'thunderbird',
                                                 'pin': 'test'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            detail = data.get("detail")
            serial = detail.get("serial")
            password = detail.get("password")

        # Check, if the token has the service_id
        tok = get_tokens(serial=serial)[0]
        self.assertEqual("thunderbird", tok.service_id)

        # now check the authentication. No service_id
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": quote("test{0!s}".format(password))}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("REJECT", data.get("result").get("authentication"), data)
            self.assertEqual("No suitable token found for authentication.",
                             data.get("detail").get("message"), data)

        # now check the authentication. wrong service_id
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "service_id": "wrong",
                                                 "pass": quote("test{0!s}".format(password))}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("REJECT", data.get("result").get("authentication"), data)
            self.assertEqual("No suitable token found for authentication.",
                             data.get("detail").get("message"), data)

        # now check the authentication. correct service_id
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "service_id": "thunderbird",
                                                 "pass": quote("test{0!s}".format(password))}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual("ACCEPT", data.get("result").get("authentication"), (data, password))
            self.assertEqual("matching 1 tokens", data.get("detail").get("message"), data)

        # delete token
        remove_token(serial)
