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
  It generates the URL for smartphone apps like
                google authenticator
                oath token
  Implementation inspired by:
      https://github.com/neush/otpn900/blob/master/src/test_motp.c
'''

import logging
import time

from hashlib import md5

from privacyidea.lib.utils import to_unicode, to_bytes
from privacyidea.lib.crypto import zerome
from privacyidea.lib.log import log_with


log = logging.getLogger(__name__)


class mTimeOtp(object):
    '''
    implements the motp timebased check_otp
    - s. https://github.com/neush/otpn900/blob/master/src/test_motp.c
    '''

    def __init__(self, secObj=None, secPin=None, oldtime=0, digits=6,
                 key=None, pin=None):
        '''
        constructor for the mOtp class
        
        :param secObj:    secretObject, which covers the encrypted secret
        :param secPin:    secretObject, which covers the encrypted pin
        :param oldtime:   the previously detected otp counter/time
        :param digits:    length of otp chars to be tested
        :param key:       direct key provider (for selfTest)
        :param pin:       direct pin provider (for selfTest)
        
        :return:          nothing
        '''
        self.secretObject = secObj
        self.key = key

        self.secPin = secPin
        self.pin = pin

        self.oldtime = oldtime  ## last time access
        self.digits = digits

    @log_with(log)
    def checkOtp(self, anOtpVal, window=10, options=None):
        '''
        check a provided otp value

        :param anOtpVal: the to be tested otp value
        :type anOtpVal: str
        :param window: the +/- window around the test time
        :param options: generic container for additional values \
                        here only used for seltest: setting the initTime

        :return: -1 for fail else the identified counter/time 
        '''
        res = -1
        window = window * 2

        initTime = 0
        if options is not None and type(options) == dict:
            initTime = int(options.get('initTime', 0))

        if initTime == 0:
            otime = int(time.time() // 10)
        else:
            otime = initTime

        if self.secretObject is None:
            key = self.key
            pin = self.pin
        else:
            key = self.secretObject.getKey()
            pin = self.secPin.getKey()

        for i in range(otime - window, otime + window):
            otp = self.calcOtp(i, to_unicode(key), to_unicode(pin))
            if anOtpVal == otp:
                res = i
                log.debug("otpvalue {0!r} found at: {1!r}".format(anOtpVal, res))
                break

        if self.secretObject is not None:
            zerome(key)
            zerome(pin)
            del key
            del pin

        ## prevent access twice with last motp
        if res <= self.oldtime:
            log.warning("otpvalue {0!s} checked once before ({1!r}<={2!r})".format(anOtpVal, res, self.oldtime))
            res = -1
        if res == -1:
            msg = 'checking motp failed'
        else:
            msg = 'checking motp sucess'

        log.debug("end. {0!s} : returning result: {1!r}, ".format(msg, res))
        return res

    def calcOtp(self, counter, key=None, pin=None):
        '''
        calculate an otp value from counter/time, key and pin
        
        :param counter:    counter/time to be checked
        :type counter:     int
        :param key:        the secret key
        :type key:         str
        :param pin:        the secret pin
        :type pin:         str
        
        :return:           the otp value
        :rtype:            str
        '''
        ## ref impl from https://github.com/szimszon/motpy/blob/master/motpy
        if pin is None:
            pin = self.pin
        if key is None:
            key = self.key

        vhash = u"{0:d}{1!s}{2!s}".format(counter, key, pin)
        motp = md5(to_bytes(vhash)).hexdigest()[:self.digits]
        return to_unicode(motp)
