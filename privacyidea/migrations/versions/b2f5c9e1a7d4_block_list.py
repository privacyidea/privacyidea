"""Add block_list table and merge the lockout / authentication-log heads

Create the block_list table, which records a blocked source IP written by the
BLOCK_IP conditional-access action and consulted by the authentication
pre-check on the next inbound request - the same live-state pattern as
user_lockout_state, but keyed by source IP. The load-bearing field is
block_expires_at: a row whose block_expires_at lies in the future means the IP
is currently blocked; a NULL value means a permanent block.

This revision also merges the two pre-existing heads into one: the lockout
branch (...->173d32328846->c1a9f7e2b840) and the authentication-log branch
(...->0147d78cbace) both descend from 7d4e9b2c1a3f. Giving this migration both
as its down_revision rejoins them into a single head, so a fresh install ends
up with one linear head again.

Revision ID: b2f5c9e1a7d4
Revises: 0147d78cbace, c1a9f7e2b840
Create Date: 2026-06-10 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'b2f5c9e1a7d4'
down_revision = ('0147d78cbace', 'c1a9f7e2b840')
branch_labels = None
depends_on = None

TABLES = ['block_list']


def _create_table(table_name, *columns):
    try:
        op.create_table(table_name, *columns)
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print(f"Table '{table_name}' already exists.")
        else:
            print(f"Could not add table '{table_name}' to database.")
            raise


def upgrade():
    _create_table(
        'block_list',
        sa.Column('ip', sa.Unicode(length=50), nullable=False),
        sa.Column('is_blocked', sa.Boolean(), nullable=False),
        sa.Column('block_expires_at', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.Unicode(length=255), nullable=True),
        sa.Column('last_stage_triggered', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['last_stage_triggered'], ['lockout_policy_stages.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('ip'),
        sa.Index('ix_block_list_last_stage_triggered', 'last_stage_triggered'),
    )


def downgrade():
    for table_name in TABLES:
        try:
            op.drop_table(table_name)
        except (OperationalError, ProgrammingError) as ex:
            msg = str(ex.orig).lower()
            if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
                print(f"Table '{table_name}' already removed.")
            else:
                print(f"Could not remove table '{table_name}'.")
                raise
