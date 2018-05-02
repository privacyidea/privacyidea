#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  2018-02-09 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Speedup thanks to Friedrich Weber.
#             Add flexible resolver mapping
#  2016-09-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
"""
You can use this script to migrate a LinOTP database to privacyIDEA.
All tokens and token assignments are transferred to privacyIDEA.

You only need an export of the LinOTP "Token" table.
Please configure below, how your database URIs look like,
what should be migrated and what should be mapped.
"""
# ========================================================
# You need to change the following values:
#  1. set the database URIs for LinOTP and privacyIDEA
#  2. configure, what you want to migrate in the
#     MIGRATE dictionary
#  3. Set the ASSIGNMENTS dictionary, to define, which
#     realms you want to have the tokens in.
# =========================================================
LINOTP_URI = "mysql://linotp2:linotp2@localhost/linotp2"
PRIVACYIDEA_URI = "mysql://pitest:pitest@localhost/pitest"

"""
Define, what should be migrated:

"tokens" should always be True.
If "assignments" is False, the imported tokens will be unassigned!

"""
MIGRATE = {"tokens": True,
           "tokeninfo": True,
           "assignments": True}

"""
This assigns the token to the new resolver

The "resolver" key maps LinOTP-resolvers to privacyIDEA-Resolvers. This value is
rewritten in the token tabel.

The "realm" key puts tokens in the privacyIDEA-Resolver into this privacyIDEA realm.

In this example the resolvername "lokal" from LinOTP gets imported to
privacyIDEA with the resolver "PIResolver" in realm "pirealm".

Tokens, that were not assigned to a user will be assigned to the realms "realm1" and "realm2"
in privacyIDEA.
"""
ASSIGNMENTS = {
    "resolver": {"lokal": "PIResolver"},
    "realm": {"PIResolver": "pirealm"},
    "unassigned_tokens": ["realm1", "realm2"]
}

"""
This option splits INSERT statements into chunks of a given size, which is useful
if the number of migrated tokens is so large that it cannot fit in one INSERT
statement.
"""
INSERT_CHUNK_SIZE = 10000

# Do not change anything after this line
# ============================================================================
#
from sqlalchemy import Table, MetaData, Column
from sqlalchemy import Integer, Unicode, Boolean, UnicodeText
import sys
import getopt


