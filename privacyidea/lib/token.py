# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  2014-07-02 Cornelius Kölbel, remove references to machines, when a token is deleted 
#
#
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
'''It  contains several token functions
'''

import traceback
import string
import datetime
import sys
import re
import binascii
import base64
import os
import logging

import json

from sqlalchemy import or_, and_
from sqlalchemy import func


from pylons import tmpl_context as c
from pylons.i18n.translation import _
from pylons import config
from pylons import request

from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.error import UserError
from privacyidea.lib.error import ParameterError

from privacyidea.lib.user import getUserId, getUserInfo
from privacyidea.lib.user import User, getUserRealms
from privacyidea.lib.user import check_user_password

from privacyidea.lib.util import getParam
from privacyidea.lib.util import generate_password
from privacyidea.lib.util import modhex_decode
from privacyidea.lib.log import log_with

from privacyidea.lib.realm import realm2Objects
from privacyidea.lib.realm import getRealms

from privacyidea.lib.validate import ValidateToken
from privacyidea.lib.validate import create_challenge
from privacyidea.lib.validate import get_challenges

from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.config import get_privacyIDEA_config

from privacyidea import model
from privacyidea.model import Token, createToken, Realm, TokenRealm
from privacyidea.model.meta import Session
from privacyidea.model import Challenge
from privacyidea.model import MachineToken

from privacyidea.lib.config  import getFromConfig
from privacyidea.lib.resolver import getResolverObject

from privacyidea.lib.realm import createDBRealm, getRealmObject
from privacyidea.lib.realm import getDefaultRealm

from privacyidea.weblib.util import get_client

log = logging.getLogger(__name__)

optional = True
required = False

ENCODING = "utf-8"

###############################################
@log_with(log)
def createTokenClassObject(token, typ=None):
    '''
    createTokenClassObject - create a token class object from a given type

    :param token:  the database refeneced token
    :type  token:  database token
    :param typ:    type of to be created token
    :type  typ:    string

    :return: instance of the token class object
    :rtype:  token class object
    '''

    # if type is not given, we take it out of the token database object
    if (typ is None):
        typ = token.privacyIDEATokenType

    if typ == "":
        typ = "hmac"

    typ = typ.lower()
    tok = None

    # search which tokenclass should be created and create it!
    tokenclasses = config['tokenclasses']
    if tokenclasses.has_key(typ.lower()):
        try:
            token_class = tokenclasses.get(typ)
            tok = newToken(token_class)(token)
        except Exception as e:
            log.debug('createTokenClassObject failed!')
            raise TokenAdminError("createTokenClassObject failed:  %r" % e, id=1609)

    else:
        log.error('type %r not found in tokenclasses: %r' %
                  (typ, tokenclasses))
        #
        ## we try to use the parent class, which is able to handle most of the
        ## administrative tasks. This will allow to unassigen and disable or delete
        ## this 'abandoned token'
        #
        from privacyidea.lib.tokenclass import TokenClass
        tok = TokenClass(token)
        log.error("failed: unknown token type %r. \
                 Using fallback 'TokenClass' for %r" % (typ, token))

    return tok

@log_with(log)
def newToken(token_class):
    '''
    newTokenClass - return a token class, which could be used as a constructor

    :param token_class: string representation of the token class name
    :type   token_class: string
    :return: token class
    :rtype:  token class

    '''

    ret = ""
    attribute = ""

    ## prepare the lookup
    parts = token_class.split('.')
    package_name = '.'.join(parts[:-1])
    class_name = parts[-1]

    if sys.modules.has_key(package_name):
        mod = sys.modules.get(package_name)
    else:
        mod = __import__(package_name, globals(), locals(), [class_name])
    try:
        klass = getattr(mod, class_name)

        attrs = ["getType", "checkOtp"]
        for att in attrs:
            attribute = att
            getattr(klass, att)

        ret = klass
    except:
        raise NameError(
            "IdResolver AttributeError: " + package_name + "." + class_name
             + " instance has no attribute '" + attribute + "'")
    return ret

@log_with(log)
def get_token_type_list():
    '''
    get_token_type_list - returns the list of the available tokentypes like hmac, spass, totp...

    :return: list of token types
    :rtype : list
    '''

    try:
#        from privacyidea.lib.config      import getGlobalObject
        tokenclasses = config['tokenclasses']

    except Exception as e:
        log.debug('get_token_type_list failed!')
        raise TokenAdminError("get_token_type_list failed:  %r" % e, id=1611)

    token_type_list = tokenclasses.keys()
    return token_type_list


#######################################
@log_with(log)
def _create_google_authenticator(param):
    '''
    create url for google authenticator

    :param param: request dictionary
    :return: string with google url
    '''

    otpkey = getParam(param, "otpkey", required)
    serial = getParam(param, "serial", required)
    digits = getParam(param, "otplen", required)
    algo = param.get("hashlib", "sha1") or "sha1"
    algo = algo.upper()

    typ = getParam(param, "type", required)
    key = base64.b32encode(binascii.unhexlify(otpkey))
    key = key.strip("=")

    if typ.lower() == "totp":
        ga = ("otpauth://totp/%s?secret=%s&digits=%s&algorithm=%s" %
                                            (serial, key, digits, algo))
    else:
        ga = ("otpauth://hotp/%s?secret=%s&digits=%s&algorithm=%s&counter=0"
                                            % (serial, key, digits, algo))

    return ga


@log_with(log)
def getRealms4Token(user, tokenrealm=None):
    '''
    get the realm objects of a user or from the tokenrealm defintion,
    which could be a list of realms or a single realm
     - helper method to enhance the code readablility

    :param user: the user wich defines the set of realms
    :param tokenrealm: a string or a list of realm strings

    :return: the list of realm objects
    '''

    realms = []
    if user is not None and user.login != "" :
        ## the getUserRealms should return the default realm if realm was empty
        realms = getUserRealms(user)
        ## hack: sometimes the realm of the user is not in the
        ## realmDB - so check and add
        for r in realms:
            realmObj = getRealmObject(name=r)
            if realmObj is None:
                createDBRealm(r)

    if tokenrealm is not None:
        # tokenrealm can either be a string or a list
        log.debug("tokenrealm given (%r). We will add the "
                  "new token to this realm" % tokenrealm)
        if isinstance(tokenrealm, str):
            log.debug("String: adding realm: %r" % tokenrealm)
            realms.append(tokenrealm)
        elif isinstance(tokenrealm, list):
            for tr in tokenrealm:
                log.debug("List: adding realm: %r" % tr)
                realms.append(tr)

    realmList = realm2Objects(realms)

    return realmList

@log_with(log)
def get_tokenserial_of_transaction(transId):
    '''
    get the serial number of a token from a challenge state / transaction

    :param transId: the state / transaction id
    :return: the serial number or None
    '''
    serial = None
    
    challenges = Session.query(Challenge)\
                .filter(Challenge.transid == u'' + transId).all()

    if len(challenges) == 0:
        log.info('no challenge found for tranId %r' % (transId))
        return None
    elif len(challenges) > 1:
        log.info('multiple challenges found for tranId %r' % (transId))
        return None

    serial = challenges[0].tokenserial

    return serial

@log_with(log)
def initToken(param, user, tokenrealm=None):
    '''
    initToken - create a new token or update a token

    :param param: the list of provided parameters
                  in the list the serialnumber is required,
                  the token type default ist hmac
    :param user:  the token owner
    :param tokenrealm: the realms, to which the token belongs

    :return: tuple of success and token object
    '''
    token = None
    tokenObj = None

    typ = getParam(param, "type", optional)
    if typ is None:
        typ = "hmac"

    #serial = getParam(param, "serial", required)
    serial = param.get('serial', None)
    if serial is None:
        prefix = param.get('prefix', None)
        serial = genSerial(typ, prefix)



    # if a token was initialized for a user, the param "realm" might be contained.
    # otherwise - without a user the param tokenrealm could be contained.
    log.debug("initilizing token %r for user %r " % (serial, user.login))

    ## create a list of the found db tokens - no token class objects
    toks = getTokens4UserOrSerial(None, serial, _class=False)
    tokenNum = len(toks)

    tokenclasses = config['tokenclasses']

    if tokenNum == 0:  ## create new a one token
        ## check if this token is in the list of available tokens
        if not tokenclasses.has_key(typ.lower()):
            log.error('type %r not found in tokenclasses: %r' %
                      (typ, tokenclasses))
            raise TokenAdminError("[initToken] failed: unknown token type %r" % typ , id=1610)
        token = createToken(serial)

    elif tokenNum == 1:  # update if already there
        token = toks[0]

        # prevent from changing the token type
        old_typ = token.privacyIDEATokenType
        if old_typ.lower() != typ.lower():
            msg = 'token %r already exist with type %r. Can not initialize token with new type %r' % (serial, old_typ, typ)
            log.error(msg)
            raise TokenAdminError("initToken failed: %s" % msg)

        ## prevent update of an unsupported token type
        if not tokenclasses.has_key(typ.lower()):
            log.error('type %r not found in tokenclasses: %r' %
                      (typ, tokenclasses))
            raise TokenAdminError("failed: unknown token type %r" % typ , id=1610)

    else:  ## something wrong
        if tokenNum > 1:
            raise TokenAdminError("multiple tokens found - cannot init!", id=1101)
        else:
            raise TokenAdminError("cannot init! Unknown error!", id=1102)

    ## if there is a realm as parameter, we assign the token to this realm
    if 'realm' in param:
        ## if we get a undefined tokenrealm , we create a list
        if tokenrealm is None:
            tokenrealm = []
        ## if we get a tokenrealm as string, we make an array out of this
        elif type(tokenrealm) in [str, unicode]:
            tokenrealm = [tokenrealm]
        ## and append our parameter realm
        tokenrealm.append(param.get('realm'))

    ## get the RealmObjects of the user and the tokenrealms
    realms = getRealms4Token(user, tokenrealm)
    token.setRealms(realms)

    ## on behalf of the type, the class is created
    tokenObj = createTokenClassObject(token, typ)

    if tokenNum == 0:
        ## if this token is a newly created one, we have to setup the defaults,
        ## which lateron might be overwritten by the tokenObj.update(params)
        tokenObj.setDefaults()

    tokenObj.update(param)


    if user is not None and user.login != "" :
        tokenObj.setUser(user, report=True)

    try:
        token.storeToken()
    except Exception as e:
        log.error('token create failed!')
        log.error("%r" % (traceback.format_exc()))
        raise TokenAdminError("token create failed %r" % e, id=1112)

    return (True, tokenObj)

