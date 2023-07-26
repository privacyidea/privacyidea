# -*- coding: utf-8 -*-
import logging
from testfixtures import log_capture
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from privacyidea.lib.utils import to_unicode
from urllib.parse import urlencode, quote
import json
from privacyidea.lib.tokens.pushtoken import PUSH_ACTION, strip_key
from privacyidea.lib.utils import hexlify_and_unicode
from .base import MyApiTestCase
from privacyidea.lib.user import (User)
from privacyidea.lib.tokens.totptoken import HotpTokenClass
from privacyidea.lib.tokens.yubikeytoken import YubikeyTokenClass
from privacyidea.lib.tokens.registrationtoken import RegistrationTokenClass
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.models import (Token, Policy, Challenge, AuthCache, db, TokenOwner)
from privacyidea.lib.authcache import _hash_password
from privacyidea.lib.config import (set_privacyidea_config,
                                    get_inc_fail_count_on_false_pin,
                                    delete_privacyidea_config)
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   reset_token, enable_token, revoke_token,
                                   set_pin, get_one_token)
from privacyidea.lib.policy import SCOPE, ACTION, set_policy, delete_policy, AUTHORIZED
from privacyidea.lib.event import set_event
from privacyidea.lib.event import delete_event
from privacyidea.lib.error import ERROR
from privacyidea.lib.resolver import save_resolver, get_resolver_list, delete_resolver
from privacyidea.lib.realm import set_realm, set_default_realm, delete_realm
from privacyidea.lib.radiusserver import add_radius
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.tokens.webauthn import webauthn_b64_decode
from privacyidea.lib.tokens.registrationtoken import DEFAULT_LENGTH as DEFAULT_LENGTH_REG
from privacyidea.lib.tokens.passwordtoken import DEFAULT_LENGTH as DEFAULT_LENGTH_PW
from privacyidea.lib.tokenclass import ROLLOUTSTATE, CLIENTMODE
from privacyidea.lib import _
from passlib.hash import argon2
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway

from testfixtures import Replace, test_datetime
import datetime
import time
import responses
import mock
from . import smtpmock, ldap3mock, radiusmock


PWFILE = "tests/testdata/passwords"
HOSTSFILE = "tests/testdata/hosts"
DICT_FILE="tests/testdata/dictionary"

LDAPDirectory = [{"dn": "cn=alice,ou=example,o=test",
                 "attributes": {'cn': 'alice',
                                "sn": "Cooper",
                                "givenName": "Alice",
                                'userPassword': 'alicepw',
                                'oid': "2",
                                "homeDirectory": "/home/alice",
                                "email": "alice@test.com",
                                "memberOf": ["cn=admins,o=test", "cn=users,o=test"],
                                "accountExpires": 131024988000000000,
                                "objectGUID": '\xef6\x9b\x03\xc0\xe7\xf3B'
                                              '\x9b\xf9\xcajl\rM1',
                                'mobile': ["1234", "45678"]}},
                {"dn": 'cn=bob,ou=example,o=test',
                 "attributes": {'cn': 'bob',
                                "sn": "Marley",
                                "givenName": "Robert",
                                "email": "bob@example.com",
                                "memberOf": ["cn=users,o=test"],
                                "mobile": "123456",
                                "homeDirectory": "/home/bob",
                                'userPassword': 'bobpwééé',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": '\xef6\x9b\x03\xc0\xe7\xf3B'
                                              '\x9b\xf9\xcajl\rMw',
                                'oid': "3"}},
                {"dn": 'cn=manager,ou=example,o=test',
                 "attributes": {'cn': 'manager',
                                "givenName": "Corny",
                                "sn": "keule",
                                "email": "ck@o",
                                "memberOf": ["cn=helpdesk,o=test", "cn=users,o=test"],
                                "mobile": "123354",
                                'userPassword': 'ldaptest',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": '\xef6\x9b\x03\xc0\xe7\xf3B'
                                              '\x9b\xf9\xcajl\rMT',
                                'oid': "1"}},
                {"dn": 'cn=frank,ou=sales,o=test',
                 "attributes": {'cn': 'frank',
                                "givenName": "Frank",
                                "sn": "Hause",
                                "email": "fh@o",
                                "memberOf": ["cn=users,o=test"],
                                "mobile": "123354",
                                'userPassword': 'ldaptest',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": '\xef7\x9b\x03\xc0\xe7\xf3B'
                                              '\x9b\xf9\xcajl\rMT',
                                'oid': "5"}}
                 ]


OTPs = ["755224",
        "287082",
        "359152",
        "969429",
        "338314",
        "254676",
        "287922",
        "162583",
        "399871",
        "520489"]


