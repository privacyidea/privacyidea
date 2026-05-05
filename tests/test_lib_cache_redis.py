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
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Tests for the Redis challenge cache (privacyidea/lib/cache/redis.py).

Two test strategies are used:

1. In-memory fake (FakeRedis + fake_redis_in_store)
   No network required.  A minimal Redis double is injected directly into
   the app-local store so get_redis() returns it without touching the network.
   Covers the full DTO / cache logic and all fallback paths.
   Runs unconditionally in every CI environment.

2. Real Redis (TestRealRedisIntegration)
   Requires TEST_REDIS_URL to be set (e.g. redis://127.0.0.1:6379/0).
   Skipped automatically when the env var is absent.  In CI, both the
   MariaDB and PostgreSQL workflows spin up a Redis service container and
   export TEST_REDIS_URL, so these tests always run there.
   Catches issues the fake cannot: serialisation edge cases, pipeline
   behaviour, actual TTL handling, and connection lifecycle.

Where applicable, the same behaviour is verified against both the Redis
path (DTO) and the DB fallback path to prove callers are unaffected by
which backend is active.
"""
import os
import unittest
from contextlib import contextmanager
from datetime import timedelta

import pytest

from .base import MyTestCase
from privacyidea.lib.cache.redis import (
    ChallengeDTO,
    cache_challenge,
    evict_challenge,
    get_challenges_from_cache,
    get_redis,
)
from privacyidea.lib.challenge import get_challenges, get_challenges_paginate
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.token import create_challenge, init_token, remove_token
from privacyidea.models import Challenge, db
from privacyidea.models.utils import utc_now


class FakeRedis:
    """
    Minimal Redis double that covers the operations used by the cache module:
    setex, get, mget, delete, sadd, srem, smembers, expire, pipeline.
    Enough to make real logic run without a network connection.
    """

    def __init__(self):
        self._data: dict[str, str] = {}  # key → value
        self._sets: dict[str, set] = {}  # key → set of members
        self._ttls: dict[str, int] = {}  # key → ttl seconds (last set)
        self.ping_raises = False

    def ping(self):
        if self.ping_raises:
            raise ConnectionError("fake ping failure")

    def setex(self, key, ttl, value):
        self._data[key] = value
        self._ttls[key] = ttl

    def get(self, key):
        return self._data.get(key)

    def mget(self, keys):
        return [self._data.get(k) for k in keys]

    def delete(self, *keys):
        for k in keys:
            self._data.pop(k, None)
            self._sets.pop(k, None)
            self._ttls.pop(k, None)

    def sadd(self, key, *values):
        self._sets.setdefault(key, set()).update(values)

    def srem(self, key, *values):
        if key in self._sets:
            self._sets[key].discard(*values)

    def smembers(self, key):
        return set(self._sets.get(key, set()))

    def expire(self, key, ttl, nx=False, xx=False, gt=False, lt=False):
        # Mirror the Redis 7 EXPIRE flag semantics we rely on (NX, GT). The key
        # must exist (as a value or a set) for any of these to apply.
        if key not in self._data and key not in self._sets:
            return 0
        current = self._ttls.get(key)
        if nx and current is not None:
            return 0
        if xx and current is None:
            return 0
        if gt and current is not None and ttl <= current:
            return 0
        if lt and current is not None and ttl >= current:
            return 0
        self._ttls[key] = ttl
        return 1

    def ttl(self, key):
        if key not in self._data and key not in self._sets:
            return -2
        return self._ttls.get(key, -1)

    def pipeline(self):
        return _FakePipeline(self)


class _FakePipeline:
    """Accumulates commands and executes them all at once on execute()."""

    def __init__(self, redis: FakeRedis):
        self._r = redis
        self._cmds = []

    def setex(self, key, ttl, value):
        self._cmds.append(('setex', key, ttl, value))
        return self

    def delete(self, *keys):
        self._cmds.append(('delete', *keys))
        return self

    def sadd(self, key, *values):
        self._cmds.append(('sadd', key, *values))
        return self

    def srem(self, key, *values):
        self._cmds.append(('srem', key, *values))
        return self

    def expire(self, key, ttl, nx=False, xx=False, gt=False, lt=False):
        self._cmds.append(('expire', key, ttl, nx, xx, gt, lt))
        return self

    def execute(self):
        for cmd in self._cmds:
            op, *args = cmd
            getattr(self._r, op)(*args)
        self._cmds.clear()


@contextmanager
def fake_redis_in_store(fake: FakeRedis | None = None, enable_challenges: bool = True):
    """
    Context manager: inject *fake* (or None) into the app-local store so that
    get_redis() returns it without network I/O, and flip on the per-feature
    cache flag so callers actually exercise the cache path.  Cleans up on exit.
    """
    from flask import current_app
    store = get_app_local_store()
    had_init = '_redis_initialized' in store
    had_client = '_redis_client' in store
    old_init = store.get('_redis_initialized')
    old_client = store.get('_redis_client')

    store['_redis_initialized'] = True
    store['_redis_client'] = fake

    flag_key = 'PI_REDIS_CACHE_CHALLENGES'
    had_flag = flag_key in current_app.config
    old_flag = current_app.config.get(flag_key)
    current_app.config[flag_key] = enable_challenges
    try:
        yield fake
    finally:
        if had_init:
            store['_redis_initialized'] = old_init
        else:
            store.pop('_redis_initialized', None)
        if had_client:
            store['_redis_client'] = old_client
        else:
            store.pop('_redis_client', None)
        if had_flag:
            current_app.config[flag_key] = old_flag
        else:
            current_app.config.pop(flag_key, None)


def _make_dto(serial='SE_CACHE_1', txn='txn-test-001', challenge='abc',
              data='', session='', offset_seconds=120) -> ChallengeDTO:
    now = utc_now()
    return ChallengeDTO(
        transaction_id=txn,
        serial=serial,
        challenge=challenge,
        data=data,
        session=session,
        timestamp=now,
        expiration=now + timedelta(seconds=offset_seconds),
    )


class TestChallengeDTO(MyTestCase):

    def test_is_valid_within_window(self):
        dto = _make_dto(offset_seconds=120)
        self.assertTrue(dto.is_valid())

    def test_is_valid_expired(self):
        dto = _make_dto(offset_seconds=-1)
        self.assertFalse(dto.is_valid())

    def test_get_data_json(self):
        dto = _make_dto(data='{"key": "value"}')
        self.assertEqual(dto.get_data(), {"key": "value"})

    def test_get_data_plain_string(self):
        dto = _make_dto(data='plain')
        self.assertEqual(dto.get_data(), 'plain')

    def test_get_data_empty(self):
        dto = _make_dto(data='')
        self.assertEqual(dto.get_data(), {})

    def test_set_otp_status(self):
        dto = _make_dto()
        self.assertEqual(dto.get_otp_status(), (0, False))
        dto.set_otp_status(True)
        self.assertEqual(dto.get_otp_status(), (1, True))
        dto.set_otp_status(False)
        self.assertEqual(dto.get_otp_status(), (2, False))

    def test_set_data_dict(self):
        dto = _make_dto()
        dto.set_data({"mode": "push"})
        self.assertEqual(dto.get_data(), {"mode": "push"})

    def test_set_data_string(self):
        dto = _make_dto()
        dto.set_data("raw_string")
        self.assertEqual(dto.data, "raw_string")

    def test_set_session(self):
        dto = _make_dto()
        dto.set_session("enrollment")
        self.assertEqual(dto.get_session(), "enrollment")

    def test_get_transaction_id(self):
        dto = _make_dto(txn='txn-getter')
        self.assertEqual(dto.get_transaction_id(), 'txn-getter')

    def test_get_challenge(self):
        dto = _make_dto(challenge='nonce-xyz')
        self.assertEqual(dto.get_challenge(), 'nonce-xyz')

    def test_get_session_after_set(self):
        dto = _make_dto(session='preset')
        self.assertEqual(dto.get_session(), 'preset')

    def test_get_returns_expected_keys(self):
        dto = _make_dto()
        result = dto.get(timestamp=True)
        for key in ('transaction_id', 'challenge', 'serial', 'data',
                    'otp_received', 'received_count', 'otp_valid',
                    'expiration', 'timestamp'):
            self.assertIn(key, result)


class TestRedisCacheOperations(MyTestCase):

    def _write_dto(self, fake: FakeRedis, dto: ChallengeDTO):
        with fake_redis_in_store(fake):
            cache_challenge(
                serial=dto.serial,
                transaction_id=dto.transaction_id,
                challenge=dto.challenge,
                data=dto.data,
                session=dto.session,
                timestamp=dto.timestamp,
                expiration=dto.expiration,
            )

    def test_cache_then_read_by_txn(self):
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE1', txn='txn-rcache-001')
        self._write_dto(fake, dto)

        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(transaction_id='txn-rcache-001')

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, 'txn-rcache-001')
        self.assertEqual(result[0].serial, 'RCACHE1')
        self.assertEqual(result[0].challenge, 'abc')

    def test_cache_then_read_by_serial(self):
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE2', txn='txn-rcache-002')
        self._write_dto(fake, dto)

        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(serial='RCACHE2')

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].serial, 'RCACHE2')

    def test_cache_miss_by_txn_returns_none(self):
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(transaction_id='nonexistent-txn')
        self.assertIsNone(result)

    def test_cache_miss_by_serial_returns_none(self):
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(serial='NOSUCHSERIAL')
        self.assertIsNone(result)

    def test_no_redis_returns_none(self):
        with fake_redis_in_store(None):
            result = get_challenges_from_cache(serial='WHATEVER')
        self.assertIsNone(result)

    def test_unfiltered_query_returns_none(self):
        """get_challenges_from_cache(no args) must always return None — can't serve from cache."""
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            result = get_challenges_from_cache()
        self.assertIsNone(result)

    def test_evict_removes_from_cache(self):
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE3', txn='txn-rcache-003')
        self._write_dto(fake, dto)

        with fake_redis_in_store(fake):
            evict_challenge('txn-rcache-003', 'RCACHE3')
            result = get_challenges_from_cache(transaction_id='txn-rcache-003')

        self.assertIsNone(result)

    def test_multiple_challenges_same_serial(self):
        fake = FakeRedis()
        dto1 = _make_dto(serial='RCACHE4', txn='txn-rcache-004a')
        dto2 = _make_dto(serial='RCACHE4', txn='txn-rcache-004b')
        self._write_dto(fake, dto1)
        self._write_dto(fake, dto2)

        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(serial='RCACHE4')

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        txn_ids = {c.transaction_id for c in result}
        self.assertEqual(txn_ids, {'txn-rcache-004a', 'txn-rcache-004b'})

    def test_serial_set_ttl_not_shrunk_by_shorter_challenge(self):
        # Regression: writing a shorter-lived challenge after a longer-lived
        # one for the same serial used to reset the shared serial-set TTL to
        # the shorter value, which then expired the set before the longer
        # challenge's own key — so get_challenges(serial=...) silently lost
        # still-valid challenges. The fix uses EXPIRE NX + GT so the set TTL
        # only ever grows.
        fake = FakeRedis()
        long_dto = _make_dto(serial='RCACHE_TTL', txn='txn-long', offset_seconds=600)
        short_dto = _make_dto(serial='RCACHE_TTL', txn='txn-short', offset_seconds=30)

        self._write_dto(fake, long_dto)
        ttl_after_long = fake.ttl(f'pi:challenge:serial:RCACHE_TTL')
        self._write_dto(fake, short_dto)
        ttl_after_short = fake.ttl(f'pi:challenge:serial:RCACHE_TTL')

        # The shorter write must not have shrunk the set TTL.
        self.assertGreaterEqual(ttl_after_short, ttl_after_long)
        # Sanity: the kept TTL is the longer one (plus the buffer).
        self.assertGreaterEqual(ttl_after_short, 600)

        # And the reverse order must still extend the TTL up to the longer one.
        fake2 = FakeRedis()
        self._write_dto(fake2, _make_dto(serial='RCACHE_TTL2', txn='txn-s', offset_seconds=30))
        self._write_dto(fake2, _make_dto(serial='RCACHE_TTL2', txn='txn-l', offset_seconds=600))
        self.assertGreaterEqual(fake2.ttl('pi:challenge:serial:RCACHE_TTL2'), 600)

    def test_dto_save_updates_cache(self):
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE5', txn='txn-rcache-005')
        self._write_dto(fake, dto)

        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(transaction_id='txn-rcache-005')
            challenge = result[0]
            challenge.set_otp_status(True)
            challenge.save()

            # Re-read from cache — otp_valid must now be True
            updated = get_challenges_from_cache(transaction_id='txn-rcache-005')

        self.assertIsNotNone(updated)
        self.assertTrue(updated[0].otp_valid)
        self.assertEqual(updated[0].received_count, 1)

    def test_dto_save_updates_data_in_cache(self):
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE6', txn='txn-rcache-006')
        self._write_dto(fake, dto)

        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(transaction_id='txn-rcache-006')
            challenge = result[0]
            challenge.set_data({"mode": "push", "display_code": "1234"})
            challenge.save()

            updated = get_challenges_from_cache(transaction_id='txn-rcache-006')

        self.assertEqual(updated[0].get_data(), {"mode": "push", "display_code": "1234"})

    def test_dto_delete_evicts_from_cache(self):
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE7', txn='txn-rcache-007')
        self._write_dto(fake, dto)

        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(transaction_id='txn-rcache-007')
            result[0].delete()
            after_delete = get_challenges_from_cache(transaction_id='txn-rcache-007')

        self.assertIsNone(after_delete)

    def test_cache_and_evict_no_op_when_feature_disabled(self):
        # Both write paths must short-circuit without ever calling into the
        # injected client when the per-feature flag is off.
        from privacyidea.lib.cache import evict_challenge
        fake = FakeRedis()
        with fake_redis_in_store(fake, enable_challenges=False):
            cache_challenge(serial='RCACHE_OFF', transaction_id='txn-off',
                            challenge='c', data='', session='',
                            timestamp=utc_now(), expiration=utc_now() + timedelta(seconds=120))
            evict_challenge('txn-off', 'RCACHE_OFF')
        # Nothing should have been written.
        self.assertEqual(fake._data, {})
        self.assertEqual(fake._sets, {})

    def test_evict_disables_redis_on_error(self):
        from privacyidea.lib.cache import evict_challenge
        fake = FakeRedis()

        def boom(*a, **kw):
            raise ConnectionError("simulated pipeline failure")

        fake.pipeline = boom
        with fake_redis_in_store(fake):
            evict_challenge('txn-err', 'RCACHE_ERR')
            self.assertIsNone(get_redis())

    def test_get_from_cache_disables_redis_on_error(self):
        fake = FakeRedis()

        def boom(*a, **kw):
            raise ConnectionError("simulated get failure")

        fake.get = boom
        with fake_redis_in_store(fake):
            self.assertIsNone(get_challenges_from_cache(transaction_id='whatever'))
            self.assertIsNone(get_redis())

    def test_get_from_cache_filters_by_challenge_value(self):
        # Two challenges on the same serial; query must apply the
        # ``challenge=`` filter and return only the matching one.
        fake = FakeRedis()
        self._write_dto(fake, _make_dto(serial='RCACHE_F', txn='txn-f-1', challenge='alpha'))
        self._write_dto(fake, _make_dto(serial='RCACHE_F', txn='txn-f-2', challenge='beta'))
        with fake_redis_in_store(fake):
            result = get_challenges_from_cache(serial='RCACHE_F', challenge='beta')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, 'txn-f-2')

    def test_dto_save_no_op_when_feature_disabled(self):
        # _update_challenge_in_cache's flag-disabled early return.
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE_SOFF', txn='txn-soff')
        self._write_dto(fake, dto)
        original = fake._data['pi:challenge:txn:txn-soff']
        with fake_redis_in_store(fake, enable_challenges=False):
            cached_dto = ChallengeDTO(
                transaction_id='txn-soff', serial='RCACHE_SOFF',
                challenge='c', data='', session='',
                timestamp=utc_now(), expiration=utc_now() + timedelta(seconds=120),
            )
            cached_dto.set_otp_status(True)
            cached_dto.save()  # must short-circuit; key untouched
        self.assertEqual(fake._data['pi:challenge:txn:txn-soff'], original)

    def test_save_disables_redis_on_error(self):
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE_SAVE_ERR', txn='txn-save-err')
        self._write_dto(fake, dto)

        def boom(*a, **kw):
            raise ConnectionError("simulated setex failure")

        fake.setex = boom
        with fake_redis_in_store(fake):
            cached = get_challenges_from_cache(transaction_id='txn-save-err')[0]
            cached.set_otp_status(True)
            cached.save()  # _update_challenge_in_cache hits boom → _disable_redis
            self.assertIsNone(get_redis())

    def test_evict_for_serial_no_op_when_feature_disabled(self):
        from privacyidea.lib.cache import evict_challenges_for_serial
        fake = FakeRedis()
        with fake_redis_in_store(fake, enable_challenges=False):
            evict_challenges_for_serial('RCACHE_DISABLED')  # must not raise / touch Redis

    def test_evict_for_serial_disables_redis_on_error(self):
        from privacyidea.lib.cache import evict_challenges_for_serial
        fake = FakeRedis()

        def boom(*a, **kw):
            raise ConnectionError("simulated smembers failure")

        fake.smembers = boom

        with fake_redis_in_store(fake):
            evict_challenges_for_serial('RCACHE_BOOM')
            self.assertIsNone(get_redis())

    def test_get_from_cache_returns_none_when_all_keys_expired(self):
        # Serial set has members, but the per-transaction keys have already
        # expired and evaporated → caller must see a cache miss, not an
        # empty success.
        fake = FakeRedis()
        fake._sets['pi:challenge:serial:RCACHE_GHOST'] = {'gone-1', 'gone-2'}
        with fake_redis_in_store(fake):
            self.assertIsNone(get_challenges_from_cache(serial='RCACHE_GHOST'))

    def test_get_from_cache_returns_none_on_corrupt_payload(self):
        fake = FakeRedis()
        fake._data['pi:challenge:txn:txn-corrupt'] = '{"not": "a valid challenge"'  # truncated JSON
        with fake_redis_in_store(fake):
            self.assertIsNone(get_challenges_from_cache(transaction_id='txn-corrupt'))

    def test_save_short_circuits_when_already_expired(self):
        fake = FakeRedis()
        dto = _make_dto(serial='RCACHE_EXP', txn='txn-rcache-exp', offset_seconds=120)
        self._write_dto(fake, dto)
        with fake_redis_in_store(fake):
            cached = get_challenges_from_cache(transaction_id='txn-rcache-exp')[0]
            # Force the DTO into the past so _update_challenge_in_cache hits
            # the "already expired" early return without re-writing the key.
            # Push expiration past the TTL buffer so the early-return fires.
            cached.expiration = utc_now() - timedelta(seconds=120)
            existing_payload = fake._data['pi:challenge:txn:txn-rcache-exp']
            cached.set_otp_status(True)
            cached.save()
        # Key must be unchanged — the save() should not have re-written an
        # already-expired challenge.
        self.assertEqual(fake._data['pi:challenge:txn:txn-rcache-exp'], existing_payload)

    def test_redis_disabled_on_operation_error(self):
        """If a Redis operation raises, the client must be disabled for this worker."""
        fake = FakeRedis()

        def boom(*a, **kw):
            raise ConnectionError("simulated mid-flight failure")

        fake.setex = boom

        with fake_redis_in_store(fake):
            # cache_challenge internally calls pipeline → setex → boom → _disable_redis
            dto = _make_dto(serial='RCACHE8', txn='txn-rcache-008')
            cache_challenge(
                serial=dto.serial,
                transaction_id=dto.transaction_id,
                challenge=dto.challenge,
                data=dto.data,
                session=dto.session,
                timestamp=dto.timestamp,
                expiration=dto.expiration,
            )
            # After the failure, get_redis() must return None
            self.assertIsNone(get_redis())


