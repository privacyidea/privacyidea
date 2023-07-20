# -*- coding: utf-8 -*-
#
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
import datetime
import logging
import traceback
from privacyidea.lib.error import PolicyError, ValidateError
from flask import g, current_app, make_response
from privacyidea.lib.policy import SCOPE, ACTION, AUTOASSIGNVALUE, AUTHORIZED
from privacyidea.lib.policy import DEFAULT_ANDROID_APP_URL, DEFAULT_IOS_APP_URL
from privacyidea.lib.policy import DEFAULT_PREFERRED_CLIENT_MODE_LIST
from privacyidea.lib.policy import Match
from privacyidea.lib.token import get_tokens, assign_token, get_realms_of_token, get_one_token
from privacyidea.lib.machine import get_auth_items
from privacyidea.lib.config import get_multichallenge_enrollable_tokentypes, get_token_class
from .prepolicy import check_max_token_user, check_max_token_realm
import functools
import json
import re
import netaddr
from privacyidea.lib.crypto import Sign
from privacyidea.api.lib.utils import get_all_params
from privacyidea.lib.auth import ROLE
from privacyidea.lib.user import User
from privacyidea.lib.realm import get_default_realm
from privacyidea.lib.subscriptions import subscription_status
from privacyidea.lib.utils import create_img
from privacyidea.lib.config import get_privacyidea_node
from privacyidea.lib.tokenclass import ROLLOUTSTATE

log = logging.getLogger(__name__)

optional = True
required = False
DEFAULT_LOGOUT_TIME = 120
DEFAULT_AUDIT_PAGE_SIZE = 10
DEFAULT_PAGE_SIZE = 15
DEFAULT_TOKENTYPE = "hotp"
DEFAULT_TIMEOUT_ACTION = "lockscreeen"
DEFAULT_POLICY_TEMPLATE_URL = "https://raw.githubusercontent.com/privacyidea/" \
                              "policy-templates/master/templates/"


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

    The usual way to use it is, to wrap the after_request, so that we can also
    sign errors.

    @postrequest(sign_response, request=request)
    def after_request(response):

    :param request: The Request object
    :param response: The Response object
    """
    if current_app.config.get("PI_NO_RESPONSE_SIGN"):
        return response

    priv_file_name = current_app.config.get("PI_AUDIT_KEY_PRIVATE")

    # Disable the costly checking of private RSA keys when loading them.
    check_private_key = not current_app.config.get("PI_RESPONSE_NO_PRIVATE_KEY_CHECK", False)
    try:
        with open(priv_file_name, 'rb') as priv_file:
            priv_key = priv_file.read()
        sign_object = Sign(priv_key, public_key=None,
                           check_private_key=check_private_key)
    except (IOError, ValueError, TypeError) as e:
        log.info('Could not load private key from '
                 'file {0!s}: {1!r}!'.format(priv_file_name, e))
        log.debug(traceback.format_exc())
        return response

    request.all_data = get_all_params(request)
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

    :param response: The response of the decorated function
    :type response: Response object
    :return: A new (maybe modified) response
    """
    tokentype = response.json.get("detail", {}).get("type")
    user_object = request.User
    allowed_tokentypes = Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.TOKENTYPE,
                                    user_object=user_object).action_values(unique=False)
    if tokentype and allowed_tokentypes and tokentype not in allowed_tokentypes:
        # If we have tokentype policies, but
        # the tokentype is not allowed, we raise an exception
        g.audit_object.log({"success": False,
                            'action_detail': "Tokentype {0!r} not allowed for "
                                             "authentication".format(tokentype)})
        raise PolicyError("Tokentype not allowed for authentication!")
    return response


