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
from mock import patch
from testfixtures import log_capture
from privacyidea.lib.user import User

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
from privacyidea.lib.token import init_token, check_user_pass, remove_token
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.error import PolicyError, ParameterError, EnrollmentError

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
ASSERTION_RESPONSE_SIGN_COUNT = 637
CRED_KEY = {
    'alg': -7,
    'type': 'public-key'
}
CREDENTIAL_ID = b'ilNaaY5fYJoR1sg5IB7FL2Zoa-qBd_5Q95ZcyxNkmjkoDhiLCLgEKoKfCUElLt6_6Dmj_EUuOHZUI6x_gC32LQ'
REGISTRATION_CHALLENGE = 'bPzpX3hHQtsp9evyKYkaZtVc9UN07PUdJ22vZUdDp94'
ASSERTION_CHALLENGE = 'e-g-nXaRxMagEiqTJSyD82RsEc5if_6jyfJDy8bNKlw'
RP_ID = "webauthn.io"
ORIGIN = "https://webauthn.io"
USER_NAME = 'hans'
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

URL_DECODE_TEST_STRING = 'MEQCIBxR_Zn2XNp8yp4gVaFWU7xdpdAjkBXpXPphKPrgc_4uAiBAB0oVN-8ryLRfo-koEF5NLn1J\r\n'\
                         'Cj8yyeCsp1U7mhR32A'
URL_DECODE_EXPECTED_RESULT = b'0D\x02 \x1cQ\xfd\x99\xf6\\\xda|\xca\x9e U\xa1VS\xbc]\xa5\xd0#\x90\x15\xe9\\\xfaa(\xfa'\
                             b'\xe0s\xfe.\x02 @\x07J\x157\xef+\xc8\xb4_\xa3\xe9(\x10^M.}I\n?2\xc9\xe0\xac\xa7U;\x9a'\
                             b'\x14w\xd8'
NONE_ATTESTATION_REGISTRATION_RESPONSE_TMPL = {
    'clientData': b'eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiZkszN3hLZGhXSmhVNmQyVEFH'
                  b'VllESEttZHNwb3JsanNSb1daMDlaaVRYTSIsIm9yaWdpbiI6Imh0dHBzOi8vd2ViYXV0aG4uaW8i'
                  b'LCJjcm9zc09yaWdpbiI6ZmFsc2V9',
    'attObj': b'o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjEdKbqkhPJnC90siSSsyDPQCYqlMGpUKA5fykl'
              b'C2CEHvBBAAAAtQAAAAAAAAAAAAAAAAAAAAAAQF8gbz2rT3N24r4ojF9kZKuVY_luj5OkbTYuq-79'
              b'HUoKy2Gj8cVotKsYQG6zAUGvh2DNRWCplAwAJI93pAqCExOlAQIDJiABIVgg0hC-jd-1sLwL4eqN'
              b'6u3sGX5D4f7OTrlXkel-HZIZSR8iWCD4DkCLED1CSAhHSZlVak4sdkU8_RFClaObyTJag7hEFg'
}
NONE_ATTESTATION_REGISTRATION_CHALLENGE = 'fK37xKdhWJhU6d2TAGVYDHKmdsporljsRoWZ09ZiTXM'
NONE_ATTESTATION_USER_NAME = 'john.doe'
NONE_ATTESTATION_USER_DISPLAY_NAME = '<john.doe.resolver1@foorealm>'
NONE_ATTESTATION_USER_ID = b'WAN000136AE'
NONE_ATTESTATION_ATTESTATION_FORM = 'none'
NONE_ATTESTATION_CRED_ID = 'XyBvPatPc3biviiMX2Rkq5Vj-W6Pk6RtNi6r7v0dSgrLYaPxxWi0qxhAbrMBQa-HYM1FYKmUDAAkj3ekCoITEw'
NONE_ATTESTATION_PUB_KEY = 'a5010203262001215820d210be8ddfb5b0bc0be1ea8deaedec197e43e1fece4eb95791e97e1d9219491f22582'\
                           '0f80e408b103d424808474999556a4e2c76453cfd114295a39bc9325a83b84416'

SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL = {
    "clientData": "eyJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjMwMDAiLCJjaGFsbGVuZ2Ui"
                  "OiJBWGtYV1hQUDNnTHg4T0xscGtKM2FSUmhGV250blNFTmdnbmpEcEJxbDFu"
                  "Z0tvbDd4V3dldlVZdnJwQkRQM0xFdmRyMkVPU3RPRnBHR3huTXZYay1WdyIs"
                  "InR5cGUiOiJ3ZWJhdXRobi5jcmVhdGUifQ",
    "attObj": "o2NmbXRmcGFja2VkZ2F0dFN0bXSiY2FsZzn__mNzaWdZAQCPypMLXWqtCZ1sc5Qd"
              "jhH-pAzm8-adpfbemd5zsym2krscwV0EeOdTrdUOdy3hWj5HuK9dIX_OpNro2jKr"
              "HfUj_0Kp-u87iqJ3MPzs-D9zXOqkbWqcY94Zh52wrPwhGfJ8BiQp5T4Q97E042hY"
              "QRDKmtv7N-BT6dywiuFHxfm1sDbUZ_yyEIN3jgttJzjp_wvk_RJmb78bLPTlym83"
              "Y0Ws73K6FFeiqFNqLA_8a4V0I088hs_IEPlj8PWxW0wnIUhI9IcRf0GEmUwTBpbN"
              "DGpIFGOudnl_C3YuXuzK3R6pv2r7m9-9cIIeeYXD9BhSMBQ0A8oxBbVF7j-0xXDN"
              "rXHZaGF1dGhEYXRhWQFnSZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NB"
              "AAAAOKjVmSRjt0nqud40p1PeHgEAIB-l9gZ544Ds7vzo_O76UZ8DCXiWFc8DN8LW"
              "NZYQH0NepAEDAzn__iBZAQDAIqzybPPmgeL5OR6JKq9bWDiENJlN_LePQEnf1_sg"
              "Om4FJ9kBTbOTtWplfoMXg40A7meMppiRqP72A3tmILwZ5xKIyY7V8Y2t8X1ilYJo"
              "l2nCKOpAEqGLTRJjF64GQxen0uFpi1tA6l6N-ZboPxjky4aidBdUP22YZuEPCO8-"
              "9ZTha8qwvTgZwMHhZ40TUPEJGGWOnHNlYmqnfFfk0P-UOZokI0rqtqqQGMwzV2Rr"
              "H2kjKTZGfyskAQnrqf9PoJkye4KUjWkWnZzhkZbrDoLyTEX2oWvTTflnR5tAVMQc"
              "h4UGgEHSZ00G5SFoc19nGx_UJcqezx5cLZsny-qQYDRjIUMBAAE"
}

SELF_ATTESTATION_REGISTRATION_RESPONSE_BAD_COSE_ALG = {
    'clientData': SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['clientData'],
    'attObj': SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['attObj'][:529]
              + 'y' + SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['attObj'][530:]
}

SELF_ATTESTATION_REGISTRATION_RESPONSE_ALG_MISMATCH = {
    'clientData': SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['clientData'],
    'attObj': SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['attObj'][:37]
              + '2' + SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['attObj'][38:]
}

SELF_ATTESTATION_REGISTRATION_RESPONSE_BROKEN_SIG = {
    'clientData': SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['clientData'],
    'attObj': SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['attObj'][:46]
              + 'AA' + SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL['attObj'][48:]
}


