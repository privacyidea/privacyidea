# SPDX-FileCopyrightText: 2015 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
from contextlib import contextmanager, suppress
from datetime import datetime, timedelta, UTC

from unittest import mock

from privacyidea.lib.auditmodules.base import Audit as BaseAudit
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.utils import AUTH_RESPONSE
from privacyidea.models import Audit, db
from .base import MyApiTestCase, non_utc_time_zone

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
                                    [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        (added, failed) = set_realm(self.realm2b,
                                    [{'name': self.resolvername1}])
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
            audit_response = set(json_response['result']['value']['auditcolumns'])
            self.assertEqual(audit_response, set(a.available_audit_columns),
                             json_response['result']['value']['auditcolumns'])
            audit_response = set(json_response['result']['value']['auditdata'][0].keys())
            self.assertEqual(audit_response, set(a.available_audit_columns),
                             json_response['result']['value']['auditcolumns'])

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
            self.assertEqual(27, len(cols))

    def test_01_get_audit_csv(self):
        @contextmanager
        def _fake_time(t):
            """ context manager that fakes the current time that is written
            to the database """
            with mock.patch("privacyidea.models.audit.datetime") as mock_dt:
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
        self.setUp_user_realms()
        Audit.query.delete()

        # Check that an administrator is only allowed to see log entries of
        # the defined realms and its own log entries
        # fill some audit entries
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()

        # check, that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"realm": self.realm1a},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 2)
            self.assertEqual(2, len(json_response.get("result").get("value").get("auditdata")))

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(6, json_response.get("result").get("value").get(
                "count"))
            audit_list = json_response.get("result").get("value").get("auditdata")
            audit_actions = [a for a in audit_list if a.get("action") == "GET /audit/"]
            self.assertGreaterEqual(len(audit_actions), 1)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"realm": self.realm2b},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(3, json_response.get("result").get("value").get(
                "count"))

        # set policy for audit realms
        set_policy("audit01", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT,
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
            self.assertEqual(3, len(audit_realms))
            admin_audit = [a for a in audit_list if a.get("administrator") == "testadmin"]
            self.assertEqual(3, len(admin_audit))
            self.assertEqual(5, json_response.get("result").get("value").get("count"))
            # Check that all audit columns are available
            self.assertEqual(set(BaseAudit().available_audit_columns),
                             set(json_response.get("result").get("value").get("auditcolumns")))

        # Set policy to restrict audit columns
        set_policy("audit02", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.HIDE_AUDIT_COLUMNS}=serial action")

        # Check, that the normal user can only see the restricted audit columns
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # Check that only restricted audit columns are available
            self.assertTrue({"serial", "action"}.isdisjoint(
                set(json_response.get("result").get("value").get("auditcolumns"))),
                json_response.get("result").get("value").get("auditcolumns"))
            self.assertEqual(len(json_response.get("result").get("value").get("auditdata")[0]),
                             len(json_response.get("result").get("value").get("auditcolumns")))
        # delete policy
        delete_policy("audit01")
        delete_policy("audit02")

    def test_03_get_allowed_audit_realm(self):
        self.setUp_user_realms()
        Audit.query.delete()
        # Check that an internal admin is allowed to see all realms
        # A helpdesk user in "adminrealm" is only allowed to see realm1A
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()

        # check, that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"realm": self.realm1a},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(2, json_response.get("result").get("value").get("count"))

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"realm": self.realm2b},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(3, json_response.get("result").get("value").get("count"))

        # set policy: helpdesk users in adminrealm are only allowed to
        # view "realm1A".
        set_policy("audit01", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT, adminrealm="adminrealm",
                   realm=self.realm1a)
        # Test admin is allowed to view unrestricted logs!
        set_policy("audit02", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT, adminuser="testadmin")

        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm("adminrealm",
                                    [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={'username': 'selfservice@adminrealm',
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
                                           query_string={"action": "**",
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
                                                         "user": "**",
                                                         "container_serial": "**",
                                                         "container_type": "**"},
                                           headers={'Authorization': helpdesk_authorization}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # We have 3 entries for realm1a and 1 auth entry for the admin
            count = json_response.get("result").get("value").get("count")
            self.assertEqual(4, count)
            audit_list = json_response.get("result").get("value").get("auditdata")
            # Own audit entries
            admin_auth = [a for a in audit_list if a.get("action") == "POST /auth"]
            self.assertEqual("selfservice", admin_auth[0].get("administrator"))
            self.assertEqual(1, len(admin_auth))
            # audit entries for realm1a
            audit_realm1a = [a for a in audit_list if a.get("action") != "POST /auth"]
            self.assertEqual(3, len(audit_realm1a))
            for ad in audit_realm1a:
                self.assertEqual(ad.get("realm"), self.realm1a)

        # Now check, that the testadmin (self.at) sees all entries!
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            count = json_response.get("result").get("value").get("count")
            self.assertEqual(9, count)
            audit_data = json_response.get("result").get("value").get("auditdata")
            audit_realm1a = [a for a in audit_data if a.get("realm") == self.realm1a]
            self.assertEqual(3, len(audit_realm1a))
            audit_realm2b = [a for a in audit_data if a.get("realm") == self.realm2b]
            self.assertEqual(4, len(audit_realm2b))
            audit_testadmin = [a for a in audit_data if a.get("administrator") == "testadmin"]
            self.assertEqual(2, len(audit_testadmin))
            audit_admin = [a for a in audit_data if a.get("administrator") == "selfservice"]
            self.assertEqual(2, len(audit_admin))

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
        set_policy("audit01", scope=SCOPE.USER, action=PolicyAction.AUDIT, realm=self.realm1a)

        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={'username': f'selfservice@{self.realm1a!s}',
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
                                           query_string={"action": "enroll",
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
                                                         "user": "**",
                                                         "container_serial": "**",
                                                         "container_type": "**"},
                                           headers={'Authorization': user_authorization}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            count = json_response.get("result").get("value").get("count")
            auditdata = json_response.get("result").get("value").get("auditdata")
            self.assertEqual(2, count, json_response)
            # Check that all audit columns are available
            self.assertEqual(set(BaseAudit().available_audit_columns),
                             set(json_response.get("result").get("value").get("auditcolumns")))
            # All entries are in realm1A!
            for ad in auditdata:
                self.assertEqual(ad.get("realm"), self.realm1a)

        # Set policy to restrict audit columns
        set_policy("audit02", scope=SCOPE.USER,
                   action=f"{PolicyAction.HIDE_AUDIT_COLUMNS}=serial action")

        # Check, that the normal user can only see the restricted audit columns
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': user_authorization}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            # Check that only restricted audit columns are available
            self.assertTrue({"serial", "action"}.isdisjoint(
                set(json_response.get("result").get("value").get("auditcolumns"))),
                json_response.get("result").get("value").get("auditcolumns"))
            self.assertEqual(len(json_response.get("result").get("value").get("auditdata")[0]),
                             len(json_response.get("result").get("value").get("auditcolumns")))

        # try to explicitly query another realm
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"action": "**",
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
                                                         "user": "**",
                                                         "container_serial": "**",
                                                         "container_type": "**"},
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
        delete_policy("audit02")

    def test_05_audit_age(self):
        # Check that audit age policy is applied correctly
        Audit.query.delete()
        self.setUp_user_realms()
        date = datetime.now(UTC)
        three_days = timedelta(days=3)
        # enroll policies are within last day and enable policies not
        audit = Audit(action="enroll", success=1, realm=self.realm1a)
        audit.date = date - timedelta(minutes=5)
        audit.save()
        audit = Audit(action="enable", success=1, realm=self.realm1a)
        audit.date = date - three_days
        audit.save()
        audit = Audit(action="enroll", success=1, realm=self.realm2b)
        audit.date = date - timedelta(minutes=2)
        audit.save()
        audit = Audit(action="enable", success=1, realm=self.realm2b)
        audit.date = date - three_days
        audit.save()
        audit = Audit(action="enroll", success=1, realm=self.realm2b)
        audit.date = date
        audit.save()

        # check that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(5, json_response.get("result").get("value").get("count"))

        # Set audit age policy
        set_policy("audit_age", scope=SCOPE.ADMIN, action=f"{PolicyAction.AUDIT},{PolicyAction.AUDIT_AGE}=1d")
        # Now we should only get audit entries within the last day
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            audit_result = json_response.get("result").get("value")
            self.assertEqual(4, audit_result.get("count"))
            for audit in audit_result.get("auditdata"):
                self.assertNotEqual("enable", audit.get("action"), audit)

        # Set audit policy for helpdesk
        set_policy("audit_age", scope=SCOPE.ADMIN, action=f"{PolicyAction.AUDIT},{PolicyAction.AUDIT_AGE}=1d",
                   realm=self.realm2b)
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            audit_result = json_response.get("result").get("value")
            self.assertEqual(4, audit_result.get("count"))
            for audit in audit_result.get("auditdata"):
                self.assertNotEqual("enable", audit.get("action"), audit)
                self.assertNotEqual(self.realm1a, audit.get("realm"), audit)

        delete_policy("audit_age")

    def test_06_audit_pagination(self):
        self.setUp_user_realms()
        # prepare some log entries
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

        # Query API with page size parameter
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={'page_size': 3},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), json_response)
            self.assertGreaterEqual(json_response.get("result").get("value").get(
                "count"), 6,  json_response)
            self.assertEqual(3, len(json_response.get("result").get("value").get(
                "auditdata")), json_response)
            self.assertEqual(1, json_response.get("result").get("value").get(
                "current"), json_response)
            self.assertEqual(2, json_response.get("result").get("value").get(
                "next"), json_response)

        # Query API with negative page size parameter
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={'page_size': -5},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), json_response)
            self.assertGreaterEqual(json_response.get("result").get("value").get(
                "count"), 6,  json_response)
            self.assertGreaterEqual(len(json_response.get("result").get("value").get(
                "auditdata")), 5, json_response)
            self.assertEqual(1, json_response.get("result").get("value").get(
                "current"), json_response)

        # Query API with negative page parameter
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={'page': -1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), json_response)
            self.assertGreaterEqual(json_response.get("result").get("value").get(
                "count"), 6,  json_response)
            self.assertGreaterEqual(len(json_response.get("result").get("value").get(
                "auditdata")), 5, json_response)
            self.assertEqual(1, json_response.get("result").get("value").get(
                "current"), json_response)

    def test_07_search_negation_matches_unset_columns(self):
        Audit.query.delete()
        Audit(action="enroll", success=1, authentication=AUTH_RESPONSE.CHALLENGE).save()
        Audit(action="enroll", success=1, authentication=AUTH_RESPONSE.REJECT).save()
        Audit(action="enroll", success=1).save()
        # entries written before the column was added contain NULL, not ""
        Audit.query.filter(Audit.authentication == "").update({Audit.authentication: None})
        db.session.commit()

        # the entry with the unset column is not dropped by the negation
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"action": "enroll",
                                                         "authentication": f"!{AUTH_RESPONSE.CHALLENGE}"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result").get("value")
            self.assertEqual(2, value.get("count"), value)
            self.assertIn(None, [entry.get("authentication") for entry in value.get("auditdata")], value)

        # a positive filter still does not match it
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"action": "enroll",
                                                         "authentication": AUTH_RESPONSE.CHALLENGE},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json.get("result").get("value")
            self.assertEqual(1, value.get("count"), value)

    def test_08_an_audit_policy_is_read_with_its_wildcard_and_exclusions(self):
        self.setUp_user_realms()
        Audit.query.delete()
        for realm in (self.realm1a, self.realm1a, self.realm2b):
            Audit(action="enroll", success=1, realm=realm).save()

        def enroll_realms() -> list[str]:
            with self.app.test_request_context('/audit/', method='GET', query_string={"action": "enroll"},
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            return sorted(entry["realm"] for entry in res.json["result"]["value"]["auditdata"])

        every_entry = [self.realm1a, self.realm1a, self.realm2b]
        try:
            set_policy("audit_realms", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT, realm="*")
            self.assertEqual(every_entry, enroll_realms())

            set_policy("audit_realms", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT, realm=f"*,!{self.realm2b}")
            self.assertEqual([self.realm1a, self.realm1a], enroll_realms())

            # A policy with no target scope at all grants every realm, whatever another policy names.
            set_policy("audit_every_realm", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT)
            self.assertEqual(every_entry, enroll_realms())
            delete_policy("audit_every_realm")

            # A policy scoped by user grants no realm, since the audit log can not show just that user: next to
            # another policy it adds nothing, and on its own it leaves the admin's own entries only.
            set_policy("audit_one_user", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT, user="cornelius")
            self.assertEqual([self.realm1a, self.realm1a], enroll_realms())
            for realm in ("*", self.realm2b):
                set_policy("audit_one_user", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT, user="cornelius",
                           realm=realm)
                self.assertEqual([self.realm1a, self.realm1a], enroll_realms(), realm)
            delete_policy("audit_realms")
            for realm in (None, "*", self.realm2b):
                set_policy("audit_one_user", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT, user="cornelius",
                           realm=realm)
                self.assertEqual([], enroll_realms(), realm)
            delete_policy("audit_one_user")

            # A realm field that matches no realm grants no realm.
            set_policy("audit_realms", scope=SCOPE.ADMIN, action=PolicyAction.AUDIT, realm=f"!{self.realm2b}")
            self.assertEqual([], enroll_realms())
        finally:
            for name in ("audit_realms", "audit_every_realm", "audit_one_user"):
                with suppress(ResourceNotFoundError):
                    delete_policy(name)

    def test_09_search_by_day_matches_that_day_only(self):
        Audit.query.delete()
        for day, hour in ((24, 23), (25, 0), (25, 23), (26, 0)):
            Audit(action="enroll", success=1, date=datetime(2026, 9, day, hour, 30)).save()
        # 2024-12-30 lies in ISO week 1 of 2025, so the day is only found under its calendar year.
        Audit(action="enroll", success=1, date=datetime(2024, 12, 30, 12, 0)).save()

        for day, expected in (("2026-09-25", ["2026-09-25", "2026-09-25"]),
                              ("2024-12-30", ["2024-12-30"]),
                              ("2025-12-30", [])):
            with self.app.test_request_context('/audit/',
                                               method='GET',
                                               query_string={"action": "enroll", "date": f"*{day}*"},
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                value = res.json.get("result").get("value")
                self.assertEqual(expected, sorted(entry.get("date")[:10] for entry in value.get("auditdata")), day)

    # The range of the time range tests is 10:00 to 12:00 UTC on 2026-03-10, which is 18:00 to 20:00 in Asia/Shanghai
    # (UTC+8, no daylight saving), the zone of non_utc_time_zone().
    RANGE_ENTRIES_IN_RANGE = {"range_marked_at_start", "range_marked_inside",
                              "range_unmarked_inside", "range_unmarked_at_end"}

    def _insert_entries_around_a_time_range(self):
        # Entries marked with entry_version 2 are written in UTC, unmarked ones in local time of the server. Each
        # kind has one entry that only lies in the range if it is compared on the clock of the other kind.
        Audit.query.delete()
        entries = [
            # marked, naive UTC
            ("range_marked_before", datetime(2026, 3, 10, 9, 59), 2),
            ("range_marked_at_start", datetime(2026, 3, 10, 10, 0), 2),
            ("range_marked_inside", datetime(2026, 3, 10, 11, 0), 2),
            ("range_marked_after", datetime(2026, 3, 10, 12, 1), 2),
            # 19:00 UTC lies in the range only when read as local time
            ("range_marked_at_local_time", datetime(2026, 3, 10, 19, 0), 2),
            # unmarked, naive local time of Asia/Shanghai
            ("range_unmarked_before", datetime(2026, 3, 10, 17, 0), None),
            ("range_unmarked_inside", datetime(2026, 3, 10, 19, 30), None),
            ("range_unmarked_at_end", datetime(2026, 3, 10, 20, 0), None),
            # 11:00 local time is 03:00 UTC, it lies in the range only when read as UTC
            ("range_unmarked_at_utc_time", datetime(2026, 3, 10, 11, 0), None)]
        db.session.execute(Audit.__table__.insert(),
                           [{"action": action, "date": date, "entry_version": entry_version, "success": 1,
                             "signature": ""}
                            for action, date, entry_version in entries])
        db.session.commit()

    # Long requests around the same range: each one starts 10 minutes before it is written. Each kind has one
    # request that only lies in the range if its start is compared on the clock of the other kind.
    LONG_REQUESTS_STARTED_IN_RANGE = {"range_long_marked_inside", "range_long_unmarked_inside"}

    def _insert_long_requests_around_a_time_range(self):
        Audit.query.delete()
        entries = [
            # marked, naive UTC. Started before the range, written in it
            ("range_long_marked_before", datetime(2026, 3, 10, 9, 55), 2),
            # started in the range, written after it
            ("range_long_marked_inside", datetime(2026, 3, 10, 11, 55), 2),
            ("range_long_marked_at_local_time", datetime(2026, 3, 10, 19, 0), 2),
            # unmarked, naive local time of Asia/Shanghai
            ("range_long_unmarked_before", datetime(2026, 3, 10, 17, 55), None),
            ("range_long_unmarked_inside", datetime(2026, 3, 10, 19, 55), None),
            ("range_long_unmarked_at_utc_time", datetime(2026, 3, 10, 11, 0), None)]
        db.session.execute(Audit.__table__.insert(),
                           [{"action": action, "startdate": startdate, "date": startdate + timedelta(minutes=10),
                             "entry_version": entry_version, "success": 1, "signature": ""}
                            for action, startdate, entry_version in entries])
        db.session.commit()

    def _search_actions(self, query_string: dict) -> set[str]:
        with self.app.test_request_context('/audit/', method='GET',
                                           query_string={"action": "range_*", "page_size": 50, **query_string},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        return {entry.get("action") for entry in res.json["result"]["value"]["auditdata"]}

    def test_10_search_by_date_interval_on_mixed_entries(self):
        with non_utc_time_zone():
            self._insert_entries_around_a_time_range()

            # Both ends are inclusive. A bound is given with any offset, a bound without one is UTC.
            for interval in ("2026-03-10T18:00:00+08:00/2026-03-10T12:00:00Z",
                             "2026-03-10T10:00:00/2026-03-10T07:00:00-05:00"):
                self.assertEqual(self.RANGE_ENTRIES_IN_RANGE, self._search_actions({"date": interval}), interval)

            # An open end limits only the other side
            self.assertEqual({"range_marked_inside", "range_marked_after", "range_marked_at_local_time",
                              "range_unmarked_inside", "range_unmarked_at_end"},
                             self._search_actions({"date": "2026-03-10T11:00:00+00:00/"}))
            self.assertEqual({"range_marked_before", "range_marked_at_start", "range_unmarked_before",
                              "range_unmarked_at_utc_time"},
                             self._search_actions({"date": "/2026-03-10T10:00:00+00:00"}))

    def test_11_csv_download_by_startdate_interval(self):
        with non_utc_time_zone():
            self._insert_long_requests_around_a_time_range()
            with self.app.test_request_context('/audit/audit.csv', method='GET',
                                               query_string={"action": "range_*",
                                                             "startdate": "2026-03-10T18:00:00+08:00/"
                                                                          "2026-03-10T12:00:00Z"},
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                rows = list(csv.reader(io.StringIO(res.get_data(as_text=True))))
        actions = {cell for row in rows for cell in row if cell.startswith("range_")}
        self.assertEqual(self.LONG_REQUESTS_STARTED_IN_RANGE, actions)

        with self.app.test_request_context('/audit/audit.csv', method='GET', query_string={"startdate": "foo/"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(400, res.status_code, res)
        self.assertEqual(905, res.json["result"]["error"]["code"], res.json)
        self.assertIn("Invalid ISO 8601 timestamp for startdate", res.json["result"]["error"]["message"])

    def test_12_search_by_startdate_interval_on_mixed_entries(self):
        with non_utc_time_zone():
            self._insert_long_requests_around_a_time_range()

            # A bound is given with any offset, without one (UTC) or in the readable form with spaces
            for interval in ("2026-03-10T10:00:00Z/2026-03-10T12:00:00Z",
                             "2026-03-10T18:00:00+08:00/2026-03-10T07:00:00-05:00",
                             "2026-03-10T10:00:00/2026-03-10T12:00:00",
                             "2026-03-10 18:00:00 +08:00/2026-03-10 20:00:00 +08:00"):
                self.assertEqual(self.LONG_REQUESTS_STARTED_IN_RANGE,
                                 self._search_actions({"startdate": interval}), interval)

            # An open end limits only the other side
            self.assertEqual({"range_long_marked_inside", "range_long_marked_at_local_time",
                              "range_long_unmarked_inside"},
                             self._search_actions({"startdate": "2026-03-10T10:00:00Z/"}))
            self.assertEqual({"range_long_marked_before", "range_long_unmarked_before",
                              "range_long_unmarked_at_utc_time"},
                             self._search_actions({"startdate": "/2026-03-10T10:00:00Z"}))

    def test_13_invalid_time_interval_is_refused(self):
        for key in ("startdate", "date"):
            for value in ("foo/2026-03-10T12:00:00Z", "!2026-03-10/", "*/2026-03-10T12:00:00Z", "a/b/c"):
                with self.app.test_request_context('/audit/', method='GET', query_string={key: value},
                                                   headers={'Authorization': self.at}):
                    res = self.app.full_dispatch_request()
                self.assertEqual(400, res.status_code, (key, value, res.json))
                self.assertEqual(905, res.json["result"]["error"]["code"], res.json)
                if value.startswith("foo"):
                    self.assertIn(f"Invalid ISO 8601 timestamp for {key}", res.json["result"]["error"]["message"])

    def test_14_end_bound_includes_its_whole_second(self):
        with non_utc_time_zone():
            Audit.query.delete()
            entries = [("range_marked_in_last_second", datetime(2026, 3, 10, 12, 0, 0, 400000), 2),
                       # 20:00:00.400 in Asia/Shanghai is 12:00:00.400 UTC
                       ("range_unmarked_in_last_second", datetime(2026, 3, 10, 20, 0, 0, 400000), None),
                       ("range_marked_in_next_second", datetime(2026, 3, 10, 12, 0, 1), 2)]
            db.session.execute(Audit.__table__.insert(),
                               [{"action": action, "startdate": startdate, "date": startdate,
                                 "entry_version": entry_version, "success": 1, "signature": ""}
                                for action, startdate, entry_version in entries])
            db.session.commit()

            # An end in whole seconds includes its whole second, an end with a fraction of a second is the bound
            self.assertEqual({"range_marked_in_last_second", "range_unmarked_in_last_second"},
                             self._search_actions({"startdate": "/2026-03-10T12:00:00Z"}))
            self.assertEqual(set(), self._search_actions({"startdate": "/2026-03-10T12:00:00.300Z"}))

    def test_15_start_time_and_end_time_are_no_filters(self):
        with non_utc_time_zone():
            self._insert_entries_around_a_time_range()
            every_entry = {"range_marked_before", "range_marked_at_start", "range_marked_inside",
                           "range_marked_after", "range_marked_at_local_time", "range_unmarked_before",
                           "range_unmarked_inside", "range_unmarked_at_end", "range_unmarked_at_utc_time"}
            self.assertEqual(every_entry, self._search_actions({"start_time": "2026-03-10T11:00:00+00:00",
                                                                "end_time": "2026-03-10T11:30:00+00:00"}))
            self.assertEqual(every_entry, self._search_actions({"start_time": "foo"}))
