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
import responses
import uuid
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPResolver
from privacyidea.lib.resolvers.SQLIdResolver import IdResolver as SQLResolver
from privacyidea.lib.resolvers.SCIMIdResolver import IdResolver as SCIMResolver
from privacyidea.lib.resolvers.SQLIdResolver import PasswordHash
from privacyidea.lib.resolvers.UserIdResolver import UserIdResolver

from privacyidea.lib.resolver import (save_resolver,
                                      delete_resolver,
                                      get_resolver_config,
                                      get_resolver_list,
                                      get_resolver_object, pretestresolver)
from privacyidea.models import ResolverConfig

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
                                'oid': "1"}}]


class SQLResolverTestCase(MyTestCase):
    """
    Test the SQL Resolver
    """
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
        self.assertTrue(len(userlist) == 6, len(userlist))

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
        self.assertTrue(len(userlist) == 4, userlist)

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
        self.assertEqual(result[0], 6)
        self.assertTrue('Found 6 users.' in result[1])

    def test_05_add_user_update_delete(self):
        y = SQLResolver()
        y.loadConfig(self.parameters)
        uid = y.add_user({"username":"achmed",
                         "email": "achmed@world.net",
                         "mobile": "12345"})
        self.assertTrue(uid > 6)

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
                                             'LDAPFILTER': '(&('
                                                           'cn=%s))',
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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'DN',
        })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), 3)

        user = "bob"
        user_id = y.getUserId(user)
        self.assertTrue(user_id == "cn=bob,ou=example,o=test", user_id)

        rid = y.getResolverId()
        self.assertTrue(rid == "ldap://localhost", rid)

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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "email",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "email", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'DN',
        })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), 3)

        user = "bob"
        user_id = y.getUserId(user)
        self.assertTrue(user_id == "cn=bob,ou=example,o=test", user_id)

        rid = y.getResolverId()
        self.assertTrue(rid == "ldap://localhost", rid)

        rtype = y.getResolverType()
        self.assertTrue(rtype == "ldapresolver", rtype)

        rdesc = y.getResolverClassDescriptor()
        rdesc = y.getResolverDescriptor()
        self.assertTrue("ldapresolver" in rdesc, rdesc)
        self.assertTrue("config" in rdesc.get("ldapresolver"), rdesc)
        self.assertTrue("clazz" in rdesc.get("ldapresolver"), rdesc)

        uinfo = y.getUserInfo(user_id)
        self.assertTrue(uinfo.get("username") == "bob@example.com", uinfo)

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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'unknownType',
        })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), 3)

        rid = y.getResolverId()
        self.assertTrue(rid == "ldap://localhost", rid)

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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'oid',
        })

        result = y.getUserList({'username': '*'})
        self.assertEqual(len(result), 3)

        user = "bob"
        user_id = y.getUserId(user)
        self.assertTrue(user_id == "3", "{0!s}".format(user_id))

        rid = y.getResolverId()
        self.assertTrue(rid == "ldap://localhost", rid)

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
                                'LDAPFILTER': '(&(cn=%s))',
                                'USERINFO': '{ "username": "cn",'
                                            '"phone" : "telephoneNumber", '
                                            '"mobile" : "mobile"'
                                            ', "email" : "mail", '
                                            '"surname" : "sn", '
                                            '"givenname" : "givenName" }',
                                'UIDTYPE': 'oid',
        })

        self.assertTrue(res[0], res)
        self.assertTrue(res[1] == 'Your LDAP config seems to be OK, 3 user '
                                  'objects found.', res)

    @ldap3mock.activate
    def test_03_testconnection_anonymous(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        y = LDAPResolver()
        res = y.testconnection({'LDAPURI': 'ldap://localhost',
                                'LDAPBASE': 'o=test',
                                'LOGINNAMEATTRIBUTE': 'cn',
                                'LDAPSEARCHFILTER': '(cn=*)',
                                'BINDDN': '',
                                'LDAPFILTER': '(&(cn=%s))',
                                'USERINFO': '{ "username": "cn",'
                                            '"phone" : "telephoneNumber", '
                                            '"mobile" : "mobile"'
                                            ', "email" : "mail", '
                                            '"surname" : "sn", '
                                            '"givenname" : "givenName" }',
                                'UIDTYPE': 'oid',
        })

        self.assertTrue(res[0], res)
        self.assertTrue(res[1] == 'Your LDAP config seems to be OK, 3 user '
                                  'objects found.', res)

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
                                'LDAPFILTER': '(&(cn=%s))',
                                'USERINFO': '{ "username": "cn",'
                                            '"phone" : "telephoneNumber", '
                                            '"mobile" : "mobile"'
                                            ', "email" : "mail", '
                                            '"surname" : "sn", '
                                            '"givenname" : "givenName" }',
                                'UIDTYPE': 'oid',
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
                                'LDAPFILTER': '(&(cn=%s))',
                                'USERINFO': '{ "username": "cn",'
                                            '"phone" : "telephoneNumber", '
                                            '"mobile" : "mobile"'
                                            ', "email" : "mail", '
                                            '"surname" : "sn", '
                                            '"givenname" : "givenName" }',
                                'UIDTYPE': 'oid',
        })

        self.assertFalse(res[0], res)
        self.assertTrue("Authtype unknown not supported" in res[1], res)

    def test_06_slit_uri(self):
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
        self.assertEqual(server_pool.active, True)
        self.assertEqual(server_pool.exhaust, True)
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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'oid',
                      'NOREFERRALS': True
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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber",'
                                  '"mobile" : "mobile",'
                                  '"password" : "userPassword",'
                                  '"email" : "mail",'
                                  '"surname" : "sn",'
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True
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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName",'
                                  '"additionalAttr": "homeDirectory" }',
                      'UIDTYPE': 'DN',
                      'NOREFERRALS': True}
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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName", '
                                  '"accountExpires": "accountExpires" }',
                      'UIDTYPE': 'DN',
                      'NOREFERRALS': True
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
                      'LDAPFILTER': '(&(cn=%s))',
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
                      'NOREFERRALS': True
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
                      'LDAPFILTER': '(&(cn=%s))',
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
                      'NOREFERRALS': True
        })

        user = "achmed"
        uid = uuid.uuid4().bytes
        user_id = str(uuid.UUID(bytes_le=uid))

        attributes = {"username": user,
                      "surname": "Ali",
                      "userid": uid,
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
                      'LDAPFILTER': '(&(cn=%s))',
                      'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"givenname" : "givenName" }',
                      'UIDTYPE': 'objectGUID',
                      'NOREFERRALS': True
                      })
        user_id = y.getUserId("bob")
        user_info = y.getUserInfo(user_id)
        self.assertEqual(user_info.get("username"), "bob")
        self.assertEqual(user_info.get("surname"), "Marley")
        self.assertEqual(user_info.get("givenname"), "Robert")


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
                               'LDAPFILTER': '(&(cn=%s))',
                               'USERINFO': '{ "username": "cn",'
                                           '"phone" : "telephoneNumber", '
                                           '"mobile" : "mobile"'
                                           ', "email" : "mail", '
                                           '"surname" : "sn", '
                                           '"givenname" : "givenName" }',
                               'UIDTYPE': 'DN'
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
                               'LDAPFILTER': '(&(cn=%s))',
                               'USERINFO': '{ "username": "cn",'
                                           '"phone" : "telephoneNumber", '
                                           '"surname" : "sn", '
                                           '"givenname" : "givenName" }',
                               'UIDTYPE': 'DN'
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
