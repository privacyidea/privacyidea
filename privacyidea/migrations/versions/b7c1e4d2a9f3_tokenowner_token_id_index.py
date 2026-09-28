"""v3.14: Add an index to tokenowner.token_id

Every token query that reads the owner joins tokenowner on token_id. Only SQLite
gains from an index here: it scans the whole tokenowner table per token, which
makes counting the tokens of a realm unusable once many tokens are assigned.

The other databases neither gain nor lose. MySQL and MariaDB index the foreign
key column themselves, so nothing is added there at all, and on PostgreSQL and
Oracle the same queries were measured to take the same time with the index as
without it. The index brings a SQLite development database in line with the
databases used in production, at no cost to them.

The column may already be indexed, by MySQL for the foreign key or by hand, so
the migration only adds an index when there is none.

Revision ID: b7c1e4d2a9f3
Revises: a2b3c4d5e6f7
Create Date: 2026-09-22 15:00:00.000000

"""
from alembic import op
from sqlalchemy import inspect

revision = 'b7c1e4d2a9f3'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None

INDEX_NAME = 'ix_tokenowner_token_id'


def _has_token_id_index() -> bool:
    indexes = inspect(op.get_bind()).get_indexes('tokenowner')
    return any(index["column_names"][:1] == ["token_id"] for index in indexes)


def upgrade():
    if not _has_token_id_index():
        op.create_index(INDEX_NAME, 'tokenowner', ['token_id'], unique=False)


def downgrade():
    indexes = inspect(op.get_bind()).get_indexes('tokenowner')
    if any(index["name"] == INDEX_NAME for index in indexes):
        op.drop_index(INDEX_NAME, table_name='tokenowner')
