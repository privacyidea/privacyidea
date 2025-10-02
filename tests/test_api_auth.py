""" Test for the '/auth' API-endpoint """
import datetime
import json
import logging

import mock
from dateutil.tz import tzlocal
from testfixtures import log_capture, LogCapture

from privacyidea.api.lib.utils import verify_auth_token
from privacyidea.config import TestingConfig
from privacyidea.lib.auth import create_db_admin
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import set_privacyidea_config, SYSCONF
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.event import set_event, delete_event
from privacyidea.lib.eventhandler.base import CONDITION
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import (set_policy, SCOPE, REMOTE_USER,
                                    delete_policy)
from privacyidea.lib.realm import (set_realm, set_default_realm, delete_realm,
                                   get_default_realm)
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.token import get_tokens, remove_token, init_token, get_one_token
from privacyidea.lib.tokenclass import FAILCOUNTER_EXCEEDED, DATE_FORMAT, FAILCOUNTER_CLEAR_TIMEOUT
from privacyidea.lib.user import User
from privacyidea.lib.utils import to_unicode, AUTH_RESPONSE
from privacyidea.models import Realm
from . import ldap3mock
from .base import MyApiTestCase, OverrideConfigTestCase

PWFILE = "tests/testdata/passwd-duplicate-name"


class AuthApiTestCase(MyApiTestCase):
    def test_01_auth_with_split(self):
        # By default, splitAtSign should be true
        set_privacyidea_config(SYSCONF.SPLITATSIGN, True)
        self.setUp_user_realms()
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            self.assertEqual('realm1', result['value']['realm'], result)
        aentry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(aentry['action'], 'POST /auth', aentry)
        self.assertEqual(aentry['success'], 1, aentry)

        # test failed auth
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "false"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Wrong credentials',
                             result['error']['message'], result)
        aentry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(aentry['action'], 'POST /auth', aentry)
        self.assertEqual(aentry['success'], 0, aentry)

        # test with realm added to user
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            self.assertEqual('realm1', result['value']['realm'], result)

        # test with realm added to user and unknown realm param
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@realm1",
                                                 "realm": "unknown",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Unknown realm: unknown.',
                             result['error']['message'], result)

        # test with realm parameter
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": "realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            self.assertEqual('realm1', result['value']['realm'], result)

        # test with broken realm parameter
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": "unknown",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Unknown realm: unknown.',
                             result['error']['message'], result)

        # test with empty realm parameter
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": "",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            # realm1 should be the default realm
            self.assertEqual('realm1', result['value']['realm'], result)

        # TODO: Add test with empty realm parameter and user@realm not in default realm

        # test with realm parameter and wrong realm added to user
        with mock.patch("logging.Logger.error") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "cornelius@unknown",
                                                     "realm": "realm1",
                                                     "password": "test"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
                result = res.json.get("result")
                self.assertFalse(result.get("status"), result)
            expected = "The user User(login='cornelius@unknown', " \
                       "realm='realm1', resolver='') exists in NO resolver."
            mock_log.assert_called_once_with(expected)

        # test with wrong realm parameter and wrong realm added to user
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@unknown",
                                                 "realm": "anotherunknown",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Unknown realm: anotherunknown.',
                             result['error']['message'], result)

        # Now we take it up one notch and add another resolver
        self.setUp_user_realm3()
        # The selfservice user does not exist in realm3
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm3",
                                                 "realm": "realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            self.assertEqual('realm1', result['value']['realm'], result)

        # and the other way round
        with mock.patch("logging.Logger.error") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "selfservice@realm1",
                                                     "realm": "realm3",
                                                     "password": "test"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
                result = res.json.get("result")
                self.assertFalse(result.get("status"), result)
                self.assertEqual(4031, result['error']['code'], result)
                self.assertEqual('Authentication failure. Wrong credentials',
                                 result['error']['message'], result)
            # the realm will be split from the login name
            expected = "The user User(login='selfservice', " \
                       "realm='realm3', resolver='') exists in NO resolver."
            mock_log.assert_called_once_with(expected)

    # And now we do all of the above without the splitAtSign setting
    def test_02_auth_without_split(self):
        set_privacyidea_config(SYSCONF.SPLITATSIGN, False)
        self.setUp_user_realms()
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            self.assertEqual('realm1', result['value']['realm'], result)

        # test failed auth wrong password
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "false"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Wrong credentials',
                             result['error']['message'], result)

        # test failed auth no password
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Wrong credentials',
                             result['error']['message'], result)

        # test with realm added to user. This fails since we do not split
        with mock.patch("logging.Logger.error") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "cornelius@realm1",
                                                     "password": "test"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
                result = res.json.get("result")
                self.assertFalse(result.get("status"), result)
                self.assertEqual(4031, result['error']['code'], result)
                self.assertEqual('Authentication failure. Wrong credentials',
                                 result['error']['message'], result)
            expected = "The user User(login='cornelius@realm1', " \
                       "realm='realm1', resolver='') exists in NO resolver."
            mock_log.assert_called_once_with(expected)

        # test with realm added to user and unknown realm param
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@realm1",
                                                 "realm": "unknown",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Unknown realm: unknown.',
                             result['error']['message'], result)

        # test with realm parameter
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": "realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            self.assertEqual('realm1', result['value']['realm'], result)

        # test with broken realm parameter
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": "unknown",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Unknown realm: unknown.',
                             result['error']['message'], result)

        # test with empty realm parameter
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": "",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            # realm1 should be the default realm
            self.assertEqual('realm1', result['value']['realm'], result)

        # test with realm parameter and wrong realm added to user
        with mock.patch("logging.Logger.error") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "cornelius@unknown",
                                                     "realm": "realm1",
                                                     "password": "test"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
                result = res.json.get("result")
                self.assertFalse(result.get("status"), result)
            expected = "The user User(login='cornelius@unknown', " \
                       "realm='realm1', resolver='') exists in NO resolver."
            mock_log.assert_called_once_with(expected)

        # test with wrong realm parameter and wrong realm added to user
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@unknown",
                                                 "realm": "anotherunknown",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Unknown realm: anotherunknown.',
                             result['error']['message'], result)

        # Now we take it up one notch and add another resolver
        self.setUp_user_realm3()
        # The selfservice user does not exist in realm3
        with mock.patch("logging.Logger.error") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "selfservice@realm3",
                                                     "realm": "realm1",
                                                     "password": "test"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
                result = res.json.get("result")
                self.assertFalse(result.get("status"), result)
                self.assertEqual(4031, result['error']['code'], result)
            expected = "The user User(login='selfservice@realm3', " \
                       "realm='realm1', resolver='') exists in NO resolver."
            mock_log.assert_called_once_with(expected)

        # and the other way round
        with mock.patch("logging.Logger.error") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "selfservice@realm1",
                                                     "realm": "realm3",
                                                     "password": "test"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
                result = res.json.get("result")
                self.assertFalse(result.get("status"), result)
                self.assertEqual(4031, result['error']['code'], result)
                self.assertEqual('Authentication failure. Wrong credentials',
                                 result['error']['message'], result)
            # the realm will be split from the login name
            expected = "The user User(login='selfservice@realm1', " \
                       "realm='realm3', resolver='') exists in NO resolver."
            mock_log.assert_called_once_with(expected)

        set_privacyidea_config(SYSCONF.SPLITATSIGN, True)

    def test_03_admin_auth(self):
        set_privacyidea_config(SYSCONF.SPLITATSIGN, True)
        # check that the default admin works
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            # role should be 'admin'
            self.assertEqual('admin', result['value']['role'], result)

        # add an admin with an '@' in the login name
        create_db_admin('super@intern', password='testing')
        # as long as the part after the '@' does not resemble an existing realm,
        # this should work with 'spltAtSign' set to True
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "super@intern",
                                                 "password": "testing"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            # role should be 'admin'
            self.assertEqual('admin', result['value']['role'], result)

        # both admin logins should also work with 'splitAtSign' set to False
        set_privacyidea_config(SYSCONF.SPLITATSIGN, False)
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            # role should be 'admin'
            self.assertEqual('admin', result['value']['role'], result)

        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "super@intern",
                                                 "password": "testing"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            # role should be 'admin'
            self.assertEqual('admin', result['value']['role'], result)

        # reset 'splitAtSign' to default value
        set_privacyidea_config(SYSCONF.SPLITATSIGN, True)

    def test_04_remote_user_auth(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        # first check that without a remote_user policy the login fails
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius"},
                                           environ_base={"REMOTE_USER": "cornelius"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(result.get("error").get('code'), 4031, result)
            self.assertEqual(result.get("error").get('message'),
                             'Authentication failure. Wrong credentials', result)
        aentry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(aentry['action'], 'POST /auth', aentry)
        self.assertEqual(aentry['success'], 0, aentry)

        # now check that with a disabled remote_user policy the login fails
        set_policy(name="remote", scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.DISABLE))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius"},
                                           environ_base={"REMOTE_USER": "cornelius"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(result.get("error").get('code'), 4031, result)
            self.assertEqual(result.get("error").get('message'),
                             'Authentication failure. Wrong credentials', result)
        aentry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(aentry['action'], 'POST /auth', aentry)
        self.assertEqual(aentry['success'], 0, aentry)
        self.assertEqual(aentry['policies'], 'remote', aentry)

        # And now check that with an enabled remote_user policy the login succeeds
        set_policy(name="remote", scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.ACTIVE))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius"},
                                           environ_base={"REMOTE_USER": "cornelius"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertEqual(result.get("value").get('role'), 'user', result)
        aentry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(aentry['action'], 'POST /auth', aentry)
        self.assertEqual(aentry['success'], 1, aentry)
        self.assertEqual(aentry['policies'], 'remote', aentry)

        # check that a remote user with "@" works as well
        set_policy(name="remote", scope=SCOPE.WEBUI, realm=self.realm1,
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.ACTIVE))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@realm1"},
                                           environ_base={"REMOTE_USER": "cornelius@realm1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertEqual(result.get("value").get('role'), 'user', result)
        aentry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(aentry['action'], 'POST /auth', aentry)
        self.assertEqual(aentry['success'], 1, aentry)
        self.assertEqual(aentry['policies'], 'remote', aentry)

        # check that the policy remote_user=force passes the necessary hidden tag to the
        # login window
        set_policy(name="remote", scope=SCOPE.WEBUI, realm=self.realm1,
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.FORCE))
        with self.app.test_request_context('/',
                                           method='GET',
                                           environ_base={"REMOTE_USER": "cornelius@realm1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            # The login page contains the info about force remote_user, which will hide the
            # "login with credentials" button.
            self.assertIn('input type=hidden id=FORCE_REMOTE_USER value="True"', to_unicode(res.data))

        # bind the remote user policy to a different realm
        set_policy(name="remote", scope=SCOPE.WEBUI, realm=self.realm2,
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.ACTIVE))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@realm1"},
                                           environ_base={"REMOTE_USER": "cornelius@realm1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
        aentry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(aentry['action'], 'POST /auth', aentry)
        self.assertEqual(aentry['success'], 0, aentry)
        self.assertEqual("", aentry['policies'], aentry)

        # check split@sign is working correctly
        set_policy(name="remote", scope=SCOPE.WEBUI, realm=self.realm1,
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.ACTIVE))
        set_privacyidea_config(SYSCONF.SPLITATSIGN, False)
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "user@test"},
                                           environ_base={"REMOTE_USER": "user@test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertEqual(result.get("value").get('role'), 'user', result)
        aentry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(aentry['action'], 'POST /auth', aentry)
        self.assertEqual(aentry['success'], 1, aentry)
        self.assertEqual(aentry['policies'], 'remote', aentry)

        delete_policy(name='remote')
        set_privacyidea_config(SYSCONF.SPLITATSIGN, True)

    @ldap3mock.activate
    def test_05_local_admin_with_failing_resolver(self):
        ldap3mock.setLDAPDirectory([])
        # define, that we want to get an exception
        ldap3mock.set_exception()
        # Create an LDAP Realm as default realm
        params = {'LDAPURI': 'ldap://localhost',
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
                  "resolver": "ldap1",
                  "type": "ldapresolver"}
        save_resolver(params)
        set_realm("ldap1", [{'name': "ldap1"}])
        set_default_realm("ldap1")

        # Try to log in as internal admin with a failing LDAP resolver
        with mock.patch("logging.Logger.warning") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "testadmin",
                                                     "password": "testpw"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                self.assertTrue(result.get("status"), result)
                self.assertIn('token', result.get("value"), result)
                # role should be 'admin'
                self.assertEqual('admin', result['value']['role'], result)
                mock_log.assert_not_called()

        delete_realm("ldap1")
        delete_resolver("ldap1")
        ldap3mock.set_exception(False)

    @ldap3mock.activate
    def test_06_user_with_failing_resolver(self):
        ldap3mock.setLDAPDirectory([])
        # define, that we want to get an exception
        ldap3mock.set_exception()
        # Create an LDAP Realm as default realm
        params = {'LDAPURI': 'ldap://localhost',
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
                  "resolver": "ldap1",
                  "type": "ldapresolver"}
        save_resolver(params)
        set_realm("ldap1", [{'name': "ldap1"}])
        set_default_realm("ldap1")

        # Try to log in as user with a failing LDAP resolver
        with mock.patch("logging.Logger.warning") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "hans",
                                                     "password": "test"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
                mock_log.assert_called_once_with("Problem resolving user hans in realm ldap1: ERR907: Error performing "
                                                 "bind operation: LDAP request failed.")

        delete_realm("ldap1")
        delete_resolver("ldap1")
        ldap3mock.set_exception(False)

    def test_07_auth_user_not_in_defrealm(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm3)
        # check that realm3 is the default realm
        self.assertEqual(self.realm3, get_default_realm())
        # authentication with "@realm1" works
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            self.assertEqual('realm1', result['value']['realm'], result)

        # while authentication without a realm fails (user "selfservice"
        # doesn't exist in default realm "realm3")
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)

        # A given empty realm parameter should not change the realm of the user
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "test",
                                                 "realm": ""}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get("value"), result)
            self.assertEqual('realm1', result['value']['realm'], result)

    def test_08_user_not_in_userstore(self):
        # If a user can not be found in the userstore we always get the response
        # "Wrong Credentials"
        self.setUp_user_realms()
        set_default_realm(self.realm1)

        # user authenticates against userstore but user does not exist
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "user-really-does-not-exist",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            error = result.get("error")
            self.assertEqual(4031, error.get("code"))
            self.assertEqual("Authentication failure. Wrong credentials", error.get("message"))

        # set a policy to authenticate against privacyIDEA
        set_policy("piLogin", scope=SCOPE.WEBUI, action="{0!s}=privacyIDEA".format(PolicyAction.LOGINMODE))

        # user authenticates against privacyidea but user does not exist
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "user-really-does-not-exist",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            error = result.get("error")
            self.assertEqual(4031, error.get("code"))
            self.assertEqual("Authentication failure. Wrong credentials", error.get("message"))

        # cleanup
        delete_policy("piLogin")
        delete_realm(self.realm1)
        delete_realm(self.realm2)
        delete_resolver(self.resolvername1)

    def test_09_auth_disabled_token_types(self):
        self.setUp_user_realms()
        serial = "SPASS1"

        # Create a working Simple-Pass token
        init_token({"serial": serial,
                    "type": "spass",
                    "pin": "1"},
                   user=User("cornelius", self.realm1))

        # Set the policy to use privacyIDEA for authentication
        set_policy("piLogin", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")

        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": "realm1",
                                                 "password": "1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get('value'), result)
            self.assertEqual(result.get("value").get('role'), 'user', result)

        # Disable the spass token for authentication
        set_policy(name="disable_spass_token", scope=SCOPE.AUTH, action=f"{PolicyAction.DISABLED_TOKEN_TYPES}=spass")

        # The very same auth must now be rejected
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "realm": "realm1",
                                                 "password": "1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"), result)
            self.assertEqual(4031, result['error']['code'], result)
            self.assertEqual('Authentication failure. Wrong credentials',
                             result['error']['message'], result)

        # Clean-up
        remove_token(serial=serial)
        delete_policy("disable_spass_token")
        delete_policy("piLogin")

    def test_10_auth_with_deleted_realm(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm3)
        # User exist in realm1 and realm3 (default realm)
        user = User("cornelius", self.realm1)
        token = init_token({"type": "spass", "pin": "1234"}, user=user)
        user_realm1 = User("hans", self.realm1)
        token_realm1 = init_token({"type": "spass", "pin": "1234"}, user=user_realm1)

        set_policy(name="pi-login", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")

        # successful authentication
        with self.app.test_request_context('/auth', method="POST",
                                           data={"username": user.login, "realm": user.realm, "password": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)

        # Delete realm of user
        Realm.query.filter_by(name=self.realm1).first().delete()

        with self.app.test_request_context('/auth', method="POST",
                                           data={"username": user.login, "realm": user.realm, "password": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
            error = res.json.get("result").get("error")
            self.assertEqual(4031, error.get("code"), error)
            self.assertEqual(f"Authentication failure. Unknown realm: {user.realm}.", error.get("message"), error)

        # only passing username will set the default realm (realm3), in which a user with the same name exist.
        # But credentials for this user are wrong (has no token assigned), hence authentication fails
        with self.app.test_request_context('/auth', method="POST",
                                           data={"username": user.login, "password": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
            error = res.json.get("result").get("error")
            self.assertEqual(4031, error.get("code"), error)
            self.assertEqual(f"Authentication failure. Wrong credentials", error.get("message"), error)
            details = res.json.get("detail")
            self.assertEqual("The user has no tokens assigned", details.get("message"), details)

        # Only passing username will set the default realm, but the user does not exist in that realm.
        # Hence, authentication fails.
        with LogCapture() as capture:
            logging.getLogger("privacyidea.lib.auth").setLevel(logging.DEBUG)
            with self.app.test_request_context('/auth', method="POST",
                                               data={"username": user_realm1.login, "password": "1234"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res.json)
                error = res.json.get("result").get("error")
                self.assertEqual(4031, error.get("code"), error)
                self.assertEqual(f"Authentication failure. Wrong credentials", error.get("message"), error)
            log_msg = ("Error authenticating user against privacyIDEA: UserError(description='User <hans@realm3> does "
                       "not exist.', id=904)")
            capture.check_present(("privacyidea.lib.auth", "DEBUG", log_msg))

        token.delete_token()
        token_realm1.delete_token()
        delete_policy("pi-login")
        Realm.query.filter_by(name=self.realm3).first().delete()

    def test_11_failcounter_exceeded(self):
        set_policy("pi-login", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")
        self.setUp_user_realms()
        user = User("hans", self.realm1)
        token = init_token({"pin": "123456", "type": "spass"}, user=user)
        token.set_maxfail(5)
        token.set_failcount(5)
        past = datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=10)
        token.add_tokeninfo(FAILCOUNTER_EXCEEDED, past.strftime(DATE_FORMAT))
        # a valid authentication will fail
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": user.login,
                                                 "password": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("status"))
            self.assertEqual("Failcounter exceeded", detail.get("message"))
        self.assertEqual(5, token.get_failcount())
        # invalid authentication fails with same message
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": user.login,
                                                 "password": "000000"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("status"))
            self.assertEqual("Failcounter exceeded", detail.get("message"))
        self.assertEqual(5, token.get_failcount())

        # set timeout
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 30)
        # timeout not expired: same behaviour
        # a valid authentication will fail
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": user.login,
                                                 "password": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("status"))
            self.assertEqual("Failcounter exceeded", detail.get("message"))
        self.assertEqual(5, token.get_failcount())
        # invalid authentication fails with same message
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": user.login,
                                                 "password": "000000"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("status"))
            self.assertEqual("Failcounter exceeded", detail.get("message"))
        self.assertEqual(5, token.get_failcount())

        # timeout expired
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 5)
        # a valid authentication succeeds and resets failcount to 0
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": user.login,
                                                 "password": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("value"))
            self.assertEqual("matching 1 tokens", detail.get("message"))
        self.assertEqual(0, token.get_failcount())
        # an invalid auth also resets the failcount and increase it directly to one due to the invalid auth
        token.set_failcount(5)
        token.add_tokeninfo(FAILCOUNTER_EXCEEDED, past.strftime(DATE_FORMAT))
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": user.login,
                                                 "password": "000000"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("status"))
            self.assertEqual("wrong otp pin", detail.get("message"))
        self.assertEqual(1, token.get_failcount())

        token.delete_token()
        delete_policy("pi-login")
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 0)

    def test_12_passthru_token_verify(self):
        """
        In case the passthru and verify_enrollment policies are set, but the user does not verify the enrollment,
        he will not be able to login anymore to complete the enrollment. For this case, an event handler can be used
        to delete a token in the rollout_state verify before the authentication to allow the enrollment of a new token.
        """
        set_policy("passthru", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.PASSTHRU}=userstore,{PolicyAction.OTPPIN}=userstore")
        set_policy("login-mode", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")
        set_policy("verify", scope=SCOPE.ENROLL, action=f"{PolicyAction.VERIFY_ENROLLMENT}=hotp")
        event_id = set_event("delete_verify", event="auth", handlermodule="Token", action="delete",
                  conditions={"rollout_state": "verify"}, position="pre")
        self.setUp_user_realms()

        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            auth_token = result.get("value").get("token")

        # Enroll Token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           headers={"Authorization": auth_token},
                                           data={"type": "hotp"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            serial = res.json.get("detail").get("serial")
            self.assertIsNotNone(serial, result)

        first_token = get_one_token(serial=serial)
        self.assertEqual("verify", first_token.rollout_state)

        # New authentication succeeds
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            auth_token = result.get("value").get("token")

        # enrolled token is deleted
        self.assertRaises(ResourceNotFoundError, get_one_token, serial=serial)

        # Enroll new token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           headers={"Authorization": auth_token},
                                           data={"type": "hotp"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            serial = res.json.get("detail").get("serial")
            self.assertIsNotNone(serial, result)

        new_token = get_one_token(serial=serial)
        self.assertEqual("verify", new_token.rollout_state)

        # verify token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           headers={"Authorization": auth_token},
                                           data={"type": "hotp", "serial": serial, "verify": new_token.get_otp()[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)

        self.assertEqual("enrolled", new_token.rollout_state)

        # auth without token now fails
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # token still exists
        self.assertIsNotNone(get_one_token(serial=serial))

        # auth with token succeeds
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "test" + new_token.get_otp()[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)

        # clean up
        new_token.delete_token()
        delete_policy("passthru")
        delete_policy("login-mode")
        delete_policy("verify")
        delete_event(event_id)


class AdminFromUserstore(OverrideConfigTestCase):
    class Config(TestingConfig):
        SUPERUSER_REALM = ["realm1"]

    def test_01_admin_from_userstore(self):
        self.setUp_user_realms()
        # login as an admin user from userstore
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get('value'), result)
            self.assertEqual(result.get("value").get('role'), 'admin', result)
            # if no admin policy is set, the user should have all admin rights
            self.assertIn(PolicyAction.DELETE, result.get('value').get('rights'), result)

        # Now test with a helpdesk policy for the admin realm
        set_policy(name='helpdesk', scope=SCOPE.ADMIN, adminrealm=self.realm1,
                   action=PolicyAction.DISABLE)
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "cornelius@Realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertIn('token', result.get('value'), result)
            self.assertEqual(result.get("value").get('role'), 'admin', result)
            # check that the appropriate rights are set/unset
            self.assertNotIn(PolicyAction.DELETE, result.get('value').get('rights'), result)
            self.assertIn(PolicyAction.DISABLE, result.get('value').get('rights'), result)
        delete_policy(name='helpdesk')


class DuplicateUserApiTestCase(MyApiTestCase):

    def setUp(self):
        # create a default realm, that contains the used "testadmin"
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1,
                                    [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        set_default_realm(self.realm1)

    def test_01_admin_and_user_same_name(self):
        # Test the logging, if admin and user have the same name (testadmin/testpw)

        # If the admin logs in, everything is fine
        with mock.patch("logging.Logger.info") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "testadmin",
                                                     "password": "testpw"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                self.assertTrue(result.get("status"), result)
                self.assertIn('token', result.get("value"), result)
                # role should be 'admin'
                self.assertEqual('admin', result['value']['role'], result)
            mock_log.assert_any_call("Local admin 'testadmin' successfully logged in.")

        # If a user logs in, with the same name as the admin, this event is logged in warning
        with mock.patch("logging.Logger.warning") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "testadmin",
                                                     "password": "test"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                self.assertTrue(result.get("status"), result)
                self.assertIn('token', result.get("value"), result)
                # role should be 'user'
                self.assertEqual('user', result['value']['role'], result)
            # check if we have this log entry
            mock_log.assert_called_with("A user 'testadmin' exists as local admin and as user "
                                        "in your default realm!")

        # Check that a wrong/missing password doesn't trigger the warning in the log
        with mock.patch("logging.Logger.warning") as mock_log:
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "testadmin",
                                                     "password": "unknown"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
                result = res.json.get("result")
                self.assertFalse(result.get("status"), result)
                self.assertEqual(result.get("error").get('code'), 4031, result)
                self.assertEqual(result.get("error").get('message'),
                                 'Authentication failure. Wrong credentials', result)
            # check if we have the correct log entry
            mock_log.assert_called_with("user uid 1004 failed to authenticate")

    def test_02_max_auth_failed(self):
        """
        Test that the prepolicies "auth_max_fail" is applied correctly to a local admin and
        user with the same username in the defrealm
        """
        # Generic policy is applied to both
        set_policy("max_fail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXFAIL}=2/1m")
        self.app_context.g.audit_object.clear()

        # Admin
        for i in range(2):
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "testadmin",
                                                     "password": "wrong"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)
        # third successful authentication fails due to policy
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"), "Only 2 failed authentications per 0:01:00 allowed.", details)

        # Correct authentication for user also fails, since we can not differentiate between local admin and user
        # before the authentication
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"), "Only 2 failed authentications per 0:01:00 allowed.", details)

        # Even if we explicitly pass the realm, the user can not authenticate since we can not distinguish admins and
        # users in the audit log for failed authentications
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "realm": self.realm1,
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"), "Only 2 failed authentications per 0:01:00 allowed.", details)

        # Realm policy is only applied to user
        set_policy("max_fail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXFAIL}=2/1m", realm=self.realm1)

        # Failed authentications
        for i in range(2):
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "testadmin",
                                                     "password": "wrong"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(401, res.status_code, res)

        # Admin: third successful authentication is successful
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

        # User: third successful authentication fails due to policy
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 failed authentications per 0:01:00 allowed.",
                             details)

        delete_policy("max_fail")

    def test_03_max_auth_success(self):
        """
        Test that the prepolicies "auth_max_success" is applied correctly to a local admin and user with the same
        username in the defrealm
        """
        # Generic policy is applied to both
        set_policy("max_success", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXSUCCESS}=2/1m")
        self.app_context.g.audit_object.clear()

        # Admin
        for i in range(2):
            with self.app.test_request_context('/auth',
                                               method='POST',
                                               data={"username": "testadmin",
                                                     "password": "testpw"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res.json)
        # third successful authentication fails due to policy
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 successful authentications per 0:01:00 allowed.", details)

        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 successful authentications per 0:01:00 allowed.", details)

        # But if we explicitly pass the realm, the user can authenticate
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "realm": self.realm1,
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

        # Realm policy is only applied to user
        set_policy("max_success", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXSUCCESS}=2/1m", realm=self.realm1)

        # Admin can log in successfully
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)

        # User can also authenticate successfully a second time even without the realm
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
        # but third login still fails
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 successful authentications per 0:01:00 allowed.", details)

        delete_policy("max_success")

    def test_04_increase_failcounter_on_challenge(self):
        set_policy("pi_login", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")
        set_policy("challenge_response", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGERESPONSE}=hotp,{PolicyAction.OTPPIN}=userstore")
        set_policy("failcounter_challenge", scope=SCOPE.AUTH, action=PolicyAction.INCREASE_FAILCOUNTER_ON_CHALLENGE,
                   realm=self.realm1)

        user = User(self.testadmin, self.realm1)
        hotp = init_token({"type": "hotp"}, user)
        serial = hotp.get_serial()

        # Authenticate with admin not triggers a challenge
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(AUTH_RESPONSE.ACCEPT, res.json.get("result").get("authentication"))
            hotp = get_one_token(serial=serial)
            self.assertEqual(0, hotp.get_failcount())
            self.assertEqual(0, len(get_challenges(serial)))

        # Failed admin authentication also increases the fail counter of the user token
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "wrong"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)
            hotp = get_one_token(serial=serial)
            self.assertEqual(1, hotp.get_failcount())
            self.assertEqual(0, len(get_challenges(serial)))

        # Authenticate with user triggers a challenge and increase the fail counter
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(AUTH_RESPONSE.CHALLENGE, res.json.get("result").get("authentication"))
            hotp = get_one_token(serial=serial)
            self.assertEqual(2, hotp.get_failcount())
            self.assertEqual(1, len(get_challenges(serial)))

        hotp.delete_token()
        delete_policy("pi_login")
        delete_policy("challenge_response")
        delete_policy("failcounter_challenge")

    def test_05_disabled_token_types(self):
        set_policy("pi_login", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")
        set_policy("otp_pin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        set_policy("disabled_token_types", scope=SCOPE.AUTH, action=f"{PolicyAction.DISABLED_TOKEN_TYPES}=totp",
                   realm=self.realm1)
        user = User(self.testadmin, self.realm1)
        totp = init_token({"type": "totp"}, user=user)
        hotp = init_token({"type": "hotp"}, user=user)

        # Authenticate with admin works without token
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(AUTH_RESPONSE.ACCEPT, res.json.get("result").get("authentication"))

        # Authenticate user with TOTP token fails
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": f"test{totp.get_otp()[2]}"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)

        # Authenticate user with HOTP token works
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": f"test{hotp.get_otp()[2]}"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(AUTH_RESPONSE.ACCEPT, res.json.get("result").get("authentication"))

        # Clean-up
        totp.delete_token()
        hotp.delete_token()
        delete_policy("pi_login")
        delete_policy("otp_pin")
        delete_policy("disabled_token_types")

    def test_06_jwt_validity(self):
        # generic policy applies to both
        set_policy("jwt_validity", scope=SCOPE.WEBUI, action=f"{PolicyAction.JWTVALIDITY}=1800")

        # Admin
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            jwt = res.json.get("result").get("value").get("token")
            verify_result = verify_auth_token(jwt)
            expiration = datetime.datetime.fromtimestamp(verify_result.get("exp"), tz=datetime.timezone.utc)
            expected_expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=1800)
            self.assertAlmostEqual(expected_expiration, expiration, delta=datetime.timedelta(seconds=5))

        # User
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            jwt = res.json.get("result").get("value").get("token")
            verify_result = verify_auth_token(jwt)
            expiration = datetime.datetime.fromtimestamp(verify_result.get("exp"), tz=datetime.timezone.utc)
            expected_expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=1800)
            self.assertAlmostEqual(expected_expiration, expiration, delta=datetime.timedelta(seconds=5))

        # change to realm policy
        set_policy("jwt_validity", scope=SCOPE.WEBUI, action=f"{PolicyAction.JWTVALIDITY}=7200", realm=self.realm1)

        # Admin: Default time 3600 s
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            jwt = res.json.get("result").get("value").get("token")
            verify_result = verify_auth_token(jwt)
            expiration = datetime.datetime.fromtimestamp(verify_result.get("exp"), tz=datetime.timezone.utc)
            expected_expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=3600)
            self.assertAlmostEqual(expected_expiration, expiration, delta=datetime.timedelta(seconds=5))

        # User: takes value from policy
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            jwt = res.json.get("result").get("value").get("token")
            verify_result = verify_auth_token(jwt)
            expiration = datetime.datetime.fromtimestamp(verify_result.get("exp"), tz=datetime.timezone.utc)
            expected_expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=7200)
            self.assertAlmostEqual(expected_expiration, expiration, delta=datetime.timedelta(seconds=5))

        delete_policy("jwt_validity")


