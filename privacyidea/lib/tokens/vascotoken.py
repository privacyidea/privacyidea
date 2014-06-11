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
  Description:  This file contains the definition of the VASCO token class
              The vasco library is need to run correctly
              It will not do so at the moment!
  
  Dependencies: -

'''

from privacyidea.lib.util    import getParam
from pylons.i18n.translation import _
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
try:
    from privacyideaee.lib.ImportOTP.vasco import vasco_otp_check
    from privacyideaee.lib.ImportOTP.vasco import compress
    from privacyideaee.lib.ImportOTP.vasco import decompress
    VASCO = True
except ImportError:
    VASCO = False

import logging
log = logging.getLogger(__name__)

optional = True
required = False

###############################################
class VascoTokenClass(TokenClass):

    def __init__(self, aToken):
        TokenClass.__init__(self, aToken)
        self.setType(u"vasco")
        self.hKeyRequired = True

    @classmethod
    def getClassType(cls):
        '''
        return the generic token class identifier
        '''
        return "vasco"

    @classmethod
    def getClassPrefix(cls):
        return "vasco"

    @classmethod
    def getClassInfo(cls, key=None, ret='all'):
        '''
        getClassInfo - returns all or a subtree of the token definition

        :param key: subsection identifier
        :type key: string

        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype : s.o.

        '''

        res = {
               'type' : 'vasco',
               'title' : _('Vasco Token'),
               'description' :
                    _('Vasco Digipass Token Class - proprietary timebased tokens'),
               'init'         : {},
               'config'         : {},
               'selfservice'   :  {},
        }

        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    def update(self, param):

        ## check for the required parameters
        if (self.hKeyRequired == True):
            getParam(param, "otpkey", required)

        TokenClass.update(self, param, reset_failcount=False)

        for key in ["vasco_appl", "vasco_type", "vasco_auth"]:
            val = getParam(param, key, optional)
            if val is not None:
                self.addToTokenInfo(key, val)


    def reset(self):
        TokenClass.reset(self)

    def check_otp_exist(self, otp, window=10):
        '''
        checks if the given OTP value is/are values of this very token.
        This is used to autoassign and to determine the serial number of
        a token.

        :param otp: The OTP value to search for
        :type otp: string
        :param window: In how many future OTP values the given OTP value should be searched
        :type window: int

        :return: tuple of the result value and the data itself
        '''
        res = self.checkOtp(otp, 0, window)

        return res

    @log_with(log)
    def checkOtp(self, anOtpVal, counter, window, options=None):
        '''
        Checks if the OTP value is valid.

        Therefore the vasco data blob is fetched from the database and this very
        blob and the otp value is passed to the vasco function vasco_otp_check.

        After that the modified vasco blob needs to be stored (updated) in the
        database again.
        '''
        res = -1

        if VASCO:
            secObject = self.token.getHOtpKey()
            otpkey = secObject.getKey()
            data = decompress(otpkey)
            # let vasco handle the OTP checking
            (res, data) = vasco_otp_check(data, anOtpVal)
            # update the vasco data blob
            self.update({"otpkey" : compress(data)})
        else:
            log.warning("Trying to validate a vasco token, but the module is not loaded!")

        if res != 0:
            log.warning("Vasco token failed to authenticate. Vasco Error code: %d" % res)
            # TODO: Vasco gives much more detailed error codes. But at the moment we do not handle more error codes!
            res = -1

        return res
