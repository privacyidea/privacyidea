"""v3.8: Add thread_id to audit_log

Revision ID: 006d4747f858
Revises: d3c0f0403a84
Create Date: 2022-11-30 22:37:42.163199

"""

# revision identifiers, used by Alembic.
revision = '006d4747f858'
down_revision = 'd3c0f0403a84'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.add_column('pidea_audit', sa.Column('thread_id', sa.Unicode(length=20), nullable=True))
    except (OperationalError, ProgrammingError, InternalError) as exx:
        print("Looks like the thread_id already exists in the pidea_audit table.")
        print(exx)
    except Exception as exx:
        print("Could not add thread_id to pidea_audit table.")
        print (exx)


def downgrade():
    op.drop_column('pidea_audit', 'thread_id')
