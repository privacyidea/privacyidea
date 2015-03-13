# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  2015-03-13 Cornelius Kölbel, <cornelius@privacyidea.org>
#             initial writeup
#
# License:  AGPLv3
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
from privacyidea.lib.crypto import salted_hash_256
from privacyidea.lib.token import get_tokens


class MachineApplication(MachineApplicationBase):
    """
    This is the application for Offline authentication with PAM or
    the privacyIDEA credential provider.

    The machine application returns a list of salted OTP hashes to be used with
    offline authentication. The token then is disabled, so that it can not
    be used for online authentication anymore, to avoid reusing a fished OTP
    value.

    The server stores the information, which OTP values were issued.

    required options:
        user

    """
    application_name = "offline"

    @classmethod
    def get_authentication_item(cls,
                                token_type,
                                serial,
                                challenge=None):
        """
        :param token_type: the type of the token. At the moment
                           we only support "HOTP" token. Supporting time
                           based tokens is difficult, since we would have to
                           return a looooong list of OTP values.
                           Supporting "yubikey" token (AES) would be
                           possible, too.
        :param serial:     the serial number of the token.
        :param challenge:  n/a
        :type challenge:   hex string
        :return auth_item: A list of hashed OTP values
        """
        ret = {}
        if token_type.lower() == "hotp":
            # TODO: make this configurable
            count = 100
            # get the token
            toks = get_tokens(serial=serial)
            if len(toks) == 1:
                (res, err, otp_dict) = toks[0].get_multi_otp(count=count)
                otps = otp_dict.get("otp")
                for key in otps.keys():
                    otps[key] = salted_hash_256(otps.get(key))
                ret["response"] = otps

        else:
            log.info("Token %r, type %r is not supported by"
                     "OFFLINE application module" % (serial, token_type))

        return ret

    @classmethod
    def get_options(cls):
        """
        returns a dictionary with a list of required and optional options
        """
        return {'required': [],
                'optional': ['user', 'count']}
