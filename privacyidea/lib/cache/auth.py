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
Optional Redis backend for the authentication cache.

The authentication cache lets a user skip the round trip to their user store
for a policy-defined window after a successful authentication (see the
``auth_cache`` policy). It is a pure optimisation: every entry can be thrown
away at any moment, and the only consequence is one real authentication
against the backend. That is what makes Redis the natural place for it - the
same reasoning that lets challenges live in Redis alone.

The database table it replaces is written to on the authentication path in
three directions - an ``UPDATE`` on every cache *hit* to bump the counter, an
``INSERT`` per successful authentication, and ``DELETE`` statements for entries
that turn out to be stale. With Redis enabled, none of that reaches the
database, and the ``pi-manage config authcache cleanup`` job has nothing left
to do because entries carry a TTL.

Configuration (pi.cfg or environment)::

    PI_REDIS_URL = "redis://localhost:6379/0"
    PI_REDIS_CACHE_AUTH = True
    PI_REDIS_AUTH_CACHE_TTL = 3600

``PI_REDIS_AUTH_CACHE_TTL`` is only a fallback for a caller that cannot say how
long its entry may live. The ``auth_cache`` policy's first interval is that
answer, so in practice the TTL is the policy's own window and an entry
physically disappears the moment the policy stops honouring it.

Data at rest
------------

An entry holds an Argon2 hash of the user's password - a credential-derived
secret that can be attacked offline if it leaks. Every entry is therefore
encrypted with the server's encryption key before it reaches Redis, so a dump
of the Redis database yields nothing usable on its own.

