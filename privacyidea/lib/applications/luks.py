# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  Jul 18, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
from privacyidea.lib.applications import MachineApplicationBase
import logging
log = logging.getLogger(__name__)
from privacyidea.lib.crypto import geturandom
import binascii
from privacyidea.lib.token import get_tokens


class MachineApplication(MachineApplicationBase):
    """
    This is the application for LUKS.

    required options:
        slot
        partition
    """
    application_name = "luks"

    @staticmethod
    def get_authentication_item(token_type,
                                serial,
                                challenge=None, options=None,
                                filter_param=None):
        """
        :param token_type: the type of the token. At the moment
                           we only support yubikeys, tokentype "TOTP".
        :param serial:     the serial number of the token.
                           The challenge response token needs to start with
                           "UBOM".
        :param challenge:  A challenge, for which a response get calculated.
                           If none is presented, we create one.
        :type challenge:   hex string
        :return auth_item: For Yubikey token type it
                           returns a dictionary with a "challenge" and
                           a "response".
        """
        ret = {}
        options = options or {}
        if token_type.lower() == "totp" and serial.startswith("UBOM"):
                # create a challenge of 32 byte
                # Although the yubikey is capable of doing 64byte challenges
                # the hmac module calculates different responses for 64 bytes.
                if challenge is None:
                    challenge = geturandom(32)
                    challenge_hex = binascii.hexlify(challenge)
                else:
                    challenge_hex = challenge
                ret["challenge"] = challenge_hex
                # create the response. We need to get
                # the HMAC key and calculate a HMAC response for
                # the challenge
                toks = get_tokens(serial=serial, active=True)
                if len(toks) == 1:
                    # tokenclass is a TimeHmacTokenClass
                    (_r, _p, otp, _c) = toks[0].get_otp(challenge=challenge_hex,
                                                        do_truncation=False)
                    ret["response"] = otp
        else:
                log.info("Token %r, type %r is not supported by"
                         "LUKS application module" % (serial, token_type))

        return ret

    @staticmethod
    def get_options():
        """
        returns a dictionary with a list of required and optional options
        """
        return {'required': [],
                'optional': ['slot', 'partition']}
