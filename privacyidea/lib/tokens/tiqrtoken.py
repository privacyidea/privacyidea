# -*- coding: utf-8 -*-
#
#  http://www.privacyidea.org
#  2015-09-01 Initial writeup.
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
The TiQR token is a special App based token, which allows easy login and
which is based on OCRA.

It generates an enrollment QR code, which contains a link with the more
detailed enrollment information.

For a description of the TiQR protocol see

* https://www.usenix.org/legacy/events/lisa11/tech/full_papers/Rijswijk.pdf
* https://github.com/SURFnet/tiqr/wiki/Protocol-documentation.
* https://tiqr.org

The TiQR token is based on the OCRA algorithm. It lets you authenticate
with your smartphone by scanning a QR code.

The TiQR token is enrolled via /token/init, but it requires no otpkey, since
the otpkey is generated on the smartphone and pushed to the privacyIDEA
server in a seconds step.

Enrollment
----------

1. Start enrollment with /token/init
2. Scan the QR code in the details of the JSON result. The QR code contains
   a link to /ttype/tiqr?action=metadata
3. The TiQR Smartphone App will fetch this link and get more information
4. The TiQR Smartphone App will push the otpkey to a
   link /ttype/tiqr?action=enrollment and the token will be ready for use.

Authentication
--------------

An application that wants to use the TiQR token with privacyIDEA has to use
the token in challenge response.

1. Call ``/validate/check?user=<user>&pass=<pin>``
   with the PIN of the TiQR token
2. The details of the JSON response contain a QR code, that needs to
   be shown to the user.
   In addition the application needs to save the ``transaction_id`` in the
   response.
3. The user scans the QR code.
4. The TiQR App communicates with privacyIDEA via the API /ttype/tiqr. In this
   step the response of the App to the challenge is verified. The successful
   authentication is stored in the Challenge DB table.
   (No need for the application to take any action)
5. Now, the application needs to poll
   ``/validate/check?user=<user>&transaction_id=*&pass=`` to verifiy the
   successful authentication. The ``pass`` can be empty.
   If ``value=true`` is returned, the user authenticated successfully
   with the TiQR token.

This code is tested in tests/test_lib_tokens_tiqr.
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

log = logging.getLogger(__name__)
optional = True
required = False
_ = gettext.gettext

OCRA_DEFAULT_SUITE = "OCRA-1:HOTP-SHA1-6:QN10"


class API_ACTIONS():
    METADATA = "metadata"
    ENROLLMENT = "enrollment"
    AUTHENTICATION = "authentication"
    ALLOWED_ACTIONS = [METADATA, ENROLLMENT, AUTHENTICATION]


