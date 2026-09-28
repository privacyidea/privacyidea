"""v3.14: Convert the remaining Oracle DATE columns to TIMESTAMP

The conversion released in 3.13.4 covers the tables that existed at its point in
the history. The tables added since - API clients, remembered devices, user
settings, conditional access, the block list, the lock state, the authentication
log, internal user attributes and the metric aggregate - are created after it, so
their DateTime columns are out of its reach and this converts them too.

On a database created once the models render TIMESTAMP on Oracle, these columns
are already TIMESTAMP and the conversion is a no-op. It matters for an
installation that created those tables while DateTime still mapped to DATE, which
resolves to whole seconds and drops the fraction without a word.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-09-17 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

revision = 'a2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None

DATETIME_COLUMNS = [
    ("authentication_log", "timestamp"),
    ("block_list", "blocked_at"),
    ("block_list", "block_expires_at"),
    ("clients", "created_at"),
    ("clients", "last_used_at"),
    ("conditional_access_policies", "enforced_since"),
    ("internaluserattribute", "last_modified"),
    ("metric_aggregate", "window_start"),
    ("remembered_devices", "created_at"),
    ("remembered_devices", "expires_at"),
    ("remembered_devices", "last_used_at"),
    ("user_lock_state", "locked_at"),
    ("user_lock_state", "lock_expires_at"),
    ("usersetting", "last_modified"),
]


def _convert(target_type):
    bind = op.get_bind()
    if bind.dialect.name != "oracle":
        # Every other dialect already stores the fraction: MySQL through the
        # DATETIME(6) compile hook, PostgreSQL and SQLite by default.
        return
    type_name = target_type.__class__.__name__
    # A table is skipped rather than assumed: these are recent tables, and an
    # installation that has not reached the migration creating one of them has
    # nothing to convert there.
    existing_tables = set(inspect(bind).get_table_names())
    for table_name, column_name in DATETIME_COLUMNS:
        if table_name not in existing_tables:
            continue
        print(f"  {table_name}.{column_name} -> {type_name}")
        try:
            op.alter_column(table_name, column_name, type_=target_type)
        except (OperationalError, ProgrammingError) as ex:
            print(f"Could not convert '{table_name}.{column_name}': {ex}")
            raise


def upgrade():
    _convert(sa.TIMESTAMP())


def downgrade():
    _convert(sa.DATE())
