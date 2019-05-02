# coding: utf-8
"""
This test file tests the lib.usercache

The lib.usercache.py only depends on the database model
"""
from contextlib import contextmanager

from mock import patch

from privacyidea.lib.error import UserError
from tests import ldap3mock
from tests.test_mock_ldap3 import LDAPDirectory
from .base import MyTestCase
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPResolver
from privacyidea.lib.resolver import (save_resolver, delete_resolver, get_resolver_object)
from privacyidea.lib.realm import (set_realm, delete_realm)
from privacyidea.lib.user import (User, get_username, create_user)
from privacyidea.lib.usercache import (get_cache_time,
                                       cache_username, delete_user_cache,
                                       EXPIRATION_SECONDS, retrieve_latest_entry, is_cache_enabled)
from privacyidea.lib.config import set_privacyidea_config, get_from_config
from datetime import timedelta
from datetime import datetime
from privacyidea.models import UserCache


class UserCacheTestCase(MyTestCase):
    """
    Test the user on the database level
    """
    PWFILE = "tests/testdata/passwd"
    resolvername1 = "resolver1"
    realm1 = "realm1"
    username = "root"
    uid = "0"

    sql_realm = "sqlrealm"
    sql_resolver = "SQL1"
    sql_parameters = {'Driver': 'sqlite',
                  'Server': '/tests/testdata/',
                  'Database': "testusercache.sqlite",
                  'Table': 'users',
                  'Encoding': 'utf8',
                  'Map': '{ "username": "username", \
                    "userid" : "id", \
                    "email" : "email", \
                    "surname" : "name", \
                    "givenname" : "givenname", \
                    "password" : "password", \
                    "phone": "phone", \
                    "mobile": "mobile"}',
                  'resolver': sql_resolver,
                  'type': 'sqlresolver',
    }

    def _create_realm(self):

        rid = save_resolver({"resolver": self.resolvername1,
                               "type": "passwdresolver",
                               "fileName": self.PWFILE,
                               "type.fileName": "string",
                               "desc.fileName": "The name of the file"})
        self.assertTrue(rid > 0, rid)
        added, failed = set_realm(realm=self.realm1, resolvers=[self.resolvername1])
        self.assertTrue(len(added) > 0, added)
        self.assertEqual(len(failed), 0)

    def _delete_realm(self):
        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    def test_00_set_config(self):
        # Save wrong data in EXPIRATION_SECONDS
        set_privacyidea_config(EXPIRATION_SECONDS, "wrong")
        exp_delta = get_cache_time()
        self.assertEqual(exp_delta, timedelta(seconds=0))
        self.assertFalse(is_cache_enabled())

        # Save empty data in EXPIRATION_SECONDS
        set_privacyidea_config(EXPIRATION_SECONDS, "")
        exp_delta = get_cache_time()
        self.assertEqual(exp_delta, timedelta(seconds=0))
        self.assertFalse(is_cache_enabled())

        # Save real data in EXPIRATION_SECONDS
        set_privacyidea_config(EXPIRATION_SECONDS, 600)
        exp_delta = get_cache_time()
        self.assertEqual(exp_delta, timedelta(seconds=600))
        self.assertTrue(is_cache_enabled())

    def test_01_get_username_from_cache(self):
        # If a username is already contained in the cache, the function
        # lib.user.get_username will return the cache value
        username = "cached_user"
        resolver = "resolver1"
        uid = "1"

        expiration_delta = get_cache_time()
        r = UserCache(username, username, resolver, uid, datetime.now()).save()
        u_name = get_username(uid, resolver)
        self.assertEqual(u_name, username)

        # A non-existing user is not in the cache and returns and empty username
        u_name = get_username(uid, "resolver_does_not_exist")
        self.assertEqual(u_name, "")

    def test_02_get_resolvers(self):
        # create realm
        self._create_realm()
        # delete user_cache
        r = delete_user_cache()
        self.assertTrue(r >= 0)

        # The username is not in the cache. It is fetched from the resolver
        # At the same time the cache is filled.
        user = User(self.username, self.realm1)
        self.assertEqual(user.login, self.username)
        # The user ID is fetched from the resolver
        self.assertEqual(user.uid, self.uid)

        # Now, the cache should have exactly one entry
        entry = UserCache.query.one()
        self.assertEqual(entry.user_id, self.uid)
        self.assertEqual(entry.username, self.username)
        self.assertEqual(entry.resolver, self.resolvername1)

        # delete the resolver, which also purges the cache
        self._delete_realm()

        # manually re-add the entry from above
        UserCache(entry.username, entry.username, entry.resolver, entry.user_id, entry.timestamp).save()

        # the username is fetched from the cache
        u_name = get_username(self.uid, self.resolvername1)
        self.assertEqual(u_name, self.username)

        # delete the cache
        r = delete_user_cache()

        # try to fetch the username. It is not in the cache and the
        # resolver does not exist anymore.
        u_name = get_username(self.uid, self.resolvername1)
        self.assertEqual(u_name, "")

    def test_03_get_identifiers(self):
        # create realm
        self._create_realm()
        # delete user_cache
        r = delete_user_cache()
        self.assertTrue(r >= 0)

        # The username is not in the cache. It is fetched from the resolver
        # At the same time the cache is filled. Implicitly we test the
        # _get_resolvers!
        user = User(self.username, self.realm1, self.resolvername1)
        uids = user.get_user_identifiers()
        self.assertEqual(user.login, self.username)
        self.assertEqual(user.uid, self.uid)

        # Now, the cache should have exactly one entry
        entry = UserCache.query.one()
        self.assertEqual(entry.user_id, self.uid)
        self.assertEqual(entry.username, self.username)
        self.assertEqual(entry.resolver, self.resolvername1)

        # delete the resolver, which also purges the cache
        self._delete_realm()

        # manually re-add the entry from above
        UserCache(entry.username, entry.username, entry.resolver, entry.user_id, entry.timestamp).save()

        # the username is fetched from the cache
        u_name = get_username(self.uid, self.resolvername1)
        self.assertEqual(u_name, self.username)

        # The `User` class also fetches the UID from the cache
        user2 = User(self.username, self.realm1, self.resolvername1)
        self.assertEqual(user2.uid, self.uid)

        # delete the cache
        r = delete_user_cache()

        # try to fetch the username. It is not in the cache and the
        # resolver does not exist anymore.
        u_name = get_username(self.uid, self.resolvername1)
        self.assertEqual(u_name, "")

        # similar case for the `User` class
        # The `User` class also tries to fetch the UID from the cache
        with self.assertRaises(UserError):
            user3 = User(self.username, self.realm1, self.resolvername1)


    def test_04_delete_cache(self):
        now = datetime.now()
        UserCache("hans1", "hans1", "resolver1", "uid1", now).save()
        UserCache("hans2", "hans1", "resolver2", "uid2", now).save()

        r = UserCache.query.filter(UserCache.username == "hans1").first()
        self.assertTrue(r)
        r = UserCache.query.filter(UserCache.username == "hans2").first()
        self.assertTrue(r)

        # delete hans1
        delete_user_cache(username="hans1")
        r = UserCache.query.filter(UserCache.username == "hans1").first()
        self.assertFalse(r)
        r = UserCache.query.filter(UserCache.username == "hans2").first()
        self.assertTrue(r)

        # delete resolver2
        delete_user_cache(resolver="resolver2")
        r = UserCache.query.filter(UserCache.username == "hans1").first()
        self.assertFalse(r)
        r = UserCache.query.filter(UserCache.username == "hans2").first()
        self.assertFalse(r)

    def test_05_multiple_entries(self):
        # two consistent entries
        now = datetime.now()
        UserCache("hans1", "hans1", "resolver1", "uid1", now - timedelta(seconds=60)).save()
        UserCache("hans1", "hans1", "resolver1", "uid1", now).save()

        r = UserCache.query.filter(UserCache.username == "hans1", UserCache.resolver == "resolver1")
        self.assertEquals(r.count(), 2)

        u_name = get_username("uid1", "resolver1")
        self.assertEqual(u_name, "hans1")

        r = delete_user_cache()

        # two inconsistent entries: most recent entry (ordered by datetime) wins
        UserCache("hans2", "hans2", "resolver1", "uid1", now).save()
        UserCache("hans1", "hans1", "resolver1", "uid1", now - timedelta(seconds=60)).save()

        r = UserCache.query.filter(UserCache.user_id == "uid1", UserCache.resolver == "resolver1")
        self.assertEquals(r.count(), 2)

        u_name = get_username("uid1", "resolver1")
        self.assertEqual(u_name, "hans2")

        # Clean up the cache
        r = delete_user_cache()

    def test_06_implicit_cache_population(self):
        self._create_realm()
        # testing `get_username`
        self.assertEquals(UserCache.query.count(), 0)
        # the cache is empty, so the username is read from the resolver
        u_name = get_username(self.uid, self.resolvername1)
        self.assertEqual(self.username, u_name)
        # it should be part of the cache now
        r = UserCache.query.filter(UserCache.user_id == self.uid, UserCache.resolver == self.resolvername1).one()
        self.assertEqual(self.username, r.username)
        # Apart from that, the cache should be empty.
        self.assertEqual(UserCache.query.count(), 1)
        r = delete_user_cache()

        # testing `User()`, but this time we add an already-expired entry to the cache
        self.assertEquals(UserCache.query.count(), 0)
        UserCache(self.username, self.username,
                  self.resolvername1, 'fake_uid', datetime.now() - timedelta(weeks=50)).save()
        # cache contains an expired entry, uid is read from the resolver (we can verify
        # that the cache entry is indeed not queried as it contains 'fake_uid' instead of the correct uid)
        user = User(self.username, self.realm1, self.resolvername1)
        self.assertEqual(user.uid, self.uid)
        # a new entry should have been added to the cache now
        r = retrieve_latest_entry((UserCache.username == self.username) & (UserCache.resolver == self.resolvername1))
        self.assertEqual(self.uid, r.user_id)
        # But the expired entry is also still in the cache
        self.assertEqual(UserCache.query.count(), 2)
        r = delete_user_cache()

        self._delete_realm()

    def _populate_cache(self):
        self.assertEquals(UserCache.query.count(), 0)
        # initially populate the cache with three entries
        timestamp = datetime.now()
        UserCache("hans1", "hans1", self.resolvername1, "uid1", timestamp).save()
        UserCache("hans2", "hans2", self.resolvername1, "uid2", timestamp - timedelta(weeks=50)).save()
        UserCache("hans3", "hans3", "resolver2", "uid2", timestamp).save()
        self.assertEquals(UserCache.query.count(), 3)

    def test_07_invalidate_save_resolver(self):
        self._create_realm()
        self._populate_cache()
        # call save_resolver on resolver1, which should invalidate all entries of "resolver1"
        # (even the expired 'hans2' one)
        save_resolver({"resolver": self.resolvername1,
             "type": "passwdresolver",
             "fileName": self.PWFILE,
             "type.fileName": "string",
             "desc.fileName": "Some change"
        })
        self.assertEquals(UserCache.query.count(), 1)
        # Only hans3 in resolver2 should still be in the cache
        # We can use get_username to ensure it is fetched from the cache
        # because resolver2 does not actually exist
        u_name = get_username("uid2", "resolver2")
        self.assertEquals("hans3", u_name)
        delete_user_cache()
        self._delete_realm()

    def test_08_invalidate_delete_resolver(self):
        self._create_realm()
        self._populate_cache()
        # call delete_resolver on resolver1, which should invalidate all of its entries
        self._delete_realm()
        self.assertEquals(UserCache.query.count(), 1)
        # Only hans3 in resolver2 should still be in the cache
        u_name = get_username("uid2", "resolver2")
        self.assertEquals("hans3", u_name)
        delete_user_cache()

    def _create_sql_realm(self):
        rid = save_resolver(self.sql_parameters)
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.sql_realm, [self.sql_resolver])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

    def _delete_sql_realm(self):
        delete_realm(self.sql_realm)
        delete_resolver(self.sql_resolver)

    def test_09_invalidate_edit_user(self):
        # Validate that editing users actually invalidates the cache. For that, we first need an editable resolver
        self._create_sql_realm()
        # The cache is initially empty
        self.assertEquals(UserCache.query.count(), 0)
        # The following adds an entry to the cache
        user = User(login="wordpressuser", realm=self.sql_realm)
        self.assertEquals(UserCache.query.count(), 1)
        uinfo = user.info
        self.assertEqual(uinfo.get("givenname", ""), "")

        user.update_user_info({"givenname": "wordy"})
        uinfo = user.info
        self.assertEqual(uinfo.get("givenname"), "wordy")
        # This should have removed the entry from the cache
        self.assertEqual(UserCache.query.count(), 0)
        # But now it gets added again
        user2 = User(login="wordpressuser", realm=self.sql_realm)
        self.assertEqual(UserCache.query.count(), 1)
        # Change it back for the other tests
        user.update_user_info({"givenname": ""})
        uinfo = user.info
        self.assertEqual(uinfo.get("givenname", ""), "")
        self.assertEqual(UserCache.query.count(), 0)
        self._delete_sql_realm()

    def test_10_invalidate_delete_user(self):
        # Validate that deleting users actually invalidates the cache. For that, we first need an editable resolver
        self._create_sql_realm()
        # The cache is initially empty
        self.assertEquals(UserCache.query.count(), 0)
        # The following adds an entry to the cache
        user = User(login="wordpressuser", realm=self.sql_realm)
        self.assertEquals(UserCache.query.count(), 1)
        uinfo = user.info
        user.delete()
        # This should have removed the entry from the cache
        self.assertEqual(UserCache.query.count(), 0)
        # We add the user again for the other tests
        create_user(self.sql_resolver, uinfo)
        self.assertEqual(UserCache.query.count(), 0)
        self._delete_sql_realm()

    @contextmanager
    def _patch_datetime_now(self, target, delta=timedelta(days=1)):
        with patch(target) as mock_datetime:
            mock_datetime.now.side_effect = lambda: datetime.now() + delta
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            yield mock_datetime

    def test_11_cache_expiration(self):
        # delete user_cache
        r = delete_user_cache()
        self.assertTrue(r >= 0)
        # populate the cache with artificial, somewhat "old", but still relevant data
        timestamp = datetime.now() - timedelta(seconds=300)
        UserCache("hans1", "hans1", "resolver1", "uid1", timestamp).save()
        UserCache("hans2", "hans2", "resolver1", "uid2", timestamp).save()
        # check that the cache is indeed queried
        self.assertEqual(get_username("uid1", "resolver1"), "hans1")
        self.assertEqual(User("hans2", "realm1", "resolver1").uid, "uid2")
        # check that the (non-existent) resolver is queried
        # for entries not contained in the cache
        self.assertEqual(get_username("uid3", "resolver1"), "")

        # TODO: Interestingly, if we mock `datetime` here to increase the time by one
        # day, this test works, but a subsequent test (test_ui_certificate) will fail
        # with weird error messages. So we do not use the datetime mock for now.
        #with self._patch_datetime_now('privacyidea.lib.usercache.datetime.datetime') as mock_datetime:
        with patch('privacyidea.lib.usercache.get_cache_time') as mock_get_cache_time:
            # Instead, we just decrease the cache time from 600 to 60 seconds,
            # which causes the entries above to be considered expired
            mock_get_cache_time.return_value = timedelta(seconds=60)
            # check that the cached entries are not queried anymore
            self.assertEqual(UserCache.query.count(), 2)
            self.assertEqual(get_username("uid1", "resolver1"), "")
            with self.assertRaises(UserError):
                User("hans2", "realm1", "resolver1")
            self.assertEqual(get_username("uid3", "resolver1"), "")
            # We add another, "current" entry
            UserCache("hans4", "hans4", "resolver1", "uid4", datetime.now()).save()
            self.assertEqual(UserCache.query.count(), 3)
            # we now remove old entries, only the newest remains
            delete_user_cache(expired=True)
            self.assertEqual(UserCache.query.count(), 1)
            self.assertEqual(UserCache.query.one().user_id, "uid4")
        # clean up
        delete_user_cache()

    def test_12_multiple_resolvers(self):
        # one realm, two SQL resolvers
        parameters_a = self.sql_parameters.copy()
        # first resolver only contains users with phone numbers
        parameters_a['Where'] = 'phone LIKE %'
        parameters_a['resolver'] = 'reso_a'
        rid_a = save_resolver(parameters_a)
        self.assertTrue(rid_a > 0, rid_a)
        # second resolver contains all users
        parameters_b = self.sql_parameters.copy()
        parameters_b['resolver'] = 'reso_b'
        rid_b = save_resolver(parameters_b)
        self.assertTrue(rid_b > 0, rid_b)

        # First ask reso_a, then reso_b
        (added, failed) = set_realm(self.sql_realm, ['reso_a', 'reso_b'], {
            'reso_a': 1,
            'reso_b': 2
        })
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 2)

        # Now, query the user and populate the cache
        self.assertEqual(UserCache.query.count(), 0)
        user1 = User('wordpressuser', self.sql_realm)
        self.assertEqual(user1.uid, 6)
        # Assert it was found in reso_b (as it does not have a phone number)!
        self.assertEqual(user1.resolver, 'reso_b')
        self.assertEqual(UserCache.query.filter(UserCache.username == 'wordpressuser',
                                                UserCache.user_id == 6).one().resolver,
                         'reso_b')
        # Add a phone number. We do not use the User API to do that to simulate that the change is performed
        # out of privacyIDEA's control. Using `update_user_info` would invalidate the cache, which would be unrealistic.
        info = user1.info
        new_info = info.copy()
        new_info['phone'] = '123456'
        get_resolver_object('reso_a').update_user(user1.uid, new_info)
        # Ensure that the user's association with reso_b is still cached.
        self.assertEqual(UserCache.query.filter(UserCache.username == 'wordpressuser',
                                                UserCache.user_id == 6).one().resolver,
                         'reso_b')
        # Now, it should be located in reso_a!
        user2 = User('wordpressuser', self.sql_realm)
        self.assertEqual(user2.uid, 6)
        self.assertEqual(user2.resolver, 'reso_a')
        # ... but the cache still contains entries for both!
        resolver_query = UserCache.query.filter(UserCache.username == 'wordpressuser',
                                                UserCache.user_id == 6).order_by(UserCache.timestamp.desc())
        cached_resolvers = [entry.resolver for entry in resolver_query.all()]
        self.assertEqual(cached_resolvers, ['reso_a', 'reso_b'])
        # Remove the phone number.
        get_resolver_object('reso_a').update_user(user1.uid, {'phone': None})
        delete_realm(self.sql_realm)
        delete_resolver('reso_a')
        delete_resolver('reso_b')

    def test_13_cache_username(self):

        self.counter = 0

        def get_username(uid, resolver):
            self.counter += 1
            return "user1"

        r = cache_username(get_username, "uid1", "reso1")
        self.assertEqual(r, "user1")
        self.assertEqual(self.counter, 1)

        # The second call does not increase the counter, since the result is fetched from the cache
        r = cache_username(get_username, "uid1", "reso1")
        self.assertEqual(r, "user1")
        self.assertEqual(self.counter, 1)

    def test_99_unset_config(self):
        # Test early exit!
        # Assert that the function `retrieve_latest_entry` is called if the cache is enabled
        with patch('privacyidea.lib.usercache.retrieve_latest_entry') as mock_retrieve:
            mock_retrieve.return_value = None
            get_username('some-userid', 'resolver1')
            self.assertEqual(mock_retrieve.call_count, 1)
        set_privacyidea_config(EXPIRATION_SECONDS, 0)

        self.assertFalse(is_cache_enabled())
        # Assert that the function `retrieve_latest_entry` is not called anymore
        with patch('privacyidea.lib.usercache.retrieve_latest_entry') as mock_retrieve:
            mock_retrieve.return_value = None
            get_username('some-userid', 'resolver1')
            self.assertEqual(mock_retrieve.call_count, 0)


