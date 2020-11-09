"""Add startdate and duration to audit log

Revision ID: 3236a1abf1c6
Revises: 140ba0ca4f07
Create Date: 2020-10-10 12:00:09.291665

"""

# revision identifiers, used by Alembic.
revision = '3236a1abf1c6'
down_revision = '140ba0ca4f07'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('pidea_audit', sa.Column('duration', sa.Interval(), nullable=True))
        op.add_column('pidea_audit', sa.Column('startdate', sa.DateTime(), nullable=True))
    except Exception as exx:
        print("Could not add duration and startdate to the table pidea_audit.")
        print(exx)


def downgrade():
    op.drop_column('pidea_audit', 'startdate')
    op.drop_column('pidea_audit', 'duration')