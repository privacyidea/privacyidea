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
import ldap3mock
from ldap3.core.exceptions import LDAPOperationResult
from ldap3.core.results import RESULT_SIZE_LIMIT_EXCEEDED
import mock
import responses
import uuid
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPResolver
from privacyidea.lib.resolvers.SQLIdResolver import IdResolver as SQLResolver
from privacyidea.lib.resolvers.SCIMIdResolver import IdResolver as SCIMResolver
from privacyidea.lib.resolvers.SQLIdResolver import PasswordHash
from privacyidea.lib.resolvers.UserIdResolver import UserIdResolver
from privacyidea.lib.resolvers.LDAPIdResolver import (SERVERPOOL_ROUNDS, SERVERPOOL_SKIP)

from privacyidea.lib.resolver import (save_resolver,
                                      delete_resolver,
                                      get_resolver_config,
                                      get_resolver_list,
                                      get_resolver_object, pretestresolver)
from privacyidea.models import ResolverConfig

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
                                'oid': "1"}}
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
    parameters = {'Driver': 'sqlite',
                  'Server': '/tests/testdata/',
                  'Database': "testuser.sqlite",
                  'Table': 'users',
                  'Encoding': 'utf8',
                  'Passwort_Hash_Type': "SSHA",
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
        self.assertTrue(len(userlist) == 7, len(userlist))

        user = "cornelius"
        user_id = y.getUserId(user)
        self.assertTrue(user_id == 3, user_id)

        rid = y.getResolverId()
        self.assertTrue(rid == "sql.testuser.sqlite", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "sqlresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("sqlresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("sqlresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("sqlresolver"), rdesc)

        uinfo = y.getUserInfo(user_id)
        self.assertTrue(uinfo.get("username") == "cornelius", uinfo)

        ret = y.getUserList({"username": "cornelius"})
        self.assertTrue(len(ret) == 1, ret)

        username = y.getUsername(user_id)
        self.assertTrue(username == "cornelius", username)

    def test_01_where_tests(self):
        y = SQLResolver()
        y.loadConfig(dict(self.parameters.items() + {"Where": "givenname == "
                                                              "hans"}.items()))
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 1, userlist)

        y = SQLResolver()
        y.loadConfig(dict(self.parameters.items() + {"Where": "givenname like "
                                                              "hans"}.items()))
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 1, userlist)

        y = SQLResolver()
        y.loadConfig(
            dict(self.parameters.items() + {"Where": "id > 2"}.items()))
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 5, userlist)

        y = SQLResolver()
        y.loadConfig(dict(self.parameters.items() + {"Where": "id < "
                                                              "5"}.items()))
        userlist = y.getUserList()
        self.assertTrue(len(userlist) == 4, userlist)


    def test_02_check_passwords(self):
        y = SQLResolver()
        y.loadConfig(self.parameters)

        # SHA256 of "dunno"
        # 772cb52221f19104310cd2f549f5131fbfd34e0f4de7590c87b1d73175812607

        result = y.checkPass(3, "dunno")
        print(result)
        assert result is True
        '''
        SHA1 base64 encoded of "dunno"
        Lg8DuLoXOwvPkMABDprnaTp0JOA=
        '''
        result = y.checkPass(2, "dunno")
        assert result is True

        result = y.checkPass(1, "dunno")
        assert result is True

        result = y.checkPass(4, "dunno")
        assert result is True

        result = y.checkPass(5, "dunno")
        assert result is True

        '''
        >>> PH = PasswordHash()
        >>> PH.hash_password("testpassword")
        '$P$Bz4R6lzp6VWCL0SCeTozqKHNV8DM.Q/'
        '''
        result = y.checkPass(6, "testpassword")
        self.assertTrue(result)

    def test_03_testconnection(self):
        y = SQLResolver()
        result = y.testconnection(self.parameters)
        self.assertEqual(result[0], 7)
        self.assertTrue('Found 7 users.' in result[1])

    def test_05_add_user_update_delete(self):
        y = SQLResolver()
        y.loadConfig(self.parameters)
        uid = y.add_user({"username":"achmed",
                          "email": "achmed@world.net",
                          "password": "passw0rd",
                          "mobile": "12345"})
        self.assertTrue(uid > 6)
        self.assertTrue(y.checkPass(uid, "passw0rd"))
        self.assertFalse(y.checkPass(uid, "password"))

        uid = y.getUserId("achmed")
        self.assertTrue(uid > 6)

        r = y.update_user(uid, {"username": "achmed2",
                                "password": "test"})
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
        success, desc = \
            pretestresolver("ldapresolver", {'LDAPURI':
                                                 'ldap://localhost',
                                             'LDAPBASE': 'o=test',
                                             'BINDDN':
                                                 'cn=manager,'
                                                 'ou=example,'
                                                 'o=test',
                                             'BINDPW': 'ldaptest',
                                             'LOGINNAMEATTRIBUTE': 'cn',
                                             'LDAPSEARCHFILTER':
                                                 '(cn=*)',
                                             'USERINFO': '{ '
                                                         '"username": "cn",'
                                                         '"phone" '
                                                         ': '
                                                         '"telephoneNumber", '
                                                         '"mobile" : "mobile"'
                                                         ', '
                                                         '"email" '
                                                         ': '
                                                         '"mail", '
                                                         '"surname" : "sn", '
                                                         '"givenname" : '
                                                         '"givenName" }',
                                             'UIDTYPE': 'DN'})
        self.assertTrue(success, (success, desc))

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
        self.assertTrue(rid == "d6ce19abbc3c23e24e1cefa41cbe6f9f118613b9", rid)

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

        res = y.checkPass(user_id, u"bobpwééé")
        self.assertTrue(res)

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
        self.assertEqual('8372b96a28ff8b4710f4aba838d5f9891ad4e381', rid)

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
        self.assertTrue(rid == "d6ce19abbc3c23e24e1cefa41cbe6f9f118613b9", rid)

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
        self.assertTrue(rid == "d6ce19abbc3c23e24e1cefa41cbe6f9f118613b9", rid)

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
        server_pool = LDAPResolver.get_serverpool(urilist, timeout)
        self.assertEqual(len(server_pool), 1)
        self.assertEqual(server_pool.active, SERVERPOOL_ROUNDS)
        self.assertEqual(server_pool.exhaust, SERVERPOOL_SKIP)
        self.assertEqual(server_pool.strategy, "ROUND_ROBIN")

        urilist = "ldap://themis, ldap://server2"
        server_pool = LDAPResolver.get_serverpool(urilist, timeout)
        self.assertEqual(len(server_pool), 2)
        self.assertEqual(server_pool.servers[0].name, "ldap://themis:389")
        self.assertEqual(server_pool.servers[1].name, "ldap://server2:389")

        urilist = "ldap://themis, ldaps://server2"
        server_pool = LDAPResolver.get_serverpool(urilist, timeout)
        self.assertEqual(len(server_pool), 2)
        self.assertEqual(server_pool.servers[0].name, "ldap://themis:389")
        self.assertEqual(server_pool.servers[1].name, "ldaps://server2:636")

        urilist = "ldap://themis, ldaps://server2"
        server_pool = LDAPResolver.get_serverpool(urilist, timeout,
                                                  rounds=5,
                                                  exhaust=60)
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

        user = u"kölbel".encode("utf-8")
        user_id = y.getUserId(user)
        self.assertEqual(user_id, "cn=kölbel,ou=example,o=test")

        rid = y.getResolverId()
        self.assertTrue(rid == "d6ce19abbc3c23e24e1cefa41cbe6f9f118613b9", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        uinfo = y.getUserInfo(user_id)
        self.assertEqual(uinfo.get("username"), user)

        ret = y.getUserList({"username": user})
        self.assertTrue(len(ret) == 1, ret)

        username = y.getUsername(user_id)
        self.assertTrue(username == "kölbel", username)

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

        user = u"kölbel"
        user_id = y.getUserId(user)
        self.assertEqual(user_id, "cn=kölbel,ou=example,o=test")

        rid = y.getResolverId()
        self.assertTrue(rid == "d6ce19abbc3c23e24e1cefa41cbe6f9f118613b9", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        uinfo = y.getUserInfo(user_id)
        self.assertEqual(uinfo.get("username"), user.encode("utf-8"))

        ret = y.getUserList({"username": user})
        self.assertTrue(len(ret) == 1, ret)

        username = y.getUsername(user_id)
        self.assertTrue(username == user.encode("utf-8"), username)

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

        user = u"kölbel"
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

        user = u"kölbel"
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
            self.assertTrue(ret[1] in [u'Your LDAP config seems to be OK, 1 user objects found.',
                                       u'Die LDAP-Konfiguration scheint in Ordnung zu sein. Es wurden 1 Benutzer-Objekte gefunden.'],
                            ret[1])


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

        reso_list = get_resolver_list(editable=True)
        self.assertTrue(len(reso_list) == 0)

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
        self.assertTrue(y.getUserId(u"cornelius") == "1000",
                        y.getUserId("cornelius"))
        self.assertTrue(y.getUserId("user does not exist") == "")
        # Check that non-ASCII user was read successfully
        self.assertEqual(y.getUsername("1116"), u"nönäscii")
        self.assertEqual(y.getUserId(u"nönäscii"), "1116")
        self.assertEqual(y.getUserInfo("1116").get('givenname'),
                         u"Nön")
        self.assertFalse(y.checkPass("1116", "wrong"))
        self.assertTrue(y.checkPass("1116", u"pässwörd"))
        r = y.getUserList({"username": u"*ö*"})
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
        self.assertTrue(y._stringMatch(u"Hallo", "*lo"))
        self.assertTrue(y._stringMatch("Hallo", u"Hal*"))
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
        # TODO check the data
        ui = ResolverConfig.query.filter(
            ResolverConfig.Key=='USERINFO').first().Value
        # Check that the email is NOT contained in the UI
        self.assertTrue("email" not in ui, ui)

class PasswordHashTestCase(MyTestCase):
    """
    Test the password hashing in the SQL database
    """
    def test_01_get_random_bytes(self):
        ph = PasswordHash()
        rb = ph.get_random_bytes(10)
        self.assertTrue(len(rb) == 10, len(rb))
        rb = ph.get_random_bytes(100)
        self.assertTrue(len(rb) == 100, len(rb))
        _ph = PasswordHash(iteration_count_log2=32)

    def test_02_checkpassword_crypt(self):
        ph = PasswordHash()
        r = ph.check_password("Hallo", "_xyFAfsLH.5Z.Q")
        self.assertTrue(r)

        # Drupal passwords
        r = ph.check_password("mohsen123",
                              "$S$D98Bg3ANTUrjVwx073djifdH1KxbyzXQaPrmbpxGOu4VXFyMClRz")
        self.assertTrue(r)

        r = ph.check_password("DevYubic",
                              "$S$D3f83Mbqy.9SV8Ip1zo7nRauu/4HVFOXfEkfsq.8ryCdFV40DCLl")
        self.assertTrue(r)

        # blowfish crypt
        # user http://www.passwordtool.hu/
        r = ph.check_password("asdasdasd", "$2a$07$4MnpSZo6xAIT7PArFIcO7uc/dfkP60Nuq2KmIQH3rdjrcG9/Ef48.")
        self.assertTrue(r)

        # Wordpress password hash
        r = ph.check_password("asdasdasd", "$P$BkFOEwjLEEQVVJqRp3wANZbH83ZnN6.")
        self.assertTrue(r)
