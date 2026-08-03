from .base import MyApiTestCase

from privacyidea.lib.clients import hash_api_key, create_client
from privacyidea.lib.authsession import create_auth_session
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
            self.assertEqual(res.status_code, 200, res)
            return res.json['result']['value']

    def test_01_create_client_returns_key_once(self):
        value = self._create_client()
        # The plaintext key is returned exactly once, on creation.
        self.assertIn("api_key", value)
        self.assertEqual(value["display_name"], "My CP")
        self.assertEqual(value["client_type"], "windows_cp")
        self.assertEqual(value["status"], "active")
        self.assertNotIn("key_hash", value)
        client_id = value["id"]
        api_key = value["api_key"]

        # The key has the form pi_<key_id>_<secret>; the key_id is exposed, the
        # secret is not.
        self.assertEqual(api_key, f"pi_{value['key_id']}_{api_key.split('_', 2)[2]}")
        self.assertTrue(api_key.startswith(f"pi_{value['key_id']}_"), api_key)

        # The plaintext key is not retrievable via the API afterwards.
        with self.app.test_request_context(f'/clients/{client_id}',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
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
            self.assertEqual(res.status_code, 200, res)
            ids = [c["id"] for c in res.json['result']['value']]
            self.assertIn(a["id"], ids)
            self.assertIn(b["id"], ids)

    def test_03_update_client_status_and_name(self):
        client_id = self._create_client()["id"]
        with self.app.test_request_context(f'/clients/{client_id}',
                                           data={"display_name": "Renamed CP",
                                                 "status": "suspended"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            value = res.json['result']['value']
            self.assertEqual(value["display_name"], "Renamed CP")
            self.assertEqual(value["status"], "suspended")

    def test_03b_update_invalid_status_is_400(self):
        client_id = self._create_client()["id"]
        with self.app.test_request_context(f'/clients/{client_id}',
                                           data={"status": "bogus"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # An invalid status is a bad parameter (400), not a missing resource (404).
            self.assertEqual(res.status_code, 400, res)

    def test_04_rotate_key_invalidates_old(self):
        created = self._create_client()
        client_id = created["id"]
        old = Client.query.filter_by(id=client_id).first()
        old_hash, old_key_id = old.key_hash, old.key_id
        with self.app.test_request_context(f'/clients/{client_id}/rotate',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            new_key = res.json['result']['value']["api_key"]
            self.assertNotEqual(new_key, created["api_key"])

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
            self.assertEqual(res.status_code, 200, res)
            self.assertEqual(res.json['result']['value'], client_id)

        self.assertIsNone(Client.query.filter_by(id=client_id).first())

    def test_06_get_missing_client_404(self):
        with self.app.test_request_context('/clients/does-not-exist',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404, res)

    def test_07_create_requires_auth(self):
        # Without an admin auth token the endpoint must not be reachable.
        with self.app.test_request_context('/clients/',
                                           data={"display_name": "x",
                                                 "client_type": "keycloak"},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401, res)


class APIClientAPIKeyMiddlewareTestCase(MyApiTestCase):

    def _create_client(self):
        with self.app.test_request_context('/clients/',
                                           data={"display_name": "Mw",
                                                 "client_type": "entraid"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
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
            self.assertEqual(self.app.full_dispatch_request().status_code, 401)

    def test_04_suspended_key_ignored_but_not_identified(self):
        client = self._create_client()
        with self.app.test_request_context(f'/clients/{client["id"]}',
                                           data={"status": "suspended"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            self.assertEqual(self.app.full_dispatch_request().status_code, 200)

        # A suspended key does not lock out a non-client endpoint ...
        with self.app.test_request_context('/', method='GET',
                                           headers={'X-API-Key': client["api_key"]}):
            self.assertNotEqual(self.app.full_dispatch_request().status_code, 401)
        # ... and no longer identifies a client (capabilities requires one).
        with self.app.test_request_context('/validate/capabilities', method='GET',
                                           headers={'X-API-Key': client["api_key"]}):
            self.assertEqual(self.app.full_dispatch_request().status_code, 401)

    def test_05_stale_key_does_not_break_authenticated_request(self):
        # A request authenticated by other means (admin JWT) succeeds even if it
        # also carries an unknown X-API-Key header.
        with self.app.test_request_context('/clients/', method='GET',
                                           headers={'Authorization': self.at,
                                                    'X-API-Key': 'pi_totally_wrong'}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)


class APIClientSessionsTestCase(MyApiTestCase):
    """
    Listing and revoking a client's persistent remember-device sessions.
    Order-independent: each test creates its own client(s) and sessions.
    """

    def test_01_list_sessions(self):
        client, _key = create_client("sessions client", "windows_cp")
        session, _cookie = create_auth_session("alice", client.id, ip_address="10.0.0.9",
                                               user_agent="curl")

        with self.app.test_request_context(f'/clients/{client.id}/sessions',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            sessions = res.json['result']['value']
            self.assertEqual(len(sessions), 1)
            entry = sessions[0]
            self.assertEqual(entry["series_id"], session.series_id)
            self.assertEqual(entry["user_id"], "alice")
            self.assertEqual(entry["ip_address"], "10.0.0.9")
            # The rotating token/counter must never be exposed.
            self.assertNotIn("counter", entry)

    def test_02_revoke_session(self):
        client, _key = create_client("revoke client", "windows_cp")
        session, _cookie = create_auth_session("bob", client.id)

        with self.app.test_request_context(f'/clients/{client.id}/sessions/{session.series_id}',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertEqual(res.json['result']['value'], session.series_id)

        self.assertIsNone(AuthSession.query.filter_by(series_id=session.series_id).first())

    def test_03_revoke_is_scoped_to_client(self):
        client_a, _ = create_client("client A", "windows_cp")
        client_b, _ = create_client("client B", "keycloak")
        session, _cookie = create_auth_session("carol", client_a.id)

        # Try to revoke A's session via B's id -> 404, and A's session survives.
        with self.app.test_request_context(f'/clients/{client_b.id}/sessions/{session.series_id}',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404, res)
        self.assertIsNotNone(AuthSession.query.filter_by(series_id=session.series_id).first())

    def test_04_sessions_missing_client_404(self):
        with self.app.test_request_context('/clients/does-not-exist/sessions',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404, res)
