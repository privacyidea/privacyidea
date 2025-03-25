"""v3.11: Add table tokencredentialidhash

Revision ID: 903a6ed6f6c4
Revises: c128c01a5520
Create Date: 2025-02-19 11:53:45.910016

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = '903a6ed6f6c4'
down_revision = 'c128c01a5520'


def upgrade():
    try:
        op.create_table('tokencredentialidhash',
                        sa.Column('id', sa.Integer(), primary_key=True),
                        sa.Column('credential_id_hash', sa.String(length=256), nullable=False),
                        sa.Column('token_id', sa.Integer(), nullable=False),
                        sa.ForeignKeyConstraint(['token_id'], ['token.id'], ),
                        sa.Index('ix_tokencredentialidhash_credentialidhash',
                                 'credential_id_hash', unique=True))
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Table 'tokencredentialidhash' already exists.")
        else:
            print("Could not add table 'tokencredentialidhash' to database.")
            raise


def downgrade():
    try:
        op.drop_table('tokencredentialidhash')
    except (OperationalError, ProgrammingError) as exx:
        msg = str(exx.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'tokencredentialidhash' already removed.")
        else:
            print("Could not remove table 'tokencredentialidhash'.")
            raise
