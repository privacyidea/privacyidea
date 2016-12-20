# -*- coding: utf-8 -*-
#
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
log = logging.getLogger(__name__)
from privacyidea.lib.error import PolicyError
from flask import g, current_app
from privacyidea.lib.policy import SCOPE, ACTION, AUTOASSIGNVALUE
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.token import get_tokens, assign_token, get_realms_of_token
from privacyidea.lib.machine import get_hostname, get_auth_items
from .prepolicy import check_max_token_user, check_max_token_realm
import functools
import json
import re
import netaddr
from privacyidea.lib.crypto import Sign
from privacyidea.api.lib.utils import get_all_params
from privacyidea.lib.auth import ROLE
from privacyidea.lib.user import (split_user, User)
from privacyidea.lib.realm import get_default_realm


optional = True
required = False
DEFAULT_LOGOUT_TIME = 120
DEFAULT_PAGE_SIZE = 15
DEFAULT_TOKENTYPE = "hotp"
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
    request, if it exist and adds the nonce and the signature to the response.

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

    priv_file = current_app.config.get("PI_AUDIT_KEY_PRIVATE")
    pub_file = current_app.config.get("PI_AUDIT_KEY_PUBLIC")
    sign_object = Sign(priv_file, pub_file)
    request.all_data = get_all_params(request.values, request.data)
    # response can be either a Response object or a Tuple (Response, ErrorID)
    response_value = 200
    response_is_tuple = False
    if type(response).__name__ == "tuple":
        response_is_tuple = True
        response_value = response[1]
        response_object = response[0]
    else:
        response_object = response
    try:
        content = json.loads(response_object.data)
        nonce = request.all_data.get("nonce")
        if nonce:
            content["nonce"] = nonce

        content["signature"] = sign_object.sign(json.dumps(content))
        response_object.data = json.dumps(content)
    except ValueError:
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
    content = json.loads(response.data)
    tokentype = content.get("detail", {}).get("type")
    policy_object = g.policy_object
    user_object = request.User
    allowed_tokentypes = policy_object.get_action_values(
        "tokentype",
        scope=SCOPE.AUTHZ,
        user=user_object.login,
        resolver=user_object.resolver,
        realm=user_object.realm,
        client=g.client_ip)
    if tokentype and allowed_tokentypes and tokentype not in allowed_tokentypes:
        g.audit_object.log({"success": False,
                            'action_detail': "Tokentype not allowed for "
                                             "authentication"})
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
    content = json.loads(response.data)
    policy_object = g.policy_object
    serial = content.get("detail", {}).get("serial")
    # get the serials from a policy definition
    allowed_serials = policy_object.get_action_values("serial",
                                                    scope=SCOPE.AUTHZ,
                                                    client=g.client_ip)

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
    content = json.loads(response.data)
    policy_object = g.policy_object

    # get the serials from a policy definition
    detailPol = policy_object.get_policies(action=ACTION.NODETAILSUCCESS,
                                           scope=SCOPE.AUTHZ,
                                           client=g.client_ip,
                                           active=True)

    if detailPol and content.get("result", {}).get("value"):
        # The policy was set, we need to strip the details, if the
        # authentication was successful. (value=true)
        del content["detail"]
        response.data = json.dumps(content)

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
    content = json.loads(response.data)
    policy_object = g.policy_object

    detail_pol = policy_object.get_policies(action=ACTION.ADDUSERINRESPONSE,
                                           scope=SCOPE.AUTHZ,
                                           client=g.client_ip,
                                           active=True)

    if detail_pol and content.get("result", {}).get("value") and request.User:
        # The policy was set, we need to add the user
        #  details
        ui = request.User.info
        ui["password"] = ""
        for key, value in ui.iteritems():
            if type(value) == datetime.datetime:
                ui[key] = str(value)
        content["detail"]["user"] = ui
        response.data = json.dumps(content)

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
    content = json.loads(response.data)
    policy_object = g.policy_object

    # get the serials from a policy definition
    detailPol = policy_object.get_policies(action=ACTION.NODETAILFAIL,
                                           scope=SCOPE.AUTHZ,
                                           client=g.client_ip,
                                           active=True)

    if detailPol and content.get("result", {}).get("value") is False:
        # The policy was set, we need to strip the details, if the
        # authentication was successful. (value=true)
        del content["detail"]
        response.data = json.dumps(content)

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
    content = json.loads(response.data)
    policy_object = g.policy_object
    serial = serial or request.all_data.get("serial")
    if not serial:
        # No serial in request, so we look into the response
        serial = content.get("detail", {}).get("serial")
    if not serial:
        log.error("Can not determine serial number. Have no idea of any "
                  "realm!")
    else:
        # Determine the realm by the serial
        realm = get_realms_of_token(serial, only_first_realm=True)
        realm = realm or get_default_realm()

        if g.logged_in_user.get("role") == ROLE.ADMIN:
            pinpol = policy_object.get_policies(action=ACTION.CHANGE_PIN_FIRST_USE,
                                                scope=SCOPE.ENROLL, realm=realm,
                                                client=g.client_ip, active=True)
            if pinpol:
                token = get_tokens(serial=serial)[0]
                token.set_next_pin_change(diff="0d")

        elif g.logged_in_user.get("role") == ROLE.USER:
            # Check for parameter "pin" or "otppin".
            otppin = request.all_data.get("otppin")
            pin = request.all_data.get("pin")
            # The user sets a pin or enrolls a token. -> delete the pin_change
            if otppin or pin:
                token = get_tokens(serial=serial)[0]
                token.del_tokeninfo("next_pin_change")

                # If there is a change_pin_every policy, we need to set the PIN
                # anew.
                pinpol = policy_object.get_action_values(
                    ACTION.CHANGE_PIN_EVERY, scope=SCOPE.ENROLL,
                    realm=realm, client=g.client_ip, unique=True)
                if pinpol:
                    token = get_tokens(serial=serial)[0]
                    token.set_next_pin_change(diff=pinpol[0])

    # we do not modify the response!
    return response


