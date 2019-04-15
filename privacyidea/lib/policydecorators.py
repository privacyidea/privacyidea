# -*- coding: utf-8 -*-
#
#  2017-08-11 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add authcache decorator
#  2017-07-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             add resolver dependent policy for lastauth, otppin, passthru,
#             timelimit, losttoken
#  2015-10-31 Cornelius Kölbel <cornelius@privacyidea.org>
#             Added time_limit and last_auth
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
from privacyidea.lib.error import PolicyError, privacyIDEAError
import functools
from privacyidea.lib.policy import ACTION, SCOPE, ACTIONVALUE, LOGINMODE
from privacyidea.lib.user import User
from privacyidea.lib.utils import parse_timelimit, parse_timedelta
from privacyidea.lib.authcache import verify_in_cache, add_to_cache
import datetime
from dateutil.tz import tzlocal
from privacyidea.lib.radiusserver import get_radius

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
            allowed_tokentypes_dict = policy_object.get_action_values(
                action=ACTION.CHALLENGERESPONSE,
                scope=SCOPE.AUTH,
                realm=user_object.realm,
                resolver=user_object.resolver,
                user=user_object.login,
                client=clientip)
            log.debug("Found these allowed tokentypes: {0!s}".format(list(allowed_tokentypes_dict)))

            # allowed_tokentypes_dict.keys() is a list of actions from several policies. I
            # could look like this:
            # ["tiqr hotp totp", "tiqr motp"]
            chal_resp_found = False
            for toks in allowed_tokentypes_dict:
                if token.get_tokentype().upper() in [x.upper() for x in toks.split(" ")]:
                    # This token is allowed to to chal resp
                    chal_resp_found = True
                    g.audit_object.add_policy(allowed_tokentypes_dict.get(toks))

            if not chal_resp_found:
                # No policy to allow this token to do challenge response
                return False

        f_result = func(*args, **kwds)
        return f_result

    return challenge_response_wrapper


