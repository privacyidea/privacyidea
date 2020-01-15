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

from privacyidea.lib.tokenclass import TokenClass
from privacyidea.models import Challenge
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
generated from your domain), and a serial number. It will also pass some
additional options regarding timeout, which authenticators are acceptable,
and what key types are acceptable to the server.

2. Step
~~~~~~~

.. sourcecode:: http

    POST /token/init HTTP/1.1
    Host: example.com
    Accept: application/json
    
    type=webauthn
    serial=<serial>
    id=<id>
    clientdata=<clientDataJSON>
    regdata=<attestationObject>

*id*, *clientDataJSON* and *attestationObject* are the values returned by the
WebAuthn authenticator.

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
            pubKeyCredParams: <pubKeyCredParams>,
            authenticatorSelection: <authenticatorSelection>,
            timeout: <timeout>,
            attestation: <attestation>
        })
        .then(function(credential) { <responseHandler> })
        .catch(function(error) { <errorHandler> });

Here *nonce*, *relyingParty*, *serialNumber*, *pubKeyCredParams*,
*authenticatorSelection*, *timeout*, and *attestation* are the values
provided by the server in the first step, *name* is the user name the user
uses to log in (often an email address), and *displayName* is the
human-readable name used to address the user (usually the users full name).

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
                        "type": <keyType>,
                        "transports": <allowedTransports>
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
                        "type": <keyType>,
                        "transports": <allowedTransports>
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
                            "type": <keyType>,
                            "transports": <allowedTransports>
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

The application now needs to call the javascipt function
*navigator.credentials.get* with *publicKeyCredentialRequstOptions* built using
the *nonce*, *credentialId*, *keyType*, *allowedTransports* and *timeout* from
the server.

    const publicKeyCredentialRequestOptions = {
        challenge: Uint8Array.from(<nonce>, c => c.charCodeAt(0)),
        allowCredentials: [{
            id: Uint8Array.from(<credentialId>, c=> c.charCodeAt(0)),
            type: <keyType>,
            transports: <allowedTransports>
        }],
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
above. The *serial* may be pulled from the challenge provided by the server, or
decoded from the *response.userHandle* field contained in the *assertion*.

.. sourcecode:: http

    POST /validate/check HTTP/1.1
    Host: example.com
    Accept: application/json
    
    user=<user>
    pass=
    transaction_id=<transaction_id>
    serial=<serial>
    id=<id>
    clientdata=<clientDataJSON>
    signaturedata=<signature>
    authenticatordata=<authenticatorData>

"""

IMAGES = IMAGES

log = logging.getLogger(__name__)
optional = True
required = False


class WEBAUTHNACTION(object):
    ALLOWED_TRANSPORTS = 'webauthn_allowed_transports'
    TIMEOUT_AUTH = 'webauthn_timeout_auth'
    TIMEOUT_ENROLL = 'webauthn_timeout_enroll'
    RELYING_PARTY_NAME = 'webauthn_relying_party_name'
    RELYING_PARTY_ID = 'webauthn_relying_party_id'
    PUBLIC_KEY_CREDENTIAL_ALGORITHMS = 'webauthn_public_key_credential_algorithms'
    AUTHENTICATOR_ATTACHMENT = 'webauthn_authenticator_attachment'


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
                        'desc': _("Only the specified transports may be used to speak to WebAuthn tokens."
                                  "Default: usb ble nfc internal lightning (All transports are allowed)")
                    },
                    WEBAUTHNACTION.TIMEOUT_AUTH: {
                        'type': 'int',
                        'desc': _("The amount of time in seconds the user has to confirm an authorization request on "
                                  "his WebAuthn token. Default: 60")
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
                        'desc': _("The amount of time in seconds the user has to confirm enrollment on his "
                                  "WebAuthn token. Default: 60")
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