"""Move policy conditions to a separate table

Revision ID: 7ac61e64e16d
Revises: 849170064430
Create Date: 2019-06-04 16:06:22.890250

"""

# revision identifiers, used by Alembic.
from sqlalchemy import Sequence, orm
from sqlalchemy.ext.declarative import declarative_base

from privacyidea.models import Policy

revision = '7ac61e64e16d'
down_revision = '849170064430'

from alembic import op
import sqlalchemy as sa

Base = declarative_base()


class OldPolicy(Base):
    __tablename__ = 'policy'
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
    condition = sa.Column(sa.Integer, default=0, nullable=False)
    priority = sa.Column(sa.Integer, default=1, nullable=False)


class PolicyCondition(Base):
    __tablename__ = "policycondition"
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}

    id = sa.Column(sa.Integer, Sequence("policycondition_seq"), primary_key=True)
    policy_id = sa.Column(sa.Integer, sa.ForeignKey('policy.id'), nullable=False)
    key = sa.Column(sa.Unicode(255), nullable=False)
    value = sa.Column(sa.Unicode(2000), default=u'')
    comparator = sa.Column(sa.Unicode(255), default=u'equal')


def upgrade():
    # Add new policycondition table
    try:
        op.create_table('policycondition',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.Unicode(length=255), nullable=False),
        sa.Column('value', sa.Unicode(length=2000), nullable=True),
        sa.Column('comparator', sa.Unicode(length=255), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['policy.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'key', name='pcix_1'),
        mysql_row_format='DYNAMIC'
        )

    except Exception as exx:
        print("Could not create policycondition table.")
        print(exx)

    # Migrate data
    try:
        bind = op.get_bind()
        session = orm.Session(bind=bind)
        for old_policy in session.query(OldPolicy):
            print(u'Migrating policy {!r} ...'.format(old_policy.name))
            for attribute in ['adminrealm', 'client', 'user', 'resolver', 'time', 'realm']:
                value = getattr(old_policy, attribute)
                if value is not None:
                    print(u'    {!s} = {!r}'.format(attribute, value))
                    condition_object = PolicyCondition(policy_id=old_policy.id,
                                                       key=attribute,
                                                       comparator='equal',
                                                       value=value)
                    session.add(condition_object)
        session.commit()

        op.drop_column(u'policy', 'adminrealm')
        op.drop_column(u'policy', 'client')
        op.drop_column(u'policy', 'user')
        op.drop_column(u'policy', 'resolver')
        op.drop_column(u'policy', 'time')
        op.drop_column(u'policy', 'realm')
        op.drop_column(u'policy', 'condition')
    except Exception as exx:
        session.rollback()
        print("Failed to migrate policy conditions!")
        print(exx)


def downgrade():
    op.add_column(u'policy', sa.Column('condition', sa.INTEGER(), nullable=False))
    op.add_column(u'policy', sa.Column('realm', sa.VARCHAR(length=256), nullable=True))
    op.add_column(u'policy', sa.Column('time', sa.VARCHAR(length=64), nullable=True))
    op.add_column(u'policy', sa.Column('resolver', sa.VARCHAR(length=256), nullable=True))
    op.add_column(u'policy', sa.Column('user', sa.VARCHAR(length=256), nullable=True))
    op.add_column(u'policy', sa.Column('client', sa.VARCHAR(length=256), nullable=True))
    op.add_column(u'policy', sa.Column('adminrealm', sa.VARCHAR(length=256), nullable=True))
    op.drop_table('policycondition')
