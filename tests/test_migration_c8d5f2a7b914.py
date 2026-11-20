"""
Data test for migration c8d5f2a7b914
Add the nullable entry_version column to the audit table.

upgrade()   — ADD COLUMN entry_version (INTEGER, nullable, no default), if the column is missing.
              Existing audit entries keep NULL, which marks them as written in local time.
downgrade() — DROP COLUMN entry_version, if the column exists
"""

import os
from datetime import datetime

import pytest
import sqlalchemy as sa

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

    def test_upgrade_adds_a_nullable_integer_column(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            assert "entry_version" not in self._columns(engine)

            self._upgrade()

            columns = self._columns(engine)
            assert "entry_version" in columns
            assert columns["entry_version"]["nullable"] is True
            assert isinstance(columns["entry_version"]["type"], sa.Integer)
            assert columns["entry_version"]["default"] is None
        finally:
            engine.dispose()

    def test_upgrade_leaves_existing_entries_unmarked(self, flask_app):
        """Entries written before the upgrade keep NULL and their other values."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_old_entries(engine)

            self._upgrade()

            assert self._entry_versions(engine) == {self.OLD_ID: None}
            assert self._fetch_scalar(engine, "SELECT serial FROM pidea_audit WHERE id = :id",
                                      {"id": self.OLD_ID}) == "OATH0001"
        finally:
            engine.dispose()

    def test_upgrade_allows_marking_new_entries_with_version_2(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._upgrade()

            self._insert_rows(engine, "pidea_audit", [
                {"id": self.NEW_ID, "date": datetime(2026, 1, 2, 12, 0, 0), "action": "GET /token/",
                 "entry_version": 2},
            ])

            assert self._entry_versions(engine) == {self.NEW_ID: 2}
        finally:
            engine.dispose()

    def test_upgrade_succeeds_when_the_column_already_exists(self, flask_app):
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

    def test_downgrade_drops_the_column_and_keeps_the_entries(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_old_entries(engine)
            self._upgrade()

            self._downgrade()

            assert "entry_version" not in self._columns(engine)
            assert self._fetch_scalar(engine, "SELECT action FROM pidea_audit WHERE id = :id",
                                      {"id": self.OLD_ID}) == "GET /token/"
        finally:
            engine.dispose()

    def test_downgrade_succeeds_when_the_column_is_missing(self, flask_app):
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

    def test_round_trip_adds_the_column_again(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_old_entries(engine)
            self._upgrade()
            self._downgrade()

            self._upgrade()

            assert self._entry_versions(engine) == {self.OLD_ID: None}
        finally:
            engine.dispose()

    FILLER_ROWS = 25
    FILLER_FIRST_ID = 9100

    def _insert_filler_entries(self, engine: sa.engine.Engine) -> None:
        """Fill the table with entries of this test, the number of seeded entries does not matter."""
        self._insert_rows(engine, "pidea_audit", [
            {"id": self.FILLER_FIRST_ID + i, "date": datetime(2026, 1, 1, 12, 0, i % 60),
             "action": "GET /token/", "serial": f"OATH{i:04d}"}
            for i in range(self.FILLER_ROWS)])

    @staticmethod
    def _execute_ddl(engine: sa.engine.Engine, statement: str) -> None:
        with engine.connect() as connection:
            connection.execute(sa.text(statement))
            connection.commit()

    @staticmethod
    def _storage_identity(engine: sa.engine.Engine) -> int:
        """A number that changes whenever the engine rewrites the table into new storage."""
        dialect = engine.dialect.name
        if dialect == "postgresql":
            query = ("SELECT relfilenode FROM pg_class WHERE relname = 'pidea_audit' "
                     "AND relnamespace = current_schema()::regnamespace")
        elif dialect == "oracle":
            query = ("SELECT data_object_id FROM user_objects "
                     "WHERE object_name = 'PIDEA_AUDIT' AND object_type = 'TABLE'")
        else:
            raise AssertionError(f"No storage identity for dialect {dialect}")
        with engine.connect() as connection:
            return connection.execute(sa.text(query)).scalar_one()

    @pytest.mark.migration
    def test_upgrade_adds_the_column_without_rewriting_the_table(self, flask_app):
        """
        The marker column is a metadata-only change on a filled table, so the upgrade stays fast on a large
        audit log. Every engine gets its own probe, each with a counter-probe that proves the probe can fail.

        MariaDB and MySQL: the same ADD COLUMN with ALGORITHM=INSTANT is accepted (it fails if the engine
        would have to copy the table), PostgreSQL: pg_class.relfilenode and Oracle:
        user_objects.data_object_id of pidea_audit stay the same across the upgrade.
        """
        engine = self._engine()
        try:
            dialect = engine.dialect.name
            if dialect not in ("mysql", "mariadb", "postgresql", "oracle"):
                pytest.skip(f"No rewrite probe for dialect {dialect}")
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_filler_entries(engine)

            if dialect in ("mysql", "mariadb"):
                # The probe column has another name, so the migration still finds its own column missing.
                self._execute_ddl(engine, "ALTER TABLE pidea_audit ADD COLUMN entry_version_probe INTEGER NULL, "
                                          "ALGORITHM=INSTANT")
                self._execute_ddl(engine, "ALTER TABLE pidea_audit DROP COLUMN entry_version_probe")
                # Counter-probe: a type change needs a table copy, INSTANT must be refused.
                serial = self._columns(engine)["serial"]
                null = "NULL" if serial["nullable"] else "NOT NULL"
                with pytest.raises(sa.exc.OperationalError):
                    self._execute_ddl(engine, f"ALTER TABLE pidea_audit MODIFY serial TEXT {null}, "
                                              "ALGORITHM=INSTANT")
                self._upgrade()
            else:
                before = self._storage_identity(engine)
                self._upgrade()
                after = self._storage_identity(engine)
                assert after == before, "The upgrade rewrote the table"
                # Counter-probe: a statement that copies the table changes the identity.
                if dialect == "postgresql":
                    self._execute_ddl(engine, "ALTER TABLE pidea_audit ALTER COLUMN serial TYPE text "
                                              "USING serial || ''")
                else:
                    self._execute_ddl(engine, "ALTER TABLE pidea_audit MOVE")
                assert self._storage_identity(engine) != before

            assert "entry_version" in self._columns(engine)
            assert self._fetch_scalar(engine, "SELECT COUNT(*) FROM pidea_audit WHERE id >= :first "
                                              "AND entry_version IS NULL",
                                      {"first": self.FILLER_FIRST_ID}) == self.FILLER_ROWS
        finally:
            engine.dispose()
