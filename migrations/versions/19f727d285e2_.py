"""Add monitoringstats table

Revision ID: 19f727d285e2
Revises: 2c9430cfc66b
Create Date: 2018-07-03 11:45:57.967604

"""

# revision identifiers, used by Alembic.
revision = '19f727d285e2'
down_revision = '2c9430cfc66b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('monitoringstats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('stats_key', sa.Unicode(length=128), nullable=False),
        sa.Column('stats_value', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('timestamp', 'stats_key', name='msix_1'),
        mysql_row_format='DYNAMIC'
        )
    except Exception as exx:
        print("Could not add table for monitoring stats!")
        print(exx)


def downgrade():
    op.drop_table('monitoringstats')
