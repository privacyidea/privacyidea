"""
This test file tests the lib/smtpserver.py
"""
from privacyidea.lib.queue import get_job_queue

from tests.queuemock import MockQueueTestCase
from .base import MyTestCase
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.smtpserver import (get_smtpservers, add_smtpserver,
                                        delete_smtpserver, get_smtpserver,
                                        SMTPServer)
from privacyidea.models import SMTPServer as SMTPServerDB
from . import smtpmock
from smtplib import SMTPException


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
        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        with self.assertRaises(ResourceNotFoundError):
            get_smtpserver(None)

        server = get_smtpserver("myserver")
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)
        r = server.send_email(["recp@example.com"], "Hallo", "Body")
        self.assertEqual(r, True)

        smtpmock.setdata(response={"recp@example.com": (550,
                                                        "Message rejected")},
                         support_tls=False)
        r = server.send_email(["recp@example.com"], "Hallo", "Body")
        self.assertEqual(r, False)

        # Use TLS
        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=True)
        self.assertTrue(r > 0)
        server = get_smtpserver("myserver")
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=True)
        r = server.send_email(["recp@example.com"], "Hallo", "Body")
        self.assertEqual(r, True)

        # If we configure TLS but the server does not support this, we raise
        # an error
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)
        self.assertRaises(SMTPException, server.send_email,
                          ["recp@example.com"], "Hallo", "Body")

        delete_smtpserver("myserver")

    def test_03_updateserver(self):
        r = add_smtpserver(identifier="myserver", server="100.2.3.4")
        self.assertTrue(r > 0)
        server_list = get_smtpservers(identifier="myserver")
        self.assertTrue(server_list[0].config.server, "100.2.3.4")

    def test_04_missing_configuration(self):
        self.assertRaises(ResourceNotFoundError, get_smtpserver, "notExisting")

    @smtpmock.activate
    def test_05_test_email(self):
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=True)
        identifier = "newConfig"
        server = "mailsever"
        port = 25
        username = "mailsender"
        password = "secret"
        sender = "mailsender@exmaple.com"
        tls = True
        recipient = "user@example.com"

        s = dict(identifier=identifier, server=server, port=port,
                 username=username, password=password, sender=sender,
                 tls=tls)
        r = SMTPServer.test_email(s, recipient,
                                  "Test Email from privacyIDEA",
                                  "This is a test email from privacyIDEA. "
                                  "The configuration %s is working." % identifier)


class SMTPServerQueueTestCase(MockQueueTestCase):
    @smtpmock.activate
    def test_01_enqueue_email(self):
        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False, enqueue_job=True)
        self.assertTrue(r > 0)

        server = get_smtpserver("myserver")
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)
        r = server.send_email(["recp@example.com"], "Hallo", "Body")
        self.assertEqual(r, True)

        queue = get_job_queue()
        self.assertEqual(len(queue.enqueued_jobs), 1)
        job_name, args, kwargs = queue.enqueued_jobs[0]
        self.assertEqual(job_name, "smtpserver.send_email")
        self.assertEqual(args[1], ["recp@example.com"])
        self.assertEqual(args[2], "Hallo")
        self.assertEqual(args[3], "Body")

        # send_email returns True, even if the SMTP server will eventually reject the message
        smtpmock.setdata(response={"fail@example.com": (550,
                                                        "Message rejected")},
                         support_tls=False)
        r = server.send_email(["fail@example.com"], "Hallo", "Body")
        self.assertEqual(r, True)
        self.assertEqual(len(queue.enqueued_jobs), 2)
        job_name, args, kwargs = queue.enqueued_jobs[1]
        self.assertEqual(job_name, "smtpserver.send_email")
        self.assertEqual(args[1], ["fail@example.com"])
        self.assertEqual(args[2], "Hallo")
        self.assertEqual(args[3], "Body")

        delete_smtpserver("myserver")

    @smtpmock.activate
    def test_02_send_email_without_queue(self):
        # enqueue_job is False!
        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        server = get_smtpserver("myserver")
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)
        r = server.send_email(["recp@example.com"], "Hallo", "Body")
        self.assertEqual(r, True)

        smtpmock.setdata(response={"recp@example.com": (550,
                                                        "Message rejected")},
                         support_tls=False)
        r = server.send_email(["recp@example.com"], "Hallo", "Body")
        self.assertEqual(r, False)

        # Use TLS
        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=True)
        self.assertTrue(r > 0)
        server = get_smtpserver("myserver")
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=True)
        r = server.send_email(["recp@example.com"], "Hallo", "Body")
        self.assertEqual(r, True)

        # If we configure TLS but the server does not support this, we raise
        # an error
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)
        self.assertRaises(SMTPException, server.send_email,
                          ["recp@example.com"], "Hallo", "Body")

        # Assert that no
        queue = get_job_queue()
        self.assertEqual(queue.enqueued_jobs, [])

        delete_smtpserver("myserver")

