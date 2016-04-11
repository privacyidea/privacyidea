# -*- coding: utf-8 -*-
#
#  2015-01-06 Cornelius Kölbel <cornelius@privacyidea.org>
#             The Password reset functions
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
#
from privacyidea.models import PasswordReset
from privacyidea.lib.crypto import hash_with_pepper, verify_with_pepper
import logging
from privacyidea.lib.log import log_with
from privacyidea.lib.error import UserError, privacyIDEAError, ConfigAdminError
from privacyidea.lib.smtpserver import send_email_identifier
from privacyidea.lib.utils import generate_password
from privacyidea.lib.config import get_from_config
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.policy import PolicyClass, ACTION, SCOPE
from sqlalchemy import and_
from datetime import datetime


__doc__ = """
This is the library for creating a recovery code for password reset.
The recovery code is sent to the user.

The salted/peppered hash of the recovery code is stored in the passwordreset
database table.

This module is tested in tests/test_lib_passwordreset.py
"""

log = logging.getLogger(__name__)

BODY = """Someone requested to reset the password within privacyIDEA.

To reset your user password please visit the link

%s/reset/%s@%s/%s
"""


@log_with(log)
def create_recoverycode(user, email=None, expiration_seconds=3600,
                        recoverycode=None, base_url=""):
    """
    Create and send a password recovery code

    :param user: User for whom the password reset code should be sent
    :type user: User Object
    :param email: The optional email of the user
    :param recoverycode: Only used for testing purpose
    :return: bool
    """
    base_url = base_url.strip("recover")
    base_url += "#"
    recoverycode = recoverycode or generate_password(size=24)
    hash_code = hash_with_pepper(recoverycode)
    # send this recoverycode
    #
    pwreset = PasswordReset(hash_code, username=user.login,
                            realm=user.realm,
                            expiration_seconds=expiration_seconds)
    pwreset.save()

    res = False
    if not user:
        raise UserError("User required for recovery token.")
    user_email = user.info.get("email")
    if email and email.lower() != user_email.lower():
        raise UserError("The email does not match the users email.")

    identifier = get_from_config("recovery.identifier")
    if identifier:
        # send email
        r = send_email_identifier(identifier, user_email,
                                  "Your password reset",
                                  BODY % (base_url,
                                          user.login, user.realm,
                                          recoverycode))
        if not r:
            raise privacyIDEAError("Failed to send email. {0!s}".format(r))
    else:
        raise ConfigAdminError("Missing configuration "
                               "recovery.identifier.")
    res = True
    return res


@log_with(log)
def check_recoverycode(user, recoverycode):
    """
    Check if the given recovery code is a valid recovery code for this user

    :param user: User, who wants to reset his password.
    :type user: User object
    :param recoverycode: The recovery code
    :type recoverycode: basestring
    :return: True is code was correct
    """
    recoverycode_valid = False
    # delete old entries
    r = PasswordReset.query.filter(and_(PasswordReset.expiration <
                                      datetime.now())).delete()
    log.debug("{0!s} old password recoverycodes deleted.".format(r))
    sql_query = PasswordReset.query.filter(and_(PasswordReset.username ==
                                            user.login,
                                                PasswordReset.realm
                                                == user.realm))
    for pwr in sql_query:
        if verify_with_pepper(pwr.recoverycode, recoverycode):
            recoverycode_valid = True
            log.debug("Found valid recoverycode for user {0!s}".format(user))
            # Delete the recovery code, so that it can only be used once!
            r = pwr.delete()
            log.debug("{0!s} used password recoverycode deleted.".format(r))

    return recoverycode_valid


@log_with(log)
def is_password_reset():
    """
    Check if password reset is allowed.

    We need to check, if a user policy with password_reset exists AND if an
    editable resolver exists. Otherwise password_reset does not make any sense.

    :return: True or False
    """
    rlist = get_resolver_list(editable=True)
    log.debug("Number of editable resolvers: {0!s}".format(len(rlist)))
    Policy = PolicyClass()
    policy_at_all = Policy.get_policies(scope=SCOPE.USER, active=True)
    log.debug("Policy at all: {0!s}".format(policy_at_all))
    policy_reset_pw = Policy.get_policies(scope=SCOPE.USER,
                                          action=ACTION.PASSWORDRESET)
    log.debug("Password reset policy: {0!s}".format(policy_reset_pw))
    pwreset = (policy_at_all and policy_reset_pw) or not policy_at_all
    log.debug("Password reset allowed via policy: {0!s}".format(pwreset))

    return bool(rlist and pwreset)
