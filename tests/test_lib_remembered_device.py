from .base import MyTestCase

from privacyidea.lib.clients import create_client
from privacyidea.lib.remembered_device import (parse_cookie, build_cookie_value,
                                         create_remembered_device, consume_remember_device_cookie,
                                         get_valid_device, user_identity, UserIdentity,
                                         cleanup_expired_remembered_devices,
                                         RESOLVER_MAX_LEN, USER_ID_MAX_LEN, MAX_DEVICE_VALIDITY_DAYS)
from privacyidea.lib.realm import set_realm
from privacyidea.lib.user import User
from privacyidea.models import RememberedDevice
from privacyidea.models.utils import utc_now

from datetime import timedelta


class RememberedDeviceLibTestCase(MyTestCase):
    """
    Order-independent: every test creates its own client and device. Devices
    are bound to the resolver-stable identity (resolver, user_id, realm_id), so a
    real realm is set up to supply a valid realm_id; the ``user_id`` values are
    arbitrary resolver ids (the cookie mechanics never resolve them).
    """

    def setUp(self):
        self.setUp_user_realms()
        self.realm_id = User(login="cornelius", realm=self.realm1).realm_id

    def _client_id(self):
        client, _key = create_client("device client", "windows_cp")
        return client.id

    def _identity(self, user_id, resolver=None, realm_id=None):
        return UserIdentity(resolver or self.resolvername1, user_id,
                            realm_id if realm_id is not None else self.realm_id)

    def test_parse_cookie(self):
        self.assertEqual(("abc", 5), parse_cookie("abc:5"))
        # series ids from token_urlsafe may contain - and _ but never ':'
        self.assertEqual(("aB-c_d", 42), parse_cookie("aB-c_d:42"))
        # malformed
        self.assertEqual((None, None), parse_cookie(""))
        self.assertEqual((None, None), parse_cookie(None))
        self.assertEqual((None, None), parse_cookie("noseparator"))
        self.assertEqual((None, None), parse_cookie("series:notanumber"))
        self.assertEqual((None, None), parse_cookie(":5"))
        # an embedded colon in the counter half is not a valid integer
        self.assertEqual((None, None), parse_cookie("series:1:2"))

    def test_user_identity(self):
        # A resolvable user maps to the (resolver, uid, realm_id) triple - the
        # resolver-stable identity, not the login.
        user = User(login="cornelius", realm=self.realm1)
        identity = user_identity(user)
        self.assertEqual(user.resolver, identity.resolver)
        self.assertEqual(str(user.uid), identity.user_id)
        self.assertEqual(user.realm_id, identity.realm_id)
        # No resolvable user -> no identity to bind to.
        self.assertIsNone(user_identity(None))
        self.assertIsNone(user_identity(User()))

    def test_user_identity_rejects_overlong(self):
        # The identity is a lookup key stored verbatim; one that would overflow
        # its column yields no identity (so no unmatchable cookie is issued).
        long_uid = User(login="cornelius", realm=self.realm1)
        long_uid.uid = "x" * (USER_ID_MAX_LEN + 1)
        self.assertIsNone(user_identity(long_uid))
        long_resolver = User(login="cornelius", realm=self.realm1)
        long_resolver.resolver = "y" * (RESOLVER_MAX_LEN + 1)
        self.assertIsNone(user_identity(long_resolver))

    def test_validity_is_capped(self):
        # An absurd validity must not overflow timedelta (which would 500 the
        # auth); it is capped at MAX_DEVICE_VALIDITY_DAYS.
        client_id = self._client_id()
        device, _cookie = create_remembered_device(self._identity("cap"), client_id, validity_days=10 ** 12)
        days = (device.expires_at - utc_now()).days
        self.assertLessEqual(days, MAX_DEVICE_VALIDITY_DAYS)
        self.assertGreater(days, MAX_DEVICE_VALIDITY_DAYS - 2)

    def test_create_remembered_device(self):
        client_id = self._client_id()
        device, cookie = create_remembered_device(self._identity("alice"), client_id,
                                              ip_address="10.0.0.1", user_agent="curl")
        self.assertEqual(1, device.counter)
        self.assertEqual(cookie, build_cookie_value(device.series_id, 1))
        # The device is bound to the full resolver-stable identity.
        self.assertEqual(self.resolvername1, device.resolver)
        self.assertEqual("alice", device.user_id)
        self.assertEqual(self.realm_id, device.realm_id)
        self.assertEqual(device.client_id, client_id)
        # 30 day default validity
        self.assertGreater(device.expires_at, utc_now() + timedelta(days=29))

    def test_series_id_is_not_logged(self):
        # The series_id is the secret half of the remember-device cookie. It must
        # not be written to the DEBUG log (log_with redacts it via the denylist),
        # or the log would contain a replayable bearer token.
        client_id = self._client_id()
        with self.assertLogs("privacyidea.models.remembered_device", level="DEBUG") as captured:
            device, _cookie = create_remembered_device(self._identity("kim"), client_id)
        output = "\n".join(captured.output)
        self.assertNotIn(device.series_id, output)
        self.assertIn("HIDDEN", output)

    def test_theft_log_does_not_leak_series_id(self):
        # The series_id is the secret half of the cookie. The theft/replay log
        # path must not write it verbatim - the SENSITIVE_KEY_NAMES redaction only
        # covers structured keys, not f-string messages.
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client_id = self._client_id()
            nemo = self._identity("nemo")
            device, cookie = create_remembered_device(nemo, client_id)
            consume_remember_device_cookie(cookie, client_id, nemo)   # -> counter 2
            with self.assertLogs("privacyidea.lib.remembered_device", level="DEBUG") as captured:
                consume_remember_device_cookie(cookie, client_id, nemo)   # replay -> theft
            self.assertNotIn(device.series_id, "\n".join(captured.output))
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_consume_recognized_rotates(self):
        client_id = self._client_id()
        bob = self._identity("bob")
        device, cookie = create_remembered_device(bob, client_id)
        series_id = device.series_id

        result = consume_remember_device_cookie(cookie, client_id, bob)
        self.assertEqual("recognized", result.status)
        self.assertEqual(result.cookie_value, build_cookie_value(series_id, 2))
        self.assertEqual(result.expires_at, device.expires_at)

        stored = RememberedDevice.query.filter_by(series_id=series_id).first()
        self.assertEqual(2, stored.counter)
        self.assertIsNotNone(stored.last_used_at)

        # The rotated cookie is recognised again, bumping to 3.
        again = consume_remember_device_cookie(result.cookie_value, client_id, bob)
        self.assertEqual(again.cookie_value, build_cookie_value(series_id, 3))

    def test_wrong_user_does_not_match(self):
        # A cookie is bound to the user it was issued for; another user of the
        # same client presenting it does not validate (get_valid_device returns
        # None) - but since the series is live for someone else on this client it
        # is a "foreign" soft miss (not recognised, must not be cleared), not a
        # dead "miss".
        client_id = self._client_id()
        _device, cookie = create_remembered_device(self._identity("frank"), client_id)
        eve = self._identity("eve")
        self.assertIsNone(get_valid_device(cookie, client_id, eve))
        self.assertEqual("foreign", consume_remember_device_cookie(cookie, client_id, eve).status)

    def test_cross_realm_does_not_match(self):
        # The realm is part of the identity: the same resolver + user_id in a
        # *different* realm must not be recognised, so a device remembered in one
        # realm is not honoured in another. The series stays live for its own
        # realm (a soft "foreign" miss), so it is not cleared.
        set_realm("realm_other", [{"name": self.resolvername1}])
        other_realm_id = User(login="cornelius", realm="realm_other").realm_id
        self.assertNotEqual(self.realm_id, other_realm_id)
        client_id = self._client_id()
        device, cookie = create_remembered_device(self._identity("cornelius"), client_id)
        other = self._identity("cornelius", realm_id=other_realm_id)
        self.assertEqual("foreign", consume_remember_device_cookie(cookie, client_id, other).status)
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_theft_detection_deletes_series(self):
        client_id = self._client_id()
        carol = self._identity("carol")
        device, cookie = create_remembered_device(carol, client_id)
        series_id = device.series_id

        # Advance the counter twice so the original cookie is two steps stale
        # (beyond the single-step grace window).
        rotated = consume_remember_device_cookie(cookie, client_id, carol)       # -> counter 2
        consume_remember_device_cookie(rotated.cookie_value, client_id, carol)   # -> counter 3

        # Replaying the original counter=1 cookie (two behind) is theft: reported
        # as "theft" (not raised) and the whole series is gone.
        self.assertEqual("theft", consume_remember_device_cookie(cookie, client_id, carol).status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=series_id).first())

    def test_forged_higher_counter_is_theft(self):
        # An attacker holding the current cookie cannot mint a "fresh" one by
        # incrementing the counter: a counter ahead of the stored value is not a
        # valid rotation, it is treated as theft and destroys the series.
        client_id = self._client_id()
        mallory = self._identity("mallory")
        device, _cookie = create_remembered_device(mallory, client_id)
        series_id = device.series_id
        forged = build_cookie_value(series_id, device.counter + 1)
        self.assertEqual("theft", consume_remember_device_cookie(forged, client_id, mallory).status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=series_id).first())

    def test_grace_allows_previous_counter_without_rotating(self):
        client_id = self._client_id()
        gina = self._identity("gina")
        device, cookie = create_remembered_device(gina, client_id)
        # Rotate to counter 2.
        consume_remember_device_cookie(cookie, client_id, gina)
        # A concurrent request still presenting counter 1 (the previous one) is
        # tolerated within the grace window: recognised as a grace hit, no new
        # cookie handed out, and the series is neither rotated nor deleted.
        result = consume_remember_device_cookie(cookie, client_id, gina)
        self.assertEqual("grace", result.status)
        self.assertIsNone(result.cookie_value)
        stored = RememberedDevice.query.filter_by(series_id=device.series_id).first()
        self.assertIsNotNone(stored)
        self.assertEqual(2, stored.counter)

    def test_grace_disabled_treats_previous_counter_as_theft(self):
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client_id = self._client_id()
            hank = self._identity("hank")
            device, cookie = create_remembered_device(hank, client_id)
            consume_remember_device_cookie(cookie, client_id, hank)   # -> counter 2
            self.assertEqual("theft", consume_remember_device_cookie(cookie, client_id, hank).status)
            self.assertIsNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_grace_requires_matching_ip(self):
        client_id = self._client_id()
        iris = self._identity("iris")
        device, cookie = create_remembered_device(iris, client_id, ip_address="10.0.0.1")
        consume_remember_device_cookie(cookie, client_id, iris, "10.0.0.1")   # -> counter 2
        # Presenting the previous counter from a different IP is not a tolerated
        # concurrent request -> theft.
        self.assertEqual("theft", consume_remember_device_cookie(cookie, client_id, iris, "9.9.9.9").status)

    def test_grace_window_expires_and_previous_counter_becomes_theft(self):
        # The grace window is a short time window, not a standing exemption: the
        # previous counter presented from the same IP but after the window has
        # elapsed is theft, not a tolerated duplicate.
        client_id = self._client_id()
        kate = self._identity("kate")
        device, cookie = create_remembered_device(kate, client_id, ip_address="10.0.0.1")
        consume_remember_device_cookie(cookie, client_id, kate, "10.0.0.1")   # -> counter 2
        # Age the last use well beyond the (default 10s) grace window.
        stored = RememberedDevice.query.filter_by(series_id=device.series_id).first()
        stored.last_used_at = utc_now() - timedelta(hours=1)
        stored.save()
        self.assertEqual("theft", consume_remember_device_cookie(cookie, client_id, kate, "10.0.0.1").status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_grace_without_stored_ip_is_not_ip_bound(self):
        # When the device has no recorded source IP, the grace window cannot be
        # IP-bound, so a previous-counter duplicate is tolerated regardless of the
        # request IP (it stays single-step and time-bounded). This pins that IP is
        # only enforced when it is actually known.
        client_id = self._client_id()
        liam = self._identity("liam")
        device, cookie = create_remembered_device(liam, client_id)   # no ip_address recorded
        consume_remember_device_cookie(cookie, client_id, liam, "10.0.0.1")   # -> counter 2
        result = consume_remember_device_cookie(cookie, client_id, liam, "9.9.9.9")
        self.assertEqual("grace", result.status)
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_wrong_client_does_not_match(self):
        client_id_a = self._client_id()
        client_id_b = self._client_id()
        dave = self._identity("dave")
        device, cookie = create_remembered_device(dave, client_id_a)

        # A cookie issued for client A must not validate for client B.
        self.assertEqual("miss", consume_remember_device_cookie(cookie, client_id_b, dave).status)
        # ... and client A's device is untouched.
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=device.series_id).first().counter)

    def test_unknown_series_returns_miss(self):
        client_id = self._client_id()
        self.assertEqual("miss", consume_remember_device_cookie("doesnotexist:1", client_id,
                                                                self._identity("x")).status)

    def test_expired_device_is_removed(self):
        client_id = self._client_id()
        erin = self._identity("erin")
        device, cookie = create_remembered_device(erin, client_id)
        series_id = device.series_id
        device.expires_at = utc_now() - timedelta(seconds=1)
        device.save()

        self.assertEqual("miss", consume_remember_device_cookie(cookie, client_id, erin).status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=series_id).first())

    def test_cleanup_expired_remembered_devices(self):
        # The periodic cleanup reclaims expired rows (which are otherwise only
        # deleted lazily when their own cookie is presented) and leaves live
        # devices untouched.
        client_id = self._client_id()
        expired, _ = create_remembered_device(self._identity("jane"), client_id)
        expired.expires_at = utc_now() - timedelta(seconds=1)
        expired.save()
        live, _ = create_remembered_device(self._identity("john"), client_id)
        # Capture ids before the delete+commit expires the ORM instances.
        expired_series = expired.series_id
        live_series = live.series_id

        deleted = cleanup_expired_remembered_devices()
        self.assertGreaterEqual(deleted, 1)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=expired_series).first())
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=live_series).first())
