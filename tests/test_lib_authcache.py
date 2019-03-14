"""
This test file tests the lib.auth_cache.py

The lib.auth_cache.py only depends on the database model.
"""
from .base import MyTestCase

from privacyidea.lib.authcache import (add_to_cache, delete_from_cache,
                                       update_cache_last_auth, verify_in_cache,
                                       _hash_password,
                                       cleanup)
from privacyidea.models import AuthCache
import datetime


class AuthCacheTestCase(MyTestCase):
    """
    Test the policies on a database level
    """
    password = u"secret123456"
    username = "hans"
    realm = "realm"
    resolver = "resolver"

    def test_01_write_update_delete_cache(self):
        teststart = datetime.datetime.utcnow()

        r = add_to_cache(self.username, self.realm, self.resolver, self.password)

        self.assertTrue(r > 0)

        auth = AuthCache.query.filter(AuthCache.id == r).first()
        self.assertEqual(auth.username, self.username)
        self.assertEqual(auth.authentication, _hash_password(self.password))

        self.assertTrue(auth.first_auth > teststart)
        self.assertEqual(auth.last_auth, auth.first_auth)

        update_cache_last_auth(r)
        auth = AuthCache.query.filter(AuthCache.id == r).first()
        self.assertTrue(auth.last_auth > teststart)

        r_delete = delete_from_cache(self.username, self.realm, self.resolver,
                                     self.password)
        self.assertEqual(r, r_delete)

        auth = AuthCache.query.filter(AuthCache.username ==
                                      self.username).first()
        self.assertEqual(auth, None)

    def test_02_verify_cache(self):
        # Verify if no entry in cache
        r = verify_in_cache(self.username, self.realm, self.resolver,
                            self.password)
        self.assertFalse(r)

        # Add Entry to cache
        r = add_to_cache(self.username, self.realm, self.resolver, self.password)
        update_cache_last_auth(r)
        auth = AuthCache.query.filter(AuthCache.id == r).first()
        last_auth1 = auth.last_auth

        first_auth = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
        last_auth = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)

        r = verify_in_cache(self.username, self.realm, self.resolver,
                            self.password, first_auth=first_auth,
                            last_auth=last_auth)
        self.assertTrue(r)

        # The last_auth was increased!
        auth = AuthCache.query.filter(AuthCache.id == r).first()
        last_auth2 = auth.last_auth
        self.assertTrue(last_auth2 > last_auth1)

    def test_03_delete_old_entries(self):
        # Create a VERY old authcache entry
        AuthCache("grandpa", self.realm, self.resolver, _hash_password(self.password),
                  first_auth=datetime.datetime.utcnow() - datetime.timedelta(
                      days=10),
                  last_auth=datetime.datetime.utcnow() - datetime.timedelta(
                      days=2)).save()

        r = verify_in_cache(
            "grandpa", self.realm, self.resolver,
            self.password,
            first_auth=datetime.datetime.utcnow() - datetime.timedelta(hours=4),
            last_auth=datetime.datetime.utcnow() - datetime.timedelta(
                minutes=5))
        # Verification for grandpa fails.
        self.assertFalse(r)
        # The verify_in_cache should have deleted old grandpa entries:
        r = AuthCache.query.filter(AuthCache.username == "grandpa").first()
        self.assertEqual(r, None)

    def test_04_cleanup_authcache(self):
        # cleanup everything!
        r = cleanup(100000000)
        # Create some entries:
        AuthCache("grandpa", self.realm, self.resolver, _hash_password(self.password),
                  first_auth=datetime.datetime.utcnow() - datetime.timedelta(
                      days=10),
                  last_auth=datetime.datetime.utcnow() - datetime.timedelta(
                      days=2)).save()
        AuthCache("grandpa", self.realm, self.resolver, _hash_password(self.password),
                  first_auth=datetime.datetime.utcnow() - datetime.timedelta(
                      minutes=10),
                  last_auth=datetime.datetime.utcnow() - datetime.timedelta(
                      minutes=2)).save()

        # Now we delete entries, that are older than 20 minutes. Only the 2 days old
        # should be deleted. Not the 2 minutes old.
        r = cleanup(10)
        self.assertEqual(1, r)