class TestCreateChallengeIntegration(MyTestCase):
    """
    Test create_challenge() and get_challenges() end-to-end.
    The same assertions run for both the Redis path (DTO) and the DB path,
    proving that callers are truly transparent to the backend.
    """

    serial = 'SE_INTG_CHAL'

    def setUp(self):
        super().setUp()
        self._token = init_token({"genkey": 1, "serial": self.serial, "pin": "pin"})
        # Clean up any leftover challenges
        Challenge.query.filter_by(serial=self.serial).delete()
        db.session.commit()

    def tearDown(self):
        Challenge.query.filter_by(serial=self.serial).delete()
        db.session.commit()
        super().tearDown()

    def _assert_challenge_readable(self, txn_id: str, fake: FakeRedis | None):
        """Shared assertions for both backends."""
        with fake_redis_in_store(fake):
            # lookup by transaction_id
            by_txn = get_challenges(serial=self.serial, transaction_id=txn_id)
            self.assertEqual(len(by_txn), 1)
            self.assertEqual(by_txn[0].transaction_id, txn_id)
            self.assertEqual(by_txn[0].serial, self.serial)
            self.assertTrue(by_txn[0].is_valid())

            # lookup by serial
            by_serial = get_challenges(serial=self.serial)
            txn_ids = [c.transaction_id for c in by_serial]
            self.assertIn(txn_id, txn_ids)

    def test_create_challenge_db_path(self):
        """With no Redis, challenge must be persisted to the DB."""
        with fake_redis_in_store(None):
            ch = create_challenge(self.serial, challenge='testchallenge', validitytime=120)
            txn_id = ch.transaction_id

        # DB row must exist
        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNotNone(row)

        self._assert_challenge_readable(txn_id, None)

    def test_create_challenge_redis_path(self):
        """With Redis available, challenge is stored in cache only — no DB row."""
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            ch = create_challenge(self.serial, challenge='testchallenge', validitytime=120)
            txn_id = ch.transaction_id

        # No DB row should exist
        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNone(row, "Challenge must NOT be written to DB when Redis is available")

        self._assert_challenge_readable(txn_id, fake)

    def test_create_challenge_flag_disabled_writes_to_db(self):
        """
        With Redis reachable but PI_REDIS_CACHE_CHALLENGES off, create_challenge()
        must write through to the DB and skip the cache entirely.
        """
        fake = FakeRedis()
        with fake_redis_in_store(fake, enable_challenges=False):
            ch = create_challenge(self.serial, challenge='flag_off', validitytime=120)
            txn_id = ch.transaction_id

        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNotNone(row, "Challenge must be written to DB when feature flag is off")
        # And nothing should have been written to Redis
        self.assertEqual(len(fake._data), 0,
                         "No keys should exist in Redis when feature flag is off")

    def test_get_challenges_flag_disabled_reads_from_db(self):
        """
        Even if a stale key happens to be in Redis, get_challenges() must skip
        the cache and serve from the DB when the feature flag is off.
        """
        ch = Challenge(self.serial, transaction_id=None, challenge='db_only',
                       data='', session='', validitytime=120)
        ch.save()
        txn_id = ch.transaction_id

        fake = FakeRedis()
        with fake_redis_in_store(fake, enable_challenges=False):
            result = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, txn_id)
        # Confirm the DB type came back, not a DTO
        self.assertIsInstance(result[0], Challenge)

    def test_create_challenge_redis_fallback_to_db_on_write_failure(self):
        """If cache_challenge() fails, create_challenge() must fall back to DB."""
        fake = FakeRedis()

        def boom(*a, **kw):
            raise ConnectionError("fake write failure")

        fake.setex = boom

        with fake_redis_in_store(fake):
            ch = create_challenge(self.serial, challenge='failover', validitytime=120)
            txn_id = ch.transaction_id

        # Redis was disabled; challenge must have been saved to DB
        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNotNone(row, "Challenge must fall back to DB when Redis write fails")

    def test_get_challenges_falls_back_to_db_on_cache_miss(self):
        """
        If a transaction_id is not in Redis (e.g. challenge was created before
        Redis was enabled), get_challenges() must fall back to the DB.
        """
        # Write directly to DB, bypassing cache
        ch = Challenge(self.serial, transaction_id=None, challenge='db_only',
                       data='', session='', validitytime=120)
        ch.save()
        txn_id = ch.transaction_id

        # Empty fake Redis — the key won't be there
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            result = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, txn_id)

    def test_otp_status_update_survives_roundtrip_redis(self):
        """set_otp_status + save must be visible on the next get_challenges call."""
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            ch = create_challenge(self.serial, challenge='roundtrip', validitytime=120)
            txn_id = ch.transaction_id

            challenges = get_challenges(serial=self.serial, transaction_id=txn_id)
            self.assertEqual(len(challenges), 1)
            challenges[0].set_otp_status(True)
            challenges[0].save()

            updated = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertTrue(updated[0].otp_valid)
        self.assertEqual(updated[0].received_count, 1)

    def test_otp_status_update_survives_roundtrip_db(self):
        """Same as above but with DB path (no Redis)."""
        with fake_redis_in_store(None):
            ch = create_challenge(self.serial, challenge='roundtrip_db', validitytime=120)
            txn_id = ch.transaction_id

            challenges = get_challenges(serial=self.serial, transaction_id=txn_id)
            self.assertEqual(len(challenges), 1)
            challenges[0].set_otp_status(True)
            challenges[0].save()

            updated = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertTrue(updated[0].otp_valid)

    def test_delete_challenge_redis(self):
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            ch = create_challenge(self.serial, challenge='to_delete', validitytime=120)
            txn_id = ch.transaction_id

            challenges = get_challenges(serial=self.serial, transaction_id=txn_id)
            challenges[0].delete()

            after = get_challenges(serial=self.serial, transaction_id=txn_id)

        # Cache miss → falls back to DB → also nothing there
        self.assertEqual(len(after), 0)

    def test_multiple_challenges_same_serial_redis(self):
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            ch1 = create_challenge(self.serial, challenge='c1', validitytime=120)
            ch2 = create_challenge(self.serial, challenge='c2', validitytime=120)

            result = get_challenges(serial=self.serial)

        txn_ids = {c.transaction_id for c in result}
        self.assertIn(ch1.transaction_id, txn_ids)
        self.assertIn(ch2.transaction_id, txn_ids)

    def test_get_challenges_paginate_by_serial_redis(self):
        """get_challenges_paginate filtered by serial must be served from Redis."""
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            ch1 = create_challenge(self.serial, challenge='p1', validitytime=120)
            ch2 = create_challenge(self.serial, challenge='p2', validitytime=120)

            result = get_challenges_paginate(serial=self.serial)

        self.assertEqual(result['count'], 2)
        txn_ids = {c['transaction_id'] for c in result['challenges']}
        self.assertIn(ch1.transaction_id, txn_ids)
        self.assertIn(ch2.transaction_id, txn_ids)
        # No DB rows — unfiltered DB query would return 0
        self.assertEqual(Challenge.query.filter_by(serial=self.serial).count(), 0)

    def test_get_challenges_paginate_by_txn_redis(self):
        """get_challenges_paginate filtered by transaction_id must be served from Redis."""
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            ch = create_challenge(self.serial, challenge='p_txn', validitytime=120)
            txn_id = ch.transaction_id

            result = get_challenges_paginate(transaction_id=txn_id)

        self.assertEqual(result['count'], 1)
        self.assertEqual(result['challenges'][0]['transaction_id'], txn_id)

    def test_paginate_falls_back_to_natural_order_on_unsortable_field(self):
        # Sorting by a field whose value is None on some entries (here:
        # `session` is empty for one challenge and a string for another)
        # raises TypeError under Python 3 comparisons. The paginator must
        # swallow the TypeError and return results in natural order rather
        # than failing the request.
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            ch1 = create_challenge(self.serial, challenge='ord1', session='b', validitytime=120)
            ch2 = create_challenge(self.serial, challenge='ord2', validitytime=120)
            # Mutate one DTO's session to None to provoke the comparator failure.
            cached = get_challenges_from_cache(serial=self.serial)
            for c in cached:
                if c.transaction_id == ch2.transaction_id:
                    c.session = None
                    c.save()
            result = get_challenges_paginate(serial=self.serial, sortby='session')

        self.assertEqual(result['count'], 2)
        returned = {c['transaction_id'] for c in result['challenges']}
        self.assertEqual(returned, {ch1.transaction_id, ch2.transaction_id})

    def test_get_challenges_paginate_unfiltered_empty_with_redis(self):
        """Unfiltered paginate always queries the DB — empty when Redis is active."""
        fake = FakeRedis()
        with fake_redis_in_store(fake):
            create_challenge(self.serial, challenge='p_nofilt', validitytime=120)
            result = get_challenges_paginate()  # no serial, no txn_id

        # DB has no rows, so result is empty
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['challenges'], [])


