"""Add a generic admin policy for all admin read actions

Revision ID: 3d7f8b29cbb1
Revises: dceb6cd3c41e
Create Date: 2019-07-04 22:37:53.594962

"""

# revision identifiers, used by Alembic.
revision = '3d7f8b29cbb1'
down_revision = 'dceb6cd3c41e'

from alembic import op
import sqlalchemy as sa

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import orm
from sqlalchemy.schema import Sequence
from privacyidea.lib.policy import SCOPE, ACTION

Base = declarative_base()

# dashes are not allowed, when creating policies in the WebUI
# or via the library. So we are sure, that in normal operation
# this policy can never be created.
POLICYNAME = u"pi-update-policy-3d7f8b29cbb1"


class Policy(Base):
    """
    The policy table contains policy definitions which control
    the behaviour during
     * enrollment
     * authentication
     * authorization
     * administration
     * user actions
    """
    __tablename__ = "policy"
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}
    id = sa.Column(sa.Integer, Sequence("policy_seq"), primary_key=True)
    active = sa.Column(sa.Boolean, default=True)
    check_all_resolvers = sa.Column(sa.Boolean, default=False)
    name = sa.Column(sa.Unicode(64), unique=True, nullable=False)
    scope = sa.Column(sa.Unicode(32), nullable=False)
    action = sa.Column(sa.Unicode(2000), default=u"")
    realm = sa.Column(sa.Unicode(256), default=u"")
    adminrealm = sa.Column(sa.Unicode(256), default=u"")
    resolver = sa.Column(sa.Unicode(256), default=u"")
    user = sa.Column(sa.Unicode(256), default=u"")
    client = sa.Column(sa.Unicode(256), default=u"")
    time = sa.Column(sa.Unicode(64), default=u"")
    # If there are multiple matching policies, choose the one
    # with the lowest priority number. We choose 1 to be the default priotity.
    priority = sa.Column(sa.Integer, default=1, nullable=False)


def upgrade():
    """
    During upgrade we check, if admin policies exist.
    If so, we add a generic policy for all admins, that allows to
    read all configuration, which mimicks the previous behaviour
    :return:
    """
    actions = u",".join([ACTION.PERIODICTASKREAD, ACTION.MACHINERESOLVERREAD,
                         ACTION.PRIVACYIDEASERVERREAD, ACTION.RADIUSSERVERREAD,
                         ACTION.SMTPSERVERREAD, ACTION.EVENTHANDLINGREAD,
                         ACTION.POLICYREAD, ACTION.RESOLVERREAD,
                         ACTION.CACONNECTORREAD, ACTION.SMSGATEWAYREAD,
                         ACTION.STATISTICSREAD, ACTION.SYSTEMREAD])

    bind = op.get_bind()
    session = orm.Session(bind=bind)
    if session.query(Policy.id).filter(Policy.scope == u"{0!s}".format(SCOPE.ADMIN),
                                       Policy.active.is_(True)).all():

        if session.query(Policy.id).filter_by(name=POLICYNAME).first() is None:
            # add policy
            tokenlist_pol = Policy(name=POLICYNAME, scope=u"{0!s}".format(SCOPE.ADMIN),
                                   action=actions)
            session.add(tokenlist_pol)
            print("Added '{0!s}' action for admin policies.".format(actions))
        else:
            print("Policy {} already exists.".format(POLICYNAME))
    else:
        print("No admin policy active. No need to create '{0!s}' action.".format(actions))

    try:
        session.commit()
    except Exception as exx:
        print("Could not create policy {}: {!r}".format(POLICYNAME, exx))
        print(exx)


def downgrade():
    # Delete the policy, if it still exists
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    session.query(Policy).filter(Policy.name == u"{0!s}".format(POLICYNAME)).delete()
    session.commit()
