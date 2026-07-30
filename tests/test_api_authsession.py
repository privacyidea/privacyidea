from .base import MyApiTestCase

from privacyidea.lib.clients import create_client
from privacyidea.lib.authsession import PERSISTENT_COOKIE_NAME, create_auth_session, session_user_id
from privacyidea.lib.error import ResourceNotFoundError
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
            # The session is bound to the authenticating user (login@realm).
            self.assertEqual(session.user_id, f"cornelius@{self.realm1}")
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
    Consuming a presented pi_remember_device cookie on /validate/check. Redeeming
    a recognised device to skip the second factor requires the remember_device
    policy (set in setUp) and the cookie is bound to the authenticating user.
    Theft detection is always active when a cookie is presented.
    """

    POLICY = "remember_consume"

    def setUp(self):
        self.setUp_user_realms()
        init_token({"type": "spass", "pin": "test", "serial": "SPASS_CONSUME"},
                   user=User(login="cornelius", realm=self.realm1))
        self.uid = session_user_id(User(login="cornelius", realm=self.realm1))
        set_policy(self.POLICY, scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)

    def tearDown(self):
        remove_token("SPASS_CONSUME")
        try:
            delete_policy(self.POLICY)
        except ResourceNotFoundError:
            pass
        super().tearDown()

    def _cookie_headers(self, res):
        return [v for k, v in res.headers if k == "Set-Cookie"
                and v.startswith(PERSISTENT_COOKIE_NAME + "=")]

    def _check(self, api_key=None, cookie=None, user="cornelius", password="test", expect_value=True):
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        if cookie:
            headers["Cookie"] = f"{PERSISTENT_COOKIE_NAME}={cookie}"
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": user, "realm": self.realm1, "pass": password},
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertEqual(bool(res.json['result']['value']), expect_value, res.json)
            return res

    def test_01_valid_cookie_is_rotated_and_recognised(self):
        client, api_key = create_client("consume client", "windows_cp")
        session, cookie = create_auth_session(self.uid, client.id)
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
        # Disable the grace window so replaying the previous counter is treated
        # strictly as reuse (with grace on it would be a tolerated duplicate).
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client, api_key = create_client("theft client", "windows_cp")
            session, cookie = create_auth_session(self.uid, client.id)
            series = session.series_id

            # First use rotates to counter 2.
            self._check(api_key=api_key, cookie=cookie)
            # Replaying the original counter=1 cookie is reuse: series is
            # invalidated, but the request still succeeds via the real second
            # factor (pass=test).
            res = self._check(api_key=api_key, cookie=cookie)
            self.assertFalse(res.json['detail'].get("remembered_device"))
            self.assertIsNone(AuthSession.query.filter_by(series_id=series).first())
            # The stale cookie is cleared from the client.
            self.assertTrue(any(h.startswith(f"{PERSISTENT_COOKIE_NAME}=;")
                                for h in self._cookie_headers(res)), self._cookie_headers(res))
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_02b_concurrent_duplicate_tolerated_by_grace(self):
        # Two requests presenting the same cookie: the second still shows the
        # previous counter but is tolerated within the grace window - accepted,
        # not treated as theft, and the series is neither rotated again nor
        # deleted.
        client, api_key = create_client("grace client", "windows_cp")
        session, cookie = create_auth_session(self.uid, client.id)
        series = session.series_id
        self._check(api_key=api_key, cookie=cookie)          # rotates to counter 2
        res = self._check(api_key=api_key, cookie=cookie)    # previous counter, within grace
        self.assertTrue(res.json['detail'].get("remembered_device"))
        stored = AuthSession.query.filter_by(series_id=series).first()
        self.assertIsNotNone(stored)
        self.assertEqual(stored.counter, 2)

    def test_03_wrong_client_cookie_not_honoured(self):
        client_a, _ = create_client("client A", "windows_cp")
        _client_b, key_b = create_client("client B", "keycloak")
        session, cookie = create_auth_session(self.uid, client_a.id)

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

    def test_05_accept_is_audited_as_accept(self):
        # A recognised device is accepted before token verification, so the audit
        # records a clean ACCEPT (not a CHALLENGE) and no token is touched. A
        # wrong password would normally fail - the device carries the auth.
        client, api_key = create_client("audit accept client", "windows_cp")
        _session, cookie = create_auth_session(self.uid, client.id)
        self._check(api_key=api_key, cookie=cookie, password="wrong", expect_value=True)

        entry = self.find_most_recent_audit_entry(info="*Accepted by remembered device*")
        self.assertEqual(entry["success"], 1)
        self.assertEqual(entry["authentication"], "ACCEPT")
        # No token was involved (no challenge fired).
        self.assertFalse(entry.get("serial"))

    def test_06_reuse_is_audited(self):
        # Replaying a stale cookie is recorded in the audit log (grace disabled
        # so the replay is treated strictly as reuse).
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client, api_key = create_client("audit reuse client", "windows_cp")
            _session, cookie = create_auth_session(self.uid, client.id)
            self._check(api_key=api_key, cookie=cookie)   # rotates to counter 2
            self._check(api_key=api_key, cookie=cookie)   # stale counter 1 replayed

            entry = self.find_most_recent_audit_entry(action_detail="*persistent cookie reuse detected*")
            self.assertIn("persistent cookie reuse detected", entry.get("action_detail", ""))
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_07_no_policy_means_device_not_accepted(self):
        # Without the remember_device policy, a recognised device does NOT skip
        # the second factor: a wrong password fails despite a valid cookie.
        delete_policy(self.POLICY)
        client, api_key = create_client("no policy consume", "windows_cp")
        _session, cookie = create_auth_session(self.uid, client.id)
        self._check(api_key=api_key, cookie=cookie, password="wrong", expect_value=False)

    def test_08_cookie_bound_to_user_not_honoured_for_other_user(self):
        # A cookie issued for one user must not be honoured for a different user
        # on the same API client.
        client, api_key = create_client("shared client", "windows_cp")
        other_uid = session_user_id(User(login="someoneelse", realm=self.realm1))
        session, cookie = create_auth_session(other_uid, client.id)
        # cornelius presents someoneelse's cookie: it is not bound to cornelius,
        # so it is not honoured (cornelius still authenticates via the real
        # second factor).
        res = self._check(api_key=api_key, cookie=cookie)
        self.assertFalse(res.json['detail'].get("remembered_device"))
        # The other user's session is untouched.
        self.assertEqual(AuthSession.query.filter_by(series_id=session.series_id).first().counter, 1)