def migrate():

    # This maps the resolver types. You must not change this!
    resolver_map = {"LDAPIdResolver": "ldapresolver",
                    "SQLIdResolver": "sqlresolver",
                    "PasswdIdResolver": "passwdresolver"}

    token_serial_id_map = {}
    realm_id_map = {}
    resolver_id_map = {}

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

    def insert_chunks(conn, table, values, chunk_size=INSERT_CHUNK_SIZE):
        """
        Split **values** into chunks of size **chunk_size** and insert them sequentially.
        """
        values_length = len(values)
        for i in xrange(0, values_length, chunk_size):
            print 'Insert records {} to {} ...'.format(i, min(i + chunk_size, values_length) - 1)
            conn.execute(table.insert(), values[i:i+chunk_size])


    # Values to be imported
    token_values = []
    tokeninfo_values = []
    tokenrealm_values = []

    warnings = []

    # Process Assignments in table "tokenrealm"
    if MIGRATE.get("assignments"):
        s = select([realm_table])
        result = conn_pi.execute(s)
        for r in result:
            realm_id_map[r["name"]] = r["id"]

        s = select([resolver_table])
        result = conn_pi.execute(s)
        for r in result:
            resolver_id_map[r["name"]] = r["id"]

        print("Realm-Map: {}".format(realm_id_map))
        print("Resolver-Map: {}".format(resolver_id_map))

    # Process Tokens

    if MIGRATE.get("tokens"):
        s = select([linotp_token_table])
        result = conn_linotp.execute(s)

        i = 0
        for r in result:
            i = i + 1
            print("processing token #{1!s}: {0!s}".format(r["LinOtpTokenSerialnumber"], i))
            # Adapt type
            type = r["LinOtpTokenType"]
            if type.lower() == "hmac":
                type = "HOTP"
            # Adapt resolver
            linotp_resolver = r["LinOtpIdResClass"].split(".")[-1]

            # Adapt resolver type
            resolver_type = ""
            if r["LinOtpIdResClass"]:
                resolver_type = r['LinOtpIdResClass'].split(".")[1]
                resolver_type = resolver_map.get(resolver_type)

            # Adapt tokeninfo
            ti = {}
            if r["LinOtpTokenInfo"]:
                ti = json.loads(r["LinOtpTokenInfo"])

            if MIGRATE.get("assignments"):
                user_pin = r['LinOtpTokenPinUser']
                user_pin_iv = r['LinOtpTokenPinUserIV']
                # Map the LinOTP-Resolver to the PI-Resolver
                resolver = ASSIGNMENTS.get("resolver").get(linotp_resolver)
                if not resolver and linotp_resolver:
                    warnings.append(u"No mapping defined for the LinOTP resolver: {0!s}".format(linotp_resolver))
                resolver_type = resolver_type
                user_id = r['LinOtpUserid']
            else:
                user_pin = None
                user_pin_iv = None
                resolver = None
                resolver_type = None
                user_id = None

            token_values.append(dict(
                description=r["LinOtpTokenDesc"],
                serial=r["LinOtpTokenSerialnumber"],
                tokentype=type,
                user_pin=user_pin,
                user_pin_iv=user_pin_iv,
                so_pin=r['LinOtpTokenPinSO'],
                so_pin_iv=r['LinOtpTokenPinSOIV'],
                resolver=resolver,
                resolver_type=resolver_type,
                user_id=user_id,
                pin_seed=r['LinOtpSeed'],
                pin_hash=r['LinOtpPinHash'],
                key_enc=r['LinOtpKeyEnc'],
                key_iv=r['LinOtpKeyIV'],
                maxfail=r['LinOtpMaxFail'],
                active=r['LinOtpIsactive'],
                failcount=r['LinOtpFailCount'],
                count=r['LinOtpCount'],
                count_window=r['LinOtpCountWindow'],
                sync_window=r['LinOtpSyncWindow']))

            if MIGRATE.get("tokeninfo") and ti:
                # Add tokeninfo for this token
                for k, v in ti.iteritems():
                    tokeninfo_values.append(dict(
                        serial=r["LinOtpTokenSerialnumber"],
                        Key=k, Value=v,
                        token_id=r["LinOtpTokenId"]))
                    print(" +--- processing tokeninfo {0!s}".format(k))

        print
        print("Adding {} tokens...".format(len(token_values)))
        insert_chunks(conn_pi, token_table, token_values)

        # fetch the new token_id's in privacyIDEA and write them to the
        # token serial id map.
        s = select([token_table])
        result = conn_pi.execute(s)
        for r in result:
            token_serial_id_map[r["serial"]] = r["id"]

        # rewrite the id's in the token_values list
        for i in range(0, len(token_values)):
            token_values[i]["id"] = token_serial_id_map[token_values[i]["serial"]]

        if MIGRATE.get("tokeninfo"):
            # Now we have to rewrite the token_id in the tokeninfo_values
            for ti in tokeninfo_values:
                ti["token_id"] = token_serial_id_map[ti["serial"]]
                del ti["serial"]

            print("Adding {} token infos...".format(len(tokeninfo_values)))
            insert_chunks(conn_pi, tokeninfo_table, tokeninfo_values)

    if MIGRATE.get("assignments"):
        # If the token is assigned, we also need to create an entry for tokenrealm
        # We need to determine the realm_id for this resolver!
        for token in token_values:
            token_id = token.get("id")
            resolver = token.get("resolver")
            if resolver:
                realm = ASSIGNMENTS.get("realm").get(resolver)
                realm_id = realm_id_map.get(realm)
                print("Assigning token {} for resolver {} to realm_id {} (realm {})".format(token_id,
                                                                                            resolver,
                                                                                            realm_id,
                                                                                            realm))
                tokenrealm_values.append(dict(token_id=token_id,
                                              realm_id=realm_id))
            else:
                # The token has no resolver and thus is not assigned
                for tokenrealm in ASSIGNMENTS.get("unassigned_tokens", []):
                    realm_id = realm_id_map.get(tokenrealm)
                    if realm_id:
                        tokenrealm_values.append(dict(token_id=token_id,
                                                      realm_id=realm_id))

        print("Adding {} tokenrealms...".format(len(tokenrealm_values)))
        insert_chunks(conn_pi, tokenrealm_table, tokenrealm_values)

    if warnings:
        print("We need to inform you about the following WARNINGS:")
        for warning in warnings:
            print(warning)


def usage():
    print("You need to configure some mapping within the script and then pass the parameter '-c'.")


try:
    opts, args = getopt.getopt(sys.argv[1:], "c", ["configured"])
except getopt.GetoptError as e:
    print(str(e))
    sys.exit(1)

for o, a in opts:
    if o in ("-c", "--configured"):
        migrate()
        sys.exit(0)

usage()
sys.exit(1)
