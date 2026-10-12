import datetime
import email
import os
import shutil
import tempfile
from unittest import mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from privacyidea.lib.crypto import encryptPassword, CENSORED
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
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

    def test_update_keeps_the_fields_that_are_not_passed(self):
        """An update that does not pass the user name, the sender or the description keeps the stored values, an
        empty value clears them."""
        from privacyidea.models import db
        from privacyidea.models.server import SMTPServer as SMTPServerDB
        from sqlalchemy import select

        def stored():
            db.session.expire_all()
            return db.session.execute(select(SMTPServerDB).filter(SMTPServerDB.identifier == "server1")).scalar_one()

        self._create_server()
        res = self._create_server(extra_data={"port": "587"})
        assert res.status_code == 200
        with self.app.test_request_context('/smtpserver/server1', method='POST',
                                           data={"server": "1.2.3.4", "port": "587"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
        assert res.status_code == 200
        server = stored()
        assert ("cornelius", "privacyidea@local", "myServer", 587) == (
            server.username, server.sender, server.description, server.port)

        with self.app.test_request_context('/smtpserver/server1', method='POST',
                                           data={"server": "1.2.3.4", "description": ""},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
        assert res.status_code == 200
        assert "" == stored().description
        assert "cornelius" == stored().username

    def _listed_definition(self, identifier: str) -> dict:
        with self.app.test_request_context("/smtpserver/", method="GET", headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        return res.json["result"]["value"][identifier]

    def _send_censored_test_email(self, body: dict) -> tuple[bool, list]:
        with mock.patch("smtplib.SMTP.login", return_value=(235, b"OK")) as login:
            with self.app.test_request_context("/smtpserver/send_test_email", method="POST", json=body,
                                               headers={"Authorization": self.at}):
                res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        return res.json["result"]["value"], login.call_args_list

    def test_test_email_of_a_saved_definition_logs_in_with_the_stored_password(self):
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        add_smtpserver("savedServer", server="mail.example.com", username="u", password="realsecret",
                       sender="privacyidea@local")
        self.addCleanup(delete_smtpserver, "savedServer")
        # The edit dialog loads the listed definition and posts it for the test, as both WebUIs do
        body = self._listed_definition("savedServer")
        self.assertEqual(CENSORED, body["password"])
        body.update(identifier="savedServer", recipient="recp@example.com")
        value, logins = self._send_censored_test_email(body)
        self.assertTrue(value)
        self.assertEqual([mock.call("u", "realsecret")], logins)

    def test_test_email_uses_a_password_typed_in_for_the_test(self):
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        add_smtpserver("savedServer2", server="mail.example.com", username="u", password="realsecret")
        self.addCleanup(delete_smtpserver, "savedServer2")
        body = self._listed_definition("savedServer2")
        body.update(identifier="savedServer2", recipient="recp@example.com", password="newsecret")
        _value, logins = self._send_censored_test_email(body)
        self.assertEqual([mock.call("u", "newsecret")], logins)

    def test_test_email_of_an_unknown_definition_does_not_log_in_with_the_placeholder(self):
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        body = {"identifier": "notSaved", "server": "mail.example.com", "username": "u", "password": CENSORED,
                "recipient": "recp@example.com"}
        _value, logins = self._send_censored_test_email(body)
        self.assertEqual([mock.call("u", "")], logins)

    def test_test_email_of_a_saved_definition_signs_with_the_stored_key_password(self):
        self.smtp_mock.setdata(response={"recp@example.com": (200, "OK")})
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        key_file, certificate_file = _write_smime_key_and_certificate(directory, "keysecret")
        add_smtpserver("smimeServer", server="mail.example.com", sender="privacyidea@local", smime=True,
                       dont_send_on_error=True, private_key=key_file, private_key_password="keysecret",
                       certificate=certificate_file)
        self.addCleanup(delete_smtpserver, "smimeServer")
        body = self._listed_definition("smimeServer")
        self.assertEqual(CENSORED, body["private_key_password"])
        body.update(identifier="smimeServer", recipient="recp@example.com")
        value, _logins = self._send_censored_test_email(body)
        self.assertTrue(value)
        self.assertIn("application/x-pkcs7-signature", self.smtp_mock.get_sent_message().decode())


def _write_smime_key_and_certificate(directory: str, key_password: str) -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "privacyidea@local")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                   .serial_number(x509.random_serial_number())
                   .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=1))
                   .sign(key, hashes.SHA256()))
    key_file = os.path.join(directory, "smime.key")
    certificate_file = os.path.join(directory, "smime.pem")
    with open(key_file, "wb") as key_output:
        key_output.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.BestAvailableEncryption(key_password.encode())))
    with open(certificate_file, "wb") as certificate_output:
        certificate_output.write(certificate.public_bytes(serialization.Encoding.PEM))
    return key_file, certificate_file
