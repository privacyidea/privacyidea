# -*- coding: utf-8 -*-
#
#  2017-03-30   Friedrich Weber <friedrich.weber@netknights.it>
#               First ideas for a user cache to improve performance
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
import functools

import logging

import datetime

from privacyidea.lib.config import get_from_config
from privacyidea.models import UserCache
from sqlalchemy import and_

log = logging.getLogger(__name__)
EXPIRATION_SECONDS = "UserCacheExpiration"


class user_cache(object):
    """
    This is the decorator wrapper to call a specific resolver function to
    allow user caching.
    """

    def __init__(self, decorator_function):
        """
        :param decorator_function: This is the cache function that is to be
            called
        :type decorator_function: function
        """
        self.decorator_function = decorator_function

    def __call__(self, wrapped_function):
        """
        This decorates the given function.

        :param wrapped_function: The function, that is decorated.
        :return: None
        """
        @functools.wraps(wrapped_function)
        def cache_wrapper(*args, **kwds):
            return self.decorator_function(wrapped_function, *args, **kwds)

        return cache_wrapper


def get_cache_time():
    seconds = int(get_from_config(EXPIRATION_SECONDS, '0'))
    return datetime.timedelta(seconds=seconds)


def delete_user_cache():
    """
    This completely deletes the user cache
    :return:
    """
    r = UserCache.query.delete()
    return r


def one_or_none(query):
    """
    Given a SQLAlchemy query, ensure that it only has zero or one result and
    return None or the result, respectively. In case the query has more results,
    raise a RuntimeError.
    :param query: a SQLAlchemy Query
    :return: None or a row
    """
    results = query.all()
    length = len(results)
    if length == 0:
        return None
    elif length == 1:
        return results[0]
    else:
        raise RuntimeError('Expected one result, got {!r}'.format(length))


def add_to_cache(username, realm, resolver, user_id):
    """
    Add the given record to the user cache, if it is enabled.
    The user cache is considered disabled if the config option
    'usercache.expirationSeconds' is set to 0.
    :param username: login name of the user
    :param realm: realm name of the user
    :param resolver: resolver name of the user
    :param user_id: ID of the user in its resolver
    """
    # TODO: It is very possible that the entry did not exist in the cache when queried,
    # but was added in the meantime and exists now!
    # How do we handle that case?
    cache_time = get_cache_time()
    if cache_time:
        expiration = datetime.datetime.now() + cache_time
        record = UserCache(username, realm, resolver, user_id,
                           expiration=expiration)
        log.debug('Adding record to cache: ({!r}, {!r}, {!r}, {!r}, {!r})'.format(
            username, realm, resolver, user_id, expiration))
        record.save()


def create_filter(username=None, realm=None, resolver=None,
                  user_id=None):
    """
    Build and return a SQLAlchemy query that searches the UserCache cache for a combination
    of username, realm, resolver and user ID. This also takes the expiration time into account.
    :return: SQLAlchemy Query
    """
    cache_time = get_cache_time()
    conditions = []
    conditions.append(UserCache.timestamp >= datetime.datetime.now() - cache_time)
    if username:
        conditions.append(UserCache.username == username)
    if realm:
        conditions.append(UserCache.realm == realm)
    if resolver:
        conditions.append(UserCache.resolver == resolver)
    if user_id:
        conditions.append(UserCache.user_id == user_id)
    filter_condition = and_(*conditions)
    return filter_condition


def cache_username(wrapped_function, userid, resolvername):
    """
    Decorator that adds a UserCache lookup to a function that looks up  user
    names based on a user ID and a resolver name.
    Raises a RuntimeError in case of an inconsistent cache.
    """

    # try to fetch the record from the UserCache
    filter_conditions = create_filter(user_id=userid,
                                      resolver=resolvername)
    results = UserCache.query.filter(filter_conditions).all()
    if results:
        username = results[0].username
        if len(results) == 1:
            log.debug('Found username of {!r}/{!r} in cache: {!r}'.format(userid, resolvername, username))
            return username
        else:
            # more than one result was returned
            # check if all results produce the same username
            # if not: RuntimeError!
            usernames = set(result.username for result in results)
            if len(usernames) == 1:
                log.debug('Found {!r} entries of {!r}/{!r} in cache, all pointing to to: {!r}'.format(
                    len(usernames), userid, resolvername, username))
                return
            else:
                raise RuntimeError(
                    "User cache contains {!r} usernames for user ID {!r} and resolver {!r}".format(
                        len(usernames), userid, resolvername))
    else:
        # record was not found in the cache
        return wrapped_function(userid, resolvername)


def user_init(wrapped_function, self):
    filter_conditions = create_filter(username=self.login, realm=self.realm,
                                     resolver=self.resolver)
    result = one_or_none(UserCache.query.filter(filter_conditions))
    if result:
        # User is cached
        self.resolver = result.resolver
        self.uid = result.user_id

    else:
        # User is not in cache. We need to get additional information from
        # the userstore.
        wrapped_function(self)
        if self.login and self.realm and self.resolver and self.uid:
            # We only cache complete sets!
            cache_time = get_cache_time()
            add_to_cache(self.login, self.realm, self.resolver, self.uid)

