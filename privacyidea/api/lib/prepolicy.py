# -*- coding: utf-8 -*-
#
#  2016-04-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Avoid "None" as redundant 2nd argument
#  2015-12-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add ACTION.REQUIREDEMAIL
#  2015-12-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Change eval to importlib
#  2015-11-04 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add check for REMOTE_USER
#  2015-04-13 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add hook for external decorator for init and assign
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
from privacyidea.lib.error import PolicyError, RegistrationError
from flask import g, current_app
from privacyidea.lib.policy import SCOPE, ACTION, PolicyClass
from privacyidea.lib.user import (get_user_from_param, get_default_realm,
                                  split_user)
from privacyidea.lib.token import (get_tokens, get_realms_of_token)
from privacyidea.lib.utils import generate_password
from privacyidea.lib.auth import ROLE
from privacyidea.api.lib.utils import getParam
import functools
import jwt
import re
import importlib

optional = True
required = False


class prepolicy(object):
    """
    This is the decorator wrapper to call a specific function before an API
    call.
    The prepolicy decorator is to be used in the API calls.
    A prepolicy decorator then will modify the request data or raise an
    exception
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
                                               client=g.client_ip,
                                               unique=True)

    if len(pin_pols) == 1:
        log.debug("Creating random OTP PIN with length {0!s}".format(pin_pols[0]))
        request.all_data["pin"] = generate_password(size=int(pin_pols[0]))

        # handle the PIN
        handle_pols = policy_object.get_action_values(
            action=ACTION.PINHANDLING, scope=SCOPE.ENROLL,
            user=user_object.login, realm=user_object.realm,
            client=g.client_ip)
        # We can have more than one pin handler policy. So we can process the
        #  PIN in several ways!
        for handle_pol in handle_pols:
            log.debug("Handle the random PIN with the class {0!s}".format(handle_pol))
            packageName = ".".join(handle_pol.split(".")[:-1])
            className = handle_pol.split(".")[-1:][0]
            mod = __import__(packageName, globals(), locals(), [className])
            pin_handler_class = getattr(mod, className)
            pin_handler = pin_handler_class()
            # Send the PIN
            pin_handler.send(request.all_data["pin"],
                             request.all_data.get("serial", "N/A"),
                             user_object,
                             tokentype=request.all_data.get("type", "hotp"),
                             logged_in_user=g.logged_in_user)

    return True


def check_otp_pin(request=None, action=None):
    """
    This policy function checks if the OTP PIN that is about to be set
    follows the OTP PIN policies ACTION.OTPPINMAXLEN, ACTION.OTPPINMINLEN and
    ACTION.OTPPINCONTENTS in the SCOPE.USER. It is used to decorate the API
    functions.

    The pin is investigated in the params as pin = params.get("pin")

    In case the given OTP PIN does not match the requirements an exception is
    raised.
    """
    # This policy is only used for USER roles at the moment:
    if g.logged_in_user.get("role") == "user":
        params = request.all_data
        pin = params.get("otppin", "") or params.get("pin", "")
        serial = params.get("serial")
        if serial:
            # if this is a token, that does not use a pin, we ignore this check
            # And immediately return true
            tokensobject_list = get_tokens(serial=serial)
            if (len(tokensobject_list) == 1 and
                    tokensobject_list[0].using_pin is False):
                return True
        policy_object = g.policy_object
        user_object = get_user_from_param(params)
        # get the policies for minimum length, maximum length and PIN contents
        pol_minlen = policy_object.get_action_values(action=ACTION.OTPPINMINLEN,
                                                     scope=SCOPE.USER,
                                                     user=user_object.login,
                                                     realm=user_object.realm,
                                                     client=g.client_ip,
                                                     unique=True)
        pol_maxlen = policy_object.get_action_values(action=ACTION.OTPPINMAXLEN,
                                                     scope=SCOPE.USER,
                                                     user=user_object.login,
                                                     realm=user_object.realm,
                                                     client=g.client_ip,
                                                     unique=True)
        pol_contents = policy_object.get_action_values(action=ACTION.OTPPINCONTENTS,
                                                       scope=SCOPE.USER,
                                                       user=user_object.login,
                                                       realm=user_object.realm,
                                                       client=g.client_ip,
                                                       unique=True)

        if len(pol_minlen) == 1 and len(pin) < int(pol_minlen[0]):
            # check the minimum length requirement
            raise PolicyError("The minimum OTP PIN length is {0!s}".format(
                              pol_minlen[0]))

        if len(pol_maxlen) == 1 and len(pin) > int(pol_maxlen[0]):
            # check the maximum length requirement
            raise PolicyError("The maximum OTP PIN length is {0!s}".format(
                              pol_minlen[0]))

        if len(pol_contents) == 1:
            # check the contents requirement
            chars = "[a-zA-Z]"  # c
            digits = "[0-9]"    # n
            special = "[.:,;-_<>+*!/()=?$§%&#~\^]"  # s
            no_others = False
            grouping = False

            if pol_contents[0] == "-":
                no_others = True
                pol_contents = pol_contents[1:]
            elif pol_contents[0] == "+":
                grouping = True
                pol_contents = pol_contents[1:]
            #  TODO implement grouping and substraction
            if "c" in pol_contents[0] and not re.search(chars, pin):
                raise PolicyError("Missing character in PIN: {0!s}".format(chars))
            if "n" in pol_contents[0] and not re.search(digits, pin):
                raise PolicyError("Missing character in PIN: {0!s}".format(digits))
            if "s" in pol_contents[0] and not re.search(special, pin):
                raise PolicyError("Missing character in PIN: {0!s}".format(special))

    return True


def encrypt_pin(request=None, action=None):
    """
    This policy function is to be used as a decorator for several API functions.
    E.g. token/assign, token/setpin, token/init
    If the policy is set to define the PIN to be encrypted,
    the request.all_data is modified like this:
    encryptpin = True

    It uses the policy SCOPE.ENROLL, ACTION.ENCRYPTPIN
    """
    params = request.all_data
    policy_object = g.policy_object
    user_object = get_user_from_param(params)
    # get the length of the random PIN from the policies
    pin_pols = policy_object.get_policies(action=ACTION.ENCRYPTPIN,
                                          scope=SCOPE.ENROLL,
                                          user=user_object.login,
                                          realm=user_object.realm,
                                          client=g.client_ip,
                                          active=True)

    if pin_pols:
        request.all_data["encryptpin"] = "True"
    else:
        if "encryptpin" in request.all_data:
            del request.all_data["encryptpin"]

    return True


def init_tokenlabel(request=None, action=None):
    """
    This policy function is to be used as a decorator in the API init function.
    It adds the tokenlabel definition to the params like this:
    params : { "tokenlabel": "<u>@<r>" }

    In addtion it adds the tokenissuer to the params like this:
    params : { "tokenissuer": "privacyIDEA instance" }

    It uses the policy SCOPE.ENROLL, ACTION.TOKENLABEL and ACTION.TOKENISSUER
    to set the tokenlabel and tokenissuer
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
                                                 client=g.client_ip,
                                                 unique=True)

    if len(label_pols) == 1:
        # The policy was set, so we need to set the tokenlabel in the request.
        request.all_data["tokenlabel"] = label_pols[0]

    issuer_pols = policy_object.get_action_values(action=ACTION.TOKENISSUER,
                                                  scope=SCOPE.ENROLL,
                                                  user=user_object.login,
                                                  realm=user_object.realm,
                                                  client=g.client_ip,
                                                  unique=True)
    if len(issuer_pols) == 1:
        request.all_data["tokenissuer"] = issuer_pols[0]

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
                                                     client=g.client_ip)
        if limit_list:
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
                                                     client=g.client_ip)
        if limit_list:
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

    :param request: The request that is intercepted during the API call
    :type request: Request Object
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
                                                client=g.client_ip)
    if len(new_realm) > 1:
        raise PolicyError("I do not know, to which realm I should set the "
                          "new realm. Conflicting policies exist.")
    elif len(new_realm) == 1:
        # There is one specific realm, which we set in the request
        request.all_data["realm"] = new_realm[0]

    return True


