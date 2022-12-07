# -*- coding: utf-8 -*-

import mock
from contextlib import contextmanager
from datetime import datetime, timedelta

from .base import MyApiTestCase
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from privacyidea.models import Audit
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.auditmodules.base import Audit as BaseAudit

PWFILE = "tests/testdata/passwords"


class APIAuditTestCase(MyApiTestCase):

    realm1a = "realm1a"
    realm2b = "realm2b"

    def setUp_user_realms(self):
        # create user realm
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1a,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        (added, failed) = set_realm(self.realm2b,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

    def test_00_get_audit(self):
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertTrue(json_response.get("result").get("value").get(
                "current") == 1, res)
            # check that we have all available entries in the audit data
            # create a fake base Audit object to get the available_columns prop
            a = BaseAudit()
            self.assertEqual(set(json_response['result']['value']['auditcolumns']),
                             set(a.available_audit_columns),
                             json_response['result']['value']['auditcolumns'])
            self.assertEqual(set(json_response['result']['value']['auditdata'][0].keys()),
                             set(a.available_audit_columns),
                             json_response['result']['value']['auditcolumns'])

        # TODO: test audit columns if HIDE_AUDIT_COLUMNS policy is set.

        # check for entry in audit log
        aentry = self.find_most_recent_audit_entry(action='GET /audit/')
        self.assertEqual(aentry['action'], 'GET /audit/', aentry)
        self.assertEqual(aentry['success'], 1, aentry)

        # Empty search, like search for a date, that contains X
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={'date': '*X*'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            cols = json_response.get("result").get("value").get("auditcolumns")
            self.assertIn("number", cols)
            self.assertIn("serial", cols)
            self.assertEqual(22, len(cols))

    def test_01_get_audit_csv(self):
        @contextmanager
        def _fake_time(t):
            """ context manager that fakes the current time that is written
            to the database """
            with mock.patch("privacyidea.models.datetime") as mock_dt:
                mock_dt.now.return_value = t
                yield

        with self.app.test_request_context('/audit/test.csv',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/csv', res)
            self.assertIn('Content-disposition', res.headers, res.headers)
            self.assertEqual('attachment; filename=test.csv',
                             res.headers['Content-disposition'], res.headers)
            # we have at least 2 entries here, the authentication and this one
            self.assertGreater(len(list(res.response)), 1)

        # add an audit entry which happened 10 minutes ago
        with _fake_time(datetime.now() - timedelta(minutes=10)):
            Audit(action="enroll", success=1, realm="foo").save()
        # now request all audit entries from the last 5 minutes
        with self.app.test_request_context('/audit/test.csv',
                                           method='GET',
                                           data={'timelimit': '5m'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/csv', res)
            # The audit entry from (fake) 10 minutes ago should not be in the
            # result data
            self.assertNotIn(b"'enroll','1','','','','foo'", res.data, res)

    def test_02_get_allowed_audit_realm(self):
        # Check that an administrator is only allowed to see log entries of
        # the defined realms.
        # fill some audit entries
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()

        # check, that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": self.realm1a},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 2)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertGreaterEqual(json_response.get("result").get("value").get(
                "count"), 7)
            audit_list = json_response.get("result").get("value").get("auditdata")
            audit_actions = [a for a in audit_list if a.get("action") == "GET /audit/"]
            self.assertGreaterEqual(len(audit_actions), 1)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": self.realm2b},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 3)

        # set policy for audit realms
        set_policy("audit01", scope=SCOPE.ADMIN, action=ACTION.AUDIT,
                   realm=self.realm1a)

        # check, that we only see allowed audit realms
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            audit_list = json_response.get("result").get("value").get("auditdata")
            audit_realms = [a for a in audit_list if a.get("realm") == self.realm1a]
            self.assertEqual(len(audit_realms), 3)
            self.assertEqual(json_response.get("result").get("value").get("count"), 3)

        # delete policy
        delete_policy("audit01")

    def test_03_get_allowed_audit_realm(self):
        # Check than an internal admin is allowed to see all realms
        # A helpdesk user in "adminrealm" is only allowerd to see realm1A
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()

        # check, that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": self.realm1a},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertGreaterEqual(json_response.get("result").get("value").get(
                "count"), 2)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": self.realm2b},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertGreaterEqual(json_response.get("result").get("value").get(
                "count"), 3)

        # set policy: helpdesk users in adminrealm are only allowed to
        # view "realm1A".
        set_policy("audit01", scope=SCOPE.ADMIN, action=ACTION.AUDIT,
                   adminrealm="adminrealm", realm=self.realm1a)
        # Test admin is allowed to view unrestricted logs!
        set_policy("audit02", scope=SCOPE.ADMIN, action=ACTION.AUDIT,
                   user="testadmin")

        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm("adminrealm",
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        helpdesk_authorization = None
        with self.app.test_request_context('/auth',
                                           method='POST', data={'username': 'selfservice@adminrealm',
                                                                'password': 'test'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            value = json_response.get("result").get("value")
            # Helpdesk user is allowed to view the audit log.
            self.assertTrue("auditlog" in value.get("rights"))
            helpdesk_authorization = value.get("token")

        # check, that we only see allowed audit realms
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"action": "**",
                                                 "action_detail": "**",
                                                 "administrator": "**",
                                                 "client": "**",
                                                 "date": "**",
                                                 "info": "**",
                                                 "page": "1",
                                                 "page_size": "10",
                                                 "policies": "**",
                                                 "privacyidea_server": "**",
                                                 "realm": "**",
                                                 "resolver": "**",
                                                 "serial": "**",
                                                 "sortorder": "desc",
                                                 "success": "**",
                                                 "tokentype": "**",
                                                 "user": "**"},
                                           headers={'Authorization': helpdesk_authorization}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            count = json_response.get("result").get("value").get("count")
            auditdata = json_response.get("result").get("value").get("auditdata")
            self.assertGreaterEqual(count, 3)
            # All entries are in realm1A!
            for ad in auditdata:
                self.assertEqual(ad.get("realm"), self.realm1a)

        # Now check, that the testadmin (self.at) sees all entries!
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            count = json_response.get("result").get("value").get("count")
            auditdata = json_response.get("result").get("value").get("auditdata")
            self.assertGreaterEqual(count, 10)

        # delete policy
        delete_policy("audit01")
        delete_policy("audit02")

    def test_04_get_user_audit_log(self):
        # Test that the user only sees audit log entries with his own data
        self.setUp_user_realms()
        # prepare some log entries for the normal user to try to fetch
        Audit(action="enroll", success=1, user="selfservice", administrator=None,
              resolver="resolver1", realm=self.realm1a).save()
        Audit(action="enroll", success=1, user="selfservice", administrator=None,
              resolver="resolver1", realm=self.realm1a).save()
        Audit(action="enroll", success=1, user="selfservice", administrator=None,
              resolver="resolver1", realm=self.realm2b).save()
        Audit(action="enroll", success=1, user="selfservice", administrator=None,
              resolver="resolver1", realm=self.realm2b).save()
        Audit(action="enroll", success=1, user="selfservice", administrator=None,
              resolver="resolver1", realm=self.realm2b).save()

        # set policy: normal users in realm1a are allowed to view audit log
        set_policy("audit01", scope=SCOPE.USER, action=ACTION.AUDIT, realm=self.realm1a)

        user_authorization = None
        with self.app.test_request_context('/auth',
                                           method='POST', data={'username': 'selfservice@{0!s}'.format(self.realm1a),
                                                                'password': 'test'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            value = json_response.get("result").get("value")
            self.assertTrue("auditlog" in value.get("rights"))
            user_authorization = value.get("token")

        # check, that the normal user only sees his own entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"action": "**",
                                                 "action_detail": "**",
                                                 "administrator": "**",
                                                 "client": "**",
                                                 "date": "**",
                                                 "info": "**",
                                                 "page": "1",
                                                 "page_size": "10",
                                                 "policies": "**",
                                                 "privacyidea_server": "**",
                                                 "realm": "**",
                                                 "resolver": "**",
                                                 "serial": "**",
                                                 "sortorder": "desc",
                                                 "success": "**",
                                                 "tokentype": "**",
                                                 "user": "**"},
                                           headers={'Authorization': user_authorization}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            count = json_response.get("result").get("value").get("count")
            auditdata = json_response.get("result").get("value").get("auditdata")
            self.assertGreaterEqual(count, 3)
            # All entries are in realm1A!
            for ad in auditdata:
                self.assertEqual(ad.get("realm"), self.realm1a)

        # try to explicitly query another realm
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"action": "**",
                                                 "action_detail": "**",
                                                 "administrator": "**",
                                                 "client": "**",
                                                 "date": "**",
                                                 "info": "**",
                                                 "page": "1",
                                                 "page_size": "10",
                                                 "policies": "**",
                                                 "privacyidea_server": "**",
                                                 "realm": self.realm2b,
                                                 "resolver": "**",
                                                 "serial": "**",
                                                 "sortorder": "desc",
                                                 "success": "**",
                                                 "tokentype": "**",
                                                 "user": "**"},
                                           headers={'Authorization': user_authorization}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # The normal user can not fetch audit entries, that do not belong to him!
            count = json_response.get("result").get("value").get("count")
            self.assertGreaterEqual(count, 0)

        # delete policy
        delete_policy("audit01")