class TiqrTokenClass(TokenClass):
    """
    The TiQR Token implementation.
    """

    @classmethod
    def get_class_type(cls):
        """
        Returns the internal token type identifier
        :return: tiqr
        :rtype: basestring
        """
        return "tiqr"

    @classmethod
    def get_class_prefix(cls):
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: TiQR
        :rtype: basestring
        """
        return "TiQR"

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
        res = {'type': 'tiqr',
               'title': 'TiQR Token',
               'description': ('TiQR: Enroll a TiQR token.'),
               'init': {},
               'config': {},
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {},
               }

        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new TiQR Token object from a database object

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"tiqr")
        self.hKeyRequired = False

    def update(self, param):
        """
        This method is called during the initialization process.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        # We should only initialize such a token, when the user is
        # immediately given in the init process, since the token on the
        # smartphone needs to contain a userId.
        user_object = get_user_from_param(param, required)
        self.set_user(user_object)

        ocrasuite = get_from_config("tiqr.ocrasuite") or OCRA_DEFAULT_SUITE
        OCRASuite(ocrasuite)
        self.add_tokeninfo("ocrasuite", ocrasuite)
        TokenClass.update(self, param)
        # We have to set the realms here, since the token DB object does not
        # have an ID before TokenClass.update.
        self.set_realms([user_object.realm])

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we return the URL for the TiQR App.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        params = params or {}
        enroll_url = get_from_config("tiqr.regServer")
        log.info("using tiqr.regServer for enrollment: %s" % enroll_url)
        serial = self.token.serial
        session = generate_otpkey()
        # save the session in the token
        self.add_tokeninfo("session", session)
        tiqrenroll = "tiqrenroll://%s?action=%s&session=%s&serial=%s" % (
            enroll_url, API_ACTIONS.METADATA,
            session, serial)

        response_detail["tiqrenroll"] = {"description":
                                                    _("URL for TiQR "
                                                      "enrollment"),
                                         "value": tiqrenroll,
                                         "img": create_img(tiqrenroll,
                                                           width=250)}

        return response_detail

    @classmethod
    def api_endpoint(cls, params):
        """
        This provides a function to be plugged into the API endpoint
        /ttype/<tokentype> which is defined in api/ttype.py
        See :ref:`rest_ttype`.

        :param params: The Request Parameters which can be handled with getParam
        :return: Flask Response
        """
        action = getParam(params, "action", optional) or \
                 API_ACTIONS.AUTHENTICATION
        if action not in API_ACTIONS.ALLOWED_ACTIONS:
            raise ParameterError("Allowed actions are %s" %
                                 API_ACTIONS.ALLOWED_ACTIONS)

        if action == API_ACTIONS.METADATA:
            session = getParam(params, "session", required)
            serial = getParam(params, "serial", required)
            # The user identifier is displayed in the App
            # We need to set the user ID
            tokens = get_tokens(serial=serial)
            if len(tokens) == 0:  # pragma: no cover
                raise ParameterError("No token with serial %s" % serial)
            user_identifier, user_displayname = tokens[0].get_user_displayname()

            service_identifier = get_from_config("tiqr.serviceIdentifier") or\
                                 "org.privacyidea"
            ocrasuite = get_from_config("tiqr.ocrasuite") or OCRA_DEFAULT_SUITE
            service_displayname = get_from_config("tiqr.serviceDisplayname") or \
                                  "privacyIDEA"
            reg_server = get_from_config("tiqr.regServer")
            auth_server = get_from_config("tiqr.authServer") or reg_server
            logo_url = get_from_config("tiqr.logoUrl")

            service = {"displayName": service_displayname,
                       "identifier": service_identifier,
                       "logoUrl": logo_url,
                       "infoUrl": "https://www.privacyidea.org",
                       "authenticationUrl":
                           "%s" % auth_server,
                       "ocraSuite": ocrasuite,
                       "enrollmentUrl":
                           "%s?action=%s&session=%s&serial=%s" % (
                               reg_server,
                               API_ACTIONS.ENROLLMENT,
                               session, serial)
                       }
            identity = {"identifier": user_identifier,
                        "displayName": user_displayname
                        }

            res = {"service": service,
                   "identity": identity
                   }

            return "json", res

        elif action == API_ACTIONS.ENROLLMENT:
            """
            operation: register
            secret: HEX
            notificationType: GCM
            notificationAddress: ...
            language: de
            session:
            serial:
            """
            res = "Fail"
            serial = getParam(params, "serial", required)
            session = getParam(params, "session", required)
            secret = getParam(params, "secret", required)
            # The secret needs to be stored in the token object.
            # We take the token "serial" and check, if it contains the "session"
            # in the tokeninfo.
            enroll_tokens = get_tokens(serial=serial)
            if len(enroll_tokens) == 1:
                if enroll_tokens[0].get_tokeninfo("session") == session:
                    # save the secret
                    enroll_tokens[0].set_otpkey(secret)
                    # delete the session
                    enroll_tokens[0].del_tokeninfo("session")
                    res = "OK"
                else:
                    raise ParameterError("Invalid Session")

            return "text", res
        elif action == API_ACTIONS.AUTHENTICATION:
            res = "FAIL"
            userId = getParam(params, "userId", required)
            session = getParam(params, "sessionKey", required)
            passw = getParam(params, "response", required)
            operation = getParam(params, "operation", required)
            res = "INVALID_CHALLENGE"
            # The sessionKey is stored in the db_challenge.transaction_id
            # We need to get the token serial for this sessionKey
            challenges = get_challenges(transaction_id=session)
            if len(challenges) == 1:
                # We found exactly one challenge
                if challenges[0].is_valid() and \
                                challenges[0].otp_valid is False:
                    # Challenge is still valid (time has not passed) and no
                    # correct response was given.
                    serial = challenges[0].serial
                    tokens = get_tokens(serial=serial)
                    if len(tokens) == 1:
                        # We found exactly the one token
                        res = "INVALID_RESPONSE"
                        r = tokens[0].verify_response(
                            challenge=challenges[0].challenge, passw=passw)
                        if r > 0:
                            res = "OK"
                            # Mark the challenge as answered successfully.
                            challenges[0].set_otp_status(True)

            cleanup_challenges()

            return "text", res

    @log_with(log)
    def is_challenge_request(self, passw, user=None, options=None):
        """
        check, if the request would start a challenge
        In fact every Request that is not a response needs to start a
        challenge request.

        At the moment we do not think of other ways to trigger a challenge.

        This function is not decorated with
            @challenge_response_allowed
        as the TiQR token is always a challenge response token!

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
        message = 'Please scan the QR Code'

        # Get ValidityTime=120s. Maybe there is a TIQRChallengeValidityTime...
        validity = int(get_from_config('DefaultChallengeValidityTime', 120))
        tokentype = self.get_tokentype().lower()
        lookup_for = tokentype.capitalize() + 'ChallengeValidityTime'
        validity = int(get_from_config(lookup_for, validity))

        # We need to set the user ID
        user_identifier, user_displayname = self.get_user_displayname()

        service_identifier = get_from_config("tiqr.serviceIdentifier") or \
                             "org.privacyidea"

        # Get the OCRASUITE from the token information
        ocrasuite = self.get_tokeninfo("ocrasuite") or OCRA_DEFAULT_SUITE
        # Depending on the OCRA-SUITE we create the challenge
        os = OCRASuite(ocrasuite)
        challenge = os.create_challenge()

        # Create the challenge in the database
        db_challenge = Challenge(self.token.serial,
                                 transaction_id=None,
                                 challenge=challenge,
                                 data=None,
                                 session=options.get("session"),
                                 validitytime=validity)
        db_challenge.save()

        authurl = "tiqrauth://%s@%s/%s/%s" % (user_identifier,
                                              service_identifier,
                                              db_challenge.transaction_id,
                                              challenge)
        attributes = {"img": create_img(authurl, width=250),
                      "value": authurl,
                      "poll": True,
                      "hideResponseInput": True}

        return True, message, db_challenge.transaction_id, attributes

    def verify_response(self, passw=None, challenge=None):
        """
        This method verifies if the *passw* is the valid OCRA response to the
        *challenge*.
        In case of success we return a value > 0

        :param passw: the password (pin+otp)
        :type passw: string
        :return: return otp_counter. If -1, challenge does not match
        :rtype: int
        """
        ocrasuite = self.get_tokeninfo("ocrasuite")
        security_object = self.token.get_otpkey()
        ocra_object = OCRA(ocrasuite, security_object=security_object)
        # TODO: We might need to add additional Signing or Counter objects
        r = ocra_object.check_response(passw, question=challenge)
        return r

    @check_token_locked
    def check_challenge_response(self, user=None, passw=None, options=None):
        """
        This function checks, if the challenge for the given transaction_id
        was marked as answered correctly.
        For this we check the otp_status of the challenge with the
        transaction_id in the database.

        We do not care about the password

        :param user: the requesting user
        :type user: User object
        :param passw: the password (pin+otp)
        :type passw: string
        :param options: additional arguments from the request, which could
                        be token specific. Usually "transaction_id"
        :type options: dict
        :return: return otp_counter. If -1, challenge does not match
        :rtype: int
        """
        options = options or {}
        otp_counter = -1

        # fetch the transaction_id
        transaction_id = options.get('transaction_id', None)
        if transaction_id is None:
            transaction_id = options.get('state')

        # get the challenges for this transaction ID
        if transaction_id is not None:
            challengeobject_list = get_challenges(serial=self.token.serial,
                                                  transaction_id=transaction_id)

            for challengeobject in challengeobject_list:
                if challengeobject.is_valid():
                    # we are still in time.
                    if challengeobject.otp_valid:
                        # create a positive response
                        otp_counter = 1
                        # delete the challenge
                        challengeobject.delete()
                        break

        return otp_counter
