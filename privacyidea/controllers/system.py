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
This file is part of the privacyidea service
'''
import json
import re
import webob

from privacyidea.lib.selftest import isSelfTest
from pylons import request, response, config, tmpl_context as c

from privacyidea.model.meta import Session

from privacyidea.lib.base import BaseController

from privacyidea.lib.config  import storeConfig
from privacyidea.lib.config  import getFromConfig
from privacyidea.lib.config  import updateConfig
from privacyidea.lib.config  import removeFromConfig

from privacyidea.lib.realm  import setDefaultRealm
from privacyidea.lib.realm  import isRealmDefined

from privacyidea.weblib.util import get_client

from privacyidea.lib.resolver import defineResolver
from privacyidea.lib.resolver import checkResolverType
from privacyidea.lib.resolver import getResolverList
from privacyidea.lib.resolver import getResolverInfo
from privacyidea.lib.resolver import deleteResolver
from privacyidea.lib.resolver import get_resolver_name

from privacyidea.lib.error   import ParameterError

from privacyidea.lib.util import remove_session_from_param
from privacyidea.lib.util    import getParam, getLowerParams
from privacyidea.lib.reply   import sendResult, sendError, sendXMLResult, sendXMLError
from privacyidea.lib.realm   import getRealms
from privacyidea.lib.realm   import getDefaultRealm
from privacyidea.lib.user    import setRealm
from privacyidea.lib.user    import getUserFromRequest

from privacyidea.lib.realm   import deleteRealm
from privacyidea.lib.token   import newToken
from privacyidea.lib.token import get_token_type_list
from privacyidea.lib.token import get_policy_definitions
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.policy import PolicyException
from privacyidea.lib.config import get_privacyIDEA_config

from privacyidea.weblib.policy import setPolicy
from privacyidea.weblib.policy import deletePolicy
from privacyidea.lib.log import log_with
from paste.fileapp import FileApp
from cgi import escape
from pylons.i18n.translation import _

ENCODING = "utf-8"

import traceback
import logging
log = logging.getLogger(__name__)

optional = True
required = False


class SystemController(BaseController):

    '''
    The privacyidea.controllers are the implementation of the web-API to talk to the privacyIDEA server.
    The SystemController is used to configure the privacyIDEA server.
    The functions of the SystemController are invoked like this

        https://server/system/<functionname>

    The functions are described below in more detail.
    '''

    @log_with(log)
    def __before__(self, action, **params):
        '''
        __before__ is called before every action
             so we can check the authorization (fixed?)

        :param action: name of the to be called action
        :param params: the list of http parameters

        :return: return response
        :rtype:  pylon response
        '''
        try:
            c.audit['success'] = False
            c.audit['client'] = get_client()
            self.Policy = PolicyClass(request, config, c,
                                      get_privacyIDEA_config(),
                                      token_type_list = get_token_type_list())
            self.before_identity_check(action)
            
            # check authorization
            if action not in ["_add_dynamic_tokens", 'setupSecurityModule',]:
                self.Policy.checkPolicyPre('system', action)

            ## default return for the __before__ and __after__
            return response

        except PolicyException as pex:
            log.error("%r: policy exception %r" % (action, pex))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, pex, context='before')

        except webob.exc.HTTPUnauthorized as acc:
            ## the exception, when an abort() is called if forwarded
            log.error("%r: webob.exception %r" % (action, acc))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            raise acc

        except Exception as exx:
            log.error("%r: exception %r" % (action, exx))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, exx, context='before')

        finally:
            pass


    @log_with(log)
    def __after__(self, action, **params):
        '''
        __after is called after every action

        :return: return the response
        :rtype:  pylons response
        '''
        try:
            c.audit['administrator'] = getUserFromRequest(request).get("login")
            self.audit.log(c.audit)
            ## default return for the __before__ and __after__
            return response

        except Exception as exx:
            log.error("exception %r" % (exx))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, exx, context='after')

        finally:
            pass


########################################################

    def setDefault(self):
        """
        method:
            system/set

        description:
            define default settings for tokens. These default settings
            are used when new tokens are generated. The default settings will
            not affect already enrolled tokens.

        arguments:
            DefaultMaxFailCount    - Default value for the maximum allowed authentication failures
            DefaultSyncWindow      - Default value for the synchronization window
            DefaultCountWindow     - Default value for the coutner window
            DefaultOtpLen          - Default value for the OTP value length -- usuall 6 or 8
            DefaultResetFailCount  - Default value, if the FailCounter should be reset on successful authentication [True|False]


        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}
        count = 0
        description = "setDefault: parameters are\
        DefaultMaxFailCount\
        DefaultSyncWindow\
        DefaultCountWindow\
        DefaultOtpLen\
        DefaultResetFailCount\
        "

        keys = [ "DefaultMaxFailCount", "DefaultSyncWindow", "DefaultCountWindow", "DefaultOtpLen",
                "DefaultResetFailCount"]


        ### config settings from here
        try:
            param = getLowerParams(request.params)

            for k in keys:
                if param.has_key(k.lower()):
                    value = getParam(param, k.lower(), required)
                    ret = storeConfig(k, value)
                    des = "set " + k
                    res[des] = ret
                    count = count + 1

                    c.audit['success'] = count
                    c.audit['info'] += "%s=%s, " % (k, value)

            if count == 0 :
                log.warning("Failed saving config. Could not find any known parameter. %s"
                    % description)
                raise ParameterError("Usage: %s" % description, id=77)

            Session.commit()
            return sendResult(response, res)

        except Exception as exx:
            log.error('commit failed: %r' % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    def setConfig(self):
        """
        set a configuration key or a set of configuration entries

        parameter could either be in the form key=..&value=..
        or as a set of generic keyname=value pairs.

        *remark: In case of key-value pairs the type information could be
                 provided by an additional parameter with same keyname with the
                 postfix ".type". Value could then be 'password' to trigger the
                 storing of the value in an encrypted form

        :param key: configuration entry name
        :param value: configuration value
        :param type: type of the value: int or string/text or password
                     password will trigger to store the encrypted value
        :param description: additional information for this config entry

        * or
        :param key-value pairs: pair of &keyname=value pairs
        :return: a json result with a boolean "result": true
        """

        res = {}
        param = {}

        try:
            param.update(request.params)
            if "key" in param:

                key = param.get("key")
                val = param.get("value", None)
                typ = param.get("type", None)
                des = param.get("description", None)

                if val is None:
                    raise ParameterError("Required parameters: value")

                ret = storeConfig(key, val, typ, des)
                string = "setConfig %s" % key
                res[string] = ret

                c.audit['success'] = True
                c.audit['info'] = "%s=%s" % (key, val)

            else:
                ## we gather all key value pairs in the conf dict
                conf = {}
                for key in remove_session_from_param(param):
                    val = param.get(key, '') or ''

                    Key = key
                    if not key.startswith('privacyidea'):
                        Key = 'privacyidea.' + key
                    conf[Key] = val

                    string = "setConfig " + key + ":" + val
                    res[string] = True

                    c.audit['success'] = True
                    c.audit['info'] += "%s=%s, " % (key, val)

                updateConfig(conf)

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error saving config: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()

########################################################

    @log_with(log)
    def delConfig(self, action, **params):
        """
        delete a configuration key
        * if an error occurs an exception is serializedsetConfig and returned

        :param key: configuration key name
        :returns: a json result with the deleted value

        """
        res = {}

        try:
            param = getLowerParams(request.params)

            key = getParam(param, "key", required)
            ret = removeFromConfig(key)
            string = "delConfig " + key
            res[string] = ret

            c.audit['success'] = ret
            c.audit['info'] = key

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error deleting config: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
########################################################

    @log_with(log)
    def getConfig(self, action, **params):
        """
        retrieve value of a defined configuration key, or if no key is given,
        the complete configuration is returned
        if an error occurs an exception is serialized and returned

        * remark: the assumption is, that the access to system/getConfig
                  is only allowed to privileged users

        :param key: generic configuration entry name (optional)

        :return: a json result with key value or all key + value pairs

        """
        res = {}
        param = {}
        try:
            param.update(remove_session_from_param(request.params))

            ## if there is no parameter, we return them all
            if len(param) == 0:
                conf = get_privacyIDEA_config()
                keys = conf.keys()
                keys.sort()
                for key in keys:
                    if key.startswith("encprivacyidea."):
                        continue
                    if key.startswith("privacyidea."):
                        Key = key[len("privacyidea."):]
                        typ = type(conf.get(key)).__name__
                        if typ == 'datetime':
                            res[Key] = unicode(conf.get(key))
                        else:
                            res[Key] = conf.get(key)


                ## as we return the decrypted values, we could do this in place
                ## and display the value under the original key
                for key in keys:
                    if key.startswith("encprivacyidea."):
                        Key = key[len("encprivacyidea."):]
                        res[Key] = conf.get(key)

                c.audit['success'] = True
                c.audit['info'] = "complete config"

            else:
                key = getParam(param, "key", required)
                ret = getFromConfig(key)
                string = "getConfig " + key
                res[string] = ret

                c.audit['success'] = ret
                c.audit['info'] = "config key %s" % key

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error getting config: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def getRealms(self, action, **params):
        '''
        method:
            system/getRealms

        description:
            returns all realm definitinos as a json result.

        arguments:

        returns:
            a json result with a list of Realms

        exception:
            if an error occurs an exception is serialized and returned


        Either the admin has the policy scope=system, action=read
        or he is rights in scope=admin for some realms.
        If he does not have the system-read-right, then he will only
        see the realms, he is admin of.
        '''




        ### config settings from here
        try:
            param = getLowerParams(request.params)
            res = getRealms()
            c.audit['success'] = True

            # If the admin is not allowed to see all realms, (policy scope=system, action=read)
            # the realms, where he has no administrative rights need, to be stripped.

            polPost = self.Policy.checkPolicyPost('system', 'getRealms', { 'realms' : res })
            res = polPost['realms']

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pex:
            log.error("policy exception: %r" % pex)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, pex)

        except Exception as exx:
            log.error("error getting realms: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def setResolver(self, action, **params):
        """
        method:
            system/setResolver

        description:
            creates or updates a useridresolver

        arguments:
            name    -    the name of the resolver
            type    -    the type of the resolver [ldapsersolver, sqlresolver]

            LDAP:
                LDAPURI
                LDAPBASE
                BINDDN
                BINDPW
                TIMEOUT
                SIZELIMIT
                LOGINNAMEATTRIBUTE
                LDAPSEARCHFILTER
                LDAPFILTER
                USERINFO
                NOREFERRALS        - True|False
            SQL:
                Database
                Driver
                Server
                Port
                User
                Password
                Table
                Map

        returns:
            a json result with the found value

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}
        param = {}

        try:
            param.update(request.params)

            res = defineResolver(param)

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error saving config: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def getResolvers(self, action, **params):
        """
        method:
            system/getResolvers

        descriptions:
            returns a json list of all useridresolvers

        arguments:

        returns:
            a json result with a list of all available resolvers

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}

        try:
            res = getResolverList()

            c.audit['success'] = True
            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error getting resolvers: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def delResolver(self, action, **params):
        """
        method:
            system/delResolver

        description:
            this function deletes an existing resolver
            All config keys of this resolver get deleted

        arguments:
            resolver - the name of the resolver to delete.

        returns:
            success state

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}

        try:
            param = getLowerParams(request.params)

            resolver = getParam(param, "resolver", required)
            ### only delete a resolver, if it is not used by any realm
            found = False
            fRealms = []
            realms = getRealms()
            for realm in realms:
                info = realms.get(realm)
                reso = info.get('useridresolver')

                for idRes in reso:
                    if resolver == get_resolver_name(idRes):
                        fRealms.append(realm)
                        found = True

            if found == True:
                c.audit['failed'] = res
                err = 'Resolver %r  still in use by the realms: %r' % \
                                    (resolver, fRealms)
                c.audit['info'] = err
                raise Exception('%r !' % err)

            res = deleteResolver(resolver)
            c.audit['success'] = res
            c.audit['info'] = resolver

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error deleting resolver: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def getResolver(self, action, **params):
        """
        method:
            system/getResolver

        description:
            this function retrieves the definition of the resolver

        arguments:
            resolver - the name of the resolver

        returns:
            a json result with the configuration of a specified resolver

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}

        try:
            param = getLowerParams(request.params)

            resolver = getParam(param, "resolver", required)
            if (len(resolver) == 0):
                raise Exception ("[getResolver] missing resolver name")

            res = getResolverInfo(resolver)

            c.audit['success'] = True
            c.audit['info'] = resolver

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error getting resolver: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


    @log_with(log)
    def get_resolver_list(self, action, **params):
        res = {}
        try:
            from privacyidea.config.environment import get_resolver_list as getlist
            list = getlist()
            res['resolverlist'] = [l for l in list]
            res['resolvertypes'] = [l.split(".")[-1] for l in list]
            return sendResult(response, res, 1)
        except Exception as exx:
            Session.rollback()
            return sendError(response, exx)
        finally:
            Session.close()

########################################################
    @log_with(log)
    def setDefaultRealm(self, action, **params):
        """
        method:
            system/setDefaultRealm

        description:
            this function sets the given realm to the default realm

        arguments:
            realm - the name of the realm, that should be the default realm

        returns:
            a json result with a list of Realms

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = False

        try:
            param = getLowerParams(request.params)

            defRealm = getParam(param, "realm", optional)
            if defRealm is None:
                defRealm = ""

            defRealm = defRealm.lower().strip()
            res = setDefaultRealm(defRealm)
            if res == False and defRealm != "" :
                c.audit['info'] = "The realm %s does not exist" % defRealm

            c.audit['success'] = True
            c.audit['info'] = defRealm

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("setting default realm failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def getDefaultRealm(self, action, **params):
        """
        method:
            system/getDefaultRealm

        description:
            this function returns the default realm

        arguments:
            ./.

        returns:
            a json description of the default realm

        exception:
            if an error occurs an exception is serialized and returned
        """
        res = False

        try:
            defRealm = getDefaultRealm()
            res = getRealms(defRealm)

            c.audit['success'] = True
            c.audit['info'] = defRealm

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("return default realm failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def setRealm(self, action, **params):
        """
        method:
            system/setRealm

        description:
            this function is used to define a realm with the given
            useridresolvers

        arguments:
            realm     - name of the realm
            resolvers - comma seperated list of resolvers, that should be
                        in this realm

        returns:
            a json result with a list of Realms

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = False
        err = ""
        realm = ""
        param = {}

        try:
            param.update(request.params)

            realm = getParam(param, "realm", required)
            resolvers = getParam(param, "resolvers", required)

            realm_resolvers = []
            for resolver in resolvers.split(','):
                # check resolver returns the correct resolver description
                (res, realm_resolver) = checkResolverType(resolver)
                if res is False:
                    raise Exception("Error in resolver %r please check the"
                                    " logfile!" % resolver)
                realm_resolvers.append(realm_resolver)

            resolvers = ",".join(realm_resolvers)
            res = setRealm(realm, resolvers)
            c.audit['success'] = res
            c.audit['info'] = "realm: %r, resolvers: %r" % (realm, resolvers)

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            err = ("Failed to set realm with %r " % param)
            log.error("%r %r" % (err, exx))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def delRealm(self, action, **params):
        """
        method:
            system/delRealm

        description:
            this function deletes the given realm

        arguments:
            realm - the name of the realm to be deleted

        returns:
            a json result if deleting the realm was successful

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}

        try:
            param = request.params
            realm = getParam(param, "realm", required)
            ## we test if before delete there has been a default
            ## if yes - check after delete, if still one there
            ##         and set the last available to default
            defRealm = getDefaultRealm()
            hadDefRealmBefore = False
            if defRealm != "":
                hadDefRealmBefore = True

            ## now test if realm is defined
            if isRealmDefined(realm) == True:
                if realm.lower() == defRealm.lower():
                    setDefaultRealm("")
                # this is a remnant of linotp 2.0
                if realm == "_default_": # pragma: no cover
                    realmConfig = "useridresolver"
                else:
                    realmConfig = "useridresolver.group." + realm

                res["delRealm"] = {"result":removeFromConfig(realmConfig, iCase=True)}

            ret = deleteRealm(realm)

            if hadDefRealmBefore == True:
                defRealm = getDefaultRealm()
                if defRealm == "":
                    realms = getRealms()
                    if len(realms) == 1:
                        for k in realms:
                            setDefaultRealm(k)
            c.audit['success'] = ret
            c.audit['info'] = realm

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error deleting realm: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()



########################################################

    @log_with(log)
    def setPolicy(self, action, **params):
        """
        method:
            system/setPolicy

        description:
            Stores a policy that define ACL or behaviour of several different
            actions in privacyIDEA. The policy is stored as configuration values like
            this:
                Policy.<NAME>.action
                Policy.<NAME>.scope
                Policy.<NAME>.realm

        arguments:
            name:       name of the policy
            action:     which action may be executed
            scope:      selfservice
            realm:      This polcy holds for this realm
            user:       (optional) This polcy binds to this user
            time:       (optional) on which time does this policy hold
            client:     (optional) for which requesting client this should be

        returns:
            a json result with success or error

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}
        param = {}
        try:
            param.update(remove_session_from_param(request.params))

            name = getParam(param, "name", required)

            # check that the name does not contain a .
            if not re.match('^[a-zA-Z0-9_]*$', name):
                raise Exception (_("The name of the policy may only contain the characters a-zA-Z0-9_"))
            if not name:
                raise Exception (_("The name of the policy must not be empty"))

            action = getParam(param, "action", required)
            scope = getParam(param, "scope", required)
            realm = getParam(param, "realm", required)
            user = getParam(param, "user", optional)
            time = getParam(param, "time", optional)
            client = getParam(param, "client", optional)
            active = getParam(param, "active", optional)

            p_param = { 'name': name,
                      'action' : action,
                      'scope' : scope,
                      'realm' : realm,
                      'user' : user,
                      'time' : time,
                      'client': client,
                      'active' : active}

            c.audit['action_detail'] = unicode(param)

            if len(name) > 0 and len(action) > 0:

                log.debug("saving policy %r" % p_param)
                ret = setPolicy(p_param)
                log.debug("policy %s successfully saved." % name)

                string = "setPolicy " + name
                res[string] = ret

                c.audit['success'] = True

                Session.commit()
            else:
                log.error("failed: policy with empty name or action %r"
                                                                % p_param)
                string = "setPolicy <%r>" % name
                res[string] = False

                c.audit['success'] = False
                raise Exception('setPolicy failed: name and action required!')

            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error saving policy: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def policies_flexi(self, action, **params):
        '''
        This function is used to fill the policies tab
        Unlike the complex /system/getPolcies function, it only returns a
        simple array of the tokens.
        '''

        pol = {}

        try:
            param = getLowerParams(request.params)

            name = getParam(param, "name", optional)
            realm = getParam(param, "realm", optional)
            scope = getParam(param, "scope", optional)
            sortname = getParam(param, "sortname", optional)
            sortorder = getParam(param, "sortorder", optional)


            log.debug("retrieving policy name: %s, realm: %s, scope: %s, sort:%s by %s"
                % (name, realm, scope, sortorder, sortname))
            pols = self.Policy.getPolicy({'name':name, 'realm':realm, 'scope': scope}, display_inactive=True)

            lines = []
            for pol in pols:
                lines.append(
                    { 'id' : pol,
                        'cell': [
                                 1 if pols[pol].get('active', "True") == "True" else 0,
                                 pol,
                                 pols[pol].get('user', ""),
                                 pols[pol].get('scope', ""),
                                 escape(pols[pol].get('action', "") or ""),
                                 pols[pol].get('realm', ""),
                                 pols[pol].get('client', ""),
                                 pols[pol].get('time', "")
                             ]
                    }
                    )
            # sorting
            reverse = False
            sortnames = { 'active': 0, 'name' : 1, 'user' : 2, 'scope' : 3,
                    'action' : 4, 'realm' : 5, 'client':6, 'time' : 7 }
            if sortorder == "desc":
                reverse = True
            lines = sorted(lines, key=lambda policy: policy['cell'][sortnames[sortname]] , reverse=reverse)
            # end: sorting

            # We need to return 'page', 'total', 'rows'
            res = { "page": 1,
                "total": len(lines),
                "rows": lines }

            c.audit['success'] = True
            c.audit['info'] = "name = %s, realm = %s, scope = %s" % (name, realm, scope)

            Session.commit()
            response.content_type = 'application/json'
            return json.dumps(res, indent=3)

        except Exception as exx:
            log.error("error in policy flexi: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def getPolicyDef(self, action, **params):
        '''
        method:
            system/getPolicyDef

        description:
            This is a helper function that returns the POSSIBLE policy definitions, that can
            be used to define your policies.

        arguments:
            scope - optional - if given, the function will only return policy definitions for the given scope.

        returns:
             the policy definitions of
              - allowed scopes
              - allowed actions in scopes
              - type of actions

        exception:
            if an error occurs an exception is serialized and returned
        '''
        pol = {}

        try:
            param = getLowerParams(request.params)
            log.debug("getting policy definitions: %r" % param)

            scope = getParam(param, "scope", optional)
            pol = get_policy_definitions(scope)
            dynpol = self._add_dynamic_tokens(scope)
            pol.update(dynpol)

            c.audit['success'] = True
            c.audit['info'] = scope

            Session.commit()
            return sendResult(response, pol, 1)

        except Exception as exx:
            log.error("error getting policy definitions: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


#########################################################
    @log_with(log)
    def _add_dynamic_tokens(self, scope):
        '''
            add the policy description of the dynamic token

            :param scope: scope of the policy definition
            :type  scope: string

            :return: policy dict
            :rtype:  dict

        '''
        pol = {}

        glo = config['pylons.app_globals']
        tokenclasses = glo.tokenclasses

        for tok in tokenclasses.keys():
            tclass = tokenclasses.get(tok)
            tclass_object = newToken(tclass)
            if hasattr(tclass_object, 'getClassInfo'):
                ## check if we have a policy in the definition
                try:
                    policy = tclass_object.getClassInfo('policy', ret=None)
                    if policy is not None and policy.has_key(scope):
                        scope_policy = policy.get(scope)
                        pol.update(scope_policy)
                except Exception as exx:
                    log.info('no policy for tokentype %r found (%r)'
                             % (tok, exx))

        return pol

#########################################################
    @log_with(log)
    def importPolicy(self, action, **params):
        '''
        method:
            system/importPolicy

        description:
            This function is used to import policies from a file.

        arguments:
            file - mandatory: The policy file in the POST request
        '''
        sendResultMethod = sendResult
        sendErrorMethod = sendError

        res = True
        try:
            policy_file = request.POST['file']
            fileString = ""
            log.debug("loading policy file to server using POST request. File: %s" % policy_file)

            # In case of form post requests, it is a "instance" of FieldStorage
            # i.e. the Filename is selected in the browser and the data is transferred
            # in an iframe. see: http://jquery.malsup.com/form/#sample4
            #
            if type(policy_file).__name__ == 'instance':
                log.debug("Field storage file: %s", policy_file)
                fileString = policy_file.value
                sendResultMethod = sendXMLResult
                sendErrorMethod = sendXMLError
            else:
                fileString = policy_file
            log.debug("fileString: %s", fileString)

            if fileString == "":
                log.error("Error loading/importing policy file. file empty!")
                return sendErrorMethod(response, "Error loading policy. File empty!")

            # the contents of filestring needs to be parsed and stored as policies.
            from configobj import ConfigObj
            policies = ConfigObj(fileString.split('\n'), encoding="UTF-8")
            log.info("read the following policies: %s" % policies)
            res = len(policies)
            for policy_name in policies.keys():
                ret = setPolicy({ 'name': policy_name,
                              'action' : policies[policy_name].get('action', ""),
                              'scope' : policies[policy_name].get('scope', ""),
                              'realm' : policies[policy_name].get('realm', ""),
                              'user' : policies[policy_name].get('user', ""),
                              'time' : policies[policy_name].get('time', ""),
                              'client': policies[policy_name].get('client', "")})
                log.debug("import policy %s: %s" % (policy_name, ret))

            c.audit['info'] = "Policies imported from file %s" % policy_file
            c.audit['success'] = 1
            Session.commit()
            return sendResultMethod(response, res)

        except Exception as exx:
            log.error("failed! %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendErrorMethod(response, exx)

        finally:
            Session.close()


############################################################
    @log_with(log)
    def checkPolicy(self, action, **params):
        '''
        method:
            system/checkPolicy

        description:
            this function checks if a the given parameter will trigger a policy or not.

        arguments:
            * user   - the name of the user
            * realm  - the realm
            * scope  - the scope
            * action
            * client - the client IP

        returns:
            a json result like this:
              value : { "allowed" : "true",
                        "policy" : <Name der Policy, die das erlaubt hat> }
              value : { "allowed" : "false",
                         "info" : <sowas wie die Fehlermeldung> }

        '''
        res = {}

        try:
            param = getLowerParams(request.params)

            user = getParam(param, "user", required)
            realm = getParam(param, "realm", required)
            scope = getParam(param, "scope", required)
            action = getParam(param, "action", required)
            client = getParam(param, "client", required)

            pol = {}
            if scope in ["admin", "system", "license"]:
                pol = self.Policy.getPolicy({"scope":scope})
                if len(pol) > 0:
                    # Policy active for this scope!
                    pol = self.Policy.getPolicy({"user":user,
                                      "realm":realm,
                                      "scope":scope,
                                      "action":action,
                                      "client":client})
                    res["allowed"] = len(pol) > 0
                    res["policy"] = pol
                    if len(pol) > 0:
                        c.audit['info'] = "allowed by policy %s" % pol.keys()
                else:
                    # No policy active for this scope
                    c.audit['info'] = "allowed since no policies in scope %s" % scope
                    res["allowed"] = True
                    res["policy"] = "No policies in scope %s" % scope
            else:
                log.debug("checking policy for client %s, scope %s, action %s, realm %s and user %s" %
                          (client, scope, action, realm, user))

                pol = self.Policy.get_client_policy(client, scope, action, realm, user)
                res["allowed"] = len(pol) > 0
                res["policy"] = pol
                if len(pol) > 0:
                    c.audit['info'] = "allowed by policy %s" % pol.keys()

            c.audit['action_detail'] = "action = %s, realm = %s, scope = %s"\
                    % (action, realm, scope)
            c.audit['success'] = True

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error checking policy: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()

##########################################################################
    @log_with(log)
    def getPolicy(self, action, **params):
        """
        method:
            system/getPolicy

        description:
            this function is used to retrieve the policies that you
            defined.

        arguments:
            * realm - (optional) will return all policies in the given realm
            * name  - (optional) will only return the policy with the given name
            * scope - (optional) will only return the policies within the given scope
            * export - (optional) The filename needs to be specified as the third part of the URL like /system/getPolicy/policy.cfg. It
                    will then be exported to this file.
            * display_inactive - (optional) if set, then also inactive policies will be displayed

        returns:
            a json result with the configuration of the specified policies

        exception:
            if an error occurs an exception is serialized and returned

        """


        pol = {}
        param = getLowerParams(request.params)
        export = None

        ### config settings from here

        try:
            name = getParam(param, "name", optional)
            realm = getParam(param, "realm", optional)
            scope = getParam(param, "scope", optional)
            display_inactive = getParam(param, "display_inactive", optional)
            if display_inactive:
                display_inactive = True

            route_dict = request.environ.get('pylons.routes_dict')
            export = route_dict.get('id')

            log.debug("retrieving policy name: %s, realm: %s, scope: %s"
                      % (name, realm, scope))
            pol = {}
            if name != None:
                for nam in name.split(','):
                    poli = self.Policy.getPolicy({'name':nam, 'realm':realm, 'scope': scope}, display_inactive=display_inactive)
                    pol.update(poli)
            else:
                pol = self.Policy.getPolicy({'name':name, 'realm':realm, 'scope': scope}, display_inactive=display_inactive)

            c.audit['success'] = True
            c.audit['info'] = "name = %s, realm = %s, scope = %s" \
                                % (name, realm, scope)

            Session.commit()

            if export:
                filename = self.Policy.create_policy_export_file(pol, export)
                wsgi_app = FileApp(filename)
                return wsgi_app(request.environ, self.start_response)
            else:
                return sendResult(response, pol, 1)

        except Exception as exx:
            log.error("error getting policy: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()

########################################################
    @log_with(log)
    def delPolicy(self, action, **params):
        """
        method:
            system/delPolicy

        description:
            this function deletes the policy with the given name

        arguments:
            name  - the policy with the given name

        returns:
            a json result about the delete success

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}
        try:
            param = getLowerParams(request.params)
            name = getParam(param, "name", required)
            log.debug("trying to delete policy %s" % name)
            ret = deletePolicy(name)
            res["delPolicy"] = {"result": ret}

            c.audit['success'] = ret
            c.audit['info'] = name

            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("error deleting policy: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def setupSecurityModule(self, action, **params):

        res = {}

        try:
            params = getLowerParams(request.params)
            hsm_id = params.get('hsm_id', None)

            from privacyidea.lib.config  import getGlobalObject
            glo = getGlobalObject()
            sep = glo.security_provider

            ## for test purpose we switch to an errHSM
            if isSelfTest():
                if params.get('__hsmexception__') == '__ON__':
                    hsm = c.hsm.get('obj')
                    hsm_id = sep.activeOne
                    if type(hsm).__name__ == 'DefaultSecurityModule':
                        hsm_id = sep.setupModule('err', params)

                if params.get('__hsmexception__') == '__OFF__':
                    hsm = c.hsm.get('obj')
                    hsm_id = sep.activeOne
                    if type(hsm).__name__ == 'ErrSecurityModule':
                        hsm_id = sep.setupModule('default', params)



            if hsm_id is None:
                hsm_id = sep.activeOne
                hsm = c.hsm.get('obj')
                error = c.hsm.get('error')
                if hsm is None or len(error) != 0:
                    raise Exception ('current activeSecurityModule >%r< is not initialized::%s:: - Please check your security module configuration and connection!' % (hsm_id, error))

                ready = hsm.isReady()
                res['setupSecurityModule'] = {'activeSecurityModule': hsm_id ,
                                              'connected' : ready }
                ret = ready
            else:
                if hsm_id != sep.activeOne:
                    raise Exception ('current activeSecurityModule >%r< could only be changed through the configuration!' % sep.activeOne)

                ret = sep.setupModule(hsm_id, config=params)

                hsm = c.hsm.get('obj')
                ready = hsm.isReady()
                res['setupSecurityModule'] = {'activeSecurityModule': hsm_id ,
                                              'connected' : ready ,
                                              'result' : ret}

            c.audit['success'] = ret
            Session.commit()
            return sendResult(response, res, 1)

        except Exception as exx:
            log.error("setup failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


#eof###########################################################################

