import json
from .base import MyTestCase
from privacyidea.lib.error import (ParameterError, ConfigAdminError)
from urllib import urlencode

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


    #def test_01_download_audit(self):
    #    with self.app.test_request_context('/audit/auditfile.csv',
    #                                       method='GET',
    #                                       headers={'Authorization': self.at}):
    #        res = self.app.full_dispatch_request()
    #        self.assertTrue(res.status_code == 200, res)
    #        self.assertTrue(res.mimetype == "text/csv", res.mimetype)
    #        self.assertTrue(res.stream)
