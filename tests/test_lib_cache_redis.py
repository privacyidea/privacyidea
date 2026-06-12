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

All cache-behavior tests run against a real Redis instance. The runtime
contract (TTL semantics, EXPIRE NX/GT, pipeline atomicity, decode_responses)
is too subtle to reproduce faithfully with a hand-rolled mock - a real
backend catches the bugs hand-rolled fakes silently mask.

Local DX: ``tests/conftest.py`` probes ``127.0.0.1:6379`` and auto-exports
``TEST_REDIS_URL`` when reachable, so ``docker compose -f compose-dev.yml up -d redis``
is the only step a developer needs. CI workflows export the URL explicitly
against a Redis 7 service container.

Tests that don't need Redis at all (pure DTO unit tests, the protocol
contract check, the version-gate behaviour) run unconditionally.
"""
import os
import unittest
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

import pytest
import redis as redis_lib

from .base import MyTestCase
from privacyidea.lib.cache.redis import (
    ChallengeDTO,
    cache_challenge,
    evict_challenge,
    get_challenges_from_cache,
    get_redis,
)
from privacyidea.lib.challenge import get_challenges, get_challenges_paginate
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.token import create_challenge, init_token, remove_token
from privacyidea.models import Challenge, db
from privacyidea.models.utils import utc_now


_TEST_REDIS_URL = os.environ.get('TEST_REDIS_URL')


# -----------------------------------------------------------------------------
# Test infrastructure
# -----------------------------------------------------------------------------


@contextmanager
def redis_in_store(client, enable_challenges: bool = True):
    """
    Inject *client* (or ``None``) into the app-local store so ``get_redis()``
    returns it without re-running the connect path, and set the per-feature
    cache flag so callers actually exercise the cache. Cleans up on exit.

    Pass ``None`` to simulate a worker with no Redis configured at all.
    """
    import os
    from flask import current_app
    store = get_app_local_store()
    had_client = '_redis_client_entry' in store
    old_client = store.get('_redis_client_entry')

    # Match the (pid, client) shape get_redis() now uses. client=None
    # simulates "no Redis configured" and stores no entry.
    if client is None:
        store.pop('_redis_client_entry', None)
    else:
        store['_redis_client_entry'] = (os.getpid(), client)

    flag_key = 'PI_REDIS_CACHE_CHALLENGES'
    url_key = 'PI_REDIS_URL'
    had_flag = flag_key in current_app.config
    had_url = url_key in current_app.config
    old_flag = current_app.config.get(flag_key)
    old_url = current_app.config.get(url_key)
    current_app.config[flag_key] = enable_challenges
    # When a client is given we also stub a URL so the config looks
    # consistent. When the caller passes ``None`` they want to simulate
    # "no Redis at all", so drop the URL too - otherwise ``get_redis()``
    # would try to connect via the URL and produce a live client,
    # defeating the test setup.
    if client is None:
        current_app.config.pop(url_key, None)
    else:
        current_app.config[url_key] = _TEST_REDIS_URL or "redis://stub:6379/0"
    try:
        yield client
    finally:
        if had_client:
            store['_redis_client_entry'] = old_client
        else:
            store.pop('_redis_client_entry', None)
        # Tests that trip _disable_redis or fail a probe set
        # _redis_retry_after - clear it so the cooldown doesn't leak into
        # unrelated tests in the same session.
        store.pop('_redis_retry_after', None)
        if had_flag:
            current_app.config[flag_key] = old_flag
        else:
            current_app.config.pop(flag_key, None)
        if had_url:
            current_app.config[url_key] = old_url
        else:
            current_app.config.pop(url_key, None)


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


@pytest.mark.skipif(not _TEST_REDIS_URL,
                    reason="TEST_REDIS_URL not set - start compose-dev's Redis or export the env var")
class _RealRedisBase(MyTestCase):
    """
    Shared base for tests that need a real Redis client.

    Connects once per class to ``TEST_REDIS_URL``; flushes all ``pi:challenge:*``
    keys before each test so tests can rely on a clean cache without
    interfering with each other.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import redis as redis_lib
        try:
            client = redis_lib.Redis.from_url(_TEST_REDIS_URL, decode_responses=True,
                                              socket_connect_timeout=2, socket_timeout=2)
            client.ping()
        except Exception as e:
            raise unittest.SkipTest(f"Redis not reachable at {_TEST_REDIS_URL}: {e}")
        cls._real_client = client

    def setUp(self):
        super().setUp()
        self._flush_cache()

    def tearDown(self):
        self._flush_cache()
        super().tearDown()

    def _flush_cache(self):
        """Delete every pi:challenge:* key the cache uses. Cheaper than FLUSHDB
        and doesn't disturb anything else sharing the Redis instance."""
        client = type(self)._real_client
        keys = list(client.scan_iter(match="pi:challenge:*"))
        if keys:
            client.delete(*keys)


# -----------------------------------------------------------------------------
# Pure DTO unit tests (no Redis needed)
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# Cache primitive behavior (against real Redis)
# -----------------------------------------------------------------------------


