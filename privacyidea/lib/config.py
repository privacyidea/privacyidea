# -*- coding: utf-8 -*-
#
#  2016-04-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Avoid consecutive if-statements
#  2015-12-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Change eval to importlib
#  2015-04-23 Cornelius Kölbel <cornelius.koelbel@netknigts.it>
#             Add CA Connector functions
#
#  privacyIDEA is a fork of LinOTP
#  Nov 11, 2014 Cornelius Kölbel
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__doc__ = """The config module takes care about storing server configuration in
the Config database table.

It provides functions to retrieve (get) and and set configuration.

The code is tested in tests/test_lib_config
"""

import copy
import sys
import logging
import inspect
import threading
import traceback

from .log import log_with
from ..models import (Config, db, Resolver, Realm, PRIVACYIDEA_TIMESTAMP,
                      save_config_timestamp, Policy, EventHandler, CAConnector)
from privacyidea.lib.framework import get_request_local_store, get_app_config_value, get_app_local_store
from privacyidea.lib.utils import to_list
from privacyidea.lib.utils.export import (register_import, register_export)
from .crypto import encryptPassword
from .crypto import decryptPassword
from .resolvers.UserIdResolver import UserIdResolver
from .machines.base import BaseMachineResolver
from .caconnectors.baseca import BaseCAConnector
# We need these imports to return the list of CA connector types. Bummer: New import for each new Class anyway.
from .caconnectors import localca, msca
from .utils import reload_db, is_true
import importlib
import datetime

log = logging.getLogger(__name__)

ENCODING = 'utf-8'

# this is a pointer to the module object instance itself.
this = sys.modules[__name__]

this.config = {}


class SharedConfigClass(object):
    """
    A shared config class object is shared between threads and is supposed
    to store the current configuration with resolvers, realms, policies
    and event handler definitions along with the timestamp of the configuration.

    The method ``_reload_from_db()`` compares this timestamp against the
    timestamp in the database (while taking the PI_CHECK_RELOAD_CONFIG
    setting into account). If the database timestamp is newer, the current
    configuration is updated.

    However, app code must not access the config stored in the shared object!
    Instead, it must use ``reload_and_clone()`` to retrieve
    a ``LocalConfigClass`` object which holds a local configuration snapshot.
    """
    def __init__(self):
        self._config_lock = threading.Lock()
        self.config = {}
        self.resolver = {}
        self.realm = {}
        self.default_realm = None
        self.policies = []
        self.events = []
        self.timestamp = None
        self.caconnectors = []

    def _reload_from_db(self):
        """
        Read the timestamp from the database. If the timestamp is newer than
        the internal timestamp, then read the complete data
        :return:
        """
        check_reload_config = get_app_config_value("PI_CHECK_RELOAD_CONFIG", 0)
        if not self.timestamp or \
            self.timestamp + datetime.timedelta(seconds=check_reload_config) < datetime.datetime.now():
            db_ts = Config.query.filter_by(Key=PRIVACYIDEA_TIMESTAMP).first()
            if reload_db(self.timestamp, db_ts):
                log.debug("Reloading shared config from database")
                config = {}
                resolverconfig = {}
                realmconfig = {}
                default_realm = None
                policies = []
                events = []
                caconnectors = []
                # Load system configuration
                for sysconf in Config.query.all():
                    config[sysconf.Key] = {
                        "Value": sysconf.Value,
                        "Type": sysconf.Type,
                        "Description": sysconf.Description}
                # Load resolver configuration
                for resolver in Resolver.query.all():
                    resolverdef = {"type": resolver.rtype,
                                   "resolvername": resolver.name,
                                   "censor_keys": []}
                    data = {}
                    for rconf in resolver.config_list:
                        if rconf.Type == "password":
                            value = decryptPassword(rconf.Value)
                            resolverdef["censor_keys"].append(rconf.Key)
                        else:
                            value = rconf.Value
                        data[rconf.Key] = value
                    resolverdef["data"] = data
                    resolverconfig[resolver.name] = resolverdef
                # Load realm configuration
                for realm in Realm.query.all():
                    if realm.default:
                        default_realm = realm.name
                    realmdef = {"id": realm.id,
                                "option": realm.option,
                                "default": realm.default,
                                "resolver": []}
                    for x in realm.resolver_list:
                        realmdef["resolver"].append({"priority": x.priority,
                                                     "name": x.resolver.name,
                                                     "type": x.resolver.rtype})
                    realmconfig[realm.name] = realmdef
                # Load all policies
                for pol in Policy.query.all():
                    policies.append(pol.get())
                # Load all events
                for event in EventHandler.query.order_by(EventHandler.ordering):
                    events.append(event.get())
                # Load all CA connectors
                from privacyidea.lib.caconnector import get_caconnector_object
                for ca in CAConnector.query.all():
                    try:
                        ca_obj = get_caconnector_object(ca.name)
                        caconnectors.append({"connectorname": ca.name,
                                             "type": ca.catype,
                                             "data": ca_obj.config,
                                             "templates": ca_obj.get_templates()})
                    except Exception as exx:  # pragma: no cover
                        log.debug("{0!s}".format(traceback.format_exc()))
                        log.error(exx)

                # Finally, set the current timestamp
                timestamp = datetime.datetime.now()
                with self._config_lock:
                    self.config = config
                    self.resolver = resolverconfig
                    self.realm = realmconfig
                    self.default_realm = default_realm
                    self.policies = policies
                    self.events = events
                    self.timestamp = timestamp
                    self.caconnectors = caconnectors

    def _clone(self):
        """
        :return: a ``LocalConfigClass`` object containing the current configuration state
        """
        with self._config_lock:
            return LocalConfigClass(
                self.config,
                self.resolver,
                self.realm,
                self.default_realm,
                self.policies,
                self.events,
                self.caconnectors,
                self.timestamp
            )

    def reload_and_clone(self):
        """
        Check if the current configuration state is outdated (according to the
        PI_CHECK_RELOAD_CONFIG setting), reload it if needed and return a
        ``LocalConfigClass`` object containing the current configuration state
        """
        self._reload_from_db()
        return self._clone()


