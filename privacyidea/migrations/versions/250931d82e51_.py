"""v3.10: Add columns authentication, user_agent/version to Audit

Revision ID: 250931d82e51
Revises: 5741e5dac477
Create Date: 2024-03-27 16:08:47.242337

"""

# revision identifiers, used by Alembic.
revision = '250931d82e51'
down_revision = '5741e5dac477'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import DatabaseError


def upgrade():
    try:
        op.add_column('pidea_audit', sa.Column('authentication', sa.Unicode(length=12), nullable=True))
        op.add_column('pidea_audit', sa.Column('user_agent', sa.Unicode(length=20), nullable=True))
        op.add_column('pidea_audit', sa.Column('user_agent_version',
                                               sa.Unicode(length=20), nullable=True))
    except DatabaseError as exx:
        if any(x in str(exx.orig).lower() for x in ["already exists", "duplicate column name"]):
            print("Can not add columns 'authentication', 'user_agent', 'user_agent_version' to "
                  "table 'pidea_audit'. Probably already exist.")
        else:
            raise
    except Exception as exx:
        print("Can not add columns 'authentication', 'user_agent', 'user_agent_version' to "
              "table 'pidea_audit'. Probably already exist.")
        print(exx)
        raise


def downgrade():
    for col in ['user_agent_version', 'user_agent', 'authentication']:
        try:
            op.drop_column('pidea_audit', col)
        except DatabaseError as exx:
            msg = str(exx.orig).lower()
            if any(x in msg for x in ["no such column", "does not exist", "check that it exists"]):
                print(f"Column '{col}' in 'pidea_audit' already removed.")
            else:
                raise
