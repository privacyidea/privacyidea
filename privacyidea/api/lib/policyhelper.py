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
from dataclasses import dataclass
import logging

from privacyidea.lib.container import get_container_realms, find_container_for_token, find_container_by_serial
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import Match, SCOPE, ACTION
from privacyidea.lib.error import PolicyError, ResourceNotFoundError
from privacyidea.lib.token import get_tokens_from_serial_or_user, get_token_owner, get_realms_of_token
from privacyidea.lib.user import User

log = logging.getLogger(__name__)


@dataclass
class UserAttributes:
    role: str = None
    username: str = None
    realm: str = None
    resolver: str = None
    adminuser: str = None
    adminrealm: str = None
    additional_realms: list = None


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
    firebase_config = Match.user(g, scope=SCOPE.ENROLL,
                                 action=PUSH_ACTION.FIREBASE_CONFIG,
                                 user_object=user_obj if user_obj else None
                                 ).action_values(unique=True,
                                                 allow_white_space_in_action=True)
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
    :return: UserAttributes dataclass
    """
    user_attributes = UserAttributes()
    # get user attributes from the token
    try:
        token = get_tokens_from_serial_or_user(serial, user=None)[0]
        token_owner = get_token_owner(serial)
    except ResourceNotFoundError:
        token = None
        token_owner = None
        log.error(f"Could not find token with serial {serial}.")
    if token_owner:
        user_attributes.username = token_owner.login
        user_attributes.realm = token_owner.realm
        user_attributes.resolver = token_owner.resolver
    if token:
        user_attributes.additional_realms = token.get_realms()
    return user_attributes


def get_container_user_attributes(container_serial: str) -> UserAttributes:
    """
    Get the user and container realms from the request.
    If a user attribute (username, realm, resolver) is not available, it is set to None.
    If no container realms are available an empty list is set.

    :param container_serial: Serial of the container
    :return: container_owner_attributes
    """
    container_owner_attributes = UserAttributes()

    try:
        container = find_container_by_serial(container_serial)
    except ResourceNotFoundError:
        container = None
        log.error(f"Could not find container with serial {container_serial}.")
    if container:
        container_owners = container.get_users()
        container_owner = container_owners[0] if container_owners else None
        if container_owner:
            container_owner_attributes.username = container_owner.login
            container_owner_attributes.realm = container_owner.realm
            container_owner_attributes.resolver = container_owner.resolver
        container_owner_attributes.additional_realms = [realm.name for realm in container.realms]

    return container_owner_attributes


def check_token_action_allowed(g, action: str, serial: str, user_attributes: UserAttributes) -> bool:
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
    :param user_attributes: User attributes of the logged-in user
    :return: True if the action is allowed, False otherwise
    """
    if serial:
        token_owner_attributes = get_token_user_attributes(serial)
    else:
        token_owner_attributes = UserAttributes()

    if user_attributes.role == "admin":
        if action == ACTION.ASSIGN:
            # Assigning a user to a token is only possible if the token has no owner yet.
            # To avoid helpdesk admins (for a specific resolver) lose access on their tokens while changing the owner
            # of a token, they are allowed to assign their users to tokens without owner.
            # Note: the policies are still filtered by the token realms.
            user_attributes.username = token_owner_attributes.username or None
            user_attributes.realm = token_owner_attributes.realm or None
            user_attributes.resolver = token_owner_attributes.resolver or None
        else:
            # If no user is available, explicitly filter for generic policies without conditions on the user
            user_attributes.username = token_owner_attributes.username or ""
            user_attributes.realm = token_owner_attributes.realm or ""
            user_attributes.resolver = token_owner_attributes.resolver or ""
        user_attributes.additional_realms = token_owner_attributes.additional_realms or None
    elif user_attributes.role == "user" and serial:
        # for adding / removing tokens from a container, the user has to be the owner of the token
        if action in [ACTION.CONTAINER_ADD_TOKEN, ACTION.CONTAINER_REMOVE_TOKEN]:
            if not user_is_owner(user_attributes, token_owner_attributes, allow_no_owner=False):
                return False

    # Check action for the token
    action_allowed = Match.generic(g,
                                   scope=user_attributes.role,
                                   action=action,
                                   user=user_attributes.username,
                                   resolver=user_attributes.resolver,
                                   realm=user_attributes.realm,
                                   adminrealm=user_attributes.adminrealm,
                                   adminuser=user_attributes.adminuser,
                                   additional_realms=user_attributes.additional_realms).allowed()

    if action_allowed and action == ACTION.CONTAINER_ADD_TOKEN:
        # Adding a token to a container will remove it from the old container: Check if the remove action is allowed
        try:
            old_container = find_container_for_token(serial)
        except ResourceNotFoundError:
            old_container = None

        if old_container:
            action_allowed = check_container_action_allowed(g, ACTION.CONTAINER_REMOVE_TOKEN, old_container.serial,
                                                            user_attributes)
            if not action_allowed:
                log.info(f"Token {serial} is in container {old_container.serial}. The user is not allowed to remove the"
                         " token from this container.")

    return action_allowed


