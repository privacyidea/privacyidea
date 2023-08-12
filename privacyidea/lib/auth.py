# -*- coding: utf-8 -*-
#
# 2015-11-03 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add check if an admin user exists
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
from privacyidea.lib.token import check_user_pass
from privacyidea.lib.policydecorators import libpolicy, login_mode
from privacyidea.lib.crypto import hash_with_pepper, verify_with_pepper
from privacyidea.lib.utils import fetch_one_resource
import logging

log = logging.getLogger(__name__)



class ROLE(object):
    ADMIN = "admin"
    USER = "user"
    VALIDATE = "validate"


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
        success = verify_with_pepper(qa.password, password)

    return success


def db_admin_exist(username):
    """
    Checks if a local admin in the database exists

    :param username: The username of the admin
    :return: True, if exist
    """
    return bool(get_db_admin(username))


def create_db_admin(app, username, email=None, password=None):
    pw_dig = None
    if password:
        pw_dig = hash_with_pepper(password)
    user = Admin(email=email, username=username, password=pw_dig)
    user.save()


def list_db_admin():
    admins = Admin.query.all()
    print("Name \t email")
    print(30*"=")
    for admin in admins:
        print("{0!s} \t {1!s}".format(admin.username, admin.email))


def get_db_admins():
    admins = Admin.query.all()
    return admins


def get_db_admin(username):
    return Admin.query.filter(Admin.username == username).first()


def delete_db_admin(username):
    print("Deleting admin {0!s}".format(username))
    fetch_one_resource(Admin, username=username).delete()


@libpolicy(login_mode)
def check_webui_user(user_obj,
                     password,
                     options=None,
                     superuser_realms=None,
                     check_otp=False):
    """
    This function is used to authenticate the user at the web ui.
    It checks against the userstore or against OTP/privacyidea (check_otp).
    It returns a tuple of

    * true/false if the user authenticated successfully
    * the role of the user
    * the "detail" dictionary of the response

    :param user_obj: The user who tries to authenticate
    :type user_obj: User Object
    :param password: Password, static and or OTP
    :param options: additional options like g and clientip
    :type options: dict
    :param superuser_realms: list of realms, that contain admins
    :type superuser_realms: list
    :param check_otp: If set, the user is not authenticated against the
         userstore but against privacyidea
    :return: tuple of bool, string and dict/None
    """
    options = options or {}
    superuser_realms = superuser_realms or []
    user_auth = False
    role = ROLE.USER
    details = None

    if check_otp:
        # check if the given password matches an OTP token
        try:
            check, details = check_user_pass(user_obj, password, options=options)
            details["loginmode"] = "privacyIDEA"
            if check:
                user_auth = True
        except Exception as e:
            log.debug("Error authenticating user against privacyIDEA: {0!r}".format(e))
    else:
        # check the password of the user against the userstore
        if user_obj.check_password(password):
            user_auth = True

    # If the realm is in the SUPERUSER_REALM then the authorization role
    # is risen to "admin".
    if user_obj.realm in superuser_realms:
        role = ROLE.ADMIN

    return user_auth, role, details
