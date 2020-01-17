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

import base64
import binascii
import codecs
import hashlib
import json
import logging
import os

import cbor2
import six
from OpenSSL import crypto
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import constant_time
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers, SECP256R1, ECDSA

__doc__ = """
Business logic for WebAuthn protocol.

This file implements the server part of the WebAuthn protocol.

This file is tested in tests/test_lib_tokens_webauthn.py
"""

# Authenticator data flags.
#
# https://www.w3.org/TR/webauthn/#authenticator-data
#
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15, PSS, MGF1
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.hashes import SHA256

USER_PRESENT = 1 << 0
USER_VERIFIED = 1 << 2
ATTESTATION_DATA_INCLUDED = 1 << 6
EXTENSION_DATA_INCLUDED = 1 << 7

# Default client extensions
#
DEFAULT_CLIENT_EXTENSIONS = {'appid': None}

# Default authenticator extensions
#
DEFAULT_AUTHENTICATOR_EXTENSIONS = {}

log = logging.getLogger(__name__)


class ATTESTATION_TYPES(object):
    """
    Attestation types supported by this implementation.
    """

    BASIC = 'Basic'
    ECDAA = 'ECDAA'
    NONE = 'None'
    ATTESTATION_CA = 'AttCA'
    SELF_ATTESTATION = 'Self'


# Only supporting 'None', 'Basic', and 'Self Attestation' attestation types for now.
SUPPORTED_ATTESTATION_TYPES = (
    ATTESTATION_TYPES.BASIC,
    ATTESTATION_TYPES.ECDAA,
    ATTESTATION_TYPES.NONE,
    ATTESTATION_TYPES.ATTESTATION_CA,
    ATTESTATION_TYPES.SELF_ATTESTATION
)


class ATTESTATION_FORMATS(object):
    """
    Attestation formats supported by this implementation.
    """

    FIDO_U2F = 'fido-u2f'
    PACKED = 'packed'
    NONE = 'none'


# Only supporting 'fido-u2f', 'packed', and 'none' attestation formats for now.
SUPPORTED_ATTESTATION_FORMATS = (
    ATTESTATION_FORMATS.FIDO_U2F,
    ATTESTATION_FORMATS.PACKED,
    ATTESTATION_FORMATS.NONE
)


class CLIENT_DATA_TYPES(object):
    """
    Client data types used by this implementation.
    """

    CREATE = 'webauthn.create'
    GET = 'webauthn.get'


SUPPORTED_CLIENT_DATA_TYPES = (
    CLIENT_DATA_TYPES.CREATE,
    CLIENT_DATA_TYPES.GET
)


class COSE_ALGORITHM(object):
    """
    IANA-assigned identifiers of supported COSE algorithms.
    """

    ES256 = -7
    PS256 = -37
    RS256 = -257


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
    LIGHTNING = 'lightning'


TRANSPORTS = (
    TRANSPORT.USB,
    TRANSPORT.BLE,
    TRANSPORT.NFC,
    TRANSPORT.INTERNAL,
    TRANSPORT.LIGHTNING
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
                 location=None):
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
        :param user_name: The user name the user logs in with.
        :type user_name: basestring
        :param user_display_name: The human readable name of the user.
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

        attestation = str(attestation).lower()
        if attestation not in ATTESTATION_FORMS:
            raise ValueError('Attestation string must be one of '
                             + ', '.join(ATTESTATION_FORMS))
        self.attestation = attestation

        if user_verification is not None:
            user_verification = str(user_verification).lower()
            if user_verification not in USER_VERIFICATION_LEVELS:
                raise ValueError('user_verification must be one of '
                                 + ', '.join(USER_VERIFICATION_LEVELS))
        self.user_verification = user_verification

        if authenticator_attachment is not None:
            authenticator_attachment = str(authenticator_attachment).lower()
            if authenticator_attachment not in AUTHENTICATOR_ATTACHMENT_TYPES:
                raise ValueError('authenticator_attachment must be one of '
                                 + ', '.join(AUTHENTICATOR_ATTACHMENT_TYPES))
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
        The publicKeyCredentialCreationOptions dictionary.

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
            'excludeCredentials': [],
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
        The publicKeyCredentialCreationOptions dictionary encoded as JSON.

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
        if len(self.webauthn_users) < 1:
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
        if len(self.transports) < 1:
            raise ValueError('transports may not be empty.')

        self.user_verification_requirement = str(user_verification_requirement).lower()
        if self.user_verification_requirement not in USER_VERIFICATION_LEVELS:
            raise ValueError('user_verification_requirement must be one of '
                             + ', '.join(USER_VERIFICATION_LEVELS))

    @property
    def assertion_dict(self):
        """
        The publicKeyCredentialRequestOptions dictionary.

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
        The publicKeyCredentialRequestOptions dictionary encoded as JSON.

        :return: The publicKeyCredentialRequestOptions dictionary encoded as JSON.
        :rtype: basestring
        """

        return json.dumps(self.assertion_dict)


