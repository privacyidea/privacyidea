"""Add column revoked to Token table

Revision ID: 20969b4cbf06
Revises: 4d9178fa8336
Create Date: 2015-08-27 12:19:57.272525

"""

# revision identifiers, used by Alembic.
revision = '20969b4cbf06'
down_revision = '4d9178fa8336'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.add_column('token', sa.Column('revoked', sa.Boolean(),
                                         default=False))
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Column revoked already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add column 'revoked' to table 'token'")
        print (exx)

    try:
        op.add_column('token', sa.Column('locked', sa.Boolean(),
                                         default=False))
    except (OperationalError, ProgrammingError)  as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Column locked already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add column 'locked' to table 'token'")
        print (exx)


def downgrade():
    op.drop_column('token', 'revoked')
    op.drop_column('token', 'locked')
