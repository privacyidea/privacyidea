from .base import MyApiTestCase

from privacyidea.lib.clients import create_client
from privacyidea.lib.remembered_device import PERSISTENT_COOKIE_NAME, create_remembered_device, user_identity
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.user import User
from privacyidea.models import RememberedDevice
from privacyidea.models.utils import utc_now


class CapabilitiesEndpointTestCase(MyApiTestCase):

    def _get(self, api_key=None):
        headers = {'X-API-Key': api_key} if api_key else {}
        with self.app.test_request_context('/validate/capabilities', method='GET', headers=headers):
            return self.app.full_dispatch_request()

    def test_01_requires_api_client(self):
        # Without an X-API-Key header, g.client_id is None -> 401.
        self.assertEqual(401, self._get().status_code)

    def test_02_invalid_api_key_rejected(self):
        self.assertEqual(401, self._get("pi_deadbeef_nope").status_code)

    def test_03_remember_device_reflects_policy(self):
        _client, api_key = create_client("caps client", "keycloak")

        # No remember_device policy -> capability is False (default off).
        res = self._get(api_key)
        self.assertEqual(200, res.status_code, res)
        self.assertDictEqual({"capabilities": {"remember_device": False}}, res.json['result']['value'])

        # With the policy, the capability is advertised.
        set_policy("caps_remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            res = self._get(api_key)
            self.assertDictEqual({"capabilities": {"remember_device": True}}, res.json['result']['value'])
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
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json['result']['value'], res.json)
            return res

    def test_01_cookie_issued_when_policy_allows(self):
        client, api_key = create_client("validate client", "windows_cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            res = self._check(api_key)
            cookies = self._cookies(res)
            self.assertEqual(1, len(cookies), res.headers)
            cookie = cookies[0]
            self.assertIn("HttpOnly", cookie)
            self.assertIn("Secure", cookie)
            self.assertIn("SameSite=Strict", cookie)
            # Both a relative Max-Age (which the client needs) and an Expires.
            self.assertIn("Max-Age=", cookie)
            self.assertIn("Expires=", cookie)
            self.assertNotIn(api_key, cookie)

            device = RememberedDevice.query.filter_by(client_id=client.id).first()
            self.assertIsNotNone(device)
            self.assertEqual(1, device.counter)
            # The device is bound to the authenticating user's resolver-stable
            # identity (resolver, user_id, realm_id) - not the login.
            identity = user_identity(User(login="cornelius", realm=self.realm1))
            self.assertEqual(identity.resolver, device.resolver)
            self.assertEqual(identity.user_id, device.user_id)
            self.assertEqual(identity.realm_id, device.realm_id)
            self.assertIn(f"{PERSISTENT_COOKIE_NAME}={device.series_id}:1", cookie)
        finally:
            delete_policy("remember")

    def test_02_no_cookie_without_policy(self):
        _client, api_key = create_client("no policy client", "windows_cp")
        # No remember_device policy at all -> default off.
        self.assertEqual([], self._cookies(self._check(api_key)))

    def test_03_no_cookie_without_opt_in(self):
        _client, api_key = create_client("no opt-in client", "windows_cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            self.assertEqual([], self._cookies(self._check(api_key, opt_in=False)))
        finally:
            delete_policy("remember")

    def test_04_no_cookie_without_api_key(self):
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            # Opt-in but no API client identified -> no cookie (legacy behaviour).
            self.assertEqual([], self._cookies(self._check(api_key=None)))
        finally:
            delete_policy("remember")

    def test_06_no_cookie_for_userless_auth(self):
        # A serial-only (userless) auth has no resolver-stable identity to bind
        # to, and the recognition endpoint matches on that identity, so a cookie
        # here could never be redeemed. It must not be issued (no dead device row).
        client, api_key = create_client("serial-only client", "windows_cp")
        init_token({"type": "spass", "pin": "test", "serial": "SPASS_NOUSER"})
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            with self.app.test_request_context(
                    '/validate/check', method='POST',
                    data={"serial": "SPASS_NOUSER", "pass": "test",
                          "request_persistent_cookie": True},
                    headers={'X-API-Key': api_key}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                self.assertTrue(res.json['result']['value'], res.json)
                self.assertEqual([], self._cookies(res))
            self.assertIsNone(RememberedDevice.query.filter_by(client_id=client.id).first())
        finally:
            delete_policy("remember")
            remove_token("SPASS_NOUSER")

    def test_07_validity_is_policy_configurable(self):
        # The cookie lifetime comes from the remember_device_validity policy
        # (scopable per realm/user), falling back to the 30-day default.
        client, api_key = create_client("validity client", "windows_cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            # Default (no validity policy) -> ~30 days.
            self._check(api_key)
            device = RememberedDevice.query.filter_by(client_id=client.id).first()
            self.assertAlmostEqual((device.expires_at - utc_now()).days, 30, delta=1)

            # With a 7-day validity policy, a newly issued cookie lasts ~7 days.
            set_policy("remember_validity", scope=SCOPE.AUTH,
                       action=f"{PolicyAction.REMEMBER_DEVICE_VALIDITY}=7")
            other, other_key = create_client("validity client 2", "windows_cp")
            self._check(other_key)
            device2 = RememberedDevice.query.filter_by(client_id=other.id).first()
            self.assertAlmostEqual((device2.expires_at - utc_now()).days, 7, delta=1)
        finally:
            delete_policy("remember")
            try:
                delete_policy("remember_validity")
            except ResourceNotFoundError:
                pass


class RememberDeviceRecognitionTestCase(MyApiTestCase):
    """
    Recognition of a presented pi_remember_device cookie on the dedicated
    /validate/remember_device endpoint. This only answers "is this device
    remembered for this user and client?" and rotates the cookie on a hit; it is
    not an authentication (no credential, no challenge). Recognition is offered
    only when the remember_device policy allows it (set in setUp) and the cookie
    is bound to the exact user. Theft detection is always active.
    """

    POLICY = "remember_consume"

    def setUp(self):
        self.setUp_user_realms()
        self.identity = user_identity(User(login="cornelius", realm=self.realm1))
        set_policy(self.POLICY, scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)

    def tearDown(self):
        try:
            delete_policy(self.POLICY)
        except ResourceNotFoundError:
            pass
        super().tearDown()

    def _cookie_headers(self, res):
        return [v for k, v in res.headers if k == "Set-Cookie"
                and v.startswith(PERSISTENT_COOKIE_NAME + "=")]

    def _recognise(self, api_key=None, cookie=None, user="cornelius", expect_value=True):
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        if cookie:
            headers["Cookie"] = f"{PERSISTENT_COOKIE_NAME}={cookie}"
        with self.app.test_request_context('/validate/remember_device', method='POST',
                                           data={"user": user, "realm": self.realm1},
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(bool(res.json['result']['value']), expect_value, res.json)
            self.assertEqual(bool(res.json['detail'].get("remembered_device")), expect_value, res.json)
            return res

    def test_00_requires_api_client(self):
        # Without an X-API-Key header, g.client_id is None -> 401.
        with self.app.test_request_context('/validate/remember_device', method='POST',
                                           data={"user": "cornelius", "realm": self.realm1}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)

    def test_01_valid_cookie_is_rotated_and_recognised(self):
        client, api_key = create_client("consume client", "windows_cp")
        device, cookie = create_remembered_device(self.identity, client.id)
        series = device.series_id

        res = self._recognise(api_key=api_key, cookie=cookie)
        # Cookie rotated to counter 2.
        headers = self._cookie_headers(res)
        self.assertEqual(1, len(headers), headers)
        self.assertIn(f"{PERSISTENT_COOKIE_NAME}={series}:2", headers[0])
        # Counter incremented in the DB.
        self.assertEqual(2, RememberedDevice.query.filter_by(series_id=series).first().counter)

    def test_02_reused_cookie_invalidates_series(self):
        # Disable the grace window so replaying the previous counter is treated
        # strictly as reuse (with grace on it would be a tolerated duplicate).
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client, api_key = create_client("theft client", "windows_cp")
            device, cookie = create_remembered_device(self.identity, client.id)
            series = device.series_id

            # First use rotates to counter 2.
            self._recognise(api_key=api_key, cookie=cookie)
            # Replaying the original counter=1 cookie is reuse: the series is
            # invalidated and the device is no longer recognised.
            res = self._recognise(api_key=api_key, cookie=cookie, expect_value=False)
            self.assertIsNone(RememberedDevice.query.filter_by(series_id=series).first())
            # The stale cookie is cleared from the client.
            self.assertTrue(any(h.startswith(f"{PERSISTENT_COOKIE_NAME}=;")
                                for h in self._cookie_headers(res)), self._cookie_headers(res))
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_02b_concurrent_duplicate_tolerated_by_grace(self):
        # Two requests presenting the same cookie: the second still shows the
        # previous counter but is tolerated within the grace window - recognised,
        # not treated as theft, and the series is neither rotated again nor
        # deleted (and no new cookie is handed out).
        client, api_key = create_client("grace client", "windows_cp")
        device, cookie = create_remembered_device(self.identity, client.id)
        series = device.series_id
        self._recognise(api_key=api_key, cookie=cookie)          # rotates to counter 2
        res = self._recognise(api_key=api_key, cookie=cookie)    # previous counter, within grace
        self.assertEqual([], self._cookie_headers(res))
        stored = RememberedDevice.query.filter_by(series_id=series).first()
        self.assertIsNotNone(stored)
        self.assertEqual(2, stored.counter)

    def test_03_wrong_client_cookie_not_honoured(self):
        client_a, _ = create_client("client A", "windows_cp")
        _client_b, key_b = create_client("client B", "keycloak")
        device, cookie = create_remembered_device(self.identity, client_a.id)

        # Present A's cookie but as client B -> not matched.
        self._recognise(api_key=key_b, cookie=cookie, expect_value=False)
        # A's device is untouched (not rotated, not deleted).
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=device.series_id).first().counter)

    def test_04_no_cookie_reports_not_remembered(self):
        _client, api_key = create_client("plain client", "windows_cp")
        res = self._recognise(api_key=api_key, expect_value=False)
        self.assertEqual([], self._cookie_headers(res))

    def test_05_recognition_is_audited(self):
        # A recognition is its own audit action and is recorded as a success,
        # but it is not an authentication (no ACCEPT/REJECT) and touches no token.
        client, api_key = create_client("audit recognise client", "windows_cp")
        _device, cookie = create_remembered_device(self.identity, client.id)
        self._recognise(api_key=api_key, cookie=cookie)

        entry = self.find_most_recent_audit_entry(info="*remembered device recognised*")
        self.assertEqual(1, entry["success"])
        # Not marked as an authentication.
        self.assertFalse(entry.get("authentication"))
        # No token was involved.
        self.assertFalse(entry.get("serial"))

    def test_06_reuse_is_audited(self):
        # Replaying a stale cookie is recorded in the audit log (grace disabled
        # so the replay is treated strictly as reuse).
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client, api_key = create_client("audit reuse client", "windows_cp")
            _device, cookie = create_remembered_device(self.identity, client.id)
            self._recognise(api_key=api_key, cookie=cookie)                      # rotates to counter 2
            self._recognise(api_key=api_key, cookie=cookie, expect_value=False)  # stale counter 1 replayed

            entry = self.find_most_recent_audit_entry(action_detail="*persistent cookie reuse detected*")
            self.assertIn("persistent cookie reuse detected", entry.get("action_detail", ""))
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_07_no_policy_means_no_recognition(self):
        # Without the remember_device policy, recognition is not offered: a valid
        # cookie reports "not remembered" and is left untouched (not consumed).
        delete_policy(self.POLICY)
        client, api_key = create_client("no policy consume", "windows_cp")
        device, cookie = create_remembered_device(self.identity, client.id)
        res = self._recognise(api_key=api_key, cookie=cookie, expect_value=False)
        # The cookie is neither rotated nor cleared.
        self.assertEqual([], self._cookie_headers(res))
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=device.series_id).first().counter)

    def test_08_foreign_user_cookie_is_soft_miss_not_cleared(self):
        # Shared browser: a cookie issued for one user, presented while a
        # different user of the same client authenticates, is not recognised -
        # but it must be left alone (soft miss), not cleared, or one user logging
        # in would wipe the other user's remembered device off the browser.
        client, api_key = create_client("shared client", "windows_cp")
        other_identity = user_identity(User(login="shadow", realm=self.realm1))
        device, cookie = create_remembered_device(other_identity, client.id)
        # cornelius presents shadow's cookie: it is not bound to cornelius.
        res = self._recognise(api_key=api_key, cookie=cookie, expect_value=False)
        # No clearing Set-Cookie, and the other user's device is untouched.
        self.assertEqual([], self._cookie_headers(res))
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=device.series_id).first().counter)

    def test_10_dead_cookie_is_cleared(self):
        # A genuinely dead cookie (unknown series) is a hard miss: it is cleared
        # so the client stops sending it.
        _client, api_key = create_client("clear client", "windows_cp")
        res = self._recognise(api_key=api_key, cookie="doesnotexist:1", expect_value=False)
        self.assertTrue(any(h.startswith(f"{PERSISTENT_COOKIE_NAME}=;")
                            for h in self._cookie_headers(res)), self._cookie_headers(res))

    def test_09_unresolvable_user_not_recognized(self):
        # Recognition resolves the presented login to its stable identity before
        # matching. A login that does not resolve (e.g. a deleted/removed account)
        # yields no identity, so no remembered device is ever recognised for it -
        # deleting an account revokes its remembered devices.
        client, api_key = create_client("ghost client", "windows_cp")
        device, cookie = create_remembered_device(self.identity, client.id)   # bound to cornelius
        # Present cornelius's cookie but as a non-existent user -> not recognised,
        # and cornelius's real device is never even reached, so it is untouched.
        self._recognise(api_key=api_key, cookie=cookie, user="ghost", expect_value=False)
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=device.series_id).first().counter)
