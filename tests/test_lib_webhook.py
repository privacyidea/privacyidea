"""
Tests for privacyidea/lib/webhook.py -- CRUD operations on first-class
webhook configuration objects.

See https://github.com/privacyidea/privacyidea/issues/5751 (step 2.1)
"""
from privacyidea.lib.crypto import CENSORED, decryptPassword
from privacyidea.lib.error import ParameterError, ResourceNotFoundError
from privacyidea.lib.webhook import (
    AuthType, ContentType, HttpMethod, DEFAULT_TIMEOUT,
    delete_webhook, export_webhook, get_webhook, get_webhook_identifiers,
    get_webhook_object, get_webhooks, import_webhook, set_webhook,
)
from privacyidea.models.webhook import Webhook
from .base import MyTestCase


class WebhookCrudTestCase(MyTestCase):
    """CRUD cycle, validation and secret handling for webhook objects."""

    def _cleanup(self):
        for wh in Webhook.query.all():
            wh.delete()

    def setUp(self):
        super().setUp()
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        super().tearDown()

    # ------------------------------------------------------------------
    # Create / read
    # ------------------------------------------------------------------

    def test_create_minimal(self):
        """A webhook can be created with just an identifier and a URL."""
        wid = set_webhook("minimal", url="https://example.com/hook")
        self.assertIsInstance(wid, int)

        wh = get_webhook("minimal")
        self.assertEqual(wh["identifier"], "minimal")
        self.assertEqual(wh["url"], "https://example.com/hook")
        # Defaults
        self.assertEqual(wh["http_method"], HttpMethod.POST)
        self.assertEqual(wh["content_type"], ContentType.JSON)
        self.assertEqual(wh["auth_type"], AuthType.NONE)
        self.assertEqual(wh["timeout"], DEFAULT_TIMEOUT)
        self.assertTrue(wh["verify_tls"])
        self.assertEqual(wh["headers"], {})

    def test_create_full(self):
        """All configuration fields round-trip through set/get."""
        set_webhook(
            "full",
            url="https://siem.example.com/ingest",
            description="Ship events to the SIEM",
            http_method="PUT",
            content_type=ContentType.URLENCODED,
            default_payload='{"msg": "{logged_in_user}"}',
            auth_type=AuthType.BASIC,
            username="pi",
            password="s3cret",
            verify_tls=False,
            tls_ca_bundle="/etc/ssl/ca.pem",
            http_proxy="http://proxy:3128",
            https_proxy="http://proxy:3128",
            timeout=17,
        )

        wh = get_webhook("full")
        self.assertEqual(wh["description"], "Ship events to the SIEM")
        self.assertEqual(wh["http_method"], "PUT")
        self.assertEqual(wh["content_type"], ContentType.URLENCODED)
        self.assertEqual(wh["default_payload"], '{"msg": "{logged_in_user}"}')
        self.assertEqual(wh["auth_type"], AuthType.BASIC)
        self.assertEqual(wh["username"], "pi")
        self.assertEqual(wh["password"], "s3cret")  # decrypted on read
        self.assertFalse(wh["verify_tls"])
        self.assertEqual(wh["tls_ca_bundle"], "/etc/ssl/ca.pem")
        self.assertEqual(wh["http_proxy"], "http://proxy:3128")
        self.assertEqual(wh["timeout"], 17)

    def test_get_webhooks_lists_all_sorted(self):
        """get_webhooks() returns every webhook, ordered by identifier."""
        set_webhook("zulu", url="https://z.example.com")
        set_webhook("alpha", url="https://a.example.com")

        all_hooks = get_webhooks()
        self.assertEqual([h["identifier"] for h in all_hooks], ["alpha", "zulu"])

    def test_get_webhooks_filtered(self):
        """Filtering by identifier returns exactly one entry."""
        set_webhook("one", url="https://one.example.com")
        set_webhook("two", url="https://two.example.com")

        self.assertEqual(len(get_webhooks(identifier="one")), 1)
        self.assertEqual(get_webhooks(identifier="one")[0]["url"],
                         "https://one.example.com")
        self.assertEqual(get_webhooks(identifier="nope"), [])

    def test_get_webhook_identifiers(self):
        """The dropdown helper returns just the sorted names."""
        set_webhook("b", url="https://b.example.com")
        set_webhook("a", url="https://a.example.com")
        self.assertEqual(get_webhook_identifiers(), ["a", "b"])

    def test_get_unknown_webhook_raises(self):
        """Reading a non-existent webhook raises ResourceNotFoundError."""
        with self.assertRaises(ResourceNotFoundError):
            get_webhook("does-not-exist")
        with self.assertRaises(ResourceNotFoundError):
            get_webhook_object("does-not-exist")

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def test_update_existing(self):
        """Setting an existing identifier updates instead of creating."""
        first_id = set_webhook("hook", url="https://old.example.com")
        second_id = set_webhook("hook", url="https://new.example.com",
                                description="updated")

        self.assertEqual(first_id, second_id)
        self.assertEqual(len(get_webhooks()), 1)

        wh = get_webhook("hook")
        self.assertEqual(wh["url"], "https://new.example.com")
        self.assertEqual(wh["description"], "updated")

    def test_partial_update_keeps_other_fields(self):
        """Parameters left at None keep their stored value."""
        set_webhook("hook", url="https://example.com", username="pi",
                    password="s3cret", auth_type=AuthType.BASIC, timeout=9)

        set_webhook("hook", description="only the description changed")

        wh = get_webhook("hook")
        self.assertEqual(wh["description"], "only the description changed")
        self.assertEqual(wh["url"], "https://example.com")
        self.assertEqual(wh["username"], "pi")
        self.assertEqual(wh["password"], "s3cret")
        self.assertEqual(wh["timeout"], 9)

    def test_update_without_url_is_allowed(self):
        """url is only mandatory when creating."""
        set_webhook("hook", url="https://example.com")
        set_webhook("hook", timeout=30)
        self.assertEqual(get_webhook("hook")["timeout"], 30)

    def test_create_without_url_raises(self):
        """Creating a webhook without a URL is a ParameterError."""
        with self.assertRaises(ParameterError):
            set_webhook("no-url")

    # ------------------------------------------------------------------
    # Identifiers the API could store but never address again
    # ------------------------------------------------------------------

    def test_an_identifier_the_api_can_not_address_is_refused(self):
        """
        Every route but the listing puts the identifier in a path segment, which is Flask's
        single-segment string converter. A name the rule cannot match would be listed and then be
        unreadable, unsaveable, undeletable and untestable - see
        test_api_webhook.WebhookApiIdentifierTestCase for the round trip.
        """
        for identifier in ("team/siem", "a\\b", ".", "..", "with\tcontrol"):
            with self.subTest(identifier=identifier):
                with self.assertRaises(ParameterError):
                    set_webhook(identifier, url="https://example.com/hook")
                self.assertNotIn(identifier, get_webhook_identifiers())

    def test_names_that_survive_the_round_trip_are_still_accepted(self):
        # The restriction is about reachability, not about looking like an identifier: all of
        # these come back unchanged once the client percent-encodes them.
        for identifier in ("My Hook", "a.b", "...", "hook#1", "a?b", "Gr\u00fc\u00dfe"):
            with self.subTest(identifier=identifier):
                set_webhook(identifier, url="https://example.com/hook")
                self.assertIn(identifier, get_webhook_identifiers())

    def test_an_import_can_not_smuggle_one_in(self):
        # The import is the only way such a name gets in: the API cannot express it, because the
        # route that would create it is the route that cannot match it.
        with self.assertRaises(ParameterError):
            import_webhook({"team/siem": {"url": "https://example.com/hook"}})
        self.assertNotIn("team/siem", get_webhook_identifiers())

    # ------------------------------------------------------------------
    # Secrets
    # ------------------------------------------------------------------

    def test_password_is_encrypted_at_rest(self):
        """The password column holds ciphertext, not the plaintext."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.BASIC, username="pi", password="s3cret")

        stored = get_webhook_object("hook").password
        self.assertNotEqual(stored, "s3cret")
        self.assertEqual(decryptPassword(stored), "s3cret")

    def test_client_key_password_is_encrypted_at_rest(self):
        """The mTLS key password is encrypted too."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.MTLS,
                    client_certificate="/etc/ssl/client.pem",
                    client_key="/etc/ssl/client.key",
                    client_key_password="keypw")

        stored = get_webhook_object("hook").client_key_password
        self.assertNotEqual(stored, "keypw")
        self.assertEqual(decryptPassword(stored), "keypw")
        self.assertEqual(get_webhook("hook")["client_key_password"], "keypw")

    def test_censor_hides_secrets(self):
        """censor=True replaces secrets with the placeholder."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.BASIC, username="pi", password="s3cret")

        wh = get_webhook("hook", censor=True)
        self.assertEqual(wh["password"], CENSORED)
        # Non-secret fields are untouched.
        self.assertEqual(wh["username"], "pi")

    def test_censor_of_empty_secret_stays_empty(self):
        """An unset secret is reported as empty, not as censored."""
        set_webhook("hook", url="https://example.com")
        self.assertEqual(get_webhook("hook", censor=True)["password"], "")

    def test_censored_password_keeps_stored_value(self):
        """Writing back a censored password must not destroy the credential."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.BASIC, username="pi", password="s3cret")

        # Simulate a UI round-trip: read censored, write back unchanged.
        set_webhook("hook", auth_type=AuthType.BASIC, username="pi",
                    password=CENSORED)

        self.assertEqual(get_webhook("hook")["password"], "s3cret")

    def test_empty_password_clears_it(self):
        """An explicit empty string clears the stored password."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.BASIC, username="pi", password="s3cret")
        set_webhook("hook", auth_type=AuthType.BASIC, username="pi", password="")
        self.assertEqual(get_webhook("hook")["password"], "")

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def test_headers_are_stored(self):
        """Static headers round-trip through set/get."""
        set_webhook("hook", url="https://example.com",
                    headers={"X-Source": "privacyIDEA", "Accept": "*/*"})

        wh = get_webhook("hook")
        self.assertEqual(wh["headers"],
                         {"X-Source": "privacyIDEA", "Accept": "*/*"})
        self.assertEqual(wh["secret_headers"], [])

    def test_secret_header_is_encrypted_at_rest(self):
        """Header values listed in secret_headers are encrypted."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.HEADER,
                    headers={"Authorization": "Bearer tok", "X-Env": "prod"},
                    secret_headers={"Authorization"})

        rows = {h.key: h for h in get_webhook_object("hook").headers}
        self.assertTrue(rows["Authorization"].encrypted)
        self.assertNotEqual(rows["Authorization"].value, "Bearer tok")
        self.assertFalse(rows["X-Env"].encrypted)
        self.assertEqual(rows["X-Env"].value, "prod")

        # Reading decrypts transparently.
        wh = get_webhook("hook")
        self.assertEqual(wh["headers"]["Authorization"], "Bearer tok")
        self.assertEqual(wh["secret_headers"], ["Authorization"])

    def test_censor_hides_secret_header_values(self):
        """Secret header values are censored, plain ones are not."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.HEADER,
                    headers={"Authorization": "Bearer tok", "X-Env": "prod"},
                    secret_headers={"Authorization"})

        wh = get_webhook("hook", censor=True)
        self.assertEqual(wh["headers"]["Authorization"], CENSORED)
        self.assertEqual(wh["headers"]["X-Env"], "prod")

    def test_set_webhook_never_logs_the_url_or_a_secret_header(self):
        """The DEBUG entry log of a write must not carry either secret.

        Both slip past the name based hiding of log_with(): a token embedded in
        the URL path is not a named field at all, and a secret header is secret
        because secret_headers says so, not because "X-Webhook-Token" reads as
        sensitive.
        """
        with self.assertLogs("privacyidea.lib.webhook", level="DEBUG") as logs:
            set_webhook("hook",
                        url="https://example.com/t/SUPERSECRETTOKEN",
                        auth_type=AuthType.HEADER,
                        password="TOPSECRETPW",
                        headers={"X-Webhook-Token": "LEAKME"},
                        secret_headers={"X-Webhook-Token"})

        everything = "\n".join(logs.output)
        self.assertNotIn("SUPERSECRETTOKEN", everything)
        self.assertNotIn("LEAKME", everything)
        self.assertNotIn("TOPSECRETPW", everything)
        # The identifier is still reported, so the write itself is traceable.
        self.assertIn("'hook'", everything)

    def test_import_webhook_never_logs_the_url_or_a_secret_header(self):
        """import_webhook() reaches set_webhook() with the same secrets."""
        with self.assertLogs("privacyidea.lib.webhook", level="DEBUG") as logs:
            import_webhook({"hook": {
                "url": "https://example.com/t/SUPERSECRETTOKEN",
                "auth_type": AuthType.HEADER,
                "password": "TOPSECRETPW",
                "headers": {"X-Webhook-Token": "LEAKME"},
                "secret_headers": ["X-Webhook-Token"],
            }})

        everything = "\n".join(logs.output)
        self.assertNotIn("SUPERSECRETTOKEN", everything)
        self.assertNotIn("LEAKME", everything)
        self.assertNotIn("TOPSECRETPW", everything)
        self.assertIn("'hook'", everything)

    def test_headers_replace_removes_missing(self):
        """Passing a headers dict replaces the stored set entirely."""
        set_webhook("hook", url="https://example.com",
                    headers={"A": "1", "B": "2"})
        set_webhook("hook", headers={"A": "9"})

        self.assertEqual(get_webhook("hook")["headers"], {"A": "9"})

    def test_headers_none_keeps_existing(self):
        """Omitting headers leaves the stored headers alone."""
        set_webhook("hook", url="https://example.com", headers={"A": "1"})
        set_webhook("hook", description="unrelated change")
        self.assertEqual(get_webhook("hook")["headers"], {"A": "1"})

    def test_censored_header_value_is_kept(self):
        """A censored header value must not overwrite the stored secret."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.HEADER,
                    headers={"Authorization": "Bearer tok"},
                    secret_headers={"Authorization"})

        set_webhook("hook", auth_type=AuthType.HEADER,
                    headers={"Authorization": CENSORED},
                    secret_headers={"Authorization"})

        self.assertEqual(get_webhook("hook")["headers"]["Authorization"],
                         "Bearer tok")

    def test_censored_header_value_on_create_yields_an_empty_header(self):
        """
        There is nothing stored to keep when the header is new, so the row is
        created empty rather than dropped: the header name and its 'encrypted'
        flag are configuration too, and a header-authenticated webhook must not
        silently end up without any header.
        """
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.HEADER,
                    headers={"Authorization": CENSORED, "X-Env": "prod"},
                    secret_headers={"Authorization"})

        webhook = get_webhook("hook")
        self.assertEqual(webhook["headers"], {"Authorization": "", "X-Env": "prod"})
        self.assertEqual(webhook["secret_headers"], ["Authorization"])

    def test_renaming_a_secret_header_keeps_its_value(self):
        """
        The caller never holds a secret header's value, only the placeholder, and that means "keep
        what is stored under this name". Under a new name nothing is stored, so without being told
        about the rename the credential is created empty and the save still reports success.
        """
        set_webhook("siem", url="https://siem.example.com/ingest", headers={"X-Api-key": "s3cr3t"},
                    secret_headers={"X-Api-key"})

        set_webhook("siem", headers={"X-API-Key": CENSORED}, secret_headers={"X-API-Key"},
                    header_renames={"X-API-Key": "X-Api-key"})

        stored = get_webhook("siem", censor=False)
        self.assertEqual({"X-API-Key": "s3cr3t"}, stored["headers"])
        self.assertEqual(["X-API-Key"], stored["secret_headers"])

    def test_renaming_a_plain_header_keeps_its_value_too(self):
        set_webhook("siem", url="https://siem.example.com/ingest", headers={"X-Source": "privacyidea"})

        set_webhook("siem", headers={"X-Origin": CENSORED},
                    header_renames={"X-Origin": "X-Source"})

        self.assertEqual({"X-Origin": "privacyidea"}, get_webhook("siem")["headers"])

    def test_a_rename_may_be_sent_twice(self):
        # A double submit must not fail a request that has already done what it asked for.
        set_webhook("siem", url="https://siem.example.com/ingest", headers={"X-Api-key": "s3cr3t"},
                    secret_headers={"X-Api-key"})
        renamed = dict(headers={"X-API-Key": CENSORED}, secret_headers={"X-API-Key"},
                       header_renames={"X-API-Key": "X-Api-key"})

        set_webhook("siem", **renamed)
        set_webhook("siem", **renamed)

        self.assertEqual({"X-API-Key": "s3cr3t"}, get_webhook("siem", censor=False)["headers"])

    def test_a_rename_of_an_unknown_header_is_refused(self):
        set_webhook("siem", url="https://siem.example.com/ingest", headers={"X-Source": "privacyidea"})

        self.assertRaisesRegex(
            ParameterError, "no header named 'X-Nothing' is stored",
            set_webhook, "siem", headers={"X-New": CENSORED},
            header_renames={"X-New": "X-Nothing"})

    def test_a_rename_onto_an_existing_header_is_refused(self):
        # Two rows would claim one name, and which value survived would be an accident.
        set_webhook("siem", url="https://siem.example.com/ingest", headers={"A": "1", "B": "2"})

        self.assertRaisesRegex(
            ParameterError, "a header named 'B' already exists",
            set_webhook, "siem", headers={"A": "1", "B": CENSORED},
            header_renames={"B": "A"})

    def test_a_rename_without_a_header_set_is_refused(self):
        # The header set is replaced wholesale, so a rename on its own describes a state the next
        # write would undo.
        set_webhook("siem", url="https://siem.example.com/ingest", headers={"A": "1"})

        self.assertRaisesRegex(
            ParameterError, "requires sending the header set",
            set_webhook, "siem", description="x", header_renames={"B": "A"})

    def test_toggling_header_encryption_off(self):
        """Un-checking 'encrypted' decrypts the stored value in place."""
        set_webhook("hook", url="https://example.com",
                    auth_type=AuthType.HEADER,
                    headers={"Authorization": "Bearer tok"},
                    secret_headers={"Authorization"})

        # Censored value + empty secret set == "keep value, drop encryption".
        set_webhook("hook", auth_type=AuthType.HEADER,
                    headers={"Authorization": CENSORED},
                    secret_headers=set())

        row = {h.key: h for h in get_webhook_object("hook").headers}["Authorization"]
        self.assertFalse(row.encrypted)
        self.assertEqual(row.value, "Bearer tok")

    def test_toggling_header_encryption_on(self):
        """Checking 'encrypted' encrypts the stored value in place."""
        set_webhook("hook", url="https://example.com",
                    headers={"X-Api-Key": "plain"})
        set_webhook("hook", auth_type=AuthType.HEADER,
                    headers={"X-Api-Key": CENSORED},
                    secret_headers={"X-Api-Key"})

        row = {h.key: h for h in get_webhook_object("hook").headers}["X-Api-Key"]
        self.assertTrue(row.encrypted)
        self.assertNotEqual(row.value, "plain")
        self.assertEqual(get_webhook("hook")["headers"]["X-Api-Key"], "plain")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_empty_identifier_raises(self):
        with self.assertRaises(ParameterError):
            set_webhook("", url="https://example.com")
        with self.assertRaises(ParameterError):
            set_webhook("   ", url="https://example.com")

    def test_invalid_url_scheme_raises(self):
        for bad in ("ftp://example.com", "file:///etc/passwd", "example.com"):
            with self.assertRaises(ParameterError):
                set_webhook("bad", url=bad)

    def test_invalid_http_method_raises(self):
        with self.assertRaises(ParameterError):
            set_webhook("bad", url="https://example.com", http_method="TRACE")

    def test_http_method_is_normalised_to_upper(self):
        set_webhook("hook", url="https://example.com", http_method="patch")
        self.assertEqual(get_webhook("hook")["http_method"], "PATCH")

    def test_legacy_content_type_shorthand_is_rejected(self):
        """
        The pre-3.15 shorthands are not accepted here.

        Converting them is the migration's job for stored data, and the event
        handler's tolerant reader handles unmigrated inline options. A
        first-class webhook always carries a real MIME type, so 'json' must be
        rejected rather than silently stored and later sent as an invalid
        Content-Type header.
        """
        for shorthand in ("json", "urlencoded"):
            with self.assertRaises(ParameterError):
                set_webhook("bad", url="https://example.com",
                            content_type=shorthand)

    def test_arbitrary_mime_types_are_allowed(self):
        """Any real MIME type is accepted, not just JSON and urlencoded."""
        set_webhook("hook", url="https://example.com", content_type="text/plain")
        self.assertEqual(get_webhook("hook")["content_type"], "text/plain")

    def test_invalid_auth_type_raises(self):
        with self.assertRaises(ParameterError):
            set_webhook("bad", url="https://example.com", auth_type="oauth2")

    def test_auth_type_is_normalised_to_lower(self):
        set_webhook("hook", url="https://example.com", auth_type="BASIC",
                    username="pi")
        self.assertEqual(get_webhook("hook")["auth_type"], AuthType.BASIC)

    def test_basic_auth_requires_username(self):
        with self.assertRaises(ParameterError):
            set_webhook("bad", url="https://example.com",
                        auth_type=AuthType.BASIC)

    def test_mtls_requires_client_certificate(self):
        with self.assertRaises(ParameterError):
            set_webhook("bad", url="https://example.com",
                        auth_type=AuthType.MTLS)

    def test_header_auth_requires_a_header(self):
        with self.assertRaises(ParameterError):
            set_webhook("bad", url="https://example.com",
                        auth_type=AuthType.HEADER)

    def test_invalid_timeout_raises(self):
        for bad in (0, -1, "abc"):
            with self.assertRaises(ParameterError):
                set_webhook("bad", url="https://example.com", timeout=bad)

    def test_numeric_string_timeout_is_accepted(self):
        """The API hands over strings; they must be coerced."""
        set_webhook("hook", url="https://example.com", timeout="12")
        self.assertEqual(get_webhook("hook")["timeout"], 12)

    def test_failed_validation_does_not_create_a_row(self):
        """A rejected create must not leave a half-written webhook behind."""
        with self.assertRaises(ParameterError):
            set_webhook("bad", url="https://example.com", timeout=-5)
        self.assertEqual(get_webhooks(), [])

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def test_delete(self):
        set_webhook("hook", url="https://example.com")
        deleted_id = delete_webhook("hook")

        self.assertIsInstance(deleted_id, int)
        self.assertEqual(get_webhooks(), [])
        with self.assertRaises(ResourceNotFoundError):
            get_webhook("hook")

    def test_delete_cascades_to_headers(self):
        """Deleting a webhook removes its header rows."""
        from privacyidea.models.webhook import WebhookHeader

        set_webhook("hook", url="https://example.com",
                    headers={"A": "1", "B": "2"})
        webhook_id = get_webhook_object("hook").id
        self.assertEqual(
            WebhookHeader.query.filter_by(webhook_id=webhook_id).count(), 2)

        delete_webhook("hook")
        self.assertEqual(
            WebhookHeader.query.filter_by(webhook_id=webhook_id).count(), 0)

    def test_delete_unknown_raises(self):
        with self.assertRaises(ResourceNotFoundError):
            delete_webhook("does-not-exist")


