# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Health checks intended for admin observability via the /system/health API.

Currently provides certificate expiry information for configured LDAP resolvers
and the privacyIDEA server certificate.
"""
import datetime
import logging
import socket
import ssl
import threading

import ldap3
from cryptography import x509

from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPIdResolver
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

WARNING_DAYS = 30
CRITICAL_DAYS = 7

_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()
_CACHE_KEY = "certificates"


def invalidate_certificate_cache() -> None:
    """Drop all cached certificate health results.

    Called from resolver save/delete paths so that admins see the effect of
    LDAP resolver changes immediately, without waiting for the TTL to elapse.
    """
    with _CACHE_LOCK:
        _CACHE.clear()


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


def _fetch_ldaps_cert(host: str, port: int, timeout: float) -> x509.Certificate:
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
            cert = _fetch_ldaps_cert(host, port, timeout)
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


def _check_server_cert(server_host: str | None, server_port: int | None,
                       https: bool) -> dict:
    entry = {"source": "privacyidea-server",
             "name": server_host or "privacyidea",
             "host": f"{server_host}:{server_port}" if server_host and server_port else None,
             "tls_mode": "ldaps"}  # plain TLS wrap, same as ldaps probe
    if not https or not server_host or not server_port:
        entry.update({"subject": None, "issuer": None, "not_after": None,
                      "days_remaining": None, "status": "not_configured",
                      "error": "The privacyIDEA server certificate can only be "
                               "checked when this endpoint is reached over HTTPS."})
        return entry
    try:
        cert = _fetch_ldaps_cert(server_host, server_port, timeout=5.0)
        entry.update(_cert_info(cert, datetime.datetime.now(tz=datetime.timezone.utc)))
        entry["error"] = None
    except Exception as e:
        log.info(f"Failed to fetch server certificate from {server_host}:{server_port}: {e}")
        entry.update({"subject": None, "issuer": None, "not_after": None,
                      "days_remaining": None, "status": "error", "error": str(e)})
    return entry


def get_certificate_status(server_host: str | None = None,
                           server_port: int | None = None,
                           https: bool = False,
                           refresh: bool = False) -> list:
    """Return certificate expiry info for configured LDAP resolvers and the server cert.

    The privacyIDEA server certificate is fetched by opening a TLS connection to
    ``server_host:server_port`` (typically derived from the incoming admin
    request, so we probe whatever endpoint the admin actually reached us on -
    works uniformly for apache+uwsgi, nginx+gunicorn or the flask dev server).

    Results are cached per (host, port) for ``PI_CERT_CHECK_CACHE_SECONDS``
    seconds (default 3600). Pass ``refresh=True`` to bypass the cache.
    """
    ttl = int(get_app_config_value("PI_CERT_CHECK_CACHE_SECONDS", 3600))
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    cache_key = (server_host, server_port, https)
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if not refresh and cached and (now - cached[0]).total_seconds() < ttl:
            return cached[1]

    results = _check_ldap_resolvers()
    results.append(_check_server_cert(server_host, server_port, https))

    with _CACHE_LOCK:
        _CACHE[cache_key] = (now, results)
    return results