class TestRedisCacheOperations(_RealRedisBase):

    def _write_dto(self, dto: ChallengeDTO):
        with redis_in_store(self._real_client):
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
        dto = _make_dto(serial='RCACHE1', txn='txn-rcache-001')
        self._write_dto(dto)
        with redis_in_store(self._real_client):
            result = get_challenges_from_cache(transaction_id='txn-rcache-001')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, 'txn-rcache-001')
        self.assertEqual(result[0].serial, 'RCACHE1')
        self.assertEqual(result[0].challenge, 'abc')

    def test_cache_then_read_by_serial(self):
        dto = _make_dto(serial='RCACHE2', txn='txn-rcache-002')
        self._write_dto(dto)
        with redis_in_store(self._real_client):
            result = get_challenges_from_cache(serial='RCACHE2')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].serial, 'RCACHE2')

    def test_cache_miss_by_txn_returns_miss(self):
        """Cache reachable, key absent -> CacheState.MISS (authoritative-empty)."""
        from privacyidea.lib.cache import CacheState
        with redis_in_store(self._real_client):
            result = get_challenges_from_cache(transaction_id='nonexistent-txn')
        self.assertIs(result, CacheState.MISS)

    def test_cache_miss_by_serial_returns_miss(self):
        """Serial set not present -> MISS (cache speaks for the negative)."""
        from privacyidea.lib.cache import CacheState
        with redis_in_store(self._real_client):
            result = get_challenges_from_cache(serial='NOSUCHSERIAL')
        self.assertIs(result, CacheState.MISS)

    def test_no_redis_returns_unavailable(self):
        """Client absent -> UNAVAILABLE (can't speak for the cache state)."""
        from privacyidea.lib.cache import CacheState
        with redis_in_store(None):
            result = get_challenges_from_cache(serial='WHATEVER')
        self.assertIs(result, CacheState.UNAVAILABLE)

    def test_unfiltered_query_returns_unavailable(self):
        """Unfiltered list-all can't be served from a key-value store, so it
        returns UNAVAILABLE and the caller falls back to the DB. The admin
        aggregate 'list all challenges' view is intentionally degraded under
        the cache (the WebUI shows a banner); per-serial/per-txn lookups work."""
        from privacyidea.lib.cache import CacheState
        self._write_dto(_make_dto(serial='RENUM_A', txn='txn-enum-a'))
        self._write_dto(_make_dto(serial='RENUM_B', txn='txn-enum-b'))
        with redis_in_store(self._real_client):
            self.assertIs(get_challenges_from_cache(), CacheState.UNAVAILABLE)

    def test_evict_removes_from_cache(self):
        from privacyidea.lib.cache import CacheState
        dto = _make_dto(serial='RCACHE3', txn='txn-rcache-003')
        self._write_dto(dto)
        with redis_in_store(self._real_client):
            evict_challenge('txn-rcache-003', 'RCACHE3')
            result = get_challenges_from_cache(transaction_id='txn-rcache-003')
        self.assertIs(result, CacheState.MISS)

    def test_multiple_challenges_same_serial(self):
        self._write_dto(_make_dto(serial='RCACHE4', txn='txn-rcache-004a'))
        self._write_dto(_make_dto(serial='RCACHE4', txn='txn-rcache-004b'))
        with redis_in_store(self._real_client):
            result = get_challenges_from_cache(serial='RCACHE4')
        self.assertEqual(len(result), 2)
        self.assertEqual({c.transaction_id for c in result},
                         {'txn-rcache-004a', 'txn-rcache-004b'})

    def test_multiple_challenges_same_transaction(self):
        """Regression: several tokens triggered in one authentication share a
        single transaction_id (one challenge per token). Each must keep its own
        payload - the second token's challenge must not overwrite the first.
        The txn hash holds one field per serial; both query shapes must see
        both challenges."""
        self._write_dto(_make_dto(serial='RTXN_A', txn='txn-shared', challenge='chal-a'))
        self._write_dto(_make_dto(serial='RTXN_B', txn='txn-shared', challenge='chal-b'))
        with redis_in_store(self._real_client):
            # By transaction_id: both tokens' challenges.
            by_txn = get_challenges_from_cache(transaction_id='txn-shared')
            # By (serial, transaction_id): only that token's challenge.
            a_only = get_challenges_from_cache(serial='RTXN_A', transaction_id='txn-shared')
            b_only = get_challenges_from_cache(serial='RTXN_B', transaction_id='txn-shared')
            # By serial alone: that token's challenge across its transactions.
            by_serial_a = get_challenges_from_cache(serial='RTXN_A')
        self.assertEqual({c.serial for c in by_txn}, {'RTXN_A', 'RTXN_B'})
        self.assertEqual({c.challenge for c in by_txn}, {'chal-a', 'chal-b'})
        self.assertEqual([c.serial for c in a_only], ['RTXN_A'])
        self.assertEqual([c.challenge for c in a_only], ['chal-a'])
        self.assertEqual([c.serial for c in b_only], ['RTXN_B'])
        self.assertEqual([c.challenge for c in by_serial_a], ['chal-a'])

    def test_evict_one_challenge_keeps_transaction_siblings(self):
        """Evicting one token's challenge from a shared transaction must leave
        the sibling tokens' challenges intact (deleting one token does not
        cancel another's in-flight challenge)."""
        from privacyidea.lib.cache import CacheState
        self._write_dto(_make_dto(serial='RTXN_C', txn='txn-sib', challenge='c-c'))
        self._write_dto(_make_dto(serial='RTXN_D', txn='txn-sib', challenge='c-d'))
        with redis_in_store(self._real_client):
            evict_challenge('txn-sib', 'RTXN_C')
            remaining = get_challenges_from_cache(transaction_id='txn-sib')
            gone = get_challenges_from_cache(serial='RTXN_C')
        self.assertEqual([c.serial for c in remaining], ['RTXN_D'])
        self.assertIs(gone, CacheState.MISS)

    def test_evict_for_serial_keeps_transaction_siblings(self):
        """Deleting a token (evict_challenges_for_serial) must remove only that
        token's field from each shared transaction, not the whole hash."""
        from privacyidea.lib.cache import evict_challenges_for_serial
        self._write_dto(_make_dto(serial='RTXN_E', txn='txn-del', challenge='c-e'))
        self._write_dto(_make_dto(serial='RTXN_F', txn='txn-del', challenge='c-f'))
        with redis_in_store(self._real_client):
            evict_challenges_for_serial('RTXN_E')
            remaining = get_challenges_from_cache(transaction_id='txn-del')
        self.assertEqual([c.serial for c in remaining], ['RTXN_F'])
        self.assertEqual(self._real_client.smembers('pi:challenge:serial:RTXN_E'), set())

    def test_serial_set_ttl_not_shrunk_by_shorter_challenge(self):
        """Writing a shorter-lived challenge after a longer-lived one for the
        same serial must not shrink the shared serial-set TTL. EXPIRE NX + GT
        guarantees the TTL only grows."""
        self._write_dto(_make_dto(serial='RCACHE_TTL', txn='txn-long', offset_seconds=600))
        ttl_after_long = self._real_client.ttl('pi:challenge:serial:RCACHE_TTL')
        self.assertGreaterEqual(ttl_after_long, 600)

        self._write_dto(_make_dto(serial='RCACHE_TTL', txn='txn-short', offset_seconds=30))
        ttl_after_short = self._real_client.ttl('pi:challenge:serial:RCACHE_TTL')

        # The shorter write must not have shrunk the set TTL.
        self.assertGreaterEqual(ttl_after_short, ttl_after_long - 5)
        self.assertGreater(ttl_after_short, 60)

        # Reverse order must still extend up to the longer one.
        self._write_dto(_make_dto(serial='RCACHE_TTL2', txn='txn-s', offset_seconds=30))
        self._write_dto(_make_dto(serial='RCACHE_TTL2', txn='txn-l', offset_seconds=600))
        self.assertGreaterEqual(self._real_client.ttl('pi:challenge:serial:RCACHE_TTL2'), 600)

    def test_dto_save_updates_cache(self):
        dto = _make_dto(serial='RCACHE5', txn='txn-rcache-005')
        self._write_dto(dto)
        with redis_in_store(self._real_client):
            challenge = get_challenges_from_cache(transaction_id='txn-rcache-005')[0]
            challenge.set_otp_status(True)
            challenge.save()
            updated = get_challenges_from_cache(transaction_id='txn-rcache-005')
        self.assertTrue(updated[0].otp_valid)
        self.assertEqual(updated[0].received_count, 1)

    def test_dto_save_updates_data_in_cache(self):
        dto = _make_dto(serial='RCACHE6', txn='txn-rcache-006')
        self._write_dto(dto)
        with redis_in_store(self._real_client):
            challenge = get_challenges_from_cache(transaction_id='txn-rcache-006')[0]
            challenge.set_data({"mode": "push", "display_code": "1234"})
            challenge.save()
            updated = get_challenges_from_cache(transaction_id='txn-rcache-006')
        self.assertEqual(updated[0].get_data(), {"mode": "push", "display_code": "1234"})

    def test_dto_delete_evicts_from_cache(self):
        from privacyidea.lib.cache import CacheState
        dto = _make_dto(serial='RCACHE7', txn='txn-rcache-007')
        self._write_dto(dto)
        with redis_in_store(self._real_client):
            result = get_challenges_from_cache(transaction_id='txn-rcache-007')
            result[0].delete()
            after_delete = get_challenges_from_cache(transaction_id='txn-rcache-007')
        self.assertIs(after_delete, CacheState.MISS)

    def test_cache_and_evict_no_op_when_feature_disabled(self):
        """Both write paths must short-circuit without touching Redis when
        the per-feature flag is off."""
        with redis_in_store(self._real_client, enable_challenges=False):
            cache_challenge(serial='RCACHE_OFF', transaction_id='txn-off',
                            challenge='c', data='', session='',
                            timestamp=utc_now(), expiration=utc_now() + timedelta(seconds=120))
            evict_challenge('txn-off', 'RCACHE_OFF')
        # Nothing should have been written.
        self.assertIsNone(self._real_client.get('pi:challenge:txn:txn-off'))
        self.assertEqual(self._real_client.smembers('pi:challenge:serial:RCACHE_OFF'), set())

    def test_evict_disables_redis_on_error(self):
        with redis_in_store(self._real_client):
            with patch.object(self._real_client, 'pipeline',
                              side_effect=redis_lib.exceptions.ConnectionError("simulated pipeline failure")):
                evict_challenge('txn-err', 'RCACHE_ERR')
            self.assertIsNone(get_redis())

    def test_get_from_cache_disables_redis_on_error(self):
        from privacyidea.lib.cache import CacheState
        with redis_in_store(self._real_client):
            with patch.object(self._real_client, 'hgetall',
                              side_effect=redis_lib.exceptions.ConnectionError("simulated hgetall failure")):
                self.assertIs(get_challenges_from_cache(transaction_id='whatever'),
                              CacheState.UNAVAILABLE)
            self.assertIsNone(get_redis())

    def test_empty_serial_does_not_create_shared_set(self):
        """Usernameless passkey auth init writes challenges with serial="".
        Those must NOT all be funneled into the single shared key
        ``pi:challenge:serial:``, otherwise its membership grows unbounded
        across the worker lifetime and its TTL never settles. They are
        only ever fetched by transaction_id, so the set is pointless."""
        with redis_in_store(self._real_client):
            cache_challenge(serial='', transaction_id='txn-empty-1', challenge='c1',
                            data='', session='',
                            timestamp=utc_now(), expiration=utc_now() + timedelta(seconds=120))
            cache_challenge(serial='', transaction_id='txn-empty-2', challenge='c2',
                            data='', session='',
                            timestamp=utc_now(), expiration=utc_now() + timedelta(seconds=120))

        # Per-transaction hashes must exist (the challenge lives under field
        # "" for the empty serial), but the shared serial set must not.
        self.assertTrue(self._real_client.exists('pi:challenge:txn:txn-empty-1'))
        self.assertTrue(self._real_client.exists('pi:challenge:txn:txn-empty-2'))
        self.assertEqual(self._real_client.smembers('pi:challenge:serial:'), set())

        # And txn-keyed retrieval must still work for both.
        with redis_in_store(self._real_client):
            self.assertEqual(len(get_challenges_from_cache(transaction_id='txn-empty-1')), 1)
            self.assertEqual(len(get_challenges_from_cache(transaction_id='txn-empty-2')), 1)

    def test_evict_with_empty_serial(self):
        """evict_challenge() must tolerate serial="" too - there is no set to
        SREM from, but the txn hash field (and thus the now-empty hash) must
        still go."""
        with redis_in_store(self._real_client):
            cache_challenge(serial='', transaction_id='txn-evict-empty', challenge='c',
                            data='', session='',
                            timestamp=utc_now(), expiration=utc_now() + timedelta(seconds=120))
            self.assertTrue(self._real_client.exists('pi:challenge:txn:txn-evict-empty'))
            evict_challenge('txn-evict-empty', '')
        self.assertFalse(self._real_client.exists('pi:challenge:txn:txn-evict-empty'))

    def test_get_from_cache_filters_by_challenge_value(self):
        """Two challenges on the same serial; query must apply the
        ``challenge=`` filter and return only the matching one."""
        self._write_dto(_make_dto(serial='RCACHE_F', txn='txn-f-1', challenge='alpha'))
        self._write_dto(_make_dto(serial='RCACHE_F', txn='txn-f-2', challenge='beta'))
        with redis_in_store(self._real_client):
            result = get_challenges_from_cache(serial='RCACHE_F', challenge='beta')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, 'txn-f-2')

    def test_dto_save_no_op_when_feature_disabled(self):
        """_update_challenge_in_cache's flag-disabled early return."""
        dto = _make_dto(serial='RCACHE_SOFF', txn='txn-soff')
        self._write_dto(dto)
        original = self._real_client.hget('pi:challenge:txn:txn-soff', 'RCACHE_SOFF')
        with redis_in_store(self._real_client, enable_challenges=False):
            cached_dto = ChallengeDTO(
                transaction_id='txn-soff', serial='RCACHE_SOFF',
                challenge='c', data='', session='',
                timestamp=utc_now(), expiration=utc_now() + timedelta(seconds=120),
            )
            cached_dto.set_otp_status(True)
            cached_dto.save()  # must short-circuit; field untouched
        self.assertEqual(self._real_client.hget('pi:challenge:txn:txn-soff', 'RCACHE_SOFF'), original)

    def test_save_disables_redis_on_error(self):
        dto = _make_dto(serial='RCACHE_SAVE_ERR', txn='txn-save-err')
        self._write_dto(dto)
        with redis_in_store(self._real_client):
            cached = get_challenges_from_cache(transaction_id='txn-save-err')[0]
            cached.set_otp_status(True)
            with patch.object(self._real_client, 'pipeline',
                              side_effect=redis_lib.exceptions.ConnectionError("simulated setex failure")):
                cached.save()
            self.assertIsNone(get_redis())

    def test_evict_for_serial_no_op_when_feature_disabled(self):
        from privacyidea.lib.cache import evict_challenges_for_serial
        with redis_in_store(self._real_client, enable_challenges=False):
            evict_challenges_for_serial('RCACHE_DISABLED')  # must not raise / touch Redis

    def test_evict_for_serial_disables_redis_on_error(self):
        from privacyidea.lib.cache import evict_challenges_for_serial
        with redis_in_store(self._real_client):
            with patch.object(self._real_client, 'smembers',
                              side_effect=redis_lib.exceptions.ConnectionError("simulated smembers failure")):
                evict_challenges_for_serial('RCACHE_BOOM')
            self.assertIsNone(get_redis())

    def test_get_from_cache_returns_unavailable_when_all_keys_expired(self):
        """Serial set has members, but the per-transaction keys have already
        expired individually. The cache no longer has authoritative state
        for this serial -> UNAVAILABLE so the caller falls back to the DB
        rather than treating the absence as authoritative-empty."""
        from privacyidea.lib.cache import CacheState
        # Manually plant a serial set whose members have no backing txn keys.
        self._real_client.sadd('pi:challenge:serial:RCACHE_GHOST', 'gone-1', 'gone-2')
        with redis_in_store(self._real_client):
            result = get_challenges_from_cache(serial='RCACHE_GHOST')
        self.assertIs(result, CacheState.UNAVAILABLE)

    def test_get_from_cache_returns_unavailable_on_corrupt_payload(self):
        """Corrupt payload -> can't trust the cache for this entry -> UNAVAILABLE."""
        from privacyidea.lib.cache import CacheState
        self._real_client.hset('pi:challenge:txn:txn-corrupt', 'RCORRUPT',
                               '{"not": "a valid challenge"')  # truncated JSON
        with redis_in_store(self._real_client):
            self.assertIs(get_challenges_from_cache(transaction_id='txn-corrupt'),
                          CacheState.UNAVAILABLE)

    def test_save_short_circuits_when_already_expired(self):
        dto = _make_dto(serial='RCACHE_EXP', txn='txn-rcache-exp', offset_seconds=120)
        self._write_dto(dto)
        with redis_in_store(self._real_client):
            cached = get_challenges_from_cache(transaction_id='txn-rcache-exp')[0]
            # Force the DTO into the past so _update_challenge_in_cache hits
            # the "already expired" early return without re-writing the key.
            cached.expiration = utc_now() - timedelta(seconds=120)
            existing_payload = self._real_client.hget('pi:challenge:txn:txn-rcache-exp', 'RCACHE_EXP')
            cached.set_otp_status(True)
            cached.save()
        self.assertEqual(self._real_client.hget('pi:challenge:txn:txn-rcache-exp', 'RCACHE_EXP'),
                         existing_payload)

    def test_redis_disabled_on_operation_error(self):
        """If a Redis operation raises, the client must be disabled for this worker."""
        with redis_in_store(self._real_client):
            dto = _make_dto(serial='RCACHE8', txn='txn-rcache-008')
            with patch.object(self._real_client, 'pipeline',
                              side_effect=redis_lib.exceptions.ConnectionError("simulated mid-flight failure")):
                cache_challenge(
                    serial=dto.serial,
                    transaction_id=dto.transaction_id,
                    challenge=dto.challenge,
                    data=dto.data,
                    session=dto.session,
                    timestamp=dto.timestamp,
                    expiration=dto.expiration,
                )
            self.assertIsNone(get_redis())


