"""
This testcase is used to test the REST API  in api/caconnector.py
to create, update, delete CA connectors.
"""
from .base import MyApiTestCase
import json
from privacyidea.lib.caconnector import get_caconnector_list, save_caconnector


class CAConnectorTestCase(MyApiTestCase):

    def test_01_fail_without_auth(self):
        # creation fails without auth
        with self.app.test_request_context('/caconnector/con1',
                                           data={'type': 'localca'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)

    def test_02_create_ca_connector(self):
        # create a CA connector
        with self.app.test_request_context('/caconnector/con1',
                                           data={'type': 'local'},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        ca_list = get_caconnector_list()
        self.assertEqual(len(ca_list), 1)
        self.assertEqual(ca_list[0].get("connectorname"), "con1")

    def test_03_update_ca_connector(self):
        with self.app.test_request_context('/caconnector/con1',
                                           data={'type': 'local',
                                                 'cakey': '/etc/key.pem',
                                                 'cacert': '/etc/cert.pem'},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        ca_list = get_caconnector_list()
        self.assertEqual(len(ca_list), 1)
        self.assertEqual(ca_list[0].get("data"), {u'cacert': u'/etc/cert.pem',
                                                  u'cakey': u'/etc/key.pem'})

    def test_04_read_ca_connector(self):
        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 1)

        # create a second CA connector
        save_caconnector({"caconnector": "con2",
                          "type": "local"})

        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 2)

        # Get only one destinct connector filtered by name
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0].get("connectorname"), "con1")

    def test_05_read_as_user(self):
        self.setUp_user_realms()
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username":
                                                     "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            at_user = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)
            self.assertEqual(result.get("value").get("realm"), "realm1")

        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 2)
            self.assertEqual(value[0].get("data"), {})

    def test_06_delete_caconnector(self):
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(value, 1)

        ca_list = get_caconnector_list()
        self.assertEqual(len(ca_list), 1)
        self.assertEqual(ca_list[0].get("connectorname"), "con2")
