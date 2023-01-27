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
from privacyidea.models import UserCache, db
from sqlalchemy import and_

log = logging.getLogger(__name__)
EXPIRATION_SECONDS = "UserCacheExpiration"


class user_cache(object):
    """
    This is the decorator wrapper to call a specific resolver function to
    allow user caching.
    If the user cache is disabled, the decorator wrapper is not called and
    the original function's result is returned instead.
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
        The returned wrapper checks if the cache is enabled. If it is disabled, the
        original function is called.

        :param wrapped_function: The function, that is decorated.
        :return: None
        """
        @functools.wraps(wrapped_function)
        def cache_wrapper(*args, **kwds):
            if is_cache_enabled():
                return self.decorator_function(wrapped_function, *args, **kwds)
            else:
                return wrapped_function(*args, **kwds)

        return cache_wrapper


def get_cache_time():
    """
    :return: UserCacheExpiration config value as a timedelta
    :rtype: timedelta
    """
    seconds = 0
    try:
        seconds = int(get_from_config(EXPIRATION_SECONDS, '0'))
    except ValueError:
        log.info("Non-Integer value stored in system config {0!s}".format(EXPIRATION_SECONDS))

    return datetime.timedelta(seconds=seconds)


def is_cache_enabled():
    """
    :return: True if the user cache is enabled (i.e. UserCacheExpiration is non-zero)
    """
    return bool(get_cache_time())


def delete_user_cache(resolver=None, username=None, expired=None):
    """
    This completely deletes the user cache.
    If no parameter is given, it deletes the user cache completely.

    :param resolver: Will only delete entries of this resolver
    :param username: Will only delete entries of this username
    :param expired: Will delete expired (True) or non-expired (False) entries
        or will not care about the expiration date (None)

    :return: number of deleted entries
    :rtype: int
    """
    filter_condition = create_filter(username=username, resolver=resolver,
                                     expired=expired)
    rowcount = db.session.query(UserCache).filter(filter_condition).delete()
    db.session.commit()
    log.info('Deleted {} entries from the user cache (resolver={!r}, username={!r}, expired={!r})'.format(
        rowcount, resolver, username, expired
    ))
    return rowcount


def add_to_cache(username, used_login, resolver, user_id):
    """
    Add the given record to the user cache, if it is enabled.
    The user cache is considered disabled if the config option
    EXPIRATION_SECONDS is set to 0.
    :param username: login name of the user
    :param used_login: login name that was used in request
    :param resolver: resolver name of the user
    :param user_id: ID of the user in its resolver
    """
    if is_cache_enabled():
        timestamp = datetime.datetime.now()
        record = UserCache(username, used_login, resolver, user_id, timestamp)
        log.debug('Adding record to cache: ({!r}, {!r}, {!r}, {!r}, {!r})'.format(
            username, used_login, resolver, user_id, timestamp))
        record.save()


def retrieve_latest_entry(filter_condition):
    """
    Return the most recently added entry in the user cache matching the given filter condition, or None.
    :param filter_condition: SQLAlchemy filter, as created (for example) by create_filter
    :return: A `UserCache` object or None, if no entry matches the given condition.
    """
    return UserCache.query.filter(filter_condition).order_by(UserCache.timestamp.desc()).first()


def create_filter(username=None, used_login=None, resolver=None,
                  user_id=None, expired=False):
    """
    Build and return a SQLAlchemy query that searches the UserCache cache for a combination
    of username, resolver and user ID. This also takes the expiration time into account.

    :param username: will filter for username
    :param used_login: will filter for used_login
    :param resolver: will filter for this resolver name
    :param user_id: will filter for this user ID
    :param expired: Can be True/False/None. If set to False will return
        only non-expired entries. If set to True, it will return only expired entries.
        If set to None, it will return expired as well as non-expired entries.

    :return: SQLAlchemy Filter
    """
    conditions = []
    if expired:
        cache_time = get_cache_time()
        conditions.append(
            UserCache.timestamp < datetime.datetime.now() - cache_time)
    elif expired is False:
        cache_time = get_cache_time()
        conditions.append(UserCache.timestamp >= datetime.datetime.now() - cache_time)

    if username:
        conditions.append(UserCache.username == username)
    if used_login:
        conditions.append(UserCache.used_login == used_login)
    if resolver:
        conditions.append(UserCache.resolver == resolver)
    if user_id:
        conditions.append(UserCache.user_id == user_id)
    filter_condition = and_(*conditions)
    return filter_condition


def cache_username(wrapped_function, userid, resolvername):
    """
    Decorator that adds a UserCache lookup to a function that looks up user
    names based on a user ID and a resolver name.
    After a successful lookup, the entry is added to the cache.
    """

    # try to fetch the record from the UserCache
    filter_conditions = create_filter(user_id=userid,
                                      resolver=resolvername)
    result = retrieve_latest_entry(filter_conditions)
    if result:
        username = result.username
        log.debug('Found username of {!r}/{!r} in cache: {!r}'.format(userid, resolvername, username))
        return username
    else:
        # record was not found in the cache
        username = wrapped_function(userid, resolvername)
        if username:
            # If we could figure out a user name, add the record to the cache.
            add_to_cache(username, username, resolvername, userid)
        return username


def user_init(wrapped_function, self):
    """
    Decorator to decorate the User creation function

    :param wrapped_function:
    :param self:
    :return:
    """
    if self.resolver:
        resolvers = [self.resolver]
    else:
        # In order to query the user cache, we need to find out the resolver
        resolvers = self.get_ordererd_resolvers()
    for resolvername in resolvers:
        # If we could figure out a resolver, we can query the user cache
        filter_conditions = create_filter(used_login=self.used_login, resolver=resolvername)
        result = retrieve_latest_entry(filter_conditions)
        if result:
            # Cached user exists, retrieve information and exit early
            self.login = result.username
            self.resolver = result.resolver
            self.uid = result.user_id
            return
        else:
            # If the user does not exist in the cache, we actually query the resolver
            # before moving on to the next resolver in the prioritized list.
            # This is important in the following scenario:
            # We have a realm with two resolvers, resolverA and resolverB,
            # a user foo has been located in resolverB and a corresponding cache entry
            # has been added.
            # Now, if a user of the same name is added to the store associated with resolverA,
            # we want to notice! This is why we actually query resolverA if there is no
            # cache entry associating foo with resolverA before checking the cache entries
            # of resolverB. Otherwise, we could end up with a cache that associates foo with
            # resolverB even though it should be associated with resolverA.
            if self._locate_user_in_resolver(resolvername):
                break
    # Either we could not determine a resolver or we could, but the user is not in cache.
    # We need to get additional information from the userstore.
    wrapped_function(self)
    # If the user object is complete, add it to the cache.
    if self.login and self.resolver and self.uid and self.used_login:
        # We only cache complete sets!
        add_to_cache(self.login, self.used_login, self.resolver, self.uid)

