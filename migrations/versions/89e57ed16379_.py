"""v3.8: Add database tables tokengroup and tokentokengroup

Revision ID: 89e57ed16379
Revises: 00762b3f7a60
Create Date: 2022-09-28 11:24:28.966256

"""

# revision identifiers, used by Alembic.
revision = '89e57ed16379'
down_revision = '00762b3f7a60'

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
        seq = Sequence('tokengroup')
        try:
            create_seq(seq)
        except Exception as _e:
            pass
        op.create_table('tokengroup',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=255), nullable=False),
        sa.Column('Description', sa.Unicode(length=2000), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        mysql_row_format='DYNAMIC'
        )
    except Exception as exx:
        print("Could not add table 'tokengroup' - probably already exists!")
        print(exx)

    try:
        seq = Sequence('tokentokengroup')
        try:
            create_seq(seq)
        except Exception as _e:
            pass
        op.create_table('tokentokengroup',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token_id', sa.Integer(), nullable=True),
        sa.Column('tokengroup_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['token_id'], ['token.id'], ),
        sa.ForeignKeyConstraint(['tokengroup_id'], ['tokengroup.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_id', 'tokengroup_id', name='ttgix_2'),
        mysql_row_format='DYNAMIC'
        )
    except Exception as exx:
        print("Could not add table 'tokentokengroup' - probably already exists!")
        print(exx)


def downgrade():
    op.drop_table('tokentokengroup')
    op.drop_table('tokengroup')
