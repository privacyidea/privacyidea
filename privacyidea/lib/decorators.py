# -*- coding: utf-8 -*-
#
#  2016-02-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add caching decorator
#
#  (c) Cornelius Kölbel
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

import logging
import functools
from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.error import ParameterError
from flask import request, current_app
from gettext import gettext as _
import redis
import cPickle as pickle
from privacyidea.lib.resolvers.UserIdResolver import UserIdResolver


log = logging.getLogger(__name__)


def cached(time=5, skip_args=0):
    """
    Decorator that caches the result of a method for the specified time in
    seconds.

    :param time: The time in seconds to cache the result
    :param skip_args: number of the args to skip. Usually this would be 1 in
        case of LDAP.

    Use it as:

    @cached(time=1200)
    def get_user(arguments):
      ...
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            redis_url = current_app.config.get("PI_REDIS_URL")
            if redis_url:
                redis_up = True
                prefix = ""
                if skip_args:
                    if isinstance(args[0], UserIdResolver):
                        # In case of LDAP, we need to prefix the ResolverID!
                        prefix = args[0].resolverId
                cache = redis.Redis.from_url(redis_url)
                # args[0] contains the Instance of the LDAP Resolver
                key = '%s_%s_%s_%s' % (prefix,
                                       function.__name__,
                                       str(args[skip_args:]),
                                       str(kwargs))
                # Spaces are not allowed in key
                key = key.replace(' ', '_')
                try:
                    svalue = cache.get(key)
                except redis.ConnectionError as exx:
                    log.error('Failed to get key from redis: %s' % exx)
                    redis_up = False
                    svalue = None
                if svalue:
                    log.debug('Cache lookup for %s: Hit found' % key)
                    value = pickle.loads(svalue)
                else:
                    log.debug('Cache lookup for %s: Cache empty' % key)
                    value = function(*args, **kwargs)
                    if redis_up:
                        svalue = pickle.dumps(value)
                        log.debug("Saving %s for %i seconds" % (key, time))
                        cache.setex(key, svalue, time)
            else:
                value = function(*args, **kwargs)

            return value
        return wrapper
    return decorator


def check_token_locked(func):
    """
    Decorator to check if a token is locked or not.
    The decorator is to be used in token class methods.
    It can be used to avoid performing an action on a locked token.

    If the token is locked, a TokenAdminError is raised.
    """
    @functools.wraps(func)
    def token_locked_wrapper(*args, **kwds):
        # The token object
        token = args[0]
        if token.is_locked():
            raise TokenAdminError(_("This action is not possible, since the "
                                    "token is locked"), id=1007)
        f_result = func(*args, **kwds)
        return f_result

    return token_locked_wrapper


def check_user_or_serial(func):
    """
    Decorator to check user and serial at the beginning of a function
    The wrapper will check the parameters user and serial and verify that
    not both parameters are None. Otherwise it will throw an exception
    ParameterError.
    """
    @functools.wraps(func)
    def user_or_serial_wrapper(*args, **kwds):
        # If there is no user and serial keyword parameter and if
        # there is no normal argument, we do not have enough information
        serial = kwds.get("serial")
        user = kwds.get("user")
        if serial is None and (len(args) == 0 or args[0] is None):
            # We have no serial! The serial would be the first arg
            if user is None or (user is not None and user.is_empty()):
                # We either have an empty User object or None
                raise ParameterError(ParameterError.USER_OR_SERIAL)

        f_result = func(*args, **kwds)
        return f_result

    return user_or_serial_wrapper


def check_user_or_serial_in_request(func):
    """
    Decorator to check user and serial in a request.
    If the request does not contain a serial number (serial) or a user
    (user) it will throw a ParameterError.
    """

    @functools.wraps(func)
    def check_user_or_serial_in_request_wrapper(*args, **kwds):
        user = request.all_data.get("user")
        serial = request.all_data.get("serial")
        if not serial and not user:
            raise ParameterError(_("You need to specify a serial or a user."))
        f_result = func(*args, **kwds)
        return f_result

    return check_user_or_serial_in_request_wrapper


def check_copy_serials(func):
    """
    Decorator to check if the serial_from and serial_to exist.
    If the serials are not unique, we raise an error
    """
    from privacyidea.lib.token import get_tokens
    @functools.wraps(func)
    def check_serial_wrapper(*args, **kwds):
        tokenobject_list_from = get_tokens(serial=args[0])
        tokenobject_list_to = get_tokens(serial=args[1])
        if len(tokenobject_list_from) != 1:
            log.error("not a unique token to copy from found")
            raise(TokenAdminError("No unique token to copy from found",
                                   id=1016))
        if len(tokenobject_list_to) != 1:
            log.error("not a unique token to copy to found")
            raise(TokenAdminError("No unique token to copy to found",
                                   id=1017))

        f_result = func(*args, **kwds)
        return f_result

    return check_serial_wrapper

