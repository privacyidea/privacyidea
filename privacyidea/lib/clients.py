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
"""
This module handles API clients that authenticate with an API key. It provides
the secure generation of API keys and the keyed hashing used to look them up.

The plaintext API key is shown to the administrator exactly once at creation
time and is never stored. Only a keyed hash of the key is persisted.
"""
import hashlib
import hmac
import logging
import secrets

from privacyidea.lib.error import ParameterError, ResourceNotFoundError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.models import Client
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

DEFAULT_KEY_PREFIX = "pi"
# Bytes of entropy in the public key id (identifier only, not a secret).
KEY_ID_BYTES = 8
# Bytes of entropy in the secret half. 32 random bytes (~256 bits) make an
# offline brute force against the keyed hash infeasible regardless of the hash
# speed, which is why a fast keyed hash (rather than a slow KDF) is used and why
# exposing the key id publicly leaks nothing useful about the secret.
KEY_SECRET_BYTES = 32
# The states a client may be in. Only "active" clients can authenticate;
# "suspended" is a reversible off-switch. Permanent removal is a delete, and a
# compromised key is handled by rotation - so there is no separate "revoked".
CLIENT_STATUS = ("active", "suspended")


def _hash_secret(secret: str) -> str:
    """
    Compute the keyed hash of the secret half of an API key.

    The hash is an HMAC-SHA256 keyed with the server's ``PI_PEPPER`` so that the
    stored value cannot be reproduced without access to the server config.

    :param secret: the secret half of the API key
    :return: the hex-encoded HMAC-SHA256 hash (64 characters)
    """
    pepper = get_app_config_value("PI_PEPPER", "missing")
    return hmac.new(pepper.encode("utf-8"), secret.encode("utf-8"), hashlib.sha256).hexdigest()


