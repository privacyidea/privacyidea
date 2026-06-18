"""v3.14: Add usersetting table for per-principal frontend settings

Revision ID: d4f5a6b7c8e9
Revises: 7d4e9b2c1a3f
Create Date: 2026-06-18 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

from privacyidea.models.db import (create_sequence_if_supported, restart_sequence_past_max,
                                   sequence_id_column)

# revision identifiers, used by Alembic.
revision = 'd4f5a6b7c8e9'
down_revision = '7d4e9b2c1a3f'
branch_labels = None
depends_on = None

SEQUENCE_NAME = "usersetting_seq"


def upgrade():
    # The model declares Sequence('usersetting_seq'), so SQLAlchemy emits
    # SELECT nextval(...) on every ORM insert; create it where supported.
    create_sequence_if_supported(op, SEQUENCE_NAME)

    try:
        op.create_table(
            'usersetting',
            sequence_id_column(op, SEQUENCE_NAME),
            sa.Column('subject_type', sa.Unicode(length=20), nullable=False),
            sa.Column('username', sa.Unicode(length=320), nullable=True),
            sa.Column('user_id', sa.Unicode(length=320), nullable=True),
            sa.Column('resolver', sa.Unicode(length=120), nullable=True),
            sa.Column('realm_id', sa.Integer(), nullable=True),
            sa.Column('settings', sa.JSON(), nullable=True),
            sa.Column('last_modified', sa.DateTime(), nullable=True),
            sa.Column('node', sa.Unicode(length=120), nullable=True),
            sa.ForeignKeyConstraint(['realm_id'], ['realm.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('subject_type', 'username', 'user_id', 'resolver', 'realm_id',
                                name='uq_usersetting_subject'),
            # Serves the resolver-user lookup, which keys on
            # (user_id, resolver, realm_id) and is not a prefix of the unique key.
            sa.Index('ix_usersetting_user', 'user_id', 'resolver', 'realm_id'),
        )
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Table 'usersetting' already exists.")
        else:
            print("Could not add table 'usersetting' to database.")
            raise

    # Advance the sequence past any existing rows (covers the
    # table-already-exists branch where it would otherwise hand out a value
    # <= MAX(id)).
    restart_sequence_past_max(op, 'usersetting', SEQUENCE_NAME)


def downgrade():
    try:
        op.drop_table('usersetting')
        if op.get_bind().dialect.supports_sequences:
            op.execute("DROP SEQUENCE IF EXISTS usersetting_seq")
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'usersetting' already removed.")
        else:
            print("Could not remove table 'usersetting'.")
            raise
