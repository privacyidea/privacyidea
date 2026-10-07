import json

import responses

from .base import MyApiTestCase
from .test_lib_privacyideaserver import PI_RESPONSE_SIGNATURE


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
            data = res.json
            self.assertEqual(data.get("result").get("value"), True)

        # list servers
        with self.app.test_request_context('/privacyideaserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("url"), "https://pi")
            self.assertEqual(server1.get("description"), "myServer")

        # Listing privacyIDEA servers as a user is not allowed
        self.setUp_user_realms()
        self.authenticate_selfservice_user()
        with self.app.test_request_context('/privacyideaserver/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)

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
            data = res.json
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 0)

    @responses.activate
    def test_02_test_conncection(self):
        responses.add(responses.POST, "https://pi/validate/check",
                      body=json.dumps({"jsonrpc": "2.0",
                                       "signature": PI_RESPONSE_SIGNATURE,
                                       "detail": None,
                                       "version": "privacyIDEA 2.20.dev2",
                                       "result": {"status": True, "value": True},
                                       "time": 1503561105.028947,
                                       "id": 1}),
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
            data = res.json
            self.assertEqual(data.get("result").get("value"), True)
