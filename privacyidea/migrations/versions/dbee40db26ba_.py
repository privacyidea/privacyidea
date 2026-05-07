"""empty message

Revision ID: dbee40db26ba
Revises: b1a2c3d4e5f6
Create Date: 2026-05-07 13:22:55.368183

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'dbee40db26ba'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('enckey_check',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('check_value', sa.Unicode(length=2000), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('enckey_check')
