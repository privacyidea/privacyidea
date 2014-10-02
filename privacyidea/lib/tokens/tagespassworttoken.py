# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2014-10-02 Added the dpwOtp class from lib/dpwotp.py
#             Cornelius Kölbel, <cornelius@privacyidea.org>
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
This file contains the definition of the tagespasswort token class
'''
from privacyidea.lib.util import getParam
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.config import getFromConfig
from privacyidea.lib.error import TokenAdminError
from hashlib import md5
from datetime import (datetime,
                      timedelta)
from binascii import hexlify

from privacyidea.lib.crypto import zerome

import logging
log = logging.getLogger(__name__)
optional = True
required = False


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
        input_data = key + date_string

        md = hexlify(md5(input_data).digest())
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

        if date_string is None:
            date_string = datetime.now().strftime("%d%m%y")

        input_data = key + date_string

        md = hexlify(md5(input_data).digest())
        md = md[len(md) - self.digits:]
        otp = int(md, 16)
        otp = unicode(otp)
        otp = otp[len(otp) - self.digits:]

        zerome(key)
        del key

        return otp


###############################################
class TagespasswortTokenClass(TokenClass):
    '''
    The Tagespasswort is a one time password that is calculated based on the
    day input.
    '''

    def __init__(self, aToken):
        TokenClass.__init__(self, aToken)
        self.setType(u"DPW")

        self.hKeyRequired = True

    @classmethod
    def getClassType(cls):
        return "dpw"

    @classmethod
    def getClassPrefix(cls):
        return "DOTP"

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
        res = {'type': 'dpw',
               'title': 'Tagespasswort Token',
               'description': ('A token uses a new password every day.'),
               'init': {'page': {'html': 'tagespassworttoken.mako',
                                 'scope': 'enroll', },
                        'title': {'html': 'tagespassworttoken.mako',
                                  'scope': 'enroll.title', },
                        },
               'config': {},
               'selfservice': {},
               'policy': {},
               }
        # I don't think we need to define the lost token policies here...

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    def update(self, param):

        # check for the required parameters
        if (self.hKeyRequired is True):
            getParam(param, "otpkey", required)

        TokenClass.update(self, param)

    def reset(self):
        TokenClass.reset(self)

    @log_with(log)
    def checkOtp(self, anOtpVal, counter, window, options=None):
        res = -1

        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError:
            return res

        secretHOtp = self.token.getHOtpKey()

        dpw = dpwOtp(secretHOtp, otplen)
        res = dpw.checkOtp(anOtpVal, window=window)

        return res

    @log_with(log)
    def getOtp(self, curTime=None):
        # kay: init value
        res = (-1, 0, 0, 0)

        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError:
            return res

        secretHOtp = self.token.getHOtpKey()

        dpw = dpwOtp(secretHOtp, otplen)

        date_string = None
        if curTime:
            if type(curTime) == datetime:
                date_string = curTime.strftime("%d%m%y")
            elif type(curTime) == unicode:
                date_string = datetime.strptime(curTime,
                                                "%Y-%m-%d %H:%M:%S.%f"
                                                ).strftime("%d%m%y")
            else:
                log.error("invalid curTime: %r. "
                          "You need to specify a datetime" % type(curTime))
        otpval = dpw.getOtp(date_string)
        pin = self.token.getPin()
        combined = "%s%s" % (otpval, pin)
        if getFromConfig("PrependPin") == "True":
            combined = "%s%s" % (pin, otpval)

        return (1, pin, otpval, combined)

    @log_with(log)
    def get_multi_otp(self, count=0, epoch_start=0, epoch_end=0,
                      curTime=None, timestamp=None):
        '''
        This returns a dictionary of multiple future OTP values of the
        Tagespasswort token

        parameter
            count    - how many otp values should be returned
            epoch_start    - time based tokens: start when
            epoch_end      - time based tokens: stop when

        return
            True/False
            error text
            OTP dictionary
        '''
        otp_dict = {"type": "DPW", "otp": {}}
        ret = False
        error = "No count specified"
        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError as ex:
            log.error("%r" % ex)
            return (False, unicode(ex), otp_dict)

        secretHOtp = self.token.getHOtpKey()
        dpw = dpwOtp(secretHOtp, otplen)
        log.debug("retrieving %i OTP values for token %s" % (count, dpw))

        if count > 0:
            now = datetime.now()
            if curTime:
                if type(curTime) == datetime:
                    now = curTime
                elif type(curTime) == unicode:
                    now = datetime.strptime(curTime, "%Y-%m-%d %H:%M:%S.%f")
                else:
                    log.error("wrong curTime type: %s" % type(curTime))
                    raise TokenAdminError("[get_multi_otp] wrong curTime type:"
                                          " %s (%s)" %
                                          (type(curTime), curTime), id=2001)
            for i in range(count):
                delta = timedelta(days=i)
                date_string = (now + delta).strftime("%d%m%y")
                otpval = dpw.getOtp(date_string=date_string)
                otp_dict["otp"][(now + delta).strftime("%y-%m-%d")] = otpval
            ret = True

        return (ret, error, otp_dict)
