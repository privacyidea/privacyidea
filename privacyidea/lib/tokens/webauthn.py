# -*- coding: utf-8 -*-
#
# 2020-01-14 Jean-Pierre Höhmann <jean-pierre.hoehmann@netknights.it>
#
# License:  AGPLv3
# Contact:  https://www.privacyidea.org
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
# This code was originally adapted from the Duo Security implementation of
# WebAuthn for Python.
#
# Copyright (c) 2017 Duo Security, Inc. All rights reserved.
# License:  BSD-3-Clause
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import binascii
import codecs
import hashlib
import json
import logging
import os
import struct

import cbor2
import cryptography.x509
from OpenSSL import crypto
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import constant_time
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers, SECP256R1, ECDSA
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15, PSS, MGF1
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.hashes import SHA256, SHA1
from cryptography.x509 import load_der_x509_certificate

from privacyidea.lib.tokens.u2f import url_encode, url_decode
from privacyidea.lib.utils import to_bytes, to_unicode

__doc__ = """
Business logic for WebAuthn protocol.

This file implements the server part of the WebAuthn protocol.

This file is tested in tests/test_lib_tokens_webauthn.py
"""

# Default client extensions
#
DEFAULT_CLIENT_EXTENSIONS = {'appid': None}

# Default authenticator extensions
#
DEFAULT_AUTHENTICATOR_EXTENSIONS = {}

log = logging.getLogger(__name__)


class COSE_PUBLIC_KEY(object):
    """
    The indices of the various parameters in a COSE-formatted public key.
    """

    ALG = 3
    X = -2
    Y = -3
    E = -2
    N = -1


class ATTESTATION_TYPE(object):
    """
    Attestation types known to this implementation.
    """

    BASIC = 'Basic'
    ECDAA = 'ECDAA'
    NONE = 'None'
    ATTESTATION_CA = 'AttCA'
    SELF_ATTESTATION = 'Self'


# Only supporting 'None', 'Basic', and 'Self Attestation' attestation types for now.
SUPPORTED_ATTESTATION_TYPES = (
    ATTESTATION_TYPE.BASIC,
    ATTESTATION_TYPE.NONE,
    ATTESTATION_TYPE.SELF_ATTESTATION
)


class ATTESTATION_FORMAT(object):
    """
    Attestation format identifiers as registered in the IANA WebAuthn attestation statement format identifiers registry.
    """

    PACKED = 'packed'
    TPM = 'tpm'
    ANDROID_KEY = 'android-key'
    ANDROID_SAFETYNET = 'android-safetynet'
    APPLE = 'apple'
    FIDO_U2F = 'fido-u2f'
    NONE = 'none'


# Only supporting 'fido-u2f', 'packed', and 'none' attestation formats for now.
# TODO: implement android, apple and TPM authentication formats
SUPPORTED_ATTESTATION_FORMATS = (
    ATTESTATION_FORMAT.FIDO_U2F,
    ATTESTATION_FORMAT.PACKED,
    ATTESTATION_FORMAT.NONE
)


REGISTERED_ATTESTATION_FORMATS = (
    ATTESTATION_FORMAT.PACKED,
    ATTESTATION_FORMAT.TPM,
    ATTESTATION_FORMAT.ANDROID_KEY,
    ATTESTATION_FORMAT.ANDROID_SAFETYNET,
    ATTESTATION_FORMAT.APPLE,
    ATTESTATION_FORMAT.FIDO_U2F,
    ATTESTATION_FORMAT.NONE
)


class CLIENT_DATA_TYPE(object):
    """
    Client data types used by this implementation.
    """

    CREATE = 'webauthn.create'
    GET = 'webauthn.get'


SUPPORTED_CLIENT_DATA_TYPES = (
    CLIENT_DATA_TYPE.CREATE,
    CLIENT_DATA_TYPE.GET
)


class COSE_ALGORITHM(object):
    """
    IANA-assigned identifiers of supported COSE algorithms.
    """

    ES256 = -7
    PS256 = -37
    RS256 = -257
    RS1 = -65535  # for tests, otherwise unsupported


SUPPORTED_COSE_ALGORITHMS = (
    COSE_ALGORITHM.ES256,
    COSE_ALGORITHM.PS256,
    COSE_ALGORITHM.RS256,
)


class ATTESTATION_FORM(object):
    """
    The different forms of attestation.
    """

    NONE = 'none'
    INDIRECT = 'indirect'
    DIRECT = 'direct'


ATTESTATION_FORMS = (
    ATTESTATION_FORM.NONE,
    ATTESTATION_FORM.INDIRECT,
    ATTESTATION_FORM.DIRECT
)


class USER_VERIFICATION_LEVEL(object):
    """
    The different levels of user verification.
    """

    REQUIRED = 'required'
    PREFERRED = 'preferred'
    DISCOURAGED = 'discouraged'


USER_VERIFICATION_LEVELS = (
    USER_VERIFICATION_LEVEL.REQUIRED,
    USER_VERIFICATION_LEVEL.PREFERRED,
    USER_VERIFICATION_LEVEL.DISCOURAGED
)


class ATTESTATION_LEVEL(object):
    """
    The different levels of attestation requirement.
    """

    TRUSTED = 'trusted'
    UNTRUSTED = 'untrusted'
    NONE = 'none'


ATTESTATION_LEVELS = (
    ATTESTATION_LEVEL.TRUSTED,
    ATTESTATION_LEVEL.UNTRUSTED,
    ATTESTATION_LEVEL.NONE
)


ATTESTATION_REQUIREMENT_LEVEL = {
    ATTESTATION_LEVEL.TRUSTED: {
        'self_attestation_permitted': False,
        'none_attestation_permitted': False
    },
    ATTESTATION_LEVEL.UNTRUSTED: {
        'self_attestation_permitted': True,
        'none_attestation_permitted': False
    },
    ATTESTATION_LEVEL.NONE: {
        'self_attestation_permitted': True,
        'none_attestation_permitted': True
    }
}


ATTESTATION_REQUIREMENT_LEVELS = (
    ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.TRUSTED],
    ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.UNTRUSTED],
    ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.NONE]
)


class AUTHENTICATOR_ATTACHMENT_TYPE(object):
    """
    The different types of authenticator attachment.
    """

    PLATFORM = 'platform'
    CROSS_PLATFORM = 'cross-platform'


AUTHENTICATOR_ATTACHMENT_TYPES = (
    AUTHENTICATOR_ATTACHMENT_TYPE.PLATFORM,
    AUTHENTICATOR_ATTACHMENT_TYPE.CROSS_PLATFORM
)


class TRANSPORT(object):
    """
    The standard transports.
    """

    USB = 'usb'
    BLE = 'ble'
    NFC = 'nfc'
    INTERNAL = 'internal'


TRANSPORTS = (
    TRANSPORT.USB,
    TRANSPORT.BLE,
    TRANSPORT.NFC,
    TRANSPORT.INTERNAL,
)


class COSEKeyException(Exception):
    """
    COSE public key invalid or unsupported.
    """

    pass


class AuthenticationRejectedException(Exception):
    """
    The authentication attempt was rejected.
    """

    pass


class RegistrationRejectedException(Exception):
    """
    The registration attempt was rejected.
    """

    pass


class WebAuthnUserDataMissing(Exception):
    """
    The user data is missing.
    """

    pass


class AuthenticatorDataFlags(object):
    """
    Authenticator data flags:

    https://www.w3.org/TR/webauthn/#authenticator-data
    """

    USER_PRESENT = 1 << 0
    USER_VERIFIED = 1 << 2
    ATTESTATION_DATA_INCLUDED = 1 << 6
    EXTENSION_DATA_INCLUDED = 1 << 7

    def __init__(self, auth_data):
        """
        Create a new AuthenticatorDataFlags object.

        :param auth_data: The authenticator data.
        :type auth_data: basestring
        :return: An AuthenticatorDataFlags object.
        :rtype: AuthenticatorDataFlags
        """

        self.flags = struct.unpack('!B', auth_data[32:33])[0]

    @property
    def user_present(self):
        """
        :return: Whether the user was present.
        :rtype: bool
        """

        return (self.flags & self.USER_PRESENT) == self.USER_PRESENT

    @property
    def user_verified(self):
        """
        :return: Whether the user's identity was verified.
        :rtype: bool
        """

        return (self.flags & self.USER_VERIFIED) == self.USER_VERIFIED

    @property
    def attestation_data_included(self):
        """
        :return: Whether the authenticator response includes attestation information.
        :rtype: bool
        """

        return (self.flags & self.ATTESTATION_DATA_INCLUDED) == self.ATTESTATION_DATA_INCLUDED

    @property
    def extension_data_included(self):
        """
        :return: Whether the authenticator respone included extension data.
        :rtype: bool
        """

        return (self.flags & self.EXTENSION_DATA_INCLUDED) == self.EXTENSION_DATA_INCLUDED


