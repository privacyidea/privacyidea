import json
from .base import MyApiTestCase
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

class APIAuditTestCase(MyApiTestCase):

    def test_00_get_audit(self):
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertTrue(json_response.get("result").get("value").get(
                "current") == 1, res)

    def test_02_get_allowed_audit_realm(self):
        # Check that an administrator is only allowed to see log entries of
        # the defined realms.
        # fill some audit entries
        Audit(action="enroll", success=1, realm="realm1a").save()
        Audit(action="enroll", success=1, realm="realm1a").save()
        Audit(action="enroll", success=1, realm="realm2b").save()
        Audit(action="enroll", success=1, realm="realm2b").save()
        Audit(action="enroll", success=1, realm="realm2b").save()

        # check, that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": "realm1a"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 2)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 8)
            audit_list = json_response.get("result").get("value").get("auditdata")
            audit_actions = [a for a in audit_list if a.get("action") == "GET /audit/"]
            self.assertEqual(len(audit_actions), 2)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": "realm2b"},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 3)

        # set policy for audit realms
        set_policy("audit01", scope=SCOPE.ADMIN, action=ACTION.AUDIT,
                   realm="realm1a")

        # check, that we only see allowed audit realms
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            audit_list = json_response.get("result").get("value").get("auditdata")
            audit_realms = [a for a in audit_list if a.get("realm") == "realm1a"]
            self.assertEqual(len(audit_realms), 3)
            self.assertEqual(json_response.get("result").get("value").get("count"), 3)

        # delete policy
        delete_policy("audit01")

    def test_03_get_allowed_audit_realm(self):
        # Check than an internal admin is allowed to see all realms
        # A helpdesk user in "adminrealm" is only allowerd to see realm1A
        Audit(action="enroll", success=1, realm="realm1a").save()
        Audit(action="enroll", success=1, realm="realm1a").save()
        Audit(action="enroll", success=1, realm="realm2b").save()
        Audit(action="enroll", success=1, realm="realm2b").save()
        Audit(action="enroll", success=1, realm="realm2b").save()

        # check, that we see all audit entries
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": "realm1a"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 5)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={"realm": "realm2b"},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 7)

        # set policy: helpdesk users in adminrealm are only allowed to
        # view "realm1A".
        set_policy("audit01", scope=SCOPE.ADMIN, action=ACTION.AUDIT,
                   adminrealm="adminrealm", realm="realm1a")
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
            json_response = json.loads(res.data.decode('utf8'))
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
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            count = json_response.get("result").get("value").get("count")
            auditdata = json_response.get("result").get("value").get("auditdata")
            self.assertEqual(count, 6)
            # All entries are in realm1A!
            for ad  in auditdata:
                self.assertEqual(ad.get("realm"), "realm1a")

        # Now check, that the testadmin (self.at) sees all entries!
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data.decode('utf8'))
            self.assertTrue(json_response.get("result").get("status"), res)
            # We now have 3 entries, as we added one by the search in line #43
            count = json_response.get("result").get("value").get("count")
            auditdata = json_response.get("result").get("value").get("auditdata")
            self.assertEqual(count, 20)

        # delete policy
        delete_policy("audit01")
        delete_policy("audit02")

