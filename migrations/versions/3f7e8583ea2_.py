"""Add columns name and active to event handlers

Revision ID: 3f7e8583ea2
Revises: 22558d9f3178
Create Date: 2016-11-16 16:37:27.342209

"""

# revision identifiers, used by Alembic.
revision = '3f7e8583ea2'
down_revision = '22558d9f3178'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.add_column('eventhandler', sa.Column('name', sa.Unicode(
            length=64), default=u""))
        op.add_column('eventhandler', sa.Column('active', sa.Boolean(), nullable=True))
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if exx.orig.message.lower().startswith("duplicate column name"):
            print("Good. Columns name and active already exist.")
        else:
            print("Columns name and active already exist.")
            print(exx)

    except Exception as exx:
        print("Could not add columns name and active.")
        print (exx)



def downgrade():
    op.drop_column('eventhandler', 'name')
    op.drop_column('eventhandler', 'active')
