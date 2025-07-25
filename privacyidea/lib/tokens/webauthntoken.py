# 2020-01-13 Jean-Pierre Höhmann <jean-pierre.hoehmann@netknights.it>
#
# License:  AGPLv3
# Contact:  https://www.privacyidea.org
#
# Copyright (C) 2020 NetKnights GmbH
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
import binascii
import logging

from cryptography import x509
from webauthn.helpers import bytes_to_base64url

from privacyidea.api.lib.utils import (attestation_certificate_allowed, get_required_one_of,
                                       get_optional_one_of, get_optional, get_required)
from privacyidea.lib import _, lazy_gettext
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import get_from_config
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.error import ParameterError, EnrollmentError, PolicyError, ERROR
from privacyidea.lib.fido2.config import FIDO2ConfigOptions
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.fido2.token_info import FIDO2TokenInfo
from privacyidea.lib.fido2.util import hash_credential_id, save_credential_id_hash
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import SCOPE, GROUP, ACTION
from privacyidea.lib.token import get_tokens
from privacyidea.lib.tokenclass import TokenClass, CLIENTMODE, ROLLOUTSTATE
from privacyidea.lib.tokens.u2ftoken import IMAGES
from privacyidea.lib.tokens.webauthn import (CoseAlgorithm, webauthn_b64_encode, WebAuthnRegistrationResponse,
                                             ATTESTATION_REQUIREMENT_LEVEL, webauthn_b64_decode,
                                             WebAuthnMakeCredentialOptions, WebAuthnAssertionOptions, WebAuthnUser,
                                             WebAuthnAssertionResponse, AuthenticationRejectedException,
                                             UserVerificationLevel)
from privacyidea.lib.user import User
from privacyidea.lib.utils import hexlify_and_unicode, is_true, convert_imagefile_to_dataimage

