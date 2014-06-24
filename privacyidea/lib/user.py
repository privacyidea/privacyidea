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
user functions
'''


import logging
import re
import traceback

from privacyidea.lib.error   import UserError
from privacyidea.lib.util    import getParam
from privacyidea.lib.log import log_with

from privacyidea.lib.config  import getFromConfig, storeConfig
from privacyidea.lib.config  import get_privacyIDEA_config
from privacyidea.lib.realm   import setDefaultRealm
from privacyidea.lib.realm   import getDefaultRealm
from privacyidea.lib.realm   import getRealms

from privacyidea.lib.resolver import splitResolver
from privacyidea.lib.resolver import getResolverObject


from privacyidea.lib.realm import createDBRealm
from privacyidea.lib.selftest import isSelfTest


ENCODING = 'utf-8'

log = logging.getLogger(__name__)

@log_with(log)
class User(object):

    # In some test case the login attribute from a not
    # initialized user is requested. This is why we need
    # these dummy class attributes.
    login=""
    realm=""
    conf=""
    
    def __init__(self, login="", realm="", conf=""):
        self.login = ""
        self.realm = ""
        self.conf = ""

        if login is not None:
            self.login = login
        if realm is not None:
            self.realm = realm
        if conf is not None:
            self.conf = conf

        self.resolverUid = {}
        self.resolverConf = {}
        self.resolvers_list = []

    def getRealm(self):
        return self.realm

    def getResConf(self):
        return self.conf

    def getUser(self):
        return self.login

    def isEmpty(self):
        ## ignore if only conf is set! as it makes no sense
        if len(self.login or "") + len(self.realm or "") == 0:
            return True
        else:
            return False
##def __eq__(self,other):
##    ret = False
##    if other is None:
##        if self.isEmpty() == True:
##            return True
##        else:
##            return False
##    if other.login == self.login and self.realm == other.realm and other.conf == self.conf:
##        return True
##    else:
##        return False

##def __ne__(self,other):
##      return not(self.__eq__(other))

    def __str__(self):
        ret = str(None)
        if self.isEmpty() == False:
            loginname = ""
            try:
                loginname = unicode(self.login)
            except UnicodeEncodeError:
                loginname = unicode(self.login.encode(ENCODING))

            conf = ''
            if self.conf is not None and len(self.conf) > 0:
                conf = '.%s' % (unicode(self.conf))
            ret = '<%s%s@%s>' % (loginname, conf, unicode(self.realm))

        return ret

    def __repr__(self):
        ret = ('User(login=%r, realm=%r, conf=%r ::resolverUid:%r, '
             'resolverConf:%r)' % (self.login, self.realm, self.conf,
                                   self.resolverUid, self.resolverConf))
        return ret

    def saveResolvers(self, resolvers):
        """
        save the resolver objects as list as part of the user
        """
        self.resolvers_list = resolvers

    def getResolvers(self):
        return self.resolverUid.keys()

    def addResolverUId(self, resolver, uid, conf="", resId="", resCId=""):
        self.resolverUid[resolver] = uid
        self.resolverConf[resolver] = (resId, resCId, conf)

    def getResolverUId(self, resolver):
        uid = ""
        if self.resolverUid.has_key(resolver):
            uid = self.resolverUid.get(resolver)

        return uid

    def getResolverConf(self, resolver):
        conf = ""
        if self.resolverConf.has_key(resolver):
            conf = self.resolverConf.get(resolver)

        return conf

@log_with(log)
def getUserResolverId(user, report=False):
    ## here we call the userid resolver!!"

    (uuserid, uidResolver, uidResolverClass) = (u'', u'', u'')

    if (user is not None and user.isEmpty() != True):
        try:
            (uuserid, uidResolver, uidResolverClass) = getUserId(user)
        except Exception as e:
            log.error('for %r@%r failed: %r' % (user.login, user.realm, e))
            log.error("%s" % traceback.format_exc())
            if report == True:
                raise UserError("getUserResolverId failed: %r" % e, id=1112)

    return (uuserid, uidResolver, uidResolverClass)

@log_with(log)
def splitUser(username):

    user = username.strip()
    group = ""

    ## todo split the last
    l = user.split('@')
    if len(l) >= 2:
        (user, group) = user.rsplit('@')
    else:
        l = user.split('\\')
        if len(l) >= 2:
            (group, user) = user.rsplit('\\')

    return (user, group)

@log_with(log)
def getUserFromParam(param, optionalOrRequired):
    realm = ""
    conf = ""
    user = getParam(param, "user", optionalOrRequired)
    log.debug("got user <<%r>>" % user)

    if user is None:
        user = ""
    else:
        splitAtSign = getFromConfig("splitAtSign", "true")

        if splitAtSign.lower() == "true":
            (user, realm) = splitUser(user)

    if param.has_key("realm"):
        realm = param["realm"]

    if user != "":
        if realm is None or realm == "" :
            realm = getDefaultRealm()

    usr = User(user, realm, "")

    if param.has_key("resConf"):
        conf = param["resConf"]
        ## with the short resolvernames, we have to extract the
        ## configuration name from the resolver spec
        if "(" in conf and ")" in conf:
            res_conf, resolver_typ = conf.split(" ")
            conf = res_conf
        usr.conf = conf
    else:
        if len(usr.login) > 0 or len(usr.realm) > 0 or len(usr.conf) > 0:
            res = getResolversOfUser(usr)
            usr.saveResolvers(res)
            if len(res) > 1:
                log.error("user %r@%r is in more than one resolver: %r" % (user, realm, res))
                raise Exception("The user %s@%s is in more than one resolver:"
                                " %s" % (user, realm, unicode(res)))

    log.debug("creating user object %r,%r,%r"
              % (user, realm, conf))

    return usr

@log_with(log)
def getUserFromRequest(request):
    '''
    This function first tries to get the user from
     * a DigestAuth and otherwise from
     * basic auth and otherwise from
     * the client certificate and otherwise from
     * the repoze who information.
    '''
    d_auth = { 'login' : '' }

    param = request.params

    try:
        # Do BasicAuth
        if request.environ.has_key('REMOTE_USER'):
            d_auth['login'] = request.environ['REMOTE_USER']
            log.debug("BasicAuth: found the REMOTE_USER: %r" % d_auth)

        # Do DigestAuth
        elif request.environ.has_key('HTTP_AUTHORIZATION'):
            a_auth = request.environ['HTTP_AUTHORIZATION'].split(",")

            for field in a_auth:
                (key, _delimiter, value) = field.partition("=")
                d_auth[key.lstrip(' ')] = value.strip('"')

            if d_auth.has_key('Digest username'):
                d_auth['login'] = d_auth['Digest username']

            log.debug("DigestAuth: found HTTP_AUTHORIZATION: %r" % d_auth)

        # Do SSL Client Cert
        elif request.environ.has_key('SSL_CLIENT_S_DN_CN'):
            d_auth['login'] = request.environ.get('SSL_CLIENT_S_DN_CN')
            log.debug("SSLClientCert Auth: found this SSL_CLIENT_S_DN_CN: %r" % d_auth)

        # In case of selftest
        log.debug("Doing selftest!: %r" % isSelfTest())

        if isSelfTest():
            log.debug("Doing selftest!")
            param = request.params
            d_auth['login'] = getParam(param, "selftest_admin", True)
            log.debug("Found the user: %r in the request."
                       % d_auth)

    except Exception as e:
        log.error("An error occurred when trying to fetch "
                  "the user from the request: %r" % e)
        pass

    return d_auth

@log_with(log)
def setRealm(realm, resolvers):

    realm = realm.lower().strip()
    realm = realm.replace(" ", "-")

    nameExp = "^[A-Za-z0-9_\-\.]*$"
    res = re.match(nameExp, realm)
    if res is None:
        e = Exception("non conformant characters in realm name:"
                      " %s (not in %s)" % (realm, nameExp))
        raise e

    ret = storeConfig("useridresolver.group.%s" % realm, resolvers)
    if ret == False:
        return ret

    createDBRealm(realm)

    ## if this is the first one, make it the default
    realms = getRealms()
    if 1 == len(realms):
        for name in realms:
            setDefaultRealm(name)

    return True

@log_with(log)
def getUserRealms(user):
    '''
    Returns the realms, a user belongs to.
    If the user has no realm but only a useridresolver, than all realms, containing this
    resolver are returned.
    This function is used for the policy module
    '''
    allRealms = getRealms()
    Realms = []
    if user.realm == "" and user.conf == "":
        defRealm = getDefaultRealm().lower()
        Realms.append(defRealm)
        user.realm = defRealm
    elif user.realm != "":
        Realms.append(user.realm.lower())
    else:
        # we got a resolver and will get all realms the resolver belongs to.
        for key, v in allRealms.items():
            log.debug("evaluating realm %r: %r " % (key, v))
            for reso in v['useridresolver']:
                resotype, resoname = reso.rsplit('.', 1)
                log.debug("found resolver %r of type %r" % (resoname, resotype))
                if resoname == user.conf:
                    Realms.append(key.lower())
                    log.debug("added realm %r to Realms due to resolver %r" % (key, user.conf))

    return Realms

@log_with(log)
def getRealmBox():
    '''
    returns the config value of selfservice.realmbox.
    if True, the realmbox in the selfservice login will be displayed.
    if False, the realmbox will not be displayed and the user needs to login via user@realm
    '''
    rb_string = "privacyidea.selfservice.realmbox"
    conf = get_privacyIDEA_config()
    if rb_string in conf:
        log.debug("read setting: %r" % conf.get(rb_string))
        return "True" == conf.get(rb_string)
    else:
        return False

@log_with(log)
def getConf(Realms, Conf):
    """
    extract the configguration part from the resolver definition
    """
    for k in Realms:
        r = Realms[k]
        resIds = r["useridresolver"]
        for reso in resIds:
            (_package, _module, _class_, conf) = splitResolver(reso)
            if conf.lower() == Conf.lower():
                return reso
    return ""

@log_with(log)
def getResolvers(user):
    '''
    get the list of the Resolvers within a users.realm
    or from the resolver conf, if given in the user object

    :note:  It ignores the user.login attribute!

    :param user: User with realm or resolver conf
    :type  user: User object
    '''
    Resolver = []

    realms = getRealms();

    if user.conf != "":
        reso = getConf(realms, user.conf)
        if len(reso) > 0:
            Resolver.append(reso)
    else:
        if user.realm != "":
            if user.realm.lower() in realms:
                Resolver = realms[user.realm.lower()]["useridresolver"]
            else:
                resDict = {}
                if user.realm.endswith('*') and len(user.realm) > 1:
                    pattern = user.realm[:-1]
                    for r in realms:
                        if r.startswith(pattern):
                            for idres in realms[r]["useridresolver"]:
                                resDict[idres] = idres
                    for k in resDict:
                        Resolver.append(k)


                elif user.realm.endswith('*') and len(user.realm) == 1:
                    for r in realms:
                        for idres in realms[r]["useridresolver"]:
                            resDict[idres] = idres
                    for k in resDict:
                        Resolver.append(k)

        else:
            for k in realms:
                r = realms[k]
                if r.has_key("default"):
                    Resolver = r["useridresolver"]

    return Resolver

@log_with(log)
def getResolversOfUser(user):
    '''
    This returns the list of the Resolvers of a user in a given realm.
    Usually this should only return one resolver

    input:
        user.login, user.realm

    returns:
        array of resolvers, the user was found in
    '''

    login = user.login
    realm = user.realm

    Resolvers = user.getResolvers()

    if len(Resolvers) > 0:
        return Resolvers

    if realm is None or realm == "":
        realm = getDefaultRealm()

    #if realm is None or realm=="" or login is None or login == "":
    #    log.error("You need to specify the name ( %s) and the realm (%s) of a user with conf %s" % (login, realm, user.conf))

    realms = getRealms();

    if user.conf != "":
        reso = getConf(realms, user.conf)
        if len(reso) > 0:
            Resolvers.append(reso)
    else:
        Realm_resolvers = getResolvers(User("", realm, ""))

        log.debug("check if user %r is in resolver %r"
                   % (login, Realm_resolvers))
        # Search for user in each resolver in the realm_
        for realm_resolver in Realm_resolvers:
            log.debug("checking in %r" % realm_resolver)

            (package, module, class_, conf) = splitResolver(realm_resolver)
            module = package + "." + module

            y = getResolverObject(realm_resolver)
            if y is None:
                log.error("module %r not found!" % (module))

            try:
                log.debug("checking in module %r" % y)
                uid = y.getUserId(login)
                log.debug("type of uid: %s" % type(uid))
                log.debug("type of realm_resolver: %s" % type(realm_resolver))
                log.debug("type of login: %s" % type(login))
                if uid not in ["", None]:
                    log.info("user %r found in resolver %r" % (login, realm_resolver))
                    log.info("userid resolved to %r " % uid)

                    ## Unicode Madness:
                    ## This will break as soon as the unicode "uid" is put into a tuple
                    ## v = (login, realm_resolver, uid)
                    ## log.info("%s %s %s" % v)
                    resId = y.getResolverId();
                    resCId = realm_resolver
                    Resolvers.append(realm_resolver)
                    user.addResolverUId(realm_resolver, uid, conf, resId, resCId)
                else:
                    log.debug("user %r not found"
                              " in resolver %r" % (login, realm_resolver))
            except Exception as e:
                log.error("error searching user in"
                          " module %r:%r" % (module, e))
                log.error("%s" % traceback.format_exc())

            log.debug("Resolvers: %r" % Resolvers)

    log.debug("Found the user %r in %r" % (login, Resolvers))
    return Resolvers

@log_with(log)
def getUserId(user):
    """
    getUserId (userObject)

    return (uid,resId,resIdC)
    """

    uid = ''
    loginUser = u''
    loginUser = user.login;

    resolvers = getResolversOfUser(user)
    for reso in resolvers:
        resId = ""
        resIdC = ""
        conf = ""
        uid = user.getResolverUId(reso)
        if uid != '':
            (resId, resIdC, conf) = user.getResolverConf(reso)
            break

        (package, module, class_, conf) = splitResolver(reso)

        if len(user.conf) > 0:
            if conf.lower() != user.conf.lower():
                continue

        ## try to load the UserIdResolver Class
        try:
            module = package + "." + module
            log.debug("Getting resolver class: [%r] [%r]"
                       % (module, class_))
            y = getResolverObject(reso)
            log.debug("Getting UserID for user %r"
                        % loginUser)
            uid = y.getUserId(loginUser)
            log.debug("Got UserId for user %r: %r"
                        % (loginUser, uid))

            log.debug("Retrieving ResolverID...")
            resId = y.getResolverId()

            resIdC = reso
            log.debug("Got ResolverID: %r, Loginuser: %r, "
                      "Uid: %r" % (resId, loginUser, uid))

            if uid != "":
                break;

        except Exception as e:
            log.error("module %r: %r" % (module, e))
            continue

    if (uid == ''):
        log.warning("No uid found for the user >%r< in realm %r"
                    % (loginUser, user.realm))
        raise UserError(u"getUserId failed: no user >%s< found!"
                         % unicode(loginUser), id=1205)

    return (unicode(uid), unicode(resId), unicode(resIdC))

@log_with(log)
def getSearchFields(User):

    searchFields = {}

    for reso in getResolvers(User):
        """  """
        (_package, module, class_, conf) = splitResolver(reso)

        if len(User.conf) > 0:
            if conf.lower() != User.conf.lower():
                continue

        ## try to load the UserIdResolver Class
        try:
            y = getResolverObject(reso)
            sf = y.getSearchFields()
            searchFields[reso] = sf

        except Exception as e:
            log.warning("module %r: %r" % (module, e))
            continue

    return searchFields

@log_with(log)
def getUserList(param, User):

    users = []
    searchDict = {}

    ## we have to recreate a new searchdict without the realm key
    ## as delete does not work
    for key in param:
        lval = param[key]
        if key == "realm":
            continue
        if key == "resConf":
            continue

        searchDict[key] = lval
        log.debug("Parameter key:%r=%r" % (key, lval))

    resolverrrs = getResolvers(User)

    for reso in resolverrrs:
        (package, module, class_, conf) = splitResolver(reso)
        module = package + "." + module

        if len(User.conf) > 0:
            if conf.lower() != User.conf.lower():
                continue

        ## try to load the UserIdResolver Class
        try:
            log.debug("Check for resolver class: %r" % reso)
            y = getResolverObject(reso)
            log.debug("with this search dictionary: %r " % searchDict)
            ulist = y.getUserList(searchDict)
            log.debug("setting the resolver <%r> for each user" % reso)
            for u in ulist:
                u["useridresolver"] = reso

            log.debug("Found this userlist: %r" % ulist)
            users.extend (ulist)

        except KeyError as exx:
            log.error("module %r:%r" % (module, exx))
            log.error("%s" % traceback.format_exc())
            raise exx

        except Exception as exx:
            log.error("module %r:%r" % (module, exx))
            log.error("%s" % traceback.format_exc())
            continue

    return users

@log_with(log)
def getUserInfo(userid, resolver, resolverC):
    userInfo = {}
    module = ""

    if len(userid) == 0 or userid is None:
        return userInfo

    try:
        (package, module, _class, _conf) = splitResolver(resolverC)
        module = package + "." + module

        y = getResolverObject(resolverC)
        log.debug("Getting user info for userid >%r< in resolver" % userid)
        userInfo = y.getUserInfo(userid)

    except Exception as e:
        log.error("resolver %r notfound! :%r" % (resolverC, e))

    return userInfo

@log_with(log)
def getUserPhone(user, phone_type='phone'):
    '''
    Returns the phone numer of a user

    :param user: the user with the phone
    :type user: user object

    :param phone_type: The type of the phone, i.e. either mobile or phone (land line)
    :type phone_type: string

    :returns: list with phone numbers of this user object
    '''
    (uid, resId, resClass) = getUserId(user)
    log.debug("got uid %r, ResId %r, Class %r"
              % (uid, resId, resClass))
    userinfo = getUserInfo(uid, resId, resClass)
    if userinfo.has_key(phone_type):
        log.debug("got user phone %r of type %r"
                  % (userinfo[phone_type], phone_type))
        return userinfo[phone_type]
    else:
        log.warning("userobject (%r,%r,%r) has no phone of type %r." 
                    % (uid, resId, resClass, phone_type))
        return ""
    
@log_with(log)
def check_user_password(username, realm, password):
    '''
    This is a helper function to check the username and password against
    a userstore.

    return

      success    --- This is the username of the authenticated user. If unsuccessful,
                      returns None
    '''
    success = None
    try:
        log.info("User %r from realm %r tries to "
                 "authenticate to selfservice" % (username, realm))
        if type(username) != unicode:
            username = username.decode(ENCODING)
        u = User(username, realm, "")
        res = getResolversOfUser(u)
        # Now we know, the resolvers of this user and we can verify the password
        if (len(res) == 1):
            (uid, resolver, resolverC) = getUserId(u)
            log.info("the user resolves to %r" % uid)
            log.info("The username is found within the resolver %r" % resolver)
            # Authenticate user
            try:
                (package, module, class_, conf) = splitResolver(resolverC)
                module = package + "." + module
                y = getResolverObject(resolverC)
            except Exception as e:
                log.error("module %r not found! :%r"
                          % (module, e))
            try:
                if  y.checkPass(uid, password):
                    log.debug("Successfully authenticated user %r." % username)
                    # try:
                    #identity = self.add_metadata( environ, identity )
                    success = username + '@' + realm
                else:
                    log.info("user %r failed to authenticate." % username)
            except Exception as e:
                log.error("Error checking password within module %r:%r" 
                          % (module, e))
                log.error("%s" % traceback.format_exc())

        elif (len(res) == 0):
            log.error("The username %r exists in NO resolver within the realm %r." 
                      % (username, realm))
        else:
            log.error("The username %r exists in more than one resolver within the realm %r" 
                      % (username, realm))
            log.error(res)
    except UserError as e:
        log.error("Error while trying to verify the username: %r" 
                  % e.description)

    return success

#eof###########################################################################

