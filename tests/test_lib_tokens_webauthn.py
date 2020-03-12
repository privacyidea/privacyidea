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

"""
This file tests the lib.tokens.webauthntoken, along with lib.tokens.webauthn.
This depends on lib.tokenclass
"""

import os
import struct
import unittest
from copy import copy

from sqlalchemy.testing.pickleable import User

from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.tokens.webauthn import (COSE_ALGORITHM, RegistrationRejectedException,
                                             WebAuthnMakeCredentialOptions, AuthenticationRejectedException,
                                             webauthn_b64_decode, webauthn_b64_encode,
                                             WebAuthnRegistrationResponse, ATTESTATION_REQUIREMENT_LEVEL,
                                             ATTESTATION_LEVEL, AuthenticatorDataFlags, WebAuthnAssertionResponse,
                                             WebAuthnUser)
from privacyidea.lib.utils import hexlify_and_unicode
from .base import MyTestCase
from privacyidea.lib.tokens.webauthntoken import (WebAuthnTokenClass, WEBAUTHNACTION, WEBAUTHNCONFIG,
                                                  DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
                                                  DEFAULT_USER_VERIFICATION_REQUIREMENT, WEBAUTHNINFO)
from privacyidea.lib.token import init_token
from privacyidea.lib.policy import set_policy, SCOPE

