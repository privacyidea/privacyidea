"""
This test file tests the lib/smtpserver.py
"""
import binascii
import email
import re
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from smtplib import SMTPException
from unittest.mock import patch

from privacyidea.lib.crypto import encryptPassword, decryptPassword
from privacyidea.lib.error import ConfigAdminError, ParameterError, ResourceNotFoundError
from privacyidea.lib.queue import get_job_queue
from privacyidea.lib.smtpserver import (get_smtpservers, add_smtpserver,
                                        delete_smtpserver, get_smtpserver,
                                        SMTPServer, send_email_identifier,
                                        send_email_data, parse_server_address, TIMEOUT)
from tests.queuemock import MockQueueTestCase
from . import smtpmock
from .base import MyTestCase

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
        # Initial create
        smtp_id = add_smtpserver(identifier="myserver", server="100.2.3.4", smime=True, private_key="123",
                                 private_key_password="top_secret", certificate="cert")
        self.assertGreater(smtp_id, 0)
        server_list = get_smtpservers(identifier="myserver")
        server = server_list[0].config
        self.assertEqual("100.2.3.4", server.server)
        self.assertTrue(server.smime)
        self.assertEqual("123", server.private_key)
        # assume encryption
        self.assertEqual(len(encryptPassword("top_secret")), len(server.private_key_password))
        self.assertNotEqual("top_secret", server.private_key_password)
        self.assertEqual("top_secret", decryptPassword(server.private_key_password))
        self.assertEqual("cert", server.certificate)

        # Update private key password
        smtp_id = add_smtpserver(identifier="myserver", server="200.2.3.4", private_key_password="new_secret")
        self.assertGreater(smtp_id, 0)
        server_list = get_smtpservers(identifier="myserver")
        server = server_list[0].config
        # assume encryption
        self.assertEqual(len(encryptPassword("new_secret")), len(server.private_key_password))
        self.assertNotEqual("new_secret", server.private_key_password)
        self.assertEqual("new_secret", decryptPassword(server.private_key_password))

        # Update keeps unspecified private key password unchanged
        smtp_id = add_smtpserver(identifier="myserver", server="200.2.3.4")
        self.assertGreater(smtp_id, 0)
        server_list = get_smtpservers(identifier="myserver")
        server = server_list[0].config
        self.assertEqual("200.2.3.4", server.server)
        self.assertEqual("new_secret", decryptPassword(server.private_key_password))

        # Can clear private key password
        smtp_id = add_smtpserver(identifier="myserver", server="200.2.3.4", private_key_password="")
        self.assertGreater(smtp_id, 0)
        server_list = get_smtpservers(identifier="myserver")
        server = server_list[0].config
        self.assert_empty_string(server.private_key_password)

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

    @smtpmock.activate
    def test_07_message_uses_crlf_line_endings(self):
        # Regression test for issue #5217: when the message was serialized
        # via as_bytes() the payload reaching smtplib.sendmail was bytes
        # with bare "\n" line breaks. smtplib only normalizes line endings
        # to CRLF for str input (via _fix_eols); bytes are sent through
        # unchanged, so Exchange SE received the message with bare LF and
        # treated the body as empty.
        #
        # Switching to as_string() means smtplib gets a str and normalizes
        # to CRLF before transmission. This test simulates that wire
        # transformation and asserts no bare LF remains -- which would
        # fail if anyone reverts to as_bytes().
        smtpmock.setdata(response={"user@example.com": (200, "OK")},
                         support_tls=False)
        s = dict(identifier="crlfConfig", server="mailserver", port=25,
                 sender="mailsender@example.com", tls=False)

        body = MIMEText(
            "<p>Hello</p>\n\n<p>Dein OTP <b>562012</b></p>\n\n"
            "<p>Hier ist ansonsten noch viel mehr Text, der zu "
            "Zeilenumbrüchen führt</p>\n",
            "html", "utf-8")
        r = SMTPServer.test_email(s, "user@example.com",
                                  "Regression CRLF", body)
        self.assertTrue(r)

        sent = smtpmock.get_sent_message()
        # Reproduce smtplib.sendmail's wire transformation: str input is
        # passed through _fix_eols and ASCII-encoded; bytes are sent as-is.
        if isinstance(sent, str):
            wire = re.sub(r"(?:\r\n|\n|\r(?!\n))", "\r\n", sent).encode("ascii")
        else:
            wire = sent
        self.assertIn(b"\r\n", wire)
        bare_lf = re.search(rb"(?<!\r)\n", wire)
        self.assertIsNone(
            bare_lf,
            "Wire payload contains a bare LF, which Exchange treats as "
            "an empty body (issue #5217). This happens when the message "
            "is handed to smtplib as bytes (e.g. via as_bytes()) instead "
            "of as a str.")