class LocalConfigClass(object):
    """
    The Config_Object will contain all database configuration of system
    config, resolvers, realms, policies and event handler definitions.

    It will be cloned from the shared config object at the beginning of the
    request and is supposed to stay alive and unchanged during the request.
    """
    def __init__(self, config, resolver, realm, default_realm, policies, events, caconnectors, timestamp):
        self.config = config
        self.resolver = resolver
        self.realm = realm
        self.default_realm = default_realm
        self.policies = policies
        self.events = events
        self.caconnectors = caconnectors
        self.timestamp = timestamp

    def get_config(self, key=None, default=None, role="admin",
                   return_bool=False):
        """
        :param key: A key to retrieve
        :type key: string
        :param default: The default value, if it does not exist in the database
        :param role: The role which wants to retrieve the system config. Can be
            "admin" or "public". If "public", only values with type="public"
            are returned.
        :type role: string
        :param return_bool: If a boolean value should be returned. Returns
            True if value is "True", "true", 1, "1", True...
        :return: If key is None, then a dictionary is returned. If a certain key
            is given a string/bool is returned.
        """
        default_true_keys = [SYSCONF.PREPENDPIN, SYSCONF.SPLITATSIGN,
                             SYSCONF.INCFAILCOUNTER, SYSCONF.RETURNSAML]

        r_config = {}

        # reduce the dictionary to only public keys!
        reduced_config = {}
        for ckey, cvalue in self.config.items():
            if role == "admin" or cvalue.get("Type") == "public":
                reduced_config[ckey] = self.config[ckey]
        if not reduced_config and role == "admin":
            reduced_config = self.config

        for ckey, cvalue in reduced_config.items():
            if cvalue.get("Type") == "password":
                # decrypt the password
                r_config[ckey] = decryptPassword(cvalue.get("Value"))
            else:
                r_config[ckey] = cvalue.get("Value")

        for t_key in default_true_keys:
            if t_key not in r_config:
                r_config[t_key] = "True"

        if key:
            # We only return a single key
            r_config = r_config.get(key, default)

        if return_bool:
            if isinstance(r_config, bool):
                pass
            if isinstance(r_config, int):
                r_config = r_config > 0
            if isinstance(r_config, str):
                r_config = is_true(r_config.lower())

        return r_config


