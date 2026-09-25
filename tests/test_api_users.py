""" API testcases for the "/user/" endpoint """

from typing import Any
from urllib.parse import urlencode, quote

from privacyidea.lib.error import ResolverError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver, get_resolver_object
from privacyidea.lib.token import init_token, remove_token, get_tokens
from privacyidea.lib.container import init_container, delete_container_by_serial
from privacyidea.lib.user import User
from privacyidea.lib.users.internal_user_attributes import InternalUserAttributes
from .base import MyApiTestCase, PristineSqliteFixtures
from .test_lib_user import patch_resolver_to_raise

PWFILE = "tests/testdata/passwd"


class APIUsersTestCase(PristineSqliteFixtures, MyApiTestCase):
    parameters = {'Driver': 'sqlite',
                  'Server': '/tests/testdata/',
                  'Database': "testuser-api.sqlite",
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

    # SQL-resolver fixture this test class writes to (create/update/delete
    # user, password re-salting); kept pristine via PristineSqliteFixtures.
    pristine_fixtures = ["tests/testdata/testuser-api.sqlite"]

    def _create_user_wordy(self):
        """
        This creates a user "wordy" in the realm "sqlrealm"
        """
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
        with self.app.test_request_context('/user/',
                                           method='POST',
                                           data={"user": "wordy",
                                                 "resolver": resolver,
                                                 "surname": "zappa",
                                                 "givenname": "frank",
                                                 "email": "f@z.com",
                                                 "phone": "12345",
                                                 "mobile": "12345",
                                                 "password": "12345"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") > 6, result.get("value"))

    def _get_wordy_auth_token(self, password="12345"):
        """
        User wordy logs in and gets an auth-token: self.wordy_auth_token
        :return:
        """
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "wordy@{0!s}".format("sqlrealm"),
                                                 "password": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.wordy_auth_token = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertEqual("user", role, result)

    def test_00_get_empty_users(self):
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json["result"]["status"], res.json)
            self.assertEqual([], res.json["result"]["value"], res.json)

    def test_01_get_passwd_user(self):
        # create resolver
        with self.app.test_request_context('/resolver/r1',
                                           json={"resolver": "r1",
                                                 "type": "passwdresolver",
                                                 "fileName": PWFILE},
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            self.assertEqual(res.json['result']['value'], 1, res.json)

        # create realm
        realm = "realm1"
        resolvers = "r1, r2"
        with self.app.test_request_context('/realm/{0!s}'.format(realm),
                                           data={"resolvers": resolvers},
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json
            value = result.get("result").get("value")
            self.assertIn('r1', value["added"], result)
            self.assertIn('r2', value["failed"], result)

        # get user list
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({"realm": realm}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json
            value = result.get("result").get("value")
            unames = [x.get('username') for x in value]
            self.assertIn("cornelius", unames, value)
            self.assertIn("corny", unames, value)
            # Check that there is no password entry in the results
            self.assertTrue(all(["password" not in x for x in value]), value)

        # get user list with search dict
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({"username": "cornelius"}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json
            value = result.get("result").get("value")
            # Check that there is no password entry in the result
            self.assertNotIn("password", value, result)
            unames = [x.get('username') for x in value]
            self.assertIn("cornelius", unames, value)
            self.assertNotIn("corny", unames, value)

        # Get user with a non-existing realm
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({"realm": "non_existing"}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json
            value = result.get("result").get("value")
            unames = [x.get('username') for x in value]
            self.assertNotIn("cornelius", unames, value)
            self.assertNotIn("corny", unames, value)

    def test_02_create_update_delete_user(self):
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

        # CREATE a user
        self._create_user_wordy()

        # Get users
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "wordy"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertEqual(result.get("value")[0].get("username"), "wordy")

        # Update by administrator. Set the password to "passwort"
        with self.app.test_request_context('/user/',
                                           method='PUT',
                                           query_string=urlencode(
                                               {"user": "wordy",
                                                "resolver": resolver,
                                                "password": "passwort"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Get user authentication and update by user.
        self._get_wordy_auth_token("passwort")
        wordy_auth_token = self.wordy_auth_token

        # Even if a user specifies another username, the username is
        # overwritten by his own name!
        with self.app.test_request_context('/user/',
                                           method='PUT',
                                           query_string=urlencode(
                                               {"user": "wordy2",
                                                "resolver": resolver,
                                                "password": "newPassword"}),
                                           headers={'Authorization': wordy_auth_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Although the user "wordy" tried to update the password of user
        # "wordy2", he updated his own password.
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "wordy@{0!s}".format(realm),
                                                 "password": "newPassword"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)

        # The administrator can update the username of the user by specifying the userid
        with self.app.test_request_context('/user/',
                                           method='PUT',
                                           query_string=urlencode(
                                               {"user": "wordy2",
                                                "resolver": resolver,
                                                "userid": "7"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Delete the users
        with self.app.test_request_context('/user/{0!s}/{1!s}'.format(resolver, "wordy2"),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        with self.app.test_request_context('/user/{0!s}/{1!s}'.format(resolver, "wordy"),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

    def test_03_create_update_delete_unicode_user(self):
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

        # CREATE a user
        with self.app.test_request_context('/user/',
                                           method='POST',
                                           data={"user": "wördy",
                                                 "resolver": resolver,
                                                 "surname": "zappa",
                                                 "givenname": "frank",
                                                 "email": "f@z.com",
                                                 "phone": "12345",
                                                 "mobile": "12345",
                                                 "password": "12345"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") > 6, result.get("value"))

        # Get users
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "wördy".encode('utf-8')}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertEqual(result.get("value")[0].get("username"), "wördy")

        # Update by administrator. Set the password to "passwort"
        with self.app.test_request_context('/user/',
                                           method='PUT',
                                           query_string=urlencode(
                                               {"user": "wördy".encode('utf-8'),
                                                "resolver": resolver,
                                                "password": "passwort"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Get user authentication and update by user.
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "wördy@{0!s}".format(realm).encode('utf-8'),
                                                 "password": "passwort"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            wordy_auth_token = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)

        # Even if a user specifies another username, the username is
        # overwritten by his own name!
        with self.app.test_request_context('/user/',
                                           method='PUT',
                                           query_string=urlencode(
                                               {"user": "wördy2".encode('utf-8'),
                                                "resolver": resolver,
                                                "password": "newPassword"}),
                                           headers={'Authorization': wordy_auth_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Although the user "wördy" tried to update the password of user
        # "wördy2", he updated his own password.
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "wördy@{0!s}".format(realm).encode('utf-8'),
                                                 "password": "newPassword"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)

        # Delete the users
        with self.app.test_request_context(quote(f"/user/{resolver}/wördy"),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))
        # Check that the user is removed from the resolver
        res = get_resolver_object(resolver)
        uid = res.getUserId("wördy")
        self.assertEqual(uid, "")

    def test_10_additional_attributes(self):
        with self.app.test_request_context('/user/attribute',
                                           method='POST',
                                           data={"user": "cornelius@realm1",
                                                 "key": "newattribute",
                                                 "value": "newvalue"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), res.data)
            self.assertEqual(result.get("error").get("message"),
                             "You are not allowed to set the custom user attribute newattribute!")

        # Allow to set custom attributes
        set_policy("custom_attr", scope=SCOPE.ADMIN,
                   action="{0!s}=:*:*".format(PolicyAction.SET_USER_ATTRIBUTES))

        # Check that the user has not attribute
        with self.app.test_request_context('/user/attribute',
                                           method='GET',
                                           query_string={"user": "cornelius@realm1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertNotIn("newattribute", result.get("value"))

        with self.app.test_request_context('/user/attribute',
                                           method='POST',
                                           data={"user": "cornelius@realm1",
                                                 "key": "newattribute",
                                                 "value": "newvalue"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertTrue(result.get("value") >= 0)

        # Now we verify if the user has the additional attribute:
        with self.app.test_request_context('/user/attribute',
                                           method='GET',
                                           query_string={"user": "cornelius@realm1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertIn("newattribute", result.get("value"))
            self.assertEqual(result.get("value").get("newattribute"), "newvalue")

        with self.app.test_request_context('/user/attribute',
                                           method='GET',
                                           query_string={"user": "cornelius@realm1",
                                                         "key": "newattribute"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertEqual(result.get("value"), "newvalue")

        # Now we check, if the additional attribute is also contained in the
        # user listing
        delete_policy("custom_attr")
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string={"realm": "realm1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            additional_attribute_found = False
            # check in the user list for the username=cornelius
            for user in result.get("value"):
                if user.get("username") == "cornelius":
                    self.assertEqual(user.get("newattribute"), "newvalue")
                    additional_attribute_found = True
            self.assertTrue(additional_attribute_found)

        # Now we search for the one explicit user
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string={"realm": "realm1",
                                                         "username": "cornelius"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # check in the user list for the username=cornelius
            self.assertEqual(len(result.get("value")), 1)
            self.assertEqual(result.get("value")[0].get("newattribute"), "newvalue")

        # The additional attribute should also be returned, if the user authenticates successfully.
        init_token({"serial": "SPASS1", "type": "spass", "pin": "test"},
                   user=User("cornelius", self.realm1))
        set_policy(name="POL1", scope=SCOPE.AUTHZ, action=PolicyAction.ADDUSERINRESPONSE)
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@realm1",
                                                 "pass": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            details = res.json.get("detail")
            user_data = details.get("user")
            self.assertIn("newattribute", user_data)
            self.assertEqual(user_data.get("newattribute"), "newvalue")
        remove_token("SPASS1")
        delete_policy("POL1")

        # Try to delete custom user attributes without a policy
        with self.app.test_request_context('/user/attribute/newattribute/cornelius/realm1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), res.data)
            error = result.get("error")
            self.assertEqual("You are not allowed to delete the custom user attribute newattribute!",
                             error.get("message"))

        # Now we delete the additional user attribute
        set_policy("custom_attr", scope=SCOPE.ADMIN,
                   action="{0!s}=*".format(PolicyAction.DELETE_USER_ATTRIBUTES))
        with self.app.test_request_context('/user/attribute/newattribute/cornelius/realm1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertTrue(result.get("value") >= 0)

        # and verify, that it is gone
        with self.app.test_request_context('/user/attribute',
                                           method='GET',
                                           query_string={"user": "cornelius@realm1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertNotIn("newattribute", result.get("value"))

        # The admin is allowed to delete all attributes. Check what happens
        # if the admin tries to delete an attribute that does not exist:
        # Returns a result-value: 0
        with self.app.test_request_context('/user/attribute/doesnotexist/cornelius/realm1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertTrue(result.get("value") == 0)

        # Check, which attributes the admin is allowed to set or delete
        set_policy("custom_attr", scope=SCOPE.ADMIN,
                   action="{0!s}=:hello: one two".format(PolicyAction.SET_USER_ATTRIBUTES))
        set_policy("custom_attr2", scope=SCOPE.ADMIN,
                   action="{0!s}=:hello2: * :hello: three".format(PolicyAction.SET_USER_ATTRIBUTES))
        set_policy("custom_attr3", scope=SCOPE.ADMIN,
                   action="{0!s}=:*: on off".format(PolicyAction.SET_USER_ATTRIBUTES))
        set_policy("custom_attr4", scope=SCOPE.ADMIN,
                   action="{0!s}=*".format(PolicyAction.DELETE_USER_ATTRIBUTES))
        with self.app.test_request_context('/user/editable_attributes/',
                                           method='GET',
                                           query_string={"user": "cornelius@realm1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertIn("delete", value)
            self.assertEqual(value.get("delete"), ['*'])
            self.assertIn("set", value)
            setables = value.get("set")
            self.assertIn("*", setables)
            self.assertIn("hello", setables)
            self.assertIn("hello2", setables)
            self.assertEqual(["off", "on"], sorted(setables.get("*")))
            self.assertIn("one", setables.get("hello"))
            self.assertIn("two", setables.get("hello"))
            self.assertIn("three", setables.get("hello"))
            self.assertEqual(["*"], setables.get("hello2"))

        set_policy("custom_create_user", scope=SCOPE.ADMIN,
                   action=PolicyAction.ADDUSER)
        # CREATE a user
        self._create_user_wordy()
        self._get_wordy_auth_token()
        # The admin sets attributes for this user:
        with self.app.test_request_context('/user/attribute',
                                           method='POST',
                                           data={"user": "wordy@sqlrealm",
                                                 "key": "hello",
                                                 "value": "one"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertTrue(result.get("value") >= 0)

        # We let the user wordy@sqlrealm login and GET his attributes
        with self.app.test_request_context('/user/attribute',
                                           method='GET',
                                           query_string={"user": "cornelius@realm1"},
                                           headers={'Authorization': self.wordy_auth_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertIn("hello", result.get("value"))
            self.assertEqual("one", result.get("value").get("hello"))

        # The user tries to delete his attribute, but he is not allowed to.
        with self.app.test_request_context('/user/attribute/hello/wordy/sqlrealm',
                                           method='DELETE',
                                           headers={'Authorization': self.wordy_auth_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), res.data)
            error = result.get("error")
            self.assertEqual("You are not allowed to delete the custom user attribute hello!",
                             error.get("message"))

        # The user tries to set an attribute, but he is not allowed to.
        with self.app.test_request_context('/user/attribute',
                                           method='POST',
                                           data={"key": "newattr",
                                                 "value": "newvalue"},
                                           headers={'Authorization': self.wordy_auth_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), res.data)
            error = result.get("error")
            self.assertEqual("You are not allowed to set the custom user attribute newattr!",
                             error.get("message"))

        delete_policy("custom_attr")
        delete_policy("custom_attr2")
        delete_policy("custom_attr3")
        delete_policy("custom_attr4")
        delete_policy("custom_create_user")

    def test_11_internal_custom_user_attributes(self):
        """The ``last_used_token_`` prefix used to be reserved in
        customuserattribute because internal state was stored there. Now
        that internal state lives in a separate table, admins are free to
        use the prefix as a regular custom-attribute name."""
        self.setUp_user_realms()
        set_policy("custom_attribute", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.SET_USER_ATTRIBUTES}=:*:*,{PolicyAction.DELETE_USER_ATTRIBUTES}='*'")

        attrkey = f"{InternalUserAttributes.LAST_USED_TOKEN}_privacyIDEA-cp"

        # Setting a key with the (formerly reserved) prefix is now allowed.
        with self.app.test_request_context("/user/attribute",
                                           method="POST",
                                           data={"user": "hans",
                                                 "realm": self.realm1,
                                                 "key": attrkey,
                                                 "value": "push"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result", {}).get("status"), res.data)

        # And deleting it works the same as any other custom attribute.
        with self.app.test_request_context(
                f"/user/attribute/{attrkey}/hans/{self.realm1}",
                method="DELETE",
                data={},
                headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json.get("result", {}).get("status"), res.data)

        delete_policy("custom_attribute")

    def test_11b_get_internal_attributes(self):
        """The /user/internal_attribute endpoint exposes the diagnostic
        cache (fido2_user_id, last_used_token) to admins."""
        self.setUp_user_realms()
        user = User("hans", self.realm1)
        user.set_internal_attribute("last_used_token", {"privacyidea-cp": "push"})
        user.set_internal_attribute("fido2_user_id", "abc123")

        with self.app.test_request_context("/user/internal_attribute",
                                           method="GET",
                                           query_string={"user": "hans", "realm": self.realm1},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result", {}).get("value")
            self.assertEqual({"privacyidea-cp": "push"}, value.get("last_used_token"))
            self.assertEqual("abc123", value.get("fido2_user_id"))

        user.delete_internal_attribute()

    def test_11c_get_internal_attributes_realm_scoped(self):
        """A realm-restricted admin may only read internal attributes of
        users in their own realm(s)."""
        self.setUp_user_realms()
        self.setUp_user_realm2()
        realm1_user = User("hans", self.realm1)
        realm1_user.set_internal_attribute("fido2_user_id", "realm1-id")
        realm2_user = User("cornelius", self.realm2)
        realm2_user.set_internal_attribute("fido2_user_id", "realm2-id")

        # Admin policy that grants the right only for realm1
        set_policy("internal_attr_realm1", scope=SCOPE.ADMIN,
                   action=PolicyAction.GET_USER_INTERNAL_ATTRIBUTES,
                   realm=self.realm1)

        # Reading a realm1 user is allowed
        with self.app.test_request_context("/user/internal_attribute",
                                           method="GET",
                                           query_string={"user": "hans", "realm": self.realm1},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.assertEqual("realm1-id", result.get("value").get("fido2_user_id"))

        # Reading a realm2 user is denied for this realm-restricted admin
        with self.app.test_request_context("/user/internal_attribute",
                                           method="GET",
                                           query_string={"user": "cornelius", "realm": self.realm2},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), res.data)
            self.assertIn(PolicyAction.GET_USER_INTERNAL_ATTRIBUTES,
                          result.get("error").get("message"))

        delete_policy("internal_attr_realm1")
        realm1_user.delete_internal_attribute()
        realm2_user.delete_internal_attribute()

    def test_11d_get_internal_attributes_no_realm_no_bypass(self):
        """Omitting the realm must not let a realm-restricted admin read a
        user in a different (default) realm. The realm used to read the data
        must match the realm the policy authorized, not the default realm
        that request.User would otherwise resolve to."""
        self.setUp_user_realms()      # realm1 is the default realm
        self.setUp_user_realm2()
        # The secret lives on the user in the DEFAULT realm (realm1)
        default_user = User("hans", self.realm1)
        default_user.set_internal_attribute("fido2_user_id", "realm1-secret")

        # Admin is restricted to realm2 only
        set_policy("internal_attr_realm2", scope=SCOPE.ADMIN,
                   action=PolicyAction.GET_USER_INTERNAL_ATTRIBUTES,
                   realm=self.realm2)

        # Request without a realm: realmadmin injects realm2, so the user must
        # be resolved in realm2 (hans@realm2 has no internal attributes) and
        # the realm1 secret must never leak.
        with self.app.test_request_context("/user/internal_attribute",
                                           method="GET",
                                           query_string={"user": "hans"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            value = (res.json.get("result") or {}).get("value") or {}
            self.assertNotEqual("realm1-secret", value.get("fido2_user_id"), res.data)

        delete_policy("internal_attr_realm2")
        default_user.delete_internal_attribute()

    def test_12_get_users(self):
        self.setUp_user_realms()

        # add some custom attributes
        user = User("cornelius", self.realm1)
        user.set_attribute("custom1", "value1")
        user.set_attribute("custom2", "value2")
        user.set_attribute("custom3", "value3")

        # Request with only resolver (no realm) resolves the resolver to its realm(s)
        # and returns users in realm context, including custom attributes
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "cornelius", "resolver": self.resolvername1}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            user = result.get("value")[0]
            # should contain all attributes including custom attributes since realm is resolved
            expected_attributes = {"userid", "username", "surname", "givenname", "email", "phone", "mobile",
                                   "description", "resolver", "editable", "realm",
                                   "custom1", "custom2", "custom3"}
            self.assertSetEqual(expected_attributes, set(user.keys()))
            self.assertEqual("1000", user.get("userid"))
            self.assertEqual("cornelius", user.get("username"))
            self.assertEqual("", user.get("surname"))
            self.assertEqual("Cornelius", user.get("givenname"))
            self.assertEqual("user@localhost.localdomain", user.get("email"))
            self.assertEqual("+491234566", user.get("phone"))
            self.assertEqual("+491111111", user.get("mobile"))
            self.assertEqual("Cornelius,field2,+491111111,+491234566,user@localhost.localdomain",
                             user.get("description"))
            self.assertEqual(self.resolvername1, user.get("resolver"))
            self.assertEqual(False, user.get("editable"))
            self.assertEqual(self.realm1, user.get("realm"))

        # With realm as request parameter we also get the custom attributes of the users
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode({"username": "cornelius", "realm": self.realm1}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            user = result.get("value")[0]
            # should contain all attributes ( resolver, editable and realm are added on lib layer not by the resolver itself)
            expected_attributes = {"userid", "username", "surname", "givenname", "email", "phone", "mobile",
                                   "description", "resolver", "editable", "realm",
                                   "custom1", "custom2", "custom3"}
            self.assertSetEqual(expected_attributes, set(user.keys()))
            self.assertEqual("1000", user.get("userid"))
            self.assertEqual("cornelius", user.get("username"))
            self.assertEqual("", user.get("surname"))
            self.assertEqual("Cornelius", user.get("givenname"))
            self.assertEqual("user@localhost.localdomain", user.get("email"))
            self.assertEqual("+491234566", user.get("phone"))
            self.assertEqual("+491111111", user.get("mobile"))
            self.assertEqual("Cornelius,field2,+491111111,+491234566,user@localhost.localdomain",
                             user.get("description"))
            self.assertEqual(self.resolvername1, user.get("resolver"))
            self.assertEqual(False, user.get("editable"))
            self.assertEqual(self.realm1, user.get("realm"))
            self.assertEqual("value1", user.get("custom1"))
            self.assertEqual("value2", user.get("custom2"))
            self.assertEqual("value3", user.get("custom3"))

        # Do not get custom attributes if explicitly disabled
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode({"username": "cornelius", "realm": self.realm1,
                                                                   "include_custom_attributes": False}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            user = result.get("value")[0]
            # should contain all attributes ( resolver and editable are added on lib layer not by the resolver itself)
            expected_attributes = {"userid", "username", "surname", "givenname", "email", "phone", "mobile",
                                   "description", "resolver", "editable", "realm"}
            self.assertSetEqual(expected_attributes, set(user.keys()))
            self.assertEqual("1000", user.get("userid"))
            self.assertEqual("cornelius", user.get("username"))
            self.assertEqual("", user.get("surname"))
            self.assertEqual("Cornelius", user.get("givenname"))
            self.assertEqual("user@localhost.localdomain", user.get("email"))
            self.assertEqual("+491234566", user.get("phone"))
            self.assertEqual("+491111111", user.get("mobile"))
            self.assertEqual("Cornelius,field2,+491111111,+491234566,user@localhost.localdomain",
                             user.get("description"))
            self.assertEqual(self.resolvername1, user.get("resolver"))
            self.assertEqual(False, user.get("editable"))

        # Request specific attributes (without custom attributes)
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "cornelius", "realm": self.realm1,
                                                "attributes": "username,email"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            user = result.get("value")[0]
            # realm is only added when explicitly requested
            self.assertDictEqual({"username": "cornelius", "email": "user@localhost.localdomain"}, user)

        # Request specific attributes with editable and resolver which are not set in the user store itself
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "cornelius", "realm": self.realm1,
                                                "attributes": "username,email,editable,resolver"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            user = result.get("value")[0]
            # realm is only added when explicitly requested
            self.assertDictEqual({"username": "cornelius", "email": "user@localhost.localdomain", "editable": False,
                                  "resolver": self.resolvername1}, user)

        # Request specific attributes with custom attributes
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "cornelius", "realm": self.realm1,
                                                "attributes": "username,email,custom2,custom1"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            user = result.get("value")[0]
            # realm is only added when explicitly requested
            expected_user = {"username": "cornelius", "email": "user@localhost.localdomain", "custom1": "value1",
                             "custom2": "value2"}
            self.assertDictEqual(expected_user, user)

        # Request specific attributes with custom attributes in attributes list, but disable custom_attributes retrieval
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "cornelius", "realm": self.realm1,
                                                "attributes": "username,email,custom2,custom1",
                                                "include_custom_attributes": False}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            user = result.get("value")[0]
            # should contain all attributes ( resolver and editable are added on lib layer not by the resolver itself)
            expected_user = {"username": "cornelius", "email": "user@localhost.localdomain"}
            self.assertDictEqual(expected_user, user)

        # Clean up
        User("cornelius", self.realm1).delete_attribute()

    def test_13_get_users_resolver_scoping(self):
        # Add a second passwd resolver to realm1 alongside resolvername1.
        # Both resolvers read the same PWFILE, so they hold the same set of users.
        # Querying with ``?resolver=<second>`` must return users carrying the
        # second resolver's name in their record — under the pre-fix behaviour
        # the resolver parameter was silently expanded to every resolver in the
        # realm and the higher-priority resolver won (username, realm) dedup,
        # so callers saw the wrong ``resolver`` field.
        self.setUp_user_realms()
        second_resolver = "resolver_secondary"
        save_resolver({"resolver": second_resolver,
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        # Both the realm-membership change and the resolver row need to be
        # rolled back even if a later assertion raises; register cleanups
        # before mutating realm1 so they fire in reverse order on teardown.
        self.addCleanup(delete_resolver, second_resolver)
        self.addCleanup(set_realm, self.realm1, [{"name": self.resolvername1}])
        (added, failed) = set_realm(self.realm1,
                                    [{"name": self.resolvername1, "priority": 1},
                                     {"name": second_resolver, "priority": 2}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 2)

        def assert_query_narrows_to(query_params, expected_resolver):
            with self.app.test_request_context('/user/',
                                               method='GET',
                                               query_string=urlencode(query_params),
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                self.assertTrue(result.get("status"))
                users = result.get("value")
                self.assertTrue(len(users) > 0, users)
                for user in users:
                    self.assertEqual(expected_resolver, user.get("resolver"), user)

        # ?resolver=<second> alone — narrows across every realm containing it.
        assert_query_narrows_to({"resolver": second_resolver}, second_resolver)
        # realm + resolver — realm1 contains the second resolver, so the query
        # narrows to it within that realm.
        assert_query_narrows_to({"realm": self.realm1, "resolver": second_resolver}, second_resolver)

    def test_14_get_users_skipped_resolvers_dedup(self):
        # When a resolver fails across multiple realms, the lib collects one
        # entry per (resolver, realm), but the API formatter must dedupe by
        # resolver name so callers see each broken resolver only once in
        # ``detail.skipped_resolvers``.
        from privacyidea.lib.error import ResolverError
        self.setUp_user_realms()
        flaky = "resolver_flaky"
        save_resolver({"resolver": flaky, "type": "passwdresolver", "fileName": PWFILE})
        self.addCleanup(delete_resolver, flaky)
        self.addCleanup(set_realm, self.realm1, [{"name": self.resolvername1}])
        self.addCleanup(delete_realm, "extra_realm")
        set_realm(self.realm1, [{"name": self.resolvername1}, {"name": flaky}])
        set_realm("extra_realm", [{"name": flaky}])

        with patch_resolver_to_raise(flaky, ResolverError("simulated outage")):
            with self.app.test_request_context('/user/',
                                               method='GET',
                                               query_string=urlencode({"resolver": flaky}),
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                # The only queried resolver raised, so no users are returned.
                self.assertEqual([], result.get("value"), res.json)
                detail = res.json.get("detail") or {}
                self.assertEqual([flaky], detail.get("skipped_resolvers"), res.json)

    def test_15_get_users_empty_attributes_param(self):
        # An empty ``attributes=`` must behave like omitting the parameter
        # entirely, not like an unrecognised resolver search field: it must
        # not cause the resolver to be reported as skipped.
        self.setUp_user_realms()
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "cornelius", "attributes": ""}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(len(result.get("value")) > 0, res.json)
            self.assertIsNone(res.json.get("detail"), res.json)

    def test_16_get_users_has_tokens_filter(self):
        self.setUp_user_realms()

        def usernames(query):
            with self.app.test_request_context('/user/',
                                               method='GET',
                                               query_string=urlencode(query),
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res.json)
                return [user.get("username") for user in res.json["result"]["value"]]

        everyone = usernames({"realm": self.realm1})
        self.assertIn("cornelius", everyone)

        serial = None
        try:
            token = init_token({"type": "spass"}, user=User("cornelius", self.realm1))
            serial = token.get_serial()

            self.assertEqual(["cornelius"], usernames({"realm": self.realm1, "has_tokens": "True"}))

            without_tokens = usernames({"realm": self.realm1, "has_tokens": "False"})
            self.assertNotIn("cornelius", without_tokens)
            self.assertEqual(len(everyone) - 1, len(without_tokens))

            # The filter needs the user id, which an attribute list of its own does not ask for.
            self.assertEqual(["cornelius"],
                             usernames({"realm": self.realm1, "has_tokens": "True",
                                        "attributes": "username"}))
        finally:
            if serial:
                remove_token(serial)

        self.assertEqual([], usernames({"realm": self.realm1, "has_tokens": "True"}))

    def test_17_get_users_has_tokens_filter_as_a_user(self):
        self.setUp_user_realms()
        self.authenticate_selfservice_user()
        set_policy(name="pol-userlist", scope=SCOPE.USER, action=PolicyAction.USERLIST)

        def own_usernames(query):
            with self.app.test_request_context('/user/',
                                               method='GET',
                                               query_string=urlencode(query),
                                               headers={'Authorization': self.at_user}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res.json)
                return [user.get("username") for user in res.json["result"]["value"]]

        serial = None
        try:
            # A user only ever sees their own record, so the filter decides whether that
            # one record is listed - never whether someone else's is.
            self.assertEqual([], own_usernames({"has_tokens": "True"}))
            self.assertEqual(["selfservice"], own_usernames({"has_tokens": "False"}))

            token = init_token({"type": "spass"}, user=User("selfservice", self.realm1))
            serial = token.get_serial()

            self.assertEqual(["selfservice"], own_usernames({"has_tokens": "True"}))
            self.assertEqual([], own_usernames({"has_tokens": "False"}))
        finally:
            if serial:
                remove_token(serial)
            delete_policy("pol-userlist")

    def test_18_get_users_has_tokens_rejects_an_unknown_value(self):
        self.setUp_user_realms()
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode({"realm": self.realm1, "has_tokens": "yes"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res.json)

    def test_19_count_users(self):
        self.setUp_user_realms()

        def get(path, query, auth=None):
            with self.app.test_request_context(path,
                                               method='GET',
                                               query_string=urlencode(query),
                                               headers={'Authorization': auth or self.at}):
                return self.app.full_dispatch_request()

        def count(query, auth=None):
            res = get('/user/count', query, auth)
            self.assertEqual(200, res.status_code, res.json)
            return res.json["result"]["value"]

        everyone = get('/user/', {"realm": self.realm1}).json["result"]["value"]
        self.assertEqual({"count": len(everyone), "with_tokens": 0}, count({"realm": self.realm1}))

        serial = None
        try:
            token = init_token({"type": "spass"}, user=User("cornelius", self.realm1))
            serial = token.get_serial()
            counts = count({"realm": self.realm1})
            self.assertEqual({"count": len(everyone), "with_tokens": 1}, counts)
            with_tokens = get('/user/', {"realm": self.realm1, "has_tokens": "True"}).json["result"]["value"]
            self.assertEqual(len(with_tokens), counts["with_tokens"])

            # A user counts only their own record, as they only ever list that one.
            self.authenticate_selfservice_user()
            set_policy(name="pol-userlist", scope=SCOPE.USER, action=PolicyAction.USERLIST)
            self.assertEqual({"count": 1, "with_tokens": 0}, count({"realm": self.realm1}, auth=self.at_user))
            delete_policy("pol-userlist")

            # The userlist action guards the count as it guards the list.
            set_policy(name="pol-only-init", scope=SCOPE.ADMIN, action="enrollHOTP")
            res = get('/user/count', {"realm": self.realm1})
            self.assertEqual(403, res.status_code, res.json)
            delete_policy("pol-only-init")
        finally:
            if serial:
                remove_token(serial)

    def test_20_count_users_reports_skipped_resolvers(self):
        self.setUp_user_realms()
        with patch_resolver_to_raise(self.resolvername1, ResolverError("down")):
            with self.app.test_request_context('/user/count',
                                               method='GET',
                                               query_string=urlencode({"realm": self.realm1}),
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({"count": 0, "with_tokens": 0}, res.json["result"]["value"])
        self.assertEqual([self.resolvername1], res.json["detail"]["skipped_resolvers"])

    def test_21_resolver_is_bound_to_the_admins_realms(self):
        """An admin restricted to one realm can not address a resolver of another realm.

        The user endpoints take the target store from the request: `resolver` in the body for create
        and update, and the first path component for delete. The policy is matched against the realm,
        so without a binding between the two a realm-restricted admin reaches every resolver.
        """
        self.setUp_user_realms()
        # an editable resolver in a realm the admin was not granted
        foreign_parameters = dict(self.parameters, resolver="foreign_sql", type="sqlresolver", Editable=True)
        self.assertTrue(save_resolver(foreign_parameters) > 0)
        set_realm("otherrealm", [{"name": "foreign_sql"}])

        set_policy("admin_realm1", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.UPDATEUSER},{PolicyAction.ADDUSER},{PolicyAction.DELETEUSER}",
                   realm=self.realm1)

        # create: named by resolver alone, so the resolver has to be in a realm the admin was granted
        with self.app.test_request_context("/user/", method="POST",
                                           data={"user": "planted", "resolver": "foreign_sql",
                                                 "password": "Test1234!"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
            self.assertIn("foreign_sql", res.json["result"]["error"]["message"])

        # delete: same, with the resolver in the path
        with self.app.test_request_context("/user/foreign_sql/cornelius", method="DELETE",
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
            self.assertIn("foreign_sql", res.json["result"]["error"]["message"])

        # update: the realm the policy matches and the resolver the write follows must agree
        with self.app.test_request_context("/user/", method="PUT",
                                           data={"user": "cornelius", "realm": self.realm1,
                                                 "resolver": "foreign_sql", "email": "x@example.com"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
            self.assertIn("foreign_sql", res.json["result"]["error"]["message"])

        # a resolver of the granted realm is not refused by the binding
        with self.app.test_request_context(f"/user/{self.resolvername1}/cornelius", method="DELETE",
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertNotEqual(403, res.status_code, res.json)

        delete_policy("admin_realm1")
        delete_realm("otherrealm")
        delete_resolver("foreign_sql")

    def test_22_token_and_container_assign_reject_a_foreign_resolver(self):
        """Assigning by (realm, resolver) must not let the owner come from another realm."""
        self.setUp_user_realms()
        save_resolver({"resolver": "foreign_pw", "type": "passwdresolver", "fileName": PWFILE})
        set_realm("otherrealm", [{"name": "foreign_pw"}])
        set_policy("admin_realm1_assign", scope=SCOPE.ADMIN,
                   action=PolicyAction.ASSIGN, realm=self.realm1)
        token = init_token({"type": "hotp", "genkey": True})

        with self.app.test_request_context("/token/assign", method="POST",
                                           data={"serial": token.get_serial(), "user": "cornelius",
                                                 "realm": self.realm1, "resolver": "foreign_pw"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
        self.assertIsNone(get_tokens(serial=token.get_serial())[0].user)

        remove_token(token.get_serial())
        delete_policy("admin_realm1_assign")
        delete_realm("otherrealm")
        delete_resolver("foreign_pw")

    def _assign_user_to_new_container(self):
        serial = init_container({"type": "generic"})["container_serial"]
        with self.app.test_request_context(f"/container/{serial}/assign", method="POST",
                                           data={"user": "cornelius", "realm": self.realm1,
                                                 "resolver": self.resolvername1},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        delete_container_by_serial(serial)
        return res

    def test_23_user_scoped_grant_does_not_revoke_a_realm_grant(self):
        """A further, narrower grant of the same action must not take away what a realm grant allows."""
        self.setUp_user_realms()
        set_policy("assign_realm1", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER,
                   realm=self.realm1)
        set_policy("assign_one_user", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER,
                   user="someone")

        res = self._assign_user_to_new_container()
        delete_policy("assign_realm1")
        delete_policy("assign_one_user")

        self.assertEqual(200, res.status_code, res.json)

    def test_24_unrestricted_grant_wins_regardless_of_policy_order(self):
        """An unrestricted grant of the action allows the request whichever policy is evaluated first."""
        self.setUp_user_realms()
        scopes = {"user": {"user": "someone"}, "all": {}}
        status_by_first_policy = {}
        for first, second in [("all", "user"), ("user", "all")]:
            set_policy(f"a_{first}", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER,
                       priority=1, **scopes[first])
            set_policy(f"b_{second}", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER,
                       priority=2, **scopes[second])
            status_by_first_policy[first] = self._assign_user_to_new_container().status_code
            delete_policy(f"a_{first}")
            delete_policy(f"b_{second}")

        self.assertEqual({"all": 200, "user": 200}, status_by_first_policy)


class UserListScopeTestCase(MyApiTestCase):
    """
    Which users an administrator may list, and whether they may learn which of them own a token.
    """

    def _get(self, path: str, query: dict | None = None, json: dict | None = None) -> tuple[int, Any]:
        """GET as the administrator, with the query string and, if given, the parameters as a JSON body."""
        with self.app.test_request_context(path, method='GET', query_string=urlencode(query or {}), json=json,
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
        return res.status_code, (res.json.get("result") or {}).get("value")

    def _realms_listed(self, query: dict | None = None, json: dict | None = None) -> set[str]:
        status, users = self._get('/user/', query, json)
        self.assertEqual(200, status, users)
        return {user["realm"] for user in users}

    def test_01_several_realms_are_checked_one_by_one(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_policy("pol-userlist", scope=SCOPE.ADMIN, action=PolicyAction.USERLIST, realm=self.realm1)
        set_policy("pol-tokenlist", scope=SCOPE.ADMIN, action=PolicyAction.TOKENLIST)
        try:
            # A realm that is not granted is refused however the realms are given, and does not
            # come along with one that is.
            for path in ('/user/', '/user/count'):
                self.assertEqual(403, self._get(path, {"realm": f"{self.realm1},{self.realm3}"})[0], path)
                self.assertEqual(403, self._get(path, json={"realm": [self.realm1, self.realm3]})[0], path)
                self.assertEqual(403, self._get(path, json={"realm": [self.realm3]})[0], path)
                self.assertEqual(200, self._get(path, json={"realm": [self.realm1]})[0], path)
            # Realm names are lowercase, so the case a realm is given in does not matter.
            self.assertEqual({self.realm1}, self._realms_listed({"realm": self.realm1.upper()}))
            self.assertEqual(403, self._get('/user/', {"realm": self.realm3.upper()})[0])

            # Several granted realms may be asked for at once.
            set_policy("pol-userlist", scope=SCOPE.ADMIN, action=PolicyAction.USERLIST,
                       realm=[self.realm1, self.realm3])
            self.assertEqual({self.realm1, self.realm3},
                             self._realms_listed({"realm": f"{self.realm1},{self.realm3}"}))
        finally:
            delete_policy("pol-userlist")
            delete_policy("pol-tokenlist")

    def test_02_a_realm_excluded_by_the_policy_stays_excluded(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_policy("pol-userlist", scope=SCOPE.ADMIN, action=PolicyAction.USERLIST, realm=f"*,!{self.realm3}")
        try:
            for query in ({"realm": self.realm3}, {"realm": self.realm3.upper()},
                          {"realm": f"{self.realm1},{self.realm3}"}):
                self.assertEqual(403, self._get('/user/', query)[0], query)
            self.assertEqual(403, self._get('/user/', json={"realm": [self.realm1, self.realm3]})[0])
            # Without a realm, the realms that are not excluded are listed.
            realms = self._realms_listed()
            self.assertIn(self.realm1, realms)
            self.assertNotIn(self.realm3, realms)
        finally:
            delete_policy("pol-userlist")

    def test_03_the_resolvers_of_the_policy_restrict_the_list(self):
        self.setUp_user_realm4_with_2_resolvers()
        serial = init_token({"type": "spass"}, user=User("cornelius", self.realm4, self.resolvername3)).get_serial()
        set_policy("pol-userlist", scope=SCOPE.ADMIN, action=PolicyAction.USERLIST, realm=self.realm4,
                   resolver=self.resolvername3)
        set_policy("pol-tokenlist", scope=SCOPE.ADMIN, action=PolicyAction.TOKENLIST)
        try:
            status, users = self._get('/user/', {"realm": self.realm4})
            self.assertEqual(200, status, users)
            self.assertEqual({self.resolvername3}, {user["resolver"] for user in users})
            # The resolver of higher priority is not queried, so its cornelius does not hide this one.
            self.assertIn(("cornelius", self.resolvername3), {(user["username"], user["resolver"]) for user in users})
            self.assertEqual((200, {"count": len(users), "with_tokens": 1}),
                             self._get('/user/count', {"realm": self.realm4}))
            status, owners = self._get('/user/', {"realm": self.realm4, "has_tokens": "True"})
            self.assertEqual((200, [("cornelius", self.resolvername3)]),
                             (status, [(user["username"], user["resolver"]) for user in owners]))
            # Asking for a resolver the policy does not name is refused.
            self.assertEqual(403, self._get('/user/', {"realm": self.realm4, "resolver": self.resolvername1})[0])
        finally:
            remove_token(serial)
            delete_policy("pol-userlist")
            delete_policy("pol-tokenlist")

    def test_04_the_users_of_the_policy_restrict_the_list(self):
        self.setUp_user_realms()
        set_policy("pol-userlist", scope=SCOPE.ADMIN, action=PolicyAction.USERLIST, realm=self.realm1,
                   user="cornelius")
        set_policy("pol-tokenlist", scope=SCOPE.ADMIN, action=PolicyAction.TOKENLIST)
        try:
            status, users = self._get('/user/', {"realm": self.realm1})
            self.assertEqual((200, ["cornelius"]), (status, [user["username"] for user in users]))
            self.assertEqual((200, {"count": 1, "with_tokens": 0}), self._get('/user/count', {"realm": self.realm1}))
            self.assertEqual(403, self._get('/user/', {"realm": self.realm1, "user": "selfservice"})[0])

            # A policy that names no user grants every user.
            set_policy("pol-userlist-all", scope=SCOPE.ADMIN, action=PolicyAction.USERLIST, realm=self.realm1)
            status, users = self._get('/user/', {"realm": self.realm1})
            self.assertEqual(200, status, users)
            self.assertIn("selfservice", {user["username"] for user in users})
        finally:
            delete_policy("pol-userlist")
            delete_policy("pol-userlist-all")
            delete_policy("pol-tokenlist")

    def test_05_telling_who_owns_a_token_requires_the_tokenlist_action(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        serial = init_token({"type": "spass"}, user=User("cornelius", self.realm1)).get_serial()
        set_policy("pol-userlist", scope=SCOPE.ADMIN, action=PolicyAction.USERLIST)
        try:
            # Without tokenlist the users are listed, but not by whether they own a token.
            self.assertEqual(200, self._get('/user/', {"realm": self.realm1})[0])
            for has_tokens in ("True", "False"):
                self.assertEqual(403, self._get('/user/', {"realm": self.realm1, "has_tokens": has_tokens})[0])
            self.assertEqual(403, self._get('/user/count', {"realm": self.realm1})[0])

            # With tokenlist in one realm, in that realm only.
            set_policy("pol-tokenlist", scope=SCOPE.ADMIN, action=PolicyAction.TOKENLIST, realm=self.realm1)
            status, owners = self._get('/user/', {"realm": self.realm1, "has_tokens": "True"})
            self.assertEqual((200, ["cornelius"]), (status, [user["username"] for user in owners]))
            self.assertEqual(1, self._get('/user/count', {"realm": self.realm1})[1]["with_tokens"])
            self.assertEqual(403, self._get('/user/count', {"realm": self.realm3})[0])
            self.assertEqual(403, self._get('/user/count', {"realm": f"{self.realm1},{self.realm3}"})[0])
            # Without a realm every realm is listed, so it is needed in every realm.
            self.assertEqual(403, self._get('/user/count')[0])

            # Ownership is told exactly where the token list shows the tokens of the realm, however the
            # realms of the tokenlist policy are written.
            for token_realms in ("*", f"*,!{self.realm3}", f"{self.realm1},{self.realm3}"):
                set_policy("pol-tokenlist", scope=SCOPE.ADMIN, action=PolicyAction.TOKENLIST, realm=token_realms)
                token_listed = self._get('/token/', {"serial": serial})[1]["count"] == 1
                self.assertEqual(200 if token_listed else 403, self._get('/user/count', {"realm": self.realm1})[0],
                                 token_realms)
            self.assertEqual(200, self._get('/user/count', {"realm": self.realm1})[0])
            self.assertEqual(200, self._get('/user/count', {"realm": f"{self.realm1},{self.realm3}"})[0])
        finally:
            remove_token(serial)
            delete_policy("pol-userlist")
            delete_policy("pol-tokenlist")

    def test_06_the_audit_records_the_has_tokens_filter(self):
        self.setUp_user_realms()
        self.assertEqual(200, self._get('/user/', {"realm": self.realm1, "has_tokens": "False"})[0])
        audit_entry = self.find_most_recent_audit_entry(action="GET /user/")
        self.assertIn("has_tokens: False", audit_entry.get("info", ""), audit_entry)
