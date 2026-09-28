# SPDX-FileCopyrightText: (C) 2023 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
import datetime

from sqlalchemy import select

from .base import CliTestCase
from privacyidea.cli.tools.usercache_cleanup import delete as privacyidea_usercache_cleanup
from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config
from privacyidea.lib.usercache import EXPIRATION_SECONDS, delete_user_cache
from privacyidea.models import UserCache, db


def add_cache_entry(username: str, age: datetime.timedelta) -> int:
    """Add a user cache entry for ``username`` that was written ``age`` ago and return its id."""
    timestamp = datetime.datetime.now() - age
    return UserCache(username, username, "cacheresolver", f"uid-{username}", timestamp).save()


def cached_usernames() -> list[str]:
    return sorted(db.session.scalars(select(UserCache.username)).all())


class PIUsercacheCleanupTestCase(CliTestCase):
    def setUp(self) -> None:
        self.addCleanup(delete_user_cache)
        self.addCleanup(delete_privacyidea_config, EXPIRATION_SECONDS)

    def add_expired_and_fresh_entry(self) -> int:
        """
        Enable the user cache with a lifetime of ten minutes and add one entry that is an hour old and one that is
        a minute old. Return the id of the expired entry.
        """
        set_privacyidea_config(EXPIRATION_SECONDS, 600)
        expired_id = add_cache_entry("expireduser", datetime.timedelta(hours=1))
        add_cache_entry("freshuser", datetime.timedelta(minutes=1))
        return expired_id

    def test_01_piusercachecleanup_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(privacyidea_usercache_cleanup, ["-h"])
        self.assertIn("Delete all cache entries that are considered expired according to",
                      result.output, result)

    def test_02_expired_entries_are_deleted(self):
        # Only the entry older than UserCacheExpiration is removed, the one within the lifetime stays.
        expired_id = self.add_expired_and_fresh_entry()

        runner = self.app.test_cli_runner()
        result = runner.invoke(privacyidea_usercache_cleanup, [])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("expireduser", result.output, result)
        self.assertNotIn("freshuser", result.output, result)
        self.assertIn(f"Deleting entry with id={expired_id} ...", result.output, result)
        self.assertIn("Deleted 1 expired entries.", result.output, result)
        self.assertEqual(["freshuser"], cached_usernames())

    def test_03_noaction_lists_expired_entries_and_deletes_nothing(self):
        self.add_expired_and_fresh_entry()

        runner = self.app.test_cli_runner()
        for noaction_option in ["-n", "--noaction"]:
            result = runner.invoke(privacyidea_usercache_cleanup, [noaction_option])
            self.assertEqual(0, result.exit_code, result.output)
            self.assertIn("expireduser", result.output, result)
            self.assertNotIn("freshuser", result.output, result)
            self.assertIn("1 entries", result.output, result)
            self.assertIn("'--noaction' was passed, not doing anything.", result.output, result)
            self.assertNotIn("Deleting entry", result.output, result)
            self.assertEqual(["expireduser", "freshuser"], cached_usernames())

    def test_04_disabled_cache_deletes_nothing(self):
        # With a lifetime of 0 the user cache is disabled, so even very old entries are left alone.
        set_privacyidea_config(EXPIRATION_SECONDS, 0)
        add_cache_entry("olduser", datetime.timedelta(days=30))

        runner = self.app.test_cli_runner()
        result = runner.invoke(privacyidea_usercache_cleanup, [])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("User cache is disabled, not doing anything.", result.output, result)
        self.assertNotIn("Expired entries", result.output, result)
        self.assertEqual(["olduser"], cached_usernames())

    def test_05_no_expired_entries(self):
        set_privacyidea_config(EXPIRATION_SECONDS, 600)
        add_cache_entry("freshuser", datetime.timedelta(minutes=1))

        runner = self.app.test_cli_runner()
        result = runner.invoke(privacyidea_usercache_cleanup, [])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("0 entries", result.output, result)
        self.assertIn("Deleted 0 expired entries.", result.output, result)
        self.assertEqual(["freshuser"], cached_usernames())
