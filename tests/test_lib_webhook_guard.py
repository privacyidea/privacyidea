"""
Tests for the outbound request guard in privacyidea/lib/webhook.py.

See https://github.com/privacyidea/privacyidea/issues/5751
"""
import socket
from unittest.mock import patch

import responses

from privacyidea.lib.webhook import (
    GuardMode, check_outbound_target, fire_webhook, set_webhook,
)
from privacyidea.models.webhook import Webhook
from .base import MyTestCase


def _fake_getaddrinfo(mapping):
    """
    Build a stand-in for socket.getaddrinfo() that resolves each hostname in
    `mapping` to the given list of IP address strings, and raises
    socket.gaierror for anything else.
    """

    def fake(host, port, *args, **kwargs):
        if host not in mapping:
            raise socket.gaierror(f"no mock DNS entry for {host!r}")
        results = []
        for ip in mapping[host]:
            if ":" in ip:
                results.append((socket.AF_INET6, socket.SOCK_STREAM,
                                socket.IPPROTO_TCP, "", (ip, port or 0, 0, 0)))
            else:
                results.append((socket.AF_INET, socket.SOCK_STREAM,
                                socket.IPPROTO_TCP, "", (ip, port or 0)))
        return results

    return fake


class CheckOutboundTargetTestCase(MyTestCase):
    """Direct tests of check_outbound_target(), independent of fire_webhook()."""

    def test_off_mode_never_resolves(self):
        with patch("socket.getaddrinfo") as mock_resolve:
            result = check_outbound_target(
                "https://internal.example/", mode=GuardMode.OFF)
        self.assertIsNone(result)
        mock_resolve.assert_not_called()

    def test_enforce_blocks_loopback(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"internal.example": ["127.0.0.1"]})):
            result = check_outbound_target(
                "http://internal.example/", mode=GuardMode.ENFORCE)
        self.assertIsNotNone(result)
        self.assertIn("127.0.0.1", result)

    def test_enforce_blocks_private_rfc1918(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"siem.corp": ["10.1.2.3"]})):
            result = check_outbound_target(
                "https://siem.corp/", mode=GuardMode.ENFORCE)
        self.assertIsNotNone(result)

    def test_enforce_blocks_link_local_metadata(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"metadata.example": ["169.254.169.254"]})):
            result = check_outbound_target(
                "http://metadata.example/", mode=GuardMode.ENFORCE)
        self.assertIsNotNone(result)

    def test_enforce_blocks_cgnat(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"cgnat.example": ["100.64.0.5"]})):
            result = check_outbound_target(
                "http://cgnat.example/", mode=GuardMode.ENFORCE)
        self.assertIsNotNone(result)

    def test_enforce_blocks_ipv6_loopback_and_ula(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"v6.example": ["::1"]})):
            self.assertIsNotNone(check_outbound_target(
                "http://v6.example/", mode=GuardMode.ENFORCE))
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"v6.example": ["fc00::1"]})):
            self.assertIsNotNone(check_outbound_target(
                "http://v6.example/", mode=GuardMode.ENFORCE))

    def test_enforce_blocks_ipv4_mapped_ipv6(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"mapped.example": ["::ffff:127.0.0.1"]})):
            result = check_outbound_target(
                "http://mapped.example/", mode=GuardMode.ENFORCE)
        self.assertIsNotNone(result)

    def test_enforce_allows_public_address(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"public.example": ["203.0.113.5"]})):
            result = check_outbound_target(
                "https://public.example/", mode=GuardMode.ENFORCE)
        self.assertIsNone(result)

    def test_mixed_public_private_a_records_is_rejected(self):
        """A name with one public and one private address must be rejected:
        checking only the first address would be a bypass."""
        with patch("socket.getaddrinfo", _fake_getaddrinfo(
                {"mixed.example": ["203.0.113.5", "10.0.0.1"]})):
            result = check_outbound_target(
                "http://mixed.example/", mode=GuardMode.ENFORCE)
        self.assertIsNotNone(result)

    def test_warn_mode_reports_but_caller_decides(self):
        """check_outbound_target() itself doesn't distinguish warn/enforce
        beyond OFF -- it always reports a hit; fire_webhook() decides what a
        hit means for each mode."""
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"internal.example": ["127.0.0.1"]})):
            result = check_outbound_target(
                "http://internal.example/", mode=GuardMode.WARN)
        self.assertIsNotNone(result)

    def test_unresolvable_host_is_rejected(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({})):
            result = check_outbound_target(
                "http://does-not-resolve.example/", mode=GuardMode.ENFORCE)
        self.assertIsNotNone(result)
        self.assertIn("could not resolve", result)

    # -- Allowlist ---------------------------------------------------------

    def test_allowlist_cidr_permits_blocked_address(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"siem.corp": ["10.1.2.3"]})):
            result = check_outbound_target(
                "https://siem.corp/", mode=GuardMode.ENFORCE,
                allowlist=["10.0.0.0/8"])
        self.assertIsNone(result)

    def test_allowlist_cidr_does_not_permit_other_private_ranges(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"siem.corp": ["192.168.1.1"]})):
            result = check_outbound_target(
                "https://siem.corp/", mode=GuardMode.ENFORCE,
                allowlist=["10.0.0.0/8"])
        self.assertIsNotNone(result)

    def test_allowlist_host_port_permits_by_hostname(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"siem.corp": ["10.1.2.3"]})):
            result = check_outbound_target(
                "https://siem.corp:8443/", mode=GuardMode.ENFORCE,
                allowlist=["siem.corp:8443"])
        self.assertIsNone(result)

    def test_allowlist_host_port_requires_matching_port(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"siem.corp": ["10.1.2.3"]})):
            result = check_outbound_target(
                "https://siem.corp:9999/", mode=GuardMode.ENFORCE,
                allowlist=["siem.corp:8443"])
        self.assertIsNotNone(result)

    def test_allowlist_bare_ip_permits_resolved_address(self):
        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"siem.corp": ["10.1.2.3"]})):
            result = check_outbound_target(
                "https://siem.corp/", mode=GuardMode.ENFORCE,
                allowlist=["10.1.2.3"])
        self.assertIsNone(result)


