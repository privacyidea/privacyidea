"""Add event handler conditions table

Revision ID: 3ae3c668f444
Revises: 5402fd96fbca
Create Date: 2016-07-20 12:18:55.643974

"""

# revision identifiers, used by Alembic.
revision = '3ae3c668f444'
down_revision = '5402fd96fbca'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.create_table('eventhandlercondition',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('eventhandler_id', sa.Integer(), nullable=True),
        sa.Column('Key', sa.Unicode(length=255), nullable=False),
        sa.Column('Value', sa.Unicode(length=2000), nullable=True),
        sa.Column('comparator', sa.Unicode(length=255), nullable=True),
        sa.ForeignKeyConstraint(['eventhandler_id'], ['eventhandler.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('eventhandler_id', 'Key', name='ehcix_1')
        )
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Table eventhandlercondition already exists.")
        else:
            print("Table already exists")
            print(exx)

    except Exception as exx:
        print("Could not add Table eventhandlercondition")
        print (exx)


def downgrade():
    op.drop_table('eventhandlercondition')

