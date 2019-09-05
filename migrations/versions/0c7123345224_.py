"""Store privacyIDEA node in clientapplication table

Revision ID: 0c7123345224
Revises: d756b34061ff
Create Date: 2019-09-06 13:27:12.020779

"""

# revision identifiers, used by Alembic.
revision = '0c7123345224'
down_revision = 'd756b34061ff'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

from privacyidea.lib.config import get_privacyidea_node


def upgrade():
    node = get_privacyidea_node()
    try:
        # The ``node`` field is not nullable. Hence, We set the server_default to the current node to ensure that
        # the ``node`` of all existing rows is set to the current node.
        op.add_column('clientapplication', sa.Column('node', sa.Unicode(length=255),
                                                     nullable=False, server_default=node))
        op.drop_constraint(u'caix', 'clientapplication', type_='unique')
        op.create_unique_constraint('caix', 'clientapplication', ['ip', 'clienttype', 'node'])
    except Exception as exx:
        print("Failed to add 'node' column to 'clientapplication' table")
        print(exx)


def downgrade():
    op.drop_constraint('caix', 'clientapplication', type_='unique')
    op.create_unique_constraint(u'caix', 'clientapplication', ['ip', 'clienttype'])
    # This will probably raise errors about violated UNIQUE constraints
    op.drop_column('clientapplication', 'node')
