"""v3.13: Add S/MIME columns to smtpserver table

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

SMTPSERVER_COLUMNS = ['smime', 'dont_send_on_error', 'private_key', 'certificate', 'private_key_password']


def upgrade():
    bind = op.get_bind()
    existing_cols = {col['name'] for col in sa.inspect(bind).get_columns('smtpserver')}
    with op.batch_alter_table('smtpserver', schema=None) as batch_op:
        if 'smime' not in existing_cols:
            batch_op.add_column(sa.Column('smime', sa.Boolean(), nullable=True))
        if 'dont_send_on_error' not in existing_cols:
            batch_op.add_column(sa.Column('dont_send_on_error', sa.Boolean(), nullable=True))
        if 'private_key' not in existing_cols:
            batch_op.add_column(sa.Column('private_key', sa.Unicode(length=255), nullable=True))
        if 'certificate' not in existing_cols:
            batch_op.add_column(sa.Column('certificate', sa.Unicode(length=255), nullable=True))
        if 'private_key_password' not in existing_cols:
            batch_op.add_column(sa.Column('private_key_password', sa.Unicode(length=255), nullable=True))


def downgrade():
    bind = op.get_bind()
    existing_cols = {col['name'] for col in sa.inspect(bind).get_columns('smtpserver')}
    with op.batch_alter_table('smtpserver', schema=None) as batch_op:
        for col in reversed(SMTPSERVER_COLUMNS):
            if col in existing_cols:
                batch_op.drop_column(col)
