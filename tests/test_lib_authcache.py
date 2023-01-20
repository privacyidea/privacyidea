"""
This test file tests the lib.auth_cache.py

The lib.auth_cache.py only depends on the database model.
"""
from .base import MyTestCase

from privacyidea.lib.authcache import (add_to_cache, delete_from_cache,
                                       update_cache, verify_in_cache,
                                       _hash_password,
                                       cleanup)
from passlib.hash import argon2
from privacyidea.models import AuthCache
import datetime


class AuthCacheTestCase(MyTestCase):
    """
    Test the policies on a database level
    """
    password = "secret123456"
    username = "hans"
    realm = "realm"
    resolver = "resolver"

    def test_01_write_update_delete_cache(self):
        teststart = datetime.datetime.utcnow()

        r = add_to_cache(self.username, self.realm, self.resolver, self.password)

        self.assertTrue(r > 0)

        auth = AuthCache.query.filter(AuthCache.id == r).first()
        self.assertEqual(auth.username, self.username)
        self.assertTrue(argon2.verify(self.password, auth.authentication))

        self.assertTrue(auth.first_auth > teststart)
        self.assertEqual(auth.last_auth, auth.first_auth)

        update_cache(r)
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
        ac_id = add_to_cache(self.username, self.realm, self.resolver, self.password)

        auth = AuthCache.query.filter(AuthCache.id == ac_id).first()
        last_auth1 = auth.last_auth
        auth_count1 = auth.auth_count
        self.assertEqual(0, auth_count1)

        first_auth = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
        last_auth = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)

        r = verify_in_cache(self.username, self.realm, self.resolver,
                            self.password, first_auth=first_auth,
                            last_auth=last_auth, max_auths=1)
        self.assertTrue(r)

        # The last_auth was increased!
        auth = AuthCache.query.filter(AuthCache.id == ac_id).first()
        last_auth2 = auth.last_auth
        auth_count2 = auth.auth_count
        self.assertTrue(last_auth2 > last_auth1)
        self.assertEqual(1, auth_count2)

        r = verify_in_cache(self.username, self.realm, self.resolver,
                            self.password, first_auth=first_auth,
                            last_auth=last_auth, max_auths=1)
        self.assertFalse(r)

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

    def test_05_old_hashes(self):
        from privacyidea.lib.crypto import hash
        # Test that old hashes do not break the code
        r = cleanup(100000000)
        # Add an entry with an old password hash
        AuthCache("grandpa", self.realm, self.resolver, hash("old password", seed=""),
                  first_auth=datetime.datetime.utcnow() - datetime.timedelta(
                      minutes=10),
                  last_auth=datetime.datetime.utcnow() - datetime.timedelta(
                      minutes=2)).save()

        r = verify_in_cache("grandpa", self.realm, self.resolver, "old password")
        self.assertFalse(r)

    def test_06_delete_other_invalid_entries(self):
        # Test deletion of expired entries
        r1 = add_to_cache(self.username, self.realm, self.resolver, "somethingDifferent")
        r2 = add_to_cache(self.username, self.realm, self.resolver, self.password)

        auth1 = AuthCache.query.filter(AuthCache.id == r1).first()
        auth2 = AuthCache.query.filter(AuthCache.id == r2).first()
        last_valid_cache_time = auth1.first_auth
        new_valid_cache_time = auth2.first_auth

        self.assertFalse(auth1.first_auth == auth2.first_auth)

        # delete entries where password matches or first_auth is older than last_valid_cache_time
        delete_from_cache(self.username, self.realm, self.resolver, self.password,
                          last_valid_cache_time=last_valid_cache_time)

        auth = AuthCache.query.filter(AuthCache.username == self.username).first()
        # r2 should have been deleted since the password matches,
        # r1 is still there since it's first_auth is equal to last_valid_cache_time
        self.assertEqual(auth.id, r1)

        # by setting the last_valid_cache_time to the first_auth of r2, the
        # entry r1 should be deleted as well
        delete_from_cache(self.username, self.realm, self.resolver, 'unknown_pw',
                          last_valid_cache_time=new_valid_cache_time)

        auth = AuthCache.query.filter(AuthCache.username == self.username).first()
        self.assertEqual(None, auth)

        # Test deletion if max_auths is reached
        r1 = add_to_cache(self.username, self.realm, self.resolver, self.password)
        r2 = add_to_cache(self.username, self.realm, self.resolver, "somethingDifferent")

        update_cache(r2)
        update_cache(r2)

        auth2 = AuthCache.query.filter(AuthCache.id == r2).first()

        self.assertEqual(2, auth2.auth_count)
        # this deletes the entries matching the password and max_auth
        delete_from_cache(self.username, self.realm, self.resolver, self.password, max_auths=2)

        auth = AuthCache.query.filter(AuthCache.username == self.username).first()
        self.assertEqual(auth, None)
