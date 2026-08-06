from unittest import mock

from .base import MyApiTestCase

from privacyidea.lib.clients import hash_api_key, create_client
from privacyidea.lib.authsession import create_auth_session, session_user_identity
from privacyidea.lib.realm import set_realm
from privacyidea.lib.user import User
from privacyidea.models import Client, AuthSession


class APIClientsTestCase(MyApiTestCase):
    """
    These tests do not rely on execution order or absolute row counts: each
    test creates the clients it needs and asserts on their specific ids.
    """

    def _create_client(self, display_name="My CP", client_type="windows_cp"):
        with self.app.test_request_context('/clients/',
                                           data={"display_name": display_name,
                                                 "client_type": client_type},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            return res.json['result']['value']

    def test_01_create_client_returns_key_once(self):
        value = self._create_client()
        # The plaintext key is returned exactly once, on creation.
        self.assertIn("api_key", value)
        self.assertEqual("My CP", value["display_name"])
        self.assertEqual("windows_cp", value["client_type"])
        self.assertEqual("active", value["status"])
        self.assertNotIn("key_hash", value)
        client_id = value["id"]
        api_key = value["api_key"]

        # The key has the form pi_<key_id>_<secret>; the key_id is exposed, the
        # secret is not.
        self.assertEqual(f"pi_{value['key_id']}_{api_key.split('_', 2)[2]}", api_key)
        self.assertTrue(api_key.startswith(f"pi_{value['key_id']}_"), api_key)

        # Creation is audited (never with the plaintext key in it).
        create_audit = self.find_most_recent_audit_entry(info="*windows_cp: My CP*")
        self.assertEqual(1, create_audit["success"])
        self.assertNotIn(api_key, str(create_audit))

        # The plaintext key is not retrievable via the API afterwards.
        with self.app.test_request_context(f'/clients/{client_id}',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            client = res.json['result']['value'][0]
            self.assertNotIn("api_key", client)
            self.assertNotIn("key_hash", client)
            self.assertEqual(client["key_id"], value["key_id"])

        # Only the key id and the hash of the secret are persisted, never the
        # plaintext key or its secret half.
        stored = Client.query.filter_by(id=client_id).first()
        self.assertEqual(stored.key_id, value["key_id"])
        self.assertEqual(stored.key_hash, hash_api_key(api_key))
        self.assertNotIn(api_key.split("_", 2)[2], stored.key_hash)

    def test_02_list_contains_created_clients(self):
        a = self._create_client("List A", "keycloak")
        b = self._create_client("List B", "entraid")
        with self.app.test_request_context('/clients/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            ids = [c["id"] for c in res.json['result']['value']]
            self.assertIn(a["id"], ids)
            self.assertIn(b["id"], ids)

    def test_03_update_client_status_and_name(self):
        client_id = self._create_client()["id"]
        with self.app.test_request_context(f'/clients/{client_id}',
                                           data={"display_name": "Renamed CP",
                                                 "status": "suspended"},
                                           method='PATCH',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json['result']['value']
            self.assertEqual("Renamed CP", value["display_name"])
            self.assertEqual("suspended", value["status"])
        entry = self.find_most_recent_audit_entry(info=f"*Client ID: {client_id}*")
        self.assertEqual(1, entry["success"])

    def test_03b_update_invalid_status_is_400(self):
        client_id = self._create_client()["id"]
        with self.app.test_request_context(f'/clients/{client_id}',
                                           data={"status": "bogus"},
                                           method='PATCH',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # An invalid status is a bad parameter (400), not a missing resource (404).
            self.assertEqual(400, res.status_code, res)

    def test_04_rotate_key_invalidates_old(self):
        created = self._create_client()
        client_id = created["id"]
        old = Client.query.filter_by(id=client_id).first()
        old_hash, old_key_id = old.key_hash, old.key_id
        with self.app.test_request_context(f'/clients/{client_id}/rotate',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            new_key = res.json['result']['value']["api_key"]
            self.assertNotEqual(new_key, created["api_key"])
        rotate_audit = self.find_most_recent_audit_entry(info=f"*Client ID: {client_id}*")
        self.assertEqual(1, rotate_audit["success"])
        self.assertNotIn(new_key, str(rotate_audit))

        # Rotation replaces both the public key id and the stored secret hash.
        stored = Client.query.filter_by(id=client_id).first()
        self.assertNotEqual(stored.key_id, old_key_id)
        self.assertNotEqual(stored.key_hash, old_hash)
        self.assertEqual(stored.key_hash, hash_api_key(new_key))

    def test_05_delete_client(self):
        client_id = self._create_client()["id"]
        with self.app.test_request_context(f'/clients/{client_id}',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(res.json['result']['value'], client_id)
        entry = self.find_most_recent_audit_entry(info=f"*Client ID: {client_id}*")
        self.assertEqual(1, entry["success"])

        self.assertIsNone(Client.query.filter_by(id=client_id).first())

    def test_06_get_missing_client_404(self):
        with self.app.test_request_context('/clients/does-not-exist',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res)

    def test_07_create_requires_auth(self):
        # Without an admin auth token the endpoint must not be reachable.
        with self.app.test_request_context('/clients/',
                                           data={"display_name": "x",
                                                 "client_type": "keycloak"},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)


class APIClientAPIKeyMiddlewareTestCase(MyApiTestCase):

    def _create_client(self):
        with self.app.test_request_context('/clients/',
                                           data={"display_name": "Mw",
                                                 "client_type": "entraid"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            return res.json['result']['value']

    def test_01_missing_header_allows_legacy(self):
        # A request without X-API-Key is not rejected by the client middleware.
        with self.app.test_request_context('/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertNotEqual(res.status_code, 401, res)

    def test_02_valid_key_accepted(self):
        client = self._create_client()
        with self.app.test_request_context('/', method='GET',
                                           headers={'X-API-Key': client["api_key"]}):
            res = self.app.full_dispatch_request()
            self.assertNotEqual(res.status_code, 401, res)

        stored = Client.query.filter_by(id=client["id"]).first()
        self.assertIsNotNone(stored.last_used_at)

    def test_03_invalid_key_ignored_on_non_client_endpoint(self):
        # The X-API-Key is optional identification: an unknown key must NOT lock
        # out an endpoint that does not use API-key auth.
        with self.app.test_request_context('/', method='GET',
                                           headers={'X-API-Key': 'pi_totally_wrong'}):
            self.assertNotEqual(self.app.full_dispatch_request().status_code, 401)
        # But an endpoint that requires an identified client still rejects it.
        with self.app.test_request_context('/validate/capabilities', method='GET',
                                           headers={'X-API-Key': 'pi_totally_wrong'}):
            self.assertEqual(401, self.app.full_dispatch_request().status_code)

    def test_04_suspended_key_ignored_but_not_identified(self):
        client = self._create_client()
        with self.app.test_request_context(f'/clients/{client["id"]}',
                                           data={"status": "suspended"},
                                           method='PATCH',
                                           headers={'Authorization': self.at}):
            self.assertEqual(200, self.app.full_dispatch_request().status_code)

        # A suspended key does not lock out a non-client endpoint ...
        with self.app.test_request_context('/', method='GET',
                                           headers={'X-API-Key': client["api_key"]}):
            self.assertNotEqual(self.app.full_dispatch_request().status_code, 401)
        # ... and no longer identifies a client (capabilities requires one).
        with self.app.test_request_context('/validate/capabilities', method='GET',
                                           headers={'X-API-Key': client["api_key"]}):
            self.assertEqual(401, self.app.full_dispatch_request().status_code)

    def test_05_stale_key_does_not_break_authenticated_request(self):
        # A request authenticated by other means (admin JWT) succeeds even if it
        # also carries an unknown X-API-Key header.
        with self.app.test_request_context('/clients/', method='GET',
                                           headers={'Authorization': self.at,
                                                    'X-API-Key': 'pi_totally_wrong'}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

    def test_05b_key_resolution_error_does_not_500(self):
        # Identification is optional: an error while resolving the X-API-Key
        # (e.g. a transient DB failure) must leave the request unidentified and
        # let it proceed, never turn it into a 500.
        client = self._create_client()
        with mock.patch("privacyidea.api.before_after.identify_client_by_key",
                        side_effect=Exception("DB is down")):
            with self.app.test_request_context('/', method='GET',
                                               headers={'X-API-Key': client["api_key"]}):
                res = self.app.full_dispatch_request()
                self.assertNotEqual(res.status_code, 500, res)

    def test_06_suspended_key_not_blocked_but_audited(self):
        # A known key whose client is suspended does not block /validate/check,
        # but its use is recorded in the audit log (a real, issued key still in
        # use after it was disabled).
        self.setUp_user_realms()
        client = self._create_client()
        with self.app.test_request_context(f'/clients/{client["id"]}',
                                           data={"status": "suspended"}, method='PATCH',
                                           headers={'Authorization': self.at}):
            self.assertEqual(200, self.app.full_dispatch_request().status_code)

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "realm": self.realm1, "pass": "x"},
                                           headers={'X-API-Key': client["api_key"]}):
            res = self.app.full_dispatch_request()
            # Not blocked by the disabled key (normal validate, auth just fails).
            self.assertEqual(200, res.status_code, res)

        entry = self.find_most_recent_audit_entry(action_detail="*suspended API key presented*")
        self.assertIn("suspended API key presented", entry.get("action_detail", ""))

    def test_07_unknown_key_is_not_audited(self):
        # An unknown/garbage key must NOT create an audit note (avoid flooding).
        self.setUp_user_realms()
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "realm": self.realm1, "pass": "x"},
                                           headers={'X-API-Key': 'pi_deadbeef00000000_nope'}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
        entry = self.find_most_recent_audit_entry()
        self.assertNotIn("API key presented", entry.get("action_detail", "") or "")


class APIClientSessionsTestCase(MyApiTestCase):
    """
    Listing and revoking a client's persistent remember-device sessions.
    Order-independent: each test creates its own client(s) and sessions.
    """

    def setUp(self):
        self.setUp_user_realms()
        # Sessions bind to a resolver-stable identity, so use a real user.
        self.identity = session_user_identity(User(login="cornelius", realm=self.realm1))

    def _session(self, client_id, login="cornelius", realm=None):
        identity = session_user_identity(User(login=login, realm=realm or self.realm1))
        session, _cookie = create_auth_session(identity, client_id)
        return session

    def _revoke_all(self, client_id, **params):
        with self.app.test_request_context(f'/clients/{client_id}/sessions',
                                           query_string=params, method='DELETE',
                                           headers={'Authorization': self.at}):
            return self.app.full_dispatch_request()

    def test_01_list_sessions(self):
        client, _key = create_client("sessions client", "windows_cp")
        session, _cookie = create_auth_session(self.identity, client.id, ip_address="10.0.0.9",
                                               user_agent="curl")

        with self.app.test_request_context(f'/clients/{client.id}/sessions',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            sessions = res.json['result']['value']
            self.assertEqual(1, len(sessions))
            entry = sessions[0]
            self.assertEqual(entry["series_id"], session.series_id)
            # The stored identity is the resolver-stable triple; the login is
            # resolved best-effort for display.
            self.assertEqual(self.identity.user_id, entry["user_id"])
            self.assertEqual(self.identity.resolver, entry["resolver"])
            self.assertEqual(self.realm1, entry["realm"])
            self.assertEqual("cornelius", entry["user"])
            self.assertEqual("10.0.0.9", entry["ip_address"])
            # The rotating token/counter must never be exposed.
            self.assertNotIn("counter", entry)

    def test_02_revoke_session(self):
        client, _key = create_client("revoke client", "windows_cp")
        session, _cookie = create_auth_session(self.identity, client.id)

        with self.app.test_request_context(f'/clients/{client.id}/sessions/{session.series_id}',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(res.json['result']['value'], session.series_id)

        self.assertIsNone(AuthSession.query.filter_by(series_id=session.series_id).first())

    def test_03_revoke_is_scoped_to_client(self):
        client_a, _ = create_client("client A", "windows_cp")
        client_b, _ = create_client("client B", "keycloak")
        session, _cookie = create_auth_session(self.identity, client_a.id)

        # Try to revoke A's session via B's id -> 404, and A's session survives.
        with self.app.test_request_context(f'/clients/{client_b.id}/sessions/{session.series_id}',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res)
        self.assertIsNotNone(AuthSession.query.filter_by(series_id=session.series_id).first())

    def test_04_sessions_missing_client_404(self):
        with self.app.test_request_context('/clients/does-not-exist/sessions',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res)

    def test_05_revoke_all_sessions(self):
        client, _key = create_client("revoke-all client", "windows_cp")
        self._session(client.id, "cornelius")
        self._session(client.id, "shadow")

        res = self._revoke_all(client.id)
        self.assertEqual(200, res.status_code, res)
        # All of the client's sessions are revoked, and the count is reported.
        self.assertEqual(2, res.json['result']['value'])
        self.assertEqual([], AuthSession.query.filter_by(client_id=client.id).all())

        entry = self.find_most_recent_audit_entry(info=f"*Client ID: {client.id}*")
        self.assertEqual(1, entry["success"])

    def test_06_revoke_all_is_scoped_to_client(self):
        client_a, _ = create_client("all client A", "windows_cp")
        client_b, _ = create_client("all client B", "keycloak")
        self._session(client_a.id)
        keep = self._session(client_b.id)

        res = self._revoke_all(client_a.id)
        self.assertEqual(200, res.status_code, res)
        self.assertEqual(1, res.json['result']['value'])
        # Client B's session is untouched.
        self.assertIsNotNone(AuthSession.query.filter_by(series_id=keep.series_id).first())

    def test_07_revoke_all_narrowed_to_user(self):
        client, _key = create_client("by-user client", "windows_cp")
        # Capture series ids up front: the bulk delete+commit expires the ORM rows.
        target_series = self._session(client.id, "cornelius").series_id
        keep_series = self._session(client.id, "shadow").series_id

        res = self._revoke_all(client.id, user="cornelius", realm=self.realm1)
        self.assertEqual(200, res.status_code, res)
        # Only cornelius's device is revoked; shadow's survives.
        self.assertEqual(1, res.json['result']['value'])
        self.assertIsNone(AuthSession.query.filter_by(series_id=target_series).first())
        self.assertIsNotNone(AuthSession.query.filter_by(series_id=keep_series).first())

    def test_08_revoke_all_narrowed_to_realm(self):
        set_realm("realm_other", [{"name": self.resolvername1}])
        client, _key = create_client("by-realm client", "windows_cp")
        # Capture series ids up front: the bulk delete+commit expires the ORM rows.
        target_series = self._session(client.id, "cornelius", realm=self.realm1).series_id
        keep_series = self._session(client.id, "cornelius", realm="realm_other").series_id

        res = self._revoke_all(client.id, realm=self.realm1)
        self.assertEqual(200, res.status_code, res)
        # Only the realm1 device is revoked; the one in the other realm survives.
        self.assertEqual(1, res.json['result']['value'])
        self.assertIsNone(AuthSession.query.filter_by(series_id=target_series).first())
        self.assertIsNotNone(AuthSession.query.filter_by(series_id=keep_series).first())

    def test_09_revoke_all_unknown_user_is_400(self):
        client, _key = create_client("bad-user client", "windows_cp")
        res = self._revoke_all(client.id, user="ghost", realm=self.realm1)
        # A user that does not resolve cannot be targeted by login.
        self.assertEqual(400, res.status_code, res)

    def test_10_revoke_all_missing_client_404(self):
        res = self._revoke_all("does-not-exist")
        self.assertEqual(404, res.status_code, res)
