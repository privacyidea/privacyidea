#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  2016-09-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
"""
You can use this script to migrate a LinOTP database to privacyIDEA.
All tokens and token assignments are transferred to privacyIDEA.

"""
# You need to change this!
LINOTP_URI = "mysql://linotp2:testtest@localhost/LinOTP2"
PRIVACYIDEA_URI = "mysql://pi:pi@localhost/pi"

from sqlalchemy import Table, MetaData, Column
from sqlalchemy import Integer, Unicode, Boolean, UnicodeText
metadata = MetaData()

token_table = Table("token", metadata,
                    Column("id", Integer, primary_key=True, nullable=False),
                    Column("description", Unicode(80), default=u''),
                    Column("serial", Unicode(40), default=u'', unique=True,
                           nullable=False, index=True),
                    Column("tokentype", Unicode(30), default=u'HOTP',
                           index=True),
                    Column("user_pin", Unicode(512), default=u''),
                    Column("user_pin_iv", Unicode(32), default=u''),
                    Column("so_pin", Unicode(512), default=u''),
                    Column("so_pin_iv", Unicode(32), default=u''),
                    Column("resolver", Unicode(120), default=u'', index=True),
                    Column("resolver_type",  Unicode(120), default=u''),
                    Column("user_id", Unicode(320), default=u'', index=True),
                    Column("pin_seed", Unicode(32), default=u''),
                    Column("otplen", Integer(), default=6),
                    Column("pin_hash", Unicode(512), default=u''),
                    Column("key_enc", Unicode(1024), default=u''),
                    Column("key_iv", Unicode(32), default=u''),
                    Column("maxfail", Integer(), default=10),
                    Column("active", Boolean(), nullable=False, default=True),
                    Column("revoked", Boolean(), default=False),
                    Column("locked", Boolean(), default=False),
                    Column("failcount", Integer(), default=0),
                    Column("count", Integer(), default=0),
                    Column("count_window", Integer(), default=10),
                    Column("sync_window", Integer(), default=1000),
                    Column("rollout_state", Unicode(10), default=u''))

tokeninfo_table = Table("tokeninfo", metadata,
                  Column("id", Integer, primary_key=True),
                  Column("Key", Unicode(255), nullable=False),
                  Column("Value", UnicodeText(), default=u''),
                  Column("Type", Unicode(100), default=u''),
                  Column("Description", Unicode(2000), default=u''),
                  Column("token_id", Integer()))

tokenrealm_table = Table("tokenrealm", metadata,
                         Column("id", Integer(), primary_key=True),
                         Column("token_id", Integer()),
                         Column("realm_id", Integer()))

realm_table = Table("realm", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("name", Unicode(255), default=u''),
                    Column("default",  Boolean(), default=False),
                    Column("option", Unicode(40), default=u''))

resolver_table = Table("resolver", metadata,
                       Column("id", Integer, primary_key=True),
                       Column("name", Unicode(255), default=u""),
                       Column("rtype", Unicode(255), default=u""))

resolver_config_table = Table("resolverconfig", metadata,
                              Column("id", Integer, primary_key=True),
                              Column("resolver_id", Integer),
                              Column("Key", Unicode(255), default=u""),
                              Column("Value", Unicode(2000), default=u""),
                              Column("Type", Unicode(2000), default=u""),
                              Column("Description", Unicode(2000), default=u""),
                              )

resolverrealm_table = Table("resolverrealm", metadata,
                            Column("id", Integer, primary_key=True),
                            Column("resolver_id", Integer),
                            Column("realm_id", Integer),
                            Column("priority", Integer))

#
# LinOTP table definitions
#
linotp_config_table = Table("Config", metadata,
                            Column("Key", Unicode(255)),
                            Column("Value", Unicode(2000)),
                            Column("Type", Unicode(2000)),
                            Column("Description", Unicode(2000))
                            )

linotp_tokenrealm_table = Table("TokenRealm", metadata,
                         Column("id", Integer(), primary_key=True),
                         Column("token_id", Integer()),
                         Column("realm_id", Integer()))

linotp_realm_table = Table("Realm", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("name", Unicode(255), default=u''),
                    Column("default",  Boolean(), default=False),
                    Column("option", Unicode(40), default=u''))

