# coding: utf-8
from .base import MyTestCase
import json
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from urllib import urlencode

PWFILE = "tests/testdata/passwd"


class APIUsersTestCase(MyTestCase):

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

    def test_00_get_empty_users(self):
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"status": true' in res.data, res.data)
            self.assertTrue('"value": []' in res.data, res.data)

    def test_01_get_passwd_user(self):
        # create resolver
        with self.app.test_request_context('/resolver/r1',
                                           data=json.dumps({u"resolver": u"r1",
                                                 u"type": u"passwdresolver",
                                                 u"fileName": PWFILE}),
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"status": true' in res.data, res.data)
            self.assertTrue('"value": 1' in res.data, res.data)
        
        # create realm
        realm = u"realm1"
        resolvers = u"r1, r2"
        with self.app.test_request_context('/realm/{0!s}'.format(realm),
                                           data={u"resolvers": resolvers},
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
            value = result.get("result").get("value")
            self.assertTrue('r1' in value["added"], res.data)
            self.assertTrue('r2' in value["failed"], res.data)
                   
        # get user list
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({u"realm":
                                                                       realm}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
            value = result.get("result").get("value")
            self.assertTrue('"username": "cornelius"' in res.data, res.data)
            self.assertTrue('"username": "corny"' in res.data, res.data)

        # get user list with search dict
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({u"username":
                                                           "cornelius"}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
            value = result.get("result").get("value")
            self.assertTrue('"username": "cornelius"' in res.data, res.data)
            self.assertTrue('"username": "corny"' not in res.data, res.data)
            
        # get user with a non existing realm
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({"realm":
                                                            "non_existing"}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
            value = result.get("result").get("value")
            self.assertTrue('"username": "cornelius"' not in res.data, res.data)
            self.assertTrue('"username": "corny"' not in res.data, res.data)

    def test_02_create_update_delete_user(self):
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

        # CREATE a user
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") > 6, result.get("value"))

        # Get users
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": "wordy"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        # Get user authentication and update by user.
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "wordy@{0!s}".format(realm),
                                                 "password": "passwort"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
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
                                               {"user": "wordy2",
                                                "resolver": resolver,
                                                "password": "newPassword"}),
                                           headers={'Authorization':
                                                        wordy_auth_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        # Although the user "wordy" tried to update the password of user
        # "wordy2", he updated his own password.
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "wordy@{0!s}".format(realm),
                                                 "password": "newPassword"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            wordy_auth_token = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)

        # Delete the users
        with self.app.test_request_context('/user/{0!s}/{1!s}'.format(resolver, "wordy"),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

    def test_03_create_update_delete_unicode_user(self):
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

        # CREATE a user
        with self.app.test_request_context('/user/',
                                           method='POST',
                                           data={"user": u"wördy",
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") > 6, result.get("value"))

        # Get users
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           query_string=urlencode(
                                               {"username": u"wördy".encode('utf-8')}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"))
            self.assertEqual(result.get("value")[0].get("username"), u"wördy")

        # Update by administrator. Set the password to "passwort"
        with self.app.test_request_context('/user/',
                                           method='PUT',
                                           query_string=urlencode(
                                               {"user": u"wördy".encode('utf-8'),
                                                "resolver": resolver,
                                                "password": "passwort"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        # Get user authentication and update by user.
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": u"wördy@{0!s}".format(realm).encode('utf-8'),
                                                 "password": "passwort"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
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
                                               {"user": u"wördy2".encode('utf-8'),
                                                "resolver": resolver,
                                                "password": "newPassword"}),
                                           headers={'Authorization':
                                                        wordy_auth_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        # Although the user "wördy" tried to update the password of user
        # "wördy2", he updated his own password.
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": u"wördy@{0!s}".format(realm).encode('utf-8'),
                                                 "password": "newPassword"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            wordy_auth_token = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)

        # Delete the users
        with self.app.test_request_context(u'/user/{0!s}/{1!s}'.format(resolver, u"wördy").encode('utf-8'),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))