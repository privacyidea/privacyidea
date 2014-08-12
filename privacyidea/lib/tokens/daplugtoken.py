# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  Aug 12, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  based on the tokenclass.py base class of LinOTP which is
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
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
This is the token module for the daplug token. It behaves like HOTP,
but uses another OTP format/mapping.
'''
import binascii
from privacyidea.lib.tokens.hmactoken import HmacTokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.config import getFromConfig

optional = True
required = False

import logging
log = logging.getLogger(__name__)

MAPPING = {"b": "0",
           "c": "1",
           "d": "2",
           "e": "3",
           "f": "4",
           "g": "5",
           "h": "6",
           "i": "7",
           "j": "8",
           "k": "9"}
         
         
def _daplug2digit(daplug_otp):
    hex_otp = ""
    for i in daplug_otp:
        digit = MAPPING.get(i)
        hex_otp += digit
    otp = binascii.unhexlify(hex_otp)
    return otp
         
         
class DaplugTokenClass(HmacTokenClass):
    '''
    daplug token class implementation
    '''

    @classmethod
    def getClassType(cls):
        '''
        getClassType - return the token type shortname

        :return: 'daplug'
        :rtype: string

        '''
        return "daplug"

    @classmethod
    def getClassPrefix(cls):
        return "DPLG"

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
        res = {'type': 'daplug',
               'title': 'Daplug Event Token',
               'description': ("event based OTP token using "
                               "the HOTP algorithm"),
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def __init__(self, a_token):
        '''
        constructor - create a token object

        :param aToken: instance of the orm db object
        :type aToken:  orm object

        '''
        HmacTokenClass.__init__(self, a_token)
        self.setType(u"DAPLUG")
        self.hKeyRequired = True
        return

    @log_with(log)
    def checkOtp(self, anOtpVal, counter, window, options=None):
        '''
        checkOtp - validate the token otp against a given otpvalue

        :param anOtpVal: the otpvalue to be verified
        :type anOtpVal:  string, format: efekeiebekeh

        :param counter: the counter state, that should be verified
        :type counter: int

        :param window: the counter +window, which should be checked
        :type window: int

        :param options: the dict, which could contain token specific info
        :type options: dict

        :return: the counter state or -1
        :rtype: int

        '''
        # convert OTP value
        otp = _daplug2digit(anOtpVal)
        res = HmacTokenClass.checkOtp(self, otp, counter, window, options)
        return res

    @log_with(log)
    def check_otp_exist(self, otp, window=10):
        '''
        checks if the given OTP value is/are values of this very token.
        This is used to autoassign and to determine the serial number of
        a token.

        :param otp: the to be verified otp value
        :type otp: string

        :param window: the lookahead window for the counter
        :type window: int

        :return: counter or -1 if otp does not exist
        :rtype:  int

        '''
        otp = _daplug2digit(otp)
        res = HmacTokenClass.check_otp_exist(self, otp, window)
        return res

    @log_with(log)
    def autosync(self, hmac2Otp, anOtpVal):
        '''
        auto - sync the token based on two otp values
        - internal method to realize the autosync within the
        checkOtp method

        :param hmac2Otp: the hmac object (with reference to the token secret)
        :type hmac2Otp: hmac object

        :param anOtpVal: the actual otp value
        :type anOtpVal: string

        :return: counter or -1 if otp does not exist
        :rtype:  int

        '''
        otp = _daplug2digit(anOtpVal)
        res = HmacTokenClass.autosync(self, hmac2Otp, otp)
        return res

    @log_with(log)
    def resync(self, otp1, otp2, options=None):
        '''
        resync the token based on two otp values
        - external method to do the resync of the token

        :param otp1: the first otp value
        :type otp1: string

        :param otp2: the second otp value
        :type otp2: string

        :param options: optional token specific parameters
        :type options:  dict or None

        :return: counter or -1 if otp does not exist
        :rtype:  int

        '''
        n_otp1 = _daplug2digit(otp1)
        n_otp2 = _daplug2digit(otp2)
        res = HmacTokenClass.resync(self, n_otp1, n_otp2, options)
        return res

    def splitPinPass(self, passw):

        res = 0
        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError:
            otplen = 6

        # For splitting the value we use 12 characters.
        # For internal calculation we use 6 digits.
        otplen = otplen * 2
        
        if getFromConfig("PrependPin") == "True":
            pin = passw[0:-otplen]
            otpval = passw[-otplen:]
        else:
            pin = passw[otplen:]
            otpval = passw[0:otplen]

        return (res, pin, otpval)
