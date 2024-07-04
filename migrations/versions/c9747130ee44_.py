"""v3.10: Add columns 'container_serial' and 'container_type' to the audit table

Revision ID: c9747130ee44
Revises: 1344dfe78b17
Create Date: 2024-06-21 08:38:37.172857

"""

# revision identifiers, used by Alembic.
revision = 'c9747130ee44'
down_revision = '1344dfe78b17'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('pidea_audit', sa.Column('container_serial', sa.Unicode(), nullable=True))
    op.add_column('pidea_audit', sa.Column('container_type', sa.Unicode(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('pidea_audit', 'container_type')
    op.drop_column('pidea_audit', 'container_serial')
    # ### end Alembic commands ###