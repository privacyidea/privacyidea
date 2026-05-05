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

Setting PI_REDIS_URL alone does nothing — each cacheable workload has its own
opt-in flag (e.g. PI_REDIS_CACHE_CHALLENGES) so they can be rolled out and
rolled back independently.  Use ``redis_feature_enabled("challenges")`` to gate
caller code; it returns True only when the client is connected *and* the
per-feature flag is set.
"""
import json
import logging
from datetime import datetime

from privacyidea.lib.framework import get_app_config_value, get_app_local_store
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

# Redis key templates
_TXN_KEY = "pi:challenge:txn:{}"  # pi:challenge:txn:<transaction_id>  → JSON
_SERIAL_KEY = "pi:challenge:serial:{}"  # pi:challenge:serial:<serial>       → SET of txn ids

# Keep Redis keys a bit beyond validitytime so we don't evict just before the
# DB expiry check fires, and to absorb minor clock skew between nodes.
_TTL_BUFFER_SECONDS = 30


def get_redis():
    """
    Return a connected Redis client if PI_REDIS_URL is configured, else None.

    The client is initialised once per Flask app instance (per worker) and
    cached in the app-local store.  If the initial connection fails, or if any
    later operation fails, the client is set to None for the lifetime of the
    worker — so Redis is never retried and can never add latency to auth
    requests after a failure.
    """
    store = get_app_local_store()
    if '_redis_initialized' not in store:
        store['_redis_initialized'] = True
        url = get_app_config_value('PI_REDIS_URL')
        if url:
            try:
                import redis as redis_lib
                client = redis_lib.Redis.from_url(
                    url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                client.ping()
                store['_redis_client'] = client
                log.info("Redis cache connected (%s).", url)
            except Exception as e:
                log.warning("Redis not available at '%s': %s — falling back to DB only.", url, e)
                store['_redis_client'] = None
        else:
            store['_redis_client'] = None
    return store.get('_redis_client')


def redis_feature_enabled(feature: str) -> bool:
    """
    Return True if Redis is reachable AND caching is enabled for ``feature``.

    Each cacheable workload has its own boolean flag (PI_REDIS_CACHE_<FEATURE>)
    so operators can stage rollouts and turn one workload off without touching
    the others.  All callers should gate on this rather than on get_redis()
    directly.
    """
    if get_redis() is None:
        return False
    key = f"PI_REDIS_CACHE_{feature.upper()}"
    return bool(get_app_config_value(key, False))


def _disable_redis(e: Exception):
    """
    Mark Redis as unavailable for this worker after an operation-level failure.

    This is a one-way trip: once Redis fails during normal operation, we stop
    trying for the lifetime of the worker process rather than paying a timeout
    on every subsequent request.  The worker will start using Redis again after
    it is restarted (e.g. by gunicorn's worker recycling).
    """
    log.warning("Redis operation failed: %s — disabling cache for this worker.", e)
    store = get_app_local_store()
    store['_redis_client'] = None


class ChallengeDTO:
    """
    A challenge object reconstituted from the Redis cache.

    Implements the same attribute/method surface as the Challenge SQLAlchemy
    model so token classes work transparently with either.  Challenges stored
    only in Redis have no DB row, so save() and delete() operate on Redis only.
    """

    def __init__(self, transaction_id: str, serial: str, challenge: str = '',
                 data: str = '', session: str = '', timestamp: datetime = None,
                 expiration: datetime = None, received_count: int = 0,
                 otp_valid: bool = False):
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
        self.received_count += 1
        self.otp_valid = valid

    def set_data(self, data):
        if isinstance(data, str):
            self.data = data
        else:
            self.data = json.dumps(data)

    def set_session(self, session: str):
        self.session = session

    def save(self):
        """Update the Redis entry with any mutations (otp_status, data, session, …)."""
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
    if not redis_feature_enabled("challenges"):
        return
    r = get_redis()
    try:
        ttl = max(1, int((expiration - utc_now()).total_seconds()) + _TTL_BUFFER_SECONDS)
        payload = json.dumps({
            'transaction_id': transaction_id,
            'serial': serial,
            'challenge': challenge,
            'data': data or '',
            'session': session or '',
            'timestamp': timestamp.isoformat(),
            'expiration': expiration.isoformat(),
            'received_count': received_count,
            'otp_valid': otp_valid,
        })
        pipe = r.pipeline()
        pipe.setex(_TXN_KEY.format(transaction_id), ttl, payload)
        pipe.sadd(_SERIAL_KEY.format(serial), transaction_id)
        pipe.expire(_SERIAL_KEY.format(serial), ttl)
        pipe.execute()
    except Exception as e:
        _disable_redis(e)


def evict_challenge(transaction_id: str, serial: str):
    """
    Remove a challenge from Redis.
    Called from ChallengeDTO.delete() and can be called on explicit invalidation.
    """
    if not redis_feature_enabled("challenges"):
        return
    r = get_redis()
    try:
        pipe = r.pipeline()
        pipe.delete(_TXN_KEY.format(transaction_id))
        pipe.srem(_SERIAL_KEY.format(serial), transaction_id)
        pipe.execute()
    except Exception as e:
        _disable_redis(e)


def get_challenges_from_cache(serial: str = None, transaction_id: str = None,
                              challenge: str = None) -> list[ChallengeDTO] | None:
    """
    Try to serve a get_challenges() call from Redis.

    Returns a list of ChallengeDTO on a cache hit (may be empty after filtering),
    or None to signal a cache miss so the caller falls back to the database.

    A None return means "don't know" — an empty list means "found nothing".
    """
    if not redis_feature_enabled("challenges"):
        return None
    r = get_redis()

    try:
        if transaction_id:
            raw = r.get(_TXN_KEY.format(transaction_id))
            if raw is None:
                return None  # cache miss
            dto = _deserialize(raw)
            if dto is None:
                return None
            candidates = [dto]

        elif serial:
            txn_ids = r.smembers(_SERIAL_KEY.format(serial))
            if not txn_ids:
                return None  # cache miss
            raws = r.mget([_TXN_KEY.format(tid) for tid in txn_ids])
            candidates = [_deserialize(raw) for raw in raws if raw is not None]
            candidates = [c for c in candidates if c is not None]
            if not candidates:
                # All individual keys expired → treat as miss so DB is consulted
                return None

        else:
            # Unfiltered "get all" — cannot serve from Redis
            return None

        # Apply remaining filters
        if serial is not None:
            candidates = [c for c in candidates if c.serial == serial]
        if challenge is not None:
            candidates = [c for c in candidates if c.challenge == challenge]

        return candidates

    except Exception as e:
        _disable_redis(e)
        return None


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
    except Exception as e:
        log.warning("Could not deserialize challenge from Redis: %s", e)
        return None


def _update_challenge_in_cache(dto: ChallengeDTO):
    """Re-serialise a mutated ChallengeDTO back into Redis."""
    if not redis_feature_enabled("challenges"):
        return
    r = get_redis()
    try:
        remaining = int((dto.expiration - utc_now()).total_seconds()) + _TTL_BUFFER_SECONDS
        if remaining <= 0:
            return  # already expired, no point updating
        payload = json.dumps({
            'transaction_id': dto.transaction_id,
            'serial': dto.serial,
            'challenge': dto.challenge,
            'data': dto.data or '',
            'session': dto.session or '',
            'timestamp': dto.timestamp.isoformat(),
            'expiration': dto.expiration.isoformat(),
            'received_count': dto.received_count,
            'otp_valid': dto.otp_valid,
        })
        r.setex(_TXN_KEY.format(dto.transaction_id), remaining, payload)
    except Exception as e:
        _disable_redis(e)




