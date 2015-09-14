"""Add column Type to the TokenInfo

Revision ID: 2551ee982544
Revises: 4f32a4e1bf33
Create Date: 2015-02-02 18:05:02.480354

"""

# revision identifiers, used by Alembic.
revision = '2551ee982544'
down_revision = '4f32a4e1bf33'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('tokeninfo', sa.Column('Type', sa.Unicode(length=100), nullable=True))
    except Exception as exx:
        print("Could not add the column 'Type' to table tokeninfo")
        print (exx)
    ### end Alembic commands ###


def downgrade():
    op.drop_column('tokeninfo', 'Type')
    ### end Alembic commands ###
