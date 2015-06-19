# -*- coding: utf-8 -*-
#
#  2015-02-25 Cornelius Kölbel <cornelius@privacyidea.org>
#             Initial writup
#
#  This is derived from the UserIdResolver in LinOTP which is originally:
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
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
#
"""
This is the library for creating new machine resolvers in the database and
deleting existing ones.

This module is tested in tests/test_lib_machines.py in the class
MachineTestCase.
Its only dependencies are to the database model.py and to the
config.py, so this can be tested standalone without realms, tokens and
webservice!
"""

import logging
from log import log_with
from ..models import (MachineResolver,
                      MachineResolverConfig)
from ..api.lib.utils import required
from ..api.lib.utils import getParam
from sqlalchemy import func
from .crypto import encryptPassword, decryptPassword
from privacyidea.lib.config import get_machine_resolver_class_dict
from privacyidea.lib.utils import (sanity_name_check, get_data_from_params)


log = logging.getLogger(__name__)



@log_with(log)
def save_resolver(params):
    """
    create a new machine resolver from request parameters
    and save the machine resolver in the database.

    If the machine resolver already exist, it is updated.
    If you update machine resolver, you do not need to provide all parameters.
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
    # for the name and type.
    resolvername = getParam(params, 'name', required)
    resolvertype = getParam(params, 'type', required)
    update_resolver = False
    # check the name
    sanity_name_check(resolvername)
    # check the type
    (class_dict, type_dict) = get_machine_resolver_class_dict()
    if resolvertype not in type_dict.values():
            raise Exception("machine resolver type : %s not in %s" %
                            (resolvertype, type_dict.values()))

    # check the name
    resolvers = get_resolver_list(filter_resolver_name=resolvername)
    for r_name, resolver in resolvers.items():
        if resolver.get("type") == resolvertype:
            # We found the resolver with the same name and the same type,
            # So we will update this resolver
            update_resolver = True
        else:  # pragma: no cover
            raise Exception("machine resolver with similar name and other type "
                            "already exists: %s" % r_name)

    # create a dictionary for the ResolverConfig
    resolver_config = get_resolver_config_description(resolvertype)
    config_description = resolver_config.get(resolvertype,
                                             {}).get('config',
                                                     {})
    data, types, desc = get_data_from_params(params,
                                             ["name", "type"],
                                             config_description,
                                             "machine resolver",
                                             resolvertype)

    # Everything passed. So lets actually create the resolver in the DB
    if update_resolver:
        resolver_id = MachineResolver.query.filter(func.lower(
            MachineResolver.name) == resolvername.lower()).first().id
    else:
        resolver = MachineResolver(params.get("name"), params.get("type"))
        resolver_id = resolver.save()
    # create the config
    for key, value in data.items():
        if types.get(key) == "password":
            value = encryptPassword(value)
        MachineResolverConfig(resolver_id=resolver_id,
                              Key=key,
                              Value=value,
                              Type=types.get(key, ""),
                              Description=desc.get(key, "")).save()
    return resolver_id


@log_with(log)
#@cache.memoize(10)
def get_resolver_list(filter_resolver_type=None,
                      filter_resolver_name=None):
    """
    Gets the list of configured machine resolvers from the database

    :param filter_resolver_type: Only resolvers of the given type are returned
    :type filter_resolver_type: string
    :rtype: Dictionary of the resolvers and their configuration
    """
    Resolvers = {}
    if filter_resolver_name:
        resolvers = MachineResolver.query\
            .filter(func.lower(MachineResolver.name) ==
                    filter_resolver_name.lower())
    elif filter_resolver_type:
        resolvers = MachineResolver.query\
                            .filter(MachineResolver.rtype ==
                                    filter_resolver_type)
    else:
        resolvers = MachineResolver.query.all()
    
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
        Resolvers[reso.name] = r

    return Resolvers


@log_with(log)
def delete_resolver(resolvername):
    """
    delete a machine resolver and all related MachineResolverConfig entries
    If there was no resolver, that could be deleted, it returns -1

    :param resolvername: the name of the to be deleted resolver
    :type resolvername: string
    :return: The Id of the resolver
    :rtype: int
    """
    ret = -1

    reso = MachineResolver.query.filter_by(name=resolvername).first()
    if reso:
        reso.delete()
        ret = reso.id
    return ret


@log_with(log)
#@cache.memoize(10)
def get_resolver_config_description(resolver_type):
    """
    get the configuration description of a machine resolver

    :param resolver_type: the type of the resolver. Something like
                          "base" or "hosts".
    :type resolver_type: string
    :return: configuration description dict
             This should contain a key "config" that contains a dictionary
             and a key "clazz":
             {'base': {'config': {'fileName': 'string'},
                                 'clazz': 'useridresolver.PasswdIdResolver'
                                          '.IdResolver'}}

    """
    descriptor = None
    resolver_class = get_resolver_class(resolver_type)

    if resolver_class is not None:
        descriptor = resolver_class.get_config_description()

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
    
    (resolver_clazzes, resolver_types) = get_machine_resolver_class_dict()

    if resolver_type in resolver_types.values():
        for k, v in resolver_types.items():
            if v == resolver_type:
                ret = resolver_clazzes.get(k, None)
                break
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
def get_resolver_object(resolvername):
    """
    return the resolver object for a given name

    :param resolvername: the resolver string as from the token including
                         the config as last part
    :return: instance of the resolver with the loaded config

    """
    r_obj = None
    resolver = get_resolver_list(filter_resolver_name=resolvername).get(
        resolvername)
    if resolver:
        r_obj_class = get_resolver_class(resolver.get("type"))

        if r_obj_class is None:  # pragma: no cover
            # This can only happen if a resolver class definition would be
            # removed.
            log.error("unknown resolver class for type %s " %
                      resolver.get("type"))
        else:
            # create the resolver instance and load the config
            r_obj = r_obj_class(resolvername, resolver.get("data"))

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
