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

import json
import logging

__doc__ = """
Business logic for WebAuthn protocol.

This file implements the server part of the WebAuthn protocol.

This file is tested in tests/test_lib_tokens_webauthn.py
"""

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
    ES384 = -35
    ES512 = -36

    PS256 = -37
    PS384 = -38
    PS512 = -39

    RS256 = -257
    RS384 = -258
    RS512 = -259


SUPPORTED_COSE_ALGORITHMS = (
    COSE_ALGORITHM.ES256,
    COSE_ALGORITHM.ES384,
    COSE_ALGORITHM.ES512,
    COSE_ALGORITHM.PS256,
    COSE_ALGORITHM.PS384,
    COSE_ALGORITHM.PS512,
    COSE_ALGORITHM.RS256,
    COSE_ALGORITHM.RS384,
    COSE_ALGORITHM.RS512
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


class COSEKeyException(Exception):
    """
    COSE algorithm key unsupported or unknown.
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

    def __init__(self, challenge, rp_name, rp_id, user_id, user_name, user_display_name, timeout, attestation,
                 user_verification, public_key_credential_algorithms, icon_url=None, authenticator_attachment=None,
                 authenticator_selection_list=None, location=None):
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
        """

        self.challenge = challenge
        self.rp_name = rp_name
        self.rp_id = rp_id
        self.user_id = user_id
        self.user_name = user_name
        self.user_display_name = user_display_name
        self.icon_url = icon_url
        self.timeout = timeout
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
        return json.dumps(self.registration_dict)