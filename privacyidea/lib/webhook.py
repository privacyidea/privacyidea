# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
import inspect
import ipaddress
import json
import logging
import socket
import ssl
import time
from urllib.parse import urlsplit

import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from sqlalchemy import select

from privacyidea.lib.crypto import (encryptPassword, decryptPassword,
                                    FAILED_TO_DECRYPT_PASSWORD, is_censored,
                                    CENSORED)
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.metrics import inc, observe
from privacyidea.lib.utils import fetch_one_resource
from privacyidea.lib.utils.export import register_import, register_export
from privacyidea.models import db
from privacyidea.models.webhook import Webhook, WebhookHeader

__doc__ = """
This is the library for creating, listing and deleting Webhook objects in the
database.

A webhook object owns the *endpoint*: the URL, HTTP method, authentication,
static headers, TLS settings, proxy settings and timeout.  The *call site* --
an event handler or a Conditional Access stage action -- owns the payload and
references the webhook by its identifier.

It depends on the Webhook model in ``privacyidea/models/webhook.py``.  This
module can be tested standalone without any webservices and is tested in
tests/test_lib_webhook.py.
"""

log = logging.getLogger(__name__)

#: Default request timeout in seconds.  Deliberately low: delivery in V1 is
#: synchronous, so a slow endpoint directly adds latency to the triggering
#: request.
DEFAULT_TIMEOUT = 3


class AuthType:
    """Supported webhook authentication types."""
    NONE = "none"
    BASIC = "basic"
    HEADER = "header"
    MTLS = "mtls"

    ALL = (NONE, BASIC, HEADER, MTLS)


