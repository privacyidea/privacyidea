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
from unittest.mock import patch

from webauthn.helpers.structs import AttestationConveyancePreference

import privacyidea.lib.token
from privacyidea.config import TestingConfig, Config
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction, PasskeyAction
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.token import remove_token, init_token, get_tokens
from privacyidea.lib.tokens.webauthn import COSE_ALGORITHM
from privacyidea.lib.user import User
from tests.base import MyApiTestCase, OverrideConfigTestCase
from tests.passkey_base import PasskeyTestBase


class PasskeyAPITestBase(MyApiTestCase, PasskeyTestBase):

    def setUp(self):
        PasskeyTestBase.setUp(self)
        self.setUp_user_realms()
        self.user = User(login="hans", realm=self.realm1,
                         resolver=self.resolvername1)
        PasskeyTestBase.__init__(self)

        set_policy("passkey_rp_id", scope=SCOPE.ENROLL, action=f"{FIDO2PolicyAction.RELYING_PARTY_ID}={self.rp_id}")
        set_policy("passkey_rp_name", scope=SCOPE.ENROLL,
                   action=f"{FIDO2PolicyAction.RELYING_PARTY_NAME}={self.rp_id}")
        self.pk_headers = {'ORIGIN': self.expected_origin, 'Authorization': self.at}
        # Delete all token
        tokens = get_tokens(user=self.user)
        for t in tokens:
            remove_token(t.get_serial())

    def tearDown(self):
        delete_policy("passkey_rp_id")
        delete_policy("passkey_rp_name")

    def _token_init_step_one(self):
        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = self.registration_challenge

            with self.app.test_request_context('/token/init',
                                               method='POST',
                                               data={"type": "passkey", "user": self.user.login,
                                                     "realm": self.user.realm},
                                               headers=self.pk_headers):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                self.assertIn("detail", res.json)
                detail = res.json["detail"]
                self.assertIn("passkey_registration", detail)
                self.validate_default_passkey_registration(detail["passkey_registration"])
                self.assertIn("rollout_state", detail)
                self.assertEqual("clientwait", detail["rollout_state"])
                passkey_registration = detail["passkey_registration"]
                # PubKeyCredParams: Via the API, all three key algorithms (from webauthn) are valid by default
                self.assertEqual(len(passkey_registration["pubKeyCredParams"]), 3)
                for param in passkey_registration["pubKeyCredParams"]:
                    self.assertIn(param["type"], ["public-key"])
                    self.assertIn(param["alg"], [-7, -37, -257])
                # ExcludeCredentials should be empty because no other passkey token is registered for the user
                self.assertEqual(0, len(passkey_registration["excludeCredentials"]),
                                 "excludeCredentials should be empty")
                return res.json

    def _token_init_step_two(self, transaction_id, serial):
        data = {
            "attestationObject": self.registration_attestation,
            "clientDataJSON": self.registration_client_data,
            "credential_id": self.credential_id,
            "rawId": self.credential_id,
            "authenticatorAttachment": self.authenticator_attachment,
            FIDO2PolicyAction.RELYING_PARTY_ID: self.rp_id,
            "transaction_id": transaction_id,
            "type": "passkey",
            "user": self.user.login,
            "realm": self.user.realm,
            "serial": serial
        }
        with self.app.test_request_context('/token/init', method='POST', data=data, headers=self.pk_headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self._assert_result_value_true(res.json)

    def _enroll_static_passkey(self) -> str:
        """
        Returns the serial of the enrolled passkey token
        """
        data = self._token_init_step_one()
        detail = data["detail"]
        serial = detail["serial"]
        transaction_id = detail["transaction_id"]
        self._token_init_step_two(transaction_id, serial)
        return serial

    def _trigger_passkey_challenge(self, mock_nonce: str) -> dict:
        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = mock_nonce
            with self.app.test_request_context('/validate/initialize', method='POST', data={"type": "passkey"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                self.assertIn("detail", res.json)
                detail = res.json["detail"]
                self.assertIn("passkey", detail)
                passkey = detail["passkey"]
                self.assertIn("challenge", passkey)
                self.assertEqual(mock_nonce, passkey["challenge"])
                self.assertIn("message", passkey)
                self.assertIn("transaction_id", passkey)
                self.assertIn("rpId", passkey)
                self.assertEqual(self.rp_id, passkey["rpId"])
            return passkey

    def _assert_result_value_true(self, response_json):
        self.assertIn("result", response_json)
        self.assertIn("status", response_json["result"])
        self.assertTrue(response_json["result"]["status"])
        self.assertIn("value", response_json["result"])
        self.assertTrue(response_json["result"]["value"])

    def _verify_auth_fail_with_error(self, res, error_code: int):
        self.assertEqual(401, res.status_code)
        self.assertIn("result", res.json)
        self.assertIn("status", res.json["result"])
        self.assertFalse(res.json["result"]["status"])
        self.assertIn("error", res.json["result"])
        error = res.json["result"]["error"]
        self.assertIn("message", error)
        self.assertTrue(error["message"])
        self.assertIn("code", error)
        self.assertEqual(error_code, error["code"])


class PasskeyAPITest(PasskeyAPITestBase):
    """
    Passkey uses challenges that are not bound to a user.
    A successful authentication with a passkey should return the username.
    Passkeys can be used with cross-device sign-in, similar to how push token work
    """

    def test01_token_init_with_policies(self):
        # Test if setting the policies alters the registration data correctly
        # Create a passkey token so excludeCredentials is not empty
        serial = self._enroll_static_passkey()

        set_policy("key_algorithm", scope=SCOPE.ENROLL,
                   action=f"{FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS}=ecdsa")
        set_policy("attestation", scope=SCOPE.ENROLL, action=f"{PasskeyAction.AttestationConveyancePreference}="
                                                             f"{AttestationConveyancePreference.ENTERPRISE.value}")
        set_policy("user_verification", scope=SCOPE.ENROLL,
                   action=f"{FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT}=required")

        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = self.registration_challenge

            with self.app.test_request_context('/token/init',
                                               method='POST',
                                               data={"type": "passkey", "user": self.user.login,
                                                     "realm": self.user.realm},
                                               headers=self.pk_headers):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                data = res.json
                self.assertIn("detail", data)
                self.assertIn("serial", data["detail"])
                serial_2 = data["detail"]["serial"]
                self.assertIn("passkey_registration", data["detail"])
                passkey_registration = data["detail"]["passkey_registration"]
                # PubKeyCredParams: Only ecdsa should be allowed
                self.assertEqual(len(passkey_registration["pubKeyCredParams"]), 1)
                self.assertEqual(passkey_registration["pubKeyCredParams"][0]["alg"], COSE_ALGORITHM.ES256)
                # Attestation should be enterprise
                self.assertEqual(passkey_registration["attestation"], AttestationConveyancePreference.ENTERPRISE)
                # ExcludeCredentials should contain the credential id of the registered token
                self.assertEqual(len(passkey_registration["excludeCredentials"]), 1)
                self.assertEqual(passkey_registration["excludeCredentials"][0]["id"], self.credential_id)

        delete_policy("key_algorithm")
        delete_policy("attestation")
        delete_policy("user_verification")
        remove_token(serial)
        remove_token(serial_2)

    def test_02_authenticate_no_uv(self):
        serial = self._enroll_static_passkey()
        passkey_challenge = self._trigger_passkey_challenge(self.authentication_challenge_no_uv)
        self.assertIn("user_verification", passkey_challenge)
        # By default, user_verification is preferred
        self.assertEqual("preferred", passkey_challenge["user_verification"])

        transaction_id = passkey_challenge["transaction_id"]
        # Answer the challenge
        data = self.authentication_response_no_uv
        data["transaction_id"] = transaction_id
        with self.app.test_request_context('/validate/check', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self._assert_result_value_true(res.json)
            self.assertNotIn("auth_items", res.json)
        remove_token(serial)

    def test_03_authenticate_wrong_uv(self):
        """
        Wrong UV meaning user verification is required but the authenticator data does not contain the UV flag
        """
        serial = self._enroll_static_passkey()
        set_policy("user_verification", scope=SCOPE.AUTH,
                   action=f"{FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT}=required")
        passkey_challenge = self._trigger_passkey_challenge(self.authentication_challenge_no_uv)
        self.assertIn("user_verification", passkey_challenge)
        self.assertEqual("required", passkey_challenge["user_verification"])
        transaction_id = passkey_challenge["transaction_id"]

        data = self.authentication_response_no_uv
        data["transaction_id"] = transaction_id
        with self.app.test_request_context('/validate/check', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertIn("result", res.json)
            self.assertIn("status", res.json["result"])
            self.assertTrue(res.json["result"]["status"])
            # Value is false and authentication is REJECT
            self.assertIn("value", res.json["result"])
            self.assertFalse(res.json["result"]["value"])
            self.assertIn("authentication", res.json["result"])
            self.assertEqual("REJECT", res.json["result"]["authentication"])

        remove_token(serial)
        delete_policy("user_verification")

    def test_04_authenticate_with_uv(self):
        serial = self._enroll_static_passkey()
        set_policy("user_verification", scope=SCOPE.AUTH,
                   action=f"{FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT}=required")
        passkey_challenge = self._trigger_passkey_challenge(self.authentication_challenge_uv)
        self.assertIn("user_verification", passkey_challenge)
        self.assertEqual("required", passkey_challenge["user_verification"])
        transaction_id = passkey_challenge["transaction_id"]

        data = self.authentication_response_uv
        data["transaction_id"] = transaction_id
        with self.app.test_request_context('/validate/check', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self._assert_result_value_true(res.json)

        remove_token(serial)
        delete_policy("user_verification")

    def test_05_trigger_with_pin(self):
        """
        By default, passkeys are not triggered using the PIN, because the flow of authentication is very different
        from our other token types. However, it is possible to enable this behavior with the
        policy passkey_trigger_with_pin.
        """
        # Without the policy, the passkey should not be triggered with the PIN
        serial = self._enroll_static_passkey()
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": self.user.login, "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertEqual("REJECT", res.json["result"]["authentication"])
            self.assertFalse(res.json["result"]["value"])


        # Now set the policy to trigger the passkey with the PIN
        set_policy("passkey_trigger_with_pin", scope=SCOPE.AUTH, action=f"{PasskeyAction.EnableTriggerByPIN}=true")
        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = self.authentication_challenge_no_uv
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": self.user.login, "pass": ""}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                self.assertIn("detail", res.json)
                detail = res.json["detail"]
                self.assertIn("multi_challenge", detail)

                multi_challenge = detail["multi_challenge"]
                self.assertEqual(len(multi_challenge), 1)

                challenge = multi_challenge[0]
                self.assertIn("transaction_id", challenge)
                transaction_id = challenge["transaction_id"]
                self.assertTrue(transaction_id)

                self.assertIn("challenge", challenge)
                self.assertEqual(self.authentication_challenge_no_uv, challenge["challenge"])

                self.assertIn("serial", challenge)
                self.assertEqual(serial, challenge["serial"])

                self.assertIn("type", challenge)
                self.assertEqual("passkey", challenge["type"])

                self.assertIn("userVerification", challenge)
                self.assertTrue(challenge["userVerification"])

                self.assertIn("rpId", challenge)
                self.assertEqual(self.rp_id, challenge["rpId"])

                self.assertIn("message", challenge)
                self.assertTrue(challenge["message"])

                self.assertIn("client_mode", challenge)
                self.assertEqual("webauthn", challenge["client_mode"])

        # Answer the challenge
        data = self.authentication_response_no_uv
        data["transaction_id"] = transaction_id
        with self.app.test_request_context('/validate/check', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self._assert_result_value_true(res.json)
            self.assertIn("result", res.json)
            self.assertIn("authentication", res.json["result"])
            self.assertEqual("ACCEPT", res.json["result"]["authentication"])
            # Should return the username
            self.assertIn("detail", res.json)
            detail = res.json["detail"]
            self.assertIn("username", detail)
            self.assertEqual(self.user.login, detail["username"])
            self.assertNotIn("auth_items", res.json)
        remove_token(serial)
        delete_policy("passkey_trigger_with_pin")

    def test_06_validate_check_wrong_serial(self):
        """
        Challenges triggered via /validate/check should be bound to a specific serial.
        Trying to answer the challenge with a token with a different serial should fail.
        """
        set_policy("passkey_trigger_with_pin", scope=SCOPE.AUTH, action=f"{PasskeyAction.EnableTriggerByPIN}=true")
        serial = self._enroll_static_passkey()
        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = self.authentication_challenge_no_uv
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": self.user.login, "pass": ""}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                detail = res.json["detail"]
                transaction_id = detail["multi_challenge"][0]["transaction_id"]
        # Change the token serial
        token = privacyidea.lib.token.get_tokens(serial=serial)[0]
        token.token.serial = "123456"
        token.token.save()
        # Try to answer the challenge, will fail
        data = self.authentication_response_no_uv
        data["transaction_id"] = transaction_id
        with self.app.test_request_context('/validate/check', method='POST', data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code)
            result = res.json["result"]
            self.assertIn("error", result)
            error = result["error"]
            self.assertIn("message", error)
            self.assertIn("code", error)
            self.assertEqual(403, error["code"])
            self.assertFalse(result["status"])
        remove_token(token.token.serial)
        delete_policy("passkey_trigger_with_pin")

    def test_07_trigger_challenge(self):
        """
        Just test if the challenge is returned by /validate/triggerchallenge. The response would be sent to
        /validate/check and that is already tested. Requires the passkey_trigger_with_pin policy to be set.
        """
        set_policy("passkey_trigger_with_pin", scope=SCOPE.AUTH, action=f"{PasskeyAction.EnableTriggerByPIN}=true")
        serial = self._enroll_static_passkey()
        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = self.authentication_challenge_no_uv
            with self.app.test_request_context('/validate/triggerchallenge', method='POST',
                                               data={"user": self.user.login}, headers=self.pk_headers):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code)
                self.assertIn("detail", res.json)
                detail = res.json["detail"]
                self.assertIn("multi_challenge", detail)

                multi_challenge = detail["multi_challenge"]
                self.assertEqual(len(multi_challenge), 1)

                challenge = multi_challenge[0]
                self.assertIn("transaction_id", challenge)
                transaction_id = challenge["transaction_id"]
                self.assertTrue(transaction_id)

                self.assertIn("challenge", challenge)
                self.assertEqual(self.authentication_challenge_no_uv, challenge["challenge"])

                self.assertIn("serial", challenge)
                self.assertEqual(serial, challenge["serial"])

                self.assertIn("type", challenge)
                self.assertEqual("passkey", challenge["type"])

                self.assertIn("userVerification", challenge)
                self.assertTrue(challenge["userVerification"])

                self.assertIn("rpId", challenge)
                self.assertEqual(self.rp_id, challenge["rpId"])

                self.assertIn("message", challenge)
                self.assertTrue(challenge["message"])

                self.assertIn("client_mode", challenge)
                self.assertEqual("webauthn", challenge["client_mode"])
        remove_token(serial)

    def test_08_offline(self):
        serial = self._enroll_static_passkey()
        data = {"serial": serial, "machineid": 0, "application": "offline", "resolver": ""}
        with self.app.test_request_context('/machine/token', method='POST', data=data, headers=self.pk_headers):
            res = self.app.full_dispatch_request()
            self.assertIn("result", res.json)
            self.assertIn("status", res.json["result"])
            self.assertTrue(res.json["result"]["status"])
            self.assertIn("value", res.json["result"])
            self.assertEqual(1, res.json["result"]["value"])

        # A successful authentication should return the offline data now
        challenge = self._trigger_passkey_challenge(self.authentication_challenge_no_uv)
        transaction_id = challenge["transaction_id"]
        data = self.authentication_response_no_uv
        data["transaction_id"] = transaction_id
        # A user agent that identifies the machine is required.
        user_agent = "privacyidea-cp/1.1.1 Windows/Laptop-1231312"
        headers = {"Origin": self.expected_origin, "User-Agent": user_agent}
        # IP is needed to get the offline data
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           environ_base={'REMOTE_ADDR': '10.0.0.17'},
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self._assert_result_value_true(res.json)
            self.assertIn("detail", res.json)
            self.assertIn("auth_items", res.json)
            auth_items = res.json["auth_items"]
            self.assertIn("offline", auth_items)
            # Offline items for 1 token should be returned
            offline = auth_items["offline"]
            self.assertEqual(1, len(offline))
            offline = offline[0]
            # At least for this test user=username
            self.assertIn("user", offline)
            self.assertEqual(self.user.login, offline["user"])
            self.assertIn("refilltoken", offline)
            self.assertTrue(offline["refilltoken"])
            refill_token = offline["refilltoken"]
            self.assertIn("username", offline)
            self.assertEqual(self.user.login, offline["username"])
            self.assertIn("response", offline)
            response = offline["response"]
            self.assertIn("rpId", response)
            self.assertEqual(self.rp_id, response["rpId"])
            self.assertIn("pubKey", response)
            self.assertIn("credentialId", response)
            # Verify that the returned values are correct
            token = privacyidea.lib.token.get_tokens(serial=serial)[0]
            public_key = token.get_tokeninfo("public_key")
            self.assertEqual(public_key, response["pubKey"])
            credential_id = token.token.get_otpkey().getKey().decode("utf-8")
            self.assertEqual(credential_id, response["credentialId"])

        # Refill without machine name will fail with parameter error 905
        data = {"serial": serial, "refilltoken": refill_token, "pass": ""}
        with self.app.test_request_context('/validate/offlinerefill', method='POST', data=data):
            res = self.app.full_dispatch_request()
            self.assertIn("result", res.json)
            result = res.json["result"]
            self.assertIn("status", result)
            self.assertFalse(result["status"])
            self.assertIn("error", result)
            self.assertIn("message", result["error"])
            self.assertTrue(result["error"]["message"])
            self.assertIn("code", result["error"])
            self.assertEqual(905, result["error"]["code"])

        # Refill with machine name works
        data = {"serial": serial, "refilltoken": refill_token, "pass": ""}
        with self.app.test_request_context('/validate/offlinerefill', method='POST', data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self._assert_result_value_true(res.json)
            # For FIDO2 offline, the refill just checks if the token is still marked as offline and returns
            # a new refill token
            self.assertIn("auth_items", res.json)
            auth_items = res.json["auth_items"]
            self.assertIn("offline", auth_items)
            offline = auth_items["offline"]
            self.assertEqual(1, len(offline))
            offline = offline[0]
            self.assertIn("refilltoken", offline)
            self.assertTrue(offline["refilltoken"])
            self.assertNotEqual(refill_token, offline["refilltoken"])
            refill_token = offline["refilltoken"]
            self.assertIn("serial", offline)
            self.assertEqual(serial, offline["serial"])
            self.assertIn("response", offline)
            self.assertFalse(offline["response"])

        # Disable offline for the token
        with self.app.test_request_context(f'/machine/token/{serial}/offline/1',
                                           method='DELETE',
                                           headers=self.pk_headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertIn("result", res.json)
            self.assertIn("status", res.json["result"])
            self.assertTrue(res.json["result"]["status"])
            self.assertIn("value", res.json["result"])
            self.assertEqual(1, res.json["result"]["value"])

        # Try to refill again, should indicate that the token is no longer valid for offline use.
        data.update({"refilltoken": refill_token})
        with self.app.test_request_context('/validate/offlinerefill', method='POST', data=data,
                                           headers=self.pk_headers):
            res = self.app.full_dispatch_request()
            self.assertIn("result", res.json)
            result = res.json["result"]
            self.assertIn("status", result)
            self.assertFalse(result["status"])
            self.assertIn("error", result)
            error = result["error"]
            self.assertIn("message", error)
            self.assertTrue(error["message"])
            self.assertIn("code", error)
            self.assertEqual(905, error["code"])
        remove_token(serial)

    def test_09_enroll_via_multichallenge(self):
        spass_token = init_token({"type": "spass", "pin": "1"}, self.user)
        action = "enroll_via_multichallenge=PASSKEY, enroll_via_multichallenge_text=enrollVia multichallenge test text"
        set_policy("enroll_passkey", scope=SCOPE.AUTH, action=action)

        # Using the spass token should result in a challenge to enroll a passkey
        with patch('privacyidea.lib.fido2.challenge.get_fido2_nonce') as get_nonce:
            get_nonce.return_value = self.registration_challenge
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": self.user.login, "pass": "1"}):
                res = self.app.full_dispatch_request()
                # Authentication is not successful, instead, it is a challenge
                self.assertIn("result", res.json)
                result = res.json["result"]
                self.assertIn("status", result)
                self.assertTrue(result["status"])
                self.assertIn("value", result)
                self.assertFalse(result["value"], res.json)
                self.assertIn("authentication", result)
                self.assertEqual("CHALLENGE", result["authentication"])
                # Detail
                self.assertIn("detail", res.json)
                detail = res.json["detail"]
                self.assertIn("multi_challenge", detail)
                self.assertIn("client_mode", detail)
                self.assertEqual("webauthn", detail["client_mode"])
                self.assertIn("message", detail)
                self.assertTrue(detail["message"])
                self.assertIn("serial", detail)
                passkey_serial = detail["serial"]
                self.assertTrue(passkey_serial)
                self.assertIn("type", detail)
                self.assertEqual("passkey", detail["type"])
                # Multi challenge
                multi_challenge = detail["multi_challenge"]
                self.assertEqual(1, len(multi_challenge))
                challenge = multi_challenge[0]
                self.assertIn("transaction_id", challenge)
                transaction_id = challenge["transaction_id"]
                self.assertTrue(transaction_id)
                self.assertIn("serial", challenge)
                self.assertTrue(challenge["serial"])
                # Passkey registration
                self.assertIn("passkey_registration", challenge)
                passkey_registration = challenge["passkey_registration"]
                self.assertIn("rp", passkey_registration)
                rp = passkey_registration["rp"]
                self.assertIn("name", rp)
                self.assertEqual(self.rp_id, rp["name"])
                self.assertIn("id", rp)
                self.assertEqual(self.rp_id, rp["id"])
                self.assertIn("user", passkey_registration)
                user = passkey_registration["user"]
                self.assertIn("id", user)
                self.assertIn("name", user)
                self.assertEqual(self.user.login, user["name"])
                self.assertIn("displayName", user)
                self.assertEqual(self.user.login, user["displayName"])
                self.assertIn("challenge", passkey_registration)
                self.assertEqual(self.registration_challenge, passkey_registration["challenge"])
                self.assertIn("pubKeyCredParams", passkey_registration)
                self.assertEqual(3, len(passkey_registration["pubKeyCredParams"]))
                for param in passkey_registration["pubKeyCredParams"]:
                    self.assertIn("type", param)
                    self.assertEqual("public-key", param["type"])
                    self.assertIn("alg", param)
                    self.assertIn(param["alg"], [-7, -37, -257])
                self.assertIn("timeout", passkey_registration)
                self.assertIn("excludeCredentials", passkey_registration)
                self.assertEqual(0, len(passkey_registration["excludeCredentials"]))
                self.assertIn("authenticatorSelection", passkey_registration)
                authenticator_selection = passkey_registration["authenticatorSelection"]
                self.assertIn("residentKey", authenticator_selection)
                self.assertEqual("required", authenticator_selection["residentKey"])
                self.assertIn("requireResidentKey", authenticator_selection)
                self.assertTrue(authenticator_selection["requireResidentKey"])
                self.assertIn("userVerification", authenticator_selection)
                self.assertEqual("preferred", authenticator_selection["userVerification"])
                self.assertIn("attestation", passkey_registration)
                self.assertEqual("none", passkey_registration["attestation"])

        # Answer the challenge
        data = {
            "attestationObject": self.registration_attestation,
            "clientDataJSON": self.registration_client_data,
            "credential_id": self.credential_id,
            "rawId": self.credential_id,
            "authenticatorAttachment": self.authenticator_attachment,
            FIDO2PolicyAction.RELYING_PARTY_ID: self.rp_id,
            "transaction_id": transaction_id,
            "type": "passkey",
            "user": self.user.login,
            "realm": self.user.realm,
            "serial": passkey_serial
        }
        with self.app.test_request_context('/validate/check', method='POST', data=data, headers=self.pk_headers):
            res = self.app.full_dispatch_request()
            self._assert_result_value_true(res.json)
            self.assertIn("detail", res.json)
            detail = res.json["detail"]
            self.assertIn("message", detail)
            self.assertTrue(detail["message"])
            self.assertIn("username", detail)
            self.assertEqual(self.user.login, detail["username"])
            self.assertIn("serial", detail)
            self.assertEqual(passkey_serial, detail["serial"])
            self.assertEqual("ACCEPT", res.json["result"]["authentication"])

        remove_token(spass_token.get_serial())
        remove_token(passkey_serial)
        delete_policy("enroll_passkey")

    def test_10_auth_success(self):
        """
        To use a passkey with /auth, the challenge is initiated via /validate/initialize and
        then answered via /validate/check.
        UserVerification is always required for /auth.
        """
        serial = self._enroll_static_passkey()
        passkey_challenge = self._trigger_passkey_challenge(self.authentication_challenge_uv)
        data = self.authentication_response_uv
        transaction_id = passkey_challenge["transaction_id"]
        data["transaction_id"] = transaction_id
        with self.app.test_request_context('/auth', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertIn("result", res.json)
            self.assertIn("status", res.json["result"])
            self.assertTrue(res.json["result"]["status"])
            self.assertIn("value", res.json["result"])
            # Value contains the user data (rights etc.)
            value = res.json["result"]["value"]
            self.assertIn("realm", value)
            self.assertEqual(self.user.realm, value["realm"])
            self.assertIn("log_level", value)
            self.assertIn("menus", value)
            self.assertIn("rights", value)
            self.assertTrue(len(value["rights"]) > 0)
            self.assertIn("role", value)
            self.assertEqual("user", value["role"])
            self.assertIn("token", value)
            self.assertTrue(value["token"])
        remove_token(serial)

    def test_11_auth_fail_uv(self):
        """
        Test an authentication with a wrong response and without user verification.
        """
        set_policy("user_verification", scope=SCOPE.AUTH,
                   action=f"{FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT}=required")
        serial = self._enroll_static_passkey()
        passkey_challenge = self._trigger_passkey_challenge(self.authentication_challenge_no_uv)
        data = self.authentication_response_no_uv
        transaction_id = passkey_challenge["transaction_id"]
        data["transaction_id"] = transaction_id
        with self.app.test_request_context('/auth', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self._verify_auth_fail_with_error(res, 4031)
        delete_policy("user_verification")
        remove_token(serial)

    def test_12_auth_fail_signature(self):
        serial = self._enroll_static_passkey()
        passkey_challenge = self._trigger_passkey_challenge(self.authentication_challenge_uv)
        data = self.authentication_response_uv
        transaction_id = passkey_challenge["transaction_id"]
        data["transaction_id"] = transaction_id
        # Change the signature
        data["signature"] = "wrong_signature"
        with self.app.test_request_context('/auth', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self._verify_auth_fail_with_error(res, 4031)
        remove_token(serial)

    def test_13_uv_in_challenge_data(self):
        """
        The user_verification requirement is set in the challenge data. When a challenge is triggered, the value of the
        policy at that moment is stored in the challenge data and used for the authentication.
        If the policy value was changed in the meantime, the authentication will still work because the value from the
        challenge data is used and not read from the policy.
        """
        # Trigger a challenge with no uv requirement, then change it to required and answer the challenge
        # That should still work
        serial = self._enroll_static_passkey()
        passkey_challenge = self._trigger_passkey_challenge(self.authentication_challenge_uv)
        data = self.authentication_response_uv
        transaction_id = passkey_challenge["transaction_id"]
        data["transaction_id"] = transaction_id
        set_policy("user_verification", scope=SCOPE.AUTH,
                   action=f"{FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT}=required")
        with self.app.test_request_context('/auth', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self._assert_result_value_true(res.json)
        remove_token(serial)
        delete_policy("user_verification")


class PasskeyAuthAPITest(PasskeyAPITestBase, OverrideConfigTestCase):
    """
    Test if the feature switch for passkey usage with /auth works.
    Successful use has been tested before in PasskeyAPITest.
    """

    class Config(TestingConfig):
        WEBUI_PASSKEY_LOGIN_ENABLED = False

    def test_01_webui_passkey_disabled(self):
        self.assertFalse(get_app_config_value("WEBUI_PASSKEY_LOGIN_ENABLED", True))
        serial = self._enroll_static_passkey()
        passkey_challenge = self._trigger_passkey_challenge(self.authentication_challenge_uv)
        data = self.authentication_response_uv
        transaction_id = passkey_challenge["transaction_id"]
        data["transaction_id"] = transaction_id
        with self.app.test_request_context('/auth', method='POST',
                                           data=data,
                                           headers={"Origin": self.expected_origin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
            self._verify_auth_fail_with_error(res, 4307)
        remove_token(serial)
