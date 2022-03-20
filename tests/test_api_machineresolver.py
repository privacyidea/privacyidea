import json
from .base import MyApiTestCase

HOSTSFILE = "tests/testdata/hosts"

class APIMachineResolverTestCase(MyApiTestCase):

    # Resolvers
    def test_01_pretestresolver(self):
        param = {'filename': HOSTSFILE,
                 'type': 'hosts'}
        with self.app.test_request_context('/machineresolver/test',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"), result)
            self.assertEqual("Not Implemented", detail.get("description"))

    def test_02_resolvers_hosts(self):

        # create a machine resolver
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           data={'type': 'hosts',
                                                 'filename': HOSTSFILE},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        with self.app.test_request_context('/machineresolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("machineresolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["machineresolver1"][
                "data"])

        # Get a non existing resolver
        with self.app.test_request_context('/machineresolver/unknown',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            # The value is empty
            self.assertTrue(result["value"] == {}, result)

        # this will fetch all resolvers
        with self.app.test_request_context('/machineresolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue("machineresolver1" in value, value)

        # get a resolver name
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("machineresolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["machineresolver1"][
                "data"])


        # get a resolver name
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("machineresolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["machineresolver1"][
                "data"])

        # delete the resolver
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        # delete a non existing resolver
        with self.app.test_request_context('/machineresolver/xycswwf',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 404)
            self.assertFalse(result["status"])

    def test_03_resolvers_ldap(self):

        # create a machine resolver
        with self.app.test_request_context('/machineresolver/machineresolver2',
                                           data={'type': 'ldap',
                                                 'LDAPURI': "ldap://1.2.3.4",
                                                 'LDAPBASE': "dc=ex,dc=com"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertGreaterEqual(result["value"], 1, result)
            mr_id = result["value"]

        with self.app.test_request_context('/machineresolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("machineresolver2" in result["value"], result)
            self.assertTrue("LDAPURI" in result["value"]["machineresolver2"][
                "data"])

        # delete the resolver
        with self.app.test_request_context('/machineresolver/machineresolver2',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            self.assertEqual(result["value"], mr_id, result)
