# -*- coding: utf-8 -*-
#
#  2015-03-15 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add decorator for losttoken
#  2015-02-06 Cornelius Kölbel <cornelius@privacyidea.org>
#             Rewrite for flask migration.
#             Policies handled by decorators as
#             1. precondition for API calls
#             2. internal modifications of LIB-functions
#             3. postcondition for API calls
#
#  Jul 07, 2014 add check_machine_policy, Cornelius Kölbel
#  May 08, 2014 Cornelius Kölbel
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
# MERCHANTABILITY or FITNE7SS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
These are the policy decorator functions for internal (lib) policy decorators.
policy decorators for the API (pre/post) are defined in api/lib/policy

The functions of this module are tested in tests/test_lib_policy_decorator.py
"""
import logging
from privacyidea.lib.error import PolicyError
import functools
from privacyidea.lib.policy import ACTION, SCOPE, ACTIONVALUE, LOGINMODE
from privacyidea.lib.user import User

log = logging.getLogger(__name__)


class libpolicy(object):
    """
    This is the decorator wrapper to call a specific function before a
    library call in contrast to prepolicy and postpolicy, which are to be
    called in API Calls.

    The decorator expects a named parameter "options". In this options dict
    it will look for the flask global "g".
    """
    def __init__(self, decorator_function):
        """
        :param decorator_function: This is the policy function that is to be
        called
        :type decorator_function: function
        """
        self.decorator_function = decorator_function

    def __call__(self, wrapped_function):
        """
        This decorates the given function.
        If some error occur the a PolicyException is raised.

        The decorator function takes the options parameter and can modify
        the behaviour of the original function.

        :param wrapped_function: The function, that is decorated.
        :type wrapped_function: API function
        :return: None
        """
        @functools.wraps(wrapped_function)
        def policy_wrapper(*args, **kwds):
            return self.decorator_function(wrapped_function, *args, **kwds)

        return policy_wrapper


def challenge_response_allowed(func):
    """
    This decorator is used to wrap tokenclass.is_challenge_request.
    It checks, if a challenge response authentication is allowed for this
    token type. To allow this, the policy

    scope:authentication, action:challenge_response must be set.

    If the tokentype is not allowed for challenge_response, this decorator
    returns false.

    See :ref:`policy_challenge_response`.

    :param func: wrapped function
    """
    @functools.wraps(func)
    def challenge_response_wrapper(*args, **kwds):
        options = kwds.get("options", {})
        g = options.get("g")
        token = args[0]
        passw = args[1]
        clientip = options.get("clientip")
        user_object = kwds.get("user") or User()
        if g:
            policy_object = g.policy_object
            allowed_tokentypes = policy_object.get_action_values(
                action=ACTION.CHALLENGERESPONSE,
                scope=SCOPE.AUTH,
                realm=user_object.realm,
                user=user_object.login,
                client=clientip)
            log.debug("Found these allowed tokentypes: %s" % allowed_tokentypes)

            # allowed_tokentypes is a list of actions from several policies. I
            # could look like this:
            # ["tiqr hotp totp", "tiqr motp"]
            # We need to create a upper case list of pure tokentypes.
            token_list = " ".join(allowed_tokentypes)
            token_list = token_list.split(" ")
            # uniquify
            token_list = list(set(token_list))
            # uppercase
            token_list = [x.upper() for x in token_list]
            if token.get_tokentype().upper() not in token_list:
                # The chal resp is not defined for this tokentype
                # This is no challenge response request!
                return False

        f_result = func(*args, **kwds)
        return f_result

    return challenge_response_wrapper


def auth_user_has_no_token(wrapped_function, user_object, passw,
                           options=None):
    """
    This decorator checks if the user has a token at all.
    If the user has a token, the wrapped function is called.

    The wrapped function is usually token.check_user_pass, which takes the
    arguments (user, passw, options={})

    :param wrapped_function:
    :param user_object:
    :param passw:
    :param options: Dict containing values for "g" and "clientip"
    :return: Tuple of True/False and reply-dictionary
    """
    from privacyidea.lib.token import get_tokens
    options = options or {}
    g = options.get("g")
    if g:
        clientip = options.get("clientip")
        policy_object = g.policy_object
        pass_no_token = policy_object.get_policies(action=ACTION.PASSNOTOKEN,
                                                   scope=SCOPE.AUTH,
                                                   realm=user_object.realm,
                                                   user=user_object.login,
                                                   client=clientip, active=True)
        if len(pass_no_token) > 0:
            # Now we need to check, if the user really has no token.
            tokencount = get_tokens(user=user_object, count=True)
            if tokencount == 0:
                return True, {"message": "The user has not token, but is "
                                         "accepted due to policy '%s'." %
                                         pass_no_token[0].get("name")}

    # If nothing else returned, we return the wrapped function
    return wrapped_function(user_object, passw, options)


def auth_user_does_not_exist(wrapped_function, user_object, passw,
                               options=None):
    """
    This decorator checks, if the user does exist at all.
    If the user does exist, the wrapped function is called.

    The wrapped function is usually token.check_user_pass, which takes the
    arguments (user, passw, options={})

    :param wrapped_function:
    :param user_object:
    :param passw:
    :param options: Dict containing values for "g" and "clientip"
    :return: Tuple of True/False and reply-dictionary
    """
    options = options or {}
    g = options.get("g")
    if g:
        clientip = options.get("clientip")
        policy_object = g.policy_object
        pass_no_user = policy_object.get_policies(action=ACTION.PASSNOUSER,
                                                  scope=SCOPE.AUTH,
                                                  realm=user_object.realm,
                                                  user=user_object.login,
                                                  client=clientip,
                                                  active=True)
        if len(pass_no_user) > 0:
            return True, {"message": "The user does not exist, but is "
                                     "accepted due to policy '%s'." %
                                     pass_no_user[0].get("name")}

    # If nothing else returned, we return the wrapped function
    return wrapped_function(user_object, passw, options)


def auth_user_passthru(wrapped_function, user_object, passw, options=None):
    """
    This decorator checks the policy settings of ACTION.PASSTHRU.
    If the authentication against the userstore is not successful,
    the wrapped function is called.

    The wrapped function is usually token.check_user_pass, which takes the
    arguments (user, passw, options={})

    :param wrapped_function:
    :param user_object:
    :param passw:
    :param options: Dict containing values for "g" and "clientip"
    :return: Tuple of True/False and reply-dictionary
    """
    from privacyidea.lib.token import get_tokens
    options = options or {}
    g = options.get("g")
    if g:
        clientip = options.get("clientip")
        policy_object = g.policy_object
        pass_thru = policy_object.get_policies(action=ACTION.PASSTHRU,
                                               scope=SCOPE.AUTH,
                                               realm=user_object.realm,
                                               user=user_object.login,
                                               client=clientip, active=True)
        if len(pass_thru) > 0:
            # If the user has NO Token, authenticate against the user store
            if get_tokens(user=user_object, count=True) == 0:
                # Now we need to check the userstore password
                if user_object.check_password(passw):
                    return True, {"message": "The user authenticated against his "
                                             "userstore according to "
                                             "policy '%s'." %
                                             pass_thru[0].get("name")}

    # If nothing else returned, we return the wrapped function
    return wrapped_function(user_object, passw, options)


def login_mode(wrapped_function, *args, **kwds):
    """
    Decorator to decorate the lib.auth.check_webui_user function.
    Depending on ACTION.LOGINMODE it sets the check_otp parameter, to signal
    that the authentication should be performed against privacyIDEA.

    :param wrapped_function: Usually the function check_webui_user
    :param args: arguments user_obj and password
    :param kwds: keyword arguments like options and !check_otp!
    kwds["options"] contains the flask g
    :return: calls the original function with the modified "check_otp" argument
    """
    ERROR = "There are contradicting policies for the action %s!" % \
            ACTION.LOGINMODE
    # if tokenclass.check_pin is called in any other way, options may be None
    #  or it might have no element "g".
    options = kwds.get("options") or {}
    g = options.get("g")
    if g:
        # We need the user but we do not need the password
        user_object = args[0]
        clientip = options.get("clientip")
        # get the policy
        policy_object = g.policy_object
        login_mode_list = policy_object.get_action_values(ACTION.LOGINMODE,
                                                          scope=SCOPE.WEBUI,
                                                          realm=user_object.realm,
                                                          user=user_object.login,
                                                          client=clientip)

        if len(login_mode_list) > 0:
            # There is a login mode policy
            # reduce the list:
            login_mode_list = list(set(login_mode_list))
            if len(login_mode_list) > 1:  # pragma: no cover
                # We can not decide how to handle the request, so we raise an
                # exception
                raise PolicyError(ERROR)

            if login_mode_list[0] == LOGINMODE.PRIVACYIDEA:
                # The original function should check against privacyidea!
                kwds["check_otp"] = True

            if login_mode_list[0] == LOGINMODE.DISABLE:
                # The login to the webui is disabled
                raise PolicyError("The login for this user is disabled.")

    return wrapped_function(*args, **kwds)


def auth_otppin(wrapped_function, *args, **kwds):
    """
    Decorator to decorate the tokenclass.check_pin function.
    Depending on the ACTION.OTPPIN it
    * either simply accepts an empty pin
    * checks the pin against the userstore
    * or passes the request to the wrapped_function

    :param wrapped_function: In this case the wrapped function should be
    tokenclass.check_ping
    :param *args: args[1] is the pin
    :param **kwds: kwds["options"] contains the flask g
    :return: True or False
    """
    ERROR = "There are contradicting policies for the action %s!" % \
            ACTION.OTPPIN
    # if tokenclass.check_pin is called in any other way, options may be None
    #  or it might have no element "g".
    options = kwds.get("options") or {}
    g = options.get("g")
    if g:
        token = args[0]
        pin = args[1]
        clientip = options.get("clientip")
        user_object = kwds.get("user")
        if not user_object:
            # No user in the parameters, so we need to determine the owner of
            #  the token
            user_object = token.get_user()
            realms = token.get_realms()
            if not user_object and len(realms):
                # if the token has not owner, we take a realm.
                user_object = User("", realm=realms[0])
        if not user_object:
            # If we still have no user and no tokenrealm, we create an empty
            # user object.
            user_object=User("", realm="")
        # get the policy
        policy_object = g.policy_object
        otppin_list = policy_object.get_action_values(ACTION.OTPPIN,
                                                      scope=SCOPE.AUTH,
                                                      realm=user_object.realm,
                                                      user=user_object.login,
                                                      client=clientip)
        if len(otppin_list) > 0:
            # There is an otppin policy
            # reduce the list:
            otppin_list = list(set(otppin_list))
            if len(otppin_list) > 1:
                # We can not decide how to handle the request, so we raise an
                # exception
                raise PolicyError(ERROR)

            if otppin_list[0] == ACTIONVALUE.NONE:
                if pin == "":
                    # No PIN checking, we expect an empty PIN!
                    return True
                else:
                    return False

            if otppin_list[0] == ACTIONVALUE.USERSTORE:
                rv = user_object.check_password(pin)
                return rv is not None

    # call and return the original check_pin function
    return wrapped_function(*args, **kwds)


def config_lost_token(wrapped_function, *args, **kwds):
    """
    Decorator to decorate the lib.token.lost_token function.
    Depending on ACTION.LOSTTOKENVALID, ACTION.LOSTTOKENPWCONTENTS,
    ACTION.LOSTTOKENPWLEN it sets the check_otp parameter, to signal
    how the lostToken should be generated.

    :param wrapped_function: Usually the function lost_token()
    :param args: argument "serial" as the old serial number
    :param kwds: keyword arguments like "validity", "contents", "pw_len"
    kwds["options"] contains the flask g

    :return: calls the original function with the modified "validity",
    "contents" and "pw_len" argument
    """
    # if called in any other way, options may be None
    #  or it might have no element "g".
    from privacyidea.lib.token import get_tokens
    options = kwds.get("options") or {}
    g = options.get("g")
    if g:
        # We need the old serial number, to determine the user - if it exist.
        serial = args[0]
        toks = get_tokens(serial=serial)
        if len(toks) == 1:
            username = None
            realm = None
            user_object = toks[0].get_user()
            if user_object:
                username = user_object.login
                realm = user_object.realm
            clientip = options.get("clientip")
            # get the policy
            policy_object = g.policy_object
            contents_list = policy_object.get_action_values(
                ACTION.LOSTTOKENPWCONTENTS,
                scope=SCOPE.ENROLL,
                realm=realm,
                user=username,
                client=clientip)
            validity_list = policy_object.get_action_values(
                ACTION.LOSTTOKENVALID,
                scope=SCOPE.ENROLL,
                realm=realm,
                user=username,
                client=clientip)
            pw_len_list = policy_object.get_action_values(
                ACTION.LOSTTOKENPWLEN,
                scope=SCOPE.ENROLL,
                realm=realm,
                user=username,
                client=clientip)

            if len(contents_list) > 0:
                contents_list = list(set(contents_list))
                if len(contents_list) > 1:  # pragma: no cover
                    # We can not decide how to handle the request, so we raise an
                    # exception
                    raise PolicyError("There are contradicting policies for the "
                                      "action %s" % ACTION.LOSTTOKENPWCONTENTS)
                kwds["contents"] = contents_list[0]

            if len(validity_list) > 0:
                validity_list = list(set(validity_list))
                if len(validity_list) > 1:  # pragma: no cover
                    # We can not decide how to handle the request, so we raise an
                    # exception
                    raise PolicyError("There are contradicting policies for the "
                                      "action %s" % ACTION.LOSTTOKENVALID)
                kwds["validity"] = int(validity_list[0])

            if len(pw_len_list) > 0:
                pw_len_list = list(set(pw_len_list))
                if len(pw_len_list) > 1:  # pragma: no cover
                    # We can not decide how to handle the request, so we raise an
                    # exception
                    raise PolicyError("There are contradicting policies for the "
                                      "action %s" % ACTION.LOSTTOKENPWLEN)
                kwds["pw_len"] = int(pw_len_list[0])

    return wrapped_function(*args, **kwds)

