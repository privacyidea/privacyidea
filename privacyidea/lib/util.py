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
several independent functions
contains utility functions
'''

from privacyidea.lib.error import ParameterError
from privacyidea.lib.config import getFromConfig
from privacyidea.lib.log import log_with
import binascii
from privacyidea.model.meta import Session
from privacyidea.model import Token, Realm, TokenRealm
from sqlalchemy import and_

import string
from privacyidea.lib.crypto import urandom
from privacyidea.lib.crypto import geturandom
import pkg_resources
import logging

log = logging.getLogger(__name__)
import re
ENCODING = "utf-8"

SESSION_KEY_LENGTH = 32

optional = True
required = False



def get_version_number():
    '''
    returns the privacyidea version
    '''
    version = "unknown"
    try:
        version = pkg_resources.get_distribution("privacyidea").version
    except:
        pass
    return version

def get_version():
    '''
    This returns the version, that is displayed in the WebUI and self service portal.
    '''
    version = get_version_number()
    return "privacyIDEA %s" % version

def get_copyright_info():
    '''
    This returns the copyright information displayed in the WebUI and selfservice portal.
    '''
    return "privacyidea.org"

def getParam(param, which, optional=True):
    """
    getParam()
    input:
     - param (hash set): the set, which contains all parameters
     - which (lteral): the entry lookup
     - optional (boolean): defines if this parameter is optional or not
                 - an exception is thrown if the parameter is required
                 - otherwise: nothing done!

    return:
     - the value (literal) of the parameter if exists or nothing
       in case the parameter is optional, otherwise throw an exception
    """
    ret = None

    if param.has_key(which):
        ret = param[which]
    else:
        if (optional == False):
            raise ParameterError("Missing parameter: %r" % which, id=905)

    return ret

@log_with(log)
def getLowerParams(param):
    ret = {}
    for key in param:
        lkey = key.lower()
        # strip the session parameter!
        if "session" != lkey:
            lval = param[key]
            ret[lkey] = lval
    return ret


def getUserRealm(param, optional):
    user = ""
    realm = ""
    return (user, realm)


def uniquify(doubleList):
    # uniquify the realm list
    uniqueList = []
    for e in doubleList:
        if e.lower() not in uniqueList:
            uniqueList.append(e.lower())

    return uniqueList

def generate_otpkey(key_size=20):
    '''
    generates the HMAC key of keysize. Should be 20 or 32
    The key is returned as a hexlified string
    '''
    log.debug("generating key of size %s" % key_size)
    return binascii.hexlify(geturandom(key_size))


def generate_password(size=6, characters=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    return ''.join(urandom.choice(characters) for _x in range(size))


def check_session(request):
    '''
    This function checks the session cookie 
    
    '''
    res = True
    cookie = None
    session = None
    log.debug(request.path.lower())
    # GUI function get not passed the session key.
    if request.path.lower() in ["/manage", 
                                "/manage/", 
                                "/manage/custom-style.css",
                                "/selfservice/custom-style.css",
                                "/",
                                "/selfservice/",
                                "/selfservice/index",
                                "/manage/tokenview",
                                "/manage/userview",
                                "/manage/policies",
                                "/manage/audittrail",
                                "/manage/machines",
                                "/selfservice/load_form",
                                "/selfservice/assign",
                                "/selfservice/resync",
                                "/selfservice/reset",
                                "/selfservice/getotp",
                                "/selfservice/disable",
                                "/selfservice/enable",
                                "/selfservice/unassign",
                                "/selfservice/delete",
                                "/selfservice/setpin",
                                "/selfservice/setmpin",
                                "/selfservice/history",
                                "/selfservice/webprovisionoathtoken",
                                "/selfservice/activateqrtoken",
                                "/selfservice/webprovisiongoogletoken"                               
                                ]:
        log.info('nothing to check')
    else:
        if request.cookies.get('privacyidea_session') != None:
            try:
                cookie = request.cookies.get('privacyidea_session')[0:40]
                session = request.params.get('session')[0:40]
            except Exception as e:
                log.warning("failed to check selfservice session: %r" % e)
                res = False
            log.info("session: %s" % session)
            log.info("cookie:  %s" % cookie)
            if session is None or session != cookie:
                log.error("The request %s did not pass a valid session!" % request.url)
                res = False
    return res

def remove_session_from_param(param):
    '''
    Some low level functions like the userlisting do not like to have a
    session parameter in the param dictionary.
    So we remove the session from the params.
    '''
    return_param = {}
    for key in param.keys():
        if "session" != key.lower():
            return_param[key] = param[key]

    return return_param


#########################################################################################
# Client overwriting stuff
#

def get_client_from_request(request):
    '''
    This function returns the client as it is passed in the HTTP Request.
    This is the very HTTP client, that contacts the privacyIDEA server.
    '''
    client = "unknown"
    try:
        client = request.environ.get('REMOTE_ADDR', None)
        log.debug("got the client %s" % client)
    except Exception as exx:
        log.warning("%r" % exx)
    return client

@log_with(log)
def get_client_from_param(param):
    '''
    This function returns the client, that is passed with the GET/POST parameter "client"
    '''
    client = getParam(param, "client", optional)
    return client

def get_client():
    '''
    This function returns the client.

    It first tries to get the client as it is passed as the HTTP Client via REMOTE_ADDR.

    If this client Address is in a list, that is allowed to overwrite its client address (like e.g.
    a FreeRADIUS server, which will always pass the FreeRADIUS address but not the address of the
    RADIUS client) it checks for the existance of the client parameter.
    '''
    #FIXME pylons dependency!
    from pylons import request
    may_overwrite = []
    over_client = getFromConfig("mayOverwriteClient", "")
    log.debug("config entry mayOverwriteClient: %s" % over_client)
    try:
        may_overwrite = [ c.strip() for c in over_client.split(',') ]
    except Exception as e:
        log.warning("evaluating config entry 'mayOverwriteClient': %r" % e)

    client = get_client_from_request(request)
    log.debug("got the original client %s" % client)

    if client in may_overwrite or client == None:
        log.debug("client %s may overwrite!" % client)
        if get_client_from_param(request.params):
            client = get_client_from_param(request.params)
            log.debug("client overwritten to %s" % client)

    log.debug("returning %s" % client)
    return client

def normalize_activation_code(activationcode, upper=True, convert_o=True, convert_0=True):
    '''
    This normalizes the activation code.
    1. lower letters are capitaliezed
    2. Oh's in the last two characters are turned to zeros
    3. zeros in in the first-2 characters are turned to Ohs
    '''
    if upper:
        activationcode = activationcode.upper()
    if convert_o:
        activationcode = activationcode[:-2] + activationcode[-2:].replace("O", "0")
    if convert_0:
        activationcode = activationcode[:-2].replace("0", "O") + activationcode[-2:]

    return activationcode


def is_valid_fqdn(hostname, split_port=False):
    '''
    Checks if the hostname is a valid FQDN
    '''
    if split_port:
        hostname = hostname.split(':')[0]
    if len(hostname) > 255:
        return False
    if hostname[-1:] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def remove_empty_lines(doc):
    '''
        remove empty lines from the input document

        @param doc: documemt containing long multiline text
        @type  doc: string

        @return: data without empty lines
        @rtype:  string

    '''
    data = '\n'.join([line for line in doc.split('\n') if line.strip() != ''])
    return data

##
## Modhex calculations for Yubikey
##
hexHexChars = '0123456789abcdef'
modHexChars = 'cbdefghijklnrtuv'

hex2ModDict = dict(zip(hexHexChars, modHexChars))
mod2HexDict = dict(zip(modHexChars, hexHexChars))

def modhex_encode(s):
    return ''.join(
        [ hex2ModDict[c] for c in s.encode('hex') ]
    )
# end def modhex_encode

def modhex_decode(m):
    return ''.join(
        [ mod2HexDict[c] for c in m ]
    ).decode('hex')
# end def modhex_decode

def checksum(msg):
    crc = 0xffff;
    for i in range(0, len(msg) / 2):
        b = int(msg[i * 2] + msg[(i * 2) + 1], 16)
        crc = crc ^ (b & 0xff)
        for _j in range(0, 8):
            n = crc & 1
            crc = crc >> 1
            if n != 0:
                crc = crc ^ 0x8408
    return crc

########################## base token ##############################

def get_token_in_realm(realm, active=True):
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

####################################################################
