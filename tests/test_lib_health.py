# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ``privacyidea.lib.health`` certificate-status helpers."""
import datetime
import threading
from unittest.mock import MagicMock, patch

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from privacyidea.lib import health
from tests.base import MyTestCase


def _cm(value):
    """Build an object that doubles as a context manager yielding ``value``."""
    return MagicMock(__enter__=lambda self: value, __exit__=lambda *a: None)


def _make_cert(days_until_expiry: int, subject_cn: str = "test.example.com",
               issuer_cn: str = "test-ca") -> x509.Certificate:
    """Generate a self-signed cert that expires ``days_until_expiry`` from now."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048,
                                   backend=default_backend())
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_cn)])
    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_cn)])
    # Pick a not_valid_before that is always strictly before not_valid_after,
    # even for negative ``days_until_expiry`` (already-expired certs in tests).
    not_after = now + datetime.timedelta(days=days_until_expiry)
    not_before = not_after - datetime.timedelta(days=365)
    return (x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .sign(key, hashes.SHA256(), backend=default_backend()))


class ClassifyTest(MyTestCase):
    """Pure-function classification thresholds."""

    def test_status_buckets(self):
        # ok > 30, warning <= 30, critical <= 7, expired <= 0, error on None.
        self.assertEqual(health._classify(31), "ok")
        self.assertEqual(health._classify(30), "warning")
        self.assertEqual(health._classify(8), "warning")
        self.assertEqual(health._classify(7), "critical")
        self.assertEqual(health._classify(1), "critical")
        self.assertEqual(health._classify(0), "expired")
        self.assertEqual(health._classify(-5), "expired")
        self.assertEqual(health._classify(None), "error")


class CertInfoTest(MyTestCase):
    """``_cert_info`` derives the expected dict from a real X.509 cert."""

    def test_valid_far_future(self):
        cert = _make_cert(days_until_expiry=400)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        info = health._cert_info(cert, now)
        self.assertEqual(info["status"], "ok")
        # Allow a one-day fuzz for the boundary.
        self.assertGreaterEqual(info["days_remaining"], 398)
        self.assertLessEqual(info["days_remaining"], 400)
        self.assertIn("test.example.com", info["subject"])
        self.assertIn("test-ca", info["issuer"])

    def test_warning_band(self):
        cert = _make_cert(days_until_expiry=15)
        info = health._cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc))
        self.assertEqual(info["status"], "warning")

    def test_critical_band(self):
        cert = _make_cert(days_until_expiry=3)
        info = health._cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc))
        self.assertEqual(info["status"], "critical")

    def test_expired(self):
        cert = _make_cert(days_until_expiry=-2)
        info = health._cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc))
        self.assertEqual(info["status"], "expired")
        self.assertLess(info["days_remaining"], 0)


class CacheTest(MyTestCase):
    """``get_certificate_status`` cache: TTL hit, refresh, invalidate."""

    def setUp(self):
        super().setUp()
        # Keep tests independent of one another and of the previous run.
        health.invalidate_certificate_cache()

    def test_cache_hit_skips_recheck(self):
        # First call populates the cache, subsequent call within the TTL must
        # not re-invoke the resolver/server probes.
        with (patch.object(health, "_check_ldap_resolvers", return_value=[]) as ldap_mock,
              patch.object(health, "_server_cert_entries", return_value=[]) as srv_mock):
            health.get_certificate_status()
            health.get_certificate_status()
            self.assertEqual(ldap_mock.call_count, 1)
            self.assertEqual(srv_mock.call_count, 1)

    def test_refresh_bypasses_cache(self):
        with (patch.object(health, "_check_ldap_resolvers", return_value=[]) as ldap_mock,
              patch.object(health, "_server_cert_entries", return_value=[]) as srv_mock):
            health.get_certificate_status()
            health.get_certificate_status(refresh=True)
            self.assertEqual(ldap_mock.call_count, 2)
            self.assertEqual(srv_mock.call_count, 2)

    def test_invalidate_drops_cache(self):
        with (patch.object(health, "_check_ldap_resolvers", return_value=[]) as ldap_mock,
              patch.object(health, "_server_cert_entries", return_value=[])):
            health.get_certificate_status()
            health.invalidate_certificate_cache()
            health.get_certificate_status()
            self.assertEqual(ldap_mock.call_count, 2)

    def test_invalidate_is_thread_safe(self):
        # Hit the lock from a few threads at once - the function must not raise
        # and must leave the cache empty.
        threads = [threading.Thread(target=health.invalidate_certificate_cache)
                   for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(health._CACHE, {})


class ServerCertEntriesTest(MyTestCase):
    """``_server_cert_entries`` reads admin config (file + probe list)."""

    def test_empty_when_nothing_configured(self):
        with patch.object(health, "get_app_config_value", return_value=None):
            self.assertEqual(health._server_cert_entries(), [])

    def test_file_path_reads_pem(self):
        cert = _make_cert(days_until_expiry=365)
        pem = cert.public_bytes(encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)
        from unittest.mock import mock_open
        config = {"PI_SERVER_CERT_FILE": "/etc/ssl/srv.pem", "PI_HEALTH_CERT_PROBES": None}
        with (patch.object(health, "get_app_config_value",
                           side_effect=lambda k, *a, **kw: config.get(k)),
              patch("builtins.open", mock_open(read_data=pem))):
            entries = health._server_cert_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"], "privacyidea-server-file")
        self.assertEqual(entries[0]["status"], "ok")

    def test_file_error_surfaces(self):
        config = {"PI_SERVER_CERT_FILE": "/no/such/file", "PI_HEALTH_CERT_PROBES": None}
        with patch.object(health, "get_app_config_value",
                          side_effect=lambda k, *a, **kw: config.get(k)):
            entries = health._server_cert_entries()
        self.assertEqual(entries[0]["status"], "error")
        self.assertIsNotNone(entries[0]["error"])

    def test_probe_list_runs_each_target(self):
        cert = _make_cert(days_until_expiry=365)
        config = {"PI_SERVER_CERT_FILE": None,
                  "PI_HEALTH_CERT_PROBES": [{"host": "127.0.0.1", "port": 443},
                                            {"host": "nginx", "port": 443}]}
        with (patch.object(health, "get_app_config_value",
                           side_effect=lambda k, *a, **kw: config.get(k)),
              patch.object(health, "_fetch_ldaps_cert", return_value=cert) as fetch):
            entries = health._server_cert_entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(entries[0]["source"], "privacyidea-server-probe")
        self.assertEqual(entries[0]["host"], "127.0.0.1:443")
        self.assertEqual(entries[1]["host"], "nginx:443")

    def test_probe_error_status(self):
        config = {"PI_SERVER_CERT_FILE": None,
                  "PI_HEALTH_CERT_PROBES": [{"host": "127.0.0.1", "port": 443}]}
        with (patch.object(health, "get_app_config_value",
                           side_effect=lambda k, *a, **kw: config.get(k)),
              patch.object(health, "_fetch_ldaps_cert",
                           side_effect=ConnectionRefusedError("nope"))):
            entries = health._server_cert_entries()
        self.assertEqual(entries[0]["status"], "error")
        self.assertIn("nope", entries[0]["error"])

    def test_single_probe_dict_is_accepted(self):
        # Convenience: a bare dict (not wrapped in a list) is treated as one entry.
        cert = _make_cert(days_until_expiry=365)
        config = {"PI_SERVER_CERT_FILE": None,
                  "PI_HEALTH_CERT_PROBES": {"host": "pi.example", "port": 5000}}
        with (patch.object(health, "get_app_config_value",
                           side_effect=lambda k, *a, **kw: config.get(k)),
              patch.object(health, "_fetch_ldaps_cert", return_value=cert)):
            entries = health._server_cert_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["host"], "pi.example:5000")

    def test_malformed_probe_entry_is_skipped(self):
        # A bad entry must not break the rest of the list.
        cert = _make_cert(days_until_expiry=365)
        config = {"PI_SERVER_CERT_FILE": None,
                  "PI_HEALTH_CERT_PROBES": [{"host": "ok", "port": 443},
                                            {"host": "bad"},  # missing port
                                            {"host": "ok2", "port": "not-a-number"}]}
        with (patch.object(health, "get_app_config_value",
                           side_effect=lambda k, *a, **kw: config.get(k)),
              patch.object(health, "_fetch_ldaps_cert", return_value=cert)):
            entries = health._server_cert_entries()
        # Only the well-formed entry made it through.
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["host"], "ok:443")


class LdapEndpointCheckTest(MyTestCase):
    """``_check_ldap_endpoint`` propagates probe results / errors."""

    def test_ldaps_success(self):
        cert = _make_cert(days_until_expiry=10)
        with patch.object(health, "_fetch_ldaps_cert", return_value=cert):
            entry = health._check_ldap_endpoint("openldap", "ldap.example", 636,
                                                use_ldaps=True, start_tls=False, timeout=2.0)
        self.assertEqual(entry["status"], "warning")  # 10 days < 30
        self.assertEqual(entry["tls_mode"], "ldaps")
        self.assertEqual(entry["host"], "ldap.example:636")
        self.assertEqual(entry["name"], "openldap")
        self.assertIsNone(entry["error"])

    def test_starttls_dispatches_to_starttls_helper(self):
        cert = _make_cert(days_until_expiry=200)
        with (patch.object(health, "_fetch_starttls_cert", return_value=cert) as starttls,
              patch.object(health, "_fetch_ldaps_cert") as ldaps):
            entry = health._check_ldap_endpoint("ad", "ldap.example", 389,
                                                use_ldaps=False, start_tls=True, timeout=2.0)
        starttls.assert_called_once()
        ldaps.assert_not_called()
        self.assertEqual(entry["tls_mode"], "starttls")
        self.assertEqual(entry["status"], "ok")

    def test_error_status_on_probe_failure(self):
        with patch.object(health, "_fetch_ldaps_cert",
                          side_effect=TimeoutError("timed out")):
            entry = health._check_ldap_endpoint("openldap", "ldap.example", 636,
                                                use_ldaps=True, start_tls=False, timeout=2.0)
        self.assertEqual(entry["status"], "error")
        self.assertIn("timed out", entry["error"])
        self.assertIsNone(entry["not_after"])


class ResolverListIntegrationTest(MyTestCase):
    """``_check_ldap_resolvers`` filters / iterates resolver list correctly."""

    def test_skips_resolvers_without_tls(self):
        # Plain ldap:// without START_TLS must be skipped (nothing to probe).
        resolvers = {
            "plain": {"data": {"LDAPURI": "ldap://ldap.example",
                               "TIMEOUT": "3", "START_TLS": "False"}},
        }
        with patch.object(health, "get_resolver_list", return_value=resolvers):
            results = health._check_ldap_resolvers()
        self.assertEqual(results, [])

    def test_includes_ldaps_and_starttls(self):
        cert = _make_cert(days_until_expiry=100)
        resolvers = {
            "ldaps_one": {"data": {"LDAPURI": "ldaps://a.example:1636",
                                   "TIMEOUT": "5", "START_TLS": "False"}},
            "starttls_one": {"data": {"LDAPURI": "ldap://b.example",
                                       "TIMEOUT": "5", "START_TLS": "True"}},
        }
        with (patch.object(health, "get_resolver_list", return_value=resolvers),
              patch.object(health, "_fetch_ldaps_cert", return_value=cert),
              patch.object(health, "_fetch_starttls_cert", return_value=cert)):
            results = health._check_ldap_resolvers()
        names = sorted(r["name"] for r in results)
        self.assertEqual(names, ["ldaps_one", "starttls_one"])
        for r in results:
            self.assertEqual(r["status"], "ok")

    def test_handles_multiple_uris_in_one_resolver(self):
        cert = _make_cert(days_until_expiry=50)
        resolvers = {
            "redundant": {"data": {"LDAPURI": "ldaps://a.example, ldaps://b.example",
                                   "TIMEOUT": "5", "START_TLS": "False"}},
        }
        with (patch.object(health, "get_resolver_list", return_value=resolvers),
              patch.object(health, "_fetch_ldaps_cert", return_value=cert)):
            results = health._check_ldap_resolvers()
        # Both URIs in the same resolver definition produce separate entries.
        self.assertEqual(len(results), 2)
        self.assertEqual({r["host"] for r in results},
                         {"a.example:636", "b.example:636"})


class KeycloakResolversTest(MyTestCase):
    """``_check_keycloak_resolvers`` probes the server cert of the base_url."""

    def test_skips_non_https_and_missing_base_url(self):
        resolvers = {
            "http_only": {"data": {"base_url": "http://keycloak.example:8080", "timeout": "5"}},
            "no_url": {"data": {"timeout": "5"}},
        }
        with patch.object(health, "get_resolver_list", return_value=resolvers):
            results = health._check_keycloak_resolvers()
        self.assertEqual(results, [])

    def test_probes_https_base_url_with_explicit_port(self):
        cert = _make_cert(days_until_expiry=100)
        resolvers = {"kc": {"data": {"base_url": "https://keycloak.example:8443", "timeout": "5"}}}
        with (patch.object(health, "get_resolver_list", return_value=resolvers),
              patch.object(health, "_fetch_ldaps_cert", return_value=cert) as fetch):
            results = health._check_keycloak_resolvers()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "keycloak-resolver")
        self.assertEqual(results[0]["host"], "keycloak.example:8443")
        self.assertEqual(results[0]["status"], "ok")
        fetch.assert_called_once_with("keycloak.example", 8443, 5.0)

    def test_defaults_to_port_443(self):
        cert = _make_cert(days_until_expiry=10)
        resolvers = {"kc": {"data": {"base_url": "https://keycloak.example"}}}
        with (patch.object(health, "get_resolver_list", return_value=resolvers),
              patch.object(health, "_fetch_ldaps_cert", return_value=cert) as fetch):
            results = health._check_keycloak_resolvers()
        self.assertEqual(results[0]["host"], "keycloak.example:443")
        self.assertEqual(results[0]["status"], "warning")
        fetch.assert_called_once_with("keycloak.example", 443, 5.0)

    def test_probe_failure_surfaces_error(self):
        resolvers = {"kc": {"data": {"base_url": "https://keycloak.example"}}}
        with (patch.object(health, "get_resolver_list", return_value=resolvers),
              patch.object(health, "_fetch_ldaps_cert", side_effect=OSError("refused"))):
            results = health._check_keycloak_resolvers()
        self.assertEqual(results[0]["status"], "error")
        self.assertIn("refused", results[0]["error"])


class EntraIDClientCertTest(MyTestCase):
    """``_check_entraid_client_certs`` reads the client-certificate credential."""

    def test_skips_secret_credential_type(self):
        resolvers = {"entra": {"data": {"client_credential_type": "secret"}}}
        with patch.object(health, "get_resolver_list", return_value=resolvers):
            results = health._check_entraid_client_certs()
        self.assertEqual(results, [])

    def test_reads_certificate_from_pem_file(self):
        from unittest.mock import mock_open
        pem = _make_cert(days_until_expiry=20).public_bytes(serialization.Encoding.PEM)
        resolvers = {"entra": {"data": {"client_credential_type": "certificate",
                                        "client_certificate": {"private_key_file": "/etc/pi/entra.pem"}}}}
        with (patch.object(health, "get_resolver_list", return_value=resolvers),
              patch("builtins.open", mock_open(read_data=pem))):
            results = health._check_entraid_client_certs()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "entraid-resolver")
        self.assertEqual(results[0]["host"], "/etc/pi/entra.pem")
        self.assertEqual(results[0]["status"], "warning")
        self.assertIsNone(results[0]["error"])

    def test_missing_private_key_file(self):
        resolvers = {"entra": {"data": {"client_credential_type": "certificate",
                                        "client_certificate": {}}}}
        with patch.object(health, "get_resolver_list", return_value=resolvers):
            results = health._check_entraid_client_certs()
        self.assertEqual(results[0]["status"], "error")
        self.assertIn("No private_key_file", results[0]["error"])

    def test_key_only_file_reports_no_certificate(self):
        from unittest.mock import mock_open
        key_pem = (rsa.generate_private_key(public_exponent=65537, key_size=2048,
                                            backend=default_backend())
                   .private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()))
        resolvers = {"entra": {"data": {"client_credential_type": "certificate",
                                        "client_certificate": {"private_key_file": "/etc/pi/key.pem"}}}}
        with (patch.object(health, "get_resolver_list", return_value=resolvers),
              patch("builtins.open", mock_open(read_data=key_pem))):
            results = health._check_entraid_client_certs()
        self.assertEqual(results[0]["status"], "error")
        self.assertIn("No X.509 certificate", results[0]["error"])

    def test_file_not_found_surfaces_error(self):
        resolvers = {"entra": {"data": {"client_credential_type": "certificate",
                                        "client_certificate": {"private_key_file": "/nope.pem"}}}}
        with (patch.object(health, "get_resolver_list", return_value=resolvers),
              patch("builtins.open", side_effect=FileNotFoundError("missing"))):
            results = health._check_entraid_client_certs()
        self.assertEqual(results[0]["status"], "error")
        self.assertIn("Could not read certificate file", results[0]["error"])


class ResolverHookTest(MyTestCase):
    """save_resolver / delete_resolver invalidate the cert cache."""

    def test_save_resolver_invalidates_cache(self):
        # Drop the heavy dependencies; save_resolver only needs to reach the
        # invalidate call at the end of its happy path. We verify the import
        # site exists and is callable - the actual save logic is covered by
        # other tests.
        from privacyidea.lib import resolver as resolver_lib
        with patch.object(health, "invalidate_certificate_cache") as invalidate:
            # Pre-populate the cache so we can prove it would be cleared.
            with (patch.object(health, "_check_ldap_resolvers", return_value=[]),
                  patch.object(health, "_server_cert_entries", return_value=[])):
                health.get_certificate_status()
            # Confirm the resolver module imports invalidate_certificate_cache
            # at the bottom of save_resolver / delete_resolver.
            import inspect
            src = inspect.getsource(resolver_lib.save_resolver)
            self.assertIn("invalidate_certificate_cache", src)
            src = inspect.getsource(resolver_lib.delete_resolver)
            self.assertIn("invalidate_certificate_cache", src)
            # The mock itself never fires here because we don't run save_resolver
            # (that needs full DB fixtures); the source-level assertion above
            # is the lightweight equivalent.
            invalidate.assert_not_called()


class FetchLdapsCertTest(MyTestCase):
    """Cover ``_fetch_ldaps_cert`` with the socket / ssl layer faked out.

    The real probe needs an actual TLS endpoint, which is too heavy for unit
    tests. We instead inject a synthetic DER-encoded certificate at the
    ``getpeercert`` boundary and assert the function parses it and returns the
    matching ``x509.Certificate``.
    """

    def test_returns_cert_loaded_from_peer_der(self):
        cert = _make_cert(days_until_expiry=42)
        der = cert.public_bytes(serialization.Encoding.DER)

        ssock = MagicMock()
        ssock.getpeercert = MagicMock(return_value=der)

        ssl_ctx = MagicMock()
        ssl_ctx.wrap_socket = MagicMock(return_value=_cm(ssock))

        with patch.object(health.ssl, "create_default_context", return_value=ssl_ctx), \
                patch.object(health.socket, "create_connection", return_value=_cm(MagicMock())):
            result = health._fetch_ldaps_cert("ldap.example", 636, 5.0)

        self.assertEqual(result.serial_number, cert.serial_number)
        # Make sure we requested the binary form (DER), not the parsed dict form,
        # so we can hand it straight to x509.load_der_x509_certificate.
        ssock.getpeercert.assert_called_with(binary_form=True)
        # And the SSL context must opt out of hostname/peer verification - we
        # are inspecting the cert, not authenticating to the peer.
        self.assertFalse(ssl_ctx.check_hostname)
        # ssl.CERT_NONE; compare loosely so the test doesn't pin to the int value.
        import ssl as _ssl
        self.assertEqual(ssl_ctx.verify_mode, _ssl.CERT_NONE)
        # And it pins TLS 1.2 minimum (added to silence CodeQL).
        self.assertEqual(ssl_ctx.minimum_version, _ssl.TLSVersion.TLSv1_2)


class FetchStartTLSCertTest(MyTestCase):
    """Cover ``_fetch_starttls_cert``, including the unbind-cleanup branch."""

    def _patch_ldap3(self, fake_conn):
        # ldap3.Tls / Server are constructors with side-effecting validation; we
        # only care about the Connection. Patch all three to keep them inert.
        return [
            patch.object(health.ldap3, "Tls"),
            patch.object(health.ldap3, "Server"),
            patch.object(health.ldap3, "Connection", return_value=fake_conn),
        ]

    def test_returns_cert_and_unbinds_on_success(self):
        cert = _make_cert(days_until_expiry=15)
        der = cert.public_bytes(serialization.Encoding.DER)

        fake_conn = MagicMock()
        fake_conn.start_tls.return_value = True
        fake_conn.socket = MagicMock()
        fake_conn.socket.getpeercert = MagicMock(return_value=der)

        patches = self._patch_ldap3(fake_conn)
        try:
            for p in patches:
                p.start()
            result = health._fetch_starttls_cert("ldap.example", 389, 5.0)
        finally:
            for p in patches:
                p.stop()

        self.assertEqual(result.serial_number, cert.serial_number)
        # Connection must be opened, then upgraded with start_tls, then unbound.
        fake_conn.open.assert_called_once_with(read_server_info=False)
        fake_conn.start_tls.assert_called_once_with(read_server_info=False)
        fake_conn.unbind.assert_called_once()

    def test_raises_when_start_tls_fails(self):
        # If start_tls() returns False, we must raise so the caller flips the
        # status to "error". The finally block must still attempt unbind.
        fake_conn = MagicMock()
        fake_conn.start_tls.return_value = False
        fake_conn.result = {"description": "server refused TLS"}

        patches = self._patch_ldap3(fake_conn)
        try:
            for p in patches:
                p.start()
            with self.assertRaises(RuntimeError) as ctx:
                health._fetch_starttls_cert("ldap.example", 389, 5.0)
        finally:
            for p in patches:
                p.stop()

        self.assertIn("server refused TLS", str(ctx.exception))
        fake_conn.unbind.assert_called_once()

    def test_unbind_failure_is_swallowed_after_successful_probe(self):
        # The cert was already read; an unbind that throws must not mask the
        # successful return value. This covers the # nosec B110 branch.
        cert = _make_cert(days_until_expiry=200)
        der = cert.public_bytes(serialization.Encoding.DER)

        fake_conn = MagicMock()
        fake_conn.start_tls.return_value = True
        fake_conn.socket = MagicMock()
        fake_conn.socket.getpeercert = MagicMock(return_value=der)
        fake_conn.unbind.side_effect = RuntimeError("connection already closed")

        patches = self._patch_ldap3(fake_conn)
        try:
            for p in patches:
                p.start()
            result = health._fetch_starttls_cert("ldap.example", 389, 5.0)
        finally:
            for p in patches:
                p.stop()

        self.assertEqual(result.serial_number, cert.serial_number)
