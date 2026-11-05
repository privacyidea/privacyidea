"""v3.14: Add usersetting table for per-principal frontend settings

The table and each of its indexes are only created when they do not exist yet, so the migration can run again on its
own result, also after it stopped between the table and its indexes.

Revision ID: d4f5a6b7c8e9
Revises: c2d3e4f5a6b7
Create Date: 2026-06-18 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

from privacyidea.models.db import (create_sequence_if_supported, drop_sequence_if_supported,
                                   restart_sequence_past_max, sequence_id_column)

# revision identifiers, used by Alembic.
revision = 'd4f5a6b7c8e9'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None

SEQUENCE_NAME = "usersetting_seq"

INDEXES = [
    # Serves the local-admin lookup on (subject_type, username), which subject_hash is not a prefix of.
    ('ix_usersetting_subject_type_username', ['subject_type', 'username']),
    # Serves the resolver-user lookup, which keys on (user_id, resolver, realm_id) and is not a prefix of the unique
    # key.
    ('ix_usersetting_user', ['user_id', 'resolver', 'realm_id']),
]


def upgrade():
    # The model declares Sequence('usersetting_seq'), so SQLAlchemy emits
    # SELECT nextval(...) on every ORM insert; create it where supported.
    create_sequence_if_supported(op, SEQUENCE_NAME)

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table('usersetting'):
        print("Table 'usersetting' already exists.")
        existing_indexes = {(index["name"] or "").lower() for index in inspector.get_indexes('usersetting')}
    else:
        existing_indexes = set()
        op.create_table(
            'usersetting',
            sequence_id_column(op, SEQUENCE_NAME),
            sa.Column('subject_type', sa.Unicode(length=20), nullable=False),
            sa.Column('username', sa.Unicode(length=320), nullable=True),
            sa.Column('user_id', sa.Unicode(length=320), nullable=True),
            sa.Column('resolver', sa.Unicode(length=120), nullable=True),
            sa.Column('realm_id', sa.Integer(), nullable=True),
            # SHA-256 hex digest of a subset of the columns above, per
            # subject_type (see privacyidea.models.usersetting.
            # _compute_subject_hash). A raw composite UNIQUE constraint over
            # all five columns is 3124 bytes under utf8mb4 -- over MySQL's
            # 3072-byte index-key limit -- so the constraint below is on this
            # fixed-width hash instead.
            sa.Column('subject_hash', sa.Unicode(length=64), nullable=False),
            sa.Column('settings', sa.JSON(), nullable=True),
            sa.Column('last_modified', sa.DateTime(), nullable=True),
            sa.Column('node', sa.Unicode(length=120), nullable=True),
            sa.ForeignKeyConstraint(['realm_id'], ['realm.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('subject_hash', name='uq_usersetting_subject'),
        )
    for index_name, index_columns in INDEXES:
        if index_name.lower() in existing_indexes:
            print(f"Index '{index_name}' already exists.")
        else:
            op.create_index(index_name, 'usersetting', index_columns)

    # Advance the sequence past any existing rows (covers the
    # table-already-exists branch where it would otherwise hand out a value
    # <= MAX(id)).
    restart_sequence_past_max(op, 'usersetting', SEQUENCE_NAME)


def downgrade():
    try:
        op.drop_table('usersetting')
        drop_sequence_if_supported(op, SEQUENCE_NAME)
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'usersetting' already removed.")
        else:
            print("Could not remove table 'usersetting'.")
            raise
