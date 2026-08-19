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
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Tests for the Redis user cache (privacyidea/lib/cache/user.py).

The cache-behaviour tests run against a real Redis instance, like the challenge
cache tests do: TTL semantics, EXPIRE NX/GT and pipeline behaviour are what this
module relies on, and a hand-rolled fake would assert the fake instead of Redis.

The tests that only exercise this module's own decisions - which requests a
cached entry covers, how the TTL setting is read, how a key segment is encoded -
need no Redis and run unconditionally.

Local DX: ``tests/conftest.py`` probes ``127.0.0.1:6379`` and exports
``TEST_REDIS_URL`` when it answers, so ``docker compose -f compose-dev.yml up -d redis``
is all a developer needs.
"""
import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import pytest
import redis as redis_lib

from privacyidea.lib.cache.user import (_covered_user_info, _segment, _ttl_seconds, cached_user_id, cached_user_info,
                                        cached_username, flush_user_cache, invalidate_resolver, invalidate_user)
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.resolver import delete_resolver, save_resolver
from privacyidea.lib.user import User
from .base import MyTestCase

_TEST_REDIS_URL = os.environ.get('TEST_REDIS_URL')

RESOLVER_NAME = "redisusercache"


class FakeResolver:
    """
    A resolver that counts what it was asked, so a test can tell a cache hit
    from a repeated lookup.

    The user cache only ever calls these three methods, and only ever with the
    arguments the real resolvers take.
    """

    def __init__(self, users: dict = None, has_multiple_loginnames: bool = False):
        # {login: (user_id, {attribute: value})}
        self.users = users or {"alice": ("1000", {"username": "alice", "email": "alice@example.com",
                                                 "givenname": "Alice", "mobile": "123"})}
        self.has_multiple_loginnames = has_multiple_loginnames
        self.user_id_calls = []
        self.username_calls = []
        self.user_info_calls = []

    def getUserId(self, login):
        self.user_id_calls.append(login)
        return self.users.get(login, ("", {}))[0]

    def getUsername(self, user_id):
        self.username_calls.append(user_id)
        for login, (uid, _info) in self.users.items():
            if uid == f"{user_id}":
                return login
        return ""

    def get_user_info(self, user_id, attributes=None):
        self.user_info_calls.append((user_id, attributes))
        for _login, (uid, info) in self.users.items():
            if uid == f"{user_id}":
                if attributes is None:
                    return dict(info)
                return {key: value for key, value in info.items() if key in attributes}
        return {}


@contextmanager
def user_cache_in_store(client, enabled: bool = True, ttl: int = 300):
    """
    Inject ``client`` into the app-local store so the cache uses it without
    running the connect path, and set the flag and TTL the module reads.

    Pass ``client=None`` to simulate a worker with no Redis at all: the URL is
    dropped too, otherwise the cache would connect through it and produce a live
    client, which is the opposite of what such a test sets up.
    """
    from flask import current_app
    store = get_app_local_store()
    had_client = '_redis_client_entry' in store
    old_client = store.get('_redis_client_entry')
    if client is None:
        store.pop('_redis_client_entry', None)
    else:
        store['_redis_client_entry'] = (os.getpid(), client)

    keys = {'PI_REDIS_CACHE_USERS': enabled,
            'PI_REDIS_USER_CACHE_TTL': ttl,
            'PI_REDIS_URL': _TEST_REDIS_URL or "redis://stub:6379/0"}
    if client is None:
        keys.pop('PI_REDIS_URL')
    previous = {key: (key in current_app.config, current_app.config.get(key)) for key in keys}
    if client is None:
        current_app.config.pop('PI_REDIS_URL', None)
    current_app.config.update(keys)
    try:
        yield client
    finally:
        for key, (was_present, old_value) in previous.items():
            if was_present:
                current_app.config[key] = old_value
            else:
                current_app.config.pop(key, None)
        if had_client:
            store['_redis_client_entry'] = old_client
        else:
            store.pop('_redis_client_entry', None)
        # A test that trips _disable_redis leaves a cooldown behind, which would
        # silently turn the cache off for every later test in the session
        store.pop('_redis_retry_after', None)


class UserCacheUnitTestCase(MyTestCase):
    """Decisions this module makes on its own, without a cache to talk to."""

    def test_01_segment_cannot_span_keys(self):
        # A login that contains the key separator must not be able to address
        # another resolver's keyspace
        self.assertEqual("a%3Ab", _segment("a:b"))
        self.assertEqual("with%20space", _segment("with space"))
        self.assertEqual("1000", _segment(1000))

    def test_02_ttl_defaults_and_disables(self):
        with patch("privacyidea.lib.cache.user.get_app_config_value", return_value=None):
            self.assertEqual(300, _ttl_seconds())
        with patch("privacyidea.lib.cache.user.get_app_config_value", return_value="not a number"):
            self.assertEqual(300, _ttl_seconds())
        with patch("privacyidea.lib.cache.user.get_app_config_value", return_value=60):
            self.assertEqual(60, _ttl_seconds())
        # An explicit 0 turns the cache off, a negative value is not an
        # invitation to cache forever
        with patch("privacyidea.lib.cache.user.get_app_config_value", return_value=0):
            self.assertEqual(0, _ttl_seconds())
        with patch("privacyidea.lib.cache.user.get_app_config_value", return_value=-10):
            self.assertEqual(0, _ttl_seconds())

    def test_03_entry_covers_only_the_attributes_it_was_written_for(self):
        narrow = '{"attributes": ["email", "username"], "info": {"username": "alice", "email": "a@b.c"}}'
        # Exactly the attributes it holds, and any subset of them
        self.assertEqual({"username": "alice", "email": "a@b.c"},
                         _covered_user_info(narrow, ["username", "email"]))
        self.assertEqual({"username": "alice"}, _covered_user_info(narrow, ["username"]))
        # An attribute it was never asked for is not absent, it is unknown
        self.assertIsNone(_covered_user_info(narrow, ["username", "mobile"]))
        # ... and neither is "everything"
        self.assertIsNone(_covered_user_info(narrow, None))

    def test_04_entry_written_for_all_attributes_covers_every_request(self):
        full = '{"attributes": null, "info": {"username": "alice", "email": "a@b.c"}}'
        self.assertEqual({"username": "alice", "email": "a@b.c"}, _covered_user_info(full, None))
        self.assertEqual({"username": "alice"}, _covered_user_info(full, ["username"]))
        # An attribute the user simply does not have stays absent rather than
        # invalidating the entry
        self.assertEqual({}, _covered_user_info(full, ["mobile"]))

    def test_05_malformed_entries_are_a_miss(self):
        # Anything can end up in a Redis database: a hand-written key, another
        # tool in the same namespace, a payload from a future version
        for raw in ['not json', '[]', '"a string"', 'null', '{"info": {}}',
                    '{"attributes": [], "info": "not a dict"}',
                    '{"attributes": "not a list", "info": {}}']:
            self.assertIsNone(_covered_user_info(raw, ["username"]), raw)
            self.assertIsNone(_covered_user_info(raw, None), raw)

    def test_06_without_redis_every_lookup_reaches_the_resolver(self):
        resolver = FakeResolver()
        with user_cache_in_store(None):
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
            self.assertEqual("alice", cached_username(resolver, RESOLVER_NAME, "1000"))
            self.assertEqual({"username": "alice"},
                             cached_user_info(resolver, RESOLVER_NAME, "1000", ["username"]))
        self.assertEqual(["alice", "alice"], resolver.user_id_calls)
        self.assertEqual(["1000"], resolver.username_calls)
        self.assertEqual([("1000", ["username"])], resolver.user_info_calls)


@pytest.mark.skipif(not _TEST_REDIS_URL,
                    reason="TEST_REDIS_URL not set - start compose-dev's Redis or export the env var")
class _RealRedisBase(MyTestCase):
    """
    Shared base for the tests that need a real Redis client.

    Connects once per class and drops every ``pi:user:*`` key around each test,
    which is cheaper than FLUSHDB and leaves anything else sharing the instance
    alone.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            client = redis_lib.Redis.from_url(_TEST_REDIS_URL, decode_responses=True,
                                              socket_connect_timeout=2, socket_timeout=2)
            client.ping()
        except Exception as error:
            raise unittest.SkipTest(f"Redis not reachable at {_TEST_REDIS_URL}: {error}")
        cls._real_client = client

    def setUp(self):
        super().setUp()
        self._flush_cache()

    def tearDown(self):
        self._flush_cache()
        super().tearDown()

    def _flush_cache(self):
        client = type(self)._real_client
        keys = list(client.scan_iter(match="pi:user:*"))
        if keys:
            client.delete(*keys)


