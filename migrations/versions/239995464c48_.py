"""Add RADIUS dictionary

Revision ID: 239995464c48
Revises: 449903fb6e35
Create Date: 2016-02-21 21:35:04.044207

"""

# revision identifiers, used by Alembic.
revision = '239995464c48'
down_revision = '449903fb6e35'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.add_column('radiusserver', sa.Column('dictionary',
                                                sa.Unicode(length=255),
                                                nullable=True))
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Table 'radiusserver' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add table 'radiusserver'")
        print (exx)


def downgrade():
    op.drop_column('radiusserver', 'dictionary')
