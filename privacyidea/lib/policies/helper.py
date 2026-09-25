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
from collections.abc import Callable, Iterable
from datetime import timedelta
from typing import TYPE_CHECKING

from flask import g, request

from privacyidea.lib.policy import Match, SCOPE
from privacyidea.lib.error import ResolverError, UserError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_list
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
            allowed_audit_realms = {}
            restricted_to_realms = False
            for pol in pols:
                if pol.get("resolver") or pol.get("user"):
                    # The audit log is only restricted by realm and can not show just these users or resolvers,
                    # so such a policy grants no realm - rather than every entry of its realms.
                    restricted_to_realms = True
                    continue
                realm_names = policy_realm_names(pol.get("realm"))
                if realm_names is None:
                    # A policy with no target scope at all grants every realm, whatever the others name.
                    return {}
                restricted_to_realms = True
                allowed_audit_realms.update(dict.fromkeys(realm_names))
            if restricted_to_realms:
                admin_params["admin"] = g.logged_in_user["username"]
                admin_params["admin_realm"] = g.logged_in_user["realm"]
                # Empty if no policy's realm field matches a realm: then only the admin's own entries are shown.
                admin_params["allowed_audit_realms"] = list(allowed_audit_realms)
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


def admin_granted_realms(action: str) -> list[str] | None:
    """
    The realms the logged-in admin's policies grant for *action*, as the union over every applicable policy.

    The realm-only counterpart of :func:`get_policy_visibility_scopes`, for the callers that need to answer
    "may this admin act in realm X" rather than build a query condition. Three answers, and they are not
    interchangeable:

    * ``None`` - unrestricted, which means one of two things: the installation defines no active admin
      policy at all, or an applicable policy carries no target scope whatsoever. Only the second is
      "this policy grants every realm"; the first is "nothing is restricted here yet".
    * a non-empty list - restricted to exactly these realms, deduplicated in the order the policies name
      them, because a caller that has to reduce them to a single realm picks the first.
    * an **empty list - restricted, but not to anything this function can name.** No applicable policy
      names a realm: each is scoped by ``user`` or ``resolver`` only, so the admin is restricted while the
      restriction has no realm to express it with. **Every caller must refuse.** Reading this as
      unrestricted is precisely the defect this function was written with: a policy granting
      ``remembered_device_revoke`` for one named user matched a request that named no user at all - a
      dimension whose search value is ``None`` is skipped by ``list_policies`` - and the caller then
      revoked every user's devices in every realm. A caller that needs the user and resolver dimensions
      rather than just a yes/no should use :func:`get_policy_visibility_scopes`, which carries all three.

    The realm field is read with :func:`policy_realm_names`, the way the policy engine matches it.

    adminrealm, adminuser and policy conditions need no handling here: ``Match.admin(...).policies()``
    already returns only the policies applicable to the current admin and request.

    :param action: the policy action whose realm scoping to read
    :return: the granted realm names, ``None`` for unrestricted, or an empty list for "refuse"
    """
    if not g.policy_object.list_policies(scope=SCOPE.ADMIN, active=True):
        # No admin policy anywhere: nothing is restricted, which is not the same as a policy granting
        # everything, but has the same answer here.
        return None
    granted_realms = {}
    for policy in Match.admin(g, action=action).policies():
        realm_names = policy_realm_names(policy.get("realm"))
        if realm_names is None:
            if policy.get("resolver") or policy.get("user"):
                # Scoped along a dimension a realm list cannot carry, so it contributes no realm. If no
                # other policy names one either, the empty result refuses rather than widening to every realm.
                continue
            return None
        granted_realms.update(dict.fromkeys(realm_names))
    return list(granted_realms)


def policy_realm_names(policy_realms: list[str] | None) -> list[str] | None:
    """
    The realms a policy's realm field matches, read the way the policy engine matches it.

    ``"*"`` stands for every realm, and a realm written with a leading ``"!"`` or ``"-"`` is excluded, also from
    ``"*"``. Every caller that turns policies into a boundary of realms reads the field with this function: taken
    literally, ``"*"`` and ``"!realm"`` are looked up as the names of realms, match none, and a grant over every
    realm, or over every realm but one, turns into a boundary that admits nothing.

    :param policy_realms: the realm field of a policy
    :return: ``None`` if the field restricts nothing - it is empty, or ``"*"`` without an exclusion. Otherwise the
        realm names it matches: ``"*"`` with exclusions yields every existing realm but the excluded ones, and an
        excluded realm is never among them. An **empty list** is a field that matches no realm at all - nothing but
        exclusions, or every realm excluded - and every caller must read it as granting nothing.
    """
    return _policy_field_names(policy_realms, get_realms)


