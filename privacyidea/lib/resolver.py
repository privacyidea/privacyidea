# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#
#  2018-12-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add censor-password functionality
#  2016-04-08 Cornelius Kölbel <cornelius@privacyidea.org>
#             simplify repetetive unequal checks
#
#  Nov 27, 2014 Cornelius Kölbel <cornelius@privacyidea.org>
#               Migration to flask
#               Rewrite of methods
#               100% test code coverage
#
#  May 08, 2014 Cornelius Kölbel
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
This is the library for creating new resolvers in the database and
deleting existing ones.
Also can create a resolver object of a class like LDAP, SQL or Passwd.

Its only dependencies are to the database model.py and to the
config.py, so this can be tested standalone without realms, tokens and
webservice!
"""

import logging

from .log import log_with
from .config import (get_resolver_types, get_resolver_classes, get_config_object)
from privacyidea.lib.usercache import delete_user_cache
from privacyidea.lib.framework import get_request_local_store
from ..models import (Resolver,
                      ResolverConfig)
from ..api.lib.utils import required
from ..api.lib.utils import getParam
from .error import ConfigAdminError
from sqlalchemy import func
from .crypto import encryptPassword
from privacyidea.lib.utils import (sanity_name_check, get_data_from_params,
                                   is_true)
from privacyidea.lib.utils.export import (register_import, register_export)
import copy

CENSORED = "__CENSORED__"
log = logging.getLogger(__name__)


# Hide the keyswords BINDPW and Password in params
@log_with(log, hide_args_keywords={0: ["BINDPW", "Password"]})
def save_resolver(params):
    """
    create a new resolver from request parameters
    and save the resolver in the database.

    If the resolver already exist, it is updated.
    If you update a resolver, you do not need to provide all parameters.
    Parameters you do not provide are left untouched.
    When updating a resolver you must not change the type!
    You do not need to specify the type, but if you specify a wrong type,
    it will produce an error.

    :param params: request parameters like "name" and "type" and the
                   configuration parameters of the resolver config.
    :type params: dict
    :return: the database ID of the resolver
    :rtype: int
    """
    # before we create the resolver in the database, we need to check
    # for the name and type thing...
    resolvername = getParam(params, 'resolver', required)
    resolvertype = getParam(params, 'type', required)
    update_resolver = False
    # check the name
    sanity_name_check(resolvername)
    # check the type
    resolvertypes = get_resolver_types()
    if resolvertype not in resolvertypes:
        raise Exception("resolver type : {0!s} not in {1!s}".format(resolvertype, str(resolvertypes)))

    # check the name
    resolvers = get_resolver_list(filter_resolver_name=resolvername)
    for r_name, resolver in resolvers.items():
        if resolver.get("type") == resolvertype:
            # We found the resolver with the same name and the same type,
            # So we will update this resolver
            update_resolver = True
        else:
            raise Exception("resolver with similar name and other type already "
                            "exists: %s" % r_name)

    # create a dictionary for the ResolverConfig
    resolver_config = get_resolver_config_description(resolvertype)
    config_description = resolver_config.get(resolvertype).get('config', {})

    data, types, desc = get_data_from_params(params, ['resolver', 'type'],
                                             config_description, resolvertype,
                                             resolvername)

    # Everything passed. So lets actually create the resolver in the DB
    if update_resolver:
        resolver_id = Resolver.query.filter(func.lower(Resolver.name) ==
                                  resolvername.lower()).first().id
    else:
        resolver = Resolver(params.get("resolver"),
                            params.get("type"))
        resolver_id = resolver.save()
    # create the config
    for key, value in data.items():
        if types.get(key) == "password":
            if value == CENSORED:
                continue
            else:
                value = encryptPassword(value)

        ResolverConfig(resolver_id=resolver_id,
                       Key=key,
                       Value=value,
                       Type=types.get(key, ""),
                       Description=desc.get(key, "")).save()

    # Remove corresponding entries from the user cache
    delete_user_cache(resolver=resolvername)

    return resolver_id


@log_with(log, log_exit=False)
#@cache.memoize(10)
def get_resolver_list(filter_resolver_type=None,
                      filter_resolver_name=None,
                      editable=None,
                      censor=False):
    """
    Gets the list of configured resolvers from the database

    :param filter_resolver_type: Only resolvers of the given type are returned
    :type filter_resolver_type: basestring
    :param filter_resolver_name: Get the distinct resolver
    :type filter_resolver_name: basestring
    :param editable: Whether only return editable resolvers
    :type editable: bool
    :param censor: censor sensitive data. Each resolver class decides on its own,
        which data should be censored.
    :type censor: bool
    :rtype: Dictionary of the resolvers and their configuration
    """
    config_object = get_config_object()
    if censor:
        resolvers = copy.deepcopy(config_object.resolver)
    else:
        resolvers = config_object.resolver
    if filter_resolver_type:
        reduced_resolvers = {}
        for reso_name, reso in resolvers.items():
            if reso.get("type") == filter_resolver_type:
                reduced_resolvers[reso_name] = resolvers[reso_name]
        resolvers = reduced_resolvers
    if filter_resolver_name:
        reduced_resolvers = {}
        for reso_name in resolvers:
            if reso_name.lower() == filter_resolver_name.lower():
                reduced_resolvers[reso_name] = resolvers[reso_name]
        resolvers = reduced_resolvers
    if editable is not None:
        reduced_resolvers = {}
        if editable is True:
            for reso_name, reso in resolvers.items():
                check_editable = is_true(reso["data"].get("Editable")) or \
                                 is_true(reso["data"].get("EDITABLE"))
                if check_editable:
                    reduced_resolvers[reso_name] = resolvers[reso_name]
        elif editable is False:
            for reso_name, reso in resolvers.items():
                check_editable = is_true(reso["data"].get("Editable")) or \
                                 is_true(reso["data"].get("EDITABLE"))
                if not check_editable:
                    reduced_resolvers[reso_name] = resolvers[reso_name]
        resolvers = reduced_resolvers
    if censor:
        for reso_name, reso in resolvers.items():
            for censor_key in reso.get("censor_keys", []):
                reso["data"][censor_key] = CENSORED

    return resolvers


@log_with(log)
def delete_resolver(resolvername):
    """
    delete a resolver and all related ResolverConfig entries
    If there was no resolver, that could be deleted, it returns -1

    :param resolvername: the name of the to be deleted resolver
    :type resolvername: string
    :return: The Id of the resolver
    :rtype: int
    """
    ret = -1

    reso = Resolver.query.filter_by(name=resolvername).first()
    if reso:
        if reso.realm_list:
            # The resolver is still contained in a realm! We must not delete it
            realmname = reso.realm_list[0].realm.name
            raise ConfigAdminError("The resolver %r is still contained in "
                                   "realm %r." % (resolvername, realmname))
        reso.delete()
        ret = reso.id
    # Delete resolver object from cache
    store = get_request_local_store()
    if 'resolver_objects' in store:
        if resolvername in store['resolver_objects']:
            del store['resolver_objects'][resolvername]

    # Remove corresponding entries from the user cache
    delete_user_cache(resolver=resolvername)

    return ret


@log_with(log, log_exit=False)
#@cache.memoize(10)
def get_resolver_config(resolvername):
    """
    return the complete config of a given resolver from the database
    :param resolvername: the name of the resolver
    :type resolvername: string
    :return: the config of the resolver
    :rtype: dict
    """
    reso = get_resolver_list(filter_resolver_name=resolvername)
    return reso.get(resolvername, {}).get("data", {})


@log_with(log)
#@cache.memoize(10)
def get_resolver_config_description(resolver_type):
    """
    get the configuration description of a resolver

    :param resolver_type: the type of the resolver. Something like
                          "passwdresolver".
    :type resolver_type: string
    :return: configuration description dict
             This should contain a key "config" that contains a dictionary
             and a key "clazz":
             {'passwdresolver': {'config': {'fileName': 'string'},
                                 'clazz': 'useridresolver.PasswdIdResolver'
                                          '.IdResolver'}}

    """
    descriptor = None
    resolver_class = get_resolver_class(resolver_type)

    if resolver_class is not None:
        descriptor = resolver_class.getResolverClassDescriptor()

    return descriptor


#@cache.memoize(10)
def get_resolver_class(resolver_type):
    """
    return the class object for a resolver type
    :param resolver_type: string specifying the resolver
                          fully qualified or abbreviated
    :return: resolver object class
    """
    ret = None
    resolver_clazzes = get_resolver_classes()
    for k in resolver_clazzes:
        if k.getResolverClassType() == resolver_type:
            ret = k
            break
    return ret


#@cache.memoize(10)
def get_resolver_type(resolvername):
    """
    return the type of a resolvername
    
    :param resolvername: THe name of the resolver
    :return: The type of the resolver
    :rtype: string
    """
    reso_list = get_resolver_list(filter_resolver_name=resolvername)
    r_type = reso_list.get(resolvername, {}).get("type")
    return r_type


@log_with(log)
#@cache.memoize(10)
def get_resolver_object(resolvername):
    """
    Return the cached resolver object for the given resolver name (stored in the request context).
    If no resolver object is cached, create it and add it to the cache.

    :param resolvername: the resolver string as from the token including
                         the config as last part
    :return: instance of the resolver with the loaded config

    """
    r_type = get_resolver_type(resolvername)
    r_obj_class = get_resolver_class(r_type)

    if r_obj_class is None:
        log.error("Can not find resolver with name {0!s} ".format(resolvername))
        return None
    else:
        store = get_request_local_store()
        if 'resolver_objects' not in store:
            store['resolver_objects'] = {}
        resolver_objects = store['resolver_objects']
        if resolvername not in resolver_objects:
            # create the resolver instance and load the config
            r_obj = resolver_objects[resolvername] = r_obj_class()
            if r_obj is not None:
                resolver_config = get_resolver_config(resolvername)
                r_obj.loadConfig(resolver_config)
        return resolver_objects[resolvername]

@log_with(log)
def pretestresolver(resolvertype, params):
    """
    This tests, if the params will create a working resolver.
    This function can be called before a resolver is created.

    :param resolvertype:
    :param params:
    :type params: dict
    :return:
    """
    # If an already saved resolver is tested again, the password
    # could be "__CENSORED__". In this case we use the old, saved password.
    if params.get("resolver"):
        old_config_list = get_resolver_list(filter_resolver_name=params.get("resolver")) or {}
        old_config = old_config_list.get(params.get("resolver")) or {}
        for key in old_config.get("censor_keys", []):
            if params.get(key) == CENSORED:
                # Overwrite with the value from the database
                params[key] = old_config.get("data").get(key)

    # determine the class by the given type
    r_obj_class = get_resolver_class(resolvertype)
    (success, desc) = r_obj_class.testconnection(params)
    return success, desc


@register_export('resolver')
def export_resolver(name=None, censor=False):
    """ Export given or all resolver configuration """
    return get_resolver_list(filter_resolver_name=name, censor=censor)


@register_import('resolver', prio=10)
def import_resolver(data, name=None):
    """Import resolver configuration"""
    # TODO: Currently this functions does not check for the plausibility of the
    #  given data. We could use "pretestresolver() / testconnection()" (which
    #  doesn't check the input) or "loadConfig()" (which also doesn't check the
    #  parameter, at least for LDAP/SQL-resolver).
    log.debug('Import resolver config: {0!s}'.format(data))
    for res_name, res_data in data.items():
        if name and name != res_name:
            continue
        # remove the 'censor_keys' entry from data since it is not necessary
        res_data.pop('censor_keys', None)
        # save_resolver() needs the resolver name at key 'resolver'
        res_data['resolver'] = res_data.pop('resolvername')
        # also all the 'data' entries need to be in the first dict level
        res_data.update(res_data.pop('data'))
        rid = save_resolver(res_data)
        # TODO: we have no information if a new resolver was created or an
        #  existing resolver updated. We would need to enhance "save_resolver()".
        log.info('Import of resolver "{0!s}" finished,'
                 ' id: {1!s}'.format(res_data['resolver'], rid))
