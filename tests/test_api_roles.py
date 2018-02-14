"""
This file tests the authentication of admin users and normal user (
selfservice) on the REST API.

implementation is contained in api/auth.py, api/token.py api/audit.py
"""
import json
from .base import MyTestCase
from privacyidea.lib.error import (TokenAdminError, UserError)
from privacyidea.lib.token import (get_tokens, remove_token, enable_token,
                                   assign_token, unassign_token)
from privacyidea.lib.user import User
from privacyidea.models import Token
from privacyidea.lib.realm import (set_realm, delete_realm)
from privacyidea.api.lib.postpolicy import DEFAULT_POLICY_TEMPLATE_URL
from privacyidea.lib.policy import ACTION, SCOPE, set_policy, delete_policy


PWFILE = "tests/testdata/passwords"


class APIAuthTestCase(MyTestCase):
    """
    This tests some side functionalities of the /auth API.
    """

    def test_00_missing_username(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

    def test_01_get_rights(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_admin = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "admin", result)

        with self.app.test_request_context('/auth/rights',
                                           method='GET',
                                           data={"username": "testadmin",
                                                 "password": "testpw"},
                                           headers={'Authorization':
                                                        self.at_admin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue("4eyes" in result.get("value"))
            self.assertTrue("hotp" in result.get("value"))
            self.assertTrue(result.get("status"), res.data)

    def test_02_REMOTE_USER(self):
        # Allow remote user
        set_policy(name="remote", scope=SCOPE.WEBUI, action="{0!s}=allowed".format(
                                                            ACTION.REMOTE_USER))

        # Admin remote user
        with self.app.test_request_context('/auth', method='POST',
                                           data={"username": "testadmin"},
                                           environ_base={"REMOTE_USER":
                                                             "testadmin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue("token" in result.get("value"))
            self.assertTrue("username" in result.get("value"))
            self.assertEqual(result.get("value").get("role"), "admin")
            self.assertTrue(result.get("status"), res.data)

        self.setUp_user_realms()
        # User "cornelius" from the default realm as normale user
        with self.app.test_request_context('/auth', method='POST',
                                           data={"username": "cornelius"},
                                           environ_base={"REMOTE_USER":
                                                             "cornelius"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue("token" in result.get("value"))
            self.assertTrue("username" in result.get("value"))
            self.assertEqual(result.get("value").get("role"), "user")
            self.assertTrue(result.get("status"), res.data)

        # Define the superuser_realm: "adminrealm"
        (added, failed) = set_realm("adminrealm",
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        # user cornelius is a member of the superuser_realm...
        with self.app.test_request_context('/auth', method='POST',
                                           data={"username":
                                                     "cornelius@adminrealm"},
                                           environ_base={"REMOTE_USER":
                                                     "cornelius@adminrealm"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue("token" in result.get("value"))
            self.assertTrue("username" in result.get("value"))
            # ...and will have the role admin
            self.assertEqual(result.get("value").get("role"), "admin")
            self.assertTrue(result.get("status"), res.data)

        delete_policy("remote")

    def test_03_realmadmin_get_user(self):
        # check issue #480
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        # testadmin is only allowed to view users in realm2
        set_policy(name="realmadmin", scope=SCOPE.ADMIN,
                   action=ACTION.USERLIST, realm=self.realm3, user="testadmin")

        with self.app.test_request_context('/user/',
                                           method='GET',
                                           data={},
                                           headers={'Authorization':
                                                        self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            # In the result list should only be users from reso3.
            for user in result.get("value"):
                self.assertEqual(user.get("resolver"), self.resolvername3)

        delete_policy("realmadmin")




class APISelfserviceTestCase(MyTestCase):

    my_serial = "myToken"
    foreign_serial = "notMyToken"

    def setUp(self):
        """
        For each test we need to initialize the self.at and the self.at_user
        members.
        """
        self.setUp_user_realms()
        Token(self.my_serial, tokentype="hotp", userid="1004",
              resolver="resolver1", realm="realm1").save()
        Token(self.foreign_serial, tokentype="hotp").save()


    def tearDown(self):
        remove_token(self.my_serial)
        remove_token(self.foreign_serial)

    def test_00_authenticate_admin_fail(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "admin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)


    def test_01_authenticate_admin(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_admin = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "admin", result)

    def test_01_authenticate_admin_from_realm(self):
        # Define an admin realm!
        (added, failed) = set_realm("adminrealm",
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        # "selfservice" is a user in adminrealm. He should be able to
        # authenticate
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username":
                                                     "selfservice@adminrealm",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_admin = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "admin", result)

        delete_realm("adminrealm")

    def test_02_user_allowed_to_get_config(self):
        self.authenticate_selfservice_user()
        # The user is allowed to get the system config
        with self.app.test_request_context('/system/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

    def test_02_user_not_allowed(self):
        self.authenticate_selfservice_user()
        # The user is not allowed to write system information
        with self.app.test_request_context('/system/setConfig',
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/system/setDefault',
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/system/documentation',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/system/hsm',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/system/hsm',
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/realm/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # The user is allowed to get his own information
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            value = response.get("result").get("value")
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0].get("username"), "selfservice")

        # If he wants to see other information, he still sees his own
        with self.app.test_request_context('/user/?username=*',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            value = response.get("result").get("value")
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0].get("username"), "selfservice")

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

    def test_03_user_enroll_token(self):
        self.authenticate_selfservice_user()
        with self.app.test_request_context('/token/init',
                                           method='POST', data={"genkey": 1},
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))
            serial = response.get("detail").get("serial")
            self.assertTrue("OATH" in serial, serial)

        # Check, who is the owner of the new token!
        tokenobject = get_tokens(serial=serial)[0]
        self.assertTrue(tokenobject.token.user_id == "1004",
                        tokenobject.token.user_id)
        self.assertTrue(tokenobject.token.resolver == "resolver1",
                        tokenobject.token.resolver == "resolver1")

        # user can delete his own token
        with self.app.test_request_context('/token/{0!s}'.format(serial),
                                           method='DELETE',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))
        # check if there is no token left
        tokenobject_list = get_tokens(serial=serial)
        self.assertTrue(len(tokenobject_list) == 0, len(tokenobject_list))

    def test_04_user_can_not_delete_another_token(self):
        self.authenticate_selfservice_user()
        assign_token(self.foreign_serial, User("cornelius", self.realm1))
        with self.app.test_request_context('/token/{0!s}'.format(self.foreign_serial),
                                           method='DELETE',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertFalse(response.get("result").get("value"),
                            response.get("result"))
        # check if the token still exists!
        tokenobject_list = get_tokens(serial=self.foreign_serial)
        self.assertTrue(len(tokenobject_list) == 1, len(tokenobject_list))

    def test_04_user_can_not_disable_another_token(self):
        self.authenticate_selfservice_user()
        assign_token(self.foreign_serial, User("cornelius", self.realm1))
        with self.app.test_request_context('/token/disable/{0!s}'.format(
                                                   self.foreign_serial),
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertFalse(response.get("result").get("value"),
                             response.get("result"))
        # check if the token still is enabled!
        tokenobject_list = get_tokens(serial=self.foreign_serial)
        self.assertTrue(len(tokenobject_list) == 1, len(tokenobject_list))
        self.assertTrue(tokenobject_list[0].token.active)

    def test_04_user_can_not_lost_another_token(self):
        self.authenticate_selfservice_user()
        assign_token(self.foreign_serial, User("cornelius", self.realm1))
        with self.app.test_request_context('/token/lost/{0!s}'.format(
                                                   self.foreign_serial),
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)


    def test_05_user_can_disable_token(self):
        self.authenticate_selfservice_user()
        # User can not disable a token, that does not belong to him.
        with self.app.test_request_context('/token/disable/{0!s}'.format(
                                                   self.foreign_serial),
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertFalse(response.get("result").get("value"),
                            response.get("result"))
        tokenobject = get_tokens(serial=self.foreign_serial)[0]
        self.assertTrue(tokenobject.token.active, tokenobject.token.active)

        # User disables his token
        with self.app.test_request_context('/token/disable/{0!s}'.format(self.my_serial),
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))

        tokenobject = get_tokens(serial=self.my_serial)[0]
        self.assertFalse(tokenobject.token.active, tokenobject.token.active)

        # User enables his token
        with self.app.test_request_context('/token/enable/{0!s}'.format(self.my_serial),
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))

        tokenobject = get_tokens(serial=self.my_serial)[0]
        self.assertTrue(tokenobject.token.active, tokenobject.token.active)

        # User can not enable foreign token
        enable_token(self.foreign_serial, enable=False)
        # Is token disabled?
        tokenobject = get_tokens(serial=self.foreign_serial)[0]
        self.assertFalse(tokenobject.token.active, tokenobject.token.active)
        with self.app.test_request_context('/token/enable/{0!s}'.format(
                                                   self.foreign_serial),
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value") == 0,
                            response.get("result"))

        # token still inactive
        tokenobject = get_tokens(serial=self.foreign_serial)[0]
        self.assertFalse(tokenobject.token.active, tokenobject.token.active)

    def test_06_user_can_assign_token(self):
        self.authenticate_selfservice_user()
        # The foreign token ist not assigned yet, so he can assign it
        with self.app.test_request_context('/token/assign',
                                           data={"serial": self.foreign_serial},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))

        tokenobject = get_tokens(serial=self.foreign_serial)[0]
        self.assertTrue(tokenobject.token.user_id == "1004",
                         tokenobject.token.user_id)

        # User can unassign token
        with self.app.test_request_context('/token/unassign',
                                           data={"serial": self.foreign_serial},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))

        tokenobject = get_tokens(serial=self.foreign_serial)[0]
        self.assertTrue(tokenobject.token.user_id == "",
                         tokenobject.token.user_id)


        # User can not unassign token, which does not belong to him
        with self.app.test_request_context('/token/unassign',
                                           data={"serial": self.foreign_serial},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_07_user_can_reset_failcount(self):
        self.authenticate_selfservice_user()
        mT = get_tokens(serial=self.my_serial)[0]
        fT = get_tokens(serial=self.foreign_serial)[0]

        fT.token.failcount = 12
        fT.save()

        mT.token.failcount = 12
        mT.save()

        # can not reset foreign token
        with self.app.test_request_context('/token/reset',
                                           data={"serial": self.foreign_serial},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value") == 0,
                            response.get("result"))
        # failcounter still on
        self.assertTrue(fT.token.failcount == 12, fT.token.failcount)

        # can reset own token
        with self.app.test_request_context('/token/reset',
                                           data={"serial": self.my_serial},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))
        # failcounter still on
        self.assertTrue(mT.token.failcount == 0, mT.token.failcount)

    def test_08_user_can_set_pin(self):
        self.authenticate_selfservice_user()
        # can not set pin of foreign token
        with self.app.test_request_context('/token/setpin',
                                           data={"serial":
                                                     self.foreign_serial,
                                                 "otppin": "1234"},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value") == 0,
                            response.get("result"))

        # can set pin for own token
        with self.app.test_request_context('/token/setpin',
                                           data={"serial": self.my_serial,
                                                 "otppin": "1234"},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))


    def test_31_user_is_not_allowed_for_some_api_calls(self):
        self.authenticate_selfservice_user()
        serial = "serial0001"
        tok = Token(serial)
        tok.save()

        # Can not set things
        with self.app.test_request_context('/token/set',
                                            method="POST",
                                            data={"serial": serial,
                                                  "pin": "test"},
                                            headers={'Authorization':
                                                         self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # Can not set token realm
        with self.app.test_request_context('/token/realm/{0!s}'.format(serial),
                                            method="POST",
                                            data={"realms": "realm1"},
                                            headers={'Authorization':
                                                         self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # Can not call get_serial token
        with self.app.test_request_context('/token/getserial/12345',
                                           method="GET",
                                           headers={'Authorization':
                                                         self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # Can not copy pin
        with self.app.test_request_context('/token/copypin',
                                            method="POST",
                                            headers={'Authorization':
                                                         self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # Can not copy user
        with self.app.test_request_context('/token/copyuser',
                                            method="POST",
                                            headers={'Authorization':
                                                         self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # Can not load tokens
        with self.app.test_request_context('/token/load/test.xml',
                                            method="POST",
                                            headers={'Authorization':
                                                         self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

    def test_41_webui_settings(self):
        set_policy(name="webui1", scope=SCOPE.WEBUI, action="{0!s}={1!s}".format(
            ACTION.TOKENPAGESIZE, 20))
        set_policy(name="webui2", scope=SCOPE.WEBUI, action="{0!s}={1!s}".format(
            ACTION.USERPAGESIZE, 20))
        set_policy(name="webui3", scope=SCOPE.WEBUI, action="{0!s}={1!s}".format(
            ACTION.LOGOUTTIME, 200))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username":
                                                     "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # Test logout time
            self.assertEqual(result.get("value").get("logout_time"), 200)
            self.assertEqual(result.get("value").get("token_page_size"), 20)
            self.assertEqual(result.get("value").get("user_page_size"), 20)
            self.assertEqual(result.get("value").get("policy_template_url"),
                             DEFAULT_POLICY_TEMPLATE_URL)
