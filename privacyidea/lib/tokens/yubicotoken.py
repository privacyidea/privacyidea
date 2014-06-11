# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
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
  Description:  This file contains the definition of the yubikey token class
  
  Dependencies: -

'''

import logging

import traceback

from privacyidea.lib.util    import getParam
from privacyidea.lib.config import getFromConfig
from privacyidea.lib.log import log_with
from hashlib import sha1
import hmac
import urllib, urllib2
import re
import os
import binascii

YUBICO_LEN_ID = 12
YUBICO_LEN_OTP = 44
YUBICO_URL = "http://api.yubico.com/wsapi/2.0/verify"
DEFAULT_CLIENT_ID = 11759
DEFAULT_API_KEY = "P1QVTgnToQWQm0b6LREEhDIAbHU="

optional = True
required = False

from privacyidea.lib.tokenclass import TokenClass


log = logging.getLogger(__name__)

###############################################
class YubicoTokenClass(TokenClass):
    """
    The Yubico Cloud token forwards an authentication request to the Yubico Cloud service.
    """

    def __init__(self, aToken):
        TokenClass.__init__(self, aToken)
        self.setType(u"yubico")

        self.tokenid = ""


    @classmethod
    def getClassType(cls):
        return "yubico"

    @classmethod
    def getClassPrefix(cls):
        return "UBCM"

    @classmethod
    @log_with(log)
    def getClassInfo(cls, key=None, ret='all'):
        '''
        getClassInfo - returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string

        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype: s.o.

        '''
        res = {
               'type'           : 'yubico',
               'title'          : 'Yubico Token',
               'description'    : ('Yubico token to forward the authentication request to the Yubico Cloud authentication'),

               'init'         : {'page' : {'html'      : 'yubicotoken.mako',
                                            'scope'      : 'enroll', },
                                   'title'  : {'html'      : 'yubicotoken.mako',
                                             'scope'     : 'enroll.title', },
                                   },

               'config'        : { 'page' : {'html'      : 'yubicotoken.mako',
                                            'scope'      : 'config', },
                                   'title'  : {'html'      : 'yubicotoken.mako',
                                             'scope'     : 'config.title', },
                                 },
               'selfservice'   :  { 'enroll' :
                                   {'page' : {
                                              'html'       : 'yubicotoken.mako',
                                              'scope'      : 'selfservice.enroll', },
                                    'title'  : {
                                                'html'      : 'yubicotoken.mako',
                                                'scope'      : 'selfservice.title.enroll', },
                                    },
                                   },
               'policy' : {},
               }


        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret


    def update(self, param):

        tokenid = getParam(param, "yubico.tokenid", required)
        if len(tokenid) < YUBICO_LEN_ID:
            log.error("The tokenid needs to be %i characters long!" % YUBICO_LEN_ID)
            raise Exception("The Yubikey token ID needs to be %i characters long!" % YUBICO_LEN_ID)

        if len(tokenid) > YUBICO_LEN_ID:
            tokenid = tokenid[:YUBICO_LEN_ID]

        self.tokenid = tokenid
        self.setOtpLen(44)

        TokenClass.update(self, param)

        self.addToTokenInfo("yubico.tokenid", self.tokenid)

        return

    @log_with(log)
    def checkOtp(self, anOtpVal, counter, window, options=None):
        '''
        Here we contact the Yubico Cloud server to validate the OtpVal.
        '''
        res = -1

        apiId = getFromConfig("yubico.id", DEFAULT_CLIENT_ID)
        apiKey = getFromConfig("yubico.secret", DEFAULT_API_KEY)

        if apiKey == DEFAULT_API_KEY or apiId == DEFAULT_CLIENT_ID:
            log.warning("Usage of default apiKey or apiId not recomended!!")
            log.warning("Please register your own apiKey and apiId at "
                                                        "yubico website !!")
            log.warning("Configure of apiKey and apiId at the "
                                             "privacyidea manage config menue!!")

        tokenid = self.getFromTokenInfo("yubico.tokenid")
        if len(anOtpVal) < 12:
            log.warning("The otpval is too short: %r" % anOtpVal)

        elif anOtpVal[:12] != tokenid:
            log.warning("the tokenid in the OTP value does not match the assigned token!")

        else:
            nonce = binascii.hexlify(os.urandom(20))
            p = urllib.urlencode({'nonce': nonce,
                                    'otp':anOtpVal,
                                    'id':apiId})
            URL = "%s?%s" % (YUBICO_URL, p)
            try:
                f = urllib2.urlopen(urllib2.Request(URL))
                rv = f.read()
                m = re.search('\nstatus=(\w+)\r', rv)
                result = m.group(1)

                m = re.search('nonce=(\w+)\r', rv)
                return_nonce = m.group(1)

                m = re.search('h=(.+)\r', rv)
                return_hash = m.group(1)

                # check signature:
                elements = rv.split('\r')
                hash_elements = []
                for elem in elements:
                    elem = elem.strip('\n')
                    if elem and elem[:2] != "h=":
                        hash_elements.append(elem)

                hash_input = '&'.join(sorted(hash_elements))

                hashed_data = binascii.b2a_base64(hmac.new(
                                                           binascii.a2b_base64(apiKey),
                                                           hash_input,
                                                           sha1).digest())[:-1]

                if hashed_data != return_hash:
                    log.error("The hash of the return from the Yubico Cloud server does not match the data!")

                if nonce != return_nonce:
                    log.error("The returned nonce does not match the sent nonce!")

                if result == "OK" and nonce == return_nonce and hashed_data == return_hash:
                    res = 1
                else:
                    # possible results are listed here:
                    # https://github.com/Yubico/yubikey-val/wiki/ValidationProtocolV20
                    log.warning("failed with %r" % result)
            except Exception as ex:
                log.error("Error getting response from Yubico Cloud Server (%r): %r" % (URL, ex))
                log.error("%r" % traceback.format_exc())

        return res
