#  2023-01-27 Cornelius Kölbel <cornelius@privacyidea.org>
#             Create this module for enabling decorators for API calls
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
"""
These are logical policy functions that are usually used in policy API decorators, but
in some cases also used beside the API.
Like policies, that are supposed to read and pass parameters during enrollment of a token.
"""

import logging

from privacyidea.lib.container import find_container_for_token, find_container_by_serial
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import Match, SCOPE, ACTION
from privacyidea.lib.error import PolicyError, ResourceNotFoundError
from privacyidea.lib.token import get_tokens_from_serial_or_user, get_token_owner

log = logging.getLogger(__name__)


@log_with(log)
def get_init_tokenlabel_parameters(g, params=None, token_type="hotp", user_object=None):
    """
    This helper function modifies the request parameters in regards
    to enrollment policies tokenlabel, tokenissuer, appimage, force_app_pin

    :param params: The request parameter
    :param user_object: User object in the request
    :return: modified request parameters
    """
    params = params or {}
    label_pols = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.TOKENLABEL,
                            user_object=user_object).action_values(unique=True, allow_white_space_in_action=True)
    if len(label_pols) == 1:
        # The policy was set, so we need to set the tokenlabel in the request.
        params[ACTION.TOKENLABEL] = list(label_pols)[0]

    issuer_pols = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.TOKENISSUER,
                             user_object=user_object).action_values(unique=True, allow_white_space_in_action=True)
    if len(issuer_pols) == 1:
        params[ACTION.TOKENISSUER] = list(issuer_pols)[0]

    imageurl_pols = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.APPIMAGEURL,
                               user_object=user_object).action_values(unique=True, allow_white_space_in_action=True)
    if len(imageurl_pols) == 1:
        params[ACTION.APPIMAGEURL] = list(imageurl_pols)[0]

    # check the force_app_pin policy
    app_pin_pols = Match.user(g, scope=SCOPE.ENROLL,
                              action='{0!s}_{1!s}'.format(token_type, ACTION.FORCE_APP_PIN),
                              user_object=user_object).any()
    if app_pin_pols:
        params[ACTION.FORCE_APP_PIN] = True

    return params


def get_pushtoken_add_config(g, params=None, user_obj=None):
    """
    This helper function modifies the request parameters in regards
    to enrollment policies for push tokens.

    :param params: The request parameter
    :param user_object: User object in the request
    :return: modified request parameters
    """
    params = params or {}
    from privacyidea.lib.tokens.pushtoken import PUSH_ACTION

    # Get the firebase configuration from the policies
    firebase_config = Match.user(g, scope=SCOPE.ENROLL, action=PUSH_ACTION.FIREBASE_CONFIG,
                                 user_object=user_obj if user_obj else None) \
        .action_values(unique=True, allow_white_space_in_action=True)
    if len(firebase_config) == 1:
        params[PUSH_ACTION.FIREBASE_CONFIG] = list(firebase_config)[0]
    else:
        raise PolicyError("Missing enrollment policy for push token: {0!s}".format(PUSH_ACTION.FIREBASE_CONFIG))

    # Get the sslverify definition from the policies
    ssl_verify = Match.user(g, scope=SCOPE.ENROLL, action=PUSH_ACTION.SSL_VERIFY,
                            user_object=user_obj if user_obj else None).action_values(unique=True)
    if len(ssl_verify) == 1:
        params[PUSH_ACTION.SSL_VERIFY] = list(ssl_verify)[0]
    else:
        params[PUSH_ACTION.SSL_VERIFY] = "1"

    # Get the TTL and the registration URL from the policies
    registration_url = Match.user(g, scope=SCOPE.ENROLL, action=PUSH_ACTION.REGISTRATION_URL,
                                  user_object=user_obj if user_obj else None) \
        .action_values(unique=True, allow_white_space_in_action=True)
    if len(registration_url) == 1:
        params[PUSH_ACTION.REGISTRATION_URL] = list(registration_url)[0]
    else:
        raise PolicyError("Missing enrollment policy for push token: {0!s}".format(PUSH_ACTION.REGISTRATION_URL))
    ttl = Match.user(g, scope=SCOPE.ENROLL, action=PUSH_ACTION.TTL,
                     user_object=user_obj if user_obj else None) \
        .action_values(unique=True, allow_white_space_in_action=True)
    if len(ttl) == 1:
        params[PUSH_ACTION.TTL] = list(ttl)[0]
    else:
        params[PUSH_ACTION.TTL] = "10"
    return params


def get_token_user_attributes(serial: str):
    """
    Get the user attributes from the token owner and the token realms.

    :param serial: The serial of the token
    :return: username (str), realm (str), resolver (str), token_realms (list)
    """
    username = realm = resolver = token_realms = None
    # get user attributes from the token
    try:
        token = get_tokens_from_serial_or_user(serial, user=None)[0]
        token_owner = get_token_owner(serial)
    except ResourceNotFoundError:
        token = None
        token_owner = None
        log.error(f"Could not find token with serial {serial}.")
    if token_owner:
        username = token_owner.login
        realm = token_owner.realm
        resolver = token_owner.resolver
    if token:
        token_realms = token.get_realms()
    return username, realm, resolver, token_realms


