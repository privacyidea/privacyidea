"""add dedicated adminuser to policies

Revision ID: a7e91b18a460
Revises: 0c7123345224
Create Date: 2020-01-29 13:42:15.390923

"""

# revision identifiers, used by Alembic.
revision = 'a7e91b18a460'
down_revision = '0c7123345224'

from alembic import op
import sqlalchemy as sa
from privacyidea.models import Policy
from sqlalchemy import orm


def upgrade():
    try:
        op.add_column('policy', sa.Column('adminuser', sa.Unicode(length=256), nullable=True))
    except Exception as exx:
        print('Adding of column "adminuser" in table policy failed: {!r}'.format(exx))
        print('This is expected behavior if this column already exists.')

    # Now that we added the column in the table, we can move the "user" from admin-policies to
    # the "adminuser" column

    try:
        bind = op.get_bind()
        session = orm.Session(bind=bind)
        pol_name = None
        for policy in session.query(Policy).filter(Policy.user != "", Policy.scope == "admin"):
            pol_name = policy.name
            # move the "user" to the "adminuser"
            policy.adminuser = policy.user
            policy.user = u""
        session.commit()
    except Exception as exx:
        session.rollback()
        print("Failed to migrate column adminuser in policies due to error in policy '{0!s}'.".format(pol_name))
        print(exx)


def downgrade():
    op.drop_column('policy', 'adminuser')