class WebAuthnTokenTestCase(MyTestCase):

    def _create_challenge(self):
        self.token.set_otpkey(hexlify_and_unicode(webauthn_b64_decode(CRED_ID)))
        self.token.add_tokeninfo(WEBAUTHNINFO.PUB_KEY, PUB_KEY)
        self.token.add_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_ID, RP_ID)
        (_, _, _, response_details) = self.token.create_challenge(options=self.challenge_options)
        return response_details

    def _setup_token(self):
        with patch('privacyidea.lib.tokens.webauthntoken.WebAuthnTokenClass._get_nonce') as mock_nonce:
            mock_nonce.return_value = webauthn_b64_decode(REGISTRATION_CHALLENGE)
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

    def setUp(self):
        self.setUp_user_realms()

        set_policy(name="WebAuthn",
                   scope=SCOPE.ENROLL,
                   action=WEBAUTHNACTION.RELYING_PARTY_NAME + "=" + RP_NAME + ","
                          + WEBAUTHNACTION.RELYING_PARTY_ID + "=" + RP_ID)
        set_privacyidea_config(WEBAUTHNCONFIG.TRUST_ANCHOR_DIR, TRUST_ANCHOR_DIR)
        set_privacyidea_config(WEBAUTHNCONFIG.APP_ID, APP_ID)

        self.user = User(login=USER_NAME, realm=self.realm1,
                         resolver=self.resolvername1)

        self.token = init_token({
            'type': 'webauthn',
            'pin': '1234'
        }, user=self.user)

        self.init_params = {
            WEBAUTHNACTION.RELYING_PARTY_ID: RP_ID,
            WEBAUTHNACTION.RELYING_PARTY_NAME: RP_NAME,
            WEBAUTHNACTION.TIMEOUT: TIMEOUT,
            WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM: DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
            WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT: DEFAULT_USER_VERIFICATION_REQUIREMENT,
            WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS: PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE
        }

        self.challenge_options = {
            "user": self.user,
            WEBAUTHNACTION.ALLOWED_TRANSPORTS: ALLOWED_TRANSPORTS,
            WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT: DEFAULT_USER_VERIFICATION_REQUIREMENT,
            WEBAUTHNACTION.TIMEOUT: TIMEOUT
        }

    def tearDown(self):
        self.token.delete_token()
        delete_policy("WebAuthn")

    def test_01_create_token(self):
        self.assertEqual(self.token.type, "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_prefix(), "WAN")
        self.assertEqual(WebAuthnTokenClass.get_class_info().get('type'), "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_info('type'), "webauthn")
        self.assertTrue(self.token.token.serial.startswith("WAN"))
        with self.assertRaises(ValueError):
            self.token.get_init_detail()
        with self.assertRaises(ParameterError):
            self.token.get_init_detail(self.init_params)

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
        self.assertIn('alg', web_authn_register_request.get("pubKeyCredAlgorithms")[0],
                      web_authn_register_request)
        self.assertIn('type', web_authn_register_request.get("pubKeyCredAlgorithms")[0],
                      web_authn_register_request)
        self.assertEqual('public-key',
                         web_authn_register_request.get("pubKeyCredAlgorithms")[0].get("type"),
                         web_authn_register_request)
        self.assertEqual(COSE_ALGORITHM.ES256,
                         web_authn_register_request.get("pubKeyCredAlgorithms")[0].get("alg"),
                         web_authn_register_request)
        self.assertEqual(USER_NAME, web_authn_register_request.get("name"))

        self.assertEqual(RP_ID, self.token.get_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_ID))
        self.assertEqual(RP_NAME, self.token.get_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_NAME))

    def test_03_token_update(self):
        self._setup_token()
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

    def test_03b_double_registration(self):
        self.assertEqual(self.token.type, "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_prefix(), "WAN")
        self.assertEqual(WebAuthnTokenClass.get_class_info().get('type'), "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_info('type'), "webauthn")
        self.assertTrue(self.token.token.serial.startswith("WAN"))

        # we need to create an additional token for this to take effect
        temp_token = init_token({
            'type': 'webauthn',
            'pin': '1234'
        }, user=self.user)

        # No avoid double registration
        init_params = self.init_params
        web_authn_register_request = temp_token \
            .get_init_detail(init_params, self.user) \
            .get("webAuthnRegisterRequest")
        self.assertEqual(temp_token.token.serial, web_authn_register_request.get("serialNumber"))
        self.assertNotIn("excludeCredentials", web_authn_register_request)

        self._setup_token()

        # Set avoid double registration
        init_params[WEBAUTHNACTION.AVOID_DOUBLE_REGISTRATION] = True
        web_authn_register_request = temp_token \
            .get_init_detail(init_params, self.user) \
            .get("webAuthnRegisterRequest")
        self.assertEqual(temp_token.token.serial, web_authn_register_request.get("serialNumber"))
        # Now the excludeCredentials is contained
        self.assertIn("excludeCredentials", web_authn_register_request)
        temp_token.delete_token()

    def test_04_authentication(self):
        reply_dict = self._create_challenge()
        attributes = reply_dict.get("attributes")
        web_authn_sign_request = attributes.get("webAuthnSignRequest")

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

    @log_capture()
    def test_06_missing_origin(self, capture):
        self._create_challenge()
        sign_count = self.token.check_otp(
            otpval=None,
            options={
                "credentialid": CRED_ID,
                "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
                "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
                "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
                "user": self.user,
                "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE)),
                "HTTP_ORIGIN": '',
            })
        self.assertTrue(sign_count == -1)
        capture.check_present(
            ('privacyidea.lib.tokens.webauthntoken',
             'WARNING',
             'Checking response for token {0!s} failed. HTTP Origin header '
             'missing.'.format(self.token.get_serial()))
        )

    def test_07_none_attestation(self):
        with patch('privacyidea.lib.tokens.webauthntoken.WebAuthnTokenClass._get_nonce') as mock_nonce:
            mock_nonce.return_value = webauthn_b64_decode(NONE_ATTESTATION_REGISTRATION_CHALLENGE)
            self.init_params[WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM] = 'none'
            self.user = User(login=NONE_ATTESTATION_USER_NAME)
            self.token.get_init_detail(self.init_params, self.user)
        self.token.update({
            'type': 'webauthn',
            'serial': self.token.token.serial,
            'regdata': NONE_ATTESTATION_REGISTRATION_RESPONSE_TMPL['attObj'],
            'clientdata': NONE_ATTESTATION_REGISTRATION_RESPONSE_TMPL['clientData'],
            WEBAUTHNACTION.RELYING_PARTY_ID: RP_ID,
            WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL: ATTESTATION_LEVEL.NONE,
            'HTTP_ORIGIN': ORIGIN
        })
        web_authn_registration_response = self.token.get_init_detail().get('webAuthnRegisterResponse')

        self.assertEqual(NONE_ATTESTATION_CRED_ID, self.token.decrypt_otpkey())
        self.assertEqual(NONE_ATTESTATION_PUB_KEY, self.token.get_tokeninfo(WEBAUTHNINFO.PUB_KEY))

    def test_08_missing_attestation(self):
        self.init_params['nonce'] = webauthn_b64_decode(NONE_ATTESTATION_REGISTRATION_CHALLENGE)
        self.user = User(login=NONE_ATTESTATION_USER_NAME)
        self.token.get_init_detail(self.init_params, self.user)

        with self.assertRaises(EnrollmentError):
            self.token.update({
                'type': 'webauthn',
                'serial': self.token.token.serial,
                'regdata': NONE_ATTESTATION_REGISTRATION_RESPONSE_TMPL['attObj'],
                'clientdata': NONE_ATTESTATION_REGISTRATION_RESPONSE_TMPL['clientData'],
                WEBAUTHNACTION.RELYING_PARTY_ID: RP_ID,
                WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL: ATTESTATION_LEVEL.UNTRUSTED,
                'HTTP_ORIGIN': ORIGIN
            })

    def test_09a_attestation_subject_allowed(self):
        self._setup_token()
        options = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "user": self.user,
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE)),
            "HTTP_ORIGIN": ORIGIN,
            WEBAUTHNACTION.REQ: ['subject/.*Yubico.*/']
        }
        res = self.token.check_otp(otpval=None, options=options)
        self.assertGreaterEqual(res, 0)

    def test_09b_attestation_subject_not_allowed(self):
        self._setup_token()
        options = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "user": self.user,
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE)),
            "HTTP_ORIGIN": ORIGIN,
            WEBAUTHNACTION.REQ: ['subject/.*Feitian.*/']
        }
        self.assertRaisesRegex(
            PolicyError,
            r"The WebAuthn token is not allowed to authenticate due to a policy "
            r"restriction.",
            self.token.check_otp,
            **{'otpval': None,
               'options': options})

    def test_10a_aaguid_allowed(self):
        self._setup_token()
        # check token with a valid aaguid
        res = self.token.check_otp(otpval=None, options={
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "user": self.user,
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE)),
            "HTTP_ORIGIN": ORIGIN,
            WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST: ['00000000000000000000000000000000']
        })
        self.assertGreaterEqual(res, 0)

    def test_10b_aaguid_not_allowed(self):
        self._setup_token()
        # check token with an invalid aaguid
        self.assertRaisesRegex(
            PolicyError,
            r"The WebAuthn token is not allowed to authenticate due to a "
            r"policy restriction.",
            self.token.check_otp,
            **{'otpval': None,
               'options': {
                   "credentialid": CRED_ID,
                   "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
                   "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
                   "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
                   "user": self.user,
                   "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE)),
                   "HTTP_ORIGIN": ORIGIN,
                   WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST: ['ffff0000000000000000000000000000']
               }})


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
            location=True,
            credential_ids=[CRED_ID]
        )

    def test_00_create_options(self):
        registration_dict = self.options.registration_dict
        self.assertEqual(registration_dict['challenge'], REGISTRATION_CHALLENGE)
        self.assertTrue(CRED_KEY in registration_dict['pubKeyCredParams'])

    def test_01_validate_registration(self):
        webauthn_credential = self.getWebAuthnCredential()
        self.assertEqual(RP_ID, webauthn_credential.rp_id, webauthn_credential)
        self.assertEqual(ORIGIN, webauthn_credential.origin, webauthn_credential)
        self.assertTrue(webauthn_credential.has_signed_attestation, webauthn_credential)
        self.assertTrue(webauthn_credential.has_trusted_attestation, webauthn_credential)
        self.assertEqual(str(webauthn_credential),
                         '{0!r} ({1!s}, {2!s}, {3!s})'.format(CREDENTIAL_ID,
                                                              RP_ID, ORIGIN, 0),
                         webauthn_credential)

    def test_01b_validate_untrusted_registration(self):
        webauthn_credential = WebAuthnRegistrationResponse(
            rp_id=RP_ID,
            origin=ORIGIN,
            registration_response=copy(REGISTRATION_RESPONSE_TMPL),
            challenge=REGISTRATION_CHALLENGE,
            attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.NONE],
            uv_required=False,
            expected_registration_client_extensions=EXPECTED_REGISTRATION_CLIENT_EXTENSIONS,
        ).verify()
        self.assertEqual(RP_ID, webauthn_credential.rp_id, webauthn_credential)
        self.assertEqual(ORIGIN, webauthn_credential.origin, webauthn_credential)
        self.assertTrue(webauthn_credential.has_signed_attestation, webauthn_credential)
        self.assertFalse(webauthn_credential.has_trusted_attestation, webauthn_credential)

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

        with self.assertRaisesRegex(RegistrationRejectedException,
                                    'Malformed request received.'):
            registration_response.verify()

    def test_03_validate_assertion(self):
        webauthn_assertion_response = self.getAssertionResponse()
        webauthn_user = webauthn_assertion_response.webauthn_user
        self.assertEqual(str(webauthn_user),
                         '{0!r} ({1!s}, {2!s}, {3!s})'.format(USER_ID, USER_NAME,
                                                              USER_DISPLAY_NAME, 0),
                         webauthn_user)
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

        # FIXME: This *should* fail because UP=0, but will fail anyway later on because the
        #  signature is invalid.
        # TODO: Build a mock Authenticator implementation, to be able to sign arbitrary
        #  authenticator data statements.
        # TODO: Sign an authenticator data statement with UP=0 and test against that so that the
        #  signature is valid.
        with self.assertRaises(AuthenticationRejectedException):
            webauthn_assertion_response.verify()

    def test_06_duplicate_authentication_fail_assertion(self):
        webauthn_assertion_response = self.getAssertionResponse()
        webauthn_assertion_response.webauthn_user.sign_count = ASSERTION_RESPONSE_SIGN_COUNT

        with self.assertRaisesRegex(AuthenticationRejectedException,
                                    'Duplicate authentication detected.'):
            webauthn_assertion_response.verify()
        # TODO: we should add a test for a missing sign_count (or 0) but we need
        #  to change the auth data for that.

    def test_07_webauthn_b64_decode(self):
        self.assertEqual(webauthn_b64_decode(URL_DECODE_TEST_STRING), URL_DECODE_EXPECTED_RESULT)

    def test_08_registration_invalid_requirement_level(self):
        with self.assertRaisesRegex(ValueError,
                                    'Illegal attestation_requirement_level.'):
            WebAuthnRegistrationResponse(
                rp_id=RP_ID,
                origin=ORIGIN,
                registration_response=copy(REGISTRATION_RESPONSE_TMPL),
                challenge=REGISTRATION_CHALLENGE,
                attestation_requirement_level={'unknown level': False},
                trust_anchor_dir=TRUST_ANCHOR_DIR,
                uv_required=True,
                expected_registration_client_extensions=EXPECTED_REGISTRATION_CLIENT_EXTENSIONS
            )

    def test_09_registration_self_Attestation(self):
        webauthn_credential = WebAuthnRegistrationResponse(
            rp_id='localhost',
            origin='http://localhost:3000',
            registration_response=copy(SELF_ATTESTATION_REGISTRATION_RESPONSE_TMPL),
            challenge='AXkXWXPP3gLx8OLlpkJ3aRRhFWntnSENggnjDpBql1ngKol7xWwevUYvrpBDP3LEvdr2EOStOFpGGxnMvXk-Vw',
            attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.UNTRUSTED],
            trust_anchor_dir=TRUST_ANCHOR_DIR,
            expected_registration_client_extensions=EXPECTED_REGISTRATION_CLIENT_EXTENSIONS
        ).verify()
        self.assertEqual('localhost', webauthn_credential.rp_id, webauthn_credential)
        self.assertEqual('http://localhost:3000', webauthn_credential.origin, webauthn_credential)
        self.assertTrue(webauthn_credential.has_signed_attestation, webauthn_credential)
        self.assertFalse(webauthn_credential.has_trusted_attestation, webauthn_credential)

    def test_09b_registration_self_Attestation_bad_cose_alg(self):
        self.assertRaises(
            RegistrationRejectedException,
            WebAuthnRegistrationResponse(
                rp_id='localhost',
                origin='http://localhost:3000',
                registration_response=copy(SELF_ATTESTATION_REGISTRATION_RESPONSE_BAD_COSE_ALG),
                challenge='AXkXWXPP3gLx8OLlpkJ3aRRhFWntnSENggnjDpBql1ngKol7xWwevUYvrpBDP3LEvdr2EOStOFpGGxnMvXk-Vw',
                attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.UNTRUSTED],
                trust_anchor_dir=TRUST_ANCHOR_DIR,
                expected_registration_client_extensions=EXPECTED_REGISTRATION_CLIENT_EXTENSIONS
            ).verify)

    def test_09c_registration_self_Attestation_alg_mismatch(self):
        self.assertRaisesRegex(
            RegistrationRejectedException,
            'does not match algorithm from attestation statement',
            WebAuthnRegistrationResponse(
                rp_id='localhost',
                origin='http://localhost:3000',
                registration_response=copy(SELF_ATTESTATION_REGISTRATION_RESPONSE_ALG_MISMATCH),
                challenge='AXkXWXPP3gLx8OLlpkJ3aRRhFWntnSENggnjDpBql1ngKol7xWwevUYvrpBDP3LEvdr2EOStOFpGGxnMvXk-Vw',
                attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.UNTRUSTED],
                trust_anchor_dir=TRUST_ANCHOR_DIR,
                expected_registration_client_extensions=EXPECTED_REGISTRATION_CLIENT_EXTENSIONS
            ).verify)

    def test_09d_registration_self_Attestation_broken_signature(self):
        self.assertRaisesRegex(
            RegistrationRejectedException,
            'Invalid signature received.',
            WebAuthnRegistrationResponse(
                rp_id='localhost',
                origin='http://localhost:3000',
                registration_response=copy(SELF_ATTESTATION_REGISTRATION_RESPONSE_BROKEN_SIG),
                challenge='AXkXWXPP3gLx8OLlpkJ3aRRhFWntnSENggnjDpBql1ngKol7xWwevUYvrpBDP3LEvdr2EOStOFpGGxnMvXk-Vw',
                attestation_requirement_level=ATTESTATION_REQUIREMENT_LEVEL[ATTESTATION_LEVEL.UNTRUSTED],
                trust_anchor_dir=TRUST_ANCHOR_DIR,
                expected_registration_client_extensions=EXPECTED_REGISTRATION_CLIENT_EXTENSIONS
            ).verify)