class AuthorizationPolicyTestCase(MyApiTestCase):
    """
    This tests the catch all resolvers and resolvers which also contain the
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
        r = set_realm("ldaprealm", resolvers=["catchall", "sales"],
                      priority={"catchall": 2, "sales": 1})
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
        r = set_realm("ldaprealm", resolvers=["catchall", "sales"],
                      priority={"catchall": 1, "sales": 2})
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
                   action="{0!s}={1!s}".format(ACTION.SETREALM, self.realm1))

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
                   action="{0!s}={1!s}".format(ACTION.AUTHORIZED, AUTHORIZED.DENY))
        set_policy(name="auth02", scope=SCOPE.AUTHZ, user="frank", priority=1,
                   action="{0!s}={1!s}".format(ACTION.AUTHORIZED, AUTHORIZED.ALLOW))

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
                                                 "transcation_id":
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


def setup_sms_gateway():
    post_url = "http://smsgateway.com/sms_send_api.cgi"
    success_body = "ID 12345"

    identifier = "myGW"
    provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider" \
                      ".HttpSMSProvider"
    id = set_smsgateway(identifier, provider_module, description="test",
                        options={"HTTP_METHOD": "POST",
                                 "URL": post_url,
                                 "RETURN_SUCCESS": "ID",
                                 "text": "{otp}",
                                 "phone": "{phone}"})
    assert (id > 0)
    # set config sms.identifier = myGW
    r = set_privacyidea_config("sms.identifier", identifier)
    assert (r in ["insert", "update"])
    responses.add(responses.POST,
                  post_url,
                  body=success_body)


class AValidateOfflineTestCase(MyApiTestCase):
    """
    Test api.validate endpoints that are responsible for offline auth.
    """

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
        pass
        # create offline app
        #tokenobj = get_tokens(self.serials[0])[0]
        from privacyidea.lib.applications.offline import REFILLTOKEN_LENGTH
        from privacyidea.lib.machine import attach_token, detach_token
        from privacyidea.lib.machineresolver import save_resolver, delete_resolver
        mr_obj = save_resolver({"name": "testresolver",
                                "type": "hosts",
                                "filename": HOSTSFILE,
                                "type.filename": "string",
                                "desc.filename": "the filename with the "
                                                 "hosts",
                                "pw": "secret",
                                "type.pw": "password"})
        self.assertTrue(mr_obj > 0)
        # Attach the offline app to pippin
        r = attach_token(self.serials[0], "offline", hostname="pippin",
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

        # Detach the token, refill should then fail
        r = detach_token(self.serials[0], "offline", "pippin")
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


class ValidateAPITestCase(MyApiTestCase):
    """
    test the api.validate endpoints
    """

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

    def test_02_validate_check(self):
        # is the token still assigned?
        tokenbject_list = get_tokens(serial=self.serials[0])
        tokenobject = tokenbject_list[0]
        self.assertEqual(tokenobject.token.first_owner.user_id, "1000")

        """                  Truncated
           Count    Hexadecimal    Decimal        HOTP
           0        4c93cf18       1284755224     755224
           1        41397eea       1094287082     287082
           2         82fef30        137359152     359152
           3        66ef7655       1726969429     969429
           4        61c5938a       1640338314     338314
           5        33c083d4        868254676     254676
           6        7256c032       1918287922     287922
           7         4e5b397         82162583     162583
           8        2823443f        673399871     399871
           9        2679dc69        645520489     520489
        """
        # test for missing parameter user
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # test for missing parameter serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # test for missing parameter "pass"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_03_check_user(self):
        # get the original counter
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_1 = hotp_tokenobject.token.count

        # test successful authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("otplen"), 6)
            # check if serial has been added to g
            self.assertTrue(self.app_context.g.serial, detail["serial"])

        # Check that the counter is increased!
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_2 = hotp_tokenobject.token.count
        self.assertTrue(count_2 > count_1, (hotp_tokenobject.token.serial,
                                            hotp_tokenobject.token.count,
                                            count_1,
                                            count_2))

        # test authentication fails with the same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            # This is the same OTP value, so we get the "previous otp value" message
            detail = res.json.get("detail")
            self.assertIn("previous otp used again", detail.get("message"))

    def test_03a_check_user_get(self):
        # Reset the counter!
        count_1 = 0
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        hotp_tokenobject.token.count = count_1
        hotp_tokenobject.token.save()

        # test successful authentication
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string=urlencode(
                                                    {"user": "cornelius",
                                                     "pass": "pin287082"})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("otplen"), 6)

        # Check that the counter is increased!
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_2 = hotp_tokenobject.token.count
        self.assertTrue(count_2 > count_1, (hotp_tokenobject.token.serial,
                                            hotp_tokenobject.token.count,
                                            count_1,
                                            count_2))

        # test authentication fails with the same OTP
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string=urlencode(
                                                    {"user": "cornelius",
                                                     "pass": "pin287082"})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)

    def test_04_check_serial(self):
        # test authentication successful with serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)

        # test authentication fails with serial with same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            details = res.json.get("detail")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            self.assertEqual(details.get("message"), "wrong otp value. "
                                                     "previous otp used again")

    def test_05_check_serial_with_no_user(self):
        # Check a token per serial when the token has no user assigned.
        init_token({"serial": "nouser",
                    "otpkey": self.otpkey,
                    "pin": "pin"})
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "nouser",
                                                 "pass": "pin359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            details = res.json.get("detail")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

    def test_05a_check_otp_only(self):
        # Check the OTP of the token without PIN
        init_token({"serial": "otponly",
                    "otpkey": self.otpkey,
                    "pin": "pin"})
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "otponly",
                                                 "otponly": "1",
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

    def test_06_fail_counter(self):
        # test if a user has several tokens that the fail counter is increased
        # reset the failcounter
        reset_token(serial="SE1")
        init_token({"serial": "s2",
                    "genkey": 1,
                    "pin": "test"}, user=User("cornelius", self.realm1))
        init_token({"serial": "s3",
                    "genkey": 1,
                    "pin": "test"}, user=User("cornelius", self.realm1))
        # Now the user cornelius has 3 tokens.
        # SE1 with pin "pin"
        # token s2 with pin "test" and
        # token s3 with pin "test".

        self.assertTrue(get_inc_fail_count_on_false_pin())
        # We give an OTP PIN that does not match any token.
        # The failcounter of all tokens will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "XXXX123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            # if there is NO matching token, g.serial is set to None
            self.assertTrue(self.app_context.g.serial is None)

        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 1)

        # Now we give the matching OTP PIN of one token.
        # Only one failcounter will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(detail.get("serial"), "SE1")
            self.assertEqual(detail.get("message"), "wrong otp value")

        # Only the failcounter of SE1 (the PIN matching token) is increased!
        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 2)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 1)

        set_privacyidea_config("IncFailCountOnFalsePin", False)
        self.assertFalse(get_inc_fail_count_on_false_pin())
        reset_token(serial="SE1")
        reset_token(serial="s2")
        reset_token(serial="s3")
        # If we try to authenticate with an OTP PIN that does not match any
        # token NO failcounter is increased!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "XXXX123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))

        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 0)

        # Now we give the matching OTP PIN of one token.
        # Only one failcounter will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(detail.get("serial"), "SE1")
            self.assertEqual(detail.get("message"), "wrong otp value")

        # Only the failcounter of SE1 (the PIN matching token) is increased!
        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 0)

    def test_07_authentication_counter_exceeded(self):
        token_obj = init_token({"serial": "pass1", "pin": "123456",
                                "type": "spass"})
        token_obj.set_count_auth_max(5)

        for i in range(0, 5):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"serial": "pass1",
                                                     "pass": "123456"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertEqual(result.get("value"), True)

        # The 6th authentication will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass1",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), False)
            self.assertTrue("Authentication counter exceeded"
                            in detail.get("message"))

    def test_08_failcounter_counter_exceeded(self):
        token_obj = init_token({"serial": "pass2", "pin": "123456",
                                "type": "spass"})
        token_obj.set_maxfail(5)
        token_obj.set_failcount(5)
        # a valid authentication will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass2",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), False)
            self.assertEqual(detail.get("message"), "matching 1 tokens, "
                                                    "Failcounter exceeded")

    def test_10_saml_check(self):
        # test successful authentication
        set_privacyidea_config("ReturnSamlAttributes", "0")
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin338314"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), True)
            # No SAML return attributes
            self.assertEqual(attributes.get("email"), None)

        set_privacyidea_config("ReturnSamlAttributes", "1")

        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin254676"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), True)
            self.assertEqual(attributes.get("email"),
                             "user@localhost.localdomain")
            self.assertEqual(attributes.get("givenname"), "Cornelius")
            self.assertEqual(attributes.get("mobile"), "+491111111")
            self.assertEqual(attributes.get("phone"),  "+491234566")
            self.assertEqual(attributes.get("realm"),  "realm1")
            self.assertEqual(attributes.get("username"),  "cornelius")

        # Return SAML attributes On Fail
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin254676"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), False)
            self.assertEqual(attributes.get("email"), None)
            self.assertEqual(attributes.get("givenname"), None)
            self.assertEqual(attributes.get("mobile"), None)
            self.assertEqual(attributes.get("phone"), None)
            self.assertEqual(attributes.get("realm"), None)
            self.assertEqual(attributes.get("username"), None)

        set_privacyidea_config("ReturnSamlAttributesOnFail", "1")
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin254676"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), False)
            self.assertEqual(attributes.get("email"),
                             "user@localhost.localdomain")
            self.assertEqual(attributes.get("givenname"), "Cornelius")
            self.assertEqual(attributes.get("mobile"), "+491111111")
            self.assertEqual(attributes.get("phone"), "+491234566")
            self.assertEqual(attributes.get("realm"), "realm1")
            self.assertEqual(attributes.get("username"), "cornelius")

    def test_11_challenge_response_hotp(self):
        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        db_token = Token(serial, tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)
        # Set the failcounter
        token.set_failcount(5)

        # try to do challenge response without a policy. It will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("wrong otp pin"))
            self.assertNotIn("transaction_id", detail)

        # set a chalresp policy for HOTP
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action':
                                                     "challenge_response=hotp",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("please enter otp: "))
            transaction_id = detail.get("transaction_id")
        self.assertEqual(token.get_failcount(), 5)

        # send the OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("value"))

        self.assertEqual(token.get_failcount(), 0)
        # delete the token
        remove_token(serial=serial)

    def test_11a_challenge_response_registration(self):
        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        db_token = Token(serial, tokentype="registration", otpkey="regcode")
        db_token.save()
        token = RegistrationTokenClass(db_token)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)

        # try to do challenge response without a policy. It will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("wrong otp pin"))
            self.assertNotIn("transaction_id", detail)

        # set a chalresp policy for Registration Token
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action':
                                                     "challenge_response=registration",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("please enter otp: "))
            transaction_id = detail.get("transaction_id")

        # use the regcode to authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id,
                                                 "pass": "regcode"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # check, that the tokenowner table does not contain a NULL entry
        r = db.session.query(TokenOwner).filter(TokenOwner.token_id == None).first()
        self.assertIsNone(r)

        # delete the policy
        delete_policy("pol_chal_resp")

    def test_11b_challenge_response_multiple_hotp_failcounters(self):
        # Check behavior of Challenge-Response with multiple tokens
        # set a chalresp policy for HOTP
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action':
                                                     "challenge_response=hotp",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertGreaterEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        chalresp_serials = ["CHALRESP1", "CHALRESP2"]
        chalresp_pins = ["chalresp1", "chalresp2"]
        tokens = []

        # create two C/R tokens with different PINs for the same user
        for serial, pin in zip(chalresp_serials, chalresp_pins):
            # create a token and assign to the user
            db_token = Token(serial, tokentype="hotp")
            db_token.update_otpkey(self.otpkey)
            db_token.save()
            token = HotpTokenClass(db_token)
            token.add_user(User("cornelius", self.realm1))
            token.set_pin(pin)
            # Set the failcounter
            token.set_failcount(5)
            tokens.append(token)

        # create a challenge for the first token by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": chalresp_pins[0]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("please enter otp: "))
            transaction_id = detail.get("transaction_id")

        # Failcounters are unchanged
        self.assertEqual(tokens[0].get_failcount(), 5)
        self.assertEqual(tokens[1].get_failcount(), 5)

        # send an incorrect OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "111111"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))

        # Failcounter for the first token is increased
        # Failcounter for the second token is unchanged
        self.assertEqual(tokens[0].get_failcount(), 6)
        self.assertEqual(tokens[1].get_failcount(), 5)

        # send the correct OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("value"))

        # Failcounter for the first token is reset
        # Failcounter for the second token is unchanged
        self.assertEqual(tokens[0].get_failcount(), 0)
        self.assertEqual(tokens[1].get_failcount(), 5)

        # Set the same failcount for both tokens
        tokens[0].set_failcount(5)

        # trigger a challenge for both tokens
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")

        # send an incorrect OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "111111"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))

        # Failcounter for both tokens are increased
        self.assertEqual(tokens[0].get_failcount(), 6)
        self.assertEqual(tokens[1].get_failcount(), 6)

        # delete the tokens
        for serial in chalresp_serials:
            remove_token(serial=serial)

    def test_11c_challenge_response_timezone(self):
        # Since we write the challenge timestamps in UTC there is no easy way
        # to test servers in different timezones with mocking.
        # We would need to verify some timestamp the server emits in local time.
        self.setUp_user_realms()
        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        init_token({'serial': serial,
                    'type': 'hotp',
                    'otpkey': self.otpkey,
                    'pin': pin},
                   user=User("cornelius", self.realm1))

        # set a chalresp policy for HOTP
        pol = Policy('pol_chal_resp_tz', action='challenge_response=hotp',
                     scope='authentication', realm='', active=True)
        pol.save()

        # create the challenge by authenticating with the OTP PIN
        with Replace('privacyidea.models.datetime',
                     test_datetime(2020, 6, 13, 1, 2, 3,
                                   tzinfo=datetime.timezone(datetime.timedelta(hours=+5)))):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "pass": pin}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                detail = res.json.get("detail")
                self.assertFalse(result.get("value"))
                self.assertEqual(detail.get("message"), _("please enter otp: "))
                transaction_id = detail.get("transaction_id")

        # send the OTP value while being an hour too early (timezone +1)
        # This should not happen unless there is a server misconfiguration
        # The transaction should not be removed by the janitor
        with Replace('privacyidea.models.datetime',
                     test_datetime(2020, 6, 13, 1, 2, 4,
                                   tzinfo=datetime.timezone(datetime.timedelta(hours=+6)))):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "transaction_id": transaction_id,
                                                     "pass": "755224"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertFalse(result.get("value"))

        # send the OTP value while being an hour too late (timezone -1)
        with Replace('privacyidea.models.datetime',
                     test_datetime(2020, 6, 13, 1, 2, 4,
                                   tzinfo=datetime.timezone(datetime.timedelta(hours=+1)))):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "transaction_id": transaction_id,
                                                     "pass": "755224"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertFalse(result.get("value"))

        # check that the challenge is removed
        self.assertFalse(get_challenges(transaction_id=transaction_id))

        # delete the token
        remove_token(serial=serial)
        pol.delete()

    def test_12_challenge_response_sms(self):
        # set a chalresp policy for SMS
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action':
                                                     "challenge_response=sms",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertGreaterEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        serial = "CHALRESP2"
        pin = "chalresp2"
        # create a token and assign to the user
        init_token({"serial": serial,
                    "type": "sms",
                    "otpkey": self.otpkey,
                    "phone": "123456",
                    "pin": pin}, user=User("cornelius", self.realm1))
        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertTrue("The PIN was correct, "
                            "but the SMS could not be sent" in
                            detail.get("message"))
            transaction_id = detail.get("transaction_id")

        # disable the token. The detail->message should be empty
        r = enable_token(serial=serial, enable=False)
        self.assertEqual(r, True)
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"),
                             "No active challenge response token found")

        # delete the token
        remove_token(serial=serial)

    @smtpmock.activate
    def test_13_challenge_response_email(self):
        smtpmock.setdata(response={"hans@dampf.com": (200, 'OK')})
        # set a chalresp policy for Email
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action':
                                                     "challenge_response=email",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertGreaterEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        serial = "CHALRESP3"
        pin = "chalresp3"
        # create a token and assign to the user
        init_token({"serial": serial,
                    "type": "email",
                    "otpkey": self.otpkey,
                    "email": "hans@dampf.com",
                    "pin": pin}, user=User("cornelius", self.realm1))
        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("Enter the OTP from the Email:"))
            transaction_id = detail.get("transaction_id")

        # send the OTP value
        # Test with parameter state.
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "state":
                                                     transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("value"))

        # delete the token
        remove_token(serial=serial)

    def test_14_check_validity_period(self):
        serial = "VP001"
        password = serial
        init_token({"serial": serial,
                    "type": "spass",
                    "pin": password}, user=User("cornelius", self.realm1))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Set validity period
        token_obj = get_tokens(serial=serial)[0]
        token_obj.set_validity_period_end("2015-01-01T10:00+0200")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value"))
            details = res.json.get("detail")
            self.assertTrue("Outside validity period" in details.get("message"))

        token_obj.set_validity_period_end("1999-01-01T10:00+0200")
        token_obj.set_validity_period_start("1998-01-01T10:00+0200")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value"))
            details = res.json.get("detail")
            self.assertTrue("Outside validity period" in details.get("message"))

        # delete the token
        remove_token(serial="VP001")

    def test_15_validate_at_sign(self):
        serial1 = "Split001"
        serial2 = "Split002"
        init_token({"serial": serial1,
                    "type": "spass",
                    "pin": serial1}, user=User("cornelius", self.realm1))

        init_token({"serial": serial2,
                    "type": "spass",
                    "pin": serial2}, user=User("cornelius", self.realm2))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": serial1}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        set_privacyidea_config("splitAtSign", "0")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@" + self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        set_privacyidea_config("splitAtSign", "1")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@" + self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Also test url-encoded parameters
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius%40" + self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # The default behaviour - if the config entry does not exist,
        # is to split the @Sign
        delete_privacyidea_config("splitAtSign")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@" + self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

    def test_16_autoresync_hotp(self):
        serial = "autosync1"
        token = init_token({"serial": serial,
                            "otpkey": self.otpkey,
                            "pin": "async"}, User("cornelius", self.realm2))
        set_privacyidea_config("AutoResync", True)
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8, is out of sync
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@" + self.realm2,
                                                 "pass": "async399871"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)

        # counter = 9, will be autosynced.
        # Authentication is successful
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@" + self.realm2,
                                                 "pass": "async520489"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_privacyidea_config("AutoResync")
        remove_token(serial)

    def test_16_autoresync_hotp_via_multichallenge(self):
        serial = "autosync1"
        token = init_token({"serial": serial,
                            "otpkey": self.otpkey,
                            "pin": "async"}, User("cornelius", self.realm2))
        set_privacyidea_config("AutoResync", True)
        set_policy(name="mcr_resync", scope=SCOPE.AUTH, action=ACTION.RESYNC_VIA_MULTICHALLENGE)
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8, is out of sync
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@" + self.realm2,
                                                 "pass": "async399871"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(detail.get('multi_challenge')[0].get("message"),
                             'To resync your token, please enter the next OTP value')
            self.assertEqual(result.get("value"), False)
            transaction_id = res.json.get("detail").get("transaction_id")
            self.assertTrue(transaction_id)

        # A false response will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                     "cornelius@" + self.realm2,
                                                 "transaction_id": transaction_id,
                                                 "pass": "520111"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertFalse(result.get("value"))

        # counter = 9, will be autosynced.
        # Authentication is successful
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@" + self.realm2,
                                                 "transaction_id": transaction_id,
                                                 "pass": "520489"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_privacyidea_config("AutoResync")
        remove_token(serial)
        delete_policy("mcr_resync")

    def test_17_auth_timelimit_success(self):
        user = User("timelimituser", realm=self.realm2)
        pin = "spass"
        # create a token
        token = init_token({"type": "spass",
                            "pin": pin}, user=user)

        # set policy for timelimit
        set_policy(name="pol_time1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=2/20s".format(ACTION.AUTHMAXSUCCESS))

        for i in [1, 2]:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "timelimituser",
                                                     "realm": self.realm2,
                                                     "pass": pin}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertEqual(result.get("value"), True)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)

        delete_policy("pol_time1")
        remove_token(token.token.serial)

    def test_18_auth_timelimit_fail(self):
        user = User("timelimituser", realm=self.realm2)
        pin = "spass"
        # create a token
        token = init_token({"type": "spass", "pin": pin}, user=user)

        # set policy for timelimit
        set_policy(name="pol_time1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=2/20s".format(ACTION.AUTHMAXFAIL))

        for i in [1, 2]:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "timelimituser",
                                                     "realm": self.realm2,
                                                     "pass": "wrongpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertEqual(result.get("value"), False)

        # Now we do the correct authentication, but
        # as already two authentications failed, this will fail, too
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 failed authentications per 0:00:20")

        delete_policy("pol_time1")
        remove_token(token.token.serial)

    def test_19_validate_passthru(self):
        # user passthru, realm: self.realm2, passwd: pthru
        set_policy(name="pthru", scope=SCOPE.AUTH, action=ACTION.PASSTHRU)

        # Passthru with GET request
        with self.app.test_request_context(
                '/validate/check',
                method='GET',
                query_string=urlencode({"user": "passthru",
                                        "realm": self.realm2,
                                        "pass": "pthru"})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        # Passthru with POST Request
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "passthru",
                                                 "realm": self.realm2,
                                                 "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        # Test if the policies "reset_all_tokens" and "passthru" work out fine at the same time
        set_policy(name="reset_all_tokens", scope=SCOPE.AUTH, action=ACTION.RESETALLTOKENS)
        # Passthru with POST Request
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "passthru",
                                                 "realm": self.realm2,
                                                 "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("reset_all_tokens")
        delete_policy("pthru")

    def test_20_questionnaire(self):
        pin = "pin"
        serial = "QUST1234"
        questions = {"frage1": "antwort1",
                     "frage2": "antwort2",
                     "frage3": "antwort3"}
        j_questions = json.dumps(questions)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "question",
                                                 "pin": pin,
                                                 "serial": serial,
                                                 "questions": j_questions},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        set_privacyidea_config("question.num_answers", 2)
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "question",
                                                 "pin": pin,
                                                 "serial": serial,
                                                 "questions": j_questions},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value, True)

        # Start a challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            question = detail.get("message")
            self.assertTrue(question in questions)

        # Respond to the challenge
        answer = questions[question]
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": answer}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

    def test_21_validate_disabled(self):
        # test a user with two tokens and otppin=userstore.
        # One token is disabled. But the user must be able to login with the
        # 2nd token
        # user disableduser, realm: self.realm2, passwd: superSecret
        set_policy(name="disabled",
                   scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, "userstore"))
        # enroll two tokens
        r = init_token({"type": "spass", "serial": "spass1d"},
                       user=User("disableduser", self.realm2))
        r = init_token({"type": "spass", "serial": "spass2d"},
                       user=User("disableduser", self.realm2))
        # disable first token
        r = enable_token("spass1d", False)
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the 2nd token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "disableduser",
                                                 "realm": self.realm2,
                                                 "pass": "superSecret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        # disable 2nd token
        r = enable_token("spass2d", False)
        r = enable_token("spass1d")
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the first token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "disableduser",
                                                 "realm": self.realm2,
                                                 "pass": "superSecret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("disabled")

    def test_22_validate_locked(self):
        # test a user with two tokens
        # One token is locked/revoked.
        #  But the user must be able to login with the 2nd token
        # user lockeduser, realm: self.realm2
        # enroll two tokens
        user = "lockeduser"
        set_policy(name="locked",
                   scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, "tokenpin"))
        r = init_token({"type": "spass", "serial": "spass1l",
                        "pin": "locked"},
                       user=User(user, self.realm2))
        r = init_token({"type": "spass", "serial": "spass2l",
                        "pin": "locked"},
                       user=User(user, self.realm2))
        # disable first token
        r = revoke_token("spass1l")
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the 2nd token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "pass": "locked"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        remove_token("spass1l")
        remove_token("spass2l")
        delete_policy("locked")

    def test_23_pass_no_user_and_pass_no_token(self):
        # Test with pass_no_user AND with pass_no_token.
        user = "passthru"
        user_no_token = "usernotoken"
        pin = "mypin"
        serial = "t23"
        set_policy(name="pass_no",
                   scope=SCOPE.AUTH,
                   action="{0!s},{1!s}".format(ACTION.PASSNOTOKEN,
                                               ACTION.PASSNOUSER))

        r = init_token({"type": "spass", "serial": serial,
                        "pin": pin}, user=User(user, self.realm2))
        self.assertTrue(r)

        r = get_tokens(user=User(user, self.realm2), count=True)
        self.assertEqual(r, 1)
        # User can authenticate with his SPASS token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("serial"), serial)

        # User that does not exist, can authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "doesNotExist",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             "user does not exist, accepted "
                             "due to 'pass_no'")

        # Creating a notification event. The non-existing user must
        # still be able to pass!
        eid = set_event("notify", event=["validate_check"], action="sendmail",
                  handlermodule="UserNotification", conditions={"token_locked": True})

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "doesNotExist",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             "user does not exist, accepted "
                             "due to 'pass_no'")

        delete_event(eid)

        r = get_tokens(user=User(user, self.realm2), count=True)
        self.assertEqual(r, 1)
        # User with no token can authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user_no_token,
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             "user has no token, "
                             "accepted due to 'pass_no'")

        r = get_tokens(user=User(user, self.realm2), count=True)
        self.assertEqual(r, 1)

        # user with wrong password fails to authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "pass": "wrongPiN"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             "wrong otp pin")

        delete_policy("pass_no")
        remove_token(serial)

        # User that does not exist, can NOT authenticate after removing the
        # policy
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "doesNotExist",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            detail = res.json.get("detail")
            self.assertEqual(detail, None)

    def test_23a_pass_no_user_resolver(self):
        # Now we set a policy, that a non existing user will authenticate
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="{0}, {1}, {2}, {3}=none".format(
                       ACTION.RESETALLTOKENS,
                       ACTION.PASSNOUSER,
                       ACTION.PASSNOTOKEN,
                       ACTION.OTPPIN
                   ),
                   realm=self.realm1)
        # Check that the non existing user MisterX is allowed to authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "MisterX",
                                                 "realm": self.realm1,
                                                 "pass": "secret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             'user does not exist, accepted due to \'pol1\'')
        delete_policy("pol1")

    @responses.activate
    def test_24_trigger_challenge(self):
        from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
        from privacyidea.lib.config import set_privacyidea_config
        setup_sms_gateway()

        self.setUp_user_realms()
        self.setUp_user_realm2()
        serial = "sms01"
        pin = "pin"
        user = "passthru"
        r = init_token({"type": "sms", "serial": serial,
                        "otpkey": self.otpkey,
                        "phone": "123456",
                        "pin": pin}, user=User(user, self.realm2))
        self.assertTrue(r)

        # Trigger challenge for serial number
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("messages")[0],
                             _("Enter the OTP from the SMS:"))
            transaction_id = detail.get("transaction_ids")[0]
            # check if serial has been added to g
            self.assertTrue(self.app_context.g.serial, detail["serial"])

        # Check authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        # Trigger challenge for user
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("messages")[0],
                             _("Enter the OTP from the SMS:"))
            transaction_id = detail.get("transaction_ids")[0]
            # check if serial has been added to g
            self.assertTrue(self.app_context.g.serial, detail["serial"])

        # Check authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        remove_token(serial)

    @smtpmock.activate
    def test_25_trigger_challenge_smtp(self):
        smtpmock.setdata(response={"hans@dampf.com": (200, 'OK')})
        from privacyidea.lib.tokens.emailtoken import EMAILACTION

        self.setUp_user_realms()
        self.setUp_user_realm2()
        serial = "smtp01"
        pin = "pin"
        user = "passthru"
        r = init_token({"type": "email", "serial": serial,
                        "otpkey": self.otpkey,
                        "email": "hans@dampf.com",
                        "pin": pin}, user=User(user, self.realm2))
        self.assertTrue(r)

        set_policy("emailtext", scope=SCOPE.AUTH,
                   action="{0!s}=Dein <otp>".format(EMAILACTION.EMAILTEXT))
        set_policy("emailsubject", scope=SCOPE.AUTH,
                   action="{0!s}=Dein OTP".format(EMAILACTION.EMAILSUBJECT))

        # Trigger challenge for serial number
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("messages")[0],
                             _("Enter the OTP from the Email:"))
            transaction_id = detail.get("transaction_ids")[0]
            # check the sent message
            sent_message = smtpmock.get_sent_message()
            self.assertTrue("RGVpbiAyODcwODI=" in sent_message)
            self.assertTrue("Subject: Dein OTP" in sent_message)

        remove_token(serial)
        delete_policy("emailtext")

    def test_26_multiple_challenge_response(self):
        # Test the challenges for multiple active tokens
        self.setUp_user_realms()
        OTPKE2 = "31323334353637383930313233343536373839AA"
        user = User("multichal", self.realm1)
        pin = "test49"
        token_a = init_token({"serial": "CR2A",
                              "type": "hotp",
                              "otpkey": OTPKE2,
                              "pin": pin}, user)
        token_b = init_token({"serial": "CR2B",
                              "type": "hotp",
                              "otpkey": self.otpkey,
                              "pin": pin}, user)
        set_policy("test49", scope=SCOPE.AUTH, action="{0!s}=hotp".format(
            ACTION.CHALLENGERESPONSE))
        # both tokens will be a valid challenge response token!

        transaction_id = None
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
            transaction_id = detail.get("transaction_id")
            multi_challenge = detail.get("multi_challenge")
            self.assertEqual(multi_challenge[0].get("serial"), "CR2A")
            self.assertEqual(transaction_id,
                             multi_challenge[0].get("transaction_id"))
            self.assertEqual("interactive", multi_challenge[0].get("client_mode"))
            self.assertEqual(transaction_id,
                             multi_challenge[1].get("transaction_id"))
            self.assertEqual(multi_challenge[1].get("serial"), "CR2B")
            self.assertEqual("interactive", multi_challenge[1].get("client_mode"))

        # There are two challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 2)

        # check that both serials appear in the audit log
        ae = self.find_most_recent_audit_entry(action='* /validate/check')
        self.assertEqual({"CR2A", "CR2B"}, set(ae.get('serial').split(',')), ae)

        # Check the second response to the challenge, the second step in
        # challenge response:

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "realm": self.realm1,
                                                 "pass": "287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(serial, "CR2B")

        # No challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 0)

        remove_token("CR2A")
        remove_token("CR2B")
        delete_policy("test49")

    def test_27_multiple_challenge_response_different_pin(self):
        # Test the challenges for multiple active tokens with different PINs
        # Test issue #649
        self.setUp_user_realms()
        OTPKE2 = "31323334353637383930313233343536373839AA"
        user = User("multichal", self.realm1)
        pinA = "testA"
        pinB = "testB"
        token_a = init_token({"serial": "CR2A",
                              "type": "hotp",
                              "otpkey": OTPKE2,
                              "pin": pinA}, user)
        token_b = init_token({"serial": "CR2B",
                              "type": "hotp",
                              "otpkey": self.otpkey,
                              "pin": pinB}, user)
        set_policy("test48", scope=SCOPE.AUTH, action="{0!s}=hotp".format(
            ACTION.CHALLENGERESPONSE))
        # both tokens will be a valid challenge response token!

        transaction_id = None
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "realm": self.realm1,
                                                 "pass": pinB}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            multi_challenge = detail.get("multi_challenge")
            self.assertEqual(multi_challenge[0].get("serial"), "CR2B")
            self.assertEqual(transaction_id,
                             multi_challenge[0].get("transaction_id"))
            self.assertEqual(len(multi_challenge), 1)

        # There is ONE challenge in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 1)

        # Check the second response to the challenge, the second step in
        # challenge response:

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "realm": self.realm1,
                                                 "pass": "287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(serial, "CR2B")

        # No challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 0)

        remove_token("CR2A")
        remove_token("CR2B")
        delete_policy("test48")

    def test_28_validate_radiuscheck(self):
        # setup a spass token
        token_obj = init_token({"serial": "pass3", "pin": "123456",
                                "type": "spass"})

        # test successful authentication
        with self.app.test_request_context('/validate/radiuscheck',
                                           method='POST',
                                           data={"serial": "pass3",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            # HTTP 204 status code signals a successful authentication
            self.assertEqual(res.status_code, 204)
            self.assertEqual(res.data, b'')

        # test authentication fails with wrong PIN
        with self.app.test_request_context('/validate/radiuscheck',
                                           method='POST',
                                           data={"serial": "pass3",
                                                 "pass": "wrong"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.data, b'')

        # test authentication fails with an unknown user
        # here, we get an ordinary JSON response
        with self.app.test_request_context('/validate/radiuscheck',
                                           method='POST',
                                           data={"user": "unknown",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))

    def test_29_several_CR_one_locked(self):
        # A user has several CR tokens. One of the tokens is locked.
        self.setUp_user_realms()
        user = User("multichal", self.realm1)
        pin = "test"
        token_a = init_token({"serial": "CR2A",
                              "type": "hotp",
                              "otpkey": self.otpkey,
                              "pin": pin}, user)
        token_b = init_token({"serial": "CR2B",
                              "type": "hotp",
                              "otpkey": self.otpkey,
                              "pin": pin}, user)
        set_policy("test48", scope=SCOPE.AUTH, action="{0!s}=hotp".format(
            ACTION.CHALLENGERESPONSE))
        # both tokens will be a valid challenge response token!

        # One token is locked
        revoke_token("CR2B")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "realm": self.realm1,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # This is a challene, the value is False
            self.assertEqual(result.get("value"), False)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(serial, "CR2A")
            # Only one challenge, the 2nd token was revoked.
            self.assertEqual(len(detail.get("multi_challenge")), 1)

        delete_policy("test48")
        remove_token("CR2A")
        remove_token("CR2B")

    def test_30_return_different_tokentypes(self):
        """
        Return different tokentypes

        If there are more than one matching tokens, the check_token_list in lib/token.py
        returns a tokentype:
        1. a specific tokentype if all matching tokens are of the same type
        2. an "undetermined" tokentype, if the matching tokens are of
           different type.
        """
        self.setUp_user_realms()
        user = User("cornelius", self.realm1)

        # Authenticate with PW token
        init_token({"serial": "PW1",
                    "type": "pw",
                    "otpkey": "123",
                    "pin": "hallo"}, user)
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("type"), "pw")
            # check if serial has been added to g
            self.assertEqual(self.app_context.g.serial, 'PW1')

        # two different token types result in "undetermined
        init_token({"serial": "SPASS1",
                    "type": "spass",
                    "pin": "hallo123"}, user)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("type"), "undetermined")
            # check if serial has been added to g
            self.assertTrue(self.app_context.g.serial is None)

        # Remove PW token, and authenticate with spass
        remove_token("PW1")
        init_token({"serial": "SPASS2",
                    "type": "spass",
                    "pin": "hallo123"}, user)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("type"), "spass")

        # A user has one HOTP token and two spass tokens.
        init_token({"serial": "HOTP1",
                    "type": "hotp",
                    "otpkey": self.otpkey,
                    "pin": "hallo"}, user)
        # Without policy he can authenticate with the spass token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("type"), "spass")

        # policy only allows HOTP.
        set_policy("onlyHOTP", scope=SCOPE.AUTHZ,
                   action="{0!s}=hotp".format(ACTION.TOKENTYPE))

        # He can not authenticate with the spass token!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), False)
            self.assertEqual(result.get("error").get("code"), ERROR.POLICY)
            detail = res.json.get("detail")
            self.assertEqual(detail, None)

        # Define a passthru policy
        set_policy("passthru", scope=SCOPE.AUTH,
                   action="{0!s}=userstore".format(ACTION.PASSTHRU))

        # A user with a passthru policy can authenticate, since he has not tokentype
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "passthru",
                                                 "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("onlyHOTP")
        delete_policy("passthru")
        remove_token("SPASS1")
        remove_token("SPASS2")
        remove_token("HOTP1")

    @responses.activate
    @smtpmock.activate
    def test_30_challenge_text(self):
        """
        Set a policy for a different challengetext and run a C/R for sms and email.
        :return:
        """
        smtpmock.setdata(response={"hallo@example.com": (200, 'OK')})

        # Configure the SMS Gateway
        setup_sms_gateway()
        from privacyidea.lib.config import set_privacyidea_config

        self.setUp_user_realms()
        user = User("cornelius", self.realm1)

        # two different token types
        init_token({"serial": "CHAL1",
                    "type": "sms",
                    "phone": "123456",
                    "pin": "sms"}, user)
        init_token({"serial": "CHAL2",
                    "type": "email",
                    "email": "hallo@example.com",
                    "pin": "email"}, user)

        set_policy("chalsms", SCOPE.AUTH, "sms_{0!s}=check your sms".format(ACTION.CHALLENGETEXT))
        set_policy("chalemail", SCOPE.AUTH, "email_{0!s}=check your email".format(ACTION.CHALLENGETEXT))

        # Challenge Response with email
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "email"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            resp = res.json
            self.assertEqual(resp.get("detail").get("message"), "check your email")

        # Challenge Response with SMS
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "sms"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            resp = res.json
            self.assertEqual(resp.get("detail").get("message"), "check your sms")

        # Two different token types that are triggered by the same PIN:
        init_token({"serial": "CHAL3",
                    "type": "sms",
                    "phone": "123456",
                    "pin": "PIN"}, user)
        init_token({"serial": "CHAL4",
                    "type": "email",
                    "email": "hallo@example.com",
                    "pin": "PIN"}, user)

        # Challenge Response with SMS and Email. The challenge message contains both hints
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "PIN"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            resp = res.json
            self.assertIn("check your sms", resp.get("detail").get("message"))
            self.assertIn("check your email", resp.get("detail").get("message"))

        delete_policy("chalsms")
        delete_policy("chalemail")
        remove_token("CHAL1")
        remove_token("CHAL2")
        remove_token("CHAL3")
        remove_token("CHAL4")

    def test_01_check_invalid_input(self):
        # Empty username
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": " ",
                                                 "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            error_msg = result.get("error").get("message")
            self.assertEqual("ERR905: You need to specify a serial or a user.", error_msg)

        # wrong username
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "h%h",
                                                 "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            error_msg = result.get("error").get("message")
            self.assertEqual("ERR905: Invalid user.", error_msg)

        # wrong serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "*",
                                                 "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            error_msg = result.get("error").get("message")
            self.assertEqual("ERR905: Invalid serial number.", error_msg)

    def test_31_count_auth(self):

        serial = "authcount001"
        tok = init_token({"serial": serial,
                          "type": "spass",
                          "pin": "spass"})
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        self.assertEqual(int(tok.get_tokeninfo("count_auth")), 1)

        set_privacyidea_config("no_auth_counter", "True")
        # Now an authentication does not increase the counter!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        self.assertEqual(int(tok.get_tokeninfo("count_auth")), 1)
        remove_token(serial)
        delete_privacyidea_config("no_auth_counter")

    @ldap3mock.activate
    def test_32_secondary_login_attribute(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # First we create an LDAP resolver
        rid = save_resolver({"resolver": "myLDAPres",
                             "type": "ldapresolver",
                             'LDAPURI': 'ldap://localhost',
                             'LDAPBASE': 'o=test',
                             'BINDDN': 'cn=manager,ou=example,o=test',
                             'BINDPW': 'ldaptest',
                             'LOGINNAMEATTRIBUTE': 'cn, sn',
                             'LDAPSEARCHFILTER': '(cn=*)',
                             'USERINFO': '{ "username": "cn",'
                                         '"phone" : "telephoneNumber", '
                                         '"mobile" : "mobile"'
                                         ', "email" : "mail", '
                                         '"surname" : "sn", '
                                         '"givenname" : "givenName" }',
                             'UIDTYPE': 'DN',
                             'CACHE_TIMEOUT': 0
                             })
        self.assertTrue(rid)
        added, failed = set_realm("tr", ["myLDAPres"])
        self.assertEqual(added, ["myLDAPres"])
        self.assertEqual(failed, [])

        params = {"type": "spass",
                  "pin": "spass"}
        init_token(params, User("alice", "tr"))

        # Alice Cooper is in the LDAP directory, but Cooper is the secondary login name
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "Cooper",
                                                 "realm": "tr",
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # Now check the audit!
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"action": "*check*", "user": "alice"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get("count"), 1)
            self.assertTrue("logged in as Cooper." in json_response.get("result").get("value").get("auditdata")[0].get("info"),
                            json_response.get("result").get("value").get("auditdata"))

        self.assertTrue(delete_realm("tr"))
        self.assertTrue(delete_resolver("myLDAPres"))

    def test_33_auth_cache(self):
        init_token({"otpkey": self.otpkey},
                   user=User("cornelius", self.realm1))
        set_policy(name="authcache", action="{0!s}=4m".format(ACTION.AUTH_CACHE), scope=SCOPE.AUTH)
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # Check that there is an entry with this OTP value in the auth_cache
        cached_auths = AuthCache.query.filter(AuthCache.username == "cornelius", AuthCache.realm == self.realm1).all()
        found = False
        for cached_auth in cached_auths:
            if argon2.verify(OTPs[1], cached_auth.authentication):
                found = True
                break
        self.assertTrue(found)

        # Authenticate again with the same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"), "Authenticated by AuthCache.")

        delete_policy("authcache")

        # If there is no policy authenticating again with the same OTP fails.
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"), "wrong otp value. previous otp used again")

        # If there is no authcache, the same value must not be used again!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # Check that there is no entry with this OTP value in the auth_cache
        r = AuthCache.query.filter(AuthCache.authentication == _hash_password(OTPs[2])).first()
        self.assertFalse(bool(r))

        # Authenticate again with the same OTP value will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))

    def test_34_validate_user_and_serial(self):
        # create a new token
        db_token = Token(self.serials[1], tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        self.assertEqual(token.token.serial, self.serials[1], token)
        # try to authenticate a given user with a given unassigned token serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": self.serials[1],
                                                 "pass": OTPs[3]}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)
            result = res.json['result']
            self.assertEqual(result['error']['message'],
                             "ERR905: Given serial does not belong to given user!",
                             result)

        # try to authenticate with a token assigned to a different user
        token.add_user(User("nönäscii", self.realm2))
        token.set_pin("pin")
        self.assertEqual(token.token.owners.first().user_id, "1116")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": self.serials[1],
                                                 "pass": OTPs[3]}):
            res = self.app.full_dispatch_request()
            result = res.json['result']
            self.assertEqual(result['error']['message'],
                             "ERR905: Given serial does not belong to given user!",
                             result)
            self.assertEqual(res.status_code, 400, res)

    def test_35_application_tokentype(self):
        # The user has two tokens
        r = init_token({"type": "hotp",
                        "genkey": 1,
                        "pin": "trigpin",
                        "serial": "tok_hotp"},
                       user=User("cornelius", self.realm1))
        r = init_token({"type": "totp",
                        "genkey": 1,
                        "pin": "trigpin",
                        "serial": "tok_totp"},
                       user=User("cornelius", self.realm1))
        # Hotp and totp are allowed for trigger challenge
        set_policy(name="pol_chalresp", scope=SCOPE.AUTH,
                   action="{0!s}=hot totp".format(ACTION.CHALLENGERESPONSE))

        # trigger a challenge for both tokens
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius", "type": "hotp"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")

        # check, that both challenges were triggered, although
        # the application tried to trigger only hotp
        triggered_serials = [item['serial'] for item in detail.get("multi_challenge")]
        self.assertTrue("tok_hotp" in triggered_serials and "tok_totp" in triggered_serials)

        # check that both serials appear in the audit log
        ae = self.find_most_recent_audit_entry(action='POST /validate/triggerchallenge')
        self.assertTrue({"tok_hotp", "tok_totp"}.issubset(set(ae.get('serial').split(','))), ae)

        # Set a policy, that the application is allowed to specify tokentype
        set_policy(name="pol_application_tokentype",
                   scope=SCOPE.AUTHZ,
                   action=ACTION.APPLICATION_TOKENTYPE)

        # Trigger another challenge for HOTP
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius", "type": "hotp"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")

        # check that only HOTP was triggered
        triggered_serials = [item['serial'] for item in detail.get("multi_challenge")]
        self.assertTrue("tok_hotp" in triggered_serials and "tok_totp" not in triggered_serials)

        # Delete tokens and policies
        remove_token("tok_hotp")
        remove_token("tok_totp")
        delete_policy("pol_chalresp")
        delete_policy("pol_application_tokentype")

    def test_36_authorize_by_tokeninfo_condition(self):

        init_token({"type": "spass", "serial": "softwareToken", "pin": "software1"},
                   tokenkind="software", user=User("cornelius", self.realm1))
        init_token({"type": "spass", "serial": "hardwareToken", "pin": "hardware1"},
                   tokenkind="hardware", user=User("cornelius", self.realm1))
        set_policy(name="always_deny_access", action="{0!s}=deny_access".format(ACTION.AUTHORIZED),
                   scope=SCOPE.AUTHZ, priority=100)
        # policy to allow tokens, condition is deactivated. All tokens will be authorized
        set_policy(name="allow_hardware_tokens", action="{0!s}=grant_access".format(ACTION.AUTHORIZED),
                   scope=SCOPE.AUTHZ, priority=1,
                   conditions=[("tokeninfo", "tokenkind", "equals", "hardware", False)])

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "software1"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "hardware1"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # activate condition, only hardware tokens will be authorized
        set_policy(name="allow_hardware_tokens",
                   conditions=[("tokeninfo", "tokenkind", "equals", "hardware", True)])

        # token with tokenkind = software is not authorized
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "software1"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            # User is not authorized under these conditions (tokenkind = software)
            self.assertEqual(result.get("error").get("code"), 401)
            self.assertFalse(result.get("status"))

        # token with tokenkind = hardware is authorized
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "hardware1"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # wrong password raises exception since the tokeninfo policy cannot be checked
        # because there is not token serial in the result
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "wrongpassword"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            # Policy has tokeninfo, but no token object available
            self.assertEqual(result.get("error").get("code"), 303)
            self.assertFalse(result.get("status"))

        delete_policy("always_deny_access")
        delete_policy("allow_hardware_tokens")
        remove_token("softwareToken")
        remove_token("hardwareToken")

    def test_03b_check_previous_otp_with_totp(self):
        token = init_token({"type": "totp",
                            "serial": "totp_previous",
                            "otpkey": self.otpkey},
                           user=User("cornelius", self.realm1))
        # get the OTP
        counter = token._time2counter(time.time(), timeStepping=30)
        otp_now = token._calc_otp(counter)

        # test successful authentication
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string=urlencode(
                                                    {"user": "cornelius",
                                                     "pass": otp_now})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # check the same OTP value again
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string=urlencode(
                                                    {"user": "cornelius",
                                                     "pass": otp_now})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            self.assertIn("previous otp used again", detail.get("message"))
        # clean up
        remove_token("totp_previous")


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
            self.assertEqual("matching 1 tokens, Outside validity period",
                             detail.get("message"), (detail, password))


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
        # The password token requires either an otpkey or genkey
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'pw'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code)
            data = res.json
            error = data.get("result").get("error")
            self.assertEqual(905, error.get("code"))
            self.assertEqual("ERR905: Missing parameter: 'otpkey'", error.get("message"), data)

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

    def test_02_application_specific_password_token(self):
        # The appl spec password token requires either an otpkey or genkey
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={'user': 'cornelius',
                                                 'type': 'applspec'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code)
            data = res.json
            error = data.get("result").get("error")
            self.assertEqual(905, error.get("code"))
            self.assertEqual("ERR905: Missing parameter: 'otpkey'", error.get("message"), data)

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
            self.assertEqual("ERR905: Missing parameter: 'service_id'", error.get("message"), data)

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


class WebAuthn(MyApiTestCase):

    username = "selfservice"
    pin = "webauthnpin"
    serial = "WAN0001D434"

    def setUp(self):
        # Set up the WebAuthn Token from the lib test case
        super(MyApiTestCase, self).setUp()
        self.setUp_user_realms()

        set_policy("wan1", scope=SCOPE.ENROLL,
                   action="webauthn_relying_party_id=example.com")
        set_policy("wan2", scope=SCOPE.ENROLL,
                   action="webauthn_relying_party_name=example")

    def test_01_enroll_token_cumstom_description(self):
        client_data = "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoibmgwaUJ6MFNNbmRsVnNQUkdM" \
                      "dk9DUWMtUHByUHhPSmYzMEtlWm1UWFk5NCIsIm9yaWdpbiI6Imh0dHBzOi8vcGkuZXhhbXBsZS5jb" \
                      "20iLCJjcm9zc09yaWdpbiI6ZmFsc2V9"
        regdata = """o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEgwRgIhANAt-cBR3mZglj13PZPXA3srJYxX