def parse_api_key(plaintext: str) -> tuple[str, str] | tuple[None, None]:
    """
    Split a full API key of the form ``<prefix>_<key_id>_<secret>`` into its
    key id and secret. The prefix and key id never contain an underscore, so the
    secret (which may contain underscores from the url-safe alphabet) is
    everything after the second underscore.

    :param plaintext: the full plaintext API key
    :return: a ``(key_id, secret)`` tuple, or ``(None, None)`` if malformed
    """
    parts = plaintext.split("_", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        return None, None
    return parts[1], parts[2]


def hash_api_key(plaintext: str) -> str:
    """
    Compute the stored hash for a full API key by hashing its secret half.

    :param plaintext: the full plaintext API key
    :return: the hex-encoded HMAC-SHA256 hash of the secret half
    """
    _, secret = parse_api_key(plaintext)
    return _hash_secret(secret or "")


def generate_api_key(prefix: str = DEFAULT_KEY_PREFIX) -> dict:
    """
    Generate a new, secure, random API key.

    The key has the form ``<prefix>_<key_id>_<secret>``. The ``key_id`` is a
    non-secret identifier used to look up the client and is safe to store and
    display; only the ``secret`` half is hashed.

    :param prefix: a short prefix identifying the key (e.g. the client type)
    :return: a dict with the ``plaintext`` key (to be shown to the admin exactly
        once), its ``key_id`` and its ``key_hash`` (both to be stored)
    """
    key_id = secrets.token_hex(KEY_ID_BYTES)
    secret = secrets.token_urlsafe(KEY_SECRET_BYTES)
    return {
        "plaintext": f"{prefix}_{key_id}_{secret}",
        "key_id": key_id,
        "key_hash": _hash_secret(secret),
    }


def get_active_client_by_key(plaintext: str) -> Client | None:
    """
    Look up an active client by its plaintext API key.

    The client is fetched by its public ``key_id`` (an indexed lookup) and the
    secret is then verified against the stored hash in constant time.

    :param plaintext: the plaintext API key from the request
    :return: the matching active ``Client`` or ``None``
    """
    client, status = identify_client_by_key(plaintext)
    return client if status == "active" else None


def identify_client_by_key(plaintext: str) -> tuple[Client | None, str]:
    """
    Classify a presented API key **without** applying the active-status filter.

    Unlike :func:`get_active_client_by_key`, this does not hide a disabled
    client: it distinguishes an *active* key from a *known but disabled* one
    (``suspended``) so the latter can be surfaced - a real, previously issued key
    still being presented after it was disabled is worth recording.

    :param plaintext: the plaintext API key from the request
    :return: a ``(client, status)`` tuple. ``status`` is the client's status
        (e.g. ``"active"`` or ``"suspended"``) when the ``key_id`` is known and
        the secret matches, or ``"unknown"`` when the ``key_id`` is unknown or
        the secret does not match. ``client`` is the matched client (even when
        disabled), or ``None`` for an unknown/invalid key.
    """
    key_id, secret = parse_api_key(plaintext)
    if not key_id or not secret:
        return None, "unknown"
    client = Client.query.filter_by(key_id=key_id).first()
    if not client or not hmac.compare_digest(client.key_hash, _hash_secret(secret)):
        return None, "unknown"
    return client, client.status


def create_client(display_name: str, client_type: str, config: dict = None,
                  prefix: str = DEFAULT_KEY_PREFIX) -> tuple[Client, str]:
    """
    Create a new client with a freshly generated API key and persist it.

    :param display_name: a human readable name for the client
    :param client_type: the type of client, e.g. 'windows_cp', 'keycloak', 'entraid'
    :param config: optional configuration dict for future remote config
    :param prefix: the prefix for the generated API key
    :return: a tuple of the stored ``Client`` and the plaintext API key. The
        plaintext key is returned here only and must be shown to the admin once.
    """
    key = generate_api_key(prefix)
    client = Client(display_name=display_name, client_type=client_type,
                    key_id=key["key_id"], key_hash=key["key_hash"],
                    config=config)
    client.save()
    return client, key["plaintext"]


def touch_client(client: Client, min_interval_seconds: int = 60) -> None:
    """
    Update the ``last_used_at`` timestamp of a client to the current time.

    Throttled: the DB write is skipped if ``last_used_at`` was updated less than
    ``min_interval_seconds`` ago, so a busy client polling on every request does
    not generate one auth write per request (the column only needs coarse
    freshness).

    :param client: the client that was used to authenticate the request
    :param min_interval_seconds: minimum age of ``last_used_at`` before it is
        rewritten
    """
    now = utc_now()
    if client.last_used_at and (now - client.last_used_at).total_seconds() < min_interval_seconds:
        return
    client.last_used_at = now
    client.save()


def get_client(client_id: str) -> Client:
    """
    Fetch a single client by its id or raise ``ResourceNotFoundError``.

    :param client_id: the UUID of the client
    :return: the ``Client``
    """
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        raise ResourceNotFoundError(f"The client with id {client_id!r} does not exist.")
    return client


def get_clients() -> list[Client]:
    """
    Return all clients, ordered by creation time.

    :return: a list of ``Client`` objects
    """
    return Client.query.order_by(Client.created_at).all()


def update_client(client_id: str, display_name: str = None, status: str = None,
                  config: dict = None) -> Client:
    """
    Update the metadata of an existing client. The API key is not touched here;
    use :func:`rotate_client_key` for that.

    :param client_id: the UUID of the client
    :param display_name: the new display name, if given
    :param status: the new status ('active' or 'suspended'), if given
    :param config: the new config dict, if given
    :return: the updated ``Client``
    """
    client = get_client(client_id)
    if display_name is not None:
        client.display_name = display_name
    if status is not None:
        if status not in CLIENT_STATUS:
            raise ParameterError(f"Unknown client status {status!r}.")
        client.status = status
    if config is not None:
        client.config = config
    client.save()
    return client


def rotate_client_key(client_id: str, prefix: str = DEFAULT_KEY_PREFIX) -> tuple[Client, str]:
    """
    Generate a new API key for an existing client and invalidate the old one.

    :param client_id: the UUID of the client
    :param prefix: the prefix for the new API key
    :return: a tuple of the updated ``Client`` and the new plaintext API key.
        The plaintext key is returned only here and must be shown to the admin once.
    """
    client = get_client(client_id)
    key = generate_api_key(prefix)
    client.key_id = key["key_id"]
    client.key_hash = key["key_hash"]
    client.save()
    return client, key["plaintext"]


def delete_client(client_id: str) -> str:
    """
    Delete a client.

    :param client_id: the UUID of the client
    :return: the id of the deleted client
    """
    client = get_client(client_id)
    return client.delete()


def client_to_dict(client: Client) -> dict:
    """
    Serialise a client for API output. The ``key_hash`` is intentionally never
    exposed; only the non-sensitive ``key_id`` is.

    :param client: the ``Client`` to serialise
    :return: a JSON-serialisable dict
    """
    return {
        "id": client.id,
        "display_name": client.display_name,
        "client_type": client.client_type,
        "key_id": client.key_id,
        "status": client.status,
        "created_at": client.created_at.isoformat() if client.created_at else None,
        "last_used_at": client.last_used_at.isoformat() if client.last_used_at else None,
        "config": client.config or {},
    }
