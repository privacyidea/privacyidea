# SPDX-FileCopyrightText: 2015 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
from contextlib import contextmanager, suppress
from datetime import datetime, timedelta, timezone

import mock

from privacyidea.lib.auditmodules.base import Audit as BaseAudit
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.utils import AUTH_RESPONSE
from privacyidea.models import Audit, db
from .base import MyApiTestCase

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
                                           data={'username': 'selfservice@{0!s}'.format(self.realm1a),
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
        date = datetime.now(timezone.utc)
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

    def test_10_a_user_sees_only_their_own_entries_whatever_their_login(self):
        realm = "operatorrealm"
        resolver = "operatorresolver"
        save_resolver({"resolver": resolver, "type": "passwdresolver",
                       "fileName": "tests/testdata/passwd-search-operator-logins"})
        set_realm(realm, [{"name": resolver}])
        set_policy("audit_operator", scope=SCOPE.USER, action=PolicyAction.AUDIT, realm=realm)
        Audit.query.delete()
        logins = ["cornelius", "!cornelius", "corn*", "*"]
        for login in logins + ["cornerstone", None]:
            Audit(action="enroll", success=1, user=login, resolver=resolver, realm=realm).save()
        try:
            for login in logins:
                with self.subTest(login=login):
                    with self.app.test_request_context('/auth', method='POST',
                                                       data={"username": f"{login}@{realm}", "password": "test"}):
                        res = self.app.full_dispatch_request()
                    self.assertEqual(200, res.status_code, res.json)
                    user_authorization = res.json["result"]["value"]["token"]

                    with self.app.test_request_context('/audit/', method='GET', query_string={"action": "enroll"},
                                                       headers={'Authorization': user_authorization}):
                        res = self.app.full_dispatch_request()
                    self.assertEqual(200, res.status_code, res.json)
                    self.assertListEqual([login],
                                         [entry["user"] for entry in res.json["result"]["value"]["auditdata"]])
        finally:
            delete_policy("audit_operator")
            delete_realm(realm)
            delete_resolver(resolver)

    def test_11_the_realms_of_an_administrator_come_from_their_audit_policies_only(self):
        # A search key named like the internal list of allowed realms neither widens nor replaces the realms of the
        # policies, in the search and in the download
        self.setUp_user_realms()
        Audit.query.delete()
        Audit(action="enroll", success=1, realm=self.realm1a).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm=self.realm2b).save()
        Audit(action="enroll", success=1, realm="").save()
        set_policy("audit_realm1a", scope=SCOPE.ADMIN, realm=self.realm1a,
                   action=f"{PolicyAction.AUDIT}, {PolicyAction.AUDIT_DOWNLOAD}")
        try:
            for requested_realms in ([self.realm2b], [self.realm1a, self.realm2b, ""]):
                body = {"action": "enroll", "allowed_audit_realm": requested_realms}
                with self.subTest(requested_realms=requested_realms):
                    with self.app.test_request_context('/audit/', method='GET', json=body,
                                                       headers={'Authorization': self.at}):
                        res = self.app.full_dispatch_request()
                    self.assertEqual(200, res.status_code, res.json)
                    self.assertListEqual([self.realm1a],
                                         [entry["realm"] for entry in res.json["result"]["value"]["auditdata"]])

                    with self.app.test_request_context('/audit/audit.csv', method='GET', json=body,
                                                       headers={'Authorization': self.at}):
                        res = self.app.full_dispatch_request()
                    self.assertEqual(200, res.status_code)
                    rows = [row for row in csv.reader(io.StringIO(res.get_data(as_text=True))) if "enroll" in row]
                    self.assertEqual(1, len(rows), rows)
                    self.assertIn(self.realm1a, rows[0])
        finally:
            delete_policy("audit_realm1a")