↵J6v-LzxAhmxZM7AsAiEAxu4gi8AiKOfyhU68HcIBHuIwgjBWJUlt4cIETWFYdetjeDVjgVkCwDCC
↵ArwwggGkoAMCAQICBAOt8BIwDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBS
↵b290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBa
↵MG0xCzAJBgNVBAYTAlNFMRIwEAYDVQQKDAlZdWJpY28gQUIxIjAgBgNVBAsMGUF1dGhlbnRpY2F0
↵b3IgQXR0ZXN0YXRpb24xJjAkBgNVBAMMHVl1YmljbyBVMkYgRUUgU2VyaWFsIDYxNzMwODM0MFkw
↵EwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEGZ6HnBYtt9w57kpCoEYWpbMJ_soJL3a-CUj5bW6VyuTM
↵Zc1UoFnPvcfJsxsrHWwYRHnCwGH0GKqVS1lqLBz6F6NsMGowIgYJKwYBBAGCxAoCBBUxLjMuNi4x
↵LjQuMS40MTQ4Mi4xLjcwEwYLKwYBBAGC5RwCAQEEBAMCBDAwIQYLKwYBBAGC5RwBAQQEEgQQ-iuZ
↵3J45QlePkkow0jxBGDAMBgNVHRMBAf8EAjAAMA0GCSqGSIb3DQEBCwUAA4IBAQAo67Nn_tHY8OKJ
↵68qf9tgHV8YOmuV8sXKMmxw4yru9hNkjfagxrCGUnw8t_Awxa_2xdbNuY6Iru1gOrcpSgNB5hA5a
↵HiVyYlo7-4dgM9v7IqlpyTi4nOFxNZQAoSUtlwKpEpPVRRnpYN0izoon6wXrfnm3UMAC_tkBa3Ee
↵ya10UBvZFMu-jtlXEoG3T0TrB3zmHssGq4WpclUmfujjmCv0PwyyGjgtI1655M5tspjEBUJQQCMr
↵K2HhDNcMYhW8A7fpQHG3DhLRxH-WZVou-Z1M5Vp_G0sf-RTuE22eYSBHFIhkaYiARDEWZTiJuGSG
↵2cnJ_7yThUU1abNFdEuMoLQ3aGF1dGhEYXRhWMSjeab27q-5pV43jBGANOJ1Hmgvq58tMKsT0hJV
↵hs4ZR0EAAAD4-iuZ3J45QlePkkow0jxBGABAkNhnmLSbmlUebUHbpXxU-zMfqtnIqT5y2E3sfQgW
↵wE1FlUGvPg_c4zNcIucBnQAN8qTHJ8clzq7v5oQnnJz7T6UBAgMmIAEhWCBARZY9ak9nT6EI-dwL
↵uj0TB5-XjlmAvivyWLi9WSI7pCJYIEJicw0LtP_hdy8yh6ANEUXBJsWtkGDci9DcN1rDG1tE"""
        # First enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "description": "my description",
                                                 "genkey": 1},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            webAuthnRequest = data.get("detail").get("webAuthnRegisterRequest")
            self.assertEqual("Please confirm with your WebAuthn token", webAuthnRequest.get("message"))
            transaction_id = webAuthnRequest.get("transaction_id")

        # We need to change the nonce in the challenge database to use our recorded WebAuthN enrollment data
        recorded_nonce = "nh0iBz0SMndlVsPRGLvOCQc-PprPxOJf30KeZmTXY94"
        recorded_nonce_hex = hexlify_and_unicode(webauthn_b64_decode(recorded_nonce))
        # Update the nonce in the challenge database.
        from privacyidea.lib.challenge import get_challenges
        chal = get_challenges(serial=self.serial, transaction_id=transaction_id)[0]
        chal.challenge = recorded_nonce_hex
        chal.save()

        # 2nd enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "transaction_id": transaction_id,
                                                 "clientdata": client_data,
                                                 "regdata": regdata},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual('my description',
                             data.get("detail").get("webAuthnRegisterResponse").get("subject"))

        # Test, if the token received the automatic description
        self.assertEqual(get_tokens(serial=self.serial)[0].token.description, "my description")
        remove_token(self.serial)

    def test_02_enroll_token(self):
        client_data = "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoibmgwaUJ6MFNNbmRsVnNQUkdM" \
                      "dk9DUWMtUHByUHhPSmYzMEtlWm1UWFk5NCIsIm9yaWdpbiI6Imh0dHBzOi8vcGkuZXhhbXBsZS5jb" \
                      "20iLCJjcm9zc09yaWdpbiI6ZmFsc2V9"
        regdata = """o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEgwRgIhANAt-cBR3mZglj13PZPXA3srJYxX
