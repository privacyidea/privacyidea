"""
This test file tests the lib.user

The lib.user.py only depends on the database model
"""
import logging

import mock
from testfixtures import log_capture, LogCapture

from privacyidea.config import TestingConfig
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.framework import get_app_config
from privacyidea.lib.realm import (set_realm, delete_realm, get_realm_id, get_ordered_resolvers)
from privacyidea.lib.resolver import (save_resolver, delete_resolver)
from privacyidea.lib.resolvers.EntraIDResolver import (CLIENT_ID, CLIENT_CREDENTIAL_TYPE, ClientCredentialType,
                                                       CLIENT_SECRET, TENANT)
from privacyidea.lib.user import (User, create_user,
                                  get_username,
                                  get_user_list,
                                  split_user,
                                  get_user_from_param,
                                  UserError, get_attributes)
from privacyidea.lib.user import log as user_log
from sqlalchemy import delete, select

from privacyidea.models import InternalUserAttribute, NodeName, db
from . import ldap3mock
from .base import MyTestCase, OverrideConfigTestCase, PristineSqliteFixtures
from .test_lib_resolver import LDAPDirectory_small
from .test_lib_resolver_httpresolver import ConfidentialClientApplicationMock

PWFILE = "tests/testdata/passwd"
PWFILE2 = "tests/testdata/passwords"
PWFILE3 = "tests/testdata/passwd-mask-user"


def patch_resolver_to_raise(resolver_name, exception):
    """
    Context-manager helper: patch ``privacyidea.lib.user.get_resolver_object`` so
    that requesting ``resolver_name`` returns an object whose ``getUserList``
    raises ``exception``. Other resolvers behave normally. Used by the
    get_user_list-failure tests (also imported by tests/test_api_users.py).
    """
    import privacyidea.lib.user as user_module
    real_get_resolver_object = user_module.get_resolver_object

    def fake_get_resolver_object(name):
        resolver = real_get_resolver_object(name)
        if name == resolver_name:
            class Broken:
                editable = resolver.editable

                def getUserList(self, search_dict, attributes):
                    raise exception
            return Broken()
        return resolver

    return mock.patch.object(user_module, "get_resolver_object", side_effect=fake_get_resolver_object)


