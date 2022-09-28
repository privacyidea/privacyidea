"""v3.8: Add database tables tokengroup and tokentokengroup

Revision ID: 89e57ed16379
Revises: 00762b3f7a60
Create Date: 2022-09-28 11:24:28.966256

"""

# revision identifiers, used by Alembic.
revision = '89e57ed16379'
down_revision = '00762b3f7a60'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
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
