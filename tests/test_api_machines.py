from .base import MyTestCase
import json

HOSTSFILE = "tests/testdata/hosts"


class APIMachinesTestCase(MyTestCase):

    def test_00_create_machine_resolver(self):
        # create a machine resolver
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           data={'type': 'hosts',
                                                 'filename': HOSTSFILE},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

    def test_01_get_machine_list(self):
        with self.app.test_request_context('/machine/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertEqual(len(result["value"]), 4)
            self.assertTrue("hostname" in result["value"][0].keys())
            self.assertTrue("id" in result["value"][0].keys())
            self.assertTrue("ip" in result["value"][0].keys())
            self.assertTrue("resolver_name" in result["value"][0].keys())
