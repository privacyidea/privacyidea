"""
This test file tests the lib.resolver and all
the resolvers under it:

lib.resolvers.passwdresolver
lib.resolvers.ldapresolver

The lib.resolver.py only depends on the database model.
"""
PWFILE = "tests/testdata/passwords"
from .base import MyTestCase
from mockldap import MockLdap
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPResolver
from privacyidea.lib.resolvers.SQLIdResolver import IdResolver as SQLResolver

from privacyidea.lib.resolver import (save_resolver,
                                      delete_resolver,
                                      get_resolver_config,
                                      get_resolver_list,
                                      get_resolver_object, pretestresolver)
from privacyidea.models import ResolverConfig

class SQLResolverTestCase(MyTestCase):
    """
    Test the SQL Resolver
    """
    parameters = {'Driver': 'sqlite',
                  'Server': '/tests/testdata/',
                  'Database': "testuser.sqlite",
                  'Table': 'users',
                  'Map': '{ "username": "username", \
                    "userid" : "id", \
                    "email" : "email", \
                    "surname" : "name", \
                    "givenname" : "givenname", \
                    "password" : "password", \
                    "phone": "phone", \
                    "mobile": "mobile"}'
    }

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
        print result
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
        self.assertTrue(result[0] == 6, result)
        self.assertTrue('Found 6 users.' in result[1])

    def test_04_testconnection_fail(self):
        y = SQLResolver()
        self.parameters['Database'] = "does_not_exist"
        result = y.testconnection(self.parameters)
        self.assertTrue(result[0] == -1, result)
        self.assertTrue("failed to retrieve" in result[1], result)


class LDAPResolverTestCase(MyTestCase):
    """
    Test the LDAP resolver
    """
    top = ('o=test', {'o': 'test'})
    example = ('ou=example,o=test', {'ou': 'example'})
    other = ('ou=other,o=test', {'ou': 'other'})
    manager = ('cn=manager,ou=example,o=test',
               {'cn': 'manager',
                'userPassword': ['ldaptest'],
                'oid': "1"})
    alice = ('cn=alice,ou=example,o=test',
             {'cn': 'alice',
              'userPassword': ['alicepw'],
              'oid': "2",
              'mobile': ["1234", "45678"]})
    bob = ('cn=bob,ou=other,o=test',
           {'cn': 'bob', 'userPassword': ['bobpw'], 'oid': ["3"]})

    # This is the content of our mock LDAP directory. It takes the form
    # {dn: {attr: [value, ...], ...}, ...}.
    directory = dict([top, example, other, manager, alice, bob])

    @classmethod
    def setUpClass(cls):
        # We only need to create the MockLdap instance once. The content we
        # pass in will be used for all LDAP connections.
        cls.mockldap = MockLdap(cls.directory)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        # Patch ldap.initialize
        self.mockldap.start()
        self.ldapobj = self.mockldap['ldap://localhost/']

    def tearDown(self):
        # Stop patching ldap.initialize and reset state.
        self.mockldap.stop()
        del self.ldapobj


    def test_00_testconnection(self):
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

    def test_01_LDAP_DN(self):
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
        self.assertTrue(len(result) == 3, result)

        user = "bob"
        user_id = y.getUserId(user)
        self.assertTrue(user_id == "cn=bob,ou=other,o=test", user_id)

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

        res = y.checkPass(user_id, "bobpw")
        self.assertTrue(res)

        res = y.checkPass(user_id, "wrong pw")
        self.assertFalse(res)

    def test_02_LDAP_OID(self):
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
        self.assertTrue(len(result) == 3, result)

        user = "bob"
        user_id = y.getUserId(user)
        self.assertTrue(user_id == "3", user_id)

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

        res = y.checkPass(user_id, "bobpw")
        self.assertTrue(res)

        res = y.checkPass(user_id, "wrong pw")
        self.assertFalse(res)

    def test_03_testconnection(self):
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


    def test_04_testconnection_fail(self):
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
        self.assertTrue("INVALID_CREDENTIALS" in res[1], res)


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
        self.assertTrue(len(r) == 1, "%s" % r)
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

    def test_13_update_resolver(self):
        # Init stuff
        top = ('o=test', {'o': 'test'})
        example = ('ou=example,o=test', {'ou': 'example'})
        other = ('ou=other,o=test', {'ou': 'other'})
        manager = ('cn=manager,ou=example,o=test',
                   {'cn': 'manager',
                    'userPassword': ['ldaptest'],
                    'oid': "1"})
        alice = ('cn=alice,ou=example,o=test',
                 {'cn': 'alice',
                  'userPassword': ['alicepw'],
                  'oid': "2",
                  'mobile': ["1234", "45678"]})
        bob = ('cn=bob,ou=other,o=test',
               {'cn': 'bob', 'userPassword': ['bobpw'], 'oid': ["3"]})

        # This is the content of our mock LDAP directory. It takes the form
        # {dn: {attr: [value, ...], ...}, ...}.
        directory = dict([top, example, other, manager, alice, bob])

        # We only need to create the MockLdap instance once. The content we
        # pass in will be used for all LDAP connections.
        mockldap = MockLdap(directory)
        mockldap.start()
        ldapobj = mockldap['ldap://localhost/']
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

        # clean up
        mockldap.stop()
        del ldapobj
        del mockldap