@log_with(log)
def getRolloutToken4User(user=None, serial=None, tok_type=u'ocra'):

    if (user is None or user.isEmpty()) and serial is None:
        return None

    serials = []
    tokens = []

    if user is not None and user.isEmpty() == False:
        resolverUid = user.resolverUid
        v = None
        k = None
        for k in resolverUid:
            v = resolverUid.get(k)
        user_id = v
        user_resolver = k

        ''' coout tokens: 0 1 or more '''
        tokens = Session.query(Token).filter(Token.privacyIDEATokenType == unicode(tok_type))\
                                       .filter(Token.privacyIDEAIdResClass == unicode(user_resolver))\
                                       .filter(Token.privacyIDEAUserid == unicode(user_id))

    elif serial is not None:
        tokens = Session.query(Token).filter(Token.privacyIDEATokenType == unicode(tok_type))\
                                       .filter(Token.privacyIDEATokenSerialnumber == unicode(serial))

    for token in tokens:
        info = token.privacyIDEATokenInfo
        if len(info) > 0:
            tinfo = json.loads(info)
            rollout = tinfo.get('rollout', None)
            if rollout is not None:
                serials.append(token.privacyIDEATokenSerialnumber)


    if len(serials) > 1:
        raise Exception('multiple tokens found in rollout state: %s'
                        % unicode(serials))

    if len(serials) == 1:
        serial = serials[0]

    return serial

@log_with(log)
def setRealms(serial, realmList):
    # set the tokenlist of DB tokens
    tokenList = getTokens4UserOrSerial(None, serial, _class=False)

    if len(tokenList) == 0:
        log.error("No token with serial %r found." % serial)
        raise TokenAdminError("setRealms failed. No token with serial %s found"
                              % serial, id=1119)

    realmObjList = realm2Objects(realmList)

    for token in tokenList:
        token.setRealms(realmObjList)

    return len(tokenList)

@log_with(log)
def getTokenRealms(serial):
    '''
    This function returns a list of the realms of a token
    '''
    tokenList = getTokens4UserOrSerial(None, serial, _class=False)

    if len(tokenList) == 0:
        log.error("No token with serial %r found." % serial)
        raise TokenAdminError("getTokenRealms failed. No token with serial %s found" % serial, id=1119)

    token = tokenList[0]

    return token.getRealmNames()

@log_with(log)
def getRealmsOfTokenOrUser(token):
    '''
    This returns the realms of either the token or
    of the user of the token.
    '''
    serial = token.getSerial()
    realms = getTokenRealms(serial)

    if len(realms) == 0:
        uid, resolver, resolverClass = token.getUser()
        log.debug("%r, %r, %r" % (uid, resolver, resolverClass))
        # No realm and no User, this is the case in /validate/check_s
        if resolver.find('.') >= 0:
            _resotype, resoname = resolver.rsplit('.', 1)
            realms = getUserRealms(User("dummy_user", "", resoname))

    log.debug("the token %r "
              "is in the following realms: %r" % (serial, realms))

    return realms

@log_with(log)
def getTokenInRealm(realm, active=True):
    '''
    This returns the number of tokens in one realm.

    You can either query only active token or also disabled tokens.
    '''
    if active:
        sqlQuery = Session.query(TokenRealm, Realm, Token).filter(and_(
                            TokenRealm.realm_id == Realm.id,
                            Realm.name == u'' + realm,
                            Token.privacyIDEAIsactive == True,
                            TokenRealm.token_id == Token.privacyIDEATokenId)).count()
    else:
        sqlQuery = Session.query(TokenRealm, Realm).filter(and_(
                            TokenRealm.realm_id == Realm.id,
                            Realm.name == realm)).count()
    return sqlQuery

@log_with(log)
def getTokenNumResolver(resolver=None, active=True):
    '''
    This returns the number of the (active) tokens
    if no resolver is passed, the overall token number is returned,
    if a resolver is passed, the token number within this resolver is returned

    if active is set to false, ALL tokens are returned
    '''
    if resolver is None:
        if active:
            sqlQuery = Session.query(Token).filter(Token.privacyIDEAIsactive == True).count()
        else:
            sqlQuery = Session.query(Token).count()
        return sqlQuery
    else:
        if active:
            sqlQuery = Session.query(Token).filter(and_(Token.privacyIDEAIdResClass == resolver, Token.privacyIDEAIsactive == True)).count()
        else:
            sqlQuery = Session.query(Token).filter(Token.privacyIDEAIdResClass == resolver).count()
        return sqlQuery

@log_with(log)
def getAllTokenUsers():
    '''
        return a list of all users
    '''
    users = {}
    sqlQuery = Session.query(Token)
    for token in sqlQuery:
        userInfo = {}

        log.debug("user serial (serial): %r" % token.privacyIDEATokenSerialnumber)

        serial = token.privacyIDEATokenSerialnumber
        userId = token.privacyIDEAUserid
        resolver = token.privacyIDEAIdResolver
        resolverC = token.privacyIDEAIdResClass

        if len(userId) > 0 and len(resolver) > 0:
            userInfo = getUserInfo(userId, resolver, resolverC)

        if len(userId) > 0 and len(userInfo) == 0:
            userInfo['username'] = u'/:no user info:/'

        if len(userInfo) > 0:
            users[serial] = userInfo

    return users


@log_with(log)
def getTokens4UserOrSerial(user=None, serial=None, forUpdate=False, _class=True):
    tokenList = []
    tokenCList = []
    tok = None

    if serial is None and user is None:
        log.warning("missing user or serial")
        return tokenList

    if (serial is not None):
        log.debug("getting token object with serial: %r" % serial)
        ## SAWarning of non unicode type
        serial = u'' + serial

        sqlQuery = Session.query(Token).filter(
                            Token.privacyIDEATokenSerialnumber == serial)

        if forUpdate == True:
            sqlQuery = Session.query(Token).with_lockmode("update").filter(
                            Token.privacyIDEATokenSerialnumber == serial)

        #for token in Session.query(Token).filter(Token.privacyIDEATokenSerialnumber == serial):
        for token in sqlQuery:
            log.debug("user serial (serial): %r" % token.privacyIDEATokenSerialnumber)
            tokenList.append(token)

    if user is not None:
        log.debug("getting token object 4 user: %r" % user)

        if (user.isEmpty() == False):
            # the upper layer will catch / at least should
            (uid, resolver, resolverClass) = getUserId(user)

            sqlQuery = Session.query(model.Token).filter(
                        model.Token.privacyIDEAUserid == uid).filter(
                        model.Token.privacyIDEAIdResClass == resolverClass)
            if forUpdate == True:
                sqlQuery = Session.query(model.Token).with_lockmode("update").filter(
                            model.Token.privacyIDEAUserid == uid).filter(
                            model.Token.privacyIDEAIdResClass == resolverClass)

            for token in sqlQuery:
                log.debug("user serial (user): %r"
                          % token.privacyIDEATokenSerialnumber)
                tokenList.append(token)

    if _class == True:
        for tok in tokenList:
            tokenCList.append(createTokenClassObject(tok))
        return tokenCList
    else:
        return tokenList

@log_with(log)
def getTokensOfType(typ=None, realm=None, assigned=None):
    '''
    This function returns a list of token objects of the following type.

    here we need to create the token list.
       1. all types (if typ==None)
       2. realms
       3. assigned or unassigned tokens (1/0)
    TODO: rename function to "getTokens"
    '''
    tokenList = []
    sqlQuery = Session.query(Token)
    if typ is not None:
        # filter for type
        sqlQuery = sqlQuery.filter(func.lower(Token.privacyIDEATokenType) == typ.lower())
    if assigned is not None:
        # filter if assigned or not
        if "0" == unicode(assigned):
            sqlQuery = sqlQuery.filter(Token.privacyIDEAUserid == "")
        elif "1" == unicode(assigned):
            sqlQuery = sqlQuery.filter(Token.privacyIDEAUserid != "")
        else:
            log.warning("assigned value not in [0,1] %r" % assigned)

    if realm is not None:
        # filter for the realm
        sqlQuery = sqlQuery.filter(and_(func.lower(Realm.name) == realm.lower(),
                                         TokenRealm.realm_id == Realm.id,
                                         TokenRealm.token_id == Token.privacyIDEATokenId)).distinct()

    for token in sqlQuery:
        log.debug("adding token with serial %r" % token.privacyIDEATokenSerialnumber)
        # the token is the database object, but we want an instance of the tokenclass!
        tokenList.append(createTokenClassObject(token))

    return tokenList

@log_with(log)
def setDefaults(token):
    ## set the defaults

    token.privacyIDEAOtpLen = int(getFromConfig("DefaultOtpLen", 6))
    token.privacyIDEACountWindow = int(getFromConfig("DefaultCountWindow", 15))
    token.privacyIDEAMaxFail = int(getFromConfig("DefaultMaxFailCount", 15))
    token.privacyIDEASyncWindow = int(getFromConfig("DefaultSyncWindow", 1000))

    token.privacyIDEATokenType = u"HMAC"


@log_with(log)
def isTokenOwner(serial, user):
    ret = False

    userid = ""
    idResolver = ""
    idResolverClass = ""

    if user is not None and (user.isEmpty() == False):
    # the upper layer will catch / at least should
        (userid, idResolver, idResolverClass) = getUserId(user)

    if len(userid) + len(idResolver) + len(idResolverClass) == 0:
        log.info("no user found %r", user.login)
        raise TokenAdminError("no user found %s" % user.login, id=1104)

    toks = getTokens4UserOrSerial(None, serial)

    if len(toks) > 1:
        log.info("multiple tokens found for user %r" % user.login)
        raise TokenAdminError("multiple tokens found!", id=1101)
    if len(toks) == 0:
        log.info("no tokens found for user %r", user.login)
        raise TokenAdminError("no token found!", id=1102)

    token = toks[0]

    (uuserid, uidResolver, uidResolverClass) = token.getUser()

    if uidResolver == idResolver:
        if uidResolverClass == idResolverClass:
            if uuserid == userid:
                ret = True

    return ret

@log_with(log)
def tokenExist(serial):
    '''
    returns true if the token exists
    '''
    if serial:
        toks = getTokens4UserOrSerial(None, serial)
        return (len(toks) > 0)
    else:
        # If we have no serial we return false anyway!
        return False


@log_with(log)
def hasOwner(serial):
    '''
    returns true if the token is owned by any user
    '''
    ret = False

    toks = getTokens4UserOrSerial(None, serial)

    if len(toks) > 1:
        log.info("multiple tokens found with serial %r" % serial)
        raise TokenAdminError("multiple tokens found!", id=1101)
    if len(toks) == 0:
        log.info("no token found with serial %r" % serial)
        raise TokenAdminError("no token found!", id=1102)

    token = toks[0]

    (uuserid, uidResolver, uidResolverClass) = token.getUser()

    if len(uuserid) + len(uidResolver) + len(uidResolverClass) > 0:
        ret = True

    return ret

