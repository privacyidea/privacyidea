# -*- coding: utf-8 -*-
from .base import MyApiTestCase
import json
from . import radiusmock
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.radiusserver import delete_radius
DICT_FILE = "tests/testdata/dictionary"


class RADIUSServerTestCase(MyApiTestCase):
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
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

        # list servers
        with self.app.test_request_context('/radiusserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
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
            data = json.loads(res.data.decode('utf8'))
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
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

    def test_03_radiusserver_user(self):
        # The user must be able to call GET /radiusserver/
        # But not POST and not DELETE
        # delete server
        self.setUp_user_realms()
        self.authenticate_selfservice_user()

        # User is not allowed to delete a radiusserver
        with self.app.test_request_context('/radiusserver/server1',
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # User is not allowed to create a radius server
        with self.app.test_request_context('/radiusserver/server1',
                                           method='POST',
                                           data={"secret": "testing123",
                                                 "port": "1812",
                                                 "server": "1.2.3.4",
                                                 "description": "myServer"},
                                           headers={'Authorization': self.at_user}):
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
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

        # User is allowed to list the radius servers
        with self.app.test_request_context('/radiusserver/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            # The user does not get any information about the server!
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("port"), "")
            self.assertEqual(server1.get("server"), "")
            self.assertEqual(server1.get("dictionary"), "")
            self.assertEqual(server1.get("description"), "")

        delete_radius("server1")
