"""
Data transformation test for migration b4c7e1a9d203
Empty the user cache, whose timestamps were written in local time.

The migration:
- Deletes every row of ``usercache``, because the stored timestamps are local time of the server and cannot be
  told apart from UTC values. The cache is refilled from the resolvers on demand.
- Leaves every other table untouched.

upgrade()   — DELETE FROM usercache
downgrade() — does nothing, the deleted cache entries are not restored
"""

import os
from datetime import datetime

import pytest
import sqlalchemy as sa
from flask import Flask

from tests.migration_test_utils import MigrationTestBase

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


class TestMigrationB4c7e1a9d203(MigrationTestBase):
    REVISION = "b4c7e1a9d203"
    PARENT_REVISION = "56529818c956"

    def _insert_cache_entries(self, engine: sa.engine.Engine, first_id: int = 1001) -> None:
        self._insert_rows(engine, "usercache", [
            {"id": first_id, "username": "cornelius", "used_login": "cornelius", "resolver": "resolver1",
             "user_id": "1000", "timestamp": datetime(2026, 1, 1, 12, 0, 0)},
            {"id": first_id + 1, "username": "hans", "used_login": "hans@example.com", "resolver": "resolver2",
             "user_id": "1001", "timestamp": datetime(2026, 1, 2, 12, 0, 0)},
        ])

    def _insert_auth_cache_entry(self, engine: sa.engine.Engine, entry_id: int = 2001) -> None:
        self._insert_rows(engine, "authcache", [
            {"id": entry_id, "first_auth": datetime(2026, 1, 1, 12, 0, 0),
             "last_auth": datetime(2026, 1, 1, 12, 0, 0), "username": "cornelius", "resolver": "resolver1",
             "realm": "realm1", "client_ip": "10.0.0.1", "user_agent": "pytest", "auth_count": 1,
             "authentication": "hash"},
        ])

    def _usercache_count(self, engine: sa.engine.Engine) -> int:
        return self._fetch_scalar(engine, "SELECT COUNT(*) FROM usercache")

    def _authcache_count(self, engine: sa.engine.Engine) -> int:
        return self._fetch_scalar(engine, "SELECT COUNT(*) FROM authcache")

    def test_upgrade_empties_the_usercache(self, flask_app: Flask):
        """Every cache entry is deleted, whatever its timestamp."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_cache_entries(engine)
            assert self._usercache_count(engine) == 2

            self._upgrade()

            assert self._usercache_count(engine) == 0
        finally:
            engine.dispose()

    def test_upgrade_with_an_empty_usercache_succeeds(self, flask_app: Flask):
        """An already empty cache is no error."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            assert self._usercache_count(engine) == 0

            self._upgrade()

            assert self._usercache_count(engine) == 0
        finally:
            engine.dispose()

    def test_upgrade_leaves_other_tables_untouched(self, flask_app: Flask):
        """The authentication cache is a different table and keeps its rows."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_cache_entries(engine)
            self._insert_auth_cache_entry(engine)

            self._upgrade()

            assert self._usercache_count(engine) == 0
            assert self._authcache_count(engine) == 1
        finally:
            engine.dispose()

    def test_downgrade_does_not_restore_the_usercache(self, flask_app: Flask):
        """The deleted entries stay deleted and unrelated rows stay in place."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_cache_entries(engine)
            self._insert_auth_cache_entry(engine)
            self._upgrade()

            self._downgrade()

            assert self._usercache_count(engine) == 0
            assert self._authcache_count(engine) == 1
        finally:
            engine.dispose()

    def test_downgrade_keeps_entries_written_after_the_upgrade(self, flask_app: Flask):
        """downgrade() does nothing, so a cache entry written in between survives it."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._upgrade()
            self._insert_cache_entries(engine)

            self._downgrade()

            assert self._usercache_count(engine) == 2
        finally:
            engine.dispose()

    def test_round_trip_empties_the_usercache_again_on_the_second_upgrade(self, flask_app: Flask):
        """upgrade, downgrade, upgrade: entries written after the downgrade are removed by the second upgrade."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_cache_entries(engine)
            self._insert_auth_cache_entry(engine)
            self._upgrade()
            self._downgrade()
            self._insert_cache_entries(engine, first_id=1101)
            assert self._usercache_count(engine) == 2

            self._upgrade()

            assert self._usercache_count(engine) == 0
            assert self._authcache_count(engine) == 1
        finally:
            engine.dispose()
