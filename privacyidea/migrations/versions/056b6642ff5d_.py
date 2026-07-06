"""v3.13: Increase audit signature column size to support 4096-bit RSA keys

Revision ID: 056b6642ff5d
Revises: 1c48d4ffb8c3
Create Date: 2025-09-15 13:29:06.058342

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = '056b6642ff5d'
down_revision = '1c48d4ffb8c3'
branch_labels = None
depends_on = None


def upgrade():
    try:
        with op.batch_alter_table('pidea_audit', schema=None) as batch_op:
            batch_op.alter_column('signature',
                                  existing_type=sa.VARCHAR(length=620),
                                  type_=sa.Unicode(length=1100),
                                  existing_nullable=True)
    except (OperationalError, ProgrammingError) as exx:
        print("Could not increase 'signature' column size in 'pidea_audit' table.")
        print(exx)


def downgrade():
    with op.batch_alter_table('pidea_audit', schema=None) as batch_op:
        batch_op.alter_column('signature',
                              existing_type=sa.Unicode(length=1100),
                              type_=sa.VARCHAR(length=620),
                              existing_nullable=True)