class WebAuthnMakeCredentialOptions(object):
    """
    Generate the options passed to navigator.credentials.create()
    """

    def __init__(self,
                 challenge,
                 rp_name,
                 rp_id,
                 user_id,
                 user_name,
                 user_display_name,
                 timeout,
                 attestation,
                 user_verification,
                 public_key_credential_algorithms,
                 icon_url=None,
                 authenticator_attachment=None,
                 authenticator_selection_list=None,
                 location=None,
                 credential_ids=None):
        """
        Create a new WebAuthnMakeCredentialOptions object.

        :param challenge: The challenge is a buffer of cryptographically random bytes needed to prevent replay attacks.
        :type challenge: basestring
        :param rp_name: The name of the relying party.
        :type rp_name: basestring
        :param rp_id: The ID of the relying party.
        :type rp_id: basestring
        :param user_id: The ID for the user credential being generated. This is the privacyIDEA token serial.
        :type user_id: basestring
        :param user_name: The username the user logs in with.
        :type user_name: basestring
        :param user_display_name: The human-readable name of the user.
        :type user_display_name: basestring
        :param icon_url: An optional icon url.
        :type icon_url: basestring
        :param timeout: The time (in milliseconds) that the user has to respond to the prompt for registration.
        :type timeout: int
        :param attestation: This option allows to indicate how important the attestation data is to this registration.
        :type attestation: basestring
        :param user_verification: The importance level of verifying the user.
        :type user_verification: basestring
        :param authenticator_attachment: What type of authenticator to register ("platform", or "cross-platform").
        :type authenticator_attachment: basestring
        :param public_key_credential_algorithms: Which algorithms to allow in order of preference.
        :type public_key_credential_algorithms: list of int
        :param authenticator_selection_list: A whitelist of allowed authenticator AAGUIDs
        :type authenticator_selection_list: list of basestring
        :param location: Whether to ask for the inclusion of location information in the attestation.
        :type location: bool
        :param credential_ids: A list of ids that are already enrolled to the user.
        :type credential_ids: list
        :return: A WebAuthnMakeCredentialOptions object.
        :rtype: WebAuthnMakeCredentialOptions
        """

        self.challenge = challenge
        self.rp_name = rp_name
        self.rp_id = rp_id
        self.user_id = user_id
        self.user_name = user_name
        self.user_display_name = user_display_name
        self.icon_url = icon_url
        self.authenticator_selection_list = authenticator_selection_list
        self.location = bool(location)
        self.exclude_credentials = []
        if credential_ids:
            for cred_id in credential_ids:
                self.exclude_credentials.append({
                    "id": cred_id,
                    "type": "public-key",
                    "transports": list(TRANSPORTS)
                })

        attestation = str(attestation).lower()
        if attestation not in ATTESTATION_FORMS:
            raise ValueError('Attestation string must be one of {0!s}'.format(', '.join(ATTESTATION_FORMS)))
        self.attestation = attestation

        if user_verification is not None:
            user_verification = str(user_verification).lower()
            if user_verification not in USER_VERIFICATION_LEVELS:
                raise ValueError('user_verification must be one of {0!s}'.format(', '.join(USER_VERIFICATION_LEVELS)))
        self.user_verification = user_verification

        if authenticator_attachment is not None:
            authenticator_attachment = str(authenticator_attachment).lower()
            if authenticator_attachment not in AUTHENTICATOR_ATTACHMENT_TYPES:
                raise ValueError(
                    'authenticator_attachment must be one of {0!s}'.format(', '.join(AUTHENTICATOR_ATTACHMENT_TYPES)))
        self.authenticator_attachment = authenticator_attachment

        if int(timeout) < 1:
            raise ValueError('timeout must be a positive integer.')
        self.timeout = timeout

        self.public_key_credential_parameters = [
            {
                'alg': i,
                'type': 'public-key'
            }
            for i in public_key_credential_algorithms
        ]

    @property
    def registration_dict(self):
        """
        :return: The publicKeyCredentialCreationOptions dictionary.
        :rtype: dict
        """
        registration_dict = {
            'challenge': self.challenge,
            'rp': {
                'name': self.rp_name,
                'id': self.rp_id
            },
            'user': {
                'id': self.user_id,
                'name': self.user_name,
                'displayName': self.user_display_name
            },
            'pubKeyCredParams': self.public_key_credential_parameters,
            'authenticatorSelection': {},
            'timeout': self.timeout,
            'excludeCredentials': self.exclude_credentials,
            # Relying parties may use AttestationConveyancePreference to specify their
            # preference regarding attestation conveyance during credential generation.
            'attestation': self.attestation,
            'extensions': {}
        }

        if self.user_verification is not None:
            registration_dict['authenticatorSelection']['userVerification'] = self.user_verification

        if self.authenticator_attachment is not None:
            registration_dict['authenticatorSelection']['authenticatorAttachment'] = self.authenticator_attachment

        if self.icon_url is not None:
            registration_dict['user']['icon'] = self.icon_url

        if self.location:
            registration_dict['extensions']['loc'] = True

        if self.authenticator_selection_list is not None:
            registration_dict['extensions']['authnSel'] = self.authenticator_selection_list

        return registration_dict

    @property
    def json(self):
        """
        :return: The publicKeyCredentialCreationOptions dictionary encoded as JSON.
        :rtype: basestring
        """

        return json.dumps(self.registration_dict)


class WebAuthnAssertionOptions(object):
    """
    Generate the options passed to navigator.credentials.get()
    """

    def __init__(self,
                 challenge,
                 webauthn_user,
                 transports,
                 user_verification_requirement,
                 timeout):
        """
        Create a new WebAuthnAssertionOptions object.

        :param challenge: The challenge is a buffer of cryptographically random bytes needed to prevent replay attacks.
        :type challenge: basestring
        :param webauthn_user: A user cred or a list of user creds to allow authentication with.
        :type webauthn_user: WebAuthnUser or list of WebAuthnUser
        :param transports: Which transports to ask for.
        :type transports: list of basestring
        :param user_verification_requirement: The level of user verification this authentication requires.
        :type user_verification_requirement: basestring
        :param timeout: The time (in milliseconds) that the user has to respond to the prompt for authentication.
        :type timeout: int
        :return: A WebAuthnAssertionOptions object.
        :rtype: WebAuthnAssertionOptions
        """

        self.challenge = challenge
        if not self.challenge:
            raise ValueError('The challenge may not be empty.')

        self.webauthn_users = webauthn_user if isinstance(webauthn_user, list) else [webauthn_user]
        if not self.webauthn_users:
            raise ValueError('webauthn_user may not be empty.')
        for user in self.webauthn_users:
            if not isinstance(user, WebAuthnUser):
                raise ValueError('webauthn_user must be of type WebAuthnUser.')
            if not user.credential_id:
                raise ValueError('user must have a credential_id.')
            if not user.rp_id:
                raise ValueError('user must have a rp_id.')

        if len(set([u.rp_id for u in self.webauthn_users])) != 1:
            raise ValueError('all users must have the same rp_id.')
        self.rp_id = self.webauthn_users[0].rp_id

        self.timeout = timeout
        if int(self.timeout) < 1:
            raise ValueError('timeout must be a positive integer.')

        self.transports = transports
        if not self.transports:
            raise ValueError('transports may not be empty.')

        self.user_verification_requirement = str(user_verification_requirement).lower()
        if self.user_verification_requirement not in USER_VERIFICATION_LEVELS:
            raise ValueError(
                'user_verification_requirement must be one of {0!s}'.format(', '.join(USER_VERIFICATION_LEVELS)))

    @property
    def assertion_dict(self):
        """
        :return: The publicKeyCredentialRequestOptions dictionary.
        :rtype: dict
        """

        return {
            'challenge': self.challenge,
            'allowCredentials': [
                {
                    'type': 'public-key',
                    'id': user.credential_id,
                    'transports': self.transports
                }
                for user in self.webauthn_users
            ],
            'rpId': self.rp_id,
            'userVerification': self.user_verification_requirement,
            'timeout': self.timeout
        }

    @property
    def json(self):
        """
        :return: The publicKeyCredentialRequestOptions dictionary encoded as JSON.
        :rtype: basestring
        """

        return json.dumps(self.assertion_dict)