def auth_cache(wrapped_function, user_object, passw, options=None):
    """
    Decorate lib.token:check_user_pass. Verify, if the authentication can 
    be found in the auth_cache.
    
    :param wrapped_function: usually "check_user_pass"
    :param user_object: User who tries to authenticate
    :param passw: The PIN and OTP
    :param options: Dict containing values for "g" and "clientip".
    :return: Tuple of True/False and reply-dictionary
    """
    options = options or {}
    g = options.get("g")
    auth_cache_dict = None
    if g:
        clientip = options.get("clientip")
        policy_object = g.policy_object
        auth_cache_dict = policy_object.get_action_values(
            action=ACTION.AUTH_CACHE,
            scope=SCOPE.AUTH,
            realm=user_object.realm,
            resolver=user_object.resolver,
            user=user_object.login,
            client=clientip,
            unique=True)
        if auth_cache_dict:
            # verify in cache and return an early success
            auth_times = list(auth_cache_dict)[0].split("/")
            # determine first_auth from policy!
            first_offset = parse_timedelta(auth_times[0])

            if len(auth_times) == 2:
                # Determine last_auth from policy
                last_offset = parse_timedelta(auth_times[1])
            else:
                # If there is no last_auth, it is equal to first_auth
                last_offset = first_offset

            first_auth = datetime.datetime.utcnow() - first_offset
            last_auth = datetime.datetime.utcnow() - last_offset
            result = verify_in_cache(user_object.login, user_object.realm,
                                     user_object.resolver, passw,
                                     first_auth=first_auth,
                                     last_auth=last_auth)
            if result:
                g.audit_object.add_policy(next(iter(auth_cache_dict.values())))
                return True, {"message": "Authenticated by AuthCache."}

    # If nothing else returned, call the wrapped function
    res, reply_dict = wrapped_function(user_object, passw, options)
    if auth_cache_dict and res:
        # If authentication is successful, we store the password in auth_cache
        add_to_cache(user_object.login, user_object.realm, user_object.resolver, passw)
    return res, reply_dict


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
                                                   resolver=user_object.resolver,
                                                   user=user_object.login,
                                                   client=clientip, active=True)
        if pass_no_token:
            # Now we need to check, if the user really has no token.
            tokencount = get_tokens(user=user_object, count=True)
            if tokencount == 0:
                g.audit_object.add_policy([p.get("name") for p in pass_no_token])
                return True, {"message": u"user has no token, accepted due to '{!s}'".format(
                    pass_no_token[0].get("name"))}

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
                                                  resolver=user_object.resolver,
                                                  user=user_object.login,
                                                  client=clientip,
                                                  active=True)
        if pass_no_user:
            # Check if user object exists
            if not user_object.exist():
                g.audit_object.add_policy([p.get("name") for p in pass_no_user])
                return True, {"message": u"user does not exist, accepted due to '{!s}'".format(
                    pass_no_user[0].get("name"))}

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
        policy_object = g.policy_object
        clientip = options.get("clientip")
        pass_thru = policy_object.get_policies(action=ACTION.PASSTHRU,
                                               scope=SCOPE.AUTH,
                                               realm=user_object.realm,
                                               resolver=user_object.resolver,
                                               user=user_object.login,
                                               client=clientip,
                                               active=True,
                                               sort_by_priority=True)
        # We only go to passthru, if the user has no tokens!
        if pass_thru and get_tokens(user=user_object, count=True) == 0:
            # Ensure that there are no conflicting action values within the same priority
            policy_object.check_for_conflicts(pass_thru, "passthru")
            pass_thru_action = pass_thru[0].get("action").get("passthru")
            policy_name = pass_thru[0].get("name")
            if pass_thru_action in ["userstore", True]:
                # Now we need to check the userstore password
                if user_object.check_password(passw):
                    g.audit_object.add_policy([p.get("name") for p in pass_thru])
                    return True, {"message": u"against userstore due to '{!s}'".format(
                                      policy_name)}
            else:
                # We are doing RADIUS passthru
                log.info("Forwarding the authentication request to the radius "
                         "server %s" % pass_thru_action)
                radius = get_radius(pass_thru_action)
                r = radius.request(radius.config, user_object.login, passw)
                if r:
                    g.audit_object.add_policy([p.get("name") for p in pass_thru])
                    return True, {'message': u"against RADIUS server {!s} due to '{!s}'".format(
                                      pass_thru_action, policy_name)}

    # If nothing else returned, we return the wrapped function
    return wrapped_function(user_object, passw, options)


def auth_user_timelimit(wrapped_function, user_object, passw, options=None):
    """
    This decorator checks the policy settings of
    ACTION.AUTHMAXSUCCESS,
    ACTION.AUTHMAXFAIL
    If the authentication was successful, it checks, if the number of allowed
    successful authentications is exceeded (AUTHMAXSUCCESS).

    If the AUTHMAXFAIL is exceed it denies even a successful authentication.

    The wrapped function is usually token.check_user_pass, which takes the
    arguments (user, passw, options={})

    :param wrapped_function:
    :param user_object:
    :param passw:
    :param options: Dict containing values for "g" and "clientip"
    :return: Tuple of True/False and reply-dictionary
    """
    # First we call the wrapped function
    res, reply_dict = wrapped_function(user_object, passw, options)

    options = options or {}
    g = options.get("g")
    if g:

        clientip = options.get("clientip")
        policy_object = g.policy_object

        max_success_dict = policy_object.get_action_values(
            action=ACTION.AUTHMAXSUCCESS,
            scope=SCOPE.AUTHZ,
            realm=user_object.realm,
            resolver=user_object.resolver,
            user=user_object.login,
            client=clientip,
            unique=True)
        max_fail_dict = policy_object.get_action_values(
            action=ACTION.AUTHMAXFAIL,
            scope=SCOPE.AUTHZ,
            realm=user_object.realm,
            resolver=user_object.resolver,
            user=user_object.login,
            client=clientip,
            unique=True)
        # Check for maximum failed authentications
        # Always - also in case of unsuccessful authentication
        if len(max_fail_dict) == 1:
            policy_count, tdelta = parse_timelimit(list(max_fail_dict)[0])
            fail_c = g.audit_object.get_count({"user": user_object.login,
                                               "realm": user_object.realm,
                                               "action":
                                                   "%/validate/check"},
                                              success=False,
                                              timedelta=tdelta)
            log.debug("Checking users timelimit %s: %s "
                      "failed authentications" %
                      (list(max_fail_dict)[0], fail_c))
            if fail_c >= policy_count:
                res = False
                reply_dict["message"] = ("Only %s failed authentications "
                                         "per %s" % (policy_count, tdelta))
                g.audit_object.add_policy(next(iter(max_fail_dict.values())))

        if res:
            # Check for maximum successful authentications
            # Only in case of a successful authentication
            if len(max_success_dict) == 1:
                policy_count, tdelta = parse_timelimit(list(max_success_dict)[0])
                # check the successful authentications for this user
                succ_c = g.audit_object.get_count({"user": user_object.login,
                                                   "realm": user_object.realm,
                                                   "action":
                                                       "%/validate/check"},
                                                  success=True,
                                                  timedelta=tdelta)
                log.debug("Checking users timelimit %s: %s "
                          "succesful authentications" %
                          (list(max_success_dict)[0], succ_c))
                if succ_c >= policy_count:
                    res = False
                    reply_dict["message"] = ("Only %s successfull "
                                             "authentications per %s"
                                             % (policy_count, tdelta))

    return res, reply_dict


