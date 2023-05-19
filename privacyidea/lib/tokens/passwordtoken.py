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

from privacyidea.lib.crypto import zerome, safe_compare
from privacyidea.lib.utils import to_unicode
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib import _
from privacyidea.lib.policy import SCOPE, ACTION, GROUP
from privacyidea.api.lib.prepolicy import _generate_pin_from_policy
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.utils import is_true

optional = True
required = False

# We use an easier length of 12 for password tokens
DEFAULT_LENGTH = 12
DEFAULT_CONTENTS = 'cn'

log = logging.getLogger(__name__)


class PasswordTokenClass(TokenClass):
    """
    This Token does use a fixed Password as the OTP value.
    In addition, the OTP PIN can be used with this token.
    This Token can be used for a scenario like losttoken
    """

    password_detail_key = "password"  # nosec B105 # key name
    default_length = DEFAULT_LENGTH
    default_contents = DEFAULT_CONTENTS

    class SecretPassword(object):

        def __init__(self, secObj):
            self.secretObject = secObj

        def get_password(self):
            return self.secretObject.getKey()

        def check_password(self, password):
            """

            :param password:
            :type password: str
            :return: result of password check: 0 if success, -1 if failed
            :rtype: int
            """
            res = -1

            key = self.secretObject.getKey()
            # getKey() returns bytes and since we can not assume, that the
            # password only contains printable characters, we need to compare
            # bytes strings here. This also avoids making another copy of 'key'.
            if safe_compare(key, password):
                res = 0

            zerome(key)
            del key

            return res

    def __init__(self, aToken):
        TokenClass.__init__(self, aToken)
        self.otp_len = self.default_length
        self.otp_contents = self.default_contents
        self.hKeyRequired = True
        self.set_type("pw")

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
               'policy': {
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of password tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of active password tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   }
               },
               }
        # I don't think we need to define the lost token policies here...

        if key:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log, log_entry=False)
    def update(self, param):
        """
        This method is called during the initialization process.
        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        genkey = is_true(getParam(param, "genkey", optional=True))
        if genkey:
            # Otherwise genkey and otpkey will raise an exception in
            # PasswordTokenClass
            del param["genkey"]
            type_prefix = self.get_class_type()
            length_param = "{0!s}.length".format(type_prefix)
            contents_param = "{0!s}.contents".format(type_prefix)
            if length_param in param:
                size = param[length_param]
                del param[length_param]
            else:
                size = self.otp_len
            if contents_param in param:
                contents = param[contents_param]
                del param[contents_param]
            else:
                contents = self.otp_contents
            param["otpkey"] = _generate_pin_from_policy(contents, size=int(size))
        if "otpkey" in param:
            param["otplen"] = len(param["otpkey"])
        TokenClass.update(self, param)

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

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we return the registration code.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        secretHOtp = self.token.get_otpkey()
        password = secretHOtp.getKey()
        response_detail[self.password_detail_key] = to_unicode(password)
        return response_detail
