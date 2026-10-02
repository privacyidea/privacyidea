"""v3.15: Remove the enqueue_job column from the smtpserver table

The job queue is gone, so an SMTP server can no longer hand its emails to it: every email is sent directly.

The migration that added the column only printed an error when it failed, so a database can be at this revision
without the column. Both directions therefore check for the column before changing it.

Revision ID: 56529818c956
Revises: b7c1e4d2a9f3
Create Date: 2026-10-02 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = '56529818c956'
down_revision = 'b7c1e4d2a9f3'
branch_labels = None
depends_on = None

TABLE_NAME = 'smtpserver'
COLUMN_NAME = 'enqueue_job'


def _has_column() -> bool:
    return COLUMN_NAME in {column["name"] for column in inspect(op.get_bind()).get_columns(TABLE_NAME)}


def upgrade():
    if not _has_column():
        print(f"Ok, column '{COLUMN_NAME}' does not exist in table '{TABLE_NAME}'.")
        return
    # SQLite cannot drop a column that a CHECK constraint refers to, which the Boolean type of older SQLAlchemy
    # versions created. Batch mode rebuilds the table there and is a plain ALTER TABLE on every other database.
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.drop_column(COLUMN_NAME)


def downgrade():
    if _has_column():
        print(f"Ok, column '{COLUMN_NAME}' already exists in table '{TABLE_NAME}'.")
        return
    op.add_column(TABLE_NAME, sa.Column(COLUMN_NAME, sa.Boolean(), nullable=False, server_default=sa.false()))
