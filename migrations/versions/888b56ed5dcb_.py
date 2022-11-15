"""v3.6: Add table for custom user attributes

Revision ID: 888b56ed5dcb
Revises: d415d490eb05
Create Date: 2021-02-10 12:17:40.880224

"""

# revision identifiers, used by Alembic.
revision = '888b56ed5dcb'
down_revision = 'd415d490eb05'

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence


def dialect_supports_sequences():
    migration_context = context.get_context()
    return migration_context.dialect.supports_sequences


def create_seq(seq):
    if dialect_supports_sequences():
        op.execute(CreateSequence(seq))


def upgrade():
    try:
        seq = Sequence('customuserattribute')
        try:
            create_seq(seq)
        except Exception as _e:
            pass
        op.create_table('customuserattribute',
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
        op.create_index(op.f('ix_customuserattribute_resolver'), 'customuserattribute', ['resolver'], unique=False)
        op.create_index(op.f('ix_customuserattribute_user_id'), 'customuserattribute', ['user_id'], unique=False)
    except Exception as exx:
        print("Could not add table 'userattribute'.")
        print(exx)


def downgrade():
    op.drop_index(op.f('ix_customuserattribute_user_id'), table_name='customuserattribute')
    op.drop_index(op.f('ix_customuserattribute_resolver'), table_name='customuserattribute')
    op.drop_table('customuserattribute')
