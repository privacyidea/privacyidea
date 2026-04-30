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


class ValidateShortPasswordTestCase(MyApiTestCase):
    yubi_otpkey = "9163508031b20d2fbb1868954e041729"

    public_uid = "ecebeeejedecebeg"
    valid_yubi_otps = [
        public_uid + "fcniufvgvjturjgvinhebbbertjnihit",
        public_uid + "tbkfkdhnfjbjnkcbtbcckklhvgkljifu",
        public_uid + "ktvkekfgufndgbfvctgfrrkinergbtdj",
        public_uid + "jbefledlhkvjjcibvrdfcfetnjdjitrn",
        public_uid + "druecevifbfufgdegglttghghhvhjcbh",
        public_uid + "nvfnejvhkcililuvhntcrrulrfcrukll",
        public_uid + "kttkktdergcenthdredlvbkiulrkftuk",
        public_uid + "hutbgchjucnjnhlcnfijckbniegbglrt",
        public_uid + "vneienejjnedbfnjnnrfhhjudjgghckl",
    ]

    def test_00_setup_tokens(self):
        self.setUp_user_realms()

        pin = ""
        # create a token and assign it to the user
        db_token = Token(self.serials[0], tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        self.assertEqual(self.serials[0], token.token.serial)
        self.assertEqual(6, token.token.otplen)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)

        # create a yubikey and assign it to the user
        db_token = Token(self.serials[1], tokentype="yubikey")
        db_token.update_otpkey(self.yubi_otpkey)
        db_token.otplen = 48
        db_token.save()
        token = YubikeyTokenClass(db_token)
        self.assertEqual(self.serials[1], token.token.serial)
        self.assertEqual(len(self.valid_yubi_otps[0]), token.token.otplen)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)

        # Successful authentication with HOTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "{0!s}{1!s}".format(pin, self.valid_otp_values[0])}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # verify the Yubikey AES mode
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "{0!s}{1!s}".format(pin, self.valid_yubi_otps[0])}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))


class Initialize(MyApiTestCase):

    def test01_no_type(self):
        with self.app.test_request_context('/validate/initialize',
                                           method='POST',
                                           data={"type": ""}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            self.assertIn("result", res.json)
            self.assertIn("error", res.json["result"])
            error = res.json["result"]["error"]
            self.assertIn("code", error)
            self.assertIn("message", error)
            self.assertEqual(905, error["code"], error)
            self.assertEqual("ERR905: Missing parameter: type", error["message"], error)
