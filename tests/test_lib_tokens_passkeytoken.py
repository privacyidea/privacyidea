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
from dataclasses import dataclass
from unittest.mock import patch

from webauthn import base64url_to_bytes
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import AttestationConveyancePreference

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.error import EnrollmentError, ParameterError, ResourceNotFoundError
from privacyidea.lib.policy import SCOPE, ACTION
from privacyidea.lib.token import (init_token, remove_token, unassign_token)
from privacyidea.lib.fido2.util import get_credential_ids_for_user, get_fido2_token_by_credential_id, hash_credential_id
from privacyidea.lib.fido2.challenge import create_fido2_challenge, verify_fido2_challenge
from privacyidea.lib.tokenclass import ROLLOUTSTATE, TokenClass
from privacyidea.lib.tokens.passkeytoken import PasskeyTokenClass
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction, PasskeyAction
from privacyidea.lib.user import User
from privacyidea.models import TokenCredentialIdHash
from tests.base import MyTestCase
from tests.passkey_base import PasskeyTestBase


class PasskeyTokenTestCase(PasskeyTestBase, MyTestCase):
    """
    The tests in this class are meant to be run consecutively, because they build on each other.
    """

    def setUp(self):
        PasskeyTestBase.setUp(self)
        self.setUp_user_realms()
        self.user = User(login="hans", realm=self.realm1, resolver=self.resolvername1)

    def _create_token(self) -> TokenClass:
        registration_request = self._initialize_registration()
        token = registration_request.token
        token.update(registration_request.registration_response)
        self.assertEqual(token.token.rollout_state, ROLLOUTSTATE.ENROLLED)
        return token

    @dataclass(frozen=True)
    class RegistrationRequest:
        token: TokenClass
        init_detail: dict
        registration_response: dict

    def _initialize_registration(self, get_init_detail_options: dict = None) -> RegistrationRequest:
        if get_init_detail_options is None:
            get_init_detail_options = {}
        token = init_token({"type": "passkey"}, user=self.user)
        self.assertIsInstance(token, PasskeyTokenClass)
        self.assertEqual(token.rollout_state, ROLLOUTSTATE.CLIENTWAIT)
        param = {}
        if get_init_detail_options:
            param.update(get_init_detail_options)
        # Overwrite these values if they have been in options
        param.update({
            FIDO2PolicyAction.RELYING_PARTY_ID: self.rp_id,
            FIDO2PolicyAction.RELYING_PARTY_NAME: self.rp_id
        })
        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = self.registration_challenge
            init_detail = token.get_init_detail(param)
        self.assertIn("serial", init_detail)
        self.assertIn("passkey_registration", init_detail)
        self.assertIn("transaction_id", init_detail)
        registration_response = {
            "attestationObject": self.registration_attestation,
            "clientDataJSON": self.registration_client_data,
            "credential_id": self.credential_id,
            "rawId": self.credential_id,
            "authenticatorAttachment": self.authenticator_attachment,
            "HTTP_ORIGIN": self.expected_origin,
            FIDO2PolicyAction.RELYING_PARTY_ID: self.rp_id,
            "transaction_id": init_detail["transaction_id"]
        }

        return self.RegistrationRequest(token, init_detail, registration_response)

    def _initialize_authentication(self) -> dict:
        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = self.authentication_challenge_no_uv
            challenge = create_fido2_challenge(self.rp_id)
            self.assertEqual(challenge["challenge"], self.authentication_challenge_no_uv)
            return challenge

    def test_01_class_values(self):
        class_prefix = PasskeyTokenClass.get_class_prefix()
        self.assertEqual(class_prefix, "PIPK")

        class_type = PasskeyTokenClass.get_class_type()
        self.assertEqual(class_type, "passkey")

        class_info = PasskeyTokenClass.get_class_info()
        self.assertEqual(class_info["type"], "passkey")
        self.assertIn("title", class_info)
        self.assertIn("description", class_info)
        self.assertIn("user", class_info)
        self.assertEqual(class_info["user"], ["enroll"])
        self.assertIn("ui_enroll", class_info)
        self.assertEqual(class_info["ui_enroll"], ["admin", "user"])

        self.assertIn("policy", class_info)
        policy = class_info["policy"]
        self.assertIn(SCOPE.AUTH, policy)
        policy_auth = policy[SCOPE.AUTH]
        self.assertIn(ACTION.CHALLENGETEXT, policy_auth)
        self.assertIn(SCOPE.ENROLL, policy)
        policy_enroll = policy[SCOPE.ENROLL]
        self.assertIn(PasskeyAction.AttestationConveyancePreference, policy_enroll)

    def test_02_init_defaults(self):
        """
        Test the basic enrollment with just the settings that are required to make it work. The token is persisted for
        the next test.
        """
        registration_request = self._initialize_registration()
        token = registration_request.token
        init_detail = registration_request.init_detail
        self.assertTrue(token.get_serial())
        self.first_serial = token.get_serial()

        self.validate_default_passkey_registration(init_detail["passkey_registration"])
        passkey_registration = init_detail["passkey_registration"]

        self.assertEqual(len(passkey_registration["pubKeyCredParams"]), 2)
        self.assertEqual(passkey_registration["pubKeyCredParams"][0]["type"], "public-key")
        self.assertEqual(passkey_registration["pubKeyCredParams"][1]["type"], "public-key")
        self.assertIn(passkey_registration["pubKeyCredParams"][0]["alg"], [-7, -257])
        self.assertIn(passkey_registration["pubKeyCredParams"][1]["alg"], [-7, -257])
        # ExcludeCredentials should be empty because no other passkey token is registered for the user
        self.assertEqual(len(passkey_registration["excludeCredentials"]), 0)

        # Complete the registration
        update_response = token.update(registration_request.registration_response)
        self.assertTrue(update_response)
        self.assertIn("details", update_response)
        self.assertEqual(update_response["details"]["serial"], self.first_serial)
        # Verify that the token is enrolled and token info was written
        self.assertEqual(token.rollout_state, ROLLOUTSTATE.ENROLLED)
        token_info = token.get_tokeninfo()
        self.assertTrue(token_info["credential_id_hash"])
        self.assertTrue(token_info["public_key"])
        self.assertTrue(token_info["aaguid"])
        self.assertTrue(token_info["sign_count"])
        self.assertTrue(token_info["fido2_user_id"])
        # Since attestation was passed, the cert should be present and the description should be set from the cert CN
        self.assertTrue(token_info["attestation_certificate"])
        self.assertEqual(token.token.description, "Yubico U2F EE Serial 2109467376")
        # The token key is the credential id
        self.assertEqual(token.token.get_otpkey().getKey().decode('utf-8'), self.credential_id)
        # Verify that the credential_id hash has been written to the database
        tcih = TokenCredentialIdHash.query.filter(
            TokenCredentialIdHash.credential_id_hash == token_info["credential_id_hash"]).one()
        self.assertEqual(tcih.token_id, token.token.id)
        # Kep the token for the next test

    def test_03_init_custom_settings(self):
        """
        Test enrollment with all custom settings. The settings that are not changeable are not checked again.
        This also just tests the registration options generated by the server, because in the previous test, the
        registration was done with attestation.
        This basically tests that the policies for enrollment are loaded by the prepolicy 'fido2_enroll', that they work
        and that excludeCredentials is set correctly.
        """
        # UserVerification is ignored by most browsers when residentKey is set to required
        # However, it can still be configured and is tested here
        # The Key Algorithm are all that are selectable in the policy via
        # privacyidea.lib.tokens.webauthntoken.PUBLIC_KEY_CREDENTIAL_ALGORITHMS
        key_algorithms = [COSEAlgorithmIdentifier.ECDSA_SHA_256,
                          COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
                          COSEAlgorithmIdentifier.RSASSA_PSS_SHA_256]
        # Because of how token are created currently (API level calls functions on the token object directly),
        # this has to be done here instead of on the lib level
        # There should be the credential_id of the token created in the previous test
        registered_credential_ids = get_credential_ids_for_user(self.user)
        self.assertEqual(len(registered_credential_ids), 1)

        options = {
            FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS: key_algorithms,
            PasskeyAction.AttestationConveyancePreference: AttestationConveyancePreference.ENTERPRISE,
            FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT: "required",
            "registered_credential_ids": registered_credential_ids
        }
        registration_request = self._initialize_registration(options)
        token = registration_request.token
        init_detail = registration_request.init_detail
        passkey_registration = init_detail["passkey_registration"]
        # Verify that the custom settings are set in the registration options
        self.assertIn("pubKeyCredParams", passkey_registration)
        self.assertEqual(len(passkey_registration["pubKeyCredParams"]), 3)
        for element in passkey_registration["pubKeyCredParams"]:
            self.assertEqual(element["type"], "public-key")
            self.assertIn(element["alg"], key_algorithms)
        self.assertEqual(passkey_registration["attestation"], "enterprise")
        self.assertEqual(passkey_registration["authenticatorSelection"]["userVerification"], "required")
        # excludeCredentials have the format [{'id': 'credential_id', 'type': 'public-key'}, {...}, ...]
        # The type is always 'public-key'
        self.assertEqual(passkey_registration["excludeCredentials"][0]["id"], registered_credential_ids[0])
        remove_token(serial=token.get_serial())
        # Remove the token from the previous test
        token = get_fido2_token_by_credential_id(registered_credential_ids[0])
        remove_token(serial=token.get_serial())
        # Verify that the hashed credential has been removed
        credential_id_hash = hash_credential_id(registered_credential_ids[0])
        tcih = TokenCredentialIdHash.query.filter(
            TokenCredentialIdHash.credential_id_hash == credential_id_hash).first()
        self.assertFalse(tcih)

    def test_04_init_fail_wrong_data(self):
        registration_request = self._initialize_registration()
        token = registration_request.token

        # Complete the registration with tampered data
        with self.assertRaises(EnrollmentError):
            registration_response = registration_request.registration_response
            registration_response["attestationObject"] = self.registration_attestation.replace("e", "f")
            token.update(registration_response)

        # Change the origin, should be reflected in the error message
        client_data = base64url_to_bytes(self.registration_client_data).decode('utf-8')
        client_data_json = json.loads(client_data)
        self.assertTrue(client_data_json["origin"])
        client_data_json["origin"] = "https://evil.nils:5000"
        tampered_client_data = bytes_to_base64url(json.dumps(client_data_json).encode('utf-8'))
        registration_response["clientDataJSON"] = tampered_client_data
        with self.assertRaises(EnrollmentError) as ex:
            token.update(registration_response)
        self.assertIn('Unexpected client data origin "https://evil.nils:5000",'
                      ' expected "https://cool.nils:5000"',
                      ex.exception.message)
        # Invalid client data (json format)
        with self.assertRaises(EnrollmentError) as ex:
            registration_response["clientDataJSON"] = self.registration_client_data.replace("a", "b")
            token.update(registration_response)
        self.assertIn("Invalid JSON structure", ex.exception.message)

    def test_05_init_exceptions(self):
        # Also test setting a description in the first step
        token: TokenClass = init_token({"type": "passkey", "description": "test"}, user=self.user)
        self.assertEqual(token.token.description, "test")
        param = {FIDO2PolicyAction.RELYING_PARTY_ID: self.rp_id,
                 FIDO2PolicyAction.RELYING_PARTY_NAME: self.rp_id}

        # Remove the user before the registration
        unassign_token(token.get_serial())
        with self.assertRaises(ParameterError) as ex:
            token.get_init_detail(param)
        self.assertIn("User must be provided", ex.exception.message)

        # Invalid enrollment state returns empty init detail
        token.token.rollout_state = ROLLOUTSTATE.PENDING
        init_detail = token.get_init_detail(param)
        self.assertFalse(init_detail)
        remove_token(serial=token.get_serial())

        # Registration challenge expired/deleted
        registration_request = self._initialize_registration()
        challenges = get_challenges(registration_request.token.get_serial())
        self.assertEqual(len(challenges), 1)
        challenges[0].delete()
        with self.assertRaises(EnrollmentError) as ex:
            registration_request.token.update(registration_request.registration_response)
        self.assertIn("The enrollment challenge does not exist", ex.exception.message)
        remove_token(serial=registration_request.token.get_serial())

    def test_06_authenticate_success(self):
        token = self._create_token()
        challenge = self._initialize_authentication()
        # UserVerification is preferred by default
        authentication_response = self.authentication_response_no_uv
        authentication_response["HTTP_ORIGIN"] = self.expected_origin
        success = verify_fido2_challenge(challenge["transaction_id"], token, authentication_response)
        self.assertEqual(success, 1)
        remove_token(serial=token.get_serial())

    def test_07_authenticate_fails(self):
        token = self._create_token()

        # Challenge does not exist
        with self.assertRaises(ResourceNotFoundError) as ex:
            verify_fido2_challenge("10039292755795086078", token, {})

        # Wrong signature
        challenge = self._initialize_authentication()
        authentication_response = self.authentication_response_no_uv
        authentication_response["HTTP_ORIGIN"] = self.expected_origin
        authentication_response["signature"] = authentication_response["signature"].replace("a", "b")
        success = verify_fido2_challenge(challenge["transaction_id"], token, authentication_response)
        self.assertEqual(success, -1)
        remove_token(serial=token.get_serial())

    def test_08_no_tokencredentialidhash_entry(self):
        _ = self._create_token()
        # Remove the tokencredentialidhash entry
        credential_id_hash = hash_credential_id(self.credential_id)
        tcih = TokenCredentialIdHash.query.filter(
            TokenCredentialIdHash.credential_id_hash == credential_id_hash).one()
        self.assertTrue(tcih)
        tcih.delete()
        # Try to get the token by credential id
        token = get_fido2_token_by_credential_id(self.credential_id)
        # Check that the credential id hash has been added again
        tcih = TokenCredentialIdHash.query.filter(
            TokenCredentialIdHash.credential_id_hash == credential_id_hash).one()
        self.assertTrue(tcih)

    def test_09_duplicate_tokencredentialidhash_entry(self):
        token1 = self._create_token()
        # Get the tokencredentialidhash entry
        credential_id_hash = hash_credential_id(self.credential_id)
        tcih = TokenCredentialIdHash.query.filter(
            TokenCredentialIdHash.credential_id_hash == credential_id_hash).one()
        self.assertTrue(tcih)
        self.assertEqual(tcih.token_id, token1.token.id)
        # Create a new token with the same credential id, which will overwrite the existing TCIH entry
        token2 = self._create_token()
        tcih = TokenCredentialIdHash.query.filter(
            TokenCredentialIdHash.credential_id_hash == credential_id_hash).one()
        self.assertTrue(tcih)
        self.assertEqual(tcih.token_id, token2.token.id)