def required_email(request=None, action=None):
    """
    This precondition checks if the "email" parameter matches the regular
    expression in the policy scope=register, action=requiredemail.
    See :ref:`policy_requiredemail`.

    Check ACTION.REQUIREDEMAIL

    This decorator should wrap POST /register

    :param request: The Request Object
    :param action: An optional Action
    :return: Modifies the request paramters or raises an Exception
    """
    email = getParam(request.all_data, "email")
    email_found = False
    email_pols = g.policy_object.\
        get_action_values(ACTION.REQUIREDEMAIL, scope=SCOPE.REGISTER,
                          client=g.client_ip)
    if email and email_pols:
        for email_pol in email_pols:
            # The policy is only "/regularexpr/".
            search = email_pol.strip("/")
            if re.findall(search, email):
                email_found = True
        if not email_found:
            raise RegistrationError("This email address is not allowed to "
                                    "register!")

    return True


def mangle(request=None, action=None):
    """
    This pre condition checks if either of the parameters pass, user or realm
    in a validate/check request should be rewritten based on an
    authentication policy with action "mangle".
    See :ref:`policy_mangle` for an example.

    Check ACTION.MANGLE

    This decorator should wrap
        /validate/check

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional Action
    :type action: basestring
    :returns: Always true. Modified the parameter request
    """
    user_object = get_user_from_param(request.all_data)

    policy_object = g.policy_object
    mangle_pols = policy_object.get_action_values(ACTION.MANGLE,
                                                  scope=SCOPE.AUTH,
                                                  realm=user_object.realm,
                                                  user=user_object.login,
                                                  client=g.client_ip)
    # We can have several mangle policies! One for user, one for realm and
    # one for pass. So we do no checking here.
    for mangle_pol_action in mangle_pols:
        # mangle_pol_action looks like this:
        # keyword/search/replace/. Where "keyword" can be "user", "pass" or
        # "realm".
        mangle_key, search, replace, _rest = mangle_pol_action.split("/", 3)
        mangle_value = request.all_data.get(mangle_key)
        if mangle_value:
            log.debug("mangling authentication data: {0!s}".format(mangle_key))
            request.all_data[mangle_key] = re.sub(search, replace,
                                                  mangle_value)
    return True


