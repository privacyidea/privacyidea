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
__doc__="""The config module takes care about storing server configuration in
the Config database table.

It provides functions to retrieve (get) and and set configuration.

The code is tested in tests/test_lib_config
"""

import logging
import inspect
from flask import current_app

from .log import log_with
from ..models import Config, db

from .crypto import encryptPassword
from .crypto import decryptPassword
from .resolvers.UserIdResolver import UserIdResolver
from .machines.base import BaseMachineResolver
from .caconnectors.localca import BaseCAConnector
from datetime import datetime
import importlib

log = logging.getLogger(__name__)

ENCODING = 'utf-8'


#@cache.memoize(1)
def get_privacyidea_config():
    # timestamp = Config.query.filter_by(Key="privacyidea.timestamp").first()
    return get_from_config()


@log_with(log)
#@cache.memoize(1)
def get_from_config(key=None, default=None, role="admin"):
    """
    :param key: A key to retrieve
    :type key: string
    :param default: The default value, if it does not exist in the database
    :param role: The role which wants to retrieve the system config. Can be
        "admin" or "public". If "public", only values with type="public"
        are returned.
    :type role: string
    :return: If key is None, then a dictionary is returned. I a certain key
        is given a string/bool is returned.
    """
    default_true_keys = ["PrependPin", "splitAtSign",
                         "IncFailCountOnFalsePin", "ReturnSamlAttributes"]
    sql_query = Config.query
    if role != "admin":
        # set the filter to get only public infos!
        # We could match for "public", but matching for not "admin" seems to
        # be safer
        sql_query = sql_query.filter_by(Type="public")

    if key:
        sql_query = sql_query.filter_by(Key=key).first()
        if sql_query:
            rvalue = sql_query.Value
            if sql_query.Type == "password":
                rvalue = decryptPassword(rvalue)
        else:
            if key in default_true_keys:
                rvalue = "True"
            else:
                rvalue = default
    else:
        rvalue = {}
        sql_query.all()
        for entry in sql_query:
            value = entry.Value
            if entry.Type == "password":
                value = decryptPassword(value)
            rvalue[entry.Key] = value
        if role == "admin":
            for tkey in default_true_keys:
                if tkey not in rvalue:
                    rvalue[tkey] = "True"

    return rvalue


#@cache.memoize(1)
def get_resolver_types():
    """
    Return a simple list of the type names of the resolvers.
    :return: array of resolvertypes like 'passwdresolver'
    :rtype: array
    """
    resolver_types = []
    if "pi_resolver_types" in current_app.config:
        resolver_types = current_app.config["pi_resolver_types"]
    else:
        (_r_classes, r_types) = get_resolver_class_dict()
        resolver_types = r_types.values()
        current_app.config["pi_resolver_types"] = resolver_types
    
    return resolver_types


def get_caconnector_types():
    """
    Returns a list of valid CA connector types
    :return:
    """
    return ["local"]


#@cache.memoize(1)
def get_resolver_classes():
    """
    Returns a list of the available resolver classes like:
    [<class 'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver'>,
    <class 'privacyidea.lib.resolvers.UserIdResolver.UserIdResolver'>]

    :return: array of resolver classes
    :rtype: array
    """
    resolver_classes = []
    if "pi_resolver_classes" in current_app.config:
        resolver_classes = current_app.config["pi_resolver_classes"]
    else:
        (r_classes, _r_types) = get_resolver_class_dict()
        resolver_classes = r_classes.values()
        current_app.config["pi_resolver_classes"] = resolver_classes
    
    return resolver_classes


#@cache.memoize(1)
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


#@cache.memoize(1)
def get_token_class(tokentype):
    """
    This takes a token type like "hotp" and returns a class
    like <class privacidea.lib.tokens.hotptoken.HotpTokenClass>
    :return: The tokenclass for the given type
    :rtype: tokenclass
    """
    if tokentype.lower() == "hmac":
        tokentype = "hotp"
    class_dict, type_dict = get_token_class_dict()
    tokenmodule = ""
    tokenclass = None
    for module, ttype in type_dict.items():
        if ttype.lower() == tokentype.lower():
            tokenmodule = module
            break
    if tokenmodule:
        tokenclass = class_dict.get(tokenmodule)

    return tokenclass


#@cache.memoize(1)
def get_token_types():
    """
    Return a simple list of the type names of the tokens.
    :return: array of tokentypes like 'hotp', 'totp'...
    :rtype: array
    """
    tokentypes = []
    if "pi_token_types" in current_app.config:
        tokentypes = current_app.config["pi_token_types"]
    else:
        (_t_classes, t_types) = get_token_class_dict()
        tokentypes = t_types.values()
        current_app.config["pi_token_types"] = tokentypes

    return tokentypes


#@cache.memoize(1)
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