@log_with(log)
def getTokenOwner(serial):
    '''
    returns the user object, to which the token is assigned.
    the token is idetified and retirved by it's serial number

    :param serial: serial number of the token
    :return: user object
    '''
    token = None

    toks = getTokens4UserOrSerial(None, serial)
    if len(toks) > 0:
        token = toks[0]

    user = get_token_owner(token)

    return user

@log_with(log)
def get_token_owner(token):
    """
    provide the owner as a user object for a given tokenclass obj

    :param token: tokenclass object
    :return: user object
    """

    user = User()

    if token is None:
        ## for backward compatibility, we return here an empty user
        return user

    serial = token.getSerial()

    log.debug("token found: %r" % token)
    uid, resolver, resolverClass = token.getUser()

    userInfo = getUserInfo(uid, resolver, resolverClass)
    log.debug("got the owner %r, %r, %r"
               % (uid, resolver, resolverClass))

    realms = getUserRealms(User(uid, "", resolverClass.split(".")[-1]))
    log.debug("got this realms: %r" % realms)

    # if there are several realms, than we need to find out, which one!
    if len(realms) > 1:
        t_realms = getTokenRealms(serial)
        common_realms = list(set(realms).intersection(t_realms))
        if len(common_realms) > 1:
            raise Exception(_("get_token_owner: The user %s/%s and the token"
                              " %s is located in several realms: "
                              "%s!" % (uid, resolverClass, serial, common_realms)))
        realm = common_realms[0]
    elif len(realms) == 0:
        raise Exception(_("get_token_owner: The user %s in the resolver"
                          " %s for token %s could not be found in any "
                          "realm!" % (uid, resolverClass, serial)))
    else:
        realm = realms[0]

    user.realm = realm
    user.login = userInfo.get('username')
    user.conf = resolverClass

    log.debug("found the user %r and the realm %r as "
              "owner of token %r" % (user.login, user.realm, serial))

    return user

@log_with(log)
def getTokenType(serial):
    '''
    Returns the tokentype of a given serial number

    :param serial: the serial number of the to be searched token
    '''
    toks = getTokens4UserOrSerial(None, serial, _class=False)

    typ = ""
    for tok in toks:
        typ = tok.privacyIDEATokenType

    return typ

@log_with(log)
def check_serial(serial):
    '''
    This checks, if a serial number already exists

    The function returns a tuple:
        (result, new_serial)

    If the serial already exists a new, modified serial new_serial is returned.

    result: bool: True if the serial does not already exist.
    '''
    # serial does not exist, yet
    result = True
    new_serial = serial

    i = 0
    while len(getTokens4UserOrSerial(None, new_serial)) > 0:
        # as long as we find a token, modify the serial:
        i = i + 1
        result = False
        new_serial = "%s_%02i" % (serial, i)

    return (result, new_serial)

@log_with(log)
def auto_assignToken(passw, user, pin="", param=None):
    '''
    This function is called to auto_assign a token, when the
    user enters an OTP value of an not assigned token.
    '''
    ret = False
    auto = False

    if param is None:
        param = {}

    # Fixme: circle dependency
    try:
        Policy = PolicyClass(request, config, c,
                             get_privacyIDEA_config())
        auto, _otplen = Policy.get_autoassignment(user)
    except Exception as e:
        log.error("%r" % e)

    # check if autoassignment is configured
    if not auto:
        log.debug("no autoassigment configured")
        return False

    # check if user has a token
    # TODO: this may dependend on a policy definition
    tokens = getTokens4UserOrSerial(user, "")
    if len(tokens) > 0:
        log.debug("no auto_assigment for user %r@%r. He "
                  "already has some tokens." % (user.login, user.realm))
        return False

    matching_token_count = 0

    token = None
    pin = ""

    ## get all tokens of the users realm, which are not assigned
    tokens = getTokensOfType(typ=None, realm=user.realm, assigned="0")
    for token in tokens:
        (res, pin, otp) = token.splitPinPass(passw)
        if res >= 0:
            r = token.check_otp_exist(otp=otp,
                                      window=token.getOtpCountWindow())
            if r >= 0:
                matching_token_count += 1

    if matching_token_count != 1:
        log.warning("%d tokens with the given OTP value found." % matching_token_count)
        return False

    success = check_user_password(user.login, user.realm, pin)
    if success is None:
        log.error("User %r@%r failed to authenticate against userstore" % (user.login, user.realm))
        return False

    serial = token.getSerial()

    log.debug("found serial number: %r" % serial)

    # should the password of the autoassignement be used as pin??
    Policy = PolicyClass(request, config, c,
                         get_privacyIDEA_config())
    if Policy.ignore_autoassignment_pin(user):
        pin = None

    # if found, assign the found token to the user.login
    try:
        assignToken(serial, user, pin)
        c.audit['serial'] = serial
        c.audit['info'] = "Token auto assigned"
        c.audit['token_type'] = token.getType()
        ret = True
    except Exception as e:
        log.error("Failed to assign token: %r" % e)
        return False

    return ret

@log_with(log)
def assignToken(serial, user, pin, param=None):
    '''
    assignToken - used to assign and to unassign token
    '''
    if param is None:
        param = {}

    toks = getTokens4UserOrSerial(None, serial)
    #toks  = Session.query(Token).filter(Token.privacyIDEATokenSerialnumber == serial)

    if len(toks) > 1:
        log.warning("multiple tokens found with serial: %r" % serial)
        raise TokenAdminError("multiple tokens found!", id=1101)
    if len(toks) == 0:
        log.warning("no tokens found with serial: %r" % serial)
        raise TokenAdminError("no token found!", id=1102)

    token = toks[0]
    if (user.login == ""):
        report = False
    else:
        report = True

    token.setUser(user, report)

    ## set the Realms of the Token
    realms = getRealms4Token(user)
    token.setRealms(realms)

    if pin is not None:
        token.setPin(pin, param)

    ## reset the OtpCounter
    token.setFailCount(0)

    try:
        token.storeToken()
    except Exception as e:
        log.error('update Token DB failed')
        raise TokenAdminError("Token assign failed for %s/%s : %r"
                              % (user.login, serial, e), id=1105)

    log.debug("successfully assigned token with serial %r to user %r" % (serial, user.login))
    return True

@log_with(log)
def unassignToken(serial, user, pin):
    '''
    unassignToken - used to assign and to unassign token
    '''
    toks = getTokens4UserOrSerial(None, serial)
    #toks  = Session.query(Token).filter(Token.privacyIDEATokenSerialnumber == serial)

    if len(toks) > 1:
        log.warning("multiple tokens found with serial: %r" % serial)
        raise TokenAdminError("multiple tokens found!", id=1101)
    if len(toks) == 0:
        log.warning("no tokens found with serial: %r" % serial)
        raise TokenAdminError("no token found!", id=1102)

    token = toks[0]
    u = User('', '', '')
    token.setUser(u, True)
    token.setPin(pin)

    ## reset the OtpCounter
    token.setFailCount(0)

    try:
        token.storeToken()
    except Exception as e:
        log.error('update token DB failed')
        raise TokenAdminError("Token assign failed for %r/%r: %r"
                              % (user, serial, e), id=1105)

    log.debug("successfully unassigned token with serial %r"
               % serial)
    return True

@log_with(log)
def checkSerialPass(serial, passw, options=None, user=None):
    '''
    This function checks the otp for a given serial
    @attention: the parameter user must be set, as the pin policy==1 will verify the user pin
    '''
    tokenList = getTokens4UserOrSerial(None, serial, forUpdate=True)

    if passw is None:
        ## other than zero or one token should not happen, as serial is unique
        if len(tokenList) == 1:
            theToken = tokenList[0]
            tok = theToken.token
            realms = tok.getRealmNames()
            if realms is None or len(realms) == 0:
                realm = getDefaultRealm()
            elif len(realms) > 0:
                realm = realms[0]
            userInfo = getUserInfo(tok.privacyIDEAUserid, tok.privacyIDEAIdResolver, tok.privacyIDEAIdResClass)
            user = User(login=userInfo.get('username'), realm=realm)

            if theToken.is_challenge_request(passw, user, options=options):
                (res, opt) = create_challenge(tokenList[0], options)
            else:
                raise ParameterError("Missing parameter: pass", id=905)

        else:
            raise Exception('No token found: unable to create challenge for %s' % serial)

    else:
        log.debug("checking len(pass)=%r for serial %r"
              % (len(passw), serial))

        (res, opt) = checkTokenList(tokenList, passw, user=user, options=options)

    return (res, opt)

@log_with(log)
def checkYubikeyPass(passw):
    '''
    Checks the password of a yubikey in Yubico mode (44,48), where the first
    12 or 16 characters are the tokenid

    :param passw: The password that consist of the static yubikey prefix and the otp
    :type passw: string

    :return: True/False and the User-Object of the token owner
    :rtype: dict
    '''
    opt = None
    res = False

    tokenList = []

    # strip the yubico OTP and the PIN
    modhex_serial = passw[:-32][-16:]
    try:
        serialnum = "UBAM" + modhex_decode(modhex_serial)
    except TypeError as exx:
        log.error("Failed to convert serialnumber: %r" % exx)
        return res, opt

    ## build list of possible yubikey tokens
    serials = [serialnum]
    for i in range(1, 3):
        serials.append("%s_%s" % (serialnum, i))

    for serial in serials:
        tokens = getTokens4UserOrSerial(serial=serial)
        tokenList.extend(tokens)

    if len(tokenList) == 0:
        c.audit['action_detail'] = ("The serial %s could not be found!"
                                    % serialnum)
        return res, opt

    ## FIXME if the Token has set a PIN and the User does not want to enter the PIN
    ## for authentication, we need to do something different here...
    ## and avoid PIN checking in __checkToken.
    ## We could pass an "option" to __checkToken.
    (res, opt) = checkTokenList(tokenList, passw)

    # Now we need to get the user
    if res is not False and 'serial' in c.audit:
        serial = c.audit.get('serial', None)
        if serial is not None:
            user = getTokenOwner(serial)
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm
            opt = {}
            opt['user'] = user.login
            opt['realm'] = user.realm

    return res, opt