def check_anonymous_user(request=None, action=None):
    """
    This decorator function takes the request and verifies the given action
    for the SCOPE USER without an authenticated user but the user from the
    parameters.

    This is used with password_reset

    :param request:
    :param action:
    :return: True otherwise raises an Exception
    """
    ERROR = "User actions are defined, but this action is not allowed!"
    params = request.all_data
    policy_object = g.policy_object
    scope = SCOPE.USER
    user_obj = get_user_from_param(params)
    username = user_obj.login
    realm = user_obj.realm

    action = policy_object.get_policies(action=action,
                                        user=username,
                                        realm=realm,
                                        scope=scope,
                                        client=g.client_ip,
                                        adminrealm=None,
                                        active=True)
    action_at_all = policy_object.get_policies(scope=scope,
                                               active=True,
                                               all_times=True)
    if action_at_all and len(action) == 0:
        raise PolicyError(ERROR)
    return True


def check_base_action(request=None, action=None, anonymous=False):
    """
    This decorator function takes the request and verifies the given action
    for the SCOPE ADMIN or USER.
    :param request:
    :param action:
    :param anonymous: If set to True, the user data is taken from the request
        parameters.
    :return: True otherwise raises an Exception
    """
    ERROR = {"user": "User actions are defined, but the action %s is not "
                     "allowed!" % action,
             "admin": "Admin actions are defined, but the action %s is not "
                      "allowed!" % action}
    params = request.all_data
    policy_object = g.policy_object
    username = g.logged_in_user.get("username")
    role = g.logged_in_user.get("role")
    scope = SCOPE.ADMIN
    admin_realm = g.logged_in_user.get("realm")
    realm = params.get("realm")
    if type(realm) == list and len(realm) == 1:
        realm = realm[0]

    if role == "user":
        scope = SCOPE.USER
        # Reset the admin realm
        admin_realm = None

    # get the realm by the serial:
    if params.get("serial") and not realm:
        realms = get_realms_of_token(params.get("serial"))
        if realms:
            realm = realms[0]
        else:
            realm = None
    action = policy_object.get_policies(action=action,
                                        user=username,
                                        realm=realm,
                                        scope=scope,
                                        client=g.client_ip,
                                        adminrealm=admin_realm,
                                        active=True)
    action_at_all = policy_object.get_policies(scope=scope,
                                               active=True,
                                               all_times=True)
    if action_at_all and len(action) == 0:
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
    admin_realm = g.logged_in_user.get("realm")
    action = policy_object.get_policies(action=ACTION.IMPORT,
                                        user=username,
                                        realm=params.get("realm"),
                                        scope=SCOPE.ADMIN,
                                        client=g.client_ip,
                                        adminrealm=admin_realm,
                                        active=True)
    action_at_all = policy_object.get_policies(scope=SCOPE.ADMIN,
                                               active=True, all_times=True)
    if action_at_all and len(action) == 0:
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
    admin_realm = g.logged_in_user.get("realm")
    scope = SCOPE.ADMIN
    if role == "user":
        scope = SCOPE.USER
        admin_realm = None
    tokentype = params.get("type", "HOTP")
    action = "enroll{0!s}".format(tokentype.upper())
    action = policy_object.get_policies(action=action,
                                        user=username,
                                        realm=params.get("realm"),
                                        scope=scope,
                                        client=g.client_ip,
                                        adminrealm=admin_realm,
                                        active=True)
    action_at_all = policy_object.get_policies(scope=scope, active=True,
                                               all_times=True)
    if action_at_all and len(action) == 0:
        raise PolicyError(ERROR.get(role))
    return True


