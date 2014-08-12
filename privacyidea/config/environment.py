# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
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
'''
Pylons environment configuration
This file is part of the privacyidea service
'''

import os

from mako.lookup import TemplateLookup
from pylons import config
from pylons.error import handle_mako_error
from sqlalchemy import engine_from_config

import privacyidea.lib.app_globals as app_globals
import privacyidea.lib.helpers
from privacyidea.lib.log import log_with
from privacyidea.lib.resolvers.UserIdResolver import UserIdResolver
from privacyidea.config.routing import make_map


import sys
import inspect
import pkg_resources
import traceback
import warnings
warnings.filterwarnings(action='ignore', category=DeprecationWarning)

def fxn():
    warnings.warn("deprecated", DeprecationWarning)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    fxn()

import logging

log = logging.getLogger(__name__)

@log_with(log)
def load_environment(global_conf, app_conf):
    """
    Configure the Pylons environment via the ``pylons.config``
    object
    """

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[app_conf.get('custom_templates',
                                         os.path.join(root, 'templates')),
                            os.path.join(root, 'templates') ])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='privacyidea', paths=paths)

    config['privacyidea.root'] = root
    config['routes.map'] = make_map()
    config['pylons.app_globals'] = app_globals.Globals()
    config['pylons.h'] = privacyidea.lib.helpers


    ## add per token a location for the mako template lookup
    ## @note: the location is defined in the .ini file by
    ##  the entry [privacyideaTokenModules]

    directories = set()
    directories.update(paths['templates'])

    ## add a template path for every token
    modules = get_token_module_list()
    for module in modules:
        mpath = os.path.dirname(module.__file__)
        directories.add(mpath)

    ## add a template path for every resolver
    modules = get_resolver_module_list()
    for module in modules:
        mpath = os.path.dirname(module.__file__)
        directories.add(mpath)

    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=list(directories),
        error_handler=handle_mako_error,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # Setup the SQLAlchemy database engine
    # If we load the privacyidea.model here, the pylons.config is loaded with
    # the entries from the config file. if it is loaded at the top of the file,
    #the pylons.config does not contain the config file, yet.
    from privacyidea.model import init_model
    engine = engine_from_config(config, 'sqlalchemy.')
    init_model(engine)

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

    # We do this per request so that we will not get any problems with the paster
    #from privacyidea.lib.audit import getAudit
    #audit = getAudit()
    #config['audit'] = audit

    ## setup Security provider definition
    try:
        log.debug('loading token list definition')
        g = config['pylons.app_globals']
        g.security_provider.load_config(config)
    except Exception as e:
        log.error("Failed to load security provider definition: %r" % e)
        raise e

    ## load the list of tokenclasses
    try:
        log.debug('loading token list definition')
        (tcl, tpl) = get_token_class_list()

        config['tokenclasses'] = tcl
        g.setTokenclasses(tcl)

        config['tokenprefixes'] = tpl
        g.setTokenprefixes(tpl)

    except Exception as e:
        log.error("Failed to load token class list: %r" % e)
        raise e

    ## load the list of resolvers
    try:
        log.debug('loading resolver list definition')
        (rclass, rname) = get_resolver_class_list()

        ## make this globaly avaliable
        g.setResolverClasses(rclass)
        g.setResolverTypes(rname)

    except Exception as exx:
        log.error("Failed to load the list of resolvers: %r" % exx)
        raise exx
    
    # load the list of applications
    try:
        log.debug('loading application list')
        config['applications'] = get_applications()
        g.set_applications(config['applications'])
    except Exception as exx:
        log.error("Failed to load application modules: %r" % exx)
        raise exx

    ## get the help url
    url = config.get("privacyideaHelp.url", None)
    if url is None:
        version = pkg_resources.get_distribution("privacyidea").version
        # First try to get the help for this specific version
        url = "http://privacyidea.org/doc/%s" % version
    config['help_url'] = url

    log.debug("done")
    return