@log_with(log)
def checkUserPass(user, passw, options=None):
    '''
    :param user: the to be identified user
    :type user: User object
    :param passw: the identifiaction pass
    :param options: optional parameters, which are provided
                to the token checkOTP / checkPass

    :return: tuple of True/False and optional information
    '''
    # the upper layer will catch / at least should ;-)
    opt = None
    serial = None
    resolverClass = None
    uid = None

    if user is not None and (user.isEmpty() == False):
    # the upper layer will catch / at least should
        try:
            (uid, _resolver, resolverClass) = getUserId(user)
        except:
            passOnNoUser = "PassOnUserNotFound"
            passOn = getFromConfig(passOnNoUser, False)
            if False != passOn and "true" == passOn.lower():
                c.audit['action_detail'] = "authenticated by PassOnUserNotFound"
                return (True, opt)
            else:
                c.audit['action_detail'] = "User not found"
                return (False, opt)

    tokenList = getTokens4UserOrSerial(user, serial, forUpdate=True)

    if len(tokenList) == 0:
        c.audit['action_detail'] = "User has no tokens assigned"

        # here we check if we should to autoassign and try to do it
        log.debug("about to check auto_assigning")

        auto_assign_return = auto_assignToken(passw, user)
        if auto_assign_return == True:
            # We can not check the token, as the OTP value is already used!
            # But we will authenticate the user....
            return (True, opt)

        passOnNoToken = "PassOnUserNoToken"
        passOn = getFromConfig(passOnNoToken, False)
        if passOn != False and "true" == passOn.lower():
            c.audit['action_detail'] = "authenticated by PassOnUserNoToken"
            return (True, opt)

        ## Check if there is an authentication policy passthru
        Policy = PolicyClass(request, config, c,
                             get_privacyIDEA_config()) 
        if Policy.get_auth_passthru(user):
            log.debug("user %r has no token. Checking for passthru in realm %r" 
                      % (user.login, user.realm))
            y = getResolverObject(resolverClass)
            c.audit['action_detail'] = "Authenticated against Resolver"
            if  y.checkPass(uid, passw):
                return (True, opt)

        ## Check if there is an authentication policy passOnNoToken
        if Policy.get_auth_passOnNoToken(user):
            log.info("user %r has not token. PassOnNoToken set - authenticated!")
            c.audit['action_detail'] = "Authenticated by passOnNoToken policy"
            return (True, opt)

        return (False, opt)

    if passw is None:
        raise ParameterError(u"Missing parameter:pass", id=905)

    (res, opt) = checkTokenList(tokenList, passw, user, options=options)
    return (res, opt)

@log_with(log)
def checkTokenList(tokenList, passw, user=User(), options=None):
    '''
    identify a matching token and test, if the token is valid, locked ..
    This function is called by checkSerialPass and checkUserPass to

    :param tokenList: list of identified tokens
    :param passw: the provided passw (mostly pin+otp)
    :param user: the identified use - as class object
    :param option: additonal parameters, which are passed to the token

    :return: tuple of boolean and optional response
    '''
    res = False
    reply = None

    tokenclasses = config['tokenclasses']

    ## add the user to the options, so that every token
    ## could see the user
    if options:
        options['user'] = user
    else:
        options = { 'user' : user }

    b = getFromConfig("FailCounterIncOnFalsePin", "False")
    b = b.lower()


    ## if there has been one token in challenge mode, we only handle challenges
    challenge_tokens = []
    pinMatchingTokenList = []
    invalidTokenlist = []
    validTokenList = []
    auditList = []

    chall_reply = None

    Policy = PolicyClass(request, config, c,
                         get_privacyIDEA_config())
    pin_policies = Policy.get_pin_policies(user) or []

    for token in tokenList:

        audit = {}
        audit['serial'] = token.getSerial()
        audit['token_type'] = token.getType()
        audit['weight'] = 0

        log.debug("Found user with loginId %r: %r:\n"
                   % (token.getUserId(), token.getSerial()))

        ## check if the token is the list of supported tokens
        ## if not skip to the next token in list
        typ = token.getType()
        if not tokenclasses.has_key(typ.lower()):
            log.error('type %r not found in tokenclasses: %r' %
                      (typ, tokenclasses))
            continue

        ## now check if the token is in the same realm as the user
        if user is not None:
            t_realms = token.token.getRealmNames()
            u_realm = user.getRealm()
            if (len(t_realms) > 0 and len(u_realm) > 0 and
                u_realm.lower() not in t_realms) :
                continue

        tok_va = ValidateToken(token, context=c)
        ## in case of a failure during checking token, we log the error and
        ## continue with the next one
        try:
            (ret, reply) = tok_va.checkToken(passw, user, options=options)
        except Exception as exx:
            log.error("checking token %r failed: %r" % (token, exx))
            log.error("%s" % (traceback.format_exc()))
            ret = -1

        (cToken, pToken, iToken, vToken) = tok_va.get_verification_result()

        ## if we have a challenge, preserve the challenge response
        if len(cToken) > 0:
            challenge_tokens.extend(cToken)
            chall_reply = reply
            audit['action_detail'] = 'challenge created'
            audit['weight'] = 20

        # this means, the resolver password was wrong
        if len(pToken) == 1 and 1 in pin_policies:
            audit['action_detail'] = "wrong user password %r" % (ret)
            audit['weight'] = 10

        elif len(iToken) == 1:  ## this means the pin is wrong
            ## check, if we should increment
            # do not overwrite other error details!
            audit['action_detail'] = "wrong otp pin %r" % (ret)
            audit['weight'] = 15

            if b == "true":
                # We do not have a complete list of all invalid tokens, if
                # FailCounterIncOnFalsePin is False!
                # So we need the auditList!
                invalidTokenlist.extend(iToken)

        elif len(pToken) == 1 :  ## pin matches but the otp is wrong
            pinMatchingTokenList.extend(pToken)
            audit['action_detail'] = "wrong otp value"
            audit['weight'] = 25

        #any valid otp increments, independend of the tokens state !!
        elif len(vToken) > 0:
            audit['weight'] = 30
            matchinCounter = ret

            #any valid otp increments, independend of the tokens state !!
            token.incOtpCounter(matchinCounter)

            if (token.isActive() == True):
                if token.getFailCount() < token.getMaxFailCount():
                    if token.check_auth_counter():
                        if token.check_validity_period():
                            token.inc_count_auth()
                            token.inc_count_auth_success()
                            validTokenList.extend(vToken)
                        else:
                            audit['action_detail'] = "validity period mismatch"
                    else:
                        audit['action_detail'] = "Authentication counter exceeded"
                else:
                    audit['action_detail'] = "Failcounter exceeded"
            else:
                audit['action_detail'] = "Token inactive"

        # add the audit information to the auditList
        auditList.append(audit)

    # compose one audit entry from all token audit information
    c_audit={}
    if len(auditList) > 0:
        # sort the list for the value of the key "weight"
        sortedAuditList = sorted(auditList, key=lambda audit_entry: audit_entry.get("weight", 0))
        highest_audit = sortedAuditList[-1]
        c_audit['action_detail'] = highest_audit.get('action_detail', '')
        # check how many highest_audit values entries exist!
        highest_list = filter(lambda audit_entry: audit_entry.get("weight", 0) == highest_audit.get("weight", 0), sortedAuditList)
        if len(highest_list) == 1:
            c_audit['serial'] = highest_audit.get('serial', '')
            c_audit['token_type'] = highest_audit.get('token_type', '')
        else:
            # multiple tokens that might contain "wrong otp value" or "wrong otp pin"
            c_audit['serial'] = ''
            c_audit['token_type'] = ''
        try:
            for k in c_audit.keys():
                c.audit[k] = c_audit[k]
        except TypeError as exx:
            pass
        # FIXME: THe audit (c) stuff should be removed from this level!
            #log.error('''Problem accessing the pylons tmpl_context to store audit information. 
            #            This probably happens when an adminstrator authententicates to the
            #            selfservice, i.e. the validation is called outside of a request.''')
            #log.error("%r" % (traceback.format_exc()))


    ## handle the processing of challenge tokens
    if len(challenge_tokens) == 1:
        challenge_token = challenge_tokens[0]
        (_res, reply) = create_challenge(challenge_token, options=options)
        return (False, reply)

    elif len(challenge_tokens) > 1:
        raise Exception("processing of multiple challenges is not supported!")


    log.debug("Number of valid tokens found (validTokenNum): %d" % len(validTokenList))

    res = finish_check_TokenList(validTokenList, pinMatchingTokenList,
                                 invalidTokenlist, user)

    return (res, reply)

@log_with(log)
def finish_check_TokenList(validTokenList, pinMatchingTokenList,
                                    invalidTokenlist, user):

    validTokenNum = len(validTokenList)


    if validTokenNum > 1:
        c.audit['action_detail'] = "Multiple token found!"
        if user:
            log.error("multiple token match error: "
                      "Several Tokens matching with the same OTP PIN and OTP "
                      "for user %r. Not sure how to authenticate", user.login)
        raise UserError("multiple token match error", id= -33)
        ##return jsonError(-36,"multiple token match error",0)

    elif validTokenNum == 1:
        token = validTokenList[0]

        if user:
            log.info("user %r@%r successfully authenticated."
                      % (user.login, user.realm))
        else:
            log.info("serial %r successfully authenticated."
                      % c.audit.get('serial'))
        token.statusValidationSuccess()
        return True


    elif validTokenNum == 0:
        if user:
            log.warning("user %r@%r failed to authenticate."
                        % (user.login, user.realm))
        else:
            log.warning("serial %r failed to authenticate."
                        % c.audit.get('serial'))
        pinMatching = False;

        # check, if there have been some tokens
        # where the pin matched (but OTP failed
        # and increment only these
        for tok in pinMatchingTokenList:
            tok.incOtpFailCounter()
            tok.statusValidationFail()
            tok.inc_count_auth()
            pinMatching = True

        if pinMatching == False:
            for tok in invalidTokenlist:
                tok.incOtpFailCounter()
                tok.statusValidationFail()

    return False

