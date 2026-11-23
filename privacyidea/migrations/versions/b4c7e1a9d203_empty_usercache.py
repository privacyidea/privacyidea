"""v3.15: Empty the user cache, whose timestamps were local time

The user cache wrote its timestamps in the local time of the server, but all other timestamps are UTC. Entries from
before this revision cannot be told apart from UTC values, so the cache is emptied once. It is refilled from the
resolvers on demand.

Revision ID: b4c7e1a9d203
Revises: 56529818c956
Create Date: 2026-11-19 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = 'b4c7e1a9d203'
down_revision = '56529818c956'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No lib or ORM code is used on purpose, the statement only needs the table name.
    op.execute(sa.text("DELETE FROM usercache"))


def downgrade() -> None:
    # The deleted entries cannot be restored, and the cache refills itself.
    pass
