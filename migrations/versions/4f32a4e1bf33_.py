"""Update from version 1.5 to version 2.0

Revision ID: 4f32a4e1bf33
Revises:
ne
Create Date: 2015-01-26 10:06:50.568505

"""

# revision identifiers, used by Alembic.
revision = '4f32a4e1bf33'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session as BaseSession, relationship
import json

Session = sessionmaker()

Base = declarative_base()


class Token_old(Base):
    __tablename__ = 'Token_old'
    privacyIDEATokenId = sa.Column(sa.Integer, primary_key=True, nullable=False)
    privacyIDEATokenDesc = sa.Column(sa.Unicode(80), default=u'')
    privacyIDEATokenSerialnumber = sa.Column(sa.Unicode(40), default=u'',
                                 unique=True, nullable=False, index=True)
    privacyIDEATokenType = sa.Column(sa.Unicode(30))
    privacyIDEATokenInfo = sa.Column(sa.Unicode(2000))
    privacyIDEATokenPinUser = sa.Column(sa.Unicode(512))
    privacyIDEATokenPinUserIV = sa.Column(sa.Unicode(32))
    privacyIDEATokenPinSO = sa.Column(sa.Unicode(512))
    privacyIDEATokenPinSOIV = sa.Column(sa.Unicode(32))
    privacyIDEAIdResolver = sa.Column(sa.Unicode(120))
    privacyIDEAIdResClass = sa.Column(sa.Unicode(120))
    privacyIDEAUserid = sa.Column(sa.Unicode(320))
    privacyIDEASeed = sa.Column(sa.Unicode(32))
    privacyIDEAOtpLen = sa.Column(sa.Integer)
    privacyIDEAPinHash = sa.Column(sa.Unicode(512))
    privacyIDEAKeyEnc = sa.Column(sa.Unicode(1024))
    privacyIDEAKeyIV = sa.Column(sa.Unicode(32))
    privacyIDEAMaxFail = sa.Column(sa.Integer)
    privacyIDEAIsactive = sa.Column(sa.Boolean)
    privacyIDEAFailCount = sa.Column(sa.Integer)
    privacyIDEACount = sa.Column(sa.Integer)
    privacyIDEACountWindow = sa.Column(sa.Integer)
    privacyIDEASyncWindow = sa.Column(sa.Integer)


class Token(Base):
    """
    The Token table contains all token information.
    """
    __tablename__ = 'token'
    id = sa.Column(sa.Integer,
                   primary_key=True,
                   nullable=False)
    description = sa.Column(sa.Unicode(80), default=u'')
    serial = sa.Column(sa.Unicode(40), default=u'',
                       unique=True,
                       nullable=False,
                       index=True)
    tokentype = sa.Column(sa.Unicode(30), default=u'HOTP', index=True)
    user_pin = sa.Column(sa.Unicode(512), default=u'')
    user_pin_iv = sa.Column(sa.Unicode(32), default=u'')
    so_pin = sa.Column(sa.Unicode(512), default=u'')
    so_pin_iv = sa.Column(sa.Unicode(32), default=u'')
    resolver = sa.Column(sa.Unicode(120), default=u'', index=True)
    resolver_type = sa.Column(sa.Unicode(120), default=u'')
    user_id = sa.Column(sa.Unicode(320), default=u'', index=True)
    pin_seed = sa.Column(sa.Unicode(32), default=u'')
    otplen = sa.Column(sa.Integer(), default=6)
    pin_hash = sa.Column(sa.Unicode(512), default=u'')
    key_enc = sa.Column(sa.Unicode(1024), default=u'')
    key_iv = sa.Column(sa.Unicode(32), default=u'')
    maxfail = sa.Column(sa.Integer(), default=10)
    active = sa.Column(sa.Boolean(), default=True)
    failcount = sa.Column(sa.Integer(), default=0)
    count = sa.Column(sa.Integer(), default=0)
    count_window = sa.Column(sa.Integer(), default=10)
    sync_window = sa.Column(sa.Integer(), default=1000)
    rollout_state = sa.Column(sa.Unicode(10), default=u'')
    info = relationship('TokenInfo', lazy='dynamic', backref='info')


class TokenInfo(Base):
    """
    The Info Table for additional, flexible information store with each token.
    The idea of the tokeninfo table is, that new token types can easily store
    long additional information.
    """
    __tablename__ = 'tokeninfo'
    id = sa.Column(sa.Integer, primary_key=True)
    Key = sa.Column(sa.Unicode(255),
                    nullable=False)
    Value = sa.Column(sa.UnicodeText(), default=u'')
    Description = sa.Column(sa.Unicode(2000), default=u'')
    token_id = sa.Column(sa.Integer(),
                         sa.ForeignKey('token.id'))
    token = relationship('Token', lazy='joined', backref='info_list')
    __table_args__ = (sa.UniqueConstraint('token_id',
                                          'Key',
                                          name='tiix_2'), {})