__doc__ = """
WebAuthn  is the Web Authentication API specified by the FIDO Alliance.
The register and authentication process is described here:

https://w3c.github.io/webauthn/#sctn-rp-operations

But you do not need to be aware of this. privacyIDEA wraps all FIDO specific
communication, which should make it easier for you, to integrate the U2F
tokens managed by privacyIDEA into your application.

WebAuthn tokens can be either

 * registered by administrators for users or
 * registered by the users themselves.

Be aware that WebAuthn tokens can only be used if the privacyIDEA server and
the applications and services the user needs to access all reside under the
same domain or subdomains thereof.

This means a WebAuthn token registered by privacyidea.mycompany.com can be
used to sign in to sites like mycompany.com and vpn.mycompany.com, but not
(for example) mycompany.someservice.com.

Enrollment
----------
The enrollment/registering can be completely performed within privacyIDEA.

But if you want to enroll the WebAuthn token via the REST API you need to do
it in two steps:

**Step 1**

.. sourcecode:: http

    POST /token/init HTTP/1.1
    Host: <privacyIDEA server>
    Accept: application/json

    type=webauthn
    user=<username>

The request returns:

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "detail": {
            "serial": "<serial number>",
            "webAuthnRegisterRequest": {
                "attestation": "direct",
                "authenticatorSelection": {
                    "userVerification": "preferred"
                },
                "displayName": "<user.resolver@realm>",
                "message": "Please confirm with your WebAuthn token",
                "name": "<username>",
                "nonce": "<nonce>",
                "pubKeyCredAlgorithms": [
                    {
                        "alg": -7,
                        "type": "public-key"
                    },
                    {
                        "alg": -37,
                        "type": "public-key"
                    }
                ],
                "relyingParty": {
                    "id": "<relying party ID>",
                    "name": "<relying party name>"
                },
                "serialNumber": "<serial number>",
                "timeout": 60000,
                "transaction_id": "<transaction ID>"
            }
        },
        "result": {
            "status": true,
            "value": true
        },
        "version": "<privacyIDEA version>"
    }

This step returns a *webAuthnRegisterRequest* which contains a nonce, a relying party (containing a
name and an ID generated from your domain), a serial number along with a transaction ID
and a message to display to the user. It will also contain some additional options
regarding timeout, which authenticators are acceptable, and what key types are
acceptable to the server.

With the received data You need to call the javascript function

.. sourcecode:: javascript

    navigator
        .credentials
        .create({
            challenge: <nonce>,
            rp: <relyingParty>,
            user: {
                id: Uint8Array.from(<serialNumber>, c => c.charCodeAt(0)),
                name: <name>,
                displayName: <displayName>
            },
            pubKeyCredParams: <pubKeyCredAlgorithms>,
            authenticatorSelection: <authenticatorSelection>,
            timeout: <timeout>,
            attestation: <attestation>,
            extensions: {
                authnSel: <authenticatorSelectionList>
            }
        })
        .then(function(credential) { <responseHandler> })
        .catch(function(error) { <errorHandler> });

Here *nonce*, *relyingParty*, *serialNumber*, *pubKeyCredAlgorithms*,
*authenticatorSelection*, *timeout*, *attestation*,
*authenticatorSelectionList*, *name*, and *displayName* are the values
provided by the server in the *webAuthnRegisterRequest* field in the response
from the first step. *authenticatorSelection*,
*timeout*, *attestation*, and *authenticatorSelectionList* are optional. If
*attestation* is not provided, the client should default to `direct`
attestation. If *timeout* is not provided, it may be omitted, or a sensible
default chosen. Any other optional values must be omitted, if the server has
not sent them. Please note that the nonce will be a binary, encoded using the
web-safe base64 algorithm specified by WebAuthn, and needs to be decoded and
passed as Uint8Array.

If an *authenticationSelectionList* was given, the *responseHandler* needs to
verify, that the field *authnSel* of *credential.getExtensionResults()*
contains true. If this is not the case, the *responseHandler* should abort and
call the *errorHandler*, displaying an error telling the user to use his
company-provided token.

The *responseHandler* needs to then send the *clientDataJSON*,
*attestationObject*, and *registrationClientExtensions* contained in the
*response* field of the *credential* back to the server. If
enrollment succeeds, the server will send a response with a
*webAuthnRegisterResponse* field, containing a *subject* field with the
description of the newly created token.


**Step 2**

.. sourcecode:: http

    POST /token/init HTTP/1.1
    Host: <privacyIDEA server>
    Accept: application/json

    type=webauthn
    transaction_id=<transaction_id>
    description=<description>
    clientdata=<clientDataJSON>
    regdata=<attestationObject>
    registrationclientextensions=<registrationClientExtensions>

The values *clientDataJSON* and *attestationObject* are returned by the
WebAuthn authenticator. *description* is an optional description string for
the new token.

The server expects the *clientDataJSON* and *attestationObject* encoded as
web-safe base64 as defined by the WebAuthn standard. This encoding is similar
to standard base64, but '-' and '_' should be used in the alphabet instead of
'+' and '/', respectively, and any padding should be omitted.

The *registrationClientExtensions* are optional and should simply be omitted,
if the client does not provide them. If the *registrationClientExtensions* are
available, they must be encoded as a utf-8 JSON string, then sent to the server
as web-safe base64.

Please beware that the btoa() function provided by
ECMA-Script expects a 16-bit encoded string where all characters are in the
range 0x0000 to 0x00FF. The *attestationObject* contains CBOR-encoded binary
data, returned as an ArrayBuffer.

The problem and ways to solve it are described in detail in this MDN-Article:

https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding#The_Unicode_Problem

Authentication
--------------

The WebAuthn token is a challenge response token. I.e. you need to trigger a
challenge, either by sending the OTP PIN/Password for this token to the
/validate/check endpoint, or by calling the /validate/triggerchallenge
endpoint using a service account with sufficient permissions.

Get the challenge (using /validate/check)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The /validate/check endpoint can be used to trigger a challenge using the PIN
for the token (without requiring any special permissions).

**Request:**

.. sourcecode:: http

    POST /validate/check HTTP/1.1
    Host: <privacyIDEA server>
    Accept: application/json

    user=<username>
    pass=<password>

**Response:**

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "detail": {
            "attributes": {
                "hideResponseInput": true,
                "img": "<image URL>",
                "webAuthnSignRequest": {
                    "allowCredentials": [
                        {
                            "id": "<credential ID>",
                            "transports": [
                                "<allowed transports>"
                            ],
                            "type": "<credential type>"
                        }
                    ],
                    "challenge": "<nonce>",
                    "rpId": "<relying party ID>",
                    "timeout": 60000,
                    "userVerification": "<user verification requirement>"
                }
            },
            "client_mode": "webauthn",
            "message": "Please confirm with your WebAuthn token",
            "serial": "<token serial>",
            "transaction_id": "<transaction ID>",
            "type": "webauthn"
        },
        "id": 1,
        "jsonrpc": "2.0",
        "result": {
            "authentication": "CHALLENGE",
            "status": true,
            "value": false
        },
        "version": "<privacyIDEA version>"
    }


Get the challenge (using /validate/triggerchallenge)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The /validate/triggerchallenge endpoint can be used to trigger a challenge
using a service account (without requiring the PIN for the token).

**Request**

.. sourcecode:: http

    POST /validate/triggerchallenge HTTP/1.1
    Host: <privacyIDEA server>
    Accept: application/json
    PI-Authorization: <authToken>

    user=<username>
    serial=<tokenSerial>

Providing the *tokenSerial* is optional. If just a user is provided, a
challenge will be triggered for every challenge response token the user has.

**Response**

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "detail": {
            "attributes": {
                "hideResponseInput": true,
                "img": "<image URL>",
                "webAuthnSignRequest": {
                    "challenge": "<nonce>",
                    "allowCredentials": [{
                        "id": "<credential ID>",
                        "transports": [
                            "<allowed transports>"
                        ],
                        "type": "<credential type>",
                    }],
                    "rpId": "<relying party ID>",
                    "userVerification": "<user verification requirement>",
                    "timeout": 60000
                }
            },
            "message": "Please confirm with your WebAuthn token",
            "messages": ["Please confirm with your WebAuthn token"],
            "multi_challenge": [{
                "attributes": {
                    "hideResponseInput": true,
                    "img": "<image URL>",
                    "webAuthnSignRequest": {
                        "challenge": "<nonce>",
                        "allowCredentials": [{
                            "id": "<credential ID>",
                            "transports": [
                                "<allowedTransports>"
                            ],
                            "type": "<credential type>",
                        }],
                        "rpId": "<relying party ID>",
                        "userVerification": "<user verification requirement>",
                        "timeout": 60000
                    }
                },
                "message": "Please confirm with your WebAuthn token",
                "serial": "<token serial>",
                "transaction_id": "<transaction ID>",
                "type": "webauthn"
            }],
            "serial": "<token serial>",
            "transaction_id": "<transaction ID>",
            "transaction_ids": ["<transaction IDs>"],
            "type": "webauthn"
        },
        "id": 1,
        "jsonrpc": "2.0",
        "result": {
            "status": true,
            "value": 1
        },
        "version": "<privacyIDEA version>"
    }

Send the Response
~~~~~~~~~~~~~~~~~

The application now needs to call the javascript function
*navigator.credentials.get* with the *publicKeyCredentialRequestOptions* built
using the *nonce*, *credentialId*, *allowedTransports*, *userVerificationRequirement*
and *timeout* from the server.  The timeout is optional and may be omitted, if
not provided, the client may also pick a sensible default. Please note that the
nonce will be a binary, encoded using the web-safe base64 algorithm specified by
WebAuthn, and needs to be decoded and passed as Uint8Array.

.. sourcecode:: javascript

    const publicKeyCredentialRequestOptions = {
        challenge: <nonce>,
        allowCredentials: [{
            id: Uint8Array.from(<credentialId>, c=> c.charCodeAt(0)),
            type: <credentialType>,
            transports: <allowedTransports>
        }],
        userVerification: <userVerificationRequirement>,
        rpId: <relyingPartyId>,
        timeout: <timeout>
    }
    navigator
        .credentials
        .get({publicKey: publicKeyCredentialRequestOptions})
        .then(function(assertion) { <responseHandler> })
        .catch(function(error) { <errorHandler> });

The *responseHandler* needs to call the */validate/check* API providing the
*serial* of the token the user is signing in with, and the *transaction_id*,
for the current challenge, along with the *id*, returned by the WebAuthn
device in the *assertion* and the *authenticatorData*, *clientDataJSON* and
*signature*, *userHandle*, and *assertionClientExtensions* contained in the
*response* field of the *assertion*.

*clientDataJSON*, *authenticatorData* and *signature* should be encoded as
web-safe base64 without padding. For more detailed instructions, refer to
“2. Step” under “Enrollment” above.

The *userHandle* and *assertionClientExtensions* are optional and should be
omitted, if not provided by the authenticator. The
*assertionClientExtensions* – if available – must be encoded as a utf-8 JSON
string, and transmitted to the server as web-safe base64. The *userHandle*
is simply passed as a string, note – however – that it may be necessary to
re-encode this to utf-16, since the authenticator will return utf-8, while the
library making the http request will likely require all parameters in the
native encoding of the language (usually utf-16).

.. sourcecode:: http

    POST /validate/check HTTP/1.1
    Host: example.com
    Accept: application/json

    user=<user>
    pass=
    transaction_id=<transaction_id>
    credentialid=<id>
    clientdata=<clientDataJSON>
    signaturedata=<signature>
    authenticatordata=<authenticatorData>
    userhandle=<userHandle>
    assertionclientextensions=<assertionClientExtensions>

"""

