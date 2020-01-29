# -*- coding: utf-8 -*-
#
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

from OpenSSL import crypto
from cryptography import x509
from flask import request

from privacyidea.api.lib.utils import getParam
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import get_from_config
from privacyidea.lib.error import ParameterError, RegistrationError
from privacyidea.lib.token import get_tokens
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.u2f import x509name_to_string
from privacyidea.lib.tokens.webauthn import (COSE_ALGORITHM, webauthn_b64_encode, WebAuthnRegistrationResponse,
                                             ATTESTATION_REQUIREMENT_LEVEL, webauthn_b64_decode)
from privacyidea.lib.tokens.u2ftoken import IMAGES
from privacyidea.lib.log import log_with
import logging
from privacyidea.lib import _
from privacyidea.lib.policy import SCOPE, GROUP, ACTION

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

Beware the WebAuthn tokens can only be used if the privacyIDEA server and
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

1. Step
~~~~~~~

.. sourcecode:: http

    POST /token/init HTTP/1.1
    Host: example.com
    Accept: application/json
    
    type=webauthn
    
This step returns a nonce, a relying party (containing a name and an ID
generated from your domain), and a serial number, along with a transaction ID.
It will also pass some additional options regarding timeout, which
authenticators are acceptable, and what key types are acceptable to the server.

2. Step
~~~~~~~

.. sourcecode:: http

    POST /token/init HTTP/1.1
    Host: example.com
    Accept: application/json
    
    type=webauthn
    serial=<serial>
    transaction_id=<transaction_id>
    clientdata=<clientDataJSON>
    regdata=<attestationObject>
    description=<description>

*clientDataJSON* and *attestationObject* are the values returned by the
WebAuthn authenticator. *description* is an optional description string for 
the new token.

You need to call the javascript function

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
            pubKeyCredParams: [
                {
                    alg: <preferredAlgorithm>,
                    type: "public-key"
                },
                {
                    alg: <alternativeAlgorithm>,
                    type: "public-key"
                }
            ],
            authenticatorSelection: <authenticatorSelection>,
            timeout: <timeout>,
            attestation: <attestation>,
            extensions: {
                authnSel: <authenticatorSelectionList>
            }
        })
        .then(function(credential) { <responseHandler> })
        .catch(function(error) { <errorHandler> });

Here *nonce*, *relyingParty*, *serialNumber*, *preferredAlgorithm*,
*alternativeAlgorithm*, *authenticatorSelection*, *timeout*, *attestation*, and
*authenticatorSelectionList* are the values provided by the server in the first
step, *name* is the user name the user uses to log in (often an email address),
and *displayName* is the human-readable name used to address the user (usually
the users full name). *alternativeAlgorithm*, *authenticatorSelection*,
*timeout*, *attestation*, and *authenticatorSelectionList* are optional and any
of these values should simply be omitted, if the server has not sent it.

If an *authenticationSelectionList* was given, the *responseHandler* needs to
verify, that the field *authnSel* of *credential.getExtensionResults()*
contains true. If this is not the case, the *responseHandler* should abort and
call the *errorHandler*, displaying an error telling the user to use his
company-provided token.

The *responseHandler* needs to then send the *id* to the server along with the
*clientDataJSON* and the *attestationObject* contained in the *response* field
of the *credential* (2. step).

The server expects the *clientDataJSON* as a JSON-encoded string. This means,
that it is the clients responsibility to run UTF-8 decoding on the
*clientDataJSON* and to strip the leading byte order mark, if any.

The *attestationObject* is a binary and needs to be passed to the server
encoded as base64. Please beware that the btoa() function provided by
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

**Request**

.. sourcecode:: http

    POST /validate/check HTTP/1.1
    Host: example.com
    Accept: application/json
    
    user=<username>
    pass=<password>
    
**Response**

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/json
    
    {
        "detail": {
            "attributes": {
                "hideResponseInput": true,
                "img": <imageUrl>,
                "webauthnSignRequest": {
                    "challenge": <nonce>,
                    "allowCredentials": [{
                        "id": <credentialId>,
                        "transports": <allowedTransports>,
                        "userVerification": <userVerificationRequirement>
                    }],
                    "timeout": <timeout>
                }
            },
            "message": "Please confirm with your WebAuthn token",
            "transaction_id": <transactionId>
        },
        "id": 1,
        "jsonrpc": "2.0",
        "result": {
            "status": true,
            "value": false
        },
        "versionnumber": <privacyIDEAversion>
    }

Get the challenge (using /validate/triggerchallenge)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The /validate/triggerchallenge endpoint can be used to trigger a challenge
using a service account (without requiring the PIN for the token).

**Request**

