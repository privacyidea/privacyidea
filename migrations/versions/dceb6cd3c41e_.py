"""Add policycondition table, remove unused condition column from policy table

Revision ID: dceb6cd3c41e
Revises: b9131d0686eb
Create Date: 2019-07-02 12:19:19.646528

"""

# revision identifiers, used by Alembic.
revision = 'dceb6cd3c41e'
down_revision = 'b9131d0686eb'

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
        try:
            create_seq(Sequence('policycondition_seq'))
        except Exception as _e:
            pass
        op.create_table('policycondition',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('section', sa.Unicode(length=255), nullable=False),
        sa.Column('Key', sa.Unicode(length=255), nullable=False),
        sa.Column('comparator', sa.Unicode(length=255), nullable=False),
        sa.Column('Value', sa.Unicode(length=2000), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policy.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_row_format='DYNAMIC'
        )
    except Exception as exx:
        print("Could not create table policycondition: {!r}".format(exx))
    try:
        op.drop_column('policy', 'condition')
    except Exception as exx:
        print("Could not drop column policy.condition: {!r}".format(exx))

def downgrade():
    op.add_column('policy', sa.Column('condition', sa.INTEGER(), nullable=False))
    op.drop_table('policycondition')
