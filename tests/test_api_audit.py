"""
This test file tests the api/audit.py
"""
from .base import MyTestCase
import json

class APIAuditTestCase(MyTestCase):
       
    def test_00_audit(self):
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"status": true' in res.data, res.data)

        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"status": true' in res.data, res.data)
            audit_log = json.loads(res.data).get("result").get("value")
            self.assertTrue(len(audit_log) >= 1, len(audit_log))

"""
    def test_01_search(self):
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string=urlencode({
                                               "assigned": True}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"status": true' in res.data, res.data)
            audit_log = json.loads(res.data).get("result").get("value")
"""
