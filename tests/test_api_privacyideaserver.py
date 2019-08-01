# -*- coding: utf-8 -*-
from privacyidea.lib.privacyideaserver import delete_privacyideaserver
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from .base import MyApiTestCase
import json
import responses


class PrivacyIDEAServerTestCase(MyApiTestCase):
    """
    test the api.privacyideaserver endpoints
    """

    def test_01_create_server(self):
        # create and list server

        # Unauthorized
        with self.app.test_request_context('/privacyideaserver/server1',
                                           method='POST',
                                           data={"url": "https://pi/pi",
                                                 "tls": "0",
                                                 "description": "myServer"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/privacyideaserver/server1',
                                           method='POST',
                                           data={"url": "https://pi",
                                                 "tls": "0",
                                                 "description": "myServer"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

        # list servers
        with self.app.test_request_context('/privacyideaserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("url"), "https://pi")
            self.assertEqual(server1.get("description"), "myServer")

        # delete server
        with self.app.test_request_context('/privacyideaserver/server1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # list servers, No server left
        with self.app.test_request_context('/privacyideaserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 0)

    @responses.activate
    def test_02_test_conncection(self):
        responses.add(responses.POST, "https://pi/validate/check",
                      body="""{
                    "jsonrpc": "2.0",
                    "signature": "8714492288983608958721372435263469282038130269793819687538718333085851022315074567013564786433032592569773009757668260857150988825993253128403096686276017572870299270974318705442428477018018734211619614135162719525545735285162164985627482472020309913143284756699606758573589339750891246114721488327919685939018812698986042837837048205963507243718362073386749929275433723467277740468538209437683755941724140343215877868596281187733952567488886126455218397004400817126119660003078762499546137083926344365458736163867631154552432520453852071998486914168310985851091111203094188983006153929089352703802214328258347608348",
                    "detail": null,
                    "version": "privacyIDEA 2.20.dev2",
                    "result": {
                      "status": true,
                      "value": true},
                    "time": 1503561105.028947,
                    "id": 1
                        }""",
                      content_type="application/json")

        with self.app.test_request_context('/privacyideaserver/test_request',
                                           method='POST',
                                           data={
                                               "identifier": "server1",
                                               "tls": "0",
                                               "url": "https://pi",
                                               "username": "testuser",
                                               "password": "testpassword"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

    def test_03_privacyideaserver_user(self):
        self.setUp_user_realms()
        self.authenticate_selfservice_user()

        # Create a privacyIDEA server
        with self.app.test_request_context('/privacyideaserver/server1',
                                           method='POST',
                                           data={"url": "https://pi",
                                                 "tls": "0",
                                                 "description": "myServer"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

        # User is not allowed to delete a privacyIDEA server
        with self.app.test_request_context('/privacyideaserver/server1',
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)

        # User is not allowed to create a privacyIDEA server
        with self.app.test_request_context('/privacyideaserver/server1',
                                           method='POST',
                                           data={"url": "https://pi",
                                                 "tls": "0",
                                                 "description": "myServer"},
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # User is allowed to list the privacyIDEA servers
        with self.app.test_request_context('/privacyideaserver/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            # The user does not get any information about the server!
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("url"), "")
            self.assertEqual(server1.get("tls"), "")
            self.assertEqual(server1.get("description"), "")

        # define a USER policy: not allowed to read privacyIDEA Servers anymore
        set_policy("pol_user", scope=SCOPE.USER, action=ACTION.AUDIT)
        with self.app.test_request_context('/privacyideaserver/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertIn("privacyideaserver_read is not allowed", result['error']['message'])

        # ... but we are allowed with a matching policy
        set_policy("pol_privacyidea", scope=SCOPE.USER, action=ACTION.PRIVACYIDEASERVERREAD)
        with self.app.test_request_context('/privacyideaserver/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            # The user does not get any information about the server!
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("url"), "")
            self.assertEqual(server1.get("tls"), "")
            self.assertEqual(server1.get("description"), "")

        delete_privacyideaserver("server1")
        delete_policy("pol_privacyidea")
        delete_policy("pol_user")
