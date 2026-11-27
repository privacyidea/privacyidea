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
import os
import re
import socket
import ssl
import time
from collections.abc import Iterable
from urllib.parse import quote_plus, urlsplit

import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from urllib3.exceptions import LocationParseError
from urllib3.util import Timeout, parse_url
from werkzeug.http import parse_options_header
from sqlalchemy import select

from privacyidea.lib.crypto import (encryptPassword, decryptPassword,
                                    FAILED_TO_DECRYPT_PASSWORD, is_censored,
                                    CENSORED)
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.metrics import inc, observe
from privacyidea.lib.smtpserver import check_number
from privacyidea.lib.utils import check_stored_secret_settings, fetch_one_resource
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
#: The largest timeout in seconds, the same as for an SMTP server.
MAX_TIMEOUT = 3600


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

MAX_RESPONSE_LENGTH = 1000
#: The number of bytes of a response body that are read. UTF-8 uses at most four bytes for a character, so this is
#: enough for MAX_RESPONSE_LENGTH characters and shows that the body is longer.
MAX_RESPONSE_BYTES = 4 * MAX_RESPONSE_LENGTH + 1

#: A header name as RFC 9110 defines it: a token of the characters below.
_HEADER_NAME = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
#: A header value that requests accepts: empty, or no leading whitespace and no line break.
_HEADER_VALUE = re.compile(r"\S[^\r\n]*|")


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


def _validate_identifier(identifier: str) -> None:
    """
    Reject an identifier that the API could store but then never address again.

    Every route but the listing puts the identifier in a path segment
    (``/webhook/<identifier>``), which is Flask's single-segment string converter. A WSGI server
    percent-decodes ``PATH_INFO`` before routing, so a ``/`` in the name cannot be escaped on the
    way in: ``encodeURIComponent()`` turns it into ``%2F``, that is decoded back to ``/``, and the
    rule no longer matches. Such a webhook appears in the listing and can then be neither read,
    saved, deleted nor tested. The same goes for ``.`` and ``..``, which path normalisation
    removes, and for control characters, which have no business in a URL at all.

    The restriction is deliberately narrow. Spaces, dots, ``#``, ``?`` and non-ASCII letters all
    survive the round trip once the client encodes them, and names like "My Hook" are in use, so
    there is no reason to require an identifier-shaped identifier.

    :param identifier: the identifier to check
    :raises ParameterError: if the identifier could not be addressed by the API
    """
    for character in ("/", "\\"):
        if character in identifier:
            raise ParameterError(
                f"The webhook identifier must not contain {character!r}: the API addresses a "
                f"webhook by its name in the URL path, and such a name can not be reached there.")
    if any(ord(character) < 32 or ord(character) == 127 for character in identifier):
        raise ParameterError(
            "The webhook identifier must not contain control characters: the API addresses a "
            "webhook by its name in the URL path.")
    if identifier in (".", ".."):
        raise ParameterError(
            f"{identifier!r} is not a usable webhook identifier: the API addresses a webhook by "
            f"its name in the URL path, where it would be removed as a path segment.")


def _check_text_parameters(**parameters: object) -> None:
    """
    Make sure that every given parameter is a string or None.

    A JSON request or an import can carry a number or a list where a text is expected. Without this check, such a
    value fails later with an AttributeError or a TypeError, which the API answers with HTTP 500.

    :param parameters: the parameters by name
    :raises ParameterError: if a parameter is neither a string nor None
    """
    for name, value in parameters.items():
        if value is not None and not isinstance(value, str):
            raise ParameterError(f"The parameter {name!r} must be a string, not {type(value).__name__}.")


def _check_lengths(**parameters: str | None) -> None:
    """
    Make sure that every given text fits into its column of the ``webhook`` table.

    PostgreSQL, MySQL, MariaDB and Oracle refuse a longer value with a database error, which the API answers with
    HTTP 500. SQLite stores it.

    :param parameters: the parameters by column name
    :raises ParameterError: if a value is longer than its column
    """
    for name, value in parameters.items():
        maximum = Webhook.__table__.c[name].type.length
        if value is not None and maximum is not None and len(value) > maximum:
            raise ParameterError(f"The parameter {name!r} must have at most {maximum} characters.")


def _check_header_arguments(headers: object, secret_headers: object, header_renames: object) -> None:
    """
    Make sure that the header arguments have the types that :func:`_stage_webhook` reads.

    A JSON request or an import can carry a list where an object is expected. Without this check, such a value fails
    later with an AttributeError or a TypeError, which the API answers with HTTP 500.

    :raises ParameterError: if an argument has the wrong type
    """
    if headers is not None and not isinstance(headers, dict):
        raise ParameterError("The headers must be an object that maps each header name to its value.")
    if secret_headers is not None and (isinstance(secret_headers, (str, bytes, dict))
                                       or not all(isinstance(name, str) for name in secret_headers)):
        raise ParameterError("The secret headers must be a list of header names.")
    if header_renames is not None and (not isinstance(header_renames, dict)
                                       or not all(isinstance(old_name, str) for old_name in header_renames.values())):
        raise ParameterError("A header rename must give the name that the header is stored under, as text.")