def get_application_modules():
    '''
    Returns the list of application modules
    that are configured in the ini-file in
    privacyideaMachine.applications
    and also loads the modules if necessary
    
    :return: list of string with the names of the modules
    '''
    app_modules = config.get("privacyideaMachine.applications", "")
    lines = app_modules.splitlines()
    app_modules_fixed = ",".join(lines)
    app_modules_list = [module.strip()
                        for module in app_modules_fixed.split(",")]
    
    for module in app_modules_list:
        # Import the modules
        __import__(module)
        
    return app_modules_list


def get_applications():
    '''
    returns a dictionary the application,
    the names being the key, the module name the value.
    that are configured in the ini-file in
    privacyideaMachine.applications
    
    :return: dictionary of name:module
    '''
    app_module_list = get_application_modules()
    applications = {}
    for m in app_module_list:
        module_name = eval(m).MachineApplication.get_name()
        applications[module_name] = m
    return applications


#######################################
def get_token_list():
    '''
    returns the list of the modules

    :return: list of token module names from the config file
    '''
    module_list = []

    ## append our derfault list so this will overwrite in
    ## the loaded classes finally
    module_list.append("privacyidea.lib.tokenclass")

    fallback_tokens = "privacyidea.lib.tokens.hmactoken, \
                        privacyidea.lib.tokens.smstoken, \
                        privacyidea.lib.tokens.totptoken, \
                        privacyidea.lib.tokens.motptoken, \
                        privacyidea.lib.tokens.radiustoken, \
                        privacyidea.lib.tokens.remotetoken, \
                        privacyidea.lib.tokens.vascotoken, \
                        privacyidea.lib.tokens.passwordtoken, \
                        privacyidea.lib.tokens.spasstoken, \
                        privacyidea.lib.tokens.tagespassworttoken, \
                        privacyidea.lib.tokens.yubicotoken, \
                        privacyidea.lib.tokens.yubikeytoken, \
                        privacyidea.lib.tokens.ocra2token, \
                        privacyidea.lib.tokens.emailtoken, \
                        privacyidea.lib.tokens.sshkeytoken, \
                        privacyidea.lib.tokens.daplugtoken"

    config_modules = config.get("privacyideaTokenModules", fallback_tokens)
    log.debug("%s " % config_modules)
    if config_modules:
        ## in the config *.ini files we have some line continuation slashes,
        ## which will result in ugly module names, but as they are followed by
        ## \n they could be separated as single entries by the following two
        ## lines
        lines = config_modules.splitlines()
        coco = ",".join(lines)
        for module in coco.split(','):
            if module.strip() != '\\':
                module_list.append(module.strip())

    return module_list

@log_with(log)
def get_token_module_list():
    '''
    return the list of the available token classes like hmac, spass, totp

    :return: list of token modules
    '''

    ## def load_token_modules
    module_list = get_token_list()
    log.debug("using the module list: %s" % module_list)

    modules = []
    for mod_name in module_list:
        if mod_name == '\\' or len(mod_name.strip()) == 0:
            continue

        ## load all token class implementations
        if mod_name in sys.modules:
            module = sys.modules[mod_name]
            log.debug('module %s loaded' % (mod_name))
        else:
            try:
                ## module = imp.load_module(mod_name,
                ##                            *imp.find_module(mod_name,pp))
                log.debug("import module: %s" % mod_name)
                exec("import %s" % mod_name)
                module = eval(mod_name)

            except Exception as exx:
                module = None
                log.error('unable to load token module : %r (%r)'
                                                            % (mod_name, exx))
                log.error(traceback.format_exc())
                raise Exception('unable to load token module : %r (%r)'
                                                            % (mod_name, exx))

        if module is not None:
            modules.append(module)

    return modules

