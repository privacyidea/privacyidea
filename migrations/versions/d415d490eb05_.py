"""v3.6: Add auth_count column to authcache table

Revision ID: d415d490eb05
Revises: 9155f0d3d028
Create Date: 2021-04-06 21:19:25.931603
privacyIDEA Version: 3.6

"""

# revision identifiers, used by Alembic.
revision = 'd415d490eb05'
down_revision = '9155f0d3d028'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.add_column('authcache', sa.Column('auth_count', sa.Integer(), nullable=True))
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Column adminrealm already exists.")
        else:
            print(exx)
    except Exception as exx:
        print("Could not add the column 'auth_count' to table 'authcache'")
        print(exx)


def downgrade():
    op.drop_column('authcache', 'auth_count')
