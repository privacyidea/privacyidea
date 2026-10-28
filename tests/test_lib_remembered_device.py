from unittest.mock import patch

import privacyidea.lib.remembered_device as remembered_device_module
from .api_lib_policy_common import SSHKEY
from .base import MyTestCase
from .test_lib_tokens_certificate import CERT

from privacyidea.lib.clients import create_client
from privacyidea.lib.remembered_device import (parse_cookie, build_cookie_value,
                                         create_remembered_device, consume_remember_device_cookie,
                                         get_valid_device, user_identity, UserIdentity, rotate_device,
                                         cleanup_expired_remembered_devices, count_user_devices,
                                         hash_series_id, usable_tokens, parse_device_duration,
                                         remove_idle_devices,
                                         RESOLVER_MAX_LEN, USER_ID_MAX_LEN, MAX_DEVICE_VALIDITY_DAYS)
from privacyidea.lib.error import ParameterError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, delete_policy, get_policies, set_policy
from privacyidea.lib.realm import set_realm
from privacyidea.lib.serviceid import delete_serviceid, set_serviceid
from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config
from privacyidea.lib.token import enable_token, get_one_token, init_token, remove_token, revoke_token
from privacyidea.lib.tokenclass import DATE_FORMAT, FAILCOUNTER_CLEAR_TIMEOUT, FAILCOUNTER_EXCEEDED, RolloutState
from privacyidea.lib.user import User
from privacyidea.models import RememberedDevice, db
from privacyidea.models.utils import utc_now

from sqlalchemy import update

