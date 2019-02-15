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
This file contains the definition of the tan token class
It depends on the DB model, and the lib.tokenclass.
"""

import logging
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.papertoken import PaperTokenClass
from privacyidea.lib.policy import SCOPE
from privacyidea.lib import _
from privacyidea.lib.policydecorators import libpolicy
from privacyidea.lib.crypto import geturandom, hash
import binascii

log = logging.getLogger(__name__)
DEFAULT_COUNT = 100
SALT_LENGTH = 4


class TANACTION(object):
    TANTOKEN_COUNT = "tantoken_count"


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
        if "tans" in param:
            # init tokens with tans
            tans = param.get("tans").split()
            tan_dict = {k: v for k, v in enumerate(tans)}
            # Avoid to generate TANs in the superclass PaperToken, since we get the tans from params
            param["papertoken_count"] = 0
            # Determine the otplen from the TANs
            if len(tans) > 0:
                param["otplen"] = len(tans[0])
            PaperTokenClass.update(self, param, reset_failcount=reset_failcount)
        else:
            # Init token without tans, so we create tans in the superclass PaperToken
            param["papertoken_count"] = param.get("tantoken_count") or DEFAULT_COUNT
            PaperTokenClass.update(self, param, reset_failcount=reset_failcount)
            # After this creation, the init_details contain the complete list of the TANs
            tan_dict = self.init_details.get("otps", {})
        for tankey, tanvalue in tan_dict.items():
            # Get a 4 byte salt from the crypto module
            salt = geturandom(SALT_LENGTH, hex=True)
            # Now we add all TANs to the tokeninfo of this token.
            hashed_tan = hash(tanvalue, salt)
            self.add_tokeninfo("tan.tan{0!s}".format(tankey),
                               "{0}:{1}".format(salt, hashed_tan))

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
        for tankey, tanvalue in tans.items():
            if tankey.startswith("tan.tan"):
                salt, tan = tanvalue.split(":")
                if tan == hash(anOtpVal, salt):
                    self.del_tokeninfo(tankey)
                    return 1

        return res

    @staticmethod
    def get_import_csv(l):
        """
        Read the list from a csv file and return a dictionary, that can be used
        to do a token_init.

        :param l: The list of the line of a csv file
        :type l: list
        :return: A dictionary of init params
        """
        params = TokenClass.get_import_csv(l)
        # Delete the otplen, if it exists. The fourth column is the TANs!
        if "otplen" in params:
            del params["otplen"]

        # tans
        if len(l) >= 4:
            params["tans"] = l[3]

        return params

    def get_as_dict(self):
        """
        This returns the token data as a dictionary.
        It is used to display the token list at /token/list.

        The TAN token class removes the tan.tanXX information and
        only returns the number of remaining tans.

        :return: The token data as dict
        :rtype: dict
        """
        # first get the database values as dict
        token_dict = self.token.get()

        if "info" in token_dict:
            tan_count = 0
            filtered_info = {}
            for infokey, infovalue in token_dict["info"].items():
                if infokey.startswith("tan.tan"):
                    tan_count += 1
                else:
                    filtered_info[infokey] = infovalue
            filtered_info["tan.count"] = tan_count
            token_dict["info"] = filtered_info

        return token_dict