# -*- coding: utf-8 -*-
#
#  2017-04-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add wrapper for U2F token
#  2017-01-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add token specific PIN policies based on
#             Quynh's pull request.
#  2016-11-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add timelimit for audit entries
#  2016-08-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add decorator to save the client type to the database
#  2016-07-17 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add realmadmin decorator
#  2016-05-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add resolver to check_base_action
#  2016-04-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add init_token_defaults to set default parameters
#             during token init.
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
from privacyidea.lib.utils import (generate_password, get_client_ip,
                                   parse_timedelta, is_true)
from privacyidea.lib.auth import ROLE
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.clientapplication import save_clientapplication
from privacyidea.lib.config import (get_token_class, get_from_config, SYSCONF)
import functools
import jwt
import re
import importlib
# Token specific imports!
from privacyidea.lib.tokens.u2ftoken import (U2FACTION, parse_registration_data)
from privacyidea.lib.tokens.u2f import x509name_to_string

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


def realmadmin(request=None, action=None):
    """
    This decorator adds the first REALM to the parameters if the
    administrator, calling this API is a realm admin.
    This way, if the admin calls e.g. GET /user without realm parameter,
    he will not see all users, but only users in one of his realms.

    TODO: If a realm admin is allowed to see more than one realm,
          this is not handled at the moment. We need to change the underlying
          library functions!

    :param request: The HTTP reqeust
    :param action: The action like ACTION.USERLIST
    """
    # This decorator is only valid for admins
    if g.logged_in_user.get("role") == ROLE.ADMIN:
        params = request.all_data
        if not "realm" in params:
            # add the realm to params
            policy_object = g.policy_object
            po = policy_object.get_policies(
                action=action, scope=SCOPE.ADMIN,
                user=g.logged_in_user.get("username"),
                adminrealm=g.logged_in_user.get("realm"), client=g.client_ip,
                active=True)
            # TODO: fix this: there could be a list of policies with a list
            # of realms!
            if po and po[0].get("realm"):
                request.all_data["realm"] = po[0].get("realm")[0]

    return True


def check_otp_pin(request=None, action=None):
    """
    This policy function checks if the OTP PIN that is about to be set
    follows the OTP PIN policies ACTION.OTPPINMAXLEN, ACTION.OTPPINMINLEN and
    ACTION.OTPPINCONTENTS and token-type-specific PIN policy actions in the
    SCOPE.USER or SCOPE.ADMIN. It is used to decorate the API functions.

    The pin is investigated in the params as "otppin" or "pin"

    In case the given OTP PIN does not match the requirements an exception is
    raised.
    """
    params = request.all_data
    realm = params.get("realm")
    pin = params.get("otppin", "") or params.get("pin", "")
    serial = params.get("serial")
    tokentype = params.get("type")
    if not serial and action == ACTION.SETPIN:
        path_elems = request.path.split("/")
        serial = path_elems[-1]
        # Also set it for later use
        request.all_data["serial"] = serial
    if serial:
        # if this is a token, that does not use a pin, we ignore this check
        # And immediately return true
        tokensobject_list = get_tokens(serial=serial)
        if len(tokensobject_list) == 1:
            if tokensobject_list[0].using_pin is False:
                return True
            tokentype = tokensobject_list[0].token.tokentype
    # the default tokentype is still HOTP
    tokentype = tokentype or "hotp"
    policy_object = g.policy_object
    role = g.logged_in_user.get("role")
    username = g.logged_in_user.get("username")
    if role == ROLE.ADMIN:
        scope = SCOPE.ADMIN
        admin_realm = g.logged_in_user.get("realm")
        realm = params.get("realm", "")
    else:
        scope = SCOPE.USER
        realm = g.logged_in_user.get("realm")
        admin_realm = None
    # get the policies for minimum length, maximum length and PIN contents
    # first try to get a token specific policy - otherwise fall back to
    # default policy
    pol_minlen = policy_object.get_action_values(
        action="{0!s}_{1!s}".format(tokentype, ACTION.OTPPINMINLEN),
        scope=scope, user=username, realm=realm, adminrealm=admin_realm,
        client=g.client_ip, unique=True) or \
                 policy_object.get_action_values(
                     action=ACTION.OTPPINMINLEN, scope=scope, user=username,
                     realm=realm, adminrealm=admin_realm, client=g.client_ip,
                     unique=True)

    pol_maxlen = policy_object.get_action_values(
        action="{0!s}_{1!s}".format(tokentype, ACTION.OTPPINMAXLEN),
        scope=scope, user=username, realm=realm, adminrealm=admin_realm,
        client=g.client_ip, unique=True) or \
                 policy_object.get_action_values(
                     action=ACTION.OTPPINMAXLEN, scope=scope, user=username,
                     realm=realm, adminrealm=admin_realm, client=g.client_ip,
                     unique=True)

    pol_contents = policy_object.get_action_values(
        action="{0!s}_{1!s}".format(tokentype, ACTION.OTPPINCONTENTS),
        scope=scope, user=username, realm=realm, adminrealm=admin_realm,
        client=g.client_ip, unique=True) or \
                   policy_object.get_action_values(
                       action=ACTION.OTPPINCONTENTS, scope=scope,
                       user=username, realm=realm, adminrealm=admin_realm,
                       client=g.client_ip, unique=True)

    if len(pol_minlen) == 1 and len(pin) < int(pol_minlen[0]):
        # check the minimum length requirement
        raise PolicyError("The minimum OTP PIN length is {0!s}".format(
                          pol_minlen[0]))

    if len(pol_maxlen) == 1 and len(pin) > int(pol_maxlen[0]):
        # check the maximum length requirement
        raise PolicyError("The maximum OTP PIN length is {0!s}".format(
                          pol_maxlen[0]))

    if len(pol_contents) == 1:
        # check the contents requirement
        chars = "[a-zA-Z]"  # c
        digits = "[0-9]"    # n
        special = "[.:,;_<>+*!/()=?$§%&#~\^-]"  # s
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


