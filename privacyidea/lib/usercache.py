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
from privacyidea.lib.resolver import get_resolver_type
from privacyidea.models import UserCache

log = logging.getLogger(__name__)


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


def delete_user_cache():
    """
    This completely deletes the user cache
    :return:
    """
    r = UserCache.query.delete()
    return r


def get_expiration_delta_from_config():
    """
    Return a ``datetime.timedelta`` object that denotes the time after which
    a cache entry expires.
    """
    expiration_seconds = int(get_from_config('usercache.expirationSeconds', '0'))
    return datetime.timedelta(seconds=expiration_seconds)


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
    expiration_delta = get_expiration_delta_from_config()
    if expiration_delta:
        expiration = datetime.datetime.now() + expiration_delta
        record = UserCache(username, realm, resolver, user_id,
                           expiration=expiration)
        log.debug('Adding record to cache: ({!r}, {!r}, {!r}, {!r}, {!r})'.format(
            username, realm, resolver, user_id, expiration))
        record.save()


def build_query(username=None, realm=None, resolver=None, user_id=None):
    """
    Build and return a SQLAlchemy query that searches the UserCache cache for a combination
    of username, realm, resolver and user ID. This also takes the expiration time into account.
    :return: SQLAlchemy Query
    """
    query = UserCache.query.filter(UserCache.expiration > datetime.datetime.now())
    if username is not None:
        query = query.filter(UserCache.username == username)
    if realm is not None:
        query = query.filter(UserCache.realm == realm)
    if resolver is not None:
        query = query.filter(UserCache.resolver == resolver)
    if user_id is not None:
        query = query.filter(UserCache.user_id == user_id)
    return query


def cache_username(wrapped_function, userid, resolvername):
    """
    Decorator that adds a UserCache lookup to a function that looks up  user
    names based on a user ID and a resolver name.
    Raises a RuntimeError in case of an inconsistent cache.
    """

    # try to fetch the record from the UserCache
    results = build_query(user_id=userid, resolver=resolvername).all()
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


def cache_resolver(wrapped_function, self, all_resolvers=False):
    """
    Decorator that adds a user cache lookup to a method that looks up and sets
    the resolver of a specific user.
    May raise a RuntimeError if the cache is inconsistent.
    If the cache does not contain a matching record, the original function is
    invoked and the respective record is added to the cache (if possible).
    """
    # exit early if the resolver is already known
    if self.resolver:
        return [self.resolver]
    if self.login and self.realm:
        # tne user is identifiable by login name and realm
        result = one_or_none(build_query(username=self.login, realm=self.realm))
        if result is not None:
            # set and return the resolver
            log.debug('Set resolver and UID of {!r} from cache: {!r}, {!r}'.format(
                self, result.resolver, result.user_id))
            self.resolver = result.resolver
            self.uid = result.user_id
            return [self.resolver]
        else:
            # not found in the cache, call original function
            result = wrapped_function(self, all_resolvers)
            # now, `self` might have `resolver` and `uid` set
            if self.resolver and self.uid:
                add_to_cache(self.login, self.realm, self.resolver, self.uid)
            return result
    else:
        # user object has no proper login or realm name, call original function
        log.debug('{!r} misses loginname or realm, falling back to resolver lookup'.format(self))
        return wrapped_function(self, all_resolvers)


def cache_identifiers(wrapped_function, self):
    """
    Decorator that adds a user cache lookup to a method that returns a user's identifiers
    consisting of (uid, resolvertype, resolver).
    If the cache does not contain a matching record, the original function is invoked
    and the respective record is added to the cache.
    """
    # TODO: If `self` has `uid` set, we do not need to query the database at all!
    # TODO: review the query: should we really filter for the resolver?
    result = one_or_none(build_query(username=self.login, realm=self.realm, resolver=self.resolver))
    if result is not None:
        rtype = get_resolver_type(result.resolver)
        identifiers = (result.user_id, rtype, result.resolver)
        log.debug('Found identifiers of {!r} in cache: {!r}'.format(self, identifiers))
        return identifiers
    else:
        # not yet found in the cache: invoke original function and add to cache
        (user_id, rtype, resolver) = result = wrapped_function(self)
        if user_id:
            add_to_cache(self.login, self.realm, resolver, user_id)
        return result