def _policy_field_names(policy_values: list[str] | None,
                        existing_names: Callable[[], Iterable[str]]) -> list[str] | None:
    """
    The names a realm or resolver field of a policy matches, see :func:`policy_realm_names`. *existing_names* lists
    every realm or resolver there is, which ``"*"`` with exclusions is resolved against.
    """
    policy_values = policy_values or []
    excluded_names = {value[1:] for value in policy_values if value[:1] in ("!", "-")}
    if not policy_values or "*" in policy_values:
        if not excluded_names:
            return None
        return [name for name in existing_names() if name not in excluded_names]
    return [value for value in dict.fromkeys(policy_values)
            if value[:1] not in ("!", "-") and value not in excluded_names]


def _policy_usernames(policy_users: list[str] | None, case_insensitive: bool) -> tuple[list[str], list[str]] | None:
    """
    The users the user field of a policy matches, read the way the policy engine matches it, as a pair of the names
    and the excluded names. The users can not be listed like realms, so ``"*"`` with exclusions yields no names and
    the excluded ones: every user but these. Both are empty if the field restricts nothing, and the result is None if
    it matches no user at all - nothing but exclusions. With *case_insensitive* an exclusion also removes a name
    that differs only in case, as the policy engine compares them then.
    """
    policy_users = policy_users or []

    def fold(name: str) -> str:
        return name.lower() if case_insensitive else name

    excluded_users = list(dict.fromkeys(user[1:] for user in policy_users if user[:1] in ("!", "-")))
    if not policy_users or "*" in policy_users:
        return [], excluded_users
    excluded_folded = {fold(user) for user in excluded_users}
    named_users = [user for user in dict.fromkeys(policy_users)
                   if user[:1] not in ("!", "-") and fold(user) not in excluded_folded]
    return (named_users, []) if named_users else None


def _accounts_of(logins: list[str], realms: list[str]) -> list[tuple[str, str]]:
    """
    The accounts, as ``(resolver, uid)``, that these logins resolve to in these realms. A login that does not resolve
    in a realm has no account there.

    :raises ResolverError, UserError: if a user store can not be read
    """
    accounts = {}
    for realm in realms:
        for login in logins:
            user = User(login, realm)
            if user.exist():
                accounts[(user.resolver, user.uid)] = None
    return list(accounts)


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
    policies = Match.admin(g, action=action).policies()
    for policy in policies:
        # Every dimension is read the way the policy engine matches it: "*" is every value, and "!name" leaves
        # the name out, also of "*". Taken literally, both would be looked up as names, match none, and turn a
        # grant over everything, or over everything but one, into a boundary that admits nothing. Realms and
        # resolvers are listed out; users can not be, so every user but some is carried as excluded usernames.
        case_insensitive = bool(policy.get("user_case_insensitive"))
        realms = policy_realm_names(policy.get("realm"))
        resolvers = _policy_field_names(policy.get("resolver"), get_resolver_list)
        users = _policy_usernames(policy.get("user"), case_insensitive)
        if realms == [] or resolvers == [] or users is None:
            # A dimension matches nothing at all, so this policy grants no entries.
            continue
        usernames, excluded_usernames = users
        if not (realms or resolvers or usernames or excluded_usernames):
            # An applicable policy with no target scope grants access to all entries.
            return None
        try:
            excluded_accounts = _accounts_of(excluded_usernames, realms or list(get_realms()))
        except (ResolverError, UserError) as error:
            # Excluding the logins without their accounts would admit the entries an excluded account recorded
            # under another login, so the policy grants nothing rather than too much.
            log.warning(f"The users excluded by the policy {policy.get('name')!r} could not be resolved, so it grants "
                        f"no {action} entries: {error!s}")
            continue
        scopes.append(AuthenticationLogVisibilityScope(
            realms=realms or [], resolvers=resolvers or [], usernames=usernames,
            excluded_usernames=excluded_usernames, excluded_accounts=excluded_accounts,
            username_case_insensitive=case_insensitive))
    if policies and not scopes:
        # Every applicable policy grants nothing. None would read as unrestricted.
        return []
    return scopes or None