def papertoken_count(request=None, action=None):
    """
    This is a token specific wrapper for paper token for the endpoint
    /token/init.
    According to the policy scope=SCOPE.ENROLL,
    action=PAPERACTION.PAPER_COUNT it sets the parameter papertoken_count to
    enroll a paper token with such many OTP values.

    :param request:
    :param action:
    :return:
    """
    from privacyidea.lib.tokens.papertoken import PAPERACTION
    user_object = request.User
    policy_object = g.policy_object
    pols = policy_object.get_action_values(
        action=PAPERACTION.PAPERTOKEN_COUNT,
        scope=SCOPE.ENROLL,
        user=user_object.login,
        resolver=user_object.resolver,
        realm=user_object.realm,
        client=g.client_ip,
        unique=True)

    if pols:
        papertoken_count = pols[0]
        request.all_data["papertoken_count"] = papertoken_count

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


def enroll_pin(request=None, action=None):
    """
    This policy function is used as decorator for init token.
    It checks, if the user or the admin is allowed to set a token PIN during
    enrollment. If not, it deleted the PIN from the request.
    """
    policy_object = g.policy_object
    role = g.logged_in_user.get("role")
    if role == ROLE.USER:
        scope = SCOPE.USER
        username = g.logged_in_user.get("username")
        realm = g.logged_in_user.get("realm")
        adminrealm = None
    else:
        scope = SCOPE.ADMIN
        username = g.logged_in_user.get("username")
        realm = getParam(request.all_data, "realm")
        adminrealm = g.logged_in_user.get("realm")
    pin_pols = policy_object.get_policies(action=ACTION.ENROLLPIN,
                                          scope=scope,
                                          user=username,
                                          realm=realm,
                                          adminrealm=adminrealm,
                                          client=g.client_ip,
                                          active=True)
    action_at_all = policy_object.get_policies(scope=scope,
                                               active=True,
                                               all_times=True)

    if action_at_all and not pin_pols:
        # Not allowed to set a PIN during enrollment!
        if "pin" in request.all_data:
            del request.all_data["pin"]
    return True


def init_token_defaults(request=None, action=None):
    """
    This policy function is used as a decorator for the API init function.
    Depending on policy settings it can add token specific default values
    like totp_hashlib, hotp_hashlib, totp_otplen...
    """
    params = request.all_data
    ttype = params.get("type") or "hotp"
    token_class = get_token_class(ttype)
    default_settings = token_class.get_default_settings(params,
                                                        g.logged_in_user,
                                                        g.policy_object,
                                                        g.client_ip)
    log.debug("Adding default settings {0!s} for token type {1!s}".format(
        default_settings, ttype))
    request.all_data.update(default_settings)
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
                                                 unique=True,
                                                 allow_white_space_in_action=True)

    if len(label_pols) == 1:
        # The policy was set, so we need to set the tokenlabel in the request.
        request.all_data["tokenlabel"] = label_pols[0]

    issuer_pols = policy_object.get_action_values(action=ACTION.TOKENISSUER,
                                                  scope=SCOPE.ENROLL,
                                                  user=user_object.login,
                                                  realm=user_object.realm,
                                                  client=g.client_ip,
                                                  unique=True,
                                                  allow_white_space_in_action=True)
    if len(issuer_pols) == 1:
        request.all_data["tokenissuer"] = issuer_pols[0]

    return True


