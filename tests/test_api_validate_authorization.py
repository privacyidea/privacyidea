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


class AuthorizationPolicyTestCase(MyApiTestCase):
    """
    This tests the catch-all resolvers and resolvers which also contain the
    user.
    A user may authenticate with the default resolver, but the user may also
    be contained in other resolver. we check these other resolvers, too.

    Testcase for issue
    https://github.com/privacyidea/privacyidea/issues/543
    """

    @ldap3mock.activate
    def test_00_create_realm(self):
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

        params = {'LDAPURI': 'ldap://localhost',
                  'LDAPBASE': 'ou=sales,o=test',
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
                  "resolver": "sales",
                  "type": "ldapresolver"}

        r = save_resolver(params)
        self.assertTrue(r > 0)

        rl = get_resolver_list()
        self.assertTrue("catchall" in rl)
        self.assertTrue("sales" in rl)

    @ldap3mock.activate
    def test_01_resolving_user(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # create realm
        # If the sales resolver comes first, frank is found in sales!
        r = set_realm("ldaprealm",
                      resolvers=[
                          {'name': "catchall", 'priority': 2},
                          {'name': "sales", 'priority': 1}])
        set_default_realm("ldaprealm")
        self.assertEqual(r, (["catchall", "sales"], []))

        u = User("alice", "ldaprealm")
        uid, rtype, resolver = u.get_user_identifiers()
        self.assertEqual(resolver, "catchall")
        u = User("frank", "ldaprealm")
        uid, rtype, resolver = u.get_user_identifiers()
        self.assertEqual(resolver, "sales")

        # Catch all has the lower priority and contains all users
        # ldap2 only contains sales
        r = set_realm("ldaprealm",
                      resolvers=[
                          {'name': "catchall", 'priority': 1},
                          {'name': "sales", 'priority': 2}])
        self.assertEqual(r, (["catchall", "sales"], []))

        # Both users are found in the resolver "catchall
        u = User("alice", "ldaprealm")
        uid, rtype, resolver = u.get_user_identifiers()
        self.assertEqual(resolver, "catchall")
        u = User("frank", "ldaprealm")
        uid, rtype, resolver = u.get_user_identifiers()
        self.assertEqual(resolver, "catchall")

    @ldap3mock.activate
    def test_02_enroll_tokens(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        r = init_token({"type": "spass", "pin": "spass"}, user=User(
            login="alice", realm="ldaprealm"))
        self.assertTrue(r)
        # The token gets assigned to frank in the resolver catchall
        r = init_token({"type": "spass", "pin": "spass"}, user=User(
            login="frank", realm="ldaprealm"))
        self.assertTrue(r)
        self.assertEqual("{0!s}".format(r.user), "<frank.catchall@ldaprealm>")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "frank",
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

    @ldap3mock.activate
    def test_03_classic_policies(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)

        # This policy will not match, since frank is in resolver "catchall".
        set_policy(name="HOTPonly",
                   action="tokentype=spass",
                   scope=SCOPE.AUTHZ,
                   resolver="sales")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "frank",
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        # If users in resolver sales are required to use HOTP, then frank still
        # can login with a SPASS token, since he is identified as user in
        # resolver catchall
        set_policy(name="HOTPonly",
                   action="tokentype=hotp",
                   scope=SCOPE.AUTHZ,
                   resolver="sales")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "frank",
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # Alice - not in sales - is allowed to login
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "alice",
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

    def test_04_testing_token_with_setrealm(self):
        """
        When testing a token in the UI, the following request is triggered.
        https://privacyidea/validate/check
        serial=PISM1234
        pass=1234

        If we have a setrealm policy, this request is triggered:
        https://privacyidea/validate/check
        serial=PISM1234
        pass=1234
        realm=newrealm
        """
        init_token({"serial": "SPASS_04", "type": "spass", "pin": "1234"})

        set_policy(name="pol_setrealm_01",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}={1!s}".format(PolicyAction.SETREALM, self.realm1))

        # Successfully test the token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "SPASS_04",
                                                 "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        delete_policy("pol_setrealm_01")
        remove_token("SPASS_04")

    def test_05_is_authorized(self):
        set_policy(name="auth01", scope=SCOPE.AUTHZ, priority=2,
                   action="{0!s}={1!s}".format(PolicyAction.AUTHORIZED, AUTHORIZED.DENY))
        set_policy(name="auth02", scope=SCOPE.AUTHZ, user="frank", priority=1,
                   action="{0!s}={1!s}".format(PolicyAction.AUTHORIZED, AUTHORIZED.ALLOW))

        # The user frank actually has a spass token and is authorized to authenticate by policy auth02
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "frank",
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(result.get("authentication"), "ACCEPT")

        delete_policy("auth02")

        # If his personal policy is removed, he can not authenticate anymore
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "frank",
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertIn("error", result)
            self.assertEqual(result.get("error").get("message"),
                             "ERR401: User is not authorized to authenticate under these conditions.")

        delete_policy("auth01")
