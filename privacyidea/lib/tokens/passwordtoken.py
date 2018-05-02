# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  2014-12-05 Cornelius Kölbel <cornelius@privacyidea.org>
#             Migration to flask
#
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de

"""
This file contains the definition of the password token class
"""

import logging
from privacyidea.lib.crypto import zerome
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib import _

optional = True
required = False

log = logging.getLogger(__name__)


class PasswordTokenClass(TokenClass):
    """
    This Token does use a fixed Password as the OTP value.
    In addition, the OTP PIN can be used with this token.
    This Token can be used for a scenario like losttoken
    """

    class SecretPassword(object):

        def __init__(self, secObj):
            self.secretObject = secObj

        def get_password(self):
            return self.secretObject.getKey()

        def check_password(self, password):
            res = -1

            key = self.secretObject.getKey()

            if key == password:
                res = 0

            zerome(key)
            del key

            return res

    def __init__(self, aToken):
        TokenClass.__init__(self, aToken)
        self.hKeyRequired = True
        self.set_type(u"pw")

    @staticmethod
    def get_class_type():
        return "pw"

    @staticmethod
    def get_class_prefix():
        return "PW"

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict or scalar
        """
        res = {'type': 'pw',
               'title': 'Password Token',
               'description': _('A token with a fixed password. Can be '
                                'combined  with the OTP PIN. Is used for the '
                                'lost token scenario.'),
               'init': {},
               'config': {},
               'user':  [],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': [],
               'policy': {},
               }
        # I don't think we need to define the lost token policies here...

        if key:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    def update(self, param):
        """
        This method is called during the initialization process.
        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        """
        :param param:
        :return:
        """
        TokenClass.update(self, param)
        self.set_otplen()

    @log_with(log)
    @check_token_locked
    def set_otplen(self, otplen=0):
        """
        sets the OTP length to the length of the password

        :param otplen: This is ignored in this class
        :type otplen: int
        :result: None
        """
        secretHOtp = self.token.get_otpkey()
        sp = PasswordTokenClass.SecretPassword(secretHOtp)
        pw_len = len(sp.get_password())
        TokenClass.set_otplen(self, pw_len)
        return

    @log_with(log, log_entry=False)
    @check_token_locked
    def check_otp(self, anOtpVal, counter=None, window=None, options=None):
        """
        This checks the static password

        :param anOtpVal: This contains the "OTP" value, which is the static
        password
        :return: result of password check, 0 in case of success, -1 if fail
        :rtype: int
        """
        secretHOtp = self.token.get_otpkey()
        sp = PasswordTokenClass.SecretPassword(secretHOtp)
        res = sp.check_password(anOtpVal)

        return res