class HttpMethod:
    """HTTP methods a webhook may use."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"

    ALL = (GET, POST, PUT, PATCH)


class ContentType:
    """Common body MIME types. Any valid MIME type may be configured."""
    JSON = "application/json"
    URLENCODED = "application/x-www-form-urlencoded"


#: Keys of the webhook dict whose values are secrets.
SECRET_KEYS = ("password", "client_key_password")

#: Response bodies are truncated to this many characters before being returned
#: or logged. A webhook endpoint may answer with an arbitrarily large document
#: and we must not blow up the audit log or the API response with it.
MAX_RESPONSE_LENGTH = 1000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decrypt_or_empty(value):
    """
    Decrypt a stored secret, returning "" when the value is absent or the
    stored ciphertext cannot be decrypted (e.g. after an enckey change).
    """
    if not value:
        return ""
    decrypted = decryptPassword(value)
    if decrypted == FAILED_TO_DECRYPT_PASSWORD:
        log.warning("Failed to decrypt a stored webhook secret. "
                    "Returning an empty value.")
        return ""
    return decrypted


def _validate(identifier: str, url: str | None, http_method: str | None,
              content_type: str | None, auth_type: str | None,
              timeout, username: str | None,
              client_certificate: str | None,
              headers: dict | None) -> tuple[str, str, str, str, int]:
    """
    Validate the parameters of :func:`set_webhook`.

    Raises :class:`ParameterError` on the first problem found. Returns the
    normalised ``(url, http_method, content_type, auth_type, timeout)`` tuple.
    """
    if not identifier or not identifier.strip():
        raise ParameterError("The webhook identifier must not be empty.")
    if not url or not url.strip():
        raise ParameterError("The webhook URL must not be empty.")
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ParameterError(
            "The webhook URL must start with 'http://' or 'https://'.")

    # Normalise the method so 'post' and 'POST' behave identically.
    http_method = (http_method or HttpMethod.POST).upper()
    if http_method not in HttpMethod.ALL:
        raise ParameterError(
            f"Unsupported HTTP method {http_method!r}. "
            f"Supported methods are: {', '.join(HttpMethod.ALL)}.")

    # Legacy shorthands ('json', 'urlencoded') are deliberately NOT accepted
    # here. Converting them is the job of the migration for stored data and of
    # the event handler's tolerant reader for unmigrated inline options; a
    # first-class webhook always carries a real MIME type. Rejecting them loudly
    # beats storing 'json' and later sending an invalid Content-Type header.
    content_type = content_type or ContentType.JSON
    if "/" not in content_type:
        raise ParameterError(
            f"{content_type!r} is not a valid content type. Expected a MIME "
            f"type such as {ContentType.JSON!r} or {ContentType.URLENCODED!r}.")

    auth_type = (auth_type or AuthType.NONE).lower()
    if auth_type not in AuthType.ALL:
        raise ParameterError(
            f"Unsupported authentication type {auth_type!r}. "
            f"Supported types are: {', '.join(AuthType.ALL)}.")

    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        raise ParameterError(f"The timeout must be an integer, got {timeout!r}.")
    if timeout <= 0:
        raise ParameterError(
            f"The timeout must be a positive number of seconds, got {timeout}.")

    # Auth-type specific requirements.
    if auth_type == AuthType.BASIC and not username:
        raise ParameterError(
            "Basic authentication requires a username.")
    if auth_type == AuthType.MTLS and not client_certificate:
        raise ParameterError(
            "Mutual TLS authentication requires a client certificate.")
    if auth_type == AuthType.HEADER and not headers:
        raise ParameterError(
            "Header authentication requires at least one header "
            "(e.g. 'Authorization' or 'X-API-Key').")

    return url, http_method, content_type, auth_type, timeout


def _webhook_to_dict(webhook, censor=False):
    """
    Turn a :class:`Webhook` database object into a plain dict.

    :param webhook: the database object
    :param censor: when True, secrets (basic-auth password, client key
        password and the values of headers marked as encrypted) are replaced
        by the ``__CENSORED__`` placeholder. When False they are returned
        decrypted, ready to be used or re-imported.
    :return: a dict describing the webhook
    """
    result = webhook.get()
    # Webhook.get() returns the raw, still-encrypted secret columns.
    for key in SECRET_KEYS:
        if censor:
            result[key] = CENSORED if result.get(key) else ""
        else:
            result[key] = _decrypt_or_empty(result.get(key))

    # Webhook.header_dict (used by get()) already decrypts. Note which headers
    # are secret so the value can be censored and a round-trip through the API
    # preserves the 'encrypted' flag.
    secret_headers = [h.key for h in webhook.headers if h.encrypted]
    result["secret_headers"] = secret_headers
    if censor:
        result["headers"] = {
            key: (CENSORED if key in secret_headers and value else value)
            for key, value in result.get("headers", {}).items()
        }
    return result


def _apply_headers(webhook, headers, secret_headers):
    """
    Synchronise the ``webhookheader`` rows of ``webhook`` with ``headers``.

    Headers absent from ``headers`` are deleted, existing ones are updated and
    new ones are created. A value of ``__CENSORED__`` means "keep the stored
    value"; in that case only the encryption flag may still be toggled, which
    mirrors the behaviour of ``set_smsgateway()``.

    :param webhook: the Webhook database object (must already have an id)
    :param headers: dict of header name -> value
    :param secret_headers: iterable of header names whose values are secret
        and must be stored encrypted
    """
    headers = headers or {}
    secret_headers = set(secret_headers or ())

    existing = {h.key: h for h in webhook.headers}

    # 1. Remove headers that are no longer configured.
    for key, row in existing.items():
        if key not in headers:
            db.session.delete(row)

    # 2. Create or update the configured headers.
    for key, value in headers.items():
        should_be_secret = key in secret_headers
        row = existing.get(key)

        if is_censored(value):
            # The caller did not send the real value back.
            if row is None:
                # Nothing is stored yet, so there is no value to keep. Create
                # the header with an empty value rather than dropping it: the
                # name and the "encrypted" flag are configuration too, and this
                # mirrors how a censored password behaves on create (the column
                # exists and is empty). Silently discarding it would leave a
                # header-authenticated webhook without any header at all.
                WebhookHeader(webhook_id=webhook.id, key=key, value="",
                              encrypted=should_be_secret)
                continue
            # Keep the stored value, but still honor a change of the
            # "encrypted" checkbox.
            if should_be_secret == bool(row.encrypted):
                continue
            current = row.value or ""
            if should_be_secret:
                row.value = encryptPassword(current) if current else ""
                row.encrypted = True
            else:
                if current:
                    decrypted = decryptPassword(current)
                    if decrypted == FAILED_TO_DECRYPT_PASSWORD:
                        # Never replace unreadable ciphertext with garbage.
                        log.warning(
                            f"Could not decrypt header {key!r} while turning off "
                            f"encryption. Leaving the stored value untouched.")
                        continue
                    current = decrypted
                row.value = current
                row.encrypted = False
            continue

        stored_value = value
        if should_be_secret and value:
            stored_value = encryptPassword(value)

        if row is None:
            # WebhookHeader.__init__ persists the row itself.
            WebhookHeader(webhook_id=webhook.id, key=key, value=stored_value,
                          encrypted=should_be_secret)
        else:
            row.value = stored_value
            row.encrypted = should_be_secret


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@log_with(log)
def get_webhook_object(identifier):
    """
    Return the :class:`Webhook` *database object* for ``identifier``.

    Intended for internal callers that need the raw row (for example
    ``fire_webhook()``). Application code that only needs the configuration
    should use :func:`get_webhook`.

    :param identifier: the unique name of the webhook definition
    :return: a Webhook database object
    :raises ResourceNotFoundError: if no such webhook exists
    """
    return fetch_one_resource(Webhook, identifier=identifier)


@log_with(log, log_exit=False)
def get_webhook(identifier, censor=False):
    """
    Return a single webhook configuration as a dict.

    :param identifier: the unique name of the webhook definition
    :param censor: replace secrets with the ``__CENSORED__`` placeholder
    :return: a dict describing the webhook
    :raises ResourceNotFoundError: if no such webhook exists
    """
    return _webhook_to_dict(get_webhook_object(identifier), censor=censor)


@log_with(log, log_exit=False)
def get_webhooks(identifier=None, censor=False):
    """
    Return a list of webhook configurations.

    :param identifier: restrict the result to this identifier. Since the
        identifier is unique, this returns a list of either one or no entry.
    :param censor: replace secrets with the ``__CENSORED__`` placeholder
    :return: list of webhook dicts, ordered by identifier
    """
    stmt = select(Webhook)
    if identifier:
        stmt = stmt.filter(Webhook.identifier == identifier)
    stmt = stmt.order_by(Webhook.identifier)

    return [_webhook_to_dict(row, censor=censor)
            for row in db.session.scalars(stmt).all()]


@log_with(log, log_exit=False)
def get_webhook_identifiers():
    """
    Return the sorted list of all configured webhook identifiers.

    This is what the event handler and Conditional Access dropdowns need; it
    avoids loading and decrypting every webhook just to render a select box.

    :return: list of identifier strings
    """
    stmt = select(Webhook.identifier).order_by(Webhook.identifier)
    return list(db.session.scalars(stmt).all())


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

# log_entry=False, not a plain @log_with(log): two of the arguments carry
# secrets that the name based hiding of log_with() cannot recognise. The URL may
# embed a token in its path, and a secret header is secret by virtue of being
# listed in secret_headers -- its name ("X-Webhook-Token") says nothing, so the
# denylist cannot hide its value. Only the whole argument list can be withheld.
# The identifier is logged at INFO on the way out, which is the line an admin
# reads to see that the write happened.
@log_with(log, log_entry=False)
def set_webhook(identifier, url=None, description=None, http_method=None,
                content_type=None, default_payload=None,
                auth_type=None, username=None, password=None,
                verify_tls=None, tls_ca_bundle=None,
                client_certificate=None, client_key=None,
                client_key_password=None,
                http_proxy=None, https_proxy=None, timeout=None,
                headers=None, secret_headers=None):
    """
    Create or update a webhook definition.

    If a webhook with this ``identifier`` already exists it is updated,
    otherwise a new one is created. On update, every parameter left at ``None``
    keeps its stored value, so a partial update is possible. ``url`` is only
    required when creating a new webhook.

    Secrets (``password``, ``client_key_password`` and the values of headers
    listed in ``secret_headers``) are encrypted with ``encryptPassword()``
    before being written. Passing the ``__CENSORED__`` placeholder for a secret
    keeps the stored value unchanged, so a configuration read from the API can
    be written back without destroying the credential.

    :param identifier: the unique name of this webhook definition
    :param url: the target URL. Must start with http:// or https://
    :param description: a free-text description
    :param http_method: one of GET, POST, PUT, PATCH (default POST)
    :param content_type: MIME type of the request body (default application/json)
    :param default_payload: optional body template used when the call site
        supplies no payload of its own
    :param auth_type: one of 'none', 'basic', 'header', 'mtls'
    :param username: username for basic authentication
    :param password: password for basic authentication (stored encrypted)
    :param verify_tls: whether to verify the server certificate
    :type verify_tls: bool or None
    :param tls_ca_bundle: optional path to a CA bundle used for verification
    :param client_certificate: path to the client certificate (mTLS)
    :param client_key: path to the client key (mTLS)
    :param client_key_password: password of the client key (stored encrypted)
    :param http_proxy: proxy URL for http:// requests
    :param https_proxy: proxy URL for https:// requests
    :param timeout: request timeout in seconds (default 3)
    :param headers: dict of static HTTP headers to send with every request.
        When given, it replaces the stored headers entirely: headers missing
        from the dict are deleted. ``None`` keeps the stored headers.
    :type headers: dict or None
    :param secret_headers: iterable of header names whose values must be
        stored encrypted
    :return: the database id of the webhook
    :raises ParameterError: if a parameter is missing or invalid
    """
    stmt = select(Webhook).filter(Webhook.identifier == identifier)
    webhook = db.session.execute(stmt).scalar_one_or_none()
    creating = webhook is None

    if creating and not url:
        raise ParameterError(
            f"Cannot create the webhook {identifier!r} without a URL.")

    # For an update, fall back to the stored values so that validation sees the
    # configuration as it will be *after* the update, not just the new fragments.
    # Webhook.get() yields plain Python values, which keeps the ORM's Mapped[...]
    # types out of the validation code below.
    stored = webhook.get() if webhook is not None else {}

    def pick(new_value, key):
        """Use the supplied value, or fall back to what is stored."""
        return new_value if new_value is not None else stored.get(key)

    (effective_url, effective_method, effective_content_type, effective_auth,
     effective_timeout) = _validate(
        identifier=identifier,
        url=pick(url, "url"),
        http_method=pick(http_method, "http_method"),
        content_type=pick(content_type, "content_type"),
        auth_type=pick(auth_type, "auth_type"),
        timeout=pick(timeout, "timeout"),
        username=pick(username, "username"),
        client_certificate=pick(client_certificate, "client_certificate"),
        headers=pick(headers, "headers"),
    )

    # A censored secret means "keep what is stored", so leave it out of the
    # update entirely. An empty string clears it; any other value replaces it.
    encrypted_password = None
    if password is not None and not is_censored(password):
        encrypted_password = encryptPassword(password) if password else ""
    encrypted_key_password = None
    if client_key_password is not None and not is_censored(client_key_password):
        encrypted_key_password = (
            encryptPassword(client_key_password) if client_key_password else "")

    if webhook is None:
        # Seed the columns the model would otherwise leave as None; the
        # optional parameters below may still overwrite them.
        webhook = Webhook(identifier=identifier, url=effective_url,
                          description="", verify_tls=True)
        db.session.add(webhook)

    # Always write the normalised values.
    webhook.url = effective_url
    webhook.http_method = effective_method
    webhook.content_type = effective_content_type
    webhook.auth_type = effective_auth
    webhook.timeout = effective_timeout

    if description is not None:
        webhook.description = description
    if default_payload is not None:
        webhook.default_payload = default_payload
    if username is not None:
        webhook.username = username
    if encrypted_password is not None:
        webhook.password = encrypted_password
    if verify_tls is not None:
        webhook.verify_tls = bool(verify_tls)
    if tls_ca_bundle is not None:
        webhook.tls_ca_bundle = tls_ca_bundle
    if client_certificate is not None:
        webhook.client_certificate = client_certificate
    if client_key is not None:
        webhook.client_key = client_key
    if encrypted_key_password is not None:
        webhook.client_key_password = encrypted_key_password
    if http_proxy is not None:
        webhook.http_proxy = http_proxy
    if https_proxy is not None:
        webhook.https_proxy = https_proxy

    # Need the primary key before the header rows can reference it.
    db.session.flush()

    if headers is not None:
        _apply_headers(webhook, headers, secret_headers)

    db.session.commit()
    log.info(f"{'Created' if creating else 'Updated'} webhook {identifier!r} "
             f"(id {webhook.id})")
    return webhook.id


@log_with(log)
def delete_webhook(identifier):
    """
    Delete the webhook definition with the given identifier.

    The associated header rows are removed as well (ON DELETE CASCADE plus an
    explicit delete in :meth:`Webhook.delete`).

    :param identifier: the unique name of the webhook definition
    :return: the database id of the deleted entry
    :raises ResourceNotFoundError: if no such webhook exists
    """
    return fetch_one_resource(Webhook, identifier=identifier).delete()


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

class _SSLContextAdapter(HTTPAdapter):
    """
    A ``requests`` adapter that uses a pre-built :class:`ssl.SSLContext`.

    Needed only for mutual TLS with a password-protected client key: the
    ``cert=`` parameter of ``requests`` cannot carry a key password, so the
    key has to be loaded into an SSLContext up front.
    """

    def __init__(self, ssl_context, **kwargs):
        self._ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super().proxy_manager_for(*args, **kwargs)


def _build_verify(config):
    """
    Translate the TLS columns into the ``verify`` argument of ``requests``.

    Disabling verification wins over a configured CA bundle: if an
    administrator explicitly turned verification off, we do not silently
    re-enable it because a bundle happens to be set.
    """
    if not config["verify_tls"]:
        return False
    return config["tls_ca_bundle"] or True


def _build_proxies(config):
    """Return a ``proxies`` dict for requests, or None when none is set."""
    proxies = {}
    if config["http_proxy"]:
        proxies["http"] = config["http_proxy"]
    if config["https_proxy"]:
        proxies["https"] = config["https_proxy"]
    return proxies or None


def _build_auth_and_cert(config):
    """
    Derive the ``auth`` and ``cert`` arguments from the authentication config.

    :return: a ``(auth, cert, key_password)`` tuple. ``key_password`` is only
        set for mTLS with an encrypted client key and signals that a custom
        SSLContext is required.
    """
    auth_type = config["auth_type"]

    if auth_type == AuthType.BASIC:
        # config["password"] is already decrypted by _webhook_to_dict().
        return (config["username"], config["password"]), None, None

    if auth_type == AuthType.MTLS:
        certificate = config["client_certificate"]
        key = config["client_key"]
        key_password = config["client_key_password"]
        if key_password:
            # requests' cert= cannot carry a password; handled via SSLContext.
            return None, (certificate, key), key_password
        cert = (certificate, key) if key else certificate
        return None, cert, None

    # AuthType.NONE needs nothing; AuthType.HEADER is carried by the
    # configured static headers, which are sent for every auth type anyway.
    return None, None, None


def _resolve_body(config, payload):
    """
    Determine the request body.

    Precedence: an explicit ``payload`` from the call site beats the webhook's
    ``default_payload``; if neither is set, no body is sent.

    A dict payload is serialised according to the configured content type:
    JSON is dumped, anything else is handed to ``requests`` which form-encodes
    it.

    :return: the body to send, or None
    """
    if payload is None:
        payload = config["default_payload"]
    if payload is None or payload == "":
        return None
    if isinstance(payload, (dict, list)):
        if config["content_type"] == ContentType.JSON:
            return json.dumps(payload)
        # Let requests form-encode a dict for urlencoded and friends.
        return payload
    return payload


def _truncate(text):
    """Shorten a response body for logging and for the returned result."""
    if text is None:
        return ""
    text = str(text)
    if len(text) <= MAX_RESPONSE_LENGTH:
        return text
    return f"{text[:MAX_RESPONSE_LENGTH]}... [truncated]"


# ---------------------------------------------------------------------------
# Outbound request guard (opt-in, see issue #5751)
# ---------------------------------------------------------------------------

class GuardMode:
    """
    Modes of the outbound request guard, controlled by the
    ``PI_OUTBOUND_GUARD`` app config key.

    ``OFF`` (the default, and the only mode for the life of the 3.x line
    unless an admin opts in) performs no checks at all -- byte-for-byte the
    behaviour of privacyIDEA 3.14 and older. ``WARN`` runs every check but
    still sends the request, logging what *would* have been rejected.
    ``ENFORCE`` actually blocks a rejected request.
    """
    OFF = "off"
    WARN = "warn"
    ENFORCE = "enforce"

    ALL = (OFF, WARN, ENFORCE)


#: Networks the guard rejects by default when it is not in OFF mode: loopback,
#: RFC1918 private space, link-local (this also covers the cloud metadata
#: endpoint 169.254.169.254), unique-local IPv6, the "this network" range and
#: CGNAT. IPv4-mapped IPv6 forms of an address (e.g. ``::ffff:127.0.0.1``) are
#: unwrapped and checked against the IPv4 entries in :func:`_is_blocked_address`.
BLOCKED_NETWORKS = tuple(ipaddress.ip_network(cidr) for cidr in (
    "127.0.0.0/8", "0.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12",
    "192.168.0.0/16", "169.254.0.0/16", "100.64.0.0/10",
    "::1/128", "fe80::/10", "fc00::/7",
))


def _is_blocked_address(address):
    """Return True if the literal IP address string falls in a blocked range."""
    addr = ipaddress.ip_address(address)
    candidates = [addr]
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        candidates.append(mapped)
    return any(candidate.version == network.version and candidate in network
               for candidate in candidates for network in BLOCKED_NETWORKS)


def _same_address(left, right):
    """
    Whether two IP address strings denote the same address, comparing them as
    addresses rather than as text: ``::1`` and ``0:0:0:0:0:0:0:1`` are one
    address written two ways, and a plain string comparison would miss it.
    A value that is not an IP address at all (a hostname) never matches.
    """
    if not left or not right:
        return False
    try:
        return ipaddress.ip_address(left) == ipaddress.ip_address(right)
    except ValueError:
        return False


def _entry_matches(entry, host, address, port):
    """
    Check a single ``PI_OUTBOUND_GUARD_ALLOW`` entry against the target.

    An entry containing a ``/`` is a CIDR and matches the resolved
    ``address`` regardless of port. Otherwise it is a bare host or IP,
    optionally followed by ``:port``, and matches either the hostname as
    configured on the webhook or the resolved address.

    A bare IPv6 address is recognised whether or not it is bracketed, so
    ``::1`` works as an entry and not only ``[::1]``. It has to be: that is
    the spelling :data:`BLOCKED_NETWORKS` itself uses, so it is the spelling
    an admin reads off the blocked list when writing an exception for it.
    Bracketing is only needed to attach a port (``[::1]:8443``), since
    otherwise the last colon group is indistinguishable from one.

    This never raises. A malformed entry - an unparsable port, say - matches
    nothing rather than failing the delivery it was meant to permit.
    """
    entry = entry.strip()
    if not entry:
        return False
    if "/" in entry:
        if address is None:
            return False
        try:
            network = ipaddress.ip_network(entry, strict=False)
            addr = ipaddress.ip_address(address)
        except ValueError:
            return False
        return addr.version == network.version and addr in network

    try:
        # A bare IP address, port-less by construction: an unbracketed IPv6
        # address cannot carry one, and urlsplit would read its last colon
        # group as a port and fail.
        ipaddress.ip_address(entry)
        entry_host, entry_port = entry, None
    except ValueError:
        parsed = urlsplit(f"//{entry}")
        try:
            entry_port = parsed.port
        except ValueError:
            # Not a port at all; the entry describes no reachable target.
            return False
        entry_host = parsed.hostname
        if entry_host is None:
            return False

    if entry_port is not None and entry_port != port:
        return False
    return (entry_host.lower() == (host.lower() if host else None)
            or _same_address(entry_host, address))


def _resolve(host):
    """Return the de-duplicated list of IP addresses `host` resolves to."""
    infos = socket.getaddrinfo(host, None)
    addresses = []
    seen = set()
    for _family, _type, _proto, _canonname, sockaddr in infos:
        address = sockaddr[0].split("%", 1)[0]  # strip an IPv6 zone id
        if address not in seen:
            seen.add(address)
            addresses.append(address)
    return addresses


def check_outbound_target(url, mode=GuardMode.OFF, allowlist=None):
    """
    Check whether the host or an address it resolves to is allowed to be
    contacted, per the outbound request guard.

    This function does **not** decide whether a rejection blocks the
    request -- that is the caller's job, since the same rejection means
    "don't send it" in ``enforce`` mode and "send it, but log and audit
    the rejection" in ``warn`` mode.

    :param url: the target URL (or, when a proxy is configured for the
        request, the proxy's URL -- the guard must check whatever address
        the connection actually goes to)
    :param mode: one of :class:`GuardMode`. In ``OFF`` mode this function
        does nothing at all and returns immediately, so an installation
        that has not opted in sees no behaviour change and no added latency.
    :param allowlist: iterable of CIDR and/or host[:port] entries that are
        permitted even though they fall in a blocked range
    :return: None if the target may be contacted, otherwise a human-readable
        rejection reason
    """
    if mode == GuardMode.OFF:
        return None

    allowlist = allowlist or ()
    parsed = urlsplit(url)
    host = parsed.hostname
    if not host:
        return f"could not determine a host to check in {url!r}"
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        # _validate() only checks the scheme prefix, so a stored URL may carry
        # something that is not a port. The guard cannot judge a target it
        # cannot parse, so it refuses it rather than waving it through.
        return f"could not determine a port to check in {url!r}"

    if any(_entry_matches(entry, host, None, port) for entry in allowlist):
        return None

    try:
        addresses = _resolve(host)
    except socket.gaierror as ex:
        return f"could not resolve host {host!r}: {ex}"

    for address in addresses:
        if any(_entry_matches(entry, host, address, port) for entry in allowlist):
            continue
        if _is_blocked_address(address):
            return (f"the address {address} that {host!r} resolves to falls "
                    f"in a network range blocked by the outbound request guard")
    return None


def _guard_config():
    """Read the outbound guard's mode and allowlist from the app config."""
    mode = str(current_app.config.get("PI_OUTBOUND_GUARD", GuardMode.OFF)).lower()
    if mode not in GuardMode.ALL:
        log.warning(f"Invalid PI_OUTBOUND_GUARD value {mode!r}, treating as "
                    f"{GuardMode.OFF!r}.")
        mode = GuardMode.OFF
    allowlist = current_app.config.get("PI_OUTBOUND_GUARD_ALLOW", [])
    return mode, allowlist