↵J6v-LzxAhmxZM7AsAiEAxu4gi8AiKOfyhU68HcIBHuIwgjBWJUlt4cIETWFYdetjeDVjgVkCwDCC
↵ArwwggGkoAMCAQICBAOt8BIwDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBS
↵b290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBa
↵MG0xCzAJBgNVBAYTAlNFMRIwEAYDVQQKDAlZdWJpY28gQUIxIjAgBgNVBAsMGUF1dGhlbnRpY2F0
↵b3IgQXR0ZXN0YXRpb24xJjAkBgNVBAMMHVl1YmljbyBVMkYgRUUgU2VyaWFsIDYxNzMwODM0MFkw
↵EwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEGZ6HnBYtt9w57kpCoEYWpbMJ_soJL3a-CUj5bW6VyuTM
↵Zc1UoFnPvcfJsxsrHWwYRHnCwGH0GKqVS1lqLBz6F6NsMGowIgYJKwYBBAGCxAoCBBUxLjMuNi4x
↵LjQuMS40MTQ4Mi4xLjcwEwYLKwYBBAGC5RwCAQEEBAMCBDAwIQYLKwYBBAGC5RwBAQQEEgQQ-iuZ
↵3J45QlePkkow0jxBGDAMBgNVHRMBAf8EAjAAMA0GCSqGSIb3DQEBCwUAA4IBAQAo67Nn_tHY8OKJ
↵68qf9tgHV8YOmuV8sXKMmxw4yru9hNkjfagxrCGUnw8t_Awxa_2xdbNuY6Iru1gOrcpSgNB5hA5a
↵HiVyYlo7-4dgM9v7IqlpyTi4nOFxNZQAoSUtlwKpEpPVRRnpYN0izoon6wXrfnm3UMAC_tkBa3Ee
↵ya10UBvZFMu-jtlXEoG3T0TrB3zmHssGq4WpclUmfujjmCv0PwyyGjgtI1655M5tspjEBUJQQCMr
↵K2HhDNcMYhW8A7fpQHG3DhLRxH-WZVou-Z1M5Vp_G0sf-RTuE22eYSBHFIhkaYiARDEWZTiJuGSG
↵2cnJ_7yThUU1abNFdEuMoLQ3aGF1dGhEYXRhWMSjeab27q-5pV43jBGANOJ1Hmgvq58tMKsT0hJV
↵hs4ZR0EAAAD4-iuZ3J45QlePkkow0jxBGABAkNhnmLSbmlUebUHbpXxU-zMfqtnIqT5y2E3sfQgW
↵wE1FlUGvPg_c4zNcIucBnQAN8qTHJ8clzq7v5oQnnJz7T6UBAgMmIAEhWCBARZY9ak9nT6EI-dwL
↵uj0TB5-XjlmAvivyWLi9WSI7pCJYIEJicw0LtP_hdy8yh6ANEUXBJsWtkGDci9DcN1rDG1tE"""
        # First enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "genkey": 1},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            webAuthnRequest = data.get("detail").get("webAuthnRegisterRequest")
            self.assertEqual("Please confirm with your WebAuthn token", webAuthnRequest.get("message"))
            transaction_id = webAuthnRequest.get("transaction_id")

        # We need to change the nonce in the challenge database to use our recorded WebAuthN enrollment data
        recorded_nonce = "nh0iBz0SMndlVsPRGLvOCQc-PprPxOJf30KeZmTXY94"
        recorded_nonce_hex = hexlify_and_unicode(webauthn_b64_decode(recorded_nonce))
        # Update the nonce in the challenge database.
        from privacyidea.lib.challenge import get_challenges
        chal = get_challenges(serial=self.serial, transaction_id=transaction_id)[0]
        chal.challenge = recorded_nonce_hex
        chal.save()

        # 2nd enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "transaction_id": transaction_id,
                                                 "clientdata": client_data,
                                                 "regdata": regdata},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual('Yubico U2F EE Serial 61730834',
                             data.get("detail").get("webAuthnRegisterResponse").get("subject"))

        # Test, if the token received the automatic description
        self.assertEqual(get_tokens(serial=self.serial)[0].token.description, "Yubico U2F EE Serial 61730834")

    def test_10_validate_check(self):
        # Run challenge request agsint /validate/check
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pass": self.pin},
                                           headers={"Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            self.assertTrue("transaction_id" in data.get("detail"))
            self.assertEqual(self.serial, data.get("detail").get("serial"))
            self.assertEqual("Please confirm with your WebAuthn token (Yubico U2F EE Serial 61730834)",
                             data.get("detail").get("message"))

    def test_11_trigger_challenge(self):
        # Run challenge request agsint /validate/triggerchallenge
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": self.username},
                                           headers={"Host": "pi.example.com",
                                                    "authorization": self.at,
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            data = res.json
            print(data)
            self.assertEqual(200, res.status_code)
            self.assertTrue("transaction_id" in data.get("detail"))
            self.assertEqual(self.serial, data.get("detail").get("serial"))
            self.assertEqual("Please confirm with your WebAuthn token (Yubico U2F EE Serial 61730834)",
                             data.get("detail").get("message"))

        remove_token(self.serial)

    def test_20_authenticate_with_token(self):
        # Ensure that a not readily enrolled WebAuthn token does not disturb the usage
        # of an HOTP token with challenge response.
        client_data = "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoibmgwaUJ6MFNNbmRsVnNQUkdM" \
                      "dk9DUWMtUHByUHhPSmYzMEtlWm1UWFk5NCIsIm9yaWdpbiI6Imh0dHBzOi8vcGkuZXhhbXBsZS5jb" \
                      "20iLCJjcm9zc09yaWdpbiI6ZmFsc2V9"
        regdata = """o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEgwRgIhANAt-cBR3mZglj13PZPXA3srJYxX