def _check_secret_flags(stored: dict, headers: dict, secret_headers: list | None, header_renames: dict | None) -> None:
    """
    Refuse a write that keeps the stored value of a secret header, but stores the header as not secret.

    A client never receives the value of a secret header, only ``__CENSORED__``. If a request sends this placeholder
    without the secret flag, the stored value is decrypted and stored in clear text, and the next read returns it.
    An administrator could then read a credential that the API never discloses, and send it to another URL. To store
    such a header in clear text, the request must send its value again. A secret header with an empty value has
    nothing to disclose.

    :param stored: the stored configuration, as :meth:`Webhook.get` returns it
    :param headers: the requested header set
    :param secret_headers: the names of the requested secret headers
    :param header_renames: dict of new header name -> the name it is stored under
    :raises ParameterError: if a kept secret value would be stored in clear text
    """
    stored_values = stored.get("headers") or {}
    stored_secret = set(stored.get("secret_headers") or ())
    flagged = set(secret_headers or ())
    for name, value in headers.items():
        if not is_censored(value) or name in flagged:
            continue
        stored_name = (header_renames or {}).get(name, name)
        if stored_name not in stored_values:
            # A rename that the stored rows show as done already
            stored_name = name
        if stored_name in stored_secret and stored_values.get(stored_name):
            raise ParameterError(f"The header {name!r} is secret. Enter its value again to store it unencrypted.")


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
    _check_text_parameters(url=url, http_method=http_method, content_type=content_type, auth_type=auth_type,
                           username=username, client_certificate=client_certificate)
    if not identifier or not identifier.strip():
        raise ParameterError("The webhook identifier must not be empty.")
    _validate_identifier(identifier)
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
    timeout = check_number(timeout, "timeout", 1, MAX_TIMEOUT)

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


def check_header(name: str, value: str) -> None:
    """
    Make sure that requests can send a header, without the header value in the error message.

    requests refuses an invalid header with a message that quotes the value. The value of a secret header must not
    appear in an error, a log line or an audit entry, so the header is checked here first. The name is checked
    against the token syntax of RFC 9110, which is stricter than requests: an empty name or a name with a colon or
    a space is refused.

    :param name: the header name
    :param value: the header value, or the ``__CENSORED__`` placeholder for a stored value
    :raises ParameterError: if requests can not send the header
    """
    if not isinstance(name, str) or not _HEADER_NAME.fullmatch(name):
        raise ParameterError(f"{name!r} is not a valid header name. A header name contains only letters, digits "
                             f"and the characters !#$%&'*+-.^_`|~.")
    maximum = WebhookHeader.__table__.c.key.type.length
    if len(name) > maximum:
        raise ParameterError(f"A header name must have at most {maximum} characters.")
    if not isinstance(value, str):
        raise ParameterError(f"The value of the header {name!r} must be a string.")
    if not _HEADER_VALUE.fullmatch(value):
        raise ParameterError(f"The value of the header {name!r} must not start with whitespace or contain a line "
                             f"break.")


def _kept_secrets(stored: dict, password: str | None, headers: dict | None, header_renames: dict | None) -> list[str]:
    """
    Name the stored secrets that a write keeps without the client sending them.

    A client that never received a secret sends ``__CENSORED__`` for it or omits it, and the stored secret stays.

    :param stored: the stored configuration, as :meth:`Webhook.get` returns it
    :param password: the requested password
    :param headers: the requested header set, or None to keep the stored headers
    :param header_renames: dict of new header name -> the name it is stored under
    :return: the kept secrets for the error message, for example ``["password", "value of the header
        'X-Token'"]``
    """
    kept = []
    if stored.get("password") and (password is None or is_censored(password)):
        kept.append("password")
    stored_values = stored.get("headers") or {}
    secret_names = [name for name in stored.get("secret_headers") or () if stored_values.get(name)]
    if headers is None:
        kept_headers = secret_names
    else:
        kept_headers = []
        for name, value in headers.items():
            stored_name = (header_renames or {}).get(name, name)
            if stored_name not in stored_values:
                # A rename that the stored rows show as done already
                stored_name = name
            if is_censored(value) and stored_name in secret_names:
                kept_headers.append(stored_name)
    kept.extend(f"value of the header {name!r}" for name in sorted(kept_headers))
    return kept


def _check_kept_secrets(identifier: str, stored: dict, kept: list[str], url: str | None, username: str | None,
                        verify_tls: bool | None, tls_ca_bundle: str | None, http_proxy: str | None,
                        https_proxy: str | None) -> None:
    """
    Make sure that a stored secret is sent only to the endpoint it was saved for.

    The password and the values of the secret headers go to the URL, through the proxies, with the TLS settings of
    the saved webhook. If a write keeps one of them, it must not change these settings: an administrator who can
    write webhooks must not be able to send a credential to another host without knowing it. Turning on the TLS
    verification is allowed. A requested value of None does not change a setting.

    :raises ParameterError: if a secret is kept and one of the settings changes
    """
    if not kept:
        return
    saved_settings = {"url": stored.get("url") or "", "http_proxy": stored.get("http_proxy") or "",
                      "https_proxy": stored.get("https_proxy") or "", "verify_tls": bool(stored.get("verify_tls")),
                      "tls_ca_bundle": stored.get("tls_ca_bundle") or "", "username": stored.get("username") or ""}
    requested_settings = {"url": url.strip() if isinstance(url, str) else url, "http_proxy": http_proxy,
                          "https_proxy": https_proxy, "verify_tls": False if verify_tls is False else None,
                          "tls_ca_bundle": tls_ca_bundle,
                          "username": username if "password" in kept else None}
    check_stored_secret_settings("webhook", identifier, saved_settings, requested_settings, " and the ".join(kept),
                                 "save")


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

    secret_headers = result["secret_headers"]
    if censor:
        result["headers"] = {
            key: (CENSORED if key in secret_headers and value else value)
            for key, value in result.get("headers", {}).items()
        }
    return result


