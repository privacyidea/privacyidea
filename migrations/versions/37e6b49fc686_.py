"""Add subscription table

Revision ID: 37e6b49fc686
Revises: 3c6e9dd7fbac
Create Date: 2016-10-23 10:45:45.792467

"""

# revision identifiers, used by Alembic.
revision = '37e6b49fc686'
down_revision = '3c6e9dd7fbac'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.create_table('subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application', sa.Unicode(length=30), nullable=True),
        sa.Column('for_name', sa.Unicode(length=50), nullable=False),
        sa.Column('for_address', sa.Unicode(length=128), nullable=True),
        sa.Column('for_email', sa.Unicode(length=128), nullable=False),
        sa.Column('for_phone', sa.Unicode(length=50), nullable=False),
        sa.Column('for_url', sa.Unicode(length=80), nullable=True),
        sa.Column('for_comment', sa.Unicode(length=255), nullable=True),
        sa.Column('by_name', sa.Unicode(length=50), nullable=False),
        sa.Column('by_email', sa.Unicode(length=128), nullable=False),
        sa.Column('by_address', sa.Unicode(length=128), nullable=True),
        sa.Column('by_phone', sa.Unicode(length=50), nullable=True),
        sa.Column('by_url', sa.Unicode(length=80), nullable=True),
        sa.Column('date_from', sa.DateTime(), nullable=True),
        sa.Column('date_till', sa.DateTime(), nullable=True),
        sa.Column('num_users', sa.Integer(), nullable=True),
        sa.Column('num_tokens', sa.Integer(), nullable=True),
        sa.Column('num_clients', sa.Integer(), nullable=True),
        sa.Column('level', sa.Unicode(length=30), nullable=True),
        sa.Column('signature', sa.Unicode(length=640), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_subscription_application'), 'subscription', ['application'], unique=False)
        op.create_index(op.f('ix_subscription_id'), 'subscription', ['id'], unique=False)
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if "duplicate column name" in str(exx.orig).lower():
            print("Good. Table subscription already exists.")
        else:
            print("Table subscription exists")
            print(exx)

    except Exception as exx:
        print("Could not add Table subscription")
        print (exx)


def downgrade():
    op.drop_index(op.f('ix_subscription_id'), table_name='subscription')
    op.drop_index(op.f('ix_subscription_application'), table_name='subscription')
    op.drop_table('subscription')

