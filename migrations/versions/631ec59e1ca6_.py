"""Add privacyIDEA node to the policy table

Revision ID: 631ec59e1ca6
Revises: a7e91b18a460
Create Date: 2020-06-05 15:36:57.225327

"""

# revision identifiers, used by Alembic.
revision = '631ec59e1ca6'
down_revision = 'a7e91b18a460'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('policy', sa.Column('pinode', sa.Unicode(length=256), nullable=True))
    except Exception as exx:
        print('Adding of column "pinode" in table policy failed: {!r}'.format(exx))
        print('This is expected behavior if this column already exists.')


def downgrade():
    op.drop_column('policy', 'pinode')

