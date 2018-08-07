"""add column position for event handlers

Revision ID: 1a0710df148b
Revises: 19f727d285e2
Create Date: 2018-08-03 12:36:17.091876

"""

# revision identifiers, used by Alembic.
revision = '1a0710df148b'
down_revision = '19f727d285e2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.add_column('eventhandler', sa.Column('position', sa.Unicode(length=10), default=u"post"))
    except Exception as exx:
        print("position column in eventhandler table obviously already exists.")
        print(exx)


def downgrade():
    op.drop_column('eventhandler', 'position')
