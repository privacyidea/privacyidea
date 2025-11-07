"""v3.13: Increase audit signature column size to support 4096-bit RSA keys

Revision ID: 056b6642ff5d
Revises: 1c48d4ffb8c3
Create Date: 2025-09-15 13:29:06.058342

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '056b6642ff5d'
down_revision = '1c48d4ffb8c3'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('pidea_audit', 'signature',
                    existing_type=sa.VARCHAR(length=620),
                    type_=sa.Unicode(length=1100),
                    existing_nullable=True)


def downgrade():
    op.alter_column('pidea_audit', 'signature',
                    existing_type=sa.Unicode(length=1100),
                    type_=sa.VARCHAR(length=620),
                    existing_nullable=True)
