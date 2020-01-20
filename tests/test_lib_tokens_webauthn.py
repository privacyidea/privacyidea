# -*- coding: utf-8 -*-
#
# 2020-01-16 Jean-Pierre Höhmann <jean-pierre.hoehmann@netknights.it>
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
# This file contains a class originally adapted from the Duo Security
# implementation of WebAuthn for Python, available under BSD-3-Clause.
#

"""
This file tests the lib.tokens.webauthntoken, along with lib.tokens.webauthn.
This depends on lib.tokenclass
"""
import struct
import unittest
from copy import copy

from privacyidea.lib.tokens.webauthn import (COSE_ALGORITHM, RegistrationRejectedException,
                                             WebAuthnMakeCredentialOptions, AuthenticationRejectedException,
                                             webauthn_b64_decode, webauthn_b64_encode,
                                             WebAuthnRegistrationResponse, ATTESTATION_REQUIREMENT_LEVEL,
                                             ATTESTATION_LEVEL, AuthenticatorDataFlags, WebAuthnAssertionResponse,
                                             WebAuthnUser)
from .base import MyTestCase
from privacyidea.lib.tokens.webauthntoken import WebAuthnTokenClass, WEBAUTHNACTION
from privacyidea.lib.token import init_token
from privacyidea.lib.policy import set_policy, SCOPE


