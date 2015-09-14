"""Add column 'condition' to table 'policy'

Revision ID: 2181294eed0b
Revises: 2551ee982544
Create Date: 2015-02-06 09:30:00.848172

"""

# revision identifiers, used by Alembic.
revision = '2181294eed0b'
down_revision = '2551ee982544'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('policy', sa.Column('condition', sa.Integer(), nullable=False))
    except Exception as exx:
        print ("Could not add column 'condition' to table 'policy'")
        print (exx)


def downgrade():
    op.drop_column('policy', 'condition')
