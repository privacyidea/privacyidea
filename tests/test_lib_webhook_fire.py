"""
Tests for the transport layer of privacyidea/lib/webhook.py -- fire_webhook()
and test_webhook().

See https://github.com/privacyidea/privacyidea/issues/5751 (step 2.2)

Note the aliased import of ``test_webhook``: without it pytest would try to
collect the library function itself as a test case.
"""
import json
import ssl
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch

import requests
import responses
from sqlalchemy import update

from privacyidea.lib.crypto import encryptPassword
from privacyidea.lib.webhook import (
    AuthType, ContentType, MAX_RESPONSE_BYTES, MAX_RESPONSE_LENGTH,
    _mtls_ssl_context, _read_response_text, fire_webhook, get_webhook, set_webhook,
    test_webhook as run_webhook_test,
)
from privacyidea.models import db
from privacyidea.models.webhook import Webhook, WebhookHeader
from .base import MyTestCase

URL = "https://hook.example.com/endpoint"


class FireWebhookTestCase(MyTestCase):
    """Transport behaviour of fire_webhook()."""

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
    # Happy path
    # ------------------------------------------------------------------

    @responses.activate
    def test_simple_post(self):
        """A POST is sent and a 2xx is reported as success."""
        responses.add(responses.POST, URL, json={"ok": True}, status=200)
        set_webhook("hook", url=URL)

        result = fire_webhook("hook", payload='{"a": 1}')

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertIsNone(result["error"])
        self.assertIn("ok", result["response"])

        self.assertEqual(len(responses.calls), 1)
        request = responses.calls[0].request
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.body, '{"a": 1}')
        self.assertEqual(request.headers["Content-Type"], ContentType.JSON)

    @responses.activate
    def test_configured_method_is_used(self):
        """The webhook's http_method drives the request."""
        responses.add(responses.PUT, URL, status=204)
        set_webhook("hook", url=URL, http_method="PUT")

        result = fire_webhook("hook", payload="x")

        self.assertTrue(result["success"])
        self.assertEqual(responses.calls[0].request.method, "PUT")

    @responses.activate
    def test_get_without_body(self):
        """A webhook without any payload sends no body and no Content-Type."""
        responses.add(responses.GET, URL, status=200)
        set_webhook("hook", url=URL, http_method="GET")

        result = fire_webhook("hook")

        self.assertTrue(result["success"])
        request = responses.calls[0].request
        self.assertIsNone(request.body)
        self.assertNotIn("Content-Type", request.headers)

    # ------------------------------------------------------------------
    # Payload resolution
    # ------------------------------------------------------------------

    @responses.activate
    def test_default_payload_is_used(self):
        """With no caller payload, the webhook's default_payload is sent."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, default_payload='{"from": "default"}')

        fire_webhook("hook")

        self.assertEqual(responses.calls[0].request.body, '{"from": "default"}')

    @responses.activate
    def test_caller_payload_overrides_default(self):
        """An explicit payload beats the stored default."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, default_payload='{"from": "default"}')

        fire_webhook("hook", payload='{"from": "caller"}')

        self.assertEqual(responses.calls[0].request.body, '{"from": "caller"}')

    @responses.activate
    def test_dict_payload_is_json_encoded(self):
        """A dict is serialised to JSON when the content type is JSON."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, content_type=ContentType.JSON)

        fire_webhook("hook", payload={"a": 1, "b": "two"})

        self.assertEqual(json.loads(responses.calls[0].request.body),
                         {"a": 1, "b": "two"})

    @responses.activate
    def test_dict_payload_is_form_encoded(self):
        """A dict is form-encoded when the content type is urlencoded."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, content_type=ContentType.URLENCODED)

        fire_webhook("hook", payload={"a": "1"})

        body = responses.calls[0].request.body
        self.assertEqual(body, "a=1")
        self.assertEqual(responses.calls[0].request.headers["Content-Type"],
                         ContentType.URLENCODED)

    # ------------------------------------------------------------------
    # Headers and authentication
    # ------------------------------------------------------------------

    @responses.activate
    def test_static_headers_are_sent(self):
        """Configured headers are attached to the request."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, headers={"X-Source": "privacyIDEA"})

        fire_webhook("hook", payload="x")

        self.assertEqual(responses.calls[0].request.headers["X-Source"],
                         "privacyIDEA")

    @responses.activate
    def test_encrypted_header_is_sent_decrypted(self):
        """A secret header reaches the endpoint in clear text."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, auth_type=AuthType.HEADER,
                    headers={"Authorization": "Bearer s3cret"},
                    secret_headers={"Authorization"})

        fire_webhook("hook", payload="x")

        self.assertEqual(responses.calls[0].request.headers["Authorization"],
                         "Bearer s3cret")

    @responses.activate
    def test_basic_auth_is_sent(self):
        """Basic auth produces an Authorization header."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, auth_type=AuthType.BASIC,
                    username="pi", password="s3cret")

        fire_webhook("hook", payload="x")

        header = responses.calls[0].request.headers["Authorization"]
        self.assertTrue(header.startswith("Basic "))

    @responses.activate
    def test_explicit_content_type_header_wins(self):
        """A configured Content-Type header is not overwritten."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, content_type=ContentType.JSON,
                    headers={"Content-Type": "application/xml"})

        fire_webhook("hook", payload="<x/>")

        self.assertEqual(responses.calls[0].request.headers["Content-Type"],
                         "application/xml")

    @responses.activate
    def test_a_content_type_header_in_another_case_wins_too(self):
        """HTTP header names are case-insensitive, so "content-type" is the same header."""
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, content_type=ContentType.JSON,
                    headers={"content-type": "application/cloudevents+json"})

        fire_webhook("hook", payload={"a": 1})

        sent = responses.calls[0].request.headers
        self.assertEqual("application/cloudevents+json", sent["Content-Type"])
        self.assertEqual(1, sum(1 for name in sent if name.lower() == "content-type"))

    # ------------------------------------------------------------------
    # TLS, proxy and timeout wiring
    # ------------------------------------------------------------------

    def _capture_kwargs(self, identifier, **set_kwargs):
        """Fire a webhook with requests.request patched, return the kwargs."""
        set_webhook(identifier, url=URL, **set_kwargs)
        with patch("privacyidea.lib.webhook.requests.request") as mock_request:
            mock_request.return_value.ok = True
            mock_request.return_value.status_code = 200
            # The body is read in parts from the raw response, see _read_response_text()
            mock_request.return_value.raw.read1.return_value = b""
            mock_request.return_value.encoding = "utf-8"
            fire_webhook(identifier, payload="x")
        return mock_request.call_args

    def test_verify_tls_true_by_default(self):
        args = self._capture_kwargs("hook")
        self.assertTrue(args.kwargs["verify"])

    def test_verify_tls_disabled(self):
        args = self._capture_kwargs("hook", verify_tls=False)
        self.assertFalse(args.kwargs["verify"])

    def test_ca_bundle_is_used_as_verify(self):
        args = self._capture_kwargs("hook", tls_ca_bundle="/etc/ssl/ca.pem")
        self.assertEqual(args.kwargs["verify"], "/etc/ssl/ca.pem")

    def test_disabled_verification_beats_ca_bundle(self):
        """Turning verification off must not be undone by a stored bundle."""
        args = self._capture_kwargs("hook", verify_tls=False,
                                    tls_ca_bundle="/etc/ssl/ca.pem")
        self.assertFalse(args.kwargs["verify"])

    def test_proxies_are_forwarded(self):
        args = self._capture_kwargs("hook", http_proxy="http://p:3128",
                                    https_proxy="http://s:3128")
        self.assertEqual(args.kwargs["proxies"],
                         {"http": "http://p:3128", "https": "http://s:3128"})

    def test_no_proxies_key_when_unset(self):
        """With no proxy configured, requests is told 'no proxy'."""
        args = self._capture_kwargs("hook")
        self.assertIsNone(args.kwargs["proxies"])

    def test_timeout_is_forwarded(self):
        """The timeout limits the connection and the wait for the first data together."""
        args = self._capture_kwargs("hook", timeout=11)
        self.assertEqual(args.kwargs["timeout"].total, 11)
        self.assertTrue(args.kwargs["stream"])

    def test_mtls_cert_tuple_is_forwarded(self):
        args = self._capture_kwargs(
            "hook", auth_type=AuthType.MTLS,
            client_certificate="/etc/ssl/client.pem",
            client_key="/etc/ssl/client.key")
        self.assertEqual(args.kwargs["cert"],
                         ("/etc/ssl/client.pem", "/etc/ssl/client.key"))

    def test_mtls_without_key_forwards_single_path(self):
        args = self._capture_kwargs(
            "hook", auth_type=AuthType.MTLS,
            client_certificate="/etc/ssl/combined.pem")
        self.assertEqual(args.kwargs["cert"], "/etc/ssl/combined.pem")

    def test_mtls_with_encrypted_key_uses_ssl_context(self):
        """
        requests' cert= cannot carry a key password, so an encrypted client
        key must be loaded into an SSLContext and mounted on a Session.
        """
        set_webhook("hook", url=URL, auth_type=AuthType.MTLS,
                    client_certificate="/etc/ssl/client.pem",
                    client_key="/etc/ssl/client.key",
                    client_key_password="keypw")

        with patch("privacyidea.lib.webhook.ssl.create_default_context") as ctx, \
                patch("privacyidea.lib.webhook.requests.Session") as session_cls:
            session = session_cls.return_value
            session.request.return_value.ok = True
            session.request.return_value.status_code = 200
            # The body is read in parts from the raw response, see _read_response_text()
            session.request.return_value.raw.read1.return_value = b""
            session.request.return_value.encoding = "utf-8"

            result = fire_webhook("hook", payload="x")

        self.assertTrue(result["success"])
        # The key was loaded with its password...
        ctx.return_value.load_cert_chain.assert_called_once_with(
            "/etc/ssl/client.pem", "/etc/ssl/client.key", password="keypw")
        # ...an adapter was mounted for https...
        session.mount.assert_called_once()
        self.assertEqual(session.mount.call_args.args[0], "https://")
        # ...the request went through the session, not the module function...
        session.request.assert_called_once()
        # ...and cert= was NOT also passed (it cannot carry the password).
        self.assertIsNone(session.request.call_args.kwargs["cert"])
        # The session is closed again.
        session.close.assert_called_once()

    def test_a_ca_bundle_stays_the_only_trust_anchor_with_an_encrypted_key(self):
        """
        The context this path builds has to trust what the ordinary path trusts, no more.

        requests starts from urllib3's create_urllib3_context(), which loads no certificates, so
        a bundle passed to verify= is the only anchor. ssl.create_default_context() loads the
        system store first, and urllib3 then *adds* the bundle to it - measured here as 122
        anchors instead of 1. An administrator pinning an internal CA would have gone on trusting
        every public CA, just because the client key carries a password.
        """
        bundle = "tests/testdata/ca/cacert.pem"
        set_webhook("hook", url=URL, auth_type=AuthType.MTLS,
                    client_certificate="/etc/ssl/client.pem",
                    client_key="/etc/ssl/client.key",
                    client_key_password="keypw",
                    tls_ca_bundle=bundle)

        # Only the chain loading is mocked away (it would need real key files); the context
        # itself is the real one, so its trust anchors can be counted.
        with patch("ssl.SSLContext.load_cert_chain"):
            context = _mtls_ssl_context(get_webhook("hook"), bundle, "keypw")

        self.assertEqual(1, len(context.get_ca_certs()))
        self.assertTrue(context.check_hostname)

    def test_without_a_bundle_the_system_store_still_applies(self):
        # The other half: no bundle configured means the default trust, exactly as before.
        set_webhook("hook", url=URL, auth_type=AuthType.MTLS,
                    client_certificate="/etc/ssl/client.pem",
                    client_key="/etc/ssl/client.key",
                    client_key_password="keypw")

        with patch("ssl.SSLContext.load_cert_chain"):
            context = _mtls_ssl_context(get_webhook("hook"), True, "keypw")

        self.assertGreater(len(context.get_ca_certs()), 1)

    def test_mtls_with_encrypted_key_and_verification_off(self):
        """Disabling verification must also relax the custom SSLContext."""
        set_webhook("hook", url=URL, auth_type=AuthType.MTLS,
                    client_certificate="/etc/ssl/client.pem",
                    client_key="/etc/ssl/client.key",
                    client_key_password="keypw",
                    verify_tls=False)

        with patch("privacyidea.lib.webhook.ssl.create_default_context") as ctx, \
                patch("privacyidea.lib.webhook.requests.Session") as session_cls:
            session = session_cls.return_value
            session.request.return_value.ok = True
            session.request.return_value.status_code = 200
            # The body is read in parts from the raw response, see _read_response_text()
            session.request.return_value.raw.read1.return_value = b""
            session.request.return_value.encoding = "utf-8"

            fire_webhook("hook", payload="x")

        context = ctx.return_value
        self.assertFalse(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)

    def test_ssl_setup_failure_does_not_raise(self):
        """A bad certificate path is a logged failure, not an exception."""
        set_webhook("hook", url=URL, auth_type=AuthType.MTLS,
                    client_certificate="/nonexistent/client.pem",
                    client_key="/nonexistent/client.key",
                    client_key_password="keypw")

        result = fire_webhook("hook", payload="x")

        self.assertFalse(result["success"])
        self.assertIsNone(result["status_code"])
        self.assertIsNotNone(result["error"])

    # ------------------------------------------------------------------
    # Failure handling -- nothing may propagate
    # ------------------------------------------------------------------

    @responses.activate
    def test_http_500_is_reported_not_raised(self):
        """A server error is a failed result, not an exception."""
        responses.add(responses.POST, URL, body="boom", status=500)
        set_webhook("hook", url=URL)

        result = fire_webhook("hook", payload="x")

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 500)
        self.assertEqual(result["error"], "HTTP 500")
        self.assertEqual(result["response"], "boom")

    @responses.activate
    def test_connection_error_is_caught(self):
        """A connection failure is caught and reported."""
        responses.add(responses.POST, URL,
                      body=ConnectionError("no route to host"))
        set_webhook("hook", url=URL)

        result = fire_webhook("hook", payload="x")

        self.assertFalse(result["success"])
        self.assertIsNone(result["status_code"])
        self.assertIsNotNone(result["error"])

    @responses.activate
    def test_timeout_is_caught(self):
        """A timeout is caught and reported."""
        from requests.exceptions import Timeout
        responses.add(responses.POST, URL, body=Timeout("too slow"))
        set_webhook("hook", url=URL)

        result = fire_webhook("hook", payload="x")

        self.assertFalse(result["success"])
        self.assertIsNone(result["status_code"])

    def test_unknown_identifier_does_not_raise(self):
        """Firing a non-existent webhook returns a failure, not an exception."""
        result = fire_webhook("does-not-exist")

        self.assertFalse(result["success"])
        self.assertIsNone(result["status_code"])
        self.assertIsNotNone(result["error"])

    # ------------------------------------------------------------------
    # Response truncation and logging hygiene
    # ------------------------------------------------------------------

    @responses.activate
    def test_long_response_is_truncated(self):
        """An oversized response body is cut down."""
        responses.add(responses.POST, URL, body="x" * 5000, status=200)
        set_webhook("hook", url=URL)

        result = fire_webhook("hook", payload="x")

        self.assertTrue(result["response"].endswith("... [truncated]"))
        self.assertLess(len(result["response"]), 5000)
        self.assertTrue(result["response"].startswith("x" * MAX_RESPONSE_LENGTH))

    @responses.activate
    def test_url_and_headers_are_never_logged(self):
        """The URL may embed a token and headers may carry credentials."""
        secret_url = "https://hook.example.com/t/SUPERSECRETTOKEN"
        responses.add(responses.POST, secret_url, status=200)
        set_webhook("hook", url=secret_url, auth_type=AuthType.HEADER,
                    headers={"Authorization": "Bearer LEAKME"},
                    secret_headers={"Authorization"})

        with self.assertLogs("privacyidea.lib.webhook", level="DEBUG") as logs:
            fire_webhook("hook", payload="x")

        everything = "\n".join(logs.output)
        self.assertNotIn("SUPERSECRETTOKEN", everything)
        self.assertNotIn("LEAKME", everything)
        # The identifier and status code are what we do want to see.
        self.assertIn("'hook'", everything)
        self.assertIn("200", everything)

    @responses.activate
    def test_a_passed_config_and_payload_are_not_logged(self):
        """
        The event handler passes the configuration it has already read. That dict holds the URL
        and the decrypted secret headers, whose names log_with() cannot recognise as sensitive,
        and the payload may carry user data.
        """
        secret_url = "https://hook.example.com/t/SUPERSECRETTOKEN"
        responses.add(responses.POST, secret_url, status=200)
        set_webhook("hook", url=secret_url, auth_type=AuthType.HEADER,
                    headers={"X-Webhook-Sig": "LEAKME"},
                    secret_headers={"X-Webhook-Sig"})

        with self.assertLogs("privacyidea.lib.webhook", level="DEBUG") as logs:
            fire_webhook("hook", payload="PAYLOAD-OF-cornelius", config=get_webhook("hook"))

        everything = "\n".join(logs.output)
        self.assertNotIn("SUPERSECRETTOKEN", everything)
        self.assertNotIn("LEAKME", everything)
        self.assertNotIn("PAYLOAD-OF-cornelius", everything)
        self.assertIn("'hook'", everything)

    @responses.activate
    def test_a_failed_delivery_does_not_leak_the_url_either(self):
        """
        The failure path is where the URL gets out on its own: a transport error quotes the
        endpoint it could not reach, and that message is logged, returned to the API *and*
        written to the audit log by the event handler.
        """
        secret_url = "https://hook.example.com/t/SUPERSECRETTOKEN"
        responses.add(responses.POST, secret_url,
                      body=requests.exceptions.ConnectionError(
                          "HTTPSConnectionPool(host='hook.example.com', port=443): "
                          "Max retries exceeded with url: /t/SUPERSECRETTOKEN"))
        set_webhook("hook", url=secret_url)

        with self.assertLogs("privacyidea.lib.webhook", level="DEBUG") as logs:
            result = fire_webhook("hook")

        self.assertFalse(result["success"])
        self.assertNotIn("SUPERSECRETTOKEN", result["error"])
        self.assertNotIn("SUPERSECRETTOKEN", "\n".join(logs.output))
        # The host is kept on purpose: it is what makes a broken integration diagnosable, and the
        # token an admin embeds sits in the path.
        self.assertIn("hook.example.com", result["error"])
        self.assertIn("ConnectionError", result["error"])

    @responses.activate
    def test_the_response_body_is_logged_at_debug_only(self):
        """A webhook endpoint may answer with user data, so the body belongs below INFO."""
        responses.add(responses.POST, URL, body="ACCOUNT-OF-cornelius", status=200)
        set_webhook("hook", url=URL)

        with self.assertLogs("privacyidea.lib.webhook", level="INFO") as info_logs:
            fire_webhook("hook")
        self.assertNotIn("ACCOUNT-OF-cornelius", "\n".join(info_logs.output))

        with self.assertLogs("privacyidea.lib.webhook", level="DEBUG") as debug_logs:
            fire_webhook("hook")
        self.assertIn("ACCOUNT-OF-cornelius", "\n".join(debug_logs.output))


