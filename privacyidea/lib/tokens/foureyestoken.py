# -*- coding: utf-8 -*-
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2020-09-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Use Multi-Challenge to ask for several tokens one after
#             the other.
#  2018-01-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add tokenkind
#  2015-08-28 Initial writeup of the 4eyes token
#             according to
#             https://github.com/privacyidea/privacyidea/issues/167
#             Cornelius Kölbel <cornelius@privacyidea.org>
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
__doc__ = """This is the implementation of the 4eyes token.
The 4eyes token combines several other tokens to a virtual new token,
requiring that 2 or more users with different tokens are present to
authenticate.

A 4eyes token stores the required number of tokens of each realm
and the splitting sign.

The code is tested in tests/test_lib_tokens_4eyes.
"""
import logging
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.config import get_from_config
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass, TOKENKIND
from privacyidea.lib.error import ParameterError
from privacyidea.lib.token import check_realm_pass
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib import _
from privacyidea.lib.policy import ACTION, SCOPE, GROUP, get_action_values_from_options
from privacyidea.lib.challenge import get_challenges, Challenge
import json
import datetime

log = logging.getLogger(__name__)
optional = True
required = False


class FourEyesTokenClass(TokenClass):
    """
    The FourEyes token can be used to implement the Two Man Rule.
    The FourEyes token defines how many tokens of which realms are required
    like:

        * 2 tokens of RealmA
        * 1 token of RealmB

    Then users (the owners of those tokens) need to login by everyone
    entering their OTP PIN and OTP value. It does not matter, in which order
    they enter the values. All their PINs and OTPs are concatenated into one
    password field but need to be separated by the splitting sign.

    The FourEyes token again splits the password value and tries to
    authenticate each of the these passwords in the realms using the function
    ``check_realm_pass``.

    The FourEyes token itself does not provide an OTP PIN.

    The token is initialized using additional parameters at token/init:

    **Example Authentication Request**:

        .. sourcecode:: http

           POST /auth HTTP/1.1
           Host: example.com
           Accept: application/json

           type=4eyes
           user=cornelius
           realm=realm1
           4eyes=realm1:2,realm2:1
           separator=%20
    """

    def __init__(self, db_token):
        """
        :param db_token: the token
        :type db_token: database token object
        """
        TokenClass.__init__(self, db_token)
        self.set_type("4eyes")

    @staticmethod
    def get_class_type():
        """
        return the class type identifier
        """
        return "4eyes"

    @staticmethod
    def get_class_prefix():
        """
        return the token type prefix
        """
        return "PI4E"

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
        res = {'type': '4eyes',
               'title': '4Eyes Token',
               'description': _('4Eyes Token: Use tokens of two or more users '
                                'to authenticate'),
               'init': {},
               'config': {},
               'user':  [],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin"],
               'policy': {
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of 4eyes tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of active 4eyes tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   }
               },
               }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res
        return ret

    @staticmethod
    def realms_dict_to_string(realms):
        """
        This function converts the realms - if it is a dictionary - to a string::

            {"realm1": {"selected": True,
                        "count": 1 },
             "realm2": {"selected": True,
                        "count": 2}}
                                        -> "realm1:1,realm2:2"

        :param realms: the realms as they are passed from the WebUI
        :type realms: dict
        :return: realms
        :rtype: str
        """
        realms_string = ""
        if type(realms) is dict:
            for realmname, v in realms.items():
                if v.get("selected"):
                    realms_string += "{0!s}:{1!s},".format(realmname, v.get("count"))
            if realms_string[-1] == ',':
                realms_string = realms_string[:-1]
        else:
            realms_string = realms

        return realms_string

    @staticmethod
    def convert_realms(realms):
        """
        This function converts the realms as given by the API parameter to a
        dictionary::

            "realm1:2,realm2:1" -> {"realm1":2,
                                    "realm2":1}

        :param realms: a serialized list of realms
        :type realms: str
        :return: dict of realms
        :rtype: dict
        """
        realms_dict = {}
        realm_list = realms.split(",")
        for rl in realm_list:
            r = rl.split(":")
            if len(r) == 2:
                realms_dict[r[0]] = int(r[1])
        return realms_dict

    def _get_realms(self):
        """
        This returns the dictionary how many tokens of each realm are necessary
        :return: dict with realms
        """
        return self.convert_realms(self.get_tokeninfo("4eyes"))

    @staticmethod
    def _dict_diff(required, used):
        """
        Subtract the "used" dict from the "required" dict
        :return: diff dict
        """
        result = {}
        for k, v in required.items():
            result[k] = v - used.get(k, 0)
        return result

    def _get_separator(self):
        return self.get_tokeninfo("separator") or " "

    def update(self, param):
        """
        This method is called during the initialization process.
        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        TokenClass.update(self, param)

        realms = getParam(param, "4eyes", required)
        separator = getParam(param, "separator", optional, default=" ")
        if len(separator) > 1:
            raise ParameterError("The separator must only be one single "
                                 "character")
        realms = self.realms_dict_to_string(realms)
        self.convert_realms(realms)
        self.add_tokeninfo("separator", separator)
        self.add_tokeninfo("4eyes", realms)
        self.add_tokeninfo("tokenkind", TOKENKIND.VIRTUAL)

    def _authenticate_in_realm(self, realm, password):
        """
        This method tries to authenticate a given credential (can be PIN + OTP)
        against tokens in a realm and returns the serial of the token, if successful.
        Otherwise None

        :param realm: The realm where to authenticate
        :param password: The PIN + OTP
        :return: token_id or None
        """
        serial = None
        res, reply = check_realm_pass(realm, password,
                                      exclude_types=[self.get_tokentype()])
        if res:
            serial = reply.get("serial")
        return serial

    def _authenticate_remaining_realms(self, passw, remaining_realms, used_tokens, options):
        r_success = -1
        for realm in remaining_realms:
            # check for token in realm
            serial = self._authenticate_in_realm(realm, passw)
            if serial:
                # check that not the same token is used again
                if serial in used_tokens.get(realm, []):
                    log.info("The same token {0!s} was already used. "
                             "You can not use a token twice.".format(serial))
                else:
                    # Add the serial to the used tokens.
                    if realm in used_tokens:
                        used_tokens[realm].append(serial)
                    else:
                        used_tokens[realm] = [serial]
                    options["data"] = used_tokens
                    log.debug("Partially authenticated with token {0!s}.".format(serial))
                    r_success = 1
                    break
        return r_success

    @log_with(log)
    @check_token_locked
    def authenticate(self, passw, user=None, options=None):
        """
        do the authentication on base of password / otp and user and
        options, the request parameters.

        Here we contact the other privacyIDEA server to validate the OtpVal.

        :param passw: the password / otp
        :param user: the requesting user
        :param options: the additional request parameters

        :return: tuple of (success, otp_count - 0 or -1, reply)

        """
        pin_match = True
        otp_counter = -1
        reply = None

        required_realms = self._get_realms()
        # This holds the found serial numbers in the realms
        found_serials = {}

        separator = self._get_separator()
        passwords = passw.split(separator)

        for realm in required_realms.keys():
            found_serials[realm] = []
            for otp in passwords:
                serial = self._authenticate_in_realm(realm, otp)
                if serial:
                    found_serials[realm].append(serial)
            # uniquify the serials in the list
            found_serials[realm] = list(set(found_serials[realm]))

            if len(found_serials[realm]) < required_realms[realm]:
                reply = {"foureyes": "Only found {0:d} tokens in realm {1!s}".format(
                    len(found_serials[realm]), realm)}
                otp_counter = -1
                break
            else:
                otp_counter = 1

        return pin_match, otp_counter, reply

    def _get_remaining_tokens(self, used_tokens_with_serials):
        """
        Takes a dictionary like::

            {"realm1": ["serial1", "serial2"],
             "realm3": ["serialB"]}

        and returns a dictionary of the tokens that remain for authentication like::

            {"realm1": 1, "realm3": 0}

        :param used_tokens_with_serials: dictionary with used serials
        :type used_tokens_with_serials: dict
        :return: dict
        """
        required_tokens = self._get_realms()
        used_tokens = {k: len(v) for (k, v) in used_tokens_with_serials.items()}
        # compare the dict of required tokens with the dict of used tokens
        remaining_tokens = self._dict_diff(required_tokens, used_tokens)
        return remaining_tokens

    def _get_remaining_realms(self, used_tokens_with_serials):
        """
        Return the list of the remaining realms, from which an authentication is needed.
        :param used_tokens_with_serials:
        :return:
        """
        remaining_tokens = self._get_remaining_tokens(used_tokens_with_serials)
        remaining_realms = [r for (r, toks) in remaining_tokens.items() if toks > 0]
        return remaining_realms

    @log_with(log)
    def has_further_challenge(self, options=None):
        """
        Check if there are still more tokens to be authenticated
        :param options: Options dict
        :return: True, if further challenge is required.
        """
        transaction_id = options.get('transaction_id')
        challengeobject_list = get_challenges(serial=self.token.serial,
                                              transaction_id=transaction_id)
        if len(challengeobject_list) == 1:
            remaining_realms = self._get_remaining_realms(options.get("data", {}))
            if remaining_realms:
                options["data"] = json.dumps(options.get("data", {}))
                options["message"] = "Remaining tokens: {0!s}".format(remaining_realms)
                return True
        return False

    @check_token_locked
    def check_challenge_response(self, user=None, passw=None, options=None):
        """
        This method verifies if the given response is the PIN + OTP of one of the
        remaining tokens.
        In case of success it then returns ``1``

        :param user: the requesting user
        :type user: User object
        :param passw: the password: PIN + OTP
        :type passw: string
        :param options: additional arguments from the request, which could
                        be token specific. Usually "transaction_id"
        :type options: dict
        :return: return 1 if the answer to the challenge is correct, -1 otherwise.
        :rtype: int
        """
        options = options or {}
        r_success = -1

        # fetch the transaction_id
        transaction_id = options.get('transaction_id')
        if transaction_id is None:
            transaction_id = options.get('state')

        # get the challenges for this transaction ID
        if transaction_id is not None:
            challengeobject_list = get_challenges(serial=self.token.serial,
                                                  transaction_id=transaction_id)

            for challengeobject in challengeobject_list:
                if challengeobject.is_valid():
                    # challenge is still valid
                    used_tokens = json.loads(challengeobject_list[0].data or json.dumps({}))
                    remaining_realms = self._get_remaining_realms(used_tokens)
                    r_success = self._authenticate_remaining_realms(passw, remaining_realms, used_tokens, options)

                    if r_success:
                        challengeobject.set_otp_status(True)
                    if not r_success:
                        # increase the received_count
                        challengeobject.set_otp_status()

        self.challenge_janitor()
        return r_success

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
        :return: tuple of (bool, message, transactionid, reply_dict)
        :rtype: tuple

        The return tuple builds up like this:
        ``bool`` if submit was successful;
        ``message`` which is displayed in the JSON response;
        additional challenge ``reply_dict``, which are displayed in the JSON challenges response.
        """
        options = options or {}
        message = ""
        if type(options.get("data")) == dict:
            # In the special first chal-resp case we do not have jsonified data, yet. So we need to convert
            options["data"] = json.dumps(options.get("data"))
        used_tokens = json.loads(options.get("data", json.dumps({})))
        remaining_realms = self._get_remaining_realms(used_tokens)
        if remaining_realms:
            message = "Please authenticate with another token from " \
                      "either realm: {0!s}.".format(", ".join(remaining_realms))

        validity = int(get_from_config('DefaultChallengeValidityTime', 120))
        tokentype = self.get_tokentype().lower()
        # Maybe there is a 4EYESChallengeValidityTime...
        lookup_for = tokentype.capitalize() + 'ChallengeValidityTime'
        validity = int(get_from_config(lookup_for, validity))

        # Create the challenge in the database
        db_challenge = Challenge(self.token.serial,
                                 transaction_id=transactionid,
                                 data=options.get("data"),
                                 session=options.get("session"),
                                 challenge=message,
                                 validitytime=validity)
        db_challenge.save()
        expiry_date = datetime.datetime.now() + \
                      datetime.timedelta(seconds=validity)
        reply_dict = {'attributes': {'valid_until': "{0!s}".format(expiry_date)}}
        return True, message, db_challenge.transaction_id, reply_dict

    def is_challenge_request(self, passw, user=None, options=None):
        """
        The 4eyes token can act as a challenge response token.

        Either
         * if the first passw given is the PIN of the 4eyes token or
         * if the first passw given is the complete PIN+OTP from one of
           the admintokens.

        :param passw: password, which might be pin or pin+otp
        :type passw: str
        :param user: The user from the authentication request
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict
        :return: true or false
        :rtype: bool
        """
        options = options or {}
        pin_match = self.check_pin(passw, user=user, options=options)
        if pin_match:
            return True
        elif "transaction_id" not in options:
            # The special case, when the *first* admin token already matches, we will
            # start a multi challenge chain
            used_tokens = {}
            remaining_realms = self._get_remaining_realms({})
            r_success = self._authenticate_remaining_realms(passw, remaining_realms, used_tokens, options)
            return r_success >= 0

        return False