def check_container_action_allowed(g, action: str, container_serial: str, user_attributes: UserAttributes) -> bool:
    """
    Retrieves user attributes from the container and checks if the logged-in user is allowed to perform the action
    on the container.

    For admins, the policies either need to match the container owner or at least one of the container realms.
    If no user attributes (username, realm, resolver) are available, the policies are filtered for generic policies
    without conditions on the user. Only for the action CONTAINER_ASSIGN_USER, all policies are considered, ignoring
    the username, realm, and resolver conditions. The container realms are still taken into account. This shall allow
    helpdesk admins to assign their users to containers without owner.

    For the action CONTAINER_CREATE, the user attributes from the parameters are considered, as the container has no
    owner yet.

    :param g: The global flask object g
    :param action: The action to be performed on the container
    :param container_serial: The serial of the container
    :param user_attributes: User attributes of the logged-in user
    :return: True if the action is allowed, False otherwise
    """
    user_attributes.additional_realms = None
    container_owner_attributes = UserAttributes()
    if container_serial:
        # get user attributes from the container
        container_owner_attributes = get_container_user_attributes(container_serial)

    if user_attributes.role == "admin":
        if action == ACTION.CONTAINER_ASSIGN_USER:
            # Assigning a user to a container is only possible if the container has no owner yet.
            # To avoid helpdesk admins (for a specific resolver) lose access on their containers while changing the
            # owner of a container, they are allowed to assign their users to containers without user.
            # Note: the policies are still filtered by the container realms.
            user_attributes.username = container_owner_attributes.username or None
            user_attributes.realm = container_owner_attributes.realm or None
            user_attributes.resolver = container_owner_attributes.resolver or None
        elif action == ACTION.CONTAINER_CREATE:
            # If the container is created, it has no owner yet, instead check the user attributes from the parameters
            user_attributes.username = user_attributes.username or ""
            user_attributes.realm = user_attributes.realm or ""
            user_attributes.resolver = user_attributes.resolver or ""
        else:
            # If no user is available, explicitly filter for generic policies without conditions on the user
            user_attributes.username = container_owner_attributes.username or ""
            user_attributes.realm = container_owner_attributes.realm or ""
            user_attributes.resolver = container_owner_attributes.resolver or ""
        user_attributes.additional_realms = container_owner_attributes.additional_realms or None
    elif user_attributes.role == "user" and container_serial:
        # check if the user is the owner of the container
        if action == ACTION.CONTAINER_CREATE:
            # container has no owner yet, skip this check
            is_owner = True
        elif action == ACTION.CONTAINER_ASSIGN_USER:
            # users are allowed to assign containers without owner
            is_owner = user_is_owner(user_attributes, container_owner_attributes, allow_no_owner=True)
        else:
            is_owner = user_is_owner(user_attributes, container_owner_attributes, allow_no_owner=False)
        if not is_owner:
            return False

    # Check action for container
    action_allowed = Match.generic(g,
                                   scope=user_attributes.role,
                                   action=action,
                                   user=user_attributes.username,
                                   resolver=user_attributes.resolver,
                                   realm=user_attributes.realm,
                                   adminrealm=user_attributes.adminrealm,
                                   adminuser=user_attributes.adminuser,
                                   additional_realms=user_attributes.additional_realms).allowed()
    return action_allowed


def user_is_owner(logged_in_user_attr: UserAttributes, owner_attr: UserAttributes,
                  allow_no_owner: bool = False) -> bool:
    """
    Checks if the logged-in user is the owner of the token or container.

    :param logged_in_user_attr: User attributes of the logged-in user
    :param owner_attr: User attributes of the token or container owner
    :param allow_no_owner: If True, the user is considered the owner if the owner is None
    :return: True if the user is the owner, False otherwise
    """
    user = User(logged_in_user_attr.username, logged_in_user_attr.realm, logged_in_user_attr.resolver)
    owner = User(owner_attr.username, owner_attr.realm, owner_attr.resolver)
    is_owner = user == owner
    if not is_owner and allow_no_owner and not owner:
        is_owner = True
    return is_owner
