"""Add the DB table SMTPServer in version 2.10

Revision ID: 2ac117d0a6f5
Revises: 20969b4cbf06
Create Date: 2015-12-27 10:17:23.861696

"""

# revision identifiers, used by Alembic.
revision = '2ac117d0a6f5'
down_revision = '20969b4cbf06'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import (OperationalError, ProgrammingError, InternalError)


def upgrade():
    try:
        op.create_table('smtpserver',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.Unicode(length=255), nullable=False),
        sa.Column('server', sa.Unicode(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('username', sa.Unicode(length=255), nullable=True),
        sa.Column('password', sa.Unicode(length=255), nullable=True),
        sa.Column('sender', sa.Unicode(length=255), nullable=True),
        sa.Column('tls', sa.Boolean(), nullable=True),
        sa.Column('description', sa.Unicode(length=2000), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Column smtpserver already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add table 'smtpserver'")
        print (exx)


def downgrade():
    op.drop_table('smtpserver')