class TokenRealm(Base):
    """This table stores in which realms a token is assign"""
    __tablename__ = 'tokenrealm'
    id = sa.Column(sa.Integer(), primary_key=True, nullable=True)
    token_id = sa.Column(sa.Integer(),
                         sa.ForeignKey('token.id'))
    realm_id = sa.Column(sa.Integer(),
                         sa.ForeignKey('realm.id'))
    token = relationship('Token',
                            lazy='joined',
                            backref='realm_list')
    realm = relationship('Realm',
                            lazy='joined',
                            backref='token_list')
    __table_args__ = (sa.UniqueConstraint('token_id',
                                          'realm_id',
                                          name='trix_2'), {})

class TokenRealm_old(Base):
    """This table stores in which realms a token is assign"""
    __tablename__ = 'TokenRealm_old'
    id = sa.Column(sa.Integer(), primary_key=True, nullable=True)
    token_id = sa.Column(sa.Integer(),
                         sa.ForeignKey('token.id'))
    realm_id = sa.Column(sa.Integer(),
                         sa.ForeignKey('realm.id'))

class Realm(Base):
    __tablename__ = 'realm'
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    name = sa.Column(sa.Unicode(255), default=u'',
                     unique=True, nullable=False)
    default = sa.Column(sa.Boolean(), default=False)
    option = sa.Column(sa.Unicode(40), default=u'')

class Realm_old(Base):
    __tablename__ = 'Realm_old'
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    name = sa.Column(sa.Unicode(255), default=u'',
                     unique=True, nullable=False)
    default = sa.Column(sa.Boolean(), default=False)
    option = sa.Column(sa.Unicode(40), default=u'')


class Resolver(Base):
    __tablename__ = 'resolver'
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    name = sa.Column(sa.Unicode(255), default=u"",
                     unique=True, nullable=False)
    rtype = sa.Column(sa.Unicode(255), default=u"",
                      nullable=False)
    rconfig = relationship('ResolverConfig', lazy='dynamic', backref='resolver')


class ResolverConfig(Base):
    """
    Each Resolver can have multiple configuration entries.
    The config entries are referenced by the id of the resolver
    """
    __tablename__ = 'resolverconfig'
    id = sa.Column(sa.Integer, primary_key=True)
    resolver_id = sa.Column(sa.Integer,
                            sa.ForeignKey('resolver.id'))
    Key = sa.Column(sa.Unicode(255), nullable=False)
    Value = sa.Column(sa.Unicode(2000), default=u'')
    Type = sa.Column(sa.Unicode(2000), default=u'')
    Description = sa.Column(sa.Unicode(2000), default=u'')
    reso = relationship('Resolver',
                           lazy='joined',
                           backref='config_list')
    __table_args__ = (sa.UniqueConstraint('resolver_id',
                                          'Key',
                                          name='rcix_2'), {})


class Config(Base):
    __tablename__ = "config"
    Key = sa.Column(sa.Unicode(255),
                    primary_key=True,
                    nullable=False)
    Value = sa.Column(sa.Unicode(2000), default=u'')
    Type = sa.Column(sa.Unicode(2000), default=u'')
    Description = sa.Column(sa.Unicode(2000), default=u'')


class Config_old(Base):
    __tablename__ = "Config_old"
    Key = sa.Column(sa.Unicode(255),
                    primary_key=True,
                    nullable=False)
    Value = sa.Column(sa.Unicode(2000), default=u'')
    Type = sa.Column(sa.Unicode(2000), default=u'')
    Description = sa.Column(sa.Unicode(2000), default=u'')


class ResolverRealm(Base):
    """
    This table stores which Resolver is located in which realm
    This is a N:M relation
    """
    __tablename__ = 'resolverrealm'
    id = sa.Column(sa.Integer, primary_key=True)
    resolver_id = sa.Column(sa.Integer, sa.ForeignKey("resolver.id"))
    realm_id = sa.Column(sa.Integer, sa.ForeignKey("realm.id"))
    # this will create a "realm_list" in the resolver object
    resolver = relationship(Resolver,
                               lazy="joined",
                               foreign_keys="ResolverRealm.resolver_id",
                               backref="realm_list")
    # this will create a "resolver list" in the realm object
    realm = relationship(Realm,
                            lazy="joined",
                            foreign_keys="ResolverRealm.realm_id",
                            backref="resolver_list")
    __table_args__ = (sa.UniqueConstraint('resolver_id',
                                          'realm_id',
                                          name='rrix_2'), {})


