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
from privacyidea.lib.error import ValidateError, ParameterError
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
    def generate_new_refilltoken(token_obj):
        """
        Generate new refill token and store it in the tokeninfo of the token.
        :param token_obj: token in question
        :return: a string
        """
        new_refilltoken = geturandom(REFILLTOKEN_LENGTH, hex=True)
        token_obj.add_tokeninfo("refilltoken", new_refilltoken)
        return new_refilltoken

    @staticmethod
    def get_offline_otps(token_obj, otppin, amount, rounds=ROUNDS):
        """
        Retrieve the desired number of passwords (= PIN + OTP), hash them
        and return them in a dictionary. Increase the token counter.
        :param token_obj: token in question
        :param otppin: The OTP PIN to prepend in the passwords. The PIN is not validated!
        :param amount: Number of OTP values (non-negative!)
        :param rounds: Number of PBKDF2 rounds
        :return: dictionary
        """
        if amount < 0:
            raise ParameterError("Invalid refill amount: {!r}".format(amount))
        (res, err, otp_dict) = token_obj.get_multi_otp(count=amount, counter_index=True)
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
        token_obj.inc_otp_counter(increment=amount)

        return otps

    @staticmethod
    def get_refill(token_obj, password, options=None):
        """
        Returns new authentication OTPs to refill the client

        To do so we also verify the password, which may consist of PIN + OTP.

        :param token_obj: Token object
        :param password: PIN + OTP
        :param options: dict that might contain "count" and "rounds"
        :return: a dictionary of auth items
        """
        options = options or {}
        count = int(options.get("count", 100))
        rounds = int(options.get("rounds", ROUNDS))
        _r, otppin, otpval = token_obj.split_pin_pass(password)
        if not _r:
            raise ParameterError("Could not split password")
        current_token_counter = token_obj.token.count
        first_offline_counter = current_token_counter - count
        if first_offline_counter < 0:
            first_offline_counter = 0
        # find the value in the offline OTP values! This resets the token.count!
        matching_count = token_obj.check_otp(otpval, first_offline_counter, count)
        token_obj.set_otp_count(current_token_counter)
        # Raise an exception *after* we reset the token counter
        if matching_count < 0:
            raise ValidateError("You provided a wrong OTP value.")
        # We have to add 1 here: Assume *first_offline_counter* is the counter value of the first offline OTP
        # we sent to the client. Assume the client then requests a refill with that exact OTP value.
        # Then, we need to respond with a refill of one OTP value, as the client has consumed one OTP value.
        counter_diff = matching_count - first_offline_counter + 1
        otps = MachineApplication.get_offline_otps(token_obj, otppin, counter_diff, rounds)
        token_obj.add_tokeninfo(key="offline_counter",
                                value=count)
        return otps

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
                if password:
                    _r, otppin, _ = token_obj.split_pin_pass(password)
                    if not _r:
                        raise ParameterError("Could not split password")
                else:
                    otppin = ""
                otps = MachineApplication.get_offline_otps(token_obj,
                                                           otppin,
                                                           int(options.get("count", 100)),
                                                           int(options.get("rounds", ROUNDS)))
                refilltoken = MachineApplication.generate_new_refilltoken(token_obj)
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
