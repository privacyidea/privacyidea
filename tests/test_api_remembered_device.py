import re
from unittest.mock import patch

from .base import MyApiTestCase

from privacyidea.lib.clients import create_client
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs
from privacyidea.lib.remembered_device import (PERSISTENT_COOKIE_NAME, create_remembered_device, user_identity,
                                               parse_cookie, hash_series_id)
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.policy import AUTHORIZED, set_policy, delete_policy, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.token import enable_token, init_token, remove_token
from privacyidea.lib.user import User
from privacyidea.models import RememberedDevice
from privacyidea.models.utils import utc_now

from datetime import timedelta


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
        _client, api_key = create_client("caps client", "privacyidea-keycloak")

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

    def test_04_successful_capabilities_audited_as_success(self):
        # A successful discovery must be recorded as success=1, not the
        # success=False seeded by validate's before_request.
        _client, api_key = create_client("caps audit client", "privacyidea-keycloak")
        self.assertEqual(200, self._get(api_key).status_code)
        entry = self.find_most_recent_audit_entry(action="*validate/capabilities*")
        self.assertEqual(1, entry["success"])


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

    def _check(self, api_key=None, opt_in=True, user="cornelius", password="test"):
        data = {"user": user, "realm": self.realm1, "pass": password}
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
        client, api_key = create_client("validate client", "privacyidea-cp")
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
            # The cookie carries the series id, the device stores its digest
            series_id, counter = parse_cookie(cookie.split(";", 1)[0].split("=", 1)[1])
            self.assertEqual(1, counter)
            self.assertEqual(hash_series_id(series_id), device.series_id)
        finally:
            delete_policy("remember")

    def test_02_no_cookie_without_policy(self):
        _client, api_key = create_client("no policy client", "privacyidea-cp")
        # No remember_device policy at all -> default off.
        self.assertEqual([], self._cookies(self._check(api_key)))

    def test_03_no_cookie_without_opt_in(self):
        _client, api_key = create_client("no opt-in client", "privacyidea-cp")
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
        client, api_key = create_client("serial-only client", "privacyidea-cp")
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
        client, api_key = create_client("validity client", "privacyidea-cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        try:
            # Default (no validity policy) -> ~30 days.
            self._check(api_key)
            device = RememberedDevice.query.filter_by(client_id=client.id).first()
            self.assertAlmostEqual((device.expires_at - utc_now()).days, 30, delta=1)

            # With a 7-day validity policy, a newly issued cookie lasts ~7 days.
            set_policy("remember_validity", scope=SCOPE.AUTH,
                       action=f"{PolicyAction.REMEMBER_DEVICE_VALIDITY}=7")
            other, other_key = create_client("validity client 2", "privacyidea-cp")
            self._check(other_key)
            device2 = RememberedDevice.query.filter_by(client_id=other.id).first()
            self.assertAlmostEqual((device2.expires_at - utc_now()).days, 7, delta=1)

            # The validity also takes a unit, like 8h
            set_policy("remember_validity", scope=SCOPE.AUTH,
                       action=f"{PolicyAction.REMEMBER_DEVICE_VALIDITY}=8h")
            third, third_key = create_client("validity client 3", "privacyidea-cp")
            res = self._check(third_key)
            device3 = RememberedDevice.query.filter_by(client_id=third.id).first()
            remaining = device3.expires_at - utc_now()
            self.assertGreater(remaining, timedelta(hours=7, minutes=59))
            self.assertLessEqual(remaining, timedelta(hours=8))
            # The cookie expires with the device
            max_age = int(re.search(r"Max-Age=(\d+)", self._cookies(res)[0]).group(1))
            self.assertGreater(max_age, 8 * 3600 - 60)
            self.assertLessEqual(max_age, 8 * 3600)
        finally:
            delete_policy("remember")
            try:
                delete_policy("remember_validity")
            except ResourceNotFoundError:
                pass

    def test_08_max_devices_caps_issuance(self):
        # remember_device_max_devices caps how many live devices a user may have
        # per client: once at the cap, opt-in issues no new cookie/row.
        client, api_key = create_client("cap client", "privacyidea-cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        set_policy("remember_max", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.REMEMBER_DEVICE_MAX_DEVICES}=1")
        try:
            # First opt-in issues a device.
            self.assertEqual(1, len(self._cookies(self._check(api_key))))
            self.assertEqual(1, RememberedDevice.query.filter_by(client_id=client.id).count())
            # Second opt-in for the same user+client is at the cap: no cookie, no new row.
            self.assertEqual([], self._cookies(self._check(api_key)))
            self.assertEqual(1, RememberedDevice.query.filter_by(client_id=client.id).count())
        finally:
            delete_policy("remember")
            delete_policy("remember_max")

    def test_09_idle_devices_are_removed_at_issuance(self):
        # A device not recognized within remember_device_idle_timeout is no longer recognized. An opt-in removes the
        # user's idle devices on the client before the cap is checked, so it issues a new device in place of the idle
        # one.
        client, api_key = create_client("idle cap client", "privacyidea-cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        set_policy("remember_max", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.REMEMBER_DEVICE_MAX_DEVICES}=1, "
                          f"{PolicyAction.REMEMBER_DEVICE_IDLE_TIMEOUT}=1h")
        try:
            self.assertEqual(1, len(self._cookies(self._check(api_key))))
            self.assertEqual([], self._cookies(self._check(api_key)))

            device = RememberedDevice.query.filter_by(client_id=client.id).first()
            device.created_at = utc_now() - timedelta(hours=2)
            device.save()
            idle_series_id = device.series_id
            self.assertEqual(1, len(self._cookies(self._check(api_key))))
            self.assertEqual(1, RememberedDevice.query.filter_by(client_id=client.id).count())
            self.assertIsNone(RememberedDevice.query.filter_by(series_id=idle_series_id).first())
        finally:
            delete_policy("remember")
            delete_policy("remember_max")

    def test_10_no_cookie_without_a_verified_token(self):
        # A remembered device stands for a token the user presented. A login that a policy accepts without verifying a
        # token gets no cookie: passOnNoToken, passthru to the user store and a credential served from the
        # authentication cache.
        client, api_key = create_client("token check client", "privacyidea-cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        self.addCleanup(delete_policy, "remember")
        for login in ("hans", "passthru"):
            remove_token(user=User(login, self.realm1))

        set_policy("no_token", scope=SCOPE.AUTH, action=PolicyAction.PASSONNOTOKEN)
        try:
            self.assertEqual([], self._cookies(self._check(api_key, user="hans", password="anything")))
        finally:
            delete_policy("no_token")

        set_policy("pass_thru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)
        try:
            self.assertEqual([], self._cookies(self._check(api_key, user="passthru", password="pthru")))
        finally:
            delete_policy("pass_thru")

        set_policy("cache", scope=SCOPE.AUTH, action=f"{PolicyAction.AUTH_CACHE}=4m")
        try:
            # The token verifies the first login, which puts the credential into the cache
            self._check(api_key, opt_in=False)
            res = self._check(api_key)
            self.assertIn("AuthCache", res.json["detail"]["message"])
            self.assertEqual([], self._cookies(res))
        finally:
            delete_policy("cache")

        self.assertIsNone(RememberedDevice.query.filter_by(client_id=client.id).first())


    def test_11_audit_says_what_came_of_the_requested_device(self):
        # When the client asks for a remembered device, the audit entry of /validate/check says whether one was issued
        # or why not. Without the request it says nothing about it.
        def action_detail():
            return self.find_most_recent_audit_entry(action="*validate/check*").get("action_detail") or ""

        client, api_key = create_client("audit issue client", "privacyidea-cp")
        self._check(api_key, opt_in=False)
        self.assertNotIn("remembered device", action_detail())

        self._check(api_key)
        self.assertIn("remembered device not issued: no remember_device policy applies to the user", action_detail())
        self._check(api_key=None)
        self.assertIn("remembered device not issued: no API client is identified by an X-API-Key header",
                      action_detail())

        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        set_policy("remember_max", scope=SCOPE.AUTH, action=f"{PolicyAction.REMEMBER_DEVICE_MAX_DEVICES}=1")
        self.addCleanup(delete_policy, "remember")
        self.addCleanup(delete_policy, "remember_max")
        self._check(api_key)
        device = RememberedDevice.query.filter_by(client_id=client.id).first()
        self.assertIn(f"remembered device issued, device id {device.device_id}, valid until ", action_detail())
        self._check(api_key)
        self.assertIn("remembered device not issued: the user has reached remember_device_max_devices (1) on this "
                      "client", action_detail())

        # Policies of the same priority that set different values name the conflict, not a storage failure
        set_policy("idle_long", scope=SCOPE.AUTH, action=f"{PolicyAction.REMEMBER_DEVICE_IDLE_TIMEOUT}=7d")
        set_policy("idle_short", scope=SCOPE.AUTH, action=f"{PolicyAction.REMEMBER_DEVICE_IDLE_TIMEOUT}=4h")
        try:
            self._check(api_key)
        finally:
            delete_policy("idle_long")
            delete_policy("idle_short")
        self.assertIn("remembered device not issued: There are policies with conflicting actions", action_detail())
        self.assertNotIn("storing it failed", action_detail())

        with patch("privacyidea.api.validate._resolve_persistent_cookie", side_effect=RuntimeError("database gone")):
            self._check(api_key)
        self.assertIn("remembered device not issued: storing it failed", action_detail())

        remove_token(user=User("hans", self.realm1))
        set_policy("no_token", scope=SCOPE.AUTH, action=PolicyAction.PASSONNOTOKEN)
        self.addCleanup(delete_policy, "no_token")
        self._check(api_key, user="hans", password="anything")
        self.assertIn("remembered device not issued: the login was accepted without a token", action_detail())

    def test_12_no_device_when_an_authorization_policy_refuses(self):
        # The device is issued after the authorization policies checked the authentication. A login they refuse
        # after the token was verified gets neither a cookie nor a stored device.
        client, api_key = create_client("refused client", "privacyidea-cp")
        set_policy("remember", scope=SCOPE.AUTH, action=PolicyAction.REMEMBER_DEVICE)
        self.addCleanup(delete_policy, "remember")
        for action in (f"{PolicyAction.TOKENTYPE}=hotp", f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}"):
            set_policy("refuse", scope=SCOPE.AUTHZ, action=action)
            try:
                with self.app.test_request_context('/validate/check', method='POST',
                                                   data={"user": "cornelius", "realm": self.realm1, "pass": "test",
                                                         "request_persistent_cookie": True},
                                                   headers={"X-API-Key": api_key}):
                    res = self.app.full_dispatch_request()
                self.assertFalse(res.json["result"].get("value"), res.json)
                self.assertEqual([], self._cookies(res), action)
                self.assertIsNone(RememberedDevice.query.filter_by(client_id=client.id).first(), action)
            finally:
                delete_policy("refuse")

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
        # A device is only recognised while the user has a usable token
        init_token({"type": "spass", "pin": "test", "serial": "SPASS_RECOGNISE"},
                   user=User(login="cornelius", realm=self.realm1))
        self.addCleanup(remove_token, "SPASS_RECOGNISE")

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
            # Recognition is not an authentication: the response carries no
            # result.authentication (ACCEPT/REJECT) - validity is result.value.
            self.assertNotIn("authentication", res.json['result'], res.json)
            return res

    def test_00_requires_api_client(self):
        # Without an X-API-Key header, g.client_id is None -> 401.
        with self.app.test_request_context('/validate/remember_device', method='POST',
                                           data={"user": "cornelius", "realm": self.realm1}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)

    def test_01_valid_cookie_is_rotated_and_recognised(self):
        client, api_key = create_client("consume client", "privacyidea-cp")
        device, cookie = create_remembered_device(self.identity, client.id)
        series = device.series_id

        res = self._recognise(api_key=api_key, cookie=cookie)
        # Cookie rotated to counter 2.
        headers = self._cookie_headers(res)
        self.assertEqual(1, len(headers), headers)
        self.assertIn(f"{PERSISTENT_COOKIE_NAME}={parse_cookie(cookie)[0]}:2", headers[0])
        # Counter incremented in the DB.
        self.assertEqual(2, RememberedDevice.query.filter_by(series_id=series).first().counter)

    def test_02_reused_cookie_invalidates_series(self):
        # Disable the grace window so replaying the previous counter is treated
        # strictly as reuse (with grace on it would be a tolerated duplicate).
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client, api_key = create_client("theft client", "privacyidea-cp")
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
        client, api_key = create_client("grace client", "privacyidea-cp")
        device, cookie = create_remembered_device(self.identity, client.id)
        series = device.series_id
        self._recognise(api_key=api_key, cookie=cookie)          # rotates to counter 2
        res = self._recognise(api_key=api_key, cookie=cookie)    # previous counter, within grace
        self.assertEqual([], self._cookie_headers(res))
        stored = RememberedDevice.query.filter_by(series_id=series).first()
        self.assertIsNotNone(stored)
        self.assertEqual(2, stored.counter)

    def test_03_wrong_client_cookie_not_honoured(self):
        client_a, _ = create_client("client A", "privacyidea-cp")
        _client_b, key_b = create_client("client B", "privacyidea-keycloak")
        device, cookie = create_remembered_device(self.identity, client_a.id)

        # Present A's cookie but as client B -> not matched.
        self._recognise(api_key=key_b, cookie=cookie, expect_value=False)
        # A's device is untouched (not rotated, not deleted).
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=device.series_id).first().counter)

    def test_04_no_cookie_reports_not_remembered(self):
        _client, api_key = create_client("plain client", "privacyidea-cp")
        res = self._recognise(api_key=api_key, expect_value=False)
        self.assertEqual([], self._cookie_headers(res))

    def test_05_recognition_is_audited(self):
        # A recognition is its own audit action and is recorded as a success,
        # but it is not an authentication (no ACCEPT/REJECT) and touches no token.
        client, api_key = create_client("audit recognise client", "privacyidea-cp")
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
            client, api_key = create_client("audit reuse client", "privacyidea-cp")
            _device, cookie = create_remembered_device(self.identity, client.id)
            self._recognise(api_key=api_key, cookie=cookie)                      # rotates to counter 2
            self._recognise(api_key=api_key, cookie=cookie, expect_value=False)  # stale counter 1 replayed

            entry = self.find_most_recent_audit_entry(action_detail="*persistent cookie reuse detected*")
            self.assertIn("persistent cookie reuse detected", entry.get("action_detail", ""))
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_06b_reuse_logs_event_and_revokes_every_device(self):
        # A stolen cookie means this user's browser is compromised, not just the
        # one series that got replayed: reuse is logged as DEVICE_TOKEN_REUSED
        # (so conditional access can lock the account, block the IP or notify),
        # and every one of the user's remembered devices, on every client, is
        # revoked - not just the replayed series.
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client, api_key = create_client("reuse escalation client", "privacyidea-cp")
            other_client, _other_key = create_client("other client", "privacyidea-keycloak")
            _device, cookie = create_remembered_device(self.identity, client.id)
            other_device, _other_cookie = create_remembered_device(self.identity, other_client.id)
            other_series_id = other_device.series_id

            logs_before = len(get_authentication_logs())
            self._recognise(api_key=api_key, cookie=cookie)                      # rotates to counter 2
            self._recognise(api_key=api_key, cookie=cookie, expect_value=False)  # stale counter 1 replayed -> theft

            entries = get_authentication_logs()[logs_before:]
            self.assertEqual([AuthEventType.DEVICE_TOKEN_REUSED],
                             [entry.event_type for entry in entries])

            # The other client's device for the same user is gone too, though it was never touched directly.
            self.assertIsNone(RememberedDevice.query.filter_by(series_id=other_series_id).first())
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_07_no_policy_means_no_recognition(self):
        # Without the remember_device policy, recognition is not offered: a valid
        # cookie reports "not remembered" and is left untouched (not consumed).
        delete_policy(self.POLICY)
        client, api_key = create_client("no policy consume", "privacyidea-cp")
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
        client, api_key = create_client("shared client", "privacyidea-cp")
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
        _client, api_key = create_client("clear client", "privacyidea-cp")
        res = self._recognise(api_key=api_key, cookie="doesnotexist:1", expect_value=False)
        self.assertTrue(any(h.startswith(f"{PERSISTENT_COOKIE_NAME}=;")
                            for h in self._cookie_headers(res)), self._cookie_headers(res))

    def test_09_unresolvable_user_not_recognized(self):
        # Recognition resolves the presented login to its stable identity before
        # matching. A login that does not resolve (e.g. a deleted/removed account)
        # yields no identity, so no remembered device is ever recognised for it -
        # deleting an account revokes its remembered devices.
        client, api_key = create_client("ghost client", "privacyidea-cp")
        device, cookie = create_remembered_device(self.identity, client.id)   # bound to cornelius
        # Present cornelius's cookie but as a non-existent user -> not recognised,
        # and cornelius's real device is never even reached, so it is untouched.
        self._recognise(api_key=api_key, cookie=cookie, user="ghost", expect_value=False)
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=device.series_id).first().counter)

    def test_11_idle_device_is_not_recognized(self):
        # A device not recognized within remember_device_idle_timeout is removed and its cookie cleared. A device
        # used within the timeout is recognized.
        set_policy("remember_idle", scope=SCOPE.AUTH, action=f"{PolicyAction.REMEMBER_DEVICE_IDLE_TIMEOUT}=1h")
        try:
            client, api_key = create_client("idle client", "privacyidea-cp")
            device, cookie = create_remembered_device(self.identity, client.id)
            device.created_at = utc_now() - timedelta(minutes=50)
            device.save()
            self._recognise(api_key=api_key, cookie=cookie)

            idle, idle_cookie = create_remembered_device(self.identity, client.id)
            idle_series = idle.series_id
            idle.created_at = utc_now() - timedelta(hours=2)
            idle.save()
            res = self._recognise(api_key=api_key, cookie=idle_cookie, expect_value=False)
            self.assertTrue(any(h.startswith(f"{PERSISTENT_COOKIE_NAME}=;")
                                for h in self._cookie_headers(res)), self._cookie_headers(res))
            self.assertIsNone(RememberedDevice.query.filter_by(series_id=idle_series).first())
        finally:
            delete_policy("remember_idle")

    def test_12_device_needs_a_usable_token(self):
        # While no token of the user could be used for a login, the device is not recognised. The cookie is neither
        # rotated nor cleared, so the device is recognised again once a token is usable.
        client, api_key = create_client("token state client", "privacyidea-cp")
        device, cookie = create_remembered_device(self.identity, client.id)
        stored_series_id = device.series_id

        enable_token("SPASS_RECOGNISE", False)
        res = self._recognise(api_key=api_key, cookie=cookie, expect_value=False)
        self.assertEqual([], self._cookie_headers(res))
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=stored_series_id).first().counter)
        entry = self.find_most_recent_audit_entry(action="*validate/remember_device*")
        self.assertEqual("device not recognised: the user has no usable token", entry["info"])

        enable_token("SPASS_RECOGNISE", True)
        res = self._recognise(api_key=api_key, cookie=cookie)
        self.assertEqual(1, len(self._cookie_headers(res)))
        self.assertEqual(2, RememberedDevice.query.filter_by(series_id=stored_series_id).first().counter)

    def test_12b_device_needs_a_token_the_policies_allow(self):
        # The token restrictions a login applies decide as well: while they allow none of the user's tokens, the
        # device is not recognised, the audit and the log name the policies, and the cookie is neither rotated nor
        # cleared. One allowed token of the user is enough.
        client, api_key = create_client("token policy client", "privacyidea-cp")
        device, cookie = create_remembered_device(self.identity, client.id)
        stored_series_id = device.series_id

        def recognise_with(scope: str, action: str, expect_value: bool) -> None:
            nonlocal cookie
            set_policy("token_restriction", scope=scope, action=action)
            try:
                if expect_value:
                    with self.assertNoLogs("privacyidea.api.validate", level="WARNING"):
                        res = self._recognise(api_key=api_key, cookie=cookie, expect_value=True)
                else:
                    with self.assertLogs("privacyidea.api.validate", level="WARNING") as logs:
                        res = self._recognise(api_key=api_key, cookie=cookie, expect_value=False)
            finally:
                delete_policy("token_restriction")
            if expect_value:
                cookie = self._cookie_headers(res)[0].split(";", 1)[0].split("=", 1)[1]
                return
            self.assertEqual([], self._cookie_headers(res), action)
            self.assertEqual("device not recognised: the policies token_restriction allow none of the user's tokens",
                             self.find_most_recent_audit_entry(action="*validate/remember_device*")["info"], action)
            self.assertTrue(any("the policies token_restriction allow none of the user's tokens" in line
                                for line in logs.output), logs.output)

        for scope, action in ((SCOPE.AUTH, f"{PolicyAction.DISABLED_TOKEN_TYPES}=spass"),
                              (SCOPE.AUTHZ, f"{PolicyAction.TOKENTYPE}=hotp"),
                              (SCOPE.AUTHZ, f"{PolicyAction.SERIAL}=^HOTP"),
                              (SCOPE.AUTHZ, f"{PolicyAction.TOKENINFO}=recognise/^yes$/")):
            recognise_with(scope, action, expect_value=False)
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=stored_series_id).first().counter)

        for scope, action in ((SCOPE.AUTH, f"{PolicyAction.DISABLED_TOKEN_TYPES}=hotp"),
                              (SCOPE.AUTHZ, f"{PolicyAction.TOKENTYPE}=spass"),
                              (SCOPE.AUTHZ, f"{PolicyAction.SERIAL}=^SPASS_")):
            recognise_with(scope, action, expect_value=True)

        # A second token the policy allows is enough
        init_token({"type": "hotp", "otpkey": "3132333435363738393031323334353637383930", "serial": "HOTP_RECOGNISE"},
                   user=User(login="cornelius", realm=self.realm1))
        self.addCleanup(remove_token, "HOTP_RECOGNISE")
        recognise_with(SCOPE.AUTHZ, f"{PolicyAction.TOKENTYPE}=hotp", expect_value=True)
        self.assertEqual(5, RememberedDevice.query.filter_by(series_id=stored_series_id).first().counter)

    def test_13_audit_names_the_reason(self):
        # The audit entry of a recognition says why a device was not recognised
        client, api_key = create_client("audit reason client", "privacyidea-cp")
        self._recognise(api_key=api_key, expect_value=False)
        self.assertEqual("device not recognised: no cookie presented",
                         self.find_most_recent_audit_entry(action="*validate/remember_device*")["info"])
        self._recognise(api_key=api_key, cookie="doesnotexist:1", expect_value=False)
        self.assertEqual("device not recognised: the cookie is unknown, expired or idle and is cleared",
                         self.find_most_recent_audit_entry(action="*validate/remember_device*")["info"])
        _device, cookie = create_remembered_device(self.identity, client.id)
        delete_policy(self.POLICY)
        self._recognise(api_key=api_key, cookie=cookie, expect_value=False)
        self.assertEqual("device not recognised: no remember_device policy applies to the user",
                         self.find_most_recent_audit_entry(action="*validate/remember_device*")["info"])
