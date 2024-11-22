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

from privacyidea.lib.container import get_container_realms, find_container_by_serial
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import Match, SCOPE, ACTION
from privacyidea.lib.error import PolicyError, ResourceNotFoundError
from privacyidea.lib.token import get_realms_of_token

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


def check_matching_realms(container_serial, allowed_realms, params):
    """
    Checks if at least one realm of the container is contained in the allowed realms.
    If a token serial is given in the request parameters, it is also evaluated for the token realms.

    :param container_serial: The serial of the container
    :param allowed_realms: A list of the realms that are allowed to perform the action
    :param params: The request parameters
    :return: True if at least one realm is allowed, False otherwise
    """
    action_allowed = True
    container_realms = get_container_realms(container_serial)

    # Check if at least one container realm is allowed
    if allowed_realms and container_realms:
        matching_realms = list(set(container_realms).intersection(allowed_realms))
        action_allowed = len(matching_realms) > 0

    # get the realm by the token serial:
    token_realms = None
    if params.get("serial"):
        serial = params.get("serial")
        if serial.isalnum():
            # single serial, no list
            token_realms = get_realms_of_token(params.get("serial"), only_first_realm=False)

        # Check if at least one token realm is allowed
        if action_allowed and allowed_realms and token_realms:
            matching_realms = list(set(token_realms).intersection(allowed_realms))
            action_allowed = len(matching_realms) > 0

    return action_allowed


def get_container_user_attributes_for_policy_match(request):
    """
    Get the user and container realms from the request.
    If a user attribute (username, realm, resolver) is not available, an empty string is returned.
    If no container realms are available or if it is equal to the user realm, an empty list is returned.

    :param request: The request object
    :return: username, realm, resolver, container realms
    :rtype: str, str, str, list
    """
    params = request.all_data
    container_serial = params.get("container_serial")
    user_object = request.User
    username = realm = resolver = ""
    try:
        container_realms = get_container_realms(container_serial)
    except ResourceNotFoundError:
        log.info(f"Container serial {container_serial} passed as request parameter does not exist.")
        container_realms = []

    if user_object:
        username = user_object.login
        realm = user_object.realm
        resolver = user_object.resolver

    if len(container_realms) == 1 and realm in container_realms:
        container_realms = None
    elif len(container_realms) == 0:
        container_realms = None

    return username, realm, resolver, container_realms


def user_is_container_owner(params, username, realm, allow_no_owner=False):
    """
    This decorator checks if the user is the owner of the container.
    A user is only allowed to manage and edit its own containers.
    If the user is not the owner of the container, a PolicyError is raised.
    If no container is found, the user is allowed to do the action.

    :param request: The request object
    :param allow_no_owner: If True, the user is allowed to manage a container without owner
    :return: True if the user is the owner of the container, otherwise raises a PolicyError
    """

    container_serial = params.get("container_serial")
    try:
        container = find_container_by_serial(container_serial) if container_serial else None
    except ResourceNotFoundError:
        log.info(f"Container with serial {container_serial} not found.")
    if container:
        container_owners = container.get_users()
        is_owner = False
        for owner in container_owners:
            if owner.login == username and owner.realm == realm:
                is_owner = True
                break
        if allow_no_owner and len(container_owners) == 0:
            is_owner = True
        if not is_owner:
            raise PolicyError("User is not the owner of the container.")
    return is_owner
