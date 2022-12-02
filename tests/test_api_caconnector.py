"""
This testcase is used to test the REST API  in api/caconnector.py
to create, update, delete CA connectors.
"""
from .base import MyApiTestCase
import json
from privacyidea.lib.caconnector import get_caconnector_list, save_caconnector
from privacyidea.lib.policy import set_policy, SCOPE, ACTION
from privacyidea.lib.error import ERROR


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
                                           data={'type': 'local',
                                                 'cacert': '/etc/key.pem',
                                                 'cakey': '/etc/cert.pem'},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        ca_list = get_caconnector_list()
        self.assertEqual(len(ca_list), 1)
        self.assertEqual(ca_list[0].get("data").get("cacert"), '/etc/cert.pem')
        self.assertEqual(ca_list[0].get("data").get("cakey"), '/etc/key.pem')
        self.assertEqual(ca_list[0].get("data").get("name"), 'con1')

    def test_04_read_ca_connector(self):
        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 1)

        # create a second CA connector
        with self.app.test_request_context('/caconnector/con2',
                                           data={'type': 'local',
                                                 'cakey': '/etc/key2.pem',
                                                 'cacert': '/etc/cert2.pem'},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 2, result)

        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            at_user = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)
            self.assertEqual(result.get("value").get("realm"), "realm1")

        # Only admins are allowed to access the /caconnector/ endpoints
        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = res.json.get("result")
            self.assertIn("do not have the necessary role", result["error"]["message"])

    def test_06_delete_caconnector(self):
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(value, 1)

        ca_list = get_caconnector_list()
        self.assertEqual(len(ca_list), 1)
        self.assertEqual(ca_list[0].get("connectorname"), "con2")

    def test_07_caconnector_admin_required(self):
        self.authenticate_selfservice_user()

        # As a selfservice user, we are not allowed to delete a CA connector
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = res.json.get("result")
            self.assertFalse(result['status'])
            self.assertEqual(result['error']['code'], ERROR.AUTHENTICATE_MISSING_RIGHT)
            self.assertIn("You do not have the necessary role (['admin']) to access this resource",
                          result['error']['message'])

        # We should get the same error message if a USER policy is defined.
        set_policy("user", scope=SCOPE.USER, action=ACTION.AUDIT, realm="")
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = res.json.get("result")
            self.assertFalse(result['status'])
            self.assertEqual(result['error']['code'], ERROR.AUTHENTICATE_MISSING_RIGHT)
            self.assertIn("You do not have the necessary role (['admin']) to access this resource",
                          result['error']['message'])