# -----------------------------------------------------------------------------
# Higher-level create_challenge / get_challenges integration
# -----------------------------------------------------------------------------


class TestCreateChallengeIntegration(_RealRedisBase):
    """End-to-end tests for ``create_challenge`` + ``get_challenges`` with the
    cache layer engaged. The same assertions run for both the Redis path (DTO)
    and the DB path, proving callers are transparent to the backend."""

    serial = 'SE_INTG_CHAL'

    def setUp(self):
        super().setUp()
        self._token = init_token({"genkey": 1, "serial": self.serial, "pin": "pin"})
        Challenge.query.filter_by(serial=self.serial).delete()
        db.session.commit()

    def tearDown(self):
        Challenge.query.filter_by(serial=self.serial).delete()
        db.session.commit()
        super().tearDown()

    def _assert_challenge_readable(self, txn_id: str, client):
        """Shared assertions for both backends."""
        with redis_in_store(client):
            by_txn = get_challenges(serial=self.serial, transaction_id=txn_id)
            self.assertEqual(len(by_txn), 1)
            self.assertEqual(by_txn[0].transaction_id, txn_id)
            self.assertEqual(by_txn[0].serial, self.serial)
            self.assertTrue(by_txn[0].is_valid())

            by_serial = get_challenges(serial=self.serial)
            txn_ids = [c.transaction_id for c in by_serial]
            self.assertIn(txn_id, txn_ids)

    def test_create_challenge_db_path(self):
        """With no Redis, challenge must be persisted to the DB."""
        with redis_in_store(None):
            ch = create_challenge(self.serial, challenge='testchallenge', validitytime=120)
            txn_id = ch.transaction_id

        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNotNone(row)
        self._assert_challenge_readable(txn_id, None)

    def test_create_challenge_redis_path(self):
        """With Redis available, challenge is stored in cache only - no DB row."""
        with redis_in_store(self._real_client):
            ch = create_challenge(self.serial, challenge='testchallenge', validitytime=120)
            txn_id = ch.transaction_id

        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNone(row, "Challenge must NOT be written to DB when Redis is available")
        self._assert_challenge_readable(txn_id, self._real_client)

    def test_create_challenge_flag_disabled_writes_to_db(self):
        """With Redis reachable but PI_REDIS_CACHE_CHALLENGES off,
        create_challenge() writes through to the DB and skips the cache."""
        with redis_in_store(self._real_client, enable_challenges=False):
            ch = create_challenge(self.serial, challenge='flag_off', validitytime=120)
            txn_id = ch.transaction_id

        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNotNone(row, "Challenge must be written to DB when feature flag is off")
        # And nothing should have been written to Redis.
        self.assertIsNone(self._real_client.get(f'pi:challenge:txn:{txn_id}'))

    def test_get_challenges_flag_disabled_reads_from_db(self):
        """Even if a stale key happens to be in Redis, get_challenges() must
        skip the cache and serve from the DB when the feature flag is off."""
        ch = Challenge(self.serial, transaction_id=None, challenge='db_only',
                       data='', session='', validitytime=120)
        ch.save()
        txn_id = ch.transaction_id

        with redis_in_store(self._real_client, enable_challenges=False):
            result = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, txn_id)
        # Confirm the DB type came back, not a DTO.
        self.assertIsInstance(result[0], Challenge)

    def test_create_challenge_redis_fallback_to_db_on_write_failure(self):
        """If cache_challenge() fails, create_challenge() falls back to DB."""
        with redis_in_store(self._real_client):
            with patch.object(self._real_client, 'pipeline',
                              side_effect=redis_lib.exceptions.ConnectionError("simulated write failure")):
                ch = create_challenge(self.serial, challenge='failover', validitytime=120)
                txn_id = ch.transaction_id

        # Redis was disabled, challenge must have been saved to DB.
        row = Challenge.query.filter_by(transaction_id=txn_id).first()
        self.assertIsNotNone(row, "Challenge must fall back to DB when Redis write fails")

    def test_get_challenges_falls_back_to_db_on_cache_miss(self):
        """A challenge in the DB but not in Redis must still be found
        (e.g. challenge was created before the cache was enabled)."""
        ch = Challenge(self.serial, transaction_id=None, challenge='db_only',
                       data='', session='', validitytime=120)
        ch.save()
        txn_id = ch.transaction_id

        with redis_in_store(self._real_client):
            result = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transaction_id, txn_id)

    def test_otp_status_update_survives_roundtrip_redis(self):
        """set_otp_status + save must be visible on the next get_challenges call."""
        with redis_in_store(self._real_client):
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
        with redis_in_store(None):
            ch = create_challenge(self.serial, challenge='roundtrip_db', validitytime=120)
            txn_id = ch.transaction_id

            challenges = get_challenges(serial=self.serial, transaction_id=txn_id)
            self.assertEqual(len(challenges), 1)
            challenges[0].set_otp_status(True)
            challenges[0].save()

            updated = get_challenges(serial=self.serial, transaction_id=txn_id)

        self.assertTrue(updated[0].otp_valid)

    def test_delete_challenge_redis(self):
        with redis_in_store(self._real_client):
            ch = create_challenge(self.serial, challenge='to_delete', validitytime=120)
            txn_id = ch.transaction_id

            challenges = get_challenges(serial=self.serial, transaction_id=txn_id)
            challenges[0].delete()

            after = get_challenges(serial=self.serial, transaction_id=txn_id)

        # Cache miss -> falls back to DB -> also nothing there.
        self.assertEqual(len(after), 0)

    def test_multiple_challenges_same_serial_redis(self):
        with redis_in_store(self._real_client):
            ch1 = create_challenge(self.serial, challenge='c1', validitytime=120)
            ch2 = create_challenge(self.serial, challenge='c2', validitytime=120)

            result = get_challenges(serial=self.serial)

        txn_ids = {c.transaction_id for c in result}
        self.assertIn(ch1.transaction_id, txn_ids)
        self.assertIn(ch2.transaction_id, txn_ids)

    def test_get_challenges_paginate_by_serial_redis(self):
        """get_challenges_paginate filtered by serial must be served from Redis."""
        with redis_in_store(self._real_client):
            ch1 = create_challenge(self.serial, challenge='p1', validitytime=120)
            ch2 = create_challenge(self.serial, challenge='p2', validitytime=120)

            result = get_challenges_paginate(serial=self.serial)

        self.assertEqual(result['count'], 2)
        txn_ids = {c['transaction_id'] for c in result['challenges']}
        self.assertIn(ch1.transaction_id, txn_ids)
        self.assertIn(ch2.transaction_id, txn_ids)
        # No DB rows - unfiltered DB query would return 0.
        self.assertEqual(Challenge.query.filter_by(serial=self.serial).count(), 0)

    def test_get_challenges_paginate_by_txn_redis(self):
        """get_challenges_paginate filtered by transaction_id must be served from Redis."""
        with redis_in_store(self._real_client):
            ch = create_challenge(self.serial, challenge='p_txn', validitytime=120)
            txn_id = ch.transaction_id

            result = get_challenges_paginate(transaction_id=txn_id)

        self.assertEqual(result['count'], 1)
        self.assertEqual(result['challenges'][0]['transaction_id'], txn_id)

    def test_paginate_falls_back_to_natural_order_on_unsortable_field(self):
        """Sorting by a field whose value is None on some entries raises
        TypeError under Python 3 comparisons. The paginator must swallow
        the TypeError and return results in natural order rather than
        failing the request."""
        with redis_in_store(self._real_client):
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

    def test_get_challenges_paginate_unfiltered_degraded_with_redis(self):
        """Unfiltered and wildcard paginate cannot be served from the cache, so
        they fall through to the (empty) DB and report redis_cache_enabled=True
        - the WebUI 'List Challenges' view is intentionally degraded and shows a
        banner. Challenges only live in Redis, so count is 0."""
        with redis_in_store(self._real_client):
            create_challenge(self.serial, challenge='p_nofilt', validitytime=120)
            unfiltered = get_challenges_paginate()       # no serial, no txn_id
            wildcard = get_challenges_paginate(serial='*')  # the pattern the WebUI sends

        for result in (unfiltered, wildcard):
            self.assertEqual(result['count'], 0)
            self.assertEqual(result['challenges'], [])
            self.assertTrue(result['redis_cache_enabled'])

    def test_cancel_enrollment_via_multichallenge_no_attribute_error(self):
        """cancel_enrollment_via_multichallenge() must not AttributeError on
        Redis-backed ChallengeDTOs (no .id) on its early-out log paths."""
        from privacyidea.lib.challenge import cancel_enrollment_via_multichallenge
        with redis_in_store(self._real_client):
            # No data on the challenge - hits the "No data found" log path.
            ch = create_challenge(self.serial, challenge='no_data', validitytime=120)
            self.assertFalse(cancel_enrollment_via_multichallenge(ch.transaction_id))

            # Data present but optional flag is False - hits the
            # "does not have the action ... set to True" log path.
            ch2 = create_challenge(self.serial, challenge='opt_false', validitytime=120,
                                   data={
                                       PolicyAction.ENROLL_VIA_MULTICHALLENGE: "HOTP",
                                       PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL: False,
                                   })
            self.assertFalse(cancel_enrollment_via_multichallenge(ch2.transaction_id))

    def test_remove_token_evicts_redis_challenges(self):
        """Deleting a token drops its Redis-cached challenges so transaction
        IDs can't keep resolving until TTL expiry."""
        serial = 'SE_REAL_REDIS_LIFECYCLE'
        init_token({"genkey": 1, "serial": serial, "pin": "pin"})
        try:
            with redis_in_store(self._real_client):
                ch = create_challenge(serial, challenge='will_be_orphaned', validitytime=600)
                txn_id = ch.transaction_id
                # Sanity: transaction is resolvable from the cache pre-deletion.
                self.assertEqual(len(get_challenges(serial=serial, transaction_id=txn_id)), 1)

                remove_token(serial)

                # Both the per-transaction key and the serial set must be gone.
                self.assertIsNone(self._real_client.get(f"pi:challenge:txn:{txn_id}"))
                self.assertEqual(
                    self._real_client.smembers(f"pi:challenge:serial:{serial}"), set())
        finally:
            Challenge.query.filter_by(serial=serial).delete()
            db.session.commit()