class WebAuthnUser(object):
    """
    A single WebAuthn user credential.
    """

    def __init__(self,
                 id,
                 name,
                 display_name,
                 icon_url,
                 credential_id,
                 public_key,
                 sign_count,
                 rp_id):
        """
        Create a new WebAuthnUser object.

        :param id: The ID for the user credential being stored. This is the privacyIDEA token serial.
        :type id: basestring
        :param name: The user name the user logs in with.
        :type name: basestring
        :param display_name: The human readable name of the user.
        :type display_name: basestring
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
        if not rp_id:
            raise WebAuthnUserDataMissing("rp_id missing")

        self.id = id
        self.name = name
        self.display_name = display_name
        self.icon_url = icon_url
        self.credential_id = credential_id
        self.public_key = public_key
        self.sign_count = sign_count
        self.rp_id = rp_id

    def __str__(self):
        return '{} ({}, {}, {})'.format(self.id, self.name, self.display_name, self.sign_count)


class WebAuthnCredential(object):
    """
    A single WebAuthn credential.
    """

    def __init__(self,
                 rp_id,
                 origin,
                 credential_id,
                 public_key,
                 sign_count):
        """
        Create a new WebAuthnCredential object.

        :param rp_id: The relying party ID.
        :type rp_id: basestring
        :param origin: The origin of the user the credential is for.
        :type origin: basestring
        :param credential_id: The ID of the credential.
        :type credential_id: basestring
        :param public_key: The public key of the credential.
        :type public_key: basestring
        :param sign_count: The signature count.
        :type sign_count: int
        :return: A WebAuthnCredential
        :rtype: WebAuthnCredential
        """

        self.rp_id = rp_id
        self.origin = origin
        self.credential_id = credential_id
        self.public_key = public_key
        self.sign_count = sign_count

    def __str_(self):
        return '{} ({}, {}, {})'.format(self.credential_id, self.rp_id, self.origin, self.sign_count)


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
    ALG_KEY = 3

    cose_public_key = cbor2.loads(key_bytes)

    if ALG_KEY not in cose_public_key:
        raise COSEKeyException('Public key missing required algorithm parameter.')

    alg = cose_public_key[ALG_KEY]

    if alg == COSE_ALGORITHM.ES256:
        X_KEY = -2
        Y_KEY = -3

        required_keys = {
            ALG_KEY,
            X_KEY,
            Y_KEY
        }

        if not set(cose_public_key.keys()).issuperset(required_keys):
            raise COSEKeyException('Public key must match COSE_Key spec.')

        if len(cose_public_key[X_KEY]) != 32:
            raise RegistrationRejectedException('Bad public key.')
        x = int(codecs.encode(cose_public_key[X_KEY], 'hex'), 16)

        if len(cose_public_key[Y_KEY]) != 32:
            raise RegistrationRejectedException('Bad public key.')
        y = int(codecs.encode(cose_public_key[Y_KEY], 'hex'), 16)

        return alg, EllipticCurvePublicNumbers(x, y, SECP256R1()).public_key(backend=default_backend())
    elif alg in (COSE_ALGORITHM.PS256, COSE_ALGORITHM.RS256):
        E_KEY = -2
        N_KEY = -1

        required_keys = {
            ALG_KEY,
            E_KEY,
            N_KEY
        }

        if not set(cose_public_key.keys()).issuperset(required_keys):
            raise COSEKeyException('Public key must match COSE_Key spec.')

        if len(cose_public_key[E_KEY]) != 3 or len(cose_public_key[N_KEY]) != 256:
            raise COSEKeyException('Bad public key.')

        e = int(codecs.encode(cose_public_key[E_KEY], 'hex'), 16)
        n = int(codecs.encode(cose_public_key[N_KEY], 'hex'), 16)

        return alg, RSAPublicNumbers(e, n).public_key(backend=default_backend())
    else:
        raise COSEKeyException('Unsupported algorithm.')


def _webauthn_b64_decode(encoded):
    """
    Pad a WebAuthn base64-encoded string and decode it.

    WebAuthn specifies web-safe base64 encoding *without* padding. The Python
    implementation of base64 requires padding. This function will add the
    padding back in to a WebAuthn base64-encoded string, then run it through
    the native Python implementation of base64 to decode.

    :param encoded: A WebAuthn base64-encoded string.
    :type encoded: basestring or bytes
    :return: The decoded binary.
    :rtype: bytes
    """

    if isinstance(encoded, bytes):
        encoded = str(encoded, 'utf-8')

    # Add '=' until length is a multiple of 4 bytes, then decode.
    padding_len = (-len(encoded) % 4)
    encoded += '=' * padding_len
    return base64.urlsafe_b64decode(encoded)


def _webauthn_b64_encode(raw):
    """
    Encode bytes using WebAuthn base64-encoding.

    WebAuthn specifies a web-safe base64 encoding *without* padding. The Python
    implementation of base64 will include padding. This function will use the
    native Python implementation of base64 do encode, then strip of the padding.

    :param raw: Bytes to encode.
    :type raw: bytes
    :return: The encoded base64.
    :rtype: bytes
    """
    return base64.urlsafe_b64encode(raw).rstrip(b'=')

def _get_trust_anchors(attestation_type, attestation_fmt, trust_anchor_dir):
    """
    Return a list of trusted attestation root certificates.

    This will fetch all CA certificates from the given directory, silently skipping any invalid ones.

    :param attestation_type: The attestation type being used. If the type is unsupported, an empty list is returned.
    :type attestation_type: basestring
    :param attestation_fmt: The attestation format being used. If the format is unsupported, an empty list is returned.
    :type attestation_fmt: basestring
    :param trust_anchor_dir: The path to the directory that contains the CA certificates.
    :type trust_anchor_dir: basestring
    :return: The list of trust anchors.
    """

    if attestation_type not in SUPPORTED_ATTESTATION_TYPES or attestation_fmt not in SUPPORTED_ATTESTATION_FORMATS:
        return []

    trust_anchors = []

    if os.path.isdir(trust_anchor_dir):
        for trust_anchor_name in os.listdir(trust_anchor_dir):
            trust_anchor_path = os.path.join(trust_anchor_dir, trust_anchor_name)
            if os.path.isfile(trust_anchor_path):
                with open(trust_anchor_path, 'rb') as f:
                    pem_data = f.read().strip()
                    try:
                        pem = crypto.load_certificate(crypto.FILETYPE_PEM, pem_data)
                        trust_anchors.append(pem)
                    except Exception:
                        pass


def _is_trusted_attestation_cert(trust_path, trust_anchors):
    if not trust_path or not isinstance(trust_path, list):
        return False

    # FIXME Only using the first attestation certificate in the trust path for now, should be able to build a chain.
    attestation_cert = trust_path[0]
    store = crypto.X509Store()
    for i in trust_anchors:
        store.add_cert(i)
    store_ctx = crypto.X509StoreContext(store, attestation_cert)

    try:
        store_ctx.verify_certificate()
        return True
    except Exception as e:
        log.info('Unable to verify certificate: {}'.format(e))

    return False


def _verify_type(received_type, expected_type):
    return received_type == expected_type


def _verify_challenge(received_challenge, sent_challenge):
    return received_challenge \
        and sent_challenge \
        and isinstance(received_challenge, six.string_types) \
        and isinstance(sent_challenge, six.string_types) \
        and constant_time.bytes_eq(
            bytes(sent_challenge, encoding='utf-8'),
            bytes(received_challenge, encoding='utf-8')
        )


def _verify_origin(client_data, origin):
    return isinstance(client_data, dict) \
        and client_data.get('origin') \
        and client_data.get('origin') == origin


def _verify_token_binding_id(client_data):
    """
    Verify tokenBinding. Currently this is unimplemented, so it will simply return false if tokenBinding is required.

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

    # TODO Add support for verifying the token binding ID.

    return client_data['tokenBinding']['status'] in ('supported', 'not_supported')


