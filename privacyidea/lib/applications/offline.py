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

import logging

from passlib.hash import pbkdf2_sha512

from privacyidea.lib.applications import MachineApplicationBase
from privacyidea.lib.config import get_prepend_pin
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.error import ValidateError, ParameterError
from privacyidea.lib.policy import TYPE
from privacyidea.lib.token import get_one_token
from privacyidea.lib.utils import get_computer_name_from_user_agent

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

    options:
      * user: a username.
      * count: is the number of OTP values returned

    """
    application_name = "offline"

    @staticmethod
    def generate_new_refilltoken(token, user_agent=None):
        """
        Generate new refill token and store it in the tokeninfo of the token.
        :param token: token in question
        :param user_agent: name of the machine, taken from the user-agent header
        :return: a string
        """
        log.debug(f"Generating refilltoken for {token.get_serial()} with user agent {user_agent}")

        # If the token is a FIDO2 token, we need to store the machine name with the refill token, because
        # the token can be on multiple machines, which need to be managed separately
        # TODO improve where the information about offline capabilities is stored
        if token.type.lower() in ["webauthn", "passkey"]:
            computer_name = get_computer_name_from_user_agent(user_agent)
            if not computer_name:
                log.warning(f"No computer name found in user agent {user_agent}. Unable to generate refill token.")
                raise ParameterError("Unable to generate refill token without computer name.")
            key = "refilltoken_" + computer_name
        else:
            key = "refilltoken"

        new_refilltoken = geturandom(REFILLTOKEN_LENGTH, hex=True)
        token.add_tokeninfo(key, new_refilltoken)
        return new_refilltoken

    @staticmethod
    def get_offline_otps(token, otppin, amount, rounds=ROUNDS):
        """
        Retrieve the desired number of passwords (= PIN + OTP), hash them
        and return them in a dictionary. Increase the token counter.

        :param token: token in question
        :param otppin: The OTP PIN to prepend in the passwords. The PIN is not validated!
        :param amount: Number of OTP values (non-negative!)
        :param rounds: Number of PBKDF2 rounds
        :return: dictionary
        """
        if amount < 0:
            raise ParameterError("Invalid refill amount: {!r}".format(amount))
        (res, err, otp_dict) = token.get_multi_otp(count=amount, counter_index=True)
        otps = otp_dict.get("otp")
        prepend_pin = get_prepend_pin()
        for key, otp in otps.items():
            # Return the hash of OTP PIN and OTP values
            otp_with_pin = otppin + otp if prepend_pin else otp + otppin
            otps[key] = pbkdf2_sha512.using(rounds=rounds, salt_size=10).hash(otp_with_pin)
        # We do not disable the token, so if all offline OTP values
        # are used, the token can be used to authenticate online again.
        # token_obj.enable(False)
        # increase the counter by the consumed values and
        # also store it in tokeninfo.
        token.inc_otp_counter(increment=amount)

        return otps

    @staticmethod
    def get_refill(token, password, options=None):
        """
        Returns new authentication OTPs to refill the client

        To do so we also verify the password, which may consist of PIN + OTP.

        :param token: Token object
        :param password: PIN + OTP
        :param options: dict that might contain "count" and "rounds"
        :return: a dictionary of auth items
        """
        options = options or {}
        otps = {}
        if token.type.lower() == "hotp":
            count = int(options.get("count", 100))
            rounds = int(options.get("rounds", ROUNDS))
            _r, otppin, otpval = token.split_pin_pass(password)
            if not _r:
                raise ParameterError("Could not split password")
            current_token_counter = token.token.count
            first_offline_counter = current_token_counter - count
            if first_offline_counter < 0:
                first_offline_counter = 0
            # find the value in the offline OTP values! This resets the token.count!
            matching_count = token.check_otp(otpval, first_offline_counter, count)
            token.set_otp_count(current_token_counter)
            # Raise an exception *after* we reset the token counter
            if matching_count < 0:
                raise ValidateError("You provided a wrong OTP value.")
            # We have to add 1 here: Assume *first_offline_counter* is the counter value of the first offline OTP
            # we sent to the client. Assume the client then requests a refill with that exact OTP value.
            # Then, we need to respond with a refill of one OTP value, as the client has consumed one OTP value.
            counter_diff = matching_count - first_offline_counter + 1
            otps = MachineApplication.get_offline_otps(token, otppin, counter_diff, rounds)
            token.add_tokeninfo(key="offline_counter",
                                value=count)
        elif token.type.lower() in ["webauthn", "passkey"]:
            pass
        return otps

    @staticmethod
    def get_authentication_item(token_type, serial, challenge=None, options=None, filter_param=None, user_agent=None):
        """
        :param token_type: the type of the token. At the moment
                           we support HOTP and WebAuthn/Passkey tokens.
        :param serial:     the serial number of the token.
        :param challenge:  this can contain the password (otp pin + otp value)
                           so that we can put the OTP PIN into the hashed response.
        :type challenge: basestring
        :param options: options
        :param filter_param: parameters
        :param user_agent: The user agent of the request
        :return auth_item: A list of hashed OTP values or pubKey, rpId and credentialId for WebAuthn token
        """
        ret = {}
        options = options or {}
        password = challenge
        token_type = token_type.lower()
        # TODO improve where the information about offline capabilities is stored
        if token_type in ["hotp", "webauthn", "passkey"]:
            token = get_one_token(serial=serial)
            user = token.user
            if user:
                user_info = user.info
                if "username" in user_info:
                    ret["user"] = ret["username"] = user_info.get("username")

            ret["refilltoken"] = MachineApplication.generate_new_refilltoken(token, user_agent)

            # Gather offline data depending on the token type
            if token_type == "webauthn":
                # return the pubKey, rpId and the credentialId (contained in the otpkey) to allow the machine to
                # verify the WebAuthn assertions signed with the token
                ret["response"] = {
                    "pubKey": token.get_tokeninfo("pubKey"),
                    "credentialId": token.decrypt_otpkey(),
                    "rpId": token.get_tokeninfo("relying_party_id")
                }
            elif token_type == "hotp":
                if password:
                    success, otppin, _ = token.split_pin_pass(password)
                    if not success:
                        raise ParameterError("Could not split password")
                else:
                    otppin = ""

                ret["response"] = MachineApplication.get_offline_otps(token,
                                                                      otppin,
                                                                      int(options.get("count", 100)),
                                                                      int(options.get("rounds", ROUNDS)))
            elif token_type == "passkey":
                ret["response"] = {
                    "pubKey": token.get_tokeninfo("public_key"),
                    "rpId": token.get_tokeninfo("relying_party_id"),
                    "credentialId": token.token.get_otpkey().getKey().decode("utf-8")
                }
        else:
            log.info(f"Token {serial} of type {token_type} is not supported by OFFLINE application module")

        return ret

    @staticmethod
    def get_options():
        """
        Returns a dictionary with a list of required and optional options
        """
        options = {
            "hotp": {
                "count": {"type": TYPE.STRING},
                "rounds": {"type": TYPE.STRING}
            },
            "webauthn": {},
            "passkey": {}
        }
        return options
