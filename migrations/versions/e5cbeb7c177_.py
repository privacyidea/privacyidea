"""Add column 'priority' to table 'resolverealm'

Revision ID: e5cbeb7c177
Revises: 2181294eed0b
Create Date: 2015-04-26 17:02:09.578608

"""

# revision identifiers, used by Alembic.
revision = 'e5cbeb7c177'
down_revision = '2181294eed0b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('resolverrealm', sa.Column('priority', sa.Integer(),
                                                 nullable=True))
    except Exception as exx:
        print ("Could not add column 'priority' to table 'resolverrealm'")
        print (exx)


def downgrade():
    op.drop_column('resolverrealm', 'priority')