class SYSCONF(object):
    __doc__ = """This is a list of system config attributes"""
    OVERRIDECLIENT = "OverrideAuthorizationClient"
    PREPENDPIN = "PrependPin"
    SPLITATSIGN = "splitAtSign"
    INCFAILCOUNTER = "IncFailCountOnFalsePin"
    RETURNSAML = "ReturnSamlAttributes"
    RETURNSAMLONFAIL = "ReturnSamlAttributesOnFail"
    RESET_FAILCOUNTER_ON_PIN_ONLY = "ResetFailcounterOnPIN"


#@cache.cached(key_prefix="allConfig")
def get_privacyidea_config():
    # timestamp = Config.query.filter_by(Key="privacyidea.timestamp").first()
    return get_from_config()


def get_shared_config_object():
    """
    :return: the application-wide ``SharedConfigClass`` object, which is created on demand.
    """
    store = get_app_local_store()
    if 'shared_config_object' not in store:
        # It might happen that two threads create SharedConfigClass() instances in parallel.
        # However, as setting dictionary values is atomic, one of the two objects will "win",
        # and the next request handled by the second thread will use the winning config object.
        log.debug("Creating new shared config object")
        store['shared_config_object'] = SharedConfigClass()
    return store['shared_config_object']


def invalidate_config_object():
    """
    Invalidate the request-local config object. This is useful whenever a request modifies
    the configuration in the database: In this case, the request-local config object still
    contains the old configuration and needs to be invalidated. The same request can then
    create a new request-local config object, which will contain the new configuration.

    In other words, this function does the following:
    If the request-local store contains a config object, remove it.
    If the request-local store contains no config object, do nothing.
    """
    store = get_request_local_store()
    if 'config_object' in store:
        log.debug("Invalidating request-local config object")
        del store['config_object']


def ensure_no_config_object():
    """
    Ensure that the request-local store contains no config object, and emit
    a warning if it does. This should only be the case if we are running tests.

    If the request-local store contains a config object, remove it and emit a warning.
    If the request-local store contains no config object, do nothing.
    """
    store = get_request_local_store()
    if 'config_object' in store:
        log.warning("Request-local store already contains config object, even though it should not")
        del store['config_object']


def get_config_object():
    """
    Return the request-local config object. If it does not exist yet, create it.
    :return: a ``LocalConfigClass`` object
    """
    store = get_request_local_store()
    if 'config_object' not in store:
        log.debug("Cloning request-local config from shared config object")
        shared_config = get_shared_config_object()
        store['config_object'] = shared_config.reload_and_clone()
    return store['config_object']


@log_with(log)
#@cache.cached(key_prefix="singleConfig")
def get_from_config(key=None, default=None, role="admin", return_bool=False):
    """
    :param key: A key to retrieve
    :type key: string
    :param default: The default value, if it does not exist in the database
    :param role: The role which wants to retrieve the system config. Can be
        "admin" or "public". If "public", only values with type="public"
        are returned.
    :type role: string
    :param return_bool: If the a boolean value should be returned. Returns
        True if value is "True", "true", 1, "1", True...
    :return: If key is None, then a dictionary is returned. If a certain key
        is given a string/bool is returned.
    """
    config_object = get_config_object()
    return config_object.get_config(key=key, default=default, role=role,
                                    return_bool=return_bool)


#@cache.cached(key_prefix="resolver")
def get_resolver_types():
    """
    Return a simple list of the type names of the resolvers.
    :return: array of resolvertypes like 'passwdresolver'
    :rtype: array
    """
    if "pi_resolver_types" not in this.config:
        (r_classes, r_types) = get_resolver_class_dict()
        this.config["pi_resolver_classes"] = r_classes
        this.config["pi_resolver_types"] = r_types

    return list(this.config["pi_resolver_types"].values())


def get_caconnector_types():
    """
    Returns a list of valid CA connector types
    :return:
    """
    caconnector_types = []
    for cacon in BaseCAConnector.__subclasses__():
        caconnector_types.append(cacon.connector_type)
    return caconnector_types