class UserCacheRedisTestCase(_RealRedisBase):
    """The cache reading and writing against a real Redis."""

    def test_01_second_lookup_is_served_from_the_cache(self):
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
        self.assertEqual(["alice"], resolver.user_id_calls)

        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            self.assertEqual("alice", cached_username(resolver, RESOLVER_NAME, "1000"))
            self.assertEqual("alice", cached_username(resolver, RESOLVER_NAME, "1000"))
        self.assertEqual(["1000"], resolver.username_calls)

        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            info = cached_user_info(resolver, RESOLVER_NAME, "1000", ["username", "email"])
            self.assertEqual({"username": "alice", "email": "alice@example.com"}, info)
            self.assertEqual(info, cached_user_info(resolver, RESOLVER_NAME, "1000", ["username", "email"]))
        self.assertEqual([("1000", ["username", "email"])], resolver.user_info_calls)

    def test_02_values_are_encrypted_in_redis(self):
        # A dump of the Redis database must not be a dump of the directory
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            cached_user_id(resolver, RESOLVER_NAME, "alice")
            cached_user_info(resolver, RESOLVER_NAME, "1000", None)
        stored = [self._real_client.get(key) for key in self._real_client.scan_iter(match="pi:user:v1:uid:*")]
        stored += [self._real_client.get(key) for key in self._real_client.scan_iter(match="pi:user:v1:info:*")]
        self.assertEqual(2, len(stored), stored)
        for raw in stored:
            self.assertNotIn("alice", raw, raw)
            self.assertNotIn("example.com", raw, raw)

    def test_03_entries_expire_with_the_configured_ttl(self):
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client, ttl=60):
            cached_user_id(resolver, RESOLVER_NAME, "alice")
        key = f"pi:user:v1:uid:{RESOLVER_NAME}:alice"
        self.assertGreater(self._real_client.ttl(key), 0)
        self.assertLessEqual(self._real_client.ttl(key), 60)
        # The index has to outlive the entries it points at, so it is seeded
        # once and then only ever extended
        index_ttl = self._real_client.ttl(f"pi:user:v1:index:{RESOLVER_NAME}")
        self.assertGreater(index_ttl, 0)
        with user_cache_in_store(self._real_client, ttl=600):
            cached_username(resolver, RESOLVER_NAME, "1000")
        self.assertGreater(self._real_client.ttl(f"pi:user:v1:index:{RESOLVER_NAME}"), index_ttl)

    def test_04_a_ttl_of_zero_does_not_cache(self):
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client, ttl=0):
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
        self.assertEqual(["alice", "alice"], resolver.user_id_calls)
        self.assertEqual([], list(self._real_client.scan_iter(match="pi:user:*")))

    def test_05_a_cleared_flag_does_not_cache(self):
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client, enabled=False):
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
        self.assertEqual(["alice", "alice"], resolver.user_id_calls)
        self.assertEqual([], list(self._real_client.scan_iter(match="pi:user:*")))

    def test_06_an_unknown_user_is_not_cached(self):
        # The empty answer is the one that changes when a user is created, so a
        # new user must never be shut out until an entry expires
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            self.assertEqual("", cached_user_id(resolver, RESOLVER_NAME, "nosuchuser"))
            self.assertEqual("", cached_user_id(resolver, RESOLVER_NAME, "nosuchuser"))
            self.assertEqual("", cached_username(resolver, RESOLVER_NAME, "9999"))
            self.assertEqual("", cached_username(resolver, RESOLVER_NAME, "9999"))
            self.assertEqual({}, cached_user_info(resolver, RESOLVER_NAME, "9999", None))
            self.assertEqual({}, cached_user_info(resolver, RESOLVER_NAME, "9999", None))
        self.assertEqual(["nosuchuser", "nosuchuser"], resolver.user_id_calls)
        self.assertEqual(["9999", "9999"], resolver.username_calls)
        self.assertEqual([("9999", None), ("9999", None)], resolver.user_info_calls)
        self.assertEqual([], list(self._real_client.scan_iter(match="pi:user:*")))

    def test_07_a_wider_request_refetches_and_widens_the_entry(self):
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            self.assertEqual({"username": "alice"},
                             cached_user_info(resolver, RESOLVER_NAME, "1000", ["username"]))
            # "mobile" was never asked for, so the narrow entry cannot answer
            self.assertEqual({"username": "alice", "mobile": "123"},
                             cached_user_info(resolver, RESOLVER_NAME, "1000", ["username", "mobile"]))
            # The wider entry replaced the narrow one and now answers both
            self.assertEqual({"username": "alice"},
                             cached_user_info(resolver, RESOLVER_NAME, "1000", ["username"]))
            self.assertEqual({"username": "alice", "mobile": "123"},
                             cached_user_info(resolver, RESOLVER_NAME, "1000", ["username", "mobile"]))
        self.assertEqual([("1000", ["username"]), ("1000", ["username", "mobile"])], resolver.user_info_calls)

    def test_08_one_users_entries_are_dropped_alone(self):
        resolver = FakeResolver(users={"alice": ("1000", {"username": "alice"}),
                                       "bob": ("1001", {"username": "bob"})})
        with user_cache_in_store(self._real_client):
            cached_user_id(resolver, RESOLVER_NAME, "alice")
            cached_username(resolver, RESOLVER_NAME, "1000")
            cached_user_info(resolver, RESOLVER_NAME, "1000", None)
            cached_user_id(resolver, RESOLVER_NAME, "bob")
            invalidate_user(RESOLVER_NAME, login="alice", user_id="1000")

            # The dropped keys leave the index too, so it does not grow without
            # bound as users are invalidated and cached again
            index = self._real_client.smembers(f"pi:user:v1:index:{RESOLVER_NAME}")
            self.assertEqual({f"pi:user:v1:uid:{RESOLVER_NAME}:bob"}, index)

            resolver.user_id_calls.clear()
            resolver.username_calls.clear()
            resolver.user_info_calls.clear()
            cached_user_id(resolver, RESOLVER_NAME, "alice")
            cached_username(resolver, RESOLVER_NAME, "1000")
            cached_user_info(resolver, RESOLVER_NAME, "1000", None)
            # Bob was never touched
            cached_user_id(resolver, RESOLVER_NAME, "bob")
        self.assertEqual(["alice"], resolver.user_id_calls)
        self.assertEqual(["1000"], resolver.username_calls)
        self.assertEqual([("1000", None)], resolver.user_info_calls)

    def test_09_a_resolvers_entries_are_dropped_through_its_index(self):
        resolver = FakeResolver(users={"alice": ("1000", {"username": "alice"}),
                                       "bob": ("1001", {"username": "bob"})})
        other_resolver = FakeResolver(users={"carol": ("2000", {"username": "carol"})})
        with user_cache_in_store(self._real_client):
            cached_user_id(resolver, RESOLVER_NAME, "alice")
            cached_user_id(resolver, RESOLVER_NAME, "bob")
            cached_user_info(resolver, RESOLVER_NAME, "1000", None)
            cached_user_id(other_resolver, "otherresolver", "carol")

            invalidate_resolver(RESOLVER_NAME)

            self.assertEqual([], list(self._real_client.scan_iter(match=f"pi:user:v1:*:{RESOLVER_NAME}:*")))
            self.assertFalse(self._real_client.exists(f"pi:user:v1:index:{RESOLVER_NAME}"))
            # A different resolver keeps its entries
            other_resolver.user_id_calls.clear()
            self.assertEqual("2000", cached_user_id(other_resolver, "otherresolver", "carol"))
            self.assertEqual([], other_resolver.user_id_calls)

    def test_10_invalidating_an_unknown_resolver_is_harmless(self):
        with user_cache_in_store(self._real_client):
            invalidate_resolver("never-cached-anything")
            invalidate_user("never-cached-anything", login="nobody", user_id="0")

    def test_11_a_corrupt_entry_is_dropped_and_refetched(self):
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            cached_user_id(resolver, RESOLVER_NAME, "alice")
            key = f"pi:user:v1:uid:{RESOLVER_NAME}:alice"
            # Written under a different encryption key, or simply damaged
            self._real_client.set(key, "not decryptable")
            resolver.user_id_calls.clear()
            self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
            self.assertEqual(["alice"], resolver.user_id_calls)
            # It was dropped rather than left to fail on every later read
            self.assertNotEqual("not decryptable", self._real_client.get(key))

    def test_12_a_failing_redis_falls_through_to_the_resolver(self):
        resolver = FakeResolver()
        broken = self._real_client
        with user_cache_in_store(broken):
            with patch.object(type(broken), "get",
                              side_effect=redis_lib.exceptions.ConnectionError("gone")):
                self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
        self.assertEqual(["alice"], resolver.user_id_calls)

    def test_13_a_failing_write_still_answers_the_caller(self):
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            with patch.object(type(self._real_client), "pipeline",
                              side_effect=redis_lib.exceptions.ConnectionError("gone")):
                self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
        self.assertEqual(["alice"], resolver.user_id_calls)

    def test_14_a_failing_hsm_does_not_fail_the_lookup(self):
        from privacyidea.lib.error import HSMException
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            with patch("privacyidea.lib.cache.user.encryptPassword",
                       side_effect=HSMException("HSM not ready")):
                self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
        self.assertEqual(["alice"], resolver.user_id_calls)
        # Nothing was written, so the next lookup simply asks again
        self.assertEqual([], list(self._real_client.scan_iter(match="pi:user:*")))

    def test_15_an_hsm_that_cannot_decrypt_does_not_fail_the_lookup(self):
        # decryptPassword returns a placeholder for a failed decryption, but it
        # reaches the HSM before that guard applies, so an HSM that is not ready
        # raises. Reading a cache must never turn a working lookup into an error.
        resolver = FakeResolver()
        with user_cache_in_store(self._real_client):
            cached_user_id(resolver, RESOLVER_NAME, "alice")
            resolver.user_id_calls.clear()
            with patch("privacyidea.lib.cache.user.decryptPassword",
                       side_effect=Exception("HSM not ready")):
                self.assertEqual("1000", cached_user_id(resolver, RESOLVER_NAME, "alice"))
        self.assertEqual(["alice"], resolver.user_id_calls)

    def test_16_logins_cannot_reach_another_resolvers_keyspace(self):
        # A login built to look like a key separator must stay inside its own
        # resolver's namespace
        resolver = FakeResolver(users={"a:b": ("1000", {"username": "a:b"})})
        with user_cache_in_store(self._real_client):
            cached_user_id(resolver, "res", "a:b")
        self.assertTrue(self._real_client.exists("pi:user:v1:uid:res:a%3Ab"))


