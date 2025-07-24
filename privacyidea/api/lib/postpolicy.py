#  2020-02-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add QR codes for Authenticator Apps
#  2016-02-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add tokenwizard
#  2015-10-25 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add default token type for tokenenrollment
#  2015-09-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add decorator to sign a response
#  2015-04-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add logout time config
#  2015-03-31 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add postpolicy for offline information
#  2015-02-06 Cornelius Kölbel <cornelius@privacyidea.org>
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
These are the policy decorators as POST conditions for the API calls.
I.e. these conditions are executed after the wrapped API call.
This module uses the policy base functions from
privacyidea.lib.policy but also components from flask like g.

Wrapping the functions in a decorator class enables easy modular testing.

The functions of this module are tested in tests/test_api_lib_policy.py
"""
import copy
import datetime
import functools
import json
import logging
import re
import traceback
from urllib.parse import quote

from flask import g, current_app, make_response, Request

from privacyidea.api.lib.utils import get_all_params
from privacyidea.lib import _, lazy_gettext
from privacyidea.lib.auth import ROLE
from privacyidea.lib.config import get_multichallenge_enrollable_types, get_token_class, get_privacyidea_node
from privacyidea.lib.crypto import Sign
from privacyidea.lib.error import PolicyError, ValidateError
from privacyidea.lib.info.rss import FETCH_DAYS
from privacyidea.lib.machine import get_auth_items
from privacyidea.lib.policy import (DEFAULT_ANDROID_APP_URL, DEFAULT_IOS_APP_URL, DEFAULT_PREFERRED_CLIENT_MODE_LIST,
                                    SCOPE, ACTION, AUTOASSIGNVALUE, AUTHORIZED, Match)
from privacyidea.lib.realm import get_default_realm
from privacyidea.lib.subscriptions import (subscription_status,
                                           get_subscription,
                                           check_subscription,
                                           SubscriptionError,
                                           EXPIRE_MESSAGE)
from privacyidea.lib.token import get_tokens, assign_token, get_realms_of_token, get_one_token, init_token
from privacyidea.lib.tokenclass import ROLLOUTSTATE, CHALLENGE_SESSION
from privacyidea.lib.tokens.passkeytoken import PasskeyTokenClass
from privacyidea.lib.user import User
from privacyidea.lib.utils import (create_img, get_version, AUTH_RESPONSE,
                                   get_plugin_info_from_useragent)
from .prepolicy import check_max_token_user, check_max_token_realm, fido2_enroll, rss_age, container_registration_config
from ...lib.challenge import get_challenges
from ...lib.container import (get_all_containers, init_container, init_registration, find_container_by_serial,
                              create_container_tokens_from_template)
from ...lib.containers.container_info import SERVER_URL, CHALLENGE_TTL, REGISTRATION_TTL, SSL_VERIFY, RegistrationState
from ...lib.users.custom_user_attributes import InternalCustomUserAttributes

log = logging.getLogger(__name__)

optional = True
required = False
DEFAULT_LOGOUT_TIME = 120
DEFAULT_AUDIT_PAGE_SIZE = 10
DEFAULT_PAGE_SIZE = 15
DEFAULT_TOKENTYPE = "hotp"
DEFAULT_CONTAINER_TYPE = "generic"
DEFAULT_TIMEOUT_ACTION = "lockscreen"
DEFAULT_POLICY_TEMPLATE_URL = "https://raw.githubusercontent.com/privacyidea/" \
                              "policy-templates/master/templates/"
BODY_TEMPLATE = lazy_gettext("""
<--- Please describe your Problem in detail --->

<--- Please provide as many additional information as possible --->

