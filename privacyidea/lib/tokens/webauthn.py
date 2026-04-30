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
import logging
import re

from privacyidea.lib.utils import urlsafe_b64encode_and_unicode, to_bytes, to_unicode

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


class AttestationType:
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
    AttestationType.BASIC,
    AttestationType.NONE,
    AttestationType.SELF_ATTESTATION
)


class AttestationFormat:
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
    AttestationFormat.FIDO_U2F,
    AttestationFormat.PACKED,
    AttestationFormat.NONE
)

REGISTERED_ATTESTATION_FORMATS = (
    AttestationFormat.PACKED,
    AttestationFormat.TPM,
    AttestationFormat.ANDROID_KEY,
    AttestationFormat.ANDROID_SAFETYNET,
    AttestationFormat.APPLE,
    AttestationFormat.FIDO_U2F,
    AttestationFormat.NONE
)


class ClientDataType:
    """
    Client data types used by this implementation.
    """

    CREATE = 'webauthn.create'
    GET = 'webauthn.get'


SUPPORTED_CLIENT_DATA_TYPES = (
    ClientDataType.CREATE,
    ClientDataType.GET
)


class CoseAlgorithm:
    """
    IANA-assigned identifiers of supported COSE algorithms.
    """

    ES256 = -7
    PS256 = -37
    RS256 = -257
    RS1 = -65535  # for tests, otherwise unsupported


SUPPORTED_COSE_ALGORITHMS = (
    CoseAlgorithm.ES256,
    CoseAlgorithm.PS256,
    CoseAlgorithm.RS256,
)


class AttestationForm:
    """
    The different forms of attestation.
    """

    NONE = 'none'
    INDIRECT = 'indirect'
    DIRECT = 'direct'


ATTESTATION_FORMS = (
    AttestationForm.NONE,
    AttestationForm.INDIRECT,
    AttestationForm.DIRECT
)


class UserVerificationLevel:
    """
    The different levels of user verification.
    """

    REQUIRED = 'required'
    PREFERRED = 'preferred'
    DISCOURAGED = 'discouraged'


USER_VERIFICATION_LEVELS = (
    UserVerificationLevel.REQUIRED,
    UserVerificationLevel.PREFERRED,
    UserVerificationLevel.DISCOURAGED
)


class AttestationLevel:
    """
    The different levels of attestation requirement.
    """

    TRUSTED = 'trusted'
    UNTRUSTED = 'untrusted'
    NONE = 'none'


ATTESTATION_LEVELS = (
    AttestationLevel.TRUSTED,
    AttestationLevel.UNTRUSTED,
    AttestationLevel.NONE
)

ATTESTATION_REQUIREMENT_LEVEL = {
    AttestationLevel.TRUSTED: {
        'self_attestation_permitted': False,
        'none_attestation_permitted': False
    },
    AttestationLevel.UNTRUSTED: {
        'self_attestation_permitted': True,
        'none_attestation_permitted': False
    },
    AttestationLevel.NONE: {
        'self_attestation_permitted': True,
        'none_attestation_permitted': True
    }
}

ATTESTATION_REQUIREMENT_LEVELS = (
    ATTESTATION_REQUIREMENT_LEVEL[AttestationLevel.TRUSTED],
    ATTESTATION_REQUIREMENT_LEVEL[AttestationLevel.UNTRUSTED],
    ATTESTATION_REQUIREMENT_LEVEL[AttestationLevel.NONE]
)


class AuthenticatorAttachmentType:
    """
    The different types of authenticator attachment.
    """

    PLATFORM = 'platform'
    CROSS_PLATFORM = 'cross-platform'


AUTHENTICATOR_ATTACHMENT_TYPES = (
    AuthenticatorAttachmentType.PLATFORM,
    AuthenticatorAttachmentType.CROSS_PLATFORM
)


class TRANSPORT:
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


class WebAuthnUserDataMissing(Exception):
    """
    The user data is missing.
    """

    pass


class AuthenticationRejectedException(Exception):
    """
    The authentication attempt was rejected.
    """

    pass


class WebAuthnUser:
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
        return f'{self.user_id!r} ({self.user_name}, {self.user_display_name}, {self.sign_count})'


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
    # remove all non base64 characters (newline, CR) from the string before
    # calculating the padding length
    pad_len = -len(re.sub('[^A-Za-z0-9-_+/]+', '', to_unicode(encoded))) % 4

    padding = pad_len * "="
    res = base64.urlsafe_b64decode(to_bytes(encoded) + to_bytes(padding))
    return res


def webauthn_b64_encode(raw):
    """
    Encode bytes using WebAuthn base64-encoding.

    :param raw: Bytes to encode.
    :type raw: basestring or bytes
    :return: The encoded base64.
    :rtype: basestring
    """

    url = urlsafe_b64encode_and_unicode(raw)
    return url.strip("=")
