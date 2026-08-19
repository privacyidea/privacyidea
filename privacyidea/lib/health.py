# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Health checks intended for admin observability via the /system/health API.

Currently provides certificate expiry information for configured LDAP resolvers,
the TLS server certificate of Keycloak resolvers, the client-certificate
credential of EntraID resolvers, and the privacyIDEA server certificate.
"""
import datetime
import json
import logging
import socket
import ssl
import threading
from urllib.parse import urlparse

import ldap3
import redis as redis_lib
from cryptography import x509

from privacyidea.lib.cache.redis import _disable_redis, redis_client_for_feature
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPIdResolver
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

WARNING_DAYS = 30
CRITICAL_DAYS = 7

_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()

# Producing these results means opening a TLS connection to every configured
# LDAP, Keycloak and EntraID endpoint. The dictionary above keeps them for one
# process, so every worker on every node probes every endpoint for itself once
# per TTL. Redis lets them share one answer, which is what turns "workers times
# nodes" rounds of outbound connections per TTL into one.
#
# The results only feed a dashboard panel, so a shared answer needs nothing
# beyond the TTL that already governs the per-process one.
HEALTH_CACHE_FEATURE = "health"
_CERTIFICATE_KEY = "pi:health:v1:certificates"


def _cache_client():
    """Return the Redis client to share health results through, or None."""
    return redis_client_for_feature(HEALTH_CACHE_FEATURE)


def _cache_ttl() -> int:
    """Return how long a certificate health result may be reused."""
    try:
        return int(get_app_config_value("PI_CERT_CHECK_CACHE_SECONDS", 3600))
    except (TypeError, ValueError):
        log.warning("PI_CERT_CHECK_CACHE_SECONDS is not a number, using 3600s.")
        return 3600


def _read_shared_certificates(client) -> list | None:
    """
    Return the certificate results another worker has already produced, or None.

    None means this worker has to probe: nothing is stored, Redis could not be
    read, or what is stored is not what this version writes. Nothing here may
    raise - a dashboard panel is not worth an error, and probing is always an
    option.
    """
    try:
        raw = client.get(_CERTIFICATE_KEY)
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)
        return None
    if raw is None:
        return None
    try:
        results = json.loads(raw)
        if not isinstance(results, list):
            raise TypeError(f"certificate health payload is {type(results).__name__}, expected list")
        return results
    except (json.JSONDecodeError, TypeError) as error:
        log.warning(f"Ignoring a malformed certificate health entry: {error}")
        return None


def _write_shared_certificates(client, results: list, ttl: int) -> None:
    """Share the results this worker produced with the other workers."""
    try:
        client.set(_CERTIFICATE_KEY, json.dumps(results), ex=ttl)
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)
    except (TypeError, ValueError) as error:
        log.warning(f"Could not serialise the certificate health results: {error}")


def invalidate_certificate_cache() -> None:
    """Drop all cached certificate health results.

    Called from resolver save/delete paths so that admins see the effect of
    LDAP resolver changes immediately, without waiting for the TTL to elapse.

    Drops the shared results as well, so one admin's resolver change reaches
    every worker on every node rather than only the one that served the request.
    """
    with _CACHE_LOCK:
        _CACHE.clear()
    client = _cache_client()
    if client is None:
        return
    try:
        client.unlink(_CERTIFICATE_KEY)
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)


def _classify(days_remaining: int | None) -> str:
    if days_remaining is None:
        return "error"
    if days_remaining <= 0:
        return "expired"
    if days_remaining <= CRITICAL_DAYS:
        return "critical"
    if days_remaining <= WARNING_DAYS:
        return "warning"
    return "ok"


def _cert_info(cert: x509.Certificate, now: datetime.datetime) -> dict:
    not_after = cert.not_valid_after_utc
    days_remaining = (not_after - now).days
    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "not_after": not_after.isoformat(),
        "days_remaining": days_remaining,
        "status": _classify(days_remaining),
    }


def _fetch_tls_cert(host: str, port: int, timeout: float) -> x509.Certificate:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # We never authenticate the peer here - the goal is to read the certificate so we
    # can report on its validity. Pin TLS 1.2+ anyway to avoid CodeQL flagging the
    # default context as accepting TLSv1 / TLSv1.1.
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            der = ssock.getpeercert(binary_form=True)
    return x509.load_der_x509_certificate(der)


def _fetch_starttls_cert(host: str, port: int, timeout: float) -> x509.Certificate:
    tls = ldap3.Tls(validate=ssl.CERT_NONE)
    server = ldap3.Server(host, port=port, use_ssl=False, connect_timeout=timeout, tls=tls)
    conn = ldap3.Connection(server, auto_bind=False, receive_timeout=timeout)
    try:
        conn.open(read_server_info=False)
        if not conn.start_tls(read_server_info=False):
            raise RuntimeError(f"StartTLS failed: {conn.result.get('description')}")
        der = conn.socket.getpeercert(binary_form=True)
    finally:
        # Cleanup-only: the cert was already read in the try block, so a failure
        # to unbind shouldn't mask the result. Log for diagnostics.
        try:
            conn.unbind()
        except Exception as e:  # nosec B110 - cleanup, swallow on purpose
            log.debug(f"unbind after cert probe failed for {host}:{port}: {e}")
    return x509.load_der_x509_certificate(der)


def _check_ldap_endpoint(resolver_name: str, host: str, port: int,
                         use_ldaps: bool, start_tls: bool, timeout: float) -> dict:
    entry = {
        "source": "ldap-resolver",
        "name": resolver_name,
        "host": f"{host}:{port}",
        "tls_mode": "ldaps" if use_ldaps else "starttls",
    }
    try:
        if use_ldaps:
            cert = _fetch_tls_cert(host, port, timeout)
        else:
            cert = _fetch_starttls_cert(host, port, timeout)
        entry.update(_cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc)))
        entry["error"] = None
    except Exception as e:
        log.info(f"Failed to fetch certificate for resolver {resolver_name!r} ({host}:{port}): {e}")
        entry.update({"subject": None, "issuer": None, "not_after": None,
                      "days_remaining": None, "status": "error", "error": str(e)})
    return entry


def _check_ldap_resolvers() -> list:
    results = []
    for name, reso in get_resolver_list(filter_resolver_type="ldapresolver").items():
        data = reso.get("data", {})
        uri = data.get("LDAPURI", "") or ""
        timeout = float(data.get("TIMEOUT") or 5)
        start_tls = is_true(data.get("START_TLS"))
        for raw_uri in uri.split(","):
            raw_uri = raw_uri.strip()
            if not raw_uri:
                continue
            host, port, use_ldaps = LDAPIdResolver.split_uri(raw_uri)
            # Only inspect endpoints that actually negotiate TLS. START_TLS is
            # ignored when the URI is already ldaps:// (matches resolver behavior).
            uses_starttls = start_tls and not use_ldaps
            if not use_ldaps and not uses_starttls:
                continue
            actual_port = port or (636 if use_ldaps else 389)
            results.append(_check_ldap_endpoint(name, host, actual_port,
                                                use_ldaps, uses_starttls, timeout))
    return results


def _check_keycloak_endpoint(resolver_name: str, host: str, port: int, timeout: float) -> dict:
    entry = {
        "source": "keycloak-resolver",
        "name": resolver_name,
        "host": f"{host}:{port}",
        "tls_mode": "https",
    }
    try:
        # A Keycloak endpoint is a plain TLS server, so the generic TLS-wrap
        # probe used for ldaps:// reads its certificate too.
        cert = _fetch_tls_cert(host, port, timeout)
        entry.update(_cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc)))
        entry["error"] = None
    except Exception as e:
        log.info(f"Failed to fetch certificate for resolver {resolver_name!r} ({host}:{port}): {e}")
        entry.update({"subject": None, "issuer": None, "not_after": None,
                      "days_remaining": None, "status": "error", "error": str(e)})
    return entry


def _check_keycloak_resolvers() -> list:
    """Probe the TLS server certificate of each Keycloak resolver's ``base_url``.

    Keycloak resolvers talk to an admin-operated (often self-hosted) HTTPS
    endpoint, so its server certificate is worth surfacing.
    """
    results = []
    for name, reso in get_resolver_list(filter_resolver_type="keycloakresolver").items():
        data = reso.get("data", {})
        base_url = (data.get("base_url") or "").strip()
        timeout = float(data.get("timeout") or 5)
        if not base_url:
            continue
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            # Only an https endpoint presents a TLS server certificate to inspect.
            continue
        port = parsed.port or 443
        results.append(_check_keycloak_endpoint(name, parsed.hostname, port, timeout))
    return results


def _check_entraid_cert_file(resolver_name: str, path: str | None) -> dict:
    entry = {
        "source": "entraid-resolver",
        "name": resolver_name,
        "host": path,
        "tls_mode": "client-certificate",
    }
    if not path:
        entry.update({"subject": None, "issuer": None, "not_after": None, "days_remaining": None,
                      "status": "error", "error": "No private_key_file configured for the client certificate."})
        return entry
    try:
        with open(path, "rb") as f:
            data = f.read()
        # The file holds the private key; for the common combined-PEM case it also
        # carries the certificate. load_pem_x509_certificate picks the first
        # CERTIFICATE block and ignores the key. A key-only file raises ValueError,
        # which we turn into a clear "no certificate" message below.
        cert = x509.load_pem_x509_certificate(data)
        entry.update(_cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc)))
        entry["error"] = None
    except FileNotFoundError as e:
        log.info(f"Client certificate file for resolver {resolver_name!r} not found: {e}")
        entry.update({"subject": None, "issuer": None, "not_after": None, "days_remaining": None,
                      "status": "error", "error": f"Could not read certificate file '{path}': {e}"})
    except ValueError as e:
        log.info(f"No certificate found in private key file for resolver {resolver_name!r} ({path}): {e}")
        entry.update({"subject": None, "issuer": None, "not_after": None, "days_remaining": None,
                      "status": "error",
                      "error": f"No X.509 certificate found in '{path}'. The file may contain only the "
                               "private key, so the expiry date cannot be determined."})
    except Exception as e:
        log.info(f"Failed to read client certificate for resolver {resolver_name!r} ({path}): {e}")
        entry.update({"subject": None, "issuer": None, "not_after": None, "days_remaining": None,
                      "status": "error", "error": str(e)})
    return entry


def _check_entraid_client_certs() -> list:
    """Report expiry of the client-certificate credential each EntraID resolver
    uses to authenticate against Entra.

    Only resolvers configured with ``client_credential_type = certificate`` have
    such a credential. The certificate is read from the configured
    ``private_key_file``; we never need the private key or its passphrase here,
    only the public certificate's validity period.
    """
    results = []
    for name, reso in get_resolver_list(filter_resolver_type="entraidresolver").items():
        data = reso.get("data", {})
        credential_type = (data.get("client_credential_type") or "").strip().lower()
        if credential_type != "certificate":
            continue
        client_certificate = data.get("client_certificate") or {}
        results.append(_check_entraid_cert_file(name, client_certificate.get("private_key_file")))
    return results


def _check_server_cert_file(path: str) -> dict:
    """Read a server certificate from a configured file path on disk."""
    entry = {"source": "privacyidea-server-file",
             "name": path,
             "host": path,
             "tls_mode": "file"}
    try:
        with open(path, "rb") as f:
            data = f.read()
        # PEM is the common case; fall back to DER if the bytes don't start
        # with the BEGIN CERTIFICATE marker.
        if b"BEGIN CERTIFICATE" in data:
            cert = x509.load_pem_x509_certificate(data)
        else:
            cert = x509.load_der_x509_certificate(data)
        entry.update(_cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc)))
        entry["error"] = None
    except Exception as e:
        log.info(f"Failed to read server certificate from {path}: {e}")
        entry.update({"subject": None, "issuer": None, "not_after": None,
                      "days_remaining": None, "status": "error", "error": str(e)})
    return entry


def _check_server_cert_probe(host: str, port: int, timeout: float = 5.0) -> dict:
    """Open a TLS connection to a configured (host, port) and read the cert."""
    entry = {"source": "privacyidea-server-probe",
             "name": f"{host}:{port}",
             "host": f"{host}:{port}",
             "tls_mode": "ldaps"}  # plain TLS wrap, same as ldaps probe
    try:
        cert = _fetch_tls_cert(host, port, timeout=timeout)
        entry.update(_cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc)))
        entry["error"] = None
    except Exception as e:
        log.info(f"Failed to fetch server certificate from {host}:{port}: {e}")
        entry.update({"subject": None, "issuer": None, "not_after": None,
                      "days_remaining": None, "status": "error", "error": str(e)})
    return entry


def _server_cert_entries() -> list:
    """Build the server-cert section of the response from admin config.

    Two opt-in sources, both safe (no client-controlled input):

    * ``PI_SERVER_CERT_FILE`` - one path on disk.
    * ``PI_HEALTH_CERT_PROBES`` - list of ``{"host": "...", "port": int}``
      dicts naming TLS endpoints to probe.

    Both unset -> empty list (panel shows just LDAP resolver entries).
    """
    entries: list = []
    cert_file = get_app_config_value("PI_SERVER_CERT_FILE")
    if cert_file:
        entries.append(_check_server_cert_file(cert_file))
    probes = get_app_config_value("PI_HEALTH_CERT_PROBES") or []
    # Accept a single {"host": ..., "port": ...} dict as a convenience for
    # the common case of one probe target; iteration below normalises.
    if isinstance(probes, dict):
        probes = [probes]
    for probe in probes:
        try:
            host = str(probe["host"])
            port = int(probe["port"])
        except (KeyError, TypeError, ValueError) as e:
            log.warning(f"Ignoring malformed PI_HEALTH_CERT_PROBES entry "
                        f"{probe!r}: {e}")
            continue
        entries.append(_check_server_cert_probe(host, port))
    return entries


def get_certificate_status(refresh: bool = False) -> list:
    """Return certificate expiry info for configured LDAP resolvers, Keycloak
    resolver endpoints, EntraID client-certificate credentials, and any
    admin-configured server certificates.

    Server certificate sources are opt-in via two config keys (see
    :func:`_server_cert_entries`); nothing is auto-probed from request headers.

    Results are cached for ``PI_CERT_CHECK_CACHE_SECONDS`` seconds (default
    3600). Pass ``refresh=True`` to bypass the cache.

    With ``PI_REDIS_CACHE_HEALTH`` enabled the results are shared between all
    workers and nodes, so the endpoints are probed once per TTL for the whole
    installation instead of once per worker process. The per-process dictionary
    stays in front of it, since a worker that already has the answer has no
    reason to ask Redis for it.
    """
    ttl = _cache_ttl()
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    cache_key = "certificates"
    client = _cache_client()
    if not refresh:
        with _CACHE_LOCK:
            cached = _CACHE.get(cache_key)
            if cached and (now - cached[0]).total_seconds() < ttl:
                return cached[1]
        if client is not None:
            shared = _read_shared_certificates(client)
            if shared is not None:
                # Hold on to it locally too, so the next request in this worker
                # does not go to Redis either
                with _CACHE_LOCK:
                    _CACHE[cache_key] = (now, shared)
                return shared

    results = _check_ldap_resolvers()
    results.extend(_check_keycloak_resolvers())
    results.extend(_check_entraid_client_certs())
    results.extend(_server_cert_entries())

    with _CACHE_LOCK:
        _CACHE[cache_key] = (now, results)
    if client is not None:
        _write_shared_certificates(client, results, ttl)
    return results
