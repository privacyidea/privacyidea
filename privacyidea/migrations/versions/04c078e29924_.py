"""v3.12: Add column 'user_agent' to the policy table

Revision ID: 04c078e29924
Revises: 5f40baab76ca
Create Date: 2025-07-21 15:07:49.375967

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = '04c078e29924'
down_revision = '5f40baab76ca'


def upgrade():
    try:
        op.add_column('policy',
                      sa.Column('user_agents', sa.Unicode(length=256), nullable=True))
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower() or "duplicate column name" in str(exx.orig).lower():
            print("Column 'user_agents' already exists.")
        else:
            print("Could not add column 'user_agents' to table 'policy'.")
            print(exx)


def downgrade():
    try:
        op.drop_column('policy', 'user_agents')
    except (OperationalError, ProgrammingError) as exx:
        msg = str(exx.orig).lower()
        if "no such column" in msg or "does not exist" in msg:
            print("Column 'user_agents' already removed.")
        else:
            print("Could not remove column 'user_agents' from table 'policy'.")
            print(exx)
