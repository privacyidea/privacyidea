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
import logging
import passlib.hash
from privacyidea.lib.token import get_tokens
log = logging.getLogger(__name__)
ROUNDS = 6549

"""
TOOD: Add a mechanism for resynching offline

Resynching the offline state means that the backend is online again _before_
the cached OTP values are used up.
Then we need to be able to contact the privacyIDEA server again, to either
authenticate online or to fetch new OTP values.

Requirements for resynching offline state.

1. When going offline the client receives a list of hashed
   OTP PIN / OTP values pairs. These are marked as not usable, since the server
   would not know, if the values were used offline.

2. The privacyIDEA server can not simply verify on off the offline OTP values.
   We need an additional proof, that not a shoulder surfer is using a offline
   OTP value, that he akquired from shoulder surfing.

3. Two consecutive OTP values could be aquired by shoulder surfing a longer
   time.

4. For synching we need to add information, that can not be aquired from
   shoulder surfing.

5. This could be the remaining hashed OTP values. These hashed OTP values are
   only known to the system.

Resynching the offline state requires:
a) a OTP value entered by the user
b) the list of (or parts of the list) remaining hashed OTP values.

This way the attacker would have to:

1. should surf to receive an OTP value
2. get grasp of the client machine, to get the remaining hashed OTP values.

So if the client has cached OTP values the client may:
1. authenticate against these hashed values
2. if successfull try to contact the privacyIDEA server and try to resync
   using
   a) the entered OTP PIN / OTP value
   b) the remaining hashed OTP values.

privacyIDEA knows that this is an offline token and try to find the OTP value in
the past OTP values and ask for the hashed OTP values.
It then can reissue another 100 hashed OTP values.

This way the issued offline OTP values become some kind of offline cache.

"""


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
        otppin = ""
        if token_type.lower() == "hotp":
            count = int(options.get("count", 100))
            rounds = int(options.get("rounds", ROUNDS))
            # get the token
            toks = get_tokens(serial=serial)
            if len(toks) == 1:
                token_obj = toks[0]
                if password:
                    _r, otppin, _otpval = token_obj.split_pin_pass(password)
                (res, err, otp_dict) = token_obj.get_multi_otp(count=count)
                otps = otp_dict.get("otp")
                for key in otps.keys():
                    # Return the hash of OTP PIN and OTP values
                    otps[key] = passlib.hash.\
                        pbkdf2_sha512.encrypt(otppin + otps.get(key),
                                                rounds=rounds,
                                                salt_size=10)
                # We do not disable the token, so if all offline OTP values
                # are used, the token can be used the authenticate online again.
                # token_obj.enable(False)
                # increase the counter by the consumed values and
                # also store it in tokeninfo.
                token_obj.inc_otp_counter(counter=count)
                token_obj.add_tokeninfo(key="offline_counter",
                                        value=count)
                ret["response"] = otps
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