class WebhookExportImportTestCase(MyTestCase):
    """Registry export/import of webhook objects (`pi-manage config export`)."""

    def _cleanup(self):
        for wh in Webhook.query.all():
            wh.delete()

    def setUp(self):
        super().setUp()
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        super().tearDown()

    @staticmethod
    def _create_full_webhook(identifier="siem"):
        set_webhook(
            identifier,
            url="https://siem.example.com/ingest",
            description="Ship events to the SIEM",
            http_method="PUT",
            content_type=ContentType.JSON,
            default_payload='{"event": "{action}"}',
            auth_type=AuthType.BASIC,
            username="pi",
            password="s3cret",
            verify_tls=False,
            tls_ca_bundle="/etc/ssl/ca.pem",
            client_certificate="/etc/ssl/client.pem",
            client_key="/etc/ssl/client.key",
            client_key_password="keypw",
            http_proxy="http://proxy:3128",
            https_proxy="http://proxy:3128",
            timeout=7,
            headers={"X-API-Key": "apikey", "X-Source": "privacyidea"},
            secret_headers=["X-API-Key"],
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def test_export_is_registered(self):
        """The exporter must be reachable through `pi-manage config export`."""
        from privacyidea.lib.utils.export import EXPORT_FUNCTIONS, IMPORT_FUNCTIONS
        # Importing the CLI module must be enough to register both functions.
        import privacyidea.cli.pimanage.pi_config  # noqa: F401

        self.assertIn("webhook", EXPORT_FUNCTIONS)
        self.assertIn("webhook", IMPORT_FUNCTIONS)

    def test_export_all_keyed_by_identifier(self):
        set_webhook("one", url="https://one.example.com")
        set_webhook("two", url="https://two.example.com")

        exported = export_webhook()
        self.assertEqual(sorted(exported), ["one", "two"])
        self.assertEqual(exported["one"]["url"], "https://one.example.com")

    def test_export_drops_id_and_identifier(self):
        """The payload must contain configuration only, not the object keys."""
        set_webhook("hook", url="https://example.com")
        config = export_webhook()["hook"]
        self.assertNotIn("id", config)
        self.assertNotIn("identifier", config)

    def test_export_single_by_name(self):
        set_webhook("one", url="https://one.example.com")
        set_webhook("two", url="https://two.example.com")
        self.assertEqual(list(export_webhook(name="two")), ["two"])

    def test_export_unknown_name_is_empty(self):
        set_webhook("one", url="https://one.example.com")
        self.assertEqual(export_webhook(name="nope"), {})

    def test_export_censors_all_secrets(self):
        self._create_full_webhook()
        config = export_webhook(censor=True)["siem"]

        self.assertEqual(config["password"], CENSORED)
        self.assertEqual(config["client_key_password"], CENSORED)
        self.assertEqual(config["headers"]["X-API-Key"], CENSORED)
        # Non-secret values stay readable.
        self.assertEqual(config["username"], "pi")
        self.assertEqual(config["headers"]["X-Source"], "privacyidea")

    def test_export_without_censor_returns_decrypted_secrets(self):
        """An uncensored export must be re-importable, so secrets are decrypted."""
        self._create_full_webhook()
        config = export_webhook()["siem"]

        self.assertEqual(config["password"], "s3cret")
        self.assertEqual(config["client_key_password"], "keypw")
        self.assertEqual(config["headers"]["X-API-Key"], "apikey")

    def test_export_empty_secrets_are_not_censored(self):
        """An unset secret must stay empty, not become the placeholder."""
        set_webhook("hook", url="https://example.com")
        config = export_webhook(censor=True)["hook"]
        self.assertEqual(config["password"], "")
        self.assertEqual(config["client_key_password"], "")

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def test_import_creates_webhook(self):
        import_webhook({"new": {"url": "https://new.example.com",
                                "http_method": "PATCH"}})
        webhook = get_webhook("new")
        self.assertEqual(webhook["url"], "https://new.example.com")
        self.assertEqual(webhook["http_method"], "PATCH")

    def test_import_single_by_name(self):
        import_webhook({"one": {"url": "https://one.example.com"},
                        "two": {"url": "https://two.example.com"}},
                       name="two")
        self.assertEqual(get_webhook_identifiers(), ["two"])

    def test_import_ignores_unknown_keys(self):
        """A hand-edited export must not abort the whole import."""
        import_webhook({"new": {"url": "https://new.example.com",
                                "id": 42,
                                "identifier": "new",
                                "not_a_parameter": "boom"}})
        self.assertEqual(get_webhook("new")["url"], "https://new.example.com")

    def test_uncensored_export_roundtrips(self):
        """export -> delete -> import must restore the webhook byte for byte."""
        self._create_full_webhook()
        exported = export_webhook()
        delete_webhook("siem")

        import_webhook(exported)
        self.assertEqual(export_webhook(), exported)

    def test_uncensored_import_sets_new_secrets(self):
        """Importing clear-text secrets over an existing webhook replaces them."""
        self._create_full_webhook()
        exported = export_webhook()
        exported["siem"]["password"] = "rotated"
        exported["siem"]["headers"]["X-API-Key"] = "rotated-key"

        import_webhook(exported)
        webhook = get_webhook("siem")
        self.assertEqual(webhook["password"], "rotated")
        self.assertEqual(webhook["headers"]["X-API-Key"], "rotated-key")
        # ...and the rotated header is still stored encrypted.
        self.assertIn("X-API-Key", webhook["secret_headers"])

    def test_censored_import_preserves_existing_secrets(self):
        """Re-importing a censored export must not wipe stored credentials."""
        self._create_full_webhook()
        censored = export_webhook(censor=True)
        # Change something else so the import definitely writes the row.
        censored["siem"]["description"] = "updated"

        import_webhook(censored)
        webhook = get_webhook("siem")
        self.assertEqual(webhook["description"], "updated")
        self.assertEqual(webhook["password"], "s3cret")
        self.assertEqual(webhook["client_key_password"], "keypw")
        self.assertEqual(webhook["headers"]["X-API-Key"], "apikey")
        self.assertIn("X-API-Key", webhook["secret_headers"])

    def test_censored_import_on_a_fresh_instance_leaves_secrets_empty(self):
        """
        A censored export carries no secret. Importing it where the webhook is
        unknown must still work; the credential simply has to be entered once.
        """
        self._create_full_webhook()
        censored = export_webhook(censor=True)
        delete_webhook("siem")

        import_webhook(censored)
        webhook = get_webhook("siem")
        self.assertEqual(webhook["url"], "https://siem.example.com/ingest")
        self.assertEqual(webhook["password"], "")
        self.assertEqual(webhook["client_key_password"], "")
        # The non-secret header survives, the secret one is stored empty.
        self.assertEqual(webhook["headers"]["X-Source"], "privacyidea")
        self.assertEqual(webhook["headers"]["X-API-Key"], "")

    def test_import_of_empty_data_is_a_noop(self):
        import_webhook({})
        self.assertEqual(get_webhook_identifiers(), [])
