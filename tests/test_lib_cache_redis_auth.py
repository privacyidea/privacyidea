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
Tests for the Redis authentication cache (privacyidea/lib/cache/auth.py).

The cache-behaviour tests run against a real Redis, like the other cache tests:
TTL semantics, EXPIRE NX/GT and HINCRBY are the parts this module leans on, and
a hand-rolled fake would only assert the fake.

The tests go through ``privacyidea.lib.authcache``, not the Redis module
directly, because the point of the change is that the existing callers keep
working unchanged - and that when Redis holds the entries, the database table
stays empty.

Local DX: ``tests/conftest.py`` probes ``127.0.0.1:6379`` and exports
``TEST_REDIS_URL`` when it answers, so ``docker compose -f compose-dev.yml up -d redis``
is all a developer needs.
"""
import datetime
import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import pytest
import redis as redis_lib

from privacyidea.lib.authcache import add_to_cache, delete_from_cache, verify_in_cache
from privacyidea.lib.cache.auth import _ttl_seconds, cache_enabled
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import PolicyClass, SCOPE, delete_policy, set_policy
from privacyidea.lib.policydecorators import auth_cache
from privacyidea.lib.realm import delete_realm, set_realm
from privacyidea.lib.resolver import delete_resolver, save_resolver
from privacyidea.lib.user import User
from privacyidea.models import AuthCache
from privacyidea.models.utils import utc_now
from .base import FakeAudit, FakeFlaskG, MyTestCase

_TEST_REDIS_URL = os.environ.get('TEST_REDIS_URL')


@contextmanager
def auth_cache_in_store(client, enabled: bool = True, ttl: int = 3600):
    """
    Inject ``client`` into the app-local store so the cache uses it without
    running the connect path, and set the flag and fallback TTL the module reads.

    Pass ``client=None`` to simulate a worker with no Redis at all.
    """
    from flask import current_app
    store = get_app_local_store()
    had_client = '_redis_client_entry' in store
    old_client = store.get('_redis_client_entry')
    if client is None:
        store.pop('_redis_client_entry', None)
    else:
        store['_redis_client_entry'] = (os.getpid(), client)

    keys = {'PI_REDIS_CACHE_AUTH': enabled,
            'PI_REDIS_AUTH_CACHE_TTL': ttl,
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
        store.pop('_redis_retry_after', None)


class AuthCacheTtlTestCase(MyTestCase):
    """The lifetime decision, which needs no cache to talk to."""

    def test_01_the_policy_window_wins_over_the_configured_default(self):
        with patch("privacyidea.lib.cache.auth.get_app_config_value", return_value=3600):
            self.assertEqual(60, _ttl_seconds(60))
            self.assertEqual(3600, _ttl_seconds(None))

    def test_02_a_malformed_default_falls_back_rather_than_disabling(self):
        with patch("privacyidea.lib.cache.auth.get_app_config_value", return_value="not a number"):
            self.assertEqual(3600, _ttl_seconds())
        with patch("privacyidea.lib.cache.auth.get_app_config_value", return_value=None):
            self.assertEqual(3600, _ttl_seconds())

    def test_03_zero_and_negative_disable(self):
        with patch("privacyidea.lib.cache.auth.get_app_config_value", return_value=0):
            self.assertEqual(0, _ttl_seconds())
        self.assertEqual(0, _ttl_seconds(0))
        self.assertEqual(0, _ttl_seconds(-10))


@pytest.mark.skipif(not _TEST_REDIS_URL,
                    reason="TEST_REDIS_URL not set - start compose-dev's Redis or export the env var")
class RedisAuthCacheTestCase(MyTestCase):
    """The authentication cache with Redis holding the entries."""

    username = "cornelius"
    realm = "home"
    resolver = "resolver1"
    password = "topsecret"

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
        keys = list(client.scan_iter(match="pi:authcache:*"))
        if keys:
            client.delete(*keys)

    def _key(self):
        return f"pi:authcache:v1:{self.username}:{self.realm}:{self.resolver}"

    def _windows(self, first_hours=4, last_minutes=5):
        now = utc_now()
        return (now - datetime.timedelta(hours=first_hours),
                now - datetime.timedelta(minutes=last_minutes))

    def test_01_a_cached_authentication_verifies_and_writes_no_row(self):
        with auth_cache_in_store(self._real_client):
            self.assertEqual(0, add_to_cache(self.username, self.realm, self.resolver, self.password))
            first_auth, last_auth = self._windows()
            self.assertTrue(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                            first_auth=first_auth, last_auth=last_auth))
        # The whole point: the authentication path did not touch the database
        self.assertEqual(0, AuthCache.query.filter(AuthCache.username == self.username).count())
        self.assertTrue(self._real_client.exists(self._key()))

    def test_02_a_wrong_password_does_not_verify(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
            first_auth, last_auth = self._windows()
            self.assertFalse(verify_in_cache(self.username, self.realm, self.resolver, "wrong",
                                             first_auth=first_auth, last_auth=last_auth))
            # ... and the right one still does: a failed attempt must not
            # invalidate an entry it never matched
            self.assertTrue(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                            first_auth=first_auth, last_auth=last_auth))

    def test_03_an_unknown_user_is_a_miss(self):
        with auth_cache_in_store(self._real_client):
            first_auth, last_auth = self._windows()
            self.assertFalse(verify_in_cache("nobody", self.realm, self.resolver, self.password,
                                             first_auth=first_auth, last_auth=last_auth))

    def test_04_the_entry_expires_with_the_policy_window(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password, max_age_seconds=120)
        ttl = self._real_client.ttl(self._key())
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 120)

    def test_05_the_configured_default_applies_without_a_policy_window(self):
        with auth_cache_in_store(self._real_client, ttl=900):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
        ttl = self._real_client.ttl(self._key())
        self.assertGreater(ttl, 120)
        self.assertLessEqual(ttl, 900)

    def test_06_using_an_entry_does_not_extend_its_life(self):
        # The window runs from the first authentication, so a password must not
        # stay valid longer just because it keeps being used
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password, max_age_seconds=120)
            ttl_before = self._real_client.ttl(self._key())
            first_auth, last_auth = self._windows()
            self.assertTrue(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                            first_auth=first_auth, last_auth=last_auth))
            self.assertLessEqual(self._real_client.ttl(self._key()), ttl_before)

    def test_07_an_entry_first_used_before_the_window_is_dropped(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
            # A window that started after this entry did
            first_auth = utc_now() + datetime.timedelta(minutes=1)
            self.assertFalse(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                             first_auth=first_auth))
            # It was removed rather than left to cost an argon2 verification on
            # every later attempt
            self.assertEqual({}, self._real_client.hgetall(self._key()))

    def test_08_an_entry_last_used_before_the_window_does_not_verify(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
            first_auth, _ = self._windows()
            last_auth = utc_now() + datetime.timedelta(minutes=1)
            self.assertFalse(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                             first_auth=first_auth, last_auth=last_auth))

    def test_09_max_auths_is_counted_and_enforced(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
            first_auth, last_auth = self._windows()
            # Two uses are allowed, the third is not
            self.assertTrue(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                            first_auth=first_auth, last_auth=last_auth, max_auths=2))
            self.assertTrue(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                            first_auth=first_auth, last_auth=last_auth, max_auths=2))
            self.assertFalse(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                             first_auth=first_auth, last_auth=last_auth, max_auths=2))

    def test_10_the_counter_is_raised_atomically(self):
        # The counter lives in a field of its own so it can be raised with
        # HINCRBY. Folding it into the encrypted record would make every hit a
        # read-modify-write, and an entry could be used once more than allowed
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
            first_auth, last_auth = self._windows()
            verify_in_cache(self.username, self.realm, self.resolver, self.password,
                            first_auth=first_auth, last_auth=last_auth)
            counts = [value for field, value in self._real_client.hgetall(self._key()).items()
                      if field.startswith("count:")]
            self.assertEqual(["1"], counts)

    def test_11_the_stored_record_is_encrypted(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
        records = [value for field, value in self._real_client.hgetall(self._key()).items()
                   if field.startswith("entry:")]
        self.assertEqual(1, len(records))
        # Neither the argon2 hash nor its recognisable prefix may be readable
        self.assertNotIn("argon2", records[0])
        self.assertNotIn("first_auth", records[0])

    def test_12_deleting_removes_the_matching_entry_only(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
            add_to_cache(self.username, self.realm, self.resolver, "anotherPassword")
            self.assertEqual(1, delete_from_cache(self.username, self.realm, self.resolver, self.password))
            first_auth, last_auth = self._windows()
            self.assertFalse(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                             first_auth=first_auth, last_auth=last_auth))
            self.assertTrue(verify_in_cache(self.username, self.realm, self.resolver, "anotherPassword",
                                            first_auth=first_auth, last_auth=last_auth))

    def test_13_users_do_not_share_entries(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
            first_auth, last_auth = self._windows()
            # Same password, different realm and resolver
            self.assertFalse(verify_in_cache(self.username, "otherrealm", self.resolver, self.password,
                                             first_auth=first_auth, last_auth=last_auth))
            self.assertFalse(verify_in_cache(self.username, self.realm, "otherresolver", self.password,
                                             first_auth=first_auth, last_auth=last_auth))

    def test_14_an_unreadable_entry_is_ignored(self):
        with auth_cache_in_store(self._real_client):
            add_to_cache(self.username, self.realm, self.resolver, self.password)
            field = next(field for field in self._real_client.hgetall(self._key())
                         if field.startswith("entry:"))
            self._real_client.hset(self._key(), field, "not decryptable")
            first_auth, last_auth = self._windows()
            self.assertFalse(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                             first_auth=first_auth, last_auth=last_auth))

    def test_15_a_failing_redis_falls_back_to_the_database(self):
        # Write the entry while the cache is off, so it exists only in the
        # database, then ask for it with a Redis that cannot be read
        with auth_cache_in_store(self._real_client, enabled=False):
            self.assertGreater(add_to_cache(self.username, self.realm, self.resolver, self.password), 0)
        try:
            first_auth, last_auth = self._windows()
            with auth_cache_in_store(self._real_client):
                with patch.object(type(self._real_client), "hgetall",
                                  side_effect=redis_lib.exceptions.ConnectionError("gone")):
                    self.assertTrue(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                                    first_auth=first_auth, last_auth=last_auth))
        finally:
            with auth_cache_in_store(self._real_client, enabled=False):
                delete_from_cache(self.username, self.realm, self.resolver, self.password)

    def test_16_a_failing_hsm_does_not_fail_the_authentication(self):
        with auth_cache_in_store(self._real_client):
            with patch("privacyidea.lib.cache.auth.encryptPassword",
                       side_effect=Exception("HSM not ready")):
                # Nothing could be cached, so this went to the database instead
                # of raising
                self.assertGreater(add_to_cache(self.username, self.realm, self.resolver, self.password), 0)

    def test_17_the_cache_reports_that_it_holds_the_entries(self):
        with auth_cache_in_store(self._real_client):
            self.assertTrue(cache_enabled())
        with auth_cache_in_store(self._real_client, enabled=False):
            self.assertFalse(cache_enabled())
        with auth_cache_in_store(None):
            self.assertFalse(cache_enabled())

    def test_18_a_disabled_cache_uses_the_database(self):
        with auth_cache_in_store(self._real_client, enabled=False):
            row_id = add_to_cache(self.username, self.realm, self.resolver, self.password)
            self.assertGreater(row_id, 0)
            first_auth, last_auth = self._windows()
            self.assertTrue(verify_in_cache(self.username, self.realm, self.resolver, self.password,
                                            first_auth=first_auth, last_auth=last_auth))
        self.assertEqual([], list(self._real_client.scan_iter(match="pi:authcache:*")))
        delete_from_cache(self.username, self.realm, self.resolver, self.password)


@pytest.mark.skipif(not _TEST_REDIS_URL,
                    reason="TEST_REDIS_URL not set - start compose-dev's Redis or export the env var")
class RedisAuthCachePolicyTestCase(MyTestCase):
    """
    The cache as the ``auth_cache`` policy actually drives it.

    The tests above call the cache functions directly. These go through the
    policy decorator, which is what works out the window an entry belongs to and
    hands it to the cache.
    """

    password = "secret123456"
    username = "cornelius"
    realm = "authcacherealm"
    resolver = "authcachereso"

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
        save_resolver({"resolver": cls.resolver,
                       "type": "passwdresolver",
                       "fileName": "tests/testdata/passwords"})
        set_realm(cls.realm, [{"name": cls.resolver}])

    @classmethod
    def tearDownClass(cls):
        delete_realm(cls.realm)
        delete_resolver(cls.resolver)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        keys = list(type(self)._real_client.scan_iter(match="pi:authcache:*"))
        if keys:
            type(self)._real_client.delete(*keys)

    def _options(self):
        fake_g = FakeFlaskG()
        fake_g.policy_object = PolicyClass()
        fake_g.audit_object = FakeAudit()
        return {"g": fake_g}

    def test_01_the_second_authentication_comes_from_redis(self):
        set_policy(name="authcachepol", scope=SCOPE.AUTH, realm=self.realm, resolver=self.resolver,
                   action=f"{PolicyAction.AUTH_CACHE!s}=4h/5m")
        try:
            def authenticate(user, passw, options=None):
                return True, {"message": "Fake Authentication"}

            with auth_cache_in_store(self._real_client):
                user = User(self.username, self.realm)
                # Nothing is cached yet, so the real authentication runs and its
                # result is cached on the way out
                result = auth_cache(authenticate, user, self.password, options=self._options())
                self.assertTrue(result[0])
                self.assertEqual("Fake Authentication", result[1].get("message"))

                # The next one is answered by the cache
                result = auth_cache(authenticate, user, self.password, options=self._options())
                self.assertTrue(result[0])
                self.assertEqual("Authenticated by AuthCache.", result[1].get("message"))

            self.assertEqual(0, AuthCache.query.filter(AuthCache.username == self.username).count())
            # The policy's first interval is the entry's lifetime, so a password
            # cannot stay usable for longer than the policy grants
            key = f"pi:authcache:v1:{self.username}:{self.realm}:{self.resolver}"
            ttl = self._real_client.ttl(key)
            self.assertGreater(ttl, 4 * 3600 - 60)
            self.assertLessEqual(ttl, 4 * 3600)
        finally:
            delete_policy("authcachepol")

    def test_02_a_wrong_password_is_never_served_from_the_cache(self):
        set_policy(name="authcachepol", scope=SCOPE.AUTH, realm=self.realm, resolver=self.resolver,
                   action=f"{PolicyAction.AUTH_CACHE!s}=4h/5m")
        try:
            def authenticate(user, passw, options=None):
                return passw == self.password, {"message": "Fake Authentication"}

            with auth_cache_in_store(self._real_client):
                user = User(self.username, self.realm)
                auth_cache(authenticate, user, self.password, options=self._options())
                # A wrong password reaches the real authentication and fails
                # there, whatever this user has cached
                result = auth_cache(authenticate, user, "wrongpassword", options=self._options())
                self.assertFalse(result[0])
                # ... and the right one still works afterwards
                result = auth_cache(authenticate, user, self.password, options=self._options())
                self.assertTrue(result[0])
                self.assertEqual("Authenticated by AuthCache.", result[1].get("message"))
        finally:
            delete_policy("authcachepol")

    def test_03_the_number_of_allowed_authentications_is_honoured(self):
        set_policy(name="authcachepol", scope=SCOPE.AUTH, realm=self.realm, resolver=self.resolver,
                   action=f"{PolicyAction.AUTH_CACHE!s}=4h/2")
        try:
            real_authentications = []

            def authenticate(user, passw, options=None):
                real_authentications.append(passw)
                return True, {"message": "Fake Authentication"}

            with auth_cache_in_store(self._real_client):
                user = User(self.username, self.realm)
                auth_cache(authenticate, user, self.password, options=self._options())
                self.assertEqual(1, len(real_authentications))
                # Two uses of the entry are allowed
                for _ in range(2):
                    result = auth_cache(authenticate, user, self.password, options=self._options())
                    self.assertEqual("Authenticated by AuthCache.", result[1].get("message"))
                self.assertEqual(1, len(real_authentications))
                # The third has to authenticate for real again
                result = auth_cache(authenticate, user, self.password, options=self._options())
                self.assertEqual("Fake Authentication", result[1].get("message"))
                self.assertEqual(2, len(real_authentications))
        finally:
            delete_policy("authcachepol")