class TestWebhookHelperTestCase(MyTestCase):
    """The thin test_webhook() wrapper used by the configuration UI."""

    def _cleanup(self):
        for wh in Webhook.query.all():
            wh.delete()

    def setUp(self):
        super().setUp()
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        super().tearDown()

    @responses.activate
    def test_returns_status_and_body(self):
        responses.add(responses.POST, URL, body="pong", status=200)
        set_webhook("hook", url=URL)

        result = run_webhook_test("hook", payload="ping")

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["response"], "pong")
        self.assertEqual(responses.calls[0].request.body, "ping")

    @responses.activate
    def test_uses_default_payload_when_none_given(self):
        responses.add(responses.POST, URL, status=200)
        set_webhook("hook", url=URL, default_payload='{"ping": true}')

        run_webhook_test("hook")

        self.assertEqual(responses.calls[0].request.body, '{"ping": true}')

    def test_failure_is_reported_not_raised(self):
        result = run_webhook_test("does-not-exist")
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])


class _TrickleHandler(BaseHTTPRequestHandler):
    """Answer at once, then send the body one byte every 0.3 seconds."""

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.send_response(200)
        self.send_header("Content-Length", "20")
        self.end_headers()
        for _ in range(20):
            self.wfile.write(b"x")
            self.wfile.flush()
            time.sleep(0.3)

    def log_message(self, *args: object) -> None:
        pass


