# -*- coding: utf-8 -*-
#
#  2016-12-05 Cornelisu Kölbel <cornelius.koelbel@netknights.it>
#             Add policy papertoken_count
#
#  2015-11-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             initial write
#  (c) 2015 Cornelius Kölbel - cornelius@privacyidea.org
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
This file contains the definition of the paper token class
It depends on the DB model, and the lib.tokenclass.
"""

import logging
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.lib.policy import SCOPE
from privacyidea.lib import _
from privacyidea.lib.policydecorators import libpolicy

log = logging.getLogger(__name__)
DEFAULT_COUNT = 100


class PAPERACTION(object):
    PAPERTOKEN_COUNT = "papertoken_count"


class PaperTokenClass(HotpTokenClass):

    """
    The Paper Token allows to print out the next e.g. 100 OTP values.
    This sheet of paper can be used to authenticate and strike out the used
    OTP values.
    """

    @log_with(log)
    def __init__(self, db_token):
        """
        This creates a new Paper token object from a DB token object.

        :param db_token: instance of the orm db object
        :type db_token:  orm object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"paper")
        self.hKeyRequired = False

    @staticmethod
    def get_class_type():
        """
        return the token type shortname

        :return: 'paper'
        :rtype: string
        """
        return "paper"

    @staticmethod
    def get_class_prefix():
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: PPR
        """
        return "PPR"

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
        res = {'type': 'paper',
               'title': 'Paper Token',
               'description': 'PPR: One Time Passwords printed on a sheet '
                              'of paper.',
               'init': {},
               'config': {},
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ENROLL: {
                       PAPERACTION.PAPERTOKEN_COUNT: {
                           "type": "int",
                           "desc": _("The number of OTP values, which are "
                                     "printed on the paper.")
                       }
                   }
               }
               }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res
        return ret

    def update(self, param, reset_failcount=True):
        if "otpkey" not in param:
            param["genkey"] = 1
        HotpTokenClass.update(self, param, reset_failcount=reset_failcount)
        papertoken_count = int(param.get("papertoken_count", DEFAULT_COUNT))
        # Now we calculate all the OTP values and add them to the
        # init_details. Thus they will be returned by token/init.
        otps = self.get_multi_otp(count=papertoken_count)
        self.add_init_details("otps", otps[2].get("otp", {}))
