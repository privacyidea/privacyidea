"""Add the boolean field check_all_resolvers to policy table.

Revision ID: 58e4f7ebb705
Revises: 3f7e8583ea2
Create Date: 2016-12-13 15:20:54.003819

"""

# revision identifiers, used by Alembic.
revision = '58e4f7ebb705'
down_revision = '3f7e8583ea2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('policy', sa.Column('check_all_resolvers', sa.Boolean(), nullable=True))
    except Exception as exx:
        print ("Could not add column 'check_all_resolvers'")
        print (exx)


def downgrade():
    op.drop_column('policy', 'check_all_resolvers')
