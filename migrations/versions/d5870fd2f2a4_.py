"""merge two heads of audit log and auth_cache

Revision ID: d5870fd2f2a4
Revises: ('3236a1abf1c6', '8d40dbcfda25')
Create Date: 2020-11-21 14:12:41.097913

"""

# revision identifiers, used by Alembic.
revision = 'd5870fd2f2a4'
down_revision = ('3236a1abf1c6', '8d40dbcfda25')

from alembic import op
import sqlalchemy as sa


def upgrade():
    pass


def downgrade():
    pass
