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
            sshtokenoptions = value.get("ssh").get("options")
            lukstokenoptions = value.get("luks").get("options")
            offlinetokenoptions = value.get("offline").get("options")
            # Check the correct token types
            self.assertIn("sshkey", sshtokenoptions)
            self.assertIn("totp", lukstokenoptions)
            self.assertIn("hotp", offlinetokenoptions)
            self.assertIn("webauthn", offlinetokenoptions)
            self.assertIn("service_id", sshtokenoptions.get("sshkey"))
            self.assertIn("user", sshtokenoptions.get("sshkey"))
            self.assertEqual("str", sshtokenoptions.get("sshkey").get("service_id").get("type"))
            self.assertEqual("str", sshtokenoptions.get("sshkey").get("user").get("type"))
