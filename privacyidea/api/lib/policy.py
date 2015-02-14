# -*- coding: utf-8 -*-
#
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
These are the policy decorators for the API calls.
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
from privacyidea.lib.token import get_tokens
import functools
import json
import re

optional = True
required = False

class prepolicy(object):
    """
    This is the decorator wrapper to call a specific function before an API
    call.
    The prepolicy decorator is to be used in the API calls.
    """
    def __init__(self, function, request, action=None):
        """
        :param function: This is the policy function the is to be called
        :type function: function
        :param request: The original request object, that needs to be passed
        :type request: Request Object
        """
        self.action = action
        self.request = request
        self.function = function

    def __call__(self, wrapped_function):
        """
        This decorates the given function. The prepolicy decorator is ment
        for API functions on the API level.

        If some error occur the a PolicyException is raised.

        The decorator function can modify the request data.

        :param wrapped_function: The function, that is decorated.
        :type wrapped_function: API function
        :return: None
        """
        @functools.wraps(wrapped_function)
        def policy_wrapper(*args, **kwds):
            self.function(request=self.request,
                          action=self.action)
            return wrapped_function(*args, **kwds)

        return policy_wrapper


def check_max_token_user(request=None, action=None):
    """
    Pre Policy
    This checks the maximum token per user policy.
    Check ACTION.MAXTOKENUSER

    This decorator can wrap:
        /token/init  (with a realm and user)
        /token/assign

    :param req:
    :param action:
    :return: True otherwise raises an Exception
    """
    ERROR = "The number of tokens for this user is limited!"
    params = request.all_data
    user_object = get_user_from_param(params)
    if user_object:
        policy_object = g.policy_object
        limit_list = policy_object.get_action_values(ACTION.MAXTOKENUSER,
                                                     scope=SCOPE.ENROLL,
                                                     realm=user_object.realm,
                                                     user=user_object.login,
                                                     client=request.remote_addr)
        if len(limit_list) > 0:
            # we need to check how many tokens the user already has assigned!
            tokenobject_list = get_tokens(user=user_object)
            already_assigned_tokens = len(tokenobject_list)
            if already_assigned_tokens >= int(max(limit_list)):
                raise PolicyError(ERROR)
    return True


def check_max_token_realm(request=None, action=None):
    """
    Pre Policy
    This checks the maximum token per realm.
    Check ACTION.MAXTOKENREALM

    This decorator can wrap:
        /token/init  (with a realm and user)
        /token/assign
        /token/tokenrealms

    :param req: The request that is intercepted during the API call
    :type req: Request Object
    :param action: An optional Action
    :type action: basestring
    :return: True otherwise raises an Exception
    """
    ERROR = "The number of tokens in this realm is limited!"
    params = request.all_data
    user_object = get_user_from_param(params)
    if user_object:
        realm = user_object.realm
    else:
        realm = params.get("realm")

    if realm:
        policy_object = g.policy_object
        limit_list = policy_object.get_action_values(ACTION.MAXTOKENREALM,
                                                     scope=SCOPE.ENROLL,
                                                     realm=realm,
                                                     client=request.remote_addr)
        if len(limit_list) > 0:
            # we need to check how many tokens the user already has assigned!
            tokenobject_list = get_tokens(realm=realm)
            already_assigned_tokens = len(tokenobject_list)
            if already_assigned_tokens >= int(max(limit_list)):
                raise PolicyError(ERROR)
    return True


def check_base_action(request=None, action=None):
    """
    This decorator function takes the request and verifies the given action
    for the SCOPE ADMIN or USER.
    :param req:
    :param action:
    :return: True otherwise raises an Exception
    """
    ERROR = {"user": "User actions are defined, but this action is not "
                     "allowed!",
             "admin": "Admin actions are defined, but this action is not "
                      "allowed!"}
    params = request.all_data
    policy_object = g.policy_object
    username = g.logged_in_user.get("username")
    role = g.logged_in_user.get("role")
    scope = SCOPE.ADMIN
    if role == "user":
        scope = SCOPE.USER
    action = policy_object.get_policies(action=action,
                                        user=username,
                                        realm=params.get("realm"),
                                        scope=scope,
                                        client=request.remote_addr)
    action_at_all = policy_object.get_policies(scope=scope)
    if len(action_at_all) and len(action) == 0:
        raise PolicyError(ERROR.get(role))
    return True


def check_token_upload(request=None, action=None):
    """
    This decorator function takes the request and verifies the given action
    for scope ADMIN
    :param req:
    :param filename:
    :return:
    """
    params = request.all_data
    policy_object = g.policy_object
    username = g.logged_in_user.get("username")
    action = policy_object.get_policies(action="import",
                                        user=username,
                                        realm=params.get("realm"),
                                        scope=SCOPE.ADMIN,
                                        client=request.remote_addr)
    action_at_all = policy_object.get_policies(scope=SCOPE.ADMIN)
    if len(action_at_all) and len(action) == 0:
        raise PolicyError("Admin actions are defined, but you are not allowed"
                          " to upload token files.")
    return True


def check_token_init(request=None, action=None):
    """
    This decorator function takes the request and verifies
    if the requested tokentype is allowed to be enrolled in the SCOPE ADMIN
    or the SCOPE USER.
    :param request:
    :param action:
    :return: True or an Exception is raised
    """
    ERROR = {"user": "User actions are defined, you are not allowed to "
                     "enroll this token type!",
             "admin": "Admin actions are defined, but you are not allowed to "
                      "enroll this token type!"}
    params = request.all_data
    policy_object = g.policy_object
    username = g.logged_in_user.get("username")
    role = g.logged_in_user.get("role")
    scope = SCOPE.ADMIN
    if role == "user":
        scope = SCOPE.USER
    tokentype = params.get("type", "HOTP")
    action = "enroll%s" % tokentype.upper()
    action = policy_object.get_policies(action=action,
                                        user=username,
                                        realm=params.get("realm"),
                                        scope=scope,
                                        client=request.remote_addr)
    action_at_all = policy_object.get_policies(scope=scope)
    if len(action_at_all) and len(action) == 0:
        raise PolicyError(ERROR.get(role))
    return True


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


def set_tokenlabel(request, response):
    """
    This policy function is to be used as a decorator in the API init function.
    It adds the token label to the URL that generates the QR code.

    TODO: This is an internal config function.

    :param request:
    :param response:
    :return:
    """
    pass


def set_detail_on_fail(request, response):
    """
    This policy function is used with the AUTHZ scope.
    If the boolean value detail_on_fail is set, the details will be set if
    the authentication request failed.

    :param request:
    :param response:
    :return:
    """
    pass


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
                                           client=request.remote_addr)

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
                                           client=request.remote_addr)

    if len(detailPol):
        # The policy was set, we need to strip the details, if the
        # authentication was successful. (value=true)
        if content.get("result", {}).get("value") is False:
            del content["detail"]
            response.data = json.dumps(content)

    return response