class MultipleWebAuthnTokenTestCase(MyTestCase):
    rp_name = 'pitest'
    rp_id = 'pitest.local'
    app_id = 'https://pitest.local:5000'
    client_data1 = ('eyJjaGFsbGVuZ2UiOiJlTENMaUpsaEpPdHZhdURuR05ERHdRWUZieFZBbE'
                    'JOTGZjcXQ3NEZ6cGVZ\r\nIiwiY2xpZW50RXh0ZW5zaW9ucyI6e30sImhh'
                    'c2hBbGdvcml0aG0iOiJTSEEtMjU2Iiwib3JpZ2lu\r\nIjoiaHR0cHM6Ly'
                    '9waXRlc3QubG9jYWw6NTAwMCIsInR5cGUiOiJ3ZWJhdXRobi5jcmVhdGUifQ')
    reg_data1 = ('o2NmbXRoZmlkby11MmZnYXR0U3RtdKJjc2lnWEgwRgIhAOV477bXb_0txmSFn'
                 'n-Sgnhlrdl_edxK\r\naDVKZZ-jy89HAiEAivdhbia91Y8UsFprkvuymfRJr2'
                 'FhKk3btE1T2uG_PXhjeDVjgVkCwDCCArww\r\nggGkoAMCAQICBAOt8BIwDQY'
                 'JKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBSb290\r\nIENB'
                 'IFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwM'
                 'DAwMDBaMG0x\r\nCzAJBgNVBAYTAlNFMRIwEAYDVQQKDAlZdWJpY28gQUIxIj'
                 'AgBgNVBAsMGUF1dGhlbnRpY2F0b3Ig\r\nQXR0ZXN0YXRpb24xJjAkBgNVBAM'
                 'MHVl1YmljbyBVMkYgRUUgU2VyaWFsIDYxNzMwODM0MFkwEwYH\r\nKoZIzj0C'
                 'AQYIKoZIzj0DAQcDQgAEGZ6HnBYtt9w57kpCoEYWpbMJ_soJL3a-CUj5bW6Vy'
                 'uTMZc1U\r\noFnPvcfJsxsrHWwYRHnCwGH0GKqVS1lqLBz6F6NsMGowIgYJKw'
                 'YBBAGCxAoCBBUxLjMuNi4xLjQu\r\nMS40MTQ4Mi4xLjcwEwYLKwYBBAGC5Rw'
                 'CAQEEBAMCBDAwIQYLKwYBBAGC5RwBAQQEEgQQ-iuZ3J45\r\nQlePkkow0jxB'
                 'GDAMBgNVHRMBAf8EAjAAMA0GCSqGSIb3DQEBCwUAA4IBAQAo67Nn_tHY8OKJ6'
                 '8qf\r\n9tgHV8YOmuV8sXKMmxw4yru9hNkjfagxrCGUnw8t_Awxa_2xdbNuY6'
                 'Iru1gOrcpSgNB5hA5aHiVy\r\nYlo7-4dgM9v7IqlpyTi4nOFxNZQAoSUtlwK'
                 'pEpPVRRnpYN0izoon6wXrfnm3UMAC_tkBa3Eeya10\r\nUBvZFMu-jtlXEoG3'
                 'T0TrB3zmHssGq4WpclUmfujjmCv0PwyyGjgtI1655M5tspjEBUJQQCMrK2Hh'
                 '\r\nDNcMYhW8A7fpQHG3DhLRxH-WZVou-Z1M5Vp_G0sf-RTuE22eYSBHFIhkaYi'
                 'ARDEWZTiJuGSG2cnJ\r\n_7yThUU1abNFdEuMoLQ3aGF1dGhEYXRhWMQWJeYw'
                 'kTqKuQrIIynVbIb5ZwDrxRtUsbT69Ja-Yeiy\r\n9kEAAAAAAAAAAAAAAAAAA'
                 'AAAAAAAAABA8Fiap8SFbm99-iwuVdn2BbJ-gWJkWlQhasMDTOeLRoGX\r\nzp'
                 'c8k-cldR2neh4enFZe_eMftsJMhxdxl4Py_4idEaUBAgMmIAEhWCDXbuIEoFe'
                 'XpAnfvegi4KkY\r\nNc0FjraVVgZrTtBaVnoZLyJYIDTYuM6O11SMTZuSWWBO'
                 'FBW3B3UrxBj-HjPola1okria')
    serial1 = 'WAN0000704B'
    nonce1 = 'eLCLiJlhJOtvauDnGNDDwQYFbxVAlBNLfcqt74FzpeY'

    client_data2 = ('eyJjaGFsbGVuZ2UiOiJGbnlMMEZ6VlZFQ3U5d01IajJQTVhzRVBYa0xwQy'
                    '0tNkFRY0duNHdZX3hn\r\nIiwiY2xpZW50RXh0ZW5zaW9ucyI6e30sImhh'
                    'c2hBbGdvcml0aG0iOiJTSEEtMjU2Iiwib3JpZ2lu\r\nIjoiaHR0cHM6Ly'
                    '9waXRlc3QubG9jYWw6NTAwMCIsInR5cGUiOiJ3ZWJhdXRobi5jcmVhdGUifQ')
    reg_data2 = ('o2NmbXRoZmlkby11MmZnYXR0U3RtdKJjc2lnWEcwRQIhANTcUgL-wcH6b61n6'
                 '_eolC37Dw9G7_h6\r\nznFfsG37lObtAiBSEx5hny-NPyycq7vfkHV3Jzj3f_'
                 'Vn5bh6haYizInC8mN4NWOBWQJTMIICTzCC\r\nATegAwIBAgIEEjbRfzANBgk'
                 'qhkiG9w0BAQsFADAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3Qg\r\nQ0Eg'
                 'U2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwM'
                 'DAwMFowMTEv\r\nMC0GA1UEAwwmWXViaWNvIFUyRiBFRSBTZXJpYWwgMjM5Mj'
                 'U3MzQxMDMyNDEwODcwWTATBgcqhkjO\r\nPQIBBggqhkjOPQMBBwNCAATTZak'
                 'eXpng1bQ5wNmvu4f0BY5H3RKxRO2xTSsz-NNcFRPkDXnw-Zmr\r\n4jZxlZOB'
                 'ydwrB4WLgqxjR2IEzPc01q4hozswOTAiBgkrBgEEAYLECgIEFTEuMy42LjEuN'
                 'C4xLjQx\r\nNDgyLjEuNTATBgsrBgEEAYLlHAIBAQQEAwIFIDANBgkqhkiG9w'
                 '0BAQsFAAOCAQEAIhubs7JyJPE-\r\nvqMi8DUer0ZJZqNvcmmFfI4j-eUFtVJ'
                 '13U5BIj5_JhEJFGnPkp-lJj5sx3aBskhtqvQfsc-r6FUI\r\n8T9nUPbIGyne'
                 'YBtecgi7-mR25WSpHX1kq1JK0E67Ws4hixUm8XH4fN71I5joQyxQub8VeBl6t'
                 'uu-\r\nMqvRdpM4OJwkuMl6zuPxvGFkdsr0LxNn3yko0CZVxjudPNCrabaZb-'
                 'VzeIuZUvgCq0-UEVWxCdwe\r\nIOxtJUIXWFfuq-GbR4pfJheGDTGdPkWmD8Q'
                 'GmDVpBWHczmQmiHUG10WXn4Bn2zFIgAtoMFje34jx\r\n1fXrvNjWMqRlN9jo'
                 'oxvQY4Rrf2hhdXRoRGF0YVjEFiXmMJE6irkKyCMp1WyG-WcA68UbVLG0-vSW'
                 '\r\nvmHosvZBAAAAAAAAAAAAAAAAAAAAAAAAAAAAQNEGCFfy7qPnR-evAu5q4'
                 '1SvPKP0w5KmRqQLbjEX\r\nA0jyIzTiwYnY39CYWaMmpPmWyOsFNyKgkpjFI4'
                 '8qsworRHWlAQIDJiABIVggz5UnPRI1wM8RErq3\r\nzvQeEMdPkH0t5OLrWb-'
                 '3j7pFZ3ciWCBOKhWKM_s8Ayf65080LBPp3nfarOadhoZbbSqUN2LjFg')
    serial2 = 'WAN0001831A'
    nonce2 = 'FnyL0FzVVECu9wMHj2PMXsEPXkLpC--6AQcGn4wY_xg'

    init_params = {
            WEBAUTHNACTION.RELYING_PARTY_ID: rp_id,
            WEBAUTHNACTION.RELYING_PARTY_NAME: rp_name,
            WEBAUTHNACTION.TIMEOUT: TIMEOUT,
            WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM: DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
            WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT: DEFAULT_USER_VERIFICATION_REQUIREMENT,
            WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS: PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE
        }
    auth_options = {
        WEBAUTHNACTION.ALLOWED_TRANSPORTS: ALLOWED_TRANSPORTS,
        WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT: DEFAULT_USER_VERIFICATION_REQUIREMENT,
        WEBAUTHNACTION.TIMEOUT: TIMEOUT}

    def setUp(self):
        self.setUp_user_realms()
        set_policy(name="WebAuthn", scope=SCOPE.ENROLL,
                   action='{0!s}={1!s},{2!s}={3!s}'.format(WEBAUTHNACTION.RELYING_PARTY_NAME,
                                                           self.rp_name,
                                                           WEBAUTHNACTION.RELYING_PARTY_ID,
                                                           self.rp_id))
        set_privacyidea_config(WEBAUTHNCONFIG.APP_ID, self.app_id)
        self.user = User(login='hans', realm=self.realm1,
                         resolver=self.resolvername1)
        # TODO: extract token enrollment into a local function
        # init token step 1
        self.token1 = init_token({'type': 'webauthn',
                                  'serial': self.serial1},
                                 user=self.user)
        # TODO: use mocking to set nonce
        with patch('privacyidea.lib.tokens.webauthntoken.WebAuthnTokenClass._get_nonce') as mock_nonce:
            mock_nonce.return_value = webauthn_b64_decode(self.nonce1)
            res = self.token1.get_init_detail(self.init_params, self.user)
        self.assertEqual(self.serial1, res['serial'], res)
        self.assertEqual(self.nonce1, res['webAuthnRegisterRequest']['nonce'], res)

        # init token step 2
        self.token1.update({
            'type': 'webauthn',
            'serial': self.serial1,
            'regdata': self.reg_data1,
            'clientdata': self.client_data1,
            WEBAUTHNACTION.RELYING_PARTY_ID: self.rp_id,
            WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL: ATTESTATION_LEVEL.NONE,
            'HTTP_ORIGIN': self.app_id
        })
        res = self.token1.get_init_detail()
        self.assertEqual('Yubico U2F EE Serial 61730834',
                         res['webAuthnRegisterResponse']['subject'], res)
        # enroll the second webauthn token
        # init token step 1
        self.token2 = init_token({'type': 'webauthn',
                                  'serial': self.serial2},
                                 user=self.user)
        with patch('privacyidea.lib.tokens.webauthntoken.WebAuthnTokenClass._get_nonce') as mock_nonce:
            mock_nonce.return_value = webauthn_b64_decode(self.nonce2)
            res = self.token2.get_init_detail(self.init_params, self.user)
        self.assertEqual(self.serial2, res['serial'], res)
        self.assertEqual(self.nonce2, res['webAuthnRegisterRequest']['nonce'], res)

        # init token step 2
        self.token2.update({
            'type': 'webauthn',
            'serial': self.serial2,
            'regdata': self.reg_data2,
            'clientdata': self.client_data2,
            WEBAUTHNACTION.RELYING_PARTY_ID: self.rp_id,
            WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL: ATTESTATION_LEVEL.NONE,
            'HTTP_ORIGIN': self.app_id
        })
        res = self.token2.get_init_detail()
        self.assertEqual('Yubico U2F EE Serial 23925734103241087',
                         res['webAuthnRegisterResponse']['subject'], res)

    def tearDown(self):
        remove_token(serial=self.serial1)
        remove_token(serial=self.serial2)

    # TODO: also test challenge-response with different tokens (webauthn + totp)
    def test_01_mulitple_webauthntoken_auth(self):
        set_policy("otppin", scope=SCOPE.AUTH, action="{0!s}=none".format(ACTION.OTPPIN))
        res, reply = check_user_pass(self.user, '', options=self.auth_options)
        self.assertFalse(res)
        self.assertIn('transaction_id', reply, reply)
        tid = reply['transaction_id']
        self.assertIn('multi_challenge', reply, reply)
        self.assertEqual(len(reply['multi_challenge']), 2, reply['multi_challenge'])
        self.assertIn('messages', reply, reply)
        self.assertEqual(len(reply['messages']), 2, reply['messages'])
        # check that the serials of the challenges are different
        chal1 = reply['multi_challenge'][0]
        chal2 = reply['multi_challenge'][1]
        self.assertNotEqual(chal1['serial'], chal2['serial'],
                            reply['multi_challenge'])
        self.assertEqual(chal1['transaction_id'], chal2['transaction_id'],
                         reply['multi_challenge'])
        # Now make sure that the requests contain the same challenge
        self.assertEqual(chal1['attributes']['webAuthnSignRequest']['challenge'],
                         chal2['attributes']['webAuthnSignRequest']['challenge'],
                         reply['multi_challenge'])
        # check that we have two challenges in the db with the same challenge
        chals = get_challenges(transaction_id=tid)
        self.assertEqual(len(chals), 2, chals)
        self.assertEqual(chals[0].challenge, chals[1].challenge, chals)

        delete_policy('otppin')
