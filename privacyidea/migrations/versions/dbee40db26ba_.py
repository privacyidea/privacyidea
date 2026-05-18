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
    pi_internal_seq = sa.Sequence('pi_internal_seq')
    try:
        if context.get_context().dialect.supports_sequences:
            op.execute(CreateSequence(pi_internal_seq))
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print(f"Ok, sequence '{pi_internal_seq}' already exists.")
        else:
            raise
    except Exception as _exx:
        print(f"Could not create sequence '{pi_internal_seq}'!")
        raise
    op.execute(sa.schema.CreateSequence(pi_internal_seq))
    op.create_table('pi_internal',
                    sa.Column('id', sa.Integer(), server_default=pi_internal_seq.next_value(), nullable=False),
                    sa.Column('name', sa.Unicode(length=255), nullable=False),
                    sa.Column('check_value', sa.Unicode(length=2000), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name'),
                    mysql_row_format='DYNAMIC'
                    )


def downgrade():
    try:
        op.drop_table('pi_internal')
    except (OperationalError, ProgrammingError) as exx:
        msg = str(exx.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'description' already removed.")
        else:
            raise
    seq = Sequence('pi_internal_seq')
    if context.get_context().dialect.supports_sequences:
        try:
            op.execute(DropSequence(seq))
        except (OperationalError, ProgrammingError) as exx:
            if "does not exist" in str(exx.orig).lower():
                print(f"Sequence '{seq.name}' already removed.")
            else:
                raise
