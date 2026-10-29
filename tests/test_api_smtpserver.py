import email
import smtplib
import socket
import ssl
from unittest import mock

from privacyidea.api.smtpserver import _describe_smtp_error
from privacyidea.lib.crypto import encryptPassword, CENSORED
from . import smtpmock
from .base import MyApiTestCase


class SMTPServerTestCase(MyApiTestCase):
    """
    test the api.smtpserver endpoints
    """

    def setUp(self):
        super().setUp()
        self.smtp_mock = smtpmock
        self.smtp_mock.start()

    def tearDown(self):
        self.smtp_mock.stop()
        self.smtp_mock.reset()
        super().tearDown()

    def _create_server(self, name="server1", extra_data=None):
        """Helper to create an SMTP server via the API."""
        data = {
            "username": "cornelius",
            "password": "secret",
            "port": "123",
            "server": "1.2.3.4",
            "sender": "privacyidea@local",
            "description": "myServer",
        }
        if extra_data:
            data.update(extra_data)
        with self.app.test_request_context(
                f'/smtpserver/{name}',
                method='POST',
                data=data,
                headers={'Authorization': self.at},
        ):
            res = self.app.full_dispatch_request()
        return res

    def _list_servers(self):
        """Helper to list SMTP servers."""
        with self.app.test_request_context(
                '/smtpserver/',
                method='GET',
                headers={'Authorization': self.at},
        ):
            res = self.app.full_dispatch_request()
        return res

    def _delete_server(self, name="server1"):
        """Helper to delete an SMTP server."""
        with self.app.test_request_context(
                f'/smtpserver/{name}',
                method='DELETE',
                headers={'Authorization': self.at},
        ):
            res = self.app.full_dispatch_request()
        return res

    def _send_test_email(self, extra_data=None):
        """Helper to send a test email via the API."""
        data = {
            "identifier": "someServer",
            "username": "cornelius",
            "password": encryptPassword("secret"),
            "port": "123",
            "server": "1.2.3.4",
            "sender": "privacyidea@local",
            "recipient": "recp@example.com",
            "description": "myServer",
        }
        if extra_data:
            data.update(extra_data)
        with self.app.test_request_context(
                '/smtpserver/send_test_email',
                method='POST',
                data=data,
                headers={'Authorization': self.at},
        ):
            res = self.app.full_dispatch_request()
        return res

    def test_create_server_unauthorized(self):
        """Creating a server without auth returns 401."""
        with self.app.test_request_context(
                '/smtpserver/server1',
                method='POST',
                data={
                    "username": "cornelius",
                    "password": "secret",
                    "port": "123",
                    "server": "1.2.3.4",
                    "description": "myServer",
                },
        ):
            res = self.app.full_dispatch_request()
            assert res.status_code == 401

    def test_create_server(self):
        """Creating a server returns success."""
        res = self._create_server()
        assert res.status_code == 200
        assert res.json["result"]["value"] is True

    def test_list_servers(self):
        """After creating a server, it appears in the list."""
        self._create_server()
        res = self._list_servers()
        assert res.status_code == 200
        server_list = res.json["result"]["value"]
        assert len(server_list) == 1
        server1 = server_list["server1"]
        assert server1["server"] == "1.2.3.4"
        assert server1["sender"] == "privacyidea@local"
        assert server1["username"] == "cornelius"
        assert server1["password"] == CENSORED

    def test_delete_server(self):
        """After deleting a server, the list is empty."""
        self._create_server()
        res = self._delete_server()
        assert res.status_code == 200

        res = self._list_servers()
        assert res.status_code == 200
        assert len(res.json["result"]["value"]) == 0

    def test_send_test_email(self):
        """Sending a test email succeeds."""
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        res = self._send_test_email()
        assert res.status_code == 200
        assert res.json["result"]["value"] is True

    def test_send_test_email_with_censored_password(self):
        """A censored password in the test request is replaced by the stored one."""
        self._create_server()
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        with mock.patch("smtplib.SMTP.login", return_value=(235, b"OK")) as login:
            res = self._send_test_email(extra_data={"identifier": "server1", "password": CENSORED})
        assert res.status_code == 200
        assert res.json["result"]["value"] is True
        login.assert_called_once_with("cornelius", "secret")

    def test_send_test_email_with_censored_private_key_password(self):
        """A censored private key password is replaced by the stored one."""
        self._create_server(extra_data={"private_key_password": "pkpass"})
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        with mock.patch("privacyidea.lib.smtpserver.serialization.load_pem_private_key",
                        side_effect=ValueError("no key")) as load_key:
            self._send_test_email(extra_data={"identifier": "server1",
                                              "smime": True,
                                              "private_key": "tests/testdata/ca/cakey.pem",
                                              "certificate": "tests/testdata/ca/cacert.pem",
                                              "private_key_password": CENSORED})
        load_key.assert_called_once()
        assert load_key.call_args.args[1] == b"pkpass"

    def test_send_test_email_with_censored_password_unknown_server(self):
        """A censored password without a saved server is rejected, not sent."""
        with mock.patch("smtplib.SMTP.login") as login:
            res = self._send_test_email(extra_data={"identifier": "unknown", "password": CENSORED})
        assert res.status_code == 400
        login.assert_not_called()

    def test_send_test_email_smtp_error(self):
        """An SMTP error is reported as a readable 400 error instead of a 500."""
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        error = smtplib.SMTPAuthenticationError(535, b"5.7.8 Error: authentication failed")
        with mock.patch("smtplib.SMTP.login", side_effect=error):
            res = self._send_test_email()
        assert res.status_code == 400
        assert res.json["result"]["status"] is False
        assert ("Authentication failed for user 'cornelius': 535 5.7.8 Error: authentication failed"
                in res.json["result"]["error"]["message"])

    def test_send_test_email_connection_error(self):
        """A server that can not be reached is reported as a readable 400 error."""
        with mock.patch("smtplib.SMTP.ehlo", side_effect=ConnectionRefusedError(111, "Connection refused")):
            res = self._send_test_email()
        assert res.status_code == 400
        assert "Could not connect to 1.2.3.4:123: connection refused." in res.json["result"]["error"]["message"]

    def test_send_test_email_not_accepted(self):
        """A message the server did not accept is reported instead of returning a silent False."""
        self.smtp_mock.setdata(response={"recp@example.com": (550, "User unknown")})
        res = self._send_test_email()
        assert res.status_code == 400
        assert ("The server did not accept the message for recp@example.com."
                in res.json["result"]["error"]["message"])

    def test_describe_smtp_error(self):
        """Every kind of error the mail server or the network can raise gets its own message."""
        cert_error = ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED]")
        cert_error.verify_message = "unable to get local issuer certificate"
        version_error = ssl.SSLError(1, "[SSL: WRONG_VERSION_NUMBER] wrong version number")
        version_error.reason = "WRONG_VERSION_NUMBER"
        cases = [
            (smtplib.SMTPAuthenticationError(535, b"5.7.8 Error: authentication failed"),
             "Authentication failed for user 'helpdesk': 535 5.7.8 Error: authentication failed"),
            (smtplib.SMTPNotSupportedError("SMTP AUTH extension not supported by server."),
             "The server does not support authentication (SMTP AUTH). Check whether TLS must be enabled."),
            (smtplib.SMTPNotSupportedError("STARTTLS extension not supported by server."),
             "The server does not support STARTTLS."),
            (socket.gaierror(-2, "Name or service not known"),
             "Could not resolve the host name 'mx.example.com'."),
            (ConnectionRefusedError(111, "Connection refused"),
             "Could not connect to mx.example.com:587: connection refused."),
            (TimeoutError("timed out"),
             "Connection to mx.example.com:587 timed out after 10 seconds."),
            (cert_error,
             "TLS error: certificate verify failed: unable to get local issuer certificate"),
            (version_error,
             "TLS error: WRONG_VERSION_NUMBER. Check whether port and TLS mode (smtps:// or STARTTLS) match."),
            (smtplib.SMTPServerDisconnected("Connection unexpectedly closed"),
             "The server closed the connection unexpectedly. "
             "Check whether port and TLS mode (smtps:// or STARTTLS) match."),
            (smtplib.SMTPSenderRefused(553, b"5.7.1 Sender address rejected", "pi@example.com"),
             "The server refused the sender 'pi@example.com': 553 5.7.1 Sender address rejected"),
            (smtplib.SMTPRecipientsRefused({"x@example.com": (550, b"5.1.1 User unknown")}),
             "The server refused the recipient 'x@example.com': 550 5.1.1 User unknown"),
            (smtplib.SMTPDataError(554, b"5.6.0 Message rejected"),
             "The server rejected the message: 554 5.6.0 Message rejected"),
            (smtplib.SMTPResponseException(451, b"4.3.0 Try again later"),
             "SMTP error 451 4.3.0 Try again later"),
            (smtplib.SMTPException("something else"),
             "SMTP error: something else"),
        ]
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                self.assertEqual(expected, _describe_smtp_error(error, "smtp://mx.example.com", 587,
                                                                "helpdesk", 10))

    def test_describe_smtp_error_port_from_url(self):
        """A port in the server URL takes precedence over the port parameter, as when sending."""
        message = _describe_smtp_error(ConnectionRefusedError(111, "Connection refused"),
                                       "smtps://mx.example.com:465", 25, "", 10)
        self.assertEqual("Could not connect to mx.example.com:465: connection refused.", message)

    def test_send_smime_email(self):
        """Sending an S/MIME signed test email succeeds."""
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        res = self._send_test_email(extra_data={
            "smime": True,
            "private_key": "tests/testdata/ca/cakey.pem",
            "certificate": "tests/testdata/ca/cacert.pem",
        })
        assert res.status_code == 200
        assert res.json["result"]["value"] is True

        msg = self.smtp_mock.get_sent_message().decode('utf-8')
        assert "application/x-pkcs7-signature" in msg
        assert "smime.p7s" in msg

    def test_dont_send_email_on_smime_error(self):
        """When S/MIME signing fails with dont_send_on_error, no email is sent."""
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        res = self._send_test_email(extra_data={
            "smime": True,
            "dont_send_on_error": True,
            "private_key": "tests/testdata/ca/cakey.pem",
            "certificate": "tests/testdata/ca",
        })
        assert res.status_code == 400
        assert "S/MIME signature could not be created" in res.json["result"]["error"]["message"]
        assert self.smtp_mock.get_sent_message() is None

    def test_sent_email_text_content(self):
        """Verify the sender, recipient, subject and body passed to smtplib.sendmail."""
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        res = self._send_test_email()
        assert res.status_code == 200
        assert res.json["result"]["value"] is True

        # Check the envelope sender and recipient passed to smtplib.SMTP.sendmail
        assert self.smtp_mock.get_sent_sender() == "privacyidea@local"
        assert "recp@example.com" in self.smtp_mock.get_sent_recipient()

        # Check the actual email message content passed to smtplib.SMTP.sendmail
        raw_msg = self.smtp_mock.get_sent_message()
        parsed = email.message_from_string(raw_msg)
        assert parsed["Subject"] == "Test Email from privacyIDEA"
        assert parsed["From"] == "privacyidea@local"
        assert parsed["To"] == "recp@example.com"

        body = parsed.get_payload(decode=True).decode("utf-8")
        assert "This is a test email from privacyIDEA." in body
        assert "The configuration someServer is working." in body

    def test_password_not_overwritten_by_censored(self):
        """Updating an SMTP server with __CENSORED__ password must preserve the original."""
        # Create a server with a known password
        self._create_server()

        # Update the server, sending CENSORED as the password (simulating UI re-save)
        data = {
            "username": "cornelius",
            "password": CENSORED,
            "port": "123",
            "server": "1.2.3.4",
            "sender": "privacyidea@local",
            "description": "updated description",
        }
        with self.app.test_request_context(
                '/smtpserver/server1',
                method='POST',
                data=data,
                headers={'Authorization': self.at},
        ):
            res = self.app.full_dispatch_request()
        assert res.status_code == 200

        # Verify the password was NOT replaced with __CENSORED__ in the DB
        from privacyidea.lib.smtpserver import list_smtpservers
        servers = list_smtpservers(identifier="server1")
        server = servers["server1"]
        # The decrypted password should still be "secret" (the original)
        assert server["password"] == "secret"
        # Other fields should be updated
        assert server["description"] == "updated description"

    def test_private_key_password_censored_in_response(self):
        """GET /smtpserver/ must censor private_key_password if it has a value."""
        self._create_server(extra_data={"private_key_password": "pkpass"})
        res = self._list_servers()
        assert res.status_code == 200
        server_list = res.json["result"]["value"]
        server = server_list["server1"]
        assert server["private_key_password"] == CENSORED

    def test_private_key_password_not_overwritten_by_censored(self):
        """Updating with __CENSORED__ private_key_password must preserve the original."""
        # Create a server with a private_key_password
        self._create_server(extra_data={"private_key_password": "my_key_pass"})

        # Update the server, sending CENSORED for private_key_password (simulating UI re-save)
        data = {
            "username": "cornelius",
            "password": CENSORED,
            "port": "123",
            "server": "1.2.3.4",
            "sender": "privacyidea@local",
            "private_key_password": CENSORED,
            "description": "updated with censored pkpass",
        }
        with self.app.test_request_context(
                '/smtpserver/server1',
                method='POST',
                data=data,
                headers={'Authorization': self.at},
        ):
            res = self.app.full_dispatch_request()
        assert res.status_code == 200

        # Verify the private_key_password was NOT overwritten
        from privacyidea.lib.crypto import decryptPassword
        from privacyidea.models import db
        from privacyidea.models.server import SMTPServer as SMTPServerDB
        from sqlalchemy import select

        # Check raw DB value is still encrypted (not None or __CENSORED__)
        stmt = select(SMTPServerDB).filter(SMTPServerDB.identifier == "server1")
        db_server = db.session.execute(stmt).scalar_one()
        # The private_key_password in DB should still be a valid encrypted value
        assert db_server.private_key_password is not None
        assert db_server.private_key_password != ""
        assert db_server.private_key_password != CENSORED
        # Decrypting should give back the original
        assert decryptPassword(db_server.private_key_password) == "my_key_pass"
        # Other fields should be updated
        assert db_server.description == "updated with censored pkpass"

    def test_private_key_not_censored_in_response(self):
        """private_key holds the *path* to the S/MIME key file (not key material),
        so it is intentionally returned as-is and NOT censored, unlike password and
        private_key_password."""
        self._create_server(extra_data={"smime": "1",
                                        "private_key": "/etc/privacyidea/smime.key"})
        res = self._list_servers()
        assert res.status_code == 200
        server = res.json["result"]["value"]["server1"]
        # secrets are censored ...
        assert server["password"] == CENSORED
        # ... but the key-file path is returned unchanged
        assert server["private_key"] == "/etc/privacyidea/smime.key"

    def test_password_cleared_with_empty_string(self):
        """An empty password clears the stored password (only __CENSORED__ keeps
        it). This is the counterpart to test_password_not_overwritten_by_censored."""
        from privacyidea.lib.crypto import decryptPassword
        from privacyidea.models import db
        from privacyidea.models.server import SMTPServer as SMTPServerDB
        from sqlalchemy import select

        self._create_server(extra_data={"password": "to_be_cleared"})
        data = {
            "username": "cornelius",
            "password": "",
            "port": "123",
            "server": "1.2.3.4",
            "sender": "privacyidea@local",
            "description": "cleared password",
        }
        with self.app.test_request_context('/smtpserver/server1',
                                           method='POST',
                                           data=data,
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
        assert res.status_code == 200

        stmt = select(SMTPServerDB).filter(SMTPServerDB.identifier == "server1")
        db_server = db.session.execute(stmt).scalar_one()
        # the password was overwritten and now decrypts to the empty string
        assert decryptPassword(db_server.password) == ""
