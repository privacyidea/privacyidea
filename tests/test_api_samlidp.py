# -*- coding: utf-8 -*-
from .base import MyTestCase
import json
from privacyidea.lib.error import ConfigAdminError
import responses

# Some long data
METADATA = 300 * "1234567890"


class SAMLIdPTestCase(MyTestCase):
    """
    test the api.samlidp endpoints
    """

    def test_01_create_server(self):
        # create and list server

        # Unauthorized
        with self.app.test_request_context(
                '/samlidp/server1',
                method='POST',
                data={"metadata_url": "http://example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context(
                '/samlidp/server1',
                method='POST',
                data={"metadata_url": "http://example.com"},
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            self.assertEqual(data.get("result").get("value"), True)

        # list servers
        with self.app.test_request_context('/samlidp/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("metadata_url"), "http://example.com")
            self.assertEqual(server1.get("active"), True)

        # delete server
        with self.app.test_request_context('/samlidp/server1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # list servers, No server left
        with self.app.test_request_context('/samlidp/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 0)

    @responses.activate
    def test_02_send_test_email(self):
        responses.add(responses.GET, "http://example.com",
                      status=200, content_type='text/html',
                      body=METADATA)

        with self.app.test_request_context(
                '/samlidp/server1',
                method='POST',
                data={"metadata_url": "http://example.com"},
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            self.assertEqual(data.get("result").get("value"), True)