def auth_lastauth(wrapped_function, user_or_serial, passw, options=None):
    """
    This decorator checks the policy settings of ACTION.LASTAUTH
    If the last authentication stored in tokeninfo last_auth_success of a
    token is exceeded, the authentication is denied.

    The wrapped function is usually token.check_user_pass, which takes the
    arguments (user, passw, options={}) OR
    token.check_serial_pass with the arguments (user, passw, options={})

    :param wrapped_function: either check_user_pass or check_serial_pass
    :param user_or_serial: either the User user_or_serial or a serial
    :param passw:
    :param options: Dict containing values for "g" and "clientip"
    :return: Tuple of True/False and reply-dictionary
    """
    # First we call the wrapped function
    res, reply_dict = wrapped_function(user_or_serial, passw, options)

    options = options or {}
    g = options.get("g")
    if g and res:
        clientip = options.get("clientip")
        policy_object = g.policy_object

        # in case of a serial:
        realm = None
        login = None
        serial = user_or_serial
        try:
            # Assume we have a user
            realm = user_or_serial.realm
            resolver = user_or_serial.resolver
            login = user_or_serial.login
            serial = reply_dict.get("serial")
        except Exception:
            # in case of a serial:
            realm = None
            resolver = None
            login = None
            serial = user_or_serial

        # In case of a passthru policy we have no serial in the response
        # So we may only continue, if we have a serial.
        if serial:
            from privacyidea.lib.token import get_tokens
            try:
                token = get_tokens(serial=serial)[0]
            except IndexError:
                # In the special case of a registration token,
                # the token does not exist anymore. So we immediately return
                return res, reply_dict

            last_auth_dict = policy_object.get_action_values(
                action=ACTION.LASTAUTH,
                scope=SCOPE.AUTHZ,
                realm=realm,
                resolver=resolver,
                user=login,
                client=clientip, unique=True)

            if len(last_auth_dict) == 1:
                res = token.check_last_auth_newer(list(last_auth_dict)[0])
                if not res:
                    reply_dict["message"] = "The last successful " \
                                            "authentication was %s. " \
                                            "It is to long ago." % \
                                            token.get_tokeninfo(ACTION.LASTAUTH)
                    g.audit_object.add_policy(next(iter(last_auth_dict.values())))

            # set the last successful authentication, if res still true
            if res:
                token.add_tokeninfo(ACTION.LASTAUTH,
                                    datetime.datetime.now(tzlocal()))

    return res, reply_dict


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
        login_mode_dict = policy_object.get_action_values(
            ACTION.LOGINMODE,
            scope=SCOPE.WEBUI,
            realm=user_object.realm,
            resolver=user_object.resolver,
            user=user_object.login,
            client=clientip,
            unique=True,
            audit_data=g.audit_object.audit_data)

        if login_mode_dict:
            # There is a login mode policy
            if list(login_mode_dict)[0] == LOGINMODE.PRIVACYIDEA:
                # The original function should check against privacyidea!
                kwds["check_otp"] = True

            if list(login_mode_dict)[0] == LOGINMODE.DISABLE:
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
            user_object = token.user
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
        otppin_dict = policy_object.get_action_values(ACTION.OTPPIN,
                                                      scope=SCOPE.AUTH,
                                                      realm=user_object.realm,
                                                      resolver=user_object.resolver,
                                                      user=user_object.login,
                                                      client=clientip,
                                                      unique=True,
                                                      audit_data=g.audit_object.audit_data)
        if otppin_dict:
            if list(otppin_dict)[0] == ACTIONVALUE.NONE:
                if pin == "":
                    # No PIN checking, we expect an empty PIN!
                    return True
                else:
                    return False

            if list(otppin_dict)[0] == ACTIONVALUE.USERSTORE:
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
            resolver = None
            user_object = toks[0].user
            if user_object:
                username = user_object.login
                realm = user_object.realm
                resolver = user_object.resolver
            clientip = options.get("clientip")
            # get the policy
            policy_object = g.policy_object
            contents_dict = policy_object.get_action_values(
                ACTION.LOSTTOKENPWCONTENTS,
                scope=SCOPE.ENROLL,
                realm=realm,
                resolver=resolver,
                user=username,
                client=clientip,
                unique=True,
                audit_data=g.audit_object.audit_data)
            validity_dict = policy_object.get_action_values(
                ACTION.LOSTTOKENVALID,
                scope=SCOPE.ENROLL,
                realm=realm,
                resolver=resolver,
                user=username,
                client=clientip,
                unique=True,
                audit_data=g.audit_object.audit_data)
            pw_len_dict = policy_object.get_action_values(
                ACTION.LOSTTOKENPWLEN,
                scope=SCOPE.ENROLL,
                realm=realm,
                resolver=resolver,
                user=username,
                client=clientip,
                unique=True,
                audit_data=g.audit_object.audit_data)

            if contents_dict:
                kwds["contents"] = list(contents_dict)[0]

            if validity_dict:
                kwds["validity"] = int(list(validity_dict)[0])

            if pw_len_dict:
                kwds["pw_len"] = int(list(pw_len_dict)[0])

    return wrapped_function(*args, **kwds)