#@cache.cached(key_prefix="classes")
def get_resolver_classes():
    """
    Returns a list of the available resolver classes like:
    [<class 'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver'>,
    <class 'privacyidea.lib.resolvers.UserIdResolver.UserIdResolver'>]

    :return: array of resolver classes
    :rtype: array
    """
    resolver_classes = {}
    if "pi_resolver_classes" not in this.config:
        (r_classes, r_types) = get_resolver_class_dict()
        this.config["pi_resolver_types"] = r_types
        this.config["pi_resolver_classes"] = r_classes

    return list(this.config["pi_resolver_classes"].values())


#@cache.cached(key_prefix="classes")
def get_token_class_dict():
    """
    get a dictionary of the token classes and a dictionary of the
    token types:

    ({'privacyidea.lib.tokens.hotptoken.HotpTokenClass':
      <class 'privacyidea.lib.tokens.hotptoken.HotpTokenClass'>,
      'privacyidea.lib.tokens.totptoken.TotpTokenClass':
      <class 'privacyidea.lib.tokens.totptoken.TotpTokenClass'>},

      {'privacyidea.lib.tokens.hotptoken.HotpTokenClass':
      'hotp',
      'privacyidea.lib.tokens.totptoken.TotpTokenClass':
      'totp'})

    :return: tuple of two dicts
    """
    from .tokenclass import TokenClass

    tokenclass_dict = {}
    tokentype_dict = {}
    modules = get_token_module_list()
    for module in modules:
        for name in dir(module):
            obj = getattr(module, name)
            # We must not process imported classes!
            if (inspect.isclass(obj) and issubclass(obj, TokenClass) and
                        obj.__module__ == module.__name__):
                try:
                    class_name = "{0!s}.{1!s}".format(module.__name__, obj.__name__)
                    tokenclass_dict[class_name] = obj
                    if hasattr(obj, 'get_class_type'):
                        tokentype_dict[class_name] = obj.get_class_type()
                except Exception as e:  # pragma: no cover
                    log.error("error constructing token_class_dict: {0!r}".format(e))

    return tokenclass_dict, tokentype_dict


#@cache.cached(key_prefix="classes")
def get_token_class(tokentype):
    """
    This takes a token type like "hotp" and returns a class
    like <class privacidea.lib.tokens.hotptoken.HotpTokenClass>
    :return: The tokenclass for the given type
    :rtype: tokenclass
    """
    if tokentype.lower() == "hmac":
        tokentype = "hotp"

    tokenclass = None
    tokenclasses = get_token_classes()
    for tclass in tokenclasses:
        if tclass.get_class_type().lower() == tokentype.lower():
            tokenclass = tclass
            break

    return tokenclass


#@cache.cached(key_prefix="types")
def get_token_types():
    """
    Return a simple list of the type names of the tokens.
    :return: list of tokentypes like 'hotp', 'totp'...
    :rtype: list
    """
    if "pi_token_types" not in this.config:
        (t_classes, t_types) = get_token_class_dict()
        this.config["pi_token_types"] = t_types
        this.config["pi_token_classes"] = t_classes

    return list(this.config["pi_token_types"].values())


#@cache.cached(key_prefix="prefix")
def get_token_prefix(tokentype=None, default=None):
    """
    Return the token prefix for a tokentype as it is defined in the
    tokenclass. If no tokentype is specified, we return a dictionary
    with the tokentypes as keys.
    :param tokentype: the type of the token like "hotp" or "totp"
    :type tokentype: basestring
    :param default: If the tokentype is not found, we return default
    :type default: basestring
    :return: the prefix of the tokentype or the dict with all prefixes
    :rtype: string or dict
    """
    prefix_dict = {}
    for tokenclass in get_token_classes():
        prefix_dict[tokenclass.get_class_type()] = tokenclass.get_class_prefix()

    if tokentype:
        ret = prefix_dict.get(tokentype, default)
    else:
        ret = prefix_dict
    return ret


