# -*- coding: utf-8 -*-
#
#  http://www.privacyidea.org
#  2015-09-21 Initial writeup.
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
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
__doc__ = """
U2F Token
"""

from privacyidea.api.lib.utils import getParam
from privacyidea.lib.config import get_from_config
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import generate_otpkey
from privacyidea.lib.utils import create_img
import logging
from privacyidea.lib.token import get_tokens
from privacyidea.lib.error import ParameterError
from privacyidea.models import Challenge
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.tokens.ocra import OCRASuite, OCRA
from privacyidea.lib.challenge import get_challenges
from privacyidea.models import cleanup_challenges
import gettext
from privacyidea.lib.policydecorators import challenge_response_allowed
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.tokens.u2f import (check_registration_data, url_decode,
                                        parse_registration_data, url_encode,
                                        parse_response_data, check_response)
from privacyidea.lib.error import ValidateError
import base64
import binascii
import json
from OpenSSL import crypto
import time


U2F_Version = "U2F_V2"
APP_ID = "http://localhost:5000"

log = logging.getLogger(__name__)
optional = True
required = False
_ = gettext.gettext


class U2fTokenClass(TokenClass):
    """
    The U2F Token implementation.

    The U2F Token is enrolled in two steps.

    **1. Step**

       .. sourcecode:: http

       POST /token/init HTTP/1.1
       Host: example.com
       Accept: application/json

       type=utf

    This step returns a serial number.

    **2. Step**

       .. sourcecode:: http

       POST /token/init HTTP/1.1
       Host: example.com
       Accept: application/json

       type=utf
       serial=U2F1234578
       clientdata=<clientdata>
       regdata=<regdata>

    *clientdata* and *regdata* are the values returned by the U2F device.
    """

    @classmethod
    def get_class_type(cls):
        """
        Returns the internal token type identifier
        :return: u2f
        :rtype: basestring
        """
        return "u2f"

    @classmethod
    def get_class_prefix(cls):
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: U2F
        :rtype: basestring
        """
        return "U2F"

    @classmethod
    @log_with(log)
    def get_class_info(cls, key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict or scalar
        """
        res = {'type': 'u2f',
               'title': 'U2F Token',
               'description': 'U2F: Enroll a U2F token.',
               'init': {},
               'config': {},
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {},
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new U2F Token object from a database object

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"u2f")
        self.hKeyRequired = False
        self.init_step = 1

    def update(self, param):
        """
        This method is called during the initialization process.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        TokenClass.update(self, param)
        description = "U2F initialization"
        reg_data = getParam(param, "regdata")
        if reg_data:
            self.init_step = 2
            attestation_cert, user_pub_key, key_handle, \
                signature, description = parse_registration_data(reg_data)
            client_data = getParam(param, "clientdata", required)
            client_data_str = url_decode(client_data)
            app_id = self.get_tokeninfo("appId", "")
            # Verify the registration data
            # In case of any crypto error, check_data raises an exception
            check_registration_data(attestation_cert, app_id, client_data_str,
                                    user_pub_key, key_handle, signature)
            self.set_otpkey(key_handle)
            self.add_tokeninfo("pubKey", user_pub_key)

        self.set_description(description)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we ask the user to press the button
        """
        response_detail = {}
        if self.init_step == 1:
            # This is the first step of the init request
            app_id = APP_ID
            nonce = base64.urlsafe_b64encode(geturandom(32))
            response_detail = TokenClass.get_init_detail(self, params, user)
            register_request = {"version": U2F_Version,
                                "challenge": nonce,
                                "appId": app_id,
                                "origin": app_id}
            response_detail["u2fRegisterRequest"] = register_request
            self.add_tokeninfo("appId", app_id)

        elif self.init_step == 2:
            # This is the second step of the init request
            response_detail["u2fRegisterResponse"] = {"subject":
                                                          self.token.description}

        return response_detail

    @log_with(log)
    def is_challenge_request(self, passw, user=None, options=None):
        """
        check, if the request would start a challenge
        In fact every Request that is not a response needs to start a
        challenge request.

        At the moment we do not think of other ways to trigger a challenge.

        This function is not decorated with
            @challenge_response_allowed
        as the U2F token is always a challenge response token!

        :param passw: The PIN of the token.
        :param options: dictionary of additional request parameters

        :return: returns true or false
        """
        trigger_challenge = False
        options = options or {}
        pin_match = self.check_pin(passw, user=user, options=options)
        if pin_match is True:
            trigger_challenge = True

        return trigger_challenge

    def create_challenge(self, transactionid=None, options=None):
        """
        This method creates a challenge, which is submitted to the user.
        The submitted challenge will be preserved in the challenge
        database.

        If no transaction id is given, the system will create a transaction
        id and return it, so that the response can refer to this transaction.

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :type options: dict
        :return: tuple of (bool, message, transactionid, attributes)
        :rtype: tuple

        The return tuple builds up like this:
        ``bool`` if submit was successful;
        ``message`` which is displayed in the JSON response;
        additional ``attributes``, which are displayed in the JSON response.
        """
        options = options or {}
        message = 'Please confirm with your U2F token'

        validity = int(get_from_config('DefaultChallengeValidityTime', 120))
        tokentype = self.get_tokentype().lower()
        lookup_for = tokentype.capitalize() + 'ChallengeValidityTime'
        validity = int(get_from_config(lookup_for, validity))

        challenge = geturandom(32)
        # Create the challenge in the database
        db_challenge = Challenge(self.token.serial,
                                 transaction_id=None,
                                 challenge=binascii.hexlify(challenge),
                                 data=None,
                                 session=options.get("session"),
                                 validitytime=validity)
        db_challenge.save()
        sec_object = self.token.get_otpkey()
        key_handle_hex = sec_object.getKey()
        key_handle_bin = binascii.unhexlify(key_handle_hex)
        key_handle_url = url_encode(key_handle_bin)
        challenge_url = url_encode(challenge)
        u2f_sign_request = {"appId": APP_ID,
                            "version": U2F_Version,
                            "challenge": challenge_url,
                            "keyHandle": key_handle_url}

        response_details = {"u2fSignRequest": u2f_sign_request,
                            "hideResponseInput": True}

        return True, message, db_challenge.transaction_id, response_details

    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        This checks the response of a previous challenge.
        :param otpval: N/A
        :param counter:
        :param window: N/A
        :param options: contains "clientdata", "signaturedata" and
            "transaction_id"
        :return: A value > 0 in case of success
        """
        ret = -1
        clientdata = options.get("clientdata")
        signaturedata = options.get("signaturedata")
        transaction_id = options.get("transaction_id")
        # The challenge in the challenge DB object is saved in hex
        challenge = binascii.unhexlify(options.get("challenge"))
        if not (clientdata and signaturedata and transaction_id and challenge):
            # This is no valid response for a U2F token
            return ret
        challenge_url = url_encode(challenge)
        clientdata = url_decode(clientdata)
        clientdata_dict = json.loads(clientdata)
        client_challenge = clientdata_dict.get("challenge")
        if challenge_url != client_challenge:
            raise ValidateError("Challenge mismatch. The U2F key did not send "
                                "to original challenge.")
        if clientdata_dict.get("typ") != "navigator.id.getAssertion":
            raise ValidateError("Incorrect navigator.id")
        client_origin = clientdata_dict.get("origin")
        client_typ = clientdata_dict.get("typ")

        signaturedata = url_decode(signaturedata)
        signaturedata_hex = binascii.hexlify(signaturedata)
        user_presence, counter, signature = parse_response_data(
            signaturedata_hex)

        user_pub_key = self.get_tokeninfo("pubKey")
        app_id = self.get_tokeninfo("appId", "")
        if check_response(user_pub_key, app_id, clientdata,
                          binascii.hexlify(signature), counter,
                          user_presence):
            # Signature verified.
            # check, if the counter increased!
            if counter > self.get_otp_count():
                self.set_otp_count(counter)
                ret = counter
            else:
                log.warning("The signature of %s was valid, but contained an "
                            "old counter." % self.token.serial)

        return ret
