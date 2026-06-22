# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for the hide_version policy.

Verifies that:
- Version fields are stripped from unauthenticated API responses when the
  HIDE_VERSION policy is active.
- The JSON signature remains valid after version stripping (i.e. stripping
  happens *before* signing, not after).
- Authenticated users still see version fields.
- Multiple API endpoints are covered.
"""
import json

from flask import current_app, g

from privacyidea.lib.config import get_app_local_store
from privacyidea.lib.crypto import Sign
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from .base import MyApiTestCase


class HideVersionIntegrationTest(MyApiTestCase):
    """
    Full-stack tests that exercise the real Flask after_request pipeline
    (hide_version → sign_response) via ``app.full_dispatch_request()``.
    """

    def setUp(self):
        super().setUp()
        pub_key_path = current_app.config.get("PI_AUDIT_KEY_PUBLIC")
        with open(pub_key_path, "rb") as f:
            public_key = f.read()
        self.sign_object = Sign(private_key=None, public_key=public_key)

    def _set_policy(self):
        """Activate the hide_version policy and invalidate config cache."""
        set_policy(name="test_hide_version",
                   scope=SCOPE.HARDENING,
                   action=PolicyAction.HIDE_VERSION)
        store = get_app_local_store()
        store.pop('shared_config_object', None)

    def _clear_policy(self):
        """Remove the hide_version policy and invalidate config cache."""
        try:
            delete_policy("test_hide_version")
        except Exception:
            pass
        store = get_app_local_store()
        store.pop('shared_config_object', None)

    def _dispatch(self, path, method='GET', data=None, headers=None):
        """Dispatch a request through the full Flask pipeline and return the
        parsed JSON response."""
        g.pop('logged_in_user', None)
        g.pop('policy_object', None)
        kwargs = {'method': method}
        if data:
            kwargs['data'] = data
        if headers:
            kwargs['headers'] = headers
        with self.app.test_request_context(path, **kwargs):
            res = self.app.full_dispatch_request()
        return res

    def _verify_signature(self, data):
        """Verify the JSON signature on a response dict."""
        content = dict(data)
        sig = content.pop("signature", None)
        if not sig:
            return False
        return self.sign_object.verify(json.dumps(content, sort_keys=True), sig)

    def _assert_version_hidden(self, data):
        """Assert version fields are stripped and signature is valid."""
        self.assertNotIn("version", data)
        self.assertNotIn("versionnumber", data)
        self.assertIn("signature", data)
        self.assertTrue(self._verify_signature(data),
                        "Signature must be valid after version stripping")

    def _assert_version_visible(self, data):
        """Assert version field is present and signature is valid.
        Note: 'versionnumber' is only included in success responses (send_result),
        not in error responses (send_error)."""
        self.assertIn("version", data)
        self.assertIn("signature", data)
        self.assertTrue(self._verify_signature(data))

    # ------------------------------------------------------------------
    # Core behaviour: unauthenticated requests with/without policy
    # ------------------------------------------------------------------
    def test_unauthenticated_hides_version_with_policy(self):
        """Unauthenticated responses have version stripped when policy is active."""
        self._set_policy()
        self.addCleanup(self._clear_policy)

        res = self._dispatch('/auth', method='POST',
                             data={"username": "nonexistent", "password": "wrong"})
        self._assert_version_hidden(res.json)

    def test_unauthenticated_shows_version_without_policy(self):
        """Without the policy, version fields remain in unauthenticated responses."""
        self._clear_policy()

        res = self._dispatch('/auth', method='POST',
                             data={"username": "nonexistent", "password": "wrong"})
        self._assert_version_visible(res.json)

    # ------------------------------------------------------------------
    # Authenticated users always see version
    # ------------------------------------------------------------------
    def test_authenticated_shows_version_with_policy(self):
        """Authenticated users see the version even with the policy active."""
        self._set_policy()
        self.addCleanup(self._clear_policy)

        res = self._dispatch('/auth', method='POST',
                             data={"username": self.testadmin,
                                   "password": self.testadminpw})
        self.assertEqual(200, res.status_code)
        self._assert_version_visible(res.json)

    def test_admin_endpoint_shows_version_with_policy(self):
        """Admin endpoints always show version, even with the policy."""
        self._set_policy()
        self.addCleanup(self._clear_policy)

        res = self._dispatch('/system/', headers={"Authorization": self.at})
        self.assertEqual(200, res.status_code)
        self._assert_version_visible(res.json)

    # ------------------------------------------------------------------
    # Signature validity: the original bug (regression guard)
    # ------------------------------------------------------------------
    def test_signature_valid_after_version_stripping(self):
        """Version stripping must happen *before* signing. If it happened
        after, the signature would not match the delivered body."""
        self._set_policy()
        self.addCleanup(self._clear_policy)

        res = self._dispatch('/auth', method='POST',
                             data={"username": "nobody", "password": "nothing"})
        data = res.json
        self.assertNotIn("version", data)
        sig = data.pop("signature")
        self.assertTrue(
            self.sign_object.verify(json.dumps(data, sort_keys=True), sig),
            "Signature must verify against body with version already stripped"
        )

    # ------------------------------------------------------------------
    # Multi-endpoint coverage
    # ------------------------------------------------------------------
    def test_multiple_endpoints_hide_version(self):
        """Various unauthenticated endpoints all strip version fields."""
        self._set_policy()
        self.addCleanup(self._clear_policy)

        endpoints = [
            ('/auth', 'POST', {"username": "x", "password": "y"}),
            ('/validate/check', 'POST', {"user": "cornelius", "pass": "wrong"}),
            ('/config', 'GET', None),
        ]
        for path, method, data in endpoints:
            with self.subTest(endpoint=path):
                res = self._dispatch(path, method=method, data=data)
                self._assert_version_hidden(res.json)

    # ------------------------------------------------------------------
    # /config endpoint: nested privacyideaVersionNumber
    # ------------------------------------------------------------------
    def test_config_hides_nested_version_number(self):
        """/config strips privacyideaVersionNumber from result.value."""
        self._set_policy()
        self.addCleanup(self._clear_policy)

        res = self._dispatch('/config')
        self.assertEqual(200, res.status_code)
        data = res.json
        self._assert_version_hidden(data)
        value = data.get("result", {}).get("value", {})
        self.assertNotIn("privacyideaVersionNumber", value)
        # Other config values must remain
        self.assertIn("browser_lang", value)

    def test_config_shows_version_without_policy(self):
        """Without the policy, /config includes all version fields."""
        self._clear_policy()

        res = self._dispatch('/config')
        data = res.json
        self._assert_version_visible(data)
        self.assertIn("versionnumber", data)
        value = data.get("result", {}).get("value", {})
        self.assertIn("privacyideaVersionNumber", value)