def check_serial(request, response):
    """
    This policy function is to be used in a decorator of an API function.
    It checks, if the token, that was used in the API call has a serial
    number that is allowed to be used.

    If not, a PolicyException is raised.

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

    :param response: The response of the decorated function
    :type response: Response object
    :return: A new modified response
    """
    serial = response.json.get("detail", {}).get("serial")

    if serial:
        tokeninfos_pol = Match.action_only(g, scope=SCOPE.AUTHZ, action=ACTION.TOKENINFO)\
            .action_values(unique=False, allow_white_space_in_action=True)
        if tokeninfos_pol:
            tokens = get_tokens(serial=serial)
            if len(tokens) == 1:
                token_obj = tokens[0]
                for tokeninfo_pol in tokeninfos_pol:
                    try:
                        key, regex, _r = tokeninfo_pol.split("/")
                        value = token_obj.get_tokeninfo(key, "")
                        if re.search(regex, value):
                            log.debug("Regular expression {0!s} "
                                      "matches the tokeninfo field {1!s}.".format(regex, key))
                        else:
                            log.info("Tokeninfo field {0!s} with contents {1!s} "
                                     "does not match {2!s}".format(key, value, regex))
                            raise PolicyError("Tokeninfo field {0!s} with contents does not"
                                              " match regular expression.".format(key))
                    except ValueError:
                        log.warning("invalid tokeinfo policy: {0!s}".format(tokeninfo_pol))

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
    detailPol = Match.action_only(g, scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS)\
        .policies(write_to_audit_log=False)
    if detailPol and content.get("result", {}).get("value"):
        # The policy was set, we need to strip the details, if the
        # authentication was successful. (value=true)
        # None assures that we do not get an error, if "detail" does not exist.
        content.pop("detail", None)
        response.set_data(json.dumps(content))
        g.audit_object.add_policy([p.get("name") for p in detailPol])

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
    user_object = request.User

    # get the preferred client mode from a policy definition
    detail_pol = Match.user(g, scope=SCOPE.AUTH, action=ACTION.PREFERREDCLIENTMODE, user_object=user_object)\
        .action_values(allow_white_space_in_action=True, unique=True)

    if detail_pol:
        # Split at whitespaces and strip
        preferred_client_mode_list = str.split(list(detail_pol)[0])
    else:
        preferred_client_mode_list = DEFAULT_PREFERRED_CLIENT_MODE_LIST
    if content.get("detail"):
        detail = content.get("detail")
        if detail.get("multi_challenge"):
            multi_challenge = detail.get("multi_challenge")
            client_modes = [x.get('client_mode') for x in multi_challenge]

            try:
                preferred = [x for x in preferred_client_mode_list if x in client_modes][0]
                content.setdefault("detail", {})["preferred_client_mode"] = preferred
            except IndexError as err:
                content.setdefault("detail", {})["preferred_client_mode"] = 'interactive'
                log.error('There was no acceptable client mode in the multi-challenge list. '
                          'The preferred client mode is set to "interactive". '
                          'Please check Your policy ({0!s}). '
                          'Error: {1!s} '.format(preferred_client_mode_list, err))
            except Exception as err:  # pragma no cover
                content.setdefault("detail", {})["preferred_client_mode"] = 'interactive'
                log.error('Something went wrong during setting the preferred '
                          'client mode. Error: {0!s}'.format(err))

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
    detail_pol = Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.ADDUSERINRESPONSE, user_object=request.User)\
        .policies(write_to_audit_log=False)
    if detail_pol and content.get("result", {}).get("value") and request.User:
        # The policy was set, we need to add the user
        #  details
        ui = request.User.info.copy()
        ui["password"] = ""  # nosec B105 # Hide a potential password
        for key, value in ui.items():
            if type(value) == datetime.datetime:
                ui[key] = str(value)
        content.setdefault("detail", {})["user"] = ui
        g.audit_object.add_policy([p.get("name") for p in detail_pol])

    # Check for ADD RESOLVER IN RESPONSE
    detail_pol = Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.ADDRESOLVERINRESPONSE, user_object=request.User)\
        .policies(write_to_audit_log=False)
    if detail_pol and content.get("result", {}).get("value") and request.User:
        # The policy was set, we need to add the resolver and the realm
        content.setdefault("detail", {})["user-resolver"] = request.User.resolver
        content["detail"]["user-realm"] = request.User.realm
        g.audit_object.add_policy([p.get("name") for p in detail_pol])

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
    detailPol = Match.action_only(g, scope=SCOPE.AUTHZ, action=ACTION.NODETAILFAIL).policies(write_to_audit_log=False)
    if detailPol and content.get("result", {}).get("value") is False:
        # The policy was set, we need to strip the details, if the
        # authentication was successful. (value=true)
        del content["detail"]
        response.set_data(json.dumps(content))
        g.audit_object.add_policy([p.get("name") for p in detailPol])

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
    :param action:
    :return:
    """
    policy_object = g.policy_object
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
            pinpol = Match.realm(g, scope=SCOPE.ENROLL, action=ACTION.CHANGE_PIN_FIRST_USE,
                                 realm=realm).policies()
            if pinpol:
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

                # If there is a change_pin_every policy, we need to set the PIN
                # anew.
                pinpol = Match.realm(g, scope=SCOPE.ENROLL, action=ACTION.CHANGE_PIN_EVERY,
                                     realm=realm).action_values(unique=True)
                if pinpol:
                    token = get_one_token(serial=serial)
                    token.set_next_pin_change(diff=list(pinpol)[0])

    # we do not modify the response!
    return response


def offline_info(request, response):
    """
    This decorator is used with the function /validate/check.
    It is not triggered by an ordinary policy but by a MachineToken definition.
    If for the given Token an offline application is defined,
    the response is enhanced with the offline information - the hashes of the
    OTP.

    """
    content = response.json
    # check if the authentication was successful
    if content.get("result").get("value") is True and g.client_ip:
        # check if there is a MachineToken definition
        serial = content.get("detail", {}).get("serial")
        if serial:
            try:
                auth_items = get_auth_items(serial=serial, application="offline",
                                            challenge=request.all_data.get("pass"))
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
    # check, if the authentication was successful, then we need to do nothing
    if content.get("result").get("status") is True:
        role = content.get("result").get("value").get("role")
        loginname = content.get("result").get("value").get("username")
        realm = content.get("result").get("value").get("realm") or get_default_realm()

        # At this point the logged in user is not necessarily a user object. It can
        # also be a local admin.
        logout_time_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.LOGOUTTIME,
                                        user=loginname, realm=realm).action_values(unique=True)
        timeout_action_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.TIMEOUT_ACTION,
                                           user=loginname, realm=realm).action_values(unique=True)
        audit_page_size_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.AUDITPAGESIZE,
                                            user=loginname, realm=realm).action_values(unique=True)
        token_page_size_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.TOKENPAGESIZE,
                                            user=loginname, realm=realm).action_values(unique=True)
        user_page_size_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.USERPAGESIZE,
                                           user=loginname, realm=realm).action_values(unique=True)
        token_wizard_2nd = bool(role == ROLE.USER
                                and Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.TOKENWIZARD2ND,
                                                  user=loginname, realm=realm).policies())
        admin_dashboard = (role == ROLE.ADMIN
                           and Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.ADMIN_DASHBOARD,
                                             user=loginname, realm=realm).any())
        token_rollover = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.TOKENROLLOVER,
                                       user=loginname, realm=realm).action_values(unique=False)
        token_wizard = False
        dialog_no_token = False
        if role == ROLE.USER:
            user_obj = User(loginname, realm)
            user_token_num = get_tokens(user=user_obj, count=True)
            token_wizard_pol = Match.user(g, scope=SCOPE.WEBUI, action=ACTION.TOKENWIZARD, user_object=user_obj).any()
            # We also need to check, if the user has not tokens assigned.
            # If the user has no tokens, we run the wizard. If the user
            # already has tokens, we do not run the wizard.
            token_wizard = token_wizard_pol and (user_token_num == 0)

            dialog_no_token_pol = Match.user(g, scope=SCOPE.WEBUI, action=ACTION.DIALOG_NO_TOKEN,
                                             user_object=user_obj).any()
            dialog_no_token = dialog_no_token_pol and (user_token_num == 0)
        user_details_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.USERDETAILS,
                                         user=loginname, realm=realm).policies()
        search_on_enter = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SEARCH_ON_ENTER,
                                        user=loginname, realm=realm).policies()
        hide_welcome = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.HIDE_WELCOME,
                                     user=loginname, realm=realm).any()
        hide_buttons = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.HIDE_BUTTONS,
                                     user=loginname, realm=realm).any()
        deletion_confirmation = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.DELETION_CONFIRMATION,
                                     user=loginname, realm=realm).any()
        default_tokentype_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.DEFAULT_TOKENTYPE,
                                              user=loginname, realm=realm).action_values(unique=True)
        show_seed = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_SEED,
                                  user=loginname, realm=realm).any()
        show_node = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_NODE, realm=realm).any()
        qr_ios_authenticator = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_IOS_AUTHENTICATOR,
                                             user=loginname, realm=realm).any()
        qr_android_authenticator = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_ANDROID_AUTHENTICATOR,
                                                 user=loginname, realm=realm).any()
        qr_custom_authenticator_url = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.SHOW_CUSTOM_AUTHENTICATOR,
                                                    user=loginname, realm=realm).action_values(unique=True)
        logout_redirect_url_pol = Match.generic(g, scope=SCOPE.WEBUI, action=ACTION.LOGOUT_REDIRECT,
                                                user=loginname, realm=realm).action_values(unique=True)
        require_description = Match.generic(g, scope=SCOPE.ENROLL, action=ACTION.REQUIRE_DESCRIPTION,
                                            user=loginname, realm=realm).action_values(unique=False)

        qr_image_android = create_img(DEFAULT_ANDROID_APP_URL) if qr_android_authenticator else None
        qr_image_ios = create_img(DEFAULT_IOS_APP_URL) if qr_ios_authenticator else None
        qr_image_custom = create_img(list(qr_custom_authenticator_url)[0]) if qr_custom_authenticator_url else None
        audit_page_size = DEFAULT_AUDIT_PAGE_SIZE
        token_page_size = DEFAULT_PAGE_SIZE
        user_page_size = DEFAULT_PAGE_SIZE
        require_description = list(require_description.keys())
        default_tokentype = DEFAULT_TOKENTYPE
        logout_redirect_url = ""
        if len(audit_page_size_pol) == 1:
            audit_page_size = int(list(audit_page_size_pol)[0])
        if len(token_page_size_pol) == 1:
            token_page_size = int(list(token_page_size_pol)[0])
        if len(user_page_size_pol) == 1:
            user_page_size = int(list(user_page_size_pol)[0])
        if len(default_tokentype_pol) == 1:
            default_tokentype = list(default_tokentype_pol)[0]
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

        # This only works for users, because the value of the policy does not change while logged in.
        if role == ROLE.USER and \
                Match.user(g, SCOPE.USER, "indexedsecret_force_attribute", user_obj).action_values(unique=False):
            content["result"]["value"]["indexedsecret_force_attribute"] = 1

        content["result"]["value"]["logout_time"] = logout_time
        content["result"]["value"]["audit_page_size"] = audit_page_size
        content["result"]["value"]["token_page_size"] = token_page_size
        content["result"]["value"]["user_page_size"] = user_page_size
        content["result"]["value"]["policy_template_url"] = policy_template_url
        content["result"]["value"]["default_tokentype"] = default_tokentype
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
        user_obj = request.User
        #user_obj = get_user_from_param(request.all_data)
        password = request.all_data.get("pass", "")
        if user_obj.login and user_obj.realm:
            # If there is no user in the request (because it is a serial
            # authentication request) we immediately bail out
            # check if the policy is defined
            autoassign_values = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.AUTOASSIGN,
                                           user_object=user_obj).action_values(unique=True, write_to_audit_log=False)
            # check if the user has no token
            if autoassign_values and get_tokens(user=user_obj, count=True) == 0:
                # Check if the token would match
                # get all unassigned tokens in the realm and look for
                # a matching OTP:
                realm_tokens = get_tokens(realm=user_obj.realm,
                                          assigned=False)

                for token_obj in realm_tokens:
                    (res, pin, otp) = token_obj.split_pin_pass(password)
                    if res:
                        pin_check = True
                        if list(autoassign_values)[0] == \
                                AUTOASSIGNVALUE.USERSTORE:
                            # If the autoassign policy is set to userstore,
                            # we need to check against the userstore.
                            pin_check = user_obj.check_password(pin)
                        if pin_check:
                            otp_check = token_obj.check_otp(otp)
                            if otp_check >= 0:
                                # we found a matching token
                                #    check MAXTOKENUSER and MAXTOKENREALM
                                check_max_token_user(request=request)
                                check_max_token_realm(request=request)
                                #    Assign token
                                assign_token(serial=token_obj.token.serial,
                                             user=user_obj, pin=pin)
                                # Set the response to true
                                content.get("result")["value"] = True
                                # Set the serial number
                                detail = content.setdefault("detail", {})
                                detail["serial"] = token_obj.token.serial
                                detail["otplen"] = token_obj.token.otplen
                                detail["type"] = token_obj.type
                                detail["message"] = "Token assigned to user via Autoassignment"
                                response.set_data(json.dumps(content))

                                g.audit_object.log(
                                    {"success": True,
                                     "info":
                                         "Token assigned via auto assignment",
                                     "serial": token_obj.token.serial})
                                # The token was assigned by autoassign. We save the first policy name
                                g.audit_object.add_policy(next(iter(autoassign_values.values())))
                                break

    return response


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
    # check, if the authentication was successful, then we need to do nothing
    result = content.get("result")
    if result.get("value") and result.get("authentication") == "ACCEPT":
        user_obj = request.User
        if user_obj.login and user_obj.realm:
            enroll_pol = Match.user(g, scope=SCOPE.AUTH, action=ACTION.ENROLL_VIA_MULTICHALLENGE,
                                    user_object=user_obj).action_values(unique=True, write_to_audit_log=False)
            # check if we have a multi enroll policy
            if enroll_pol:
                tokentype = list(enroll_pol)[0]
                # TODO: Somehow we need to add condition, when we should stop enrolling!
                #       Here: If the user has one token of this type.
                if len(get_tokens(tokentype=tokentype, user=user_obj)) == 0:
                    if tokentype.lower() in get_multichallenge_enrollable_tokentypes():
                        tclass = get_token_class(tokentype)
                        tclass.enroll_via_validate(g, content, user_obj)
                        response.set_data(json.dumps(content))

    return response


def construct_radius_response(request, response):
    """
    This decorator implements the /validate/radiuscheck endpoint.
    In case this URL was requested, a successful authentication
    results in an empty response with a HTTP 204 status code.
    An unsuccessful authentication results in an empty response
    with a HTTP 400 status code.
    :return:
    """
    if request.url_rule.rule == '/validate/radiuscheck':
        return_code = 400 # generic 400 error by default
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
    serial = response.json.get("detail").get("serial")
    verify = request.all_data.get("verify")
    if verify:
        # In case we are in a 2nd step verification, we must early exit
        return response
    tokenobj_list = get_tokens(serial=serial)
    if len(tokenobj_list) == 1:
        tokenobj = tokenobj_list[0]
        # check if this token type can do verify enrollment
        if tokenobj.can_verify_enrollment:
            # Get policies
            verify_pol_dict = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.VERIFY_ENROLLMENT,
                                         user_object=request.User).action_values(unique=False,
                                                                                 allow_white_space_in_action=True,
                                                                                 write_to_audit_log=False)
            # verify_pol_dict.keys() is a list of actions from several policies. It
            # could look like this:
            # ["hotp totp", "hotp email"]
            do_verify_enrollment = False
            for toks in verify_pol_dict:
                if tokenobj.get_tokentype().upper() in [x.upper() for x in toks.split(" ")]:
                    # This token is supposed to do verify enrollment
                    do_verify_enrollment = True
                    g.audit_object.add_policy(verify_pol_dict.get(toks))
            if do_verify_enrollment:
                content = response.json
                content["detail"]["verify"] = tokenobj.prepare_verify_enrollment()
                content["detail"]["rollout_state"] = ROLLOUTSTATE.VERIFYPENDING
                tokenobj.token.rollout_state = ROLLOUTSTATE.VERIFYPENDING
                tokenobj.token.save()
                response.set_data(json.dumps(content))
    else:
        log.warning("No distinct token object found in enrollment response!")

    return response
