"""empty message

Revision ID: b637a1eeeeeb
Revises: 056b6642ff5d
Create Date: 2026-01-16 12:21:02.005022

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b637a1eeeeeb'
down_revision = '056b6642ff5d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('smtpserver', schema=None) as batch_op:
        batch_op.add_column(sa.Column('smime', sa.Boolean(), nullable=False))
        batch_op.add_column(sa.Column('dont_send_on_error', sa.Boolean(), nullable=False))
        batch_op.add_column(sa.Column('private_key', sa.Unicode(length=255), nullable=True))
        batch_op.add_column(sa.Column('certificate', sa.Unicode(length=255), nullable=True))
        batch_op.add_column(sa.Column('private_key_password', sa.Unicode(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('smtpserver', schema=None) as batch_op:
        batch_op.drop_column('private_key_password')
        batch_op.drop_column('certificate')
        batch_op.drop_column('private_key')
        batch_op.drop_column('dont_send_on_error')
        batch_op.drop_column('smime')