def _apply_renames(webhook, renames):
    """
    Rename stored ``webhookheader`` rows before the set is synchronised.

    Applied first, so everything after it finds the row under its new name and the ordinary
    "keep the stored value" path does the rest.

    All renames are applied in one step, against the names stored before the request. So the
    editor's natural requests work: swapping the names of two headers, a chain like A to B and
    B to C, and renaming a header and then adding a new one under its old name.

    A rename onto the name of a stored row that is not renamed itself replaces that row: the
    header set of the request has one header of that name, and the rename says it is the renamed
    row, so the stored one is no longer part of the set. That is how the editor deletes header B
    and renames header A to B in one save.

    Re-sending a plain rename is a no-op rather than an error: a double submit would otherwise
    fail a request that has already done exactly what it asked for. A swap cannot be told apart
    from its repetition, so a swap sent twice swaps the names back.

    :param webhook: the Webhook database object
    :param renames: dict of new header name -> the name it is stored under
    :raises ParameterError: if a rename names no stored header, or if two renames name the same
        stored header
    """
    existing = {h.key: h for h in webhook.headers}
    pending = {}
    for new_key, old_key in (renames or {}).items():
        if new_key == old_key:
            continue
        if old_key not in existing:
            if new_key in existing:
                # Already renamed - the same request sent twice.
                continue
            raise ParameterError(f"Cannot rename the header {old_key!r} to {new_key!r}: no header "
                                 f"named {old_key!r} is stored on this webhook.")
        pending[new_key] = old_key

    sources = set(pending.values())
    if len(sources) != len(pending):
        duplicates = sorted({old for old in pending.values() if list(pending.values()).count(old) > 1})
        raise ParameterError(f"Cannot rename the header(s) {', '.join(map(repr, duplicates))} to "
                             f"more than one new name.")
    for new_key, old_key in pending.items():
        if new_key in existing and new_key not in sources:
            # The renamed row takes the name, so the stored row of that name leaves the set. The
            # relationship is dynamic, so _apply_headers() no longer finds it once it is deleted.
            db.session.delete(existing[new_key])
            log.info(f"Header {new_key!r} on webhook {webhook.identifier!r} is replaced by the "
                     f"header renamed from {old_key!r}.")

    # Collect the rows first: once one key has changed, a lookup by the stored name would find
    # the wrong row in a swap or a chain.
    rows = {new_key: existing[old_key] for new_key, old_key in pending.items()}
    for new_key, row in rows.items():
        row.key = new_key
        log.info(f"Renamed header {pending[new_key]!r} to {new_key!r} on webhook "
                 f"{webhook.identifier!r}, keeping its stored value.")


def _apply_headers(webhook, headers, secret_headers, renames=None):
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
    :param renames: dict of new header name -> the name it is stored under, applied before
        anything else looks at the stored rows (see :func:`_apply_renames`)
    """
    _apply_renames(webhook, renames)

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
                db.session.add(WebhookHeader(webhook_id=webhook.id, key=key, value="",
                                             encrypted=should_be_secret))
                continue
            # Keep the stored value, but still honor a change of the
            # "encrypted" checkbox. _check_secret_flags() refuses to keep a
            # secret value in clear text, so only an empty one gets here.
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
            # Added, not saved: the caller commits, so that _stage_webhook() never does.
            db.session.add(WebhookHeader(webhook_id=webhook.id, key=key, value=stored_value,
                                         encrypted=should_be_secret))
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
                content_type=None, default_payload=None, encode_values=None,
                auth_type=None, username=None, password=None,
                verify_tls=None, tls_ca_bundle=None,
                client_certificate=None, client_key=None,
                client_key_password=None,
                http_proxy=None, https_proxy=None, timeout=None,
                headers=None, secret_headers=None, header_renames=None):
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
    :param encode_values: whether the values that replace the placeholders of
        a plain-text payload are encoded for the content type: URL-encoded for
        ``application/x-www-form-urlencoded``, escaped as JSON string content
        for ``application/json`` (default True)
    :type encode_values: bool or None
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
    :param header_renames: dict of new header name -> the name it is currently stored under.
        Applied before the set is synchronised, so the renamed row keeps its value - which is the
        only way a secret header can be renamed at all, since the caller never holds its value and
        can only send the ``__CENSORED__`` placeholder for it.
    :type header_renames: dict or None
    :return: the database id of the webhook
    :raises ParameterError: if a parameter is missing or invalid
    """
    webhook_id = _stage_webhook(identifier, url=url, description=description, http_method=http_method,
                                content_type=content_type, default_payload=default_payload,
                                encode_values=encode_values, auth_type=auth_type, username=username,
                                password=password, verify_tls=verify_tls, tls_ca_bundle=tls_ca_bundle,
                                client_certificate=client_certificate, client_key=client_key,
                                client_key_password=client_key_password,
                                http_proxy=http_proxy, https_proxy=https_proxy, timeout=timeout,
                                headers=headers, secret_headers=secret_headers, header_renames=header_renames)
    db.session.commit()
    return webhook_id


