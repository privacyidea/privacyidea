# (c) NetKnights GmbH 2024,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Nils Behlen <nils.behlen@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import json
from unittest.mock import patch

from webauthn.helpers.structs import AttestationConveyancePreference

from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.tokens.passkeytoken import PasskeyAction
from privacyidea.lib.tokens.webauthn import COSE_ALGORITHM
from privacyidea.lib.tokens.webauthntoken import WEBAUTHNACTION
from privacyidea.lib.user import User
from tests.base import MyApiTestCase
from tests.passkeytestbase import PasskeyTestBase


class PasskeyAPITest(MyApiTestCase, PasskeyTestBase):
    """
    Passkey uses challenges that are not bound to a user.
    A successful authentication with a passkey should return the username.
    Passkeys can be used with cross-device sign-in, similar to how push token work
    """

    def setUp(self):
        PasskeyTestBase.setUp(self)
        self.setUp_user_realms()
        self.user = User(login="hans", realm=self.realm1,
                         resolver=self.resolvername1)
        PasskeyTestBase.__init__(self)

        set_policy("passkey_rp_id", scope=SCOPE.ENROLL, action=f"{WEBAUTHNACTION.RELYING_PARTY_ID}={self.rp_id}")
        set_policy("passkey_rp_name", scope=SCOPE.ENROLL,
                   action=f"{WEBAUTHNACTION.RELYING_PARTY_NAME}={self.rp_id}")
        self.pk_headers = {'ORIGIN': self.expected_origin, 'Authorization': self.at}

    def tearDown(self):
        delete_policy("passkey_rp_id")
        delete_policy("passkey_rp_name")

    def _token_init_step_one(self):
        with (self.app.test_request_context('/token/init',
                                            method='POST',
                                            data={"type": "passkey", "user": self.user.login, "realm": self.user.realm},
                                            headers=self.pk_headers),
              patch('privacyidea.lib.tokens.passkeytoken.PasskeyTokenClass._get_nonce') as get_nonce):
            get_nonce.return_value = self.registration_challenge
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertIn("detail", res.json)
            detail = res.json["detail"]
            self.assertIn("passkey_registration", detail)
            self.validate_default_passkey_registration(detail["passkey_registration"])
            passkey_registration = json.loads(detail["passkey_registration"])
            # PubKeyCredParams: Via the API, all three key algorithms (from webauthn) are valid by default
            self.assertEqual(len(passkey_registration["pubKeyCredParams"]), 3)
            for param in passkey_registration["pubKeyCredParams"]:
                self.assertIn(param["type"], ["public-key"])
                self.assertIn(param["alg"], [-7, -37, -257])
            # ExcludeCredentials should be empty because no other passkey token is registered for the user
            self.assertEquals(len(passkey_registration["excludeCredentials"]), 0)
            return res.json

    def _token_init_step_two(self, transaction_id):
        data = {
            "attestationObject": self.registration_attestation,
            "clientDataJSON": self.registration_client_data,
            "credential_id": self.registration_cred_id,
            "rawId": self.registration_cred_id,
            "authenticatorAttachment": self.authenticator_attachment,
            WEBAUTHNACTION.RELYING_PARTY_ID: self.rp_id,
            "transaction_id": transaction_id,
            "type": "passkey",
            "user": self.user.login,
            "realm": self.user.realm,
            "serial": self.serial1
        }
        with self.app.test_request_context('/token/init', method='POST', data=data, headers=self.pk_headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertIn("result", res.json)
            self.assertIn("status", res.json["result"])
            self.assertTrue(res.json["result"]["status"])
            self.assertIn("value", res.json["result"])
            self.assertTrue(res.json["result"]["value"])

    def test01_token_init_with_policies(self):
        # This test just checks if setting the policies alters the registration data correctly
        # Create a passkey token so excludeCredentials is not empty
        data = self._token_init_step_one()
        detail = data["detail"]
        self.serial1 = detail["serial"]
        transaction_id = detail["transaction_id"]
        self._token_init_step_two(transaction_id)
        set_policy("key_algorithm", scope=SCOPE.ENROLL,
                   action=f"{WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS}={COSE_ALGORITHM.ES256}")
        set_policy("attestation", scope=SCOPE.ENROLL, action=f"{PasskeyAction.AttestationConveyancePreference}="
                                                             f"{AttestationConveyancePreference.ENTERPRISE}")
        set_policy("user_verification", scope=SCOPE.ENROLL,
                   action=f"{WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT}='required'")

        with (self.app.test_request_context('/token/init',
                                            method='POST',
                                            data={"type": "passkey", "user": self.user.login, "realm": self.user.realm},
                                            headers=self.pk_headers),
              patch('privacyidea.lib.tokens.passkeytoken.PasskeyTokenClass._get_nonce') as get_nonce):
            get_nonce.return_value = self.registration_challenge
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            print(res.json)

        delete_policy("key_algorithm")
        delete_policy("attestation")
        delete_policy("user_verification")