class Admin(Base):
    """
    The administrators for managing the system.
    Certain realms can be defined to be administrative realms in addition
    """
    __tablename__ = "admin"
    username = sa.Column(sa.Unicode(120),
                         primary_key=True,
                         nullable=False)
    password = sa.Column(sa.Unicode(255))
    email = sa.Column(sa.Unicode(255))


def create_update_token_table():
    print("----------------------------------")
    print("Migrating the Token information...")
    print("----------------------------------")
    # rename the old table
    op.rename_table('Token', 'Token_old')

    bind = op.get_bind()
    session = Session(bind=bind)

    # create the tables
    Token.__table__.create(bind)
    TokenInfo.__table__.create(bind)

    for ot in session.query(Token_old):
        print(ot.privacyIDEATokenSerialnumber)
        resolvername = None
        resolvertype = None
        if ot.privacyIDEAIdResClass:
            reso = ot.privacyIDEAIdResClass.split(".")
            resolvername = reso[-1]
            if reso[3] == "PasswdIdResolver":
                resolvertype = "passwdresolver"
            elif reso[3] == "LDAPIdResolver":
                resolvertype = "ldapresolver"
            elif reso[3] == "SQLIdResolver":
                resolvertype = "sqlresolver"
            else:
                print("Error: Unknown resolvertype: {0!s}".format(reso[3]))
                resolvertype = "FIXME"
        if ot.privacyIDEATokenType.lower() == "hmac":
            tokentype = "hotp"
        else:
            tokentype = ot.privacyIDEATokenType.lower()

        nt = Token(id=ot.privacyIDEATokenId,
                   serial=ot.privacyIDEATokenSerialnumber,
                   active=ot.privacyIDEAIsactive,
                   description=ot.privacyIDEATokenDesc,
                   tokentype=tokentype,
                   user_pin=ot.privacyIDEATokenPinUser,
                   user_pin_iv=ot.privacyIDEATokenPinUserIV,
                   so_pin=ot.privacyIDEATokenPinSO,
                   so_pin_iv=ot.privacyIDEATokenPinSOIV,
                   resolver=resolvername,
                   resolver_type=resolvertype,
                   user_id=ot.privacyIDEAUserid,
                   pin_seed=ot.privacyIDEASeed,
                   pin_hash=ot.privacyIDEAPinHash,
                   otplen=ot.privacyIDEAOtpLen,
                   key_enc=ot.privacyIDEAKeyEnc,
                   key_iv=ot.privacyIDEAKeyIV,
                   maxfail=ot.privacyIDEAMaxFail,
                   failcount=ot.privacyIDEAFailCount,
                   count=ot.privacyIDEACount,
                   count_window=ot.privacyIDEACountWindow,
                   sync_window=ot.privacyIDEASyncWindow
                   )

        session.add(nt)
        if ot.privacyIDEATokenInfo:
            info = json.loads(ot.privacyIDEATokenInfo)
            for k, v in info.iteritems():
                ti = TokenInfo(Key=k,
                               Value=v,
                               token_id=nt.id)
                session.add(ti)

    session.commit()


def create_resolver_config():
    # read the resolver config from the table config
    # and create ONE Resolver entry and the corresponding ResolverConfig
    # entries.

    print("----------------------------------")
    print("Read the resolvers from the config")

    bind = op.get_bind()
    session = Session(bind=bind)

    # create the tables
    Resolver.__table__.create(bind)
    ResolverConfig.__table__.create(bind)

    # Read Passwd resolver like privacyidea.passwdresolver.*.name
    for resolvertype in ["passwdresolver", "ldapresolver", "sqlresolver"]:
        print("processing {0!s}".format(resolvertype))
        resolvers = {}
        configs = session.query(Config_old).filter(
            Config_old.Key.like("privacyidea." + resolvertype + ".%"))
        for oc in configs:
            (_pi, _rtype, key, name) = oc.Key.split(".")
            value = oc.Value
            desc = oc.Description
            if name not in resolvers:
                resolvers[name] = {key : {"value": value,
                                          "desc": desc}}
            else:
                resolvers[name][key] = {"value": value,
                                        "desc": desc}

        for resolvername in resolvers:
            r = Resolver(name=resolvername,
                         rtype=resolvertype)
            session.add(r)
            session.commit()
            # get the DB id and save the config
            rid = session.query(Resolver).filter(Resolver.name==resolvername).first(

            ).id
            resconfig = resolvers.get(resolvername)
            for k, v in resconfig.iteritems():
                rc = ResolverConfig(Key=k, Value=v.get("value"),
                                    Description=v.get("desc"), resolver_id=rid)
                session.add(rc)
            session.commit()

        # Remove the resolvers from the Config table
        session.query(Config_old).\
            filter(Config_old.Key.like("privacyidea." + resolvertype + ".%")).\
            delete(synchronize_session=False)
        session.commit()


