# -*- coding: utf-8 -*-
"""
This test file tests the lib.resolver and all
the resolvers under it:

lib.resolvers.passwdresolver
lib.resolvers.ldapresolver

The lib.resolver.py only depends on the database model.
"""

PWFILE = "tests/testdata/passwords"
from .base import MyTestCase
from . import ldap3mock
from ldap3.core.exceptions import LDAPOperationResult
from ldap3.core.results import RESULT_SIZE_LIMIT_EXCEEDED
import mock
import ldap3
import responses
import datetime
import uuid
import pytest
import json
import ssl
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPResolver, LockingServerPool
from privacyidea.lib.resolvers.SQLIdResolver import IdResolver as SQLResolver
from privacyidea.lib.resolvers.SCIMIdResolver import IdResolver as SCIMResolver
from privacyidea.lib.resolvers.UserIdResolver import UserIdResolver
from privacyidea.lib.resolvers.LDAPIdResolver import (SERVERPOOL_ROUNDS, SERVERPOOL_SKIP)
from privacyidea.lib.resolvers.HTTPResolver import HTTPResolver

from privacyidea.lib.resolver import (save_resolver,
                                      delete_resolver,
                                      get_resolver_config,
                                      get_resolver_list,
                                      get_resolver_object, pretestresolver,
                                      CENSORED)
from privacyidea.lib.realm import (set_realm, delete_realm)
from privacyidea.models import ResolverConfig
from privacyidea.lib.utils import to_bytes, to_unicode
from requests import HTTPError

objectGUIDs = [
    '039b36ef-e7c0-42f3-9bf9-ca6a6c0d4d31',
    '039b36ef-e7c0-42f3-9bf9-ca6a6c0d4d77',
    '039b36ef-e7c0-42f3-9bf9-ca6a6c0d4d54',
    '7dd0533c-afe3-4c6f-b49e-af82eaed045c'
]


LDAPDirectory = [{"dn": "cn=alice,ou=example,o=test",
                 "attributes": {'cn': 'alice',
                                "sn": "Cooper",
                                "givenName": "Alice",
                                'userPassword': 'alicepw',
                                'oid': "2",
                                "homeDirectory": "/home/alice",
                                "email": "alice@test.com",
                                "accountExpires": 131024988000000000,
                                "objectGUID": objectGUIDs[0],
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
                                "objectGUID": objectGUIDs[1],
                                'oid': "3"}},
                {"dn": 'cn=manager,ou=example,o=test',
                 "attributes": {'cn': 'manager',
                                "givenName": "Corny",
                                "sn": "keule",
                                "email": "ck@o",
                                "mobile": "123354",
                                'userPassword': 'ldaptest',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": objectGUIDs[2],
                                'oid': "1"}},
                 {"dn": 'cn=kölbel,ou=example,o=test',
                  "attributes": {'cn': "kölbel",
                                 "givenName": "Cornelius",
                                 "sn": "Kölbel",
                                 "email": "cko@o",
                                 "mobile": "123456",
                                 "userPassword": "mySecret",
                                 "accoutnExpires": 9223372036854775807,
                                 "objectGUID": objectGUIDs[3],
                                 "someAttr": ["value1", "value2"],
                                 "oid": "4"}}]

LDAPDirectory_small = [{"dn": 'cn=bob,ou=example,o=test',
                 "attributes": {'cn': 'bob',
                                "sn": "Marley",
                                "givenName": "Robert",
                                "email": "bob@example.com",
                                "mobile": "123456",
                                "homeDirectory": "/home/bob",
                                'userPassword': 'bobpwééé',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": objectGUIDs[0],
                                'oid': "3"}},
                {"dn": 'cn=manager,ou=example,o=test',
                 "attributes": {'cn': 'manager',
                                "givenName": "Corny",
                                "sn": "keule",
                                "email": "ck@o",
                                "mobile": "123354",
                                'userPassword': 'ldaptest',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": objectGUIDs[1],
                                'oid': "1"}},
                       {"dn": 'cn=salesman,ou=example,o=test',
                        "attributes": {'cn': 'salesman',
                                       'givenName': 'hans',
                                       'sn': 'Meyer',
                                       'mobile': ['1234', '3456'],
                                       'objectGUID': objectGUIDs[2]}}
                       ]
# Same as above, but with curly-braced string representation of objectGUID
# to imitate ldap3 > 2.4.1
LDAPDirectory_curly_objectGUID = [{"dn": 'cn=bob,ou=example,o=test',
                 "attributes": {'cn': 'bob',
                                "sn": "Marley",
                                "givenName": "Robert",
                                "email": "bob@example.com",
                                "mobile": "123456",
                                "homeDirectory": "/home/bob",
                                'userPassword': 'bobpwééé',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": "{" + objectGUIDs[0] + "}",
                                'oid': "3"}},
                {"dn": 'cn=manager,ou=example,o=test',
                 "attributes": {'cn': 'manager',
                                "givenName": "Corny",
                                "sn": "keule",
                                "email": "ck@o",
                                "mobile": "123354",
                                'userPassword': 'ldaptest',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": "{" + objectGUIDs[1] + "}",
                                'oid': "1"}}
                       ]


