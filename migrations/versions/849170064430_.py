"""add enqueue_job column to smtpserver table

Revision ID: 849170064430
Revises: a63df077051a
Create Date: 2018-11-22 10:04:00.330101

"""

# revision identifiers, used by Alembic.
revision = '849170064430'
down_revision = '48ee74b8a7c8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('smtpserver', sa.Column('enqueue_job', sa.Boolean(), nullable=False, server_default=sa.false()))
    except Exception as exx:
        print("Could not add column 'smtpserver.enqueue_job'")
        print(exx)


def downgrade():
    op.drop_column('smtpserver', 'enqueue_job')
