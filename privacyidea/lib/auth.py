# -*- coding: utf-8 -*-
#
# 2014-12-15 Cornelius Kölbel, info@privacyidea.org
#            Initial creation
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
from privacyidea.models import Admin
import passlib.hash
from flask import current_app

def verify_db_admin(username, password):
    """
    This function is used to verify the username and the password against the
    database table "Admin".
    :param username: The administrator username
    :param password: The password
    :return: True if password is correct for the admin
    :rtype: bool
    """
    success = False
    qa = Admin.query.filter(Admin.username == username).first()
    if qa:
        pw_dig = qa.password
        # get the password pepper
        key = current_app.config.get("PI_PEPPER", "missing")
        success = passlib.hash.pbkdf2_sha512.verify(key + password, pw_dig)

    return success


def create_db_admin(app, username, email=None, password=None):
    if password:
        key = app.config.get("PI_PEPPER", "missing")
        pw_dig = passlib.hash.pbkdf2_sha512.encrypt(key + password,
                                                    rounds=10023,
                                                    salt_size=10)
    else:
        pw_dig = None
    user = Admin(email=email, username=username, password=pw_dig)
    user.save()


def list_db_admin():
    admins = Admin.query.all()
    print "Name \t email"
    print 30*"="
    for admin in admins:
        print "%s \t %s" % (admin.username, admin.email)


def delete_db_admin(username):
    print "Deleting admin %s" % username
    Admin.query.filter(Admin.username == username).first().delete()