#@cache.cached(key_prefix="classes")
def get_token_classes():
    """
    Returns a list of the available token classes like:
    [<class 'privacyidea.lib.tokens.totptoken.TotpTokenClass'>,
    <class 'privacyidea.lib.tokens.hotptoken.HotpTokenClass'>]

    :return: array of token classes
    :rtype: array
    """
    if "pi_token_classes" not in this.config:
        (t_classes, t_types) = get_token_class_dict()
        this.config["pi_token_classes"] = t_classes
        this.config["pi_token_types"] = t_types

    return list(this.config["pi_token_classes"].values())


def get_machine_resolver_class_dict():
    """
    get a dictionary of the machine resolver classes and a dictionary of the
    machines resolver types like this:

    ({'privacyidea.lib.machines.hosts.HostsMachineResolver':
      <class 'privacyidea.lib.machines.hosts.HostsMachineResolver'>},
     {'privacyidea.lib.machines.hosts.HostsMachineResolver':
      'hosts'})

    :return: tuple of two dicts
    """
    resolverclass_dict = {}
    resolvertype_dict = {}

    modules = get_machine_resolver_module_list()
    for module in modules:
        log.debug("module: {0!s}".format(module))
        for name in dir(module):
            obj = getattr(module, name)
            if inspect.isclass(obj) and \
                    (issubclass(obj, BaseMachineResolver)) and \
                    (obj != BaseMachineResolver):
                try:
                    class_name = "{0!s}.{1!s}".format(module.__name__, obj.__name__)
                    resolverclass_dict[class_name] = obj
                    resolvertype_dict[class_name] = obj.type

                except Exception as e:  # pragma: no cover
                    log.error("error constructing machine resolver "
                              "class_list: %r" % e)

    return resolverclass_dict, resolvertype_dict


def get_caconnector_class_dict():
    """
    get a dictionary of the CA connector classes and a dictionary of the
    machines resolver types like this:

    ({'privacyidea.lib.caconnectors.localca.LocalCAConnector':
      <class 'privacyidea.lib.caconnectors.localca.LocalCAConnector'>},
     {'privacyidea.lib.caconnectors.localca.LocalCAConnector':
      'local'})

    :return: tuple of two dicts
    """
    class_dict = {}
    type_dict = {}

    modules = get_caconnector_module_list()
    for module in modules:
        log.debug("module: {0!s}".format(module))
        for name in dir(module):
            obj = getattr(module, name)
            if inspect.isclass(obj) and \
                    (issubclass(obj, BaseCAConnector)) and \
                    (obj != BaseCAConnector):
                try:
                    class_name = "{0!s}.{1!s}".format(module.__name__, obj.__name__)
                    class_dict[class_name] = obj
                    type_dict[class_name] = obj.connector_type

                except Exception as e:  # pragma: no cover
                    log.error("error constructing CA connector "
                              "class_list: %r" % e)

    return class_dict, type_dict


#@cache.cached(key_prefix="resolver")
def get_resolver_class_dict():
    """
    get a dictionary of the resolver classes and a dictionary
    of the resolver types:

    ({'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver':
      <class 'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver'>,
      'privacyidea.lib.resolvers.PasswdIdResolver.UserIdResolver':
      <class 'privacyidea.lib.resolvers.UserIdResolver.UserIdResolver'>},

      {'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver':
      'passwdresolver',
      'privacyidea.lib.resolvers.PasswdIdResolver.UserIdResolver':
      'UserIdResolver'})

    :return: tuple of two dicts.
    """
    resolverclass_dict = {}
    resolverprefix_dict = {}

    modules = get_resolver_module_list()
    for module in modules:
        log.debug("module: {0!s}".format(module))
        for name in dir(module):
            obj = getattr(module, name)
            # There are other classes like HMAC in the lib.tokens module,
            # which we do not want to load.
            if inspect.isclass(obj) and (issubclass(obj, UserIdResolver) or
                                             obj == UserIdResolver):
                # We must not process imported classes!
                # if obj.__module__ == module.__name__:
                try:
                    class_name = "{0!s}.{1!s}".format(module.__name__, obj.__name__)
                    resolverclass_dict[class_name] = obj

                    prefix = class_name.split('.')[1]
                    if hasattr(obj, 'getResolverClassType'):
                        prefix = obj.getResolverClassType()

                    resolverprefix_dict[class_name] = prefix

                except Exception as e:  # pragma: no cover
                    log.error("error constructing resolverclass_list: {0!r}".format(e))

    return resolverclass_dict, resolverprefix_dict