TRUST_ANCHOR_DIR = "{}/testdata/trusted_attestation_roots".format(os.path.abspath(os.path.dirname(__file__)))
REGISTRATION_RESPONSE_TMPL = {
    'clientData': b'eyJ0eXBlIjogIndlYmF1dGhuLmNyZWF0ZSIsICJjbGllbnRFeHRlbnNpb25zIjoge30sICJjaGFsbGVu'
                  b'Z2UiOiAiYlB6cFgzaEhRdHNwOWV2eUtZa2FadFZjOVVOMDdQVWRKMjJ2WlVkRHA5NCIsICJvcmlnaW4i'
                  b'OiAiaHR0cHM6Ly93ZWJhdXRobi5pbyJ9',
    'attObj': b'o2NmbXRoZmlkby11MmZnYXR0U3RtdKJjc2lnWEgwRgIhAI1qbvWibQos_t3zsTU05IXw1Ek3SDApATok'
              b'09uc4UBwAiEAv0fB_lgb5Ot3zJ691Vje6iQLAtLhJDiA8zDxaGjcE3hjeDVjgVkCUzCCAk8wggE3oAMC'
              b'AQICBDxoKU0wDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBSb290IENBIFNlcmlh'
              b'bCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBaMDExLzAtBgNVBAMMJll1'
              b'YmljbyBVMkYgRUUgU2VyaWFsIDIzOTI1NzM0ODExMTE3OTAxMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcD'
              b'QgAEvd9nk9t3lMNQMXHtLE1FStlzZnUaSLql2fm1ajoggXlrTt8rzXuSehSTEPvEaEdv_FeSqX22L6Ao'
              b'a8ajIAIOY6M7MDkwIgYJKwYBBAGCxAoCBBUxLjMuNi4xLjQuMS40MTQ4Mi4xLjUwEwYLKwYBBAGC5RwC'
              b'AQEEBAMCBSAwDQYJKoZIhvcNAQELBQADggEBAKrADVEJfuwVpIazebzEg0D4Z9OXLs5qZ_ukcONgxkRZ'
              b'8K04QtP_CB5x6olTlxsj-SXArQDCRzEYUgbws6kZKfuRt2a1P-EzUiqDWLjRILSr-3_o7yR7ZP_GpiFK'
              b'wdm-czb94POoGD-TS1IYdfXj94mAr5cKWx4EKjh210uovu_pLdLjc8xkQciUrXzZpPR9rT2k_q9HkZhH'
              b'U-NaCJzky-PTyDbq0KKnzqVhWtfkSBCGw3ezZkTS-5lrvOKbIa24lfeTgu7FST5OwTPCFn8HcfWZMXMS'
              b'D_KNU-iBqJdAwTLPPDRoLLvPTl29weCAIh-HUpmBQd0UltcPOrA_LFvAf61oYXV0aERhdGFYwnSm6pIT'
              b'yZwvdLIkkrMgz0AmKpTBqVCgOX8pJQtghB7wQQAAAAAAAAAAAAAAAAAAAAAAAAAAAECKU1ppjl9gmhHW'
              b'yDkgHsUvZmhr6oF3_lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r_oOaP8RS44dlQjrH-ALfYtpAECAyYh'
              b'WCAxnqAfESXOYjKUc2WACuXZ3ch0JHxV0VFrrTyjyjIHXCJYIFnx8H87L4bApR4M-hPcV-fHehEOeW-K'
              b'Cyd0H-WGY8s6'
}
ASSERTION_RESPONSE_TMPL = {
    'authData': b'dKbqkhPJnC90siSSsyDPQCYqlMGpUKA5fyklC2CEHvABAAACfQ',
    'clientData': b'eyJjaGFsbGVuZ2UiOiJlLWctblhhUnhNYWdFaXFUSlN5RDgyUnNFYzVpZl82anlmSkR5OGJOS2x3Iiwi'
                  b'b3JpZ2luIjoiaHR0cHM6Ly93ZWJhdXRobi5pbyIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ',
    'signature': b'MEUCIEp28FzVKneM3U3xVl4ABOXMHq02BBnQ9cOgFDvzfn8VAiEAkytcMIpWDP5PJEIUhDB1uQSz7aZO'
                 b'hdZGYqgRmMOGzd4='
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
ATTESTATION_FORM = 'direct'
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
APP_ID = "http://localhost:5000"
PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE = [
    COSE_ALGORITHM.ES256,
    COSE_ALGORITHM.PS256
]
ALLOWED_TRANSPORTS = "usb ble nfc"
CRED_ID = 'ilNaaY5fYJoR1sg5IB7FL2Zoa-qBd_5Q95ZcyxNkmjkoDhiLCLgEKoKfCUElLt6_6Dmj_EUuOHZUI6x_gC32LQ'
PUB_KEY = 'a401020326215820319ea01f1125ce6232947365800ae5d9ddc874247c55d1516bad3ca3ca32075c'\
          '22582059f1f07f3b2f86c0a51e0cfa13dc57e7c77a110e796f8a0b27741fe58663cb3a'


class WebAuthnTokenTestCase(MyTestCase):
    USER_LOGIN = "testuser"
    USER_REALM = "testrealm"
    USER_RESOLVER = "testresolver"

    def _create_challenge(self):
        self.token.set_otpkey(hexlify_and_unicode(webauthn_b64_decode(CRED_ID)))
        self.token.add_tokeninfo(WEBAUTHNINFO.PUB_KEY, PUB_KEY)
        self.token.add_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_ID, RP_ID)
        (_, _, _, response_details) = self.token.create_challenge(options=self.challenge_options)
        return response_details

    def setUp(self):
        self.token = init_token({
            'type': 'webauthn',
            'pin': '1234'
        })

        self.init_params = {
            WEBAUTHNACTION.RELYING_PARTY_ID: RP_ID,
            WEBAUTHNACTION.RELYING_PARTY_NAME: RP_NAME,
            WEBAUTHNACTION.TIMEOUT: TIMEOUT,
            WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM: DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
            WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT: DEFAULT_USER_VERIFICATION_REQUIREMENT,
            WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE: PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE
        }

        self.user = User(login=USER_NAME)

        self.challenge_options = {
            "user": self.user,
            WEBAUTHNACTION.ALLOWED_TRANSPORTS: ALLOWED_TRANSPORTS,
            WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT: DEFAULT_USER_VERIFICATION_REQUIREMENT,
            WEBAUTHNACTION.TIMEOUT: TIMEOUT
        }

    def test_00_users(self):
        self.setUp_user_realms()

        set_policy(name="WebAuthn",
                   scope=SCOPE.ENROLL,
                   action=WEBAUTHNACTION.RELYING_PARTY_NAME + "=" + RP_NAME + ","
                         +WEBAUTHNACTION.RELYING_PARTY_ID   + "=" + RP_ID)
        set_privacyidea_config(WEBAUTHNCONFIG.TRUST_ANCHOR_DIR, TRUST_ANCHOR_DIR)
        set_privacyidea_config(WEBAUTHNCONFIG.APP_ID, APP_ID)

    def test_01_create_token(self):
        self.assertEqual(self.token.type, "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_prefix(), "WAN")
        self.assertEqual(WebAuthnTokenClass.get_class_info().get('type'), "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_info('type'), "webauthn")
        self.assertTrue(self.token.token.serial.startswith("WAN"))
        with self.assertRaises(ValueError):
            self.token.get_init_detail()

    def test_02_token_init(self):
        web_authn_register_request = self\
            .token\
            .get_init_detail(self.init_params, self.user)\
            .get("webAuthnRegisterRequest")

        self.assertEqual(self.token.token.serial, web_authn_register_request.get("serialNumber"))
        self.assertIn('id', web_authn_register_request.get("relyingParty"))
        self.assertIn('name', web_authn_register_request.get("relyingParty"))
        self.assertEqual(RP_ID, web_authn_register_request.get("relyingParty").get('id'))
        self.assertEqual(RP_NAME, web_authn_register_request.get("relyingParty").get('name'))
        self.assertIn('alg', web_authn_register_request.get("preferredAlgorithm"))
        self.assertIn('type', web_authn_register_request.get("preferredAlgorithm"))
        self.assertEqual('public-key', web_authn_register_request.get("preferredAlgorithm").get("type"))
        self.assertEqual(COSE_ALGORITHM.ES256, web_authn_register_request.get("preferredAlgorithm").get("alg"))
        self.assertEqual(USER_NAME, web_authn_register_request.get("name"))

        self.assertEqual(RP_ID, self.token.get_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_ID))
        self.assertEqual(RP_NAME, self.token.get_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_NAME))

    def test_03_token_update(self):
        self.init_params['nonce'] = webauthn_b64_decode(REGISTRATION_CHALLENGE)
        self.token.get_init_detail(self.init_params, self.user)
        self.token.update({
            'type': 'webauthn',
            'serial': self.token.token.serial,
            'regdata': REGISTRATION_RESPONSE_TMPL['attObj'],
            'clientdata': REGISTRATION_RESPONSE_TMPL['clientData'],
            WEBAUTHNACTION.RELYING_PARTY_ID: RP_ID,
            WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL: ATTESTATION_LEVEL.NONE,
            'HTTP_ORIGIN': ORIGIN
        })
        web_authn_registration_response = self.token.get_init_detail().get("webAuthnRegisterResponse")

        self.assertTrue(web_authn_registration_response
                        .get("subject")
                        .startswith("Yubico U2F EE Serial"))
        self.assertTrue(self
                        .token
                        .get_tokeninfo(WEBAUTHNINFO.ATTESTATION_ISSUER)
                        .startswith("CN=Yubico U2F Root CA Serial"))
        self.assertTrue(self
                        .token
                        .get_tokeninfo(WEBAUTHNINFO.ATTESTATION_SUBJECT)
                        .startswith("CN=Yubico U2F EE Serial"))
        self.assertEqual(CRED_ID, self.token.decrypt_otpkey())
        self.assertEqual(PUB_KEY, self.token.get_tokeninfo(WEBAUTHNINFO.PUB_KEY))

    def test_04_authentication(self):
        web_authn_sign_request = self._create_challenge().get("webAuthnSignRequest")

        self.assertEqual(RP_ID, web_authn_sign_request.get('rpId'))
        self.assertEqual(1, len(web_authn_sign_request.get('allowCredentials') or []))
        self.assertEqual('public-key', web_authn_sign_request.get('allowCredentials')[0].get('type'))
        self.assertEqual(CRED_ID, web_authn_sign_request.get('allowCredentials')[0].get('id'))
        self.assertEqual(ALLOWED_TRANSPORTS, web_authn_sign_request.get('allowCredentials')[0].get('transports'))

    def test_05_authorization(self):
        self.challenge_options['nonce'] = webauthn_b64_decode(ASSERTION_CHALLENGE)
        self._create_challenge()
        sign_count = self.token.check_otp(otpval=None,
                                          options={
                                              "credentialid": CRED_ID,
                                              "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
                                              "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
                                              "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
                                              "user": self.user,
                                              "challenge": hexlify_and_unicode(self.challenge_options['nonce']),
                                              "HTTP_ORIGIN": ORIGIN,
                                          })
        self.assertTrue(sign_count > 0)


