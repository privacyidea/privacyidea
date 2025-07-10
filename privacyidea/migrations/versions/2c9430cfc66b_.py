"""create periodictask, periodictaskoption, periodictasklastrun tables

Revision ID: 2c9430cfc66b
Revises: 204d8d4f351e
Create Date: 2018-06-20 09:55:52.086626

"""

# revision identifiers, used by Alembic.
revision = '2c9430cfc66b'
down_revision = '204d8d4f351e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('periodictask',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=64), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('interval', sa.Unicode(length=256), nullable=False),
        sa.Column('nodes', sa.Unicode(length=256), nullable=False),
        sa.Column('taskmodule', sa.Unicode(length=256), nullable=False),
        sa.Column('ordering', sa.Integer(), nullable=False),
        sa.Column('last_update', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        mysql_row_format='DYNAMIC'
        )
        op.create_table('periodictasklastrun',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('periodictask_id', sa.Integer(), nullable=True),
        sa.Column('node', sa.Unicode(length=256), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['periodictask_id'], ['periodictask.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('periodictask_id', 'node', name='ptlrix_1'),
        mysql_row_format='DYNAMIC'
        )
        op.create_table('periodictaskoption',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('periodictask_id', sa.Integer(), nullable=True),
        sa.Column('key', sa.Unicode(length=256), nullable=False),
        sa.Column('value', sa.Unicode(length=2000), nullable=True),
        sa.ForeignKeyConstraint(['periodictask_id'], ['periodictask.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('periodictask_id', 'key', name='ptoix_1'),
        mysql_row_format='DYNAMIC'
        )
    except Exception as exx:
        print("Could not add tables for periodic tasks!")
        print(exx)


def downgrade():
    op.drop_table('periodictaskoption')
    op.drop_table('periodictasklastrun')
    op.drop_table('periodictask')
