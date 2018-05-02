"""Add table eventcounter

Revision ID: 145ce80decd
Revises: 49a04e560d96
Create Date: 2018-03-01 12:22:04.523615

"""

# revision identifiers, used by Alembic.
revision = '145ce80decd'
down_revision = '49a04e560d96'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('eventcounter',
                        sa.Column('counter_name', sa.Unicode(length=80), nullable=False),
                        sa.Column('counter_value', sa.Integer(), nullable=True),
                        sa.PrimaryKeyConstraint('counter_name')
                        )
    except Exception as exx:
        print("Could not create table eventcounter. Probably already exists!")
        print (exx)


def downgrade():
    op.drop_table('eventcounter')
