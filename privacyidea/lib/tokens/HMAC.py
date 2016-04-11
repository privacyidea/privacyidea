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
#  HMAC-OTP (RFC 4226)
#  Copyright (C) LSE Leading Security Experts GmbH, Weiterstadt
#  Written by Max Vozeler <max.vozeler@lsexperts.de>
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
"""
  Description:  HOTP basic functions
"""
  
import hmac
import logging
import struct
import binascii

from hashlib import sha1
from privacyidea.lib.log import log_with

import sys
(ma, mi, _, _, _,) = sys.version_info
pver = float(int(ma) + int(mi) * 0.1)


log = logging.getLogger(__name__)


class HmacOtp(object):

    def __init__(self, secObj=None, counter=0, digits=6, hashfunc=sha1):
        self.secretObj = secObj
        self.counter = int(counter)
        self.digits = digits
        self.hashfunc = hashfunc

    def hmac(self,
             counter=None,
             key=None,
             challenge=None):
        """

        :param counter:
        :param key:
        :param challenge: The datainput for OCRA
        :type challenge: hex string
        :return:
        """
        # log.error("hmacSecret()")
        if counter is None:
            counter = self.counter

        # When using a counter, we can only use 64bit as data_input.
        # When we allow a raw data_input, we could use 160bit or more.
        if not challenge:
            data_input = struct.pack(">Q", counter)
        else:
            data_input = binascii.unhexlify(challenge)

        if key is None:
            dig = str(self.secretObj.hmac_digest(data_input, self.hashfunc))
        else:
            if pver > 2.6:
                dig = hmac.new(key, data_input, self.hashfunc).digest()
            else:
                dig = hmac.new(key, str(data_input), self.hashfunc).digest()

        return dig

    def truncate(self, digest):
        offset = ord(digest[-1:]) & 0x0f

        binary = (ord(digest[offset + 0]) & 0x7f) << 24
        binary |= (ord(digest[offset + 1]) & 0xff) << 16
        binary |= (ord(digest[offset + 2]) & 0xff) << 8
        binary |= (ord(digest[offset + 3]) & 0xff)

        return binary % (10 ** self.digits)

    def generate(self,
                 counter=None,
                 inc_counter=True,
                 key=None,
                 do_truncation=True,
                 challenge=None):
        """

        :param counter:
        :param inc_counter:
        :param key:
        :param do_truncation:
        :param challenge: hexlified challenge
        :return:
        """
        if counter is None:
            counter = self.counter

        if challenge:
            hmac = self.hmac(challenge=challenge, key=key)
        else:
            hmac = self.hmac(counter=counter, key=key)
        if do_truncation:
            otp = str(self.truncate(hmac))
            """  fill in the leading zeros  """
            sotp = (self.digits - len(otp)) * "0" + otp
        else:
            sotp = binascii.hexlify(hmac)
            
        if inc_counter:
            self.counter = counter + 1
        return sotp

    @log_with(log)
    def checkOtp(self, anOtpVal, window, symetric=False):
        res = -1
        start = self.counter
        end = self.counter + window
        if symetric is True:
            # changed window/2 to window for TOTP
            start = self.counter - (window)
            start = 0 if (start < 0) else start
            end = self.counter + (window)

        log.debug("OTP range counter: {0!r} - {1!r}".format(start, end))
        for c in range(start, end):
            otpval = self.generate(c)
            log.debug("calculating counter {0!r}: {1!r} {2!r}".format(c, anOtpVal, otpval))

            if unicode(otpval) == unicode(anOtpVal):
                res = c
                break
        # return -1 or the counter
        return res
