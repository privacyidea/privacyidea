"""v3.14: Clear challenge table for dict-only data format

All challenge data is now stored as encrypted JSON dicts. Legacy challenges
that stored raw strings or non-dict values are incompatible with the new
format. Since challenges are short-lived (typically < 120s), this migration
simply deletes all existing rows. Any in-flight authentications at the time
of upgrade will need to be restarted by the user.

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-08-06
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'a1b2c3d4e5f6'


def upgrade():
    # Delete all challenges - they are short-lived and any legacy data
    # is incompatible with the new dict-only format.
    op.execute("DELETE FROM challenge")


def downgrade():
    # Nothing to undo - challenges are ephemeral by nature.
    pass
