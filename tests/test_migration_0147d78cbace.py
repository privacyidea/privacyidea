"""
Schema-drift retrofit test for migration 0147d78cbace ("v3.14: Add authentication log table").

Unlike the tests under test_migration_<rev>.py naming convention that transform existing row *data*
(see tests/README.md), this migration has instead been amended in place several times since it first
shipped: peer_ip, source_ip_source, client_label, client_label_source, ip_chain and endpoint were folded
into authentication_log's own column list later, ix_authlog_time was added later still, and the entire
authentication_log_reason table (plus its two indexes) was folded in by the reason-split commits - all
inside this same file rather than as separate migrations.

_create_table's "table already exists" guard used to skip straight past all of that once the table itself
was there, so a database stamped at this revision from an earlier form of the file kept the older, narrower
shape forever. These tests reproduce exactly that starting state (a table carrying only the original
columns, none of the later ones) and assert that upgrade() now retrofits it - column by column and index by
index - rather than treating "the table exists" as "there is nothing left to do".

No live multi-dialect database is needed for this: the retrofit is plain DDL (add_column/create_index), so a
single in-memory SQLite connection bound to a real Alembic op context is enough to exercise upgrade() itself.
"""
import importlib

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION = importlib.import_module("privacyidea.migrations.versions.0147d78cbace_authentication_log")

# The columns authentication_log had before peer_ip/source_ip_source/client_label/client_label_source/
# ip_chain/endpoint were folded into this same migration file.
_OLD_AUTHENTICATION_LOG_COLUMNS = (
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("resolver", sa.Unicode(120), nullable=True),
    sa.Column("uid", sa.Unicode(320), nullable=True),
    sa.Column("realm", sa.Unicode(255), nullable=True),
    sa.Column("username", sa.Unicode(255), nullable=True),
    sa.Column("user_role", sa.Unicode(30), nullable=True),
    sa.Column("event_type", sa.Unicode(40), nullable=False),
    sa.Column("timestamp", sa.DateTime(), nullable=False),
    sa.Column("source_ip", sa.Unicode(50), nullable=True),
    sa.Column("serial", sa.Unicode(1024), nullable=True),
    sa.Column("transaction_id", sa.Unicode(64), nullable=True),
    sa.Column("attempt_id", sa.Unicode(64), nullable=True),
    sa.Column("other_info", sa.JSON(), nullable=True),
)

_NEW_COLUMNS = {"peer_ip", "source_ip_source", "client_label", "client_label_source", "ip_chain", "endpoint"}


def _run_upgrade(connection) -> None:
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        MIGRATION.upgrade()


def test_upgrade_retrofits_a_table_stamped_before_the_later_columns_existed():
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            connection.execute(sa.text(
                "CREATE TABLE authentication_log ("
                "id INTEGER PRIMARY KEY, resolver VARCHAR(120), uid VARCHAR(320), realm VARCHAR(255), "
                "username VARCHAR(255), user_role VARCHAR(30), event_type VARCHAR(40) NOT NULL, "
                "timestamp DATETIME NOT NULL, source_ip VARCHAR(50), serial VARCHAR(1024), "
                "transaction_id VARCHAR(64), attempt_id VARCHAR(64), other_info TEXT)"
            ))
            connection.execute(sa.text(
                "INSERT INTO authentication_log (id, event_type, timestamp) "
                "VALUES (1, 'LOGIN_SUCCESS', '2026-01-01 00:00:00')"
            ))
            connection.commit()

            _run_upgrade(connection)
            connection.commit()

            inspector = sa.inspect(connection)
            columns = {col["name"] for col in inspector.get_columns("authentication_log")}
            assert _NEW_COLUMNS <= columns, columns
            index_names = {idx["name"] for idx in inspector.get_indexes("authentication_log")}
            assert "ix_authlog_time" in index_names, index_names
            assert "authentication_log_reason" in inspector.get_table_names()
            reason_indexes = {idx["name"] for idx in inspector.get_indexes("authentication_log_reason")}
            assert {"ix_authlog_reason_authlog", "ix_authlog_reason_reason"} <= reason_indexes, reason_indexes

            # The pre-existing row survived the retrofit, with the new columns reading NULL rather than the
            # row having been recreated or dropped.
            row = connection.execute(sa.text(
                "SELECT event_type, peer_ip, endpoint FROM authentication_log WHERE id = 1")).one()
            assert row.event_type == "LOGIN_SUCCESS"
            assert row.peer_ip is None
            assert row.endpoint is None
    finally:
        engine.dispose()


def test_upgrade_is_idempotent_once_fully_retrofitted():
    # A second upgrade() run (e.g. a retry, or a downgrade/upgrade round trip against the same live database)
    # must not error out on columns/indexes/tables that are now already there.
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            _run_upgrade(connection)
            connection.commit()
            _run_upgrade(connection)
            connection.commit()

            inspector = sa.inspect(connection)
            columns = {col["name"] for col in inspector.get_columns("authentication_log")}
            assert _NEW_COLUMNS <= columns, columns
    finally:
        engine.dispose()


def test_upgrade_on_a_fresh_database_creates_the_complete_schema():
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            _run_upgrade(connection)
            connection.commit()

            inspector = sa.inspect(connection)
            assert {"authentication_log", "authentication_log_reason"} <= set(inspector.get_table_names())
            columns = {col["name"] for col in inspector.get_columns("authentication_log")}
            expected = {c.name for c in _OLD_AUTHENTICATION_LOG_COLUMNS} | _NEW_COLUMNS
            assert expected <= columns, columns
    finally:
        engine.dispose()
