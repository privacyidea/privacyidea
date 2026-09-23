"""v3.13.4: Convert the Oracle DATE columns to TIMESTAMP

Oracle maps a DateTime column to DATE, which resolves to whole seconds and drops
the fraction without a word. Two monitoring statistics written in the same second
then collide on UniqueConstraint('timestamp', 'stats_key'), and every other
timestamp loses its sub-second ordering. The models now render TIMESTAMP on
Oracle, which only affects newly created tables - this converts the columns an
existing installation already has.

pidea_audit is converted as well, so that the schema keeps matching the models.
Be aware that Oracle rewrites every row for a type change: on an installation
with a large audit table this step takes a while and holds an exclusive lock, so
the upgrade wants a maintenance window.

Revision ID: d3a4b5c6e7f8
Revises: c7f1a2b3d4e5
Create Date: 2026-09-16 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

revision = 'd3a4b5c6e7f8'
down_revision = 'c7f1a2b3d4e5'
branch_labels = None
depends_on = None

DATETIME_COLUMNS = [
    ("authcache", "first_auth"),
    ("authcache", "last_auth"),
    ("challenge", "timestamp"),
    ("challenge", "expiration"),
    ("clientapplication", "lastseen"),
    ("description", "last_update"),
    ("monitoringstats", "timestamp"),
    ("nodename", "lastseen"),
    ("passwordreset", "timestamp"),
    ("passwordreset", "expiration"),
    ("periodictask", "last_update"),
    ("periodictasklastrun", "timestamp"),
    ("pidea_audit", "date"),
    ("pidea_audit", "startdate"),
    ("subscription", "date_from"),
    ("subscription", "date_till"),
    ("tokencontainer", "last_seen"),
    ("tokencontainer", "last_updated"),
    ("usercache", "timestamp"),
]


def _convert(target_type):
    bind = op.get_bind()
    if bind.dialect.name != "oracle":
        # Every other dialect already stores the fraction: MySQL through the
        # DATETIME(6) compile hook, PostgreSQL and SQLite by default.
        return
    type_name = target_type.__class__.__name__
    print(f"Converting {len(DATETIME_COLUMNS)} Oracle date columns to {type_name}.")
    print("Oracle rewrites every row of a table for this, so on an installation with a large "
          "audit log the pidea_audit columns can take a while.")
    for table_name, column_name in DATETIME_COLUMNS:
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
