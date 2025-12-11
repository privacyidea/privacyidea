# (c) NetKnights GmbH 2025,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2025 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import logging
from datetime import timedelta

from flask import g

from privacyidea.lib.policy import Match, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.user import User
from privacyidea.lib.utils import parse_timelimit, AUTH_RESPONSE

log = logging.getLogger(__name__)

DEFAULT_JWT_VALIDITY = 3600


def check_max_auth_fail(user: User, user_search_dict: dict, check_validate_check: bool = True):
    """
    Check if the maximum number of authentication failures is reached.
    This function is used to determine if the user should be blocked due to too many failed authentication attempts.
    """
    result = True
    reply_dict = {}
    max_fail_dict = Match.user(g, scope=SCOPE.AUTHZ, action=PolicyAction.AUTHMAXFAIL,
                               user_object=user).action_values(unique=True, write_to_audit_log=False)

    if len(max_fail_dict) != 1:
        return result, reply_dict

    policy_count, time_delta = parse_timelimit(list(max_fail_dict)[0])
    fail_count = 0
    if check_validate_check:
        # Local admins can not authenticate at validate/check, no need to search the audit log for it
        # at validate/check users and admins are not distinguished: always search for user
        search_dict = {"action": "%/validate/check", "authentication": f"!{AUTH_RESPONSE.CHALLENGE}",
                       "user": user.login, "realm": user_search_dict.get("realm", "%")}
        fail_count = g.audit_object.get_count(search_dict, success=False, timedelta=time_delta)
        log.debug(f"Checking users timelimit {list(max_fail_dict)[0]}: {fail_count} failed authentications with "
                  "/validate/check")
    search_dict = {"action": "%/auth"}
    search_dict.update(user_search_dict)
    fail_auth_count = g.audit_object.get_count(search_dict, success=False, timedelta=time_delta)
    log.debug(f"Checking users timelimit {list(max_fail_dict)[0]}: {fail_auth_count} failed authentications with "
              "/auth")
    fail_count += fail_auth_count
    if fail_count >= policy_count:
        result = False
        reply_dict["message"] = f"Only {policy_count} failed authentications per {time_delta} allowed."
        g.audit_object.add_policy(next(iter(max_fail_dict.values())))

    return result, reply_dict


def check_max_auth_success(user: User, user_search_dict: dict, check_validate_check: bool = True):
    """
    Check if the maximum number of successful authentication is reached.
    This function is used to determine if the user should be blocked due to too many successful authentication attempts.
    """
    result = True
    reply_dict = {}
    # Get policies
    max_success_dict = Match.user(g, scope=SCOPE.AUTHZ, action=PolicyAction.AUTHMAXSUCCESS,
                                  user_object=user).action_values(unique=True, write_to_audit_log=False)

    if len(max_success_dict) != 1:
        return result, reply_dict

    # Check for maximum successful authentications
    policy_count, time_delta = parse_timelimit(list(max_success_dict)[0])
    # Check the successful authentications for this user
    success_count = 0
    if check_validate_check:
        search_dict = {"action": "%/validate/check"}
        search_dict.update(user_search_dict)
        success_count = g.audit_object.get_count(search_dict, success=True, timedelta=time_delta)
        log.debug(f"Checking users timelimit {list(max_success_dict)[0]}: {success_count} successful "
                  "authentications with /validate/check")
    search_dict = {"action": "%/auth"}
    search_dict.update(user_search_dict)
    success_auth_count = g.audit_object.get_count(search_dict,
                                                  success=True, timedelta=time_delta)
    log.debug(f"Checking users timelimit {list(max_success_dict)[0]}: {success_auth_count} successful "
              "authentications with /auth")
    success_count += success_auth_count
    if success_count >= policy_count:
        result = False
        reply_dict["message"] = f"Only {policy_count} successful authentications per {time_delta} allowed."

    return result, reply_dict


def get_jwt_validity(user: User) -> timedelta:
    """
    Reads the JWT validity for the auth token from the policy or returns the default time of 1 hour if no policy is set.

    :param user: The user for whom the JWT validity is checked.
    :return: A timedelta object representing the JWT validity period.
    """
    validity_policy = (Match.user(g, scope=SCOPE.WEBUI, action=PolicyAction.JWTVALIDITY,
                                  user_object=user).action_values(unique=True))

    validity_time = DEFAULT_JWT_VALIDITY
    if len(validity_policy) == 1:
        try:
            validity_time = int(list(validity_policy)[0])
        except ValueError:
            log.warning(
                f"Invalid JWT validity period: {list(validity_policy)[0]}. Using the default of {validity_time} s.")

    validity_time = timedelta(seconds=int(validity_time))
    return validity_time

def get_admin_audit_params() -> dict:
    """
    Checks if a policy is set, which limits the audit log access for admins to certain realms.
    If such a policy is set, the admin's username, realm and the allowed realms are returned in a dictionary. Otherwise,
    an empty dictionary is returned. For admins, it should still be possible to see their own audit log entries, which
    is why the admin's username and realm are also returned.

    :return: A dictionary with the keys "admin", "admin_realm" and "allowed_audit_realms" or an empty dictionary.
    """
    from privacyidea.lib.auth import ROLE
    admin_params = {}
    if g.logged_in_user["role"] == ROLE.ADMIN:
        pols = Match.admin(g, action=PolicyAction.AUDIT).policies()
        if pols:
            # get all values in realm:
            allowed_audit_realms = []
            for pol in pols:
                if pol.get("realm"):
                    allowed_audit_realms += pol.get("realm")
            if allowed_audit_realms:
                admin_params["admin"] = g.logged_in_user["username"]
                admin_params["admin_realm"] = g.logged_in_user["realm"]
                admin_params["allowed_audit_realms"] = list(set(allowed_audit_realms))
    return admin_params