↵J6v-LzxAhmxZM7AsAiEAxu4gi8AiKOfyhU68HcIBHuIwgjBWJUlt4cIETWFYdetjeDVjgVkCwDCC
↵ArwwggGkoAMCAQICBAOt8BIwDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBS
↵b290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBa
↵MG0xCzAJBgNVBAYTAlNFMRIwEAYDVQQKDAlZdWJpY28gQUIxIjAgBgNVBAsMGUF1dGhlbnRpY2F0
↵b3IgQXR0ZXN0YXRpb24xJjAkBgNVBAMMHVl1YmljbyBVMkYgRUUgU2VyaWFsIDYxNzMwODM0MFkw
↵EwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEGZ6HnBYtt9w57kpCoEYWpbMJ_soJL3a-CUj5bW6VyuTM
↵Zc1UoFnPvcfJsxsrHWwYRHnCwGH0GKqVS1lqLBz6F6NsMGowIgYJKwYBBAGCxAoCBBUxLjMuNi4x
↵LjQuMS40MTQ4Mi4xLjcwEwYLKwYBBAGC5RwCAQEEBAMCBDAwIQYLKwYBBAGC5RwBAQQEEgQQ-iuZ
↵3J45QlePkkow0jxBGDAMBgNVHRMBAf8EAjAAMA0GCSqGSIb3DQEBCwUAA4IBAQAo67Nn_tHY8OKJ
↵68qf9tgHV8YOmuV8sXKMmxw4yru9hNkjfagxrCGUnw8t_Awxa_2xdbNuY6Iru1gOrcpSgNB5hA5a
↵HiVyYlo7-4dgM9v7IqlpyTi4nOFxNZQAoSUtlwKpEpPVRRnpYN0izoon6wXrfnm3UMAC_tkBa3Ee
↵ya10UBvZFMu-jtlXEoG3T0TrB3zmHssGq4WpclUmfujjmCv0PwyyGjgtI1655M5tspjEBUJQQCMr
↵K2HhDNcMYhW8A7fpQHG3DhLRxH-WZVou-Z1M5Vp_G0sf-RTuE22eYSBHFIhkaYiARDEWZTiJuGSG
↵2cnJ_7yThUU1abNFdEuMoLQ3aGF1dGhEYXRhWMSjeab27q-5pV43jBGANOJ1Hmgvq58tMKsT0hJV
↵hs4ZR0EAAAD4-iuZ3J45QlePkkow0jxBGABAkNhnmLSbmlUebUHbpXxU-zMfqtnIqT5y2E3sfQgW
↵wE1FlUGvPg_c4zNcIucBnQAN8qTHJ8clzq7v5oQnnJz7T6UBAgMmIAEhWCBARZY9ak9nT6EI-dwL
↵uj0TB5-XjlmAvivyWLi9WSI7pCJYIEJicw0LtP_hdy8yh6ANEUXBJsWtkGDci9DcN1rDG1tE"""
        # First enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "genkey": 1},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            webAuthnRequest = data.get("detail").get("webAuthnRegisterRequest")
            self.assertEqual("Please confirm with your WebAuthn token", webAuthnRequest.get("message"))
            transaction_id = webAuthnRequest.get("transaction_id")

        # The token is now in the client_wait rollout state. We do not do the 2nd enrollment step
        toks = get_tokens(serial=self.serial)
        self.assertEqual(ROLLOUTSTATE.CLIENTWAIT, toks[0].rollout_state)

        # Now we create the 2nd token of the user, an HOTP token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "otpkey": self.otpkey,
                                                 "type": "hotp",
                                                 "serial": "hotpX1"},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))
        # We need a policy for HOTP trigger challenge
        set_policy(name="trigpol", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        # Check if the challenge is triggered for the HOTP token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pass": self.pin},
                                           headers={"Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            transaction_id = data.get("detail").get("transaction_id")
            messages = data.get("detail").get("messages")
            # There is a working chal resp message for the HOTP token
            self.assertIn("please enter otp: ", messages)
            # The WebAuthn token died not work, so there is no challenge for this one
            self.assertIn("Token is not yet enrolled", messages)

        # Authenticate with HOTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.username,
                                                 "transaction_id": transaction_id,
                                                 "pass": self.valid_otp_values[0]},
                                           headers={"Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # check if the challenge is triggered for the HOTP token via triggerchallenge
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": self.username},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            transaction_id = data.get("detail").get("transaction_id")

        # Authenticate with HOTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.username,
                                                 "transaction_id": transaction_id,
                                                 "pass": self.valid_otp_values[1]},
                                           headers={"Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        delete_policy("trigpol")
        remove_token("hotpX1")
        remove_token(self.serial)


class MultiChallege(MyApiTestCase):

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
    smartphone_public_key_pem_urlsafe = strip_key(smartphone_public_key_pem).replace("+", "-").replace("/", "_")
    serial_push = "PIPU001"

    def setUp(self):
        self.setUp_user_realms()

    def test_00_pin_change_via_validate_chalresp(self):
        # Test PIN change after challenge response authentication
        # Create policy change pin on first use
        set_policy("first_use", scope=SCOPE.ENROLL, action=ACTION.CHANGE_PIN_FIRST_USE)
        set_policy("via_validate", scope=SCOPE.AUTH, action=ACTION.CHANGE_PIN_VIA_VALIDATE)
        set_policy("hotp_chalresp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))

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

    def test_01_pin_change_via_validate_single_shot(self):
        # Test PIN change after authentication with a single shot authentication
        # Create policy change pin on first use
        set_policy("first_use", scope=SCOPE.ENROLL, action=ACTION.CHANGE_PIN_FIRST_USE)
        set_policy("via_validate", scope=SCOPE.AUTH, action=ACTION.CHANGE_PIN_VIA_VALIDATE)
        set_policy("hotp_chalresp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))

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

    def test_02_challenge_text_header(self):
        # Test PIN change after authentication with a single shot authentication
        # Create policy change pin on first use
        set_policy("first_use", scope=SCOPE.ENROLL, action=ACTION.CHANGE_PIN_FIRST_USE)
        set_policy("via_validate", scope=SCOPE.AUTH, action=ACTION.CHANGE_PIN_VIA_VALIDATE)
        set_policy("hotp_chalresp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        challenge_header = "Choose one: <ul>"
        set_policy("challenge_header", scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(ACTION.CHALLENGETEXT_HEADER, challenge_header))

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
            # check that the challenge header is contained in the message
            self.assertEqual("{0!s}<li>Please enter a new PIN</li>\n".format(challenge_header),
                             details.get("message"))

        remove_token(self.serial)
        delete_policy("first_use")
        delete_policy("via_validate")
        delete_policy("hotp_chalresp")
        delete_policy("challenge_header")

    def test_03_preferred_client_mode(self):
        REGISTRATION_URL = "http://test/ttype/push"
        TTL = "10"

        # set policy
        from privacyidea.lib.tokens.pushtoken import POLL_ONLY
        set_policy("push2", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       PUSH_ACTION.FIREBASE_CONFIG, POLL_ONLY,
                       PUSH_ACTION.REGISTRATION_URL, REGISTRATION_URL,
                       PUSH_ACTION.TTL, TTL))

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
                   action="{0!s}=hotp totp, {1!s}=  poll   u2f   webauthn ".format(
                       ACTION.CHALLENGERESPONSE, ACTION.PREFERREDCLIENTMODE))

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
            ACTION.CHALLENGERESPONSE))

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
        set_policy("test49", scope=SCOPE.AUTH, action="{0!s}=hotp".format(
            ACTION.CHALLENGERESPONSE))
        # both tokens will be a valid challenge response token!
        set_policy("test", scope=SCOPE.AUTH, action="{0!s}=wrong, falsch, Chigau, sbagliato".format(
            ACTION.PREFERREDCLIENTMODE))

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


class AChallengeResponse(MyApiTestCase):

    serial = "hotp1"
    serial_email = "email1"
    serial_sms = "sms1"

    def setUp(self):
        self.setUp_user_realms()

    def test_01_challenge_response_token_deactivate(self):
        # New token for the user "selfservice"
        Token("hotp1", "hotp", otpkey=self.otpkey, userid=1004, resolver=self.resolvername1,
              realm=self.realm1).save()
        # Define HOTP token to be challenge response
        set_policy(name="pol_cr", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        set_pin(self.serial, "pin")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "CHALLENGE")
            detail = data.get("detail")
            self.assertTrue("enter otp" in detail.get("message"), detail.get("message"))
            transaction_id = detail.get("transaction_id")

        # Now we try to provide the OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": self.valid_otp_values[0],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "ACCEPT")

        # Now we send the challenge and then we disable the token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "CHALLENGE")
            detail = data.get("detail")
            self.assertTrue("enter otp" in detail.get("message"), detail.get("message"))
            transaction_id = detail.get("transaction_id")

        # disable the token
        enable_token(self.serial, False)

        # Now we try to provide the OTP value, but authentication must fail, since the token is disabled
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "REJECT")
            detail = data.get("detail")
            self.assertEqual(detail.get("message"), "Challenge matches, but token is not fit for challenge. Token is disabled")

        # The token is still disabled. We are checking, if we can do a challenge response
        # for a disabled token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "REJECT")
            detail = data.get("detail")
            self.assertTrue("No active challenge response" in detail.get("message"), detail.get("message"))

        delete_policy("pol_cr")

    @smtpmock.activate
    def test_02_two_challenge_response_tokens(self):
        smtpmock.setdata(response={"bla@example.com": (200, 'OK')})
        # We test two challenge response tokens. One is active, one is disabled.
        # Enroll an Email-Token to the user
        init_token(user=User("selfservice", self.realm1),
                   param={"serial": self.serial_email,
                          "type": "email",
                          "email": "bla@example.com",
                          "otpkey": self.otpkey})
        set_pin(self.serial_email, "pin")

        toks = get_tokens(user=User("selfservice", self.realm1))
        self.assertEqual(len(toks), 2)
        self.assertFalse(toks[0].token.active)
        self.assertTrue(toks[1].token.active)

        # Now we create a challenge with two tokens
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "CHALLENGE")
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email:", detail.get("message"))

        # Now test with triggerchallenge
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "selfservice"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            # Triggerchallenge returns the numbers of tokens in the "value
            self.assertEqual(data.get("result").get("value"), 1)
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email:", detail.get("messages")[0])
        remove_token(self.serial_email)

    @smtpmock.activate
    def test_03_two_challenges_from_one_email_token(self):
        set_privacyidea_config("email.concurrent_challenges", "True")
        smtpmock.setdata(response={"bla@example.com": (200, 'OK')})
        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an Email-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_email,
                          "type": "email",
                          "email": "bla@example.com",
                          "otpkey": self.otpkey})
        set_pin(self.serial_email, "pin")

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we create the first challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email:", detail.get("message"))
            transaction_id1 = detail.get("transaction_id")

        # Now we create the second challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email:", detail.get("message"))
            transaction_id2 = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id2,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        remove_token(self.serial_email)
        delete_privacyidea_config("email.concurrent_challenges")

    @smtpmock.activate
    def test_04_only_last_challenge_from_one_email_token(self):
        set_privacyidea_config("email.concurrent_challenges", "False")
        smtpmock.setdata(response={"bla@example.com": (200, 'OK')})
        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an Email-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_email,
                          "type": "email",
                          "email": "bla@example.com",
                          "otpkey": self.otpkey})
        set_pin(self.serial_email, "pin")

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we create the first challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email:", detail.get("message"))
            transaction_id1 = detail.get("transaction_id")

        # Now we create the second challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email:", detail.get("message"))
            transaction_id2 = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            # The first challenge will not authenticate anymore, since the OTP is not stored in the challenge data
            # and the token counter was increased
            self.assertFalse(data.get("result").get("value"))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id2,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        remove_token(self.serial_email)
        delete_privacyidea_config("email.concurrent_challenges")

    @responses.activate
    def test_05_two_challenges_from_one_sms_token(self):
        # Configure the SMS Gateway
        setup_sms_gateway()

        ### Now do the enrollment and authentication
        set_privacyidea_config("sms.concurrent_challenges", "True")
        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an SMS-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_sms,
                          "type": "sms",
                          "phone": "1234567",
                          "otpkey": self.otpkey})
        set_pin(self.serial_sms, "pin")

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we create the first challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Enter the OTP from the SMS:", detail.get("message"))
            transaction_id1 = detail.get("transaction_id")

        # Now we create the second challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Enter the OTP from the SMS:", detail.get("message"))
            transaction_id2 = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id2,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        remove_token(self.serial_sms)
        delete_privacyidea_config("sms.concurrent_challenges")

    @responses.activate
    def test_06_only_last_challenges_from_one_sms_token(self):
        # Configure the SMS Gateway
        setup_sms_gateway()

        ### Now do the enrollment and authentication
        try:
            delete_privacyidea_config("sms.concurrent_challenges")
        except AttributeError:
            pass

        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an SMS-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_sms,
                          "type": "sms",
                          "phone": "1234567",
                          "otpkey": self.otpkey})
        set_pin(self.serial_sms, "pin")

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we create the first challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Enter the OTP from the SMS:", detail.get("message"))
            transaction_id1 = detail.get("transaction_id")

        # Now we create the second challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Enter the OTP from the SMS:", detail.get("message"))
            transaction_id2 = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            # First OTP fails, since the counter increased
            self.assertFalse(data.get("result").get("value"))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id2,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            # Last value succeeds
            self.assertTrue(data.get("result").get("value"))

        remove_token(self.serial_sms)

    @responses.activate
    def test_07_disabled_sms_token_will_not_trigger_challenge(self):
        # Configure the SMS Gateway
        setup_sms_gateway()

        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an SMS-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_sms,
                          "type": "sms",
                          "phone": "1234567",
                          "otpkey": self.otpkey})
        set_pin(self.serial_sms, "pin")
        # disable the token
        enable_token(self.serial_sms, False)

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we try to create a challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("No active challenge response token found", detail.get("message"))

        remove_token(self.serial_sms)

    def test_08_challenge_text(self):
        # We create two HOTP tokens for the user as challenge response and run a
        # challenge response request with both tokens.
        set_policy(name="pol_header",
                   scope=SCOPE.AUTH,
                   action="{0!s}=These are your options:<ul>".format(ACTION.CHALLENGETEXT_HEADER))
        # Set a policy for the footer
        set_policy(name="pol_footer",
                   scope=SCOPE.AUTH,
                   action="{0!s}=</ul>.<b>Authenticate Now!</b>".format(ACTION.CHALLENGETEXT_FOOTER))
        # make HOTP a challenge response token
        set_policy(name="pol_hotp",
                   scope=SCOPE.AUTH,
                   action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))

        init_token({"serial": "tok1",
                    "otpkey": self.otpkey,
                    "pin": "pin"}, user=User("cornelius", self.realm1))
        init_token({"serial": "tok2",
                    "otpkey": self.otpkey,
                    "pin": "pin"}, user=User("cornelius", self.realm1))

        # Now we try to create a challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual(detail.get("message"),
                             'These are your options:<ul><li>please enter otp: </li>\n</ul>.<b>Authenticate Now!</b>')

        remove_token("tok1")
        remove_token("tok2")
        delete_policy("pol_header")
        delete_policy("pol_footer")
        delete_policy("pol_hotp")

    def test_09_challenge_response_inc_failcounter(self):
        # make HOTP a challenge response token
        set_policy(name="pol_hotp",
                   scope=SCOPE.AUTH,
                   action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        init_token({"serial": "tok1",
                    "otpkey": self.otpkey,
                    "pin": "pin"}, user=User("cornelius", self.realm1))

        # On token fails to challenge response
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            transaction_id = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "wrongOTP",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("tok1", detail.get("serial"))
            self.assertEqual("hotp", detail.get("type"))
            self.assertEqual("Response did not match the challenge.", detail.get("message"))

        init_token({"serial": "tok2",
                    "otpkey": self.otpkey,
                    "pin": "pin"}, user=User("cornelius", self.realm1))

        # Now, two tokens will not match
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            transaction_id = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "wrongOTP",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertTrue("serial" not in detail)
            self.assertEqual("Response did not match for 2 tokens.", detail.get("message"))

        # Now check the fail counters of the tokens
        self.assertEqual(2, get_one_token(serial="tok1").token.failcount)
        self.assertEqual(1, get_one_token(serial="tok2").token.failcount)

        remove_token("tok1")
        remove_token("tok2")
        delete_policy("pol_hotp")

    def test_10_unique_transaction_id(self):
        # Tokens should create a unique transaction id
        # The TiQR token changes the transaction id.

        # Assign token to user:
        r = init_token({"serial": "tok1", "type": "hotp", "otpkey": self.otpkey},
                       user=User("cornelius", self.realm1))
        self.assertTrue(r)
        r = init_token({"serial": "tok2", "type": "tiqr", "otpkey": self.otpkey},
                       user=User("cornelius", self.realm1))
        self.assertTrue(r)

        set_policy("chalresp", scope=SCOPE.AUTHZ, action="{0!s}=hotp".format(ACTION.TRIGGERCHALLENGE))

        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius"},
                                           headers={"authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertEqual(data.get("result").get("value"), 2)
            # The two challenges should be the same
            multichallenge = data.get("detail").get("multi_challenge")
            transaction_id = data.get("detail").get("transaction_id")
            self.assertEqual(multichallenge[0].get("transaction_id"), transaction_id)
            self.assertEqual(multichallenge[1].get("transaction_id"), transaction_id)

        delete_policy("chalresp")
        remove_token("tok1")
        remove_token("tok2")

    @radiusmock.activate
    def test_11_validate_radiustoken(self):
        # A RADIUS token with RADIUS challenge response
        # remove all tokens of user Cornelius
        user_obj = User("cornelius", self.realm1)
        remove_token(user=user_obj)

        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "serial": "rad1",
                            "radius.identifier": "myserver",
                            "radius.local_checkpin": False,
                            "radius.user": "nönäscii"},
                           user=user_obj)
        radiusmock.setdata(timeout=False, response=radiusmock.AccessChallenge)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "radiuspassword"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            transaction_id = data.get("detail").get("transaction_id")

        # Now we send the response to this request but the wrong response!
        radiusmock.setdata(timeout=False, response=radiusmock.AccessReject)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "wrongPW",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            t = data.get("detail").get("transaction_id")
            # No transaction_id
            self.assertIsNone(t)

        # Finally we succeed
        radiusmock.setdata(timeout=False, response=radiusmock.AccessAccept)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "correctPW",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))
            t = data.get("detail").get("transaction_id")
            # No transaction_id
            self.assertIsNone(t)

        # A second request tries to use the same transaction_id, but the RADIUS server
        # responds with a Reject
        radiusmock.setdata(timeout=False, response=radiusmock.AccessReject)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "correctPW",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))

        # And finally a single shot authentication, no chal resp, no transaction_id
        radiusmock.setdata(timeout=False, response=radiusmock.AccessAccept)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "correctPW"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))
        remove_token("rad1")

    def test_12_polltransaction(self):
        # Assign token to user:
        r = init_token({"serial": "tok1", "type": "hotp", "otpkey": self.otpkey},
                       user=User("cornelius", self.realm1))
        self.assertTrue(r)
        r = init_token({"serial": "tok2", "type": "tiqr", "otpkey": self.otpkey},
                       user=User("cornelius", self.realm1))
        self.assertTrue(r)

        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius"},
                                           headers={"authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertEqual(data.get("result").get("value"), 2)
            # The two challenges should be the same
            multichallenge = data.get("detail").get("multi_challenge")
            transaction_id = data.get("detail").get("transaction_id")
            self.assertEqual(multichallenge[0].get("transaction_id"), transaction_id)
            self.assertEqual(multichallenge[1].get("transaction_id"), transaction_id)

        # Check that serials are written to the audit log
        entry = self.find_most_recent_audit_entry(action="*/validate/triggerchallenge*")
        self.assertIn("tok1", entry["serial"])
        self.assertIn("tok2", entry["serial"])

        # add a really old expired challenge for tok1
        old_transaction_id = "1111111111"
        old_challenge = Challenge(serial="tok1", transaction_id=old_transaction_id, challenge="")
        old_challenge_timestamp = datetime.datetime.now() - datetime.timedelta(days=3)
        old_challenge.timestamp = old_challenge_timestamp
        old_challenge.expiration = old_challenge_timestamp + datetime.timedelta(minutes=120)
        old_challenge.save()

        # Check behavior of the polltransaction endpoint
        # POST is not allowed
        with self.app.test_request_context("/validate/polltransaction", method="POST"):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 405)

        # transaction_id is required
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           data={}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            self.assertFalse(res.json["result"]["status"])
            self.assertIn("Missing parameter: 'transaction_id'", res.json["result"]["error"]["message"])

        # wildcards do not work
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           data={"transaction_id": "*"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # a non-existent transaction_id just returns false
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           data={"transaction_id": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # check audit log
        entry = self.find_most_recent_audit_entry(action="*/validate/polltransaction*")
        self.assertEqual(entry["action_detail"], "transaction_id: 123456")
        self.assertEqual(entry["info"], "status: pending")
        self.assertEqual(entry["serial"], None)
        self.assertEqual(entry["user"], None)

        # polling the transaction returns false, because no challenge has been answered
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           data={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # but audit log contains both serials and the user
        entry = self.find_most_recent_audit_entry(action="*/validate/polltransaction*")
        self.assertEqual(entry["action_detail"], "transaction_id: {}".format(transaction_id))
        self.assertEqual(entry["info"], "status: pending")
        self.assertIn("tok1", entry["serial"])
        self.assertIn("tok2", entry["serial"])
        self.assertFalse(entry["success"])
        self.assertEqual(entry["user"], "cornelius")
        self.assertEqual(entry["resolver"], "resolver1")
        self.assertEqual(entry["realm"], self.realm1)

        # polling the expired transaction returns false
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           data={"transaction_id": old_transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # and the audit log contains no serials and the user
        entry = self.find_most_recent_audit_entry(action="*/validate/polltransaction*")
        self.assertEqual(entry["action_detail"], "transaction_id: {}".format(old_transaction_id))
        self.assertEqual(entry["info"], "status: pending")
        self.assertEqual(entry["serial"], None)
        self.assertFalse(entry["success"])

        # Mark one challenge as answered
        Challenge.query.filter_by(serial="tok1", transaction_id=transaction_id).update({"otp_valid": True})
        db.session.commit()

        # polling the transaction returns true, because the challenge has been answered
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           data={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertTrue(res.json["result"]["value"])

        entry = self.find_most_recent_audit_entry(action="*/validate/polltransaction*")
        self.assertEqual(entry["action_detail"], "transaction_id: {}".format(transaction_id))
        self.assertEqual(entry["info"], "status: accept")
        # tok2 is not written to the audit log
        self.assertEqual(entry["serial"], "tok1")
        self.assertTrue(entry["success"])
        self.assertEqual(entry["user"], "cornelius")
        self.assertEqual(entry["resolver"], "resolver1")
        self.assertEqual(entry["realm"], self.realm1)

        # polling the transaction again gives the same result, even with the more REST-y endpoint
        with self.app.test_request_context("/validate/polltransaction/{}".format(transaction_id), method="GET",
                                           data={}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertTrue(res.json["result"]["value"])

        remove_token("tok1")
        remove_token("tok2")

        # polling the transaction now gives false
        with self.app.test_request_context("/validate/polltransaction/{}".format(transaction_id), method="GET",
                                           data={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

    def test_13_chal_resp_indexed_secret(self):
        my_secret = "HelloMyFriend"
        tok = init_token({"otpkey": my_secret,
                          "pin": "test",
                          "serial": "PIIX01",
                          "type": "indexedsecret"},
                         user=User("cornelius", self.realm1))
        # Trigger a challenge
        transaction_id = None
        password = None
        with self.app.test_request_context("/validate/check",
                                           data={"user": "cornelius",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            response = res.json
            self.assertTrue(response.get("result").get("status"))
            self.assertFalse(response.get("result").get("value"))
            transaction_id = response.get("detail").get("transaction_id")
            random_positions = response.get("detail").get("attributes").get("random_positions")
            password_list = [my_secret[x - 1] for x in random_positions]
            password = "".join(password_list)

        with self.app.test_request_context("/validate/check",
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id,
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            response = res.json
            # successful authentication
            self.assertTrue(response.get("result").get("value"))

        # ennroll an empty indexedsecret token and check the raised exception
        remove_token("PIIX01")
        tok = init_token({"otpkey": "",
                          "pin": "test",
                          "serial": "PIIX01",
                          "type": "indexedsecret"},
                         user=User("cornelius", self.realm1))
        with self.app.test_request_context("/validate/check",
                                           data={"user": "cornelius",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            response = res.json
            result = response.get("result")
            self.assertFalse(result.get("status"))
            self.assertEqual('ERR401: The indexedsecret token has an empty secret '
                             'and can not be used for authentication.',
                             result.get("error").get("message"))
        remove_token("PIIX01")

    def test_14_indexed_secret_multichallenge(self):
        index_secret = "abcdefghijklmn"
        serial = "indx001"
        tok = init_token({"type": "indexedsecret", "otpkey": index_secret, "pin": "index", "serial": serial},
                         user=User("cornelius", self.realm1))
        tok.add_tokeninfo("multichallenge", 1)

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": "index"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            position = detail.get("attributes").get("random_positions")[0]

        # First response
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": index_secret[position - 1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            position = detail.get("attributes").get("random_positions")[0]

        # Second response
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": index_secret[position - 1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            # Successful authentication!
            self.assertTrue(result.get("value"))

        remove_token(serial)

    def test_15_questionnaire_multichallenge(self):
        questionnaire = {"Question1": "Answer1",
                         "Question2": "Answer2",
                         "Question3": "Answer3",
                         "Q4": "A4",
                         "Q5": "A5"}
        serial = "quest001"
        found_questions = []
        tok = init_token({"type": "question", "questions": questionnaire, "pin": "quest", "serial": serial},
                         user=User("cornelius", self.realm1))

        # We want two questions during authentication
        set_policy(name="questpol", scope=SCOPE.AUTH, action="question_number=6")

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": "quest"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            question = detail.get("message")
            found_questions.append(question)

        # Run 5 responses that require more
        for i in range(0, 5):
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "cornelius", "pass": questionnaire.get(question),
                                                     "transaction_id": transaction_id}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                result = res.json['result']
                self.assertFalse(result.get("value"))
                detail = res.json.get("detail")
                transaction_id = detail.get("transaction_id")
                question = detail.get("message")
                found_questions.append(question)

        self.assertEqual(len(set(found_questions)), 5)

        # Now we run the last resonse. It can be any of the 5 originial questions again.

        # Sixth and last response will be successful
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": questionnaire.get(question),
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            # Successful authentication!
            self.assertTrue(result.get("value"))

        # But we still have 5 distinct questions
        self.assertEqual(len(set(found_questions)), 5)
        remove_token(serial)
        delete_policy("questpol")

    def test_16_4eyes_multichallenge_with_pin(self):
        # We require 1 token in realm1 and 2 tokens in realm2
        required_tokens = {"realm1": {"selected": True,
                                      "count": 1},
                           "realm3": {"selected": True,
                                      "count": 2}}
        serial = "4eyes001"
        # We want more than one realm
        self.setUp_user_realm3()
        tok = init_token({"type": "4eyes", "4eyes": required_tokens, "pin": "pin", "serial": serial},
                         user=User("root", self.realm3))
        self.assertTrue(tok.get_tokeninfo("4eyes"), "realm1:1,realm3:2")

        # Now we enroll some tokens for the 3 admins.
        # user: cornelius@realm1
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin1", "serial": "admintok1"},
                         user=User("cornelius", self.realm1))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")
        # user: cornelius@realm3
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin2", "serial": "admintok2"},
                         user=User("cornelius", self.realm3))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")
        # user: privacyidea@realm3
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin3", "serial": "admintok3"},
                         user=User("privacyidea", self.realm3))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")

        # Start the authentication with the PIN of the 4eyes token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root", "realm": self.realm3, "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)

        # Authenticate with the first admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin1" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertEqual("Please authenticate with another token from either realm: realm3.",
                             detail.get("message"))

        # Authenticate with the second admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin2" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertEqual("Please authenticate with another token from either realm: realm3.",
                             detail.get("message"))

        # If we would use the 2nd token *again*, then the authentication fails
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin2" + self.valid_otp_values[2],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            self.assertNotIn("transaction_id", detail)
            self.assertEqual("Response did not match the challenge.", detail.get("message"))

        # Authenticate with the third admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin3" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")

        remove_token(serial)
        remove_token("admintok1")
        remove_token("admintok2")
        remove_token("admintok3")

    def test_17_4eyes_multichallenge(self):
        # We require 1 token in realm1 and 2 tokens in realm2
        required_tokens = {"realm1": {"selected": True,
                                      "count": 1},
                           "realm3": {"selected": True,
                                      "count": 2}}
        serial = "4eyes001"
        # We want more than one realm
        self.setUp_user_realm3()
        # Init 4eyes token without PIN
        tok = init_token({"type": "4eyes", "4eyes": required_tokens, "serial": serial},
                         user=User("root", self.realm3))
        self.assertTrue(tok.get_tokeninfo("4eyes"), "realm1:1,realm3:2")

        # Now we enroll some tokens for the 3 admins.
        # user: cornelius@realm1
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin1", "serial": "admintok1"},
                         user=User("cornelius", self.realm1))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")
        # user: cornelius@realm3
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin2", "serial": "admintok2"},
                         user=User("cornelius", self.realm3))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")
        # user: privacyidea@realm3
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin3", "serial": "admintok3"},
                         user=User("privacyidea", self.realm3))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")

        # Start the authentication with one of the tokens!
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin2" + self.valid_otp_values[1]}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)

        # Authenticate with the 2nd admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin1" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)

        # Authenticate with the second admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin3" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))

        remove_token(serial)
        remove_token("admintok1")
        remove_token("admintok2")
        remove_token("admintok3")

    @smtpmock.activate
    def test_18_email_triggerchallenge_no_pin(self):
        # Test that the HOTP value from an email token without a PIN
        # can not be used in challenge response after the challenge expired.
        smtpmock.setdata(response={"hans@dampf.com": (200, 'OK')})
        self.setUp_user_realms()
        self.setUp_user_realm2()
        serial = "smtp01"
        user = "timelimituser"
        # Create token without PIN
        r = init_token({"type": "email", "serial": serial,
                        "otpkey": self.otpkey,
                        "email": "hans@dampf.com"}, user=User(user, self.realm2))
        self.assertTrue(r)

        # Trigger challenge for the user
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": user, "realm": self.realm2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("messages")[0],
                             _("Enter the OTP from the Email:"))
            transaction_id = detail.get("transaction_id")

        # If we wait long enough, the challenge has expired,
        # while the HOTP value 287082 in itself would still be valid.
        # However, the authentication with the expired transaction_id has to fail
        new_utcnow = datetime.datetime.utcnow().replace(tzinfo=None) + datetime.timedelta(minutes=12)
        new_now = datetime.datetime.now().replace(tzinfo=None) + datetime.timedelta(minutes=12)
        with mock.patch('privacyidea.models.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = new_utcnow
            mock_datetime.now.return_value = new_now
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": user, "realm": self.realm2,
                                                     "transaction_id": transaction_id,
                                                     "pass": self.valid_otp_values[1]}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertFalse(result.get("value"))
                detail = res.json.get("detail")
                self.assertEqual("Response did not match the challenge.", detail.get("message"))

        remove_token(serial)

    def test_19_increase_failcounter_on_challenge(self):
        # Create email token
        init_token({
            "type": "email",
            "serial": self.serial_email,
            "email": "hans@dampf.com",
            "pin": "pin"},
            user=User("cornelius", self.realm1))

        # Create SMS token
        init_token({
            "type": "sms",
            "serial": self.serial_sms,
            "phone": "123456",
            "pin": "pin"},
            user=User("cornelius", self.realm1))

        # Create HOTP token
        init_token({
            "type": "hotp",
            "serial": "hotp_serial",
            "otpkey": "abcde12345",
            "pin": "pin"},
            user=User("cornelius", self.realm1))

        # Now check the fail counters of the tokens, all should be 0
        self.assertEqual(0, get_one_token(serial=self.serial_email).token.failcount)
        self.assertEqual(0, get_one_token(serial=self.serial_sms).token.failcount)
        self.assertEqual(0, get_one_token(serial="hotp_serial").token.failcount)

        # Set the increase_failcounter_on_challenge policy
        set_policy(name="increase_failcounter_on_challenge",
                   scope=SCOPE.AUTH,
                   action=ACTION.INCREASE_FAILCOUNTER_ON_CHALLENGE)

        # Now we create the challenges via validate/check
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # The failcounter (email, sms) increased by 1
        self.assertEqual(1, get_one_token(serial=self.serial_email).token.failcount)
        self.assertEqual(1, get_one_token(serial=self.serial_sms).token.failcount)
        self.assertEqual(0, get_one_token(serial="hotp_serial").token.failcount)

        # Trigger a challenge for all token via validate/triggerchallenge
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # All failcounter increased by 1
        self.assertEqual(2, get_one_token(serial=self.serial_email).token.failcount)
        self.assertEqual(2, get_one_token(serial=self.serial_sms).token.failcount)
        self.assertEqual(1, get_one_token(serial="hotp_serial").token.failcount)

        # Clean up
        remove_token(self.serial_email)
        remove_token(self.serial_sms)
        remove_token("hotp_serial")
        delete_policy("increase_failcounter_on_challenge")


class TriggeredPoliciesTestCase(MyApiTestCase):

    def setUp(self):
        super(TriggeredPoliciesTestCase, self).setUp()
        self.setUp_user_realms()

    def test_00_two_policies(self):
        set_policy("otppin", scope=SCOPE.AUTH, action="{0!s}=none".format(ACTION.OTPPIN))
        set_policy("lastauth", scope=SCOPE.AUTHZ, action="{0!s}=1s".format(ACTION.LASTAUTH))

        # Create a Spass token
        tok = init_token({"serial": "triggtoken", "type": "spass"})

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
                                           data={"policies": "*otppin*"},
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
                                           data={"policies": "*lastauth*"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get("count"), 1)
            # Both policies have triggered
            self.assertEqual(json_response.get("result").get("value").get("auditdata")[0].get("policies"),
                             "otppin,lastauth")

        # clean up
        remove_token("triggtoken")
        delete_policy("otppin")
        delete_policy("lastauth")


class MultiChallengeEnrollTest(MyApiTestCase):

    # Note: Testing the enrollment of the push token is done in test_api_push_validate.py

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
        r = set_realm("ldaprealm", resolvers=["catchall"])
        set_default_realm("ldaprealm")

        # 1. set policies.
        # Policy scope:auth, action:enroll_via_multichallenge=hotp
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=ACTION.PASSTHRU)

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
                   action="{0!s}=hotp".format(ACTION.ENROLL_VIA_MULTICHALLENGE))

        # Set force_app_pin
        set_policy("pol_forcepin", scope=SCOPE.ENROLL,
                   action="hotp_{0!s}=True".format(ACTION.FORCE_APP_PIN))
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
            self.assertTrue("Please scan the QR code!" in detail.get("message"), detail.get("message"))
            # Get image and client_mode
            self.assertEqual(CLIENTMODE.INTERACTIVE, detail.get("client_mode"), detail)
            # Check, that multi_challenge is also contained.
            chal = detail.get("multi_challenge")[0]
            self.assertEqual(CLIENTMODE.INTERACTIVE, chal.get("client_mode"), detail)
            self.assertIn("image", detail, detail)
            self.assertEqual(1, len(detail.get("messages")))
            self.assertEqual("Please scan the QR code!", detail.get("messages")[0])
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
        self.assertIn('Exiting get_init_tokenlabel_parameters with result {\'force_app_pin\': True}', log_msg, log_msg)
        logging.getLogger('privacyidea').setLevel(logging.INFO)

        # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        delete_policy("pol_forcepin")
        remove_token(serial)

    @ldap3mock.activate
    def test_02_enroll_TOTP(self):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # create realm
        r = set_realm("ldaprealm", resolvers=["catchall"])
        set_default_realm("ldaprealm")

        # 1. set policies.
        # Policy scope:auth, action:enroll_via_multichallenge=hotp
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=ACTION.PASSTHRU)

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
                   action="{0!s}=totp".format(ACTION.ENROLL_VIA_MULTICHALLENGE))
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
            self.assertTrue("Please scan the QR code!" in detail.get("message"), detail.get("message"))
            # Get image and client_mode
            self.assertEqual(CLIENTMODE.INTERACTIVE, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(CLIENTMODE.INTERACTIVE, detail.get("multi_challenge")[0].get("client_mode"))
            self.assertIn("image", detail)
            serial = detail.get("serial")

        # 3. scan the qrcode / Get the OTP value
        token_obj = get_tokens(serial=serial)[0]
        counter = int(time.time() / 30)
        otp = token_obj._calc_otp(counter)

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

        # Cleanup
        delete_policy("pol_passthru")
        delete_policy("pol_multienroll")
        remove_token(serial)

    @ldap3mock.activate
    @smtpmock.activate
    def test_03_enroll_EMail(self):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # mock email sending
        smtpmock.setdata(response={"alice@example.com": (200, 'OK')})
        # create realm
        r = set_realm("ldaprealm", resolvers=["catchall"])
        set_default_realm("ldaprealm")

        # 1. set policies.
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=ACTION.PASSTHRU)

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
                   action="{0!s}=email".format(ACTION.ENROLL_VIA_MULTICHALLENGE))
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
            self.assertEqual(CLIENTMODE.INTERACTIVE, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(CLIENTMODE.INTERACTIVE, detail.get("multi_challenge")[0].get("client_mode"))
            self.assertIn("image", detail)
            serial = detail.get("serial")

        # 3. Enter the email address and finalize the token
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
    @responses.activate
    def test_04_enroll_SMS(self):
        # Init LDAP
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # mock http response
        setup_sms_gateway()

        # create realm
        r = set_realm("ldaprealm", resolvers=["catchall"])
        set_default_realm("ldaprealm")

        # 1. set policies.
        set_policy("pol_passthru", scope=SCOPE.AUTH, action=ACTION.PASSTHRU)

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
                   action="{0!s}=sms".format(ACTION.ENROLL_VIA_MULTICHALLENGE))
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
            self.assertTrue("Please enter your new phone number!" in detail.get("message"), detail.get("message"))
            # Get image and client_mode
            self.assertEqual(CLIENTMODE.INTERACTIVE, detail.get("client_mode"))
            # Check, that multi_challenge is also contained.
            self.assertEqual(CLIENTMODE.INTERACTIVE, detail.get("multi_challenge")[0].get("client_mode"))
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
        remove_token(serial)


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
            detail = res.json.get("detail")
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
            detail = res.json.get("detail")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