#@cache.memoize(1)
def get_token_classes():
    """
    Returns a list of the available token classes like:
    [<class 'privacyidea.lib.tokens.totptoken.TotpTokenClass'>,
    <class 'privacyidea.lib.tokens.hotptoken.HotpTokenClass'>]

    :return: array of token classes
    :rtype: array
    """
    token_classes = []
    if "pi_token_classes" in current_app.config:
        token_classes = current_app.config["pi_token_classes"]
    else:
        (t_classes, _t_types) = get_token_class_dict()
        token_classes = t_classes.values()
        current_app.config["pi_token_classes"] = token_classes

    return token_classes

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


#@cache.memoize(1)
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
    base_class_repr = "privacyidea.lib.resolvers.UserIdResolver.UserIdResolver"
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
#@cache.memoize(1)
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
#@cache.memoize(1)
def get_token_list():
    """
    get the list of the tokens
    :return: list of token names from the config file
    """
    module_list = set()

    # TODO: migrate the implementations and uncomment
    module_list.add("privacyidea.lib.tokens.daplugtoken")
    module_list.add("privacyidea.lib.tokens.hotptoken")
    module_list.add("privacyidea.lib.tokens.motptoken")
    module_list.add("privacyidea.lib.tokens.passwordtoken")
    module_list.add("privacyidea.lib.tokens.remotetoken")
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
    module_list.add("privacyidea.lib.tokens.u2ftoken")
    module_list.add("privacyidea.lib.tokens.papertoken")
    module_list.add("privacyidea.lib.tokens.questionnairetoken")

    #module_list.add(".tokens.tagespassworttoken")
    #module_list.add(".tokens.vascotoken")
    
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
            log.warning('unable to load resolver module : {0!r} ({1!r})'.format(mod_name, exx))

    return modules


#@cache.memoize(1)
def get_resolver_module_list():
    """
    return the list of modules of the available resolver classes
    like passw, sql, ldap

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


#@cache.memoize(1)
def get_caconnector_module_list():
    """
    return the list of modules of the available CA connector classes

    :return: list of CA connector modules
    """
    module_list = set()
    module_list.add("privacyidea.lib.caconnectors.localca.LocalCAConnector")

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


#@cache.memoize(1)
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
    Can by of type "password" or "public". "password" gets encrypted.
    """
    if not typ:
        # check if this is a token specific config and if it should be public
        try:
            token_type = key.split(".")[0]
            tclass = get_token_class(token_type)
            typ = tclass.get_setting_type(key)
        except Exception:
            log.debug("This seems to be no token specific setting")

    ret = 0
    if typ == "password":
        # store value in encrypted way
        value = encryptPassword(value)
    # We need to check, if the value already exist
    q1 = Config.query.filter_by(Key=key).count()
    if q1 > 0:
        # The value already exist, we need to update
        data = {'Value': value}
        if typ:
            data.update({'Type': typ})
        if desc:
            data.update({'Description': desc})
        Config.query.filter_by(Key=key).update(data)
        ret = "update"
    else:
        new_entry = Config(key, value, typ, desc)
        db.session.add(new_entry)
        ret = "insert"
        
    # Do the timestamp
    if Config.query.filter_by(Key="__timestamp__").count() > 0:
        Config.query.filter_by(Key="__timestamp__")\
            .update({'Value': datetime.now()})
    else:
        new_timestamp = Config("__timestamp__", datetime.now())
        db.session.add(new_timestamp)
    db.session.commit()
    return ret


def delete_privacyidea_config(key):
    """
    Delete a config entry
    """
    ret = 0
    # We need to check, if the value already exist
    q = Config.query.filter_by(Key=key).first()
    if q:
        db.session.delete(q)
        db.session.commit()
        ret = True
    return ret


#@cache.memoize(1)
def get_inc_fail_count_on_false_pin():
    """
    Return if the Failcounter should be increased if only tokens
    with a false PIN were identified.
    :return: True of False
    :rtype: bool
    """
    r = get_from_config(key="IncFailCountOnFalsePin")
    # The values are strings, so we need to compare:
    r = (r.lower() == "true" or r == "1")
    return r


#@cache.memoize(1)
def get_prepend_pin():
    """
    Get the status of the "PrependPin" Config

    :return: True or False
    :rtype: bool
    """
    r = get_from_config(key="PrependPin")
    # The values are strings, so we need to compare:
    r = (r.lower() == "true" or r == "1")
    return r


def set_prepend_pin(prepend=True):
    """
    Set the status of the "PrependPin" Config
    :param prepend: If the PIN should be prepended or not
    :return: None
    """
    set_privacyidea_config("PrependPin", prepend)


def return_saml_attributes():
    r = get_from_config(key="ReturnSamlAttributes", default="true")
    r = (r.lower() == "true" or r == "1")
    return r
