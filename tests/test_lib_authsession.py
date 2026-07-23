from .base import MyTestCase

from privacyidea.lib.error import AuthError
from privacyidea.lib.clients import create_client
from privacyidea.lib.authsession import (parse_cookie, build_cookie_value,
                                         create_auth_session, validate_and_rotate)
from privacyidea.models import AuthSession
from privacyidea.models.utils import utc_now

from datetime import timedelta


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

    def test_validate_and_rotate_success(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("bob", client_id)
        series_id = session.series_id

        new_cookie = validate_and_rotate(cookie, client_id)
        self.assertEqual(new_cookie, build_cookie_value(series_id, 2))

        stored = AuthSession.query.filter_by(series_id=series_id).first()
        self.assertEqual(stored.counter, 2)
        self.assertIsNotNone(stored.last_used_at)

        # The rotated cookie validates again, bumping to 3.
        self.assertEqual(validate_and_rotate(new_cookie, client_id),
                         build_cookie_value(series_id, 3))

    def test_theft_detection_deletes_series(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("carol", client_id)
        series_id = session.series_id

        # Rotate once so the stored counter moves to 2.
        validate_and_rotate(cookie, client_id)

        # Replaying the original counter=1 cookie is theft.
        self.assertRaises(AuthError, validate_and_rotate, cookie, client_id)
        # The whole series is gone, so even the "current" cookie no longer works.
        self.assertIsNone(AuthSession.query.filter_by(series_id=series_id).first())
        self.assertIsNone(validate_and_rotate(build_cookie_value(series_id, 2), client_id))

    def test_wrong_client_does_not_match(self):
        client_id_a = self._client_id()
        client_id_b = self._client_id()
        session, cookie = create_auth_session("dave", client_id_a)

        # A cookie issued for client A must not validate for client B.
        self.assertIsNone(validate_and_rotate(cookie, client_id_b))
        # ... and client A's session is untouched.
        self.assertEqual(AuthSession.query.filter_by(series_id=session.series_id).first().counter, 1)

    def test_unknown_series_returns_none(self):
        client_id = self._client_id()
        self.assertIsNone(validate_and_rotate("doesnotexist:1", client_id))

    def test_expired_session_is_removed(self):
        client_id = self._client_id()
        session, cookie = create_auth_session("erin", client_id)
        series_id = session.series_id
        session.expires_at = utc_now() - timedelta(seconds=1)
        session.save()

        self.assertIsNone(validate_and_rotate(cookie, client_id))
        self.assertIsNone(AuthSession.query.filter_by(series_id=series_id).first())
