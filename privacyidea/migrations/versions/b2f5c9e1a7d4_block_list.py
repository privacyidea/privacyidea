"""v3.14: Add block_list table

Create the block_list table, which records a blocked source IP written by the
BLOCK_IP_TEMPORARY conditional-access action and consulted by the authentication
pre-check on the next inbound request - the same live-state pattern as
user_lock_state, but keyed by source IP. The load-bearing field is
block_expires_at: a row whose block_expires_at lies in the future means the IP
is currently blocked; a NULL value means a permanent block. block_cause records
whether the engine or an administrator imposed the block.

Revision ID: b2f5c9e1a7d4
Revises: c1a9f7e2b840
Create Date: 2026-06-10 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'b2f5c9e1a7d4'
down_revision = 'c1a9f7e2b840'
branch_labels = None
depends_on = None

TABLES = ['block_list']


def _existing_tables() -> set[str]:
    """
    The names of the tables that already exist, lower-cased.

    Reflected once per migration rather than once per table: on a normal run nothing exists yet, so this
    single catalog read is all the guard below costs. Lower-cased because Oracle folds unquoted identifiers
    to upper case and the inspector reflects them back lower-cased (mirrors models.db.sequence_exists).
    """
    return {name.lower() for name in sa.inspect(op.get_bind()).get_table_names()}


def _create_table(existing_tables: set[str], table_name: str, *columns) -> None:
    """
    Create the table unless it is already there -- a schema bootstrapped from the models with create_all
    before this migration ran carries it.

    Presence is established by reflection rather than by swallowing an "already exists" error, which Oracle
    never says: it reports an existing object as ORA-00955 ("name is already used by an existing object").
    models.db.sequence_exists reflects for the same reason.
    """
    if table_name.lower() in existing_tables:
        print(f"Table '{table_name}' already exists.")
        return
    op.create_table(table_name, *columns)


def upgrade():
    existing_tables = _existing_tables()
    _create_table(
        existing_tables,
        'block_list',
        sa.Column('ip', sa.Unicode(length=50), nullable=False),
        sa.Column('block_expires_at', sa.DateTime(), nullable=True),
        sa.Column('block_cause', sa.Unicode(length=20), nullable=False, server_default='POLICY'),
        sa.Column('error_message', sa.Unicode(length=500), nullable=True),
        sa.Column('blocked_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('ip'),
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