def check_token_action_allowed(g, action: str, serial: str, role: str, username: str, realm: str, resolver: str,
                               adminuser: str, adminrealm: str):
    """
    Retrieves user attributes from the token and checks if the logged-in user is allowed to perform the action on the
    token.

    For admins, the policies either need to match the token owner or at least one of the token realms.
    If no user attributes (username, realm, resolver) are available, the policies are filtered for generic policies
    without conditions on the user. Only for the action ASSIGN, all policies are considered, ignoring the username,
    realm, and resolver conditions. The token realms are still taken into account. This shall allow helpdesk admins
    to assign their users to tokens without owner.

    :param g: The global flask object g
    :param action: The action to be performed on the token
    :param serial: The serial of the token
    :param role: The role of the logged-in user (user or admin)
    :param username: The username of the logged-in user (only for users)
    :param realm: The realm of the logged-in user (only for users)
    :param resolver: The resolver of the logged-in user (only for users)
    :param adminuser: The username of the logged-in admin (only for admins)
    :param adminrealm: The realm of the logged-in admin (only for admins)
    :return: True if the action is allowed, False otherwise
    """
    token_realms = None
    if role == "admin":
        if serial:
            username, realm, resolver, token_realms = get_token_user_attributes(serial)

        if action == ACTION.ASSIGN:
            # Assigning a user to a token is only possible if the token has no owner yet.
            # To avoid helpdesk admins (for a specific resolver) lose their tokens while changing the owner of a
            # token, they are allowed to assign their users to tokens without owner.
            # Note: the policies are still filtered by the token realms.
            username = username or None
            realm = realm or None
            resolver = resolver or None
        else:
            # If no user is available, explicitly filter for generic policies without conditions on the user
            username = username or ""
            realm = realm or ""
            resolver = resolver or ""

    # Check action for the token
    action_allowed = Match.generic(g,
                                   scope=role,
                                   action=action,
                                   user=username,
                                   resolver=resolver,
                                   realm=realm,
                                   adminrealm=adminrealm,
                                   adminuser=adminuser,
                                   additional_realms=token_realms).allowed()

    if action_allowed and action == ACTION.CONTAINER_ADD_TOKEN:
        # Adding a token to a container will remove it from the old container: Check if the remove action is allowed
        try:
            old_container = find_container_for_token(serial)
        except ResourceNotFoundError:
            old_container = None

        if old_container:
            action_allowed = check_container_action_allowed(g, ACTION.CONTAINER_REMOVE_TOKEN, old_container.serial,
                                                            role, username, realm, resolver, adminuser, adminrealm)
            if not action_allowed:
                log.info(f"Token {serial} is in container {old_container.serial}. The user is not allowed to remove the"
                         " token from this container.")

    return action_allowed


def check_container_action_allowed(g, action: str, container_serial: str, role: str, username: str, realm: str,
                                   resolver: str, adminuser: str, adminrealm: str):
    """
        Retrieves user attributes from the container and checks if the logged-in user is allowed to perform the action
        on the container.

        For admins, the policies either need to match the container owner or at least one of the container realms.
        If no user attributes (username, realm, resolver) are available, the policies are filtered for generic policies
        without conditions on the user. Only for the action ASSIGN, all policies are considered, ignoring the username,
        realm, and resolver conditions. The container realms are still taken into account. This shall allow helpdesk
        admins to assign their users to containers without owner.

        :param g: The global flask object g
        :param action: The action to be performed on the container
        :param container_serial: The serial of the container
        :param role: The role of the logged-in user (user or admin)
        :param username: The username of the logged-in user (only for users)
        :param realm: The realm of the logged-in user (only for users)
        :param resolver: The resolver of the logged-in user (only for users)
        :param adminuser: The username of the logged-in admin (only for admins)
        :param adminrealm: The realm of the logged-in admin (only for admins)
        :return: True if the action is allowed, False otherwise
        """
    container_realms = None
    if role == "admin":
        if container_serial:
            # get user attributes from the container
            try:
                container = find_container_by_serial(container_serial)
            except ResourceNotFoundError:
                container = None
                log.error(f"Could not find container with serial {container_serial}.")
            if container:
                container_owners = container.get_users()
                container_owner = container_owners[0] if container_owners else None
                if container_owner:
                    username = container_owner.login
                    realm = container_owner.realm
                    resolver = container_owner.resolver
                else:
                    username = realm = resolver = None
                container_realms = [realm.name for realm in container.realms]

        if action == ACTION.CONTAINER_ASSIGN_USER:
            # Assigning a user to a container is only possible if the container has no owner yet.
            # To avoid helpdesk admins (for a specific resolver) lose their containers while changing the owner of a
            # container, they are allowed to assign their users to containers without user.
            # Note: the policies are still filtered by the container realms.
            username = username or None
            realm = realm or None
            resolver = resolver or None
        else:
            # If no user is available, explicitly filter for generic policies without conditions on the user
            username = username or ""
            realm = realm or ""
            resolver = resolver or ""

    # Check action for container
    action_allowed = Match.generic(g,
                                   scope=role,
                                   action=action,
                                   user=username,
                                   resolver=resolver,
                                   realm=realm,
                                   adminrealm=adminrealm,
                                   adminuser=adminuser,
                                   additional_realms=container_realms).allowed()

    return action_allowed
