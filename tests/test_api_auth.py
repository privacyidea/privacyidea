# -*- coding: utf-8 -*-
""" Test for the '/auth' API-endpoint """
import logging

from testfixtures import log_capture
from .base import MyApiTestCase, OverrideConfigTestCase
import mock
from privacyidea.lib.config import set_privacyidea_config, SYSCONF
from privacyidea.lib.policy import (set_policy, SCOPE, ACTION, REMOTE_USER,
                                    delete_policy)
from privacyidea.lib.auth import create_db_admin
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.realm import (set_realm, set_default_realm, delete_realm,
                                   get_default_realm)
from privacyidea.lib.event import set_event, delete_event
from privacyidea.lib.eventhandler.base import CONDITION
from privacyidea.lib.token import get_tokens, remove_token
from privacyidea.lib.user import User
from privacyidea.lib.utils import to_unicode
from privacyidea.config import TestingConfig
from . import ldap3mock


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
        create_db_admin(self.app, 'super@intern', password='testing')
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
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.DISABLE))
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
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.ACTIVE))
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
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.ACTIVE))
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
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.FORCE))
        with self.app.test_request_context('/',
                                           method='GET',
                                           environ_base={"REMOTE_USER": "cornelius@realm1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            # The login page contains the info about force remote_user, which will hide the
            # "login with credentials" button.
            self.assertIn('input type=hidden id=FORCE_REMOTE_USER value="True"', to_unicode(res.data))

        # bind the remote user policy to an unknown realm
        set_policy(name="remote", scope=SCOPE.WEBUI, realm='unknown',
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.ACTIVE))
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
        self.assertEqual(None, aentry['policies'], aentry)

        # check split@sign is working correctly
        set_policy(name="remote", scope=SCOPE.WEBUI, realm=self.realm1,
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.ACTIVE))
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
        set_realm("ldap1", ["ldap1"])
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
                mock_log.assert_called_once_with("Problem resolving user testadmin in realm ldap1: LDAP request failed.")

        delete_realm("ldap1")
        delete_resolver("ldap1")
        ldap3mock.set_exception(False)

    def test_06_auth_user_not_in_defrealm(self):
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

    def test_07_user_not_in_userstore(self):
        # If a user can not be found in the userstore we always get the response "Wrong Credentials"
        # Setup realm
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)
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
        set_policy("piLogin", scope=SCOPE.WEBUI, action="{0!s}=privacyIDEA".format(ACTION.LOGINMODE))

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
        delete_resolver(self.resolvername1)


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
            self.assertIn(ACTION.DELETE, result.get('value').get('rights'), result)

        # Now test with a helpdesk policy for the admin realm
        set_policy(name='helpdesk', scope=SCOPE.ADMIN, adminrealm=self.realm1,
                   action=ACTION.DISABLE)
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
            self.assertNotIn(ACTION.DELETE, result.get('value').get('rights'), result)
            self.assertIn(ACTION.DISABLE, result.get('value').get('rights'), result)
        delete_policy(name='helpdesk')


class DuplicateUserApiTestCase(MyApiTestCase):

    def test_01_admin_and_user_same_name(self):
        # Test the logging, if admin and user have the same name (testadmin/testpw)
        # Now create a default realm, that contains the used "testadmin"
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        set_default_realm(self.realm1)

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
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        set_default_realm(self.realm1)

        # set a policy to authenticate against privacyIDEA
        set_policy("piLogin", scope=SCOPE.WEBUI, action="{0!s}=privacyIDEA".format(ACTION.LOGINMODE))
        # set a policy to for otppin=userstore
        set_policy("otppin", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN))
        # Set a policy to do C/R with HOTP tokens
        set_policy("crhotp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))

        # Create an event handler, that creates HOTP token on /auth with default OTP key
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
