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
Optional Redis cache for user store lookups.

Every user store lookup that privacyIDEA performs on a ``User`` object is a
round trip to an external system: an LDAP search, an SQL query, an HTTP call.
The same three questions are asked over and over - what is the ID of this
login, what is the login of this ID, and what are the attributes of this ID -
and the answers change rarely. This module keeps those answers in Redis so
they are shared by every worker process on every node, which the existing
caches are not: the ``usercache`` database table only holds the login/ID
correlation, and the LDAP resolver's own cache is a dictionary in one process.

The user store stays the single source of truth. This is a read-through cache
with an authoritative origin: a miss is always answered by asking the resolver,
nothing is ever written here that does not come from a resolver, and dropping
the whole keyspace at any moment costs nothing but a few extra lookups. That is
what makes it safe to be aggressive about invalidation - see below.

Configuration (pi.cfg or environment)::

    PI_REDIS_URL = "redis://localhost:6379/0"
    PI_REDIS_CACHE_USERS = True
    PI_REDIS_USER_CACHE_TTL = 300

``PI_REDIS_CACHE_USERS`` is the on/off switch, independent of the other Redis
workloads. ``PI_REDIS_USER_CACHE_TTL`` is the lifetime of an entry in seconds
(default 300); setting it to 0 disables caching just like clearing the flag.

Note on the resolver's own cache
--------------------------------

An LDAP resolver with a non-zero ``CACHE_TIMEOUT`` keeps a per-process
dictionary of the same answers. This cache sits *above* the resolver, so a miss
here can still be served from that dictionary rather than from LDAP. That is
harmless, but it means the dictionary, which has no invalidation hook at all,
sets the real staleness bound. Operators who want the invalidation below to
take effect promptly should lower or zero the resolvers' ``CACHE_TIMEOUT`` and
let this cache do the work, since this one is shared and can be flushed.

Invalidation
------------

TTL is the backstop, not the mechanism. Entries are dropped explicitly whenever
privacyIDEA knows something changed:

* a user is updated or deleted through privacyIDEA - that user's entries go,
* a resolver is saved or deleted - every entry of that resolver goes,
* an admin flushes the user cache - everything goes.

Changes made directly in the user store, behind privacyIDEA's back, are
invisible until the TTL expires. That is the same bound the ``usercache`` table
has always had, which is why the default TTL here is minutes rather than hours.

Every entry of a resolver is reachable through a per-resolver index set, so
dropping a resolver's entries is a set read plus a delete, never a scan of the
whole keyspace.

Data at rest
------------

