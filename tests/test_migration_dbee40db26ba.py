"""
Data transformation test for migration dbee40db26ba
Create the enckey_check table and enckey_check_seq sequence.

upgrade()   — creates the 'enckey_check_seq' sequence and the 'enckey_check' table
              with columns 'id' (server_default from sequence) and 'check_value'
downgrade() — drops the 'enckey_check' table and the 'enckey_check_seq' sequence
"""

import os

import pytest

from tests.migration_test_utils import MigrationTestBase, is_postgres

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

DB_URL = os.environ.get("TEST_DATABASE_URL", "")


def _sequence_exists(engine, seq_name: str) -> bool:
    """Check whether a sequence exists in the database."""
    from sqlalchemy import text
    with engine.connect() as conn:
        if is_postgres():
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.sequences "
                "WHERE sequence_name = :name"
            ), {"name": seq_name}).scalar()
        else:
            # MariaDB/MySQL: sequences appear in information_schema.tables
            # with table_type = 'SEQUENCE'
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = DATABASE() "
                "AND table_type = 'SEQUENCE' "
                "AND table_name = :name"
            ), {"name": seq_name}).scalar()
    return result is not None


class TestMigrationDbee40db26ba(MigrationTestBase):
    REVISION = "dbee40db26ba"
    PARENT_REVISION = "b1a2c3d4e5f6"

    def _table_exists(self, engine, table_name: str) -> bool:
        from sqlalchemy import inspect as sa_inspect
        return table_name in sa_inspect(engine).get_table_names()

    def test_upgrade_creates_enckey_check_table(self, flask_app):
        """upgrade() must create the 'enckey_check' table."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        assert not self._table_exists(engine, "enckey_check")
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._table_exists(engine, "enckey_check"), (
            "upgrade() must create the 'enckey_check' table"
        )
        engine.dispose()

    def test_upgrade_creates_sequence(self, flask_app):
        """upgrade() must create the 'enckey_check_seq' sequence."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        assert not _sequence_exists(engine, "enckey_check_seq")
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert _sequence_exists(engine, "enckey_check_seq"), (
            "upgrade() must create the 'enckey_check_seq' sequence"
        )
        engine.dispose()

    def test_upgrade_table_has_correct_columns(self, flask_app):
        """upgrade() must create the table with 'id' and 'check_value' columns."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        from sqlalchemy import inspect as sa_inspect
        columns = {c["name"] for c in sa_inspect(engine).get_columns("enckey_check")}
        assert "id" in columns, "Table must have an 'id' column"
        assert "check_value" in columns, "Table must have a 'check_value' column"
        engine.dispose()

    def test_upgrade_id_has_server_default(self, flask_app):
        """After upgrade(), inserting without specifying 'id' should auto-generate it from the sequence."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO enckey_check (check_value) VALUES ('test_value')"
            ))
            conn.commit()
            row_id = conn.execute(text(
                "SELECT id FROM enckey_check WHERE check_value = 'test_value'"
            )).scalar()
        assert row_id is not None, "id must be auto-generated via server_default from sequence"
        engine.dispose()

    def test_upgrade_allows_insert(self, flask_app):
        """After upgrade(), it should be possible to insert a row into enckey_check."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        self._insert_rows(engine, "enckey_check", [
            {"id": 1, "check_value": "abc123:def456"}
        ])
        result = self._fetch_scalar(engine, "SELECT check_value FROM enckey_check WHERE id = 1")
        assert result == "abc123:def456"
        engine.dispose()

    def test_downgrade_drops_enckey_check_table(self, flask_app):
        """downgrade() must drop the 'enckey_check' table."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._table_exists(engine, "enckey_check")
        engine.dispose()

        self._downgrade()

        engine = self._engine()
        assert not self._table_exists(engine, "enckey_check"), (
            "downgrade() must drop the 'enckey_check' table"
        )
        engine.dispose()

    def test_downgrade_drops_sequence(self, flask_app):
        """downgrade() must drop the 'enckey_check_seq' sequence."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert _sequence_exists(engine, "enckey_check_seq")
        engine.dispose()

        self._downgrade()

        engine = self._engine()
        assert not _sequence_exists(engine, "enckey_check_seq"), (
            "downgrade() must drop the 'enckey_check_seq' sequence"
        )
        engine.dispose()

    def test_round_trip(self, flask_app):
        """An upgrade → downgrade round-trip must leave no trace of the table or sequence."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert not self._table_exists(engine, "enckey_check"), (
            "After round-trip, enckey_check table should not exist"
        )
        assert not _sequence_exists(engine, "enckey_check_seq"), (
            "After round-trip, enckey_check_seq sequence should not exist"
        )
        engine.dispose()
