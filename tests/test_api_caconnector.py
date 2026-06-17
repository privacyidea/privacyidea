"""
This testcase is used to test the REST API  in api/caconnector.py
to create, update, delete CA connectors.
"""
from .base import MyApiTestCase
from privacyidea.lib.caconnector import get_caconnector_list
from privacyidea.lib.crypto import CENSORED
from privacyidea.lib.policy import set_policy, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.error import Error


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
                                           data={"username": "selfservice@realm1",
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
            self.assertEqual(result['error']['code'], Error.AUTHENTICATE_MISSING_RIGHT)
            self.assertIn("You do not have the necessary role (['admin']) to access this resource",
                          result['error']['message'])

        # We should get the same error message if a USER policy is defined.
        set_policy("user", scope=SCOPE.USER, action=PolicyAction.AUDIT, realm="")
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = res.json.get("result")
            self.assertFalse(result['status'])
            self.assertEqual(result['error']['code'], Error.AUTHENTICATE_MISSING_RIGHT)
            self.assertIn("You do not have the necessary role (['admin']) to access this resource",
                          result['error']['message'])

    def test_08_get_specific_options(self):
        with self.app.test_request_context('/caconnector/specific/local',
                                           method='GET',
                                           query_string={'type': 'local',
                                                         'cakey': '/etc/key.pem',
                                                         'cacert': '/etc/cert.pem'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertTrue(result['status'], result)
            # TODO: Add test for MSCA connector
            # The localca CA connector does return only an empty dictionary
            self.assertEqual(result['value'], {}, result)

    def test_09_password_censored_in_api_response(self):
        """GET /caconnector/ must censor password-type config values."""
        # Create a CA connector with a password-type config via the API
        with self.app.test_request_context('/caconnector/con_secret',
                                           data={
                                               'type': 'microsoft',
                                               'hostname': 'ca.example.com',
                                               'port': '443',
                                               'ssl_client_key_password': 'my_secret_key_pw',
                                           },
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # Now GET /caconnector/con_secret should censor the password
        with self.app.test_request_context('/caconnector/con_secret',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            value = result["value"]
            self.assertEqual(len(value), 1)
            connector = value[0]
            # The password config must be censored
            self.assertEqual(
                connector["data"]["ssl_client_key_password"],
                CENSORED,
                "Password-type CA connector config must be censored in the API response"
            )
            # Non-password config must NOT be censored
            self.assertEqual(connector["data"]["hostname"], "ca.example.com")

    def test_10_caconnector_password_not_overwritten_by_censored(self):
        """Saving a CA connector with __CENSORED__ must preserve the original password."""
        from privacyidea.models import db
        from privacyidea.models.caconnector import CAConnectorConfig
        from privacyidea.lib.crypto import decryptPassword
        from sqlalchemy import select

        # Create a CA connector with a password via the API
        with self.app.test_request_context('/caconnector/con_preserve',
                                           data={
                                               'type': 'microsoft',
                                               'hostname': 'ca.example.com',
                                               'port': '443',
                                               'ssl_client_key_password': 'original_ca_password',
                                           },
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            ca_id = res.json["result"]["value"]

        # Now update the connector via the API, sending CENSORED for the password
        with self.app.test_request_context('/caconnector/con_preserve',
                                           data={
                                               'type': 'microsoft',
                                               'ssl_client_key_password': CENSORED,
                                               'hostname': 'new-ca.example.com',
                                               'port': '8443',
                                           },
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # Verify the password was preserved (not overwritten with CENSORED)
        stmt = select(CAConnectorConfig).filter_by(
            caconnector_id=ca_id, Key="ssl_client_key_password"
        )
        db_config = db.session.execute(stmt).scalar_one()
        # The encrypted value should still be valid and decrypt to the original
        self.assertEqual(decryptPassword(db_config.Value), "original_ca_password")
        # Other fields should be updated
        stmt2 = select(CAConnectorConfig).filter_by(
            caconnector_id=ca_id, Key="hostname"
        )
        db_host = db.session.execute(stmt2).scalar_one()
        self.assertEqual(db_host.Value, "new-ca.example.com")