class SQLResolverTestCase(MyTestCase):
    """
    Test the SQL Resolver
    """
    num_users = 13
    parameters = {'Driver': 'sqlite',
                  'Server': '/tests/testdata/',
                  'Database': "testuser.sqlite",
                  'Table': 'users',
                  'Encoding': 'utf8',
                  'Map': '{ "username": "username", \
                    "userid" : "id", \
                    "email" : "email", \
                    "surname" : "name", \
                    "givenname" : "givenname", \
                    "password" : "password", \
                    "phone": "phone", \
                    "mobile": "mobile"}'
    }

    def test_00_delete_achmeds(self):
        # If the test failed and some achmeds are still in the database (from
        #  add_user) we delete them here.
        y = SQLResolver()
        y.loadConfig(self.parameters)
        for username in ["achmed", "achmed2", "corneliusReg"]:
            uid = True
            while uid:
                uid = y.getUserId(username)
                y.delete_user(uid)

    def test_01_sqlite_resolver(self):
        y = SQLResolver()
        y.loadConfig(self.parameters)

        userlist = y.getUserList()
        self.assertEqual(len(userlist), self.num_users, userlist)

        user = "cornelius"
        user_id = y.getUserId(user)
        self.assertEqual(user_id, '3', user_id)

        rid = y.getResolverId()
        self.assertTrue(rid.startswith("sql."))

        rtype = y.getResolverType()
        self.assertTrue(rtype == "sqlresolver", rtype)

        rdesc = y.getResolverDescriptor()
        self.assertTrue("sqlresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("sqlresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("sqlresolver"), rdesc)

        uinfo = y.getUserInfo(user_id)
        self.assertEqual("cornelius", uinfo.get("username"), uinfo)

        ret = y.getUserList({"username": "cornelius"})
        self.assertEqual(len(ret), 1, ret)

        username = y.getUsername(user_id)
        self.assertEqual(username, "cornelius", username)

    def test_01a_where_tests(self):
        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "givenname == hans"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 1, userlist)

        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "givenname like hans"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertEqual(len(userlist), 1)

        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "id > 2"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertEqual(len(userlist), self.num_users - 2)

        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "id < 5"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertEqual(len(userlist), 4)

    def test_02_check_passwords(self):
        y = SQLResolver()
        y.loadConfig(self.parameters)

        # SHA256 of "dunno"
        # 772cb52221f19104310cd2f549f5131fbfd34e0f4de7590c87b1d73175812607

        self.assertTrue(y.checkPass('3', "dunno"))
        '''
        SHA1 base64 encoded of "dunno"
        Lg8DuLoXOwvPkMABDprnaTp0JOA=
        '''
        self.assertTrue(y.checkPass('2', "dunno"))

        self.assertTrue(y.checkPass('1', "dunno"))

        self.assertTrue(y.checkPass('4', "dunno"))

        self.assertTrue(y.checkPass('5', "dunno"))

        '''
        >>> PH = PasswordHash()
        >>> PH.hash_password("testpassword")
        '$P$Bz4R6lzp6VWCL0SCeTozqKHNV8DM.Q/'
        '''
        self.assertTrue(y.checkPass('6', "testpassword"))

        self.assertTrue(y.checkPass('8', "dunno"))

        self.assertTrue(y.checkPass('9', "dunno"))

        # bcrypt hashes
        self.assertTrue(y.checkPass('10', "test"))
        self.assertFalse(y.checkPass('10', "testw"))
        self.assertTrue(y.checkPass('11', "test"))
        self.assertFalse(y.checkPass('11', "testw"))
        self.assertTrue(y.checkPass('12', "dunno"))
        self.assertFalse(y.checkPass('12', "dunno2"))
        # unknown password hash type
        self.assertFalse(y.checkPass('13', "dunno2"))

    def test_03_testconnection(self):
        y = SQLResolver()
        result = y.testconnection(self.parameters)
        self.assertEqual(result[0], self.num_users)
        self.assertTrue('Found {0!s} users.'.format(self.num_users) in result[1])

    def test_05_add_user_update_delete(self):
        y = SQLResolver()
        # This has no password hash type set at all
        y.loadConfig(self.parameters)
        uid = y.add_user({"username": "achmed",
                          "email": "achmed@world.net",
                          "password": "passw0rd",
                          "mobile": "12345"})
        self.assertTrue(uid > self.num_users)
        self.assertTrue(y.checkPass(uid, "passw0rd"))
        self.assertFalse(y.checkPass(uid, "password"))
        # check that we actually store SSHA256
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed")).first().password
        self.assertTrue(stored_password.startswith("{SSHA256}"), stored_password)

        # we assume here the uid is of type int
        uid = y.getUserId("achmed")
        self.assertGreater(int(uid), self.num_users)

        r = y.update_user(uid, {"username": "achmed2",
                                "password": "test"})
        # check that we actually store SSHA256
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("{SSHA256}"), stored_password)
        uname = y.getUsername(uid)
        self.assertEqual(uname, "achmed2")
        r = y.checkPass(uid, "test")
        self.assertTrue(r)
        # Now we delete the user
        y.delete_user(uid)
        # Now there should be no achmed anymore
        uid = y.getUserId("achmed2")
        self.assertFalse(uid)
        uid = y.getUserId("achmed")
        self.assertFalse(uid)
        
    def test_06_append_where_filter(self):
        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "givenname == hans and name == dampf"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 1, userlist)
        
        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "givenname == hans AND name == dampf"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 1, userlist)

        # Also allow more than one blank surrounding the "and"
        # SQLAlchemy strips the blanks in the condition
        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "givenname == hans   AND name == dampf"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 1, userlist)
        
        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "givenname == hans and name == test"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 0, userlist)
        
        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "givenname == chandler"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 0, userlist)

    def test_06b_where_filter_and_delete_user(self):
        y = SQLResolver()
        d = self.parameters.copy()
        d.update({"Where": "id > 10"})
        y.loadConfig(d)
        userlist = y.getUserList()
        self.assertGreaterEqual(len(userlist), 3, userlist)
        uid = y.add_user({"username": "testuser",
                          "email": "user@test.net",
                          "password": "passw0rd",
                          "mobile": "1234567"})
        self.assertTrue(uid > self.num_users)
        userlist = y.getUserList()
        self.assertGreaterEqual(len(userlist), 4, userlist)
        y.delete_user(uid)
        uid = y.getUserId("testuser")
        self.assertFalse(uid)

    def test_07_add_user_update_delete_hashes(self):
        y = SQLResolver()
        parameters = self.parameters.copy()
        # sha256 at first
        parameters["Password_Hash_Type"] = "SSHA256"
        y.loadConfig(parameters)
        uid = y.add_user({"username": "achmed",
                          "email": "achmed@world.net",
                          "password": "passw0rd",
                          "mobile": "12345"})
        self.assertTrue(uid > self.num_users)
        self.assertTrue(y.checkPass(uid, "passw0rd"))
        self.assertFalse(y.checkPass(uid, "password"))
        # check that we actually store SSHA256 at first
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed")).first().password
        self.assertTrue(stored_password.startswith("{SSHA256}"), stored_password)

        self.assertTrue(y.update_user(uid, {"username": "achmed2",
                                            "password": "test"}))
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("{SSHA256}"), stored_password)
        self.assertEqual(y.getUsername(uid), "achmed2")
        self.assertTrue(y.checkPass(uid, "test"))

        # change to SSHA512
        y = SQLResolver()
        parameters["Password_Hash_Type"] = "SSHA512"
        y.loadConfig(parameters)

        self.assertTrue(y.update_user(uid, {"username": "achmed2",
                                            "password": "test2"}))
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("{SSHA512}"), stored_password)
        self.assertTrue(y.checkPass(uid, "test2"))
        self.assertFalse(y.checkPass(uid, "test"))

        # PHPASS
        parameters["Password_Hash_Type"] = "PHPASS"
        y.loadConfig(parameters)
        self.assertTrue(y.update_user(uid, {"username": "achmed2",
                                            "password": "test3"}))
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("$P$"), stored_password)
        self.assertTrue(y.checkPass(uid, "test3"))
        self.assertFalse(y.checkPass(uid, "test"))

        # SHA
        parameters["Password_Hash_Type"] = "SHA"
        y.loadConfig(parameters)
        self.assertTrue(y.update_user(uid, {"username": "achmed2",
                                            "password": "test4"}))
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("{SHA}"), stored_password)
        self.assertTrue(y.checkPass(uid, "test4"))
        self.assertFalse(y.checkPass(uid, "test"))

        # SSHA
        parameters["Password_Hash_Type"] = "SSHA"
        y.loadConfig(parameters)
        self.assertTrue(y.update_user(uid, {"username": "achmed2",
                                            "password": "test5"}))
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("{SSHA}"), stored_password)
        self.assertTrue(y.checkPass(uid, "test5"))
        self.assertFalse(y.checkPass(uid, "test"))

        # SHA256CRYPT
        parameters["Password_Hash_Type"] = "SHA256CRYPT"
        y.loadConfig(parameters)
        self.assertTrue(y.update_user(uid, {"username": "achmed2",
                                            "password": "test6"}))
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("$5$rounds="), stored_password)
        self.assertTrue(y.checkPass(uid, "test6"))
        self.assertFalse(y.checkPass(uid, "test"))

        # SHA512CRYPT
        parameters["Password_Hash_Type"] = "SHA512CRYPT"
        y.loadConfig(parameters)
        self.assertTrue(y.update_user(uid, {"username": "achmed2",
                                            "password": "test7"}))
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("$6$rounds="), stored_password)
        self.assertTrue(y.checkPass(uid, "test7"))
        self.assertFalse(y.checkPass(uid, "test"))

        # MD5CRYPT
        parameters["Password_Hash_Type"] = "MD5CRYPT"
        y.loadConfig(parameters)
        self.assertTrue(y.update_user(uid, {"username": "achmed2",
                                            "password": "test8"}))
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "achmed2")).first().password
        self.assertTrue(stored_password.startswith("$1$"), stored_password)
        self.assertTrue(y.checkPass(uid, "test8"))
        self.assertFalse(y.checkPass(uid, "test"))

        # TODO: check unknown hash type
        parameters["Password_Hash_Type"] = "UNKNOWN"
        y.loadConfig(parameters)
        with mock.patch("logging.Logger.error") as mock_log:
            self.assertFalse(y.update_user(uid, {"username": "achmed2",
                                                 "password": "test9"}))
            expected = "Error updating user attributes for user with uid 14: " \
                       "Unsupported password hashtype 'UNKNOWN'. Use one of " \
                       "dict_keys(['PHPASS', 'SHA', 'SSHA', 'SSHA256', 'SSHA512', " \
                       "'OTRS', 'SHA256CRYPT', 'SHA512CRYPT', 'MD5CRYPT'])."
            mock_log.assert_called_once_with(expected)

        # set hash type to default
        parameters.pop("Password_Hash_Type")
        y.loadConfig(parameters)

        # Now we delete the user
        y.delete_user(uid)
        # Now there should be no achmed anymore
        uid = y.getUserId("achmed2")
        self.assertFalse(uid)
        uid = y.getUserId("achmed")
        self.assertFalse(uid)

        # Add a new user
        uid = y.add_user({"username": "hans",
                          "email": "hans@world.net",
                          "password": "foo",
                          "mobile": "12345"})
        self.assertTrue(y.checkPass(uid, "foo"))
        self.assertFalse(y.checkPass(uid, "bar"))
        # check that we actually store SSHA265 now since it is the default
        stored_password = y.session.execute(
            y.TABLE.select().where(y.TABLE.c.username == "hans")).first().password
        self.assertTrue(stored_password.startswith("{SSHA256}"), stored_password)

        y.delete_user(uid)

    def test_08_resolver_id(self):
        y = SQLResolver()
        y.loadConfig(self.parameters)
        rid1 = y.getResolverId()

        y = SQLResolver()
        param2 = self.parameters.copy()
        param2["Where"] = "1 = 1"
        y.loadConfig(param2)
        rid2 = y.getResolverId()

        # rid1 == rid2, because only the WHERE clause has changed, which does not have any effect on the resolver id!
        self.assertEqual(rid1, rid2)

        y = SQLResolver()
        param3 = self.parameters.copy()
        param3["Server"] = '/tests/../tests/testdata/'
        y.loadConfig(param3)
        rid3 = y.getResolverId()

        # rid1 != rid3, because the connect string has changed
        self.assertNotEqual(rid1, rid3)

        y = SQLResolver()
        param4 = self.parameters.copy()
        param4["poolSize"] = "42"
        y.loadConfig(param4)
        rid4 = y.getResolverId()

        # rid1 != rid4, because the pool size has changed
        self.assertNotEqual(rid1, rid4)
    
    def test_08_noninteger_userid(self):
        y = SQLResolver()
        y.loadConfig(self.parameters)
        y.map["userid"] = "username"
        user = "cornelius"
        user_info = y.getUserInfo(user)
        self.assertEqual(user_info.get("userid"), "cornelius")

    def test_99_testconnection_fail(self):
        y = SQLResolver()
        self.parameters['Database'] = "does_not_exist"
        result = y.testconnection(self.parameters)
        self.assertTrue(result[0] == -1, result)
        self.assertTrue("failed to retrieve" in result[1], result)


