"""
Running-again test for migration c8d9e0f1a2b3
v3.14: Add remembered_devices table for persistent (remember-device) devices

upgrade()   — creates the remembered_devices table, then each of its indexes that does not exist yet

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
    "ix_remembered_devices_client_id",
    "ix_remembered_devices_resolver",
    "ix_remembered_devices_user_id",
    "ix_remembered_devices_realm_id",
    "ix_remembered_devices_expires_at",
    "ix_remembered_devices_identity",
    "ix_remembered_devices_client_created",
}


class TestMigrationC8d9e0f1a2b3(MigrationTestBase):
    REVISION = "c8d9e0f1a2b3"
    PARENT_REVISION = "b7c8d9e0f1a2"

    def test_upgrade_runs_again_after_failing_before_the_indexes(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
        finally:
            engine.dispose()

        self._upgrade_failing_after(r"CREATE TABLE remembered_devices\b")
        self._upgrade()

        engine = self._engine()
        try:
            index_names = {(index["name"] or "").lower() for index in inspect(engine).get_indexes("remembered_devices")}
        finally:
            engine.dispose()
        assert INDEX_NAMES <= index_names, INDEX_NAMES - index_names
