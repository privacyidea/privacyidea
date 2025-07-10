"""add timeout and retries to radiusserver table

Revision ID: 14a1bcb10018
Revises: 36428afb2457
Create Date: 2017-10-30 15:16:04.819246

"""

# revision identifiers, used by Alembic.
revision = '14a1bcb10018'
down_revision = '36428afb2457'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('radiusserver', sa.Column('retries', sa.Integer(), nullable=True))
        op.add_column('radiusserver', sa.Column('timeout', sa.Integer(), nullable=True))
    except Exception as exx:
        print("Could not add retries and timeout to radiusserver")
        print (exx)


def downgrade():
    op.drop_column('radiusserver', 'timeout')
    op.drop_column('radiusserver', 'retries')
