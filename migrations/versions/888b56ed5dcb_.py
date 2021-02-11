"""v3.6: Add table for additional user attributes

Revision ID: 888b56ed5dcb
Revises: d5870fd2f2a4
Create Date: 2021-02-10 12:17:40.880224

"""

# revision identifiers, used by Alembic.
revision = '888b56ed5dcb'
down_revision = 'd5870fd2f2a4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('userattribute',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Unicode(length=320), nullable=True),
            sa.Column('resolver', sa.Unicode(length=120), nullable=True),
            sa.Column('realm_id', sa.Integer(), nullable=True),
            sa.Column('Key', sa.Unicode(length=255), nullable=False),
            sa.Column('Value', sa.UnicodeText(), nullable=True),
            sa.Column('Type', sa.Unicode(length=100), nullable=True),
            sa.ForeignKeyConstraint(['realm_id'], ['realm.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_userattribute_resolver'), 'userattribute', ['resolver'], unique=False)
        op.create_index(op.f('ix_userattribute_user_id'), 'userattribute', ['user_id'], unique=False)
    except Exception as exx:
        print("Could not add table 'userattribute'.")
        print(exx)


def downgrade():
    op.drop_index(op.f('ix_userattribute_user_id'), table_name='userattribute')
    op.drop_index(op.f('ix_userattribute_resolver'), table_name='userattribute')
    op.drop_table('userattribute')