def twostep_enrollment_activation(request=None, action=None):
    """
    This policy function enables the two-step enrollment process according
    to the configured policies.
    It is used to decorate the ``/token/init`` endpoint.

    If a ``<type>_2step`` policy matches, the ``2stepinit`` parameter is handled according to the policy.
    If no policy matches, the ``2stepinit`` parameter is removed from the request data.
    """
    policy_object = g.policy_object
    user_object = get_user_from_param(request.all_data)
    serial = getParam(request.all_data, "serial", optional)
    token_type = getParam(request.all_data, "type", optional, "hotp")
    token_exists = False
    if serial:
        tokensobject_list = get_tokens(serial=serial)
        if len(tokensobject_list) == 1:
            token_type = tokensobject_list[0].token.tokentype
            token_exists = True
    token_type = token_type.lower()
    role = g.logged_in_user.get("role")
    # Differentiate between an admin enrolling a token for the
    # user and a user self-enrolling a token.
    if role == ROLE.ADMIN:
        scope = SCOPE.ADMIN
        adminrealm = g.logged_in_user.get("realm")
    else:
        scope = SCOPE.USER
        adminrealm = None
    realm = user_object.realm
    # In any case, the policy's user attribute is matched against the
    # currently logged-in user (which may be the admin or the
    # self-enrolling user).
    user = g.logged_in_user.get("username")
    # Tokentypes have separate twostep actions
    action = "{}_2step".format(token_type)
    twostep_enabled_pols = policy_object.get_action_values(action=action,
                                                           scope=scope,
                                                           unique=True,
                                                           user=user,
                                                           realm=realm,
                                                           client=g.client_ip,
                                                           adminrealm=adminrealm)
    if twostep_enabled_pols:
        enabled_setting = twostep_enabled_pols[0]
        if enabled_setting == "allow":
            # The user is allowed to pass 2stepinit=1
            pass
        elif enabled_setting == "force":
            # We force 2stepinit to be 1 (if the token does not exist yet)
            if not token_exists:
                request.all_data["2stepinit"] = 1
        else:
            raise PolicyError("Unknown 2step policy setting: {}".format(enabled_setting))
    else:
        # If no policy matches, the user is not allowed
        # to pass 2stepinit
        # Force two-step initialization to be None
        if "2stepinit" in request.all_data:
            del request.all_data["2stepinit"]
    return True


