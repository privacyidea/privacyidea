"""
This test file tests the lib/smtpserver.py
"""
from .base import MyTestCase
from privacyidea.lib.smtpserver import (get_smtpservers, add_smtpserver,
                                        delete_smtpserver, SMTPServer)
import smtpmock


class SMTPServerTestCase(MyTestCase):

    def test_01_create_smtpserver(self):
        r = add_smtpserver(identifier="myserver", server="1.2.3.4")
        self.assertTrue(r > 0)
        r = add_smtpserver(identifier="myserver1", server="1.2.3.4")
        r = add_smtpserver(identifier="myserver2", server="1.2.3.4")

        server_list = get_smtpservers()
        self.assertTrue(server_list)
        self.assertEqual(len(server_list), 3)
        server_list = get_smtpservers(identifier="myserver")
        self.assertTrue(server_list[0].config.identifier, "myserver")
        self.assertTrue(server_list[0].config.port, 25)

        for server in ["myserver", "myserver1", "myserver2"]:
            r = delete_smtpserver(server)
            self.assertTrue(r > 0)

        server_list = get_smtpservers()
        self.assertEqual(len(server_list), 0)

    @smtpmock.activate
    def test_02_send_email(self):
        r = add_smtpserver(identifier="myserver", server="1.2.3.4")
        self.assertTrue(r > 0)

        server = get_smtpservers(identifier="myserver")[0]
        smtpmock.setdata(response={"recp@example.com": (200, "OK")})
        r = server.send_email(["recp@example.com"], "Hallo", "Body")

        self.assertEqual(r.get("recp@example.com"), (200, 'OK'))
        delete_smtpserver("myserver")

    def test_03_updateserver(self):
        r = add_smtpserver(identifier="myserver", server="100.2.3.4")
        self.assertTrue(r > 0)
        server_list = get_smtpservers(identifier="myserver")
        self.assertTrue(server_list[0].config.server, "100.2.3.4")
