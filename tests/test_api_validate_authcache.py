# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Which authentications the ``auth_cache`` policy stores and serves.

The cache lets a client present the same credential again for the duration of the
policy, so a client that reconnects regularly does not need a fresh OTP every time.
It therefore only holds a complete credential that was verified against a token or a
user store: a request answering a challenge, a request without a credential, and a
success that was decided by the absence of a token or of a user are all kept out.

Each test ends with a control step, so every result is attributable to the cache and
to nothing else.
"""
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from passlib.hash import argon2

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, delete_policy, set_policy
from privacyidea.lib.token import get_tokens, init_token, remove_token
from privacyidea.lib.tokens.pushtoken import (POLL_ONLY, PRIVATE_KEY_SERVER, PUBLIC_KEY_SERVER,
                                             PUBLIC_KEY_SMARTPHONE, PushAction, PushTokenClass,
                                             strip_pem_headers)
from privacyidea.lib.user import User
from privacyidea.lib.utils import b32encode_and_unicode, to_unicode
from privacyidea.models import AuthCache
from .base import MyApiTestCase


class AuthCacheCredentialTestCase(MyApiTestCase):

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    smartphone_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())

    def setUp(self) -> None:
        super().setUp()
        # The assertions read the authcache table, so keep the Redis backend out of it.
        # The decision which authentication is cached sits in the policy decorator above
        # both stores and is the same for either.
        self.pin_to_database("auth")
        self.setUp_user_realms()

    def tearDown(self) -> None:
        for policy in ("authcache", "chalresp", "nopass_token", "nopass_user", "passthru", "otppin"):
            try:
                delete_policy(policy)
            except ResourceNotFoundError:
                pass
        super().tearDown()

    def _validate(self, data: dict) -> dict:
        with self.app.test_request_context("/validate/check", method="POST", data=data):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            return res.json

    def _cache_holds(self, username: str, credential: str) -> bool:
        """Whether any entry of that user verifies the given credential. A hash only
        answers "does this string verify", so the credential has to be presented."""
        return any(argon2.verify(credential, row.authentication)
                   for row in AuthCache.query.filter(AuthCache.username == username).all())

    def _drop_tokens(self, username: str) -> None:
        for token in get_tokens(user=User(username, self.realm1)):
            remove_token(token.get_serial())

    def _create_push_token(self, user: str, pin: str) -> PushTokenClass:
        """A rolled-out, poll-only push token, so no Firebase call is involved."""
        server_key_pem = to_unicode(self.server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()))
        server_public_pem = to_unicode(self.server_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo))
        smartphone_public_pem = to_unicode(self.smartphone_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo))

        token = init_token({"type": "push", "genkey": 1})
        token.add_tokeninfo(PushAction.FIREBASE_CONFIG, POLL_ONLY)
        token.add_tokeninfo(PUBLIC_KEY_SMARTPHONE,
                            strip_pem_headers(smartphone_public_pem).replace("+", "-").replace("/", "_"))
        token.add_tokeninfo(PUBLIC_KEY_SERVER, server_public_pem)
        token.add_tokeninfo(PRIVATE_KEY_SERVER, server_key_pem, "password")
        token.delete_tokeninfo("enrollment_credential")
        token.token.rollout_state = "enrolled"
        token.token.active = True
        token.set_pin(pin)
        token.add_user(User(user, self.realm1))
        return token

    def _confirm_push(self, serial: str, transaction_id: str) -> None:
        """What the smartphone posts to /ttype/push to accept the request."""
        challenge = get_challenges(serial=serial, transaction_id=transaction_id)[0].challenge
        signature = b32encode_and_unicode(
            self.smartphone_key.sign(f"{challenge}|{serial}".encode(),
                                     padding.PKCS1v15(), hashes.SHA256()))
        with self.app.test_request_context("/ttype/push", method="POST",
                                           data={"serial": serial, "nonce": challenge,
                                                 "signature": signature}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json["result"]["value"], res.json)

    def test_01_challenge_response_is_not_cached(self):
        """The response to a challenge is only one part of the credential - the PIN was
        sent in the request before it - so it neither enters the cache nor is served
        from it."""
        self._drop_tokens("cornelius")
        init_token({"serial": "AC_CR", "otpkey": self.otpkey, "pin": "pin"},
                   user=User("cornelius", self.realm1))
        set_policy("chalresp", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        set_policy("authcache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")

        # The PIN triggers a challenge, so this request is not a success.
        first = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "pin"})
        self.assertFalse(first["result"]["value"], first)
        transaction_id = first["detail"]["transaction_id"]
        self.assertFalse(self._cache_holds("cornelius", "pin"))

        # The OTP answers that challenge and authenticates, but is not stored.
        second = self._validate({"user": "cornelius", "realm": self.realm1,
                                 "pass": "755224", "transaction_id": transaction_id})
        self.assertTrue(second["result"]["value"], second)
        self.assertFalse(self._cache_holds("cornelius", "755224"))

        # So the OTP does not authenticate on its own afterwards: the token has moved
        # past it and the cache does not hold it either.
        replay = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "755224"})
        self.assertFalse(replay["result"]["value"], replay)

        remove_token("AC_CR")

    def test_02_challenge_response_is_not_served_from_the_cache(self):
        """A request that answers a challenge is answered by the token. A credential the
        cache happens to hold does not authenticate such a request."""
        self._drop_tokens("cornelius")
        init_token({"serial": "AC_CR2", "otpkey": self.otpkey, "pin": "pin"},
                   user=User("cornelius", self.realm1))
        set_policy("authcache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")

        # A single-request authentication fills the cache with PIN+OTP.
        first = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "pin287082"})
        self.assertTrue(first["result"]["value"], first)
        self.assertTrue(self._cache_holds("cornelius", "pin287082"))

        # The same credential presented against an open challenge is not accepted, even
        # though the cache holds it.
        set_policy("chalresp", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        triggered = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "pin"})
        transaction_id = triggered["detail"]["transaction_id"]
        answer = self._validate({"user": "cornelius", "realm": self.realm1,
                                 "pass": "pin287082", "transaction_id": transaction_id})
        self.assertFalse(answer["result"]["value"], answer)

        # Control: without a transaction_id the same credential is still served from the
        # cache, so the refusal above is the transaction_id and nothing else.
        delete_policy("chalresp")
        control = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "pin287082"})
        self.assertTrue(control["result"]["value"], control)
        self.assertEqual("Authenticated by AuthCache.", control["detail"]["message"])

        remove_token("AC_CR2")

    def test_03_push_confirmation_is_not_cached(self):
        """A push token is confirmed out of band and its final request carries no
        credential at all, so there is nothing to cache."""
        self._drop_tokens("cornelius")
        token = self._create_push_token("cornelius", "pushpin")
        serial = token.get_serial()
        set_policy("authcache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")

        first = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "pushpin"})
        self.assertFalse(first["result"]["value"], first)
        transaction_id = first["detail"]["transaction_id"]

        # The user accepts the request on the phone.
        self._confirm_push(serial, transaction_id)

        # The client picks up the result. This request succeeds and carries an empty pass.
        second = self._validate({"user": "cornelius", "realm": self.realm1,
                                 "pass": "", "transaction_id": transaction_id})
        self.assertTrue(second["result"]["value"], second)
        self.assertFalse(self._cache_holds("cornelius", ""))

        # An empty pass therefore does not authenticate afterwards.
        replay = self._validate({"user": "cornelius", "realm": self.realm1, "pass": ""})
        self.assertFalse(replay["result"]["value"], replay)

        remove_token(serial)

    def test_04_push_confirmation_without_a_pass_parameter(self):
        """A client may omit ``pass`` instead of sending an empty one. The request
        authenticates and is answered normally."""
        self._drop_tokens("cornelius")
        token = self._create_push_token("cornelius", "pushpin")
        serial = token.get_serial()
        set_policy("authcache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")

        first = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "pushpin"})
        transaction_id = first["detail"]["transaction_id"]
        self._confirm_push(serial, transaction_id)

        second = self._validate({"user": "cornelius", "realm": self.realm1,
                                 "transaction_id": transaction_id})
        self.assertTrue(second["result"]["value"], second)

        remove_token(serial)

    def test_05_pass_on_no_token_is_not_cached(self):
        """The success comes from the absence of a token, not from the credential, so
        the credential is not stored and stops working with the policy."""
        self._drop_tokens("selfservice")
        set_policy("nopass_token", scope=SCOPE.AUTH, action=f"{PolicyAction.PASSONNOTOKEN}=True")
        set_policy("authcache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")

        first = self._validate({"user": "selfservice", "realm": self.realm1, "pass": "whatever"})
        self.assertTrue(first["result"]["value"], first)
        self.assertFalse(self._cache_holds("selfservice", "whatever"))
        # The marker that keeps this success out of the cache stays on the server.
        self.assertNotIn("auth_cache_exclude", first["detail"])

        delete_policy("nopass_token")
        after = self._validate({"user": "selfservice", "realm": self.realm1, "pass": "whatever"})
        self.assertFalse(after["result"]["value"], after)

    def test_06_pass_on_no_user_is_not_cached(self):
        """Same for a user that does not exist: the entry does not outlive the policy."""
        set_policy("nopass_user", scope=SCOPE.AUTH, action=f"{PolicyAction.PASSONNOUSER}=True")
        set_policy("authcache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")

        first = self._validate({"user": "ghostuser", "realm": self.realm1, "pass": "whatever"})
        self.assertTrue(first["result"]["value"], first)
        self.assertFalse(self._cache_holds("ghostuser", "whatever"))
        self.assertNotIn("auth_cache_exclude", first["detail"])

        # Without the policy the user is unknown again, which is an error and not a
        # failed authentication.
        delete_policy("nopass_user")
        with self.app.test_request_context("/validate/check", method="POST",
                                           data={"user": "ghostuser", "realm": self.realm1,
                                                 "pass": "whatever"}):
            res = self.app.full_dispatch_request()
            self.assertGreaterEqual(res.status_code, 400, res.json)

    def test_07_passthru_userstore_is_cached(self):
        """A user store password is a complete, verified credential, so it is cached and
        the next authentication does not reach the user store."""
        self._drop_tokens("cornelius")
        set_policy("passthru", scope=SCOPE.AUTH, action=f"{PolicyAction.PASSTHRU}=userstore")
        set_policy("authcache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")

        first = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "test"})
        self.assertTrue(first["result"]["value"], first)
        self.assertIn("userstore", first["detail"]["message"])
        self.assertTrue(self._cache_holds("cornelius", "test"))

        second = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "test"})
        self.assertTrue(second["result"]["value"], second)
        self.assertEqual("Authenticated by AuthCache.", second["detail"]["message"])

        delete_policy("passthru")

    def test_08_otppin_userstore_caches_password_and_otp(self):
        """The credential of a single request is complete even when it contains an OTP,
        so the whole string is cached and stays usable for the window."""
        self._drop_tokens("cornelius")
        init_token({"serial": "AC_PIN", "otpkey": self.otpkey}, user=User("cornelius", self.realm1))
        set_policy("otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")
        set_policy("authcache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")

        first = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "test755224"})
        self.assertTrue(first["result"]["value"], first)
        self.assertTrue(self._cache_holds("cornelius", "test755224"))

        # The token's counter has moved on, so only the cache can still accept this.
        second = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "test755224"})
        self.assertTrue(second["result"]["value"], second)
        self.assertEqual("Authenticated by AuthCache.", second["detail"]["message"])

        delete_policy("authcache")
        control = self._validate({"user": "cornelius", "realm": self.realm1, "pass": "test755224"})
        self.assertFalse(control["result"]["value"], control)

        delete_policy("otppin")
        remove_token("AC_PIN")