def _verify_client_extensions(client_extensions, expected_client_extensions):
    return set(expected_client_extensions.keys()).issuperset(client_extensions.keys())


def _verify_authenticator_extensions(client_data, expected_authenticator_extensions):
    # TODO
    return True


def _verify_rp_id_hash(auth_data_rp_id_hash, rp_id):
    rp_id_hash = hashlib.sha256(bytes(rp_id, "utf-8")).digest()
    return constant_time.bytes_eq(auth_data_rp_id_hash, rp_id_hash)


def _verify_attestation_statement_format(fmt):
    """
    Verify that the attestation statement format is supported.

    :param fmt: The attestation statement format.
    :type fmt: basestring
    :return: Whether the attestation statement format is supported.
    :rtype: bool
    """

    # TODO Handle more attestation statement formats

    return isinstance(fmt, six.string_types) and fmt in SUPPORTED_ATTESTATION_FORMATS


def _get_auth_data_rp_id_hash(auth_data):
    if not isinstance(auth_data, six.binary_type):
        return False

    return auth_data[:32]


def _get_client_data_hash(decoded_client_data):
    if not isinstance(decoded_client_data, six.binary_type):
        return ''

    return hashlib.sha256(decoded_client_data).digest()


def _validate_credential_id(credential_id):
    return isinstance(credential_id, six.string_types)


def _verify_signature(public_key, alg, data, signature):
    if alg == COSE_ALGORITHM.ES256:
        public_key.verify(signature, data, ECDSA(SHA256()))
    elif alg == COSE_ALGORITHM.RS256:
        public_key.verify(signature, data, PKCS1v15(), SHA256())
    elif alg == COSE_ALGORITHM.PS256:
        padding = PSS(mgf=MGF1(SHA256()), salt_length=PSS.MAX_LENGTH)
        public_key.verify(signature, data, padding, SHA256())
    else:
        raise NotImplementedError()
