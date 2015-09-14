import json
from .base import MyTestCase

HOSTSFILE = "tests/testdata/hosts"

class APIMachineResolverTestCase(MyTestCase):

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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        with self.app.test_request_context('/machineresolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            # The value is empty
            self.assertTrue(result["value"] == {}, result)

        # this will fetch all resolvers
        with self.app.test_request_context('/machineresolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue("machineresolver1" in value, value)

        # get a resolver name
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("machineresolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["machineresolver1"][
                "data"])

        # delete the resolver
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            print(res.data)
            result = json.loads(res.data).get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        # delete a non existing resolver
        with self.app.test_request_context('/machineresolver/xycswwf',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            print(res.data)
            result = json.loads(res.data).get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            # Trying to delete a non existing resolver returns -1
            self.assertTrue(result["value"] == -1, result)


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
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        with self.app.test_request_context('/machineresolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("machineresolver2" in result["value"], result)
            self.assertTrue("LDAPURI" in result["value"]["machineresolver2"][
                "data"])

        # delete the resolver
        with self.app.test_request_context('/machineresolver/machineresolver2',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            print(res.data)
            result = json.loads(res.data).get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)
