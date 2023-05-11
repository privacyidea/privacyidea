# coding: utf-8
"""
This file tests the authentication of admin users and normal user (
selfservice) on the REST API.

implementation is contained in api/auth.py, api/token.py api/audit.py
"""
import datetime
import json

from . import ldap3mock
from .test_api_validate import LDAPDirectory
from .base import MyApiTestCase
from privacyidea.lib.token import (get_tokens, remove_token, enable_token,
                                   assign_token, init_token)
from privacyidea.lib.user import User
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT
from privacyidea.lib.resolver import save_resolver
from privacyidea.models import Token
from privacyidea.lib.realm import (set_realm, delete_realm, set_default_realm)
from privacyidea.api.lib.postpolicy import DEFAULT_POLICY_TEMPLATE_URL
from privacyidea.lib.policy import (ACTION, SCOPE, set_policy, delete_policy,
                                    LOGINMODE, ACTIONVALUE)


PWFILE = "tests/testdata/passwords"


class APIAuthTestCase(MyApiTestCase):
    """
    This tests some side functionalities of the /auth API.
    """

    def test_00_missing_username(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

    def test_00_missing_password(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "admin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

    def test_01_get_rights(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue("token" in result.get("value"))
            self.assertTrue("username" in result.get("value"))
            self.assertEqual(result.get("value").get("role"), "admin")
            self.assertTrue(result.get("status"), res.data)

        # Check if the /auth request writes the policyname "remote" to the audit entry
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            auditentry = res.json.get("result").get("value").get("auditdata")[0]
            self.assertTrue("remote" in auditentry.get("policies"))

        self.setUp_user_realms()
        # User "cornelius" from the default realm as normale user
        with self.app.test_request_context('/auth', method='POST',
                                           data={"username": "cornelius"},
                                           environ_base={"REMOTE_USER":
                                                             "cornelius"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            result = res.json.get("result")
            # In the result list should only be users from reso3.
            for user in result.get("value"):
                self.assertEqual(user.get("resolver"), self.resolvername3)

        delete_policy("realmadmin")


class APIAuthChallengeResponse(MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        # New token for the user "selfservice"
        Token("hotp1", "hotp", otpkey=self.otpkey, userid=1004, resolver=self.resolvername1,
              realm=self.realm1).save()
        # Define HOTP token to be challenge response
        set_policy(name="pol_cr", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        set_policy(name="webuilog", scope=SCOPE.WEBUI, action="{0!s}=privacyIDEA".format(ACTION.LOGINMODE))
        from privacyidea.lib.token import set_pin
        set_pin("hotp1", "pin")

    def tearDown(self):
        remove_token('hotp1')
        delete_policy('pol_cr')
        delete_policy('webuilog')

    def test_01_challenge_response_at_webui(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice",
                                                 "password": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            detail = data.get("detail")
            self.assertTrue("enter otp" in detail.get("message"), detail.get("message"))
            transaction_id = detail.get("transaction_id")

        # Now we try to login with the OTP value
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice",
                                                 "password": self.valid_otp_values[0],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual(data.get("result").get("value").get("username"), "selfservice")

    def test_02_auth_chal_resp_multi_token(self):
        # create another token
        Token("hotp2", "hotp", otpkey=self.otpkey, userid=1004,
              resolver=self.resolvername1, realm=self.realm1).save()
        set_policy(name="pol_otppin", scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, ACTIONVALUE.USERSTORE))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice",
                                                 "password": 'test'}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get('detail')
            self.assertTrue('multi_challenge' in result, result)
            self.assertEqual({'hotp1', 'hotp2'}, set([x['serial'] for x in result.get('multi_challenge')]))

        # check if we have both serials in the audit log
        ae = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertTrue({"hotp1", "hotp2"}.issubset(set(ae.get('serial').split(','))), ae)

        delete_policy('pol_otppin')
        remove_token('hotp2')


class APISelfserviceTestCase(MyApiTestCase):

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
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            response = res.json
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
            response = res.json
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
            response = res.json
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))
            serial = response.get("detail").get("serial")
            self.assertTrue("OATH" in serial, serial)

        # Check, who is the owner of the new token!
        tokenobject = get_tokens(serial=serial)[0]
        self.assertEqual(tokenobject.token.first_owner.user_id, "1004")
        self.assertEqual(tokenobject.token.first_owner.resolver, "resolver1")

        # user can delete his own token
        with self.app.test_request_context('/token/{0!s}'.format(serial),
                                           method='DELETE',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = res.json
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
            self.assertEqual(res.status_code, 404)
            response = res.json
            self.assertFalse(response["result"]["status"])
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
            self.assertEqual(res.status_code, 404)
            response = res.json
            self.assertFalse(response["result"]["status"])
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
            self.assertEqual(res.status_code, 404)
            response = res.json
            self.assertFalse(response["result"]["status"])

        tokenobject = get_tokens(serial=self.foreign_serial)[0]
        self.assertTrue(tokenobject.token.active, tokenobject.token.active)

        # User disables his token
        with self.app.test_request_context('/token/disable/{0!s}'.format(self.my_serial),
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = res.json
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
            response = res.json
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
            self.assertEqual(res.status_code, 404)
            response = res.json
            self.assertFalse(response["result"]["status"])

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
            response = res.json
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))

        tokenobject = get_tokens(serial=self.foreign_serial)[0]
        self.assertTrue(tokenobject.token.first_owner.user_id == "1004",
                         tokenobject.token.first_owner.user_id)

        # User can unassign token
        with self.app.test_request_context('/token/unassign',
                                           data={"serial": self.foreign_serial},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = res.json
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))

        tokenobject = get_tokens(serial=self.foreign_serial)[0]
        self.assertEqual(tokenobject.token.first_owner, None)


        # User can not unassign token, which does not belong to him
        with self.app.test_request_context('/token/unassign',
                                           data={"serial": self.foreign_serial},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)

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
            self.assertEqual(res.status_code, 404)
            response = res.json
            self.assertFalse(response["result"]["status"])

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
            response = res.json
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
            self.assertEqual(res.status_code, 404)
            response = res.json
            self.assertFalse(response["result"]["status"])

        # can set pin for own token
        with self.app.test_request_context('/token/setpin',
                                           data={"serial": self.my_serial,
                                                 "otppin": "1234"},
                                           method='POST',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = res.json
            self.assertTrue(response.get("result").get("value"),
                            response.get("result"))

    def test_09_authz_user_detail(self):
        # Test behavior of ADDUSERINRESPONSE and ADDRESOLVERINRESPONSE policy action for /auth endpoint
        # Normally, no userinfo and realm/resolver are found in the response
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)
            # check that this is a user
            role = result.get("value").get("role")
            self.assertEqual(role, "user", result)
            self.assertEqual(result.get("value").get("realm"), "realm1", content)
            self.assertNotIn("detail", content, content)

        set_policy(name="pol_add_info",
                   scope=SCOPE.AUTHZ,
                   action=[ACTION.ADDUSERINRESPONSE, ACTION.ADDRESOLVERINRESPONSE],
                   realm="realm1")

        # Userinfo + realm/resolver are added to the response
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)
            # check that this is a user
            role = result.get("value").get("role")
            self.assertEqual(role, "user", result)
            self.assertEqual(result.get("value").get("realm"), "realm1", content)
            self.assertEqual(content["detail"]["user-realm"], "realm1", content)
            self.assertEqual(content["detail"]["user-resolver"], "resolver1", content)
            self.assertIn("user", content["detail"], content)
            self.assertEqual(content["detail"]["user"]["userid"], "1004", content)

        # ... but not for internal admins
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)
            self.assertNotIn("detail", content, content)

        delete_policy("pol_add_info")

    def test_10_authz_lastauth(self):
        # Test LASTAUTH policy action for /auth endpoint
        # This only works if we authenticate against privacyIDEA
        set_policy("pol_lastauth",
                   scope=SCOPE.AUTHZ,
                   action={
                       ACTION.LASTAUTH: "10m",
                   })
        set_policy("pol_loginmode",
                   scope=SCOPE.WEBUI,
                   action={
                       ACTION.LOGINMODE: LOGINMODE.PRIVACYIDEA,
                   })
        selfservice_token = init_token({"type": "spass", "pin": "somepin"},
                                       user=User("selfservice", "realm1"))
        # Last authentication was too long ago.
        selfservice_token.add_tokeninfo(ACTION.LASTAUTH, "2016-10-10 10:10:10.000")
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            content = res.json
            result = content.get("result")
            self.assertFalse(result.get("status"), content)
            self.assertIn("long ago", content["detail"]["message"], content)

        selfservice_token.add_tokeninfo(ACTION.LASTAUTH, datetime.datetime.now().strftime(AUTH_DATE_FORMAT))

        # But now it works
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        # Authentication still works for internal admins
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        remove_token(selfservice_token.token.serial)
        delete_policy("pol_lastauth")
        delete_policy("pol_loginmode")

    def test_11_authz_tokentype(self):
        # Check TOKENTYPE policy action for /auth endpoint
        spass_token = init_token({"type": "spass", "pin": "somepin"},
                                       user=User("selfservice", "realm1"))
        set_policy("pol_loginmode",
                   scope=SCOPE.WEBUI,
                   action={
                       ACTION.LOGINMODE: LOGINMODE.PRIVACYIDEA,
                   })
        set_policy("pol_tokentype",
                   scope=SCOPE.AUTHZ,
                   action={
                       ACTION.TOKENTYPE: "hotp",
                   })

        # Cannot authenticate with SPASS token
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            content = res.json
            result = content.get("result")
            self.assertFalse(result.get("status"), content)
            self.assertIn("Tokentype not allowed", result["error"]["message"], content)

        # Allow HOTP+SPASS
        set_policy("pol_tokentype",
                   scope=SCOPE.AUTHZ,
                   action={
                       ACTION.TOKENTYPE: "hotp spass",
                   })
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        # Authentication still works for internal admins
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        remove_token(spass_token.token.serial)
        delete_policy("pol_tokentype")
        delete_policy("pol_loginmode")

    def test_12_authz_tokeninfo(self):
        # Check TOKENINFO policy action for /auth endpoint
        spass_token = init_token({"type": "spass", "pin": "somepin"},
                                 user=User("selfservice", "realm1"))
        set_policy("pol_loginmode",
                   scope=SCOPE.WEBUI,
                   action={
                       ACTION.LOGINMODE: LOGINMODE.PRIVACYIDEA,
                   })
        set_policy("pol_tokeninfo",
                   scope=SCOPE.AUTHZ,
                   action={
                       ACTION.TOKENINFO: "secure/yes/",
                   })

        # Cannot authenticate with token that does not have a "secure" tokeninfo
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            content = res.json
            result = content.get("result")
            self.assertFalse(result.get("status"), content)
            self.assertIn("Tokeninfo field", result["error"]["message"], content)

        # Add the tokeninfo, we can authenticate
        spass_token.add_tokeninfo("secure", "yes")
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        # Authentication still works for internal admins
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        remove_token(spass_token.token.serial)
        delete_policy("pol_tokeninfo")
        delete_policy("pol_loginmode")

    def test_13_authz_tokenserial(self):
        # Check SERIAL policy action for /auth endpoint
        spass_token = init_token({"type": "spass", "pin": "somepin"},
                                 user=User("selfservice", "realm1"))
        set_policy("pol_loginmode",
                   scope=SCOPE.WEBUI,
                   action={
                       ACTION.LOGINMODE: LOGINMODE.PRIVACYIDEA,
                   })
        set_policy("pol_serial",
                   scope=SCOPE.AUTHZ,
                   action={
                       ACTION.SERIAL: "GOOD.*"
                   })

        # Cannot authenticate with token that does not have a "GOOD..." serial
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            content = res.json
            result = content.get("result")
            self.assertFalse(result.get("status"), content)
            self.assertIn("Serial is not allowed for authentication",
                          result["error"]["message"], content)

        # Add a token with a suitable serial
        good_token = init_token({"type": "spass", "pin": "anotherpin", "serial": "GOOD1234"},
                                 user=User("selfservice", "realm1"))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "anotherpin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        # Authentication still works for internal admins
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            content = res.json
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        remove_token(spass_token.token.serial)
        remove_token(good_token.token.serial)
        delete_policy("pol_serial")
        delete_policy("pol_loginmode")

    def test_13_authz_no_detail_on_success(self):
        # Check NODETAILSUCCESS policy action for /auth endpoint
        spass_token = init_token({"type": "spass", "pin": "somepin"},
                                 user=User("selfservice", "realm1"))
        set_policy("pol_loginmode",
                   scope=SCOPE.WEBUI,
                   action={
                       ACTION.LOGINMODE: LOGINMODE.PRIVACYIDEA,
                   })

        # Without the policy, there are details in the response
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            content = res.json
            self.assertIn("detail", content, content)
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        # With the policy, there aren't
        set_policy("pol_detail",
                   scope=SCOPE.AUTHZ,
                   action=ACTION.NODETAILSUCCESS)
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "somepin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            content = res.json
            self.assertNotIn("detail", content, content)
            result = content.get("result")
            self.assertTrue(result.get("status"), content)

        remove_token(spass_token.token.serial)
        delete_policy("pol_detail")
        delete_policy("pol_loginmode")

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
        set_policy(name="webui4", scope=SCOPE.WEBUI, action="{0!s}={1!s}".format(
            ACTION.AUDITPAGESIZE, 20))
        set_policy(name="webui5", scope=SCOPE.WEBUI, action=ACTION.DELETION_CONFIRMATION)
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # Test logout time
            self.assertEqual(result.get("value").get("logout_time"), 200)
            self.assertEqual(result.get("value").get("audit_page_size"), 20)
            self.assertEqual(result.get("value").get("token_page_size"), 20)
            self.assertEqual(result.get("value").get("user_page_size"), 20)
            self.assertEqual(result.get("value").get("policy_template_url"),
                             DEFAULT_POLICY_TEMPLATE_URL)
            # check if we have the same values in the data attribute
            result2 = json.loads(res.data.decode('utf8')).get('result')
            self.assertTrue(result2.get("status"), res.data)
            # Test logout time
            self.assertEqual(result2.get("value").get("logout_time"), 200)
            # check if value is True if deletion_confirmation is set
            self.assertEqual(result.get("value").get("deletion_confirmation"), True)

        delete_policy("webui5")

    def test_42_auth_timelimit_maxfail(self):
        self.setUp_user_realm2()
        # check that AUTHMAXFAIL also takes effect for /auth with loginmode=privacyIDEA
        user = User("timelimituser", realm=self.realm2)
        pin = "spass"
        # create a token
        token = init_token({"type": "spass", "pin": pin}, user=user)

        set_policy(name="pol_time1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=2/20s".format(ACTION.AUTHMAXFAIL))
        set_policy(name="pol_loginmode",
                   scope=SCOPE.WEBUI,
                   action="{}={}".format(ACTION.LOGINMODE, LOGINMODE.PRIVACYIDEA))
        for _ in range(2):
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "timelimituser@" + self.realm2,
                                                     "password": "wrong"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 401)

        # We now cannot authenticate even with the correct PIN
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "timelimituser@" + self.realm2,
                                                 "password": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 failed authentications per 0:00:20",
                             details)

        # and even /validate/check does not work
        # (since it counts /auth *and* /validate/check )
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser@" + self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertFalse(result["value"], result)

        delete_policy("pol_time1")
        delete_policy("pol_loginmode")

    def test_43_auth_timelimit_maxsuccess(self):
        self.setUp_user_realm2()
        # check that AUTHMAXSUCCESS also takes effect for /auth with loginmode=privacyIDEA
        user = User("timelimituser", realm=self.realm2)
        pin = "spass"
        # create a token
        token = init_token({"type": "spass", "pin": pin}, user=user)

        set_policy(name="pol_time1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=2/20s".format(ACTION.AUTHMAXSUCCESS))
        set_policy(name="pol_loginmode",
                   scope=SCOPE.WEBUI,
                   action="{}={}".format(ACTION.LOGINMODE, LOGINMODE.PRIVACYIDEA))
        for _ in range(2):
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "timelimituser@" + self.realm2,
                                                     "password": pin}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)

        # We now cannot authenticate even with the correct PIN
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "timelimituser@" + self.realm2,
                                                 "password": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 successful authentications per 0:00:20",
                             details)

        # ... and not with the wrong PIN
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "timelimituser@" + self.realm2,
                                                 "password": "wrong"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)

        # /validate/check does not work, since the two allowed authentications
        # are already used up for the /auth endpoint
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser@" + self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertFalse(result["value"], result)

        delete_policy("pol_time1")
        delete_policy("pol_loginmode")


