#  privacyIDEA is a fork of LinOTP
#
#  Nov 27, 2014 Cornelius Kölbel <cornelius@privacyidea.org>
#               Migration to flask
#               Rewrite of methods
#               100% test code coverage
#  May 08, 2014 Cornelius Kölbel
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
"""
These are the library functions to create, modify and delete realms in the
database. It depends on the lib.resolver.

It is independent of any user or token libraries and can be tested standalone
in tests/test_lib_realm.py
"""

from ..models import (Realm,
                      ResolverRealm,
                      Resolver, db, save_config_timestamp)
from .log import log_with
from privacyidea.lib.config import get_config_object
import logging
from privacyidea.lib.utils import sanity_name_check, fetch_one_resource, is_true
from privacyidea.lib.utils.export import (register_import, register_export)
from privacyidea.lib.error import DatabaseError

log = logging.getLogger(__name__)


@log_with(log)
#@cache.memoize(10)
def get_realms(realmname=None):
    """
    Either return all defined realms or a specific realm.
    The dictionary looks like this:

    {
      'realmname': {
        'id': <id of the realm>,
        'option': <>,
        'default': <default realm>,
        'resolver': [
          {
            'name': <resolver name>',
            'type': <resolver type>,
            'priority': <resolver priority>,
            'node': <resolver node>
          },
          {
            ...
          }
        ]
    }

    :param realmname: the realm, that is of interest. If not given, all realms
                      are returned
    :type realmname: string
    :return: a dictionary with the realm description
    :rtype: dict
    """
    config_object = get_config_object()
    realms = config_object.realm
    if realmname:
        if realmname in realms:
            realms = {realmname: realms.get(realmname)}
        else:
            realms = {}
    return realms


#@cache.memoize(10)
def get_realm(realmname):
    """
    :param realmname:
    :return: dict with the keys realmname, resolver. resolver being a dict
             with the keys name and type.
    :rtype: dict
    """
    r = get_realms(realmname).get(realmname)
    return r or {}


def get_realm_id(realmname):
    """
    Returns the realm_id for a realm name

    :param realmname: The name of the realm
    :return: The ID of the realm. If the realm does not exist, returns None.
    """
    return get_config_object().realm.get(realmname, {}).get("id")


@log_with(log)
def realm_is_defined(realm):
    """
    check, if a realm already exists or not

    :param realm: the realm, that should be verified
    :type  realm: string
    :return: found or not found
    :rtype: boolean
    """
    ret = False
    realms = get_realms()
    if realm.lower() in realms:
        ret = True
    return ret


@log_with(log)
def set_default_realm(default_realm=None):
    """
    set the default realm attribute.
    If the realm name is empty, the default realm is cleared.

    :param default_realm: the default realm name
    :type  default_realm: str or None
    :return: db ID of the realm set as default
    :rtype: int
    """
    res = 0
    r = Realm.query.filter_by(default=True).first()
    if r:
        # delete the old entry
        r.default = False
        r.save()
        res = r.id
    if default_realm:
        # set the new realm as default realm
        r = fetch_one_resource(Realm, name=default_realm)
        r.default = True
        r.save()
        res = r.id
    return res


@log_with(log)
#@cache.memoize(10)
def get_default_realm():
    """
    return the default realm
    - lookup in the config for the DefaultRealm key

    @return: the realm name
    @rtype : str
    """
    return get_config_object().default_realm


@log_with(log)
def delete_realm(realmname):
    """
    delete the realm from the Database Table with the given name
    If, after deleting this realm, there is only one realm left,
    the remaining realm is set the default realm.

    :param realmname: the to be deleted realm
    :type  realmname: string
    """
    # Check if there is a default realm
    def_realm = get_default_realm()
    had_def_realm_before = (def_realm != "")

    ret = fetch_one_resource(Realm, name=realmname).delete()

    # If there was a default realm before
    # and if there is only one realm left, we set the
    # remaining realm the default realm
    if had_def_realm_before is True:
        def_realm = get_default_realm()
        if not def_realm:
            realms = get_realms()
            if len(realms) == 1:
                for key in realms:
                    set_default_realm(key)

    return ret


@log_with(log)
def set_realm(realm, resolvers=None):
    """
    It takes a list of dictionaries describing the resolvers.
    The list looks like this:

      [ {'name': <resolvername1>,
         'node': <uuid of the node/optional>,
         'priority': <priority of the resolver/optional> },
        {'name': <resolvername2>
        }
      ]

    If the realm does not exist, it is created.
    If the realm exists, the old resolvers are removed and the new ones
    are added.

    :param realm: name of an existing or a new realm
    :type realm: str
    :param resolvers: list with names and options of resolvers
    :type resolvers: list of dicts
    :return: tuple of lists of added resolvers and resolvers, that could
             not be added
    :rtype: tuple
    .. versionchanged:: 3.10 accept a node in the resolver configuration
    """
    if resolvers is None:
        resolvers = []
    added = []
    failed = []
    realm_created = False
    realm = realm.lower().strip()
    realm = realm.replace(" ", "-")
    sanity_name_check(realm, r"^[A-Za-z0-9_\-\.]+$")

    # create new realm if it does not exist
    db_realm = Realm.query.filter_by(name=realm).first()
    if not db_realm:
        # create a new database entry for realm
        db_realm = Realm(realm)
        db_realm.save()
        realm_created = True

    if not realm_created:
        # delete old resolvers if we update the realm
        ResolverRealm.query.filter_by(realm_id=db_realm.id).delete()

    # assign the resolvers
    for reso in resolvers:
        reso_name = reso['name'].strip()
        db_reso = Resolver.query.filter_by(name=reso_name).first()
        if db_reso:
            try:
                ResolverRealm(db_reso.id, db_realm.id,
                              node_uuid=str(reso.get('node', '')),
                              priority=reso.get('priority')).save()
                added.append(reso_name)
            except DatabaseError as exx:
                log.warning(f"Could not add resolver {reso_name} to realm {realm}: {exx}")
                failed.append(reso_name)
        else:
            log.debug(f"Could not find resolver {reso_name} in database.")
            failed.append(reso_name)

    # if this is the first realm, make it the default
    if Realm.query.count() == 1:
        db_realm.default = True
        save_config_timestamp()
        db.session.commit()

    return added, failed


@register_export('realm')
def export_realms(name=None):
    """
    Export given realm configuration or all realms
    """
    return get_realms(realmname=name)


@register_import('realm')
def import_realms(data, name=None):
    """
    Import given realm configurations

    Ignores realm id and realm options
    """
    # TODO: the set_realm() function always creates the realm in the DB even if
    #  the associated resolver are not available. So the realms must be imported
    #  *after* the resolver.
    log.debug('Import realm config: {0!s}'.format(data))
    for realm, r_config in data.items():
        if name and name != realm:
            continue
        added, failed = set_realm(realm, resolvers=r_config.get('resolver', []))
        if is_true(r_config['default']):
            set_default_realm(realm)
        log.info('realm: {0!s:<15} resolver added: {1!s} '
                 'failed: {2!s}'.format(realm, added, failed))