class WebAuthnUser(object):
    """
    A single WebAuthn user credential.
    """

    def __init__(self,
                 user_id,
                 user_name,
                 user_display_name,
                 icon_url,
                 credential_id,
                 public_key,
                 sign_count,
                 rp_id):
        """
        Create a new WebAuthnUser object.

        :param user_id: The ID for the user credential being stored. This is the privacyIDEA token serial.
        :type user_id: basestring
        :param user_name: The username the user logs in with.
        :type user_name: basestring
        :param user_display_name: The human-readable name of the user.
        :type user_display_name: basestring
        :param icon_url: An optional icon url.
        :type icon_url: basestring
        :param credential_id: The ID of the credential.
        :type credential_id: basestring
        :param public_key: The credential public key.
        :type public_key: basestring
        :param sign_count: The signature counter value.
        :type sign_count: int
        :param rp_id: The ID of the relying party associated with this credential.
        :type rp_id: basestring
        :return: A WebAuthnUser object.
        :rtype: WebAuthnUser
        """

        if not credential_id:
            raise WebAuthnUserDataMissing("credential_id missing")
        if not public_key:
            raise WebAuthnUserDataMissing("public_key missing")
        if not rp_id:
            raise WebAuthnUserDataMissing("rp_id missing")

        self.user_id = user_id
        self.user_name = user_name
        self.user_display_name = user_display_name
        self.icon_url = icon_url
        self.credential_id = credential_id
        self.public_key = public_key
        self.sign_count = sign_count
        self.rp_id = rp_id

    def __str__(self):
        return '{!r} ({}, {}, {})'.format(self.user_id, self.user_name,
                                          self.user_display_name, self.sign_count)


class WebAuthnCredential(object):
    """
    A single WebAuthn credential.
    """

    def __init__(self,
                 rp_id,
                 origin,
                 aaguid,
                 credential_id,
                 public_key,
                 sign_count,
                 attestation_level,
                 attestation_cert=None):
        """
        Create a new WebAuthnCredential object.

        :param rp_id: The relying party ID.
        :type rp_id: basestring
        :param origin: The origin of the user the credential is for.
        :type origin: basestring
        :param aaguid: The aaguid of the token used to create the credential
        :type aaguid: bytes
        :param credential_id: The ID of the credential.
        :type credential_id: basestring or bytes
        :param public_key: The public key of the credential.
        :type public_key: basestring or bytes
        :param sign_count: The signature count.
        :type sign_count: int
        :param attestation_level: The level of attestation that was provided for this credential.
        :type attestation_level: basestring
        :param attestation_cert: The attestation certificate, if any.
        :type attestation_cert: Certificate
        :return: A WebAuthnCredential
        :rtype: WebAuthnCredential
        """

        self.rp_id = rp_id
        self.origin = origin
        self.aaguid = aaguid
        self.credential_id = to_bytes(credential_id)
        self.public_key = to_bytes(public_key)
        self.sign_count = sign_count
        self.attestation_cert = attestation_cert

        attestation_level = str(attestation_level).lower()
        if attestation_level not in ATTESTATION_LEVELS:
            raise ValueError('Attestation level must be one of {0!s}'.format(', '.join(ATTESTATION_LEVELS)))
        self.attestation_level = attestation_level

    @property
    def has_signed_attestation(self):
        """
        :return: Whether this credential was created with a signed attestation.
        :rtype: bool
        """

        return not ATTESTATION_REQUIREMENT_LEVEL[self.attestation_level]['none_attestation_permitted']

    @property
    def has_trusted_attestation(self):
        """
        :return: Whether this credential was created with an attestation signed by a trusted root.
        :rtype: bool
        """

        return not ATTESTATION_REQUIREMENT_LEVEL[self.attestation_level]['self_attestation_permitted']

    def __str__(self):
        return '{!r} ({}, {}, {})'.format(self.credential_id, self.rp_id,
                                          self.origin, self.sign_count)


