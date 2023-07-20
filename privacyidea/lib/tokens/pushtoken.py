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
__doc__ = """The pushtoken sends a push notification via Firebase service
to the registered smartphone.
The token is a challenge response token. The smartphone will sign the challenge
and send it back to the authentication endpoint.

This code is tested in tests/test_lib_tokens_push
"""

from base64 import b32decode
from binascii import Error as BinasciiError
from urllib.parse import quote
from datetime import datetime, timedelta
from pytz import utc
from dateutil.parser import isoparse
import traceback

from privacyidea.api.lib.utils import getParam
from privacyidea.api.lib.policyhelper import get_pushtoken_add_config
from privacyidea.lib.token import get_one_token, init_token
from privacyidea.lib.utils import prepare_result, to_bytes, is_true
from privacyidea.lib.error import (ResourceNotFoundError, ValidateError,
                                   privacyIDEAError, ConfigAdminError, PolicyError)

from privacyidea.lib.config import get_from_config
from privacyidea.lib.policy import SCOPE, ACTION, GROUP, get_action_values_from_options
from privacyidea.lib.log import log_with
from privacyidea.lib import _

from privacyidea.lib.tokenclass import (TokenClass, AUTHENTICATIONMODE, CLIENTMODE,
                                        ROLLOUTSTATE, CHALLENGE_SESSION)
from privacyidea.models import Challenge, db
from privacyidea.lib.decorators import check_token_locked
import logging
from privacyidea.lib.utils import create_img, b32encode_and_unicode
from privacyidea.lib.error import ParameterError
from privacyidea.lib.user import User
from privacyidea.lib.apps import _construct_extra_parameters
from privacyidea.lib.crypto import geturandom, generate_keypair
from privacyidea.lib.smsprovider.SMSProvider import get_smsgateway, create_sms_instance
from privacyidea.lib.challenge import get_challenges
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import time

log = logging.getLogger(__name__)

DEFAULT_CHALLENGE_TEXT = _("Please confirm the authentication on your mobile device!")
ERROR_CHALLENGE_TEXT = _("Use the polling feature of your privacyIDEA Authenticator App"
                         " to check for a new Login request.")
DEFAULT_MOBILE_TEXT = _("Do you want to confirm the login?")
PRIVATE_KEY_SERVER = "private_key_server"
PUBLIC_KEY_SERVER = "public_key_server"
PUBLIC_KEY_SMARTPHONE = "public_key_smartphone"
POLLING_ALLOWED = "polling_allowed"
GWTYPE = 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider'
ISO_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
DELAY = 1.0

# Timedelta in minutes
POLL_TIME_WINDOW = 1
UPDATE_FB_TOKEN_WINDOW = 5
POLL_ONLY = "poll only"


class PUSH_ACTION(object):
    FIREBASE_CONFIG = "push_firebase_configuration"
    REGISTRATION_URL = "push_registration_url"
    TTL = "push_ttl"
    MOBILE_TEXT = "push_text_on_mobile"
    MOBILE_TITLE = "push_title_on_mobile"
    SSL_VERIFY = "push_ssl_verify"
    WAIT = "push_wait"
    ALLOW_POLLING = "push_allow_polling"


class PushAllowPolling(object):
    ALLOW = 'allow'
    DENY = 'deny'
    TOKEN = 'token'  # nosec B105 # key name


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


