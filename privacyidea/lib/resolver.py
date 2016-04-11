# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#
#  2016-04-08 Cornelius Kölbel <cornelus@privacyidea.org>
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
from log import log_with
from config import (get_resolver_types,
                     get_resolver_class_dict)
from ..models import (Resolver,
                      ResolverConfig)
from ..api.lib.utils import required
from ..api.lib.utils import getParam
from .error import ConfigAdminError
from sqlalchemy import func
from .crypto import encryptPassword, decryptPassword
from privacyidea.lib.utils import sanity_name_check
#from privacyidea.lib.cache import cache

log = logging.getLogger(__name__)


@log_with(log)
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
            raise Exception("resolver type : {0!s} not in {1!s}".format(resolvertype, unicode(resolvertypes)))

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

    types = {}
    desc = {}
    data = {}
    for k in params:
        if k not in ['resolver', 'type']:
            if k.startswith('type.') is True:
                key = k[len('type.'):]
                types[key] = params.get(k)
            elif k.startswith('desc.') is True:
                key = k[len('desc.'):]
                desc[key] = params.get(k)
            else:
                data[k] = params.get(k)
                if k in config_description:
                    types[k] = config_description.get(k)
                else:
                    log.warn("the passed key %r is not a "
                             "parameter for the resolver %r" % (k,
                                                                resolvertype))
                        
    # Check that there is no type or desc without the data itself.
    # i.e. if there is a type.BindPW=password, then there must be a
    # BindPW=....
    _missing = False
    for t in types:
        if t not in data:
            _missing = True
    for t in desc:
        if t not in data:
            _missing = True
    if _missing:
        raise Exception("type or description without necessary data! {0!s}".format(
                        unicode(params)))

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
            value = encryptPassword(value)
        ResolverConfig(resolver_id=resolver_id,
                       Key=key,
                       Value=value,
                       Type=types.get(key, ""),
                       Description=desc.get(key, "")).save()
    return resolver_id


@log_with(log)
#@cache.memoize(10)
def get_resolver_list(filter_resolver_type=None,
                      filter_resolver_name=None,
                      editable=None):
    """
    Gets the list of configured resolvers from the database

    :param filter_resolver_type: Only resolvers of the given type are returned
    :type filter_resolver_type: basestring
    :param filter_resolver_name: Get the distinct resolver
    :type filter_resolver_name: basestring
    :param editable: Whether only return editable resolvers
    :type editable: bool
    :rtype: Dictionary of the resolvers and their configuration
    """
    Resolvers = {}
    if filter_resolver_name:
        resolvers = Resolver.query\
                            .filter(func.lower(Resolver.name) ==
                                    filter_resolver_name.lower())
    elif filter_resolver_type:
        resolvers = Resolver.query\
                            .filter(Resolver.rtype == filter_resolver_type)
    else:
        resolvers = Resolver.query.all()
    
    for reso in resolvers:
        r = {"resolvername": reso.name,
             "type": reso.rtype}
        # Add resolver config data
        data = {}
        for conf in reso.rconfig:
            value = conf.Value
            if conf.Type == "password":
                value = decryptPassword(value)
            data[conf.Key] = value
        r["data"] = data
        if editable is None:
            Resolvers[reso.name] = r
        else:
            if editable is True and r["data"].get("Editable") == "1":
                Resolvers[reso.name] = r
            elif editable is False and r["data"].get("Editable") != "1":
                Resolvers[reso.name] = r


    return Resolvers


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
    return ret


@log_with(log)
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
    '''
    return the class object for a resolver type
    :param resolver_type: string specifying the resolver
                          fully qualified or abreviated
    :return: resolver object class
    '''
    ret = None
    
    (resolver_clazzes, resolver_types) = get_resolver_class_dict()

    if resolver_type in resolver_types.values():
        for k, v in resolver_types.items():
            if v == resolver_type:
                ret = resolver_clazzes.get(k)
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
    TODO: We can cache this
    create a resolver object from a resolvername

    :param resolvername: the resolver string as from the token including
                         the config as last part
    :return: instance of the resolver with the loaded config

    """
    r_obj = None
    r_type = get_resolver_type(resolvername)
    r_obj_class = get_resolver_class(r_type)

    if r_obj_class is None:
        log.error("Can not find resolver with name {0!s} ".format(resolvername))
    else:
        # create the resolver instance and load the config
        r_obj = r_obj_class()
        if r_obj is not None:
            resolver_config = get_resolver_config(resolvername)
            r_obj.loadConfig(resolver_config)

    return r_obj


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
    # determine the class by the given type
    r_obj_class = get_resolver_class(resolvertype)
    (success, desc) = r_obj_class.testconnection(params)
    return success, desc
