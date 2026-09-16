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
from typing import TYPE_CHECKING

from flask import g, request

from privacyidea.lib.policy import Match, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.user import User
from privacyidea.lib.utils import parse_timelimit, AUTH_RESPONSE

if TYPE_CHECKING:
    from privacyidea.lib.conditional_access.authentication_log import AuthenticationLogVisibilityScope

log = logging.getLogger(__name__)

DEFAULT_JWT_VALIDITY = 3600


def check_max_auth_fail(user: User, user_search_dict: dict, check_validate_check: bool = True):
    """
    Check if the maximum number of authentication failures is reached.
    This function is used to determine if the user should be blocked due to too many failed authentication attempts.

    *reply_dict* is handed to the client as the error details, so it carries nothing but the message: the caller
    classifies the refusal for the authentication log itself (``AuthEventReason.AUTH_MAX_FAIL``), which it can,
    since it knows which of the two checks said no. That is this pair's answer to the classification travelling in a
    client-facing dict elsewhere (see :data:`~privacyidea.lib.conditional_access.authentication_event_types
    .AUTH_EVENT_TYPE_KEY`, where the response boundary strips it), not a rule the rest of the policy helpers
    follow yet. """
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
        search_dict = {"action": "*/validate/check", "authentication": f"!{AUTH_RESPONSE.CHALLENGE}",
                       "user": user.login, "realm": user_search_dict.get("realm", "*")}
        fail_count = g.audit_object.get_count(search_dict, success=False, timedelta=time_delta)
        log.debug(f"Checking users timelimit {list(max_fail_dict)[0]}: {fail_count} failed authentications with "
                  "/validate/check")
    # Exclude challenge-trigger entries from the count, as for */validate/check above.
    search_dict = {"action": "*/auth", "authentication": f"!{AUTH_RESPONSE.CHALLENGE}"}
    search_dict.update(user_search_dict)
    fail_auth_count = g.audit_object.get_count(search_dict, success=False, timedelta=time_delta)
    log.debug(f"Checking users timelimit {list(max_fail_dict)[0]}: {fail_auth_count} failed authentications with "
              "/auth")
    fail_count += fail_auth_count
    if fail_count >= policy_count:
        result = False
        deciding_policies = next(iter(max_fail_dict.values()))
        reply_dict["message"] = f"Only {policy_count} failed authentications per {time_delta} allowed."
        g.audit_object.add_policy(deciding_policies)

    return result, reply_dict


