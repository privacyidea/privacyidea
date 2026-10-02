"""
Data test for migration 56529818c956
Remove the enqueue_job column from the smtpserver table.

upgrade()   — DROP COLUMN enqueue_job, if the column exists
downgrade() — ADD COLUMN enqueue_job (NOT NULL, default false), if the column is missing
"""

import os

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


class TestMigration56529818c956(MigrationTestBase):
    REVISION = "56529818c956"
    PARENT_REVISION = "b7c1e4d2a9f3"

    # The seed ships one SMTP server of its own, so the inserted ids start well above it.
    QUEUED_ID = 101
    DIRECT_ID = 102

    @staticmethod
    def _columns(engine: sa.engine.Engine) -> set[str]:
        return {column["name"] for column in sa.inspect(engine).get_columns("smtpserver")}

    def _insert_servers(self, engine: sa.engine.Engine) -> None:
        # The flag is bound as a Boolean: PostgreSQL has a real boolean column, Oracle a NUMBER(1).
        statement = sa.text(
            "INSERT INTO smtpserver (id, identifier, server, port, sender, enqueue_job) "
            "VALUES (:id, :identifier, 'mail.example.com', 25, 'pi@example.com', :enqueue_job)"
        ).bindparams(sa.bindparam("enqueue_job", type_=sa.Boolean()))
        with engine.connect() as connection:
            connection.execute(statement, {"id": self.QUEUED_ID, "identifier": "queued", "enqueue_job": True})
            connection.execute(statement, {"id": self.DIRECT_ID, "identifier": "direct", "enqueue_job": False})
            connection.commit()

    def test_upgrade_drops_the_column_and_keeps_the_servers(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_servers(engine)

            self._upgrade()

            assert "enqueue_job" not in self._columns(engine)
            with engine.connect() as connection:
                identifiers = connection.execute(sa.text(
                    "SELECT identifier FROM smtpserver WHERE id IN (:queued, :direct) ORDER BY id"),
                    {"queued": self.QUEUED_ID, "direct": self.DIRECT_ID}).scalars().all()
            assert identifiers == ["queued", "direct"]
        finally:
            engine.dispose()

    def test_upgrade_succeeds_when_the_column_is_missing(self, flask_app):
        """The migration that added the column only printed its failure, so the column can be missing."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            with engine.connect() as connection:
                connection.execute(sa.text("ALTER TABLE smtpserver DROP COLUMN enqueue_job"))
                connection.commit()

            self._upgrade()

            assert "enqueue_job" not in self._columns(engine)
        finally:
            engine.dispose()

    def test_downgrade_restores_the_column_as_false(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_servers(engine)
            self._upgrade()

            self._downgrade()

            with engine.connect() as connection:
                values = connection.execute(sa.text(
                    "SELECT enqueue_job FROM smtpserver WHERE id IN (:queued, :direct)"),
                    {"queued": self.QUEUED_ID, "direct": self.DIRECT_ID}).scalars().all()
            assert [bool(value) for value in values] == [False, False]
        finally:
            engine.dispose()