class FireWebhookGuardTestCase(MyTestCase):
    """Integration of the guard into fire_webhook()."""

    URL = "http://internal.example/hook"

    def _cleanup(self):
        for wh in Webhook.query.all():
            wh.delete()

    def setUp(self):
        super().setUp()
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        self.app.config.pop("PI_OUTBOUND_GUARD", None)
        self.app.config.pop("PI_OUTBOUND_GUARD_ALLOW", None)
        super().tearDown()

    @responses.activate
    def test_off_mode_sends_unchanged_even_to_private_address(self):
        """The upgrade-safety test: must never be 'fixed' by changing the
        default away from off."""
        self.app.config["PI_OUTBOUND_GUARD"] = "off"
        responses.add(responses.POST, self.URL, json={"ok": True}, status=200)
        set_webhook("hook", url=self.URL)

        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"internal.example": ["127.0.0.1"]})):
            result = fire_webhook("hook")

        self.assertTrue(result["success"])
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_enforce_mode_blocks_and_sends_nothing(self):
        self.app.config["PI_OUTBOUND_GUARD"] = "enforce"
        responses.add(responses.POST, self.URL, json={"ok": True}, status=200)
        set_webhook("hook", url=self.URL)

        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"internal.example": ["127.0.0.1"]})):
            result = fire_webhook("hook")

        self.assertFalse(result["success"])
        self.assertIn("outbound request guard", result["error"])
        self.assertEqual(len(responses.calls), 0)

    @responses.activate
    def test_warn_mode_still_sends(self):
        self.app.config["PI_OUTBOUND_GUARD"] = "warn"
        responses.add(responses.POST, self.URL, json={"ok": True}, status=200)
        set_webhook("hook", url=self.URL)

        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"internal.example": ["127.0.0.1"]})):
            result = fire_webhook("hook")

        self.assertTrue(result["success"])
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_enforce_mode_allows_public_address(self):
        self.app.config["PI_OUTBOUND_GUARD"] = "enforce"
        responses.add(responses.POST, self.URL, json={"ok": True}, status=200)
        set_webhook("hook", url=self.URL)

        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"internal.example": ["203.0.113.5"]})):
            result = fire_webhook("hook")

        self.assertTrue(result["success"])
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_allowlist_entry_permits_delivery_in_enforce_mode(self):
        self.app.config["PI_OUTBOUND_GUARD"] = "enforce"
        self.app.config["PI_OUTBOUND_GUARD_ALLOW"] = ["127.0.0.0/8"]
        responses.add(responses.POST, self.URL, json={"ok": True}, status=200)
        set_webhook("hook", url=self.URL)

        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"internal.example": ["127.0.0.1"]})):
            result = fire_webhook("hook")

        self.assertTrue(result["success"])
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_proxy_configured_checks_proxy_not_destination(self):
        """When a proxy is configured, the guard must check the proxy address
        -- the proxy is what resolves and connects to the destination, so
        checking the destination would protect against nothing."""
        self.app.config["PI_OUTBOUND_GUARD"] = "enforce"
        public_url = "https://public.example/hook"
        responses.add(responses.POST, public_url, json={"ok": True}, status=200)
        set_webhook("hook", url=public_url,
                    https_proxy="https://proxy.internal:3128")

        dns = _fake_getaddrinfo({
            "public.example": ["203.0.113.5"],
            "proxy.internal": ["10.9.9.9"],
        })
        with patch("socket.getaddrinfo", dns):
            result = fire_webhook("hook")

        # The destination is public, but the configured proxy resolves into
        # blocked space, so the request must still be rejected.
        self.assertFalse(result["success"])
        self.assertEqual(len(responses.calls), 0)

    @responses.activate
    def test_invalid_guard_mode_falls_back_to_off(self):
        self.app.config["PI_OUTBOUND_GUARD"] = "not-a-real-mode"
        responses.add(responses.POST, self.URL, json={"ok": True}, status=200)
        set_webhook("hook", url=self.URL)

        with patch("socket.getaddrinfo",
                   _fake_getaddrinfo({"internal.example": ["127.0.0.1"]})):
            result = fire_webhook("hook")

        self.assertTrue(result["success"])
        self.assertEqual(len(responses.calls), 1)