def offline_info(request, response):
    """
    This decorator is used with the function /validate/check.
    It is not triggered by an ordinary policy but by a MachineToken definition.
    If for the given Client and Token an offline application is defined,
    the response is enhanced with the offline information - the hashes of the
    OTP.

    """
    content = json.loads(response.data)
    # check if the authentication was successful
    if content.get("result").get("value") is True and g.client_ip:
        # If there is no remote address, we can not determine
        # offline information
        client_ip = netaddr.IPAddress(g.client_ip)
        # check if there is a MachineToken definition
        detail = content.get("detail", {})
        serial = detail.get("serial")
        try:
            # if the hostname can not be identified, there might be no
            # offline definition!
            hostname = get_hostname(ip=client_ip)
            auth_items = get_auth_items(hostname=hostname, ip=client_ip,
                                        serial=serial, application="offline",
                                        challenge=request.all_data.get("pass"))
            if auth_items:
                content["auth_items"] = auth_items
                response.data = json.dumps(content)
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
    content = json.loads(response.data)
    # check, if the authentication was successful, then we need to do nothing
    if content.get("result").get("status") is True:
        role = content.get("result").get("value").get("role")
        loginname = content.get("result").get("value").get("username")
        realm = content.get("result").get("value").get("realm")
        realm = realm or get_default_realm()

        policy_object = g.policy_object
        try:
            client = g.client_ip
        except Exception:
            client = None
        logout_time_pol = policy_object.get_action_values(
            action=ACTION.LOGOUTTIME,
            scope=SCOPE.WEBUI,
            realm=realm,
            client=client,
            unique=True)
        token_page_size_pol = policy_object.get_action_values(
            action=ACTION.TOKENPAGESIZE,
            scope=SCOPE.WEBUI,
            realm=realm,
            client=client,
            unique=True
        )
        user_page_size_pol = policy_object.get_action_values(
            action=ACTION.USERPAGESIZE,
            scope=SCOPE.WEBUI,
            realm=realm,
            client=client,
            unique=True
        )
        token_wizard_2nd = bool(role == ROLE.USER and
            policy_object.get_policies(action=ACTION.TOKENWIZARD2ND,
                                       scope=SCOPE.WEBUI,
                                       realm=realm,
                                       client=client))
        token_wizard = False
        if role == ROLE.USER:
            token_wizard_pol = policy_object.get_policies(
                action=ACTION.TOKENWIZARD,
                scope=SCOPE.WEBUI,
                realm=realm,
                client=client
            )

            # We also need to check, if the user has not tokens assigned.
            # If the user has no tokens, we run the wizard. If the user
            # already has tokens, we do not run the wizard.
            if token_wizard_pol:
                token_wizard = get_tokens(user=User(loginname, realm),
                                          count=True) == 0
        user_details_pol = policy_object.get_policies(
            action=ACTION.USERDETAILS,
            scope=SCOPE.WEBUI,
            realm=realm,
            client=client
        )
        search_on_enter = policy_object.get_policies(
            action=ACTION.SEARCH_ON_ENTER,
            scope=SCOPE.WEBUI,
            realm=realm,
            client=client
        )
        default_tokentype_pol = policy_object.get_action_values(
            action=ACTION.DEFAULT_TOKENTYPE,
            scope=SCOPE.WEBUI,
            realm=realm,
            client=client,
            unique=True
        )

        token_page_size = DEFAULT_PAGE_SIZE
        user_page_size = DEFAULT_PAGE_SIZE
        default_tokentype = DEFAULT_TOKENTYPE
        if len(token_page_size_pol) == 1:
            token_page_size = int(token_page_size_pol[0])
        if len(user_page_size_pol) == 1:
            user_page_size = int(user_page_size_pol[0])
        if len(default_tokentype_pol) == 1:
            default_tokentype = default_tokentype_pol[0]

        logout_time = DEFAULT_LOGOUT_TIME
        if len(logout_time_pol) == 1:
            logout_time = int(logout_time_pol[0])

        policy_template_url_pol = policy_object.get_action_values(
            action=ACTION.POLICYTEMPLATEURL,
            scope=SCOPE.WEBUI,
            client=client,
            unique=True)

        policy_template_url = DEFAULT_POLICY_TEMPLATE_URL
        if len(policy_template_url_pol) == 1:
            policy_template_url = policy_template_url_pol[0]

        content["result"]["value"]["logout_time"] = logout_time
        content["result"]["value"]["token_page_size"] = token_page_size
        content["result"]["value"]["user_page_size"] = user_page_size
        content["result"]["value"]["policy_template_url"] = policy_template_url
        content["result"]["value"]["default_tokentype"] = default_tokentype
        content["result"]["value"]["user_details"] = len(user_details_pol) > 0
        content["result"]["value"]["token_wizard"] = token_wizard
        content["result"]["value"]["token_wizard_2nd"] = token_wizard_2nd
        content["result"]["value"]["search_on_enter"] = len(search_on_enter) > 0
        response.data = json.dumps(content)
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
    content = json.loads(response.data)
    # check, if the authentication was successful, then we need to do nothing
    if content.get("result").get("value") is False:
        user_obj = request.User
        #user_obj = get_user_from_param(request.all_data)
        password = request.all_data.get("pass", "")
        if user_obj.login and user_obj.realm:
            # If there is no user in the request (because it is a serial
            # authentication request) we immediately bail out
            # check if the policy is defined
            policy_object = g.policy_object

            autoassign_values = policy_object.\
                get_action_values(action=ACTION.AUTOASSIGN,
                                  scope=SCOPE.ENROLL,
                                  user=user_obj.login,
                                  resolver=user_obj.resolver,
                                  realm=user_obj.realm,
                                  client=g.client_ip)

            if len(autoassign_values) > 1:
                raise PolicyError("Contradicting Autoassign policies.")
            # check if the user has no token
            if autoassign_values and get_tokens(user=user_obj, count=True) == 0:
                # Check is the token would match
                # get all unassigned tokens in the realm and look for
                # a matching OTP:
                realm_tokens = get_tokens(realm=user_obj.realm,
                                          assigned=False)

                for token_obj in realm_tokens:
                    (res, pin, otp) = token_obj.split_pin_pass(password)
                    if res:
                        pin_check = True
                        if autoassign_values[0] == \
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
                                if not content.get("detail"):
                                    content["detail"] = {}
                                content.get("detail")["serial"] = \
                                    token_obj.token.serial
                                content.get("detail")["otplen"] = \
                                    token_obj.token.otplen
                                content.get("detail")["type"] = token_obj.type
                                content.get("detail")["message"] = "Token " \
                                                                   "assigned to " \
                                                                   "user via " \
                                                                   "Autoassignment"
                                response.data = json.dumps(content)

                                g.audit_object.log(
                                    {"success": True,
                                     "action_info":
                                         "Token assigned via auto assignment",
                                     "serial": token_obj.token.serial})
                                break

    return response
