# -*- coding: utf-8 -*-
#
#  2015-04-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add options ROUNDS to avoid timeouts during OTP hash calculation
#  2015-04-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Use pbkdf2 for OTP hashing
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
from privacyidea.lib.crypto import geturandom
import logging
import passlib.hash
from privacyidea.lib.token import get_tokens
log = logging.getLogger(__name__)
ROUNDS = 6549
REFILLTOKEN_LENGTH = 40


class MachineApplication(MachineApplicationBase):
    """
    This is the application for Offline authentication with PAM or
    the privacyIDEA credential provider.

    The machine application returns a list of salted OTP hashes to be used with
    offline authentication. The token then is disabled, so that it can not
    be used for online authentication anymore, to avoid reusing a fished OTP
    value.

    The server stores the information, which OTP values were issued.

    options options:
      * user: a username.
      * count: is the number of OTP values returned

    """
    application_name = "offline"

    @staticmethod
    def get_refill(serial, password, options=None, first_fill=False):
        """
        Returns new authentication items to refill the client

        To do so we also verify the password, which may consist of PIN + OTP

        :param serial:
        :param password:
        :param options: dict that might contain "count"
        :return: tuple of refilltoken and auth_items
        """
        otps = []
        count = int(options.get("count", 100))
        rounds = int(options.get("rounds", ROUNDS))
        new_refilltoken = geturandom(REFILLTOKEN_LENGTH, hex=True)
        toks = get_tokens(serial=serial)
        if len(toks) == 1:
            token_obj = toks[0]
            _r, otppin, otpval = token_obj.split_pin_pass(password)
            current_token_counter = token_obj.token.count
            first_old_counter = current_token_counter - count
            if first_old_counter < 0:
                first_old_counter = 0
            # find the value in the old OTP values! This resets the token.count!
            matching_count = token_obj.check_otp(otpval, first_old_counter, count)
            token_obj.set_otp_count(current_token_counter)
            if first_fill:
                counter_diff = 100
            else:
                counter_diff = matching_count - first_old_counter
            (res, err, otp_dict) = token_obj.get_multi_otp(count=counter_diff, counter_index=True)
            otps = otp_dict.get("otp")
            for key in otps.keys():
                # Return the hash of OTP PIN and OTP values
                otps[key] = passlib.hash. \
                    pbkdf2_sha512.encrypt(otppin + otps.get(key),
                                          rounds=rounds,
                                          salt_size=10)
            # We do not disable the token, so if all offline OTP values
            # are used, the token can be used the authenticate online again.
            # token_obj.enable(False)
            # increase the counter by the consumed values and
            # also store it in tokeninfo.
            token_obj.inc_otp_counter(increment=counter_diff)
            token_obj.add_tokeninfo(key="offline_counter",
                                    value=count)
            token_obj.add_tokeninfo("refilltoken", new_refilltoken)

        return new_refilltoken, otps

    @staticmethod
    def get_authentication_item(token_type,
                                serial,
                                challenge=None, options=None,
                                filter_param=None):
        """
        :param token_type: the type of the token. At the moment
                           we only support "HOTP" token. Supporting time
                           based tokens is difficult, since we would have to
                           return a looooong list of OTP values.
                           Supporting "yubikey" token (AES) would be
                           possible, too.
        :param serial:     the serial number of the token.
        :param challenge:  This can contain the password (otp pin + otp
        value) so that we can put the OTP PIN into the hashed response.
        :type challenge: basestring
        :return auth_item: A list of hashed OTP values
        """
        ret = {}
        options = options or {}
        password = challenge
        if token_type.lower() == "hotp":
            tokens = get_tokens(serial=serial)
            if len(tokens) == 1:
                token_obj = tokens[0]
                refilltoken, otps = MachineApplication.get_refill(serial, password, options, first_fill=True)
                ret["response"] = otps
                ret["refilltoken"] = refilltoken
                user_object = token_obj.user
                if user_object:
                    uInfo = user_object.info
                    if "username" in uInfo:
                        ret["username"] = uInfo.get("username")

        else:
            log.info("Token %r, type %r is not supported by"
                     "OFFLINE application module" % (serial, token_type))

        return ret

    @staticmethod
    def get_options():
        """
        returns a dictionary with a list of required and optional options
        """
        return {'required': [],
                'optional': ['user', 'count', 'rounds']}
