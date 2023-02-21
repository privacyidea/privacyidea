#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  2018-05-27 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             init

__doc__ = """
This script exports counter from privacyIDEA to a csv file.
It exports 
   serial, counter

"""
from sqlalchemy.sql import select
from privacyidea.models import Token
import argparse
from sqlalchemy import create_engine


def get_privacyidea_uri(config_file):
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
    parser.add_argument("-c", "--config", help="privacyIDEA config file. We only "
                                               "need the SQLALCHEMY_DATABASE_URI.",
                        required=True)
    args = parser.parse_args()

    # Parse data

    SQL_URI = get_privacyidea_uri(args.config)

    # Start DB stuff

    pi_engine = create_engine(SQL_URI)
    conn_pi = pi_engine.connect()

    s = select([Token.serial, Token.count])
    result = pi_engine.execute(s)

    for r in result:
        print("{0!s}, {1!s}".format(r.serial, r.count))


if __name__ == '__main__':
    main()