privacyIDEA Version: {version}
Subscriber: {subscriber_name}
Subscriptions: {subscriptions}
""")


class postpolicy(object):
    """
    Decorator that allows one to call a specific function after the decorated
    function.
    The postpolicy decorator is to be used in the API calls.
    """

    def __init__(self, function, request=None):
        """
        :param function: This is the policy function the is to be called
        :type function: function
        :param request: The original request object, that needs to be passed
        :type request: Request Object
        """
        self.request = request
        self.function = function

    def __call__(self, wrapped_function):
        """
        This decorates the given function. The postpolicy decorator is ment
        for API functions on the API level.
        The wrapped_function should return a response object.

        :param wrapped_function: The function, that is decorated.
        :type wrapped_function: API function
        :return: Response object
        """

        @functools.wraps(wrapped_function)
        def policy_wrapper(*args, **kwds):
            response = wrapped_function(*args, **kwds)
            return self.function(self.request, response, *args, **kwds)

        return policy_wrapper


class postrequest(object):
    """
    Decorator that is supposed to be used with after_request.
    """

    def __init__(self, function, request=None):
        """
        :param function: This is the policy function the is to be called
        :type function: function
        :param request: The original request object, that needs to be passed
        :type request: Request Object
        """
        self.request = request
        self.function = function

    def __call__(self, wrapped_function):
        @functools.wraps(wrapped_function)
        def policy_wrapper(*args, **kwds):
            response = wrapped_function(*args, **kwds)
            return self.function(self.request, response, **kwds)

        return policy_wrapper


def sign_response(request, response):
    """
    This decorator is used to sign the response. It adds the nonce from the
    request, if it exists and adds the nonce and the signature to the response.

    .. note:: This only works for JSON responses. So if we fail to decode the
       JSON, we just pass on.

    The usual way to use it is to wrap the after_request, so that we can also
    sign errors, like this::

        @postrequest(sign_response, request=request)
        def after_request(response):
            ...

    :param request: The Request object
    :param response: The Response object
    """
    if current_app.config.get("PI_NO_RESPONSE_SIGN"):
        return response

    private_key_file = current_app.config.get("PI_AUDIT_KEY_PRIVATE")

    # Disable the costly checking of private RSA keys when loading them.
    check_private_key = not current_app.config.get("PI_RESPONSE_NO_PRIVATE_KEY_CHECK", False)
    try:
        with open(private_key_file, 'rb') as file:
            private_key = file.read()
        sign_object = Sign(private_key, public_key=None, check_private_key=check_private_key)
    except (IOError, ValueError, TypeError) as e:
        log.info('Could not load private key from '
                 'file {0!s}: {1!r}!'.format(private_key_file, e))
        log.debug(traceback.format_exc())
        return response

    # Save the request data
    g.request_data = get_all_params(request)
    request.all_data = copy.deepcopy(g.request_data)
    # response can be either a Response object or a Tuple (Response, ErrorID)
    response_value = 200
    response_is_tuple = False
    if type(response).__name__ == "tuple":
        response_is_tuple = True
        response_value = response[1]
        response_object = response[0]
    else:
        response_object = response
    if response_object.is_json:
        content = response_object.json
        nonce = request.all_data.get("nonce")
        if nonce:
            content["nonce"] = nonce

        content["signature"] = sign_object.sign(json.dumps(content, sort_keys=True))
        response_object.set_data(json.dumps(content))
    else:
        # The response.data is no JSON (but CSV or policy export)
        # We do no signing in this case.
        log.info("We only sign JSON response data.")

    if response_is_tuple:
        resp = (response_object, response_value)
    else:
        resp = response_object
    return resp


def check_tokentype(request, response):
    """
    This policy function is to be used in a decorator of an API function.
    It checks, if the token, that was used in the API call is of a type that
    is allowed to be used.

    If not, a PolicyException is raised.

    :param request: The request object
    :param response: The response of the decorated function
    :type response: Response object
    :return: A new (maybe modified) response
    """
    token_type = response.json.get("detail", {}).get("type")
    if not hasattr(request, "User"):
        raise PolicyError("No user object in request, unable to perform check_tokentype!")
    user = request.User
    allowed_token_types = Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.TOKENTYPE,
                                     user_object=user).action_values(unique=False)
    if token_type and allowed_token_types and token_type not in allowed_token_types:
        # If we have tokentype policies, but the tokentype is not allowed, we raise an exception
        g.audit_object.log({"success": False,
                            "action_detail": f"Tokentype {token_type!r} not allowed for authentication"})
        raise PolicyError("Tokentype not allowed for authentication!")
    return response


def check_serial(request, response):
    """
    This policy function is to be used in a decorator of an API function.
    It checks, if the token, that was used in the API call has a serial
    number that is allowed to be used.

    If not, a PolicyException is raised.

    :param request: The request object
    :param response: The response of the decorated function
    :type response: Response object
    :return: A new (maybe modified) response
    """
    serial = response.json.get("detail", {}).get("serial")
    # get the serials from a policy definition
    allowed_serials = Match.action_only(g, scope=SCOPE.AUTHZ, action=ACTION.SERIAL).action_values(unique=False)

    # If we can compare a serial and if we do serial matching!
    if serial and allowed_serials:
        serial_matches = False
        for allowed_serial in allowed_serials:
            if re.search(allowed_serial, serial):
                serial_matches = True
                break
        if serial_matches is False:
            g.audit_object.log({"action_detail": "Serial is not allowed for "
                                                 "authentication!"})
            raise PolicyError("Serial is not allowed for authentication!")
    return response


def check_tokeninfo(request, response):
    """
    This policy function is used as a decorator for the validate API.
    It checks after a successful authentication if the token has a matching
    tokeninfo field. If it does not match, authorization is denied. Then
    a PolicyException is raised.

    :param request: The request object
    :param response: The response of the decorated function
    :type response: Response object
    :return: A new modified response
    """
    serial = response.json.get("detail", {}).get("serial")

    if serial:
        tokeninfo_policy = (Match.action_only(g, scope=SCOPE.AUTHZ, action=ACTION.TOKENINFO)
                            .action_values(unique=False, allow_white_space_in_action=True))
        if tokeninfo_policy:
            tokens = get_tokens(serial=serial)
            if len(tokens) == 1:
                token = tokens[0]
                for tokeninfo_pol in tokeninfo_policy:
                    try:
                        key, regex, _r = tokeninfo_pol.split("/")
                        value = token.get_tokeninfo(key, "")
                        if re.search(regex, value):
                            log.debug("Regular expression {0!s} "
                                      "matches the tokeninfo field {1!s}.".format(regex, key))
                        else:
                            log.info("Tokeninfo field {0!s} with contents {1!s} "
                                     "does not match {2!s}".format(key, value, regex))
                            raise PolicyError("Tokeninfo field {0!s} with contents does not"
                                              " match regular expression.".format(key))
                    except ValueError:
                        log.warning("Invalid tokeninfo policy: {0!s}".format(tokeninfo_pol))

    return response


def no_detail_on_success(request, response):
    """
    This policy function is used with the AUTHZ scope.
    If the boolean value no_detail_on_success is set,
    the details will be stripped if
    the authentication request was successful.

    :param request:
    :param response:
    :return:
    """
    content = response.json

    # get the serials from a policy definition
    policy = Match.action_only(g, scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS).policies(write_to_audit_log=False)
    if policy and content.get("result", {}).get("value"):
        # The policy was set, we need to strip the details, if the
        # authentication was successful. (value=true)
        # None assures that we do not get an error, if "detail" does not exist.
        # TODO: This would strip away the details for challenge-response
        #  authentication for the /auth and /validate/samlcheck endpoints
        #  since they contain a dictionary in result->value
        content.pop("detail", None)
        response.set_data(json.dumps(content))
        g.audit_object.add_policy([p.get("name") for p in policy])

    return response


def preferred_client_mode(request, response):
    """
    This policy function is used to add the preferred client mode.
    The admin can set the list of client modes in the policy in the
    same order as  he preferred them. The faction will pick the first
    client mode from the list, that is also in the multichallenge and
    set it as preferred client mode

    :param request:
    :param response:
    :return:
    """
    content = response.json
    user = request.User

    # get the preferred client mode from a policy definition
    preferred_client_mode_pol = Match.user(g, scope=SCOPE.AUTH, action=ACTION.PREFERREDCLIENTMODE,
                                           user_object=user).action_values(allow_white_space_in_action=True,
                                                                           unique=True)
    if preferred_client_mode_pol:
        # Split at whitespaces and strip
        preferred_client_mode_list = str.split(list(preferred_client_mode_pol)[0])
    else:
        preferred_client_mode_list = DEFAULT_PREFERRED_CLIENT_MODE_LIST

    # check policy if client mode per user shall be used
    client_mode_per_user_pol = Match.user(g, scope=SCOPE.AUTH, action=ACTION.CLIENT_MODE_PER_USER,
                                          user_object=user).allowed()
    last_used_token_type = None
    if client_mode_per_user_pol:
        user_agent, _, _ = get_plugin_info_from_useragent(request.user_agent.string)
        user_attributes = user.attributes
        last_used_token_type = user_attributes.get(f"{InternalCustomUserAttributes.LAST_USED_TOKEN}_{user_agent}")

    if content.get("detail"):
        detail = content.get("detail")
        if detail.get("multi_challenge"):
            multi_challenge = detail.get("multi_challenge")

            # First try to use the users preferred token type
            preferred = None
            if last_used_token_type:
                for challenge in multi_challenge:
                    if challenge.get('type') == last_used_token_type:
                        preferred = challenge.get('client_mode')
                        content.setdefault("detail", {})["preferred_client_mode"] = preferred
                        break

            if not preferred:
                # User preferred client mode not found, check the policy
                client_modes = [x.get('client_mode') for x in multi_challenge]
                try:
                    preferred = [x for x in preferred_client_mode_list if x in client_modes][0]
                    content.setdefault("detail", {})["preferred_client_mode"] = preferred
                except IndexError as err:
                    content.setdefault("detail", {})["preferred_client_mode"] = 'interactive'
                    log.error('There was no acceptable client mode in the multi-challenge list. '
                              'The preferred client mode is set to "interactive". '
                              f'Please check Your policy ({preferred_client_mode_list}). '
                              f'Error: {err} ')
                except Exception as err:  # pragma no cover
                    content.setdefault("detail", {})["preferred_client_mode"] = 'interactive'
                    log.error('Something went wrong during setting the preferred '
                              f'client mode. Error: {err}')

    response.set_data(json.dumps(content))
    return response


def add_user_detail_to_response(request, response):
    """
    This policy decorated is used in the AUTHZ scope.
    If the boolean value add_user_in_response is set,
    the details will contain a dictionary "user" with all user details.

    :param request:
    :param response:
    :return:
    """
    content = response.json

    # Check for ADD USER IN RESPONSE
    policy = (Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.ADDUSERINRESPONSE, user_object=request.User)
              .policies(write_to_audit_log=False))
    if policy and content.get("result", {}).get("authentication") == AUTH_RESPONSE.ACCEPT and request.User:
        # The policy was set, we need to add the user details
        ui = request.User.info.copy()
        ui["password"] = ""  # nosec B105 # Hide a potential password
        for key, value in ui.items():
            if isinstance(value, datetime.datetime):
                ui[key] = str(value)
        content.setdefault("detail", {})["user"] = ui
        g.audit_object.add_policy([p.get("name") for p in policy])

    # Check for ADD RESOLVER IN RESPONSE
    policy = (Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.ADDRESOLVERINRESPONSE, user_object=request.User)
              .policies(write_to_audit_log=False))
    if policy and content.get("result", {}).get("value") and request.User:
        # The policy was set, we need to add the resolver and the realm
        content.setdefault("detail", {})["user-resolver"] = request.User.resolver
        content["detail"]["user-realm"] = request.User.realm
        g.audit_object.add_policy([p.get("name") for p in policy])

    response.set_data(json.dumps(content))
    return response


def no_detail_on_fail(request, response):
    """
    This policy function is used with the AUTHZ scope.
    If the boolean value no_detail_on_fail is set,
    the details will be stripped if
    the authentication request failed.

    :param request:
    :param response:
    :return:
    """
    content = response.json

    # get the serials from a policy definition
    detail_policy = (Match.action_only(g, scope=SCOPE.AUTHZ, action=ACTION.NODETAILFAIL)
                     .policies(write_to_audit_log=False))
    if detail_policy and content.get("result", {}).get("value") is False:
        # The policy was set, we need to strip the details, if the
        # authentication failed. (value=False)
        # TODO: this strips away possible transactions ids during a
        #  challenge-response authentication. We should consider the
        #  result->authentication entry and only strip away possible user information
        del content["detail"]
        response.set_data(json.dumps(content))
        g.audit_object.add_policy([p.get("name") for p in detail_policy])

    return response


def save_pin_change(request, response, serial=None):
    """
    This policy function checks if the next_pin_change date should be
    stored in the tokeninfo table.

    1. Check scope:enrollment and
       ACTION.CHANGE_PIN_FIRST_USE.
       This action is used, when the administrator enrolls a token or sets a PIN

    2. Check scope:enrollment and
       ACTION.CHANGE_PIN_EVERY is used, if the user changes the PIN.

    This function decorates /token/init and /token/setpin. The parameter
    "pin" and "otppin" is investigated.

    :param request:
    :param response:
    :param serial:
    :return:
    """
    serial = serial or request.all_data.get("serial")
    if not serial:
        # No serial in request, so we look into the response
        serial = response.json.get("detail", {}).get("serial")
    if not serial:
        log.error("Can not determine serial number. Have no idea of any "
                  "realm!")
    else:
        # Determine the realm by the serial
        realm = get_realms_of_token(serial, only_first_realm=True)
        realm = realm or get_default_realm()

        if g.logged_in_user.get("role") == ROLE.ADMIN:
            policy = Match.realm(g, scope=SCOPE.ENROLL, action=ACTION.CHANGE_PIN_FIRST_USE,
                                 realm=realm).policies()
            if policy:
                token = get_one_token(serial=serial)
                token.set_next_pin_change(diff="0d")

        elif g.logged_in_user.get("role") == ROLE.USER:
            # Check for parameter "pin" or "otppin".
            otppin = request.all_data.get("otppin")
            pin = request.all_data.get("pin")
            # The user sets a pin or enrolls a token. -> delete the pin_change
            if otppin or pin:
                token = get_one_token(serial=serial)
                token.del_tokeninfo("next_pin_change")

                # If there is a change_pin_every policy, we need to set the PIN anew.
                policy = Match.realm(g, scope=SCOPE.ENROLL, action=ACTION.CHANGE_PIN_EVERY,
                                     realm=realm).action_values(unique=True)
                if policy:
                    token = get_one_token(serial=serial)
                    token.set_next_pin_change(diff=list(policy)[0])

    # we do not modify the response!
    return response


def offline_info(request, response):
    """
    This decorator is used with the function /validate/check.
    It is not triggered by an ordinary policy but by a MachineToken definition.
    If for the given Token an offline application is defined, the hashes of OTP values or FIDO2 credential information
    is added to the response.

    """
    content = response.json
    # check if the authentication was successful
    if content.get("result").get("value") is True and g.client_ip:
        # check if there is a MachineToken definition
        serial = content.get("detail", {}).get("serial")
        if serial:
            try:
                auth_items = get_auth_items(serial=serial, application="offline",
                                            challenge=request.all_data.get("pass"),
                                            user_agent=request.user_agent.string)
                if auth_items:
                    content["auth_items"] = auth_items
                    response.set_data(json.dumps(content))
                    # Also update JSON in the response object
                    response.get_jsons()
            except Exception as exx:
                log.info(exx)
    return response


def get_webui_settings(request, response):
    """
    This decorator is used in the /auth API to add configuration information
    like the logout_time or the policy_template_url to the response.

    :param request: flask request object
    :param response: flask response object
    :return: the response
    """
    content = response.json
    # If the authentication was successful (and not a challenge request), add the settings to the result
    if content.get("result").get("status") and isinstance(content.get("result").get("value"), dict):
        role = content.get("result").get("value").get("role")
        username = content.get("result").get("value").get("username")
        realm = content.get("result").get("value").get("realm")

        # Usually the user is already resolved in the request, except for local admins
        user = request.User if not request.User.is_empty() else None

        # At this point the logged-in user is not necessarily a user object. It can
        # also be a local admin.
        logout_time_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.LOGOUTTIME, user_object=user,
                                        user=username, realm=realm).action_values(unique=True)
        timeout_action_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.TIMEOUT_ACTION, user_object=user,
                                           user=username, realm=realm).action_values(unique=True)
        audit_page_size_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.AUDITPAGESIZE, user_object=user,
                                            user=username, realm=realm).action_values(unique=True)
        token_page_size_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.TOKENPAGESIZE, user_object=user,
                                            user=username, realm=realm).action_values(unique=True)
        user_page_size_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.USERPAGESIZE, user_object=user,
                                           user=username, realm=realm).action_values(unique=True)
        token_wizard_2nd = bool(role == ROLE.USER
                                and Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.TOKENWIZARD2ND, user_object=user,
                                                  user=username, realm=realm).policies())
        admin_dashboard = (role == ROLE.ADMIN
                           and Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.ADMIN_DASHBOARD, user_object=user,
                                             user=username, realm=realm).any())
        token_rollover = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.TOKENROLLOVER, user_object=user,
                                       user=username, realm=realm).action_values(unique=False)
        token_wizard = False
        dialog_no_token = False
        container_wizard = {"enabled": False}
        if role == ROLE.USER:
            user_token_num = get_tokens(user=user, count=True)
            token_wizard_pol = Match.user(g, scope=SCOPE.WEBUI, action=ACTION.TOKENWIZARD, user_object=user).any()
            # We also need to check, if the user has no tokens assigned.
            # If the user has no tokens, we run the wizard. If the user
            # already has tokens, we do not run the wizard.
            token_wizard = token_wizard_pol and (user_token_num == 0)

            dialog_no_token_pol = Match.user(g, scope=SCOPE.WEBUI, action=ACTION.DIALOG_NO_TOKEN,
                                             user_object=user).any()
            dialog_no_token = dialog_no_token_pol and (user_token_num == 0)
            # This only works for users, because the value of the policy does not change while logged in.
            if Match.user(g, SCOPE.USER, "indexedsecret_force_attribute", user).action_values(unique=False):
                content["result"]["value"]["indexedsecret_force_attribute"] = 1

            user_container = get_all_containers(user=user, page=1, pagesize=1)
            if user_container["count"] == 0:
                container_wizard_type_policy = Match.user(g, SCOPE.WEBUI, ACTION.CONTAINER_WIZARD_TYPE,
                                                          user_object=user).action_values(unique=True)
                if container_wizard_type_policy:
                    container_wizard_type = list(container_wizard_type_policy.keys())[0]
                    container_wizard_template_policy = Match.user(g, SCOPE.WEBUI, ACTION.CONTAINER_WIZARD_TEMPLATE,
                                                                  user_object=user).action_values(unique=True)
                    if container_wizard_template_policy:
                        template = list(container_wizard_template_policy.keys())[0]
                        # The template policy contains the name and the type: Extract only the name
                        container_wizard_template = template.split(f"({container_wizard_type})")[0]
                    else:
                        container_wizard_template = None
                    container_wizard_registration = Match.user(g, SCOPE.WEBUI,
                                                               ACTION.CONTAINER_WIZARD_REGISTRATION,
                                                               user_object=user).any()
                    container_wizard = {"enabled": True, "type": container_wizard_type,
                                        "template": container_wizard_template,
                                        "registration": container_wizard_registration}

        user_details_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.USERDETAILS, user_object=user,
                                         user=username, realm=realm).policies()
        search_on_enter = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SEARCH_ON_ENTER, user_object=user,
                                        user=username, realm=realm).policies()
        hide_welcome = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.HIDE_WELCOME, user_object=user,
                                     user=username, realm=realm).any()
        hide_buttons = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.HIDE_BUTTONS, user_object=user,
                                     user=username, realm=realm).any()
        deletion_confirmation = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.DELETION_CONFIRMATION,
                                              user_object=user, user=username, realm=realm).any()
        default_tokentype_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.DEFAULT_TOKENTYPE, user_object=user,
                                              user=username, realm=realm).action_values(unique=True)
        default_container_type_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.DEFAULT_CONTAINER_TYPE,
                                                   user_object=user, user=username,
                                                   realm=realm).action_values(unique=True)
        show_seed = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_SEED, user_object=user,
                                  user=username, realm=realm).any()
        show_node = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_NODE, realm=realm, user_object=user).any()
        qr_ios_authenticator = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_IOS_AUTHENTICATOR,
                                             user_object=user, user=username, realm=realm).any()
        qr_android_authenticator = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_ANDROID_AUTHENTICATOR,
                                                 user_object=user, user=username, realm=realm).any()
        qr_custom_authenticator_url = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_CUSTOM_AUTHENTICATOR,
                                                    user_object=user, user=username,
                                                    realm=realm).action_values(unique=True)
        logout_redirect_url_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.LOGOUT_REDIRECT, user_object=user,
                                                user=username, realm=realm).action_values(unique=True)
        require_description = Match.generic(g, scope=SCOPE.ENROLL, action=ACTION.REQUIRE_DESCRIPTION, user_object=user,
                                            user=username, realm=realm).action_values(unique=False)

        qr_image_android = create_img(DEFAULT_ANDROID_APP_URL) if qr_android_authenticator else None
        qr_image_ios = create_img(DEFAULT_IOS_APP_URL) if qr_ios_authenticator else None
        qr_image_custom = create_img(list(qr_custom_authenticator_url)[0]) if qr_custom_authenticator_url else None
        audit_page_size = DEFAULT_AUDIT_PAGE_SIZE
        token_page_size = DEFAULT_PAGE_SIZE
        user_page_size = DEFAULT_PAGE_SIZE
        require_description = list(require_description.keys())
        default_tokentype = DEFAULT_TOKENTYPE
        default_container_type = DEFAULT_CONTAINER_TYPE
        logout_redirect_url = ""
        if len(audit_page_size_pol) == 1:
            audit_page_size = int(list(audit_page_size_pol)[0])
        if len(token_page_size_pol) == 1:
            token_page_size = int(list(token_page_size_pol)[0])
        if len(user_page_size_pol) == 1:
            user_page_size = int(list(user_page_size_pol)[0])
        if len(default_tokentype_pol) == 1:
            default_tokentype = list(default_tokentype_pol)[0]
        if len(default_container_type_pol) == 1:
            default_container_type = list(default_container_type_pol)[0]
        if len(logout_redirect_url_pol) == 1:
            logout_redirect_url = list(logout_redirect_url_pol)[0]

        logout_time = DEFAULT_LOGOUT_TIME
        if len(logout_time_pol) == 1:
            logout_time = int(list(logout_time_pol)[0])

        timeout_action = DEFAULT_TIMEOUT_ACTION
        if len(timeout_action_pol) == 1:
            timeout_action = list(timeout_action_pol)[0]

        policy_template_url_pol = Match.action_only(g, scope=SCOPE.WEBUI,
                                                    action=ACTION.POLICYTEMPLATEURL).action_values(unique=True)
        policy_template_url = DEFAULT_POLICY_TEMPLATE_URL
        if len(policy_template_url_pol) == 1:
            policy_template_url = list(policy_template_url_pol)[0]

        indexed_preset_attribute = Match.realm(g, scope=SCOPE.WEBUI, action="indexedsecret_preset_attribute",
                                               realm=realm).action_values(unique=True)
        if len(indexed_preset_attribute) == 1:
            content["result"]["value"]["indexedsecret_preset_attribute"] = list(indexed_preset_attribute)[0]

        content["result"]["value"]["logout_time"] = logout_time
        content["result"]["value"]["audit_page_size"] = audit_page_size
        content["result"]["value"]["token_page_size"] = token_page_size
        content["result"]["value"]["user_page_size"] = user_page_size
        content["result"]["value"]["policy_template_url"] = policy_template_url
        content["result"]["value"]["default_tokentype"] = default_tokentype
        content["result"]["value"]["default_container_type"] = default_container_type
        content["result"]["value"]["user_details"] = len(user_details_pol) > 0
        content["result"]["value"]["token_wizard"] = token_wizard
        content["result"]["value"]["token_wizard_2nd"] = token_wizard_2nd
        content["result"]["value"]["admin_dashboard"] = admin_dashboard
        content["result"]["value"]["dialog_no_token"] = dialog_no_token
        content["result"]["value"]["search_on_enter"] = len(search_on_enter) > 0
        content["result"]["value"]["timeout_action"] = timeout_action
        content["result"]["value"]["token_rollover"] = token_rollover
        content["result"]["value"]["hide_welcome"] = hide_welcome
        content["result"]["value"]["hide_buttons"] = hide_buttons
        content["result"]["value"]["deletion_confirmation"] = deletion_confirmation
        content["result"]["value"]["show_seed"] = show_seed
        content["result"]["value"]["show_node"] = get_privacyidea_node() if show_node else ""
        content["result"]["value"]["subscription_status"] = subscription_status()
        content["result"]["value"]["subscription_status_push"] = subscription_status("privacyidea authenticator",
                                                                                     tokentype="push")
        content["result"]["value"]["qr_image_android"] = qr_image_android
        content["result"]["value"]["qr_image_ios"] = qr_image_ios
        content["result"]["value"]["qr_image_custom"] = qr_image_custom
        content["result"]["value"]["logout_redirect_url"] = logout_redirect_url
        content["result"]["value"]["require_description"] = require_description
        rss_age(request, None)
        content["result"]["value"]["rss_age"] = request.all_data.get("rss_age", FETCH_DAYS)
        content["result"]["value"]["container_wizard"] = container_wizard

        if role == ROLE.ADMIN:
            # Add a support mailto, for administrators with systemwrite rights.
            subscriptions = get_subscription("privacyidea")
            if len(subscriptions) == 1:
                subscription = subscriptions[0]
                version = get_version()
                subject = "Problem with {0!s}".format(version)
                try:
                    check_subscription("privacyidea")
                except SubscriptionError:
                    subject = EXPIRE_MESSAGE
                # Check policy, if the admin is allowed to save config
                action_allowed = Match.generic(g, scope=role,
                                               action=ACTION.SYSTEMWRITE,
                                               adminuser=username,
                                               adminrealm=realm).allowed()
                if action_allowed:
                    body = str(BODY_TEMPLATE).format(subscriptions=subscriptions,
                                                     version=version,
                                                     subscriber_name=subscription.get("for_name"))

                    body = quote(body)
                    content["result"]["value"]["supportmail"] = (f"mailto:{subscription.get('by_email')}?subject="
                                                                 f"{subject}&body={body}")
        response.set_data(json.dumps(content))
    return response


def autoassign(request, response):
    """
    This decorator decorates the function /validate/check.
    Depending on ACTION.AUTOASSIGN it checks if the user has no token and if
    the given OTP-value matches a token in the users realm, that is not yet
    assigned to any user.

    If a token can be found, it assigns the token to the user also taking
    into account ACTION.MAXTOKENUSER and ACTION.MAXTOKENREALM.
    :return:
    """
    content = response.json
    # check, if the authentication was successful, then we need to do nothing
    if content.get("result").get("value") is False:
        user = request.User
        # user_obj = get_user_from_param(request.all_data)
        password = request.all_data.get("pass", "")
        if user.login and user.realm:
            # If there is no user in the request (because it is a serial
            # authentication request) we immediately bail out
            # check if the policy is defined
            autoassign_values = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.AUTOASSIGN,
                                           user_object=user).action_values(unique=True, write_to_audit_log=False)
            # check if the user has no token
            if autoassign_values and get_tokens(user=user, count=True) == 0:
                # Check if the token would match
                # get all unassigned tokens in the realm and look for
                # a matching OTP:
                realm_tokens = get_tokens(realm=user.realm,
                                          assigned=False)

                for token in realm_tokens:
                    (res, pin, otp) = token.split_pin_pass(password)
                    if res:
                        pin_check = True
                        if list(autoassign_values)[0] == AUTOASSIGNVALUE.USERSTORE:
                            # If the autoassign policy is set to userstore, we need to check against the userstore.
                            pin_check = user.check_password(pin)
                        if pin_check:
                            otp_check = token.check_otp(otp)
                            if otp_check >= 0:
                                # we found a matching token, check MAXTOKENUSER and MAXTOKENREALM
                                check_max_token_user(request=request)
                                check_max_token_realm(request=request)
                                # Assign token
                                assign_token(serial=token.token.serial, user=user, pin=pin)
                                # Set the response to true
                                content.get("result")["value"] = True
                                # Set the serial number
                                detail = content.setdefault("detail", {})
                                detail["serial"] = token.token.serial
                                detail["otplen"] = token.token.otplen
                                detail["type"] = token.type
                                detail["message"] = "Token assigned to user via Autoassignment"
                                response.set_data(json.dumps(content))

                                g.audit_object.log(
                                    {"success": True,
                                     "info": "Token assigned via auto assignment",
                                     "serial": token.token.serial})
                                # The token was assigned by autoassign. We save the first policy name
                                g.audit_object.add_policy(next(iter(autoassign_values.values())))
                                break

    return response


def container_create_via_multichallenge(request: Request, content: dict, container_type: str) -> dict:
    """
    Checks if the user has no registered container of the given type. If not, the container is created and registration
    is initialized. The registration data is written to the response data as multi challenge.
    If the according policy is set, the container is created from a template.
    Any errors that could occur (template not found, max user tokens reached, missing registration policies) are only
    logged and the content is returned unchanged to not break the authentication flow.

    :param request: The request object
    :param content: The content of the response
    :param container_type: The type of the container to create (e.g., "smartphone")
    :return: The modified content with the registration data or unchanged content if no container was created
    """
    result = content.get("result")
    user = request.User
    containers = get_all_containers(user, ctype=container_type).get("containers")
    container = None
    container_already_exists = False
    template_tokens = None
    if len(containers) == 0:
        # User has no container of that type: create a new one
        # Check if a template should be used
        template_policies = Match.user(g, scope=SCOPE.AUTH, action=ACTION.ENROLL_VIA_MULTICHALLENGE_TEMPLATE,
                                       user_object=user).action_values(unique=True, write_to_audit_log=False)
        template_name = list(template_policies)[0] if template_policies else None

        init_result = init_container({"type": container_type, "user": user.login, "realm": user.realm,
                                      "template_name": template_name})
        template_tokens = init_result["template_tokens"]
        container_serial = init_result.get("container_serial")
        container = find_container_by_serial(container_serial)
        # Template tokens are created later to be sure that the registration policies are set. Otherwise, we would
        # create and afterward delete the tokens if the registration fails.
    elif len(containers) == 1:
        # If the user has exactly one smartphone container, we can (re)init the registration
        container = containers[0]
        container_already_exists = True
        registration_state = container.registration_state
        if registration_state not in [RegistrationState.NOT_REGISTERED, RegistrationState.CLIENT_WAIT]:
            # Container is already registered: nothing to do here
            container = None

    if container:
        # Get message
        message_policies = Match.user(g, scope=SCOPE.AUTH, action=ACTION.ENROLL_VIA_MULTICHALLENGE_TEXT,
                                      user_object=user).action_values(unique=True, write_to_audit_log=False,
                                                                      allow_white_space_in_action=True)
        message = _("Please scan the QR code to register the container.")
        if message_policies:
            message = list(message_policies)[0]
        # Registration
        # Get params from policies
        request.all_data["container_serial"] = container.serial
        try:
            # We can not check this policy earlier as the container serial is required
            container_registration_config(request)
        except PolicyError:
            log.debug("Missing container registration policy. Can not enroll container via multichallenge.")
            if not container_already_exists:
                # If a new container was created but the registration failed, we need to delete the container
                container.delete()
            return content

        # Create tokens from template
        if template_tokens:
            # Some token policies require the logged_in_user to be set
            g.logged_in_user = {"role": ROLE.USER, "username": user.login, "realm": user.realm,
                                "resolver": user.resolver}
            create_container_tokens_from_template(container.serial, template_tokens, request, ROLE.USER)
            del g.logged_in_user

        # Init registration
        server_url = request.all_data.get(SERVER_URL)
        challenge_ttl = request.all_data.get(CHALLENGE_TTL)
        registration_ttl = request.all_data.get(REGISTRATION_TTL)
        ssl_verify = request.all_data.get(SSL_VERIFY)
        res = init_registration(container, False, server_url, registration_ttl, ssl_verify, challenge_ttl,
                                request.all_data)
        challenge = get_challenges(container.serial, transaction_id=res["transaction_id"])[0]
        challenge.session = CHALLENGE_SESSION.ENROLLMENT
        challenge.save()

        # Write registration info to the response
        detail = content.setdefault("detail", {})
        challenge_data = {"serial": container.serial, "type": container_type,
                          "message": message,
                          "image": res["container_url"]["img"],
                          "link": res["container_url"]["value"],
                          "client_mode": "poll",
                          "transaction_id": res["transaction_id"]}
        detail["multi_challenge"] = [challenge_data]
        detail.update(challenge_data)
        # Change result to challenge
        result["value"] = False
        result["authentication"] = AUTH_RESPONSE.CHALLENGE
    return content


def multichallenge_enroll_via_validate(request, response):
    """
    This is a post decorator to allow enrolling tokens via /validate/check.
    It checks the AUTH policy ENROLL_VIA_MULTICHALLENGE and enrolls the
    corresponding token type.
    It also modifies the response accordingly, so that the client/plugin can
    display necessary data for the enrollment to the user.

    :param request:
    :param response:
    :return:
    """
    content = response.json
    result = content.get("result")
    # Check if the authentication was successful, only then attempt to enroll a new token
    if not result.get("value") or result.get("authentication") != AUTH_RESPONSE.ACCEPT:
        # Authentication was not successful, so we do not enroll a token
        return response

    user = request.User
    if not user.login or not user.realm:
        return response

    # Check if we have a policy to enroll a token and which type
    enroll_policies = Match.user(g, scope=SCOPE.AUTH, action=ACTION.ENROLL_VIA_MULTICHALLENGE,
                                 user_object=user).action_values(unique=True, write_to_audit_log=False)
    if not enroll_policies:
        # No policy to enroll a token via multichallenge, so we do nothing
        return response

    # Check if the type is a valid multichallenge enrollable type
    enroll_type = list(enroll_policies)[0]
    enroll_type = enroll_type.lower()
    if enroll_type not in get_multichallenge_enrollable_types():
        return response

    if enroll_type == "smartphone":
        content = container_create_via_multichallenge(request, content, enroll_type)
    else:
        tokentype = enroll_type
        # Check if the user already has a token of the type that should be enrolled
        # If so, do not enroll another one
        if len(get_tokens(tokentype=tokentype, user=user)) == 0:
            # Check if another policy restricts the token count and exit early if true
            try:
                check_max_token_user(request=request)
                check_max_token_realm(request=request)
            except PolicyError as e:
                g.audit_object.log({"success": True, "action_detail": f"{e}"})
                return response

            # Now get the alternative text from the policies
            text_policies = Match.user(g, scope=SCOPE.AUTH,
                                       action=ACTION.ENROLL_VIA_MULTICHALLENGE_TEXT,
                                       user_object=user).action_values(unique=True,
                                                                       write_to_audit_log=False,
                                                                       allow_white_space_in_action=True)
            message = None
            if text_policies:
                message = list(text_policies)[0]
            # -----------------------------
            # TODO this is not perfect yet, but the improved implementation of enroll_via_validate
            # TODO should go in this direction instead of putting the stuff in the token class
            if tokentype == PasskeyTokenClass.get_class_type().lower():
                request.all_data["type"] = tokentype
                fido2_enroll(request, None)
                token = init_token(request.all_data, user)
                try:
                    init_details = token.get_init_detail(request.all_data, user)
                    if not init_details:
                        token.token.delete()
                    content.get("result")["value"] = False
                    content.get("result")["authentication"] = AUTH_RESPONSE.CHALLENGE
                    detail = content.setdefault("detail", {})
                    detail["transaction_id"] = init_details["transaction_id"]
                    detail["transaction_ids"] = [init_details["transaction_id"]]
                    detail["multi_challenge"] = [init_details]
                    detail["serial"] = token.token.serial
                    detail["type"] = tokentype
                    detail.pop("otplen", None)
                    detail["message"] = PasskeyTokenClass.get_default_challenge_text_register()
                    detail["client_mode"] = "webauthn"
                except Exception as e:
                    log.error(f"Error during enroll_via_validate: {e}")
                    token.token.delete()
                    raise e
            # ------------------------------
            else:
                tokenclass = get_token_class(tokentype)
                tokenclass.enroll_via_validate(g, content, user, message)
    response.set_data(json.dumps(content))

    return response


def construct_radius_response(request, response):
    """
    This decorator implements the /validate/radiuscheck endpoint.
    In case this URL was requested, a successful authentication
    results in an empty response with a HTTP 204 status code.
    An unsuccessful authentication results in an empty response
    with a HTTP 400 status code.

    This needs to be the last decorator, since the JSON response is then lost.

    :return:
    """
    if request.url_rule.rule == '/validate/radiuscheck':
        return_code = 400  # generic 400 error by default
        if response.json['result']['status']:
            if response.json['result']['value']:
                # user was successfully authenticated
                return_code = 204
        # send empty body
        resp = make_response('', return_code)
        # tell other policies there is no JSON content
        resp.mimetype = 'text/plain'
        return resp
    else:
        return response


def mangle_challenge_response(request, response):
    """
    This policy decorator is used in the AUTH scope to
    decorate the /validate/check endpoint.
    It can modify the contents of the response "detail"->"message"
    to allow a better readability for a challenge response text.

    :param request:
    :param response:
    :return:
    """
    if not response.is_json:
        # This can happen with the validate/radiuscheck endpoint
        return response
    content = response.json
    user_obj = request.User

    header_pol = Match.user(g, scope=SCOPE.AUTH, action=ACTION.CHALLENGETEXT_HEADER,
                            user_object=user_obj).action_values(unique=True, allow_white_space_in_action=True)
    footer_pol = Match.user(g, scope=SCOPE.AUTH, action=ACTION.CHALLENGETEXT_FOOTER,
                            user_object=user_obj).action_values(unique=True, allow_white_space_in_action=True)
    if header_pol:
        multi_challenge = content.get("detail", {}).get("multi_challenge")
        if multi_challenge:
            message = list(header_pol)[0]
            footer = ""
            if footer_pol:
                footer = list(footer_pol)[0]
            # We actually have challenge response
            messages = content.get("detail", {}).get("messages") or []
            messages = sorted(set(messages))
            if message[-4:].lower() in ["<ol>", "<ul>"]:
                for m in messages:
                    message += "<li>{0!s}</li>\n".format(m)
            else:
                message += "\n"
                message += ", ".join(messages)
                message += "\n"
            # Add the footer
            message += footer

            content["detail"]["message"] = message
            response.set_data(json.dumps(content))

    return response


def is_authorized(request, response):
    """
    This policy decorator is used in the AUTHZ scope to
    decorate the /validate/check and /validate/triggerchallenge endpoint.
    It will cause authentication to fail, if the policy
    authorized=deny_access is set.

    :param request:
    :param response:
    :return:
    """
    if not response.is_json:
        # This can happen with the validate/radiuscheck endpoint
        return response

    authorized_pol = Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.AUTHORIZED,
                                user_object=request.User).action_values(unique=True, allow_white_space_in_action=True)

    if authorized_pol:
        if list(authorized_pol)[0] == AUTHORIZED.DENY:
            raise ValidateError("User is not authorized to authenticate under these conditions.")

    return response


def check_verify_enrollment(request, response):
    """
    This policy decorator is used in the ENROLL scope to
    decorate the /token/init
    It will check for action=verify_enrollment and ask the user
    in a 2nd step to provide information to verify, that the token was successfully enrolled.

    :param request:
    :param response:
    :return:
    """
    serial = response.json.get("detail", {}).get("serial")
    if not serial:
        log.info("No serial number found in response. Can not do check_verify_enrollment.")
        return response

    verify = request.all_data.get("verify")
    two_step = request.all_data.get("2stepinit")
    if verify or two_step:
        # In case we are in the 2nd step of verification or 2step-enrollment, we must exit early
        return response
    tokens = get_tokens(serial=serial)
    if len(tokens) == 1:
        token = tokens[0]
        # check if this token type can do verify enrollment
        if token.can_verify_enrollment:
            # Get policies
            verify_pol_dict = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.VERIFY_ENROLLMENT,
                                         user_object=request.User).action_values(unique=False,
                                                                                 allow_white_space_in_action=True,
                                                                                 write_to_audit_log=False)
            # verify_pol_dict.keys() is a list of actions from several policies. It could look like this:
            # ["hotp totp", "hotp email"]
            # The key is the token type(s)
            do_verify_enrollment = False
            for policy_key in verify_pol_dict:
                if token.get_tokentype().upper() in [x.upper() for x in policy_key.split(" ")]:
                    # This token is supposed to do verify enrollment
                    do_verify_enrollment = True
                    g.audit_object.add_policy(verify_pol_dict.get(policy_key))
            if do_verify_enrollment:
                content = response.json
                options = {"g": g, "user": request.User, "exception": request.all_data.get("exception", 0)}
                content["detail"]["verify"] = token.prepare_verify_enrollment(options=options)
                content["detail"]["rollout_state"] = ROLLOUTSTATE.VERIFYPENDING
                token.token.rollout_state = ROLLOUTSTATE.VERIFYPENDING
                token.token.save()
                response.set_data(json.dumps(content))
    else:
        log.warning("No distinct token object found in enrollment response!")

    return response