Note that, exactly as with the database-backed cache, a password changed in the
user store stays usable until the entry expires. Keep the ``auth_cache`` policy
window short enough that this is acceptable.
"""
import json
import logging
from datetime import datetime, timezone
from urllib.parse import quote
from uuid import uuid4

import redis as redis_lib
from passlib.hash import argon2

from privacyidea.lib.cache.redis import _disable_redis, redis_client_for_feature
from privacyidea.lib.crypto import FAILED_TO_DECRYPT_PASSWORD, decryptPassword, encryptPassword
from privacyidea.lib.framework import get_app_config_value
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

AUTH_CACHE_FEATURE = "auth"

# Only used when a caller cannot tell us the window its entry belongs to. The
# ``auth_cache`` policy always can, so this is a backstop rather than a default
# anybody should rely on.
_DEFAULT_TTL_SECONDS = 3600

# One HASH per user, holding every cached authentication of that user. The
# fields come in pairs: ``entry:<id>`` carries the encrypted record, and
# ``count:<id>`` carries how often it has been used.
#
# The counter is a field of its own rather than a member of the record so it can
# be raised with HINCRBY. Folding it into the encrypted record would turn every
# cache hit into a read-modify-write, and two concurrent authentications could
# then both write the same value - letting an entry be used once more than
# ``max_auths`` allows. The database-backed cache raises the counter in a single
# UPDATE and does not have that weakness, so neither should this.
_USER_KEY = "pi:authcache:v1:{}:{}:{}"  # pi:authcache:v1:<username>:<realm>:<resolver>
_ENTRY_FIELD = "entry:{}"
_COUNT_FIELD = "count:{}"


def _ttl_seconds(max_age_seconds: int = None) -> int:
    """
    Return the lifetime an entry written now should get.

    ``max_age_seconds`` is the window the caller knows its entry can be used
    in. Without one, fall back to the configured default. A missing or
    malformed configuration value falls back to the built-in default rather
    than disabling the cache; an explicit 0 or a negative value disables it.
    """
    if max_age_seconds is not None:
        return max(int(max_age_seconds), 0)
    raw = get_app_config_value('PI_REDIS_AUTH_CACHE_TTL', _DEFAULT_TTL_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        log.warning(f"PI_REDIS_AUTH_CACHE_TTL is not a number ({raw!r}), using {_DEFAULT_TTL_SECONDS}s.")
        return _DEFAULT_TTL_SECONDS
    return max(value, 0)


def _cache_client():
    """
    Return the Redis client to store cached authentications in, or None.

    None means the database has to do it: the feature is off, or Redis is
    unreachable and its connection is in the retry cooldown.
    """
    return redis_client_for_feature(AUTH_CACHE_FEATURE)


def _segment(value) -> str:
    """Encode one key segment so a login containing a colon cannot span segments."""
    return quote(f"{value or ''}", safe="")


def _key(username: str, realm: str, resolver: str) -> str:
    return _USER_KEY.format(_segment(username), _segment(realm), _segment(resolver))


def _naive(value: datetime) -> datetime:
    """
    Return ``value`` as a naive UTC timestamp.

    Every timestamp in this cache is naive UTC, because that is what
    :func:`utc_now` produces and what the database columns hold. Comparing a
    naive timestamp with an aware one raises, and this comparison sits on the
    authentication path, so a caller that hands over an aware timestamp should
    not be able to turn an authentication into an error.
    """
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _read_entries(client, key: str) -> dict | None:
    """
    Return the cached authentications under ``key`` as ``{id: record}``.

    None means Redis could not be read, which is the caller's signal to leave
    the cache alone entirely. An empty dictionary means the user simply has no
    cached authentication.

    A record that cannot be decrypted or parsed is skipped rather than raising:
    it was written under a different encryption key, or it is not ours. The
    guard around decryption is deliberately broad - ``decryptPassword`` returns
    a placeholder for a failed decryption, but it reaches the HSM before that
    guard applies, and an unreachable HSM must not turn a cache read into a
    failed authentication.
    """
    try:
        raw_fields = client.hgetall(key)
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)
        return None

    entries = {}
    for field, value in raw_fields.items():
        if not field.startswith("entry:"):
            continue
        entry_id = field.split(":", 1)[1]
        try:
            plaintext = decryptPassword(value)
            if plaintext == FAILED_TO_DECRYPT_PASSWORD:
                raise ValueError("could not be decrypted")
            record = json.loads(plaintext)
            record["first_auth"] = datetime.fromisoformat(record["first_auth"])
            record["last_auth"] = datetime.fromisoformat(record["last_auth"])
            if not isinstance(record["authentication"], str):
                raise TypeError("the stored authentication is not a string")
        except Exception as error:
            log.warning(f"Ignoring an unreadable authentication cache entry: {error}")
            continue
        try:
            record["auth_count"] = int(raw_fields.get(_COUNT_FIELD.format(entry_id), 0))
        except (TypeError, ValueError):
            record["auth_count"] = 0
        entries[entry_id] = record
    return entries


def _forget(client, key: str, entry_ids: list) -> None:
    """Remove the given entries, both the record and its counter."""
    if not entry_ids:
        return
    fields = []
    for entry_id in entry_ids:
        fields.append(_ENTRY_FIELD.format(entry_id))
        fields.append(_COUNT_FIELD.format(entry_id))
    try:
        client.hdel(key, *fields)
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)


def add_to_cache(username: str, realm: str, resolver: str, auth_hash: str,
                 max_age_seconds: int = None) -> bool:
    """
    Store a successful authentication in Redis.

    :param username: The login name of the user
    :param realm: The realm of the user
    :param resolver: The resolver of the user
    :param auth_hash: The Argon2 hash of the password that authenticated
    :param max_age_seconds: How long the entry may be used, from the policy
    :return: True if the entry was cached, False if the database has to do it
    """
    client = _cache_client()
    if client is None:
        return False
    ttl = _ttl_seconds(max_age_seconds)
    if not ttl:
        return False

    now = utc_now()
    entry_id = uuid4().hex
    record = {"authentication": auth_hash,
              "first_auth": now.isoformat(),
              "last_auth": now.isoformat()}
    try:
        ciphertext = encryptPassword(json.dumps(record))
    except Exception as error:
        # HSMException for a failed encryption, and whatever the HSM raises on
        # the way there when it is not ready. Not caching is always an option
        log.warning(f"Could not encrypt an authentication cache entry, it was not cached: {error}")
        return False

    key = _key(username, realm, resolver)
    try:
        pipe = client.pipeline()
        pipe.hset(key, _ENTRY_FIELD.format(entry_id), ciphertext)
        pipe.hset(key, _COUNT_FIELD.format(entry_id), 0)
        # Seed the key's TTL if it has none, then only ever extend it, so the
        # key lives as long as its longest-lived entry. Entries that expire
        # before the key does are filtered out on read. NX and GT need Redis 7,
        # which the connection already refuses to work without
        pipe.expire(key, ttl, nx=True)
        pipe.expire(key, ttl, gt=True)
        pipe.execute()
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)
        # The entry may or may not have made it. Either way the caller is done:
        # a lost entry costs one real authentication, and writing it to the
        # database as well would leave the two stores to disagree
        return True
    return True


def verify_in_cache(username: str, realm: str, resolver: str, password: str,
                    first_auth: datetime = None, last_auth: datetime = None,
                    max_auths: int = 0) -> bool | None:
    """
    Check whether this password authenticated recently enough to be trusted again.

    Mirrors the database-backed check: an entry counts when the password
    verifies against its hash, it was first used after ``first_auth``, it was
    last used after ``last_auth``, and it has not been used ``max_auths`` times
    already. On a match the entry's counter and last use are updated.

    Entries that are past ``first_auth`` are dropped while we are looking at
    them. Without that, expired records would keep costing an Argon2
    verification on every attempt until the whole key expires.

    :param username: The login name of the user
    :param realm: The realm of the user
    :param resolver: The resolver of the user
    :param password: The password to verify
    :param first_auth: Only accept entries first used after this point in time
    :param last_auth: Only accept entries last used after this point in time
    :param max_auths: Maximum number of times an entry may be used, 0 for no limit
    :return: True or False, or None if Redis could not answer and the database
             has to be asked instead
    """
    client = _cache_client()
    if client is None:
        return None
    first_auth = _naive(first_auth)
    last_auth = _naive(last_auth)
    key = _key(username, realm, resolver)
    entries = _read_entries(client, key)
    if entries is None:
        return None

    expired = [entry_id for entry_id, record in entries.items()
               if first_auth and record["first_auth"] <= first_auth]
    if expired:
        _forget(client, key, expired)
        for entry_id in expired:
            del entries[entry_id]

    for entry_id, record in entries.items():
        if last_auth and record["last_auth"] <= last_auth:
            continue
        try:
            if not argon2.verify(password, record["authentication"]):
                continue
        except ValueError:
            # Not an Argon2 hash - the same case the database path treats as an
            # old entry and discards
            log.debug(f"Discarding a non-argon2 authentication cache entry for {username!s}@{realm!s}.")
            _forget(client, key, [entry_id])
            continue
        if max_auths > 0 and record["auth_count"] >= max_auths:
            # Used up. Drop it so the next attempt does not verify it again
            _forget(client, key, [entry_id])
            continue
        _use(client, key, entry_id, record)
        return True

    # Nothing matched. The database path also removes the entries that match
    # this password here, so a wrong password cannot leave a usable entry behind
    delete_from_cache(username, realm, resolver, password,
                      last_valid_cache_time=first_auth, max_auths=max_auths)
    return False


def _use(client, key: str, entry_id: str, record: dict) -> None:
    """
    Record that an entry was just used.

    The counter is raised with HINCRBY so concurrent authentications cannot
    both write the same value. The TTL is deliberately left alone: an entry's
    lifetime runs from its *first* use, so extending it here would keep a
    password valid past the window the policy granted.
    """
    record = dict(record)
    record["last_auth"] = utc_now().isoformat()
    record["first_auth"] = record["first_auth"].isoformat()
    record.pop("auth_count", None)
    try:
        ciphertext = encryptPassword(json.dumps(record))
    except Exception as error:
        log.warning(f"Could not encrypt an authentication cache entry, its last use was not recorded: {error}")
        ciphertext = None
    try:
        pipe = client.pipeline()
        if ciphertext is not None:
            pipe.hset(key, _ENTRY_FIELD.format(entry_id), ciphertext)
        pipe.hincrby(key, _COUNT_FIELD.format(entry_id), 1)
        pipe.execute()
    except redis_lib.exceptions.RedisError as error:
        # The authentication itself already succeeded, so this only means the
        # counter and the last use are behind by one
        _disable_redis(error)


def delete_from_cache(username: str, realm: str, resolver: str, password: str,
                      last_valid_cache_time: datetime = None, max_auths: int = 0) -> int | None:
    """
    Remove the cached authentications of a user that match the given password,
    are expired, or have been used up.

    :param username: The login name of the user
    :param realm: The realm of the user
    :param resolver: The resolver of the user
    :param password: Entries whose hash this password verifies against are removed
    :param last_valid_cache_time: Entries first used before this point are removed
    :param max_auths: Entries used this many times are removed, 0 for no limit
    :return: the number of removed entries, or None if Redis could not answer
    """
    client = _cache_client()
    if client is None:
        return None
    last_valid_cache_time = _naive(last_valid_cache_time)
    key = _key(username, realm, resolver)
    entries = _read_entries(client, key)
    if entries is None:
        return None

    doomed = []
    for entry_id, record in entries.items():
        if max_auths > 0 and record["auth_count"] >= max_auths:
            doomed.append(entry_id)
        elif last_valid_cache_time and record["first_auth"] < last_valid_cache_time:
            doomed.append(entry_id)
        else:
            try:
                if argon2.verify(password, record["authentication"]):
                    doomed.append(entry_id)
            except ValueError:
                # Not an Argon2 hash, so it can never verify again
                doomed.append(entry_id)
    _forget(client, key, doomed)
    return len(doomed)


def cache_enabled() -> bool:
    """
    Return True if cached authentications are kept in Redis rather than in the
    database.

    Used by the cleanup command to explain that it has nothing to delete,
    instead of reporting a count of zero as though the cache were empty.
    """
    return _cache_client() is not None