def _stage_webhook(identifier: str, url: str | None = None, description: str | None = None,
                   http_method: str | None = None, content_type: str | None = None,
                   default_payload: str | None = None, encode_values: bool | None = None,
                   auth_type: str | None = None, username: str | None = None,
                   password: str | None = None, verify_tls: bool | None = None, tls_ca_bundle: str | None = None,
                   client_certificate: str | None = None, client_key: str | None = None,
                   client_key_password: str | None = None, http_proxy: str | None = None,
                   https_proxy: str | None = None, timeout: int | None = None, headers: dict | None = None,
                   secret_headers: Iterable[str] | None = None, header_renames: dict | None = None) -> int:
    """
    Write the webhook like :func:`set_webhook`, but do not commit, so that the configuration import can write
    webhooks and event handlers in one transaction.
    """
    _check_text_parameters(url=url, description=description, http_method=http_method, content_type=content_type,
                           default_payload=default_payload, auth_type=auth_type, username=username,
                           password=password, tls_ca_bundle=tls_ca_bundle, client_certificate=client_certificate,
                           client_key=client_key, client_key_password=client_key_password, http_proxy=http_proxy,
                           https_proxy=https_proxy)
    if secret_headers is not None and not isinstance(secret_headers, (str, bytes, dict)):
        # Read more than once below
        secret_headers = list(secret_headers)
    _check_header_arguments(headers, secret_headers, header_renames)
    _check_lengths(identifier=identifier, url=url, description=description, content_type=content_type,
                   username=username, tls_ca_bundle=tls_ca_bundle, client_certificate=client_certificate,
                   client_key=client_key, http_proxy=http_proxy, https_proxy=https_proxy)

    stmt = select(Webhook).filter(Webhook.identifier == identifier)
    webhook = db.session.execute(stmt).scalar_one_or_none()
    creating = webhook is None

    if creating and not url:
        raise ParameterError(
            f"Cannot create the webhook {identifier!r} without a URL.")

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
    # Checked before anything is written: a refused header must not leave a new webhook in the session.
    for key, value in (headers or {}).items():
        check_header(key, "" if is_censored(value) else value)
    if webhook is not None:
        _check_kept_secrets(identifier, stored, _kept_secrets(stored, password, headers, header_renames),
                            url=url, username=username,
                            verify_tls=None if verify_tls is None else bool(verify_tls),
                            tls_ca_bundle=tls_ca_bundle, http_proxy=http_proxy, https_proxy=https_proxy)
        if headers is not None:
            _check_secret_flags(stored, headers, secret_headers, header_renames)

    encrypted_password = None
    if password is not None and not is_censored(password):
        encrypted_password = encryptPassword(password) if password else ""
    encrypted_key_password = None
    if client_key_password is not None and not is_censored(client_key_password):
        encrypted_key_password = (
            encryptPassword(client_key_password) if client_key_password else "")
    # The columns hold the encrypted value, which is longer than the password
    for name, encrypted in (("password", encrypted_password), ("client_key_password", encrypted_key_password)):
        if encrypted and len(encrypted) > Webhook.__table__.c[name].type.length:
            raise ParameterError(f"The {name.replace('_', ' ')} is too long.")

    if webhook is None:
        webhook = Webhook(identifier=identifier, url=effective_url,
                          description="", verify_tls=True)
        db.session.add(webhook)

    webhook.url = effective_url
    webhook.http_method = effective_method
    webhook.content_type = effective_content_type
    webhook.auth_type = effective_auth
    webhook.timeout = effective_timeout

    if description is not None:
        webhook.description = description
    if default_payload is not None:
        webhook.default_payload = default_payload
    if encode_values is not None:
        webhook.encode_values = bool(encode_values)
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
        _apply_headers(webhook, headers, secret_headers, renames=header_renames)
    elif header_renames:
        raise ParameterError("Renaming a header requires sending the header set it belongs to.")

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
        return (config["username"], config["password"]), None, None

    if auth_type == AuthType.MTLS:
        certificate = config["client_certificate"]
        key = config["client_key"]
        key_password = config["client_key_password"]
        if key_password:
            return None, (certificate, key), key_password
        cert = (certificate, key) if key else certificate
        return None, cert, None

    return None, None, None


def media_type(content_type):
    """
    Return the bare media type of a ``Content-Type`` value, lower-cased.

    A Content-Type is a media type plus optional parameters, so
    ``application/json; charset=utf-8`` names the same type as ``application/json`` - and a
    webhook stores whatever an administrator types, the field offering "any valid MIME type".
    Every decision that turns on "is this JSON?" therefore has to compare the media type rather
    than the whole string.

    Comparing the whole string is not merely imprecise, it breaks the case the comparison is
    there for: a JSON body then takes the plain-text path, where ``str.format()`` reads the
    document's own braces as placeholder syntax and the substitution fails outright, leaving the
    template unreplaced.

    :param content_type: the stored Content-Type, which may be None or empty
    :return: the media type in lower case, or "" when there is none
    """
    return parse_options_header(content_type or "")[0].strip().lower()


