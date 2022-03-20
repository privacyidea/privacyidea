# -*- coding: utf-8 -*-
#  2020-09-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Use Argon2
#  2017-08-11 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             initial writeup
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
from ..models import AuthCache, db
from sqlalchemy import and_
from passlib.hash import argon2
import datetime
import logging

ROUNDS = 9
log = logging.getLogger(__name__)


def _hash_password(password):
    return argon2.using(rounds=ROUNDS).hash(password)


def add_to_cache(username, realm, resolver, password):
    # Can not store timezone aware timestamps!
    first_auth = datetime.datetime.utcnow()
    auth_hash = _hash_password(password)
    record = AuthCache(username, realm, resolver, auth_hash, first_auth, first_auth)
    log.debug('Adding record to auth cache: ({!r}, {!r}, {!r}, {!r})'.format(
        username, realm, resolver, auth_hash))
    r = record.save()
    return r


def update_cache(cache_id):
    last_auth = datetime.datetime.utcnow()
    db.session.query(AuthCache).filter(
        AuthCache.id == cache_id).update({"last_auth": last_auth,
                                          AuthCache.auth_count: AuthCache.auth_count + 1})
    db.session.commit()


def delete_from_cache(username, realm, resolver, password, last_valid_cache_time=None, max_auths=0):
    """
    Deletes all authcache entries that match the user and either match the password, are expired, or have reached the
    maximum number of allowed authentications.

    :param username:
    :param realm:
    :param resolver:
    :param password:
    :param last_valid_cache_time: Oldest valid time for a cache entry to be still valid. I.e., if the first
    authentication of the entry is before this time point, it is not valid anymore.
    :param max_auths: Maximum number of allowed authentications.
    """
    cached_auths = db.session.query(AuthCache).filter(AuthCache.username == username,
                                                      AuthCache.realm == realm,
                                                      AuthCache.resolver == resolver).all()
    r = 0
    for cached_auth in cached_auths:
        delete_entry = False
        # if the password matches or the entry is otherwise invalid, we deleted it.
        try:
            if max_auths > 0 and cached_auth.auth_count >= max_auths:
                delete_entry = True
            elif last_valid_cache_time and cached_auth.first_auth < last_valid_cache_time:
                delete_entry = True
            elif argon2.verify(password, cached_auth.authentication):
                delete_entry = True

        except ValueError:
            log.debug("Old (non-argon2) authcache entry for user {0!s}@{1!s}.".format(username, realm))
            # Also delete old entries
            delete_entry = True
        if delete_entry:
            r += 1
            cached_auth.delete()
    db.session.commit()
    return r


def cleanup(minutes):
    """
    Will delete all authcache entries, where last_auth column is older than
    the given minutes.

    :param minutes: Age of the last_authentication in minutes
    :type minutes: int
    :return:
    """
    cleanuptime = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
    r = db.session.query(AuthCache).filter(AuthCache.last_auth < cleanuptime).delete()
    db.session.commit()
    return r


def verify_in_cache(username, realm, resolver, password, first_auth=None, last_auth=None,
                    max_auths=0):
    """
    Verify if the given credentials are cached and if the time is correct.
    
    :param username: 
    :param realm: 
    :param resolver: 
    :param password: 
    :param first_auth: The timestamp when the entry was first written to the 
        cache. Only find newer entries 
    :param last_auth: The timestamp when the entry was last successfully 
        verified. Only find newer entries
    :param max_auths: Maximum number of times the authcache entry can be used to skip
        authentication, as defined by ACTION.AUTH_CACHE policy. Will return False if the current number of
        authentications + 1 of the cached authentication exceeds this value.
    :type max_auths: int
    :return: 
    """
    conditions = []
    result = False
    conditions.append(AuthCache.username == username)
    conditions.append(AuthCache.realm == realm)
    conditions.append(AuthCache.resolver == resolver)

    if first_auth:
        conditions.append(AuthCache.first_auth > first_auth)
    if last_auth:
        conditions.append(AuthCache.last_auth > last_auth)

    filter_condition = and_(*conditions)
    cached_auths = AuthCache.query.filter(filter_condition).all()

    for cached_auth in cached_auths:
        try:
            result = argon2.verify(password, cached_auth.authentication)
        except ValueError:
            log.debug("Old (non-argon2) authcache entry for user {0!s}@{1!s}.".format(username, realm))
            result = False

        if result and max_auths > 0:
            # Check if auth_count allows this authentication too
            result = cached_auth.auth_count < max_auths

        if result:
            # Update the last_auth and the auth_count
            update_cache(cached_auth.id)
            break

    if not result:
        # Delete older entries
        delete_from_cache(username, realm, resolver, password, first_auth, max_auths)

    return result
