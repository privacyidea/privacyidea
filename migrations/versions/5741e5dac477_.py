"""empty message

Revision ID: 5741e5dac477
Revises: e3a64b4ca634
Create Date: 2024-02-23 11:06:41.729152

"""

# revision identifiers, used by Alembic.
revision = '5741e5dac477'
down_revision = 'e3a64b4ca634'

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
        seq = Sequence('description_seq')
        try:
            create_seq(seq)
        except Exception as _e:
            pass
        op.create_table('description',
        sa.Column('id', sa.Integer(), seq, nullable=False),
        sa.Column('name', sa.Unicode(length=64), nullable=False),
        sa.Column('object_type', sa.Unicode(length=64), nullable=False),
        sa.Column('last_update', sa.DateTime),
        sa.Column('description', sa.UnicodeText()),
        sa.ForeignKeyConstraint(['object_id'], ['policy.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_row_format='DYNAMIC'
        )
    except Exception as exx:
        print("Could not add table 'description' - probably already exists!")
        print(exx)


def downgrade():
    op.drop_table('description')
