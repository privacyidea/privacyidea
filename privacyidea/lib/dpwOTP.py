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
                     
'''contains base functions for calculating tagespasswort.'''
#FIXME: should be moved to the token definition


from hashlib import md5
from datetime import datetime
from binascii import hexlify

from privacyidea.lib.crypto import zerome

import logging
log = logging.getLogger(__name__)





class dpwOtp:

    def __init__(self, secObj, digits=6):
        self.secretObject = secObj
        self.digits = digits

    def checkOtp(self, anOtpVal, window=0, options=None):
        '''
        window is the seconds before and after the current time
        '''
        res = -1

        key = self.secretObject.getKey()

        date_string = datetime.now().strftime("%d%m%y")
        input = key + date_string

        md = hexlify(md5(input).digest())
        md = md[len(md) - self.digits:]
        otp = int(md, 16)
        otp = unicode(otp)
        otp = otp[len(otp) - self.digits:]

        if unicode(anOtpVal) == otp:
            res = 1

        zerome(key)
        del key

        return res

    def getOtp(self, date_string=None):

        key = self.secretObject.getKey()

        if date_string == None:
            date_string = datetime.now().strftime("%d%m%y")

        input = key + date_string

        md = hexlify(md5(input).digest())
        md = md[len(md) - self.digits:]
        otp = int(md, 16)
        otp = unicode(otp)
        otp = otp[len(otp) - self.digits:]

        zerome(key)
        del key

        return otp