def twostep_enrollment_parameters(request=None, action=None):
    """
    If the ``2stepinit`` parameter is set to true, this policy function
    reads additional configuration from policies and adds it
    to ``request.all_data``, that is:

     * ``{type}_2step_serversize`` is written to ``2step_serversize``
     * ``{type}_2step_clientsize`` is written to ``2step_clientsize`
     * ``{type}_2step_difficulty`` is written to ``2step_difficulty``

    If no policy matches, the value passed by the user is kept.

    This policy function is used to decorate the ``/token/init`` endpoint.
    """
    policy_object = g.policy_object
    user_object = get_user_from_param(request.all_data)
    serial = getParam(request.all_data, "serial", optional)
    token_type = getParam(request.all_data, "type", optional, "hotp")
    if serial:
        tokensobject_list = get_tokens(serial=serial)
        if len(tokensobject_list) == 1:
            token_type = tokensobject_list[0].token.tokentype
    token_type = token_type.lower()
    role = g.logged_in_user.get("role")
    # Differentiate between an admin enrolling a token for the
    # user and a user self-enrolling a token.
    if role == ROLE.ADMIN:
        adminrealm = g.logged_in_user.get("realm")
    else:
        adminrealm = None
    realm = user_object.realm
    # In any case, the policy's user attribute is matched against the
    # currently logged-in user (which may be the admin or the
    # self-enrolling user).
    user = g.logged_in_user.get("username")
    # Tokentypes have separate twostep actions
    if is_true(getParam(request.all_data, "2stepinit", optional)):
        parameters = ("2step_serversize", "2step_clientsize", "2step_difficulty")
        for parameter in parameters:
            action = u"{}_{}".format(token_type, parameter)
            action_values = policy_object.get_action_values(action=action,
                                                            scope=SCOPE.ENROLL,
                                                            unique=True,
                                                            user=user,
                                                            realm=realm,
                                                            client=g.client_ip,
                                                            adminrealm=adminrealm)
            if action_values:
                request.all_data[parameter] = action_values[0]

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
    #user_object = get_user_from_param(request.all_data)
    user_object = request.User
    # At the moment a realm parameter with no user parameter returns a user
    # object like "@realm". If this is changed one day, we need to also fetch
    #  the realm
    if user_object:
        realm = user_object.realm
        username = user_object.login
    else:  # pragma: no cover
        realm = request.all_data.get("realm")
        username = None

    policy_object = g.policy_object
    new_realm = policy_object.get_action_values(ACTION.SETREALM,
                                                scope=SCOPE.AUTHZ,
                                                user=username,
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
    :return: Modifies the request parameters or raises an Exception
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


def auditlog_age(request=None, action=None):
    """
    This pre condition checks for the policy auditlog_age and set the
    "timelimit" parameter of the audit search API.

    Check ACTION.AUDIT_AGE

    The decorator can wrap GET /audit/

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional Action
    :type action: basestring
    :returns: Always true. Modified the parameter request
    """
    user_object = request.User
    policy_object = g.policy_object
    role = g.logged_in_user.get("role")
    if role == ROLE.ADMIN:
        scope = SCOPE.ADMIN
        adminrealm = g.logged_in_user.get("realm")
        user = g.logged_in_user.get("username")
        realm = user_object.realm
    else:
        scope = SCOPE.USER
        adminrealm = None
        user = user_object.login
        realm = user_object.realm

    audit_age = policy_object.get_action_values(ACTION.AUDIT_AGE,
                                                scope=scope,
                                                adminrealm=adminrealm,
                                                realm=realm,
                                                user=user,
                                                client=g.client_ip,
                                                unique=True)
    timelimit = None
    timelimit_s = None
    for aa in audit_age:
        if not timelimit:
            timelimit_s = aa
            timelimit = parse_timedelta(timelimit_s)
        else:
            # We will use the longest allowed timelimit
            if parse_timedelta(aa) > timelimit:
                timelimit_s = aa
                timelimit = parse_timedelta(timelimit_s)

        log.debug("auditlog_age: {0!s}".format(timelimit_s))
        request.all_data["timelimit"] = timelimit_s

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
    user_object = request.User

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
            if mangle_key in ["user", "realm"]:
                request.User = get_user_from_param(request.all_data)
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
    realm = None
    resolver = None

    if role == ROLE.USER:
        scope = SCOPE.USER
        # Reset the admin realm
        admin_realm = None
        realm = realm or g.logged_in_user.get("realm")

    # In certain cases we can not resolve the user by the serial!
    if action not in [ACTION.AUDIT]:
        realm = params.get("realm")
        if type(realm) == list and len(realm) == 1:
            realm = realm[0]
        resolver = params.get("resolver")
        # get the realm by the serial:
        if not realm and params.get("serial"):
            realm = get_realms_of_token(params.get("serial"),
                                        only_first_realm=True)

        # get the realm by the serial, while the serial is part of the URL like
        # DELETE /token/serial
        if not realm and request.view_args and request.view_args.get("serial"):
            realm = get_realms_of_token(request.view_args.get("serial"),
                                        only_first_realm=True)

    action = policy_object.get_policies(action=action,
                                        user=username,
                                        realm=realm,
                                        scope=scope,
                                        resolver=resolver,
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
    if role == ROLE.USER:
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
    #user_object = get_user_from_param(params)
    user_object = request.User

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
            g.client_ip = get_client_ip(req,
                                        get_from_config(SYSCONF.OVERRIDECLIENT))
        if "policy_object" not in g:
            g.policy_object = PolicyClass()
        ruser_active = g.policy_object.get_action_values(ACTION.REMOTE_USER,
                                                         scope=SCOPE.WEBUI,
                                                         user=loginname,
                                                         realm=realm,
                                                         client=g.client_ip)

        res = ruser_active

    return res


def save_client_application_type(request, action):
    """
    This decorator is used to write the client IP and the HTTP user agent (
    clienttype) to the database.

    In fact this is not a **policy** decorator, as it checks no policy. In
    fact, we could however one day
    define this as a policy, too.
    :param req:
    :return:
    """
    # retrieve the IP. This will also be the mapped IP!
    client_ip = g.client_ip or "0.0.0.0"
    # ...and the user agent.
    ua = request.user_agent
    save_clientapplication(client_ip, "{0!s}".format(ua) or "unknown")
    return True


def u2ftoken_verify_cert(request, action):
    """
    This is a token specific wrapper for u2f token for the endpoint
    /token/init
    According to the policy scope=SCOPE.ENROLL,
    action=U2FACTION.NO_VERIFY_CERT it can add a parameter to the
    enrollment parameters to not verify the attestation certificate.
    The default is to verify the cert.
    :param request:
    :param action:
    :return:
    """
    # Get the registration data of the 2nd step of enrolling a U2F device
    ttype = request.all_data.get("type")
    if ttype and ttype.lower() == "u2f":
        policy_object = g.policy_object
        # Add the default to verify the cert.
        request.all_data["u2f.verify_cert"] = True
        user_object = request.User

        if user_object:
            token_user = user_object.login
            token_realm = user_object.realm
            token_resolver = user_object.resolver
        else:
            token_realm = token_resolver = token_user = None

        do_not_verify_the_cert = policy_object.get_policies(
            action=U2FACTION.NO_VERIFY_CERT,
            scope=SCOPE.ENROLL,
            realm=token_realm,
            user=token_user,
            resolver=token_resolver,
            active=True,
            client=g.client_ip)
        if do_not_verify_the_cert:
            request.all_data["u2f.verify_cert"] = False

        log.debug("Should we not verify the attestation certificate? "
                  "Policies: {0!s}".format(do_not_verify_the_cert))
    return True


def u2ftoken_allowed(request, action):
    """
    This is a token specific wrapper for u2f token for the endpoint
     /token/init.
     According to the policy scope=SCOPE.ENROLL,
     action=U2FACTION.REQ it checks, if the assertion certificate is an
     allowed U2F token type.

     If the token, which is enrolled contains a non allowed attestation 
     certificate, we bail out.

    :param request: 
    :param action: 
    :return: 
    """
    policy_object = g.policy_object
    # Get the registration data of the 2nd step of enrolling a U2F device
    reg_data = request.all_data.get("regdata")
    if reg_data:
        # We have a registered u2f device!
        serial = request.all_data.get("serial")
        user_object = request.User

        # We just check, if the issuer is allowed, not if the certificate
        # is still valid! (verify_cert=False)
        attestation_cert, user_pub_key, key_handle, \
        signature, description = parse_registration_data(reg_data,
                                                         verify_cert=False)

        cert_info = {
            "attestation_issuer":
                x509name_to_string(attestation_cert.get_issuer()),
            "attestation_serial": "{!s}".format(
                attestation_cert.get_serial_number()),
            "attestation_subject": x509name_to_string(
                attestation_cert.get_subject())}

        if user_object:
            token_user = user_object.login
            token_realm = user_object.realm
            token_resolver = user_object.resolver
        else:
            token_realm = token_resolver = token_user = None

        allowed_certs_pols = policy_object.get_action_values(
            U2FACTION.REQ,
            scope=SCOPE.ENROLL,
            realm=token_realm,
            user=token_user,
            resolver=token_resolver,
            client=g.client_ip)
        for allowed_cert in allowed_certs_pols:
            tag, matching, _rest = allowed_cert.split("/", 3)
            tag_value = cert_info.get("attestation_{0!s}".format(tag))
            # if we do not get a match, we bail out
            m = re.search(matching, tag_value)
            if not m:
                log.warning("The U2F device {0!s} is not "
                            "allowed to be registered due to policy "
                            "restriction".format(
                    serial))
                raise PolicyError("The U2F device is not allowed "
                                  "to be registered due to policy "
                                  "restriction.")
                # TODO: Maybe we should delete the token, as it is a not
                # usable U2F token, now.

    return True


def allowed_audit_realm(request=None, action=None):
    """
    This decorator function takes the request and adds additional parameters 
    to the request according to the policy
    for the SCOPE.ADMIN or ACTION.AUDIT
    :param request:
    :param action:
    :return: True
    """
    admin_user = g.logged_in_user
    policy_object = g.policy_object
    pols = policy_object.get_policies(
        action=ACTION.AUDIT,
        scope=SCOPE.ADMIN,
        user=admin_user.get("username"),
        client=g.client_ip,
        active=True)

    if pols:
        # get all values in realm:
        allowed_audit_realms = []
        for pol in pols:
            if pol.get("realm"):
                allowed_audit_realms += pol.get("realm")
        request.all_data["allowed_audit_realm"] = list(set(
            allowed_audit_realms))

    return True


