# -*- coding: utf-8 -*-
"""
This test file tests the lib.user

The lib.user.py only depends on the database model
"""
import logging

from testfixtures import log_capture

from .base import MyTestCase
from privacyidea.lib.resolver import (save_resolver, delete_resolver)
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.realm import (set_realm, delete_realm)
from privacyidea.lib.user import (User, create_user,
                                  get_username,
                                  get_user_list,
                                  split_user,
                                  get_user_from_param,
                                  UserError)
from privacyidea.lib.user import log as user_log
from . import ldap3mock
from .test_lib_resolver import LDAPDirectory_small

PWFILE = "tests/testdata/passwd"
PWFILE2 = "tests/testdata/passwords"


class UserTestCase(MyTestCase):
    """
    Test the user on the database level
    """
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"

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
    
    def test_00_create_user(self):
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)
               
        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)
        
        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)
        
        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)
        self.assertIsInstance(str(user), str)
        
        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())
        
        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)
        
    def test_01_resolvers_of_user(self):
        user = User(login="root",
                    realm=self.realm1)

        resolvers = user._get_resolvers()
        self.assertTrue(self.resolvername1 in resolvers, resolvers)
        self.assertFalse(self.resolvername2 in resolvers, resolvers)
        
        user2 = User(login="root",
                     realm=self.realm1,
                     resolver=self.resolvername1)
        resolvers = user2._get_resolvers()
        self.assertTrue(self.resolvername1 in resolvers, resolvers)
        self.assertFalse(self.resolvername2 in resolvers, resolvers)
        
    def test_02_get_user_identifiers(self):
        # create user by login
        user = User(login="root",
                    realm=self.realm1)
        (uid, rtype, resolvername) = user.get_user_identifiers()
        self.assertEqual("0", uid)
        self.assertEqual("passwdresolver", rtype)
        self.assertEqual(self.resolvername1, resolvername)
        self.assertEqual(user.realm_id, 1)

        # create user by uid. fail, since the resolver is missing
        self.assertRaises(UserError, User, realm=self.realm1, uid="0")
        # create user by uid.
        user2 = User(realm=self.realm1, resolver=self.resolvername1, uid="0")
        (uid, rtype, resolvername) = user2.get_user_identifiers()
        self.assertEqual("root", user2.login)
        self.assertEqual("passwdresolver", rtype)
        self.assertEqual(self.resolvername1, resolvername)
        self.assertEqual(user.realm_id, 1)

    def test_03_get_username(self):
        username = get_username("0", self.resolvername1)
        self.assertTrue(username == "root", username)

    def test_05_get_user_list(self):
        # all users
        userlist = get_user_list()
        self.assertTrue(len(userlist) > 10, userlist)
        
        # users from one realm
        userlist = get_user_list({"realm": self.realm1,
                                  "username": "root",
                                  "resolver": self.resolvername2})
        self.assertTrue(len(userlist) == 1, userlist)
        
        # get the list with user
        userlist = get_user_list(user=User(login="root",
                                           resolver=self.resolvername1,
                                           realm=self.realm1))
        self.assertTrue(len(userlist) > 10, userlist)

        # users with email
        userlist = get_user_list({"realm": self.realm1,
                                  "email": "root@testdomain.test",
                                  "resolver": self.resolvername2})
        self.assertTrue(len(userlist) == 0, userlist)

    def test_06_get_user_phone(self):
        phone = User(login="cornelius", realm=self.realm1).get_user_phone()
        self.assertTrue(phone == "+49 561 3166797", phone)
        
        phone = User(login="cornelius",
                     realm=self.realm1).get_user_phone("landline")
        self.assertTrue(phone == "", phone)
        
    def test_07_get_user_realms(self):
        user = User(login="cornelius", realm=self.realm1)
        realms = user.get_user_realms()
        self.assertTrue(len(realms) == 1, realms)
        self.assertTrue(self.realm1 in realms, realms)
        
        # test for default realm
        user = User(login="root")
        realms = user.get_user_realms()
        self.assertTrue(len(realms) == 1, realms)
        
        # test for user with only a resolver
        user = User(login="root", resolver=self.resolvername1)
        realms = user.get_user_realms()
        self.assertTrue(len(realms) == 1, realms)
        self.assertTrue(self.realm1 in realms, realms)
        
    def test_08_split_user(self):
        user = split_user("user@realm1")
        self.assertTrue(user == ("user", "realm1"), user)
        
        user = split_user("user")
        self.assertTrue(user == ("user", ""), user)
        
        user = split_user("user@email@realm1")
        self.assertTrue(user == ("user@email", "realm1"), user)
        
        user = split_user("realm1\\user")
        self.assertTrue(user == ("user", "realm1"), user)

        # The user is not split, since there is no real "non_existing_realm.com"
        user = split_user("user@non_existing_realm.com")
        self.assertEqual(user, ("user@non_existing_realm.com", ""))

    @log_capture(level=logging.DEBUG)
    def test_09_get_user_from_param(self, capture):
        # enable splitAtSign
        set_privacyidea_config("splitAtSign", True)
        user = get_user_from_param({"user": "cornelius"})
        self.assertTrue(user.realm == self.realm1, user)
        self.assertTrue(user.resolver == self.resolvername1, user)
        
        user = get_user_from_param({"realm": self.realm1})
        self.assertTrue(user.realm == self.realm1, user)
        self.assertTrue(user.login == "", user)
        self.assertTrue(user.resolver == "", user.resolver)
        
        user = get_user_from_param({"user": "cornelius",
                                    "resolver": self.resolvername1})
        self.assertTrue(user.realm == self.realm1, user)
        
        # create a realm, where cornelius is in two resolvers!
        rid = save_resolver({"resolver": self.resolvername3,
                               "type": "passwdresolver",
                               "fileName": PWFILE2})
        self.assertTrue(rid > 0, rid)
               
        (added, failed) = set_realm(self.realm2,
                                    [self.resolvername1,
                                     self.resolvername3])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 2)
        
        # get user cornelius, who is in two resolvers!
        param = {"user": "cornelius",
                 "realm": self.realm2}
        user = get_user_from_param(param)
        self.assertEqual("{0!s}".format(user), "<cornelius.resolver1@realm2>")

        # test with splitAtSign set to False
        set_privacyidea_config("splitAtSign", False)

        # don't split at @, realm will be default realm
        param = {"user": "cornelius@realm2"}
        user = get_user_from_param(param)
        self.assertEqual(user.login, "cornelius@realm2", user)
        self.assertEqual(user.realm, "realm1", user)

        param = {"user": "cornelius",
                 "realm": self.realm2}
        user = get_user_from_param(param)
        self.assertEqual(user.login, "cornelius", user)
        self.assertEqual(user.realm, "realm2", user)

        param = {"user": "cornelius@unknown@realm1",
                 "realm": self.realm2}
        user = get_user_from_param(param)
        self.assertEqual(user.login, "cornelius@unknown@realm1", user)
        self.assertEqual(user.realm, "realm2", user)

        param = {"user": "cornelius//realm1",
                 "realm": self.realm2}
        user = get_user_from_param(param)
        self.assertEqual(user.login, "cornelius//realm1", user)
        self.assertEqual(user.realm, "realm2", user)

        # check debug log for passwords
        user_log.setLevel(logging.DEBUG)
        _user = get_user_from_param({
            'user': 'cornelius',
            'realm': self.realm2,
            'pass': 'barracuda',
            'password': 'swordfish'})
        log_msg = str(capture)
        self.assertNotIn('barracuda', log_msg, log_msg)
        self.assertNotIn('swordfish', log_msg, log_msg)
        self.assertIn('HIDDEN', log_msg, log_msg)
        user_log.setLevel(logging.INFO)

        # reset splitAtSign setting
        set_privacyidea_config("splitAtSign", True)

    def test_10_check_user_password(self):
        (added, failed) = set_realm("passwordrealm",
                                    [self.resolvername3])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)
        
        self.assertTrue(User(login="cornelius",
                             realm="passwordrealm").check_password("test"))
        self.assertFalse(User(login="cornelius",
                              realm="passwordrealm").check_password("wrong"))
        self.assertFalse(User(login="unknownuser",
                              realm="passwordrealm").check_password("wrong"))
        
        # test cornelius@realm2, since he is located in more than one
        # resolver.
        self.assertEqual(User(login="cornelius",
                              realm="realm2").check_password("test"), None)
        
    def test_11_get_search_fields(self):
        user = User(login="cornelius", realm=self.realm1)
        sF = user.get_search_fields()
        self.assertTrue(self.resolvername1 in sF, sF)
        resolver_sF = sF.get(self.resolvername1)
        self.assertTrue("username" in resolver_sF, resolver_sF)
        self.assertTrue("userid" in resolver_sF, resolver_sF)

    def test_12_resolver_priority(self):
        # Test the priority of resolvers.
        # we create resolvers with the same user in it. Depending on the
        # priority we either get the one or the other user.
        save_resolver({"resolver": "double1",
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        save_resolver({"resolver": "double2",
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        save_resolver({"resolver": "double3",
                       "type": "passwdresolver",
                       "fileName": PWFILE})

        (added, failed) = set_realm("double",
                                    ["double1", "double2", "double3"],
                                    priority={"double1": 2,
                                              "double2": 1,
                                              "double3": 3})
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 3)

        user = get_user_from_param({"user": "cornelius", "realm": "double"})
        self.assertEqual(user.resolver, "double2")

        (added, failed) = set_realm("double",
                                    ["double1", "double2", "double3"],
                                    priority={"double1": 3,
                                              "double2": 2,
                                              "double3": 1})
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 3)

        user = get_user_from_param({"user": "cornelius", "realm": "double"})
        self.assertEqual(user.resolver, "double3")

    def test_13_update_user(self):
        realm = "sqlrealm"
        resolver = "SQL1"
        parameters = self.parameters
        parameters["resolver"] = resolver
        parameters["type"] = "sqlresolver"

        rid = save_resolver(parameters)
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(realm, [resolver])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        user = User(login="wordpressuser", realm=realm)
        uinfo = user.info
        self.assertEqual(uinfo.get("givenname", ""), "")

        user.update_user_info({"givenname": "wordy",
                               "username": "WordpressUser"})
        uinfo = user.info
        self.assertEqual(uinfo.get("givenname"), "wordy")

        self.assertEqual(user.login, "WordpressUser")

        user.update_user_info({"givenname": "",
                               "username": "wordpressuser"})

    def test_14_create_delete_user(self):
        realm = "sqlrealm"
        resolver = "SQL1"
        parameters = self.parameters
        parameters["resolver"] = resolver
        parameters["type"] = "sqlresolver"

        rid = save_resolver(parameters)
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(realm, [resolver])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        # Create the user
        uid = create_user(resolver, {"username": "achmed3",
                                     "givenname": "achmed"},
                                     password="secret")
        self.assertTrue(uid > 6)

        user = User("achmed3", realm=realm)
        r = user.check_password("secret")

        # delete user
        r = user.delete()
        self.assertTrue(r)

    def test_15_user_exist(self):
        root = User("root", resolver=self.resolvername1, realm=self.realm1)
        self.assertTrue(root.exist())

    def test_16_ordered_resolver(self):
        rid = save_resolver({"resolver": "resolver2",
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        rid = save_resolver({"resolver": "reso4",
                             "type": "passwdresolver",
                             "fileName": PWFILE})

        (added, failed) = set_realm("sort_realm",
                                    ["resolver1", "resolver2", "reso3",
                                     "reso4"],
                                    priority={"resolver1": 30,
                                              "resolver2": 10,
                                              "reso3": 27,
                                              "reso4": 5})

        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 4)

        root = User("root", "sort_realm")
        r = root.get_ordererd_resolvers()
        self.assertEqual(r[0], "reso4")
        self.assertEqual(r[1], "resolver2")
        self.assertEqual(r[2], "reso3")
        self.assertEqual(r[3], "resolver1")

        delete_realm("sort_realm")

    def test_17_check_nonascii_user(self):
        realm = "sqlrealm"
        resolver = "SQL1"
        parameters = self.parameters
        parameters["resolver"] = resolver
        parameters["type"] = "sqlresolver"

        rid = save_resolver(parameters)
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(realm, [resolver])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        # check non-ascii password of non-ascii user
        self.assertFalse(User(login="nönäscii",
                              realm=realm).check_password("wrong"))
        self.assertTrue(User(login="nönäscii",
                             realm=realm).check_password("sömepassword"))

        # check proper unicode() and str() handling
        user_object = User(login="nönäscii", realm=realm)
        self.assertEqual(str(user_object), '<nönäscii.SQL1@sqlrealm>')
        self.assertEqual(str(user_object).encode('utf8'),
                         b'<n\xc3\xb6n\xc3\xa4scii.SQL1@sqlrealm>')
        # also check the User object representation
        user_repr = repr(user_object)
        self.assertEqual("User(login='nönäscii', "
                         "realm='sqlrealm', resolver='SQL1')",
                         user_repr, user_repr)

    @ldap3mock.activate
    def test_18_user_with_several_phones(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory_small)
        params = ({'LDAPURI': 'ldap://localhost',
                   'LDAPBASE': 'o=test',
                   'BINDDN': 'cn=manager,ou=example,o=test',
                   'BINDPW': 'ldaptest',
                   'LOGINNAMEATTRIBUTE': 'cn',
                   'LDAPSEARCHFILTER': '(|(cn=*))',  # we use this weird search filter to get a unique resolver ID
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
        params["resolver"] = "ldapresolver"
        params["type"] = "ldapresolver"
        rid = save_resolver(params)
        self.assertTrue(rid > 0)
        (added, failed) = set_realm("ldap", ["ldapresolver"])
        self.assertEqual(len(added), 1)
        self.assertEqual(len(failed), 0)

        u = User("salesman", "ldap")
        # get the complete list
        r = u.get_user_phone("mobile")
        self.assertEqual(r, ["1234", "3456"])
        # get the first entry
        r = u.get_user_phone("mobile", index=0)
        self.assertEqual(r, "1234")
        # Index out of range
        r = u.get_user_phone("mobile", index=2)
        self.assertEqual(r, "")

        delete_realm("ldap")
        delete_resolver("ldapresolver")

    @ldap3mock.activate
    def test_19_compare_user_object(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory_small)
        params = ({'LDAPURI': 'ldap://localhost',
                   'LDAPBASE': 'o=test',
                   'BINDDN': 'cn=manager,ou=example,o=test',
                   'BINDPW': 'ldaptest',
                   'LOGINNAMEATTRIBUTE': 'cn',
                   'LDAPSEARCHFILTER': '(|(cn=*))',  # we use this weird search filter to get a unique resolver ID
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
        params["resolver"] = "ldapresolver"
        params["type"] = "ldapresolver"
        rid = save_resolver(params)
        self.assertTrue(rid > 0)
        (added, failed) = set_realm("ldap", ["ldapresolver"])
        self.assertEqual(len(added), 1)
        self.assertEqual(len(failed), 0)

        # Comparing different objects fails
        self.assertFalse(User("salesman", "ldap") == None)
        # comparing different realm or resolver fails
        self.assertFalse(User("cornelius", self.realm1) == User("salesman", "ldap"))
        # comparing different users fails
        self.assertFalse(User("manager", "ldap") == User("salesman", "ldap"))
        # comparing case insensitive successful
        self.assertTrue(User("salesman", "ldap") == User("salesman", "ldap"))
        self.assertTrue(User(resolver='ldapresolver', realm="ldap",
                             uid="039b36ef-e7c0-42f3-9bf9-ca6a6c0d4d54") == User("salesman", "ldap"))
        delete_realm("ldap")
        delete_resolver("ldapresolver")

    def test_50_user_attributes(self):
        user = User(login="root",
                    realm=self.realm1)
        r = user.set_attribute("hans", "wurst")
        self.assertTrue(r > 0)
        r = user.set_attribute("hugen", "dubel")
        self.assertTrue(r > 1)
        attrs = user.attributes
        self.assertEqual(attrs.get("hans"), "wurst")
        self.assertEqual(attrs.get("hugen"), "dubel")
        # Now we can overwrite attributes
        r = user.set_attribute("hans", "meiser")
        attrs = user.attributes
        self.assertEqual(attrs.get("hans"), "meiser")
        self.assertEqual(attrs.get("hugen"), "dubel")
        # now delete some attributes of the user
        r = user.delete_attribute("hans")
        self.assertTrue(r == 1)
        attrs = user.attributes
        self.assertEqual(attrs.get("hans"), None)
        self.assertEqual(attrs.get("hugen"), "dubel")
        # delete all attributes
        user.set_attribute("key", "value")
        r = user.delete_attribute()
        self.assertTrue(r == 2)
        attrs = user.attributes
        self.assertEqual(attrs.get("hans"), None)
        self.assertEqual(attrs.get("hugen"), None)
        self.assertEqual(attrs.get("key"), None)
