#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  2018-05-27 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             init

__doc__ = """
This script helps you to migrate LinOTP to privacyIDEA.
You can use this script to export the counter values of the tokens
from a LinOTP database. You can then pass these values
to the script privacyidea-update-counter.py to update the counter
values of the tokens in the new privacyIDEA installation.
"""


import argparse
from sqlalchemy import create_engine
from sqlalchemy import Table, MetaData, Column
from sqlalchemy import Integer, Unicode, Boolean
from sqlalchemy.sql import select

metadata = MetaData()
linotp_token_table = Table('Token', metadata,
                           Column('LinOtpTokenId', Integer(), primary_key=True, nullable=False),
                           Column(
                               'LinOtpTokenDesc', Unicode(80), default=''),
                           Column('LinOtpTokenSerialnumber', Unicode(
                               40), default='', unique=True, nullable=False,
                                  index=True),
                           Column(
                               'LinOtpTokenType', Unicode(30), default='HMAC',
                               index=True),
                           Column(
                               'LinOtpTokenInfo', Unicode(2000), default=''),
                           Column(
                               'LinOtpTokenPinUser', Unicode(512), default=''),
                           Column(
                               'LinOtpTokenPinUserIV', Unicode(32),
                               default=''),
                           Column(
                               'LinOtpTokenPinSO', Unicode(512), default=''),
                           Column(
                               'LinOtpTokenPinSOIV', Unicode(32), default=''),
                           Column(
                               'LinOtpIdResolver', Unicode(120), default='',
                               index=True),
                           Column(
                               'LinOtpIdResClass', Unicode(120), default=''),
                           Column(
                               'LinOtpUserid', Unicode(320), default='',
                               index=True),
                           Column(
                               'LinOtpSeed', Unicode(32), default=''),
                           Column(
                               'LinOtpOtpLen', Integer(), default=6),
                           Column(
                               'LinOtpPinHash', Unicode(512), default=''),
                           Column(
                               'LinOtpKeyEnc', Unicode(1024), default=''),
                           Column(
                               'LinOtpKeyIV', Unicode(32), default=''),
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


def get_linotp_uri(config_file):
    with open(config_file) as f:
        content = f.readlines()

    lines = [l.strip() for l in content]
    sql_uri = ""
    for line in lines:
        if line.startswith("SQLALCHEMY_DATABASE_URI"):
            sql_uri = line.split("=", 1)[1].strip().strip("'").strip('"')
    return sql_uri


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--config",
                        help="LinOTP config file. We only need the SQLALCHEMY_DATABASE_URI.",
                        required=True)
    args = parser.parse_args()

    # Parse data

    SQL_URI = get_linotp_uri(args.config)

    # Start DB stuff

    linotp_engine = create_engine(SQL_URI)
    conn_linotp = linotp_engine.connect()

    s = select([linotp_token_table.c.LinOtpTokenSerialnumber, linotp_token_table.c.LinOtpCount])
    result = conn_linotp.execute(s)

    for r in result:
        print("{0!s}, {1!s}".format(r.LinOtpTokenSerialnumber, r.LinOtpCount))


if __name__ == '__main__':
    main()
