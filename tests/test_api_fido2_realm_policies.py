# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Realm-scoped FIDO2 policies: enrollment reads every enrollment policy with the enrolling user, and conflicting
realm-scoped policies affect only FIDO2 and passkey, not every authentication request.
"""
from privacyidea.api.lib.prepolicy import fido2_auth, fido2_enroll
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, delete_policy, set_policy
from privacyidea.lib.token import get_tokens, init_token, remove_token
from privacyidea.lib.tokens.webauthntoken import (DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
                                                  DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL,
                                                  DEFAULT_USER_VERIFICATION_REQUIREMENT, WebAuthnTokenClass)
from privacyidea.lib.user import User
from .base import MyApiTestCase

WEBAUTHN_TEXT_ACTION = f"{WebAuthnTokenClass.get_class_type()}_{PolicyAction.CHALLENGETEXT}"


class RequestMock:
    pass


class Fido2EnrollUserPolicyTestCase(MyApiTestCase):
    """
    WebAuthn and passkey enrollment read every enrollment policy with the enrolling user, so a policy restricted to
    another realm does not change the user verification, the attestation form and level or the challenge texts.
    """

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy("fido2_rp", scope=SCOPE.ENROLL,
                   action=f"{FIDO2PolicyAction.RELYING_PARTY_ID}=example.com,"
                          f"{FIDO2PolicyAction.RELYING_PARTY_NAME}=example")
        self.addCleanup(delete_policy, "fido2_rp")

    def _set_realm2_policy(self) -> None:
        set_policy("fido2_realm2", scope=SCOPE.ENROLL, realm=self.realm2,
                   action=f"{FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT}=required,"
                          f"{FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM}=indirect,"
                          f"{FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL}=trusted,"
                          f"{WEBAUTHN_TEXT_ACTION}=REALM2 WEBAUTHN TEXT")
        self.addCleanup(delete_policy, "fido2_realm2")

    def _init_webauthn(self) -> dict:
        with self.app.test_request_context("/token/init", method="POST",
                                           data={"type": "webauthn", "user": "cornelius", "realm": self.realm1},
                                           headers={"Authorization": self.at, "Origin": "https://example.com"}):
            res = self.app.full_dispatch_request()
        for token in get_tokens(user=User("cornelius", self.realm1)):
            remove_token(token.get_serial())
        self.assertEqual(200, res.status_code, res.json)
        return res.json["detail"]["webAuthnRegisterRequest"]

    def test_01_policy_of_other_realm_does_not_apply(self):
        self._set_realm2_policy()
        for token_type in ["webauthn", "passkey"]:
            with self.subTest(token_type=token_type):
                request = RequestMock()
                request.User = User("cornelius", self.realm1)
                request.all_data = {"type": token_type}
                fido2_enroll(request, None)
                self.assertEqual(DEFAULT_USER_VERIFICATION_REQUIREMENT,
                                 request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT))
                self.assertEqual(DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
                                 request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM))
                self.assertEqual(DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL,
                                 request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL))
                self.assertNotIn("REALM2", str(request.all_data.get(WEBAUTHN_TEXT_ACTION)))

                # The same policy applies to a user of realm2
                request = RequestMock()
                request.User = User("cornelius", self.realm2)
                request.all_data = {"type": token_type}
                fido2_enroll(request, None)
                self.assertEqual("required", request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT))
                self.assertEqual("trusted", request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL))
                self.assertEqual("REALM2 WEBAUTHN TEXT", request.all_data.get(WEBAUTHN_TEXT_ACTION))

    def test_02_token_init_uses_policy_of_the_users_realm(self):
        self._set_realm2_policy()
        register_request = self._init_webauthn()
        self.assertEqual("preferred", register_request["authenticatorSelection"]["userVerification"])
        self.assertEqual("direct", register_request.get("attestation"))
        self.assertNotIn("REALM2", register_request["message"])

    def test_03_differing_realm_policies_do_not_conflict(self):
        set_policy("uv_realm1", scope=SCOPE.ENROLL, realm=self.realm1,
                   action=f"{FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT}=discouraged")
        self.addCleanup(delete_policy, "uv_realm1")
        set_policy("uv_realm2", scope=SCOPE.ENROLL, realm=self.realm2,
                   action=f"{FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT}=required")
        self.addCleanup(delete_policy, "uv_realm2")
        register_request = self._init_webauthn()
        self.assertEqual("discouraged", register_request["authenticatorSelection"]["userVerification"])


class FIDO2PolicyConflictTestCase(MyApiTestCase):
    """
    Conflicting realm-scoped FIDO2 policies affect only FIDO2 and passkey, not every authentication request.
    """

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.user = User("cornelius", self.realm1)
        init_token({"serial": "SPASS_RPID", "type": "spass", "pin": "test"}, user=self.user)
        self.policies = []

    def tearDown(self) -> None:
        for name in self.policies:
            delete_policy(name)
        remove_token("SPASS_RPID")
        super().tearDown()

    def _policy(self, name: str, scope: str, action: str, realm: str) -> None:
        set_policy(name, scope=scope, action=action, realm=realm)
        self.policies.append(name)

    def _post(self, path: str, data: dict) -> tuple[int, object]:
        with self.app.test_request_context(path, method="POST", data=data):
            response = self.app.full_dispatch_request()
        return response.status_code, response.json.get("result", {}).get("value")

    def _logins(self) -> dict:
        return {"validate_check": self._post("/validate/check", {"user": "cornelius", "realm": self.realm1,
                                                                 "pass": "test"}),
                "auth_admin": self._post("/auth", {"username": self.testadmin, "password": self.testadminpw}),
                "initialize_passkey": self._post("/validate/initialize", {"type": "passkey"})}

    def test_01_conflicting_relying_party_ids_fail_only_passkey(self):
        self._policy("rp_realm1", SCOPE.ENROLL, "webauthn_relying_party_id=one.example.com", self.realm1)
        self._policy("rp_realm2", SCOPE.ENROLL, "webauthn_relying_party_id=two.example.com", self.realm2)
        results = self._logins()
        self.assertEqual((200, True), results["validate_check"])
        self.assertEqual(200, results["auth_admin"][0])
        # Passkey authentication has no user, so it can not choose between the two relying party IDs
        self.assertNotEqual(200, results["initialize_passkey"][0])

    def test_02_conflicting_challenge_texts_do_not_block_authentication(self):
        self._policy("text_realm1", SCOPE.AUTH, f"{WEBAUTHN_TEXT_ACTION}=Hello one", self.realm1)
        self._policy("text_realm2", SCOPE.AUTH, f"{WEBAUTHN_TEXT_ACTION}=Hello two", self.realm2)
        results = self._logins()
        self.assertEqual((200, True), results["validate_check"])
        self.assertEqual(200, results["auth_admin"][0])

    def test_03_challenge_text_of_the_users_realm(self):
        self._policy("text_realm1", SCOPE.AUTH, f"{WEBAUTHN_TEXT_ACTION}=Hello one", self.realm1)
        self._policy("text_realm2", SCOPE.AUTH, f"{WEBAUTHN_TEXT_ACTION}=Hello two", self.realm2)
        request = RequestMock()
        request.User = User("cornelius", self.realm2)
        request.all_data = {}
        with self.app.test_request_context("/validate/check", method="POST"):
            fido2_auth(request, None)
        self.assertEqual("Hello two", request.all_data[WEBAUTHN_TEXT_ACTION])
        self.assertEqual("", request.all_data[FIDO2PolicyAction.RELYING_PARTY_ID])

    def test_04_relying_party_id_of_the_users_realm(self):
        self._policy("rp_realm1", SCOPE.ENROLL, "webauthn_relying_party_id=one.example.com", self.realm1)
        self._policy("rp_realm2", SCOPE.ENROLL, "webauthn_relying_party_id=two.example.com", self.realm2)
        for realm, relying_party_id in [(self.realm1, "one.example.com"), (self.realm2, "two.example.com")]:
            with self.subTest(realm=realm):
                request = RequestMock()
                request.User = User("cornelius", realm)
                request.all_data = {}
                with self.app.test_request_context("/validate/check", method="POST"):
                    fido2_auth(request, None)
                self.assertEqual(relying_party_id, request.all_data[FIDO2PolicyAction.RELYING_PARTY_ID])
        # Without a user the two policies conflict
        request = RequestMock()
        request.User = User()
        request.all_data = {}
        with self.app.test_request_context("/validate/initialize", method="POST"):
            fido2_auth(request, None)
        self.assertEqual("", request.all_data[FIDO2PolicyAction.RELYING_PARTY_ID])