class UserTestCase(PristineSqliteFixtures, MyTestCase):
    """
    Test the user on the database level
    """
    pristine_fixtures = ["tests/testdata/testuser.sqlite"]
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
                                    [{'name': self.resolvername1}])
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

        # realm + resolver where the resolver IS part of the realm:
        # query is narrowed to that resolver and finds "root".
        userlist = get_user_list({"realm": self.realm1,
                                  "username": "root",
                                  "resolver": self.resolvername1})
        self.assertTrue(len(userlist) == 1, userlist)

        # realm + resolver where the resolver is NOT part of the realm:
        # result is empty (the resolver is no longer silently dropped).
        userlist = get_user_list({"realm": self.realm1,
                                  "username": "root",
                                  "resolver": self.resolvername2})
        self.assertEqual(userlist, [])

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
                                    [
                                        {'name': self.resolvername1, 'priority': 1},
                                        {'name': self.resolvername3, 'priority': 2}])
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

        user_log.setLevel(logging.DEBUG)
        # check hiding passwords in debug log
        get_user_from_param({
            'user': 'cornelius',
            'realm': self.realm1,
            'pass': 'testing123',
            'password': 'barracuda'})
        # merge the log messages
        log_msg = str(capture)
        self.assertIn("'pass': 'HIDDEN'", log_msg, log_msg)
        self.assertIn("'password': 'HIDDEN'", log_msg, log_msg)
        self.assertNotIn('barracuda', log_msg, log_msg)
        self.assertNotIn('testing123', log_msg, log_msg)
        user_log.setLevel(logging.INFO)

        # reset splitAtSign setting
        set_privacyidea_config("splitAtSign", True)

    #    @log_capture(level=logging.DEBUG)
    def test_10_check_user_password(self):
        (added, failed) = set_realm("passwordrealm",
                                    [{'name': self.resolvername3}])
        self.assertEqual(0, len(failed))
        self.assertEqual(1, len(added))

        user = User(login="cornelius", realm="passwordrealm")
        logging.getLogger('privacyidea.lib.user').setLevel(logging.DEBUG)
        with LogCapture(level=logging.DEBUG) as lc:
            self.assertTrue(user.check_password("test"))
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm passwordrealm tries to authenticate"),
                (
                    'privacyidea.lib.user', 'DEBUG',
                    "Successfully authenticated user <cornelius.reso3@passwordrealm>."))
        # Try another password check with the same user and password to see
        # if it was properly cached
        with LogCapture(level=logging.DEBUG) as lc:
            self.assertTrue(user.check_password("test"))
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm passwordrealm tries to authenticate"),
                (
                    'privacyidea.lib.user', 'DEBUG',
                    "Successfully authenticated user <cornelius.reso3@passwordrealm> from request cache."))
        # Now try the same user with a wrong password
        with LogCapture() as lc:
            self.assertFalse(user.check_password("wrong"))
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm passwordrealm tries to authenticate"),
                (
                    'privacyidea.lib.user', "INFO",
                    "User <cornelius.reso3@passwordrealm> failed to authenticate."))
        # And try again to check if the wrong password was cached as well
        with LogCapture() as lc:
            self.assertFalse(user.check_password("wrong"))
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm passwordrealm tries to authenticate"),
                (
                    'privacyidea.lib.user', "INFO",
                    "User <cornelius.reso3@passwordrealm> failed to authenticate from request cache."))

        self.assertFalse(User(login="cornelius",
                              realm="passwordrealm").check_password("wrong"))
        self.assertFalse(User(login="unknownuser",
                              realm="passwordrealm").check_password("wrong"))

        # test cornelius@realm2, since he is located in more than one
        # resolver.
        self.assertEqual(User(login="cornelius",
                              realm="realm2").check_password("test"), None)

        # check that for HTTPResolvers also the login name is passed to the function
        save_resolver({"resolver": "entraid", "type": "entraidresolver",
                       CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value,
                       CLIENT_SECRET: "secret", TENANT: "organization"})
        with mock.patch('privacyidea.lib.resolvers.HTTPResolver.HTTPResolver.checkPass') as mock_check_password:
            with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                            new=ConfidentialClientApplicationMock):
                mock_check_password.return_value = True
                user = User(login="cornelius", realm="EntraID", resolver="entraid", uid="1234")
                user.check_password("test")
                mock_check_password.assert_called_with("1234", "test", "cornelius")

        delete_realm("realm2")
        delete_realm("passwordrealm")

    def test_11_get_search_fields(self):
        user = User(login="cornelius", realm=self.realm1)
        s_f = user.get_search_fields()
        self.assertTrue(self.resolvername1 in s_f, s_f)
        resolver_s_f = s_f.get(self.resolvername1)
        self.assertTrue("username" in resolver_s_f, resolver_s_f)
        self.assertTrue("userid" in resolver_s_f, resolver_s_f)

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
                                    [
                                        {'name': "double1", 'priority': 2},
                                        {'name': "double2", 'priority': 1},
                                        {'name': "double3", 'priority': 3}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 3)

        user = get_user_from_param({"user": "cornelius", "realm": "double"})
        self.assertEqual(user.resolver, "double2")

        (added, failed) = set_realm("double",
                                    [
                                        {'name': "double1", 'priority': 3},
                                        {'name': "double2", 'priority': 2},
                                        {'name': "double3", 'priority': 1}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 3)

        user = get_user_from_param({"user": "cornelius", "realm": "double"})
        self.assertEqual(user.resolver, "double3")

    def test_12b_get_user_list_failures(self):
        # A resolver that raises ResolverError/ParameterError must be skipped
        # and recorded in the caller-supplied ``failures`` list as
        # ``(resolver_name, realm, error_repr)``. Other resolvers in the same
        # realm must still contribute their users.
        from privacyidea.lib.error import ResolverError

        failures = []
        with patch_resolver_to_raise("double2", ResolverError("simulated outage")):
            users = get_user_list({"realm": "double"}, failures=failures)

        # double1 and double3 still work, so we get users back.
        self.assertTrue(len(users) > 0, users)
        # The broken resolver appears once (it lives in only one realm here).
        self.assertEqual(len(failures), 1, failures)
        name, realm, error = failures[0]
        self.assertEqual(name, "double2")
        self.assertEqual(realm, "double")
        self.assertIn("simulated outage", error)

    def test_12c_get_user_list_failures_collect_per_realm(self):
        # A resolver-only query iterates every realm that contains the resolver
        # (see realm scoping in get_user_list). When the resolver is broken it
        # raises in each iteration; the lib must collect one entry per realm so
        # callers can see the full per-realm context (the API/audit formatter
        # dedupes by name when it only wants one entry per resolver).
        from privacyidea.lib.error import ResolverError

        (added, failed) = set_realm("double_extra", [{"name": "double2"}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        failures = []
        try:
            with patch_resolver_to_raise("double2", ResolverError("simulated outage")):
                users = get_user_list({"resolver": "double2"}, failures=failures)
            # Both realms iterated, both raised — both recorded with their realm.
            self.assertEqual(users, [])
            self.assertEqual(len(failures), 2, failures)
            recorded_realms = {realm for _name, realm, _err in failures}
            self.assertEqual(recorded_realms, {"double", "double_extra"})
            for name, _realm, _err in failures:
                self.assertEqual(name, "double2")
        finally:
            delete_realm("double_extra")

    def test_12a_get_user_list_resolver_only(self):
        # Realm "double" from test_12 contains double1 (prio 3), double2 (prio 2),
        # double3 (prio 1) — all backed by the same PWFILE. Querying with only
        # ``resolver=double1`` must return users from double1 exclusively. Before
        # the fix the resolver parameter was expanded to every sibling resolver
        # in the realm and the highest-priority resolver (double3) won the
        # (username, realm) dedup, so callers saw ``resolver=double3`` instead.
        userlist = get_user_list({"resolver": "double1"})
        self.assertTrue(len(userlist) > 0, userlist)
        for entry in userlist:
            self.assertEqual(entry["resolver"], "double1", entry)

    def test_13_update_user(self):
        realm = "sqlrealm"
        resolver = "SQL1"
        parameters = self.parameters
        parameters["resolver"] = resolver
        parameters["type"] = "sqlresolver"

        rid = save_resolver(parameters)
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(realm, [{'name': resolver}])
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

        (added, failed) = set_realm(realm, [{'name': resolver}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        # Create the user
        uid = create_user(resolver, {"username": "achmed3",
                                     "givenname": "achmed"},
                          password="secret")
        self.assertTrue(uid > 6)

        user = User("achmed3", realm=realm)
        r = user.check_password("secret")
        self.assertEqual(f"achmed3@{realm}", r)

        # delete user
        r = user.delete()
        self.assertTrue(r)

    def test_15_user_exist(self):
        root = User("root", resolver=self.resolvername1, realm=self.realm1)
        self.assertTrue(root.exist())
        delete_realm("realm1")

    def test_16_ordered_resolver(self):
        save_resolver({"resolver": "resolver1",
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        save_resolver({"resolver": "resolver2",
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        save_resolver({"resolver": "reso3",
                       "type": "passwdresolver",
                       "fileName": PWFILE2})
        save_resolver({"resolver": "reso4",
                       "type": "passwdresolver",
                       "fileName": PWFILE})

        (added, failed) = set_realm("sort_realm",
                                    [
                                        {'name': "resolver1", 'priority': 30},
                                        {'name': "resolver2", 'priority': 10},
                                        {'name': "reso3", 'priority': 27},
                                        {'name': "reso4", 'priority': 5}])

        self.assertEqual(0, len(failed), failed)
        self.assertEqual(4, len(added), added)

        r = get_ordered_resolvers("sort_realm")
        self.assertEqual(r[0], "reso4")
        self.assertEqual(r[1], "resolver2")
        self.assertEqual(r[2], "reso3")
        self.assertEqual(r[3], "resolver1")

        delete_realm("sort_realm")

        # Resolvers with the same priority are ordered alphabetically by name
        (added, failed) = set_realm("sort_alpha_realm",
                                    [
                                        {'name': "resolver1", 'priority': 10},
                                        {'name': "resolver2", 'priority': 10},
                                        {'name': "reso3", 'priority': 10},
                                        {'name': "reso4", 'priority': 10}])
        self.assertEqual(0, len(failed), failed)
        self.assertEqual(4, len(added), added)

        r = get_ordered_resolvers("sort_alpha_realm")
        self.assertEqual(r[0], "reso3")
        self.assertEqual(r[1], "reso4")
        self.assertEqual(r[2], "resolver1")
        self.assertEqual(r[3], "resolver2")

        delete_realm("sort_alpha_realm")

        # Now check with nodes given
        nd1_uuid = "8e4272a9-9037-40df-8aa3-976e4a04b5a9"
        nd2_uuid = "d1d7fde6-330f-4c12-88f3-58a1752594bf"
        node1 = NodeName(id=nd1_uuid, name="Node1")
        node2 = NodeName(id=nd2_uuid, name="Node2")
        db.session.add_all([node1, node2])

        (added, failed) = set_realm("sort_node_realm",
                                    [
                                        {
                                            'name': "resolver1",
                                            'priority': 30,
                                            'node': nd2_uuid,
                                        },
                                        {
                                            'name': "resolver2",
                                            'priority': 10,
                                            'node': nd1_uuid,
                                        },
                                        {
                                            "name": "reso3",
                                            "priority": 35,
                                            "node": nd2_uuid
                                        },
                                        {'name': "reso3", 'priority': 27},
                                        {'name': "reso4", 'priority': 5}
                                    ])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 5)

        # Test on node 1
        get_app_config()["PI_NODE_UUID"] = nd1_uuid
        r = get_ordered_resolvers("sort_node_realm")
        self.assertEqual(3, len(r), r)
        self.assertEqual(r[0], "reso4")
        self.assertEqual(r[1], "resolver2")
        self.assertEqual(r[2], "reso3")

        # Test on node 2
        get_app_config()["PI_NODE_UUID"] = nd2_uuid
        r = get_ordered_resolvers("sort_node_realm")
        self.assertEqual(3, len(r), r)
        self.assertEqual(r[0], "reso4")
        self.assertEqual(r[1], "reso3")
        self.assertEqual(r[2], "resolver1")

        # Check the list of users in each realm
        delete_realm("sort_node_realm")
        (added, failed) = set_realm("sort_node_realm",
                                    [
                                        {
                                            'name': "resolver1",
                                            'priority': 30,
                                            'node': nd1_uuid,
                                        },
                                        {
                                            "name": "reso3",
                                            "priority": 35,
                                            "node": nd2_uuid
                                        }
                                    ])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 2)

        # Test on node 1
        get_app_config()["PI_NODE_UUID"] = nd1_uuid
        ul = get_user_list(param={"realm": "sort_node_realm"})
        self.assertEqual(48, len(ul), ul)
        # Test on node 2
        get_app_config()["PI_NODE_UUID"] = nd2_uuid
        ul = get_user_list(param={"realm": "sort_node_realm"})
        self.assertEqual(15, len(ul), ul)

        delete_realm("sort_node_realm")
        delete_resolver("resolver1")
        delete_resolver("resolver2")
        delete_resolver("reso3")
        delete_resolver("reso4")
        db.session.delete(node1)
        db.session.delete(node2)

    def test_17_check_nonascii_user(self):
        realm = "sqlrealm"
        resolver = "SQL1"
        parameters = self.parameters
        parameters["resolver"] = resolver
        parameters["type"] = "sqlresolver"

        rid = save_resolver(parameters)
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(realm, [{'name': resolver}])
        self.assertEqual(0, len(failed))
        self.assertEqual(1, len(added))

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

        # Test with not existing search filter
        with LogCapture(level=logging.WARNING) as lc:
            userlist = get_user_list({"realm": "sqlrealm",
                                      "unknown": "parameter",
                                      "resolver": "SQL1"})
            self.assertEqual(0, len(userlist), userlist)
            lc.check_present(("privacyidea.lib.resolvers.SQLIdResolver", "ERROR",
                              "Could not find search key (['unknown']) in the "
                              "column mapping keys (['username', 'userid', "
                              "'email', 'surname', 'givenname', 'password', "
                              "'phone', 'mobile'])."))
            lc.check_present(("privacyidea.lib.user", "WARNING",
                              "Unable to get user list for resolver 'SQL1': "
                              "ParameterError(description=\"Search parameter "
                              "(['unknown']) not available in column mapping.\", id=905)"))

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
        (added, failed) = set_realm("ldap", [{'name': "ldapresolver"}])
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
        set_realm(self.realm1, [{'name': self.resolvername1}])
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
        (added, failed) = set_realm("ldap", [{'name': "ldapresolver"}])
        self.assertEqual(len(added), 1)
        self.assertEqual(len(failed), 0)

        # Comparing different objects fails
        self.assertIsNotNone(User("salesman", "ldap"))
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

    def test_20_available_info_keys(self):
        save_resolver({"resolver": self.resolvername1, "type": "passwdresolver",
                       "fileName": PWFILE})
        set_realm(self.realm1, [{'name': self.resolvername1}])
        user = User("root", self.realm1)

        info_keys = user.available_info_keys
        self.assertSetEqual(
            {"username", "userid", "givenname", "surname", "phone", "mobile", "email", "description", "cryptpass"},
            set(info_keys))

        # Cleanup
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    def test_21_get_specific_info(self):
        save_resolver({"resolver": self.resolvername1, "type": "passwdresolver",
                       "fileName": PWFILE})
        set_realm(self.realm1, [{'name': self.resolvername1}])
        user = User("root", self.realm1)

        # get specific info keys
        info = user.get_specific_info(["username", "givenname"])
        self.assertEqual(info.get("username"), "root")
        self.assertEqual(info.get("givenname"), "root")

        # get non existing info key
        info = user.get_specific_info(["nonexisting"])
        self.assertListEqual([], list(info.keys()))

        # not passing a list of keys returns all info
        info = user.get_specific_info()
        self.assertSetEqual(
            {"username", "userid", "givenname", "surname", "phone", "mobile", "email", "description", "cryptpass"},
            set(info.keys()))
        self.assertEqual("root", info.get("username"))
        self.assertEqual("0", info.get("userid"))
        self.assertEqual("root", info.get("givenname"))
        self.assertEqual("", info.get("surname"))
        self.assertEqual("", info.get("phone"))
        self.assertEqual("", info.get("mobile"))
        self.assertEqual("", info.get("email"))
        self.assertEqual("root", info.get("description"))
        self.assertEqual("x", info.get("cryptpass"))

        # empty user returns empty dict
        empty_user = User()
        info = empty_user.get_specific_info()
        self.assertEqual({}, info)

        # non-existing user returns empty dict
        non_existing_user = User("nonexisting", self.realm1)
        info = non_existing_user.get_specific_info()
        self.assertEqual({}, info)

        # Cleanup
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    def test_22_get_attributes(self):
        self.setUp_user_realms()
        user = User(login="hans", realm=self.realm1)
        realm_id = get_realm_id(self.realm1)

        # user has no attributes yet
        attributes = get_attributes(user.uid, user.resolver, realm_id)
        self.assertDictEqual({}, attributes)

        # add some attributes
        user.set_attribute("color", "green")
        user.set_attribute("department", "dev")
        user.set_attribute("working_hours", "40")

        # Get all attributes
        attributes = get_attributes(user.uid, user.resolver, realm_id)
        self.assertDictEqual({"color": "green", "department": "dev", "working_hours": "40"}, attributes)

        # Get only specific attributes
        attributes = get_attributes(user.uid, user.resolver, realm_id,
                                    requested_attributes=["department", "working_hours"])
        self.assertDictEqual({"department": "dev", "working_hours": "40"}, attributes)

        # pass empty list for attributes to get all attributes
        attributes = get_attributes(user.uid, user.resolver, realm_id, requested_attributes=[])
        self.assertDictEqual({"color": "green", "department": "dev", "working_hours": "40"}, attributes)

        # Clean up
        user.delete_attribute()
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    def test_90_masking_users_in_ordered_resolvers(self):
        # Two resolvers point at different passwd files that both contain a
        # user "cornelius" with the same uid. resolvername1 (PWFILE3) has the
        # higher priority (1) and must mask resolvername2 (PWFILE, priority 2).
        realmname = "masked_realm"
        save_resolver({"resolver": self.resolvername1,
                       "type": "passwdresolver",
                       "fileName": PWFILE3})
        save_resolver({"resolver": self.resolvername2,
                       "type": "passwdresolver",
                       "fileName": PWFILE})

        (added, failed) = set_realm(realmname,
                                    [
                                        {'name': self.resolvername1, 'priority': 1},
                                        {'name': self.resolvername2, 'priority': 2}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 2)

        r = get_user_list({"realm": realmname, "username": "cornelius"})
        # User cornelius must be returned exactly once — the lower-priority
        # entry from PWFILE must be masked.
        self.assertEqual(1, len(r), r)
        user = r[0]
        # The returned entry must be the one from the higher-priority
        # resolver (resolvername1 → PWFILE3). The passwdresolver splits the
        # GECOS field "Cornelius K" into givenname="Cornelius", surname="K",
        # with email info@netknights.it — distinct from PWFILE's
        # surname="Kölbel" / cornelius.koelbel@netknights.it.
        self.assertEqual(self.resolvername1, user.get("resolver"), user)
        self.assertEqual("info@netknights.it", user.get("email"), user)
        self.assertEqual("K", user.get("surname"), user)
        self.assertEqual("cornelius", user.get("username"), user)
        self.assertEqual("1009", user.get("userid"), user)
        self.assertEqual(realmname, user.get("realm"), user)

        delete_realm(realmname)
        delete_resolver(self.resolvername1)
        delete_resolver(self.resolvername2)

    def test_50_user_attributes(self):
        save_resolver({"resolver": self.resolvername1, "type": "passwdresolver",
                       "fileName": PWFILE})
        set_realm(self.realm1, [{'name': self.resolvername1}])
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
        user.set_attribute("hans", "meiser")
        attrs = user.attributes
        self.assertEqual(attrs.get("hans"), "meiser")
        self.assertEqual(attrs.get("hugen"), "dubel")
        # now delete some attributes of the user
        r = user.delete_attribute("hans")
        self.assertEqual(r, 1)
        attrs = user.attributes
        self.assertEqual(attrs.get("hans"), None)
        self.assertEqual(attrs.get("hugen"), "dubel")
        # delete all attributes
        user.set_attribute("key", "value")
        r = user.delete_attribute()
        self.assertEqual(r, 2)
        attrs = user.attributes
        self.assertEqual(attrs.get("hans"), None)
        self.assertEqual(attrs.get("hugen"), None)
        self.assertEqual(attrs.get("key"), None)
        # Cleanup
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    def test_51_internal_user_attributes(self):
        save_resolver({"resolver": self.resolvername1, "type": "passwdresolver",
                       "fileName": PWFILE})
        set_realm(self.realm1, [{'name': self.resolvername1}])
        user = User(login="root", realm=self.realm1)

        # Set + read JSON-typed values (dict and scalar string)
        user.set_internal_attribute("last_used_token", {"app-a": "hotp"})
        user.set_internal_attribute("fido2_user_id", "abc123")
        attrs = user.internal_attributes
        self.assertEqual({"app-a": "hotp"}, attrs.get("last_used_token"))
        self.assertEqual("abc123", attrs.get("fido2_user_id"))

        # Overwrite an existing key
        user.set_internal_attribute("last_used_token", {"app-a": "totp", "app-b": "push"})
        self.assertEqual({"app-a": "totp", "app-b": "push"},
                         user.internal_attributes.get("last_used_token"))

        # Delete a single key
        r = user.delete_internal_attribute("fido2_user_id")
        self.assertEqual(1, r)
        attrs = user.internal_attributes
        self.assertIsNone(attrs.get("fido2_user_id"))
        self.assertIn("last_used_token", attrs)

        # JSON contract: list, nested dict, numeric, boolean, None all round-trip
        user.set_internal_attribute("a_list", ["push", "hotp", "totp"])
        user.set_internal_attribute("a_nested", {"outer": {"inner": [1, 2, 3]}})
        user.set_internal_attribute("a_number", 42)
        user.set_internal_attribute("a_bool", True)
        user.set_internal_attribute("a_null", None)
        attrs = user.internal_attributes
        self.assertEqual(["push", "hotp", "totp"], attrs.get("a_list"))
        self.assertEqual({"outer": {"inner": [1, 2, 3]}}, attrs.get("a_nested"))
        self.assertEqual(42, attrs.get("a_number"))
        self.assertEqual(True, attrs.get("a_bool"))
        self.assertIsNone(attrs.get("a_null"))

        # Delete-all clears the rest
        r = user.delete_internal_attribute()
        self.assertEqual(6, r)
        self.assertEqual({}, user.internal_attributes)

        # Cleanup
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    def test_51b_internal_attributes_unresolved_user(self):
        """Unresolved User (empty uid) reads return {} (callers like
        preferred_client_mode run on every auth response); writes/deletes
        refuse to create empty-uid rows that would be shared across users."""
        from privacyidea.lib.error import UserError
        unresolved = User()
        self.assertFalse(unresolved.uid)
        self.assertEqual({}, unresolved.internal_attributes)
        self.assertRaises(UserError, unresolved.set_internal_attribute, "k", "v")
        self.assertRaises(UserError, unresolved.delete_internal_attribute)

    def test_53_find_and_delete_orphaned_internal_attributes(self):
        """find_orphaned_internal_attributes() flags rows whose user has
        vanished from the resolver; delete_orphaned_internal_attributes()
        prunes them and leaves resolvable users untouched."""
        from privacyidea.lib.user import (
            delete_orphaned_internal_attributes,
            find_orphaned_internal_attributes,
        )
        save_resolver({"resolver": self.resolvername1, "type": "passwdresolver",
                       "fileName": PWFILE})
        set_realm(self.realm1, [{'name': self.resolvername1}])
        live_user = User(login="root", realm=self.realm1)
        live_user.set_internal_attribute("k", "v-live")

        # Inject a row keyed on a uid that the resolver does not know.
        ghost = InternalUserAttribute(user_id="ghost-uid-9999",
                                      resolver=self.resolvername1,
                                      realm_id=live_user.realm_id,
                                      Key="k", Value="v-ghost")
        db.session.add(ghost)
        db.session.commit()

        orphans = find_orphaned_internal_attributes()
        self.assertEqual([("ghost-uid-9999", self.resolvername1, live_user.realm_id)], orphans)

        deleted = delete_orphaned_internal_attributes(orphans)
        self.assertEqual(1, deleted)

        # Live user's row survives, ghost row is gone, second pass is empty.
        self.assertEqual({"k": "v-live"}, live_user.internal_attributes)
        self.assertEqual([], find_orphaned_internal_attributes())

        live_user.delete_internal_attribute()
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    def test_53b_find_orphaned_edge_cases(self):
        """Cover the remaining orphan-detection branches:
        empty identifiers, deleted resolver, and resolver raising on lookup."""
        from privacyidea.lib.user import find_orphaned_internal_attributes
        save_resolver({"resolver": self.resolvername1, "type": "passwdresolver",
                       "fileName": PWFILE})
        set_realm(self.realm1, [{'name': self.resolvername1}])
        live_user = User(login="root", realm=self.realm1)

        # Branch 1: row with an empty user_id or empty resolver. Bypass the
        # write-side guard via the raw model.
        db.session.add(InternalUserAttribute(user_id="", resolver=self.resolvername1,
                                             realm_id=None, Key="k", Value="v"))
        db.session.add(InternalUserAttribute(user_id="uid-X", resolver="",
                                             realm_id=None, Key="k", Value="v"))
        # Branch 2: row pointing at a resolver name that does not exist.
        db.session.add(InternalUserAttribute(user_id="uid-Y", resolver="never-existed",
                                             realm_id=None, Key="k", Value="v"))
        # Branch 3 setup: a row on the live resolver whose lookup we will force
        # to raise via a mocked getUsername.
        db.session.add(InternalUserAttribute(user_id="uid-Z", resolver=self.resolvername1,
                                             realm_id=live_user.realm_id, Key="k", Value="v"))
        db.session.commit()

        from privacyidea.lib.resolver import get_resolver_object
        real_resolver = get_resolver_object(self.resolvername1)
        with mock.patch.object(real_resolver, "getUsername",
                               side_effect=RuntimeError("resolver unreachable")):
            # Default orphaned_on_error=False: errored row is skipped (not reported).
            orphans = set(find_orphaned_internal_attributes())
            self.assertIn(("", self.resolvername1, None), orphans)        # branch 1a
            self.assertIn(("uid-X", "", None), orphans)                   # branch 1b
            self.assertIn(("uid-Y", "never-existed", None), orphans)      # branch 2
            self.assertNotIn(("uid-Z", self.resolvername1, live_user.realm_id), orphans)

            # orphaned_on_error=True: errored row is reported.
            orphans_strict = set(find_orphaned_internal_attributes(orphaned_on_error=True))
            self.assertIn(("uid-Z", self.resolvername1, live_user.realm_id), orphans_strict)

        # Cleanup
        db.session.execute(delete(InternalUserAttribute))
        db.session.commit()
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    def test_52_internal_user_attribute_node_column(self):
        """The ``node`` column is reserved for future per-node state and is
        not writable through the set_internal_attribute API yet, so every
        row written via the API has node = NULL."""
        save_resolver({"resolver": self.resolvername1, "type": "passwdresolver",
                       "fileName": PWFILE})
        set_realm(self.realm1, [{'name': self.resolvername1}])
        user = User(login="root", realm=self.realm1)

        def _row(key):
            return db.session.execute(
                select(InternalUserAttribute).filter_by(
                    user_id=user.uid, resolver=user.resolver,
                    realm_id=user.realm_id, Key=key)
            ).scalar_one()

        # Rows written through the API default node to NULL (global value)
        user.set_internal_attribute("global_key", "v1")
        self.assertIsNone(_row("global_key").node)
        user.set_internal_attribute("global_key", "v2")
        self.assertIsNone(_row("global_key").node)

        # The write API does not accept a node argument
        self.assertRaises(TypeError, user.set_internal_attribute, "k", "v", "node-A")

        user.delete_internal_attribute()
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)


class HidePasswordInDebugLogTestCase(OverrideConfigTestCase):
    class Config(TestingConfig):
        # Set custom parameter for hash algorithms in pi.cfg.
        PI_LOGLEVEL = logging.DEBUG

    def test_01_check_for_hidden_passwords(self):
        self.setUp_user_realms()
        # Check hiding passwords in debug log
        with LogCapture(level=logging.DEBUG) as lc:
            get_user_from_param({
                'user': 'cornelius',
                'realm': self.realm1,
                'pass': 'testing123',
                'password': 'barracuda'
            })
            self.assertIn("Entering get_user_from_param with arguments [{'user': "
                          "'cornelius', 'realm': 'realm1', 'pass': 'HIDDEN', "
                          "'password': 'HIDDEN'}] and keywords {} (called from test_lib_user.py:",
                          str(lc), lc)