linotp_token_table = Table('Token',metadata,
                           Column('LinOtpTokenId', Integer(),
                                  primary_key=True, nullable=False),
                           Column(
                               'LinOtpTokenDesc', Unicode(80), default=u''),
                           Column('LinOtpTokenSerialnumber', Unicode(
                               40), default=u'', unique=True, nullable=False,
                                  index=True),
                           Column(
                               'LinOtpTokenType', Unicode(30), default=u'HMAC',
                               index=True),
                           Column(
                               'LinOtpTokenInfo', Unicode(2000), default=u''),
                           Column(
                               'LinOtpTokenPinUser', Unicode(512), default=u''),
                           Column(
                               'LinOtpTokenPinUserIV', Unicode(32),
                               default=u''),
                           Column(
                               'LinOtpTokenPinSO', Unicode(512), default=u''),
                           Column(
                               'LinOtpTokenPinSOIV', Unicode(32), default=u''),
                           Column(
                               'LinOtpIdResolver', Unicode(120), default=u'',
                               index=True),
                           Column(
                               'LinOtpIdResClass', Unicode(120), default=u''),
                           Column(
                               'LinOtpUserid', Unicode(320), default=u'',
                               index=True),
                           Column(
                               'LinOtpSeed', Unicode(32), default=u''),
                           Column(
                               'LinOtpOtpLen', Integer(), default=6),
                           Column(
                               'LinOtpPinHash', Unicode(512), default=u''),
                           Column(
                               'LinOtpKeyEnc', Unicode(1024), default=u''),
                           Column(
                               'LinOtpKeyIV', Unicode(32), default=u''),
                           Column(
                               'LinOtpMaxFail', Integer(), default=10),
                           Column(
                               'LinOtpIsactive', Boolean(), default=True),
                           Column(
                               'LinOtpFailCount', Integer(), default=0),
                           Column('LinOtpCount', Integer(), default=0),
                           Column(
                               'LinOtpCountWindow', Integer(), default=10),
                           Column(
                               'LinOtpSyncWindow', Integer(), default=1000)
                           )


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
import json

linotp_engine = create_engine(LINOTP_URI)
privacyidea_engine = create_engine(PRIVACYIDEA_URI)

linotp_session = sessionmaker(bind=linotp_engine)()
privacyidea_session = sessionmaker(bind=privacyidea_engine)()

conn_linotp = linotp_engine.connect()
conn_pi = privacyidea_engine.connect()

resolver_map = {"LDAPIdResolver": "ldapresolver",
                "SQLIdResolver": "sqlresolver",
                "PasswdIdResolver": "passwdresolver"}

# Process Tokens

s = select([linotp_token_table])
result = conn_linotp.execute(s)
for r in result:
    print("migrating token {0!s}".format(r["LinOtpTokenSerialnumber"]))
    # Adapt type
    type = r["LinOtpTokenType"]
    if type.lower() == "hmac":
        type = "HOTP"
    # Adapt resolver
    resolver = r["LinOtpIdResolver"].split(".")[-1]

    # Adapt resolver type
    resolver_type = ""
    if r["LinOtpIdResClass"]:
        resolver_type = r['LinOtpIdResClass'].split(".")[1]
        resolver_type = resolver_map.get(resolver_type)

    # Adapt tokeninfo
    ti = {}
    if r["LinOtpTokenInfo"]:
        ti = json.loads(r["LinOtpTokenInfo"])

    ins = token_table.insert().values(
        id=r["LinOtpTokenId"],
        description=r["LinOtpTokenDesc"],
        serial=r["LinOtpTokenSerialnumber"],
        tokentype=type,
        user_pin=r['LinOtpTokenPinUser'],
        user_pin_iv=r['LinOtpTokenPinUserIV'],
        so_pin=r['LinOtpTokenPinSO'],
        so_pin_iv=r['LinOtpTokenPinSOIV'],
        resolver=resolver,
        resolver_type=resolver_type,
        user_id=r['LinOtpUserid'],
        pin_seed=r['LinOtpSeed'],
        key_enc=r['LinOtpKeyEnc'],
        key_iv=r['LinOtpKeyIV'],
        maxfail=r['LinOtpMaxFail'],
        active=r['LinOtpIsactive'],
        failcount=r['LinOtpFailCount'],
        count=r['LinOtpCount'],
        count_window=r['LinOtpCountWindow'],
        sync_window=r['LinOtpSyncWindow'])
    conn_pi.execute(ins)

    if ti:
        # Add tokeninfo for this token
        for k, v in ti.iteritems():
            ins = tokeninfo_table.insert().values(
                Key=k, Value=v, token_id=r["LinOtpTokenId"])
            conn_pi.execute(ins)
            print(" +--- adding tokeninfo {0!s}".format(k))