class WebAuthnRegistrationResponse(object):
    """
    The WebAuthn registration response containing all information needed to verify the registration ceremony.
    """

    def __init__(self,
                 rp_id,
                 origin,
                 registration_response,
                 challenge,
                 attestation_requirement_level,
                 trust_anchor_dir=None,
                 uv_required=False,
                 expected_registration_client_extensions=None,
                 expected_registration_authenticator_extensions=None):
        """
        Create a new WebAuthnRegistrationResponse object.

        :param rp_id: The Relying party id.
        :type rp_id: basestring
        :param origin: The origin of the user.
        :type origin: basestring
        :param registration_response: The registration response containing the client data and attestation.
        :type registration_response: dict
        :param challenge: The challenge that was sent to the client.
        :type challenge: basestring
        :param attestation_requirement_level: Which level of attestation to allow without failing the ceremony.
        :type attestation_requirement_level: dict
        :param trust_anchor_dir: The path to the directory containing the trust anchors
        :type trust_anchor_dir: basestring
        :param uv_required: Whether user verification is required.
        :type uv_required: bool
        :param expected_registration_client_extensions: A dict whose keys indicate which client extensions are expected.
        :type expected_registration_client_extensions: dict
        :param expected_registration_authenticator_extensions: A dict whose keys indicate which auth exts to expect.
        :return: A WebAuthnRegistrationResponse object.
        :rtype: WebAuthnRegistrationResponse
        """

        self.rp_id = rp_id
        self.origin = origin
        self.registration_response = registration_response
        self.challenge = challenge
        self.trust_anchor_dir = trust_anchor_dir
        self.uv_required = uv_required

        self.expected_registration_client_extensions = expected_registration_client_extensions \
            if expected_registration_client_extensions \
            else DEFAULT_CLIENT_EXTENSIONS
        self.expected_registration_authenticator_extensions = expected_registration_authenticator_extensions \
            if expected_registration_authenticator_extensions \
            else DEFAULT_AUTHENTICATOR_EXTENSIONS

        if attestation_requirement_level not in ATTESTATION_REQUIREMENT_LEVELS:
            raise ValueError('Illegal attestation_requirement_level.')

        # With self attestation, the credential public key is also used as the attestation public key.
        self.self_attestation_permitted = attestation_requirement_level['self_attestation_permitted']
        self.trusted_attestation_cert_required = not self.self_attestation_permitted

        # With none attestation, authenticator attestation will not be performed.
        self.none_attestation_permitted = attestation_requirement_level['none_attestation_permitted']

    @staticmethod
    def parse_attestation_object(attestation_object):
        """
        Pull the individual fields out of an attestation object.

        :param attestation_object: The attestation object, as passed by the authenticator.
        :type attestation_object: basestring
        :return: The result of CBOR-decoding the attestation_object.
        :rtype: dict
        """

        return cbor2.loads(webauthn_b64_decode(attestation_object))

    @staticmethod
    def verify_attestation_statement(fmt, att_stmt, auth_data, client_data_hash=b'', none_attestation_permitted=True):
        """
        The procedure for verifying an attestation statement.

        The procedure returns either:
            * An error indicating that the attestation is invalid, or
            * The attestation type, and the trust path. This attestation trust path is
              either empty (in case of self attestation), an identifier of an ECDAA-Issuer
              public key (in the case of ECDAA), or a set of X.509 certificates.

        Verification of attestation objects requires that the Relying Party has a trusted
        method of determining acceptable trust anchors in step 15 above. Also, if
        certificates are being used, the Relying Party MUST have access to certificate
        status information for the intermediate CA certificates. The Relying Party MUST
        also be able to build the attestation certificate chain if the client did not
        provide this chain in the attestation information.

        In order to facilitate further checking of the certificate by prepolicies, the
        client_data_hash may be omitted, to only perform parsing of the statement, verifying
        it further down the line.

        :param fmt: The attestation format.
        :type fmt: basestring
        :param att_stmt: The attestation statement structure.
        :type att_stmt: dict
        :param auth_data: The authenticator data claimed to have been used for the attestation.
        :type auth_data: basestring
        :param client_data_hash: The hash of the serialized client data.
        :type client_data_hash: SHA256Type
        :param none_attestation_permitted: Whether to allow for the attestation type to be none or unsupported.
        :type none_attestation_permitted: bool
        :return: The attestation type, trust path, credential public key, credential id and aaguid.
        :rtype: (basestring, Certificate[], basestring, basestring, basestring)
        """

        attestation_data = auth_data[37:]
        aaguid = attestation_data[:16]
        credential_id_len = struct.unpack('!H', attestation_data[16:18])[0]
        cred_id = attestation_data[18:18 + credential_id_len]
        credential_pub_key = attestation_data[18 + credential_id_len:]

        if fmt == ATTESTATION_FORMAT.FIDO_U2F:
            # Step 1.
            #
            # Verify that attStmt is valid CBOR conforming to the syntax
            # defined above and perform CBOR decoding on it to extract the
            # contained fields.
            if 'x5c' not in att_stmt or 'sig' not in att_stmt:
                raise RegistrationRejectedException('Attestation statement must be a valid CBOR object.')

            # Step 2.
            #
            # Let attCert be the value of the first element of x5c. Let certificate
            # public key be the public key conveyed by attCert. If certificate public
            # key is not an Elliptic Curve (EC) public key over the P-256 curve,
            # terminate this algorithm and return an appropriate error.
            att_cert = att_stmt.get('x5c')[0]
            x509_att_cert = load_der_x509_certificate(att_cert, default_backend())
            certificate_public_key = x509_att_cert.public_key()
            if not isinstance(certificate_public_key.curve, SECP256R1):
                raise RegistrationRejectedException('Bad certificate public key.')

            # Step 3.
            #
            # Extract the claimed rpIdHash from authenticatorData, and the
            # claimed credentialId and credentialPublicKey from
            # authenticatorData.attestedCredentialData.
            #
            # The credential public key encoded in COSE_Key format, as defined in Section 7
            # of [RFC8152], using the CTAP2 canonical CBOR encoding form. The COSE_Key-encoded
            # credential public key MUST contain the optional "alg" parameter and MUST NOT
            # contain any other optional parameters. The "alg" parameter MUST contain a
            # COSEAlgorithmIdentifier value. The encoded credential public key MUST also
            # contain any additional required parameters stipulated by the relevant key type
            # specification, i.e., required for the key type "kty" and algorithm "alg" (see
            # Section 8 of [RFC8152]).
            try:
                public_key_alg, credential_public_key = _load_cose_public_key(credential_pub_key)
            except COSEKeyException as e:
                raise RegistrationRejectedException(str(e))

            public_key_u2f = _encode_public_key(credential_public_key)

            # Step 5.
            #
            # Let verificationData be the concatenation of (0x00 || rpIdHash ||
            # clientDataHash || credentialId || publicKeyU2F) (see Section 4.3
            # of [FIDO-U2F-Message-Formats]).
            auth_data_rp_id_hash = _get_auth_data_rp_id_hash(auth_data)
            alg = COSE_ALGORITHM.ES256
            signature = att_stmt['sig']
            verification_data = b''.join([
                b'\0',
                auth_data_rp_id_hash,
                client_data_hash,
                cred_id,
                public_key_u2f
            ])

            # Step 6.
            #
            # Verify the sig using verificationData and certificate public
            # key per [SEC1].
            # TODO: we need to check here what happens if we do not have a
            #  client_data_hash (this happens during the webauthntoken_allowed
            #  pre-policy).
            if client_data_hash:
                try:
                    _verify_signature(certificate_public_key, alg, verification_data, signature)
                except InvalidSignature:
                    raise RegistrationRejectedException('Invalid signature received.')
                except NotImplementedError:
                    # We do not support this. Treat as none attestation, if acceptable.
                    if none_attestation_permitted:
                        attestation_type = ATTESTATION_TYPE.NONE
                        trust_path = []
                        return (
                            attestation_type,
                            trust_path,
                            credential_pub_key,
                            cred_id,
                            aaguid
                        )

                    raise RegistrationRejectedException('Unsupported algorithm.')

            # Step 7.
            #
            # If successful, return attestation type Basic with the
            # attestation trust path set to x5c.
            attestation_type = ATTESTATION_TYPE.BASIC
            trust_path = [x509_att_cert]

            return (
                attestation_type,
                trust_path,
                credential_pub_key,
                cred_id,
                aaguid
            )
        elif fmt == ATTESTATION_FORMAT.PACKED:
            attestation_syntaxes = {
                ATTESTATION_TYPE.BASIC: ([
                    'alg',
                    'x5c',
                    'sig'
                ]),
                ATTESTATION_TYPE.ECDAA: ([
                    'alg',
                    'sig',
                    'ecdaaKeyId'
                ]),
                ATTESTATION_TYPE.SELF_ATTESTATION: ([
                    'alg',
                    'sig'
                ])
            }

            # Step 1.
            #
            # Verify that attStmt is valid CBOR conforming to the syntax
            # defined above and perform CBOR decoding on it to extract the
            # contained fields.
            if set(att_stmt.keys()) not in [set(e) for e in attestation_syntaxes.values()]:
                raise RegistrationRejectedException('Attestation statement must be a valid CBOR object.')

            alg = att_stmt['alg']
            signature = att_stmt['sig']
            verification_data = b''.join([
                auth_data,
                client_data_hash
            ])

            # Step 2.
            #
            # If x5c is present, this indicates that the attestation
            # type is not ECDAA.
            if 'x5c' in att_stmt:
                # TODO: this could be a certificate chain, we should treat it as such
                att_cert = att_stmt['x5c'][0]
                x509_att_cert = load_der_x509_certificate(att_cert, default_backend())
                certificate_public_key = x509_att_cert.public_key()

                # Verify that sig is a valid signature over the
                # concatenation of authenticatorData and clientDataHash
                # using the attestation public key in attestnCert with
                # the algorithm specified in alg.
                #
                # client_data_hash will not be provided, if this function is
                # called just to parse out the attestation data, to check
                # against WEBAUTHNACTION.REQ. In that case, this function will
                # be called a second time later on for the actual validation of
                # the signature.
                if client_data_hash:
                    try:
                        _verify_signature(certificate_public_key, alg, verification_data, signature)
                    except InvalidSignature:
                        raise RegistrationRejectedException('Invalid signature received.')
                    except NotImplementedError:
                        # We do not support this. Treat as none attestation, if acceptable.
                        if none_attestation_permitted:
                            attestation_type = ATTESTATION_TYPE.NONE
                            trust_path = []
                            return (
                                attestation_type,
                                trust_path,
                                credential_pub_key,
                                cred_id,
                                aaguid
                            )

                        raise RegistrationRejectedException('Unsupported algorithm.')

                #
                # Verify that attestnCert meets the requirements in
                # §8.2.1 Packed attestation statement certificate requirements.
                #
                # The attestation certificate MUST have the following
                # fields/extensions:
                #

                # Version MUST be set to 3 (which is indicated by an
                # ASN.1 INTEGER with value 2).
                if x509_att_cert.version.value != x509.Version.v3.value:
                    raise RegistrationRejectedException('Invalid attestation certificate version.')

                subject = x509_att_cert.subject
                c = subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)
                o = subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)
                ou = subject.get_attributes_for_oid(x509.NameOID.ORGANIZATIONAL_UNIT_NAME)
                cn = subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)

                # Subject-C: ISO 3166 code specifying the country
                #            where the Authenticator vendor is
                #            incorporated
                if not c:
                    raise RegistrationRejectedException('Attestation certificate must have subject-C.')

                # Subject-O: Legal name of the Authenticator vendor.
                if not o:
                    raise RegistrationRejectedException('Attestation certificate must have subject-O.')

                # Subject-OU: Literal string "Authenticator Attestation"
                if not ou or ou[0].value != 'Authenticator Attestation':
                    raise RegistrationRejectedException("Attestation certificate must have subject-OU set "
                                                        "to 'Authenticator Attestation'.")

                # Subject-CN: An UTF8String of the vendor's choosing.
                if not cn:
                    raise RegistrationRejectedException('Attestation certificate must have subject-CN.')

                extensions = x509_att_cert.extensions

                # If the related attestation root certificate is used
                # for multiple authenticator models, the Extension OID
                # 1.3.6.1.4.1.45724.1.1.4 (id-fido-gen-ce-aaguid) MUST
                # be present, containing the AAGUID as a 16-byte OCTET
                # STRING. The extension MUST NOT be marked as critical.
                try:
                    oid = x509.ObjectIdentifier('1.3.6.1.4.1.45724.1.1.4')
                    aaguid_ext = extensions.get_extension_for_oid(oid)
                    if aaguid_ext.value.value[2:] != aaguid:
                        raise RegistrationRejectedException('Attestation certificate AAGUID must match '
                                                            'authenticator data.')
                    if aaguid_ext.critical:
                        raise RegistrationRejectedException("Attestation certificate's 'id-fido-gen-ce-aaguid' "
                                                            "extension must not be marked critical.")
                except x509.ExtensionNotFound:
                    # This extension is optional.
                    pass

                # The Basic Constraints extension MUST have the CA
                # component set to false.
                bc_extension = extensions.get_extension_for_class(x509.BasicConstraints)
                if not bc_extension or bc_extension.value.ca:
                    raise RegistrationRejectedException('Attestation certificate must have Basic Constraints '
                                                        'extension with CA=false.')

                # If successful, return attestation type Basic and
                # attestation trust path x5c.
                attestation_type = ATTESTATION_TYPE.BASIC
                trust_path = [x509_att_cert]

                return (
                    attestation_type,
                    trust_path,
                    credential_pub_key,
                    cred_id,
                    aaguid
                )
            elif 'ecdaaKeyId' in att_stmt:
                # We do not support this. If attestation is optional, have it go through anyway.
                if none_attestation_permitted:
                    attestation_type = ATTESTATION_TYPE.ECDAA
                    trust_path = []
                    return (
                        attestation_type,
                        trust_path,
                        credential_pub_key,
                        cred_id,
                        aaguid
                    )

                # Step 3.
                #
                # If ecdaaKeyId is present, then the attestation type is
                # ECDAA. In this case:
                #   * Verify that sig is a valid signature over the
                #     concatenation of authenticatorData and clientDataHash
                #     using ECDAA-Verify with ECDAA-Issuer public key
                #     identified by ecdaaKeyId (see  [FIDOEcdaaAlgorithm]).
                #   * If successful, return attestation type ECDAA and
                #     attestation trust path ecdaaKeyId.
                raise RegistrationRejectedException('ECDAA attestation type is not currently supported.')
            else:
                # self-attestation
                # Step 1:
                # Validate that alg matches the algorithm of the credentialPublicKey
                # in authenticatorData.
                try:
                    public_key_alg, credential_public_key = _load_cose_public_key(credential_pub_key)
                except COSEKeyException as e:
                    raise RegistrationRejectedException(str(e))
                if alg != public_key_alg:
                    raise RegistrationRejectedException('credentialPublicKey algorithm {0!s} does '
                                                        'not match algorithm from attestation '
                                                        'statement {1!s}'.format(public_key_alg, alg))
                # Step 2:
                # Verify that sig is a valid signature over the concatenation of authenticatorData
                # and clientDataHash using the credential public key with alg.
                try:
                    _verify_signature(credential_public_key, alg, verification_data, signature)
                except InvalidSignature:
                    raise RegistrationRejectedException('Invalid signature received.')
                except NotImplementedError:  # pragma: no cover
                    log.warning('Unsupported algorithm ({0!s}) for signature '
                                'verification'.format(alg))
                    # We do not support this algorithm. Treat as none attestation, if acceptable.
                    if none_attestation_permitted:
                        return (
                            ATTESTATION_TYPE.NONE,
                            [],
                            credential_pub_key,
                            cred_id,
                            aaguid
                        )
                    else:
                        raise RegistrationRejectedException('Unsupported algorithm '
                                                            '({0!s}).'.format(alg))
                return (
                    ATTESTATION_TYPE.SELF_ATTESTATION,
                    [],
                    credential_pub_key,
                    cred_id,
                    aaguid
                )
        else:
            # Attestation is either none, or unsupported.
            if not none_attestation_permitted:
                if fmt == ATTESTATION_FORMAT.NONE:
                    raise RegistrationRejectedException('Authenticator attestation is required.')
                else:
                    raise RegistrationRejectedException(
                        'Unsupported authenticator attestation format ({0!s})!'.format(fmt))

            # Treat as none attestation.
            #
            # Step 1.
            #
            # Return attestation type None with an empty trust path.
            attestation_type = ATTESTATION_TYPE.NONE
            trust_path = []
            return (
                attestation_type,
                trust_path,
                credential_pub_key,
                cred_id,
                aaguid
            )

    def verify(self, existing_credential_ids=None):
        """
        Verify the WebAuthnRegistrationResponse.

        This will perform the registration ceremony for the
        WebAuthnRegistrationResponse. It will only return on successful
        verification. In any other case, an appropriate error will be raised.

        :param existing_credential_ids: A list of existing credential ids to check for duplicates.
        :type existing_credential_ids: basestring[]
        :return: The WebAuthnCredential produced by the registration ceremony.
        :rtype: WebAuthnCredential
        """

        try:
            # As described in https://www.w3.org/TR/webauthn/#sctn-registering-a-new-credential
            # In the docs it starts at step 5.
            #
            # Step 1.
            #
            # Let JSONtext be the result of running UTF-8 decode on the value of
            # response.clientDataJSON
            json_text = self.registration_response.get('clientData', '')

            # Step 2.
            #
            # Let C, the client data claimed as collected during the credential
            # creation, be the result of running an implementation-specific JSON
            # parser on JSONtext.
            decoded_cd = webauthn_b64_decode(json_text)
            c = json.loads(to_unicode(decoded_cd))

            # Step 3.
            #
            # Verify that the value of C.type is webauthn.create.
            if not _verify_type(c.get('type'), CLIENT_DATA_TYPE.CREATE):
                raise RegistrationRejectedException('Invalid type.')

            # Step 4.
            #
            # Verify that the value of C.challenge matches the challenge that was sent
            # to the authenticator in the create() call.
            if not _verify_challenge(c.get('challenge'), self.challenge):
                raise RegistrationRejectedException('Unable to verify challenge.')

            # Step 5.
            #
            # Verify that the value of C.origin matches the Relying Party's origin.
            if not _verify_origin(c, self.origin):
                raise RegistrationRejectedException('Unable to verify origin.')

            # Step 6.
            #
            # Verify that the value of C.tokenBinding.status matches the state of
            # Token Binding for the TLS connection over which the assertion was
            # obtained. If Token Binding was used on that TLS connection, also verify
            # that C.tokenBinding.id matches the base64url encoding of the Token
            # Binding ID for the connection.

            # Chrome does not currently supply token binding in the clientDataJSON
            # if not _verify_token_binding_id(c):
            #     raise RegistrationRejectedException('Unable to verify token binding ID.')

            # Step 7.
            #
            # Compute the hash of response.clientDataJSON using SHA-256.
            client_data_hash = _get_client_data_hash(decoded_cd)

            # Step 8.
            #
            # Perform CBOR decoding on the attestationObject field of
            # the AuthenticatorAttestationResponse structure to obtain
            # the attestation statement format fmt, the authenticator
            # data authData, and the attestation statement attStmt.
            att_obj = self.parse_attestation_object(self.registration_response.get('attObj'))
            att_stmt = att_obj.get('attStmt')
            auth_data = att_obj.get('authData')
            fmt = att_obj.get('fmt')
            if not auth_data or len(auth_data) < 37:
                raise RegistrationRejectedException('Auth data must be at least 37 bytes.')

            # Step 9.
            #
            # Verify that the RP ID hash in authData is indeed the
            # SHA-256 hash of the RP ID expected by the RP.
            if not _verify_rp_id_hash(_get_auth_data_rp_id_hash(auth_data), self.rp_id):
                raise RegistrationRejectedException('Unable to verify RP ID hash.')

            # Step 10.
            #
            # Verify that the User Present bit of the flags in authData
            # is set.
            if not AuthenticatorDataFlags(auth_data).user_present:
                raise RegistrationRejectedException('Malformed request received.')

            # Step 11.
            #
            # If user verification is required for this registration, verify
            # that the User Verified bit of the flags in authData is set.
            if self.uv_required and not AuthenticatorDataFlags(auth_data).user_verified:
                raise RegistrationRejectedException('Malformed request received.')

            # Step 12.
            #
            # Verify that the values of the client extension outputs in
            # clientExtensionResults and the authenticator extension outputs
            # in the extensions in authData are as expected, considering the
            # client extension input values that were given as the extensions
            # option in the create() call. In particular, any extension
            # identifier values in the clientExtensionResults and the extensions
            # in authData MUST be also be present as extension identifier values
            # in the extensions member of options, i.e., no extensions are
            # present that were not requested. In the general case, the meaning
            # of "are as expected" is specific to the Relying Party and which
            # extensions are in use.
            if not _verify_authenticator_extensions(auth_data, self.expected_registration_authenticator_extensions):
                raise RegistrationRejectedException('Unable to verify authenticator extensions.')
            if not _verify_client_extensions(
                self.registration_response.get('registrationClientExtensions'),
                self.expected_registration_client_extensions
            ):
                raise RegistrationRejectedException('Unable to verify client extensions.')

            # Step 13.
            #
            # Determine the attestation statement format by performing
            # a USASCII case-sensitive match on fmt against the set of
            # supported WebAuthn Attestation Statement Format Identifier
            # values. The up-to-date list of registered WebAuthn
            # Attestation Statement Format Identifier values is maintained
            # in the IANA registry of the same name.
            if not _verify_attestation_statement_format(fmt):
                raise RegistrationRejectedException('Unable to verify attestation statement format.')

            # Step 14.
            #
            # Verify that attStmt is a correct attestation statement, conveying
            # a valid attestation signature, by using the attestation statement
            # format fmt's verification procedure given attStmt, authData and
            # the hash of the serialized client data computed in step 7.
            (
                attestation_type,
                trust_path,
                credential_public_key,
                cred_id,
                aaguid
            ) = self.verify_attestation_statement(
                fmt,
                att_stmt,
                auth_data,
                client_data_hash,
                self.none_attestation_permitted
            )
            b64_cred_id = webauthn_b64_encode(cred_id)

            # Step 15.
            #
            # If validation is successful, obtain a list of acceptable trust
            # anchors (attestation root certificates or ECDAA-Issuer public
            # keys) for that attestation type and attestation statement format
            # fmt, from a trusted source or from policy. For example, the FIDO
            # Metadata Service [FIDOMetadataService] provides one way to obtain
            # such information, using the aaguid in the attestedCredentialData
            # in authData.
            trust_anchors = _get_trust_anchors(attestation_type, fmt, self.trust_anchor_dir) \
                if self.trust_anchor_dir \
                else None
            if not trust_anchors and self.trusted_attestation_cert_required:
                raise RegistrationRejectedException('No trust anchors available to verify attestation certificate.')

            # Step 16.
            #
            # Assess the attestation trustworthiness using the outputs of the
            # verification procedure in step 14, as follows:
            #
            #     * If self attestation was used, check if self attestation is
            #       acceptable under Relying Party policy.
            #     * If ECDAA was used, verify that the identifier of the
            #       ECDAA-Issuer public key used is included in the set of
            #       acceptable trust anchors obtained in step 15.
            #     * Otherwise, use the X.509 certificates returned by the
            #       verification procedure to verify that the attestation
            #       public key correctly chains up to an acceptable root
            #       certificate.
            if attestation_type == ATTESTATION_TYPE.SELF_ATTESTATION and not self.self_attestation_permitted:
                raise RegistrationRejectedException('Self attestation is not permitted.')
            is_trusted_attestation_cert = ((attestation_type == ATTESTATION_TYPE.BASIC
                                            and _is_trusted_x509_attestation_cert(trust_path, trust_anchors))
                                           or (attestation_type == ATTESTATION_TYPE.ECDAA
                                               and _is_trusted_ecdaa_attestation_certificate(None, trust_anchors)))
            is_signed_attestation_cert = attestation_type in SUPPORTED_ATTESTATION_TYPES

            if is_trusted_attestation_cert:
                attestation_level = ATTESTATION_LEVEL.TRUSTED
            elif is_signed_attestation_cert:
                attestation_level = ATTESTATION_LEVEL.UNTRUSTED
            else:
                attestation_level = ATTESTATION_LEVEL.NONE

            # Step 17.
            #
            # Check that the credentialId is not yet registered to any other user.
            # If registration is requested for a credential that is already registered
            # to a different user, the Relying Party SHOULD fail this registration
            # ceremony, or it MAY decide to accept the registration, e.g. while deleting
            # the older registration.
            if existing_credential_ids and b64_cred_id in existing_credential_ids:
                raise RegistrationRejectedException('Credential already exists.')

            # Step 18.
            #
            # If the attestation statement attStmt verified successfully and is
            # found to be trustworthy, then register the new credential with the
            # account that was denoted in the options.user passed to create(),
            # by associating it with the credentialId and credentialPublicKey in
            # the attestedCredentialData in authData, as appropriate for the
            # Relying Party's system.
            credential = WebAuthnCredential(rp_id=self.rp_id,
                                            origin=self.origin,
                                            aaguid=aaguid,
                                            credential_id=b64_cred_id,
                                            public_key=webauthn_b64_encode(credential_public_key),
                                            sign_count=struct.unpack('!I', auth_data[33:37])[0],
                                            attestation_level=attestation_level,
                                            attestation_cert=trust_path[0] if trust_path else None)
            if is_trusted_attestation_cert:
                return credential

            # Step 19.
            #
            # If the attestation statement attStmt successfully verified but is
            # not trustworthy per step 16 above, the Relying Party SHOULD fail
            # the registration ceremony.
            #
            #     NOTE: However, if permitted by policy, the Relying Party MAY
            #           register the credential ID and credential public key but
            #           treat the credential as one with self attestation (see
            #           6.3.3 Attestation Types). If doing so, the Relying Party
            #           is asserting there is no cryptographic proof that the
            #           public key credential has been generated by a particular
            #           authenticator model. See [FIDOSecRef] and [UAFProtocol]
            #           for a more detailed discussion.
            if self.trusted_attestation_cert_required:
                raise RegistrationRejectedException('Untrusted attestation certificate.')
            if not is_signed_attestation_cert and not self.none_attestation_permitted:
                raise RegistrationRejectedException('No (or unsupported) attestation certificate.')
            return credential

        except Exception as e:
            raise RegistrationRejectedException('Registration rejected. Error: {}'.format(e))


