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
from privacyidea.lib.token import get_tokens
import functools
import json
import re

optional = True
required = False


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
