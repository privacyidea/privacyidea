"""
Running-again test for migration d4f5a6b7c8e9
v3.14: Add usersetting table for per-principal frontend settings

upgrade()   — creates the usersetting table, then each of its indexes that does not exist yet

After the upgrade stopped between the table and its indexes, it runs again and creates the missing indexes.
"""

import os

import pytest
from sqlalchemy import inspect

from tests.migration_test_utils import MigrationTestBase

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

INDEX_NAMES = {
    "ix_usersetting_subject_type_username",
    "ix_usersetting_user",
}


class TestMigrationD4f5a6b7c8e9(MigrationTestBase):
    REVISION = "d4f5a6b7c8e9"
    PARENT_REVISION = "c2d3e4f5a6b7"

    def test_upgrade_runs_again_after_failing_before_the_indexes(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
        finally:
            engine.dispose()

        self._upgrade_failing_after(r"CREATE TABLE usersetting\b")
        self._upgrade()

        engine = self._engine()
        try:
            index_names = {(index["name"] or "").lower() for index in inspect(engine).get_indexes("usersetting")}
        finally:
            engine.dispose()
        assert INDEX_NAMES <= index_names, INDEX_NAMES - index_names