def _guard_target(config):
    """
    Return the URL the guard should check for this webhook's request.

    When a proxy is configured for the scheme in use, the connection goes to
    the proxy, so the proxy is what the guard must check -- the destination
    host is resolved by the proxy, not by us, and checking it would protect
    against nothing.
    """
    scheme = urlsplit(config["url"]).scheme
    proxies = _build_proxies(config) or {}
    return proxies.get(scheme) or config["url"]


def _record_webhook_call(identifier, start, success, error=False):
    """Emit duration and outcome metrics, mirroring _record_email_send()."""
    labels = {"identifier": identifier}
    observe("webhook_send_duration_seconds", time.monotonic() - start, labels)
    if error:
        result = "error"
    else:
        result = "ok" if success else "failed"
    inc("webhook_send_total", {**labels, "result": result})


@log_with(log, log_exit=False)
def fire_webhook(identifier, payload=None):
    """
    Send the request described by the webhook ``identifier``.

    Delivery is **synchronous**: the caller waits for the response (bounded by
    the webhook's timeout). Pointing a webhook at a slow endpoint therefore
    adds latency to the triggering request. There are no retries.

    This function **never raises**. Any transport problem is caught, logged at
    WARNING and reported through the returned dict, so that a dead webhook can
    neither fail an authentication nor abort the remaining event handler
    actions.

    Logging is deliberately restrained: the URL may embed a token and the
    headers may carry credentials, so neither is ever logged. The response body
    is logged at DEBUG only, since it can contain user data.

    :param identifier: the unique name of the webhook definition
    :param payload: the request body. A str is sent as-is; a dict or list is
        serialised according to the webhook's content type. When None, the
        webhook's ``default_payload`` is used.
    :return: a dict with the keys

        ``success``
            True if the endpoint answered with a 2xx status
        ``status_code``
            the HTTP status code, or None if no response was received
        ``response``
            the (truncated) response body, or "" on failure
        ``error``
            a message describing the failure, or None on success
    """
    start = time.monotonic()
    try:
        config = get_webhook(identifier)
    except Exception as ex:
        # An unknown identifier is a configuration error, not a transport
        # error, but it must not propagate either.
        log.warning(f"Cannot fire webhook {identifier!r}: {ex}")
        _record_webhook_call(identifier, start, False, error=True)
        return {"success": False, "status_code": None, "response": "",
                "error": str(ex)}

    # Everything from here on runs inside the try: the guard reads the app
    # config and parses a stored URL, and the request setup decrypts secrets
    # and reads key files off disk, so either can raise on a misconfiguration.
    # This function promises never to raise - an event handler configured to
    # abort on error would otherwise fail the API request that triggered it -
    # so a failure anywhere in here has to come back as a reported failure.
    session = None
    try:
        mode, allowlist = _guard_config()
        rejection = check_outbound_target(_guard_target(config), mode=mode,
                                          allowlist=allowlist)
        if rejection:
            log.warning(f"Webhook {identifier!r}: outbound request guard "
                        f"({mode}) rejected the target: {rejection}")
            if mode == GuardMode.ENFORCE:
                _record_webhook_call(identifier, start, False, error=True)
                return {"success": False, "status_code": None, "response": "",
                        "error": f"blocked by the outbound request guard "
                                 f"({mode}): {rejection}"}
            # warn mode: the request still goes out. fire_webhook() has no audit
            # object to write to, so the log line above is the only record of
            # the rejection; it does not appear in the audit log.

        headers = dict(config["headers"] or {})
        body = _resolve_body(config, payload)
        if body is not None:
            # Only advertise a content type when there is something to describe.
            headers.setdefault("Content-Type", config["content_type"])

        auth, cert, key_password = _build_auth_and_cert(config)
        verify = _build_verify(config)
        proxies = _build_proxies(config)
        # requests treats None as "not set" for data, auth, cert and proxies, so
        # they can all be passed unconditionally.
        if key_password:
            # Encrypted client key: requests' cert= parameter has no way to pass
            # the password, so the chain is loaded into an SSLContext instead and
            # cert= is left unset.
            cert = None
            certificate = config["client_certificate"]
            key = config["client_key"]
            context = ssl.create_default_context()
            if verify is False:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            context.load_cert_chain(certificate, key or None,
                                    password=key_password)
            session = requests.Session()
            session.mount("https://", _SSLContextAdapter(context))
            requester = session.request
        else:
            requester = requests.request

        response = requester(
            config["http_method"], config["url"],
            headers=headers,
            data=body,
            auth=auth,
            cert=cert,
            verify=verify,
            proxies=proxies,
            timeout=config["timeout"],
            # A redirect target was never checked by the guard above, so
            # following one would defeat it. Only deviate from the previous
            # default (True, the behaviour of privacyIDEA 3.14 and older)
            # once the guard is actually active -- an installation on OFF
            # must see byte-for-byte identical behaviour.
            allow_redirects=(mode == GuardMode.OFF),
        )
        success = response.ok
        body_text = _truncate(response.text)

        # Never log the URL (it may embed a token) or the headers.
        log.info(f"Webhook {identifier!r} answered with HTTP "
                 f"{response.status_code}")
        log.debug(f"Webhook {identifier!r} response body: {body_text}")
        if not success:
            log.warning(f"Webhook {identifier!r} failed with HTTP "
                        f"{response.status_code}")

        _record_webhook_call(identifier, start, success)
        return {"success": success, "status_code": response.status_code,
                "response": body_text,
                "error": None if success else f"HTTP {response.status_code}"}
    except Exception as ex:
        # Deliberately broad: a webhook must never break its caller, so even a
        # programming error in the TLS setup is downgraded to a logged failure.
        log.warning(f"Webhook {identifier!r} could not be delivered: "
                    f"{ex.__class__.__name__}: {ex}")
        _record_webhook_call(identifier, start, False, error=True)
        return {"success": False, "status_code": None, "response": "",
                "error": f"{ex.__class__.__name__}: {ex}"}
    finally:
        if session is not None:
            session.close()