class WebAuthnAssertionResponse(object):
    """
    The WebAuthn assertion response containing all information needed to verify the authentication ceremony.
    """

    def __init__(self,
                 webauthn_user,
                 assertion_response,
                 challenge,
                 origin,
                 allow_credentials=None,
                 uv_required=False,
                 expected_assertion_client_extensions=None,
                 expected_assertion_authenticator_extensions=None):
        """
        Create a new WebAUthnAssertionResponse object.

        :param webauthn_user: The WebAuthnUser used to create the assertion.
        :type webauthn_user: WebAuthnUser
        :param assertion_response: The assertion as a public key credential dictionary.
        :type assertion_response: dict
        :param challenge: The challenge that was sent to the client.
        :type challenge: basestring
        :param origin: The origin of the user.
        :type origin: basestring
        :param allow_credentials: Which existing credentials to allow for the authentication.
        :type allow_credentials: list of basestring
        :param uv_required: Whether user verification is required.
        :type uv_required: bool
        :param expected_assertion_client_extensions: A dict whose keys indicate which client extensions are expected.
        :type expected_assertion_client_extensions: dict
        :param expected_assertion_authenticator_extensions: A dict whose keys indicate which auth exts to expect.
        :type expected_assertion_authenticator_extensions: dict
        :return: A WebAuthnAssertionResponse object.
        :rtype: WebAuthnAssertionResponse
        """
        self.assertion_response = assertion_response
        self.challenge = challenge
        self.origin = origin
        self.allow_credentials = allow_credentials
        self.uv_required = uv_required

        self.expected_assertion_client_extensions = expected_assertion_client_extensions \
            if expected_assertion_client_extensions \
            else DEFAULT_CLIENT_EXTENSIONS
        self.expected_assertion_authenticator_extensions = expected_assertion_authenticator_extensions \
            if expected_assertion_authenticator_extensions \
            else DEFAULT_AUTHENTICATOR_EXTENSIONS

        if not isinstance(webauthn_user, WebAuthnUser):
            raise ValueError('Invalid user type.')
        self.webauthn_user = webauthn_user

    def verify(self):
        """
        Verify the WebAuthnAssertionResponse.

        This will perform the authentication ceremony for the
        WebAuthnAssertionResponse. It will only return on successful
        verification. In any other case, an appropriate error will be raised.

        :return: The new sign count of the authenticated credential.
        :rtype: int
        """

        try:
            # Step 1.
            #
            # If the allowCredentials option was given when this authentication
            # ceremony was initiated, verify that credential.id identifies one
            # of the public key credentials that were listed in allowCredentials.
            if self.allow_credentials and self.assertion_response.get('id') not in self.allow_credentials:
                raise AuthenticationRejectedException('Credential not allowed.')

            # Step 2.
            #
            # If credential.response.userHandle is present, verify that the user
            # identified by this value is the owner of the public key credential
            # identified by credential.id.
            user_handle = self.assertion_response.get('userHandle')
            if user_handle and not user_handle == self.webauthn_user.user_id:
                raise AuthenticationRejectedException('Invalid credential: user '
                                                      'handle does not match.')

            # Step 3.
            #
            # Using credential's id attribute (or the corresponding rawId, if
            # base64url encoding is inappropriate for your use case), look up
            # the corresponding credential public key.
            if not _validate_credential_id(self.webauthn_user.credential_id):
                raise AuthenticationRejectedException('Invalid credential ID.')
            if not self.webauthn_user.public_key:
                raise WebAuthnUserDataMissing("public_key missing.")
            public_key_alg, user_pubkey = _load_cose_public_key(webauthn_b64_decode(self.webauthn_user.public_key))

            # Step 4.
            #
            # Let cData, aData and sig denote the value of credential's
            # response's clientDataJSON, authenticatorData, and signature
            # respectively.
            c_data = webauthn_b64_decode(self.assertion_response.get('clientData'))
            a_data = webauthn_b64_decode(self.assertion_response.get('authData'))
            sig = webauthn_b64_decode(self.assertion_response.get('signature'))

            # Step 5.
            #
            # Let JSONtext be the result of running UTF-8 decode on the
            # value of cData.
            json_text = to_unicode(c_data)

            # Step 6.
            #
            # Let C, the client data claimed as used for the signature,
            # be the result of running an implementation-specific JSON
            # parser on JSONtext.
            c = json.loads(json_text)

            # Step 7.
            #
            # Verify that the value of C.type is the string webauthn.get.
            if not _verify_type(c.get('type'), CLIENT_DATA_TYPE.GET):
                raise RegistrationRejectedException('Invalid type.')

            # Step 8.
            #
            # Verify that the value of C.challenge matches the challenge
            # that was sent to the authenticator in the
            # PublicKeyCredentialRequestOptions passed to the get() call.
            if not _verify_challenge(c.get('challenge'), self.challenge):
                raise AuthenticationRejectedException('Unable to verify challenge.')

            # Step 9.
            #
            # Verify that the value of C.origin matches the Relying
            # Party's origin.
            if not _verify_origin(c, self.origin):
                raise AuthenticationRejectedException('Unable to verify origin.')

            # Step 10.
            #
            # Verify that the value of C.tokenBinding.status matches
            # the state of Token Binding for the TLS connection over
            # which the attestation was obtained. If Token Binding was
            # used on that TLS connection, also verify that
            # C.tokenBinding.id matches the base64url encoding of the
            # Token Binding ID for the connection.

            # XXX: Chrome does not currently supply token binding in the clientDataJSON
            # if not _verify_token_binding_id(c):
            #     raise AuthenticationRejectedException('Unable to verify token binding ID.')

            # Step 11.
            #
            # Verify that the rpIdHash in aData is the SHA-256 hash of
            # the RP ID expected by the Relying Party.
            if not _verify_rp_id_hash(_get_auth_data_rp_id_hash(a_data), self.webauthn_user.rp_id):
                raise AuthenticationRejectedException('Unable to verify RP ID hash.')

            # Step 12.
            #
            # Verify that the User Present bit of the flags in authData
            # is set.
            if not AuthenticatorDataFlags(a_data).user_present:
                raise AuthenticationRejectedException('Malformed request received.')

            # Step 13.
            #
            # If user verification is required for this assertion, verify that
            # the User Verified bit of the flags in authData is set.
            if self.uv_required and not AuthenticatorDataFlags(a_data).user_verified:
                raise RegistrationRejectedException('Malformed request received.')

            # Step 14.
            #
            # Verify that the values of the client extension outputs in
            # clientExtensionResults and the authenticator extension outputs
            # in the extensions in authData are as expected, considering the
            # client extension input values that were given as the extensions
            # option in the get() call. In particular, any extension identifier
            # values in the clientExtensionResults and the extensions in
            # authData MUST be also be present as extension identifier values
            # in the extensions member of options, i.e., no extensions are
            # present that were not requested. In the general case, the meaning
            # of "are as expected" is specific to the Relying Party and which
            # extensions are in use.
            if not _verify_authenticator_extensions(a_data, self.expected_assertion_authenticator_extensions):
                raise AuthenticationRejectedException('Unable to verify authenticator extensions.')
            if not _verify_client_extensions(
                self.assertion_response.get('assertionClientExtensions'),
                self.expected_assertion_client_extensions
            ):
                raise AuthenticationRejectedException('Unable to verify client extensions.')

            # Step 15.
            #
            # Let hash be the result of computing a hash over the cData
            # using SHA-256.
            client_data_hash = _get_client_data_hash(c_data)

            # Step 16.
            #
            # Using the credential public key looked up in step 3, verify
            # that sig is a valid signature over the binary concatenation
            # of aData and hash.
            try:
                _verify_signature(public_key=user_pubkey,
                                  alg=public_key_alg,
                                  data=b''.join([
                                      a_data,
                                      client_data_hash
                                  ]),
                                  signature=sig)
            except InvalidSignature:
                raise AuthenticationRejectedException('Invalid signature received.')
            except NotImplementedError:
                raise AuthenticationRejectedException('Unsupported algorithm.')

            # Step 17.
            #
            # If the signature counter value adata.signCount is nonzero or
            # the value stored in conjunction with credential's id attribute
            # is nonzero, then run the following sub-step:
            #     If the signature counter value adata.signCount is
            #         greater than the signature counter value stored in
            #         conjunction with credential's id attribute.
            #             Update the stored signature counter value,
            #             associated with credential's id attribute,
            #             to be the value of adata.signCount.
            #         less than or equal to the signature counter value
            #         stored in conjunction with credential's id attribute.
            #             This is a signal that the authenticator may be
            #             cloned, i.e. at least two copies of the credential
            #             private key may exist and are being used in parallel.
            #             Relying Parties should incorporate this information
            #             into their risk scoring. Whether the Relying Party
            #             updates the stored signature counter value in this
            #             case, or not, or fails the authentication ceremony
            #             or not, is Relying Party-specific.
            sign_count = struct.unpack('!I', a_data[33:37])[0]
            if (sign_count != 0 or self.webauthn_user.sign_count != 0) and sign_count <= self.webauthn_user.sign_count:
                raise AuthenticationRejectedException('Duplicate authentication detected.')

            # Step 18.
            #
            # If all the above steps are successful, continue with the
            # authentication ceremony as appropriate. Otherwise, fail the
            # authentication ceremony.
            return sign_count

        except Exception as e:
            raise AuthenticationRejectedException('Authentication rejected. Error: {}'.format(e))