.. sourcecode:: http

    POST /validate/triggerchallenge HTTP/1.1
    Host: example.com
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
                "img": <imageUrl>,
                "webauthnSignRequest": {
                    "challenge": <nonce>,
                    "allowCredentials": [{
                        "id": <credentialId>,
                        "transports": <allowedTransports>,
                        "userVerification": <userVerificationRequirement>
                    }],
                    "timeout": <timeout>
                }
            },
            "message": "Please confirm with your WebAuthn token",
            "messages": ["Please confirm with your WebAuthn token"],
            "multi_challenge": [{
                "attributes": {
                    "hideResponseInput": true,
                    "img": <imageUrl>,
                    "webauthnSignRequest": {
                        "challenge": <nonce>,
                        "allowCredentials": [{
                            "id": <credentialId>,
                            "transports": <allowedTransports>,
                            "userVerification": <userVerificationRequirement>
                        }],
                        "timeout": <timeout>
                    }
                },
                "message": "Please confirm with your WebAuthn token",
                "serial": <tokenSerial>,
                "transaction_id": <transactionId>,
                "type": "webauthn"
            }],
            "serial": <tokenSerial>,
            "threadid": <threadId>,
            "transaction_id": <transactionId>,
            "transaction_ids": [<transactionId>],
            "type": "webauthn"
        },
        "id": 1,
        "jsonrpc": "2.0",
        "result": {
            "status": true,
            "value": 1
        },
        "versionnumber": <privacyIDEAversion>
    }
    
Send the Response
~~~~~~~~~~~~~~~~~

The application now needs to call the javascript function
*navigator.credentials.get* with *publicKeyCredentialRequstOptions* built using
the *nonce*, *credentialId*, *allowedTransports*, *userVerificationRequirement*
and *timeout* from the server.

    const publicKeyCredentialRequestOptions = {
        challenge: Uint8Array.from(<nonce>, c => c.charCodeAt(0)),
        allowCredentials: [{
            id: Uint8Array.from(<credentialId>, c=> c.charCodeAt(0)),
            type: 'public-key',
            transports: <allowedTransports>
        }],
        userVerification: <userVerificationRequirement>,
        timeout: <timeout>
    }
    navigator
        .credentials
        .get({publicKey: publicKeyCredentialRequestOptions})
        .then(function(assertion) { <responseHandler> })
        .catch(function(error) { <errorHandler> });

The *responseHandler* needs to call the */validate/check* API providing the
*serial* of the token the user is signing in with, along with the *id*,
returned by the WebAuthn device in the *assertion* and the *authenticatorData*,
*clientDataJSON* and *signature* contained in the *response* field of the
*assertion*.

The *clientDataJSON* should again be encoded as a JSON-string. The
*authenticatorData* and *signature* are both binary and need to be encoded as
base64. For more detailed instructions, refer to “2. Step” under “Enrollment”
above. 

.. sourcecode:: http

    POST /validate/check HTTP/1.1
    Host: example.com
    Accept: application/json
    
    user=<user>
    pass=
    transaction_id=<transaction_id>
    id=<id>
    clientdata=<clientDataJSON>
    signaturedata=<signature>
    authenticatordata=<authenticatorData>