@log_with(log, log_exit=False)
def test_webhook(identifier, payload=None):
    """
    Fire a webhook for testing purposes and report the outcome.

    This is what the "Test" button of the configuration UI calls. It is a thin
    wrapper around :func:`fire_webhook` and shares its contract: it never
    raises, and it returns the same result dict.

    .. note::
       Import this under an alias in test modules (e.g.
       ``from privacyidea.lib.webhook import test_webhook as run_webhook_test``)
       so pytest does not try to collect it as a test case.

    :param identifier: the unique name of the webhook definition
    :param payload: an optional body overriding the webhook's default payload
    :return: the result dict of :func:`fire_webhook`
    """
    return fire_webhook(identifier, payload=payload)


# ---------------------------------------------------------------------------
# Configuration export / import
# ---------------------------------------------------------------------------

#: Keys of a webhook dict that identify the object rather than describe its
#: configuration, and therefore must not be written back on import.
_NON_CONFIG_KEYS = ("id", "identifier")


@register_export('webhook')
def export_webhook(name=None, censor=False):
    """
    Export the given, or all, webhook definitions.

    The result maps the webhook identifier to its configuration, which is
    exactly the set of keyword arguments :func:`set_webhook` accepts, so
    :func:`import_webhook` can feed it straight back.

    :param name: export only this identifier (default: export all)
    :param censor: if True, the basic-auth password, the client key password
        and the values of headers marked as encrypted are replaced by the
        ``__CENSORED__`` placeholder instead of being exported in clear text.
        Such an export is safe to share, but can only be re-imported on the
        instance it came from, where the placeholder means "keep the stored
        secret".
    :return: dict of identifier -> webhook configuration
    """
    result = {}
    for webhook in get_webhooks(identifier=name, censor=censor):
        identifier = webhook["identifier"]
        for key in _NON_CONFIG_KEYS:
            webhook.pop(key, None)
        result[identifier] = webhook
    return result


@register_import('webhook')
def import_webhook(data, name=None):
    """
    Import webhook definitions produced by :func:`export_webhook`.

    A secret carrying the ``__CENSORED__`` placeholder is *not* imported:
    :func:`set_webhook` keeps the stored value, so re-importing a censored
    export never wipes an existing credential. On an instance that does not
    know the webhook yet, such a secret simply stays empty and has to be
    entered once.

    :param data: dict of identifier -> webhook configuration
    :param name: import only this identifier (default: import all)
    """
    log.debug(f"Import webhook config: {sorted(data)}")
    known_parameters = set(inspect.signature(set_webhook).parameters) - {"identifier"}

    for res_name, res_data in data.items():
        if name and name != res_name:
            continue
        # Be tolerant about a hand-edited export: an unknown key would
        # otherwise abort the whole import with a TypeError.
        parameters = {}
        for key, value in res_data.items():
            if key in known_parameters:
                parameters[key] = value
            elif key not in _NON_CONFIG_KEYS:
                log.warning(f"Ignoring unknown key {key!r} while importing "
                            f"webhook {res_name!r}.")
        wid = set_webhook(res_name, **parameters)
        log.info(f"Import of webhook {res_name!r} finished, id: {wid}")