# Process Realms

s = select([linotp_realm_table])
result = conn_linotp.execute(s)
for r in result:
    print("migrating realm {0!s}".format(r["name"]))
    ins = realm_table.insert().values(
        id=r["id"],
        name=r["name"],
        default=r["default"],
        option=r["option"]
    )
    conn_pi.execute(ins)

# Process Tokenrealms

s = select([linotp_tokenrealm_table])
result = conn_linotp.execute(s)
for r in result:
    print("migrating tokenrealm {0!s}".format(r["id"]))
    ins = tokenrealm_table.insert().values(
        id=r["id"],
        token_id=r["token_id"],
        realm_id=r["realm_id"]
    )
    conn_pi.execute(ins)

# Process Resolvers

s = select([linotp_config_table])
result = conn_linotp.execute(s)
resolvers = {}
for r in result:
    config_key = r["Key"]
    # TODO: We need to supprt the other resolvers!
    entry = config_key.split(".")
    if entry[1] == "ldapresolver":
        name = entry[3]
        resolver_key = entry[2]
        value = r["Value"]
        desc = r["Description"]
        type = r["Type"]

        if name not in resolvers:
            resolvers[name] = {"type": "ldapresolver",
                               "config": [{"Key": "CACHE_TIMEOUT",
                                           "Value": "120"},
                                          {"Key": "SCOPE",
                                           "Value": "SUBTREE",
                                           "Type": "string"},
                                          {"Key": "EDITABLE",
                                           "Value": "0",
                                           "Type": "bool"}]}
        resolvers[name]["config"].append({
            "Key": resolver_key,
            "Value": value,
            "Description": desc,
            "Type": type
        })

if resolvers:
    # Write the resolvers
    for name, config in resolvers.iteritems():
        print("Migrating Resolver {0!s}".format(name))

        ins = resolver_table.insert().values(
                name=name,
                rtype=config.get("type")
        )
        res_id = conn_pi.execute(ins)
        resolver_id = res_id.inserted_primary_key[0]
        for resolver_entry in config.get("config"):
            # save the list of resolver configuration
            ins = resolver_config_table.insert().values(
                resolver_id=resolver_id,
                Key=resolver_entry.get("Key") or "",
                Value=resolver_entry.get("Value") or "",
                Type=resolver_entry.get("Type") or "",
                Description=resolver_entry.get("Description") or ""
            )
            conn_pi.execute(ins)


# Put resolvers into realms
s = select([linotp_config_table])
result = conn_linotp.execute(s)
realms = {}
for r in result:
    config_key = r["Key"]
    entry = config_key.split(".")
    if entry[1] == "useridresolver" and entry[2] == "group":
        resolvers = r["Value"].split()
        realms[entry[3]] = [x.split(".")[3] for x in resolvers]

print("Migrating realm definitions {0}".format(realms))

# Save the resolvers in the realms
"""For this we need to get the IDs of the realmname and the resolvernames"""
for realmname, resolvers in realms.iteritems():
    print("Migrating realm {0!s}".format(realmname))
    s = select([realm_table]).where(realm_table.c.name == realmname)
    result = conn_pi.execute(s)
    for r in result:
        realm_id = r["id"]

    for resolvername in resolvers:
        s = select([resolver_table]).where(resolver_table.c.name ==
                                           resolvername)
        result = conn_pi.execute(s)
        for r in result:
            resolver_id = r["id"]
        # insert each resolver_id for the realm_id
        ins = resolverrealm_table.insert().values(
            realm_id=realm_id,
            resolver_id=resolver_id
        )
        print(" +--- Adding resolver {0!s} to realm {1!s}".format(
            resolvername, realmname))
        conn_pi.execute(ins)

