# -*- coding: utf-8 -*-
#
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
from privacyidea.lib.crypto import hash
import datetime
import logging

log = logging.getLogger(__name__)


def _hash_password(password):
    return hash(password, seed="")


def add_to_cache(username, realm, resolver, password):
    # Can not store timezone aware timestamps!
    first_auth = datetime.datetime.utcnow()
    auth_hash = _hash_password(password)
    record = AuthCache(username, realm, resolver, auth_hash, first_auth, first_auth)
    log.debug('Adding record to auth cache: ({!r}, {!r}, {!r}, {!r})'.format(
        username, realm, resolver, auth_hash))
    r = record.save()
    return r


def update_cache_last_auth(cache_id):
    last_auth = datetime.datetime.utcnow()
    AuthCache.query.filter(
        AuthCache.id == cache_id).update({"last_auth": last_auth})
    db.session.commit()


def delete_from_cache(username, realm, resolver, password):
    r = db.session.query(AuthCache).filter(AuthCache.username == username,
                                       AuthCache.realm == realm,
                                       AuthCache.resolver == resolver,
                                       AuthCache.authentication ==
                                       _hash_password(password)).delete()
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


def verify_in_cache(username, realm, resolver, password,
                    first_auth = None,
                    last_auth = None):
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
    :return: 
    """
    conditions = []
    conditions.append(AuthCache.username == username)
    conditions.append(AuthCache.realm == realm)
    conditions.append(AuthCache.resolver == resolver)
    auth_hash = _hash_password(password)
    conditions.append(AuthCache.authentication == auth_hash)

    if first_auth:
        conditions.append(AuthCache.first_auth > first_auth)
    if last_auth:
        conditions.append(AuthCache.last_auth > last_auth)

    filter_condition = and_(*conditions)
    r = AuthCache.query.filter(filter_condition).first()
    result = bool(r)

    if result:
        # Update the last_auth
        update_cache_last_auth(r.id)

    else:
        # Delete older entries
        delete_from_cache(username, realm, resolver, password)

    return result

