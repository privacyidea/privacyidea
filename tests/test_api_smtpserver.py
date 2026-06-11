import email

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
        assert server1["password"] == "__CENSORED__"

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
        assert res.status_code == 200
        assert res.json["result"]["value"] is False
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
