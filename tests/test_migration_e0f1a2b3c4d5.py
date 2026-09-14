"""
Fail-closed test for migration e0f1a2b3c4d5 ("v3.14: Increase the audit serial column size").

upgrade() used to catch DatabaseError around the ALTER, print it, and return - which lets Alembic stamp the
revision as applied even though the column was never actually widened. A caller stuck on a lock timeout, denied
by grants that don't cover ALTER TABLE, or out of disk space during the table rebuild would end up permanently
behind this revision while the database claims to be at it. upgrade() must re-raise instead, so Alembic aborts
and the revision is not marked applied.

No live multi-dialect database is needed for this: a single in-memory SQLite connection bound to a real Alembic
op context is enough, with the ALTER itself mocked to fail - the point under test is upgrade()'s own control
flow around a DatabaseError, not any particular dialect's behavior.
"""
import importlib
from unittest import mock

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION = importlib.import_module("privacyidea.migrations.versions.e0f1a2b3c4d5_audit_serial_column_size")


def _run_upgrade(connection) -> None:
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        MIGRATION.upgrade()


def test_upgrade_reraises_when_the_alter_fails_rather_than_swallowing_it():
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            connection.execute(sa.text("CREATE TABLE pidea_audit (id INTEGER PRIMARY KEY, serial VARCHAR(40))"))
            connection.commit()

            failure = sa.exc.DatabaseError("stmt", {}, Exception("simulated lock timeout"))
            with mock.patch.object(MIGRATION.op, "batch_alter_table", side_effect=failure):
                try:
                    _run_upgrade(connection)
                except sa.exc.DatabaseError:
                    pass
                else:
                    raise AssertionError("upgrade() must re-raise the DatabaseError, not swallow it")

            # The column was never actually widened - the point of re-raising is that Alembic never gets to
            # stamp this revision as applied over a schema that still doesn't match it.
            columns = {col["name"]: col for col in sa.inspect(connection).get_columns("pidea_audit")}
            assert columns["serial"]["type"].length == 40, columns["serial"]["type"]
    finally:
        engine.dispose()


def test_upgrade_succeeds_normally_when_the_alter_does_not_fail():
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            connection.execute(sa.text("CREATE TABLE pidea_audit (id INTEGER PRIMARY KEY, serial VARCHAR(40))"))
            connection.commit()

            _run_upgrade(connection)
            connection.commit()

            columns = {col["name"]: col for col in sa.inspect(connection).get_columns("pidea_audit")}
            assert columns["serial"]["type"].length == 200, columns["serial"]["type"]
    finally:
        engine.dispose()