def placeholder_values(tags: dict, content_type: str | None, encode_values: bool) -> dict:
    """
    Return the values for the placeholders of a plain-text payload, encoded for the content type of the webhook.

    A payload that is a JSON object or array is substituted value by value and needs no encoding. Any other payload
    is substituted as plain text, and a value can then change the structure of the body:

    * In a form-encoded body (``application/x-www-form-urlencoded``), ``&`` separates the fields and ``=`` separates
      the name from the value. A value with one of these characters, a ``+`` or a ``%`` adds or changes fields.
      The value is URL-encoded.
    * In a JSON body (``application/json``), for example ``[{count}, "{username}"]``, a value with ``"`` or ``\\``
      ends the string and adds elements or keys. The value is escaped as the content of a JSON string.

    Some values come from the client, for example the login name that it tried. The setting ``encode_values`` of
    the webhook turns the encoding on. It is off for the webhooks that the upgrade and the import create from an
    inline WebHook handler, because that handler sent the values unencoded.

    Only text values are encoded. Another value, such as a number, contains none of these characters, and it keeps
    its type for a format specification such as ``{count:03d}``.

    :param tags: the values of the placeholders
    :param content_type: the content type of the webhook
    :param encode_values: the setting of the webhook
    :return: the tags, with encoded text values if the setting applies to the content type
    """
    if not encode_values:
        return tags
    media = media_type(content_type)
    if media == ContentType.URLENCODED:
        encode = quote_plus
    elif media == ContentType.JSON:
        def encode(value: str) -> str:
            # The content of a JSON string, without the quotes around it
            return json.dumps(value)[1:-1]
    else:
        return tags
    return {key: encode(value) if isinstance(value, str) else value for key, value in tags.items()}


def _mtls_ssl_context(config, verify, key_password):
    """
    Build the SSL context for a webhook whose client key carries a password.

    ``requests``' ``cert=`` cannot pass a key password, so this path loads the chain into a
    context of its own. That context has to be built the way ``requests`` builds its own, and the
    CA bundle is where the two differ: ``requests`` starts from
    ``urllib3.util.ssl_.create_urllib3_context()``, which loads no certificates at all, so a
    bundle handed to ``verify=`` becomes the only trust anchor. ``ssl.create_default_context()``
    loads the system store first, and urllib3 then calls ``load_verify_locations()`` on it - which
    *adds* the bundle to the public CAs rather than replacing them.

    An administrator who pins an internal CA and happens to protect the client key with a
    password would silently also trust every public CA again. Passing the bundle as ``cafile``
    keeps it the only anchor, because ``create_default_context()`` skips the system store exactly
    when it is given one.

    :param config: the webhook configuration
    :param verify: the ``verify`` argument as :func:`_build_verify` produced it - False, True, or
        the path of a CA bundle
    :param key_password: the decrypted password of the client key
    :return: the context to mount for this request
    """
    # cafile=None is what create_default_context() does by itself, so the system store still
    # applies when no bundle is configured. A directory of CA certificates goes to capath, as requests
    # does it: cafile only reads a file.
    ca_file = ca_path = None
    if isinstance(verify, str):
        if os.path.isdir(verify):
            ca_path = verify
        else:
            ca_file = verify
    context = ssl.create_default_context(cafile=ca_file, capath=ca_path)
    if verify is False:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    context.load_cert_chain(config["client_certificate"], config["client_key"] or None,
                            password=key_password)
    return context


