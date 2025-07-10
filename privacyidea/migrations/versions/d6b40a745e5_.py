"""Add table usercache

Revision ID: d6b40a745e5
Revises: 307a4fbe8a05
Create Date: 2017-04-13 15:25:44.050719

"""

# revision identifiers, used by Alembic.
revision = 'd6b40a745e5'
down_revision = '307a4fbe8a05'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('usercache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.Unicode(length=64), nullable=True, index=True),
        sa.Column('resolver', sa.Unicode(length=120), nullable=True),
        sa.Column('user_id', sa.Unicode(length=320), nullable=True, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
    except Exception as exx:
        print ("Could not create table 'usercache'.")
        print (exx)


def downgrade():
    op.drop_table('usercache')
