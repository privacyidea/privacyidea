"""
This test case test the REST API
api/applications.py
"""

import json
from .base import MyApiTestCase


class APIApplicationsResolverTestCase(MyApiTestCase):

    def test_get_applications(self):
        with self.app.test_request_context('/application/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            value = result.get("value")
            self.assertIn("ssh", value)
            self.assertIn("luks", value)
            sshopts = value.get("ssh").get("options")
            self.assertIn("service_id", sshopts)
            self.assertIn("user", sshopts)
            self.assertEqual("str", sshopts.get("service_id").get("type"))
            self.assertEqual("str", sshopts.get("user").get("type"))