@log_with(log)
#@cache.cached(key_prefix="resolver")
def get_resolver_list():
    """
    get the list of the module names of the resolvers like
    "resolvers.PasswdIdResolver".

    :return: list of resolver names from the config file
    :rtype: set
    """
    module_list = set()

    module_list.add("privacyidea.lib.resolvers.PasswdIdResolver")
    module_list.add("privacyidea.lib.resolvers.LDAPIdResolver")
    module_list.add("privacyidea.lib.resolvers.SCIMIdResolver")
    module_list.add("privacyidea.lib.resolvers.SQLIdResolver")
    module_list.add("privacyidea.lib.resolvers.HTTPResolver")

    # Dynamic Resolver modules
    # TODO: Migration
    # config_modules = config.get("privacyideaResolverModules", '')
    config_modules = None
    log.debug("{0!s}".format(config_modules))
    if config_modules:
        # in the config *.ini files we have some line continuation slashes,
        # which will result in ugly module names, but as they are followed by
        # \n they could be separated as single entries by the following two
        # lines
        lines = config_modules.splitlines()
        coco = ",".join(lines)
        for module in coco.split(','):
            if module.strip() != '\\':
                module_list.add(module.strip())

    return module_list


@log_with(log)
#@cache.memoize(1)
def get_machine_resolver_class_list():
    """
    get the list of the class names of the machine resolvers like
    "machines.hosts.HostsMachineResolver".

    :return: list of machine resolver class names from the config file
    :rtype: list
    """
    class_list = []
    # TODO: We should read all classes inherited by BaseMachineResolver under
    # machines/
    # Otherwise we need to add a line here for each new MachineResolver.
    class_list.append("privacyidea.lib.machines.hosts.HostsMachineResolver")
    class_list.append("privacyidea.lib.machines.ldap.LdapMachineResolver")
    return class_list


@log_with(log)
#@cache.cached(key_prefix="token")
def get_token_list():
    """
    get the list of the tokens
    :return: list of token names from the config file
    """
    module_list = set()

    module_list.add("privacyidea.lib.tokens.daplugtoken")
    module_list.add("privacyidea.lib.tokens.hotptoken")
    module_list.add("privacyidea.lib.tokens.motptoken")
    module_list.add("privacyidea.lib.tokens.passwordtoken")
    module_list.add("privacyidea.lib.tokens.applicationspecificpasswordtoken")
    module_list.add("privacyidea.lib.tokens.remotetoken")
    module_list.add("privacyidea.lib.tokens.daypasswordtoken")
    module_list.add("privacyidea.lib.tokens.spasstoken")
    module_list.add("privacyidea.lib.tokens.sshkeytoken")
    module_list.add("privacyidea.lib.tokens.totptoken")
    module_list.add("privacyidea.lib.tokens.yubicotoken")
    module_list.add("privacyidea.lib.tokens.yubikeytoken")
    module_list.add("privacyidea.lib.tokens.radiustoken")
    module_list.add("privacyidea.lib.tokens.smstoken")
    module_list.add("privacyidea.lib.tokens.emailtoken")
    module_list.add("privacyidea.lib.tokens.registrationtoken")
    module_list.add("privacyidea.lib.tokens.certificatetoken")
    module_list.add("privacyidea.lib.tokens.foureyestoken")
    module_list.add("privacyidea.lib.tokens.tiqrtoken")
    module_list.add("privacyidea.lib.tokens.ocratoken")
    module_list.add("privacyidea.lib.tokens.u2ftoken")
    module_list.add("privacyidea.lib.tokens.papertoken")
    module_list.add("privacyidea.lib.tokens.questionnairetoken")
    module_list.add("privacyidea.lib.tokens.vascotoken")
    module_list.add("privacyidea.lib.tokens.tantoken")
    module_list.add("privacyidea.lib.tokens.pushtoken")
    module_list.add("privacyidea.lib.tokens.indexedsecrettoken")
    module_list.add("privacyidea.lib.tokens.webauthntoken")

    # Dynamic token modules
    dynamic_token_modules = get_app_config_value("PI_TOKEN_MODULES")
    if dynamic_token_modules:
        # In the pi.cfg you can specify a list or set of 3rd party token modules like
        #    PI_TOKEN_MODULES = [ "myproj.tokens.tok1", "myproj.tokens.tok2" ]
        module_list.update(to_list(dynamic_token_modules))

    return module_list


