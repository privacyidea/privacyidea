"""v3.15: Add the entry_version column to the audit table

The column marks how an audit entry was written. New entries carry the value 2, which means their timestamps
are UTC. Entries written before this revision keep NULL, which means local time of the server.

If the audit log is written to a separate database (PI_AUDIT_SQL_URI), this migration does not reach it - it
runs against the token database. Apply the same change to the audit database, see READ_BEFORE_UPDATE.md.

Both directions check for the column before changing it, so a column that was added by hand does not fail them.

Revision ID: c8d5f2a7b914
Revises: b4c7e1a9d203
Create Date: 2026-11-19 14:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'c8d5f2a7b914'
down_revision = 'b4c7e1a9d203'
branch_labels = None
depends_on = None

TABLE_NAME = 'pidea_audit'
COLUMN_NAME = 'entry_version'


def _has_column() -> bool:
    return COLUMN_NAME in {column["name"] for column in inspect(op.get_bind()).get_columns(TABLE_NAME)}


def upgrade():
    if _has_column():
        print(f"Ok, column '{COLUMN_NAME}' already exists in table '{TABLE_NAME}'.")
        return
    op.add_column(TABLE_NAME, sa.Column(COLUMN_NAME, sa.Integer(), nullable=True))


def downgrade():
    if not _has_column():
        print(f"Ok, column '{COLUMN_NAME}' does not exist in table '{TABLE_NAME}'.")
        return
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.drop_column(COLUMN_NAME)
