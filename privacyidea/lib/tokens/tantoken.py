# -*- coding: utf-8 -*-
#
#  2018-05-09 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             TAN token with to be randomly used TAN values
#
#  (c) 2018 Cornelius Kölbel - cornelius.koelbel@netknights.it
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
from privacyidea.lib.tokens.papertoken import PaperTokenClass
from privacyidea.lib.policy import SCOPE
from privacyidea.lib import _
from privacyidea.lib.policydecorators import libpolicy

log = logging.getLogger(__name__)
DEFAULT_COUNT = 100


class TANACTION(object):
    TANTOKEN_COUNT = "papertoken_count"


class TanTokenClass(PaperTokenClass):
    """
    The TAN token allows to print out the next e.g. 100 OTP values.
    This sheet of paper can be used to authenticate and strike out the used
    OTP values. In contrast to the paper token, the OTP values of the TAN token
    can be used randomly.
    """

    @log_with(log)
    def __init__(self, db_token):
        """
        This creates a new TAN token object from a DB token object.

        :param db_token: instance of the orm db object
        :type db_token:  orm object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"tan")
        self.hKeyRequired = False

    @staticmethod
    def get_class_type():
        """
        return the token type shortname

        :return: 'paper'
        :rtype: string
        """
        return "tan"

    @staticmethod
    def get_class_prefix():
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: PITN
        """
        return "PITN"

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
        res = {'type': 'tan',
               'title': 'TAN Token',
               'description': 'TAN: TANs printed on a sheet '
                              'of paper.',
               'init': {},
               'config': {},
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ENROLL: {
                       TANACTION.TANTOKEN_COUNT: {
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
        param["papertoken_count"] = param.get("tantoken_count") or DEFAULT_COUNT
        PaperTokenClass.update(self, param, reset_failcount=reset_failcount)
        # After this creation, the init_details contain the complete list of the TANs
        # TODO: create a salt, save it to otpkey and hash the tans.
        for tankey, tanvalue in self.init_details.get("otps", {}).iteritems():
            # Now we add all TANs to the tokeninfo of this token.
            self.add_tokeninfo("tan.tan{0!s}".format(tankey), tanvalue)

    def check_otp(self, anOtpVal, counter=None, window=None, options=None):
        """
        check if the given OTP value is valid for this token.

        :param anOtpVal: the to be verified otpvalue
        :type anOtpVal: string
        :param counter: the counter state, that should be verified
        :type counter: int
        :param window: the counter +window, which should be checked
        :type window: int
        :param options: the dict, which could contain token specific info
        :type options: dict
        :return: the counter state or -1
        :rtype: int
        """
        res = -1
        tans = self.get_tokeninfo()
        for tankey, tanvalue in tans.iteritems():
            if tankey.startswith("tan.tan") and tanvalue == anOtpVal:
                self.del_tokeninfo(tankey)
                return 1

        return res