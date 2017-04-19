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


def delete_user_cache(resolver=None, username=None, expired=None):
    """
    This completely deletes the user cache.
    If no parameter is given, it deletes the user cache completely.

    :param resolver: Will only delete entries of this resolver
    :param username: Will only delete entries of this username
    :param expired: Will delete expired (True) or non-expired (False) entries
        or will not care about the expiration date (None)

    :return:
    """
    filter_condition = create_filter(username=username, resolver=resolver,
                                     expired=expired)
    rowcount = db.session.query(UserCache).filter(filter_condition).delete()
    db.session.commit()
    log.info('Deleted {} entries from the user cache (resolver={!r}, username={!r}, expired={!r})'.format(
        rowcount, resolver, username, expired
    ))
    return rowcount


def add_to_cache(username, resolver, user_id):
    """
    Add the given record to the user cache, if it is enabled.
    The user cache is considered disabled if the config option
    EXPIRATION_SECONDS is set to 0.
    :param username: login name of the user
    :param resolver: resolver name of the user
    :param user_id: ID of the user in its resolver
    """
    cache_time = get_cache_time()
    if cache_time:
        timestamp = datetime.datetime.now()
        record = UserCache(username, resolver, user_id, timestamp)
        log.debug('Adding record to cache: ({!r}, {!r}, {!r}, {!r})'.format(
            username, resolver, user_id, timestamp))
        record.save()


def retrieve_latest_entry(filter_condition):
    """
    Return the most recently added entry in the user cache matching the given filter condition, or None.
    :param filter_condition: SQLAlchemy filter, as created (for example) by create_filter
    :return: A `UserCache` object or None, if no entry matches the given condition.
    """
    return UserCache.query.filter(filter_condition).order_by(UserCache.timestamp.desc()).first()


def create_filter(username=None, resolver=None,
                  user_id=None, expired=False):
    """
    Build and return a SQLAlchemy query that searches the UserCache cache for a combination
    of username, resolver and user ID. This also takes the expiration time into account.

    :param username: will filter for username
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
            add_to_cache(username, resolvername, userid)
        return username


def user_init(wrapped_function, self):
    """
    Decorator to decorate the User creation function

    :param wrapped_function:
    :param self:
    :return:
    """
    if not self.resolver:
        # In order to query the user cache, we need to find out the resolver
        self._get_resolvers()
    if self.resolver:
        # If we could figure out a resolver, we can query the user cache
        filter_conditions = create_filter(username=self.login, resolver=self.resolver)
        result = retrieve_latest_entry(filter_conditions)
        if result:
            # Cached user exists, retrieve information and exit early
            self.resolver = result.resolver
            self.uid = result.user_id
            return

    # Either we could not determine a resolver or we could, but the user is not in cache.
    # We need to get additional information from the userstore.
    wrapped_function(self)
    # If the user object is complete, add it to the cache.
    if self.login and self.resolver and self.uid:
        # We only cache complete sets!
        add_to_cache(self.login, self.resolver, self.uid)

