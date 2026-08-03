from .base import MyTestCase

from privacyidea.lib.clients import create_client
from privacyidea.lib.authsession import (parse_cookie, build_cookie_value,
                                         create_auth_session, consume_remember_device_cookie,
                                         get_valid_session, session_user_id,
                                         cleanup_expired_auth_sessions)
from privacyidea.models import AuthSession
from privacyidea.models.utils import utc_now

from datetime import timedelta


class _FakeUser:
    def __init__(self, login, realm):
        self.login = login
        self.realm = realm


class AuthSessionLibTestCase(MyTestCase):
    """
    Order-independent: every test creates its own client and session.
    """

    def _client_id(self):
        client, _key = create_client("session client", "windows_cp")
        return client.id

    def test_parse_cookie(self):
        self.assertEqual(parse_cookie("abc:5"), ("abc", 5))
        # series ids from token_urlsafe may contain - and _ but never ':'
        self.assertEqual(parse_cookie("aB-c_d:42"), ("aB-c_d", 42))
        # malformed
        self.assertEqual(parse_cookie(""), (None, None))
        self.assertEqual(parse_cookie(None), (None, None))
        self.assertEqual(parse_cookie("noseparator"), (None, None))
        self.assertEqual(parse_cookie("series:notanumber"), (None, None))
        self.assertEqual(parse_cookie(":5"), (None, None))

    def test_session_user_id(self):
        self.assertEqual(session_user_id(_FakeUser("alice", "realm1")), "alice@realm1")
        self.assertIsNone(session_user_id(None))
        self.assertIsNone(session_user_id(_FakeUser("", "realm1")))

    def test_create_auth_session(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("alice", client_id,
                                              ip_address="10.0.0.1", user_agent="curl")
        self.assertEqual(session.counter, 1)
        self.assertEqual(cookie, build_cookie_value(session.series_id, 1))
        self.assertEqual(session.user_id, "alice")
        self.assertEqual(session.client_id, client_id)
        # 30 day default validity
        self.assertGreater(session.expires_at, utc_now() + timedelta(days=29))

    def test_series_id_is_not_logged(self):
        # The series_id is the secret half of the remember-device cookie. It must
        # not be written to the DEBUG log (log_with redacts it via the denylist),
        # or the log would contain a replayable bearer token.
        client_id = self._client_id()
        with self.assertLogs("privacyidea.models.authsession", level="DEBUG") as captured:
            session, _cookie = create_auth_session("kim", client_id)
        output = "\n".join(captured.output)
        self.assertNotIn(session.series_id, output)
        self.assertIn("HIDDEN", output)

    def test_consume_recognized_rotates(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("bob", client_id)
        series_id = session.series_id

        result = consume_remember_device_cookie(cookie, client_id, "bob")
        self.assertEqual(result.status, "recognized")
        self.assertEqual(result.cookie_value, build_cookie_value(series_id, 2))
        self.assertEqual(result.expires_at, session.expires_at)

        stored = AuthSession.query.filter_by(series_id=series_id).first()
        self.assertEqual(stored.counter, 2)
        self.assertIsNotNone(stored.last_used_at)

        # The rotated cookie is recognised again, bumping to 3.
        again = consume_remember_device_cookie(result.cookie_value, client_id, "bob")
        self.assertEqual(again.cookie_value, build_cookie_value(series_id, 3))

    def test_wrong_user_does_not_match(self):
        # A cookie is bound to the user it was issued for; another user of the
        # same client presenting it does not validate (get_valid_session returns
        # None) - but since the series is live for someone else on this client it
        # is a "foreign" soft miss (not recognised, must not be cleared), not a
        # dead "miss".
        client_id = self._client_id()
        _session, cookie = create_auth_session("frank", client_id)
        self.assertIsNone(get_valid_session(cookie, client_id, "eve"))
        self.assertEqual(consume_remember_device_cookie(cookie, client_id, "eve").status, "foreign")

    def test_theft_detection_deletes_series(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("carol", client_id)
        series_id = session.series_id

        # Advance the counter twice so the original cookie is two steps stale
        # (beyond the single-step grace window).
        rotated = consume_remember_device_cookie(cookie, client_id, "carol")       # -> counter 2
        consume_remember_device_cookie(rotated.cookie_value, client_id, "carol")   # -> counter 3

        # Replaying the original counter=1 cookie (two behind) is theft: reported
        # as "theft" (not raised) and the whole series is gone.
        self.assertEqual(consume_remember_device_cookie(cookie, client_id, "carol").status, "theft")
        self.assertIsNone(AuthSession.query.filter_by(series_id=series_id).first())

    def test_grace_allows_previous_counter_without_rotating(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("gina", client_id)
        # Rotate to counter 2.
        consume_remember_device_cookie(cookie, client_id, "gina")
        # A concurrent request still presenting counter 1 (the previous one) is
        # tolerated within the grace window: recognised as a grace hit, no new
        # cookie handed out, and the series is neither rotated nor deleted.
        result = consume_remember_device_cookie(cookie, client_id, "gina")
        self.assertEqual(result.status, "grace")
        self.assertIsNone(result.cookie_value)
        stored = AuthSession.query.filter_by(series_id=session.series_id).first()
        self.assertIsNotNone(stored)
        self.assertEqual(stored.counter, 2)

    def test_grace_disabled_treats_previous_counter_as_theft(self):
        self.app.config["PI_REMEMBER_DEVICE_GRACE_SECONDS"] = 0
        try:
            client_id = self._client_id()
            session, cookie = create_auth_session("hank", client_id)
            consume_remember_device_cookie(cookie, client_id, "hank")   # -> counter 2
            self.assertEqual(consume_remember_device_cookie(cookie, client_id, "hank").status, "theft")
            self.assertIsNone(AuthSession.query.filter_by(series_id=session.series_id).first())
        finally:
            self.app.config.pop("PI_REMEMBER_DEVICE_GRACE_SECONDS", None)

    def test_grace_requires_matching_ip(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("iris", client_id, ip_address="10.0.0.1")
        consume_remember_device_cookie(cookie, client_id, "iris", "10.0.0.1")   # -> counter 2
        # Presenting the previous counter from a different IP is not a tolerated
        # concurrent request -> theft.
        self.assertEqual(consume_remember_device_cookie(cookie, client_id, "iris", "9.9.9.9").status,
                         "theft")

    def test_wrong_client_does_not_match(self):
        client_id_a = self._client_id()
        client_id_b = self._client_id()
        session, cookie = create_auth_session("dave", client_id_a)

        # A cookie issued for client A must not validate for client B.
        self.assertEqual(consume_remember_device_cookie(cookie, client_id_b, "dave").status, "miss")
        # ... and client A's session is untouched.
        self.assertEqual(AuthSession.query.filter_by(series_id=session.series_id).first().counter, 1)

    def test_unknown_series_returns_miss(self):
        client_id = self._client_id()
        self.assertEqual(consume_remember_device_cookie("doesnotexist:1", client_id, "x").status, "miss")

    def test_expired_session_is_removed(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("erin", client_id)
        series_id = session.series_id
        session.expires_at = utc_now() - timedelta(seconds=1)
        session.save()

        self.assertEqual(consume_remember_device_cookie(cookie, client_id, "erin").status, "miss")
        self.assertIsNone(AuthSession.query.filter_by(series_id=series_id).first())

    def test_cleanup_expired_auth_sessions(self):
        # The periodic cleanup reclaims expired rows (which are otherwise only
        # deleted lazily when their own cookie is presented) and leaves live
        # sessions untouched.
        client_id = self._client_id()
        expired, _ = create_auth_session("jane", client_id)
        expired.expires_at = utc_now() - timedelta(seconds=1)
        expired.save()
        live, _ = create_auth_session("john", client_id)
        # Capture ids before the delete+commit expires the ORM instances.
        expired_series = expired.series_id
        live_series = live.series_id

        deleted = cleanup_expired_auth_sessions()
        self.assertGreaterEqual(deleted, 1)
        self.assertIsNone(AuthSession.query.filter_by(series_id=expired_series).first())
        self.assertIsNotNone(AuthSession.query.filter_by(series_id=live_series).first())
