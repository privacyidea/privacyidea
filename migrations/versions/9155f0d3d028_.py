"""v3.6: set TLS v1.0 for existing ldap resolvers as legacy behavior while setting TLS v1.3 as default in v3.6

Revision ID: 9155f0d3d028
Revises: d5870fd2f2a4
Create Date: 2021-03-23 14:25:48.425762
privacyIDEA Version: 3.6

"""

# revision identifiers, used by Alembic.
revision = '9155f0d3d028'
down_revision = 'd5870fd2f2a4'

from alembic import op
from sqlalchemy import orm
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Sequence

Base = declarative_base()


class Resolver(Base):
    __tablename__ = 'resolver'
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}
    id = sa.Column(sa.Integer, Sequence("resolver_seq"), primary_key=True,
                   nullable=False)
    name = sa.Column(sa.Unicode(255), default=u"",
                     unique=True, nullable=False)
    rtype = sa.Column(sa.Unicode(255), default=u"",
                      nullable=False)
    config_list = orm.relationship('ResolverConfig',
                                  lazy='select',
                                  backref='resolver')
    realm_list = orm.relationship('ResolverRealm',
                                 lazy='select',
                                 foreign_keys='ResolverRealm.resolver_id')


class ResolverConfig(Base):
    __tablename__ = 'resolverconfig'
    id = sa.Column(sa.Integer, Sequence("resolverconf_seq"), primary_key=True)
    resolver_id = sa.Column(sa.Integer,
                            sa.ForeignKey('resolver.id'))
    Key = sa.Column(sa.Unicode(255), nullable=False)
    Value = sa.Column(sa.Unicode(2000), default=u'')
    Type = sa.Column(sa.Unicode(2000), default=u'')
    Description = sa.Column(sa.Unicode(2000), default=u'')
    __table_args__ = (sa.UniqueConstraint('resolver_id',
                                          'Key',
                                          name='rcix_2'),
                      {'mysql_row_format': 'DYNAMIC'})


class Realm(Base):
    """
    The realm table contains the defined realms. User Resolvers can be
    grouped to realms. This very table contains just contains the names of
    the realms. The linking to resolvers is stored in the table "resolverrealm".
    """
    __tablename__ = 'realm'
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}
    id = sa.Column(sa.Integer, Sequence("realm_seq"), primary_key=True,
                   nullable=False)
    name = sa.Column(sa.Unicode(255), default=u'',
                     unique=True, nullable=False)
    default = sa.Column(sa.Boolean(), default=False)
    option = sa.Column(sa.Unicode(40), default=u'')
    resolver_list = orm.relationship('ResolverRealm',
                                     lazy='select',
                                     foreign_keys='ResolverRealm.realm_id')


class ResolverRealm(Base):
    """
    This table stores which Resolver is located in which realm
    This is a N:M relation
    """
    __tablename__ = 'resolverrealm'
    id = sa.Column(sa.Integer, Sequence("resolverrealm_seq"), primary_key=True)
    resolver_id = sa.Column(sa.Integer, sa.ForeignKey("resolver.id"))
    realm_id = sa.Column(sa.Integer, sa.ForeignKey("realm.id"))
    # If there are several resolvers in a realm, the priority is used the
    # find a user first in a resolver with a higher priority (i.e. lower number)
    priority = sa.Column(sa.Integer)
    resolver = orm.relationship(Resolver,
                               lazy="joined",
                               foreign_keys="ResolverRealm.resolver_id")
    realm = orm.relationship(Realm,
                            lazy="joined",
                            foreign_keys="ResolverRealm.realm_id")
    __table_args__ = (sa.UniqueConstraint('resolver_id',
                                          'realm_id',
                                          name='rrix_2'),
                      {'mysql_row_format': 'DYNAMIC'})


def upgrade():
    try:
        bind = op.get_bind()
        session = orm.Session(bind=bind)
        ldapresolvers_list = []
        # get all ldap resolvers
        for row in session.query(Resolver).filter(Resolver.rtype == 'ldapresolver'):
            ldapresolvers_list.append(row.id)
        # set the legacy TLS Version to v1.0 (=3) for all existing ldap resolvers
        for resolver_id in ldapresolvers_list:
            base_query = session.query(ResolverConfig).filter(ResolverConfig.resolver_id == resolver_id)
            # check for LDAPS
            LDAPURI_qry = base_query.filter(ResolverConfig.Key == "LDAPURI").first()
            if LDAPURI_qry:
                LDAPS = True if LDAPURI_qry.Value.startswith('ldaps') else False
            else:
                LDAPS = None
            # check for STARTTLS
            START_TLS_qry = base_query.filter(ResolverConfig.Key == "START_TLS").first()
            if START_TLS_qry:
                START_TLS = True if START_TLS_qry.Value.lower() == 'true' else False
            else:
                START_TLS = False
            # check if TLS_VERSION is already set. If not, we will use TLS v1.0 as a robust default
            TLS_VERSION_qry = base_query.filter(ResolverConfig.Key == "TLS_VERSION").first()
            if TLS_VERSION_qry:
                TLS_VERSION = TLS_VERSION_qry.Value
            else:
                TLS_VERSION = None
            # For resolvers that had TLS_VERSION set but empty or not set at all use TLS v1.0
            if (LDAPS or START_TLS):
                if TLS_VERSION_qry is None:
                    session.add(ResolverConfig(resolver_id=resolver_id, Key="TLS_VERSION", Value="3",
                                               Type=u'int'))
                elif TLS_VERSION == "":
                    base_query.filter(ResolverConfig.Key == "TLS_VERSION").update({"Value": "3"})
        session.commit()

    except Exception as exx:
        session.rollback()
        print("Failed to set TLS v1.0 for all existing ldap resolvers to keep the legacy behavior.")
        print(exx)


def downgrade():
    pass
