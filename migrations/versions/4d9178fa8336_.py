"""Add adminrealm to policies

Revision ID: 4d9178fa8336
Revises: e5cbeb7c177
Create Date: 2015-06-15 13:58:35.377862

"""

# revision identifiers, used by Alembic.
revision = '4d9178fa8336'
down_revision = 'e5cbeb7c177'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('policy', sa.Column('adminrealm',
                                      sa.Unicode(length=256),
                                      nullable=True))


def downgrade():
    op.drop_column('policy', 'adminrealm')
