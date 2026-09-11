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
import logging

from sqlalchemy import select

from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType, AUTH_EVENT_TYPE_KEY,
                                                                          AuthEventReason, AUTH_EVENT_REASON_KEY)
from privacyidea.lib.container import find_container_for_token
from privacyidea.lib.crypto import hash_with_pepper, verify_with_pepper
from privacyidea.lib.error import AuthError, Error, TokenAdminError, UserError
from privacyidea.lib.log import log_with
from privacyidea.lib.policydecorators import libpolicy, login_mode
from privacyidea.lib.token import check_user_pass
from privacyidea.lib.utils import fetch_one_resource
from privacyidea.models import Admin, db

log = logging.getLogger(__name__)


class ROLE:
    ADMIN = "admin"
    USER = "user"
    VALIDATE = "validate"


@log_with(log, hide_args=[1])
def verify_db_admin(username: str, password: str) -> bool:
    """
    This function is used to verify the username and the password against the
    database table "Admin".
    :param username: The administrator username
    :param password: The password
    :return: True if password is correct for the admin
    """
    success = False
    stmt = select(Admin).filter_by(username=username)
    admin = db.session.scalars(stmt).first()
    if admin:
        success = verify_with_pepper(admin.password, password)

    return success


def db_admin_exists(username):
    """
    Checks if a local admin in the database exists

    :param username: The username of the admin
    :return: True, if exist
    """
    return bool(get_db_admin(username))


def create_db_admin(username, email=None, password=None):
    pw_dig = None
    if password:
        pw_dig = hash_with_pepper(password)

    stmt = select(Admin).filter_by(username=username)
    admin = db.session.execute(stmt).scalar_one_or_none()

    if admin:
        if email:
            admin.email = email
        if pw_dig:
            admin.password = pw_dig
    else:
        user = Admin(email=email, username=username, password=pw_dig)
        db.session.add(user)
    db.session.commit()


def get_all_db_admins() -> list[Admin]:
    return db.session.scalars(select(Admin)).all()


def get_db_admin(username: str) -> Admin:
    stmt = select(Admin).filter_by(username=username)
    return db.session.scalars(stmt).first()


def canonical_db_admin_login(username: str | None) -> str | None:
    """
    The spelling the ``admin`` table holds for the local database admin *username*, which is the name their
    authentication-log rows and their lock are keyed by.

    The lookup that authenticates them (:func:`~privacyidea.lib.auth.verify_db_admin`) compares in the database's
    own collation, so on a case-insensitive one - MySQL's default - ``Admin`` and ``admin`` are one account, while
    the log and the lock state both match case-sensitively. Recording the stored spelling is what keeps those one
    subject: without it a lock is walked around by varying the case, each spelling counting only its own failures.

    Only the account's own spelling is kept, not the one that was typed. This is called for a name that matched an
    account, where the account is the fact worth recording; an unknown login never reaches here. A name that no
    longer matches one (deleted mid-request) is returned unchanged, and so is anything a lookup failure prevents
    canonicalizing - recording the row matters more than recording it under the better name.

    :param username: the login as it was typed
    :return: the stored spelling, or *username* itself when there is no account to take one from
    """
    if not username:
        return username
    try:
        admin = get_db_admin(username)
    except Exception as ex:
        log.debug(f"Could not canonicalize the local admin login {username!r}: {ex!r}")
        return username
    return admin.username if admin else username


def delete_db_admin(username):
    print(f"Deleting admin {username!s}")
    admin = fetch_one_resource(Admin, username=username)
    db.session.delete(admin)
    db.session.commit()


@libpolicy(login_mode)
def check_webui_user(user, password, options=None, superuser_realms=None, check_otp=False):
    """
    This function is used to authenticate the user at the web ui.
    It checks against the userstore or against OTP/privacyidea (check_otp).
    It returns a tuple of

    * true/false if the user authenticated successfully
    * the role of the user
    * the "detail" dictionary of the response

    :param user: The user who tries to authenticate
    :type user: User Object
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
            check, details = check_user_pass(user, password, options=options)
            details["loginmode"] = "privacyIDEA"
            if check:
                user_auth = True
                if details.get("serial"):
                    try:
                        container = find_container_for_token(details.get("serial"))
                        if container:
                            container.update_last_authentication()
                    except Exception as e:
                        log.debug(f"Could not find container for token {details.get('serial')}: {e}")
        except Exception as e:
            log.debug(f"Error authenticating user against privacyIDEA: {e!r}")
            # check_user_pass raises for outcomes it cannot classify by return value alone: a locked/revoked token
            # (TOKEN_LOCKED) or an unknown user (the auth_user_does_not_exist decorator). The login fails either
            # way, but the authentication log must still record the real reason.
            details = details or {}
            if isinstance(e, TokenAdminError) and e.id == Error.TOKEN_LOCKED:
                details[AUTH_EVENT_TYPE_KEY] = AuthEventType.NO_USABLE_TOKEN
                # TOKEN_LOCKED is raised only for a revoked token, which check_token_list drops before any other check.
                details[AUTH_EVENT_REASON_KEY] = AuthEventReason.TOKEN_REVOKED
            elif isinstance(e, (UserError, AuthError)) and (not user or not user.exist()):
                details[AUTH_EVENT_TYPE_KEY] = AuthEventType.USER_UNKNOWN
    else:
        # check the password of the user against the user store
        details = {}
        if user.check_password(password):
            user_auth = True
            details[AUTH_EVENT_TYPE_KEY] = AuthEventType.LOGIN_SUCCESS
        else:
            # LOGINMODE=userstore: the credential checked here *is* the user store password, which PASSWORD_FAIL
            # already says - no reason of its own.
            details[AUTH_EVENT_TYPE_KEY] = AuthEventType.PASSWORD_FAIL

    # If the realm is in the SUPERUSER_REALM then the authorization role
    # is risen to "admin".
    if user.realm in superuser_realms:
        role = ROLE.ADMIN

    return user_auth, role, details
