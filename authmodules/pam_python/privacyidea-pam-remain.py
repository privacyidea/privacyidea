#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# 2015-04-08 Cornelius Kölbel  <cornelius.koelbel@netknights.it>
#            Initial writeup
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__doc__ = """This script is used to display the remaining OTP hashes.
"""

import sqlite3
import getpass

SQLFILE = "/etc/privacyidea/pam.sqlite"


def check_remain(user, sqlfile):
    """
    Check the remaining OTP values for the given user.

    :param user: The local user in the sql file
    :param sqlfile: The sqlite file
    :return: dict of OTP counts
    """
    remains = {}
    conn = sqlite3.connect(sqlfile)
    c = conn.cursor()
    # get all possible serial/tokens for a user
    serials = []
    for row in c.execute("SELECT serial, user FROM authitems WHERE user='%s'"
                         "GROUP by serial" % user):
        serials.append(row[0])

    for serial in serials:
        r = c.execute("select count(*) from authitems where serial = '%s'" %
                      serial)
        remains[serial] = r.fetchone()[0]

    conn.close()
    return remains


def main():
    username = getpass.getuser()
    remains = check_remain(username, SQLFILE)

    print("Remaining OTP hashes:")
    print("=====================")
    for k, v in remains.iteritems():
        print("%s: %s" % (k, v))


if __name__ == '__main__':
    main()
