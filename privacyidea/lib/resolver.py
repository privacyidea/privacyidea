# -*- coding: utf-8 -*-
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
resolver handling
'''


import logging
import re
import copy

from privacyidea.lib.context import context

from privacyidea.lib.config import storeConfig
from privacyidea.lib.config import getGlobalObject
from privacyidea.lib.config import removeFromConfig
from privacyidea.lib.config import get_privacyIDEA_config

from privacyidea.lib.util import getParam
from privacyidea.lib.crypto import decryptPassword

import traceback
from privacyidea.lib.log import log_with

required = True
optional = False


__all__ = [ 'defineResolver', 'checkResolverType', 'splitResolver',
            'getResolverList', 'getResolverInfo', 'deleteResolver',
            'getResolverObject', 'initResolvers', 'closeResolvers',
            'setupResolvers'
            ]

log = logging.getLogger(__name__)


class Resolver():
    """
    helper class to define a new resolver
    """
    def __init__(self, name=None):
        self.name = name
        self.type = None
        self.data = {}
        self.types = {}
        self.desc = {}

    def getDefinition(self, param):
        self.name = getParam(param, 'resolver', required)
        return getResolverInfo(self.name)

    @log_with(log)
    def setDefinition(self, param):
        '''
            handle name
        '''
        self.name = getParam(param, 'name', required)
        # We should have no \.
        # This only leads to problems.
        nameExp = "^[A-Za-z0-9_\-]+$"
        if re.match(nameExp, self.name) is None:
            e = Exception("non conformant characters in resolver name: " + self.name + " (not in " + nameExp + ")")
            raise e

        ## handle types
        self.type = getParam(param, 'type', required)
        resolvertypes = get_resolver_types()
        if self.type not in resolvertypes:
            e = Exception("resolver type : %s not in %s" %
                          (self.type, unicode(resolvertypes)))
            raise e

        resolvers = getResolverList(filter_resolver_type=self.type)
        for resolver in resolvers:
            if self.name.lower() == resolver.lower():
                if self.name == resolver:
                    continue
                e = Exception("resolver with similar name already exists: %s" %
                              (resolver))
                raise e

        resolver_config = get_resolver_classConfig(self.type)
        if self.type in resolver_config:
            config = resolver_config.get(self.type).get('config', {})
        else:
            config = resolver_config

        for k in param:
            if k != 'name' and k != 'type':
                if k.startswith('type.') == True:
                    key = k[len('type.'):]
                    self.types[key] = param.get(k)
                elif k.startswith('desc.') == True:
                    key = k[len('desc.'):]
                    self.desc[key] = param.get(k)

                elif 'session' == k:
                    ## supress session parameter
                    pass
                else:
                    self.data[k] = param.get(k)
                    if k in config:
                        self.types[k] = config.get(k)
                    else:
                        log.warn("the passed key %r is not a "
                                 "parameter for the resolver %r" % (k, self.type))
        ## now check if we have for every type def an parameter
        ok = self._sanityCheck()
        if ok != True:
            raise Exception("type definition does not match parameter! %s"
                            % unicode(param))

        return

    def _sanityCheck(self):
        ret = True
        for t in self.types:
            if self.data.has_key(t) == False:
                ret = False
        for t in self.desc:
            if self.data.has_key(t) == False:
                ret = False

        return ret

    @log_with(log)
    def saveConfig(self):
        res = 'success'
        if self.name is None:
            return "no resolver name defined"
        # do the setConfig()'s
        prefix = self.type + "."
        postfix = "." + self.name

        for d in self.data:
            key = prefix + d + postfix
            val = self.data.get(d)
            typ = None
            desc = None
            if self.types.has_key(d) == True:
                typ = self.types.get(d)

            if self.desc.has_key(d) == True:
                desc = self.desc.get(d)

            res = storeConfig(key, val, typ, desc)

        return res

@log_with(log)
def defineResolver(params):
    """
    set up a new resolver from request parameters

    :param params: dict of request parameters
    """
    resolver = Resolver()
    resolver.setDefinition(params)
    res = resolver.saveConfig()
    return res


@log_with(log)
def checkResolverType(resolver):
    """
    check if a resolver of the given type exists
    :param resolver: full qualified resolver name
                     or optional with trailing conf like:
                       useridresolver.PasswdIdResolver.IdResolver.etc_resl
    :return: Tuple of bool (True|False) and resolver
    """
    res = ""
    ret = False

    ## prepare
    reso = resolver.strip()
    reso = reso.replace("\"", "")

    ## the fully qualified resolver
    if reso in context.resolver_clazzes:
        res = context.resolver_clazzes.get(reso)
        ret = True
    else:
        ## if the last argument is the configuration
        pack = reso.split('.')
        rtype = ".".join(pack[:-1])
        conf = pack[-1]

        ## lookup, if there is a resolver definition
        if rtype in context.resolver_types:
            res = "%s.%s" % (rtype, conf)
            ret = True
        ##
        else:
            ## legacy support, where resolver is defined as
            #    "useridresolver.passwdresolver.mrealm"
            # so we only could rely only on the type definition e.g.
            #  'passwdresolver' as part of the string
            for res_id, res_type in context.resolver_types.iteritems():
                if res_type in reso:
                    res = "%s.%s" % (res_id, conf)
                    ret = True
                    break

    ##  is resolver defined in the privacyidea config
    try:
        getResolverObject(res)
    except Exception as exx:
        log.error("Failed to setup resolver %r: %r" % (res, exx))
        log.error("%r" % traceback.format_exc())
        # upper layer (controller) will catch
        raise(exx)
        # res = False
        # ret = False

    return (ret, res)

#### helper functions to retrieve information from the UserIDResolvers ###################
@log_with(log)
def splitResolver(resolver):

    reso = resolver.strip()
    reso = reso.replace("\"", "")
    # old lin-otp had only 3 parts.
    # new lin-otp had 4 parts. 
    # we break compatibility and have more than 4 parts.    
    try:
        l = reso.rsplit('.',3)
        package = l[0]
        module = l[1]
        class_ = l[2]
        conf = l[3]
    except Exception as e:
        log.error("split of resolver failed %s : %r " % (reso, e))
        raise Exception("invalid resolver class specification" + reso)
    return (package, module, class_, conf)

## external system/getResolvers
@log_with(log)
def getResolverList(filter_resolver_type=None):
    '''
    Gets the list of configured resolvers

    :param filter_resolver_type: Only resolvers of the given type are returned
    :type filter_resolver_type: string
    :rtype: Dictionary of the resolvers and their configuration
    '''
    Resolvers = {}
    resolvertypes = get_resolver_types()

    conf = get_privacyIDEA_config()
    for entry in conf:

        for typ in resolvertypes:
            if entry.startswith("privacyidea." + typ):
                #the realm might contain dots "."
                # so take all after the 3rd dot for realm
                r = {}
                resolver = entry.split(".", 3)
                # An old entry without resolver name
                if len(resolver) <= 3:
                    break
                r["resolvername"] = resolver[3]
                r["entry"] = entry
                r["type"] = typ

                if (filter_resolver_type is None) or (filter_resolver_type and filter_resolver_type == typ):
                    Resolvers[resolver[3]] = r
                # Dont check the other resolver types
                break

    return Resolvers


@log_with(log)
def getResolverInfo(resolvername):
    '''
    return the resolver info of the given resolvername

    :param resolvername: the requested resolver
    :type  resolvername: string

    :return : dict of resolver description
    '''
    resolver_dict = {}
    typ = ""
    resolvertypes = get_resolver_types()

    descr = {}

    conf = get_privacyIDEA_config()

    for entry in conf:

        for typ in resolvertypes:

            ## get the typed values of the descriptor!
            resolver_conf = get_resolver_classConfig(typ)
            if typ in resolver_conf:
                descr = resolver_conf.get(typ).get('config', {})
            else:
                descr = resolver_conf

            if entry.startswith("privacyidea." + typ) and entry.endswith(resolvername):
                #the realm might contain dots "."
                # so take all after the 3rd dot for realm
                resolver = entry.split(".", 3)
                # An old entry without resolver name
                if len(resolver) <= 3:
                    break

                value = conf.get(entry)
                if resolver[2] in descr:
                    configEntry = resolver[2]
                    if descr.get(configEntry) == 'password':

                        ## do we already have the decrypted pass?
                        if 'enc' + entry in conf:
                            value = conf.get('enc' + entry)
                        else:
                            ## if no, we take the encpass and decrypt it
                            value = conf.get(entry)
                            try:
                                en = decryptPassword(value)
                                value = en
                            except:
                                log.info("Decryption of resolver passwd failed: compatibility issue?")

                resolver_dict[ resolver[2] ] = value
                # Dont check the other resolver types

                break

    return { "type" : typ, "data" : resolver_dict, "resolver" : resolvername}

@log_with(log)
def deleteResolver(resolvername):
    '''
    delete a resolver and all related config entries

    :paramm resolvername: the name of the to be deleted resolver
    :type   resolvername: string
    :return: sucess or fail
    :rtype:  boelean

    '''
    res = False

    resolvertypes = get_resolver_types()
    conf = get_privacyIDEA_config()

    delEntries = []

    for entry in conf:
        rest = entry.split(".", 3)
        lSplit = len(rest)
        if lSplit > 3:
            rConf = rest[lSplit - 1]
            if rConf == resolvername:
                if rest[0] == "privacyidea" or rest[0] == "encprivacyidea" :
                    typ = rest[1]
                    if typ in resolvertypes:
                        delEntries.append(entry)

    if len(delEntries) > 0 :
        try:
            for entry in delEntries:
                res = removeFromConfig(entry)
                log.debug("removing key: %s" % entry)
                res = True
        except Exception as e:
            log.error("deleteResolver: %r" % e)
            res = False


    return res




## external in token.py user.py validate.py
@log_with(log)
def getResolverObject(resolvername):
    """
    get the resolver instance from a resolver name spec
    - either take the class from the request context
    - or create one from the global object list + init with resolver config

    :remark: the resolver object is preserved in the request context, so that
              a resolver could preserve a connection durung a request

    :param resolvername: the resolver string as from the token including
                         the config as last part
    :return: instance of the resolver with the loaded config

    """
    r_obj = None
    ### this patch is a bit hacky:
    ## the normal request has a request context, where it retrieves
    ## the resolver info from and preserves the loaded resolvers for reusage
    ## But in case of a authentication request (by a redirect from a 401)
    ## the caller is no std request and the context object is missing :-(
    ## The solution is to deal with local references, either to the
    ## global context or to local data (where we have no reuse of the resolver)

    resolvers_loaded = {}
    r_obj_class = None
    try:
        if hasattr(context, 'resolvers_loaded') == False:
            setattr(context, 'resolvers_loaded', {})
        resolvers_loaded = context.resolvers_loaded
    except Exception as exx:
        resolvers_loaded = {}

    ## test if there is already a resolver of this kind loaded
    if resolvername in resolvers_loaded:
        return resolvers_loaded.get(resolvername)

    ## no resolver - so instantiate one
    else:
        parts = resolvername.split('.')
        if len(parts) > 2:
            re_name = '.'.join(parts[:-1])
            r_obj_class = get_resolver_class(re_name)

        if r_obj_class is None:
            log.error("unknown resolver class %s " % resolvername)
            return r_obj

        ## create the resolver instance and load the config
        r_obj = r_obj_class()
        conf = resolvername.split(".")[-1]

        if r_obj is not None:
            config = get_privacyIDEA_config()
            r_obj.loadConfig(config, conf)
            resolvers_loaded[resolvername] = r_obj

    return r_obj

## external lib/base.py
@log_with(log)
def setupResolvers(config=None, cache_dir="/tmp"):
    """
    hook for the server start -
        initialize the resolvers
    """
    glo = getGlobalObject()

    resolver_clazzes = copy.deepcopy(glo.getResolverClasses())
    for resolver_clazz in resolver_clazzes.values():
        if hasattr(resolver_clazz, 'setup'):
            try:
                resolver_clazz.setup(config=config, cache_dir=cache_dir)
            except Exception as exx:
                log.error("failed to call setup of %r" % resolver_clazz)

    return

@log_with(log)
def initResolvers():
    """
    hook for the request start -
        create  a deep copy of the dict with the global resolver classes
    """
    try:
        glo = getGlobalObject()

        resolver_clazzes = copy.deepcopy(glo.getResolverClasses())
        setattr(context, 'resolver_clazzes', resolver_clazzes)

        resolver_types = copy.deepcopy(glo.getResolverTypes())
        setattr(context, 'resolver_types', resolver_types)

        ## dict of all resolvers, which are instatiated during the request
        setattr(context, 'resolvers_loaded', {})

    except Exception as exx:
        log.error("Failed to initialize resolver in context %r" % exx)
    return

## external lib/base.py
@log_with(log)
def closeResolvers():
    """
    hook to close the resolvers at the end of the request
    """

    if hasattr(context, 'resolvers_loaded'):
        try:
            for resolver in context.resolvers_loaded.values():
                if hasattr(resolver, 'close'):
                    resolver.close()

        except Exception as exx:
            log.error("Failed to close resolver in context %r" % exx)
    return


## internal functions
@log_with(log)
def get_resolver_class(resolver_type):
    '''
    return the class object for a resolver type
    :param resolver_type: string specifying the resolver
                          fully qualified or abreviated
    :return: resolver object class
    '''
    ret = None

    ### this patch is a bit hacky:
    ## the normal request has a request context, where it retrieves
    ## the resolver info from and preserves the loaded resolvers for reusage
    ## But in case of a authentication request (by a redirect from a 401)
    ## the caller is no std request and the context object is missing :-(
    ## The solution is, to deal with local references, either to the
    ## global context or to local data

    try:
        resolver_clazzes = context.resolver_clazzes
        resolver_types = context.resolver_types
    except Exception as exx:
        glo = getGlobalObject()
        resolver_clazzes = copy.deepcopy(glo.getResolverClasses())
        resolver_types = copy.deepcopy(glo.getResolverTypes())

    parts = resolver_type.split('.')
    ## resolver is fully qualified
    if len(parts) > 1:
        if resolver_type in resolver_clazzes:
            ret = resolver_clazzes.get(resolver_type)

    ## resolver is in abreviated form, we have to do a reverse lookup
    elif resolver_type in resolver_types.values():
        for k, v in resolver_types.iteritems():
            if v == resolver_type:
                ret = resolver_clazzes.get(k, None)
                break
    if ret is None:
        pass
    return ret


def get_resolver_types():
    """
    get the array of the registred resolvers

    :return: array of resolvertypes like 'passwdresolver'
    """
    return context.resolver_types.values()


@log_with(log)
def get_resolver_classConfig(claszzesType):
    """
    get the configuration description of a resolver

    :param claszzesType: literal resolver type
    :return: configuration description dict
    """
    descriptor = None
    resolver_class = get_resolver_class(claszzesType)

    if resolver_class is not None:
        descriptor = resolver_class.getResolverClassDescriptor()

    return descriptor

def get_resolver_name(idRes):
    '''
    :param idRes: The id of a resolver in the dotted notation
    :return: the name of the resolver
    
    The name of the resolver is always the last part
    
    privacyidea.passwdidresolver.filename.reso1 will return "reso1"
    '''
    parts = idRes.split('.')
    return parts[-1]


#eof###########################################################################

