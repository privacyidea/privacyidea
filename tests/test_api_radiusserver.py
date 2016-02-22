# -*- coding: utf-8 -*-
from .base import MyTestCase
import json
import radiusmock
from privacyidea.lib.config import set_privacyidea_config
DICT_FILE = "tests/testdata/dictionary"


class RADIUSServerTestCase(MyTestCase):
    """
    test the api.radiusserver endpoints
    """

    def test_01_create_server(self):
        # create and list server

        # Unauthorized
        with self.app.test_request_context('/radiusserver/server1',
                                           method='POST',
                                           data={"secret": "testing123",
                                                 "port": "1812",
                                                 "server": "1.2.3.4",
                                                 "description": "myServer"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/radiusserver/server1',
                                           method='POST',
                                           data={"secret": "testing123",
                                                 "port": "1812",
                                                 "server": "1.2.3.4",
                                                 "description": "myServer"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            self.assertEqual(data.get("result").get("value"), True)

        # list servers
        with self.app.test_request_context('/radiusserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("server"), "1.2.3.4")
            self.assertEqual(server1.get("description"), "myServer")
            self.assertTrue("secret" not in server1)

        # delete server
        with self.app.test_request_context('/radiusserver/server1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # list servers, No server left
        with self.app.test_request_context('/radiusserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 0)

    @radiusmock.activate
    def test_02_send_test_email(self):
        set_privacyidea_config("radius.dictfile", DICT_FILE)
        radiusmock.setdata(success=True)

        with self.app.test_request_context('/radiusserver/test_request',
                                           method='POST',
                                           data={"identifier": "someServer",
                                                 "secret": "secret",
                                                 "port": "1812",
                                                 "server": "1.2.3.4",
                                                 "dictionary": DICT_FILE,
                                                 "username": "testuser",
                                                 "password": "testpassword"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data)
            self.assertEqual(data.get("result").get("value"), True)