def _resolve_body(config, payload):
    """
    Determine the request body.

    Precedence: an explicit ``payload`` from the call site beats the webhook's
    ``default_payload``; if neither is set, no body is sent.

    The ``default_payload`` is sent unchanged. Placeholders are the business of the call site, which
    replaces them in its own payload: the event handler and a conditional access policy know
    different ones, so one default payload could not be rendered the same for both.

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
        if media_type(config["content_type"]) == ContentType.JSON:
            return json.dumps(payload)
        # Let requests form-encode a dict for urlencoded and friends.
        return payload
    return payload


REDACTED = "<redacted>"


def _prepared_url(url: str) -> str:
    """
    Return *url* as requests sends it: the host in IDNA form, and the path and the query quoted.

    :raises requests.exceptions.RequestException: if requests can not use the URL
    :raises urllib3.exceptions.LocationParseError: if urllib3 can not parse the URL
    """
    prepared = requests.models.PreparedRequest()
    prepared.prepare_url(url, None)
    return prepared.url


def _prepared_url_or_none(url: str) -> str | None:
    """
    Return *url* as requests sends it, or None if requests refuses the URL. Then no message about the request
    contains a prepared form of it.
    """
    try:
        return _prepared_url(url)
    except Exception:
        # Every exception: redact_url() runs in the error handling of fire_webhook(), which never raises.
        return None


def redact_url(text, url):
    """
    Remove the sensitive part of a webhook's URL from a message about it.

    A transport error quotes the URL it failed on, and ``requests`` splits it across the message:
    the host appears as ``host='...'`` and the path separately as ``url: /t/SECRET``. Replacing the
    URL as one string therefore catches neither half, which is why the parts are replaced
    individually, longest first so a shorter one cannot match inside a replacement already made.

    The **host is deliberately kept**. What an admin embeds in a webhook URL is a token, and a
    token sits in the path or the query; the host is what makes a delivery failure diagnosable at
    all, and redacting it would leave "ConnectionError: HTTPSConnectionPool(host='<redacted>')" as
    the entire record of a broken integration. A host that is itself the secret (a token used as a
    subdomain) is not covered - the endpoint should carry it in the path.

    The parts are taken from the URL as configured and from the URL as requests sends it. requests quotes the path
    and the query again, so a message about the request contains, for example, ``/t/S%C3%A9CRET`` for the configured
    ``/t/SéCRET``.

    :param text: the message to sanitise
    :param url: the webhook's configured URL
    :return: the message with the path and query of *url* replaced
    """
    if not text or not url:
        return text
    candidates = [url]
    prepared = _prepared_url_or_none(url)
    if prepared is not None:
        candidates.append(prepared)
    parts = set()
    for candidate in candidates:
        try:
            split = urlsplit(candidate)
        except ValueError:
            # An unparsable URL has no parts to remove individually, so the whole string is.
            parts.add(candidate)
            continue
        query = f"?{split.query}" if split.query else ""
        parts |= {candidate, f"{split.path}{query}", split.path, query}
    # "/" is every path's prefix and carries nothing; replacing it would shred the message.
    for part in sorted((p for p in parts if p and p != "/"), key=len, reverse=True):
        text = text.replace(part, REDACTED)
    return text


def _read_response_text(response: requests.Response, deadline: float) -> tuple[str, bool]:
    """
    Read the start of the response body before the deadline of the delivery.

    requests applies its timeout to each wait for data. An endpoint that sends one byte at a time can thus hold a
    delivery much longer than the timeout. The body is read in small parts, and the deadline is checked before each
    part. Only the start of the body is read: the result and the log keep MAX_RESPONSE_LENGTH characters.

    When the deadline passes, the read stops. The endpoint has answered at that point, so the caller reports the
    status code of the response and not a timeout.

    :param response: a response of a request with ``stream=True``
    :param deadline: the value of :func:`time.monotonic` when the delivery must end
    :return: the part of the body that was read, as text, and whether the deadline stopped the read
    """
    # read1() returns as soon as data is available. urllib3 before 2.1 does not have it, and read() waits until it
    # has the requested number of bytes, so it reads small parts.
    read1 = getattr(response.raw, "read1", None)
    data = bytearray()
    stopped = False
    while len(data) < MAX_RESPONSE_BYTES:
        if time.monotonic() > deadline:
            stopped = True
            break
        if read1 is not None:
            chunk = read1(MAX_RESPONSE_BYTES - len(data), decode_content=True)
        else:
            chunk = response.raw.read(min(256, MAX_RESPONSE_BYTES - len(data)), decode_content=True)
        if not chunk:
            break
        data.extend(chunk)
    try:
        text = bytes(data).decode(response.encoding or "utf-8", errors="replace")
    except LookupError:
        # The endpoint names a character set that Python does not know.
        text = bytes(data).decode("utf-8", errors="replace")
    return text, stopped


def _redact_secrets(text: str, config: dict) -> str:
    """
    Remove the password and the values of the secret headers of a webhook from a message about it.

    requests quotes a header value in some errors, as it is or as a Python string literal.

    :param text: the message to sanitise
    :param config: the webhook configuration with the decrypted secrets
    :return: the message without the secrets
    """
    headers = config.get("headers") or {}
    secrets = {config.get("password"), config.get("client_key_password")}
    secrets.update(headers.get(name) for name in config.get("secret_headers") or ())
    for secret in sorted((secret for secret in secrets if secret), key=len, reverse=True):
        for form in sorted({secret, repr(secret)[1:-1]}, key=len, reverse=True):
            text = text.replace(form, REDACTED)
    return text


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
#: endpoint 169.254.169.254), unique-local IPv6, the "this network" and
#: unspecified ranges, and CGNAT. IPv4-mapped IPv6 forms of an address (e.g.
#: ``::ffff:127.0.0.1``) are unwrapped and checked against the IPv4 entries in
#: :func:`_is_blocked_address`.
#:
#: The unspecified addresses are listed for the same reason as loopback and not as a formality:
#: connecting to ``0.0.0.0`` or ``::`` reaches a locally bound listener, so leaving either out
#: hands an admin with ``webhook_write`` every local port the guard exists to keep them from.
#: ``::`` needs its own entry because it is not the IPv4-mapped form of ``0.0.0.0`` and so is not
#: covered by ``0.0.0.0/8``.
BLOCKED_NETWORKS = tuple(ipaddress.ip_network(cidr) for cidr in (
    "127.0.0.0/8", "0.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12",
    "192.168.0.0/16", "169.254.0.0/16", "100.64.0.0/10",
    "::/128", "::1/128", "fe80::/10", "fc00::/7",
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
    # The host and the port come from the URL as requests sends it, read with the parser of urllib3, which opens the
    # connection. urlsplit() reads some URLs differently: in "http://127.0.0.1:8080\@example.com/" it finds the
    # host example.com, but the connection goes to 127.0.0.1. requests adds "http://" to a proxy URL without a scheme.
    try:
        parsed = parse_url(_prepared_url(requests.utils.prepend_scheme_if_needed(url, "http")))
    except (requests.exceptions.RequestException, LocationParseError, ValueError):
        # _validate() only checks the scheme prefix, so a stored URL may carry something that is not a host or a
        # port. The guard cannot judge a target it cannot parse, so it refuses it rather than waving it through.
        return f"could not determine a host and a port to check in {url!r}"
    # urllib3 keeps the brackets of an IPv6 address
    host = (parsed.host or "").removeprefix("[").removesuffix("]")
    if not host:
        return f"could not determine a host to check in {url!r}"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

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
    allowlist = current_app.config.get("PI_OUTBOUND_GUARD_ALLOW") or []
    # A string would be read character by character, and no character matches an entry. One
    # arrives from the environment (PRIVACYIDEA_PI_OUTBOUND_GUARD_ALLOW=10.1.2.0/24), whose value
    # is taken as a string unless it is valid JSON, so read it as a comma separated list.
    if isinstance(allowlist, str):
        allowlist = [entry.strip() for entry in allowlist.split(",") if entry.strip()]
    return mode, allowlist


def outbound_guard_check(url):
    """
    Read the guard's configuration and judge *url* against it.

    The two steps belong together everywhere they are used - the mode decides what a rejection
    means, so a caller needs both - and this keeps callers outside this module from reaching for
    :func:`_guard_config`.

    :param url: the URL the connection will actually go to (a proxy, where one is configured)
    :return: a ``(mode, rejection)`` tuple; *rejection* is None when the target may be contacted
    """
    mode, allowlist = _guard_config()
    return mode, check_outbound_target(url, mode=mode, allowlist=allowlist)


def guard_target(url, proxies=None):
    """
    Return the URL the outbound request guard should check for a request to *url*.

    When a proxy is used, the connection goes to the proxy, so the proxy is what the guard must
    check -- the destination host is resolved by the proxy, not by us, and checking it would
    protect against nothing.

    That holds for a proxy out of the environment too. ``requests`` runs with ``trust_env=True``,
    so ``http_proxy`` / ``https_proxy`` / ``all_proxy`` in the server's environment are used even
    by a caller that passes no proxies at all; the guard would otherwise resolve and approve a
    destination the connection never goes to. ``get_environ_proxies()`` applies ``no_proxy`` as
    well, so a destination excluded there is correctly checked as itself.

    The proxy is chosen as requests chooses it: the passed proxies override those of the
    environment, and ``select_proxy()`` picks the entry for the URL, falling back from the scheme
    to ``all``.

    Every caller that is about to send a request has to go through this, not just the ones that
    can configure a proxy: the environment applies to all of them.

    :param url: the destination the caller means to reach
    :param proxies: the ``proxies`` dict the request will be sent with, if any
    :return: the proxy URL where one applies, else *url* unchanged
    """
    effective = dict(requests.utils.get_environ_proxies(url))
    # A proxy passed by the caller wins, exactly as it does for the request itself.
    effective.update(proxies or {})
    return requests.utils.select_proxy(url, effective) or url


def _guard_target(config):
    """Return the URL the guard should check for this webhook's request."""
    return guard_target(config["url"], _build_proxies(config))