def create_realms():
    """
    privacyidea.useridresolver.group.realm2
    privacyidea.lib.resolvers.LDAPIdResolver.IdResolver.themis, ...
    :return:
    """
    bind = op.get_bind()
    session = Session(bind=bind)

    op.rename_table('Realm', 'Realm_old')
    op.rename_table('TokenRealm', 'TokenRealm_old')
    # create the tables
    Realm.__table__.create(bind)
    ResolverRealm.__table__.create(bind)
    TokenRealm.__table__.create(bind)

    print("--------------------------------")
    print("Migrating Realms and tokenrealms")
    for realm in session.query(Realm_old):
        try:
            r = Realm(name=realm.name, id=realm.id, default=realm.default,
                      option=realm.option)
            session.add(r)
            session.commit()
        except Exception as exx:
            print(exx)

    for tokenrealm in session.query(TokenRealm_old):
        try:
            tr = TokenRealm(id=tokenrealm.id, token_id=tokenrealm.token_id,
                            realm_id=tokenrealm.realm_id)
            session.add(tr)
            session.commit()
        except Exception as exx:
            session.rollback()
            print (exx)

    print("Add resolvers to the realms")
    realms = session.query(Config_old).\
        filter(Config_old.Key.like("privacyidea.useridresolver.group.%"))
    for realm in realms:
        realmname = realm.Key.split(".")[-1]
        print(realmname)
        resolver_list = [x.split(".")[-1] for x in realm.Value.split(",")]
        print("   with resolvers: {0!s}".format(resolver_list))
        for resolvername in resolver_list:
            try:
                res_id = session.query(Resolver).\
                    filter(Resolver.name == resolvername).first().id
                realm_id = session.query(Realm).\
                    filter(Realm.name == realmname).first().id
                rr = ResolverRealm(resolver_id=res_id, realm_id=realm_id)
                session.add(rr)
                session.commit()
            except Exception as exx:
                session.rollback()
                print(exx)

    # Remove the realms from the config
    session.query(Config_old).\
        filter(Config_old.Key.like("privacyidea.useridresolver.group.%")).\
        delete(synchronize_session=False)
    session.commit()


def create_policy():
    # TODO
    pass


def finalize_config():
    bind = op.get_bind()
    session = Session(bind=bind)

    Config.__table__.create(bind)
    print("--------------------------------")
    print("Migrate remaining config entries")

    configs = session.query(Config_old)
    for conf in configs:
        key = ".".join(conf.Key.split(".")[1:])
        value = conf.Value
        Type = conf.Type
        Description = conf.Description
        if key == "FailCounterIncOnFalsePin":
            key = "IncFailCountOnFalsePin"
            value = (conf.Value == "True")
        if Type == "bool":
            value = (conf.Value == "True")
        if key == "splitAtSign":
            value = (conf.Value == "True")
            Type = "bool"

        c = Config(Key=key,
                   Value=value,
                   Type=Type,
                   Description=Description)
        session.add(c)
    session.commit()
    op.drop_table('Config_old')


def create_new_tables():
    print("Create remaining tables")
    bind = op.get_bind()
    Admin.__table__.create(bind)
    #op.drop_table("Challenges")
    op.create_table('challenge',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('transaction_id', sa.Unicode(length=64), nullable=False),
    sa.Column('data', sa.Unicode(length=512), nullable=True),
    sa.Column('challenge', sa.Unicode(length=512), nullable=True),
    sa.Column('session', sa.Unicode(length=512), nullable=True),
    sa.Column('serial', sa.Unicode(length=40), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('expiration', sa.DateTime(), nullable=True),
    sa.Column('received_count', sa.Integer(), nullable=True),
    sa.Column('otp_valid', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # drop old tables
    op.drop_table("MachineTokenOptions")
    op.drop_table("MachineUserOptions")
    op.drop_table("MachineUser")
    op.drop_table("MachineToken")
    op.drop_table("ClientMachine")

    op.drop_table("TokenRealm_old")
    op.drop_table("Realm_old")
    op.drop_table("Token_old")


def upgrade():
    create_update_token_table()
    # rename the old table
    op.rename_table('Config', 'Config_old')
    create_resolver_config()
    create_realms()
    create_policy()
    finalize_config()
    create_new_tables()


def downgrade():
    print("We do not support downgrading to version 1.5.")

