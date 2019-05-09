# -*- coding: utf-8 -*-
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2019-02-08   Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Start the pushtoken class
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
__doc__ = """The pushtoken sends a push notification via firebase
to the registered smartphone.
The token is a challenge response token. The smartphone will sign the challenge
and send it back to the authentication endpoint. 

This code is tested in tests/test_lib_tokens_push
"""

from base64 import b32decode
from six.moves.urllib.parse import quote

from privacyidea.api.lib.utils import getParam
from privacyidea.lib.token import get_one_token
from privacyidea.lib.utils import prepare_result, to_bytes
from privacyidea.lib.error import ResourceNotFoundError, ValidateError

from privacyidea.lib.config import get_from_config
from privacyidea.lib.policy import SCOPE, ACTION, get_action_values_from_options
from privacyidea.lib.log import log_with
from privacyidea.lib import _

from privacyidea.lib.tokenclass import TokenClass
from privacyidea.models import Challenge
from privacyidea.lib.decorators import check_token_locked
import logging
from privacyidea.lib.utils import create_img, b32encode_and_unicode
from privacyidea.lib.error import ParameterError
from privacyidea.lib.user import User
from privacyidea.lib.apps import _construct_extra_parameters
from privacyidea.lib.crypto import geturandom, generate_keypair
from privacyidea.lib.smsprovider.SMSProvider import get_smsgateway, create_sms_instance
from privacyidea.lib.smsprovider.FirebaseProvider import FIREBASE_CONFIG
from privacyidea.lib.challenge import get_challenges
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


log = logging.getLogger(__name__)

DEFAULT_CHALLENGE_TEXT = _("Please confirm the authentication on your mobile device!")
DEFAULT_MOBILE_TEXT = _("Do you want to confirm the login?")
PRIVATE_KEY_SERVER = "private_key_server"
PUBLIC_KEY_SERVER = "public_key_server"
PUBLIC_KEY_SMARTPHONE = "public_key_smartphone"
GWTYPE = u'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider'


class PUSH_ACTION(object):
    FIREBASE_CONFIG = "push_firebase_configuration"
    MOBILE_TEXT = "push_text_on_mobile"
    MOBILE_TITLE = "push_title_on_mobile"
    SSL_VERIFY = "push_ssl_verify"


def strip_key(key):
    """
    strip the headers and footers like
    -----BEGIN PUBLIC RSA KEY-----
    -----END PUBLIC KEY-----
    -----BEGIN PRIVATE RSA KEY-----
    as well as whitespace

    :param key: key as a string
    :return: stripped key
    """
    if key.startswith("-----BEGIN"):
        return "\n".join(key.strip().splitlines()[1:-1]).strip()
    else:
        return key.strip()


@log_with(log)
def create_push_token_url(url=None, ttl=10, issuer="privacyIDEA", serial="mylabel",
                          tokenlabel="<s>", user_obj=None, extra_data=None, user=None, realm=None):
    """

    :param url:
    :param ttl:
    :param issuer:
    :param serial:
    :param tokenlabel:
    :param user_obj:
    :param extra_data:
    :param user:
    :param realm:
    :return:
    """
    extra_data = extra_data or {}

    # policy depends on some lib.util

    user_obj = user_obj or User()

    # We need realm und user to be a string
    realm = realm or ""
    user = user or ""

    # Deprecated
    label = tokenlabel.replace("<s>",
                               serial).replace("<u>",
                                               user).replace("<r>", realm)
    label = label.format(serial=serial, user=user, realm=realm,
                         givenname=user_obj.info.get("givenname", ""),
                         surname=user_obj.info.get("surname", ""))

    issuer = issuer.format(serial=serial, user=user, realm=realm,
                           givenname=user_obj.info.get("givenname", ""),
                           surname=user_obj.info.get("surname", ""))

    url_label = quote(label.encode("utf-8"))
    url_issuer = quote(issuer.encode("utf-8"))
    url_url = quote(url.encode("utf-8"))

    return ("otpauth://pipush/{label!s}?"
            "url={url!s}&ttl={ttl!s}&"
            "issuer={issuer!s}{extra}".format(label=url_label, issuer=url_issuer,
                                       url=url_url, ttl=ttl,
                                       extra=_construct_extra_parameters(extra_data)))