def _build_smartphone_data(serial, challenge, registration_url, pem_privkey, options):
    """
    Create the dictionary to be send to the smartphone as challenge

    :param challenge: base32 encoded random data string
    :type challenge: str
    :param registration_url: The privacyIDEA URL, to which the Push token communicates
    :type registration_url: str
    :param options: the options dictionary
    :type options: dict
    :return: the created smartphone_data dictionary
    :rtype: dict
    """
    sslverify = get_action_values_from_options(SCOPE.AUTH, PUSH_ACTION.SSL_VERIFY,
                                               options) or "1"
    sslverify = getParam({"sslverify": sslverify}, "sslverify",
                         allowed_values=["0", "1"], default="1")
    message_on_mobile = get_action_values_from_options(SCOPE.AUTH,
                                                       PUSH_ACTION.MOBILE_TEXT,
                                                       options) or DEFAULT_MOBILE_TEXT
    title = get_action_values_from_options(SCOPE.AUTH, PUSH_ACTION.MOBILE_TITLE,
                                           options) or "privacyIDEA"
    smartphone_data = {"nonce": challenge,
                       "question": message_on_mobile,
                       "serial": serial,
                       "title": title,
                       "sslverify": sslverify,
                       "url": registration_url}
    # Create the signature.
    # value to string
    sign_string = "{nonce}|{url}|{serial}|{question}|{title}|{sslverify}".format(**smartphone_data)

    # Since the private key is generated by privacyIDEA and only stored
    # encrypted in the database, we can disable the costly key check here
    privkey_obj = serialization.load_pem_private_key(to_bytes(pem_privkey),
                                                     None, default_backend(),
                                                     unsafe_skip_rsa_key_validation=True)

    # Sign the data with PKCS1 padding. Not all Androids support PSS padding.
    signature = privkey_obj.sign(sign_string.encode("utf8"),
                                 padding.PKCS1v15(),
                                 hashes.SHA256())
    smartphone_data["signature"] = b32encode_and_unicode(signature)
    return smartphone_data


def _build_verify_object(pubkey_pem):
    """
    Load the given stripped and urlsafe public key and return the verify object

    :param pubkey_pem:
    :return:
    """
    # The public key of the smartphone was probably sent as urlsafe:
    pubkey_pem = pubkey_pem.replace("-", "+").replace("_", "/")
    # The public key was sent without any header
    pubkey_pem = "-----BEGIN PUBLIC KEY-----\n{0!s}\n-----END PUBLIC " \
                 "KEY-----".format(pubkey_pem.strip().replace(" ", "+"))

    return serialization.load_pem_public_key(to_bytes(pubkey_pem), default_backend())


