"""
Data test for migration c8d5f2a7b914
Add the nullable entry_version column to the audit table.

upgrade()   — ADD COLUMN entry_version (INTEGER, nullable, no default), if the column is missing.
              Existing audit entries keep NULL, which marks them as written in local time.
downgrade() — DROP COLUMN entry_version, if the column exists

The schema against the model, the round trip, surviving rows and the default insert are tested for every revision
in tests/test_migrations.py. This file only tests the guards for an existing or a missing column.
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


class TestMigrationC8d5f2a7b914(MigrationTestBase):
    REVISION = "c8d5f2a7b914"
    PARENT_REVISION = "b4c7e1a9d203"

    OLD_ID = 9001
    NEW_ID = 9002

    @staticmethod
    def _columns(engine: sa.engine.Engine) -> dict[str, dict]:
        return {column["name"]: column for column in sa.inspect(engine).get_columns("pidea_audit")}

    def _insert_old_entries(self, engine: sa.engine.Engine) -> None:
        self._insert_rows(engine, "pidea_audit", [
            {"id": self.OLD_ID, "date": datetime(2026, 1, 1, 12, 0, 0), "action": "GET /token/",
             "serial": "OATH0001"},
        ])

    def _entry_versions(self, engine: sa.engine.Engine) -> dict[int, int | None]:
        """The entry_version of the entries this test inserted, the seed ships audit entries of its own."""
        with engine.connect() as connection:
            rows = connection.execute(sa.text(
                "SELECT id, entry_version FROM pidea_audit WHERE id IN (:old_id, :new_id)"),
                {"old_id": self.OLD_ID, "new_id": self.NEW_ID}).fetchall()
        return {row[0]: row[1] for row in rows}

    def test_upgrade_succeeds_when_the_column_already_exists(self, flask_app: Flask):
        """A separate audit database may have been changed by hand beforehand."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            with engine.connect() as connection:
                # Oracle takes the column definition in parentheses and has no COLUMN keyword here.
                add_column = ("ADD (entry_version INTEGER)" if engine.dialect.name == "oracle"
                              else "ADD COLUMN entry_version INTEGER")
                connection.execute(sa.text(f"ALTER TABLE pidea_audit {add_column}"))
                connection.commit()
            self._insert_old_entries(engine)

            self._upgrade()

            assert "entry_version" in self._columns(engine)
            assert self._entry_versions(engine) == {self.OLD_ID: None}
        finally:
            engine.dispose()

    def test_downgrade_succeeds_when_the_column_is_missing(self, flask_app: Flask):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._upgrade()
            with engine.connect() as connection:
                connection.execute(sa.text("ALTER TABLE pidea_audit DROP COLUMN entry_version"))
                connection.commit()

            self._downgrade()

            assert "entry_version" not in self._columns(engine)
        finally:
            engine.dispose()
