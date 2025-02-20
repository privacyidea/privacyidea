"""empty message

Revision ID: 903a6ed6f6c4
Revises: c128c01a5520
Create Date: 2025-02-19 11:53:45.910016

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '903a6ed6f6c4'
down_revision = 'c128c01a5520'


def upgrade():
    op.create_table('tokencredentialidhash',
                    sa.Column('credential_id_hash', sa.String(length=1024), nullable=False),
                    sa.Column('token_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['token_id'], ['token.id'], ),
                    sa.PrimaryKeyConstraint('credential_id_hash')
                    )


def downgrade():
    op.drop_table('tokencredentialidhash')