import hashlib
from datetime import datetime, timedelta, timezone


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
        client, _key = create_client("device client", "privacyidea-cp")
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
        device, _cookie = create_remembered_device(self._identity("cap"), client_id, validity=timedelta.max)
        days = (device.expires_at - utc_now()).days
        self.assertLessEqual(days, MAX_DEVICE_VALIDITY_DAYS)
        self.assertGreater(days, MAX_DEVICE_VALIDITY_DAYS - 2)

    def test_create_remembered_device(self):
        client_id = self._client_id()
        device, cookie = create_remembered_device(self._identity("alice"), client_id,
                                              ip_address="10.0.0.1", user_agent="curl")
        self.assertEqual(1, device.counter)
        series_id, counter = parse_cookie(cookie)
        self.assertEqual(1, counter)
        self.assertEqual(hash_series_id(series_id), device.series_id)
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
            device, cookie = create_remembered_device(self._identity("kim"), client_id)
        output = "\n".join(captured.output)
        self.assertNotIn(parse_cookie(cookie)[0], output)
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
            self.assertNotIn(parse_cookie(cookie)[0], "\n".join(captured.output))
            self.assertNotIn(device.series_id, "\n".join(captured.output))
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_consume_recognized_rotates(self):
        client_id = self._client_id()
        bob = self._identity("bob")
        device, cookie = create_remembered_device(bob, client_id)
        series_id, _counter = parse_cookie(cookie)
        stored_series_id = device.series_id

        result = consume_remember_device_cookie(cookie, client_id, bob)
        self.assertEqual("recognized", result.status)
        self.assertEqual(result.cookie_value, build_cookie_value(series_id, 2))
        self.assertEqual(result.expires_at, device.expires_at)

        stored = RememberedDevice.query.filter_by(series_id=stored_series_id).first()
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
        device, cookie = create_remembered_device(mallory, client_id)
        stored_series_id = device.series_id
        series_id, counter = parse_cookie(cookie)
        forged = build_cookie_value(series_id, counter + 1)
        self.assertEqual("theft", consume_remember_device_cookie(forged, client_id, mallory).status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=stored_series_id).first())

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
        # Until the device has been seen once there is no IP to bind to, so a previous-counter
        # duplicate is tolerated whatever its source: the window stays single-step and time-bounded.
        client_id = self._client_id()
        liam = self._identity("liam")
        device, cookie = create_remembered_device(liam, client_id)   # no ip_address recorded
        result = consume_remember_device_cookie(cookie, client_id, liam, "9.9.9.9")
        self.assertEqual("recognized", result.status)
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_grace_follows_the_device_as_it_moves(self):
        # A device keeps being used as its client changes network. The grace window compares against
        # where the device was last seen, not where it was first registered, so a duplicate from the
        # current network is tolerated. Binding to the registration address would make every benign
        # duplicate after a network change a detected theft - which revokes every device of that user.
        client_id = self._client_id()
        mia = self._identity("mia")
        device, cookie = create_remembered_device(mia, client_id, ip_address="10.0.0.1")
        rotated = consume_remember_device_cookie(cookie, client_id, mia, "203.0.113.7")
        self.assertEqual("recognized", rotated.status)
        # the duplicate of that request, from the same (new) network
        result = consume_remember_device_cookie(cookie, client_id, mia, "203.0.113.7")
        self.assertEqual("grace", result.status)
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_grace_is_refused_from_a_different_network(self):
        # The counterpart: once the device has been seen, a previous-counter presentation from
        # somewhere else is not a duplicate of the last request and stays a theft.
        client_id = self._client_id()
        noah = self._identity("noah")
        device, cookie = create_remembered_device(noah, client_id, ip_address="10.0.0.1")
        consume_remember_device_cookie(cookie, client_id, noah, "10.0.0.1")
        result = consume_remember_device_cookie(cookie, client_id, noah, "9.9.9.9")
        self.assertEqual("theft", result.status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_wrong_client_does_not_match(self):
        client_id_a = self._client_id()
        client_id_b = self._client_id()
        dave = self._identity("dave")
        device, cookie = create_remembered_device(dave, client_id_a)

        # A cookie issued for client A must not validate for client B.
        self.assertEqual("miss", consume_remember_device_cookie(cookie, client_id_b, dave).status)
        # ... and client A's device is untouched.
        self.assertEqual(1, RememberedDevice.query.filter_by(series_id=device.series_id).first().counter)

    def test_rotation_refuses_a_counter_another_request_moved(self):
        # rotate_device writes from the counter it validated. If another request moved the device in the
        # meantime, this one rotates nothing and says so, instead of overwriting that request's cookie.
        client_id = self._client_id()
        rose = self._identity("rose")
        device, cookie = create_remembered_device(rose, client_id, ip_address="10.0.0.1")
        loaded = get_valid_device(cookie, client_id, rose, "10.0.0.1").device
        db.session.expunge(loaded)
        # What a request that rotated the device first leaves behind
        db.session.execute(update(RememberedDevice)
                           .where(RememberedDevice.series_id == device.series_id)
                           .values(counter=loaded.counter + 1, last_used_at=utc_now()))
        db.session.commit()

        self.assertIsNone(rotate_device(loaded, "10.0.0.1"))

    def test_a_cookie_rotated_by_another_request_is_graced_or_reused(self):
        # The same situation through consume_remember_device_cookie: the presented cookie now carries the
        # previous counter, so it is answered as a later request with that cookie is.
        client_id = self._client_id()
        iris = self._identity("iris")
        device, cookie = create_remembered_device(iris, client_id, ip_address="10.0.0.1")
        self.assertEqual("recognized", consume_remember_device_cookie(cookie, client_id, iris, "10.0.0.1").status)

        # From the address the winner came from and within the window: a tolerated duplicate
        self.assertEqual("grace", consume_remember_device_cookie(cookie, client_id, iris, "10.0.0.1").status)
        # From anywhere else: reuse, and the series is gone
        self.assertEqual("theft", consume_remember_device_cookie(cookie, client_id, iris, "9.9.9.9").status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_a_lost_rotation_is_answered_like_a_later_request(self):
        """When another request rotated the device between the validation and the rotation, this one is
        answered the way a later request with the cookie it holds is: a tolerated duplicate, or a miss."""
        client_id = self._client_id()
        ada = self._identity("ada")
        _device, cookie = create_remembered_device(ada, client_id, ip_address="10.0.0.1")

        # Nothing moved the device, so re-validating finds the current one, which is not in grace
        with patch.object(remembered_device_module, "rotate_device", return_value=None):
            self.assertEqual("miss", consume_remember_device_cookie(cookie, client_id, ada, "10.0.0.1").status)

        # The race itself: the rotation this request lost is the one that happened, so re-validating finds
        # the cookie one counter behind - a duplicate of the request that won, from the same address.
        real_rotate = remembered_device_module.rotate_device

        def rotated_by_someone_else(device, client_ip=None):
            real_rotate(device, client_ip)
            return None

        with patch.object(remembered_device_module, "rotate_device", side_effect=rotated_by_someone_else):
            self.assertEqual("grace", consume_remember_device_cookie(cookie, client_id, ada, "10.0.0.1").status)

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

    def test_parse_device_duration(self):
        self.assertEqual(timedelta(days=30), parse_device_duration("30d"))
        self.assertEqual(timedelta(hours=8), parse_device_duration("8h"))
        self.assertEqual(timedelta(minutes=90), parse_device_duration("90m"))
        self.assertEqual(timedelta(seconds=45), parse_device_duration("45s"))
        self.assertEqual(timedelta(days=365), parse_device_duration("1y"))
        self.assertEqual(timedelta(hours=12), parse_device_duration(" 12h "))
        # A number without a unit counts as days
        self.assertEqual(timedelta(days=7), parse_device_duration("7"))
        # Empty, malformed, zero and negative values set no duration
        # A value with a space would be split into two values by the policy
        for value in (None, "", "   ", "abc", "5x", "h", "1.5h", "12H", "1d12h", "8 h", "0", "0h", "-5d", "+-5d"):
            self.assertIsNone(parse_device_duration(value), value)
        # A duration is at most MAX_DEVICE_VALIDITY_DAYS, also one too large for a timedelta
        max_duration = timedelta(days=MAX_DEVICE_VALIDITY_DAYS)
        self.assertEqual(max_duration, parse_device_duration(f"{MAX_DEVICE_VALIDITY_DAYS + 1}d"))
        self.assertEqual(max_duration, parse_device_duration("99999999999y"))
        self.assertEqual(max_duration, parse_device_duration("99999999999"))

    def test_validity_sets_the_expiry(self):
        client_id = self._client_id()
        device, _cookie = create_remembered_device(self._identity("olga"), client_id, validity=timedelta(hours=8))
        remaining = device.expires_at - utc_now()
        self.assertGreater(remaining, timedelta(hours=7, minutes=59))
        self.assertLessEqual(remaining, timedelta(hours=8))

    def test_stores_the_digest_of_the_series_id(self):
        # The cookie carries the series id, the table only its SHA-256 hex digest
        client_id = self._client_id()
        device, cookie = create_remembered_device(self._identity("paul"), client_id)
        series_id, _counter = parse_cookie(cookie)
        self.assertEqual(hashlib.sha256(series_id.encode("utf-8")).hexdigest(), device.series_id)
        self.assertEqual(64, len(device.series_id))
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=series_id).first())
        # A cookie carrying the stored value instead of the series id is not recognised
        self.assertEqual("miss", consume_remember_device_cookie(build_cookie_value(device.series_id, 1), client_id,
                                                                self._identity("paul")).status)

    def test_idle_device_is_removed(self):
        client_id = self._client_id()
        quinn = self._identity("quinn")
        device, cookie = create_remembered_device(quinn, client_id)
        stored_series_id = device.series_id
        rotated = consume_remember_device_cookie(cookie, client_id, quinn)
        stored = RememberedDevice.query.filter_by(series_id=stored_series_id).first()
        stored.last_used_at = utc_now() - timedelta(hours=2)
        stored.save()

        result = consume_remember_device_cookie(rotated.cookie_value, client_id, quinn,
                                                idle_timeout=timedelta(hours=1))
        self.assertEqual("miss", result.status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=stored_series_id).first())

    def test_idle_timeout_counts_from_the_creation_of_an_unused_device(self):
        client_id = self._client_id()
        ruth = self._identity("ruth")
        device, cookie = create_remembered_device(ruth, client_id)
        stored_series_id = device.series_id
        device.created_at = utc_now() - timedelta(hours=2)
        device.save()

        self.assertEqual("miss", consume_remember_device_cookie(cookie, client_id, ruth,
                                                                idle_timeout=timedelta(hours=1)).status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=stored_series_id).first())

    def test_device_used_within_the_idle_timeout_is_recognized(self):
        # Each recognition starts the idle timeout again, while the expiry stays where it was
        client_id = self._client_id()
        sam = self._identity("sam")
        device, cookie = create_remembered_device(sam, client_id)
        expires_at = device.expires_at
        device.created_at = utc_now() - timedelta(minutes=50)
        device.save()

        result = consume_remember_device_cookie(cookie, client_id, sam, idle_timeout=timedelta(hours=1))
        self.assertEqual("recognized", result.status)
        self.assertEqual(expires_at, result.expires_at)
        result = consume_remember_device_cookie(result.cookie_value, client_id, sam, idle_timeout=timedelta(hours=1))
        self.assertEqual("recognized", result.status)

    def test_replay_on_an_idle_device_is_theft(self):
        # An outdated counter is reported as a replay before the idle timeout is looked at
        client_id = self._client_id()
        uma = self._identity("uma")
        device, cookie = create_remembered_device(uma, client_id)
        stored_series_id = device.series_id
        consume_remember_device_cookie(cookie, client_id, uma)   # -> counter 2
        stored = RememberedDevice.query.filter_by(series_id=stored_series_id).first()
        stored.last_used_at = utc_now() - timedelta(hours=2)
        stored.save()

        result = consume_remember_device_cookie(cookie, client_id, uma, idle_timeout=timedelta(hours=1))
        self.assertEqual("theft", result.status)
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=stored_series_id).first())

    def test_remove_idle_devices(self):
        # Only the idle devices of this user on this client are removed
        client_id = self._client_id()
        other_client_id = self._client_id()
        tara = self._identity("tara")
        idle, _cookie = create_remembered_device(tara, client_id)
        idle.created_at = utc_now() - timedelta(hours=2)
        idle.save()
        idle_series_id = idle.series_id
        used, _cookie = create_remembered_device(tara, client_id)
        used.created_at = utc_now() - timedelta(hours=2)
        used.last_used_at = utc_now() - timedelta(minutes=10)
        used.save()
        fresh, _cookie = create_remembered_device(tara, client_id)
        other_user, _cookie = create_remembered_device(self._identity("ulf"), client_id)
        other_client, _cookie = create_remembered_device(tara, other_client_id)
        for device in (other_user, other_client):
            device.created_at = utc_now() - timedelta(hours=2)
            device.save()
        kept = {used.series_id, fresh.series_id, other_user.series_id, other_client.series_id}

        self.assertEqual(1, remove_idle_devices(client_id, tara, timedelta(hours=1)))
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=idle_series_id).first())
        self.assertEqual(kept, {device.series_id for device in RememberedDevice.query.filter(
            RememberedDevice.series_id.in_(kept)).all()})
        self.assertEqual(2, count_user_devices(client_id, tara.resolver, tara.user_id, tara.realm_id))

    def test_duration_policy_values_are_checked_when_saved(self):
        self.addCleanup(lambda: delete_policy("duration_check") if get_policies(name="duration_check") else None)
        for action in (PolicyAction.REMEMBER_DEVICE_VALIDITY, PolicyAction.REMEMBER_DEVICE_IDLE_TIMEOUT):
            for value in ("8h", "30", "90m"):
                set_policy("duration_check", scope=SCOPE.AUTH, action=f"{action}={value}")
            for value in ("12H", "1d12h", "1.5d", "8 h", "0", "-5d"):
                with self.assertRaises(ParameterError, msg=f"{action}={value}"):
                    set_policy("duration_check", scope=SCOPE.AUTH, action=f"{action}={value}")
            with self.assertRaises(ParameterError):
                set_policy("duration_check", scope=SCOPE.AUTH, action=action)

    def test_usable_tokens(self):
        # The checks a login applies to each token decide whether the user still has a usable token
        user = User(login="cornelius", realm=self.realm1)
        remove_token(user=user)
        self.assertFalse(usable_tokens(user))

        init_token({"type": "spass", "pin": "test", "serial": "USABLE_1"}, user=user)
        self.addCleanup(remove_token, "USABLE_1")
        self.assertTrue(usable_tokens(user))

        enable_token("USABLE_1", False)
        self.assertFalse(usable_tokens(user))
        enable_token("USABLE_1", True)

        token = get_one_token(serial="USABLE_1")
        token.set_validity_period_end("2020-01-01T00:00+0000")
        self.assertFalse(usable_tokens(user))
        token.set_validity_period_end("")
        self.assertTrue(usable_tokens(user))

        token.token.rollout_state = RolloutState.CLIENTWAIT
        token.token.save()
        self.assertFalse(usable_tokens(user))
        token.token.rollout_state = ""
        token.token.save()

        token.token.failcount = token.token.maxfail
        token.token.save()
        self.assertFalse(usable_tokens(user))

        # Only the usable one of the user's tokens is returned
        init_token({"type": "spass", "pin": "test", "serial": "USABLE_2"}, user=user)
        self.addCleanup(remove_token, "USABLE_2")
        self.assertEqual(["USABLE_2"], [usable.get_serial() for usable in usable_tokens(user)])
        revoke_token("USABLE_2")
        self.assertFalse(usable_tokens(user))

    def test_usable_tokens_clears_an_expired_fail_counter(self):
        # Like a login, the check first clears a fail counter whose clear timeout has passed
        user = User(login="cornelius", realm=self.realm1)
        remove_token(user=user)
        init_token({"type": "spass", "pin": "test", "serial": "USABLE_FAIL"}, user=user)
        self.addCleanup(remove_token, "USABLE_FAIL")
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 1)
        self.addCleanup(delete_privacyidea_config, FAILCOUNTER_CLEAR_TIMEOUT)
        token = get_one_token(serial="USABLE_FAIL")
        token.set_maxfail(5)
        token.set_failcount(5)
        exceeded_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        token.write_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_at.strftime(DATE_FORMAT))
        self.assertTrue(usable_tokens(user))
        self.assertEqual(0, get_one_token(serial="USABLE_FAIL").token.failcount)

    def test_usable_tokens_skip_a_revoked_token_with_an_expired_fail_counter(self):
        # A revoked token is locked, so its fail counter is not cleared - it is skipped instead of raising
        user = User(login="cornelius", realm=self.realm1)
        remove_token(user=user)
        init_token({"type": "spass", "pin": "test", "serial": "REVOKED_FAIL"}, user=user)
        self.addCleanup(remove_token, "REVOKED_FAIL")
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 1)
        self.addCleanup(delete_privacyidea_config, FAILCOUNTER_CLEAR_TIMEOUT)
        token = get_one_token(serial="REVOKED_FAIL")
        token.set_maxfail(5)
        token.set_failcount(5)
        exceeded_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        token.write_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_at.strftime(DATE_FORMAT))
        revoke_token("REVOKED_FAIL")
        self.assertFalse(usable_tokens(user))
        self.assertEqual(5, get_one_token(serial="REVOKED_FAIL").token.failcount)

        # The user's other, usable token still counts
        init_token({"type": "spass", "pin": "test", "serial": "USABLE_AFTER_REVOKED"}, user=user)
        self.addCleanup(remove_token, "USABLE_AFTER_REVOKED")
        self.assertEqual(["USABLE_AFTER_REVOKED"], [usable.get_serial() for usable in usable_tokens(user)])

    def test_usable_tokens_skip_tokens_that_cannot_log_in(self):
        # An SSH key or a certificate cannot verify a login, and an application-specific password is not used by a
        # login without a service_id - none of them counts
        user = User(login="cornelius", realm=self.realm1)
        remove_token(user=user)
        init_token({"type": "sshkey", "sshkey": SSHKEY, "serial": "NO_LOGIN_SSH"}, user=user)
        self.addCleanup(remove_token, "NO_LOGIN_SSH")
        init_token({"type": "certificate", "certificate": CERT, "serial": "NO_LOGIN_CERT"}, user=user)
        self.addCleanup(remove_token, "NO_LOGIN_CERT")
        set_serviceid("remembered_device_service")
        self.addCleanup(delete_serviceid, "remembered_device_service")
        init_token({"type": "applspec", "service_id": "remembered_device_service", "otpkey": "applspec1234",
                    "serial": "NO_LOGIN_APPLSPEC"}, user=user)
        self.addCleanup(remove_token, "NO_LOGIN_APPLSPEC")
        self.assertEqual([], usable_tokens(user))

        init_token({"type": "spass", "pin": "test", "serial": "LOGIN_SPASS"}, user=user)
        self.addCleanup(remove_token, "LOGIN_SPASS")
        self.assertEqual(["LOGIN_SPASS"], [usable.get_serial() for usable in usable_tokens(user)])
