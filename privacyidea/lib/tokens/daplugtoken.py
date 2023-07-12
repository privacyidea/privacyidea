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
#
#
#  based on the tokenclass.py base class of LinOTP which is
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
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
from privacyidea.lib.crypto import hexlify_and_unicode

__doc__ = """
This is the token module for the daplug token. It behaves like HOTP,
but uses another OTP format/mapping.

This code is tested in tests/test_lib_tokens_daplug
"""

import binascii
from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.config import get_prepend_pin
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.utils import to_bytes, to_unicode
from privacyidea.lib import _
from privacyidea.lib.policy import SCOPE, ACTION, GROUP
optional = True
required = False

import logging
log = logging.getLogger(__name__)

MAPPING = {"b": "0",
           "c": "1",
           "d": "2",
           "e": "3",
           "f": "4",
           "g": "5",
           "h": "6",
           "i": "7",
           "j": "8",
           "k": "9"}

REVERSE_MAPPING = {v: k for k, v in MAPPING.items()}


def _daplug2digit(daplug_otp):
    hex_otp = ""
    for i in daplug_otp:
        digit = MAPPING.get(i)
        hex_otp += digit
    # we know the result is a string of digits
    otp = to_unicode(binascii.unhexlify(hex_otp))
    return otp


def _digi2daplug(normal_otp):
    """
    convert "497096" to 34 39 37 30 39 36, which is efekeiebekeh

    This function is only used for testing purposes
    :param normal_otp:
    :type normal_otp: bytes or str
    :return:
    """
    daplug_otp = ""
    hex_otp = hexlify_and_unicode(to_bytes(normal_otp))
    for i in hex_otp:
        daplug_otp += REVERSE_MAPPING.get(i)
    return daplug_otp


class DaplugTokenClass(HotpTokenClass):
    """
    daplug token class implementation
    """
    # If the token is enrollable via multichallenge
    is_multichallenge_enrollable = False

    @staticmethod
    def get_class_type():
        return "daplug"

    @staticmethod
    def get_class_prefix():
        return "DPLG"

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
        :rtype: dict or string
        """
        res = {'type': 'daplug',
               'title': 'Daplug Event Token',
               'description': _("event based OTP token using "
                                "the HOTP algorithm"),
               'policy': {
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of daplug tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of active daplug tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   }}
               }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def __init__(self, a_token):
        """
        create a token object

        :param aToken: instance of the orm db object
        :type aToken:  orm object
        """
        HotpTokenClass.__init__(self, a_token)
        self.set_type("daplug")
        self.hKeyRequired = True
        return

    @log_with(log)
    @check_token_locked
    def check_otp(self, anOtpVal, counter=None, window=None, options=None):
        """
        checkOtp - validate the token otp against a given otpvalue

        :param anOtpVal: the otpvalue to be verified
        :type anOtpVal:  string, format: efekeiebekeh
        :param counter: the counter state, that should be verified
        :type counter: int
        :param window: the counter +window, which should be checked
        :type window: int
        :param options: the dict, which could contain token specific info
        :type options: dict
        :return: the counter state or -1
        :rtype: int

        """
        # convert OTP value
        otp = _daplug2digit(anOtpVal)
        res = HotpTokenClass.check_otp(self, otp, counter, window, options)
        return res

    @log_with(log)
    def check_otp_exist(self, otp, window=10):
        """
        checks if the given OTP value is/are values of this very token.
        This is used to autoassign and to determine the serial number of
        a token.

        :param otp: the to be verified otp value
        :type otp: string
        :param window: the lookahead window for the counter
        :type window: int
        :return: counter or -1 if otp does not exist
        :rtype:  int
        """
        otp = _daplug2digit(otp)
        res = HotpTokenClass.check_otp_exist(self, otp, window)
        return res

    @log_with(log)
    def get_otp(self, current_time=None):
        res = HotpTokenClass.get_otp(self, current_time)
        # returns (1, -1, '755224', '755224-1')
        return res[0], res[1], _digi2daplug(res[2]), res[3]


    @log_with(log)
    def get_multi_otp(self, count=0, epoch_start=0, epoch_end=0,
                        curTime=None, timestamp=None):
        res = HotpTokenClass.get_multi_otp(self, count=count,
                                           epoch_start=epoch_start,
                                           epoch_end=epoch_end,
                                           curTime=curTime, timestamp=timestamp)
        #  (True, 'OK', {'otp': {0: '755224', 1: '287082',
        #                        2: '359152', 3: '969429',
        #                        4: '338314'},
        #                'type': 'hotp'})
        # convert the response
        rdict = {'type': self.get_class_type(),
                 'otp': {}}
        otp_dict = {}
        for k, v in res[2].get('otp').items():
            rdict['otp'][k] = _digi2daplug(v)

        return res[0], res[1], rdict

    @log_with(log)
    def resync(self, otp1, otp2, options=None):
        """
        resync the token based on two otp values
        - external method to do the resync of the token

        :param otp1: the first otp value
        :type otp1: string
        :param otp2: the second otp value
        :type otp2: string
        :param options: optional token specific parameters
        :type options:  dict or None
        :return: counter or -1 if otp does not exist
        :rtype:  int
        """
        n_otp1 = _daplug2digit(otp1)
        n_otp2 = _daplug2digit(otp2)
        res = HotpTokenClass.resync(self, n_otp1, n_otp2, options)
        return res

    def split_pin_pass(self, passw, user=None, options=None):
        try:
            otplen = int(self.token.otplen)
        except ValueError:  # pragma: no cover
            otplen = 6

        # For splitting the value we use 12 characters.
        # For internal calculation we use 6 digits.
        otplen *= 2
        
        if get_prepend_pin():
            pin = passw[0:-otplen]
            otpval = passw[-otplen:]
        else:
            pin = passw[otplen:]
            otpval = passw[0:otplen]

        return len(passw) >= otplen, pin, otpval
