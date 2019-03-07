"""Add the DB table password reset in version 2.10

Revision ID: 4023571658f8
Revises: 2ac117d0a6f5
Create Date: 2016-01-07 16:45:35.708951

"""

# revision identifiers, used by Alembic.
revision = '4023571658f8'
down_revision = '2ac117d0a6f5'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.create_table('passwordreset',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recoverycode', sa.Unicode(length=255), nullable=False),
        sa.Column('username', sa.Unicode(length=64), nullable=False),
        sa.Column('realm', sa.Unicode(length=64), nullable=False),
        sa.Column('resolver', sa.Unicode(length=64), nullable=True),
        sa.Column('email', sa.Unicode(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('expiration', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_passwordreset_realm'), 'passwordreset',
                        ['realm'], unique=False)
        op.create_index(op.f('ix_passwordreset_username'), 'passwordreset',
                        ['username'], unique=False)
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Table passwordreset already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add table 'passwordreset'")
        print (exx)


def downgrade():
    op.drop_index(op.f('ix_passwordreset_username'), table_name='passwordreset')
    op.drop_index(op.f('ix_passwordreset_realm'), table_name='passwordreset')
    op.drop_table('passwordreset')