@log_with(log)
def get_token_class_list():
    '''
    provide a dict of token types and their classes

    :return: tuple of two dict
             -tokenclass_dict  {token type : token class}
             -tokenprefix_dict {token type : token prefix}
    '''
    modules = get_token_module_list()

    ## load_token_classes
    tokenclass_dict = {}
    tokenprefix_dict = {}

    for module in modules:
        log.debug("module: %s" % module)
        for name in dir(module):
            obj = getattr(module, name)
            if inspect.isclass(obj):
                try:
                    # check if this is a TOKEN class
                    if issubclass(obj, privacyidea.lib.tokenclass.TokenClass):
                        typ = obj.getClassType()
                        class_name = "%s.%s" % (module.__name__, obj.__name__)

                        if typ is not None:
                            tokenclass_dict[typ] = class_name

                            prefix = 'LSUN'
                            if hasattr(obj, 'getClassPrefix'):
                                prefix = obj.getClassPrefix().upper()
                            tokenprefix_dict[typ.lower()] = prefix

                except Exception as e:
                    log.error("error constructing" +
                             " tokenclass_list: %r" % e)

    log.debug("the tokenclass list: %r"
              % tokenclass_dict)

    return (tokenclass_dict, tokenprefix_dict)

###############################################################################
@log_with(log)
def get_resolver_list():
    '''
    get the list of the resolvers
    :return: list of resolver names from the config file
    '''
    module_list = set()

    module_list.add("privacyidea.lib.resolvers.PasswdIdResolver")
    module_list.add("privacyidea.lib.resolvers.LDAPIdResolver")
    module_list.add("privacyidea.lib.resolvers.SCIMIdResolver")
    module_list.add("privacyidea.lib.resolvers.SQLIdResolver")

    # Dynamic Resolver modules
    config_modules = config.get("privacyideaResolverModules", '')
    log.debug("%s" % config_modules)
    if config_modules:
        ## in the config *.ini files we have some line continuation slashes,
        ## which will result in ugly module names, but as they are followed by
        ## \n they could be separated as single entries by the following two
        ## lines
        lines = config_modules.splitlines()
        coco = ",".join(lines)
        for module in coco.split(','):
            if module.strip() != '\\':
                module_list.add(module.strip())

    return module_list

@log_with(log)
def get_resolver_module_list():
    '''
    return the list of the available resolver classes like passw, sql, ldap

    :return: list of resolver modules
    '''

    ## def load_resolver_modules
    module_list = get_resolver_list()
    log.debug("using the module list: %s" % module_list)

    modules = []
    for mod_name in module_list:
        if mod_name == '\\' or len(mod_name.strip()) == 0:
            continue

        ## load all token class implementations
        if mod_name in sys.modules:
            module = sys.modules[mod_name]
            log.debug('module %s loaded' % (mod_name))
        else:
            try:
                ## module = imp.load_module(mod_name,
                ##                            *imp.find_module(mod_name,pp))
                log.debug("import module: %s" % mod_name)
                exec("import %s" % mod_name)
                module = eval(mod_name)

            except Exception as exx:
                module = None
                log.warning('unable to load token module : %r (%r)'
                           % (mod_name, exx))

        if module is not None:
            modules.append(module)

    return modules

@log_with(log)
def get_resolver_class_list():
    '''
    return the dict of resolver class objects
    '''
    resolverclass_dict = {}
    resolverprefix_dict = {}

    modules = get_resolver_module_list()
    base_class_repr = "privacyidea.lib.resolvers.UserIdResolver.UserIdResolver"
    for module in modules:
        log.debug("module: %s" % module)
        for name in dir(module):
            obj = getattr(module, name)
            if inspect.isclass(obj):
                try:
                    rtyp = repr(obj)
                    # check if this is a resolver class
                    if (issubclass(obj, UserIdResolver) and
                        base_class_repr not in rtyp):
                        # we index the resolver object under:
                        # useridresolver.PasswdIdResolver.IdResolver
                        # in the token.db the resolver refer to:
                        # useridresolver.PasswdIdResolver.IdResolver.myDefRes
                        class_name = "%s.%s" % (module.__name__, obj.__name__)
                        resolverclass_dict[class_name] = obj

                        prefix = class_name.split('.')[1]
                        if hasattr(obj, 'getResolverClassType'):
                            prefix = obj.getResolverClassType()

                        resolverprefix_dict[class_name] = prefix

                except Exception as e:
                    log.info("error constructing resolverclass_list: %r" % e)

    log.debug("the resolvernclass list: %r"
              % resolverclass_dict)

    return (resolverclass_dict, resolverprefix_dict)

###eof#########################################################################

