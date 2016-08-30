"""Add client application type table

Revision ID: 3c6e9dd7fbac
Revises: 3ae3c668f444
Create Date: 2016-08-30 17:40:29.869763

"""

# revision identifiers, used by Alembic.
revision = '3c6e9dd7fbac'
down_revision = '3ae3c668f444'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.create_table('clientapplication',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ip', sa.Unicode(length=255), nullable=False),
        sa.Column('hostname', sa.Unicode(length=255), nullable=True),
        sa.Column('clienttype', sa.Unicode(length=255), nullable=False),
        sa.Column('lastseen', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ip', 'clienttype', name='caix')
        )
        op.create_index(op.f('ix_clientapplication_clienttype'), 'clientapplication', ['clienttype'], unique=False)
        op.create_index(op.f('ix_clientapplication_id'), 'clientapplication', ['id'], unique=False)
        op.create_index(op.f('ix_clientapplication_ip'), 'clientapplication', ['ip'], unique=False)
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if exx.orig.message.lower().startswith("duplicate column name"):
            print("Good. Table clientapplication already exists.")
        else:
            print("Table already exists")
            print(exx)

    except Exception as exx:
        print("Could not add Table clientapplication")
        print (exx)


def downgrade():
    op.drop_index(op.f('ix_clientapplication_ip'), table_name='clientapplication')
    op.drop_index(op.f('ix_clientapplication_id'), table_name='clientapplication')
    op.drop_index(op.f('ix_clientapplication_clienttype'), table_name='clientapplication')
    op.drop_table('clientapplication')