def reset_all_user_tokens(wrapped_function, *args, **kwds):
    """
    Resets all tokens if the corresponding policy is set.

    :param token: The successful token, the tokenowner is used to find policies.
    :param tokenobject_list: The list of all the tokens of the user
    :param options: options dictionary containing g.
    :return: None
    """
    tokenobject_list = args[0]
    options = kwds.get("options") or {}
    g = options.get("g")
    allow_reset = kwds.get("allow_reset_all_tokens")

    r = wrapped_function(*args, **kwds)

    # A successful authentication was done
    if r[0] and g and allow_reset:
        clientip = options.get("clientip")
        policy_object = g.policy_object
        token_owner = tokenobject_list[0].user
        reset_all = policy_object.get_policies(
            action=ACTION.RESETALLTOKENS,
            scope=SCOPE.AUTH,
            realm=token_owner.login if token_owner else None,
            resolver=token_owner.resolver if token_owner else None,
            user=token_owner.realm if token_owner else None,
            client=clientip, active=True,
            audit_data=g.audit_object.audit_data)
        if reset_all:
            log.debug("Reset failcounter of all tokens of {0!s}".format(
                token_owner))
            for tok_obj_reset in tokenobject_list:
                try:
                    tok_obj_reset.reset()
                except Exception:
                    log.debug(
                        "registration token does not exist anymore and "
                        "cannot be reset.")

    return r