class _SlowRedirectHandler(BaseHTTPRequestHandler):
    """Answer /first with a redirect to /second after 0.7 seconds, and /second with 200 after 0.7 seconds."""

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        time.sleep(0.7)
        if self.path == "/first":
            self.send_response(307)
            self.send_header("Location", "/second")
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

    def log_message(self, *args: object) -> None:
        pass


class _QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: object, client_address: tuple) -> None:
        # The client closes the connection at its deadline, so the handler fails to write.
        pass


class FireWebhookLimitsTestCase(MyTestCase):
    """The delivery keeps to its timeout and keeps secrets out of its errors."""

    def setUp(self):
        super().setUp()
        for webhook in Webhook.query.all():
            webhook.delete()

    def tearDown(self):
        for webhook in Webhook.query.all():
            webhook.delete()
        super().tearDown()

    def test_the_timeout_limits_a_slow_response_body(self):
        """
        requests limits each wait for data, so 20 bytes at 0.3 s each take 6 s without the deadline. The endpoint
        answered, so its status code counts, with the part of the body that arrived in time.
        """
        server = _QuietServer(("127.0.0.1", 0), _TrickleHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            set_webhook("slow", url=f"http://127.0.0.1:{server.server_address[1]}/hook", timeout=1)
            start = time.monotonic()
            result = fire_webhook("slow", payload="x")
            duration = time.monotonic() - start
        finally:
            server.shutdown()
            server.server_close()

        self.assertTrue(result["success"])
        self.assertEqual(200, result["status_code"])
        self.assertIsNone(result["error"])
        self.assertLess(len(result["response"]), 20)
        self.assertLess(duration, 2.5)

    def test_a_redirect_chain_reports_the_status_of_the_last_answer(self):
        """
        Each redirect gets a timeout of its own. The answer of the last hop counts, also after the deadline. The body
        is not read after the deadline.
        """
        server = _QuietServer(("127.0.0.1", 0), _SlowRedirectHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            set_webhook("chain", url=f"http://127.0.0.1:{server.server_address[1]}/first", timeout=1)
            result = fire_webhook("chain", payload="x")
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual({"success": True, "status_code": 200, "response": "", "error": None}, result)

    @responses.activate
    def test_only_the_start_of_a_long_body_is_kept(self):
        responses.add(responses.POST, URL, body=b"y" * 100000, status=200)
        set_webhook("hook", url=URL)

        result = fire_webhook("hook", payload="x")

        self.assertTrue(result["success"])
        self.assertEqual(f"{'y' * MAX_RESPONSE_LENGTH}... [truncated]", result["response"])

    def test_the_body_is_read_only_up_to_the_limit(self):
        """An endpoint that sends an endless body does not hold the delivery until the deadline."""
        response = MagicMock()
        response.encoding = "utf-8"
        response.raw.read1.side_effect = lambda amount, decode_content: b"z" * min(amount, 1000)

        text, stopped = _read_response_text(response, time.monotonic() + 5)

        self.assertEqual(MAX_RESPONSE_BYTES, len(text))
        self.assertFalse(stopped)

    def test_a_ca_directory_is_loaded_as_capath(self):
        """ssl.create_default_context(cafile=<directory>) fails, so a directory goes to capath, as in requests."""
        with (tempfile.TemporaryDirectory() as directory,
              patch("privacyidea.lib.webhook.ssl.create_default_context") as create_context):
            _mtls_ssl_context({"client_certificate": "/etc/ssl/client.pem", "client_key": "/etc/ssl/client.key"},
                              directory, "keypw")

        create_context.assert_called_once_with(cafile=None, capath=directory)

    @responses.activate
    def test_an_invalid_stored_header_is_not_sent_and_not_quoted(self):
        set_webhook("hook", url=URL, headers={"X-Token": "valid"}, secret_headers=["X-Token"])
        # A value that set_webhook() refuses, written directly, as an import from an older version could have.
        db.session.execute(update(WebhookHeader).where(WebhookHeader.key == "X-Token")
                           .values(value=encryptPassword("Bearer LEAKME-TOKEN\n")))
        db.session.commit()

        with self.assertLogs("privacyidea.lib.webhook", level="WARNING") as logs:
            result = fire_webhook("hook", payload="x")

        self.assertFalse(result["success"])
        self.assertIn("'X-Token'", result["error"])
        self.assertNotIn("LEAKME", result["error"])
        self.assertNotIn("LEAKME", "\n".join(logs.output))
        self.assertEqual(0, len(responses.calls))

    def test_secrets_quoted_in_a_transport_error_are_redacted(self):
        set_webhook("hook", url=URL, auth_type=AuthType.BASIC, username="svc", password="S3cretPW",
                    headers={"X-Token": "tok\\en"}, secret_headers=["X-Token"])
        error = requests.exceptions.ConnectionError("failed with S3cretPW and 'tok\\\\en'")

        with patch("privacyidea.lib.webhook.requests.request", side_effect=error):
            result = fire_webhook("hook", payload="x")

        self.assertNotIn("S3cretPW", result["error"])
        self.assertNotIn("tok", result["error"])

    def test_a_path_that_requests_quotes_again_is_redacted(self):
        """requests sends /t/SéCRET?token=a b as /t/S%C3%A9CRET?token=a%20b, and its error quotes that form."""
        set_webhook("hook", url="http://127.0.0.1:1/t/SéCRET?token=a b", timeout=1)

        result = fire_webhook("hook", payload="x")

        self.assertFalse(result["success"])
        self.assertIn("127.0.0.1", result["error"])
        for part in ("SéCRET", "S%C3%A9CRET", "token=a"):
            self.assertNotIn(part, result["error"])