class PolicyConditionsTestCase(MyApiTestCase):
    @ldap3mock.activate
    def test_00_set_ldap_realm(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = {'LDAPURI': 'ldap://localhost',
                  'LDAPBASE': 'o=test',
                  'BINDDN': 'cn=manager,ou=example,o=test',
                  'BINDPW': 'ldaptest',
                  'LOGINNAMEATTRIBUTE': 'cn',
                  'LDAPSEARCHFILTER': '(cn=*)',
                  'MULTIVALUEATTRIBUTES': '["groups"]',
                  'USERINFO': '{ "username": "cn",'
                                  '"phone" : "telephoneNumber", '
                                  '"mobile" : "mobile"'
                                  ', "email" : "mail", '
                                  '"surname" : "sn", '
                                  '"groups": "memberOf", '
                                  '"givenname" : "givenName" }',
                  'UIDTYPE': 'DN',
                  "resolver": "ldapgroups",
                  "type": "ldapresolver"}

        r = save_resolver(params)
        self.assertTrue(r > 0)

        r = set_realm("ldaprealm", resolvers=["ldapgroups"])
        set_default_realm("ldaprealm")
        self.assertEqual(r, (["ldapgroups"], []))

        # find a user, check the groups
        alice = User("alice", "ldaprealm")
        self.assertEqual(alice.info["groups"], ["cn=admins,o=test", "cn=users,o=test"])

    @ldap3mock.activate
    def test_01_policies_with_userinfo_conditions(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # create some webui policies with conditions: Depending on their LDAP group membership,
        # users cannot log in at all, are authenticated against privacyIDEA, or against the userstore.

        # disabled policy: by default, login is disabled
        with self.app.test_request_context('/policy/disabled',
                                           json={'action': "{}={}".format(ACTION.LOGINMODE, LOGINMODE.DISABLE),
                                                 'scope': SCOPE.WEBUI,
                                                 'realm': '',
                                                 'priority': 2,
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # userstore policy: for admins, require the userstore password
        with self.app.test_request_context('/policy/userstore',
                                           json={'action': "{}={}".format(ACTION.LOGINMODE, LOGINMODE.USERSTORE),
                                                 'scope': SCOPE.WEBUI,
                                                 'realm': '',
                                                 'priority': 1,
                                                 'conditions': [
                                                     ["userinfo", "groups", "contains", "cn=admins,o=test", True],
                                                 ],
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # privacyidea policy: for helpdesk users, require the token PIN
        with self.app.test_request_context('/policy/privacyidea',
                                           json={'action': "{}={}".format(ACTION.LOGINMODE, LOGINMODE.PRIVACYIDEA),
                                                 'scope': SCOPE.WEBUI,
                                                 'realm': '',
                                                 'priority': 1,
                                                 'conditions': [
                                                     ["userinfo", "groups", "contains", "cn=helpdesk,o=test", True],
                                                 ],
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # enroll 4 SPASS tokens
        users_pins = [("alice", "pin1"),
                      ("bob", "pin2"),
                      ("manager", "pin3"),
                      ("frank", "pin4")]
        for username, pin in users_pins:
            init_token({"type": "spass", "pin": pin}, user=User(username, "ldaprealm"))

        # check our policies:
        # frank is not allowed to log in, because he is neither admin nor helpdesk
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "frank",
                                                 "password": "ldaptest"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertEqual(result["error"]["message"], "The login for this user is disabled.")

        # alice is allowed to log in with the userstore password, because he is in the admins group
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "alice",
                                                 "password": "alicepw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # ... but the OTP PIN will not work
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "alice",
                                                 "password": "pin1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertIn("Wrong credentials", result["error"]["message"])

        # manager can log in with the OTP PIN, because he is in the helpdesk group
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "manager",
                                                 "password": "pin3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # ... but the userstore password will not work
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "manager",
                                                 "password": "ldaptest"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertIn("Wrong credentials", result["error"]["message"])

        # if we now disable the condition on userstore and privacyidea, we get a conflicting policy error
        with self.app.test_request_context('/policy/privacyidea',
                                           json={'scope': SCOPE.WEBUI,
                                                 'action': "{}={}".format(ACTION.LOGINMODE, LOGINMODE.PRIVACYIDEA),
                                                 'realm': '',
                                                 'active': True,
                                                 'conditions': [
                                                     ["userinfo", "groups", "contains", "cn=helpdesk,o=test", False],
                                                 ]},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        with self.app.test_request_context('/policy/userstore',
                                           json={'scope': SCOPE.WEBUI,
                                                 'action': "{}={}".format(ACTION.LOGINMODE, LOGINMODE.USERSTORE),
                                                 'realm': '',
                                                 'active': True,
                                                 'conditions': [
                                                     ["userinfo", "groups", "contains", "cn=admins,o=test", False],
                                                 ]},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # policy error because of conflicting actions
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "manager",
                                                 "password": "pin3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json.get("result")
            self.assertIn("conflicting actions", result["error"]["message"])

        # delete all policies
        delete_policy("disabled")
        delete_policy("userstore")
        delete_policy("privacyidea")

    @ldap3mock.activate
    def test_02_enroll_rights(self):
        # Test a scenario that users are allowed to enroll different tokens according to their LDAP groups
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # by default, users may only enroll HOTP tokens
        with self.app.test_request_context('/policy/default_enroll',
                                           json={'action': "enrollHOTP",
                                                 'scope': SCOPE.USER,
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # but helpdesk users can additionally enroll TOTP tokens
        with self.app.test_request_context('/policy/helpdesk_enroll',
                                           json={'action': "enrollTOTP",
                                                 'scope': SCOPE.USER,
                                                 'realm': '',
                                                 'active': True,
                                                 'conditions': [
                                                     ["userinfo", "groups", "contains", "cn=helpdesk,o=test", True],
                                                 ]},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # check that the endpoint / doesn't throw an error if a user policy with
        # userinfo attribute conditions is defined
        with self.app.test_request_context('/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # get an auth token for bob, who is an ordinary user
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "bob",
                                                 "password": "bobpwééé"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            bob_token = result['value']['token']
            # check the rights and menus for bob
            self.assertEqual(result['value']['role'], 'user')
            # bob can only enroll HOTP
            self.assertEqual(result['value']['rights'], ['enrollHOTP'])
            self.assertEqual(result['value']['menus'], ['tokens'])

        # get an auth token for manager, who is a helpdesk user
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "manager",
                                                 "password": "ldaptest"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            manager_token = result['value']['token']
            # check the rights and menus for manager
            self.assertEqual(result['value']['role'], 'user')
            # manager may enroll HOTP and TOTP
            self.assertEqual(set(result['value']['rights']), {'enrollHOTP', 'enrollTOTP'})
            self.assertEqual(result['value']['menus'], ['tokens'])

        # check the rights of bob
        with self.app.test_request_context('/auth/rights',
                                           method='GET',
                                           headers={'Authorization': bob_token}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            # only HOTP tokens
            self.assertEqual(set(result['value'].keys()), {'hotp'})

        # We set a new policy condition for users (bob), to be allowed to enroll TOTP
        # tokens only in special cases. This condition will not match for certain tokens.
        with self.app.test_request_context('/policy/totp_enroll',
                                           json={'action': "enrollTOTP",
                                                 'scope': SCOPE.USER,
                                                 'realm': '',
                                                 'active': True,
                                                 'conditions': [
                                                     ["userinfo", "username", "equals", "bob", True],
                                                     ["token", "count", "equals", "1", True],
                                                 ]
                                                 },
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # check the rights of bob. The TOTP enroll right will basically be there
        with self.app.test_request_context('/auth/rights',
                                           method='GET',
                                           headers={'Authorization': bob_token}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            # HOTP and TOTP tokens
            self.assertIn('hotp', set(result['value'].keys()))
            self.assertIn('totp', set(result['value'].keys()))

        # check the rights of manager
        with self.app.test_request_context('/auth/rights',
                                           method='GET',
                                           headers={'Authorization': manager_token}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            # HOTP+TOTP tokens
            self.assertEqual(set(result['value'].keys()), {'hotp', 'totp'})

        # helper function for trying to enroll tokens, returns a tuple (status code, result)
        def _try_enroll(auth_token, token_type):
            with self.app.test_request_context('/token/init',
                                               method='POST',
                                               data={'type': token_type, 'genkey': '1'},
                                               headers={'Authorization': auth_token}):
                res = self.app.full_dispatch_request()
                return res.status_code, res.json.get("result")

        # bob may enroll HOTP ...
        status_code, result = _try_enroll(bob_token, 'hotp')
        self.assertEqual(status_code, 200)
        self.assertEqual(result, {"status": True, "value": True})
        # ... but not TOTP, since the extended condition does not match
        status_code, result = _try_enroll(bob_token, 'totp')
        self.assertEqual(status_code, 403)
        self.assertFalse(result['status'])
        self.assertIn("has conditions on tokens, but a token object is not available", result['error']['message'])
        # ... and certainly not SPASS
        status_code, result = _try_enroll(bob_token, 'spass')
        self.assertEqual(status_code, 403)
        self.assertFalse(result['status'])
        self.assertIn("not allowed to enroll this token type", result['error']['message'])

        # manager may enroll HOTP ...
        status_code, result = _try_enroll(manager_token, 'hotp')
        self.assertEqual(status_code, 200)
        self.assertEqual(result, {"status": True, "value": True})
        # ... and TOTP ...
        status_code, result = _try_enroll(manager_token, 'totp')
        self.assertEqual(status_code, 200)
        self.assertEqual(result, {"status": True, "value": True})
        # ... but not SPASS
        status_code, result = _try_enroll(manager_token, 'spass')
        self.assertEqual(status_code, 403)
        self.assertFalse(result['status'])
        self.assertIn("not allowed to enroll this token type", result['error']['message'])

        delete_policy("default_enroll")
        delete_policy("helpdesk_enroll")