class PushTokenClass(TokenClass):
    """
    The :ref:`push_token` uses the Firebase service to send challenges to the
    user's smartphone. The user confirms on the smartphone, signs the
    challenge and sends it back to privacyIDEA.

    The enrollment occurs in two enrollment steps:

    **Step 1**:
      The device is enrolled using a QR code, which encodes the following URI::

          otpauth://pipush/PIPU0006EF85?url=https://yourprivacyideaserver/enroll/this/token&ttl=120

    **Step 2**:
      In the QR code is a URL, where the smartphone sends the remaining data for the enrollment:

        .. sourcecode:: http

            POST /ttype/push HTTP/1.1
            Host: https://yourprivacyideaserver/

            enrollment_credential=<hex nonce>
            serial=<token serial>
            fbtoken=<Firebase token>
            pubkey=<public key>

    For more information see:

    - https://github.com/privacyidea/privacyidea/issues/1342
    - https://github.com/privacyidea/privacyidea/wiki/concept%3A-PushToken
    """
    mode = [AUTHENTICATIONMODE.AUTHENTICATE, AUTHENTICATIONMODE.CHALLENGE, AUTHENTICATIONMODE.OUTOFBAND]
    client_mode = CLIENTMODE.POLL
    # If the token is enrollable via multichallenge
    is_multichallenge_enrollable = True

    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type("push")
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
        :rtype: dict
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
                           'value': [POLL_ONLY] + [gw.identifier for gw in gws]
                       },
                       PUSH_ACTION.REGISTRATION_URL: {
                            "required": True,
                            'type': 'str',
                            'group': "PUSH",
                            'desc': _('The URL the Push App should contact in the second enrollment step.'
                                      ' Usually it is the endpoint /ttype/push of the privacyIDEA server.')
                       },
                       PUSH_ACTION.TTL: {
                           'type': 'int',
                           'group': "PUSH",
                           'desc': _('The second enrollment step must be completed within this time (in minutes).')
                       },
                       PUSH_ACTION.SSL_VERIFY: {
                           'type': 'str',
                           'desc': _('The smartphone needs to verify SSL during the enrollment. (default 1)'),
                           'group':  "PUSH",
                           'value': ["0", "1"]
                       },
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of Push tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of active Push tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       'push_' + ACTION.FORCE_APP_PIN: {
                           'type': 'bool',
                           'group': "PUSH",
                           'desc': _('Require to unlock the Smartphone before Push requests can be accepted')
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
                       },
                       PUSH_ACTION.WAIT: {
                           'type': 'int',
                           'desc': _('Wait for number of seconds for the user '
                                     'to confirm the challenge in the first request.'),
                           'group': "PUSH"
                       },
                       PUSH_ACTION.ALLOW_POLLING: {
                           'type': 'str',
                           'desc': _('Configure whether to allow push tokens to poll for '
                                     'challenges'),
                           'group': 'PUSH',
                           'value': [PushAllowPolling.ALLOW,
                                     PushAllowPolling.DENY,
                                     PushAllowPolling.TOKEN],
                           'default': PushAllowPolling.ALLOW
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
    def use_for_authentication(self, options):
        # A disabled PUSH token has to be removed from the list of checked tokens.
        return self.is_active()

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        process the initialization parameters

        We need to distinguish the first authentication step
        and the second authentication step.

        1. step:
            ``param`` contains:

            - ``type``
            - ``genkey``

        2. step:
            ``param`` contains:

            - ``serial``
            - ``fbtoken``
            - ``pubkey``

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        """
        upd_param = {}
        for k, v in param.items():
            upd_param[k] = v

        if "serial" in upd_param and "fbtoken" in upd_param and "pubkey" in upd_param:
            # We are in step 2:
            if self.token.rollout_state != ROLLOUTSTATE.CLIENTWAIT:
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
            # We also store the Firebase config, that was used during the enrollment.
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
        if self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            # Get enrollment values from the policy
            registration_url = getParam(params, PUSH_ACTION.REGISTRATION_URL, optional=False)
            ttl = getParam(params, PUSH_ACTION.TTL, default="10")
            # Get the values from the configured PUSH config
            fb_identifier = params.get(PUSH_ACTION.FIREBASE_CONFIG)
            if fb_identifier != POLL_ONLY:
                # If do not do poll_only, then we load all the Firebase configuration
                firebase_configs = get_smsgateway(identifier=fb_identifier, gwtype=GWTYPE)
                if len(firebase_configs) != 1:
                    raise ParameterError("Unknown Firebase configuration!")
            # this allows to upgrade our crypto
            extra_data["v"] = 1
            extra_data["serial"] = self.get_serial()
            extra_data["sslverify"] = sslverify

            # enforce App pin
            if params.get(ACTION.FORCE_APP_PIN):
                extra_data.update({'pin': True})

            # We display this during the first enrollment step!
            qr_url = create_push_token_url(url=registration_url,
                                           user=user.login,
                                           realm=user.realm,
                                           serial=self.get_serial(),
                                           tokenlabel=tokenlabel,
                                           issuer=tokenissuer,
                                           user_obj=user,
                                           extra_data=extra_data,
                                           ttl=ttl)
            response_detail["pushurl"] = {"description": _("URL for privacyIDEA Push Token"),
                                          "value": qr_url,
                                          "img": create_img(qr_url)
                                          }

            response_detail["enrollment_credential"] = self.get_tokeninfo("enrollment_credential")

        elif self.token.rollout_state == ROLLOUTSTATE.ENROLLED:
            # in the second enrollment step we return the public key of the server to the smartphone.
            pubkey = strip_key(self.get_tokeninfo(PUBLIC_KEY_SERVER))
            response_detail["public_key"] = pubkey

        return response_detail

    @staticmethod
    def _check_timestamp_in_range(timestamp, window):
        """ Check if the timestamp is a valid timestamp and if it matches the time window.

        If the check fails a privacyIDEA error is thrown.

        :param timestamp: A timestamp in iso format, either with a timezone or UTC is assumed
        :type timestamp: str
        :param window: Time window in minutes. The timestamp must lie within the
                       range of -window to +window of the current time.
        :type window: int
        """
        try:
            ts = isoparse(timestamp)
        except (ValueError, TypeError) as _e:
            log.debug('{0!s}'.format(traceback.format_exc()))
            raise privacyIDEAError('Could not parse timestamp {0!s}. '
                                   'ISO-Format required.'.format(timestamp))
        td = timedelta(minutes=window)
        # We don't know if the passed timestamp is timezone aware. If no
        # timezone is passed, we assume UTC
        if ts.tzinfo:
            now = datetime.now(utc)
        else:
            now = datetime.utcnow()
        if not (now - td <= ts <= now + td):
            raise privacyIDEAError('Timestamp {0!s} not in valid range.'.format(timestamp))

    @classmethod
    def _api_endpoint_post(cls, request_data):
        """ Handle all POST requests to the api endpoint

        :param request_data: Dictionary containing the parameters of the request
        :type request_data: dict
        :returns: The result of handling the request and a dictionary containing
                  the details of the request handling
        :rtype: (bool, dict)
        """
        details = {}
        result = False

        serial = getParam(request_data, "serial", optional=False)
        if all(k in request_data for k in ("fbtoken", "pubkey")):
            log.debug("Do the 2nd step of the enrollment.")
            try:
                token_obj = get_one_token(serial=serial,
                                          tokentype="push",
                                          rollout_state=ROLLOUTSTATE.CLIENTWAIT)
                token_obj.update(request_data)
                # in case of validate/check enrollment
                chals = get_challenges(serial=serial)
                if chals and chals[0].is_valid() and chals[0].get_session() == CHALLENGE_SESSION.ENROLLMENT:
                    chals[0].set_otp_status(True)
                    chals[0].save()
            except ResourceNotFoundError:
                raise ResourceNotFoundError("No token with this serial number "
                                            "in the rollout state 'clientwait'.")
            init_detail_dict = request_data

            details = token_obj.get_init_detail(init_detail_dict)
            result = True
        elif all(k in request_data for k in ("nonce", "signature")):
            log.debug("Handling the authentication response from the smartphone.")
            challenge = getParam(request_data, "nonce")
            signature = getParam(request_data, "signature")
            decline = is_true(getParam(request_data, "decline", default=False))

            # get the token_obj for the given serial:
            token_obj = get_one_token(serial=serial, tokentype="push")
            pubkey_obj = _build_verify_object(token_obj.get_tokeninfo(PUBLIC_KEY_SMARTPHONE))
            # Do the 2nd step of the authentication
            # Find valid challenges
            challengeobject_list = get_challenges(serial=serial, challenge=challenge)

            if challengeobject_list:
                # There are valid challenges, so we check this signature
                for chal in challengeobject_list:
                    # verify the signature of the nonce
                    sign_data = "{0!s}|{1!s}".format(challenge, serial)
                    if decline:
                        sign_data += "|decline"
                    try:
                        pubkey_obj.verify(b32decode(signature),
                                          sign_data.encode("utf8"),
                                          padding.PKCS1v15(),
                                          hashes.SHA256())
                        # The signature was valid
                        log.debug("Found matching challenge {0!s}.".format(chal))
                        if decline:
                            chal.set_data("challenge_declined")
                        else:
                            chal.set_otp_status(True)
                            chal.save()
                        result = True
                    except InvalidSignature as _e:
                        pass
        elif all(k in request_data for k in ('new_fb_token', 'timestamp', 'signature')):
            timestamp = getParam(request_data, 'timestamp', optional=False)
            signature = getParam(request_data, 'signature', optional=False)
            # first check if the timestamp is in the required span
            cls._check_timestamp_in_range(timestamp, UPDATE_FB_TOKEN_WINDOW)
            try:
                tok = get_one_token(serial=serial, tokentype=cls.get_class_type())
                pubkey_obj = _build_verify_object(tok.get_tokeninfo(PUBLIC_KEY_SMARTPHONE))
                sign_data = "{new_fb_token}|{serial}|{timestamp}".format(**request_data)
                pubkey_obj.verify(b32decode(signature),
                                  sign_data.encode("utf8"),
                                  padding.PKCS1v15(),
                                  hashes.SHA256())
                # If the timestamp and signature are valid we update the token
                tok.add_tokeninfo('firebase_token', request_data['new_fb_token'])
                result = True
            except (ResourceNotFoundError, ParameterError, TypeError,
                    InvalidSignature, ConfigAdminError, BinasciiError) as e:
                # to avoid disclosing information we always fail with an invalid
                # signature error even if the token with the serial could not be found
                log.debug('{0!s}'.format(traceback.format_exc()))
                log.info('The following error occurred during the signature '
                         'check: "{0!r}"'.format(e))
                raise privacyIDEAError('Could not verify signature!')
        else:
            raise ParameterError("Missing parameters!")

        return result, details

    @classmethod
    def _api_endpoint_get(cls, g, request_data):
        """ Handle all GET requests to the api endpoint.

        Currently this is only used for polling.
        :param g: The Flask context
        :param request_data: Dictionary containing the parameters of the request
        :type request_data: dict
        :returns: Result of the polling operation, 'True' if an unanswered and
                  matching challenge exists, 'False' otherwise.
        :rtype: bool
        """
        # By default we allow polling if the policy is not set.
        allow_polling = get_action_values_from_options(
            SCOPE.AUTH, PUSH_ACTION.ALLOW_POLLING,
            options={'g': g}) or PushAllowPolling.ALLOW
        if allow_polling == PushAllowPolling.DENY:
            raise PolicyError('Polling not allowed!')
        serial = getParam(request_data, "serial", optional=False)
        timestamp = getParam(request_data, 'timestamp', optional=False)
        signature = getParam(request_data, 'signature', optional=False)
        # first check if the timestamp is in the required span
        cls._check_timestamp_in_range(timestamp, POLL_TIME_WINDOW)
        # now check the signature
        # first get the token
        try:
            tok = get_one_token(serial=serial, tokentype=cls.get_class_type())
            # If the push_allow_polling policy is set to "token" we also
            # need to check the POLLING_ALLOWED tokeninfo. If it evaluated
            # to 'False', polling is not allowed for this token. If the
            # tokeninfo value evaluates to 'True' or is not set at all,
            # polling is allowed for this token.
            if allow_polling == PushAllowPolling.TOKEN:
                if not is_true(tok.get_tokeninfo(POLLING_ALLOWED, default='True')):
                    log.debug('Polling not allowed for pushtoken {0!s} due to '
                              'tokeninfo.'.format(serial))
                    raise PolicyError('Polling not allowed!')

            pubkey_obj = _build_verify_object(tok.get_tokeninfo(PUBLIC_KEY_SMARTPHONE))
            sign_data = "{serial}|{timestamp}".format(**request_data)
            pubkey_obj.verify(b32decode(signature),
                              sign_data.encode("utf8"),
                              padding.PKCS1v15(),
                              hashes.SHA256())
            # The signature was valid now check for an open challenge
            # we need the private server key to sign the smartphone data
            pem_privkey = tok.get_tokeninfo(PRIVATE_KEY_SERVER)
            # We need the registration URL for the challenge
            registration_url = get_action_values_from_options(
                SCOPE.ENROLL, PUSH_ACTION.REGISTRATION_URL, options={'g': g})
            if not registration_url:
                raise ResourceNotFoundError('There is no registration_url defined for the '
                                            ' pushtoken {0!s}. You need to define a push_registration_url '
                                            'in an enrollment policy.'.format(serial))
            options = {'g': g}
            challenges = []
            challengeobject_list = get_challenges(serial=serial)
            for chal in challengeobject_list:
                # check if the challenge is active and not already answered
                _cnt, answered = chal.get_otp_status()
                if not answered and chal.is_valid():
                    # then return the necessary smartphone data to answer
                    # the challenge
                    sp_data = _build_smartphone_data(serial, chal.challenge,
                                                     registration_url, pem_privkey, options)
                    challenges.append(sp_data)
            # return the challenges as a list in the result value
            result = challenges
        except (ResourceNotFoundError, ParameterError,
                InvalidSignature, ConfigAdminError, BinasciiError) as e:
            # to avoid disclosing information we always fail with an invalid
            # signature error even if the token with the serial could not be found
            log.debug('{0!s}'.format(traceback.format_exc()))
            log.info('The following error occurred during the signature '
                     'check: "{0!r}"'.format(e))
            raise privacyIDEAError('Could not verify signature!')

        return result

    @classmethod
    def api_endpoint(cls, request, g):
        """
        This provides a function which is called by the API endpoint
        ``/ttype/push`` which is defined in :doc:`../../api/ttype`

        The method returns a tuple ``("json", {})``

        This endpoint provides several functionalities:

        - It is used for the 2nd enrollment step of the smartphone.
          It accepts the following parameters:

            .. sourcecode:: http

              POST /ttype/push HTTP/1.1
              Host: https://yourprivacyideaserver

              serial=<token serial>
              fbtoken=<Firebase token>
              pubkey=<public key>

        - It is also used when the smartphone sends the signed response
          to the challenge during authentication. The following parameters are accepted:

            .. sourcecode:: http

              POST /ttype/push HTTP/1.1
              Host: https://yourprivacyideaserver

              serial=<token serial>
              nonce=<the actual challenge>
              signature=<signature over {nonce}|{serial}>

        - The smartphone can also decline the authentication request, by sending
          a response to the server:

            .. sourcecode:: http

              POST /ttype/push HTTP/1.1
              Host: https://yourprivacyideaserver

              serial=<token serial>
              nonce=<the actual challenge>
              decline=1
              signature=<signature over {nonce}|{serial}|decline

        - In some cases the Firebase service changes the token of a device. This
          needs to be communicated to privacyIDEA through this endpoint
          (https://github.com/privacyidea/privacyidea/wiki/concept%3A-pushtoken-poll#update
          -firebase-token):

            .. sourcecode:: http

              POST /ttype/push HTTP/1.1
              Host: https://yourprivacyideaserver

              new_fb_token=<new Firebase token>
              serial=<token serial>
              timestamp=<timestamp>
              signature=SIGNATURE(<new_fb_token>|<serial>|<timestamp>)

        - And it also acts as an endpoint for polling challenges:

            .. sourcecode:: http

              GET /ttype/push HTTP/1.1
              Host: https://yourprivacyideaserver

              serial=<tokenserial>
              timestamp=<timestamp>
              signature=SIGNATURE(<tokenserial>|<timestamp>)

          More on polling can be found here: https://github.com/privacyidea/privacyidea/wiki/concept%3A-pushtoken-poll

        :param request: The Flask request
        :param g: The Flask global object g
        :return: The json string representing the result dictionary
        :rtype: tuple("json", str)
        """
        details = {}
        if request.method == 'POST':
            result, details = cls._api_endpoint_post(request.all_data)
        elif request.method == 'GET':
            result = cls._api_endpoint_get(g, request.all_data)
        else:
            raise privacyIDEAError('Method {0!s} not allowed in \'api_endpoint\' '
                                   'for push token.'.format(request.method))

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
        if options.get(PUSH_ACTION.WAIT):
            # We have a push_wait in the parameters
            return False
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
        additional challenge ``reply_dict``, which are displayed in the JSON challenges response.
        """
        options = options or {}
        message = get_action_values_from_options(SCOPE.AUTH,
                                                 ACTION.CHALLENGETEXT,
                                                 options) or DEFAULT_CHALLENGE_TEXT

        data = None
        # Initially we assume there is no error from Firebase
        res = True
        fb_identifier = self.get_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG)
        if fb_identifier:
            challenge = b32encode_and_unicode(geturandom())
            if options.get("session") != CHALLENGE_SESSION.ENROLLMENT:
                if fb_identifier != POLL_ONLY:
                    # We only push to Firebase if this tokens does NOT POLL_ONLY.
                    fb_gateway = create_sms_instance(fb_identifier)
                    registration_url = get_action_values_from_options(
                        SCOPE.ENROLL, PUSH_ACTION.REGISTRATION_URL, options=options)
                    pem_privkey = self.get_tokeninfo(PRIVATE_KEY_SERVER)
                    smartphone_data = _build_smartphone_data(self.token.serial,
                                                             challenge, registration_url,
                                                             pem_privkey, options)
                    res = fb_gateway.submit_message(self.get_tokeninfo("firebase_token"), smartphone_data)

            # Create the challenge in the challenge table if either the message
            # was successfully submitted to the Firebase API or if polling is
            # allowed in general or for this specific token.
            allow_polling = get_action_values_from_options(
                SCOPE.AUTH, PUSH_ACTION.ALLOW_POLLING, options=options) or PushAllowPolling.ALLOW
            if ((allow_polling == PushAllowPolling.ALLOW or
                 (allow_polling == PushAllowPolling.TOKEN and
                  is_true(self.get_tokeninfo(POLLING_ALLOWED, default='True')))) or res):
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
                transactionid = db_challenge.transaction_id

            # If sending the Push message failed, we log a warning
            if not res:
                log.warning("Failed to submit message to Firebase service for token {0!s}."
                            .format(self.token.serial))
                message += " " + ERROR_CHALLENGE_TEXT
                if is_true(options.get("exception")):
                    raise ValidateError("Failed to submit message to Firebase service.")
        else:
            log.warning("The token {0!s} has no tokeninfo {1!s}. "
                        "The message could not be sent.".format(self.token.serial,
                                                                 PUSH_ACTION.FIREBASE_CONFIG))
            message += " " + ERROR_CHALLENGE_TEXT
            if is_true(options.get("exception")):
                raise ValidateError("The token has no tokeninfo. Can not send via Firebase service.")

        reply_dict = {"attributes": {"hideResponseInput": self.client_mode != CLIENTMODE.INTERACTIVE}}
        return True, message, transactionid, reply_dict

    @check_token_locked
    def authenticate(self, passw, user=None, options=None):
        """
        High level interface which covers the check_pin and check_otp
        This is the method that verifies single shot authentication.
        The challenge is send to the smartphone app and privacyIDEA
        waits for the response to arrive.

        :param passw: the password which could be pin+otp value
        :type passw: string
        :param user: The authenticating user
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: returns tuple of

          1. true or false for the pin match,
          2. the otpcounter (int) and the
          3. reply (dict) that will be added as additional information in the
             JSON response of ``/validate/check``.

        :rtype: tuple
        """
        otp_counter = -1
        reply = None
        pin_match = self.check_pin(passw, user=user, options=options)
        if pin_match:
            if not options.get("valid_token_num"):
                # We should only do push_wait, if we do not already have successfully authenticated tokens!
                waiting = int(options.get(PUSH_ACTION.WAIT, 20))
                # Trigger the challenge
                _t, _m, transaction_id, _attr = self.create_challenge(options=options)
                # now we need to check and wait for the response to be answered in the challenge table
                starttime = time.time()
                while True:
                    db.session.commit()
                    otp_counter = self.check_challenge_response(options={"transaction_id": transaction_id})
                    elapsed_time = time.time() - starttime
                    if otp_counter >= 0 or elapsed_time > waiting or elapsed_time < 0:
                        break
                    time.sleep(DELAY - (elapsed_time % DELAY))

        return pin_match, otp_counter, reply

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

    @classmethod
    def enroll_via_validate(cls, g, content, user_obj):
        """
        This class method is used in the policy ENROLL_VIA_MULTICHALLENGE.
        It enrolls a new token of this type and returns the necessary information
        to the client by modifying the content.

        :param g: context object
        :param content: The content of a response
        :param user_obj: A user object
        :return: None, the content is modified
        """
        # Get the firebase configuration from the policies
        params = get_pushtoken_add_config(g, user_obj=user_obj)
        token_obj = init_token({"type": cls.get_class_type(),
                                "genkey": 1,
                                "2stepinit": 1}, user=user_obj)
        # We are in step 1:
        token_obj.add_tokeninfo("enrollment_credential", geturandom(20, hex=True))
        # We also store the Firebase config, that was used during the enrollment.
        token_obj.add_tokeninfo(PUSH_ACTION.FIREBASE_CONFIG, params.get(PUSH_ACTION.FIREBASE_CONFIG))
        content.get("result")["value"] = False
        content.get("result")["authentication"] = "CHALLENGE"

        detail = content.setdefault("detail", {})
        # Create a challenge!
        c = token_obj.create_challenge(options={"session": CHALLENGE_SESSION.ENROLLMENT})
        # get details of token
        init_details = token_obj.get_init_detail(params=params)
        detail["transaction_ids"] = [c[2]]
        chal = {"transaction_id": c[2],
                "image": init_details.get("pushurl", {}).get("img"),
                "client_mode": CLIENTMODE.POLL,
                "serial": token_obj.token.serial,
                "type": token_obj.type,
                "message": _("Please scan the QR code!")}
        detail["multi_challenge"] = [chal]
        detail.update(chal)