def webauthn_b64_decode(encoded):
    """
    Pad a WebAuthn base64-encoded string and decode it.

    WebAuthn specifies a web-safe base64 encoding *without* padding. Since
    this is the same as u2f, this function will just rely on the existing u2f
    implementation of this algorithm.

    :param encoded: A WebAuthn base64-encoded string.
    :type encoded: basestring or bytes
    :return: The decoded binary.
    :rtype: bytes
    """

    return url_decode(encoded)


def webauthn_b64_encode(raw):
    """
    Encode bytes using WebAuthn base64-encoding.

    WebAuthn specifies a web-safe base64 encoding *without* padding. Since
    this is the same as u2f, this function will just rely on the existing u2f
    implementation of this algorithm.

    :param raw: Bytes to encode.
    :type raw: basestring or bytes
    :return: The encoded base64.
    :rtype: basestring
    """

    return url_encode(raw)


def _encode_public_key(public_key):
    """
    Extracts the x and y coordinates from a public point on a Cryptography elliptic curve.

    The result of running this function is a 65 byte string. This function is the inverse of
    decode_public_key().public_key().

    :param public_key: An EllipticCurvePublicKey object
    :return: The coordinates packed into a standard byte string representation.
    """
    numbers = public_key.public_numbers()
    return b'\x04' + binascii.unhexlify('{:064x}{:064x}'.format(numbers.x, numbers.y))


