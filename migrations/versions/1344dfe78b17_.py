"""v3.10: Add new association table tokencontainerrealm

Revision ID: 1344dfe78b17
Revises: cd51b7fe9d03
Create Date: 2024-06-17 14:24:31.100842

"""

# revision identifiers, used by Alembic.
revision = '1344dfe78b17'
down_revision = 'cd51b7fe9d03'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('tokencontainerrealm',
                        sa.Column('container_id', sa.Integer(), nullable=True),
                        sa.Column('realm_id', sa.Integer(), nullable=False),
                        sa.ForeignKeyConstraint(['container_id'], ['tokencontainer.id'], ),
                        sa.ForeignKeyConstraint(['realm_id'], ['realm.id'], ),
                        sa.PrimaryKeyConstraint('container_id', 'realm_id'),
                        sa.UniqueConstraint('container_id', 'realm_id'),
                        mysql_row_format='DYNAMIC'
                        )
    except Exception as e:
        print("Could not add table 'tokencontainerrealm' - probably already exists!")
        print(e)


def downgrade():
    op.drop_table('tokencontainerrealm')
