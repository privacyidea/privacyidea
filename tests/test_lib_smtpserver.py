"""
This test file tests the lib/smtpserver.py
"""
import email
from email.mime.image import MIMEImage
import binascii
from privacyidea.lib.queue import get_job_queue

from tests.queuemock import MockQueueTestCase
from .base import MyTestCase
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.smtpserver import (get_smtpservers, add_smtpserver,
                                        delete_smtpserver, get_smtpserver,
                                        SMTPServer)
from . import smtpmock
from smtplib import SMTPException

PNG_IMG = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAA' \
          'ALEwEAmpwYAAAAB3RJTUUH5AEeDxMYtXhk0QAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBk' \
          'LmUHAAAAO0lEQVQY02P8////fwYiABMDkYAFXYCRkRGFD7MQq4n///9nQHcRCzaF6KbiVIjNf0R7hnyFuIKVaB' \
          'MB6yUTDUpeapUAAAAASUVORK5CYII='


class SMTPServerTestCase(MyTestCase):

    def test_01_create_smtpserver(self):
        r = add_smtpserver(identifier="myserver", server="1.2.3.4")
        self.assertTrue(r > 0)
        r = add_smtpserver(identifier="myserver1", server="5.4.3.2")
        self.assertTrue(r)
        r = add_smtpserver(identifier="myserver2", server="1.2.3.4")
        self.assertTrue(r)

        server_list = get_smtpservers()
        self.assertTrue(server_list)
        self.assertEqual(len(server_list), 3)
        server_list = get_smtpservers(identifier="myserver")
        self.assertEqual(len(server_list), 1)
        self.assertTrue(server_list[0].config.identifier, "myserver")
        self.assertTrue(server_list[0].config.port, 25)

        servers_by_ip = get_smtpservers(server='1.2.3.4')
        self.assertEqual(len(servers_by_ip), 2)
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
    def test_05_test_email_smtp(self):
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=True)
        identifier = "newConfig"
        server = "mailsever"
        port = 25
        username = "mailsender"
        password = "secret"
        sender = "mailsender@example.com"
        tls = True
        recipient = "user@example.com"

        s = dict(identifier=identifier, server=server, port=port,
                 username=username, password=password, sender=sender,
                 tls=tls)
        r = SMTPServer.test_email(s, recipient,
                                  "Test Email from privacyIDEA",
                                  "This is a test email from privacyIDEA. "
                                  "The configuration %s is working." % identifier)
        self.assertTrue(r)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        self.assertEqual(parsed_email.get_content_type(), 'text/plain', parsed_email)
        self.assertEqual(parsed_email.get('To'), recipient, parsed_email)
        self.assertEqual(parsed_email.get('Subject'), "Test Email from privacyIDEA", parsed_email)

        # Now with an already prepared MIME email
        msg = MIMEImage(binascii.a2b_base64(PNG_IMG))
        r = SMTPServer.test_email(s, recipient, "Test Email with image",
                                  msg)
        self.assertTrue(r)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        self.assertEqual(parsed_email.get_content_type(), 'image/png', parsed_email)
        self.assertEqual(parsed_email.get('To'), recipient, parsed_email)
        self.assertEqual(parsed_email.get('Subject'), "Test Email with image", parsed_email)
        # Check, that the mock SMTP server actually has NOT been configured as SMTP_SSL
        self.assertFalse(smtpmock.get_smtp_ssl())

    @smtpmock.activate
    def test_06_test_email_smtp_ssl(self):
        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)
        identifier = "newConfig"
        server = "smtps://mailserver"
        port = 25
        username = "mailsender"
        password = "secret"
        sender = "mailsender@example.com"
        tls = False
        recipient = "user@example.com"

        s = dict(identifier=identifier, server=server, port=port,
                 username=username, password=password, sender=sender,
                 tls=tls)
        r = SMTPServer.test_email(s, recipient,
                                  "Test Email from privacyIDEA",
                                  "This is a test email from privacyIDEA. "
                                  "The configuration %s is working." % identifier)
        self.assertTrue(r)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        self.assertEqual(parsed_email.get_content_type(), 'text/plain', parsed_email)
        self.assertEqual(parsed_email.get('To'), recipient, parsed_email)
        self.assertEqual(parsed_email.get('Subject'), "Test Email from privacyIDEA", parsed_email)

        # Now with an already prepared MIME email
        msg = MIMEImage(binascii.a2b_base64(PNG_IMG))
        r = SMTPServer.test_email(s, recipient, "Test Email with image",
                                  msg)
        self.assertTrue(r)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        self.assertEqual(parsed_email.get_content_type(), 'image/png', parsed_email)
        self.assertEqual(parsed_email.get('To'), recipient, parsed_email)
        self.assertEqual(parsed_email.get('Subject'), "Test Email with image", parsed_email)
        # Check, if the mock SMTP server actually has been configured as SMTP_SSL
        self.assertTrue(smtpmock.get_smtp_ssl())


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