def _load_cose_public_key(key_bytes):

    cose_public_key = cbor2.loads(key_bytes)

    if COSE_PUBLIC_KEY.ALG not in cose_public_key:
        raise COSEKeyException('Public key missing required algorithm parameter.')

    alg = cose_public_key[COSE_PUBLIC_KEY.ALG]

    if alg == COSE_ALGORITHM.ES256:

        required_keys = {
            COSE_PUBLIC_KEY.ALG,
            COSE_PUBLIC_KEY.X,
            COSE_PUBLIC_KEY.Y
        }

        if not set(cose_public_key.keys()).issuperset(required_keys):
            raise COSEKeyException('Public key must match COSE_Key spec.')

        if len(cose_public_key[COSE_PUBLIC_KEY.X]) != 32:
            raise RegistrationRejectedException('Bad public key.')
        x = int(codecs.encode(cose_public_key[COSE_PUBLIC_KEY.X], 'hex'), 16)

        if len(cose_public_key[COSE_PUBLIC_KEY.Y]) != 32:
            raise RegistrationRejectedException('Bad public key.')
        y = int(codecs.encode(cose_public_key[COSE_PUBLIC_KEY.Y], 'hex'), 16)

        return alg, EllipticCurvePublicNumbers(x, y, SECP256R1()).public_key(backend=default_backend())
    elif alg in (COSE_ALGORITHM.PS256, COSE_ALGORITHM.RS256, COSE_ALGORITHM.RS1):

        required_keys = {
            COSE_PUBLIC_KEY.ALG,
            COSE_PUBLIC_KEY.E,
            COSE_PUBLIC_KEY.N
        }

        if not set(cose_public_key.keys()).issuperset(required_keys):
            raise COSEKeyException('Public key must match COSE_Key spec.')

        if len(cose_public_key[COSE_PUBLIC_KEY.E]) != 3 or len(cose_public_key[COSE_PUBLIC_KEY.N]) != 256:
            raise COSEKeyException('Bad public key.')

        e = int(codecs.encode(cose_public_key[COSE_PUBLIC_KEY.E], 'hex'), 16)
        n = int(codecs.encode(cose_public_key[COSE_PUBLIC_KEY.N], 'hex'), 16)

        return alg, RSAPublicNumbers(e, n).public_key(backend=default_backend())
    else:
        log.warning('Unsupported webAuthn COSE algorithm: {0!s}'.format(alg))
        raise COSEKeyException('Unsupported algorithm.')


