"""Make subscription fields (level, application, for_name) longer

Revision ID: 3429d523e51f
Revises: d6b40a745e5
Create Date: 2017-05-12 12:52:38.545144

"""

# revision identifiers, used by Alembic.
revision = '3429d523e51f'
down_revision = 'd6b40a745e5'

from alembic import op
import sqlalchemy as sa


def upgrade():

    try:
        op.alter_column('subscription', 'level', type_=sa.Unicode(80),
                        existing_type=sa.Unicode(30))
    except Exception as exx:
        print("Could not make field 'level' longer.")
        print (exx)
    try:
        op.alter_column('subscription', 'application', type_=sa.Unicode(80),
                        existing_type=sa.Unicode(30))
    except Exception as exx:
        print("Could not make field 'application' longer.")
        print (exx)

    try:
        op.alter_column('subscription', 'for_name', type_=sa.Unicode(80),
                            existing_type=sa.Unicode(30))
    except Exception as exx:
        print("Could not make field 'for_name' longer.")
        print (exx)


def downgrade():
    pass