@log_with(log)
def get_multi_otp(serial, count=0, epoch_start=0, epoch_end=0, curTime=None, timestamp=None):
    '''
    This function returns a list of OTP values for the given Token.
    Please note, that this controller needs to be activated and
    that the tokentype needs to support this function.

    method
        get_multi_otp    - get the list of OTP values

    
    :param serial: the serial number of the token
    :param count: number of the <count> next otp values (to be used with event or timebased tokens)
    :param epoch_start: unix time start date (used with timebased tokens)
    :param epoch_end: unix time end date (used with timebased tokens)
    :param curTime: used for selftest
    :type curTime: datetime object
    :param timestamp: unix time in seconds
    :type timestamp: int

    :return: dictionary of otp values
    '''
    ret = {"result" : False}
    toks = getTokens4UserOrSerial(None, serial)
    if len(toks) > 1:
        log.error("multiple tokens with serial %r found - cannot get OTP!" % serial)
        raise TokenAdminError("multiple tokens found - cannot get OTP!", id=1201)

    if len(toks) == 0:
        log.warning("there is no token with serial %r" % serial)
        ret["error"] = "No Token with serial %s found." % serial

    if len(toks) == 1:
        token = toks[0]
        log.debug("getting multiple otp values for token %r. curTime=%r" % (token, curTime))
        # if the token does not support getting the OTP value, res==False is returned
        (res, error, otp_dict) = token.get_multi_otp(count=count, 
                                                     epoch_start=epoch_start, 
                                                     epoch_end=epoch_end, 
                                                     curTime=curTime,
                                                     timestamp=timestamp)
        log.debug("received %r, %r, %r" % (res, error, otp_dict))

        if res == True:
            ret = otp_dict
            ret["result"] = True
        else:
            ret["error"] = error

    return ret

@log_with(log)
def getOtp(serial, curTime=None):
    '''
    This function returns the current OTP value for a given Token.
    Please note, that this controller needs to be activated and
    that the tokentype needs to support this function.

    method
        getOtp    - get the current OTP value

    parameter
        serial    - serialnumber for token
        curTime   - used for self test

    return
        tuple with (res, pin, otpval, passw)

    '''
    log.debug("retrieving OTP value for token %r" % serial)
    toks = getTokens4UserOrSerial(None, serial)

    if len(toks) > 1:
        raise TokenAdminError("multiple tokens found - cannot get OTP!", id=1101)

    if len(toks) == 0:
        log.warning("there is no token with serial %r" % serial)
        return (-1, "", "", "")

    if len(toks) == 1:
        token = toks[0]
        # if the token does not support getting the OTP value, a -2 is returned.
        return token.getOtp(curTime=curTime)


@log_with(log)
def get_token_by_otp(token_list=None, otp="", window=10, typ=u"HMAC", realm=None, assigned=None):
    '''
    method
        get_token_by_otp    - from the given token list this function returns
                              the token, that generates the given OTP value
    :param token_list:        - the list of token objects to be investigated
    :param otpval:            - the otp value, that needs to be found
    :param window:            - the window of search
    :param assigned:          - or unassigned tokens (1/0)

    :return:         returns the token object.
    '''
    result_token = None

    resultList = []

    if token_list is None:
        token_list = getTokensOfType(typ, realm, assigned)

    for token in token_list:
        log.debug("checking token %r" % token.getSerial())
        r = token.check_otp_exist(otp=otp, window=window)
        log.debug("result = %d" % int(r))
        if r >= 0:
            resultList.append(token)

    if len(resultList) == 1:
        result_token = resultList[0]
    elif len(resultList) > 1:
        raise TokenAdminError("multiple tokens are matching this OTP value!", id=1200)

    return result_token

@log_with(log)
def get_serial_by_otp(token_list=None, otp="", window=10, typ=None, realm=None, assigned=None):
    '''
    Returns the serial for a given OTP value and the user
    (serial, user)

    :param otp:      -  the otp value to be searched
    :param window:   -  how many OTPs should be calculated per token
    :param typ:      -  The tokentype
    :param realm:    -  The realm in which to search for the token
    :param assigned: -  search either in assigned (1) or not assigend (0) tokens

    :return: the serial for a given OTP value and the user
    '''
    serial = ""
    username = ""
    resolverClass = ""

    token = get_token_by_otp(token_list, otp, window, typ, realm, assigned)

    if token is not None:
        serial = token.getSerial()
        uid, resolver, resolverClass = token.getUser()
        userInfo = getUserInfo(uid, resolver, resolverClass)
        log.debug("userinfo for token: %r" % userInfo)
        username = userInfo.get("username", "")

    return serial, username, resolverClass

