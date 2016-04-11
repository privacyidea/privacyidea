# -*- coding: utf-8 -*-
#
#  2015-04-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#             This code is inspired by the resolver.py which was forked from
#             LinOTP, which was originally (c) by LSE Leading Security Experts.
#
# License:  AGPLv3
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
__doc__ = """This the library for handling CA connector definitions which are
stored in the database table "caconnector".

The code is tested in tests/test_lib_caconnector.py.
"""

import logging
from log import log_with
from config import (get_caconnector_types,
                    get_caconnector_class_dict)
from ..models import (CAConnector,
                      CAConnectorConfig)
from ..api.lib.utils import required
from ..api.lib.utils import getParam
from .error import ConfigAdminError
from sqlalchemy import func
from .crypto import encryptPassword, decryptPassword
from privacyidea.lib.utils import (sanity_name_check, get_data_from_params)
#from privacyidea.lib.cache import cache

log = logging.getLogger(__name__)


@log_with(log)
def save_caconnector(params):
    """
    Create a new CA connector from the given parameters and save it to the
    database.

    If the CA Connector already exists, it is updated.
    For updating some attributes of an existing CA connector you do not need
    to pass all attributes again, but only those, which should be changed.

    When updating the CA connector the type must not be changed,
    since another type might require different attributes.

    :param params: request parameters like "caconnector" (name) and "type"
        and the specific attributes of the ca connector.
    :type params: dict
    :return: the database ID of the CA connector
    :rtype: int
    """
    # before we create the resolver in the database, we need to check
    # for the name and type thing...
    connector_name = getParam(params, 'caconnector', required)
    connector_type = getParam(params, 'type', required)
    update_connector = False
    sanity_name_check(connector_name)
    # check the type
    if connector_type not in get_caconnector_types():
        raise Exception("connector type : {0!s} not in {1!s}".format(connector_type, unicode(get_caconnector_types())))

    # check the name
    connectors = get_caconnector_list(filter_caconnector_name=connector_name)
    for connector in connectors:
        if connector.get("type") == connector_type:
            # There is a CA connector with the same name, so we will update
            # the CA Connector config
            update_connector = True
        else:  # pragma: no cover
            raise Exception("CA Connector with similar name and other type "
                            "already exists: %s" % connector_name)

    # create a dictionary for the ResolverConfig
    connector_config = get_caconnector_config_description(connector_type)
    config_description = connector_config.get(connector_type, {})

    data, types, desc = get_data_from_params(params,
                                             ["caconnector", "type"],
                                             config_description,
                                             "CA connector",
                                             connector_type)

    # Everything passed. So lets actually create the CA Connector in the DB
    if update_connector:
        connector_id = CAConnector.query.filter(func.lower(CAConnector.name)
                                                == connector_name.lower()).first().id
    else:
        db_connector = CAConnector(params.get("caconnector"),
                                   params.get("type"))
        connector_id = db_connector.save()
    # create the config
    for key, value in data.items():
        if types.get(key) == "password":
            value = encryptPassword(value)
        CAConnectorConfig(caconnector_id=connector_id,
                        Key=key,
                        Value=value,
                        Type=types.get(key, ""),
                        Description=desc.get(key, "")).save()
    return connector_id


@log_with(log)
#@cache.memoize(10)
def get_caconnector_list(filter_caconnector_type=None,
                         filter_caconnector_name=None,
                         return_config=True):
    """
    Gets the list of configured CA Connectors from the database

    :param filter_caconnector_type: Only CA connectors of the given type are
        returned
    :type filter_caconnector_type: string
    :param return_config: Whether the configuration should be returned. If False
        only the list of the CAconncetor names is returned
    :rtype: list of the connectors and their configuration

    """
    Connectors = []
    if filter_caconnector_name:
        connectors = CAConnector.query\
                            .filter(func.lower(CAConnector.name) ==
                                    filter_caconnector_name.lower())
    elif filter_caconnector_type:
        connectors = CAConnector.query\
                            .filter(CAConnector.catype ==
                                    filter_caconnector_type)
    else:
        connectors = CAConnector.query.all()
    
    for conn in connectors:
        c = {"connectorname": conn.name,
             "type": conn.catype}
        # Add the connector configuration
        data = {}
        if return_config:
            for conf in conn.caconfig:
                value = conf.Value
                if conf.Type == "password":
                    value = decryptPassword(value)
                data[conf.Key] = value
        c["data"] = data
        Connectors.append(c)

    return Connectors


@log_with(log)
def delete_caconnector(connector_name):
    """
    delete a CA connector and all related config entries.
    If there was no CA connector, that could be deleted, it returns -1

    :param connector_name: The name of the CA connector that is to be deleted
    :type connector_name: basestring
    :return: The Id of the resolver
    :rtype: int
    """
    ret = -1

    conn = CAConnector.query.filter_by(name=connector_name).first()
    if conn:
        conn.delete()
        ret = conn.id
    return ret


@log_with(log)
#@cache.memoize(10)
def get_caconnector_config(connector_name):
    """
    return the complete config of a given CA connector from the database
    :param connector_name: the name of the CA connector
    :type connector_name: basestring
    :return: the config of the CA connector
    :rtype: dict
    """
    conn = get_caconnector_list(filter_caconnector_name=connector_name)
    return conn[0].get("data", {})


@log_with(log)
#@cache.memoize(10)
def get_caconnector_config_description(caconnector_type):
    """
    Get the description of the configuration of a CA connector

    :param caconnector_type: the type of the CA connector like "local"
    :type caconnector_type: basestring
    :return: configuration description dict
             that looks like this:
             {'local': {'attribute1': 'string',
                        'attribute2': 'int'}}

    """
    descriptor = None
    connector_class = get_caconnector_class(caconnector_type)

    if connector_class is not None:
        descriptor = connector_class.get_caconnector_description()

    return descriptor


#@cache.memoize(10)
def get_caconnector_class(connector_type):
    """
    Return the class for a given CA connector type.

    :param connector_type: The type of the connector
    :type connector_type: basestring
    :return: CA Connector Class
    """
    ret = None
    
    (connector_classes, connector_types) = get_caconnector_class_dict()

    if connector_type in connector_types.values():
        for k, v in connector_types.items():
            if v == connector_type:
                ret = connector_classes.get(k)
                break
    return ret


#@cache.memoize(10)
def get_caconnector_type(connector_name):
    """
    return the type of a CA connector
    
    :param connector_name: The name of the CA connector
    :return: The type of the CA connector
    :rtype: string
    """
    c_type = None
    connector_list = get_caconnector_list(filter_caconnector_name=connector_name)
    if connector_list:
        c_type = connector_list[0].get("type")
    return c_type


@log_with(log)
#@cache.memoize(10)
def get_caconnector_object(connector_name):
    """
    create a CA Connector object from a connector_name

    :param connector_name: the name of the CA connector
    :return: instance of the CA Connector with the loaded config
    """
    c_obj = None
    c_type = get_caconnector_type(connector_name)
    c_obj_class = get_caconnector_class(c_type)

    if c_obj_class is None:
        log.error("unknown CA connector class {0!s} ".format(connector_name))
    else:
        # create the resolver instance and load the config
        c_obj = c_obj_class(connector_name)
        if c_obj is not None:
            connector_config = get_caconnector_config(connector_name)
            c_obj.set_config(connector_config)

    return c_obj
