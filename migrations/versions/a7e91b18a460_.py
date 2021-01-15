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
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# Use table definition from the point where the changes took place. If we use
# the table definition from models.py we might run into problems
class Policy(Base):
    __tablename__ = "policy"
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}
    id = sa.Column(sa.Integer, sa.Sequence("policy_seq"), primary_key=True)
    active = sa.Column(sa.Boolean, default=True)
    check_all_resolvers = sa.Column(sa.Boolean, default=False)
    name = sa.Column(sa.Unicode(64), unique=True, nullable=False)
    scope = sa.Column(sa.Unicode(32), nullable=False)
    action = sa.Column(sa.Unicode(2000), default=u"")
    realm = sa.Column(sa.Unicode(256), default=u"")
    adminrealm = sa.Column(sa.Unicode(256), default=u"")
    adminuser = sa.Column(sa.Unicode(256), default=u"")
    resolver = sa.Column(sa.Unicode(256), default=u"")
    user = sa.Column(sa.Unicode(256), default=u"")
    client = sa.Column(sa.Unicode(256), default=u"")
    time = sa.Column(sa.Unicode(64), default=u"")
    priority = sa.Column(sa.Integer, default=1, nullable=False)


def upgrade():
    try:
        op.add_column('policy', sa.Column('adminuser', sa.Unicode(length=256), nullable=True))
    except Exception as exx:
        print('Adding of column "adminuser" in table policy failed: {!r}'.format(exx))
        print('This is expected behavior if this column already exists.')

    # Now that we added the column in the table, we can move the "user" from admin-policies to
    # the "adminuser" column
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    pol_name = None
    try:
        for policy in session.query(Policy).filter(Policy.user != u"", Policy.scope == u"admin"):
            pol_name = policy.name
            # move the "user" to the "adminuser"
            policy.adminuser = policy.user
            policy.user = u""
        session.commit()
    except Exception as exx:
        session.rollback()
        print("Failed to migrate column adminuser in policies due to error in "
              "policy '{0!s}'.".format(pol_name))
        print(exx)


def downgrade():
    op.drop_column('policy', 'adminuser')
