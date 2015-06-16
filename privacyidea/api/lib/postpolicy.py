# -*- coding: utf-8 -*-
#
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
import logging
log = logging.getLogger(__name__)
from privacyidea.lib.error import PolicyError
from flask import g
from privacyidea.lib.policy import SCOPE, ACTION
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.token import get_tokens, assign_token
from privacyidea.lib.machine import get_hostname, get_auth_items
from .prepolicy import check_max_token_user, check_max_token_realm
import functools
import json
import re
import netaddr

optional = True
required = False
DEFAULT_LOGOUT_TIME = 120


class postpolicy(object):
    """
    Decorator that allows to call a specific function after the decorated
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

    allowed_tokentypes = policy_object.get_action_values("tokentype",
                                                 scope=SCOPE.AUTHZ,
                                                 client=request.remote_addr)
    if tokentype and len(allowed_tokentypes) > 0:
        if tokentype not in allowed_tokentypes:
            # TODO: adapt the audit log!!!
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
                                                    client=request.remote_addr)

    # If we can compare a serial and if we do serial matching!
    if serial and len(allowed_serials) > 0:
        serial_matches = False
        for allowed_serial in allowed_serials:
            if re.search(allowed_serial, serial):
                serial_matches = True
                break
        if serial_matches is False:
            # TODO: adapt the audit log!!!
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
                                           client=request.remote_addr,
                                           active=True)

    if len(detailPol):
        # The policy was set, we need to strip the details, if the
        # authentication was successful. (value=true)
        if content.get("result", {}).get("value"):
            del content["detail"]
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
                                           client=request.remote_addr,
                                           active=True)

    if len(detailPol):
        # The policy was set, we need to strip the details, if the
        # authentication was successful. (value=true)
        if content.get("result", {}).get("value") is False:
            del content["detail"]
            response.data = json.dumps(content)

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
    if content.get("result").get("value") is True:
        # If there is no remote address, we can not determine offline information
        if request.remote_addr:
            client_ip = netaddr.IPAddress(request.remote_addr)
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
                if len(auth_items) > 0:
                    content["auth_items"] = auth_items
                    response.data = json.dumps(content)
            except Exception as exx:
                log.info(exx)
    return response


def get_logout_time(request, response):
    """
    This decorator is used in the /auth API to add configuration information
    like the logout time to the response.
    :param request: flask request object
    :param response: flask response object
    :return: the response
    """
    content = json.loads(response.data)
    # check, if the authentication was successful, then we need to do nothing
    if content.get("result").get("status") is True:
        # TODO: get the authenticated user
        policy_object = g.policy_object
        try:
            client = request.remote_addr
        except Exception:
            client = None
        logout_time_pol = policy_object.get_action_values(
            action=ACTION.LOGOUTTIME,
            scope=SCOPE.WEBUI,
            client=client,
            unique=True)

        logout_time = DEFAULT_LOGOUT_TIME
        if len(logout_time_pol) == 1:
            logout_time = int(logout_time_pol[0])

        content["result"]["value"]["logout_time"] = logout_time
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
        user_obj = get_user_from_param(request.all_data)
        password = request.all_data.get("pass", "")
        if user_obj.login and user_obj.realm:
            # If there is no user in the request (because it is a serial
            # authentication request) we immediately bail out
            # check if the policy is defined
            policy_object = g.policy_object

            autoassign_bool = policy_object.\
                get_policies(action=ACTION.AUTOASSIGN,
                             scope=SCOPE.ENROLL,
                             user=user_obj.login,
                             realm=user_obj.realm,
                             client=request.remote_addr,
                             active=True)

            if len(autoassign_bool) >= 1:
                # check if the user has no token
                if get_tokens(user=user_obj, count=True) == 0:
                    # Check is the token would match
                    # get all unassigned tokens in the realm and look for a matching OTP:
                    realm_tokens = get_tokens(realm=user_obj.realm,
                                              assigned=False)
                    for token_obj in realm_tokens:
                        (res, pin, otp) = token_obj.split_pin_pass(password)
                        # TODO: What do we want to do with the PIN?
                        # Check it against userstore?
                        if token_obj.check_otp(otp) >= 0:
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
                            content.get("detail")["type"] = token_obj.type
                            content.get("detail")["message"] = "Token " \
                                                               "assigned to " \
                                                               "user via " \
                                                               "Autoassignment"
                            response.data = json.dumps(content)
                            break

    return response
