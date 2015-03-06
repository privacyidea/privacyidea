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
These are the policy decorators as PRE conditions for the API calls.
I.e. these conditions are executed before the wrapped API call.
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
from privacyidea.lib.utils import generate_password
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


def init_random_pin(request=None, action=None):
    """
    This policy function is to be used as a decorator in the API init function.
    If the policy is set accordingly it adds a random PIN to the
    request.all_data like.

    It uses the policy SCOPE.ENROLL, ACTION.OTPPINRANDOM to set a random OTP
    PIN during Token enrollment
    """
    params = request.all_data
    policy_object = g.policy_object
    user_object = get_user_from_param(params)
    # get the length of the random PIN from the policies
    pin_pols = policy_object.get_action_values(action=ACTION.OTPPINRANDOM,
                                               scope=SCOPE.ENROLL,
                                               user=user_object.login,
                                               realm=user_object.realm,
                                               client=request.remote_addr)

    pin_pols = list(set(pin_pols))
    if len(pin_pols) > 1:
        raise PolicyError("There are conflicting random_pin definitions!")
    elif len(pin_pols) == 1:
        log.debug("Creating random OTP PIN with length %s" % pin_pols[0])
        request.all_data["pin"] = generate_password(size=int(pin_pols[0]))

    return True


def init_tokenlabel(request=None, action=None):
    """
    This policy function is to be used as a decorator in the API init function.
    It adds the tokenlabel definition to the params like this:
    params : { "tokenlabel": "<u>@<r>" }

    It uses the policy SCOPE.ENROLL, ACTION.TOKENLABEL to set the tokenlabel
    of Smartphone tokens during enrollment and this fill the details of the
    response.
    """
    params = request.all_data
    policy_object = g.policy_object
    user_object = get_user_from_param(params)
    # get the serials from a policy definition
    label_pols = policy_object.get_action_values(action=ACTION.TOKENLABEL,
                                                 scope=SCOPE.ENROLL,
                                                 user=user_object.login,
                                                 realm=user_object.realm,
                                                 client=request.remote_addr)

    label_pols = list(set(label_pols))
    if len(label_pols) > 1:
        raise PolicyError("There are conflicting tokenlabel definitions!")
    elif len(label_pols) == 1:
        # The policy was set, so we need to set the tokenlabel in the request.
        request.all_data["tokenlabel"] = label_pols[0]

    return True


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
    if user_object.login:
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
    else:  # pragma: no cover
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


def set_realm(request=None, action=None):
    """
    Pre Policy
    This pre condition gets the current realm and verifies if the realm
    should be rewritten due to the policy definition.
    I takes the realm from the request and - if a policy matches - replaces
    this realm with the realm defined in the policy

    Check ACTION.SETREALM

    This decorator should wrap
        /validate/check

    :param req: The request that is intercepted during the API call
    :type req: Request Object
    :param action: An optional Action
    :type action: basestring
    :returns: Always true. Modified the parameter request
    """
    user_object = get_user_from_param(request.all_data)
    # At the moment a realm parameter with no user parameter returns a user
    # object like "@realm". If this is changed one day, we need to also fetch
    #  the realm
    if user_object:
        realm = user_object.realm
    else:  # pragma: no cover
        realm = request.all_data.get("realm")

    policy_object = g.policy_object
    new_realm = policy_object.get_action_values(ACTION.SETREALM,
                                                scope=SCOPE.AUTHZ,
                                                realm=realm,
                                                client=request.remote_addr)
    # reduce the entries to unique entries
    new_realm = list(set(new_realm))
    if len(new_realm) > 1:
        raise PolicyError("I do not know, to which realm I should set the "
                          "new realm. Conflicting policies exist.")
    elif len(new_realm) == 1:
        # There is one specific realm, which we set in the request
        request.all_data["realm"] = new_realm[0]

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
