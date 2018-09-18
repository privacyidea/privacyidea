import json
from .base import MyTestCase
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from privacyidea.models import Audit
import datetime
from dateutil.parser import parse as parse_time_string
from dateutil.tz import tzlocal
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm

PWFILE = "tests/testdata/passwords"
POLICYFILE = "tests/testdata/policy.cfg"
POLICYEMPTY = "tests/testdata/policy_empty_file.cfg"

class APIAuditTestCase(MyTestCase):

    def test_00_get_audit(self):
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertTrue(json_response.get("result").get("value").get(
                "current") == 1, res)

    def test_01_get_statistics(self):
        with self.app.test_request_context('/audit/statistics',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertTrue("serial_plot" in json_response.get(
                "result").get("value"), json_response.get("result"))

        start = datetime.datetime.now(tzlocal()) - datetime.timedelta(days=10)
        start_str = start.strftime("%Y-%m-%dT%H:%M%Z")
        # We need to reparse it, to get rid of the seconds and milliseconds
        start = parse_time_string(start_str)
        with self.app.test_request_context('/audit/statistics',
                                           method='GET',
                                           data={"start": start_str},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertTrue("serial_plot" in json_response.get(
                "result").get("value"), json_response.get("result"))
            d = parse_time_string(json_response.get("result").get("value").get("time_start"))
            self.assertEqual(d, start)

        end = datetime.datetime.now(tzlocal()) - datetime.timedelta(days=10)
        end_str = end.strftime("%Y-%m-%dT%H:%M%Z")
        # We need to reparse it, to get rid of the seconds and milliseconds
        end = parse_time_string(end_str)
        with self.app.test_request_context('/audit/statistics',
                                           method='GET',
                                           data={"end": end_str},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertTrue("serial_plot" in json_response.get(
                "result").get("value"), json_response.get("result"))
            d = parse_time_string(json_response.get("result").get("value").get("time_end"))
            self.assertEqual(d, end)

    def test_02_get_allowed_audit_realm(self):
        # Check that an administrator is only allowed to see log entries of
        # the defined realms.
        # fill some audit entries
        Audit(action="enroll", success=1, realm="realm1A").save()
        Audit(action="enroll", success=1, realm="realm1A").save()
        Audit(action="enroll", success=1, realm="realm2B").save()
        Audit(action="enroll", success=1, realm="realm2B").save()
        Audit(action="enroll", success=1, realm="realm2B").save()

        # check, that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": "realm1A"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 2)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": "realm2B"},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 3)

        # set policy for audit realms
        set_policy("audit01", scope=SCOPE.ADMIN, action=ACTION.AUDIT,
                   realm="realm1A")

        # check, that we only see allowed audit realms
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 2 + 1)

        # delete policy
        delete_policy("audit01")

    def test_03_get_allowed_audit_realm(self):
        # Check than an internal admin is allowed to see all realms
        # A helpdesk user in "adminrealm" is only allowerd to see realm1A
        Audit(action="enroll", success=1, realm="realm1A").save()
        Audit(action="enroll", success=1, realm="realm1A").save()
        Audit(action="enroll", success=1, realm="realm2B").save()
        Audit(action="enroll", success=1, realm="realm2B").save()
        Audit(action="enroll", success=1, realm="realm2B").save()

        # check, that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": "realm1A"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 5)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": "realm2B"},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 7)

        # set policy: helpdesk users in adminrealm are only allowed to
        # view "realm1A".
        set_policy("audit01", scope=SCOPE.ADMIN, action=ACTION.AUDIT,
                   adminrealm="adminrealm", realm="realm1A")
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
            json_response = json.loads(res.data)
            value = json_response.get("result").get("value")
            # Helpdesk user is allowed to view the audit log.
            self.assertTrue("auditlog" in value.get("rights"))
            helpdesk_authorization = value.get("token")

        # check, that we only see allowed audit realms
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': helpdesk_authorization}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            count = json_response.get("result").get("value").get("count")
            auditdata = json_response.get("result").get("value").get("auditdata")
            self.assertEqual(count, 6)
            # All entries are in realm1A!
            for ad  in auditdata:
                self.assertEqual(ad.get("realm"), "realm1A")

        # Now check, that the testadmin (self.at) see all entries!
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            count = json_response.get("result").get("value").get("count")
            auditdata = json_response.get("result").get("value").get("auditdata")
            self.assertEqual(count, 25)

        # delete policy
        delete_policy("audit01")
        delete_policy("audit02")

