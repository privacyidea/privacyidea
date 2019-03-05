#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  2018-07-27 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             init
from __future__ import print_function

__doc__ = """Read a file containing serials and base32 encoded secrets and converting it to hex."""

import argparse
import sys
import binascii
import base64


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('file', help='The CSV file with the base32 secrets.'
                                 'You can specify "-" to read from stdin.',
                    type=argparse.FileType())
parser.add_argument("-t", "--type", help="The token type (like TOTP)")
parser.add_argument("-d", "--digits", help="The number of digits")
parser.add_argument("-s", "--timestep", help="The timestep (like 30 or 60)")
args = parser.parse_args()

content = args.file.readlines()
for line in content:
    values = [x.strip() for x in line.split(",")]
    if len(values) < 2:
        # not enough data (serial and secret) to process
        continue

    serial = values[0]
    secret = values[1]
    try:
        secret = binascii.hexlify(base64.b32decode(secret))
    except (TypeError, binascii.Error):
        sys.stderr.write("Error converting secret of serial {0}.\n".format(serial))
        continue

    print("{0}, {1}".format(serial, secret.decode('utf8')), end='')

    if args.type:
        print(", {0}".format(args.type), end='')
    elif len(values) > 2:
        print(", {0}".format(values[2]), end='')

    if args.digits:
        print(", {0}".format(args.digits), end='')
    elif len(values) > 3:
        print(", {0}".format(values[3]), end='')

    if args.timestep:
        print(", {0}".format(args.timestep), end='')
    elif len(values) > 4:
        print(", {0}".format(values[4]), end='')

    print()
