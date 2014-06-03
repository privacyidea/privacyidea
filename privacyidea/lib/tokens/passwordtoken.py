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

'''
  Description:  This file contains the definition of the password token class
  
  Dependencies: -

'''

import logging
from privacyidea.lib.crypto   import zerome

from privacyidea.lib.log import log_with

optional = True
required = False

from privacyidea.lib.tokenclass import TokenClass

log = logging.getLogger(__name__)

###############################################
class PasswordTokenClass(TokenClass):
    '''
    This Token does use a fixed Password as the OTP value.
    In addition, the OTP PIN can be used with this token.
    This Token can be used for a scenario like losttoken
    '''

    class __secretPassword__(object):

        def __init__(self, secObj):
            self.secretObject = secObj

        def getPassword(self):
            return self.secretObject.getKey()

        def checkOtp(self, anOtpVal):
            res = -1

            key = self.secretObject.getKey()

            if key == anOtpVal:
                res = 0

            zerome(key)
            del key

            return res

    def __init__(self, aToken):
        TokenClass.__init__(self, aToken)
        self.hKeyRequired = True
        self.setType(u"pw")

    @classmethod
    def getClassType(cls):
        return "pw"

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
               'type'           : 'pw',
               'title'          : 'Password Token',
               'description'    : ('A token with a fixed password. Can be combined with the OTP PIN. Is used for the lost token scenario.'),
               'init'         : {},
               'config'        : {},
               'selfservice'   :  {},
               'policy' : {},
               }
        # I don't think we need to define the lost token policies here...

        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret



    def update(self, param):

        TokenClass.update(self, param)
        # The otplen is determined by the otpkey. So we
        # call the setOtpLen after the parents update, to overwrite
        # specified OTP lengths with the length of the password
        self.setOtpLen(0)

    @log_with(log)
    def setOtpLen(self, otplen):
        '''
        sets the OTP length to the length of the password
        '''
        secretHOtp = self.token.getHOtpKey()
        sp = PasswordTokenClass.__secretPassword__(secretHOtp)
        pw_len = len(sp.getPassword())
        TokenClass.setOtpLen(self, pw_len)
        return

    @log_with(log, log_entry=False)
    def checkOtp(self, anOtpVal, counter, window, options=None):
        '''
        This checks the static password
        '''
        log.debug("checkOtp of PasswordToken")

        secretHOtp = self.token.getHOtpKey()
        sp = PasswordTokenClass.__secretPassword__(secretHOtp)
        res = sp.checkOtp(anOtpVal)

        return res