def check_external(request=None, action="init"):
    """
    This decorator is a hook to an external check function, that is called
    before the token/init or token/assign API.

    :param request: The REST request
    :type request: flask Request object
    :param action: This is either "init" or "assign"
    :type action: basestring
    :return: either True or an Exception is raised
    """
    function_name = None
    module = None
    try:
        module_func = current_app.config.get("PI_INIT_CHECK_HOOK")
        if module_func:
            module_name = ".".join(module_func.split(".")[:-1])
            module = importlib.import_module(module_name)
            function_name = module_func.split(".")[-1]
    except Exception as exx:
        log.error("Error importing external check function: {0!s}".format(exx))

    # Import of function was successful
    if function_name:
        external_func = getattr(module, function_name)
        external_func(request, action)
    return True


def api_key_required(request=None, action=None):
    """
    This is a decorator for check_user_pass and check_serial_pass.
    It checks, if a policy scope=auth, action=apikeyrequired is set.
    If so, the validate request will only performed, if a JWT token is passed
    with role=validate.
    """
    ERROR = "The policy requires an API key to authenticate, " \
            "but no key was passed."
    params = request.all_data
    policy_object = g.policy_object
    user_object = get_user_from_param(params)

    # Get the policies
    action = policy_object.get_policies(action=ACTION.APIKEY,
                                        user=user_object.login,
                                        realm=user_object.realm,
                                        scope=SCOPE.AUTHZ,
                                        client=g.client_ip,
                                        active=True)
    # Do we have a policy?
    if action:
        # check if we were passed a correct JWT
        # Get the Authorization token from the header
        auth_token = request.headers.get('PI-Authorization')
        if not auth_token:
            auth_token = request.headers.get('Authorization')
        try:
            r = jwt.decode(auth_token, current_app.secret_key)
            g.logged_in_user = {"username": r.get("username", ""),
                                "realm": r.get("realm", ""),
                                "role": r.get("role", "")}
        except AttributeError:
            raise PolicyError("No valid API key was passed.")

        role = g.logged_in_user.get("role")
        if role != ROLE.VALIDATE:
            raise PolicyError("A correct JWT was passed, but it was no API "
                              "key.")

    # If everything went fine, we call the original function
    return True


def mock_success(req, action):
    """
    This is a mock function as an example for check_external. This function
    returns success and the API call will go on unmodified.
    """
    return True


def mock_fail(req, action):
    """
    This is a mock function as an example for check_external. This function
    creates a problem situation and the token/init or token/assign will show
    this exception accordingly.
    """
    raise Exception("This is an Exception in an external check function")


def is_remote_user_allowed(req):
    """
    Checks if the REMOTE_USER server variable is allowed to be used.

    .. note:: This is not used as a decorator!

    :param req: The flask request, containing the remote user and the client IP
    :return:
    """
    res = False
    if req.remote_user:
        loginname, realm = split_user(req.remote_user)
        realm = realm or get_default_realm()

        # Check if the remote user is allowed
        if "client_ip" not in g:
            g.client_ip = req.remote_user
        if "policy_object" not in g:
            g.policy_object = PolicyClass()
        ruser_active = g.policy_object.get_action_values(ACTION.REMOTE_USER,
                                                         scope=SCOPE.WEBUI,
                                                         user=loginname,
                                                         realm=realm,
                                                         client=g.client_ip)

        res = ruser_active

    return res