class WebAuthnTestCase(unittest.TestCase):
    @staticmethod
    def getWebAuthnCredential():
        return WebAuthnRegistrationResponse(
            rp_id=RP_ID,
            origin=ORIGIN,
            registration_response=copy(REGISTRATION_RESPONSE_TMPL),
            challenge=REGISTRATION_CHALLENGE,
            attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.NONE],
            trust_anchor_dir=TRUST_ANCHOR_DIR,
            uv_required=False,
            expected_registration_client_extensions=EXPECTED_REGISTRATION_CLIENT_EXTENSIONS,
        ).verify()

    @staticmethod
    def getAssertionResponse():
        credential = WebAuthnTestCase.getWebAuthnCredential()
        webauthn_user = WebAuthnUser(
            user_id=USER_ID,
            user_name=USER_NAME,
            user_display_name=USER_DISPLAY_NAME,
            icon_url=ICON_URL,
            credential_id=credential.credential_id.decode(),
            public_key=credential.public_key,
            sign_count=credential.sign_count,
            rp_id=credential.rp_id
        )

        webauthn_assertion_response = WebAuthnAssertionResponse(
            webauthn_user=webauthn_user,
            assertion_response=copy(ASSERTION_RESPONSE_TMPL),
            challenge=ASSERTION_CHALLENGE,
            origin=ORIGIN,
            uv_required=False,
        )

        return webauthn_assertion_response

    def setUp(self):
        self.options = WebAuthnMakeCredentialOptions(
            challenge=REGISTRATION_CHALLENGE,
            rp_name=RP_NAME,
            rp_id=RP_ID,
            user_id=USER_ID,
            user_name=USER_NAME,
            user_display_name=USER_DISPLAY_NAME,
            icon_url=ICON_URL,
            timeout=TIMEOUT,
            attestation=ATTESTATION_FORM,
            user_verification=USER_VERIFICATION,
            public_key_credential_algorithms=PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
            location=True
        )

    def test_00_create_options(self):
        registration_dict = self.options.registration_dict
        self.assertEqual(registration_dict['challenge'], REGISTRATION_CHALLENGE)
        self.assertTrue(CRED_KEY in registration_dict['pubKeyCredParams'])

    def test_01_validate_registration(self):
        web_authn_credential = self.getWebAuthnCredential()
        self.assertEqual(RP_ID, web_authn_credential.rp_id)
        self.assertEqual(ORIGIN, web_authn_credential.origin)

    def test_02_registration_invalid_user_verification(self):
        registration_response = WebAuthnRegistrationResponse(
            rp_id=RP_ID,
            origin=ORIGIN,
            registration_response=copy(REGISTRATION_RESPONSE_TMPL),
            challenge=REGISTRATION_CHALLENGE,
            attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.UNTRUSTED],
            trust_anchor_dir=TRUST_ANCHOR_DIR,
            uv_required=True,
            expected_registration_client_extensions=EXPECTED_REGISTRATION_CLIENT_EXTENSIONS
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
