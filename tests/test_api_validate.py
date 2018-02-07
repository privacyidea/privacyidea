# -*- coding: utf-8 -*-
from urllib import urlencode
import json

from .base import MyTestCase
from privacyidea.lib.user import (User)
from privacyidea.lib.tokens.totptoken import HotpTokenClass
from privacyidea.models import (Token, Challenge)
from privacyidea.lib.config import (set_privacyidea_config, get_token_types,
                                    get_inc_fail_count_on_false_pin,
                                    delete_privacyidea_config)
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   reset_token, enable_token, revoke_token)
from privacyidea.lib.policy import SCOPE, ACTION, set_policy, delete_policy
from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.resolver import save_resolver, get_resolver_list
from privacyidea.lib.realm import set_realm, set_default_realm

import smtpmock, ldap3mock, responses


PWFILE = "tests/testdata/passwords"
HOSTSFILE = "tests/testdata/hosts"

LDAPDirectory = [{"dn": "cn=alice,ou=example,o=test",
                 "attributes": {'cn': 'alice',
                                "sn": "Cooper",
                                "givenName": "Alice",
                                'userPassword': 'alicepw',
                                'oid': "2",
                                "homeDirectory": "/home/alice",
                                "email": "alice@test.com",
                                "accountExpires": 131024988000000000,
                                "objectGUID": '\xef6\x9b\x03\xc0\xe7\xf3B'
                                              '\x9b\xf9\xcajl\rM1',
                                'mobile': ["1234", "45678"]}},
                {"dn": 'cn=bob,ou=example,o=test',
                 "attributes": {'cn': 'bob',
                                "sn": "Marley",
                                "givenName": "Robert",
                                "email": "bob@example.com",
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
                                "mobile": "123354",
                                'userPassword': 'ldaptest',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": '\xef7\x9b\x03\xc0\xe7\xf3B'
                                              '\x9b\xf9\xcajl\rMT',
                                'oid': "5"}}
                 ]


class AuthorizationPolicyTestCase(MyTestCase):
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))


class DisplayTANTestCase(MyTestCase):

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
            result = json.loads(res.data).get("result")
            value = result.get("value")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            detail = json.loads(res.data).get("detail")
            transaction_id = detail.get("transaction_id")
            hex_challenge = detail.get("attributes").get("challenge")
            self.assertEqual(len(hex_challenge), 40)

        remove_token("ocra1234")


class AAValidateOfflineTestCase(MyTestCase):
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
        token.set_user(User("cornelius", self.realm1))
        token.set_pin("pin")
        self.assertTrue(token.token.user_id == "1000", token.token.user_id)

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
                         resolver_name="testresolver")

        # first online validation
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            result = data.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("otplen"), 6)
            auth_items = json.loads(res.data).get("auth_items")
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
            data = json.loads(res.data)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            auth_items = json.loads(res.data).get("auth_items")
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
            data = json.loads(res.data)
            self.assertEqual(data.get("result").get("error").get("message"),
                             u"ERR905: Token is not an offline token or refill token is incorrect")

        # 2nd refill with 10th value
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin520489",
                                                 "refilltoken": refilltoken_2},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            auth_items = json.loads(res.data).get("auth_items")
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
            data = json.loads(res.data)
            self.assertTrue(res.status_code == 400, res)
            self.assertEqual(data.get("result").get("error").get("message"),
                             u"ERR10: You provided a wrong OTP value.")
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
            data = json.loads(res.data)
            self.assertTrue(res.status_code == 400, res)
            self.assertEqual(data.get("result").get("error").get("message"),
                             u"ERR905: The token does not exist")

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
            data = json.loads(res.data)
            self.assertTrue(res.status_code == 400, res)
            self.assertEqual(data.get("result").get("error").get("message"),
                             u"ERR905: Token is not an offline token or refill token is incorrect")


