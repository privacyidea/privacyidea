"""version 3.14 adding table pi_internal

Revision ID: dbee40db26ba
Revises: b1a2c3d4e5f6
Create Date: 2026-05-07 13:22:55.368183

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'dbee40db26ba'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    pi_internal_seq = sa.Sequence('pi_internal_seq')
    op.execute(sa.schema.CreateSequence(pi_internal_seq))
    op.create_table('pi_internal',
                    sa.Column('id', sa.Integer(), server_default=pi_internal_seq.next_value(), nullable=False),
                    sa.Column('name', sa.Unicode(length=255), nullable=False),
                    sa.Column('check_value', sa.Unicode(length=2000), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    pi_internal_seq = sa.Sequence('pi_internal_seq')
    op.drop_table('pi_internal')
    op.execute(sa.schema.DropSequence(pi_internal_seq))
