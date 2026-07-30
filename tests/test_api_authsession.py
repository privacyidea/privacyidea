from .base import MyApiTestCase

from privacyidea.lib.clients import create_client
from privacyidea.lib.authsession import PERSISTENT_COOKIE_NAME, create_auth_session
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.user import User
from privacyidea.models import AuthSession


class CapabilitiesEndpointTestCase(MyApiTestCase):

    def _get(self, api_key=None):
        headers = {'X-API-Key': api_key} if api_key else {}
        with self.app.test_request_context('/auth/capabilities', method='GET', headers=headers):
            return self.app.full_dispatch_request()

    def test_01_requires_api_client(self):
        # Without an X-API-Key header, g.client_id is None -> 401.
        self.assertEqual(self._get().status_code, 401)

    def test_02_invalid_api_key_rejected(self):
        self.assertEqual(self._get("pi_deadbeef_nope").status_code, 401)

    def test_03_remember_device_reflects_policy(self):
        _client, api_key = create_client("caps client", "keycloak")

        # No remember_device policy -> capability is False (default off).
        res = self._get(api_key)
        self.assertEqual(res.status_code, 200, res)
        self.assertEqual(res.json['result']['value'], {"capabilities": {"remember_device": False}})

        # With the policy, the capability is advertised.
        set_policy("caps_remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            res = self._get(api_key)
            self.assertEqual(res.json['result']['value'], {"capabilities": {"remember_device": True}})
        finally:
            delete_policy("caps_remember")


class PersistentCookieValidateTestCase(MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        init_token({"type": "spass", "pin": "test", "serial": "SPASS_REMEMBER"},
                   user=User(login="cornelius", realm=self.realm1))

    def tearDown(self):
        remove_token("SPASS_REMEMBER")
        super().tearDown()

    def _cookies(self, res):
        return [v for k, v in res.headers if k == "Set-Cookie"
                and v.startswith(PERSISTENT_COOKIE_NAME + "=")]

    def _check(self, api_key=None, opt_in=True):
        data = {"user": "cornelius", "realm": self.realm1, "pass": "test"}
        if opt_in:
            data["request_persistent_cookie"] = True
        headers = {'X-API-Key': api_key} if api_key else {}
        with self.app.test_request_context('/validate/check', method='POST',
                                           data=data, headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(res.json['result']['value'], res.json)
            return res

    def test_01_cookie_issued_when_policy_allows(self):
        client, api_key = create_client("validate client", "windows_cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            res = self._check(api_key)
            cookies = self._cookies(res)
            self.assertEqual(len(cookies), 1, res.headers)
            cookie = cookies[0]
            self.assertIn("HttpOnly", cookie)
            self.assertIn("Secure", cookie)
            self.assertIn("SameSite=Strict", cookie)
            self.assertNotIn(api_key, cookie)

            session = AuthSession.query.filter_by(client_id=client.id).first()
            self.assertIsNotNone(session)
            self.assertEqual(session.counter, 1)
            self.assertEqual(session.user_id, "cornelius")
            self.assertIn(f"{PERSISTENT_COOKIE_NAME}={session.series_id}:1", cookie)
        finally:
            delete_policy("remember")

    def test_02_no_cookie_without_policy(self):
        _client, api_key = create_client("no policy client", "windows_cp")
        # No remember_device policy at all -> default off.
        self.assertEqual(self._cookies(self._check(api_key)), [])

    def test_03_no_cookie_without_opt_in(self):
        _client, api_key = create_client("no opt-in client", "windows_cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            self.assertEqual(self._cookies(self._check(api_key, opt_in=False)), [])
        finally:
            delete_policy("remember")

    def test_04_no_cookie_without_api_key(self):
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            # Opt-in but no API client identified -> no cookie (legacy behaviour).
            self.assertEqual(self._cookies(self._check(api_key=None)), [])
        finally:
            delete_policy("remember")

    def test_05_client_condition_targets_specific_client(self):
        # Policy only enables remember_device for windows_cp clients. The client
        # condition uses handle_missing_data=condition_is_false so that requests
        # without an API client simply do not match (instead of erroring).
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE,
                   conditions=[("client", "client_type", "equals", "windows_cp", True, "condition_is_false")])
        cp_client, cp_key = create_client("cp", "windows_cp")
        kc_client, kc_key = create_client("kc", "keycloak")
        try:
            # windows_cp client matches -> cookie issued.
            self.assertEqual(len(self._cookies(self._check(cp_key))), 1)
            # keycloak client does not match the condition -> no cookie.
            self.assertEqual(self._cookies(self._check(kc_key)), [])
            # A request without any API key must still authenticate fine (the
            # condition evaluates to false, it does not raise).
            self.assertEqual(self._cookies(self._check(api_key=None)), [])
        finally:
            delete_policy("remember")


class PersistentCookieConsumptionTestCase(MyApiTestCase):
    """
    Consuming a presented pi_remember_device cookie on /validate/check: the
    cookie is validated and rotated, the device is recognised, and reuse is
    detected. Consumption does not require the remember_device policy (theft
    detection is always active when a cookie is presented).
    """

    def setUp(self):
        self.setUp_user_realms()
        init_token({"type": "spass", "pin": "test", "serial": "SPASS_CONSUME"},
                   user=User(login="cornelius", realm=self.realm1))

    def tearDown(self):
        remove_token("SPASS_CONSUME")
        super().tearDown()

    def _cookie_headers(self, res):
        return [v for k, v in res.headers if k == "Set-Cookie"
                and v.startswith(PERSISTENT_COOKIE_NAME + "=")]

    def _check(self, api_key=None, cookie=None):
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        if cookie:
            headers["Cookie"] = f"{PERSISTENT_COOKIE_NAME}={cookie}"
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "realm": self.realm1,
                                                 "pass": "test"},
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(res.json['result']['value'], res.json)
            return res

    def test_01_valid_cookie_is_rotated_and_recognised(self):
        client, api_key = create_client("consume client", "windows_cp")
        session, cookie = create_auth_session("cornelius", client.id)
        series = session.series_id

        res = self._check(api_key=api_key, cookie=cookie)
        # Device recognised and reported.
        self.assertTrue(res.json['detail'].get("remembered_device"))
        # Cookie rotated to counter 2.
        headers = self._cookie_headers(res)
        self.assertEqual(len(headers), 1, headers)
        self.assertIn(f"{PERSISTENT_COOKIE_NAME}={series}:2", headers[0])
        # Counter incremented in the DB.
        self.assertEqual(AuthSession.query.filter_by(series_id=series).first().counter, 2)

    def test_02_reused_cookie_invalidates_series_without_failing_auth(self):
        client, api_key = create_client("theft client", "windows_cp")
        session, cookie = create_auth_session("cornelius", client.id)
        series = session.series_id

        # First use rotates to counter 2.
        self._check(api_key=api_key, cookie=cookie)
        # Replaying the original counter=1 cookie is reuse: series is invalidated,
        # but the (otherwise successful) authentication is not turned into a failure.
        res = self._check(api_key=api_key, cookie=cookie)
        self.assertTrue(res.json['result']['value'])
        self.assertFalse(res.json['detail'].get("remembered_device"))
        self.assertIsNone(AuthSession.query.filter_by(series_id=series).first())
        # The stale cookie is cleared from the client.
        self.assertTrue(any(h.startswith(f"{PERSISTENT_COOKIE_NAME}=;") for h in self._cookie_headers(res)),
                        self._cookie_headers(res))

    def test_03_wrong_client_cookie_not_honoured(self):
        client_a, _ = create_client("client A", "windows_cp")
        _client_b, key_b = create_client("client B", "keycloak")
        session, cookie = create_auth_session("cornelius", client_a.id)

        # Present A's cookie but authenticate as client B -> not matched.
        res = self._check(api_key=key_b, cookie=cookie)
        self.assertFalse(res.json['detail'].get("remembered_device"))
        # A's session is untouched (not rotated, not deleted).
        self.assertEqual(AuthSession.query.filter_by(series_id=session.series_id).first().counter, 1)

    def test_04_no_cookie_reports_not_remembered(self):
        _client, api_key = create_client("plain client", "windows_cp")
        res = self._check(api_key=api_key)
        self.assertFalse(res.json['detail'].get("remembered_device"))
        self.assertEqual(self._cookie_headers(res), [])
