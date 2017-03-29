"""Add user index to table pidea_audit to speed up audit.

Revision ID: 1edda52b619f
Revises: 58e4f7ebb705
Create Date: 2017-03-29 12:13:56.239454

"""

# revision identifiers, used by Alembic.
revision = '1edda52b619f'
down_revision = '58e4f7ebb705'

from alembic import op
import sqlalchemy as sa


def upgrade():

    try:
        op.create_index(op.f('ix_pidea_audit_user'), 'pidea_audit', ['user'],
                        unique=False)
    except Exception as exx:
        print("Could not add index in table pidea_audit.")
        print(exx)


def downgrade():
    try:
        op.drop_index(op.f('ix_pidea_audit_user'), table_name='pidea_audit')
    except Exception as exx:
        print("Could not delete index in table pidea_audit.")
        print (exx)
