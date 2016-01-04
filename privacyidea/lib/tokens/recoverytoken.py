# -*- coding: utf-8 -*-
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2016-01-01 Cornelius Kölbel <cornelius@privacyidea.org>
#             Recovery token for password reset.
#             Creates recovery code.
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
This file contains the definition of the RegisterToken class.

The code is tested in test_lib_tokens_recovery.py.
"""

import logging
from privacyidea.lib.tokens.registrationtoken import RegistrationTokenClass
from privacyidea.lib.tokens.passwordtoken import PasswordTokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import generate_password
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.error import UserError

optional = True
required = False

log = logging.getLogger(__name__)


class RecoveryTokenClass(RegistrationTokenClass):
    """
    This token implemented the password recovery or password reset.
    A recoverycode is generated.
    This token can not be used for normal authentication!
    After this recovery code is
    used, the token is automatically deleted.
    """

    def __init__(self, aToken):
        RegistrationTokenClass.__init__(self, aToken)
        self.hKeyRequired = False
        self.set_type(u"recovery")

    @staticmethod
    def get_class_type():
        return "recovery"

    @staticmethod
    def get_class_prefix():
        return "REC"

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
        res = {'type': 'recovery',
               'title': 'Password Recovery Token',
               'description': ('Recovery: A token to create a recovery code '
                               'for password reset.'),
               'init': {},
               'config': {},
               'user':  [],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': [],
               'policy': {},
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    def update(self, param):
        """
        This method is called during the initialization process.

        At the end of initialization we send the recovery code via email.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
#        user_email = user.get_user_info().get("email")

        if "genkey" in param:
            # We do not need the genkey! We generate anyway.
            # Otherwise genkey and otpkey will raise an exception in
            # PasswordTokenClass
            del param["genkey"]
        param["otpkey"] = generate_password(size=self.otp_len)
        super(PasswordTokenClass, self).update(param)
        email = param.get("email")
        if not self.user:
            raise UserError("User required for recovery token.")
        user_email = self.user.get_user_info().get("email")
        if email and email.lower() != user_email.lower():
            raise UserError("The email does not match the users email.")

        # TODO: send email

    @log_with(log, log_entry=False)
    @check_token_locked
    def check_otp(self, anOtpVal, counter=None, window=None, options=None):
        """
        Normal authentication is not allowed with this token. Therfor we
        always fail the authentication

        :param anOtpVal:
        :param counter:
        :param window:
        :param options:
        :return:
        """
        return -1

    @log_with(log)
    def check_recovery_code(self, code):
        """
        Check if the recovery code matches
        :param code: The recovery code
        :return: Return 0 in case of success. -1 if fail
        """
        r = super(RegistrationTokenClass, self).check_otp(code)
        self.delete_token()
        return r
