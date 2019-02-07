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
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data).get("detail")
            value = result.get("value")
            self.assertTrue("ssh" in value)
            self.assertTrue("luks" in value)
            self.assertTrue(value["ssh"]["options"]["optional"] == ["user"])