def check_max_auth_success(user: User, user_search_dict: dict, check_validate_check: bool = True):
    """
    Check if the maximum number of successful authentication is reached.
    This function is used to determine if the user should be blocked due to too many successful authentication attempts.

    Like :func:`check_max_auth_fail`, *reply_dict* holds only the client-facing message; the caller classifies the
    refusal as ``AuthEventReason.AUTH_MAX_SUCCESS``.
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
        search_dict = {"action": "*/validate/check"}
        search_dict.update(user_search_dict)
        success_count = g.audit_object.get_count(search_dict, success=True, timedelta=time_delta)
        log.debug(f"Checking users timelimit {list(max_success_dict)[0]}: {success_count} successful "
                  "authentications with /validate/check")
    search_dict = {"action": "*/auth"}
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


def own_entries_scope(login: str, realm: str) -> "AuthenticationLogVisibilityScope | None":
    """
    Build the visibility scope for one principal's *own* records, bound to the resolver-stable identity
    ``(resolver, uid, realm)`` rather than to the login name.

    A login is not an identity: it can be renamed, and a freed one can be handed to a different account, which would
    then read the previous account's authentication history. The identity is what the log records the subject as and
    what the engine counts it by, so it is what this boundary matches on - a rename keeps the history, a reused login
    inherits none.

    ``None`` is returned if *login* does not resolve to an account in *realm* (no such account, an unreachable
    resolver). Callers must fail closed on that rather than fall back to the login name: records that name no account
    cannot be attributed to one.

    :param login: the principal's login name
    :param realm: the realm the principal is logged in to
    :return: a scope matching exactly that account's records, or ``None`` if it does not resolve
    """
    from privacyidea.lib.conditional_access.authentication_log import AuthenticationLogVisibilityScope
    if not (login and realm):
        return None
    user = getattr(request, "User", None)
    # before_request resolves a user-role caller's own account already (resolve_logged_in_user), so reusing it saves
    # a second resolver lookup; login and realm are compared because request.User otherwise carries a subject taken
    # from the request parameters.
    if not (user and user.login == login and user.realm == realm.lower()):
        try:
            user = User(login=login, realm=realm)
        except Exception as ex:
            # A resolver failure leaves the identity unknown; fail closed rather than falling back to login matching.
            log.warning(f"Could not resolve {login}@{realm} for the visibility scope: {ex!r}")
            return None
    if user and user.resolver and user.uid:
        return AuthenticationLogVisibilityScope(realms=[user.realm], resolvers=[user.resolver], usernames=[],
                                                uids=[str(user.uid)])
    log.info(f"{login}@{realm} resolves to no account, so no record is attributed to it.")
    return None


def get_policy_visibility_scopes(action: str) -> list["AuthenticationLogVisibilityScope"] | None:
    """
    Determine the visibility boundary for *action*: which records the logged-in principal may act on, expressed as
    realm / resolver / user scopes. Used to constrain list/read endpoints — the authentication log
    (``authentication_log_read``), the conditional-access lock state (``user_lock_read``), etc. — to only the
    entries a scoped admin is allowed to see.

    A **user** may only ever act on their own entries, so a single scope built from the logged-in user's identity is
    returned (never ``None``) -- or an empty list, matching nothing, if that identity does not resolve (see
    :func:`own_entries_scope`).

    Any **other** role acts on nothing: an empty list, which every consumer reads as a boundary that admits no
    record (:func:`~privacyidea.lib.conditional_access.authentication_log.visibility_condition` returns
    ``false()`` for it). Unreachable today - every endpoint that asks is behind ``@user_required``, so only the
    two roles above get this far - but the default of a function whose job is to restrict has to be "nothing",
    not "everything", or a role added later silently arrives unscoped. ``None`` cannot express it: that is the
    unrestricted answer an unscoped admin policy legitimately produces.

    For an **admin** the scopes are derived from the target scoping (realm, resolver, user) of that action's
    policies: one scope per scoping policy, combined OR across policies and AND across the dimensions a single policy
    sets. ``None`` (no restriction) is returned if no policy of this action is scoped, or if any applicable policy
    has no target scope at all (such a policy grants access to all entries). adminrealm, adminuser and policy
    conditions need no handling here: ``Match.admin(...).policies()`` already returns only the policies applicable to
    the current admin and request.

    :param action: the policy action whose scoping to read (e.g. ``authentication_log_read``, ``user_lock_read``)
    :return: a list of :class:`AuthenticationLogVisibilityScope` (an empty one admitting no record), or ``None``
        for unrestricted access
    """
    from privacyidea.lib.auth import ROLE
    from privacyidea.lib.conditional_access.authentication_log import AuthenticationLogVisibilityScope
    if g.logged_in_user["role"] == ROLE.USER:
        own_scope = own_entries_scope(g.logged_in_user["username"], g.logged_in_user["realm"])
        return [own_scope] if own_scope else []
    if g.logged_in_user["role"] != ROLE.ADMIN:
        # Logged and not raised: an unexpected role here is a misconfiguration to notice, not a reason to answer
        # 500 to a read that "no records" answers correctly and safely.
        log.warning(f"No visibility boundary is defined for role {g.logged_in_user['role']!r}; "
                    f"restricting {action} to no records.")
        return []
    scopes = []
    for policy in Match.admin(g, action=action).policies():
        realms = policy.get("realm") or []
        resolvers = policy.get("resolver") or []
        usernames = policy.get("user") or []
        if not (realms or resolvers or usernames):
            # An applicable policy with no target scope grants access to all entries.
            return None
        scopes.append(AuthenticationLogVisibilityScope(
            realms=realms, resolvers=resolvers, usernames=usernames,
            username_case_insensitive=bool(policy.get("user_case_insensitive"))))
    return scopes or None
