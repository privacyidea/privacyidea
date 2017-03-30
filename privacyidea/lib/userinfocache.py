# -*- coding: utf-8 -*-
#
#  2017-03-30   Friedrich Weber <friedrich.weber@netknights.it>
#               First ideas for a user information cache to improve performance
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

from privacyidea.lib.resolver import get_resolver_type
from privacyidea.models import UserInfo

log = logging.getLogger(__name__)

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

def build_query(username=None,
                realm=None,
                resolver=None,
                user_id=None):
    """
    Build and return a SQLAlchemy query that searches the userinfo cache for a combination
    of username, realm, resolver and user ID.
    :return: SQLAlchemy Query
    """
    query = UserInfo.query
    if username is not None:
        query = query.filter(UserInfo.username == username)
    if realm is not None:
        query = query.filter(UserInfo.realm == realm)
    if resolver is not None:
        query = query.filter(UserInfo.resolver == resolver)
    if user_id is not None:
        query = query.filter(UserInfo.user_id == user_id)
    return query

def cache_username(func):
    """
    Decorator that adds a userinfo cache lookup to a function that looks up user names
    based on a user ID and a resolver name.
    Raises a RuntimeError in case of an inconsistent cache.
    """
    @functools.wraps(func)
    def userinfo_cache_wrapper(userid, resolvername):
        # try to fetch the record from the userinfo cache
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
                        "User info cache contains {!r} usernames for user ID {!r} and resolver {!r}".format(
                            len(usernames), userid, resolvername))
        else:
            # record was not found in the cache
            return func(userid, resolvername)

    return userinfo_cache_wrapper

def cache_resolver(func):
    """
    Decorator that adds a userinfo cache lookup to a method that looks up and sets the
    resolver of a specific user.
    May raise a RuntimeError if the cache is inconsistent.
    """
    @functools.wraps(func)
    def resolver_cache_wrapper(self, all_resolvers=False):
        # exit early if the resolver is already known
        if self.resolver:
            return [self.resolver]
        if self.login and self.realm:
            # tne user is identifiable by login name and realm
            result = one_or_none(build_query(username=self.login, realm=self.realm))
            if result is not None:
                # set and return the resolver
                log.debug('Set resolver of {!r} from cache: {!r}'.format(self, result.resolver))
                self.resolver = result.resolver
                return [self.resolver]
            else:
                # not found in the cache, call original function
                return func(self, all_resolvers)
        else:
            # user object has no proper login or realm name, call original function
            log.debug('{!r} misses loginname or realm, falling back to resolver lookup'.format(self))
            return func(self, all_resolvers)

    return resolver_cache_wrapper

def cache_identifiers(func):
    """
    Decorator that adds a userinfo cache lookup to a method that returns a user's identifiers
    consisting of (uid, resolvertype, resolver).
    """
    @functools.wraps(func)
    def identifiers_cache_wrapper(self):
        # TODO: review the query: should we really filter for the resolver?
        result = one_or_none(build_query(username=self.login, realm=self.realm, resolver=self.resolver))
        if result is not None:
            rtype = get_resolver_type(result.resolver)
            identifiers = (result.user_id, rtype, result.resolver)
            log.debug('Found identifiers of {!r} in cache: {!r}'.format(self, identifiers))
            return identifiers
        else:
            return func(self)
    return identifiers_cache_wrapper