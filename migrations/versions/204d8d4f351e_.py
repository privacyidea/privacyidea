"""Add priority to policy

Revision ID: 204d8d4f351e
Revises: 145ce80decd
Create Date: 2018-05-09 15:30:39.878219

"""

# revision identifiers, used by Alembic.
revision = '204d8d4f351e'
down_revision = '145ce80decd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        # As we defined 'priority' to be non-NULLable, we supply a server_default value of 1
        # here to set the priority of all existing policies to 1.
        op.add_column('policy', sa.Column('priority', sa.Integer(), nullable=False, server_default='1'))
    except Exception as exx:
        print("Could not add column 'priority' to table 'policy'.")
        print(exx)

def downgrade():
    op.drop_column('policy', 'priority')