class SCIMResolverTestCase(MyTestCase):
    """
    Test the SCIM Resolver
    """
    CLIENT = "puckel"
    SECRET = "d81c31e4-9f65-4805-b5ba-6edf0761f954"
    AUTHSERVER = "http://localhost:8080/osiam-auth-server"
    RESOURCESERVER = "http://localhost:8080/osiam-resource-server"
    TOKEN_URL = 'http://localhost:8080/osiam-auth-server/oauth/token'
    USER_URL = 'http://localhost:8080/osiam-resource-server/Users'

    BODY_ACCESSTOKEN = """{"access_token": "MOCKTOKEN"}"""
    # taken from
    # http://www.simplecloud.info/specs/draft-scim-api-01.html#get-resource
    BODY_USERS = """{
  "totalResults":2,
  "schemas":["urn:scim:schemas:core:1.0"],
  "Resources":[
    {
      "userName":"bjensen"
    },
    {
      "userName":"jsmith"
    }
  ]
}"""

    BODY_SINGLE_USER = """{"schemas":["urn:scim:schemas:core:1.0"],
"id":"2819c223-7f76-453a-919d-413861904646",
"externalId":"bjensen",
"meta":{
    "created":"2011-08-01T18:29:49.793Z",
    "lastModified":"2011-08-01T18:29:49.793Z",
    "location":"https://example.com/v1/Users/2819c223-7f76-453a-919d-413861904646",
    "version":"Wf250dd84f0671c3"
},
"name":{
    "formatted":"Ms. Barbara J Jensen III",
    "familyName":"Jensen",
    "givenName":"Barbara"
},
"userName":"bjensen",
"phoneNumbers":[
    {
      "value":"555-555-8377",
      "type":"work"
    }
  ],
"emails":[
    {
      "value":"bjensen@example.com",
      "type":"work"
    }
  ]
}"""

    @responses.activate
    def test_00_testconnection(self):
        # add get access token
        responses.add(responses.GET, self.TOKEN_URL,
                      status=200, content_type='application/json',
                      body=self.BODY_ACCESSTOKEN)

        # Failed to retrieve users
        success, desc, = pretestresolver("scimresolver",
                                         {"Authserver": self.AUTHSERVER,
                                          "Resourceserver": self.RESOURCESERVER,
                                          "Client": self.CLIENT,
                                          "Secret": self.SECRET})
        self.assertFalse(success)
        self.assertTrue("failed to retrieve users" in desc)

        # Successful user retrieve
        responses.add(responses.GET, self.USER_URL,
                      status=200, content_type='application/json',
                      body=self.BODY_USERS)
        success, desc, = pretestresolver("scimresolver",
                                         {"Authserver": self.AUTHSERVER,
                                          "Resourceserver": self.RESOURCESERVER,
                                          "Client": self.CLIENT,
                                          "Secret": self.SECRET})
        self.assertTrue(success)
        self.assertEqual(desc, "Found 2 users")

    @responses.activate
    def test_01_failed_to_get_accesstoken(self):
        responses.add(responses.GET, self.TOKEN_URL,
                      status=402, content_type='application/json',
                      body=self.BODY_ACCESSTOKEN)
        # Failed to retrieve access token
        self.assertRaises(Exception, SCIMResolver.get_access_token,
                          server=self.AUTHSERVER, client=self.CLIENT,
                          secret=self.SECRET)

    @responses.activate
    def test_02_load_config(self):
        responses.add(responses.GET, self.TOKEN_URL, status=200,
                      content_type='application/json',
                      body=self.BODY_ACCESSTOKEN)
        y = SCIMResolver()
        y.loadConfig({'Authserver': self.AUTHSERVER, 'Resourceserver':
            self.RESOURCESERVER, 'Client': self.CLIENT, 'Secret':
            self.SECRET, 'Mapping': "{}"})

        rid = y.getResolverId()
        self.assertEqual(rid, self.AUTHSERVER)

        r = y.getResolverClassDescriptor()
        self.assertTrue("scimresolver" in r)
        r = y.getResolverDescriptor()
        self.assertTrue("scimresolver" in r)
        r = y.getResolverType()
        self.assertEqual("scimresolver", r)

    @responses.activate
    def test_03_checkpass(self):
        responses.add(responses.GET, self.TOKEN_URL, status=200,
                      content_type='application/json',
                      body=self.BODY_ACCESSTOKEN)
        y = SCIMResolver()
        y.loadConfig({'Authserver': self.AUTHSERVER, 'Resourceserver':
            self.RESOURCESERVER, 'Client': self.CLIENT, 'Secret':
            self.SECRET, 'Mapping': "{}"})

        r = y.checkPass("uid", "password")
        self.assertFalse(r)

    @responses.activate
    def test_04_single_user(self):
        responses.add(responses.GET, self.TOKEN_URL, status=200,
                      content_type='application/json',
                      body=self.BODY_ACCESSTOKEN)
        responses.add(responses.GET, self.USER_URL+"/bjensen",
                      status=200, content_type='application/json',
                      body=self.BODY_SINGLE_USER)

        y = SCIMResolver()
        y.loadConfig({'Authserver': self.AUTHSERVER, 'Resourceserver':
            self.RESOURCESERVER, 'Client': self.CLIENT, 'Secret':
            self.SECRET, 'Mapping': "{username: 'userName'}"})

        r = y.getUserInfo("bjensen")
        self.assertEqual(r.get("username"), "bjensen")
        self.assertEqual(r.get("phone"), "555-555-8377")
        self.assertEqual(r.get("givenname"), "Barbara")
        self.assertEqual(r.get("surname"), "Jensen")
        self.assertEqual(r.get("email"), "bjensen@example.com")

        r = y.getUsername("bjensen")
        self.assertEqual(r, "bjensen")

        r = y.getUserId("bjensen")
        self.assertEqual(r, "bjensen")

    @responses.activate
    def test_05_users(self):
        responses.add(responses.GET, self.TOKEN_URL, status=200,
                      content_type='application/json',
                      body=self.BODY_ACCESSTOKEN)
        responses.add(responses.GET, self.USER_URL,
                      status=200, content_type='application/json',
                      body=self.BODY_USERS)

        y = SCIMResolver()
        y.loadConfig({'Authserver': self.AUTHSERVER, 'Resourceserver':
            self.RESOURCESERVER, 'Client': self.CLIENT, 'Secret':
            self.SECRET, 'Mapping': "{}"})

        r = y.getUserList()
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0].get("username"), "bjensen")
        self.assertEqual(r[1].get("username"), "jsmith")

    @responses.activate
    def test_06_failed_get_user(self):
        responses.add(responses.GET, self.TOKEN_URL,
                      status=200, content_type='application/json',
                      body=self.BODY_ACCESSTOKEN)
        responses.add(responses.GET, self.USER_URL+"/jbensen",
                      status=402, content_type='application/json',
                      body=self.BODY_SINGLE_USER)
        # Failed to retrieve access token
        #SCIMResolver._get_user(resource_server=self.RESOURCESERVER,
        #                       access_token="", userid="jbensen")
        self.assertRaises(Exception, SCIMResolver._get_user,
                          resource_server=self.RESOURCESERVER,
                          access_token="", userid="jbensen")

    @responses.activate
    def test_07_failed_search_user(self):
        responses.add(responses.GET, self.TOKEN_URL,
                      status=200, content_type='application/json',
                      body=self.BODY_ACCESSTOKEN)
        responses.add(responses.GET, self.USER_URL,
                      status=402, content_type='application/json',
                      body=self.BODY_SINGLE_USER)
        # Failed to retrieve access token
        #SCIMResolver._search_users(resource_server=self.RESOURCESERVER,
        #                           access_token="")
        self.assertRaises(Exception, SCIMResolver._search_users,
                          resource_server=self.RESOURCESERVER,
                          access_token="")


