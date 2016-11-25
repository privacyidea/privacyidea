"""Add resolver column to table pidea_audit

Revision ID: 22558d9f3178
Revises: 1a69e5e5e2ac
Create Date: 2016-11-25 18:42:16.854066

"""

# revision identifiers, used by Alembic.
revision = '22558d9f3178'
down_revision = '1a69e5e5e2ac'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('pidea_audit', sa.Column('resolver', sa.String(length=50), nullable=True))
    except Exception as exx:
        print ("column resolver in pidea_audit obviously already exists.")
        print (exx)


def downgrade():
    op.drop_column('pidea_audit', 'resolver')