# -----------------------------------------------------------------------------
# DTO behavior contracts (no Redis needed)
# -----------------------------------------------------------------------------


class TestChallengeDTOIdAttribute(MyTestCase):
    """Cache-only challenges intentionally do NOT expose ``.id`` - reading
    it raises AttributeError so misuse is caught at the source rather than
    silently logging or comparing None on cache-served entries."""

    def test_dto_does_not_expose_id(self):
        dto = _make_dto(serial='RPROTO', txn='txn-proto-1')
        with self.assertRaises(AttributeError):
            _ = dto.id


# -----------------------------------------------------------------------------
# Connection lifecycle: unified cooldown
# -----------------------------------------------------------------------------


class TestCooldownLifecycle(_RealRedisBase):
    """The connection lifecycle is driven by a single ``_redis_retry_after``
    timestamp. Any failure (init or runtime) sets the cooldown; ``get_redis``
    short-circuits to ``None`` inside the window and retries once it
    expires. No one-way latch, no separate cleanup-only bypass."""

    def test_disable_redis_sets_cooldown_and_clears_client(self):
        """_disable_redis drops the cached client and arms the cooldown."""
        from privacyidea.lib.cache.redis import _disable_redis
        from privacyidea.lib.framework import get_app_local_store
        with redis_in_store(self._real_client):
            store = get_app_local_store()
            self.assertIsNotNone(store.get('_redis_client_entry'))
            _disable_redis(RuntimeError("simulated"))
            self.assertIsNone(store.get('_redis_client_entry'))
            self.assertGreater(store.get('_redis_retry_after', 0), 0)

    def test_get_redis_short_circuits_during_cooldown(self):
        """Inside the cooldown window get_redis() returns None without
        attempting a reconnect - that's the guarantee against paying a
        timeout on every hot-path request during an outage."""
        from privacyidea.lib.cache.redis import _disable_redis
        with redis_in_store(self._real_client):
            _disable_redis(RuntimeError("simulated"))
            # Even though PI_REDIS_URL is configured and reachable, the
            # cooldown blocks a retry.
            self.assertIsNone(get_redis())

    def test_get_redis_recovers_after_cooldown_expires(self):
        """Once the cooldown elapses, get_redis() reconnects and the cache
        is back online - no worker restart needed."""
        import time as _time
        from privacyidea.lib.cache.redis import _disable_redis
        from privacyidea.lib.framework import get_app_local_store
        with redis_in_store(self._real_client):
            _disable_redis(RuntimeError("simulated"))
            # Fast-forward the cooldown by rewinding the timestamp.
            store = get_app_local_store()
            store['_redis_retry_after'] = _time.monotonic() - 1
            # Now get_redis() should reconnect.
            client = get_redis()
            self.assertIsNotNone(client)
            # And the cooldown timestamp is cleared on success.
            self.assertNotIn('_redis_retry_after', store)

    def test_get_redis_reconnects_after_fork(self):
        """A client cached by a previous PID (e.g. uWSGI fork-after-init or
        Gunicorn preload_app=True) is invalidated - redis-py sockets are
        not fork-safe, so each forked child must re-run the connect path
        once and get its own socket. Simulated by storing an entry under
        an obviously-not-our PID."""
        from privacyidea.lib.framework import get_app_local_store
        with redis_in_store(self._real_client):
            store = get_app_local_store()
            # Pretend the cached client was inherited from the parent.
            store['_redis_client_entry'] = (os.getpid() - 1, self._real_client)
            client = get_redis()
            # Reconnect happened: the stored PID now matches ours.
            self.assertEqual(store['_redis_client_entry'][0], os.getpid())
            self.assertIsNotNone(client)

    def test_evict_during_cooldown_is_a_noop(self):
        """Cleanup paths share the same cooldown - during the window they
        skip the Redis op rather than paying a fresh-connect timeout. The
        next op after the cooldown expires picks up where we left off."""
        from privacyidea.lib.cache.redis import _disable_redis
        # Pre-populate Redis with an entry - it should remain after the
        # in-cooldown evict (which is a no-op).
        self._real_client.hset('pi:challenge:txn:txn-cooldown', 'RCOOL', '{"placeholder":1}')
        with redis_in_store(self._real_client):
            _disable_redis(RuntimeError("simulated"))
            evict_challenge('txn-cooldown', 'RCOOL')
        self.assertEqual(self._real_client.hget('pi:challenge:txn:txn-cooldown', 'RCOOL'),
                         '{"placeholder":1}')

    def test_evict_after_cooldown_reaches_redis(self):
        """Once the cooldown expires, cleanup ops resume against Redis."""
        import time as _time
        from privacyidea.lib.cache.redis import _disable_redis
        from privacyidea.lib.framework import get_app_local_store
        self._real_client.hset('pi:challenge:txn:txn-recovered', 'RREC', '{"placeholder":1}')
        self._real_client.sadd('pi:challenge:serial:RREC', 'txn-recovered')
        with redis_in_store(self._real_client):
            _disable_redis(RuntimeError("simulated"))
            # Skip past the cooldown.
            get_app_local_store()['_redis_retry_after'] = _time.monotonic() - 1
            evict_challenge('txn-recovered', 'RREC')
        # Eviction reached Redis post-cooldown.
        self.assertFalse(self._real_client.exists('pi:challenge:txn:txn-recovered'))
        self.assertNotIn('txn-recovered',
                         self._real_client.smembers('pi:challenge:serial:RREC'))


