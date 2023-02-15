# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2015-01-27 Rewrite due to flask migration
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
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
__doc__="""This is the implementation of the simple pass token.
The simple pass token always returns TRUE as far as the checkOTP is concerned.
Thus a user with a simple pass token can authenticate by just providing the
OTP PIN of the token.

This code is tested in tests/test_lib_tokens_spass
"""

import logging
from privacyidea.lib import _
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass, AUTHENTICATIONMODE
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.policy import SCOPE, ACTION, GROUP

optional = True
required = False

log = logging.getLogger(__name__)


class SpassTokenClass(TokenClass):
    """
    This is a simple pass token.
    It does have no OTP component. The OTP checking will always
    succeed. Of course, an OTP PIN can be used.
    """
    mode = [AUTHENTICATIONMODE.AUTHENTICATE]

    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type("spass")

    @staticmethod
    def get_class_type():
        return "spass"

    @staticmethod
    def get_class_prefix():
        return "PISP"

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        returns a subtree of the token definition
        Is used by lib.token.get_token_info

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict
        """
        res = {'type' :'spass',
               'title' :'Simple Pass Token',
               'description': _('SPass: Simple Pass token. Static passwords.'),
               'config': {},
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               # SPASS token can have specific PIN policies in the scopes
               # admin and user
               'pin_scopes': [SCOPE.ADMIN, SCOPE.USER],
               'policy': {
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of SPASS tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _(
                               "The user may only have this maximum number of active SPASS tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   }
               }
               }

        # do we need to define the lost token policies here...
        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res
        return ret

    def update(self, param):
        if 'otpkey' not in param:
            param['genkey'] = 1

        TokenClass.update(self, param)

    @staticmethod
    def is_challenge_request(passw, user, options=None):
        """
        The spass token does not support challenge response
        :param passw:
        :param user:
        :param options:
        :return:
        """
        return False  # pragma: no cover

    @staticmethod
    def is_challenge_response(passw, user, options=None, challenges=None):
        return False  # pragma: no cover

    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        As we have no otp value we always return true. (counter == 0)
        """
        return 0

    @log_with(log)
    @check_token_locked
    def authenticate(self, passw, user=None, options=None):
        """
        in case of a wrong passw, we return a bad matching pin,
        so the result will be an invalid token
        """
        otp_count = -1
        pin_match = self.check_pin(passw, user=user, options=options)
        if pin_match is True:
            otp_count = 0
        return pin_match, otp_count, None