class PushTokenClass(TokenClass):
    """
    The PUSH token uses the firebase service to send challenges to the
    users smartphone. The user confirms on the smartphone, signes the
    challenge and sends it back to privacyIDEA.

    The enrollment occurs in two enrollment steps:

    # Step 1

    The device is enrolled using a QR code, that looks like this:

    otpauth://pipush/PIPU0006EF85?url=https://yourprivacyideaserver/enroll/this/token&ttl=120

    # Step 2

    In the QR code is a URL, where the smartphone sends the remaining data for the enrollment.

    POST https://yourprivacyideaserver/ttype/push
     enrollment_credential=<some credential>
     serial=<token serial>
     fbtoken=<firebase token>
     pubkey=<public key>

    For more information see:
    https://github.com/privacyidea/privacyidea/issues/1342
    https://github.com/privacyidea/privacyidea/wiki/concept%3A-PushToken

    """
    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type(u"push")
        self.mode = ['challenge']
        self.hKeyRequired = False


    @staticmethod
    def get_class_type():
        """
        return the generic token class identifier
        """
        return "push"

    @staticmethod
    def get_class_prefix():
        return "PIPU"

    @staticmethod
    def get_class_info(key=None, ret='all'):
        """
        returns all or a subtree of the token definition

        :param key: subsection identifier
        :type key: str
        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype : s.o.
        """
        gws = get_smsgateway(gwtype=GWTYPE)
        res = {'type': 'push',
               'title': _('PUSH Token'),
               'description':
                    _('PUSH: Send a push notification to a smartphone.'),
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ENROLL: {
                       PUSH_ACTION.FIREBASE_CONFIG: {
                           'type': 'str',
                           'desc': _('The configuration of your Firebase application.'),
                           'group': "PUSH",
                           'value': [gw.identifier for gw in gws]
                       },
                       PUSH_ACTION.SSL_VERIFY: {
                           'type': 'str',
                           'desc': _('The smartphone needs to verify SSL during the enrollment. (default 1)'),
                           'group':  "PUSH",
                           'value': ["0", "1"]
                       }
                   },
                   SCOPE.AUTH: {
                       PUSH_ACTION.MOBILE_TEXT: {
                           'type': 'str',
                           'desc': _('The question the user sees on his mobile phone.'),
                           'group': 'PUSH'
                       },
                       PUSH_ACTION.MOBILE_TITLE: {
                           'type': 'str',
                           'desc': _('The title of the notification, the user sees on his mobile phone.'),
                           'group': 'PUSH'
                       },
                       PUSH_ACTION.SSL_VERIFY: {
                           'type': 'str',
                           'desc': _('The smartphone needs to verify SSL during authentication. (default 1)'),
                           'group': "PUSH",
                           'value': ["0", "1"]

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

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        process the initialization parameters

        We need to distinguish the first authentication step
        and the second authentication step.

        1. step:
            parameter type contained.
            parameter genkey contained.

        2. step:
            parameter serial contained
            parameter fbtoken contained
            parameter pubkey contained

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        """
        upd_param = {}
        for k, v in param.items():
            upd_param[k] = v

        if "serial" in upd_param and "fbtoken" in upd_param and "pubkey" in upd_param:
            # We are in step 2:
            if self.token.rollout_state != "clientwait":
                raise ParameterError("Invalid state! The token you want to enroll is not in the state 'clientwait'.")
            enrollment_credential = getParam(upd_param, "enrollment_credential", optional=False)
            if enrollment_credential != self.get_tokeninfo("enrollment_credential"):
                raise ParameterError("Invalid enrollment credential. You are not authorized to finalize this token.")
            self.del_tokeninfo("enrollment_credential")
            self.token.rollout_state = "enrolled"
            self.token.active = True
            self.add_tokeninfo(PUBLIC_KEY_SMARTPHONE, upd_param.get("pubkey"))
            self.add_tokeninfo("firebase_token", upd_param.get("fbtoken"))
            # create a keypair for the server side.
            pub_key, priv_key = generate_keypair(4096)
            self.add_tokeninfo(PUBLIC_KEY_SERVER, pub_key)
            self.add_tokeninfo(PRIVATE_KEY_SERVER, priv_key, "password")

        elif "genkey" in upd_param:
            # We are in step 1:
            upd_param["2stepinit"] = 1
            self.add_tokeninfo("enrollment_credential", geturandom(20, hex=True))
            # We also store the firebase config, that was used during the enrollment.
            self.add_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG, param.get(PUSH_ACTION.FIREBASE_CONFIG))
        else:
            raise ParameterError("Invalid Parameters. Either provide (genkey) or (serial, fbtoken, pubkey).")

        TokenClass.update(self, upd_param, reset_failcount)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        This returns the init details during enrollment.

        In the 1st step the QR Code is returned.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        if "otpkey" in response_detail:
            del response_detail["otpkey"]
        params = params or {}
        user = user or User()
        tokenlabel = params.get("tokenlabel", "<s>")
        tokenissuer = params.get("tokenissuer", "privacyIDEA")
        sslverify = getParam(params, PUSH_ACTION.SSL_VERIFY, allowed_values=["0", "1"], default="1")
        # Add rollout state the response
        response_detail['rollout_state'] = self.token.rollout_state

        extra_data = {"enrollment_credential": self.get_tokeninfo("enrollment_credential")}
        imageurl = params.get("appimageurl")
        if imageurl:
            extra_data.update({"image": imageurl})
        if self.token.rollout_state == "clientwait":
            # Get the values from the configured PUSH config
            fb_identifier = params.get(PUSH_ACTION.FIREBASE_CONFIG)
            firebase_configs = get_smsgateway(identifier=fb_identifier, gwtype=GWTYPE)
            if len(firebase_configs) != 1:
                raise ParameterError("Unknown Firebase configuration!")
            fb_options = firebase_configs[0].option_dict
            for k in [FIREBASE_CONFIG.PROJECT_NUMBER, FIREBASE_CONFIG.PROJECT_ID,
                      FIREBASE_CONFIG.APP_ID, FIREBASE_CONFIG.API_KEY,
                      FIREBASE_CONFIG.APP_ID_IOS, FIREBASE_CONFIG.API_KEY_IOS]:
                extra_data[k] = fb_options.get(k)
            # this allows to upgrade our crypto
            extra_data["v"] = 1
            extra_data["serial"] = self.get_serial()
            extra_data["sslverify"] = sslverify
            # We display this during the first enrollment step!
            qr_url = create_push_token_url(url=fb_options.get(FIREBASE_CONFIG.REGISTRATION_URL),
                                           user=user.login,
                                           realm=user.realm,
                                           serial=self.get_serial(),
                                           tokenlabel=tokenlabel,
                                           issuer=tokenissuer,
                                           user_obj=user,
                                           extra_data=extra_data,
                                           ttl=fb_options.get(FIREBASE_CONFIG.TTL))
            response_detail["pushurl"] = {"description": _("URL for privacyIDEA Push Token"),
                                          "value": qr_url,
                                          "img": create_img(qr_url, width=250)
                                          }
            self.add_tokeninfo(FIREBASE_CONFIG.PROJECT_ID, fb_options.get(FIREBASE_CONFIG.PROJECT_ID))

            response_detail["enrollment_credential"] = self.get_tokeninfo("enrollment_credential")

        elif self.token.rollout_state == "enrolled":
            # in the second enrollment step we return the public key of the server to the smartphone.
            pubkey = strip_key(self.get_tokeninfo(PUBLIC_KEY_SERVER))
            response_detail["public_key"] = pubkey

        return response_detail

    @classmethod
    def api_endpoint(cls, request, g):
        """
        This provides a function which is called by the API endpoint
        /ttype/push which is defined in api/ttype.py

        The method returns
            return "json", {}

        This endpoint is used for the 2nd enrollment step of the smartphone.
        Parameters sent:
            * serial
            * fbtoken
            * pubkey

        This endpoint is also used, if the smartphone sends the signed response
        to the challenge during authentication
        Parameters sent:
            * serial
            * nonce (which is the challenge)
            * signature (which is the signed nonce)


        :param request: The Flask request
        :param g: The Flask global object g
        :return: dictionary
        """
        details = {}
        result = False
        serial = getParam(request.all_data, "serial", optional=False)

        if serial and "fbtoken" in request.all_data and "pubkey" in request.all_data:
            log.debug("Do the 2nd step of the enrollment.")
            try:
                token_obj = get_one_token(serial=serial,
                                          tokentype="push",
                                          rollout_state="clientwait")
                token_obj.update(request.all_data)
            except ResourceNotFoundError:
                raise ResourceNotFoundError("No token with this serial number in the rollout state 'clientwait'.")
            init_detail_dict = request.all_data

            details = token_obj.get_init_detail(init_detail_dict)
            result = True
        elif serial and "nonce" in request.all_data and "signature" in request.all_data:
            log.debug("Handling the authentication response from the smartphone.")
            challenge = getParam(request.all_data, "nonce")
            serial = getParam(request.all_data, "serial")
            signature = getParam(request.all_data, "signature")

            # get the token_obj for the given serial:
            token_obj = get_one_token(serial=serial, tokentype="push")
            pubkey_pem = token_obj.get_tokeninfo(PUBLIC_KEY_SMARTPHONE)
            # The public key of the smartphone was probably sent as urlsafe:
            pubkey_pem = pubkey_pem.replace("-", "+").replace("_", "/")
            # The public key was sent without any header
            pubkey_pem = "-----BEGIN PUBLIC KEY-----\n{0!s}\n-----END PUBLIC KEY-----".format(pubkey_pem.strip().replace(" ", "+"))
            # Do the 2nd step of the authentication
            # Find valid challenges
            challengeobject_list = get_challenges(serial=serial, challenge=challenge)

            if challengeobject_list:
                # There are valid challenges, so we check this signature
                for chal in challengeobject_list:
                    # verify the signature of the nonce
                    pubkey_obj = serialization.load_pem_public_key(to_bytes(pubkey_pem), default_backend())
                    sign_data = u"{0!s}|{1!s}".format(challenge, serial)
                    try:
                        pubkey_obj.verify(b32decode(signature),
                                          sign_data.encode("utf8"),
                                          padding.PKCS1v15(),
                                          hashes.SHA256())
                        # The signature was valid
                        log.debug("Found matching challenge {0!s}.".format(chal))
                        chal.set_otp_status(True)
                        chal.save()
                        result = True
                    except InvalidSignature as e:
                        pass

        else:
            raise ParameterError("Missing parameters!")

        return "json", prepare_result(result, details=details)

    @log_with(log)
    def is_challenge_request(self, passw, user=None, options=None):
        """
        check, if the request would start a challenge

        We need to define the function again, to get rid of the
        is_challenge_request-decorator of the base class

        :param passw: password, which might be pin or pin+otp
        :param options: dictionary of additional request parameters

        :return: returns true or false
        """
        return self.check_pin(passw, user=user, options=options)

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
        res = False
        options = options or {}
        message = get_action_values_from_options(SCOPE.AUTH,
                                                 ACTION.CHALLENGETEXT,
                                                 options) or DEFAULT_CHALLENGE_TEXT

        sslverify = get_action_values_from_options(SCOPE.AUTH,
                                                   PUSH_ACTION.SSL_VERIFY,
                                                   options) or "1"
        sslverify = getParam({"sslverify": sslverify}, "sslverify", allowed_values=["0", "1"], default="1")

        attributes = None
        data = None
        challenge = b32encode_and_unicode(geturandom())
        fb_identifier = self.get_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG)
        if fb_identifier:
            # We send the challenge to the Firebase service
            fb_gateway = create_sms_instance(fb_identifier)
            url = fb_gateway.smsgateway.option_dict.get(FIREBASE_CONFIG.REGISTRATION_URL)
            message_on_mobile = get_action_values_from_options(SCOPE.AUTH,
                                                   PUSH_ACTION.MOBILE_TEXT,
                                                   options) or DEFAULT_MOBILE_TEXT
            title = get_action_values_from_options(SCOPE.AUTH,
                                                   PUSH_ACTION.MOBILE_TITLE,
                                                   options) or "privacyIDEA"
            smartphone_data = {"nonce": challenge,
                               "question": message_on_mobile,
                               "serial": self.token.serial,
                               "title": title,
                               "sslverify": sslverify,
                               "url": url}
            # Create the signature.
            # value to string
            sign_string = u"{nonce}|{url}|{serial}|{question}|{title}|{sslverify}".format(**smartphone_data)

            pem_privkey = self.get_tokeninfo(PRIVATE_KEY_SERVER)
            privkey_obj = serialization.load_pem_private_key(to_bytes(pem_privkey), None, default_backend())

            # Sign the data with PKCS1 padding. Not all Androids support PSS padding.
            signature = privkey_obj.sign(sign_string.encode("utf8"),
                                         padding.PKCS1v15(),
                                         hashes.SHA256())
            smartphone_data["signature"] = b32encode_and_unicode(signature)

            res = fb_gateway.submit_message(self.get_tokeninfo("firebase_token"), smartphone_data)
            if not res:
                raise ValidateError("Failed to submit message to firebase service.")
        else:
            log.warning(u"The token {0!s} has no tokeninfo {1!s}. "
                        u"The message could not be sent.".format(self.token.serial,
                                                                 PUSH_ACTION.FIREBASE_CONFIG))
            raise ValidateError("The token has no tokeninfo. Can not send via firebase service.")

        validity = int(get_from_config('DefaultChallengeValidityTime', 120))
        tokentype = self.get_tokentype().lower()
        # Maybe there is a PushChallengeValidityTime...
        lookup_for = tokentype.capitalize() + 'ChallengeValidityTime'
        validity = int(get_from_config(lookup_for, validity))

        # Create the challenge in the database
        db_challenge = Challenge(self.token.serial,
                                 transaction_id=transactionid,
                                 challenge=challenge,
                                 data=data,
                                 session=options.get("session"),
                                 validitytime=validity)
        db_challenge.save()
        self.challenge_janitor()
        return True, message, db_challenge.transaction_id, attributes

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
        transaction_id = options.get('transaction_id')
        if transaction_id is None:
            transaction_id = options.get('state')

        # get the challenges for this transaction ID
        if transaction_id is not None:
            challengeobject_list = get_challenges(serial=self.token.serial,
                                                  transaction_id=transaction_id)

            for challengeobject in challengeobject_list:
                # check if we are still in time.
                if challengeobject.is_valid():
                    _, status = challengeobject.get_otp_status()
                    if status is True:
                        # create a positive response
                        otp_counter = 1
                        # delete the challenge, should we really delete the challenge? If we do so, the information
                        # about the successful authentication could be fetched only once!
                        # challengeobject.delete()
                        break

        return otp_counter