class LDAPResolverTestCase(MyTestCase):
    """
    Test the LDAP resolver
    """

    @ldap3mock.activate
    def test_00_testconnection(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = {'LDAPURI': 'ldap://localhost',
                  'LDAPBASE': 'o=test',
                  'BINDDN': 'cn=manager,ou=example,o=test',
                  'BINDPW': 'ldaptest',
                  'LOGINNAMEATTRIBUTE': 'cn',
                  'LDAPSEARCHFILTER': '(cn=*)',
                  'USERINFO': '{ "username": "cn", "phone": "telephoneNumber", '
                              '"mobile" : "mobile", "email": "mail", '
                              '"surname" : "sn", "givenname": "givenName" }',
                  'UIDTYPE': 'DN'}
        success, desc = pretestresolver("ldapresolver", params)
        self.assertTrue(success, (success, desc))

        # Now we test a resolver, that is already saved in the database
        # But the UI sends the __CENSORED__ password
        params["resolver"] = "testname1"
        params["type"] = "ldapresolver"
        r = save_resolver(params)
        self.assertTrue(r)
        # Now check the resolver again
        params["BINDPW"] = CENSORED
        success, desc = pretestresolver("ldapresolver", params)
        self.assertTrue(success)
        r = delete_resolver("testname1")
        self.assertTrue(r)

    @ldap3mock.activate
    def test_01_LDAP_DN(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
        })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))

        user = "bob"
        user_id = y.getUserId(user)
        self.assertTrue(user_id == "cn=bob,ou=example,o=test", user_id)

        rid = y.getResolverId()
        self.assertTrue(rid == "035fbc6272907bc79a2c036b5bf9665ca921d558", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        uinfo = y.getUserInfo(user_id)
        self.assertTrue(uinfo.get("username") == "bob", uinfo)

        ret = y.getUserList({"username": "bob"})
        self.assertTrue(len(ret) == 1, ret)

        # user list with searchResRef entries
        # we are mocking the mock here
        original_search = y.l.extend.standard.paged_search
        with mock.patch.object(ldap3mock.Connection.Extend.Standard, 'paged_search') as mock_search:
            def _search_with_ref(*args, **kwargs):
                results = original_search(*args, **kwargs)
                # paged_search returns an iterator
                for result in results:
                    yield result
                yield {'type': 'searchResRef', 'foo': 'bar'}

            mock_search.side_effect = _search_with_ref
            ret = y.getUserList({"username": "bob"})
            self.assertTrue(mock_search.called)
            self.assertTrue(len(ret) == 1, ret)

        username = y.getUsername(user_id)
        self.assertTrue(username == "bob", username)

        pw = "bobpwééé"
        res = y.checkPass(user_id, pw)
        self.assertTrue(res)
        self.assertTrue(y.checkPass(user_id, pw.encode('utf8')))

        res = y.checkPass(user_id, "wrong pw")
        self.assertFalse(res)

    @ldap3mock.activate
    def test_01_LDAP_double_mapping(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "email", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'DN',
        })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))

        user = "bob"
        user_id = y.getUserId(user)
        self.assertEqual("cn=bob,ou=example,o=test", user_id)

        rid = y.getResolverId()
        self.assertEqual('2a92363e3f9da66321d9ff71b3cd0c464e990b02', rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        # Use email as logon name
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'email',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "email", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'DN',
                      })

        uinfo = y.getUserInfo("cn=bob,ou=example,o=test")
        self.assertTrue(uinfo.get("email") == "bob@example.com", uinfo)

        ret = y.getUserList({"username": "bob@example.com"})
        self.assertTrue(len(ret) == 1, ret)

        username = y.getUsername(user_id)
        self.assertTrue(username == "bob@example.com", username)

        res = y.checkPass(user_id, "bobpwééé")
        self.assertTrue(res)

        res = y.checkPass(user_id, "wrong pw")
        self.assertFalse(res)


    @ldap3mock.activate
    def test_01_broken_uidtype(self):
        # checkPass with wrong UIDtype
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
                      'UIDTYPE': 'unknownType',
                      'CACHE_TIMEOUT': 0
        })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))

        rid = y.getResolverId()
        self.assertTrue(rid == "035fbc6272907bc79a2c036b5bf9665ca921d558", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        res = y.checkPass("bob", "bobpwééé")
        self.assertFalse(res)

    @ldap3mock.activate
    def test_02_LDAP_OID(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
                      'UIDTYPE': 'oid',
                      'CACHE_TIMEOUT': 0
        })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))

        user = "bob"
        user_id = y.getUserId(user)
        self.assertTrue(user_id == "3", "{0!s}".format(user_id))

        rid = y.getResolverId()
        self.assertTrue(rid == "035fbc6272907bc79a2c036b5bf9665ca921d558", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        uinfo = y.getUserInfo("3")
        self.assertTrue(uinfo.get("username") == "bob", uinfo)

        ret = y.getUserList({"username": "bob"})
        self.assertTrue(len(ret) == 1, ret)

        username = y.getUsername(user_id)
        self.assertTrue(username == "bob", username)

        res = y.checkPass(user_id, "bobpwééé")
        self.assertTrue(res)

        res = y.checkPass(user_id, "wrong pw")
        self.assertFalse(res)

    @ldap3mock.activate
    def test_03_testconnection(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        res = y.testconnection({'LDAPURI': 'ldap://localhost',
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
                                'UIDTYPE': 'oid',
                                'CACHE_TIMEOUT': 0
        })

        self.assertTrue(res[0], res)
        self.assertTrue("{!s}".format(len(LDAPDirectory)) in res[1], res[1])
        # 'Your LDAP config seems to be OK, 3 user objects found.'

    @ldap3mock.activate
    def test_03_testconnection_anonymous(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        res = y.testconnection({'LDAPURI': 'ldap://localhost',
                                'LDAPBASE': 'o=test',
                                'LOGINNAMEATTRIBUTE': 'cn',
                                'LDAPSEARCHFILTER': '(cn=*)',
                                'BINDDN': '',
                                'USERINFO': '{ "username": "cn",'
                                            '"phone" : "telephoneNumber", '
                                            '"mobile" : "mobile"'
                                            ', "email" : "mail", '
                                            '"surname" : "sn", '
                                            '"givenname" : "givenName" }',
                                'UIDTYPE': 'oid',
                                'CACHE_TIMEOUT': 0
        })

        self.assertTrue(res[0], res)
        self.assertTrue("{!s}".format(len(LDAPDirectory)) in res[1])
        #'Your LDAP config seems to be OK, 3 user objects found.'

    @ldap3mock.activate
    def test_04_testconnection_fail(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        res = y.testconnection({'LDAPURI': 'ldap://localhost',
                                'LDAPBASE': 'o=test',
                                'BINDDN': 'cn=manager,ou=example,o=test',
                                'BINDPW': 'wrongpw',
                                'LOGINNAMEATTRIBUTE': 'cn',
                                'LDAPSEARCHFILTER': '(cn=*)',
                                'USERINFO': '{ "username": "cn",'
                                            '"phone" : "telephoneNumber", '
                                            '"mobile" : "mobile"'
                                            ', "email" : "mail", '
                                            '"surname" : "sn", '
                                            '"givenname" : "givenName" }',
                                'UIDTYPE': 'oid',
                                'CACHE_TIMEOUT': 0
        })

        self.assertFalse(res[0], res)
        self.assertTrue("Wrong credentials" in res[1], res)

    @ldap3mock.activate
    def test_05_authtype_not_supported(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        res = y.testconnection({'LDAPURI': 'ldap://localhost',
                                'LDAPBASE': 'o=test',
                                'BINDDN': 'cn=manager,ou=example,o=test',
                                'BINDPW': 'ldaptest',
                                'AUTHTYPE': 'unknown',
                                'LOGINNAMEATTRIBUTE': 'cn',
                                'LDAPSEARCHFILTER': '(cn=*)',
                                'USERINFO': '{ "username": "cn",'
                                            '"phone" : "telephoneNumber", '
                                            '"mobile" : "mobile"'
                                            ', "email" : "mail", '
                                            '"surname" : "sn", '
                                            '"givenname" : "givenName" }',
                                'UIDTYPE': 'oid',
                                'CACHE_TIMEOUT': 0
        })

        self.assertFalse(res[0], res)
        self.assertTrue("Authtype unknown not supported" in res[1], res)

    def test_06_split_uri(self):
        uri = "ldap://server"
        server, port, ssl = LDAPResolver.split_uri(uri)
        self.assertEqual(ssl, False)
        self.assertEqual(server, "server")
        self.assertEqual(port, None)

        uri = "ldap://server:389"
        server, port, ssl = LDAPResolver.split_uri(uri)
        self.assertEqual(ssl, False)
        self.assertEqual(server, "server")
        self.assertEqual(port, 389)

        uri = "ldaps://server:389"
        server, port, ssl = LDAPResolver.split_uri(uri)
        self.assertEqual(ssl, True)
        self.assertEqual(server, "server")
        self.assertEqual(port, 389)

        uri = "ldaps://server"
        server, port, ssl = LDAPResolver.split_uri(uri)
        self.assertEqual(ssl, True)
        self.assertEqual(server, "server")
        self.assertEqual(port, None)

        uri = "server"
        server, port, ssl = LDAPResolver.split_uri(uri)
        self.assertEqual(ssl, False)
        self.assertEqual(server, "server")
        self.assertEqual(port, None)

    def test_07_get_serverpool(self):
        timeout = 5
        urilist = "ldap://themis"
        strategy = "FIRST"
        server_pool = LDAPResolver.create_serverpool(urilist, timeout, strategy=strategy)
        self.assertEqual(len(server_pool), 1)
        self.assertEqual(server_pool.active, SERVERPOOL_ROUNDS)
        self.assertEqual(server_pool.exhaust, SERVERPOOL_SKIP)
        self.assertEqual(server_pool.strategy, "FIRST")

        urilist = "ldap://themis, ldap://server2"
        server_pool = LDAPResolver.create_serverpool(urilist, timeout)
        self.assertEqual(len(server_pool), 2)
        self.assertEqual(server_pool.servers[0].name, "ldap://themis:389")
        self.assertEqual(server_pool.servers[1].name, "ldap://server2:389")

        urilist = "ldap://themis, ldaps://server2"
        server_pool = LDAPResolver.create_serverpool(urilist, timeout)
        self.assertEqual(len(server_pool), 2)
        self.assertEqual(server_pool.servers[0].name, "ldap://themis:389")
        self.assertEqual(server_pool.servers[1].name, "ldaps://server2:636")

        urilist = "ldap://themis, ldaps://server2"
        server_pool = LDAPResolver.create_serverpool(urilist, timeout,
                                                     rounds=5,
                                                     exhaust=60)
        self.assertEqual(len(server_pool), 2)
        self.assertEqual(server_pool.active, 5)
        self.assertEqual(server_pool.exhaust, 60)
        self.assertEqual(server_pool.strategy, "ROUND_ROBIN")

        urilist = "ldap://themis, ldaps://server2"
        server_pool = LDAPResolver.create_serverpool(urilist, timeout,
                                                     rounds=5,
                                                     exhaust=60,
                                                     pool_cls=LockingServerPool)
        self.assertIs(type(server_pool), LockingServerPool)
        self.assertEqual(len(server_pool), 2)
        self.assertEqual(server_pool.active, 5)
        self.assertEqual(server_pool.exhaust, 60)
        self.assertEqual(server_pool.strategy, "ROUND_ROBIN")

    @ldap3mock.activate
    def test_08_trimresult(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
                      'UIDTYPE': 'oid',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
        })
        r = y._trim_result([{"type": "searchResEntry",
                             "DN": "blafoo"},
                            {"type": "searchResEntry",
                             "DN": "foobar"},
                            {"type": "searchResRef",
                             "info": "this is located on another LDAP"}])

        self.assertEqual(len(r), 2)

    @ldap3mock.activate
    def test_09_test_objectGUID(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber",'
                                  '"mobile" : "mobile",'
                                  '"password" : "userPassword",'
                                  '"email" : "mail",'
                                  '"surname" : "sn",'
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
        })
        user_id = y.getUserId("bob")
        res = y.checkPass(user_id, "bobpwééé")
        self.assertTrue(res)

        # Test changing the password
        res = y.update_user(user_id, {"password": "test"})
        self.assertTrue(res)

        user_id = y.getUserId("bob")
        res = y.checkPass(user_id, "test")
        self.assertTrue(res)

    @ldap3mock.activate
    def test_09b_test_curly_braced_objectGUID(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory_curly_objectGUID)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber",'
                                  '"mobile" : "mobile",'
                                  '"password" : "userPassword",'
                                  '"email" : "mail",'
                                  '"surname" : "sn",'
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
        })
        user_id = y.getUserId("bob")
        res = y.checkPass(user_id, "bobpwééé")
        self.assertTrue(res)

        # Test changing the password
        res = y.update_user(user_id, {"password": "test"})
        self.assertTrue(res)

        user_id = y.getUserId("bob")
        self.assertEqual(user_id, objectGUIDs[0])
        self.assertNotIn("{", user_id)
        self.assertNotIn("}", user_id)
        res = y.checkPass(user_id, "test")
        self.assertTrue(res)

    def test_10_escape_loginname(self):
        r = LDAPResolver._escape_loginname("hans*")
        self.assertEqual(r, "hans\\2a")
        r = LDAPResolver._escape_loginname("hans()")
        self.assertEqual(r, "hans\\28\\29")
        r = LDAPResolver._escape_loginname("hans\\/")
        self.assertEqual(r, "hans\\5c\\2f")

    @ldap3mock.activate
    def test_11_extended_userinfo(self):
        # For testing the return of additional SAML attributes.
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
                                  '"givenname" : "givenName",'
                                  '"additionalAttr": "homeDirectory" }',
                      'UIDTYPE': 'DN',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0}
                     )
        uid = y.getUserId("bob")
        self.assertEqual(uid, 'cn=bob,ou=example,o=test')
        userinfo = y.getUserInfo(uid)
        self.assertEqual(userinfo.get("additionalAttr"), "/home/bob")

    @ldap3mock.activate
    def test_12_get_expired_accounts(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
                                  '"givenname" : "givenName", '
                                  '"accountExpires": "accountExpires" }',
                      'UIDTYPE': 'DN',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
        })
        res = y.getUserList({"accountExpires": 1})
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].get("username"), "alice")

    @ldap3mock.activate
    def test_13_add_user_update_delete(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        classes = "top, inetOrgPerson"
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile",'
                                  '"email" : "email",'
                                  '"password" : "userPassword",'
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName", '
                                  '"accountExpires": "accountExpires" }',
                      'OBJECT_CLASSES': classes,
                      'DN_TEMPLATE': "cn=<username>,ou=example,o=test",
                      'UIDTYPE': 'DN',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
        })

        user = "achmed"

        # First we add the user with add_user
        r = y.add_user({"username" : user,
                        "surname" : "Ali",
                        "email" : "achmed.ali@example.com",
                        "password" : "testing123",
                        'mobile': ["1234", "45678"],
                        "givenname" : "Achmed"})
        self.assertTrue(r)

        # Find the new users user_id
        user_id = y.getUserId("achmed")
        self.assertTrue(user_id == "cn=achmed,ou=example,o=test", user_id)

        # Test changing the password
        r = y.update_user(user_id, {"password": "test"})
        self.assertTrue(r)

        # Test checking the password
        r = y.checkPass(user_id, "test")
        self.assertTrue(r)

        # Test MODIFY_DELETE
        r = y.update_user(user_id, {"email": ""})
        self.assertTrue(r)
        userinfo = y.getUserInfo(user_id)
        self.assertFalse(userinfo.get("email"))

        # Test MODIFY_REPLACE
        r = y.update_user(user_id, {"surname": "Smith"})
        self.assertTrue(r)
        userinfo = y.getUserInfo(user_id)
        self.assertEqual(userinfo.get("surname"), "Smith")

        # Test MODIFY_ADD
        r = y.update_user(user_id, {"email": "bob@testing.com"})
        self.assertTrue(r)
        userinfo = y.getUserInfo(user_id)
        self.assertEqual(userinfo.get("email"), "bob@testing.com")

        # Test multiple changes in a single transaction
        r = y.update_user(user_id, {"email": "",
                                    "givenname": "Charlie"})
        self.assertTrue(r)
        userinfo = y.getUserInfo(user_id)
        self.assertEqual(userinfo.get("givenname"), "Charlie")
        self.assertFalse(userinfo.get("email"))

        # Now we delete the user with add_user
        y.delete_user(user_id)
        # Now there should be no achmed anymore
        user_id = y.getUserId("achmed")
        self.assertFalse(user_id)

    @ldap3mock.activate
    def test_14_add_user_update_delete_objectGUID(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        classes = 'top, inetOrgPerson'
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile",'
                                  '"email" : "email",'
                                  '"userid" : "objectGUID",'
                                  '"password" : "userPassword",'
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName", '
                                  '"accountExpires": "accountExpires" }',
                      'UIDTYPE': 'objectGUID',
                      'DN_TEMPLATE': 'cn=<username>,ou=example,o=test',
                      'OBJECT_CLASSES': classes,
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
        })

        user = "achmed"
        uid_bin = uuid.uuid4().bytes
        user_id = str(uuid.UUID(bytes_le=uid_bin))

        attributes = {"username": user,
                      "surname": "Ali",
                      "userid": user_id,
                      "email": "achmed.ali@example.com",
                      "password": "testing123",
                      'mobile': ["1234", "45678"],
                      "givenname": "Achmed"}

        # First we add the user with add_user
        r = y.add_user(attributes)
        self.assertTrue(r)

        # Now we delete the user with add_user
        y.delete_user(user_id)
        # Now there should be no achmed anymore
        user_id = y.getUserId("achmed")
        self.assertFalse(user_id)

    @ldap3mock.activate
    def test_21_test_objectGUID_getUserInfo(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
                      })
        user_id = y.getUserId("bob")
        user_info = y.getUserInfo(user_id)
        self.assertEqual(user_info.get("username"), "bob")
        self.assertEqual(user_info.get("surname"), "Marley")
        self.assertEqual(user_info.get("givenname"), "Robert")

    @ldap3mock.activate
    def test_22_caching_two_ldaps(self):
        # This test checks, if the cached values are seperated for two
        # different resolvers. Alice is cached as not found in the first
        # resolver but alice will be found in the other resolver.
        ldap3mock.setLDAPDirectory(LDAPDirectory_small)
        y = LDAPResolver()
        # We add :789 to the LDAPURI in order to force a unused resolver ID.
        # If we omit it, the test occasionally fails because of leftover
        # cache entries from a resolver with the same resolver ID
        # that was instantiated in the test_api_validate.py tests.
        y.loadConfig({'LDAPURI': 'ldap://localhost:789',
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
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 120
                      })

        # in the small LDAP there is no user "alice"!
        user_id = y.getUserId("alice")
        self.assertEqual(user_id, "")

        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn",'
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 120
                      })

        # but in the full LDAP there is a "alice". We need to find it, since it
        # is not cached yet in the new resolver cache
        user_id = y.getUserId("alice")
        user_info = y.getUserInfo(user_id)
        self.assertEqual(user_info.get("username"), "alice")
        self.assertEqual(user_info.get("surname"), "Cooper")
        self.assertEqual(user_info.get("givenname"), "Alice")

    @ldap3mock.activate
    def test_23_start_tls(self):
        # Check that START_TLS and TLS_VERIFY are actually passed to the ldap3 Connection
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        config = {'LDAPURI': 'ldap://localhost',
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
                  'UIDTYPE': 'unknownType',
                  'CACHE_TIMEOUT': 0,
                  'START_TLS': '1',
                  'TLS_VERIFY': '1'
        }
        start_tls_resolver = LDAPResolver()
        start_tls_resolver.loadConfig(config)
        result = start_tls_resolver.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))
        # We check two things:
        # 1) start_tls has actually been called!
        self.assertTrue(start_tls_resolver.l.start_tls_called)
        # 2) All Server objects were constructed with a non-None TLS context, but use_ssl=False
        for _, kwargs in ldap3mock.get_server_mock().call_args_list:
            self.assertIsNotNone(kwargs['tls'])
            self.assertFalse(kwargs['use_ssl'])


    @ldap3mock.activate
    def test_24_ldaps(self):
        # Check that use_ssl and tls are actually passed to the Connection
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        config = {'LDAPURI': 'ldaps://localhost',
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
                  'UIDTYPE': 'unknownType',
                  'CACHE_TIMEOUT': 0,
                  'TLS_VERIFY': '1'
                  }
        start_tls_resolver = LDAPResolver()
        start_tls_resolver.loadConfig(config)
        result = start_tls_resolver.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))
        # We check that all Server objects were constructed with a non-None TLS context and use_ssl=True
        for _, kwargs in ldap3mock.get_server_mock().call_args_list:
            self.assertIsNotNone(kwargs['tls'])
            self.assertTrue(kwargs['use_ssl'])
            ldap3_tls_config = kwargs['tls'].__str__()
            self.assertIn("protocol: 2", ldap3_tls_config)
            self.assertIn("CA certificates file: present", ldap3_tls_config)
            self.assertTrue("verify mode: VerifyMode.CERT_REQUIRED" in ldap3_tls_config
                            or "verify mode: 2" in ldap3_tls_config
                            or "verify mode: True" in ldap3_tls_config)

    def test_24b_tls_options(self):
        @ldap3mock.activate
        def check_tls_version_ldap3(tls_version_pi, tls_version_ldap3):

            # Check that START_TLS and TLS_VERIFY are actually passed to the ldap3 Connection
            ldap3mock.setLDAPDirectory(LDAPDirectory)
            config = {'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn"}',
                      'UIDTYPE': 'unknownType',
                      'CACHE_TIMEOUT': 0,
                      'START_TLS': '1',
                      'TLS_VERIFY': '1'
                      }
            config.update({"TLS_VERSION": tls_version_pi})
            start_tls_resolver = LDAPResolver()
            start_tls_resolver.loadConfig(config)
            result = start_tls_resolver.getUserList({'username': '*'})
            self.assertEqual(len(result), len(LDAPDirectory))
            # We check two things:
            # 1) start_tls has actually been called!
            self.assertTrue(start_tls_resolver.l.start_tls_called)
            # 2) All Server objects were constructed with a non-None TLS context and use_ssl=False
            for _, kwargs in ldap3mock.get_server_mock().call_args_list:
                self.assertIsNotNone(kwargs['tls'])
                self.assertFalse(kwargs['use_ssl'])
                ldap3_tls_config = kwargs['tls'].__str__()
                self.assertIn(tls_version_ldap3, ldap3_tls_config)

        tls_versions = {"": "protocol: 2",
                        "5": "protocol: 5",
                        "1234": "protocol: 1234"}
        for tls_version_pi, tls_version_ldap3 in tls_versions.items():
            check_tls_version_ldap3(tls_version_pi, tls_version_ldap3)
        self.assertRaises(ValueError, check_tls_version_ldap3, "version is nonsense", "nothing to check")

    @ldap3mock.activate
    def test_24c_no_tls_verify(self):
        # Check that tls should not verify the server
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        config = {'LDAPURI': 'ldaps://localhost',
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
                  'UIDTYPE': 'unknownType',
                  'CACHE_TIMEOUT': 0,
                  'TLS_CA_FILE': '/unknown/path/to/ca_certs.crt',
                  'TLS_VERIFY': '0'
                  }
        start_tls_resolver = LDAPResolver()
        start_tls_resolver.loadConfig(config)
        result = start_tls_resolver.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))
        # We check that all Server objects were constructed with a non-None TLS context and use_ssl=True
        for _, kwargs in ldap3mock.get_server_mock().call_args_list:
            self.assertIsNotNone(kwargs['tls'])
            self.assertTrue(kwargs['use_ssl'])
            self.assertEqual(2, kwargs['tls'].version, kwargs['tls'])
            # the ca_certs_file should be None since we passed a non-existing path
            self.assertIsNone(kwargs['tls'].ca_certs_file, kwargs['tls'])
            self.assertEqual(ssl.CERT_NONE, kwargs['tls'].validate, kwargs['tls'])

    @ldap3mock.activate
    def test_25_LDAP_DN_with_utf8(self):
        # This tests usernames are entered in the LDAPresolver as utf-8 encoded
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
                      })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))

        user = "kölbel".encode('utf8')
        user_id = y.getUserId(user)
        self.assertEqual(user_id, "cn=kölbel,ou=example,o=test")

        rid = y.getResolverId()
        self.assertTrue(rid == "035fbc6272907bc79a2c036b5bf9665ca921d558", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        uinfo = y.getUserInfo(user_id)
        self.assertEqual(to_bytes(uinfo.get("username")), user, uinfo)

        ret = y.getUserList({"username": user})
        self.assertTrue(len(ret) == 1, ret)

        username = y.getUsername(user_id)
        self.assertTrue(to_bytes(username) == user, username)

        res = y.checkPass(user_id, "mySecret")
        self.assertTrue(res)

        res = y.checkPass(user_id, "wrong pw")
        self.assertFalse(res)

    @ldap3mock.activate
    def test_26_LDAP_DN_with_unicode(self):
        # This tests usernames are entered in the LDAPresolver as unicode.
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
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
                      })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))

        user = "kölbel"
        user_id = y.getUserId(user)
        self.assertEqual(user_id, "cn=kölbel,ou=example,o=test")

        rid = y.getResolverId()
        self.assertTrue(rid == "035fbc6272907bc79a2c036b5bf9665ca921d558", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        uinfo = y.getUserInfo(user_id)
        self.assertEqual(to_unicode(uinfo.get("username")), user, uinfo)

        ret = y.getUserList({"username": user})
        self.assertTrue(len(ret) == 1, ret)

        username = y.getUsername(user_id)
        self.assertTrue(to_unicode(username) == user, username)

        res = y.checkPass(user_id, "mySecret")
        self.assertTrue(res)

        res = y.checkPass(user_id, "wrong pw")
        self.assertFalse(res)

    @ldap3mock.activate
    def test_27_LDAP_multiple_loginnames(self):
        # This tests usernames are entered in the LDAPresolver as unicode.
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn, email',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "email", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'DN',
                      })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))

        user = "kölbel"
        user_id = y.getUserId(user)
        self.assertEqual(user_id, "cn=kölbel,ou=example,o=test")

        username = "cko@o"
        user_id = y.getUserId(username)
        self.assertEqual(user_id, "cn=kölbel,ou=example,o=test")

    @ldap3mock.activate
    def test_28_LDAP_multivalues(self):
        # This tests usernames are entered in the LDAPresolver as unicode.
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn, email',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "email", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName",'
                                  '"piAttr": "someAttr"}',
                      'UIDTYPE': 'DN',
                      'MULTIVALUEATTRIBUTES': "['piAttr']"
                      })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), len(LDAPDirectory))

        user = "kölbel"
        user_id = y.getUserId(user)
        self.assertEqual(user_id, "cn=kölbel,ou=example,o=test")
        info = y.getUserInfo(user_id)
        self.assertTrue("value1" in info.get("piAttr"))
        self.assertTrue("value2" in info.get("piAttr"))

    @ldap3mock.activate
    def test_29_sizelimit(self):
        # This tests usernames are entered in the LDAPresolver as unicode.
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn, email',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "email", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName",'
                                  '"piAttr": "someAttr"}',
                      'UIDTYPE': 'DN',
                      "SIZELIMIT": "3"
                      })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), 3)

        # We imitate ldap3 2.4.1 and raise an exception without having returned any entries
        original_search = y.l.extend.standard.paged_search
        with mock.patch.object(ldap3mock.Connection.Extend.Standard, 'paged_search') as mock_search:
            def _search_with_exception(*args, **kwargs):
                results = original_search(*args, **kwargs)
                raise LDAPOperationResult(result=RESULT_SIZE_LIMIT_EXCEEDED)
                # This ``yield`` is needed to turn this function into a generator.
                # If we omit this, the exception above would be raised immediately when ``paged_search`` is called.
                yield

            mock_search.side_effect = _search_with_exception
            ret = y.getUserList({"username": "*"})
            self.assertTrue(mock_search.called)
            # We get all three entries, due to the workaround in ``ignore_sizelimit_exception``!
            self.assertEqual(len(ret), 3)


        # We imitate a hypothetical later ldap3 version and raise an exception *after having returned all entries*!
        # As ``getUserList`` stops consuming the generator after the size limit has been reached, we can only
        # test this using testconnection.
        with mock.patch.object(ldap3mock.Connection.Extend.Standard, 'paged_search', autospec=True) as mock_search:
            # This is essentially a reimplementation of ``paged_search``
            def _search_with_exception(self, **kwargs):
                self.connection.search(search_base=kwargs.get("search_base"),
                                       search_scope=kwargs.get("search_scope"),
                                       search_filter=kwargs.get(
                                           "search_filter"),
                                       attributes=kwargs.get("attributes"),
                                       paged_size=kwargs.get("page_size"),
                                       size_limit=kwargs.get("size_limit"),
                                       paged_cookie=None)
                result = self.connection.response
                assert kwargs['generator']
                # Only return one result
                yield result[0]
                raise LDAPOperationResult(result=RESULT_SIZE_LIMIT_EXCEEDED)

            mock_search.side_effect = _search_with_exception
            ret = y.testconnection({'LDAPURI': 'ldap://localhost',
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
                                    'UIDTYPE': 'oid',
                                    'CACHE_TIMEOUT': 0,
                                    'SIZELIMIT': '1',
                                    })
            self.assertTrue(mock_search.called)
            # We do not get any duplicate entries, due to the workaround in ``ignore_sizelimit_exception``!
            self.assertTrue(ret[0])
            self.assertTrue(ret[1] in ['Your LDAP config seems to be OK, 1 user objects found.',
                                       'Die LDAP-Konfiguration scheint in Ordnung zu sein. Es wurden 1 Benutzer-Objekte gefunden.'],
                            ret[1])


    @ldap3mock.activate
    def test_30_login_with_objectGUID(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        classes = 'top, inetOrgPerson'
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn,objectGUID, email',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile",'
                                  '"email" : "email",'
                                  '"userid" : "objectGUID",'
                                  '"password" : "userPassword",'
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName", '
                                  '"accountExpires": "accountExpires" }',
                      'UIDTYPE': 'objectGUID',
                      'DN_TEMPLATE': 'cn=<username>,ou=example,o=test',
                      'OBJECT_CLASSES': classes,
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
                      })

        # Alice, the email address and objectGUID of alice return the same uid.
        uid = y.getUserId("alice")
        self.assertEqual(uid, objectGUIDs[0])
        uid = y.getUserId(objectGUIDs[0])
        self.assertEqual(uid, objectGUIDs[0])
        uid = y.getUserId("alice@test.com")
        self.assertEqual(uid, objectGUIDs[0])

    @ldap3mock.activate
    def test_31_login_with_objectGUID_only(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        classes = 'top, inetOrgPerson'
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'objectGUID',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile",'
                                  '"email" : "email",'
                                  '"userid" : "objectGUID",'
                                  '"password" : "userPassword",'
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName", '
                                  '"accountExpires": "accountExpires" }',
                      'UIDTYPE': 'objectGUID',
                      'DN_TEMPLATE': 'cn=<username>,ou=example,o=test',
                      'OBJECT_CLASSES': classes,
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
                      })

        # We can now authenticate using the objectGUID
        uid = y.getUserId(objectGUIDs[0])
        self.assertEqual(uid, objectGUIDs[0])

        info = y.getUserInfo(uid)
        self.assertEqual(info['username'], objectGUIDs[0])

    @ldap3mock.activate
    def test_32_cache_expiration(self):
        # This test checks if the short-living cache deletes expired
        # entries. NOTE: This does not test a multi-threaded scenario!
        ldap3mock.setLDAPDirectory(LDAPDirectory_small)
        cache_timeout = 120
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(&(cn=*))', # we use this weird search filter to get a unique resolver ID
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': cache_timeout
                      })
        from privacyidea.lib.resolvers.LDAPIdResolver import CACHE
        # assert that the other tests haven't left anything in the cache
        self.assertNotIn(y.getResolverId(), CACHE)
        bob_id = y.getUserId('bob')
        # assert the cache contains this entry
        self.assertEqual(CACHE[y.getResolverId()]['getUserId']['bob']['value'], bob_id)
        # assert subsequent requests for the same data hit the cache
        with mock.patch.object(ldap3mock.Connection, 'search') as mock_search:
            bob_id2 = y.getUserId('bob')
            self.assertEqual(bob_id, bob_id2)
            mock_search.assert_not_called()
        self.assertIn('bob', CACHE[y.getResolverId()]['getUserId'])
        # assert requests later than CACHE_TIMEOUT seconds query the directory again
        now = datetime.datetime.now()
        with mock.patch('privacyidea.lib.resolvers.LDAPIdResolver.datetime.datetime',
                        wraps=datetime.datetime) as mock_datetime:
            # we now live CACHE_TIMEOUT + 2 seconds in the future
            mock_datetime.now.return_value = now + datetime.timedelta(seconds=cache_timeout + 2)
            with mock.patch.object(ldap3mock.Connection, 'search', wraps=y.l.search) as mock_search:
                bob_id3 = y.getUserId('bob')
                self.assertEqual(bob_id, bob_id3)
                mock_search.assert_called_once()
        # assert the cache contains this entry, with the updated timestamp
        self.assertEqual(CACHE[y.getResolverId()]['getUserId']['bob'],
                         {'value': bob_id,
                          'timestamp': now + datetime.timedelta(seconds=cache_timeout + 2)})
        # we now go 2 * (CACHE_TIMEOUT + 2) seconds to the future and query for someone else's user ID.
        # This will cause bob's cache entry to be evicted.
        with mock.patch('privacyidea.lib.resolvers.LDAPIdResolver.datetime.datetime',
                        wraps=datetime.datetime) as mock_datetime:
            mock_datetime.now.return_value = now + datetime.timedelta(seconds=2 * (cache_timeout + 2))
            manager_id = y.getUserId('manager')
        self.assertEqual(list(CACHE[y.getResolverId()]['getUserId'].keys()), ['manager'])

    @ldap3mock.activate
    def test_33_cache_disabled(self):
        # This test checks if the short-living cache deletes expired
        # entries. NOTE: This does not test a multi-threaded scenario!
        ldap3mock.setLDAPDirectory(LDAPDirectory_small)
        y = LDAPResolver()
        y.loadConfig({'LDAPURI': 'ldap://localhost',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(|(cn=*))', # we use this weird search filter to get a unique resolver ID
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True,
                      'CACHE_TIMEOUT': 0
                      })
        from privacyidea.lib.resolvers.LDAPIdResolver import CACHE
        # assert that the other tests haven't left anything in the cache
        self.assertNotIn(y.getResolverId(), CACHE)
        bob_id = y.getUserId('bob')
        # assert the cache does not contain this entry
        self.assertNotIn(y.getResolverId(), CACHE)
        # assert subsequent requests query the directory
        with mock.patch.object(ldap3mock.Connection, 'search', wraps=y.l.search) as mock_search:
            bob_id2 = y.getUserId('bob')
            self.assertEqual(bob_id, bob_id2)
            mock_search.assert_called_once()

    @ldap3mock.activate
    def test_34_censored_tests(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = {'LDAPURI': 'ldap://localhost',
                  'LDAPBASE': 'o=test',
                  'BINDDN': 'cn=manager,ou=example,o=test',
                  'BINDPW': 'ldaptest',
                  'LOGINNAMEATTRIBUTE': 'cn',
                  'LDAPSEARCHFILTER': '(cn=*)',
                  'USERINFO': '{ "username": "cn", "phone": "telephoneNumber", '
                              '"mobile" : "mobile", "email": "mail", '
                              '"surname" : "sn", "givenname": "givenName" }',
                  'UIDTYPE': 'DN'}
        success, desc = pretestresolver("ldapresolver", params)
        self.assertTrue(success, (success, desc))

        # Now we test a resolver, that is already saved in the database
        # But the UI sends the __CENSORED__ password. The resolver password stays the same
        params["resolver"] = "testname1"
        params["type"] = "ldapresolver"
        r = save_resolver(params)
        self.assertTrue(r)
        # Now save the resolver with a censored password
        params["BINDPW"] = CENSORED
        r = save_resolver(params)
        self.assertTrue(r)
        # Check the password in the DB. It is the originial one, not "__CENSORED__".
        c = get_resolver_config("testname1")
        self.assertEqual(c.get("BINDPW"), "ldaptest")
        r = delete_resolver("testname1")
        self.assertTrue(r)

    @ldap3mock.activate
    def test_35_persistent_serverpool(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = {'LDAPURI': 'ldap://localhost, ldap://127.0.0.1, ldap://127.0.1.1',
                      'LDAPBASE': 'o=test',
                      'BINDDN': 'cn=manager,ou=example,o=test',
                      'BINDPW': 'ldaptest',
                      'LOGINNAMEATTRIBUTE': 'cn',
                      'LDAPSEARCHFILTER': '(cn=*)',
                      'USERINFO': '{ "username": "cn", "phone": "telephoneNumber", '
                                  '"mobile" : "mobile", "email": "mail", '
                                  '"surname" : "sn", "givenname": "givenName" }',
                      'UIDTYPE': 'DN',
                      'CACHE_TIMEOUT': '0', # to disable the per-process cache
                      'resolver': 'testpool',
                      'type': 'ldapresolver'}
        y1 = LDAPResolver()
        y1.loadConfig(params)
        y2 = LDAPResolver()
        y2.loadConfig(params)
        # Make a query, so that a ServerPool is instantiated
        y1.getUserId('bob')
        y2.getUserId('bob')
        # We haven't configured a persistent serverpool, so every resolver has its own ServerPool
        self.assertIs(type(y1.serverpool), ldap3.ServerPool)
        self.assertIs(type(y2.serverpool), ldap3.ServerPool)
        self.assertIsNot(y1.serverpool, y2.serverpool)
        # Now, we configure a persistent serverpool
        params["SERVERPOOL_PERSISTENT"] = "true"
        y3 = LDAPResolver()
        y3.loadConfig(params)
        y4 = LDAPResolver()
        y4.loadConfig(params)
        y3.getUserId('bob')
        y4.getUserId('bob')
        # The resolvers share a ServerPool
        self.assertIs(type(y3.serverpool), LockingServerPool)
        self.assertIs(type(y4.serverpool), LockingServerPool)
        self.assertIs(y3.serverpool, y4.serverpool)

    def test_36_locking_serverpool(self):
        # check that the LockingServerPool correctly forwards all relevant method calls
        pool = LockingServerPool()
        pool.add(ldap3.Server('server1'))
        pool.add(ldap3.Server('server2'))
        with mock.patch('ldap3.ServerPool.initialize') as mock_method:
            pool.initialize(None)
            mock_method.assert_called_once()
        with mock.patch('ldap3.ServerPool.get_server') as mock_method:
            pool.get_server(None)
            mock_method.assert_called_once()
        with mock.patch('ldap3.ServerPool.get_current_server') as mock_method:
            pool.get_current_server(None)
            mock_method.assert_called_once()

class BaseResolverTestCase(MyTestCase):

    def test_00_basefunctions(self):
        resolver = UserIdResolver()
        r = resolver.add_user({"name": "tester"})
        self.assertEqual(r, None)

        r = resolver.delete_user("hans")
        self.assertEqual(r, None)

        r = resolver.update_user(1, {"surname": "schmidt"})
        self.assertEqual(r, None)

        r = UserIdResolver.testconnection({})
        self.assertEqual(r[0], False)
        self.assertEqual(r[1], "Not implemented")

class ResolverTestCase(MyTestCase):
    """
    Test the Passwdresolver
    """
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"

    def test_01_create_resolver(self):
        rid = save_resolver({"resolver": self.resolvername1,
                               "type": "passwdresolver",
                               "fileName": "/etc/passwd",
                               "type.fileName": "string",
                               "desc.fileName": "The name of the file"})
        self.assertTrue(rid > 0, rid)

        # description with missing main key
        params = {"resolver": "reso2",
                  "type": "passwdresolver",
                  "type.fileName": "string"}
        self.assertRaises(Exception, save_resolver, params)

        # type with missing main key
        params = {"resolver": "reso2",
                  "type": "passwdresolver",
                  "desc.fileName": "The file name"}
        self.assertRaises(Exception, save_resolver, params)

        # not allowed resolver name
        params = {"resolver": "res with blank",
                  "type": "passwdresolver"}
        self.assertRaises(Exception, save_resolver, params)

        # unknown type
        params = {"resolver": "validname",
                  "type": "unknown_type"}
        self.assertRaises(Exception, save_resolver, params)

        # same name with different type
        params = {"resolver": self.resolvername1,
                  "type": "ldapresolver",
                  "fileName": "/etc/secrets"}
        self.assertRaises(Exception, save_resolver, params)

        # similar name with different type
        params = {"resolver": "Resolver1",
                  "type": "ldapresolver",
                  "fileName": "/etc/secrets"}
        self.assertRaises(Exception, save_resolver, params)

        # check that the resolver was successfully created
        reso_list = get_resolver_list()
        self.assertTrue(self.resolvername1 in reso_list)

        # test error: type without data
        params = {"resolver": self.resolvername2,
                  "type": "ldapresolver",
                  "type.BindPW": "topsecret"}
        self.assertRaises(Exception, save_resolver, params)

        # test error: description without data
        params = {"resolver": self.resolvername2,
                  "type": "ldapresolver",
                  "desc.BindPW": "something else"}
        self.assertRaises(Exception, save_resolver, params)

        # key not supported by the resolver
        # The resolver is created anyway
        params = {"resolver": self.resolvername2,
                  "type": "passwdresolver",
                  "UnknownKey": "something else"}
        rid = save_resolver(params)
        self.assertTrue(rid > 0)

        # check that the resolver was successfully created
        reso_list = get_resolver_list()
        self.assertTrue(self.resolvername2 in reso_list)

    def test_02_get_resolver_list(self):
        reso_list = get_resolver_list(filter_resolver_name=self.resolvername1)
        self.assertTrue(self.resolvername1 in reso_list, reso_list)
        self.assertTrue(self.resolvername2 not in reso_list, reso_list)

        params = {"resolver": "editableReso",
                  "type": "ldapresolver",
                  'LDAPURI': 'ldap://localhost',
                  'LDAPBASE': 'o=test',
                  'BINDDN': 'cn=manager,ou=example,o=test',
                  'BINDPW': 'ldaptest',
                  'LOGINNAMEATTRIBUTE': 'cn',
                  'LDAPSEARCHFILTER': '(cn=*)',
                  'USERINFO': '{ "username": "cn","phone" : "telephoneNumber", '
                              '"mobile" : "mobile", "email" : "mail", '
                              '"surname" : "sn", "givenname" : "givenName" }',
                  'UIDTYPE': 'DN',
                  'EDITABLE': True,
                  'CACHE_TIMEOUT': 0}
        r = save_resolver(params)
        self.assertTrue(r)
        reso_list = get_resolver_list(editable=True)
        self.assertTrue(len(reso_list) == 1)
        r = delete_resolver("editableReso")
        self.assertTrue(r)

        reso_list = get_resolver_list(editable=False)
        self.assertEqual(len(reso_list), 2)

        reso_list = get_resolver_list(filter_resolver_type="passwdresolver")
        self.assertTrue(len(reso_list) == 2)

    def test_03_get_resolver_config(self):
        reso_config = get_resolver_config(self.resolvername2)
        self.assertTrue("UnknownKey" in reso_config, reso_config)

    def test_04_if_a_resolver_exists(self):
        reso_list = get_resolver_list()
        self.assertTrue(self.resolvername1 in reso_list)
        self.assertTrue("some other" not in reso_list)

    def test_05_create_resolver_object(self):
        from privacyidea.lib.resolvers.PasswdIdResolver import IdResolver

        reso_obj = get_resolver_object(self.resolvername1)
        self.assertTrue(isinstance(reso_obj, IdResolver), type(reso_obj))

        # resolver, that does not exist
        reso_obj = get_resolver_object("unknown")
        self.assertTrue(reso_obj is None, reso_obj)

    def test_10_delete_resolver(self):
        # get the list of the resolvers
        reso_list = get_resolver_list()
        self.assertTrue(self.resolvername1 in reso_list, reso_list)
        self.assertTrue(self.resolvername2 in reso_list, reso_list)

        # delete the resolvers
        delete_resolver(self.resolvername1)
        delete_resolver(self.resolvername2)

        # check list empty
        reso_list = get_resolver_list()
        self.assertTrue(self.resolvername1 not in reso_list, reso_list)
        self.assertTrue(self.resolvername2 not in reso_list, reso_list)
        self.assertTrue(len(reso_list) == 0, reso_list)

    def test_11_base_resolver_class(self):
        save_resolver({"resolver": "baseresolver",
                       "type": "UserIdResolver"})
        y = get_resolver_object("baseresolver")
        self.assertTrue(y, y)
        rtype = y.getResolverType()
        self.assertTrue(rtype == "UserIdResolver", rtype)
        # close hook
        desc = y.getResolverDescriptor()
        self.assertTrue("clazz" in desc.get("UserIdResolver"), desc)
        self.assertTrue("config" in desc.get("UserIdResolver"), desc)

        id = y.getUserId("some user")
        self.assertTrue(id == "dummy_user_id", id)
        name = y.getUsername("some user")
        self.assertTrue(name == "dummy_user_name", name)

        self.assertTrue(y.getUserInfo("dummy") == {})
        self.assertTrue(len(y.getUserList()) == 1)
        self.assertTrue(len(y.getUserList()) == 1)
        rid = y.getResolverId()
        self.assertTrue(rid == "baseid", rid)
        self.assertFalse(y.checkPass("dummy", "pw"))
        y.close()

    def test_12_passwdresolver(self):
        # Create a resolver with an empty filename
        # will use the filename /etc/passwd
        rid = save_resolver({"resolver": self.resolvername1,
                               "type": "passwdresolver",
                               "fileName": "",
                               "type.fileName": "string",
                               "desc.fileName": "The name of the file"})
        self.assertTrue(rid > 0, rid)
        y = get_resolver_object(self.resolvername1)
        y.loadFile()
        delete_resolver(self.resolvername1)

        # Load a file with an empty line
        rid = save_resolver({"resolver": self.resolvername1,
                               "type": "passwdresolver",
                               "fileName": PWFILE,
                               "type.fileName": "string",
                               "desc.fileName": "The name of the file"})
        self.assertTrue(rid > 0, rid)
        y = get_resolver_object(self.resolvername1)
        y.loadFile()

        ulist = y.getUserList({"username": "*"})
        self.assertTrue(len(ulist) > 1, ulist)

        self.assertTrue(y.checkPass("1000", "test"))
        self.assertFalse(y.checkPass("1000", "wrong password"))
        self.assertRaises(NotImplementedError, y.checkPass, "1001", "secret")
        self.assertFalse(y.checkPass("1002", "no pw at all"))
        self.assertTrue(y.getUsername("1000") == "cornelius",
                        y.getUsername("1000"))
        self.assertTrue(y.getUserId("cornelius") == "1000",
                        y.getUserId("cornelius"))
        self.assertTrue(y.getUserId("user does not exist") == "")
        # Check that non-ASCII user was read successfully
        self.assertEqual(y.getUsername("1116"), "nönäscii")
        self.assertEqual(y.getUserId("nönäscii"), "1116")
        self.assertEqual(y.getUserInfo("1116").get('givenname'),
                         "Nön")
        self.assertFalse(y.checkPass("1116", "wrong"))
        self.assertTrue(y.checkPass("1116", "pässwörd"))
        r = y.getUserList({"username": "*ö*"})
        self.assertEqual(len(r), 1)

        sF = y.getSearchFields({"username": "*"})
        self.assertTrue(sF.get("username") == "text", sF)
        # unknown search fields. We get an empty userlist
        r = y.getUserList({"blabla": "something"})
        self.assertTrue(r == [], r)
        # list exactly one user
        r = y.getUserList({"userid": "=1000"})
        self.assertTrue(len(r) == 1, r)
        r = y.getUserList({"userid": "<1001"})
        self.assertTrue(len(r) == 1, r)
        r = y.getUserList({"userid": ">1000"})
        self.assertTrue(len(r) > 1, r)
        r = y.getUserList({"userid": "between 1000, 1001"})
        self.assertTrue(len(r) == 2, r)
        r = y.getUserList({"userid": "between 1001, 1000"})
        self.assertTrue(len(r) == 2, r)
        r = y.getUserList({"userid": "<=1000"})
        self.assertTrue(len(r) == 1, "{0!s}".format(r))
        r = y.getUserList({"userid": ">=1000"})
        self.assertTrue(len(r) > 1, r)

        r = y.getUserList({"description": "field1"})
        self.assertTrue(len(r) == 0, r)
        r = y.getUserList({"email": "field1"})
        self.assertTrue(len(r) == 0, r)

        rid = y.getResolverId()
        self.assertTrue(rid == PWFILE, rid)
        rtype = y.getResolverType()
        self.assertTrue(rtype == "passwdresolver", rtype)
        rdesc = y.getResolverDescriptor()
        self.assertTrue("config" in rdesc.get("passwdresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("passwdresolver"), rdesc)
        # internal stringMatch function
        self.assertTrue(y._stringMatch("Hallo", "*lo"))
        self.assertTrue(y._stringMatch("Hallo", "Hal*"))
        self.assertFalse(y._stringMatch("Duda", "Hal*"))
        self.assertTrue(y._stringMatch("HalloDuda", "*Du*"))
        self.assertTrue(y._stringMatch("Duda", "Duda"))

    @ldap3mock.activate
    def test_13_update_resolver(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # --------------------------------
        # First we create an LDAP resolver
        rid = save_resolver({"resolver": "myLDAPres",
                               "type": "ldapresolver",
                               'LDAPURI': 'ldap://localhost',
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
                               'CACHE_TIMEOUT': 0
        })

        self.assertTrue(rid > 0, rid)
        reso_list = get_resolver_list()
        self.assertTrue("myLDAPres" in reso_list, reso_list)
        ui = ResolverConfig.query.filter(
            ResolverConfig.Key=='USERINFO').first().Value
        # Check that the email is contained in the UI
        self.assertTrue("email" in ui, ui)

        # --------------------------------
        # Then we update the LDAP resolver
        rid = save_resolver({"resolver": "myLDAPres",
                             "type": "ldapresolver",
                             'LDAPURI': 'ldap://localhost',
                               'LDAPBASE': 'o=test',
                               'BINDDN': 'cn=manager,ou=example,o=test',
                               'BINDPW': 'ldaptest',
                               'LOGINNAMEATTRIBUTE': 'cn',
                               'LDAPSEARCHFILTER': '(cn=*)',
                               'USERINFO': '{ "username": "cn",'
                                           '"phone" : "telephoneNumber", '
                                           '"surname" : "sn", '
                                           '"givenname" : "givenName" }',
                               'UIDTYPE': 'DN',
                             'CACHE_TIMEOUT': 0
        })
        self.assertTrue(rid > 0, rid)
        reso_list = get_resolver_list(filter_resolver_name="myLDAPres")
        reso_conf = reso_list.get("myLDAPres").get("data")
        ui = reso_conf.get("USERINFO")
        # Check that the email is NOT contained in the UI
        self.assertTrue("email" not in ui, ui)

    def test_14_censor_resolver(self):
        reso_list = get_resolver_list()
        self.assertEqual(reso_list.get("myLDAPres").get("data").get("BINDPW"), "ldaptest")
        reso_list = get_resolver_list(censor=True)
        self.assertEqual(reso_list.get("myLDAPres").get("data").get("BINDPW"), "__CENSORED__")

    def test_15_try_to_delete_used_resolver(self):
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": "/etc/passwd",
                             "type.fileName": "string",
                             "desc.fileName": "The name of the file"})
        self.assertTrue(rid > 0, rid)
        added, failed = set_realm("myrealm", [self.resolvername1])
        self.assertEqual(added, [self.resolvername1])
        self.assertEqual(failed, [])
        # Trying to delete the resolver fails.
        self.assertRaises(Exception, delete_resolver, self.resolvername1)
        delete_realm("myrealm")
        delete_resolver(self.resolvername1)


class HTTPResolverTestCase(MyTestCase):

    ENDPOINT = 'http://localhost:8080/get-data'
    METHOD = responses.GET
    REQUEST_MAPPING = """
        {"id": "{userid}"}
    """
    HEADERS = """
        {"Content-Type": "application/json", "charset": "UTF-8"}
    """
    RESPONSE_MAPPING = """
        {
            "username": "{data.the_username}",
            "email": "{data.the_email}",
            "mobile": "{data.the_phones.mobile}",
            "a_static_key": "a static value"
        }
    """
    HAS_SPECIAL_ERROR_HANDLER = True
    ERROR_RESPONSE_MAPPING = """
        {"success": false}
    """

    BODY_RESPONSE_OK = """
    {
        "success": true,
        "data": {
            "the_username": "PepePerez",
            "the_email": "pepe@perez.com",
            "the_full_name": "Pepe Perez",
            "the_phones": {
                "mobile": "+1123568974",
                "other": "+1154525894"
            }
        }
    }
    """

    BODY_RESPONSE_NOK = """
    {
        "success": false,
        "data": null
    }
    """

    def test_01_load_config(self):
        params = {
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'headers': self.HEADERS,
            'requestMapping': self.REQUEST_MAPPING,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        }

        # Test with valid data
        instance = HTTPResolver()
        instance.loadConfig(params)
        rid = instance.getResolverId()
        self.assertEqual(rid, self.ENDPOINT)
        r_type = instance.getResolverClassDescriptor()
        self.assertTrue("httpresolver" in r_type)
        r_type = instance.getResolverDescriptor()
        self.assertTrue("httpresolver" in r_type)
        r_type = instance.getResolverType()
        self.assertEqual("httpresolver", r_type)

    def test_02_get_user_list(self):
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'headers': self.HEADERS,
            'requestMapping': self.REQUEST_MAPPING,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        users = instance.getUserList()
        self.assertEqual(len(users), 0)

    def test_03_get_username(self):
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'headers': self.HEADERS,
            'requestMapping': self.REQUEST_MAPPING,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        username = instance.getUsername('pepe_perez')
        self.assertEqual(username, 'pepe_perez')

    def test_04_get_user_id(self):
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'headers': self.HEADERS,
            'requestMapping': self.REQUEST_MAPPING,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        userid = instance.getUserId('pepe_perez')
        self.assertEqual(userid, 'pepe_perez')

    def test_05_get_resolver_id(self):
        instance = HTTPResolver()
        rid = instance.getResolverId()
        self.assertEqual(rid, "")
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'headers': self.HEADERS,
            'requestMapping': self.REQUEST_MAPPING,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        rid = instance.getResolverId()
        self.assertEqual(rid, self.ENDPOINT)

    @responses.activate
    def test_06_get_user(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_OK
        )
        responses.add(
            responses.POST,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_OK
        )

        # Test with valid data (method get)
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'requestMapping': self.REQUEST_MAPPING,
            'headers': self.HEADERS,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        response = instance._getUser('PepePerez')
        self.assertEqual(response.get('username'), 'PepePerez')
        self.assertEqual(response.get('email'), 'pepe@perez.com')
        self.assertEqual(response.get('mobile'), '+1123568974')
        self.assertEqual(response.get('a_static_key'), 'a static value')

        # Test with valid data (method post)
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': 'POST',
            'requestMapping': self.REQUEST_MAPPING,
            'headers': self.HEADERS,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        response = instance._getUser('PepePerez')
        self.assertEqual(response.get('username'), 'PepePerez')
        self.assertEqual(response.get('email'), 'pepe@perez.com')
        self.assertEqual(response.get('mobile'), '+1123568974')
        self.assertEqual(response.get('a_static_key'), 'a static value')

    @responses.activate
    def test_06_get_user_especial_error_handling(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_NOK
        )
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'requestMapping': self.REQUEST_MAPPING,
            'headers': self.HEADERS,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        self.assertRaises(Exception, instance._getUser, userid='PepePerez')

    @responses.activate
    def test_06_get_user_internal_error(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=500,
            adding_headers=json.loads(self.HEADERS),
        )
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'requestMapping': self.REQUEST_MAPPING,
            'headers': self.HEADERS,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        self.assertRaises(HTTPError, instance._getUser, userid='PepePerez')

    @responses.activate
    def test_07_testconnection(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_OK
        )
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_NOK
        )
        param = {
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'requestMapping': self.REQUEST_MAPPING,
            'headers': self.HEADERS,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING,
            'testUser': 'PepePerez'
        }
        success, response = HTTPResolver.testconnection(param)
        self.assertTrue(success)
        self.assertEqual(response.get('username'), 'PepePerez')

        # Test with invalid params
        invalidParam = param.copy()
        invalidParam['testUser'] = None
        success, _ = HTTPResolver.testconnection(invalidParam)
        self.assertFalse(success)

    @responses.activate
    def test_08_get_user_info(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_OK
        )
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_NOK
        )

        # Test with valid response
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'headers': self.HEADERS,
            'requestMapping': self.REQUEST_MAPPING,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        response = instance.getUserInfo('PepePerez')
        self.assertEqual(response.get('username'), 'PepePerez')
        self.assertEqual(response.get('email'), 'pepe@perez.com')
        self.assertEqual(response.get('mobile'), '+1123568974')
        self.assertEqual(response.get('a_static_key'), 'a static value')

        # Test with invalid response
        self.assertRaisesRegex(
            Exception,
            'Received an error while searching for user: PepePerez',
            instance.getUserInfo, 'PepePerez'
        )