def _record_webhook_call(identifier, start, success, error=False):
    """Emit duration and outcome metrics, mirroring _record_email_send()."""
    labels = {"identifier": identifier}
    observe("webhook_send_duration_seconds", time.monotonic() - start, labels)
    if error:
        result = "error"
    else:
        result = "ok" if success else "failed"
    inc("webhook_send_total", {**labels, "result": result})


@log_with(log, log_exit=False, hide_args=["config", "payload"])
def fire_webhook(identifier, payload=None, config=None):
    """
    Send the request described by the webhook ``identifier``.

    Delivery is **synchronous**: the caller waits for the response. The
    webhook's timeout limits the connection, the wait for the answer and the
    read of the start of the response body together. If the answer arrives
    but its body does not arrive in time, the read stops and the status code
    counts. Each redirect that is followed gets a timeout of its own. An
    endpoint that sends the status line and the headers of its answer very
    slowly can still hold a delivery longer, because requests limits each
    wait for data only.
    Pointing a webhook at a slow endpoint therefore adds latency to the
    triggering request. There are no retries.

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
    :param config: the webhook's configuration, when the caller has already read it. Reading it
        decrypts every secret column and every secret header, so a caller that needed one of its
        fields beforehand - the WebHook event handler needs the content type to render the payload
        - would otherwise pay for that twice on every event it fires on.
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
        if config is None:
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
        mode, rejection = outbound_guard_check(_guard_target(config))
        follow_redirects = mode != GuardMode.ENFORCE
        if rejection:
            rejection = redact_url(rejection, config["url"])
            log.warning(f"Webhook {identifier!r}: outbound request guard "
                        f"({mode}) rejected the target: {rejection}")
            if mode == GuardMode.ENFORCE:
                _record_webhook_call(identifier, start, False, error=True)
                return {"success": False, "status_code": None, "response": "",
                        "error": f"blocked by the outbound request guard "
                                 f"({mode}): {rejection}"}

        # requests quotes an invalid header value in its error, and the value can be a secret.
        for name, value in (config["headers"] or {}).items():
            check_header(name, value)
        # Case-insensitive, as HTTP header names are: a configured "content-type" has to keep the
        # setdefault() below from adding a second entry, which requests would let win.
        headers = requests.structures.CaseInsensitiveDict(config["headers"] or {})
        body = _resolve_body(config, payload)
        if body is not None:
            # Only advertise a content type when there is something to describe.
            headers.setdefault("Content-Type", config["content_type"])

        auth, cert, key_password = _build_auth_and_cert(config)
        verify = _build_verify(config)
        proxies = _build_proxies(config)
        if key_password:
            cert = None
            context = _mtls_ssl_context(config, verify, key_password)
            session = requests.Session()
            session.mount("https://", _SSLContextAdapter(context))
            requester = session.request
        else:
            requester = requests.request

        timeout = config["timeout"] or DEFAULT_TIMEOUT
        deadline = time.monotonic() + timeout
        # total limits the connection and the wait for the first data together. The body is read in
        # _read_response_text(), which checks the deadline.
        response = requester(
            config["http_method"], config["url"],
            headers=headers,
            data=body,
            auth=auth,
            cert=cert,
            verify=verify,
            proxies=proxies,
            timeout=Timeout(total=timeout),
            allow_redirects=follow_redirects,
            stream=True,
        )
        try:
            text, stopped = _read_response_text(response, deadline)
        finally:
            response.close()
        body_text = _truncate(text)
        if stopped:
            # The request was delivered, and the status code tells how the endpoint took it. A redirect gets a
            # timeout of its own, so a chain of redirects can also end here.
            log.info(f"Webhook {identifier!r}: the timeout stopped the read of the response body. The status "
                     f"code {response.status_code} counts.")
        # requests.Response.ok is true for anything below 400, so a 3xx counts as a success by
        # default. With redirects not followed that is wrong twice over: nothing was delivered,
        # and the caller - an event handler, or a Conditional Access WEBHOOK action - would
        # record the notification as sent. An endpoint that answers 301/302 is ordinary (an
        # http->https rewrite, a load balancer), so this is the common case, not a corner one.
        unfollowed_redirect = not follow_redirects and 300 <= response.status_code < 400
        success = response.ok and not unfollowed_redirect

        log.info(f"Webhook {identifier!r} answered with HTTP "
                 f"{response.status_code}")
        log.debug(f"Webhook {identifier!r} response body: {body_text}")
        if unfollowed_redirect:
            log.warning(f"Webhook {identifier!r} answered with HTTP {response.status_code} and the "
                        f"outbound request guard ({mode}) does not follow redirects, so nothing was "
                        f"delivered. Configure the webhook with the final URL.")
        elif response.history:
            log.info(f"Webhook {identifier!r} followed {len(response.history)} redirect(s); the "
                     f"outbound request guard would refuse to in {GuardMode.ENFORCE!r} mode, and "
                     f"the redirect target is never checked against the guard.")
        elif not success:
            log.warning(f"Webhook {identifier!r} failed with HTTP "
                        f"{response.status_code}")

        _record_webhook_call(identifier, start, success)
        if success:
            error = None
        elif unfollowed_redirect:
            error = (f"HTTP {response.status_code}: the endpoint redirects and the outbound "
                     f"request guard ({mode}) does not follow redirects")
        else:
            error = f"HTTP {response.status_code}"
        return {"success": success, "status_code": response.status_code,
                "response": body_text, "error": error}
    except Exception as ex:
        message = _redact_secrets(redact_url(f"{ex.__class__.__name__}: {ex}", config["url"]), config)
        log.warning(f"Webhook {identifier!r} could not be delivered: {message}")
        _record_webhook_call(identifier, start, False, error=True)
        return {"success": False, "status_code": None, "response": "",
                "error": message}
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

#: Text settings that an export can hold as None: a webhook without a default payload has None, and Oracle reads
#: an empty string back as NULL. For set_webhook(), None means "keep the stored value", so the import writes "".
_EMPTY_TEXT_KEYS = ("description", "default_payload", "username", "password", "tls_ca_bundle",
                    "client_certificate", "client_key", "client_key_password", "http_proxy", "https_proxy")


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
        Such an export can only be re-imported on the instance it came from,
        where the placeholder means "keep the stored secret". The URL, the
        proxy URLs and the values of the other headers stay in the export as
        they are, also if they contain a token or a password. The default is
        False, as for ``pi-manage config export`` without ``--censor``: the
        export then contains every secret in clear text.
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

    A text setting that is None in the export is empty after the import, for
    example the default payload of a webhook that has none. For
    :func:`set_webhook`, None means "keep the stored value", so it is
    imported as an empty string.

    :param data: dict of identifier -> webhook configuration
    :param name: import only this identifier (default: import all)
    """
    log.debug(f"Import webhook config: {sorted(data)}")
    known_parameters = set(inspect.signature(set_webhook).parameters) - {"identifier"}

    for res_name, res_data in data.items():
        if name and name != res_name:
            continue
        parameters = {}
        for key, value in res_data.items():
            if key in known_parameters:
                parameters[key] = "" if value is None and key in _EMPTY_TEXT_KEYS else value
            elif key not in _NON_CONFIG_KEYS:
                log.warning(f"Ignoring unknown key {key!r} while importing "
                            f"webhook {res_name!r}.")
        wid = set_webhook(res_name, **parameters)
        log.info(f"Import of webhook {res_name!r} finished, id: {wid}")
