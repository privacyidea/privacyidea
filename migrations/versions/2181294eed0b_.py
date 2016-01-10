"""Add column 'condition' to table 'policy'

Revision ID: 2181294eed0b
Revises: 2551ee982544
Create Date: 2015-02-06 09:30:00.848172

"""

# revision identifiers, used by Alembic.
revision = '2181294eed0b'
down_revision = '2551ee982544'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.add_column('policy', sa.Column('condition', sa.Integer(), nullable=False))
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if exx.orig.message.lower().startswith("duplicate column name"):
            print("Good. Column condition already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add column 'condition' to table 'policy'")
        print (exx)


def downgrade():
    op.drop_column('policy', 'condition')