class UserCacheIntegrationTestCase(_RealRedisBase):
    """The cache as the ``User`` class and the resolver hooks actually use it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        save_resolver({"resolver": RESOLVER_NAME,
                       "type": "passwdresolver",
                       "fileName": "tests/testdata/passwd"})
        from privacyidea.lib.realm import set_realm
        set_realm("redisrealm", [{"name": RESOLVER_NAME}])

    @classmethod
    def tearDownClass(cls):
        from privacyidea.lib.realm import delete_realm
        delete_realm("redisrealm")
        delete_resolver(RESOLVER_NAME)
        super().tearDownClass()

    def test_01_building_a_user_populates_the_cache(self):
        with user_cache_in_store(self._real_client):
            user = User(login="cornelius", realm="redisrealm")
            self.assertEqual("1009", user.uid)
            self.assertTrue(self._real_client.exists(f"pi:user:v1:uid:{RESOLVER_NAME}:cornelius"))
            # A user built from the uid, the way a token owner is resolved,
            # reads the login name back from the cache
            from_uid = User(uid="1009", resolver=RESOLVER_NAME, realm="redisrealm")
            self.assertEqual("cornelius", from_uid.login)

    def test_02_user_info_is_served_from_the_cache(self):
        with user_cache_in_store(self._real_client):
            user = User(login="cornelius", realm="redisrealm")
            info = user.info
            self.assertEqual("cornelius", info.get("username"))
            self.assertTrue(self._real_client.exists(f"pi:user:v1:info:{RESOLVER_NAME}:1009"))
            self.assertEqual(info, User(login="cornelius", realm="redisrealm").info)

    def test_03_custom_attributes_are_never_cached(self):
        # They live in privacyIDEA's own database and are merged on top of the
        # resolver's answer, so they must not be able to go stale here
        with user_cache_in_store(self._real_client):
            user = User(login="cornelius", realm="redisrealm")
            self.assertNotIn("customkey", user.info)
            user.set_attribute("customkey", "customvalue")
            try:
                self.assertEqual("customvalue", User(login="cornelius", realm="redisrealm").info["customkey"])
            finally:
                user.delete_attribute("customkey")
            self.assertNotIn("customkey", User(login="cornelius", realm="redisrealm").info)

    def test_04_saving_a_resolver_drops_its_entries(self):
        with user_cache_in_store(self._real_client):
            User(login="cornelius", realm="redisrealm")
            self.assertTrue(self._real_client.exists(f"pi:user:v1:uid:{RESOLVER_NAME}:cornelius"))
            # The configuration decides what the resolver's answers mean, so
            # nothing cached under it survives a change
            save_resolver({"resolver": RESOLVER_NAME,
                           "type": "passwdresolver",
                           "fileName": "tests/testdata/passwd"})
            self.assertFalse(self._real_client.exists(f"pi:user:v1:uid:{RESOLVER_NAME}:cornelius"))
            self.assertFalse(self._real_client.exists(f"pi:user:v1:index:{RESOLVER_NAME}"))

    def test_05_flush_drops_every_resolver(self):
        with user_cache_in_store(self._real_client):
            User(login="cornelius", realm="redisrealm")
            self.assertTrue(self._real_client.exists(f"pi:user:v1:uid:{RESOLVER_NAME}:cornelius"))
            self.assertGreaterEqual(flush_user_cache(), 1)
            self.assertEqual([], list(self._real_client.scan_iter(match="pi:user:*")))

    def test_06_the_api_flush_endpoint_drops_the_redis_entries(self):
        self.authenticate()
        with user_cache_in_store(self._real_client):
            User(login="cornelius", realm="redisrealm")
            self.assertTrue(self._real_client.exists(f"pi:user:v1:uid:{RESOLVER_NAME}:cornelius"))
            with self.app.test_request_context('/system/user-cache', method='DELETE',
                                               headers={'Authorization': self.at}):
                response = self.app.full_dispatch_request()
                self.assertEqual(200, response.status_code, response.data)
            self.assertEqual([], list(self._real_client.scan_iter(match="pi:user:*")))
