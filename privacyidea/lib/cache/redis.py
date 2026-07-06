# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
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
Optional Redis cache layer for privacyIDEA.

Currently used for challenge caching to support HA deployments where multiple
nodes need to share short-lived challenge state without round-tripping to a
Galera/ProxySQL cluster for every auth request.

If PI_REDIS_URL is not set, every function degrades gracefully to a no-op and
callers fall back to the database.

Configuration (pi.cfg or environment):
    PI_REDIS_URL = "redis://localhost:6379/0"
    # or for Docker secrets:
    PI_REDIS_URL_FILE = "/run/secrets/redis_url"

Setting PI_REDIS_URL alone does nothing - each cacheable workload has its own
opt-in flag (e.g. PI_REDIS_CACHE_CHALLENGES) so they can be rolled out and
rolled back independently.  Use ``redis_feature_enabled("challenges")`` to gate
caller code; it returns True only when the client is connected *and* the
per-feature flag is set.
"""
import json
import logging
import os
import threading
import time
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse, urlunparse

import redis as redis_lib

from privacyidea.lib.framework import get_app_config_value, get_app_local_store
from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

# Serialises the connect path in get_redis() so concurrent threads under
# Gunicorn gthread / uWSGI --threads can't both call _build_client and
# leak a socket. Uncontended after first successful connect - every later
# call returns early on the "client is not None" fast path before reaching
# the lock.
_connect_lock = threading.Lock()


class CacheState(Enum):
    """
    Non-hit outcomes from ``get_challenges_from_cache``.

    Returning bare ``None`` for both "cache reachable, key absent" and
    "cache unreachable" would conflate two states that callers must
    handle differently - a cleanup path needs to issue a defensive
    eviction only when the cache state is *unknown*, not when the cache
    has authoritatively told us the entry is gone.
    """

    MISS = "miss"
    """Cache is reachable and confirms the key (or set) is not present."""

    UNAVAILABLE = "unavailable"
    """
    Cache is disabled, errored mid-read, returned malformed data, or the
    query shape cannot be served from a key-value store (e.g. unfiltered
    list-all). Callers should treat the cache state as unknown and fall
    back to the database / issue defensive eviction.
    """

# Default cooldown between connection attempts after any failure (init or
# runtime). One unified value covers boot-order races (worker up before
# Redis container) and transient runtime errors (Redis restart, network
# blip): the next op after the cooldown retries, and if it succeeds we're back
# in business. During an outage the worker pays the connect timeout at most
# once per cooldown window - every other op short-circuits to None.
#
# Tunable via ``PI_REDIS_RETRY_COOLDOWN`` (seconds). Operators with flaky
# networks may raise it, tighter environments may lower it.
_DEFAULT_RETRY_COOLDOWN_SECONDS = 30


def _retry_cooldown_seconds() -> int:
    """Return the configured cooldown in seconds, falling back to the
    default if the config value is missing or malformed."""
    raw = get_app_config_value('PI_REDIS_RETRY_COOLDOWN', _DEFAULT_RETRY_COOLDOWN_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_RETRY_COOLDOWN_SECONDS
    return value if value > 0 else _DEFAULT_RETRY_COOLDOWN_SECONDS

# Redis key templates
#
# A transaction can carry more than one challenge: a single authentication
# request triggers one challenge per matching token (push + SMS, several
# passkeys, ...), and they all share the same transaction_id - mirroring the
# SQL model where multiple Challenge rows share a transaction_id. The txn key
# is therefore a HASH keyed by token serial (field "" for usernameless passkey
# challenges, which are looked up by transaction_id only). A token never
# creates two challenges in one transaction, so serial uniquely identifies a
# challenge within the hash.
_TXN_KEY = "pi:challenge:txn:{}"  # pi:challenge:txn:<transaction_id> -> HASH {serial -> JSON}
_SERIAL_KEY = "pi:challenge:serial:{}"  # pi:challenge:serial:<serial>       -> SET of txn ids

# Keep Redis keys a bit beyond validitytime so we don't evict just before the
# DB expiry check fires, and to absorb minor clock skew between nodes.
_TTL_BUFFER_SECONDS = 30

# Shared client construction args.
_CLIENT_KWARGS = dict(
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def _redact_url(url: str) -> str:
    """Strip any user:password embedded in a Redis URL before logging."""
    try:
        parts = urlparse(url)
        if parts.username or parts.password:
            host = parts.hostname or ""
            if parts.port:
                host = f"{host}:{parts.port}"
            netloc = f"***@{host}"
            return urlunparse(parts._replace(netloc=netloc))
        return url
    except Exception:
        return "<redis-url>"


def _build_client(url: str) -> "redis_lib.Redis":
    """
    Construct, ping, and version-check a Redis client. Raises on failure.

    The challenge cache writes use ``EXPIRE NX`` and ``EXPIRE GT`` flags
    that Redis 7.0 introduced. Older servers accept PING but reject those
    flags with a syntax error on first write, which would silently latch
    every worker into DB-only mode. Refuse the connection up front so the
    misconfiguration surfaces at startup instead of after the first auth.
    """
    client = redis_lib.Redis.from_url(url, **_CLIENT_KWARGS)
    client.ping()
    server_info = client.info("server")
    version = server_info.get("redis_version", "0")
    try:
        major = int(version.split(".", 1)[0])
    except (ValueError, AttributeError):
        major = 0
    if major < 7:
        raise RuntimeError(
            f"Redis server reports version {version!r}; the challenge cache "
            f"requires Redis 7 or later (EXPIRE NX/GT). Refusing to use this "
            f"server - set PI_REDIS_CACHE_CHALLENGES=False or upgrade Redis."
        )
    return client


def get_redis():
    """
    Return a connected Redis client if PI_REDIS_URL is configured, else None.

    A single ``_redis_retry_after`` timestamp drives the lifecycle:

    * Live client cached -> return it.
    * Inside the cooldown window after a recent failure -> return None
      immediately. No timeout cost on the hot path.
    * Past the cooldown -> try to (re)connect. On success cache the client,
      on failure restart the cooldown.

    There is no one-way latch: the worker self-heals when Redis comes back,
    no restart required. The cost is that during an outage the worker pays
    the connect timeout once per cooldown window per slot - acceptable
    because privacyidea's request volume is sparse and the cooldown is
    short.

    Thread- and fork-safety
    ~~~~~~~~~~~~~~~~~~~~~~~

    * Threads: the connect path is serialised by ``_connect_lock`` so two
      racing threads can't both call ``_build_client`` (which would each
      pay the 2 s connect timeout and leak the loser's socket). The fast
      path returns the cached client before reaching the lock.
    * Forks: redis-py connection-pool sockets are not fork-safe. If the
      parent process connected before forking (uWSGI ``fork-after-init``,
      Gunicorn ``preload_app=True``), every child inherits the same fds
      and concurrent RESP traffic corrupts the protocol. We stamp the PID
      on the cached client and drop it whenever ``os.getpid()`` changes -
      each child re-runs the connect path once after fork.
    """
    store = get_app_local_store()
    cached = store.get('_redis_client_entry')
    if cached is not None and cached[0] == os.getpid():
        return cached[1]
    url = get_app_config_value('PI_REDIS_URL')
    if not url:
        return None
    now = time.monotonic()
    if now < store.get('_redis_retry_after', 0):
        return None
    with _connect_lock:
        # Re-check inside the lock: another thread may have connected (or
        # tripped the cooldown) while we were waiting.
        cached = store.get('_redis_client_entry')
        if cached is not None and cached[0] == os.getpid():
            return cached[1]
        if time.monotonic() < store.get('_redis_retry_after', 0):
            return None
        try:
            client = _build_client(url)
            store['_redis_client_entry'] = (os.getpid(), client)
            store.pop('_redis_retry_after', None)
            log.info("Redis cache connected (%s).", _redact_url(url))
            return client
        except (redis_lib.exceptions.RedisError, RuntimeError, OSError) as e:
            # RedisError: connectivity / auth / protocol failures from redis-py.
            # RuntimeError: explicit version-gate refusal in _build_client.
            # OSError: raw socket errors that escape redis-py's wrapping.
            # Anything else (TypeError, AttributeError, ...) is a programmer
            # bug and should surface as a real traceback, not be silently
            # swallowed into a "Redis down" cooldown.
            cooldown = _retry_cooldown_seconds()
            store['_redis_retry_after'] = now + cooldown
            log.warning("Redis not available at '%s': %s - falling back to DB only "
                        "(will retry in %ds).",
                        _redact_url(url), e, cooldown)
            return None


def redis_client_for_feature(feature: str):
    """
    Return the Redis client to use for ``feature``, or ``None``.

    Combines the per-feature config flag check and the connectivity probe
    in a single call so hot-path ops don't pay ``get_redis()`` twice (once
    via ``redis_feature_enabled``, once for the client reference). Returns
    ``None`` when the feature is off OR Redis is unreachable.
    """
    if not redis_feature_configured(feature):
        return None
    return get_redis()


def redis_feature_enabled(feature: str) -> bool:
    """
    Return True if Redis is reachable AND caching is enabled for ``feature``.

    Each cacheable workload has its own boolean flag (PI_REDIS_CACHE_<FEATURE>)
    so operators can stage rollouts and turn one workload off without touching
    the others. Convenience boolean for callers that only need the gate
    (response payloads, log fields). Hot paths that also need the client
    should use ``redis_client_for_feature`` to avoid a duplicate lookup.
    """
    return redis_client_for_feature(feature) is not None


def redis_feature_configured(feature: str) -> bool:
    """
    Return True if the operator has opted into caching for ``feature``.

    Distinct from ``redis_feature_enabled``: this only checks the config,
    not live connectivity. Use it when "configured but unreachable" needs
    to be distinguished from "off" - e.g. cleanup paths that want to warn
    operators that an eviction silently no-op'd because the worker is in
    its retry cooldown.

    Caching requires both ``PI_REDIS_URL`` and the per-feature flag. If
    no URL is set, no Redis was ever configured - "configured" is False
    regardless of the per-feature flag.
    """
    if not get_app_config_value('PI_REDIS_URL'):
        return False
    key = f"PI_REDIS_CACHE_{feature.upper()}"
    return bool(get_app_config_value(key, False))


def _disable_redis(e: Exception):
    """
    Drop the cached client and start a cooldown after an operation-level
    failure.

    Not a permanent disable - ``get_redis`` will retry once the cooldown
    expires. The cooldown bounds the cost of repeated timeouts during an
    outage to roughly one per ``PI_REDIS_RETRY_COOLDOWN`` per worker; the
    auto-retry means a transient Redis blip (restart, network glitch) is
    invisible to operators after one cooldown window.
    """
    cooldown = _retry_cooldown_seconds()
    log.warning("Redis op failed: %s - entering %ds cooldown.", e, cooldown)
    store = get_app_local_store()
    store.pop('_redis_client_entry', None)
    store['_redis_retry_after'] = time.monotonic() + cooldown
    # TODO(metrics PR #5270): emit `pi_redis_cooldown_entered_total` so
    # operators can alert on repeated cooldowns indicating real Redis health
    # issues vs. one-off blips.


class ChallengeDTO:
    """
    A challenge object reconstituted from the Redis cache.

    Duck-typed to the same surface as ``privacyidea.models.Challenge`` so
    token classes work transparently with either backend. Challenges stored
    only in Redis have no DB row, so save() and delete() operate on Redis
    only.
    """

    def __init__(self, transaction_id: str, serial: str,
                 timestamp: datetime, expiration: datetime,
                 challenge: str = '', data: str = '', session: str = '',
                 received_count: int = 0, otp_valid: bool = False):
        # timestamp and expiration are required positionals: is_valid()
        # compares them with utc_now() and would raise TypeError on None,
        # so a half-formed DTO is unsafe by construction.
        self.transaction_id = transaction_id
        self.serial = serial
        self.challenge = challenge
        self.data = data
        self.session = session
        self.timestamp = timestamp
        self.expiration = expiration
        self.received_count = received_count
        self.otp_valid = otp_valid

    def is_valid(self) -> bool:
        now = utc_now()
        return self.timestamp <= now < self.expiration

    def is_open(self) -> bool:
        from privacyidea.lib.tokenclass import ChallengeSession
        return (self.is_valid() and not self.otp_valid
                and self.get_session() not in (ChallengeSession.DECLINED, ChallengeSession.CANCELLED))

    def get_session(self) -> str:
        return self.session

    def get_challenge(self) -> str:
        return self.challenge

    def get_transaction_id(self) -> str:
        return self.transaction_id

    def get_data(self):
        if not self.data:
            return {}
        try:
            return json.loads(self.data)
        except (json.JSONDecodeError, ValueError):
            return self.data

    def get_otp_status(self) -> tuple[int, bool]:
        return self.received_count, self.otp_valid

    def get(self, timestamp=False) -> dict:
        descr = {
            'transaction_id': self.transaction_id,
            'challenge': self.challenge,
            'serial': self.serial,
            'data': self.get_data(),
            'otp_received': self.received_count > 0,
            'received_count': self.received_count,
            'otp_valid': self.otp_valid,
            'expiration': self.expiration,
        }
        descr['timestamp'] = f"{self.timestamp}" if timestamp else self.timestamp
        return descr

    def set_otp_status(self, valid: bool = False):
        # Mutate first, then save. If save() hits a Redis error it is
        # swallowed and the cache keeps the old value while the in-memory
        # DTO has the new one. Acceptable trade-off: the only callers that
        # write valid=False are wrong-answer paths whose received_count is
        # bounded by the challenge's own TTL (a missed increment grants at
        # most a couple of extra retries on this one challenge), and the
        # valid=True callers delete the challenge immediately afterwards.
        self.received_count += 1
        self.otp_valid = valid
        self.save()

    def set_data(self, data):
        # Mirror Challenge.set_data (models/challenge.py): str -> as-is,
        # dict -> JSON, anything else (bytes, ints, ...) -> unicode coercion.
        # Keeps both backends accepting the same input shapes.
        if isinstance(data, str):
            self.data = data
        elif isinstance(data, dict):
            self.data = json.dumps(data)
        else:
            self.data = convert_column_to_unicode(data)
        self.save()

    def set_session(self, session: str):
        self.session = session
        self.save()

    def to_payload(self) -> str:
        """Serialise this DTO to the JSON payload stored under the txn key.
        Paired with ``_deserialize`` - keep the field set in sync."""
        return json.dumps({
            'transaction_id': self.transaction_id,
            'serial': self.serial,
            'challenge': self.challenge,
            'data': self.data or '',
            'session': self.session or '',
            'timestamp': self.timestamp.isoformat(),
            'expiration': self.expiration.isoformat(),
            'received_count': self.received_count,
            'otp_valid': self.otp_valid,
        })

    def save(self):
        """
        Persist any mutations back to Redis.

        Mutator methods on this DTO (``set_otp_status``, ``set_data``,
        ``set_session``) call ``save()`` themselves so that callers written
        against the DB-backed ``Challenge`` - which relies on SQLAlchemy
        autoflush at request end - get equivalent persistence semantics
        without having to know which backend they hold. Explicit ``save()``
        is still safe (idempotent SETEX overwrite) and can be useful as a
        no-op for code that wants to stay backend-agnostic.
        """
        _update_challenge_in_cache(self)

    def delete(self):
        """Evict from Redis."""
        evict_challenge(self.transaction_id, self.serial)


def cache_challenge(serial: str, transaction_id: str, challenge: str, data: str,
                    session: str, timestamp: datetime, expiration: datetime,
                    received_count: int = 0, otp_valid: bool = False):
    """
    Store a newly created challenge in Redis.
    Called from create_challenge() as the primary (and only) persistence when caching is enabled.
    """
    # TODO(metrics PR #5270): increment `pi_redis_challenge_writes_total` on
    # success and `pi_redis_challenge_write_errors_total` on the exception
    # branch - operators want both rate and error ratio.
    r = redis_client_for_feature("challenges")
    if r is None:
        return
    try:
        if expiration <= utc_now():
            # Refuse to write an already-expired challenge. is_valid() would
            # reject reads anyway, but the entry would still occupy a key
            # and show up in any raw inspection or non-is_valid() consumer.
            return
        ttl = int((expiration - utc_now()).total_seconds()) + _TTL_BUFFER_SECONDS
        payload = ChallengeDTO(
            transaction_id=transaction_id, serial=serial,
            timestamp=timestamp, expiration=expiration,
            challenge=challenge, data=data or '', session=session or '',
            received_count=received_count, otp_valid=otp_valid,
        ).to_payload()
        txn_key = _TXN_KEY.format(transaction_id)
        pipe = r.pipeline()
        # One field per token serial. Tokens sharing this transaction_id keep
        # their own field, so a second token's challenge no longer overwrites
        # the first. The hash TTL covers the whole transaction; NX seeds it on
        # the first field, GT extends (never shrinks) it so a shorter-lived
        # sibling added later cannot expire still-valid challenges early. Both
        # flags require Redis 7+. A shorter-lived field that outlives its own
        # validity is filtered out on read by is_valid(), not by per-field TTL.
        pipe.hset(txn_key, serial, payload)
        pipe.expire(txn_key, ttl, nx=True)
        pipe.expire(txn_key, ttl, gt=True)
        # Only index by serial when one is given. Usernameless passkey auth
        # creates challenges with serial="", and indexing those would funnel
        # every such request into one shared set whose TTL never settles
        # (each new write extends it via GT) and whose membership grows
        # unbounded. Those challenges are only ever retrieved by
        # transaction_id, so the set serves no purpose for them.
        if serial:
            pipe.sadd(_SERIAL_KEY.format(serial), transaction_id)
            # Same NX+GT TTL discipline as the txn hash above: the serial set
            # is shared across all of the token's open challenges, so its TTL
            # must cover the longest-lived member.
            pipe.expire(_SERIAL_KEY.format(serial), ttl, nx=True)
            pipe.expire(_SERIAL_KEY.format(serial), ttl, gt=True)
        pipe.execute()
    except redis_lib.exceptions.RedisError as e:
        _disable_redis(e)


def evict_challenge(transaction_id: str, serial: str):
    """
    Remove a single challenge (one ``serial`` within ``transaction_id``) from
    Redis. Called from ChallengeDTO.delete() and on explicit invalidation.

    Only this token's field is removed; sibling tokens that share the
    transaction keep their challenges. Redis drops the txn hash automatically
    once its last field is deleted.

    Skips silently when the cache feature is off or when ``get_redis()``
    returns None (cooldown after a recent failure). The unified retry
    cooldown means a temporarily-disabled worker will pick the cache back
    up automatically once Redis is available again.
    """
    r = redis_client_for_feature("challenges")
    if r is None:
        return
    try:
        pipe = r.pipeline()
        pipe.hdel(_TXN_KEY.format(transaction_id), serial)
        # cache_challenge() only writes the serial set when serial is truthy,
        # so don't try to remove from it otherwise - it doesn't exist.
        if serial:
            pipe.srem(_SERIAL_KEY.format(serial), transaction_id)
        pipe.execute()
    except redis_lib.exceptions.RedisError as e:
        _disable_redis(e)


def evict_transaction(transaction_id: str, serials: "list[str]"):
    """
    Remove every challenge under ``transaction_id`` from Redis - the whole
    multi-token transaction at once. Called when cancelling a transaction.

    ``serials`` are the token serials whose challenges live under this
    transaction (as returned by ``get_challenges``); their index entries are
    cleaned up alongside the hash. Deleting the hash also covers any field we
    did not know about (e.g. a sibling written by another worker after our
    read), which is why this is also the defensive eviction used on a cache
    miss.
    """
    r = redis_client_for_feature("challenges")
    if r is None:
        return
    try:
        pipe = r.pipeline()
        pipe.delete(_TXN_KEY.format(transaction_id))
        for serial in serials:
            if serial:
                pipe.srem(_SERIAL_KEY.format(serial), transaction_id)
        pipe.execute()
    except redis_lib.exceptions.RedisError as e:
        _disable_redis(e)


def evict_challenges_for_serial(serial: str):
    """
    Remove every cached challenge belonging to ``serial`` from Redis.

    Used when a token or container is deleted so that in-flight transaction
    IDs cannot continue to resolve against the cache after their owning
    object is gone. Iterates the serial-set and removes only this token's
    field from each transaction hash, then deletes the set itself. Sibling
    tokens that share a transaction keep their challenges (Redis drops a hash
    once its last field is gone), so deleting one token does not cancel
    another token's in-flight challenge.

    Race window (intentionally accepted): SMEMBERS and the subsequent
    pipeline are not atomic. If another worker calls ``cache_challenge``
    for this serial between the SMEMBERS snapshot and ``pipe.execute()``,
    the new transaction it writes is not in our snapshot - we delete the
    serial set (wiping its index entry along with the dead ones) but leave
    the new field alive until its TTL. ``get_challenges`` by transaction_id
    then resolves it directly against the txn hash, handing back a challenge
    for a token that no longer exists; the eventual lookup of that token
    fails with ResourceNotFoundError and the user retries the auth flow.

    The race window is bounded by the duration between SMEMBERS and
    EXEC (microseconds on a healthy Redis), and the orphan field survives
    at most one challenge-validity TTL. Token deletions are rare events.
    Closing the race fully would require either a server-side Lua
    script or a WATCH/MULTI retry loop; both add complexity that
    outweighs the practical exposure for this workload. Reconsider if
    operational data shows the race triggering in production.
    """
    r = redis_client_for_feature("challenges")
    if r is None:
        return
    try:
        serial_key = _SERIAL_KEY.format(serial)
        txn_ids = r.smembers(serial_key)
        pipe = r.pipeline()
        for tid in txn_ids:
            pipe.hdel(_TXN_KEY.format(tid), serial)
        pipe.delete(serial_key)
        pipe.execute()
    except redis_lib.exceptions.RedisError as e:
        _disable_redis(e)


def get_challenges_from_cache(serial: str = None, transaction_id: str = None,
                              challenge: str = None) -> "list[ChallengeDTO] | CacheState":
    """
    Try to serve a get_challenges() call from Redis. Only exact serial /
    transaction_id lookups are served; an unfiltered (list-all) query returns
    UNAVAILABLE because a key-value store cannot enumerate in aggregate.

    Returns:
        * ``list[ChallengeDTO]`` - cache hit. List may be empty after
          filtering by ``challenge`` (the txn or serial set was found,
          but the in-memory filter eliminated all members). The list
          itself being non-None is the authoritative signal that the
          cache spoke for this query.
        * ``CacheState.MISS`` - cache is reachable and confirms the key
          (or serial set) is not present. Callers can treat this as
          authoritative-empty.
        * ``CacheState.UNAVAILABLE`` - cache is disabled, errored, the
          payload was malformed, or the query shape cannot be served
          (unfiltered list-all). Callers fall back to the database.

    The three-state result intentionally avoids the older
    ``None`` collapse that hid the miss/unavailable distinction -
    cleanup paths in particular need to know whether the cache is
    authoritative for a negative answer.
    """
    # TODO(metrics PR #5270): bucket the outcomes here as
    # `pi_redis_challenge_reads_total{outcome="hit|miss|unavailable"}`
    # so the cache hit ratio can drive an SLI. The three states map
    # directly to the three return paths below.
    redis_client = redis_client_for_feature("challenges")
    if redis_client is None:
        return CacheState.UNAVAILABLE
    try:
        if transaction_id:
            # The txn hash holds one field per token serial. HGETALL returns
            # every challenge in the transaction - all triggered tokens.
            raw_payloads = redis_client.hgetall(_TXN_KEY.format(transaction_id))
            if not raw_payloads:
                return CacheState.MISS
            candidates = [_deserialize(raw) for raw in raw_payloads.values()]
            candidates = [c for c in candidates if c is not None]
            if not candidates:
                # Hash held only corrupt payloads - can't trust the cache here.
                return CacheState.UNAVAILABLE

        elif serial:
            transaction_ids = redis_client.smembers(_SERIAL_KEY.format(serial))
            if not transaction_ids:
                return CacheState.MISS
            # This serial's challenge in each of its transactions is the
            # field named after the serial. One HGET per transaction.
            pipe = redis_client.pipeline()
            for txn_id in transaction_ids:
                pipe.hget(_TXN_KEY.format(txn_id), serial)
            raw_payloads = pipe.execute()
            candidates = [_deserialize(raw) for raw in raw_payloads if raw is not None]
            candidates = [c for c in candidates if c is not None]
            if not candidates:
                # Set membership pointed at hash fields that have all expired
                # individually. The cache no longer has authoritative state
                # for this serial - fall back to DB rather than guess.
                return CacheState.UNAVAILABLE

        else:
            # Unfiltered "get all" cannot be served from a key-value store.
            # When caching is on, challenges live only in Redis, so the admin
            # "list all challenges" aggregate view is intentionally degraded:
            # this returns UNAVAILABLE, the caller falls back to the (empty) DB,
            # and the WebUI shows the "cannot be listed in aggregate" banner.
            # Per-token / per-user listing works via the serial and
            # transaction_id branches above.
            return CacheState.UNAVAILABLE

        # Apply remaining filters
        if serial is not None:
            candidates = [c for c in candidates if c.serial == serial]
        if challenge is not None:
            candidates = [c for c in candidates if c.challenge == challenge]

        return candidates

    except redis_lib.exceptions.RedisError as e:
        _disable_redis(e)
        return CacheState.UNAVAILABLE


def _deserialize(raw: str) -> ChallengeDTO | None:
    try:
        d = json.loads(raw)
        return ChallengeDTO(
            transaction_id=d['transaction_id'],
            serial=d['serial'],
            challenge=d.get('challenge', ''),
            data=d.get('data', ''),
            session=d.get('session', ''),
            timestamp=datetime.fromisoformat(d['timestamp']),
            expiration=datetime.fromisoformat(d['expiration']),
            received_count=d.get('received_count', 0),
            otp_valid=d.get('otp_valid', False),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        # Cache payload is malformed: not valid JSON, missing required field,
        # bad ISO timestamp, or wrong field type. Anything beyond that is a
        # programmer bug - let it propagate.
        log.warning("Could not deserialize challenge from Redis: %s", e)
        return None


def _update_challenge_in_cache(dto: ChallengeDTO):
    """Re-serialise a mutated ChallengeDTO back into Redis."""
    r = redis_client_for_feature("challenges")
    if r is None:
        return
    try:
        if dto.expiration <= utc_now():
            # Don't resurrect an already-expired challenge. The 30s buffer
            # only protects fresh writes from clock-skew between nodes, it
            # must not be added before the expiry gate or any save() within
            # 30s after expiration would re-write the entry with a positive
            # TTL.
            return
        remaining = int((dto.expiration - utc_now()).total_seconds()) + _TTL_BUFFER_SECONDS
        txn_key = _TXN_KEY.format(dto.transaction_id)
        pipe = r.pipeline()
        # Rewrite just this token's field; sibling challenges in the same
        # transaction are untouched. HSET preserves the hash's existing TTL
        # when the hash already exists, but if the hash was evicted between the
        # read and this save() the HSET re-creates it with NO TTL - so seed the
        # TTL with NX (GT alone cannot set a TTL on a key that has none) and
        # then extend with GT, exactly as cache_challenge does.
        pipe.hset(txn_key, dto.serial, dto.to_payload())
        pipe.expire(txn_key, remaining, nx=True)
        pipe.expire(txn_key, remaining, gt=True)
        # Re-assert the serial index. A bare HSET would otherwise leave a
        # mutated challenge unreachable by serial if its index entry had been
        # dropped (e.g. evicted while this DTO was held). NX seeds the set TTL
        # if it was re-created here; GT only extends it, never shrinks it, so a
        # shorter save() can't kill siblings.
        if dto.serial:
            pipe.sadd(_SERIAL_KEY.format(dto.serial), dto.transaction_id)
            pipe.expire(_SERIAL_KEY.format(dto.serial), remaining, nx=True)
            pipe.expire(_SERIAL_KEY.format(dto.serial), remaining, gt=True)
        pipe.execute()
    except redis_lib.exceptions.RedisError as e:
        _disable_redis(e)
