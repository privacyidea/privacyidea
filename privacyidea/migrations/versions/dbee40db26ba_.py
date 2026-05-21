"""version 3.14 adding table pi_internal

Revision ID: dbee40db26ba
Revises: b1a2c3d4e5f6
Create Date: 2026-05-07 13:22:55.368183

"""
import sqlalchemy as sa
from alembic import op, context
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence

# revision identifiers, used by Alembic.
revision = 'dbee40db26ba'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    try:
        op.create_table('pi_internal',
                        sa.Column('id', sa.Integer(), sa.Sequence('pi_internal_seq'), primary_key=True),
                        sa.Column('name', sa.Unicode(length=255), nullable=False),
                        sa.Column('check_value', sa.Unicode(length=2000), nullable=False),
                        sa.PrimaryKeyConstraint('id'),
                        sa.UniqueConstraint('name'),
                        mysql_row_format='DYNAMIC'
                        )
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Table 'pi_internal' already exists.")
        else:
            print("Could not add table 'pi_internal' to database.")
            raise


def downgrade():
    try:
        op.drop_table('pi_internal')
    except (OperationalError, ProgrammingError) as exx:
        msg = str(exx.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'description' already removed.")
        else:
            raise