# -----------------------------------------------------------------------------
# Server-version gate (uses unittest.mock, no real Redis needed)
# -----------------------------------------------------------------------------


class TestRedisVersionGate(MyTestCase):
    """_build_client refuses to use a Redis < 7 server because the challenge
    cache writes depend on EXPIRE NX/GT (Redis 7.0+)."""

    def test_build_client_refuses_redis_6(self):
        from unittest.mock import MagicMock
        from privacyidea.lib.cache.redis import _build_client
        fake = MagicMock()
        fake.ping.return_value = True
        fake.info.return_value = {"redis_version": "6.2.7"}
        import redis as _redis_lib
        with patch.object(_redis_lib.Redis, "from_url", return_value=fake):
            with self.assertRaises(RuntimeError) as cm:
                _build_client("redis://anywhere:6379/0")
        self.assertIn("6.2.7", str(cm.exception))
        self.assertIn("Redis 7", str(cm.exception))

    def test_build_client_accepts_redis_7(self):
        from unittest.mock import MagicMock
        from privacyidea.lib.cache.redis import _build_client
        fake = MagicMock()
        fake.ping.return_value = True
        fake.info.return_value = {"redis_version": "7.2.4"}
        import redis as _redis_lib
        with patch.object(_redis_lib.Redis, "from_url", return_value=fake):
            client = _build_client("redis://anywhere:6379/0")
        self.assertIs(client, fake)
