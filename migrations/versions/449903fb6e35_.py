"""Add table 'radiusserver' to configure the settings of remote RADIUS servers.

Revision ID: 449903fb6e35
Revises: 4023571658f8
Create Date: 2016-02-19 15:41:22.196074

"""

# revision identifiers, used by Alembic.
revision = '449903fb6e35'
down_revision = '4023571658f8'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.create_table('radiusserver',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.Unicode(length=255), nullable=False),
        sa.Column('server', sa.Unicode(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('secret', sa.Unicode(length=255), nullable=True),
        sa.Column('description', sa.Unicode(length=2000), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('identifier')
        )
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Table 'radiusserver' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add table 'radiusserver'")
        print (exx)


def downgrade():
    op.drop_table('radiusserver')

