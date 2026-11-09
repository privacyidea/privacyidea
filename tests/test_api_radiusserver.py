from .base import MyApiTestCase
from . import radiusmock
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.radiusserver import add_radius, delete_radius, list_radiusservers
from privacyidea.lib.crypto import CENSORED

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
            data = res.json
            self.assertEqual(data.get("result").get("value"), True)

        # list servers
        with self.app.test_request_context('/radiusserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("server"), "1.2.3.4")
            self.assertEqual(server1.get("description"), "myServer")
            self.assertEqual(server1.get("secret"), CENSORED)

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
            data = res.json
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 0)

    @radiusmock.activate
    def test_02_send_test_email(self):
        set_privacyidea_config("radius.dictfile", DICT_FILE)
        radiusmock.setdata(response=radiusmock.AccessAccept)

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
            data = res.json
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
            data = res.json
            self.assertEqual(data.get("result").get("value"), True)

        # Users are not allowed to list the radius servers
        with self.app.test_request_context('/radiusserver/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = res.json.get("result")
            self.assertIn("do not have the necessary role", result["error"]["message"])

        delete_radius("server1")

    @radiusmock.activate
    def test_censored_secret_needs_the_saved_server_and_port(self):
        add_radius("savedRadius", server="1.2.3.4", port=1812, secret="radsecret", dictionary=DICT_FILE)
        self.addCleanup(delete_radius, "savedRadius")
        radiusmock.setdata(response=radiusmock.AccessAccept)
        save_body = {"server": "5.6.7.8", "port": 1812, "secret": CENSORED, "dictionary": DICT_FILE}
        test_body = {"identifier": "savedRadius", "server": "1.2.3.4", "port": 1645, "secret": CENSORED,
                     "dictionary": DICT_FILE, "username": "testuser", "password": "testpassword"}
        for path, body, action in [("/radiusserver/savedRadius", save_body, "save"),
                                   ("/radiusserver/test_request", test_body, "test")]:
            with self.subTest(path=path):
                with self.app.test_request_context(path, method="POST", json=body,
                                                   headers={"Authorization": self.at}):
                    res = self.app.full_dispatch_request()
                self.assertEqual(400, res.status_code, res.json)
                self.assertIn(f"Enter the secret to {action} the changed settings",
                              res.json["result"]["error"]["message"])
        stored = list_radiusservers()["savedRadius"]
        self.assertEqual("1.2.3.4", stored["server"])
        self.assertEqual("radsecret", stored["secret"])