class ParseServerAddressTestCase(MyTestCase):

    def test_parse_server_address(self):
        cases = [
            (("mail.example.com", 25), ("smtp", "mail.example.com", 25)),
            (("mail.example.com:2525", 25), ("smtp", "mail.example.com", 2525)),
            (("smtp://mail.example.com", "587"), ("smtp", "mail.example.com", 587)),
            (("smtps://mail.example.com", 25), ("smtps", "mail.example.com", 25)),
            (("smtps://mail.example.com:465", 25), ("smtps", "mail.example.com", 465)),
            (("192.0.2.1", 25), ("smtp", "192.0.2.1", 25)),
            (("smtp://", 25), ("smtp", None, 25)),
        ]
        for (server, port), expected in cases:
            with self.subTest(server=server):
                self.assertEqual(expected, parse_server_address(server, port))
        with self.assertRaises(ValueError):
            parse_server_address("mail.example.com:99999", 25)

    def test_sending_connects_to_the_parsed_address(self):
        config = {"identifier": "parsed", "server": "smtps://mail.example.com:465", "port": 25,
                  "sender": "pi@example.com", "tls": False}
        with patch("smtplib.SMTP_SSL") as smtp_ssl:
            smtp_ssl.return_value.sendmail.return_value = {}
            SMTPServer.test_email(config, "recp@example.com", "subject", "body")
        smtp_ssl.assert_called_once_with("mail.example.com", port=465, timeout=TIMEOUT)


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


class SendEmailMetricsTestCase(MyTestCase):
    """Cover the metric-recording wrappers around ``send_email_identifier`` and
    ``send_email_data`` - especially the exception re-raise path that codecov
    flagged as untested.
    """

    def setUp(self):
        from privacyidea.models import db as _db
        from privacyidea.models.metric_aggregate import MetricAggregate
        _db.session.query(MetricAggregate).delete()
        _db.session.commit()

    def _read_counter(self, identifier, result):
        from privacyidea.lib.metrics import get_metrics
        rows = get_metrics(name="email_send_total")
        match = [r for r in rows if r["labels"].get("result") == result
                 and r["labels"].get("identifier") == identifier]
        return sum(r["count"] for r in match)

    def _read_duration_count(self, identifier):
        from privacyidea.lib.metrics import get_metrics
        rows = [r for r in get_metrics(name="email_send_duration_seconds")
                if r["labels"].get("identifier") == identifier]
        return sum(r["count"] for r in rows)

    def test_send_email_identifier_success_records_ok(self):
        add_smtpserver(identifier="metric-srv", server="mail.example", port=25)
        try:
            with patch("privacyidea.lib.smtpserver.SMTPServer.send_email", return_value=True):
                self.assertTrue(send_email_identifier("metric-srv", "to@example.com",
                                                     "subj", "body"))
            self.assertEqual(self._read_counter("metric-srv", "ok"), 1)
            self.assertEqual(self._read_duration_count("metric-srv"), 1)
        finally:
            delete_smtpserver("metric-srv")

    def test_send_email_identifier_returning_false_records_failed(self):
        add_smtpserver(identifier="metric-srv", server="mail.example", port=25)
        try:
            with patch("privacyidea.lib.smtpserver.SMTPServer.send_email", return_value=False):
                self.assertFalse(send_email_identifier("metric-srv", "to@example.com",
                                                      "subj", "body"))
            self.assertEqual(self._read_counter("metric-srv", "failed"), 1)
            self.assertEqual(self._read_counter("metric-srv", "ok"), 0)
        finally:
            delete_smtpserver("metric-srv")

    def test_send_email_identifier_exception_records_error_and_reraises(self):
        # The path codecov flagged: send_email raises, we record the duration +
        # error counter, then re-raise so the caller still sees the exception.
        add_smtpserver(identifier="metric-srv", server="mail.example", port=25)
        try:
            with patch("privacyidea.lib.smtpserver.SMTPServer.send_email",
                       side_effect=SMTPException("connection refused")):
                with self.assertRaises(SMTPException):
                    send_email_identifier("metric-srv", "to@example.com", "subj", "body")
            self.assertEqual(self._read_counter("metric-srv", "error"), 1)
            self.assertEqual(self._read_counter("metric-srv", "ok"), 0)
            self.assertEqual(self._read_duration_count("metric-srv"), 1)
        finally:
            delete_smtpserver("metric-srv")

    def test_send_email_data_exception_records_error_under_emailtoken_label(self):
        # send_email_data uses the synthetic identifier "emailtoken", which the
        # endpoint folds into its own row in the Notification Delivery panel.
        with patch("privacyidea.lib.smtpserver.SMTPServer.send_email",
                   side_effect=SMTPException("nope")):
            with self.assertRaises(SMTPException):
                send_email_data("mail.example", "subj", "body",
                                "from@example.com", ["to@example.com"])
        self.assertEqual(self._read_counter("emailtoken", "error"), 1)
        self.assertEqual(self._read_duration_count("emailtoken"), 1)

    def test_send_email_data_success_records_ok_under_emailtoken_label(self):
        with patch("privacyidea.lib.smtpserver.SMTPServer.send_email", return_value=True):
            self.assertTrue(send_email_data("mail.example", "subj", "body",
                                            "from@example.com", ["to@example.com"]))
        self.assertEqual(self._read_counter("emailtoken", "ok"), 1)


