"""
Tests for the Webhook and WebhookHeader database models.

See https://github.com/privacyidea/privacyidea/issues/5751 (step 1.1)
"""
from privacyidea.lib.crypto import encryptPassword, decryptPassword
from privacyidea.models import db
from privacyidea.models.webhook import Webhook, WebhookHeader
from .base import MyTestCase


class WebhookModelTestCase(MyTestCase):
    """Test the Webhook and WebhookHeader SQLAlchemy models directly."""

    def _cleanup_webhooks(self):
        """Remove all webhooks so each test starts clean."""
        for wh in Webhook.query.all():
            wh.delete()

    def setUp(self):
        super().setUp()
        self._cleanup_webhooks()

    def tearDown(self):
        self._cleanup_webhooks()
        super().tearDown()

    # ------------------------------------------------------------------
    # Webhook CRUD
    # ------------------------------------------------------------------

    def test_create_webhook_minimal(self):
        """A webhook can be created with only the required fields."""
        wh = Webhook(identifier="test-hook", url="https://siem.example.com/ingest")
        wh_id = wh.save()
        self.assertIsNotNone(wh_id)
        self.assertGreater(wh_id, 0)

        loaded = db.session.get(Webhook, wh_id)
        self.assertEqual(loaded.identifier, "test-hook")
        self.assertEqual(loaded.url, "https://siem.example.com/ingest")
        # Check defaults
        self.assertEqual(loaded.http_method, "POST")
        self.assertEqual(loaded.content_type, "application/json")
        self.assertIsNone(loaded.default_payload)
        self.assertEqual(loaded.auth_type, "none")
        self.assertTrue(loaded.verify_tls)
        self.assertEqual(loaded.timeout, 3)

    def test_create_webhook_all_fields(self):
        """A webhook can be created with all fields populated."""
        wh = Webhook(
            identifier="full-hook",
            description="A fully configured webhook",
            url="https://siem.example.com/api/v2/events",
            http_method="PUT",
            content_type="application/x-www-form-urlencoded",
            default_payload='{"event": "{event_type}"}',
            auth_type="basic",
            username="apiuser",
            password="encrypted-secret",
            verify_tls=False,
            tls_ca_bundle="/etc/ssl/custom-ca.pem",
            client_certificate="/etc/ssl/client.crt",
            client_key="/etc/ssl/client.key",
            client_key_password="key-pass",
            http_proxy="http://proxy:8080",
            https_proxy="https://proxy:8443",
            timeout=5,
        )
        wh_id = wh.save()
        self.assertGreater(wh_id, 0)

        loaded = db.session.get(Webhook, wh_id)
        self.assertEqual(loaded.description, "A fully configured webhook")
        self.assertEqual(loaded.http_method, "PUT")
        self.assertEqual(loaded.content_type, "application/x-www-form-urlencoded")
        self.assertEqual(loaded.default_payload, '{"event": "{event_type}"}')
        self.assertEqual(loaded.auth_type, "basic")
        self.assertEqual(loaded.username, "apiuser")
        self.assertEqual(loaded.password, "encrypted-secret")
        self.assertFalse(loaded.verify_tls)
        self.assertEqual(loaded.tls_ca_bundle, "/etc/ssl/custom-ca.pem")
        self.assertEqual(loaded.client_certificate, "/etc/ssl/client.crt")
        self.assertEqual(loaded.client_key, "/etc/ssl/client.key")
        self.assertEqual(loaded.client_key_password, "key-pass")
        self.assertEqual(loaded.http_proxy, "http://proxy:8080")
        self.assertEqual(loaded.https_proxy, "https://proxy:8443")
        self.assertEqual(loaded.timeout, 5)

    def test_identifier_unique_constraint(self):
        """Two webhooks cannot share the same identifier."""
        wh1 = Webhook(identifier="unique-hook", url="https://a.example.com")
        wh1.save()

        wh2 = Webhook(identifier="unique-hook", url="https://b.example.com")
        with self.assertRaises(Exception):
            wh2.save()
        db.session.rollback()

    def test_update_webhook(self):
        """An existing webhook can be updated."""
        wh = Webhook(identifier="update-hook", url="https://old.example.com")
        wh_id = wh.save()

        loaded = db.session.get(Webhook, wh_id)
        loaded.url = "https://new.example.com"
        loaded.timeout = 10
        loaded.save()

        reloaded = db.session.get(Webhook, wh_id)
        self.assertEqual(reloaded.url, "https://new.example.com")
        self.assertEqual(reloaded.timeout, 10)

    def test_delete_webhook(self):
        """Deleting a webhook removes it from the database."""
        wh = Webhook(identifier="delete-me", url="https://delete.example.com")
        wh_id = wh.save()

        loaded = db.session.get(Webhook, wh_id)
        self.assertIsNotNone(loaded)

        ret = loaded.delete()
        self.assertEqual(ret, wh_id)

        gone = db.session.get(Webhook, wh_id)
        self.assertIsNone(gone)

    def test_get_dict(self):
        """The get() method returns a complete configuration dictionary."""
        wh = Webhook(
            identifier="dict-hook",
            url="https://siem.example.com",
            http_method="POST",
            auth_type="basic",
            username="user",
            password="pass",
            timeout=5,
        )
        wh.save()

        d = wh.get()
        self.assertEqual(d["identifier"], "dict-hook")
        self.assertEqual(d["url"], "https://siem.example.com")
        self.assertEqual(d["http_method"], "POST")
        self.assertEqual(d["auth_type"], "basic")
        self.assertEqual(d["username"], "user")
        self.assertEqual(d["password"], "pass")
        self.assertEqual(d["timeout"], 5)
        # headers key should be present (empty dict when no headers)
        self.assertIsInstance(d["headers"], dict)
        self.assertEqual(len(d["headers"]), 0)

    # ------------------------------------------------------------------
    # WebhookHeader CRUD
    # ------------------------------------------------------------------

    def test_create_header(self):
        """Headers can be added to a webhook."""
        wh = Webhook(identifier="header-hook", url="https://h.example.com")
        wh_id = wh.save()

        h1 = WebhookHeader(webhook_id=wh_id, key="X-API-Key",
                           value="secret123", encrypted=False)
        self.assertIsNotNone(h1.id)
        self.assertGreater(h1.id, 0)

        h2 = WebhookHeader(webhook_id=wh_id, key="X-Custom",
                           value="plain", encrypted=False)
        self.assertIsNotNone(h2.id)

        # Verify via the parent relationship
        loaded = db.session.get(Webhook, wh_id)
        headers = loaded.header_dict
        self.assertEqual(len(headers), 2)
        self.assertEqual(headers["X-API-Key"], "secret123")
        self.assertEqual(headers["X-Custom"], "plain")

    def test_header_encrypted_round_trip(self):
        """Encrypted header values are decrypted when read via header_dict."""
        wh = Webhook(identifier="enc-header-hook", url="https://e.example.com")
        wh_id = wh.save()

        secret = "Bearer my-super-secret-token"
        encrypted_secret = encryptPassword(secret)

        WebhookHeader(webhook_id=wh_id, key="Authorization",
                      value=encrypted_secret, encrypted=True)

        loaded = db.session.get(Webhook, wh_id)
        headers = loaded.header_dict
        self.assertEqual(headers["Authorization"], secret)

    def test_an_undecryptable_header_reads_as_empty_not_as_ciphertext(self):
        """
        After an enckey change, or a restore from a backup without it, a stored header value can no
        longer be decrypted. Handing the ciphertext back would send it to the endpoint as the header
        value and write it into an uncensored export, where a re-import encrypts it a second time.
        An empty credential fails the delivery visibly; a wrong one fails it confusingly.
        """
        wh = Webhook(identifier="stale-key-hook", url="https://e.example.com")
        wh_id = wh.save()
        WebhookHeader(webhook_id=wh_id, key="Authorization",
                      value="not-something-this-key-can-decrypt", encrypted=True)

        loaded = db.session.get(Webhook, wh_id)

        self.assertEqual("", loaded.header_dict["Authorization"])

    def test_header_in_get_dict(self):
        """The get() dict includes headers."""
        wh = Webhook(identifier="get-header-hook", url="https://g.example.com")
        wh_id = wh.save()

        WebhookHeader(webhook_id=wh_id, key="X-Tenant", value="acme")

        d = wh.get()
        self.assertIn("X-Tenant", d["headers"])
        self.assertEqual(d["headers"]["X-Tenant"], "acme")

    def test_cascade_delete_removes_headers(self):
        """Deleting a webhook also deletes its headers."""
        wh = Webhook(identifier="cascade-hook", url="https://c.example.com")
        wh_id = wh.save()

        h1_id = WebhookHeader(webhook_id=wh_id, key="H1", value="v1").id
        h2_id = WebhookHeader(webhook_id=wh_id, key="H2", value="v2").id

        # Verify headers exist
        self.assertIsNotNone(db.session.get(WebhookHeader, h1_id))
        self.assertIsNotNone(db.session.get(WebhookHeader, h2_id))

        # Delete the parent
        loaded = db.session.get(Webhook, wh_id)
        loaded.delete()

        # Headers should be gone
        self.assertIsNone(db.session.get(WebhookHeader, h1_id))
        self.assertIsNone(db.session.get(WebhookHeader, h2_id))

    def test_query_by_identifier(self):
        """Webhooks can be queried by identifier."""
        Webhook(identifier="query-hook-1", url="https://q1.example.com").save()
        Webhook(identifier="query-hook-2", url="https://q2.example.com").save()

        result = Webhook.query.filter_by(identifier="query-hook-1").first()
        self.assertIsNotNone(result)
        self.assertEqual(result.url, "https://q1.example.com")

        all_hooks = Webhook.query.all()
        self.assertGreaterEqual(len(all_hooks), 2)

    def test_multiple_headers_same_webhook(self):
        """Multiple headers can be attached to the same webhook."""
        wh = Webhook(identifier="multi-header", url="https://m.example.com")
        wh_id = wh.save()

        for i in range(5):
            WebhookHeader(webhook_id=wh_id, key=f"X-Header-{i}",
                          value=f"value-{i}")

        loaded = db.session.get(Webhook, wh_id)
        headers = loaded.header_dict
        self.assertEqual(len(headers), 5)
        for i in range(5):
            self.assertEqual(headers[f"X-Header-{i}"], f"value-{i}")