from privacyidea.models import Challenge, TokenCredentialIdHash

IMAGES = IMAGES

DEFAULT_DESCRIPTION = lazy_gettext('Generic WebAuthn Token')

# Policy defaults
DEFAULT_ALLOWED_TRANSPORTS = "usb ble nfc internal"
DEFAULT_TIMEOUT = 60
DEFAULT_USER_VERIFICATION_REQUIREMENT = 'preferred'
DEFAULT_AUTHENTICATOR_ATTACHMENT = 'either'
DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE = ['ecdsa', 'rsassa-pss', 'rsassa-pkcs1v1_5']
DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL = 'untrusted'
DEFAULT_AUTHENTICATOR_ATTESTATION_FORM = 'direct'
DEFAULT_CHALLENGE_TEXT_AUTH = lazy_gettext('Please confirm with your WebAuthn token ({0!s})')
DEFAULT_CHALLENGE_TEXT_ENROLL = lazy_gettext('Please confirm with your WebAuthn token')

PUBLIC_KEY_CREDENTIAL_ALGORITHMS = {
    'ecdsa': CoseAlgorithm.ES256,
    'rsassa-pss': CoseAlgorithm.PS256,
    'rsassa-pkcs1v1_5': CoseAlgorithm.RS256
}
# since in Python < 3.7 the insert order of a dictionary is not guaranteed, we
# need a list to define the proper order
PUBKEY_CRED_ALGORITHMS_ORDER = ['ecdsa', 'rsassa-pss', 'rsassa-pkcs1v1_5']

log = logging.getLogger(__name__)
optional = True
required = False

WEBAUTHN_TOKEN_SPECIFIC_SETTINGS = {
    FIDO2ConfigOptions.TRUST_ANCHOR_DIR: 'public',
    FIDO2ConfigOptions.APP_ID: 'public'
}


class WebAuthnGroup(object):
    """
    Categories used to group WebAuthn token actions.
    """

    WEBAUTHN = "WebAuthn"