class SMTPServerExportImportTestCase(MyTestCase):
    """Coverage for the registry export/import of SMTP servers, including
    censoring and the private_key_password round-trip."""

    def test_01_export_censor_and_roundtrip(self):
        from privacyidea.lib.smtpserver import (export_smtpserver, import_smtpserver,
                                                add_smtpserver, delete_smtpserver)
        from privacyidea.lib.crypto import CENSORED
        add_smtpserver("expsmtp", server="mail.example", password="smtppw",
                       private_key_password="pkppw")
        # censored export replaces both secrets
        censored = export_smtpserver(censor=True)
        self.assertEqual(censored["expsmtp"]["password"], CENSORED)
        self.assertEqual(censored["expsmtp"]["private_key_password"], CENSORED)
        # clear-text export decrypts both secrets
        exported = export_smtpserver()
        self.assertEqual(exported["expsmtp"]["password"], "smtppw")
        self.assertEqual(exported["expsmtp"]["private_key_password"], "pkppw")
        # the export round-trips: re-importing and re-exporting yields the same
        # clear-text secrets (i.e. private_key_password is not double-encrypted)
        delete_smtpserver("expsmtp")
        import_smtpserver(exported)
        reexported = export_smtpserver()
        self.assertEqual(reexported["expsmtp"]["password"], "smtppw")
        self.assertEqual(reexported["expsmtp"]["private_key_password"], "pkppw")
        delete_smtpserver("expsmtp")

    def test_02_identifier_not_addressable_in_url(self):
        from privacyidea.lib.smtpserver import import_smtpserver
        with self.assertRaises(ParameterError):
            add_smtpserver("team/mail", server="mail.example", sender="pi@example.com")
        with self.assertRaises(ConfigAdminError):
            import_smtpserver({"team/mail": {"server": "mail.example", "sender": "pi@example.com"}})
        self.assertEqual([], get_smtpservers(identifier="team/mail"))
        # POST /smtpserver/send_test_email is the test endpoint
        with self.assertRaises(ParameterError):
            add_smtpserver("send_test_email", server="mail.example", sender="pi@example.com")
        self.assertEqual([], get_smtpservers(identifier="send_test_email"))

    def test_03_censored_password_only_kept_for_same_settings(self):
        from privacyidea.lib.crypto import CENSORED
        from privacyidea.lib.smtpserver import export_smtpserver, import_smtpserver, list_smtpservers
        add_smtpserver("censoredsmtp", server="mail.example", port=587, username="pi", password="secret",
                       sender="pi@example.com", tls=True)

        # Same settings, and settings that are not given, keep the stored password
        add_smtpserver("censoredsmtp", server="mail.example", port=587, username="pi", password=CENSORED,
                       sender="pi@example.com", tls=True, description="kept")
        add_smtpserver("censoredsmtp", server=None, port=None, username=None, password=CENSORED, tls=None)
        self.assertEqual("secret", list_smtpservers("censoredsmtp")["censoredsmtp"]["password"])

        # A changed setting is rejected and changes nothing
        with self.assertRaises(ParameterError):
            add_smtpserver("censoredsmtp", server="other.example", port=587, username="pi", password=CENSORED,
                           sender="pi@example.com", tls=True)
        self.assertEqual("mail.example", list_smtpservers("censoredsmtp")["censoredsmtp"]["server"])

        # A censored export can be imported into the same instance, but not with a changed server
        export = export_smtpserver(name="censoredsmtp", censor=True)
        import_smtpserver(export)
        self.assertEqual("secret", list_smtpservers("censoredsmtp")["censoredsmtp"]["password"])
        export["censoredsmtp"]["server"] = "other.example"
        with self.assertRaises(ConfigAdminError):
            import_smtpserver(export)
        self.assertEqual("mail.example", list_smtpservers("censoredsmtp")["censoredsmtp"]["server"])
        delete_smtpserver("censoredsmtp")

    def test_04_import_continues_after_invalid_server(self):
        from privacyidea.lib.smtpserver import import_smtpserver
        server = {"server": "mail.example", "sender": "pi@example.com"}
        with self.assertRaises(ConfigAdminError) as cm:
            import_smtpserver({"good": server, "mail/relay": server, "send_test_email": server, "after": server})
        self.assertIn('"mail/relay"', cm.exception.message)
        self.assertIn("must not contain '/'", cm.exception.message)
        self.assertIn('"send_test_email"', cm.exception.message)
        self.assertIn("Successfully imported: ['good', 'after']", cm.exception.message)
        self.assertEqual(["after", "good"],
                         sorted(server.config.identifier for server in get_smtpservers()
                                if server.config.identifier in ("good", "mail/relay", "send_test_email", "after")))
        delete_smtpserver("good")
        delete_smtpserver("after")

    def test_05_settings_that_can_not_send_are_not_saved(self):
        from privacyidea.lib.smtpserver import import_smtpserver
        invalid = {"port": ({"port": 99999}, "port must be between 1 and 65535"),
                   "port_text": ({"port": "abc"}, "port must be a whole number"),
                   "port_fraction": ({"port": 587.9}, "port must be a whole number"),
                   "port_fraction_text": ({"port": "587.9"}, "port must be a whole number"),
                   "port_infinite": ({"port": float("inf")}, "port must be a whole number"),
                   "timeout_bool": ({"timeout": True}, "timeout must be a whole number"),
                   "timeout": ({"timeout": 0}, "timeout must be between 1 and 3600"),
                   "server": ({"server": "smtp://"}, "does not contain a host name"),
                   "server_port": ({"server": "mail.example:99999"}, "must be a number between 1 and 65535"),
                   "sender": ({"sender": "pi@example.com\r\n"}, "must not contain line breaks"),
                   "sender_ascii": ({"sender": "pi@exämple.com"}, "contains non-ASCII characters")}
        for name, (change, message) in invalid.items():
            with self.subTest(name=name):
                settings = dict({"server": "mail.example", "sender": "pi@example.com"}, **change)
                with self.assertRaises(ParameterError) as cm:
                    add_smtpserver(f"invalid_{name}", **settings)
                self.assertIn(message, cm.exception.message)
                # pi-manage config import uses the same checks
                with self.assertRaises(ConfigAdminError) as cm:
                    import_smtpserver({f"invalid_{name}": settings})
                self.assertIn(message, cm.exception.message)
                self.assertEqual([], get_smtpservers(identifier=f"invalid_{name}"))

        # An existing server is not changed either
        add_smtpserver("valid", server="mail.example", port=587, sender="pi@example.com", timeout=20)
        with self.assertRaises(ParameterError):
            add_smtpserver("valid", server="mail.example", port=99999)
        stored = get_smtpserver("valid").config
        self.assertEqual(587, stored.port)
        self.assertEqual(20, stored.timeout)
        # A float without fraction is a whole number
        add_smtpserver("valid", server="mail.example", port=587.0)
        self.assertEqual(587, get_smtpserver("valid").config.port)
        # A port given as string, e.g. from an import file, is stored as number
        add_smtpserver("valid", server="mail.example", port="465", timeout="30")
        stored = get_smtpserver("valid").config
        self.assertEqual(465, stored.port)
        self.assertEqual(30, stored.timeout)
        delete_smtpserver("valid")