class TestUserCacheMultipleLoginAttributes(MyTestCase):
    ldap_realm = "ldaprealm"
    ldap_resolver = "ldap1"
    ldap_parameters = {'LDAPURI': 'ldap://localhost',
                       'LDAPBASE': 'o=test',
                       'BINDDN': 'cn=manager,ou=example,o=test',
                       'BINDPW': 'ldaptest',
                       'LOGINNAMEATTRIBUTE': 'cn, email',
                       'LDAPSEARCHFILTER': '(cn=*)',
                       'USERINFO': '{"phone" : "telephoneNumber", '
                                   '"mobile" : "mobile"'
                                   ', "email" : "email", '
                                   '"surname" : "sn", '
                                   '"givenname" : "givenName" }',
                       'UIDTYPE': 'DN',
                       'CACHE_TIMEOUT': 0,
                       'resolver': ldap_resolver,
                       'type': 'ldapresolver',
                       }

    def _create_ldap_realm(self):
        rid = save_resolver(self.ldap_parameters)
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.ldap_realm, [self.ldap_resolver])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

    def _delete_ldap_realm(self):
        delete_realm(self.ldap_realm)
        delete_resolver(self.ldap_resolver)

    @classmethod
    def setUpClass(cls):
        MyTestCase.setUpClass()
        set_privacyidea_config(EXPIRATION_SECONDS, 600)

    @classmethod
    def tearDownClass(cls):
        set_privacyidea_config(EXPIRATION_SECONDS, 0)
        MyTestCase.tearDownClass()

    @ldap3mock.activate
    def test_01_secondary_login_attribute(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        self._create_ldap_realm()
        # Populate the user cache, check its contents
        user1 = User('alice', self.ldap_realm)
        self.assertEquals(user1.resolver, self.ldap_resolver)
        self.assertEquals(user1.uid, "cn=alice,ou=example,o=test")
        self.assertEquals(user1.login, "alice")
        self.assertEquals(user1.used_login, "alice")
        entry = UserCache.query.one()
        self.assertEquals(entry.user_id, user1.uid)
        self.assertEquals(entry.used_login, "alice")
        self.assertEquals(entry.username, "alice")
        self.assertEquals(entry.resolver, self.ldap_resolver)
        # query again, user cache does not change
        user2 = User('alice', self.ldap_realm)
        self.assertEquals(user2.resolver, self.ldap_resolver)
        self.assertEquals(user2.uid, "cn=alice,ou=example,o=test")
        self.assertEquals(user2.login, "alice")
        self.assertEquals(user2.used_login, "alice")
        self.assertEquals(UserCache.query.count(), 1)
        # use secondary login attribute, usercache has a new entry with secondary login attribute
        user3 = User('alice@test.com', self.ldap_realm)
        self.assertEquals(user3.resolver, self.ldap_resolver)
        self.assertEquals(user3.uid, "cn=alice,ou=example,o=test")
        self.assertEquals(user3.login, "alice")
        self.assertEquals(user3.used_login, "alice@test.com")
        entries = UserCache.query.filter_by(user_id="cn=alice,ou=example,o=test").order_by(UserCache.id).all()
        self.assertEquals(len(entries), 2)
        entry = entries[-1]
        self.assertEquals(entry.user_id, user1.uid)
        self.assertEquals(entry.used_login, "alice@test.com")
        self.assertEquals(entry.username, "alice")
        self.assertEquals(entry.resolver, self.ldap_resolver)
        # use secondary login attribute again, login name is fetched correctly
        user4 = User('alice@test.com', self.ldap_realm)
        self.assertEquals(user4.resolver, self.ldap_resolver)
        self.assertEquals(user4.uid, "cn=alice,ou=example,o=test")
        self.assertEquals(user4.login, "alice")
        self.assertEquals(user4.used_login, "alice@test.com")
        # still only two entries in the cache
        entries = UserCache.query.filter_by(user_id="cn=alice,ou=example,o=test").order_by(UserCache.id).all()
        self.assertEquals(len(entries), 2)
        # get the primary login name
        login_name = get_username("cn=alice,ou=example,o=test", self.ldap_resolver)
        self.assertEquals(login_name, "alice")
        # still only two entries in the cache
        entries = UserCache.query.filter_by(user_id="cn=alice,ou=example,o=test").order_by(UserCache.id).all()
        self.assertEquals(len(entries), 2)
        self._delete_ldap_realm()