@log_with(log)
def removeToken(user=None, serial=None):

    if (user is None or user.isEmpty() == True) and (serial is None):
        log.warning("Parameter user or serial required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    log.debug("for serial: %r, user: %r" % (serial, user))
    tokenList = getTokens4UserOrSerial(user, serial,
                                       forUpdate=True, _class=False)

    serials = []
    tokens = []
    token_ids = []
    try:

        for token in tokenList:
            ser = token.getSerial()
            serials.append(ser)
            token_ids.append(token.privacyIDEATokenId)
            tokens.append(token)

        ## we cleanup the challenges
        challenges = set()
        for serial in serials:
            challenges.update(get_challenges(serial=serial))

        for chall in challenges:
            Session.delete(chall)

        ## due to legacy SQLAlchemy it could happen that the
        ## foreign key relation could not be deleted
        ## so we do this manualy

        for t_id in token_ids:
            # delete references to client machines
            Session.query(MachineToken).filter(MachineToken.token_id == t_id).delete()
            Session.query(TokenRealm).filter(TokenRealm.token_id == t_id).delete()

        Session.commit()

        for token in tokens:
            Session.delete(token)


    except Exception as e:
        log.error('update token DB failed')
        raise TokenAdminError("removeToken: Token update failed: %r" % e, id=1132)


    return len(tokenList)


@log_with(log)
def setMaxFailCount(maxFail, user, serial):

    if (user is None) and (serial is None):
        log.warning("Parameter user or serial required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setMaxFail(maxFail)

    return len(tokenList)

@log_with(log)
def enableToken(enable, user, serial):

    if (user is None) and (serial is None):
        log.warning("parameter serial or user missing.")
        raise ParameterError("Parameter user or serial required!", id=1212)
    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.enable(enable)

    return len(tokenList)

@log_with(log)
def copyTokenPin(serial_from, serial_to):
    '''
    This function copies the token PIN from one token to the other token.
    This can be used for workflows like lost token.

    In fact the PinHash and the PinSeed need to be transferred

    returns:
        1 : success
        -1: no source token
        -2: no destination token
    '''
    tokens_from = getTokens4UserOrSerial(None, serial_from)
    tokens_to = getTokens4UserOrSerial(None, serial_to)
    if len(tokens_from) != 1:
        log.error("not a unique token to copy from found")
        return -1
    if len(tokens_to) != 1:
        log.error("not a unique token to copy to found")
        return -2
    pinhash, seed = tokens_from[0].getPinHashSeed()
    tokens_to[0].setPinHashSeed(pinhash, seed)
    return 1

def copyTokenUser(serial_from, serial_to):
    '''
    This function copies the user from one token to the other
    This can be used for workflows like lost token

    returns:
        1: success
        -1: no source token
        -2: no destination token
    '''
    tokens_from = getTokens4UserOrSerial(None, serial_from)
    tokens_to = getTokens4UserOrSerial(None, serial_to)
    if len(tokens_from) != 1:
        log.error("not a unique token to copy from found")
        return -1
    if len(tokens_to) != 1:
        log.error("not a unique token to copy to found")
        return -2
    uid, ures, resclass = tokens_from[0].getUser()
    tokens_to[0].setUid(uid, ures, resclass)

    copyTokenRealms(serial_from, serial_to)
    return 1

@log_with(log)
def copyTokenRealms(serial_from, serial_to):
    realmlist = getTokenRealms(serial_from)
    setRealms(serial_to, realmlist)

@log_with(log)
def losttoken(serial, new_serial="", password="", default_validity=0):
    """
    This is the workflow to handle a lost token

    :param serial: Token serial number
    :param new_serial: new serial number
    :param password: new password
    :param default_validity: set the token to be valid

    :return: result dictionary
    """

    res = {}
    if new_serial == "":
        new_serial = "lost%s" % serial

    user = getTokenOwner(serial)
    log.error("doing lost token for serial %r and user %r@%r"
                                            % (serial, user.login, user.realm))

    if user.login == "" or user.login is None:
        err = "You can only define a lost token for an assigned token."
        log.warning("%s" % err)
        raise Exception(err)

    Policy = PolicyClass(request, config, c,
                         get_privacyIDEA_config())
    pol = Policy.get_client_policy(get_client(),
                                    scope="enrollment", realm=user.realm,
                                    user=user.login, userObj=user)

    pw_len = Policy.getPolicyActionValue(pol, "lostTokenPWLen")
    validity = Policy.getPolicyActionValue(pol, "lostTokenValid",
                                                      max=False)
    contents = Policy.getPolicyActionValue(pol,
                                            "lostTokenPWContents", String=True)

    log.debug("losttoken: length: %r, validity: %r, contents: %r" 
              % (pw_len, validity, contents))

    if validity == -1:
        validity = 10
    if 0 != default_validity:
        validity = default_validity

    if pw_len == -1:
        pw_len = 10

    character_pool = "%s%s%s" % (string.ascii_lowercase,
                                 string.ascii_uppercase, string.digits)
    if contents != "":
        character_pool = ""
        if "c" in contents:
            character_pool += string.ascii_lowercase
        if "C" in contents:
            character_pool += string.ascii_uppercase
        if "n" in contents:
            character_pool += string.digits
        if "s" in contents:
            character_pool += "!#$%&()*+,-./:;<=>?@[]^_"

    if password == "":
        password = generate_password(size=pw_len, characters=character_pool)

    res['serial'] = new_serial

    (ret, tokenObj) = initToken({ "otpkey" : password,
                        "serial" : new_serial,
                        "type" : "pw",
                        "description" : "temporary replacement for %s" % serial
                         }, User('', '', ''))
    res['init'] = ret
    if True == ret:
        res['user' ] = copyTokenUser(serial, new_serial)
        res['pin'] = copyTokenPin(serial, new_serial)

        # set validity period
        end_date = (datetime.date.today()
                    + datetime.timedelta(days=validity)).strftime("%d/%m/%y")

        end_date = "%s 23:59" % end_date
        tokens = getTokens4UserOrSerial(User('', '', ''), new_serial)
        for tok in tokens:
            tok.set_validity_period_end(end_date)

        # fill results
        res['valid_to'] = "xxxx"
        res['password'] = password
        res['end_date'] = end_date
        # disable token
        res['disable'] = enableToken(False, User('', '', ''), serial)

    return res

@log_with(log)
def setPin(pin, user, serial, param=None):
    '''
    set the PIN
    '''
    if param is None:
        param = {}

    if (user is None) and (serial is None):
        log.warning("Parameter user or serial required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    if (user is not None):
        log.info("setting Pin for user %r@%r" % (user.login, user.realm))
    if (serial is not None):
        log.info("setting Pin for token with serial %r" % serial)

    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setPin(pin, param)

    return len(tokenList)

@log_with(log)
def setOtpLen(otplen, user, serial):

    if (user is None) and (serial is None):
        log.warning("Parameter user or serial required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    if (serial is not None):
        log.debug("setting OTP length for serial %r" % serial)
    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setOtpLen(otplen)

    return len(tokenList)

@log_with(log)
def setHashLib(hashlib, user, serial):
    '''
    sets the Hashlib in the tokeninfo
    '''
    if user is None and serial is None:
        log.warning("Parameter user or serial required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    if serial is not None:
        log.debug("setting hashlib for serial %r" % serial)
    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setHashLib(hashlib)

    return len(tokenList)

@log_with(log)
def setCountAuth(count, user, serial, max=False, success=False):
    '''
    sets either of the counters:
        count_auth
        count_auth_max
        count_auth_success
        count_auth_success_max
    '''
    if user is None and serial is None:
        log.warning("Parameter user or serial required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    if serial is not None:
        log.debug("setting authcount for serial %r" % serial)
    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        if max:
            if success:
                token.set_count_auth_success_max(count)
            else:
                token.set_count_auth_max(count)
        else:
            if success:
                token.set_count_auth_success(count)
            else:
                token.set_count_auth(count)

    return len(tokenList)

@log_with(log)
def addTokenInfo(info, value, user, serial):
    '''
    sets an abitrary Tokeninfo field
    '''
    if user is None and serial is None:
        log.warning("Parameter user or serial required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    if serial is not None:
        log.debug("setting tokeninfo %r for serial %r" % (info, serial))
    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.addToTokenInfo(info, value)

    return len(tokenList)

###############################################################################
## privacyIDEATokenPinUser
###############################################################################
@log_with(log)
def setPinUser(userPin, serial):

    user = None

    if serial is None:
        log.warning("Parameter serial required!")
        raise ParameterError("Parameter 'serial' is required!", id=1212)

    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setUserPin(userPin)

    return len(tokenList)

###############################################################################
## privacyIDEATokenPinSO
###############################################################################
@log_with(log)
def setPinSo(soPin, serial):
    user = None

    if serial is None:
        log.warning("Parameter serial required!")
        raise ParameterError("Parameter 'serial' is required!", id=1212)

    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setSoPin(soPin)

    return len(tokenList)

@log_with(log)
def setSyncWindow(syncWindow, user, serial):

    if user is None and serial is None:
        log.warning("Parameter serial or user required!")
        raise ParameterError("Parameter user or serial required!", id=1212)
    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setSyncWindow(syncWindow)

    return len(tokenList)

@log_with(log)
def setCounterWindow(countWindow, user, serial):

    if user is None and serial is None:
        log.warning("Parameter serial or user required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setCounterWindow(countWindow)

    return len(tokenList)

@log_with(log)
def setDescription(description, user, serial):

    if user is None and serial is None:
        log.warning("Parameter serial or user required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.setDescription(description)

    return len(tokenList)

@log_with(log)
def resyncToken(otp1, otp2, user, serial, options=None):
    ret = False

    if (user is None) and (serial is None):
        log.warning("Parameter serial or user required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        res = token.resync(otp1, otp2, options)
        if res == True:
            ret = True
    return ret

@log_with(log)
def resetToken(user=None, serial=None):

    if (user is None) and (serial is None):
        log.warning("[Parameter serial or user required!")
        raise ParameterError("Parameter user or serial required!", id=1212)

    log.debug("reset token with serial %r" % serial)
    tokenList = getTokens4UserOrSerial(user, serial)

    for token in tokenList:
        token.addToSession(Session)
        token.reset()

    return len(tokenList)


@log_with(log)
def _gen_serial(prefix, tokennum, min_len=8):
    '''
    helper to create a hex digit string

    :param prefix: the prepended prefix like LSGO
    :param tokennum: the token number counter (int)
    :param min_len: int, defining the length of the hex string
    :return: hex digit string
    '''
    h_serial = ''
    num_str = '%.4d' % tokennum
    h_len = min_len - len(num_str)
    if h_len > 0:
        h_serial = binascii.hexlify(os.urandom(h_len)).upper()[0:h_len]
    return "%s%s%s" % (prefix, num_str, h_serial)

@log_with(log)
def genSerial(tokenType=None, prefix=None):
    '''
    generate a serial number similar to the one generated in the manage web gui

    :param tokenType: the token type prefix is done by a lookup on the tokens
    :return: serial number
    '''
    if tokenType is None:
        tokenType = 'LSUN'

    tokenprefixes = config['tokenprefixes']

    if prefix is None:
        prefix = tokenType.upper()
        if tokenType.lower() in tokenprefixes:
            prefix = tokenprefixes.get(tokenType.lower())

    ## now search the number of ttypes in the token database
    tokennum = Session.query(Token).filter(
                    Token.privacyIDEATokenType == u'' + tokenType).count()

    serial = _gen_serial(prefix, tokennum + 1)

    ## now test if serial already exists
    while True:
        numtokens = Session.query(Token).filter(
                        Token.privacyIDEATokenSerialnumber == u'' + serial).count()
        if numtokens == 0:
            ## ok, there is no such token, so we're done
            break
        ## else - rare case:
        ## we add the numtokens to the number of existing tokens with serial
        serial = _gen_serial(prefix, tokennum + numtokens)

    return serial

@log_with(log)
def getTokenConfig(tok, section=None):
    '''
    getTokenConfig - return the config definition
                     of a dynamic token

    :param tok: token type (shortname)
    :type  tok: string

    :param section: subsection of the token definition - optional
    :type   section: string

    :return: dict - if nothing found an empty dict
    :rtype:  dict
    '''
    res = {}

    g = config['pylons.app_globals']
    tokenclasses = g.tokenclasses

    if tok in tokenclasses.keys():
        tclass = tokenclasses.get(tok)
        tclt = newToken(tclass)
        # check if we have a policy in the token definition
        if hasattr(tclt, 'getClassInfo'):
            res = tclt.getClassInfo(section, ret={})

    return res


### TODO: move TokenIterator to dedicated file

class TokenIterator(object):
    '''
    TokenIterator class - support a smooth iterating through the tokens
    '''
    @log_with(log)
    def __init__(self, user, serial, page=None, psize=None, filter=None,
                 sort=None, sortdir=None, filterRealm=None, user_fields=None,
                 params=None):
        '''
        constructor of Tokeniterator, which gathers all conditions to build
        a sqalchemy query - iterator

        :param user:     User object - user provides as well the searchfield entry
        :type  user:     User class
        :param serial:   serial number of a token
        :type  serial:   string
        :param page:     page number
        :type  page:     int
        :param psize:    how many entries per page
        :type  psize:    int
        :param filter:   additional condition
        :type  filter:   string
        :param sort:     sort field definition
        :type  sort:     string
        :param sortdir:  sort direction: ascending or descending
        :type  sortdir:  string
        :param filterRealm:  restrict the set of token to those in the filterRealm
        :type  filterRealm:  string or list
        :param user_fields:  list of additional fields from the user owner
        :type  user_fields: array
        :param params:  list of additional request parameters - currently not used
        :type  params: dict

        :return: - nothing / None

        '''
        if params is None:
            params = {}

        self.page = 1
        self.pages = 1
        self.tokens = 0
        self.user_fields = user_fields
        if self.user_fields == None:
            self.user_fields = []

        condition = None
        ucondition = None
        scondition = None

        valid_realms = []

        if type(filterRealm) in (str, unicode):
            filterRealm = [filterRealm]

        ## create a list of all realms, which are allowed to be searched
        realms = getRealms().keys()
        if '*' in filterRealm:
            valid_realms.extend(realms)
        else:
            for realm in realms:
                if realm in filterRealm:
                    valid_realms.append(realms)

        if serial is not None:
            ## check if the requested serial is in the realms of the admin (filterRealm)
            log.debug('start search for serial: >%r<' % (serial))

            allowed = False
            if filterRealm == ['*']:
                allowed = True
            else:
                realms = getTokenRealms(serial)
                for realm in realms:
                    if realm in filterRealm:
                        allowed = True

            if allowed == True:
                scondition = and_(Token.privacyIDEATokenSerialnumber == serial)

        if user.isEmpty() == False and user is not None:
            log.debug('start search for username: >%r<'
                      % (user))

            if user.login is not None and (user.login) > 0 :
                loginUser = user.login.lower()
                loginUser = loginUser.replace('"', '')
                loginUser = loginUser.replace("'", '')

                searchType = "any"

                ## search for a 'blank' user
                if len(loginUser) == 0 and len(user.login) > 0:
                    searchType = "blank"
                elif loginUser == "/:no user:/" or loginUser == "/:none:/":
                    searchType = "blank"
                elif loginUser == "/:no user info:/":
                    searchType = "wildcard"
                elif "*" in loginUser or "." in loginUser:
                    searchType = "wildcard"
                else:
                    ## no blank and no wildcard search
                    searchType = "exact"

                if searchType == "blank":
                    log.debug('search for empty user: >%r<' % (user.login))
                    ucondition = and_(Token.privacyIDEAUserid == u'')

                if searchType == "exact":
                    log.debug('search for exact user: %r' % (user))
                    serials = []
                    users = []

                    ## if search for a realmuser 'user@realm' we can take the
                    ## realm from the argument
                    if len(user.realm) > 0:
                        users.append(user)
                    else:
                        for realm in valid_realms:
                            users.append(User(user.login, realm))

                    for usr in users:
                        try:
                            tokens = getTokens4UserOrSerial(user=usr, _class=False)
                            for tok in tokens:
                                serials.append(tok.privacyIDEATokenSerialnumber)
                        except UserError as ex:
                            ## we get an exception if the user is not found
                            log.debug('no exact user: %r'
                                      % (user))
                            log.debug('%r' % ex)

                    if len(serials) > 0:
                        ## if tokens found, search for their serials
                        ucondition = and_(Token.privacyIDEATokenSerialnumber.in_(serials))
                    else:
                        ## if no token is found, block search for user
                        ## and return nothing
                        ucondition = and_(Token.privacyIDEAUserid == u'')

                ## handle case, when nothing found in former cases
                if searchType == "wildcard":
                    log.debug('wildcard search: %r' % (user))
                    serials = []
                    users = getAllTokenUsers()
                    logRe = None
                    lU = loginUser.replace('*', '.*')
                    #lU = lU.replace('..', '.')
                    logRe = re.compile(lU)

                    for ser in users:
                        userInfo = users.get(ser)
                        tokenUser = userInfo.get('username').lower()
                        try:
                            if logRe.match(u'' + tokenUser) is not None:
                                serials.append(ser)
                        except Exception as e:
                            log.error('error no express %r ' % e)

                    ## to prevent warning, we check is serials are found
                    ## SAWarning: The IN-predicate on
                    ## "Token.privacyIDEATokenSerialnumber" was invoked with an
                    ## empty sequence. This results in a contradiction, which
                    ## nonetheless can be expensive to evaluate.  Consider
                    ## alternative strategies for improved performance.
                    if len(serials) > 0:
                        ucondition = and_(Token.privacyIDEATokenSerialnumber.in_(serials))
                    else:
                        ucondition = and_(Token.privacyIDEAUserid == u'')

        if filter is None:
            condition = None
        elif filter in ['/:active:/', '/:enabled:/',
                        '/:token is active:/', '/:token is enabled:/' ]:
            condition = and_(Token.privacyIDEAIsactive == True)
        elif filter in ['/:inactive:/', '/:disabled:/',
                        '/:token is inactive:/', '/:token is disabled:/']:
            condition = and_(Token.privacyIDEAIsactive == False)
        else:
            condition = or_(Token.privacyIDEATokenDesc.contains(filter),
                            Token.privacyIDEAIdResClass.contains(filter),
                            Token.privacyIDEATokenSerialnumber.contains(filter),
                            Token.privacyIDEAUserid.contains(filter),
                            Token.privacyIDEATokenType.contains(filter))

        #####################################################
        ##  The condition for only getting certain realms!
        if filterRealm is None:
            conditionRealm = None
        else:
            if '*' in filterRealm:
                conditionRealm = None
                log.debug("wildcard for realm '*' found. Tokens of all realms will be displayed")
            else:
                conditionRealm = None
                for r in filterRealm:
                    log.debug("adding filter condition for realm %r" % r)
                    if r == "''" or r == '""': r = ''
                    if len(r) > 0:
                        conditionRealm = or_(conditionRealm,
                                                and_(Realm.name == r,
                                                    TokenRealm.realm_id == Realm.id,
                                                    TokenRealm.token_id == Token.privacyIDEATokenId))
                    else:
                        ## TODO: this is not correct, must be 'not in'
                        conditionRealm = or_(conditionRealm,
                                                and_(Token.privacyIDEAUserid == u''))

        ## create the final condition
        #condition = and_( condition, ucondition, scondition ) #, conditionRealm )

        condTuple = ()
        for conn in (condition, ucondition, scondition, conditionRealm):
            if type(conn).__name__ != 'NoneType':
                condTuple += (conn,)

        condition = and_(*condTuple)

        order = Token.privacyIDEATokenDesc

        ##  o privacyIDEA.TokenId: 17943
        ##  o privacyIDEA.TokenInfo: ""
        ##  o privacyIDEA.TokenType: "spass"
        ##  o privacyIDEA.TokenSerialnumber: "spass0000FBA3"
        ##  o User.description: "Cornelius Koelbel,cornelius.koelbel@lsexperts.de,local,"
        ##  o privacyIDEA.IdResClass: "useridresolver.PasswdIdResolver.IdResolver._default_Passwd_"
        ##  o User.username: "koelbel"
        ##  o privacyIDEA.TokenDesc: "Always Authenticate"
        ##  o User.userid: "1000"
        ##  o privacyIDEA.IdResolver: "/etc/passwd"
        ##  o privacyIDEA.Isactive: true

        if sort == "TokenDesc":
            order = Token.privacyIDEATokenDesc
        elif sort == "TokenId":
            order = Token.privacyIDEATokenId
        elif sort == "TokenType":
            order = Token.privacyIDEATokenType
        elif sort == "TokenSerialnumber":
            order = Token.privacyIDEATokenSerialnumber
        elif sort == "TokenType":
            order = Token.privacyIDEATokenType
        elif sort == "IdResClass":
            order = Token.privacyIDEAIdResClass
        elif sort == "IdResolver":
            order = Token.privacyIDEAIdResolver
        elif sort == "Userid":
            order = Token.privacyIDEAUserid
        elif sort == "FailCount":
            order = Token.privacyIDEAFailCount
        elif sort == "Userid":
            order = Token.privacyIDEAUserid
        elif sort == "Isactive":
            order = Token.privacyIDEAIsactive

        ## care for the result sort order
        if sortdir is not None and sortdir == "desc":
            order = order.desc()
        else:
            order = order.asc()

        ## care for the result pageing
        if page is None:
            self.toks = Session.query(Token).filter(condition).order_by(order).distinct()
            self.tokens = self.toks.count()

            log.debug("DB-Query returned # of objects: %i" % self.tokens)
            self.pagesize = self.tokens
            self.it = iter(self.toks)
            return

        try:
            if psize is None:
                pagesize = int(getFromConfig("pagesize", 50))
            else:
                pagesize = int(psize)
        except:
            pagesize = 20

        try:
            thePage = int (page) - 1
        except:
            thePage = 0
        if thePage < 0:
            thePage = 0

        start = thePage * pagesize
        stop = (thePage + 1) * pagesize

        self.toks = Session.query(Token).filter(condition).order_by(order).distinct()
        self.tokens = self.toks.count()
        log.debug("DB-Query returned # of objects: %i" % self.tokens)
        self.page = thePage + 1
        fpages = float(self.tokens) / float(pagesize)
        self.pages = int(fpages)
        if fpages - int(fpages) > 0:
            self.pages = self.pages + 1
        self.pagesize = pagesize
        self.toks = self.toks.slice(start, stop)

        self.it = iter(self.toks)
        return

    @log_with(log)
    def getResultSetInfo(self):
        resSet = {"pages"   : self.pages,
                  "pagesize" : self.pagesize,
                  "tokens"  : self.tokens,
                  "page"    : self.page}
        return resSet

    @log_with(log)
    def getUserDetail(self, tok):
        userInfo = {}
        uInfo = {}

        userInfo["User.description"] = u''
        userInfo["User.userid"] = u''
        userInfo["User.username"] = u''
        for field in self.user_fields:
            userInfo["User.%s" % field] = u''

        if tok.privacyIDEAUserid != '':
            #userInfo["User.description"]    = u'/:no user info:/'
            userInfo["User.userid"] = u'/:no user info:/'
            userInfo["User.username"] = u'/:no user info:/'

            uInfo = getUserInfo(tok.privacyIDEAUserid, tok.privacyIDEAIdResolver, tok.privacyIDEAIdResClass)
            if uInfo is not None and len(uInfo) > 0:
                if uInfo.has_key("description"):
                    description = uInfo.get("description")
                    if isinstance(description, str):
                        userInfo["User.description"] = description.decode(ENCODING)
                    else:
                        userInfo["User.description"] = description

                if uInfo.has_key("userid"):
                    userid = uInfo.get("userid")
                    if isinstance(userid, str):
                        userInfo["User.userid"] = userid.decode(ENCODING)
                    else:
                        userInfo["User.userid"] = userid

                if uInfo.has_key("username"):
                    username = uInfo.get("username")
                    if isinstance(username, str):
                        userInfo["User.username"] = username.decode(ENCODING)
                    else:
                        userInfo["User.username"] = username

                for field in self.user_fields:
                    fieldvalue = uInfo.get(field, "")
                    if isinstance(fieldvalue, str):
                        userInfo["User.%s" % field] = fieldvalue.decode(ENCODING)
                    else:
                        userInfo["User.%s" % field] = fieldvalue

        return (userInfo, uInfo)

    @log_with(log)
    def next(self):
        tok = self.it.next()
        desc = tok.get_vars(save=True)
        ''' add userinfo to token description '''
        (userInfo, ret) = self.getUserDetail(tok)
        desc.update(userInfo)

        return desc

    @log_with(log)
    def __iter__(self):
        return self



'''
The policies are enhanced by the loaded tokens. 
This is whay we put the policydefinition into the token module
'''
@log_with(log)
def get_policy_definitions(scope=""):
    '''
        returns the policy definitions of
          - allowed scopes
          - allowed actions in scopes
          - type of actions
    '''

    pol = {
        'admin': {
            'enable': {'type': 'bool',
                       'desc' : _('Admin is allowed to enable tokens.')},
            'disable': {'type': 'bool',
                        'desc' : _('Admin is allowed to disable tokens.')},
            'set': {'type': 'bool',
                    'desc' : _('Admin is allowed to set token properties.')},
            'setOTPPIN': {'type': 'bool',
                          'desc' : _('Admin is allowed to set the OTP PIN of tokens.')},
            'setMOTPPIN': {'type': 'bool',
                           'desc' : _('Admin is allowed to set the mOTP PIN of motp tokens.')},
            'setSCPIN': {'type': 'bool',
                         'desc' : _('Admin is allowed to set the smartcard PIN of tokens.')},
            'resync': {'type': 'bool',
                       'desc' : _('Admin is allowed to resync tokens.')},
            'reset': {'type': 'bool',
                      'desc' : _('Admin is allowed to reset the Failcounter of a token.')},
            'assign': {'type': 'bool',
                       'desc' : _('Admin is allowed to assign a token to a user.')},
            'unassign': {'type': 'bool',
                         'desc' : _('Admin is allowed to remove the token from a user, '
                         'i.e. unassign a token.')},
            'import': {'type': 'bool',
                       'desc' : _('Admin is allowed to import token files.')},
            'remove': {'type': 'bool',
                       'desc' : _('Admin is allowed to remove tokens from the database.')},
            'userlist': {'type': 'bool',
                         'desc' : _('Admin is allowed to view the list of the users.')},
            'checkstatus': {'type': 'bool',
                            'desc' : _('Admin is allowed to check the status of a challenge'
                                       ' resonse token.')},
            'manageToken': {'type': 'bool',
                            'desc' : _('Admin is allowed to manage the realms of a token.')},
            'getserial': {'type': 'bool',
                          'desc' : _('Admin is allowed to retrieve a serial for a given OTP value.')},
            'copytokenpin': {'type': 'bool',
                             'desc' : _('Admin is allowed to copy the PIN of one token '
                                        'to another token.')},
            'copytokenuser': {'type': 'bool',
                              'desc' : _('Admin is allowed to copy the assigned user to another'
                                         ' token, i.e. assign a user ot another token.')},
            'losttoken': {'type': 'bool',
                          'desc' : _('Admin is allowed to trigger the lost token workflow.')},
            'getotp': {
                'type': 'bool',
                'desc': _('Allow the administrator to retrieve OTP values for tokens.')}
        },
        'gettoken': {
            'max_count_dpw': {'type': 'int',
                              'desc' : _('When OTP values are retrieved for a DPW token, '
                                         'this is the maximum number of retrievable OTP values.')},
            'max_count_hotp': {'type': 'int',
                               'desc' : _('When OTP values are retrieved for a HOTP token, '
                                          'this is the maximum number of retrievable OTP values.')},
            'max_count_totp': {'type': 'int',
                               'desc' : _('When OTP values are retrieved for a TOTP token, '
                                          'this is the maximum number of retrievable OTP values.')},
        },
        'selfservice': {
            'assign': {
                'type': 'bool',
                'desc': _("The user is allowed to assign an existing token"
                          " that is not yet assigned"
                          " using the token serial number.")},
            'disable': {'type': 'bool',
                        'desc': _('The user is allowed to disable his own tokens.')},
            'enable': {'type': 'bool',
                       'desc': _("The user is allowed to enable his own tokens.")},
            'delete': {'type': 'bool',
                       "desc": _("The user is allowed to delete his own tokens.")},
            'unassign': {'type': 'bool',
                         "desc": _("The user is allowed to unassign his own tokens.")},
            'resync': {'type': 'bool',
                       "desc": _("The user is allowed to resyncronize his tokens.")},
            'reset': {
                'type': 'bool',
                'desc': _('The user is allowed to reset the failcounter of his tokens.')},
            'setOTPPIN': {'type': 'bool',
                          "desc": _("The user is allowed to set the OTP PIN of his tokens.")},
            'setMOTPPIN': {'type': 'bool',
                           "desc": _("The user is allowed to set the mOTP PIN of his mOTP tokens.")},
            'getotp': {'type': 'bool',
                       "desc": _("The user is allowed to retrieve OTP values for his own tokens.")},
            'otp_pin_maxlength': {'type': 'int', 
                                  'value': range(0, 100),
                                  "desc": _("Set the maximum allowed length of the OTP PIN.")},
            'otp_pin_minlength': {'type': 'int', 
                                  'value': range(0, 100),
                                  "desc" : _("Set the minimum required lenght of the OTP PIN.")},
            'otp_pin_contents': {'type': 'str',
                                 "desc" : _("Specifiy the required contents of the OTP PIN. (c)haracters, (n)umeric, (s)pecial, (o)thers. [+/-]!")},
            'activateQR': {'type': 'bool',
                           "desc": _("The user is allowed to enroll a QR token.")},
            'webprovisionOATH': {'type': 'bool',
                                 "desc": _("The user is allowed to enroll an OATH token.")},
            'webprovisionGOOGLE': {'type': 'bool',
                                   "desc": _("The user is allowed to enroll a Google Authenticator event based token.")},
            'webprovisionGOOGLEtime': {'type': 'bool',
                                       "desc": _("The user is allowed to enroll a Google Authenticator time based token.")},
            'max_count_dpw': {'type': 'int',
                              "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a DPW token.")},
            'max_count_hotp': {'type': 'int',
                               "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a HOTP token.")},
            'max_count_totp': {'type': 'int',
                               "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a TOTP token.")},
            'history': {
                'type': 'bool',
                'desc': _('Allow the user to view his own token history.')},
            'getserial': {
                'type': 'bool',
                'desc': _('Allow the user to search an unassigned token by OTP value.')},
            'auth' : {
                'type' : 'str',
                'desc' : _('If set to "otp": Users in this realm need to login with OTP to the selfservice.')}
            },
        'system': {
            'read': {'type': 'bool',
                     "desc" : _("Admin is allowed to read the system configuration.")},
            'write': {'type': 'bool',
                      "desc" : _("Admin is allowed to write and modify the system configuration.")},
            },
        'enrollment': {
            'tokencount': {
                'type': 'int',
                'desc': _('Limit the number of allowed tokens in a realm.')},
            'maxtoken': {
                'type': 'int',
                'desc': _('Limit the number of tokens a user in this realm may '
                        'have assigned.')},
            'otp_pin_random': {
                'type': 'int',
                'value': range(0, 100),
                "desc": _("Set a random OTP PIN with this lenght for a token.")},
            'otp_pin_encrypt': {
                'type': 'int',
                'value': [0, 1],
                "desc": _("If set to 1, the OTP PIN is encrypted. The normal behaviour is the PIN is hashed.")},
            'tokenlabel': {
                'type': 'str',
                'desc': _("Set label for a new enrolled Google Authenticator. "
                          "Possible tags are &lt;u&gt; (user), &lt;r&gt; (realm), &lt;s&gt; (serial).")},
            'autoassignment': {
                'type': 'int',
                'value': [6, 8],
                'desc': _("Users can assign a token just by using the "
                          "unassigned token to authenticate. This is the lenght"
                          " of the OTP value - either 6, 8, 32, 48.")},
            'ignore_autoassignment_pin': {
                'type': 'bool',
                'desc' : _("Do not set password from auto assignment as token pin.")},
            'lostTokenPWLen': {
                'type': 'int',
                'desc': _('The length of the password in case of '
                        'temporary token (lost token).')},
            'lostTokenPWContents': {
                'type': 'str',
                'desc': _('The contents of the temporary password, '
                        'described by the characters C, c, n, s.')},
            'lostTokenValid': {
                'type': 'int',
                'desc': _('The length of the validity for the temporary '
                        'token (in days).')},
            },
        'authentication': {
            'smstext': {
                'type': 'str',
                'desc': _('The text that will be send via SMS for an SMS token. '
                        'Use &lt;otp&gt; and &lt;serial&gt; as parameters.')},
            'otppin': {
                'type': 'int',
                'value': [0, 1, 2],
                'desc': _('Either use the Token PIN (0), use the Userstore '
                        'Password (1) or use no fixed password '
                        'component (2).')},
            'autosms': {
                'type': 'bool',
                'desc': _('If set, a new SMS OTP will be sent after '
                        'successful authentication with one SMS OTP.')},
            'passthru': {
                'type': 'bool',
                'desc': _('If set, the user in this realm will be authenticated '
                        'against the UserIdResolver, if the user has no '
                        'tokens assigned.')
                },
            'passOnNoToken': {
                'type': 'bool',
                'desc': _('If the user has no token, the authentication request '
                        'for this user will always be true.')
                },
            'qrtanurl': {
                'type': 'str',
                'desc': _('The URL for the half automatic mode that should be '
                        'used in a QR Token')
                },
            'challenge_response': {
                'type': 'str',
                'desc': _('A list of tokentypes for which challenge response '
                        'should be used.')
                }
            },
        'authorization': {
            'authorize': {
                'type': 'bool',
                'desc': _('The user/realm will be authorized to login '
                        'to the clients IPs.')},
            'tokentype': {
                'type': 'str',
                'desc': _('The user will only be authenticated with this '
                        'very tokentype.')},
            'serial': {
                'type': 'str',
                'desc': _('The user will only be authenticated if the serial '
                        'number of the token matches this regexp.')},
            'setrealm': {
                'type': 'str',
                'desc': _('The Realm of the user is set to this very realm. '
                        'This is important if the user is not contained in '
                        'the default realm and can not pass his realm.')},
            'detail_on_success': {
                'type': 'bool',
                'desc': _('In case of successful authentication additional '
                        'detail information will be returned.')},
            'detail_on_fail': {
                'type': 'bool',
                'desc': _('In case of failed authentication additional '
                        'detail information will be returned.')}
            },
        'audit': {
            'view': {
                'type': 'bool',
                'desc' : _("Admin is allowed to view the audit log.")}
        },
        'ocra': {
            'request': {
                'type': 'bool',
                'desc': _('Allow to do a ocra/request.')},
            'status': {
                'type': 'bool',
                'desc': _('Allow to check the transaction status.')},
            'activationcode': {
                'type': 'bool',
                'desc': _('Allow to do an ocra/getActivationCode.')},
            'calcOTP': {
                'type': 'bool',
                'desc': _('Allow to do an ocra/calculateOtp.')}
        },
        'machine': {
                    'create': {'type': 'bool',
                               'desc': _("Create a new client "
                                         "machine definition")
                               },
                    'delete': {'type': 'bool',
                               'desc': _("delete a client machine defintion")},
                    'show': {'type': 'bool',
                             'desc': _("list the client machine definitions")},
                    'addtoken': {'type': 'bool',
                                 'desc': _("add a token to a client machine")},
                    'deltoken': {'type': 'bool',
                                 'desc': _("delete a token from "
                                           "a client machine")},
                    'showtoken': {'type': 'bool',
                                  'desc': _("list the tokens and "
                                            "client machines")},
                    'gettokenapps': {'type': 'bool',
                                  'desc': _("get the authentication items "
                                            "for a client machine")}
                    }
    }

    ## now add generic policies, which every token should provide:
    ## - init<TT>
    ## - enroll<TT>, but only, if there is a rendering section

    for ttype in get_token_type_list():
        pol['admin']["init%s" % ttype.upper()] = {'type': 'bool',
                                                  'desc': _('Admin is allowed to initalize %s tokens.') % ttype.upper()}

        ## TODO: action=initETNG
        ## Cornelius Kölbel        Apr 18 7: 31 PM
        ##
        ## Haben wir auch noch den die policy
        ##
        ## scope=admin, action=initETNG?
        ##
        ## Das ist nämlich eine spezialPolicy, die der HMAC-Token mitbringen
        ## muss.

        ## todo: if all tokens are dynamic, the token init must be only shown
        ## if there is a rendering section for:
        ## conf = getTokenConfig(ttype, section='init')
        ## if len(conf) > 0:
        ##    pol['admin']["init%s" % ttype.upper()]={'type': 'bool'}

        conf = getTokenConfig(ttype, section='selfservice')
        if 'enroll' in conf:
            pol['selfservice']["enroll%s" % ttype.upper()] = {
                'type': 'bool',
                'desc': _("The user is allowed to enroll a %s token.") % ttype}

        ## now merge the dynamic Token policy definition
        ## into the global definitions
        policy = getTokenConfig(ttype, section='policy')

        ## get all policy sections like: admin, selfservice . . '''
        pol_keys = pol.keys()

        for pol_section in policy.keys():
            ## if we have a dyn token definition of this section type
            ## add this to this section - and make sure, that it is
            ## then token type prefixed
            if pol_section in pol_keys:
                pol_entry = policy.get(pol_section)
                for pol_def in pol_entry:
                    set_def = pol_def
                    if pol_def.startswith(ttype) is not True:
                        set_def = '%s_%s' % (ttype, pol_def)

                    pol[pol_section][set_def] = pol_entry.get(pol_def)

    ##return sub section, if scope is defined
    ##  make sure that scope is in the policy key
    ##  e.g. scope='_' is undefined and would break
    if scope and scope in pol:
        pol = pol[scope]

    return pol
    


#eof###########################################################################