# Real-Redis integration tests — skipped when TEST_REDIS_URL is not set.
_TEST_REDIS_URL = os.environ.get('TEST_REDIS_URL')


@pytest.mark.skipif(not _TEST_REDIS_URL, reason="TEST_REDIS_URL not set — no Redis server available")
class TestRealRedisIntegration(MyTestCase):
    """
    Runs a subset of the integration tests against a real Redis instance.
    This catches issues that the in-memory fake cannot: serialisation edge
    cases, pipeline behaviour, actual TTL handling, connection lifecycle, etc.
    """

    serial = 'SE_REAL_REDIS'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import redis as redis_lib
        # Verify the server is reachable before the whole class runs.
        try:
            client = redis_lib.Redis.from_url(_TEST_REDIS_URL, decode_responses=True,
                                              socket_connect_timeout=2, socket_timeout=2)
            client.ping()
        except Exception as e:
            raise unittest.SkipTest(f"Redis not reachable at {_TEST_REDIS_URL}: {e}")
        cls._real_client = client

    def setUp(self):
        super().setUp()
        self._token = init_token({"genkey": 1, "serial": self.serial, "pin": "pin"})
        Challenge.query.filter_by(serial=self.serial).delete()
        db.session.commit()
        # Flush any leftover keys from previous runs
        self._real_client.delete(
            f"pi:challenge:serial:{self.serial}",
        )

    def tearDown(self):
        Challenge.query.filter_by(serial=self.serial).delete()
        db.session.commit()
        super().tearDown()

    @contextmanager
    def _real_redis(self):
        """Inject the real Redis client into the app-local store."""
        with fake_redis_in_store(self._real_client):
            yield

    def test_create_and_read_challenge(self):
        with self._real_redis():
            ch = create_challenge(self.serial, challenge='real_redis_test', validitytime=120)
            txn_id = ch.transaction_id

            # Must be readable from cache
            by_txn = get_challenges(serial=self.serial, transaction_id=txn_id)
            self.assertEqual(len(by_txn), 1)
            self.assertEqual(by_txn[0].transaction_id, txn_id)
            self.assertTrue(by_txn[0].is_valid())

        # Must NOT be in the DB (Redis-only path)
        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNone(row)

    def test_otp_status_roundtrip(self):
        with self._real_redis():
            ch = create_challenge(self.serial, challenge='otp_roundtrip', validitytime=120)
            txn_id = ch.transaction_id

            challenges = get_challenges(serial=self.serial, transaction_id=txn_id)
            challenges[0].set_otp_status(True)
            challenges[0].save()

            updated = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertTrue(updated[0].otp_valid)
        self.assertEqual(updated[0].received_count, 1)

    def test_set_data_roundtrip(self):
        with self._real_redis():
            ch = create_challenge(self.serial, challenge='data_roundtrip', validitytime=120)
            txn_id = ch.transaction_id

            challenges = get_challenges(serial=self.serial, transaction_id=txn_id)
            challenges[0].set_data({"mode": "push", "display_code": "9876"})
            challenges[0].save()

            updated = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertEqual(updated[0].get_data(), {"mode": "push", "display_code": "9876"})

    def test_delete_challenge(self):
        with self._real_redis():
            ch = create_challenge(self.serial, challenge='to_delete', validitytime=120)
            txn_id = ch.transaction_id

            challenges = get_challenges(serial=self.serial, transaction_id=txn_id)
            challenges[0].delete()

            after = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertEqual(len(after), 0)

    def test_multiple_challenges_same_serial(self):
        with self._real_redis():
            ch1 = create_challenge(self.serial, challenge='c1', validitytime=120)
            ch2 = create_challenge(self.serial, challenge='c2', validitytime=120)

            result = get_challenges(serial=self.serial)

        txn_ids = {c.transaction_id for c in result}
        self.assertIn(ch1.transaction_id, txn_ids)
        self.assertIn(ch2.transaction_id, txn_ids)

    def test_cache_miss_falls_back_to_db(self):
        """Challenge in DB but not in Redis must still be found via get_challenges()."""
        ch = Challenge(self.serial, transaction_id=None, challenge='db_only',
                       data='', session='', validitytime=120)
        ch.save()
        txn_id = ch.transaction_id

        with self._real_redis():
            result = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, txn_id)

    def test_cancel_enrollment_via_multichallenge_no_attribute_error(self):
        """Regression: cancel_enrollment_via_multichallenge() used to log
        challenge.id, which doesn't exist on Redis-backed ChallengeDTOs and
        raised AttributeError instead of returning False on the early-out
        log paths."""
        from privacyidea.lib.challenge import cancel_enrollment_via_multichallenge
        with self._real_redis():
            # No data on the challenge — hits the "No data found" log/return path.
            ch = create_challenge(self.serial, challenge='no_data', validitytime=120)
            self.assertFalse(cancel_enrollment_via_multichallenge(ch.transaction_id))

            # Data present but optional flag is False — hits the
            # "does not have the action ... set to True" log/return path.
            ch2 = create_challenge(self.serial, challenge='opt_false', validitytime=120,
                                   data={
                                       PolicyAction.ENROLL_VIA_MULTICHALLENGE: "HOTP",
                                       PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL: False,
                                   })
            self.assertFalse(cancel_enrollment_via_multichallenge(ch2.transaction_id))

    def test_remove_token_evicts_redis_challenges(self):
        """Regression: deleting a token must drop its Redis-cached challenges
        so transaction IDs cannot keep resolving until TTL expiry."""
        serial = 'SE_REAL_REDIS_LIFECYCLE'
        init_token({"genkey": 1, "serial": serial, "pin": "pin"})
        try:
            with self._real_redis():
                ch = create_challenge(serial, challenge='will_be_orphaned', validitytime=600)
                txn_id = ch.transaction_id
                # Sanity: transaction is resolvable from the cache pre-deletion.
                self.assertEqual(len(get_challenges(serial=serial, transaction_id=txn_id)), 1)

                remove_token(serial)

                # Both the per-transaction key and the serial set must be gone.
                self.assertIsNone(self._real_client.get(f"pi:challenge:txn:{txn_id}"))
                self.assertEqual(self._real_client.smembers(f"pi:challenge:serial:{serial}"), set())
        finally:
            # remove_token() above is the cleanup; nothing left to do.
            Challenge.query.filter_by(serial=serial).delete()
            db.session.commit()

    def test_serial_set_ttl_not_shrunk_by_shorter_challenge(self):
        """Regression: shorter-lived challenge must not shrink the shared serial-set TTL."""
        serial_key = f"pi:challenge:serial:{self.serial}"
        with self._real_redis():
            create_challenge(self.serial, challenge='long_lived', validitytime=600)
            ttl_after_long = self._real_client.ttl(serial_key)
            self.assertGreaterEqual(ttl_after_long, 600)

            create_challenge(self.serial, challenge='short_lived', validitytime=30)
            ttl_after_short = self._real_client.ttl(serial_key)

        # Set TTL must not have been pulled down to ~30s by the shorter write.
        self.assertGreaterEqual(ttl_after_short, ttl_after_long - 5)
        self.assertGreater(ttl_after_short, 60)