class ValidateAPITestCase(MyTestCase):
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
        token.set_user(User("cornelius", self.realm1))
        token.set_pin("pin")
        self.assertTrue(token.token.user_id == "1000", token.token.user_id)

    def test_02_validate_check(self):
        # is the token still assigned?
        tokenbject_list = get_tokens(serial=self.serials[0])
        tokenobject = tokenbject_list[0]
        self.assertTrue(tokenobject.token.user_id == "1000",
                        tokenobject.token.user_id)

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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            detail = json.loads(res.data).get("detail")
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
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)

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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)

        # test authentication fails with serial with same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            details = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            details = json.loads(res.data).get("detail")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

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
            result = json.loads(res.data).get("result")
            details = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))

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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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

        for i in range(1, 5):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"serial": "pass1",
                                                     "pass": "123456"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = json.loads(res.data).get("result")
                self.assertEqual(result.get("value"), True)

        # The 6th authentication will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass1",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue('"setPolicy pol_chal_resp": 1' in res.data,
                            res.data)

        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        db_token = Token(serial, tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        token.set_user(User("cornelius", self.realm1))
        token.set_pin(pin)
        # Set the failcounter
        token.set_failcount(5)
        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), "please enter otp: ")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertTrue(result.get("value"))

        self.assertEqual(token.get_failcount(), 0)
        # delete the token
        remove_token(serial=serial)

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
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue('"setPolicy pol_chal_resp": 1' in res.data,
                            res.data)

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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue('"setPolicy pol_chal_resp": 1' in res.data,
                            res.data)

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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), "Enter the OTP from the "
                                                    "Email:")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertFalse(result.get("value"))
            details = json.loads(res.data).get("detail")
            self.assertTrue("Outside validity period" in details.get("message"))

        token_obj.set_validity_period_end("1999-01-01T10:00+0200")
        token_obj.set_validity_period_start("1998-01-01T10:00+0200")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertFalse(result.get("value"))
            details = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        set_privacyidea_config("splitAtSign", "0")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        set_privacyidea_config("splitAtSign", "1")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        # The default behaviour - if the config entry does not exist,
        # is to split the @Sign
        delete_privacyidea_config("splitAtSign")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
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
                                                    "cornelius@"+self.realm2,
                                                 "pass": "async399871"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), False)

        # counter = 9, will be autosynced.
        # Authentication is successful
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": "async520489"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        delete_privacyidea_config("AutoResync")

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
                result = json.loads(res.data).get("result")
                self.assertEqual(result.get("value"), True)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
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
                result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), False)
            details = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        # Passthru with POST Request
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "passthru",
                                                 "realm": self.realm2,
                                                 "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

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
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value, True)

        # Start a challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertFalse(result.get("value"))
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("serial"), serial)

        # User that does not exist, can authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "doesNotExist",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("message"),
                             u"The user does not exist, but is accepted "
                             u"due to policy 'pass_no'.")

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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("message"),
                             u"The user has no token, but is "
                             u"accepted due to policy 'pass_no'.")

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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), False)
            detail = json.loads(res.data).get("detail")
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
            detail = json.loads(res.data).get("detail")
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
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("message"),
                             u'The user does not exist, but is accepted due to policy \'pol1\'.')
        delete_policy("pol1")

    @responses.activate
    def test_24_trigger_challenge(self):
        from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
        from privacyidea.lib.config import set_privacyidea_config
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
        self.assertTrue(id > 0)
        # set config sms.identifier = myGW
        r = set_privacyidea_config("sms.identifier", identifier)
        self.assertEqual(r, "insert")

        responses.add(responses.POST,
                      post_url,
                      body=success_body)

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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), 1)
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("messages")[0],
                             "Enter the OTP from the SMS:")
            transaction_id = detail.get("transaction_ids")[0]

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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), 1)
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("messages")[0],
                             "Enter the OTP from the SMS:")
            transaction_id = detail.get("transaction_ids")[0]

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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), 1)
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("messages")[0],
                             "Enter the OTP from the Email:")
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
        set_policy("test49", scope=SCOPE.AUTH, action="{0!s}=HOTP".format(
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), False)
            detail = json.loads(res.data).get("detail")
            transaction_id = detail.get("transaction_id")
            multi_challenge = detail.get("multi_challenge")
            self.assertEqual(multi_challenge[0].get("serial"), "CR2A")
            self.assertEqual(transaction_id,
                             multi_challenge[0].get("transaction_id"))
            self.assertEqual(transaction_id,
                             multi_challenge[1].get("transaction_id"))
            self.assertEqual(multi_challenge[1].get("serial"), "CR2B")

        # There are two challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 2)

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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)
            detail = json.loads(res.data).get("detail")
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
        set_policy("test48", scope=SCOPE.AUTH, action="{0!s}=HOTP".format(
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), False)
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)
            detail = json.loads(res.data).get("detail")
            serial = detail.get("serial")
            self.assertEqual(serial, "CR2B")

        # No challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 0)

        remove_token("CR2A")
        remove_token("CR2B")
        delete_policy("test49")

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
            self.assertEqual(res.data, '')

        # test authentication fails with wrong PIN
        with self.app.test_request_context('/validate/radiuscheck',
                                           method='POST',
                                           data={"serial": "pass3",
                                                 "pass": "wrong"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.data, '')

        # test authentication fails with an unknown user
        # here, we get an ordinary JSON response
        with self.app.test_request_context('/validate/radiuscheck',
                                           method='POST',
                                           data={"user": "unknown",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            result = json.loads(res.data).get("result")
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
        set_policy("test48", scope=SCOPE.AUTH, action="{0!s}=HOTP".format(
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
            result = json.loads(res.data).get("result")
            # This is a challene, the value is False
            self.assertEqual(result.get("value"), False)
            detail = json.loads(res.data).get("detail")
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

        # two different token types
        init_token({"serial": "SPASS1",
                    "type": "spass",
                    "pin": "hallo123"}, user)
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("type"), "undetermined")

        # two same token types.
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)
            detail = json.loads(res.data).get("detail")
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
            self.assertTrue(res.status_code == 403, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("status"), False)
            detail = json.loads(res.data).get("detail")
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
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("onlyHOTP")
        delete_policy("passthru")
        remove_token("SPASS1")
        remove_token("SPASS2")
        remove_token("HOTP1")