User attributes are personal data - mail addresses, phone numbers, group
memberships - and logins and user IDs identify a person by themselves. Every
value is therefore encrypted with the server's encryption key before it reaches
Redis, so a dump of the Redis database is not a dump of the directory. Keys are
not encrypted: a key holds a login or a user ID, and Redis has to be able to
look it up. Protect the Redis instance accordingly.
"""
import json
import logging
from urllib.parse import quote

import redis as redis_lib

from privacyidea.lib.cache.redis import _disable_redis, redis_client_for_feature
from privacyidea.lib.crypto import FAILED_TO_DECRYPT_PASSWORD, decryptPassword, encryptPassword
from privacyidea.lib.framework import get_app_config_value

log = logging.getLogger(__name__)

USER_CACHE_FEATURE = "users"

# Entries are short-lived on purpose: a change made directly in the user store
# is only noticed when the entry expires, so the default trades a shorter cache
# for a smaller window in which privacyIDEA can act on stale user data.
_DEFAULT_TTL_SECONDS = 300

# Redis key templates. The trailing segments are user-controlled strings, so
# every segment is percent-encoded to keep a login that contains a colon from
# colliding with a different resolver's keyspace.
#
# The index set holds the names of all keys cached for one resolver, which is
# what makes "forget everything about this resolver" a set read instead of a
# scan over every key in the database. It mirrors the challenge cache, where a
# per-serial set indexes the transactions a token takes part in.
_USER_ID_KEY = "pi:user:v1:uid:{}:{}"  # pi:user:v1:uid:<resolver>:<login>   -> user id
_LOGIN_KEY = "pi:user:v1:login:{}:{}"  # pi:user:v1:login:<resolver>:<uid>   -> login name
_USER_INFO_KEY = "pi:user:v1:info:{}:{}"  # pi:user:v1:info:<resolver>:<uid> -> attribute dict
_INDEX_KEY = "pi:user:v1:index:{}"  # pi:user:v1:index:<resolver>            -> SET of the keys above


def _ttl_seconds() -> int:
    """
    Return the configured entry lifetime in seconds, or 0 if caching is off.

    A missing or malformed value falls back to the default rather than
    disabling the cache, matching how the Redis cooldown is read. An explicit
    0 or a negative value disables caching, so operators can turn the cache
    off with the same knob they use to tune it.
    """
    raw = get_app_config_value('PI_REDIS_USER_CACHE_TTL', _DEFAULT_TTL_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        log.warning(f"PI_REDIS_USER_CACHE_TTL is not a number ({raw!r}), using {_DEFAULT_TTL_SECONDS}s.")
        return _DEFAULT_TTL_SECONDS
    return max(value, 0)


def _cache_client():
    """
    Return the Redis client to cache user lookups in, or None.

    None means "do not cache": the feature is off, the TTL is zero, or Redis
    is unreachable and the connection is in its retry cooldown.
    """
    if not _ttl_seconds():
        return None
    return redis_client_for_feature(USER_CACHE_FEATURE)


def _segment(value) -> str:
    """Percent-encode one key segment so no user-controlled value can span segments."""
    return quote(f"{value}", safe="")


def _keys_of_user(resolver_name: str, login: str = None, user_id=None) -> list[str]:
    """Return the key names that hold what is cached about one user."""
    keys = []
    if login:
        keys.append(_USER_ID_KEY.format(_segment(resolver_name), _segment(login)))
    if user_id not in (None, ""):
        keys.append(_LOGIN_KEY.format(_segment(resolver_name), _segment(user_id)))
        keys.append(_USER_INFO_KEY.format(_segment(resolver_name), _segment(user_id)))
    return keys


def _read(client, resolver_name: str, key: str) -> str | None:
    """
    Return the decrypted value stored under ``key``, or None if there is none
    to be had.

    None covers every reason a caller has to ask the resolver instead: the key
    is absent, Redis failed mid-read, or the stored value can not be decrypted.
    A value that fails to decrypt is dropped, since it can never be read again
    - it was written under a different encryption key, or it is corrupt.

    Decryption is guarded broadly on purpose. ``decryptPassword`` returns a
    placeholder for a failed decryption, but it reaches the HSM before that
    guard applies, so an HSM that is not ready raises. Nothing about reading a
    cache may turn a lookup that would have succeeded into an error, so any
    failure here means "ask the resolver".
    """
    try:
        raw = client.get(key)
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)
        return None
    if raw is None:
        return None
    try:
        value = decryptPassword(raw)
    except Exception as error:
        log.warning(f"Could not decrypt a user cache entry, ignoring it: {error}")
        return None
    if value == FAILED_TO_DECRYPT_PASSWORD:
        log.warning(f"Could not decrypt a user cache entry, dropping it: {key}")
        _unlink(client, resolver_name, [key])
        return None
    return value


def _write(client, resolver_name: str, key: str, value: str) -> None:
    """
    Store ``value`` under ``key``, encrypted, and index the key for the resolver.

    Nothing here may raise: the caller already has the answer from the
    resolver, and failing to cache it is not a reason to fail the request. A
    failing HSM is not a failing Redis, so it does not start a cooldown - the
    next request tries again, and until then lookups simply go to the resolver.
    """
    ttl = _ttl_seconds()
    index_key = _INDEX_KEY.format(_segment(resolver_name))
    try:
        ciphertext = encryptPassword(value)
    except Exception as error:
        # HSMException for an encryption that failed, and anything the HSM
        # itself raises on the way there when it is not ready
        log.warning(f"Could not encrypt a user cache entry, it was not cached: {error}")
        return
    try:
        pipe = client.pipeline()
        pipe.set(key, ciphertext, ex=ttl)
        pipe.sadd(index_key, key)
        # Seed the index TTL if it has none, then only ever extend it, so the
        # index outlives the entries it points at. NX and GT need Redis 7,
        # which the client connection already refuses to work without.
        pipe.expire(index_key, ttl, nx=True)
        pipe.expire(index_key, ttl, gt=True)
        pipe.execute()
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)


def _unlink(client, resolver_name: str, keys: list[str]) -> None:
    """
    Delete the given keys and forget them in the resolver's index.

    UNLINK rather than DEL so a large attribute dictionary is reclaimed by the
    background thread instead of blocking the server.
    """
    if not keys:
        return
    try:
        pipe = client.pipeline()
        pipe.unlink(*keys)
        pipe.srem(_INDEX_KEY.format(_segment(resolver_name)), *keys)
        pipe.execute()
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)


def cached_user_id(resolver, resolver_name: str, login: str):
    """
    Return the user ID of ``login`` in the given resolver, from the cache if it
    is there.

    A login that resolves to nothing is not cached. The empty answer is the one
    that changes when a user is created, and a new user that can not
    authenticate until a cache expires is a worse failure than a repeated
    lookup for a login that does not exist.

    :param resolver: The resolver object to ask on a cache miss
    :param resolver_name: The name of that resolver
    :param login: The login name to look up
    :return: whatever the resolver returns for this login
    """
    client = _cache_client()
    if client is None or not login:
        return resolver.getUserId(login)

    key = _USER_ID_KEY.format(_segment(resolver_name), _segment(login))
    cached = _read(client, resolver_name, key)
    if cached is not None:
        log.debug(f"Read the user id of {login!r} in {resolver_name!r} from the cache.")
        return cached

    user_id = resolver.getUserId(login)
    if user_id not in (None, ""):
        _write(client, resolver_name, key, f"{user_id}")
    return user_id


def cached_username(resolver, resolver_name: str, user_id) -> str:
    """
    Return the login name of ``user_id`` in the given resolver, from the cache
    if it is there.

    :param resolver: The resolver object to ask on a cache miss
    :param resolver_name: The name of that resolver
    :param user_id: The ID of the user in the resolver
    :return: whatever the resolver returns for this user ID
    """
    client = _cache_client()
    if client is None or user_id in (None, ""):
        return resolver.getUsername(user_id)

    key = _LOGIN_KEY.format(_segment(resolver_name), _segment(user_id))
    cached = _read(client, resolver_name, key)
    if cached is not None:
        log.debug(f"Read the login name of {user_id!r} in {resolver_name!r} from the cache.")
        return cached

    login = resolver.getUsername(user_id)
    if login:
        _write(client, resolver_name, key, login)
    return login


def cached_user_info(resolver, resolver_name: str, user_id, attributes: list[str] = None) -> dict:
    """
    Return the attributes of ``user_id`` in the given resolver, from the cache
    if the cached entry covers the requested attributes.

    A cached entry records which attributes were asked for when it was written,
    not only the ones that came back. Recording the answer's keys instead would
    make a user whose mail address is not set look like an incomplete entry and
    never be served from the cache. An entry covers a request when it was
    written for at least the requested attributes, and an entry written for all
    of them covers every request.

    Custom user attributes are deliberately not part of this: they live in
    privacyIDEA's own database and are merged on top of the resolver's answer
    by the caller, so they are never served stale from here.

    :param resolver: The resolver object to ask on a cache miss
    :param resolver_name: The name of that resolver
    :param user_id: The ID of the user in the resolver
    :param attributes: The attributes to return, or None for all of them
    :return: whatever the resolver returns for this user ID, reduced to the
             requested attributes
    """
    client = _cache_client()
    if client is None or user_id in (None, ""):
        return resolver.get_user_info(user_id, attributes)

    key = _USER_INFO_KEY.format(_segment(resolver_name), _segment(user_id))
    cached = _read(client, resolver_name, key)
    if cached is not None:
        user_info = _covered_user_info(cached, attributes)
        if user_info is not None:
            log.debug(f"Read the user information of {user_id!r} in {resolver_name!r} from the cache.")
            return user_info

    user_info = resolver.get_user_info(user_id, attributes)
    if user_info:
        payload = json.dumps({"attributes": sorted(attributes) if attributes is not None else None,
                              "info": user_info})
        _write(client, resolver_name, key, payload)
    return user_info


def _covered_user_info(cached: str, attributes: list[str] = None) -> dict | None:
    """
    Return the cached attributes reduced to the requested ones, or None if the
    entry does not cover the request.

    None is also the answer for an entry that can not be parsed. Anything may
    end up in a Redis database - a hand-written key, another tool writing into
    the same namespace - and none of it should reach a caller that expects the
    shape this module writes.
    """
    try:
        payload = json.loads(cached)
        cached_attributes = payload["attributes"]
        user_info = payload["info"]
        if not isinstance(user_info, dict) or not (cached_attributes is None or isinstance(cached_attributes, list)):
            raise TypeError("unexpected types in the cached user information")
    except (json.JSONDecodeError, TypeError, KeyError) as error:
        log.warning(f"Ignoring a malformed user cache entry: {error}")
        return None

    if attributes is None:
        # Only an entry that was itself written for all attributes is known to
        # hold all of them
        return user_info if cached_attributes is None else None
    if cached_attributes is not None and not set(attributes).issubset(cached_attributes):
        return None
    return {key: value for key, value in user_info.items() if key in attributes}


def invalidate_user(resolver_name: str, login: str = None, user_id=None) -> None:
    """
    Drop what is cached about one user.

    Call this whenever privacyIDEA itself changes a user, so the next lookup
    reads the new state instead of waiting out the TTL. Both identifiers are
    optional, but passing only one leaves the entries keyed on the other in
    place until they expire.

    :param resolver_name: The name of the resolver the user is in
    :param login: The login name of the user, if it is known
    :param user_id: The ID of the user in the resolver, if it is known
    """
    client = _cache_client()
    if client is None:
        return
    keys = _keys_of_user(resolver_name, login=login, user_id=user_id)
    if keys:
        log.debug(f"Dropping {len(keys)} user cache entries of {login or user_id!r} in {resolver_name!r}.")
        _unlink(client, resolver_name, keys)


def invalidate_resolver(resolver_name: str) -> None:
    """
    Drop everything cached for one resolver.

    A resolver's configuration decides what its answers mean - which server is
    asked, which attribute is the login, how attributes are mapped - so once it
    changes, nothing cached under it can be trusted.

    :param resolver_name: The name of the resolver
    """
    client = _cache_client()
    if client is None:
        return
    index_key = _INDEX_KEY.format(_segment(resolver_name))
    try:
        keys = list(client.sscan_iter(index_key))
        if keys:
            client.unlink(*keys)
        client.unlink(index_key)
    except redis_lib.exceptions.RedisError as error:
        _disable_redis(error)
        return
    log.info(f"Dropped {len(keys)} user cache entries of the resolver {resolver_name!r}.")


def flush_user_cache() -> int:
    """
    Drop everything this cache holds, for every resolver.

    Walks the configured resolvers rather than scanning the Redis database, so
    a flush stays proportional to the number of resolvers instead of the number
    of keys. A resolver that no longer exists keeps its entries until they
    expire, which is why deleting a resolver drops them at that moment.

    :return: the number of resolvers whose entries were dropped
    """
    if _cache_client() is None:
        return 0
    # Imported here because the resolver module reads the user cache itself
    from privacyidea.lib.resolver import get_resolver_list
    resolver_names = list(get_resolver_list())
    for resolver_name in resolver_names:
        invalidate_resolver(resolver_name)
    return len(resolver_names)