class WebAuthnTokenClass(TokenClass):
    """
    The WebAuthn Token implementation.
    """

    client_mode = CLIENTMODE.WEBAUTHN

    @staticmethod
    def _get_challenge_validity_time():
        return int(get_from_config(FIDO2ConfigOptions.CHALLENGE_VALIDITY_TIME,
                                   get_from_config('DefaultChallengeValidityTime', 120)))

    @staticmethod
    def _get_nonce():
        return geturandom(32)

    @staticmethod
    def get_class_type():
        """
        Returns the internal token type identifier

        :return: webauthn
        :rtype: basestring
        """
        return "webauthn"

    @staticmethod
    def get_class_prefix():
        """
        Return the prefix, that is used as a prefix for the serial numbers.

        :return: WAN
        :rtype: basestring
        """
        return "WAN"

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
        res = {
            'type': 'webauthn',
            'title': 'WebAuthn Token',
            'description': _('WebAuthn: Enroll a Web Authentication token.'),
            'init': {},
            'config': {},
            'user': ['enroll'],
            # This tokentype is enrollable in the UI for...
            'ui_enroll': ["admin", "user"],
            'policy': {
                SCOPE.AUTH: {
                    FIDO2PolicyAction.ALLOWED_TRANSPORTS: {
                        'type': 'str',
                        'desc': _("A list of transports to prefer to communicate with WebAuthn tokens. "
                                  "Default: usb ble nfc internal (All standard transports)")
                    },
                    FIDO2PolicyAction.TIMEOUT: {
                        'type': 'int',
                        'desc': _("The time in seconds the user has to confirm authorization on his WebAuthn token. "
                                  "Note: You will want to increase the ChallengeValidityTime along with this. "
                                  "Default: 60")
                    },
                    FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT: {
                        'type': 'str',
                        'desc': _("Whether the user's identity should be verified when authenticating with a WebAuthn "
                                  "token. Default: preferred (verify the user if supported by the token)"),
                        'value': [
                            'required',
                            'preferred',
                            'discouraged'
                        ]
                    },
                    ACTION.CHALLENGETEXT: {
                        'type': 'str',
                        'desc': _("Use an alternative challenge text for telling "
                                  "the user to confirm the login with his WebAuthn token. "
                                  "You can also use tags for automated replacement. "
                                  "Check out the documentation for more details.")
                    }
                },
                SCOPE.AUTHZ: {
                    FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST: {
                        'type': 'str',
                        'desc': _("A list of WebAuthn authenticators acceptable for authorization, given as "
                                  "a space-separated list of AAGUIDs. Per default all authenticators are acceptable."),
                        'group': GROUP.CONDITIONS,
                    },
                    FIDO2PolicyAction.REQ: {
                        'type': 'str',
                        'desc': _("Only the specified WebAuthn-tokens are authorized."),
                        'group': GROUP.CONDITIONS,
                    }
                },
                SCOPE.ENROLL: {
                    FIDO2PolicyAction.AVOID_DOUBLE_REGISTRATION: {
                        'type': 'bool',
                        'desc': _("One webauthn token can not be registered to a user more than once."),
                        'group': WebAuthnGroup.WEBAUTHN
                    },
                    FIDO2PolicyAction.RELYING_PARTY_NAME: {
                        'type': 'str',
                        'desc': _("A human-readable name for the organization rolling out WebAuthn tokens."),
                        'group': WebAuthnGroup.WEBAUTHN
                    },
                    FIDO2PolicyAction.RELYING_PARTY_ID: {
                        'type': 'str',
                        'desc': _("A domain name that is a subset of the respective FQDNs for all the webservices the "
                                  "users should be able to sign in to using WebAuthn tokens."),
                        'group': WebAuthnGroup.WEBAUTHN
                    },
                    FIDO2PolicyAction.TIMEOUT: {
                        'type': 'int',
                        'desc': _("The time in seconds the user has to confirm enrollment on his WebAuthn token. "
                                  "Note: You will want to increase the ChallengeValidityTime along with this. "
                                  "Default: 60"),
                        'group': WebAuthnGroup.WEBAUTHN
                    },
                    FIDO2PolicyAction.AUTHENTICATOR_ATTACHMENT: {
                        'type': 'str',
                        'desc': _("Whether to limit roll out of WebAuthn tokens to either only platform "
                                  "authenticators, or only cross-platform authenticators. Default: either"),
                        'group': WebAuthnGroup.WEBAUTHN,
                        'value': [
                            "platform",
                            "cross-platform",
                            "either"
                        ]
                    },
                    FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST: {
                        'type': 'str',
                        'desc': _("A list of WebAuthn authenticators acceptable for enrollment, given as a "
                                  "space-separated list of AAGUIDs. Per default all authenticators are acceptable."),
                        'group': WebAuthnGroup.WEBAUTHN
                    },
                    FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT: {
                        'type': 'str',
                        'desc': _("Whether the user's identity should be verified when rolling out a new WebAuthn "
                                  "token. Default: preferred (verify the user if supported by the token)"),
                        'group': WebAuthnGroup.WEBAUTHN,
                        'value': [
                            "required",
                            "preferred",
                            "discouraged"
                        ]
                    },
                    FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS: {
                        'type': 'str',
                        'desc': _("Which algorithm are available to use for creating public key "
                                  "credentials for WebAuthn tokens. (Default: [{0!s}], Order: "
                                  "[{1!s}])").format(', '.join(DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE),
                                                     ', '.join(PUBKEY_CRED_ALGORITHMS_ORDER)),
                        'group': WebAuthnGroup.WEBAUTHN,
                        'multiple': True,
                        'value': list(PUBLIC_KEY_CREDENTIAL_ALGORITHMS.keys())
                    },
                    FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM: {
                        'type': 'str',
                        'desc': _("Whether to request attestation data when enrolling a new WebAuthn token. "
                                  "Note: for u2f_req to work with WebAuthn, this cannot be set to none. "
                                  "Default: direct (ask for non-anonymized attestation data)"),
                        'group': WebAuthnGroup.WEBAUTHN,
                        'value': [
                            "none",
                            "indirect",
                            "direct"
                        ]
                    },
                    FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL: {
                        'type': 'str',
                        'desc': _("Whether and how strictly to check authenticator attestation data. "
                                  "Note: If the attestation form is none, the attestation level needs to also be none. "
                                  "Default: untrusted (attestation is required, but can be unknown or self-signed)"),
                        'group': WebAuthnGroup.WEBAUTHN,
                        'value': [
                            "none",
                            "untrusted",
                            "trusted"
                        ]
                    },
                    FIDO2PolicyAction.REQ: {
                        'type': 'str',
                        'desc': _("Only the specified WebAuthn-tokens are allowed to be registered."),
                        'group': WebAuthnGroup.WEBAUTHN
                    },
                    ACTION.MAXTOKENUSER: {
                        'type': 'int',
                        'desc': _("The user may only have this number of WebAuthn tokens assigned."),
                        'group': GROUP.TOKEN
                    },
                    ACTION.MAXACTIVETOKENUSER: {
                        'type': 'int',
                        'desc': _('The user may only have this number of active WebAuthn tokens assigned.'),
                        'group': GROUP.TOKEN
                    },
                    ACTION.CHALLENGETEXT: {
                        'type': 'str',
                        'desc': _("Use an alternative challenge text for telling the "
                                  "user to confirm the enrollment with his WebAuthn device. "
                                  "You can also use tags for automated replacement. Check out "
                                  "the documentation for more details."),
                        'group': WebAuthnGroup.WEBAUTHN
                    }
                }
            }
        }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res
        return ret

    @staticmethod
    def get_setting_type(key):
        """
        Fetch the type of setting specific to WebAuthn tokens.

        The WebAuthn token defines several public settings. When these are
        written to the database, the type of the setting is automatically
        stored along with the setting by set_privacyidea_config().

        The key name needs to be in WEBAUTHN_TOKEN_SPECIFIC_SETTINGS.keys()
        and match /^webauthn\\./. If the specified setting does not exist,
        a ValueError will be thrown.

        :param key: The token specific setting key
        :type key: basestring
        :return: The setting type
        :rtype: "public"
        """

        if key not in WEBAUTHN_TOKEN_SPECIFIC_SETTINGS.keys():
            raise ValueError(f"key must be one of {', '.join(WEBAUTHN_TOKEN_SPECIFIC_SETTINGS.keys())}")
        return WEBAUTHN_TOKEN_SPECIFIC_SETTINGS[key]

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new WebAuthn Token object from a database object

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(self.get_class_type())
        self.hKeyRequired = False

    def _get_message(self, options):
        challengetext = get_optional(options, f"{self.get_class_type()}_{ACTION.CHALLENGETEXT!s}")
        return challengetext.format(self.token.description) if challengetext else ""

    def _get_webauthn_user(self, user):
        return WebAuthnUser(
            user_id=self.token.serial,
            user_name=user.login,
            user_display_name=str(user),
            icon_url=IMAGES.get(self.token.description.lower().split()[0], "") if self.token.description else "",
            credential_id=self.decrypt_otpkey(),
            public_key=webauthn_b64_encode(binascii.unhexlify(self.get_tokeninfo(FIDO2TokenInfo.PUB_KEY))),
            sign_count=self.get_otp_count(),
            rp_id=self.get_tokeninfo(FIDO2TokenInfo.RELYING_PARTY_ID)
        )

    def decrypt_otpkey(self):
        """
        This method fetches a decrypted version of the otp_key.

        This method becomes necessary, since the way WebAuthn is implemented
        in PrivacyIdea, the otpkey of a WebAuthn token is the credential_id,
        which may encode important information and needs to be sent to the
        client to allow the client to create an assertion for the
        authentication process.

        :return: The otpkey decrypted and encoded as WebAuthn base64.
        :rtype: basestring
        """

        return webauthn_b64_encode(binascii.unhexlify(self.token.get_otpkey().getKey()))

    def update(self, param, reset_failcount=True):
        """
        This method is called during the initialization process.

        :param param: Parameters from the token init.
        :type param: dict
        :param reset_failcount: Whether to reset the fail count.
        :type reset_failcount: bool
        :return: Nothing
        :rtype: None
        """

        TokenClass.update(self, param)

        transaction_id = get_optional(param, "transaction_id")
        reg_data = get_optional(param, "regdata")
        client_data = get_optional(param, "clientdata")

        if not (reg_data and client_data):
            self.token.rollout_state = ROLLOUTSTATE.CLIENTWAIT
            self.token.active = False
            # Set the description in the first enrollment step
            if "description" in param:
                self.set_description(get_optional(param, "description", default=""))
        elif reg_data and client_data and self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            attestation_level = get_required(param, FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL)
            rp_id = get_required(param, FIDO2PolicyAction.RELYING_PARTY_ID)
            http_origin = get_required(param, "HTTP_ORIGIN")

            serial = self.token.serial
            registration_client_extensions = get_optional(param, "registrationclientextensions")
            uv_req = get_optional(param, FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT)

            challenges = [
                challenge
                for challenge in get_challenges(serial=serial, transaction_id=transaction_id)
                if challenge.is_valid()
            ]

            # Since we are still enrolling the token, there should be exactly one challenge.
            if not len(challenges):
                raise EnrollmentError(f"The enrollment challenge does not exist or has timed out for {serial}")
            challenge = challenges[0]
            challenge_nonce = binascii.unhexlify(challenge.challenge)

            # This does the heavy lifting.
            #
            # All data is parsed and verified. If any errors occur an exception
            # will be raised.
            try:
                webauthn_credential = WebAuthnRegistrationResponse(
                    rp_id=rp_id,
                    origin=http_origin,
                    registration_response={
                        'clientData': client_data,
                        'attObj': reg_data,
                        'registrationClientExtensions':
                            webauthn_b64_decode(registration_client_extensions)
                            if registration_client_extensions
                            else None
                    },
                    challenge=webauthn_b64_encode(challenge_nonce),
                    attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[attestation_level],
                    trust_anchor_dir=get_from_config(FIDO2ConfigOptions.TRUST_ANCHOR_DIR),
                    uv_required=uv_req == UserVerificationLevel.REQUIRED
                ).verify([
                    # TODO: this might get slow when a lot of webauthn tokens are registered
                    token.decrypt_otpkey() for token in get_tokens(tokentype=self.type) if
                    token.get_serial() != self.get_serial()
                ])
            except Exception as e:
                log.warning(f"Enrollment of {self.get_class_type()} token failed: {e}!")
                raise EnrollmentError(f"Could not enroll {self.get_class_type()} token!")

            self.set_otpkey(hexlify_and_unicode(webauthn_b64_decode(webauthn_credential.credential_id)))
            self.set_otp_count(webauthn_credential.sign_count)

            # Save the credential_id hash to an extra table to be able to find the token faster
            credential_id_hash = hash_credential_id(webauthn_b64_decode(webauthn_credential.credential_id))
            save_credential_id_hash(credential_id_hash, self.token.id)

            token_info_dict = {
                FIDO2TokenInfo.PUB_KEY: hexlify_and_unicode(webauthn_b64_decode(webauthn_credential.public_key)),
                FIDO2TokenInfo.ORIGIN: webauthn_credential.origin,
                FIDO2TokenInfo.ATTESTATION_LEVEL: webauthn_credential.attestation_level,
                FIDO2TokenInfo.AAGUID: hexlify_and_unicode(webauthn_credential.aaguid),
                FIDO2TokenInfo.CREDENTIAL_ID_HASH: credential_id_hash
            }
            automatic_description = DEFAULT_DESCRIPTION
            # Add attestation info optionally
            if webauthn_credential.attestation_cert:
                cert = webauthn_credential.attestation_cert
                token_info_dict.update({
                    FIDO2TokenInfo.ATTESTATION_ISSUER: cert.issuer.rfc4514_string(),
                    FIDO2TokenInfo.ATTESTATION_SUBJECT: cert.subject.rfc4514_string(),
                    FIDO2TokenInfo.ATTESTATION_SERIAL: cert.serial_number
                })
                automatic_description = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
            self.add_tokeninfo_dict(token_info_dict)

            # If no description has already been set, set the automatic description or the
            # description given in the 2nd request
            if not self.token.description:
                self.set_description(get_optional(param, "description", default=automatic_description))

            # Delete all challenges. We are still in enrollment, so there
            # *should* be only one, but it can't hurt to be thorough here.
            for challenge in challenges:
                challenge.delete()
            self.challenge_janitor()
            # Reset clientwait rollout_state
            self.token.rollout_state = ROLLOUTSTATE.ENROLLED
            self.token.active = True
        else:
            raise ParameterError("regdata and or clientdata provided but token not in clientwait rollout_state.")

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we ask the user to confirm the enrollment with his token.

        This will prepare all the information the client needs to build the
        publicKeyCredentialCreationOptions to call
        navigator.credentials.create() with. It will then be called again,
        once the token is created and provide confirmation of the successful
        enrollment to the client.

        :param params: A dictionary with parameters from the request.
        :type params: dict
        :param user: The user enrolling the token.
        :type user: User
        :return: The response detail returned to the client.
        :rtype: dict
        """
        # get_init_details runs after "update" method. So in the first step clientwait has already been set
        if self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            if not params:
                raise ValueError("Creating a WebAuthn token requires params to be provided")
            if not user:
                raise ParameterError("User must be provided for WebAuthn enrollment!",
                                     id=ERROR.PARAMETER_USER_MISSING)

            user_verification = get_required(params, FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT)
            timeout = get_required(params, FIDO2PolicyAction.TIMEOUT)
            attestation = get_required(params, FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM)
            rp_id = get_required(params, FIDO2PolicyAction.RELYING_PARTY_ID)
            rp_name = get_required(params, FIDO2PolicyAction.RELYING_PARTY_NAME)

            response_detail = TokenClass.get_init_detail(self, params, user)
            response_detail['rollout_state'] = self.token.rollout_state
            # To aid with unit testing a fixed nonce may be passed in.
            nonce = self._get_nonce()
            # Create the challenge in the database
            challenge = Challenge(serial=self.token.serial,
                                  transaction_id=get_optional(params, "transaction_id"),
                                  challenge=hexlify_and_unicode(nonce),
                                  data=f"user_verification={user_verification}",
                                  session=get_optional(params, "session"),
                                  validitytime=self._get_challenge_validity_time())
            challenge.save()

            exclude_credential_ids = []
            if is_true(get_optional(params, FIDO2PolicyAction.AVOID_DOUBLE_REGISTRATION)):
                # Get the other webauthn tokens of the user and add their credential_ids to the exclude list
                webauthn_tokens = get_tokens(tokentype=self.type, user=self.user)
                for token in webauthn_tokens:
                    if token.token.rollout_state != ROLLOUTSTATE.CLIENTWAIT:
                        credential_id = token.decrypt_otpkey()
                        exclude_credential_ids.append(credential_id)

            credential_options = WebAuthnMakeCredentialOptions(
                challenge=webauthn_b64_encode(nonce),
                rp_name=rp_name,
                rp_id=rp_id,
                user_id=self.token.serial,
                user_name=user.login,
                user_display_name=str(user),
                timeout=timeout,
                attestation=attestation,
                user_verification=user_verification,
                public_key_credential_algorithms=get_required(params,
                                                              FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS),
                authenticator_attachment=get_optional(params, FIDO2PolicyAction.AUTHENTICATOR_ATTACHMENT),
                authenticator_selection_list=get_optional(params, FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST),
                credential_ids=exclude_credential_ids
            ).registration_dict

            register_request = {
                "transaction_id": challenge.transaction_id,
                "message": self._get_message(params),
                "nonce": credential_options["challenge"],
                "relyingParty": credential_options["rp"],
                "serialNumber": credential_options["user"]["id"],
                "pubKeyCredAlgorithms": credential_options["pubKeyCredParams"],
                "name": credential_options["user"]["name"],
                "displayName": credential_options["user"]["displayName"]
            }

            if credential_options.get("authenticatorSelection"):
                register_request["authenticatorSelection"] = credential_options["authenticatorSelection"]
            if credential_options.get("timeout"):
                register_request["timeout"] = credential_options["timeout"]
            if credential_options.get("attestation"):
                register_request["attestation"] = credential_options["attestation"]
            if (credential_options.get("extensions") or {}).get("authnSel"):
                register_request["authenticatorSelectionList"] = credential_options["extensions"]["authnSel"]
            if credential_options.get("excludeCredentials"):
                register_request["excludeCredentials"] = credential_options.get("excludeCredentials")

            response_detail["webAuthnRegisterRequest"] = register_request
            response_detail["transaction_id"] = challenge.transaction_id

            self.add_tokeninfo_dict({
                FIDO2TokenInfo.RELYING_PARTY_ID: credential_options["rp"]["id"],
                FIDO2TokenInfo.RELYING_PARTY_NAME: credential_options["rp"]["name"],
            })

        elif self.token.rollout_state in [ROLLOUTSTATE.ENROLLED, ""]:
            # This is the second step of the init request. The registration
            # ceremony has been successfully performed.
            response_detail = {
                "webAuthnRegisterResponse": {"subject": self.token.description}
            }

        else:
            response_detail = {}

        return response_detail

    @log_with(log)
    def is_challenge_request(self, passw, user=None, options=None):
        """
        Check if the request would start a challenge.
        Every request that is not a response needs to create a challenge.

        Note:
        This function does not need to be decorated with
        @challenge_response_allowed, as the WebAuthn token is always
        a challenge response token!

        :param passw:  The PIN of the token
        :type passw: basestring
        :param user: The User making the request
        :type user: User
        :param options: Dictionary of additional request parameters
        :type options: dict
        :return: Whether to trigger a challenge
        :rtype: bool
        """

        return self.check_pin(passw, user=user, options=options or {})

    def create_challenge(self, transactionid=None, options=None):
        """
        Create a challenge for challenge-response authentication.

        This method creates a challenge, which is submitted to the user. The
        submitted challenge will be preserved in the challenge database.

        If no transaction id is given, the system will create a transaction id
        and return it, so that the response can refer to this transaction.

        This method will return a tuple containing a bool value, indicating
        whether a challenge was successfully created, along with a message to
        display to the user, the transaction id, and a dictionary containing
        all parameters and data needed to respond to the challenge, as per the
        api.

        :param transactionid:  The id of this challenge
        :type transactionid: basestring
        :param options: The request context parameters and data
        :type options: dict
        :return: Success status, message, transaction id and reply_dict
        :rtype: (bool, basestring, basestring, dict)
        """

        if not options:
            raise ValueError("Creating a WebAuthn challenge requires options to be provided")

        try:
            user = self._get_webauthn_user(get_required(options, "user"))
        except ParameterError:
            raise ValueError("When creating a WebAuthn challenge, options must contain user")

        message = self._get_message(options)

        # if a transaction id is given, check if there are other webauthn
        # token and reuse the challenge.
        # TODO: It might be more sensible to pass around a list of all tokens
        #  currently doing challenge creation in this request.
        challenge = None
        if transactionid:
            for c in get_challenges(transaction_id=transactionid):
                # TODO: this throws an exception if the token does not exists
                #  but just created a challenge with it...
                if get_tokens(serial=c.serial, tokentype=self.get_class_type(),
                              count=True):
                    challenge = c.challenge
                    break

        if not challenge:
            nonce = self._get_nonce()
            challenge = hexlify_and_unicode(nonce)
        else:
            nonce = binascii.unhexlify(challenge)

        user_verification = get_required(options, FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT)

        # Create the challenge in the database
        db_challenge = Challenge(serial=self.token.serial,
                                 transaction_id=transactionid,
                                 challenge=challenge,
                                 data=f"user_verification={user_verification}",
                                 session=get_optional(options, "session"),
                                 validitytime=self._get_challenge_validity_time())
        db_challenge.save()

        public_key_credential_request_options = WebAuthnAssertionOptions(
            challenge=webauthn_b64_encode(nonce),
            webauthn_user=user,
            transports=get_required(options, FIDO2PolicyAction.ALLOWED_TRANSPORTS),
            user_verification_requirement=user_verification,
            timeout=get_required(options, FIDO2PolicyAction.TIMEOUT)
        ).assertion_dict

        data_image = convert_imagefile_to_dataimage(user.icon_url) if user.icon_url else ""

        reply_dict = {}
        sign_request = {"webAuthnSignRequest": public_key_credential_request_options,
                        "hideResponseInput": self.client_mode != CLIENTMODE.INTERACTIVE}
        if data_image:
            sign_request["img"] = data_image
            reply_dict["image"] = data_image
        reply_dict["attributes"] = sign_request
        return True, message, db_challenge.transaction_id, reply_dict

    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        This checks the response of a previous challenge.

        Since this is not a traditional token, otpval and window are unused.
        The information from the client is instead passed in the fields
        `serial`, `id`, `assertion`, `authenticatorData`, `clientDataJSON`,
        and `signature` of the options dictionary.

        :param otpval: Unused for this token type
        :type otpval: None
        :param counter: The authentication counter
        :type counter: int
        :param window: Unused for this token type
        :type window: None
        :param options: Contains the data from the client, along with policy configurations.
        :type options: dict
        :return: A numerical value where values larger than zero indicate success.
        :rtype: int
        """

        if is_webauthn_assertion_response(options) and get_optional(options, "challenge"):
            credential_id = get_required_one_of(options, ["credential_id", "credentialid"])
            authenticator_data = get_required_one_of(options, ["authenticatorData", "authenticatordata"])
            client_data = get_required_one_of(options, ["clientDataJSON", "clientdata"])
            signature_data = get_required_one_of(options, ["signature", "signaturedata"])
            user_handle = get_optional_one_of(options, ["userHandle", "userhandle"])
            assertion_client_extensions = get_optional(options, "assertionClientExtensions")

            # Check if a whitelist for AAGUIDs exists, and if this device is whitelisted. If not raise a
            # policy exception.
            allowed_aaguids = get_optional(options, FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST)
            if allowed_aaguids and self.get_tokeninfo(FIDO2TokenInfo.AAGUID) not in allowed_aaguids:
                log.warning(
                    f"The WebAuthn token {self.token.serial} is not allowed to authenticate due to policy "
                    f"restriction {FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST}"
                )
                raise PolicyError("The WebAuthn token is not allowed to authenticate due to a policy restriction.")

            # Check if the attestation certificate is
            # authorized. If not, we can raise a policy exception.
            if not attestation_certificate_allowed(
                    {
                        "attestation_issuer": self.get_tokeninfo(FIDO2TokenInfo.ATTESTATION_ISSUER),
                        "attestation_serial": self.get_tokeninfo(FIDO2TokenInfo.ATTESTATION_SERIAL),
                        "attestation_subject": self.get_tokeninfo(FIDO2TokenInfo.ATTESTATION_SUBJECT)
                    },
                    get_optional(options, FIDO2PolicyAction.REQ)):
                log.warning(
                    f"The WebAuthn token {self.token.serial} is not allowed to authenticate "
                    f"due to policy restriction {FIDO2PolicyAction.REQ}"
                )
                raise PolicyError("The WebAuthn token is not allowed to authenticate due to a policy restriction.")

            try:
                user = self._get_webauthn_user(get_required(options, "user"))
            except ParameterError:
                raise ValueError("When performing WebAuthn authorization, options must contain user")

            uv_req = get_optional(options, FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT)
            # Check if challenge is base64 encoded to be able to use login via passkey with webauthn
            challenge = get_required(options, "challenge").rstrip("=")
            challenge_decoded = None
            if len(challenge) % 2 == 0:
                try:
                    challenge_decoded = webauthn_b64_encode(binascii.unhexlify(challenge))
                except Exception as ex:
                    log.warning(f"Challenge {get_required(options, 'challenge')} is not hex encoded. {ex}. "
                                f"Attempting to decode it as base64url.")
            if not challenge_decoded:
                try:
                    challenge_decoded = bytes_to_base64url(challenge.encode("utf-8"))
                except Exception as ex:
                    log.warning(f"Challenge {get_required(options, 'challenge')} is not base64url encoded. {ex}.")
                    raise AuthenticationRejectedException('Challenge is neither hex nor base64url encoded.')

            http_origin = get_required(options, "HTTP_ORIGIN")
            if not http_origin:
                raise AuthenticationRejectedException('HTTP Origin header missing.')

            try:
                # This does the heavy lifting.
                #
                # All data is parsed and verified. If any errors occur, an exception
                # will be raised.
                self.set_otp_count(WebAuthnAssertionResponse(
                    webauthn_user=user,
                    assertion_response={
                        'id': credential_id,
                        'userHandle': user_handle,
                        'clientData': client_data,
                        'authData': authenticator_data,
                        'signature': signature_data,
                        'assertionClientExtensions':
                            webauthn_b64_decode(assertion_client_extensions)
                            if assertion_client_extensions
                            else None
                    },
                    challenge=challenge_decoded,
                    origin=http_origin,
                    allow_credentials=[user.credential_id],
                    uv_required=uv_req
                ).verify())
            except Exception as ex:
                log.warning(f"Checking response for token {self.token.serial} failed. {ex}")
                return -1

            # Save the credential_id hash to an extra table to be able to find the token faster
            credential_id_hash = hash_credential_id(credential_id)
            existing_entry = TokenCredentialIdHash.query.filter_by(token_id=self.token.id,
                                                                   credential_id_hash=credential_id_hash).first()
            if not existing_entry:
                token_cred_id_hash = TokenCredentialIdHash(token_id=self.token.id,
                                                           credential_id_hash=credential_id_hash)
                token_cred_id_hash.save()

            sign_count = self.get_otp_count()
            # TODO returning int is not good
            return sign_count if sign_count > 0 else 1

        else:
            # Not all necessary data provided.
            return -1

    @classmethod
    def get_default_challenge_text_auth(cls):
        return str(DEFAULT_CHALLENGE_TEXT_AUTH)

    @classmethod
    def get_default_challenge_text_register(cls):
        return str(DEFAULT_CHALLENGE_TEXT_ENROLL)


def is_webauthn_assertion_response(request_data):
    """
    Verify the request received is an assertion response.

    This will check whether the given request contains all parameters
    mandatory for a WebAuthn assertion response in privacyIDEA. If
    this is not the case, check_otp() will immediately fail.

    :param request_data: The parameters passed in the request.
    :type request_data: dict
    :return: Whether all data necessary to verify the assertion is available.
    :rtype: bool
    """

    return bool(get_optional_one_of(request_data, ["credential_id", "credentialid"])
                and get_optional_one_of(request_data, ["authenticatorData", "authenticatordata"])
                and get_optional_one_of(request_data, ["clientDataJSON", "clientdata"])
                and get_optional_one_of(request_data, ["signature", "signaturedata"]))
