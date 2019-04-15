"""Add eventhandler tables

Revision ID: 50adc980d625
Revises: 239995464c48
Create Date: 2016-05-04 17:11:51.776440

"""

# revision identifiers, used by Alembic.
revision = '50adc980d625'
down_revision = '239995464c48'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.create_table('eventhandler',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ordering', sa.Integer(), nullable=False),
        sa.Column('event', sa.Unicode(length=255), nullable=False),
        sa.Column('handlermodule', sa.Unicode(length=255), nullable=False),
        sa.Column('condition', sa.Unicode(length=1024), nullable=True),
        sa.Column('action', sa.Unicode(length=1024), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_table('eventhandleroption',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('eventhandler_id', sa.Integer(), nullable=True),
        sa.Column('Key', sa.Unicode(length=255), nullable=False),
        sa.Column('Value', sa.Unicode(length=2000), nullable=True),
        sa.Column('Type', sa.Unicode(length=2000), nullable=True),
        sa.Column('Description', sa.Unicode(length=2000), nullable=True),
        sa.ForeignKeyConstraint(['eventhandler_id'], ['eventhandler.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('eventhandler_id', 'Key', name='ehoix_1')
        )
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Table 'eventhandler' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add table 'eventhandler'")
        print (exx)


def downgrade():
    op.drop_table('eventhandleroption')
    op.drop_table('eventhandler')

