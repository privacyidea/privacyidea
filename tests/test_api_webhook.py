# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the webhook REST API (privacyidea/api/webhook.py).

See https://github.com/privacyidea/privacyidea/issues/5751 (step 4.1)
"""
import responses

from privacyidea.lib.crypto import CENSORED
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from privacyidea.lib.webhook import get_webhook, set_webhook, AuthType
from privacyidea.models.webhook import Webhook

from .base import MyApiTestCase

URL = "https://hook.example.com/endpoint"


class WebhookAPITestCase(MyApiTestCase):
    """CRUD, censoring and the test endpoint."""

    def _cleanup(self):
        for webhook in Webhook.query.all():
            webhook.delete()

    def setUp(self):
        super().setUp()
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        super().tearDown()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _request(self, path, method="GET", data=None, auth=None):
        """Dispatch an authenticated request and return the response."""
        with self.app.test_request_context(
                path, method=method, data=data,
                headers={"Authorization": auth or self.at}):
            return self.app.full_dispatch_request()

    def _value(self, response, status=200):
        """Assert the request succeeded and return ``result.value``."""
        self.assertEqual(status, response.status_code, response.data)
        return response.json["result"]["value"]

    def _create(self, identifier="hook1", **extra):
        data = {"url": URL, "description": "my hook"}
        data.update(extra)
        return self._request(f"/webhook/{identifier}", "POST", data)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def test_01_create_and_list(self):
        webhook_id = self._value(self._create())
        self.assertGreater(webhook_id, 0)

        webhooks = self._value(self._request("/webhook/"))
        self.assertEqual(1, len(webhooks))
        self.assertEqual("hook1", webhooks[0]["identifier"])
        self.assertEqual(URL, webhooks[0]["url"])
        # Defaults applied by the library, surfaced through the API.
        self.assertEqual("POST", webhooks[0]["http_method"])
        self.assertEqual("application/json", webhooks[0]["content_type"])
        self.assertEqual(AuthType.NONE, webhooks[0]["auth_type"])
        self.assertEqual(3, webhooks[0]["timeout"])

    def test_02_list_is_empty_and_ordered(self):
        self.assertEqual([], self._value(self._request("/webhook/")))

        for identifier in ("zulu", "alpha", "mike"):
            self._create(identifier)
        webhooks = self._value(self._request("/webhook/"))
        self.assertEqual(["alpha", "mike", "zulu"],
                         [w["identifier"] for w in webhooks])

    def test_03_get_single(self):
        self._create("hook1")
        webhook = self._value(self._request("/webhook/hook1"))
        # A single GET returns the object itself, not a one-element list.
        self.assertIsInstance(webhook, dict)
        self.assertEqual("hook1", webhook["identifier"])

    def test_04_get_unknown_is_404(self):
        response = self._request("/webhook/nosuchhook")
        self.assertEqual(404, response.status_code, response.data)

    def test_05_update_is_partial(self):
        self._create("hook1", timeout=7)
        # Send only the description: everything else must survive.
        self._value(self._request("/webhook/hook1", "POST",
                                  {"description": "changed"}))
        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual("changed", webhook["description"])
        self.assertEqual(URL, webhook["url"])
        self.assertEqual(7, webhook["timeout"])

    def test_06_delete(self):
        self._create("hook1")
        self._value(self._request("/webhook/hook1", "DELETE"))
        self.assertEqual([], self._value(self._request("/webhook/")))

    def test_07_delete_unknown_is_404(self):
        response = self._request("/webhook/nosuchhook", "DELETE")
        self.assertEqual(404, response.status_code, response.data)

    def test_08_invalid_parameters_are_rejected(self):
        # The API does not re-implement validation, it lets set_webhook()
        # decide. These are the errors an admin is most likely to hit.
        cases = [
            ({"url": "ftp://example.com"}, "scheme"),
            ({"url": URL, "http_method": "TRACE"}, "method"),
            ({"url": URL, "auth_type": "kerberos"}, "auth type"),
            ({"url": URL, "timeout": "0"}, "timeout"),
            ({"url": URL, "content_type": "json"}, "legacy content type"),
            ({"url": URL, "auth_type": "basic"}, "basic without username"),
        ]
        for data, label in cases:
            with self.subTest(case=label):
                response = self._request("/webhook/bad", "POST", data)
                self.assertEqual(400, response.status_code, response.data)
        # None of the rejected requests may leave a row behind.
        self.assertEqual([], self._value(self._request("/webhook/")))

    def test_09_create_without_url_is_rejected(self):
        response = self._request("/webhook/hook1", "POST",
                                 {"description": "no url"})
        self.assertEqual(400, response.status_code, response.data)

    # ------------------------------------------------------------------
    # Secrets
    # ------------------------------------------------------------------

    def test_10_password_is_censored(self):
        self._create("hook1", auth_type=AuthType.BASIC,
                     username="user", password="s3cret")

        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual(CENSORED, webhook["password"])
        self.assertEqual("user", webhook["username"])
        # ...and in the list endpoint too.
        listed = self._value(self._request("/webhook/"))[0]
        self.assertEqual(CENSORED, listed["password"])

        # The real value is still stored and readable internally.
        self.assertEqual("s3cret", get_webhook("hook1")["password"])

    def test_11_unset_secret_stays_empty(self):
        # An empty secret must not be reported as __CENSORED__, otherwise
        # the UI shows a password where none is configured.
        self._create("hook1")
        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual("", webhook["password"])
        self.assertEqual("", webhook["client_key_password"])

    def test_12_censored_write_back_keeps_the_secret(self):
        """The UI reads a webhook, edits a field and posts it back."""
        self._create("hook1", auth_type=AuthType.BASIC,
                     username="user", password="s3cret")
        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual(CENSORED, webhook["password"])

        # Post the censored value straight back, with one real change.
        self._value(self._request("/webhook/hook1", "POST", {
            "auth_type": AuthType.BASIC, "username": "user",
            "password": webhook["password"], "description": "edited"}))

        self.assertEqual("s3cret", get_webhook("hook1")["password"])
        self.assertEqual("edited", get_webhook("hook1")["description"])

    def test_13_empty_string_clears_the_secret(self):
        self._create("hook1", auth_type=AuthType.BASIC,
                     username="user", password="s3cret")
        self._value(self._request("/webhook/hook1", "POST", {"password": ""}))
        self.assertEqual("", get_webhook("hook1")["password"])

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def test_14_headers_are_stored(self):
        self._create("hook1", **{"header.X-Api-Key": "abc",
                                 "header.X-Trace": "on"})
        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual({"X-Api-Key": "abc", "X-Trace": "on"},
                         webhook["headers"])
        self.assertEqual([], webhook["secret_headers"])

    def test_15_secret_header_is_censored_and_flagged(self):
        self._create("hook1", **{"header.X-Api-Key": "abc",
                                 "secret.header.X-Api-Key": "1",
                                 "header.X-Trace": "on"})
        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual(CENSORED, webhook["headers"]["X-Api-Key"])
        # A non-secret header stays readable.
        self.assertEqual("on", webhook["headers"]["X-Trace"])
        # The flag is reported so the UI can restore the checkbox.
        self.assertEqual(["X-Api-Key"], webhook["secret_headers"])
        self.assertEqual("abc", get_webhook("hook1")["headers"]["X-Api-Key"])

    def test_16_headers_are_replaced_when_sent(self):
        self._create("hook1", **{"header.A": "1", "header.B": "2"})
        self._request("/webhook/hook1", "POST", {"header.A": "9"})
        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual({"A": "9"}, webhook["headers"])

    def test_17_headers_survive_an_unrelated_update(self):
        # Sending no header.* parameter must not wipe the headers, or every
        # partial update through the API would silently drop them.
        self._create("hook1", **{"header.A": "1"})
        self._request("/webhook/hook1", "POST", {"description": "changed"})
        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual({"A": "1"}, webhook["headers"])

    def test_18_clear_headers(self):
        # Since "no header.* parameters" means "keep", removing the last
        # header needs an explicit signal.
        self._create("hook1", **{"header.A": "1"})
        self._request("/webhook/hook1", "POST", {"clear_headers": "1"})
        webhook = self._value(self._request("/webhook/hook1"))
        self.assertEqual({}, webhook["headers"])

    def test_19_censored_header_write_back_keeps_the_value(self):
        self._create("hook1", **{"header.X-Api-Key": "abc",
                                 "secret.header.X-Api-Key": "1"})
        webhook = self._value(self._request("/webhook/hook1"))

        # Write the censored value back, as the UI would.
        self._request("/webhook/hook1", "POST", {
            "header.X-Api-Key": webhook["headers"]["X-Api-Key"],
            "secret.header.X-Api-Key": "1"})

        stored = get_webhook("hook1")
        self.assertEqual("abc", stored["headers"]["X-Api-Key"])
        self.assertEqual(["X-Api-Key"], stored["secret_headers"])

    def test_19b_a_secret_flag_without_its_header_is_refused(self):
        """
        A ``secret.header.*`` is a property of a header of the set being sent, so it needs a
        ``header.*`` of the same name. Without one the request describes no state the server could
        produce - and read as "headers were sent, here are none" it deleted the whole stored set,
        which is what a client flipping only the encryption flag used to do.
        """
        self._create("hook1", **{"header.X-Api-Key": "abc",
                                 "secret.header.X-Api-Key": "1",
                                 "header.X-Trace": "on"})

        response = self._request("/webhook/hook1", "POST",
                                 {"secret.header.X-Api-Key": "1"})

        self.assertEqual(400, response.status_code, response.data)
        self.assertIn("secret.header.X-Api-Key", response.json["result"]["error"]["message"])
        # And nothing was written: both headers are still there.
        stored = get_webhook("hook1")
        self.assertEqual({"X-Api-Key": "abc", "X-Trace": "on"}, stored["headers"])
        self.assertEqual(["X-Api-Key"], stored["secret_headers"])

    def test_19c_a_flag_set_to_zero_needs_its_header_too(self):
        # "Not secret" is as much a property of a header being sent as "secret" is; a flag for a
        # header that is not in the request names nothing either way.
        self._create("hook1", **{"header.A": "1"})

        response = self._request("/webhook/hook1", "POST", {"secret.header.A": "0"})

        self.assertEqual(400, response.status_code, response.data)
        self.assertEqual({"A": "1"}, get_webhook("hook1")["headers"])

    def test_19d_a_flag_cannot_accompany_clear_headers(self):
        # Flagging a header while asking for every header to be removed contradicts itself.
        self._create("hook1", **{"header.A": "1", "secret.header.A": "1"})

        response = self._request("/webhook/hook1", "POST",
                                 {"clear_headers": "1", "secret.header.A": "1"})

        self.assertEqual(400, response.status_code, response.data)
        self.assertEqual(["A"], get_webhook("hook1")["secret_headers"])

    def test_19e_flags_with_their_headers_are_unaffected(self):
        # The rule only refuses a flag standing alone; the normal round-trip is untouched.
        self._create("hook1", **{"header.A": "1", "header.B": "2",
                                 "secret.header.A": "1", "secret.header.B": "0"})

        stored = get_webhook("hook1")
        self.assertEqual({"A": "1", "B": "2"}, stored["headers"])
        self.assertEqual(["A"], stored["secret_headers"])

    # ------------------------------------------------------------------
    # verify_tls
    # ------------------------------------------------------------------

    def test_20_verify_tls_survives_a_partial_update(self):
        # An absent verify_tls must mean "keep", never "False". Defaulting
        # it to False would silently disable certificate verification on
        # every unrelated edit.
        self._create("hook1")
        self.assertTrue(self._value(self._request("/webhook/hook1"))["verify_tls"])

        self._request("/webhook/hook1", "POST", {"description": "changed"})
        self.assertTrue(self._value(self._request("/webhook/hook1"))["verify_tls"])

    def test_21_verify_tls_can_be_toggled(self):
        self._create("hook1")
        for sent, expected in (("False", False), ("True", True),
                               ("0", False), ("1", True)):
            with self.subTest(sent=sent):
                self._request("/webhook/hook1", "POST", {"verify_tls": sent})
                webhook = self._value(self._request("/webhook/hook1"))
                self.assertEqual(expected, webhook["verify_tls"])

    # ------------------------------------------------------------------
    # Test endpoint
    # ------------------------------------------------------------------

    @responses.activate
    def test_22_test_endpoint_reports_the_remote_status(self):
        responses.add(responses.POST, URL, json={"ok": True}, status=200)
        self._create("hook1", default_payload='{"a": 1}')

        result = self._value(self._request("/webhook/hook1/test", "POST"))
        self.assertTrue(result["success"])
        self.assertEqual(200, result["status_code"])
        self.assertIn("ok", result["response"])
        self.assertIsNone(result["error"])
        self.assertEqual(1, len(responses.calls))

    @responses.activate
    def test_23_test_endpoint_uses_the_supplied_payload(self):
        responses.add(responses.POST, URL, status=200)
        self._create("hook1", default_payload='{"default": true}')

        self._value(self._request("/webhook/hook1/test", "POST",
                                  {"payload": '{"custom": true}'}))
        self.assertEqual('{"custom": true}', responses.calls[0].request.body)

    @responses.activate
    def test_24_failing_webhook_is_not_an_api_error(self):
        # The API call succeeded; the webhook did not. That distinction has
        # to survive to the client, so this is a 200 with success=False.
        responses.add(responses.POST, URL, body="boom", status=500)
        self._create("hook1", default_payload="x")

        result = self._value(self._request("/webhook/hook1/test", "POST"))
        self.assertFalse(result["success"])
        self.assertEqual(500, result["status_code"])
        self.assertEqual("HTTP 500", result["error"])

    def test_25_test_endpoint_on_unknown_webhook_is_404(self):
        # fire_webhook() swallows an unknown identifier into a result dict,
        # which is right for an event handler but wrong for an explicit
        # test request: nothing was tested, so this must be a 404.
        response = self._request("/webhook/nosuchhook/test", "POST")
        self.assertEqual(404, response.status_code, response.data)

    def test_26_audit_records_the_identifier_and_not_the_url(self):
        # The URL may embed a token in its path, so the audit log names the
        # webhook by its identifier instead. The audit log is readable by any
        # admin with auditlog rights, not only by the holder of webhook_read.
        secret_url = "https://hook.example.com/t/SUPERSECRETTOKEN"
        self._request("/webhook/audited", "POST",
                      data={"url": secret_url,
                            "auth_type": AuthType.HEADER,
                            "header.X-Webhook-Token": "LEAKME",
                            "secret.header.X-Webhook-Token": "1"})

        entry = self.find_most_recent_audit_entry(action="POST /webhook/<identifier>")
        self.assertIn("audited", entry["info"])
        serialised = str(entry)
        self.assertNotIn("SUPERSECRETTOKEN", serialised)
        self.assertNotIn("LEAKME", serialised)

    @responses.activate
    def test_27_audit_of_the_test_endpoint_names_the_identifier(self):
        secret_url = "https://hook.example.com/t/SUPERSECRETTOKEN"
        responses.add(responses.POST, secret_url, status=200)
        set_webhook("audited", url=secret_url)

        self._request("/webhook/audited/test", "POST")

        entry = self.find_most_recent_audit_entry(
            action="POST /webhook/<identifier>/test")
        self.assertIn("audited", entry["info"])
        self.assertNotIn("SUPERSECRETTOKEN", str(entry))


class WebhookAPIPolicyTestCase(MyApiTestCase):
    """End-to-end enforcement of webhook_read / webhook_write."""

    def _cleanup(self):
        for webhook in Webhook.query.all():
            webhook.delete()

    def setUp(self):
        super().setUp()
        self._cleanup()
        set_webhook("hook1", url=URL)

    def tearDown(self):
        self._cleanup()
        super().tearDown()

    def _request(self, path, method="GET", data=None):
        with self.app.test_request_context(
                path, method=method, data=data,
                headers={"Authorization": self.at}):
            return self.app.full_dispatch_request()

    #: (label, path, method, data) for every endpoint, grouped by right.
    READ_CALLS = [
        ("list", "/webhook/", "GET", None),
        ("get", "/webhook/hook1", "GET", None),
    ]
    WRITE_CALLS = [
        ("create", "/webhook/hook2", "POST", {"url": URL}),
        ("delete", "/webhook/hook1", "DELETE", None),
        ("test", "/webhook/hook1/test", "POST", None),
    ]

    def _assert_allowed(self, calls):
        # The 'test' call fires a real request, so stub the endpoint: this
        # class is about authorisation, not about transport.
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(responses.POST, URL, status=200)
            for label, path, method, data in calls:
                with self.subTest(call=label):
                    response = self._request(path, method, data)
                    self.assertNotEqual(403, response.status_code, response.data)

    def _assert_denied(self, calls):
        for label, path, method, data in calls:
            with self.subTest(call=label):
                response = self._request(path, method, data)
                self.assertEqual(403, response.status_code, response.data)

    def test_01_read_right_allows_read_but_not_write(self):
        set_policy("webhookReader", scope=SCOPE.ADMIN,
                   action=PolicyAction.WEBHOOKREAD)
        try:
            self._assert_allowed(self.READ_CALLS)
            self._assert_denied(self.WRITE_CALLS)
        finally:
            delete_policy("webhookReader")

    def test_02_write_right_allows_write_but_not_read(self):
        set_policy("webhookWriter", scope=SCOPE.ADMIN,
                   action=PolicyAction.WEBHOOKWRITE)
        try:
            self._assert_denied(self.READ_CALLS)
            # 'test' fires a real request; a connection error is still a
            # successful *authorisation*, which is all this asserts.
            self._assert_allowed(self.WRITE_CALLS)
        finally:
            delete_policy("webhookWriter")

    def test_03_unrelated_right_denies_everything(self):
        # Any admin policy at all turns off the implicit superuser default,
        # so an admin holding only a foreign right must be denied.
        set_policy("smtpAdmin", scope=SCOPE.ADMIN,
                   action=PolicyAction.SMTPSERVERREAD)
        try:
            self._assert_denied(self.READ_CALLS)
            self._assert_denied(self.WRITE_CALLS)
        finally:
            delete_policy("smtpAdmin")

    def test_04_no_policy_allows_everything(self):
        self._assert_allowed(self.READ_CALLS)
        self._assert_allowed(self.WRITE_CALLS)

    def test_05_unauthenticated_is_rejected(self):
        with self.app.test_request_context("/webhook/", method="GET"):
            response = self.app.full_dispatch_request()
        self.assertEqual(401, response.status_code, response.data)