@log_with(log)
#@cache.cached(key_prefix="modules")
def get_token_module_list():
    """
    return the list of modules of the available token classes

    :return: list of token modules
    """
    # def load_resolver_modules
    module_list = get_token_list()
    log.debug("using the module list: {0!s}".format(module_list))

    modules = []
    for mod_name in module_list:
        if mod_name == '\\' or len(mod_name.strip()) == 0:
            continue

        # load all token class implementations
        #if mod_name in sys.modules:
        #    module = sys.modules[mod_name]
        #    log.debug('module %s loaded' % (mod_name))
        #    modules.append(module)
        #else:
        try:
            log.debug("import module: {0!s}".format(mod_name))
            module = importlib.import_module(mod_name)
            modules.append(module)
        except Exception as exx:  # pragma: no cover
            module = None
            log.warning('unable to load token module : {0!r} ({1!r})'.format(mod_name, exx))

    return modules


#@cache.cached(key_prefix="modules")
def get_resolver_module_list():
    """
    return the list of modules of the available resolver classes
    like passwd, sql, ldap

    :return: list of resolver modules
    """

    # def load_resolver_modules
    module_list = get_resolver_list()
    log.debug("using the module list: {0!s}".format(module_list))

    modules = []
    for mod_name in module_list:
        if mod_name == '\\' or len(mod_name.strip()) == 0:
            continue

        try:
            log.debug("import module: {0!s}".format(mod_name))
            module = importlib.import_module(mod_name)

        except Exception as exx:  # pragma: no cover
            module = None
            log.warning('unable to load resolver module : {0!r} ({1!r})'.format(mod_name, exx))

        if module is not None:
            modules.append(module)

    return modules


#@cache.cached(key_prefix="module")
def get_caconnector_module_list():
    """
    return the list of modules of the available CA connector classes

    :return: list of CA connector modules
    """
    from privacyidea.lib.caconnectors.baseca import AvailableCAConnectors
    module_list = set(AvailableCAConnectors)

    modules = []
    for mod_name in module_list:
        mod_name = ".".join(mod_name.split(".")[:-1])
        class_name = mod_name.split(".")[-1:]
        try:
            log.debug("import module: {0!s}".format(mod_name))
            module = importlib.import_module(mod_name)

        except Exception as exx:  # pragma: no cover
            module = None
            log.warning('unable to load ca connector module : {0!r} ({1!r})'.format(mod_name, exx))

        if module is not None:
            modules.append(module)

    return modules


#@cache.cached(key_prefix="module")
def get_machine_resolver_module_list():
    """
    return the list of modules of the available machines resolver classes
    like base, hosts

    :return: list of resolver modules
    """

    # def load_resolver_modules
    class_list = get_machine_resolver_class_list()
    log.debug("using the class list: {0!s}".format(class_list))

    modules = []
    for class_name in class_list:
        try:
            module_name = ".".join(class_name.split(".")[:-1])
            log.debug("import module: {0!s}".format(module_name))
            module = importlib.import_module(module_name)

        except Exception as exx:  # pragma: no cover
            module = None
            log.warning('unable to load machine resolver module : {0!r} ({1!r})'.format(module_name, exx))

        if module is not None:
            modules.append(module)

    return modules


