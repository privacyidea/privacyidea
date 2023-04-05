"""v3.9: Add table serviceid

Revision ID: 4a0aec37e7cf
Revises: 006d4747f858
Create Date: 2023-03-15 16:14:26.204225

"""

# revision identifiers, used by Alembic.
revision = '4a0aec37e7cf'
down_revision = '006d4747f858'

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence


def dialect_supports_sequences():
    migration_context = context.get_context()
    return migration_context.dialect.supports_sequences


def create_seq(seq):
    if dialect_supports_sequences():
        op.execute(CreateSequence(seq))


def upgrade():
    try:
        seq = Sequence('serviceid_seq')
        try:
            create_seq(seq)
        except Exception as _e:
            pass
        op.create_table('serviceid',
        sa.Column('id', sa.Integer(), seq, nullable=False),
        sa.Column('name', sa.Unicode(length=255), nullable=False),
        sa.Column('Description', sa.Unicode(length=2000), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        mysql_row_format='DYNAMIC'
        )
    except Exception as exx:
        print("Could not add table 'serviceid' - probably already exists!")
        print(exx)


def downgrade():
    op.drop_table('serviceid')