class EventHandlerTest(MyApiTestCase):

    def test_01_pre_eventhandlers(self):
        # This test create an HOTP token with C/R with a pre-event handler
        # and the user uses this HOTP token to directly login to /auth

        # Setup realm
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1,
                                    [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        set_default_realm(self.realm1)

        # set a policy to authenticate against privacyIDEA
        set_policy("piLogin", scope=SCOPE.WEBUI, action="{0!s}=privacyIDEA".format(PolicyAction.LOGINMODE))
        # set a policy to for otppin=userstore
        set_policy("otppin", scope=SCOPE.AUTH, action="{0!s}=userstore".format(PolicyAction.OTPPIN))
        # Set a policy to do C/R with HOTP tokens
        set_policy("crhotp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(PolicyAction.CHALLENGERESPONSE))

        # Create an event handler, that creates HOTP token on /auth with default OTP key
        # TODO: this is probably a bad test case since enrolling an HOTP-Token
        #  during `/auth` does not return the generated secret/QR-code.
        #  For now this is useful to test the `/auth` endpoint with challenge-response.
        eid = set_event("createtoken", event=["auth"], handlermodule="Token",
                        action="enroll", position="pre",
                        conditions={CONDITION.USER_TOKEN_NUMBER: 0},
                        options={"tokentype": "hotp", "user": "1",
                                 "additional_params": {
                                     'otpkey': self.otpkey,
                                     # We need to set genkey=0, otherwise the Tokenhandler will
                                     # generate a random otpkey
                                     'genkey': 0}})
        # cleanup tokens
        remove_token(user=User("someuser", self.realm1))

        # user tries to log in with his userstore password and gets a transaction_id
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "someuser",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            detail = res.json.get("detail")
            self.assertEqual("please enter otp: ", detail.get("message"))
            transaction_id = detail.get("transaction_id")
            # In case of a challenge request, make sure no user data is spilled
            self.assertNotIn("someuser", json.dumps(res.json), res.json)
            self.assertFalse(result.get("value"), result)
            self.assertEqual(result.get("authentication"), AUTH_RESPONSE.CHALLENGE, result)

        # Check if the token was enrolled
        toks = get_tokens(user=User("someuser", self.realm1))
        self.assertEqual(len(toks), 1)
        self.assertEqual(toks[0].token.tokentype, "hotp")
        serial = toks[0].token.serial
        # Check if the correct otpkey was used
        hotptoken = toks[0]
        r = hotptoken.check_otp(self.valid_otp_values[1])
        self.assertTrue(r >= 0)

        # Now the user logs in with the second step of C/R with OTP value of new token
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "someuser",
                                                 "transaction_id": transaction_id,
                                                 "password": self.valid_otp_values[2]}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertEqual(result.get("authentication"), AUTH_RESPONSE.ACCEPT, result)
            self.assertTrue(result.get("value"))

        # Check that there is still only one token
        toks = get_tokens(user=User("someuser", self.realm1))
        self.assertEqual(len(toks), 1)
        self.assertEqual(toks[0].token.tokentype, "hotp")
        self.assertEqual(serial, toks[0].token.serial)

        # cleanup
        delete_policy("piLogin")
        delete_policy("otppin")
        delete_policy("crhotp")
        delete_event(eid)
        remove_token(hotptoken.token.serial)

    @log_capture
    def test_02_post_eventhandler(self, capture):
        self.setUp_user_realms()
        # Create an event handler, that creates HOTP token on /auth with default OTP key
        eid = set_event("post_event_log", event=["auth"], handlermodule="Logging",
                        action="logging", position="post",
                        options={"level": logging.INFO,
                                 "message": "User: {user} Event: {action}"})

        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "someuser",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)

        capture.check_present(
            ('pi-eventlogger', 'INFO',
             'User: someuser Event: /auth')
        )

        delete_event(eid)