class AuditDownloadRealmTestCase(MyApiTestCase):
    """
    The audit download contains the entries of the realms that both the auditlog_download and the auditlog policies
    of the administrator grant, and the administrator's own entries.
    """
    realm1 = "dlrealm1"
    realm2 = "dlrealm2"
    policy_names = ["dl_download", "dl_view"]
    marks = ["MARK-R1", "MARK-R2", "MARK-NOREALM"]

    def setUp(self) -> None:
        super().setUp()
        save_resolver({"resolver": self.resolvername1, "type": "passwdresolver", "fileName": PWFILE})
        set_realm(self.realm1, [{"name": self.resolvername1}])
        set_realm(self.realm2, [{"name": self.resolvername1}])
        # "adminrealm" is a superuser realm of the test configuration: selfservice@adminrealm is a helpdesk admin
        set_realm("adminrealm", [{"name": self.resolvername1}])
        Audit.query.delete()
        for _ in range(2):
            Audit(action="MARK-R1", success=1, realm=self.realm1).save()
        for _ in range(3):
            Audit(action="MARK-R2", success=1, realm=self.realm2).save()
        Audit(action="MARK-NOREALM", success=1, realm="").save()

    def tearDown(self) -> None:
        for name in self.policy_names:
            with suppress(ResourceNotFoundError):
                delete_policy(name)
        for realm in [self.realm1, self.realm2, "adminrealm"]:
            delete_realm(realm)
        super().tearDown()

    def helpdesk_authorization(self) -> str:
        with self.app.test_request_context("/auth", method="POST",
                                           data={"username": "selfservice@adminrealm", "password": "test"}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        return res.json["result"]["value"]["token"]

    def download(self, authorization: str, query: dict | None = None) -> dict[str, int]:
        with self.app.test_request_context("/audit/audit.csv", method="GET", query_string=query or {},
                                           headers={"Authorization": authorization}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code)
        body = res.get_data(as_text=True)
        return {mark: body.count(mark) for mark in self.marks}

    def test_01_download_right_without_view_right(self):
        # Without a matching auditlog policy only the administrator's own entries are downloaded
        set_policy("dl_download", scope=SCOPE.ADMIN, adminrealm="adminrealm", realm=self.realm1,
                   action=PolicyAction.AUDIT_DOWNLOAD)
        authorization = self.helpdesk_authorization()
        self.assertDictEqual({"MARK-R1": 0, "MARK-R2": 0, "MARK-NOREALM": 0}, self.download(authorization))
        self.assertDictEqual({"MARK-R1": 0, "MARK-R2": 0, "MARK-NOREALM": 0},
                             self.download(authorization, {"action": "MARK-R2"}))

    def test_02_download_and_view_rights_for_different_realms(self):
        set_policy("dl_download", scope=SCOPE.ADMIN, adminrealm="adminrealm", realm=self.realm1,
                   action=PolicyAction.AUDIT_DOWNLOAD)
        set_policy("dl_view", scope=SCOPE.ADMIN, adminrealm="adminrealm", realm=self.realm2,
                   action=PolicyAction.AUDIT)
        self.assertDictEqual({"MARK-R1": 0, "MARK-R2": 0, "MARK-NOREALM": 0},
                             self.download(self.helpdesk_authorization()))

    def test_03_local_admin_with_download_right_only(self):
        set_policy("dl_download", scope=SCOPE.ADMIN, realm=self.realm1, action=PolicyAction.AUDIT_DOWNLOAD)
        self.assertDictEqual({"MARK-R1": 0, "MARK-R2": 0, "MARK-NOREALM": 0}, self.download(self.at))

    def test_04_view_right_for_every_realm_and_download_right_for_one(self):
        set_policy("dl_download", scope=SCOPE.ADMIN, adminrealm="adminrealm", realm=self.realm1,
                   action=PolicyAction.AUDIT_DOWNLOAD)
        set_policy("dl_view", scope=SCOPE.ADMIN, adminrealm="adminrealm", action=PolicyAction.AUDIT)
        self.assertDictEqual({"MARK-R1": 2, "MARK-R2": 0, "MARK-NOREALM": 0},
                             self.download(self.helpdesk_authorization()))

    def test_05_download_and_view_rights_for_the_same_realm(self):
        set_policy("dl_download", scope=SCOPE.ADMIN, adminrealm="adminrealm", realm=self.realm1,
                   action=PolicyAction.AUDIT_DOWNLOAD)
        set_policy("dl_view", scope=SCOPE.ADMIN, adminrealm="adminrealm", realm=self.realm1,
                   action=PolicyAction.AUDIT)
        authorization = self.helpdesk_authorization()
        self.assertDictEqual({"MARK-R1": 2, "MARK-R2": 0, "MARK-NOREALM": 0}, self.download(authorization))
        # A download right without a realm: the realms of the view right
        set_policy("dl_download", scope=SCOPE.ADMIN, adminrealm="adminrealm", realm="",
                   action=PolicyAction.AUDIT_DOWNLOAD)
        self.assertDictEqual({"MARK-R1": 2, "MARK-R2": 0, "MARK-NOREALM": 0}, self.download(authorization))
        # A realm parameter only filters inside the granted realms
        self.assertDictEqual({"MARK-R1": 0, "MARK-R2": 0, "MARK-NOREALM": 0},
                             self.download(authorization, {"realm": self.realm2}))

    def test_06_no_admin_policy_at_all(self):
        self.assertDictEqual({"MARK-R1": 2, "MARK-R2": 3, "MARK-NOREALM": 1}, self.download(self.at))