def set_privacyidea_config(key, value, typ="", desc=""):
    """
    Set a config value and writes it to the Config database table.
    Can be of type "password" or "public". "password" gets encrypted.
    """
    if not typ:
        # check if this is a token specific config and if it should be public
        try:
            token_type = key.split(".")[0]
            tclass = get_token_class(token_type)
            typ = tclass.get_setting_type(key)
        except Exception:
            log.debug("This seems to be no token specific setting")

    if typ == "password":
        # store value in encrypted way
        value = encryptPassword(value)
    # We need to check, if the value already exist
    c1 = Config.query.filter_by(Key=key).first()
    if c1:
        # The value already exist, we need to update
        c1.Value = value
        if typ:
            c1.Type = typ
        if desc:
            c1.Description = desc
        save_config_timestamp()
        db.session.commit()
        ret = "update"
    else:
        #new_entry = Config(key, value, typ, desc)
        # ``save`` will call ``save_config_timestamp`` for us
        Config(key, value, typ, desc).save()
        #db.session.add(new_entry)
        ret = "insert"

    #save_config_timestamp()
    #db.session.commit()
    return ret


def delete_privacyidea_config(key):
    """
    Delete a config entry
    """
    ret = 0
    # We need to check, if the value already exist
    if Config.query.filter_by(Key=key).first().delete():
        ret = True
    #if q:
    #    db.session.delete(q)
    #    db.session.commit()
    #    ret = True
    #    save_config_timestamp()
    return ret


#@cache.cached(key_prefix="pin")
def get_inc_fail_count_on_false_pin():
    """
    Return if the Failcounter should be increased if only tokens
    with a false PIN were identified.
    :return: True of False
    :rtype: bool
    """
    r = get_from_config(key="IncFailCountOnFalsePin",
                        default=False, return_bool=True)
    return r


#@cache.cached(key_prefix="pin")
def get_prepend_pin():
    """
    Get the status of the "PrependPin" Config

    :return: True or False
    :rtype: bool
    """
    r = get_from_config(key="PrependPin", default=False, return_bool=True)
    return r


def set_prepend_pin(prepend=True):
    """
    Set the status of the "PrependPin" Config
    :param prepend: If the PIN should be prepended or not
    :return: None
    """
    set_privacyidea_config("PrependPin", prepend)


def return_saml_attributes():
    r = get_from_config(key=SYSCONF.RETURNSAML, default=False,
                        return_bool=True)
    return r


def return_saml_attributes_on_fail():
    r = get_from_config(key=SYSCONF.RETURNSAMLONFAIL, default=False,
                        return_bool=True)
    return r


def get_privacyidea_node(default='localnode'):
    """
    This returns the node name of the privacyIDEA node as found in the pi.cfg
    file in PI_NODE.
    If it does not exist, the PI_AUDIT_SERVERNAME is used.
    :return: the distinct node name
    """
    node_name = get_app_config_value("PI_NODE", get_app_config_value("PI_AUDIT_SERVERNAME", default))
    return node_name


def get_privacyidea_nodes():
    """
    This returns the list of the nodes, including the own local node name
    :return: list of nodes
    """
    own_node_name = get_privacyidea_node()
    nodes = get_app_config_value("PI_NODES", [])[:]
    if own_node_name not in nodes:
        nodes.append(own_node_name)
    return nodes


@register_export()
def export_config(name=None):
    """Export the global configuration"""
    c = copy.copy(get_config_object().config)
    if name:
        c = {name: c[name]} if name in c.keys() else {}
    return c


@register_import()
def import_config(data, name=None):
    """Import given server configuration"""
    log.debug('Import server config: {0!s}'.format(data))
    res = {}
    data.pop('__timestamp__', None)
    for key, values in data.items():
        if name and name != key:
            continue
        r = set_privacyidea_config(key, values['Value'],
                                   desc=values['Description'] if 'Description' in values else None,
                                   typ=values['Type'] if 'Type' in values else None)
        res[key] = r
    log.info('Added configuration: {0!s}'.format(
        ', '.join([k for k, v in res.items() if v == 'insert'])))
    log.info('Updated configuration: {0!s}'.format(
        ', '.join([k for k, v in res.items() if v == 'update'])))


def get_multichallenge_enrollable_tokentypes():
    enrollable_tokentypes = []
    # If the token is enrollable via multichallenge
    for tclass in get_token_classes():
        if tclass.is_multichallenge_enrollable:
            enrollable_tokentypes.append(tclass.get_class_type())

    return enrollable_tokentypes
