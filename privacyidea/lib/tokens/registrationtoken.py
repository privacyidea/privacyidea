# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  Aug 12, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2015-01-29 Adapt during migration to flask
#             Cornelius Kölbel <cornelius@privacyidea.org>
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

The code is tested in test_lib_tokens_registration.py.
"""

import logging
from privacyidea.lib.tokens.passwordtoken import PasswordTokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import generate_password
from privacyidea.lib.decorators import check_token_locked

optional = True
required = False

log = logging.getLogger(__name__)


class RegistrationTokenClass(PasswordTokenClass):
    """
    Token to implement a registration code.
    It can be used to create a registration code or a "TAN" which can be used
    once by a user to authenticate somewhere. After this registration code is
    used, the token is automatically deleted.

    The idea is to provide a workflow, where the user can get a registration code
    by e.g. postal mail and then use this code as the initial first factor to
    authenticate to the UI to enroll real tokens.

    A registration code can be created by an administrative task with the
    token/init api like this:

      **Example Authentication Request**:

        .. sourcecode:: http

           POST /token/init HTTP/1.1
           Host: example.com
           Accept: application/json

           type=register
           user=cornelius
           realm=realm1

      **Example response**:

           .. sourcecode:: http

               HTTP/1.1 200 OK
               Content-Type: application/json

               {
                  "detail": {
                    "registrationcode": "12345808124095097608"
                  },
                  "id": 1,
                  "jsonrpc": "2.0",
                  "result": {
                    "status": true,
                    "value": true
                  },
                  "version": "privacyIDEA unknown"
                }

    """

    def __init__(self, aToken):
        PasswordTokenClass.__init__(self, aToken)
        self.hKeyRequired = False
        self.set_type(u"registration")
        self.otp_len = 24

    @staticmethod
    def get_class_type():
        return "registration"

    @staticmethod
    def get_class_prefix():
        return "REG"

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
        res = {'type': 'registration',
               'title': 'Registration Code Token',
               'description': ('Registration: A token that creates a '
                               'registration code that '
                               'can be used as a second factor once.'),
               'init': {},
               'config': {},
               'user':  [],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin"],
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
        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        if "genkey" in param:
            # We do not need the genkey! We generate anyway.
            # Otherwise genkey and otpkey will raise an exception in
            # PasswordTokenClass
            del param["genkey"]
        param["otpkey"] = generate_password(size=self.otp_len)
        PasswordTokenClass.update(self, param)

    @log_with(log, log_entry=False)
    @check_token_locked
    def inc_count_auth_success(self):
        """
        Increase the counter, that counts successful authentications
        In case of successful authentication the token does needs to be deleted.
        """
        self.delete_token()
        return 1

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we return the registration code.
        """
        response_detail = PasswordTokenClass.get_init_detail(self, params, user)
        params = params or {}
        secretHOtp = self.token.get_otpkey()
        registrationcode = secretHOtp.getKey()
        response_detail["registrationcode"] = registrationcode
        return response_detail