"""

from privacyidea.lib.utils import hexlify_and_unicode

IMAGES = IMAGES

DEFAULT_DESCRIPTION = "Generic WebAuthn Token"

# Policy defaults
DEFAULT_ALLOWED_TRANSPORTS = "usb ble nfc internal lightning"
DEFAULT_TIMEOUT_AUTH = 60
DEFAULT_USER_VERIFICATION_REQUIREMENT_AUTH = 'preferred'
DEFAULT_TIMEOUT_ENROLL = 60
DEFAULT_AUTHENTICATOR_ATTACHMENT = 'either'
DEFAULT_USER_VERIFICATION_REQUIREMENT_ENROLL = 'preferred'
DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE = 'ecdsa_preferred'
DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL = 'untrusted'
DEFAULT_AUTHENTICATOR_ATTESTATION_FORM = 'direct'

PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE_OPTIONS = {
    'ecdsa_preferred': [
        COSE_ALGORITHM.ES256,
        COSE_ALGORITHM.PS256
    ],
    'ecdsa_only': [
        COSE_ALGORITHM.ES256
    ],
    'rsassa-pss_preferred': [
        COSE_ALGORITHM.PS256,
        COSE_ALGORITHM.ES256
    ],
    'rsassa-pss_only': [
        COSE_ALGORITHM.PS256
    ]
}

log = logging.getLogger(__name__)
optional = True
required = False


class WEBAUTHNCONFIG(object):
    """
    Config options defined for WebAuthn
    """

    TRUST_ANCHOR_DIR = 'webauthn.trust_anchor_dir'
    APP_ID = 'webauthn.appid'
    CHALLENGE_VALIDITY_TIME = 'WebauthnChallengeValidityTime'


class WEBAUTHNACTION(object):
    """
    Policy actions defined for WebAuthn
    """

    ALLOWED_TRANSPORTS = 'webauthn_allowed_transports'
    TIMEOUT_AUTH = 'webauthn_timeout_auth'
    TIMEOUT_ENROLL = 'webauthn_timeout_enroll'
    RELYING_PARTY_NAME = 'webauthn_relying_party_name'
    RELYING_PARTY_ID = 'webauthn_relying_party_id'
    AUTHENTICATOR_ATTACHMENT = 'webauthn_authenticator_attachment'
    AUTHENTICATOR_SELECTION_LIST = 'webauthn_authenticator_selection_list'
    USER_VERIFICATION_REQUIREMENT_ENROLL = 'webauthn_user_verification_requirement_enroll'
    USER_VERIFICATION_REQUIREMENT_AUTH = 'webauthn_user_verification_requirement_auth'
    PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE = 'webauthn_public_key_credential_algorithm_preference'
    AUTHENTICATOR_ATTESTATION_FORM = 'webauthn_authenticator_attestation_form'
    AUTHENTICATOR_ATTESTATION_LEVEL = 'webauthn_authenticator_attestation_level'
    REQ = 'webauthn_req'


class WebAuthnTokenClass(TokenClass):
    """
    The WebAuthn Token implementation.
    """

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
            'description': 'WebAuthn: Enroll a Web Authentication token.',
            'init': {},
            'config': {},
            'user': ['enroll'],
            # This tokentype is enrollable in the UI for...
            'ui_enroll': ["admin", "user"],
            'policy': {
                SCOPE.AUTH: {
                    WEBAUTHNACTION.ALLOWED_TRANSPORTS: {
                        'type': 'str',
                        'desc': _("A list of transports to prefer to communicate with WebAuthn tokens."
                                  "Default: usb ble nfc internal lightning (All standard transports)")
                    },
                    WEBAUTHNACTION.TIMEOUT_AUTH: {
                        'type': 'int',
                        'desc': _("The time in seconds the user has to confirm authorization on his WebAuthn token. " 
                                  "Note: You will want to increase the ChallengeValidityTime along with this. "
                                  "Default: 60")
                    },
                    WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT_AUTH: {
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
                        'desc': _('Use an alternate challenge text for telling the '
                                  'user to confirm with his WebAuthn device')
                    }
                },
                SCOPE.ENROLL: {
                    WEBAUTHNACTION.RELYING_PARTY_NAME: {
                        'type': 'str',
                        'desc': _("A human readable name for the organization rolling out WebAuthn tokens."),
                    },
                    WEBAUTHNACTION.RELYING_PARTY_ID: {
                        'type': 'str',
                        'desc': _("A domain name that is a subset of the respective FQDNs for all the webservices the "
                                  "users should be able to sign in to using WebAuthn tokens.")
                    },
                    WEBAUTHNACTION.TIMEOUT_ENROLL: {
                        'type': 'int',
                        'desc': _("The time in seconds the user has to confirm enrollment on his WebAuthn token. "
                                  "Note: You will want to increase the ChallengeValidityTime along with this. "
                                  "Default: 60")
                    },
                    WEBAUTHNACTION.AUTHENTICATOR_ATTACHMENT: {
                        'type': 'str',
                        'desc': _("Whether to limit roll out of WebAuthn tokens to either only platform attachments, "
                                  "or only cross-platform attachments. Default: either"),
                        'group': GROUP.TOKEN,
                        'value': [
                            "platform",
                            "cross-platform",
                            "either"
                        ]
                    },
                    WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST: {
                        'type': 'str',
                        'desc': _("A list of WebAuthn authenticators acceptable for enrollment, given as a "
                                  "space-separated list of AAGUIDs. Per default all authenticators are acceptable."),
                        'group': GROUP.TOKEN
                    },
                    WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT_ENROLL: {
                        'type': 'str',
                        'desc': _("Whether the user's identity should be verified when rolling out a new WebAuthn "
                                  "token. Default: preferred (verify the user if supported by the token)"),
                        'group': GROUP.TOKEN,
                        'value':    [
                            "required",
                            "preferred",
                            "discouraged"
                        ]
                    },
                    WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE: {
                        'type': 'str',
                        'desc': _("Which algorithm to use for creating public key credentials for WebAuthn tokens"
                                  "Default: ecdsa_preferred"),
                        'group': GROUP.TOKEN,
                        'value': [
                            "ecdsa_preferred",
                            "ecdsa_only",
                            "rsassa-pss_preferred",
                            "rsassa-pss_only"
                        ]
                    },
                    WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM: {
                        'type': 'str',
                        'desc': _("Whether to request attestation data when enrolling a new WebAuthn token."
                                  "Note: for u2f_req to work with WebAuthn, this cannot be set to none. "
                                  "Default: direct (ask for non-anonymized attestation data)"),
                        'group': GROUP.TOKEN,
                        'value': [
                            "none",
                            "indirect",
                            "direct"
                        ]
                    },
                    WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL: {
                        'type': 'str',
                        'desc': _("Whether and how strictly to check authenticator attestation data."
                                  "Note: If the attestation for is none, the needs to also be none."
                                  "Default: untrusted (attestation is required, but can be unknown or self-signed)"),
                        'group': GROUP.TOKEN,
                        'value': [
                            "none",
                            "untrusted",
                            "trusted"
                        ]
                    },
                    WEBAUTHNACTION.REQ: {
                        'type': 'str',
                        'desc': _("Only the specified WebauthnTokens are allowed to be registered."),
                        'group': GROUP.TOKEN
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

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new WebAuthn Token object from a database object

        :param db_token:  instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"webauthn")
        self.hKeyRequired = False
        self.init_step = 1

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

        transaction_id = getParam(param, "transaction_id")

        if transaction_id:
            self.init_step = 2

            serial = self.token.serial
            reg_data = getParam(param, "regdata", required)
            client_data = getParam(param, "clientdata", required)
            description = getParam(param, "description", optional)

            rp_id = getParam(param, WEBAUTHNACTION.RELYING_PARTY_ID, required)
            uv_req = getParam(param, WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT_ENROLL, optional)
            attestation_level = getParam(param, WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL, required)

            if 'HTTP_ORIGIN' not in request.environ:
                raise ParameterError("The ORIGIN HTTP header must be included, when enrolling a new WebAuthn token.")

            challengeobject_list = [
                challengeobject
                for challengeobject in get_challenges(serial=serial,
                                                      transaction_id=transaction_id)
                if challengeobject.is_valid()
            ]

            # Since we are still enrolling the token, there should be exactly one challenge.
            if not len(challengeobject_list):
                raise RegistrationError(
                    "The enrollment challenge does not exist or has timed out for {0!s}".format(serial))
            challengeobject = challengeobject_list[0]
            challenge = binascii.unhexlify(challengeobject.challenge)

            # This does the heavy lifting.
            #
            # All data is parsed and verified. If any errors occur an exception
            # will be raised.
            webAuthnCredential = WebAuthnRegistrationResponse(
                rp_id=rp_id,
                origin=request.environ['HTTP_ORIGIN'],
                registration_response={
                    'clientData': client_data,
                    'attObj': reg_data
                },
                challenge=webauthn_b64_encode(challenge),
                attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[attestation_level],
                trust_anchor_dir=get_from_config(WEBAUTHNCONFIG.TRUST_ANCHOR_DIR),
                uv_required=uv_req
            ).verify([
                token.decrypt_otpkey() for token in get_tokens(tokentype=self.type)
            ])

            self.set_otpkey(hexlify_and_unicode(webauthn_b64_decode(webAuthnCredential.credential_id)))
            self.set_otp_count(webAuthnCredential.sign_count)
            self.add_tokeninfo("pubKey", hexlify_and_unicode(webauthn_b64_decode(webAuthnCredential.public_key)))
            self.add_tokeninfo("relying_party_id", webAuthnCredential.rp_id)
            self.add_tokeninfo("origin", webAuthnCredential.origin)
            self.add_tokeninfo("attestation_level", webAuthnCredential.attestation_level)

            # Add attestation info.
            if webAuthnCredential.attestation_cert:
                # attestation_cert is of type X509. If you get warnings from your IDE
                # here, it is because your IDE mistakenly assumes it to be of type PKey,
                # due to a bug in pyOpenSSL 18.0.0. This bug is – however – purely
                # cosmetic (a wrongly hinted return type in X509.from_cryptography()),
                # and can be safely ignored.
                #
                # See also:
                # https://github.com/pyca/pyopenssl/commit/4121e2555d07bbba501ac237408a0eea1b41f467
                attestation_cert = crypto.X509.from_cryptography(webAuthnCredential.attestation_cert)
                self.add_tokeninfo("attestation_issuer", x509name_to_string(attestation_cert.get_issuer()))
                self.add_tokeninfo("attestation_serial", x509name_to_string(attestation_cert.get_serial_number()))
                self.add_tokeninfo("attestation_subject", x509name_to_string(attestation_cert.get_subject()))

                if not description:
                    cn = webAuthnCredential.attestation_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                    description = cn[0] if len(cn) else DEFAULT_DESCRIPTION

            self.set_description(description)

            # Delete all challenges. We are still in enrollment, so there
            # *should* be only one, but it can't hurt to be thorough here.
            for challengeobject in challengeobject_list:
                challengeobject.delete()
            self.challenge_janitor()
        else:
            self.set_description("WebAuthn initialization")
