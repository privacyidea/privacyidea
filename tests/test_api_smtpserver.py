# -*- coding: utf-8 -*-
from .base import MyApiTestCase
import json
from . import smtpmock


class SMTPServerTestCase(MyApiTestCase):
    """
    test the api.smtpserver endpoints
    """

    def test_01_create_server(self):
        # create and list server

        # Unauthorized
        with self.app.test_request_context('/smtpserver/server1',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "secret",
                                                 "port": "123",
                                                 "server": "1.2.3.4",
                                                 "description": "myServer"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/smtpserver/server1',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "password": "secret",
                                                 "port": "123",
                                                 "server": "1.2.3.4",
                                                 "sender": "privacyidea@local",
                                                 "description": "myServer"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual(data.get("result").get("value"), True)

        # list servers
        with self.app.test_request_context('/smtpserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 1)
            server1 = server_list.get("server1")
            self.assertEqual(server1.get("server"), "1.2.3.4")
            self.assertEqual(server1.get("sender"), "privacyidea@local")
            self.assertEqual(server1.get("username"), "cornelius")
            self.assertEqual(server1.get("password"), "secret")

        # delete server
        with self.app.test_request_context('/smtpserver/server1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # list servers, No server left
        with self.app.test_request_context('/smtpserver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            server_list = data.get("result").get("value")
            self.assertEqual(len(server_list), 0)

    @smtpmock.activate
    def test_02_send_test_email(self):
        smtpmock.setdata(response={"recp@example.com": (200, "OK")})

        with self.app.test_request_context('/smtpserver/send_test_email',
                                           method='POST',
                                           data={"identifier": "someServer",
                                                 "username": "cornelius",
                                                 "password": "secret",
                                                 "port": "123",
                                                 "server": "1.2.3.4",
                                                 "sender": "privacyidea@local",
                                                 "recipient":
                                                     "recp@example.com",
                                                 "description": "myServer"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual(data.get("result").get("value"), True)