def _get_trust_anchors(attestation_type, attestation_fmt, trust_anchor_dir):
    """
    Return a list of trusted attestation root certificates.

    This will fetch all CA certificates from the given directory, silently
    skipping any invalid ones.

    :param attestation_type: The attestation type being used. If the type is
                             unsupported, an empty list is returned.
    :type attestation_type: str
    :param attestation_fmt: The attestation format being used. If the format is
                            unsupported, an empty list is returned.
    :type attestation_fmt: str
    :param trust_anchor_dir: The path to the directory that contains the CA certificates.
    :type trust_anchor_dir: str
    :return: The list of trust anchors.
    :rtype: list
    """

    if attestation_type not in SUPPORTED_ATTESTATION_TYPES \
            or attestation_fmt not in SUPPORTED_ATTESTATION_FORMATS:
        log.debug('Unsupported attestation type ({0!s}) or attestation format '
                  '({1!s}).'.format(attestation_type, attestation_fmt))
        return []

    trust_anchors = []

    if os.path.isdir(trust_anchor_dir):
        for trust_anchor_name in os.listdir(trust_anchor_dir):
            trust_anchor_path = os.path.join(trust_anchor_dir, trust_anchor_name)
            if os.path.isfile(trust_anchor_path):
                try:
                    with open(trust_anchor_path, 'rb') as f:
                        pem_data = f.read().strip()
                        pem = cryptography.x509.load_pem_x509_certificate(pem_data.strip())
                        trust_anchors.append(pem)
                except Exception as e:
                    log.info('Could not load certificate {0!s}: '
                             '{1!s}'.format(trust_anchor_path, e))
    else:
        log.debug('Trust anchor directory ({0!s}) not available.'.format(trust_anchor_dir))

    return trust_anchors


def _is_trusted_x509_attestation_cert(trust_path, trust_anchors):
    if not trust_path or not isinstance(trust_path, list) or not trust_anchors or not isinstance(trust_anchors, list):
        return False

    # TODO: this could be a certificate chain. We should treat it as such
    attestation_cert = trust_path[0]
    store = crypto.X509Store()
    # Since the certificates are in pyca.cryptography format, we need to convert
    # them to the OpenSSL.crypto format
    for i in trust_anchors:
        store.add_cert(crypto.X509.from_cryptography(i))
    store_ctx = crypto.X509StoreContext(store, crypto.X509.from_cryptography(attestation_cert))

    try:
        store_ctx.verify_certificate()
        return True
    except Exception as e:
        log.info('Unable to verify certificate: {}'.format(e))

    return False


def _is_trusted_ecdaa_attestation_certificate(ecdaa_issuer_public_key, trust_anchors):
    # TODO: implement
    raise NotImplementedError


def _verify_type(received_type, expected_type):
    return received_type == expected_type


def _verify_challenge(received_challenge, sent_challenge):
    return received_challenge \
        and sent_challenge \
        and isinstance(received_challenge, str) \
        and isinstance(sent_challenge, str) \
        and constant_time.bytes_eq(
            to_bytes(sent_challenge),
            to_bytes(received_challenge)
        )


def _verify_origin(client_data, origin):
    return isinstance(client_data, dict) \
        and client_data.get('origin') \
        and client_data.get('origin') == origin


def _verify_token_binding_id(client_data):
    """
    Verify tokenBinding. Currently, this is unimplemented, so it will simply
    return false if tokenBinding is required.

    The tokenBinding member contains information about the state of the
    Token Binding protocol used when communicating with the Relying Party.
    The status member is one of:
        not-supported: when the client does not support token binding.
            supported: the client supports token binding, but it was not
                       negotiated when communicating with the Relying
                       Party.
              present: token binding was used when communicating with the
                       Relying Party. In this case, the id member MUST be
                       present and MUST be a base64url encoding of the
                       Token Binding ID that was used.

    :param client_data: The WebAuthn client data dictionary.
    :type client_data: dict
    :return: False, if tokenBinding is present.
    :rtype: bool
    """

    return client_data['tokenBinding']['status'] in ('supported', 'not_supported')


def _verify_client_extensions(client_extensions, expected_client_extensions):
    """
    Verify the client extensions.

    This will verify that no additional extensions were provided, that were not requested.  The extensions will be
    passed in as provided by the authenticator. Any parsing is done inside the function.

    :param client_extensions: The registrationClientExtensions or assertionClientExtensions field, respectively.
    :type client_extensions: basestring
    :param expected_client_extensions: A dictionary whose keys indicate the extensions to expect.
    :type expected_client_extensions: dict
    :return: Whether there were any unexpected extensions.
    :rtype: bool
    """
    return not client_extensions \
           or set(expected_client_extensions.keys()).issuperset(json.loads(client_extensions).keys())


def _verify_authenticator_extensions(auth_data, expected_authenticator_extensions):
    """
    Verify the authenticator extensions.

    This implementation does not currently support any authenticator
    extensions, so the authenticator is expected to never send any. Thus,
    this function will simply return false if there is any authenticator
    extensions at all for now.

    :param auth_data: The authenticator data.
    :type auth_data: bytes
    :param expected_authenticator_extensions: A dictionary whose keys indicate the extensions to expect.
    :type expected_authenticator_extensions: dict
    :return: Whether there were any unexpected extensions.
    :rtype: bool
    """
    return not AuthenticatorDataFlags(auth_data).extension_data_included


def _verify_rp_id_hash(auth_data_rp_id_hash, rp_id):
    rp_id_hash = hashlib.sha256(to_bytes(rp_id)).digest()
    return constant_time.bytes_eq(auth_data_rp_id_hash, rp_id_hash)


def _verify_attestation_statement_format(fmt):
    """
    Verify that the attestation statement format identifier matches a registered attestation statement format.

    :param fmt: The attestation statement format.
    :type fmt: basestring
    :return: Whether the attestation statement format is supported.
    :rtype: bool
    """

    return isinstance(fmt, str) and fmt in REGISTERED_ATTESTATION_FORMATS


def _get_auth_data_rp_id_hash(auth_data):
    if not isinstance(auth_data, bytes):
        return False

    return auth_data[:32]


def _get_client_data_hash(decoded_client_data):
    """
    Compute the SHA256 hash of the client data.

    :param decoded_client_data: The client data to hash.
    :type decoded_client_data: bytes
    :return: The hash of the client data.
    :rtype: bytes
    """
    if not isinstance(decoded_client_data, bytes):
        return ''

    return hashlib.sha256(decoded_client_data).digest()


def _validate_credential_id(credential_id):
    return isinstance(credential_id, str)


def _verify_signature(public_key, alg, data, signature):
    if alg == COSE_ALGORITHM.ES256:
        public_key.verify(signature, data, ECDSA(SHA256()))
    elif alg == COSE_ALGORITHM.RS256:
        public_key.verify(signature, data, PKCS1v15(), SHA256())
    elif alg == COSE_ALGORITHM.PS256:
        padding = PSS(mgf=MGF1(SHA256()), salt_length=PSS.MAX_LENGTH)
        public_key.verify(signature, data, padding, SHA256())
    elif alg == COSE_ALGORITHM.RS1:
        public_key.verify(signature, data, PKCS1v15(), SHA1())  # nosec B303 # part of webauthn specification
    else:
        raise NotImplementedError()
