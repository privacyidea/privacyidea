"""v3.10: Remove tokencontainertemplate table

Revision ID: 01bd19153598
Revises: c9747130ee44
Create Date: 2024-07-04 13:56:46.242911

"""

# revision identifiers, used by Alembic.
revision = '01bd19153598'
down_revision = 'c9747130ee44'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_table('tokencontainertemplate')


def downgrade():
    op.create_table('tokencontainertemplate',
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column('options', sa.VARCHAR(length=2000), nullable=True),
                    sa.Column('name', sa.VARCHAR(length=200), nullable=True),
                    sa.Column('container_type', sa.VARCHAR(length=100), nullable=False),
                    sa.PrimaryKeyConstraint('id'))
