"""Add table privacyideaserver

Revision ID: 36428afb2457
Revises: 205bda834127
Create Date: 2017-08-24 09:02:52.507395

"""

# revision identifiers, used by Alembic.
revision = '36428afb2457'
down_revision = '205bda834127'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('privacyideaserver',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.Unicode(length=255), nullable=False),
        sa.Column('url', sa.Unicode(length=255), nullable=False),
        sa.Column('tls', sa.Boolean(), nullable=True),
        sa.Column('description', sa.Unicode(length=2000), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('identifier')
        )
    except Exception as exx:
        print("Can not create table 'privacyideaserver'. It probably already "
              "exists")
        print (exx)


def downgrade():
    op.drop_table('privacyideaserver')