class WebAuthnTokenTestCase(MyTestCase):
    RP_ID = 'example.com'
    RP_NAME = 'ACME'

    def test_00_users(self):
        self.setUp_user_realms()

        set_policy(name="WebAuthn",
                   scope=SCOPE.ENROLL,
                   action=WEBAUTHNACTION.RELYING_PARTY_NAME+"="+self.RP_NAME+","
                          +WEBAUTHNACTION.RELYING_PARTY_ID+"="+self.RP_ID)

    def test_01_create_token(self):
        pin = "1234"

        #
        # Init step 1
        #

        token = init_token({'type': 'webauthn',
                            'pin': pin})
        serial = token.token.serial

        self.assertEqual(token.type, "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_prefix(), "WAN")
        self.assertEqual(WebAuthnTokenClass.get_class_info().get('type'), "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_info('type'), "webauthn")


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
class WebAuthnTestCase(unittest.TestCase):
    REGISTRATION_RESPONSE_TMPL = {
        'clientData': b'eyJ0eXBlIjogIndlYmF1dGhuLmNyZWF0ZSIsICJjbGllbnRFeHRlbnNpb25zIjoge30sICJjaGFsbGVuZ2UiOiAiYlB6cFgzaEhRdHNwOWV2eUtZa2FadFZjOVVOMDdQVWRKMjJ2WlVkRHA5NCIsICJvcmlnaW4iOiAiaHR0cHM6Ly93ZWJhdXRobi5pbyJ9',  # noqa
        'attObj': b'o2NmbXRoZmlkby11MmZnYXR0U3RtdKJjc2lnWEgwRgIhAI1qbvWibQos_t3zsTU05IXw1Ek3SDApATok09uc4UBwAiEAv0fB_lgb5Ot3zJ691Vje6iQLAtLhJDiA8zDxaGjcE3hjeDVjgVkCUzCCAk8wggE3oAMCAQICBDxoKU0wDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBSb290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBaMDExLzAtBgNVBAMMJll1YmljbyBVMkYgRUUgU2VyaWFsIDIzOTI1NzM0ODExMTE3OTAxMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEvd9nk9t3lMNQMXHtLE1FStlzZnUaSLql2fm1ajoggXlrTt8rzXuSehSTEPvEaEdv_FeSqX22L6Aoa8ajIAIOY6M7MDkwIgYJKwYBBAGCxAoCBBUxLjMuNi4xLjQuMS40MTQ4Mi4xLjUwEwYLKwYBBAGC5RwCAQEEBAMCBSAwDQYJKoZIhvcNAQELBQADggEBAKrADVEJfuwVpIazebzEg0D4Z9OXLs5qZ_ukcONgxkRZ8K04QtP_CB5x6olTlxsj-SXArQDCRzEYUgbws6kZKfuRt2a1P-EzUiqDWLjRILSr-3_o7yR7ZP_GpiFKwdm-czb94POoGD-TS1IYdfXj94mAr5cKWx4EKjh210uovu_pLdLjc8xkQciUrXzZpPR9rT2k_q9HkZhHU-NaCJzky-PTyDbq0KKnzqVhWtfkSBCGw3ezZkTS-5lrvOKbIa24lfeTgu7FST5OwTPCFn8HcfWZMXMSD_KNU-iBqJdAwTLPPDRoLLvPTl29weCAIh-HUpmBQd0UltcPOrA_LFvAf61oYXV0aERhdGFYwnSm6pITyZwvdLIkkrMgz0AmKpTBqVCgOX8pJQtghB7wQQAAAAAAAAAAAAAAAAAAAAAAAAAAAECKU1ppjl9gmhHWyDkgHsUvZmhr6oF3_lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r_oOaP8RS44dlQjrH-ALfYtpAECAyYhWCAxnqAfESXOYjKUc2WACuXZ3ch0JHxV0VFrrTyjyjIHXCJYIFnx8H87L4bApR4M-hPcV-fHehEOeW-KCyd0H-WGY8s6'  # noqa
    }
    ASSERTION_RESPONSE_TMPL = {
        'authData': b'dKbqkhPJnC90siSSsyDPQCYqlMGpUKA5fyklC2CEHvABAAACfQ',
        'clientData': b'eyJjaGFsbGVuZ2UiOiJlLWctblhhUnhNYWdFaXFUSlN5RDgyUnNFYzVpZl82anlmSkR5OGJOS2x3Iiwib3JpZ2luIjoiaHR0cHM6Ly93ZWJhdXRobi5pbyIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ',  # noqa
        'signature': b'304502204a76f05cd52a778cdd4df1565e0004e5cc1ead360419d0f5c3a0143bf37e7f15022100932b5c308a560cfe4f244214843075b904b3eda64e85d64662a81198c386cdde',  # noqa
    }
    CRED_KEY = {
        'alg': -7,
        'type': 'public-key'
    }
    REGISTRATION_CHALLENGE = 'bPzpX3hHQtsp9evyKYkaZtVc9UN07PUdJ22vZUdDp94'
    ASSERTION_CHALLENGE = 'e-g-nXaRxMagEiqTJSyD82RsEc5if_6jyfJDy8bNKlw'
    RP_ID = "webauthn.io"
    ORIGIN = "https://webauthn.io"
    USER_NAME = 'testuser'
    ICON_URL = "https://example.com/icon.png"
    USER_DISPLAY_NAME = "A Test User"
    USER_ID = b'\x80\xf1\xdc\xec\xb5\x18\xb1\xc8b\x05\x886\xbc\xdfJ\xdf'
    RP_NAME = "Web Authentication"
    TIMEOUT = 60000
    ATTESTATION = 'direct'
    USER_VERIFICATION = None
    PUBLIC_KEY_CREDENTIAL_ALGORITHMS = [
        COSE_ALGORITHM.ES256,
        COSE_ALGORITHM.RS256,
        COSE_ALGORITHM.PS256
    ]
    EXPECTED_REGISTRATION_CLIENT_EXTENSIONS = {
        'appid': None,
        'loc': None
    }

    def setUp(self):
        self.options = WebAuthnMakeCredentialOptions(
            challenge=self.REGISTRATION_CHALLENGE,
            rp_name=self.RP_NAME,
            rp_id=self.RP_ID,
            user_id=self.USER_ID,
            user_name=self.USER_NAME,
            user_display_name=self.USER_DISPLAY_NAME,
            icon_url=self.ICON_URL,
            timeout=self.TIMEOUT,
            attestation=self.ATTESTATION,
            user_verification=self.USER_VERIFICATION,
            public_key_credential_algorithms=self.PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
            location=True
        )

    def getAssertionResponse(self):
        credential = self.test_01_validate_registration()
        webauthn_user = WebAuthnUser(
            user_id=self.USER_ID,
            user_name=self.USER_NAME,
            user_display_name=self.USER_DISPLAY_NAME,
            icon_url=self.ICON_URL,
            credential_id=credential.credential_id.decode(),
            public_key=credential.public_key,
            sign_count=credential.sign_count,
            rp_id=credential.rp_id
        )

        webauthn_assertion_response = WebAuthnAssertionResponse(
            webauthn_user=webauthn_user,
            assertion_response=copy(self.ASSERTION_RESPONSE_TMPL),
            challenge=self.ASSERTION_CHALLENGE,
            origin=self.ORIGIN,
            uv_required=False,
        )

        return webauthn_assertion_response

    def test_00_create_options(self):
        registration_dict = self.options.registration_dict
        self.assertEqual(registration_dict['challenge'], self.REGISTRATION_CHALLENGE)
        self.assertTrue(self.CRED_KEY in registration_dict['pubKeyCredParams'])

    def test_01_validate_registration(self):
        registration_response = WebAuthnRegistrationResponse(
            rp_id=self.RP_ID,
            origin=self.ORIGIN,
            registration_response=copy(self.REGISTRATION_RESPONSE_TMPL),
            challenge=self.REGISTRATION_CHALLENGE,
            attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.NONE],
            uv_required=False,
            expected_registration_client_extensions=self.EXPECTED_REGISTRATION_CLIENT_EXTENSIONS,
        )

        return registration_response.verify()

    def test_02_registration_invalid_user_verification(self):
        registration_response = WebAuthnRegistrationResponse(
            rp_id=self.RP_ID,
            origin=self.ORIGIN,
            registration_response=copy(self.REGISTRATION_RESPONSE_TMPL),
            challenge=self.REGISTRATION_CHALLENGE,
            attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.UNTRUSTED],
            uv_required=True,
            expected_registration_client_extensions=self.EXPECTED_REGISTRATION_CLIENT_EXTENSIONS
        )

        with self.assertRaises(RegistrationRejectedException):
            registration_response.verify()

    def test_03_validate_assertion(self):
        webauthn_assertion_response = self.getAssertionResponse()
        webauthn_assertion_response.verify()

    def test_04_invalid_signature_fail_assertion(self):
        def mess_up(response):
            response = copy(response)
            response['signature'] = b'00' + response['signature'][2:]
            return response

        webauthn_assertion_response = self.getAssertionResponse()
        webauthn_assertion_response.assertion_response = mess_up(webauthn_assertion_response.assertion_response)

        with self.assertRaises(AuthenticationRejectedException):
            webauthn_assertion_response.verify()

    def test_05_no_user_presence_fail_assertion(self):
        webauthn_assertion_response = self.getAssertionResponse()
        auth_data = webauthn_b64_decode(webauthn_assertion_response.assertion_response['authData'])
        flags = struct.unpack('!B', auth_data[32:33])[0]
        flags = flags & ~AuthenticatorDataFlags.USER_PRESENT
        auth_data = auth_data[:32] + struct.pack('!B', flags) + auth_data[33:]
        webauthn_assertion_response.assertion_response['authData'] = webauthn_b64_encode(auth_data)

        # FIXME This *should* fail because UP=0, but will fail anyway later on because the signature is invalid.
        # TODO Build a mock Authenticator implementation, to be able to sign arbitrary authenticator data statements.
        # TODO Sign an authenticator data statement with UP=0 and test against that so that the signature is valid.
        with self.assertRaises(AuthenticationRejectedException):
            webauthn_assertion_response.verify()
