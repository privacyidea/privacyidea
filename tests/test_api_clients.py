from unittest import mock

from .base import MyApiTestCase

from privacyidea.lib.clients import hash_api_key, create_client
from privacyidea.lib.remembered_device import create_remembered_device, user_identity
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.realm import set_realm
from privacyidea.lib.user import User
from privacyidea.models import Client, RememberedDevice


class APIClientsTestCase(MyApiTestCase):
    """
    These tests do not rely on execution order or absolute row counts: each
    test creates the clients it needs and asserts on their specific ids.
    """

    def _create_client(self, display_name="My CP", client_type="privacyidea-cp"):
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
        self.assertEqual("privacyidea-cp", value["client_type"])
        self.assertEqual("active", value["status"])
        self.assertNotIn("key_hash", value)
        client_id = value["id"]
        api_key = value["api_key"]

        # The key has the form pi_<key_id>_<secret>; the key_id is exposed, the
        # secret is not.
        self.assertEqual(f"pi_{value['key_id']}_{api_key.split('_', 2)[2]}", api_key)
        self.assertTrue(api_key.startswith(f"pi_{value['key_id']}_"), api_key)

        # Creation is audited (never with the plaintext key in it).
        create_audit = self.find_most_recent_audit_entry(info="*privacyidea-cp: My CP*")
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
        # An omitted config is persisted as an empty dict, never None/JSON null.
        self.assertEqual({}, stored.config)

    def test_02_list_contains_created_clients(self):
        a = self._create_client("List A", "privacyidea-keycloak")
        b = self._create_client("List B", "entraid-via-keycloak")
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

    def test_01b_create_client_rejects_unknown_client_type(self):
        with self.app.test_request_context('/clients/',
                                           data={"display_name": "Bad Type",
                                                 "client_type": "bogus"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # An unknown client_type is a bad parameter (400), not accepted as free text.
            self.assertEqual(400, res.status_code, res)

    def test_03b_update_invalid_status_is_400(self):
        client_id = self._create_client()["id"]
        with self.app.test_request_context(f'/clients/{client_id}',
                                           data={"status": "bogus"},
                                           method='PATCH',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # An invalid status is a bad parameter (400), not a missing resource (404).
            self.assertEqual(400, res.status_code, res)

    def test_03c_update_empty_display_name_is_noop(self):
        value = self._create_client()
        client_id = value["id"]
        with self.app.test_request_context(f'/clients/{client_id}',
                                           data={"display_name": "", "status": "suspended"},
                                           method='PATCH',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            updated = res.json['result']['value']
            # An empty display_name is ignored (not blanked); status still changes.
            self.assertEqual("My CP", updated["display_name"])
            self.assertEqual("suspended", updated["status"])

    def test_03d_config_is_never_none(self):
        # The model normalises config to a dict for any caller: nullable=False on
        # a JSON column does not stop a Python None (it stores JSON null).
        client = Client(display_name="x", client_type="privacyidea-cp",
                        key_id="k1", key_hash="h", config=None)
        self.assertEqual({}, client.config)
        client.config = None
        self.assertEqual({}, client.config)

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
                                                 "client_type": "privacyidea-keycloak"},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)

    def test_08_key_prefix_with_underscore_rejected(self):
        # The key format splits on the first two underscores, so a prefix
        # containing '_' would desync key_id/secret; it must be rejected.
        from privacyidea.lib.clients import generate_api_key
        from privacyidea.lib.error import ParameterError
        self.assertRaises(ParameterError, generate_api_key, prefix="win_cp")


class APIClientAPIKeyMiddlewareTestCase(MyApiTestCase):

    def _create_client(self):
        with self.app.test_request_context('/clients/',
                                           data={"display_name": "Mw",
                                                 "client_type": "entraid-via-keycloak"},
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

    def test_05c_touch_client_failure_does_not_unidentify(self):
        # Refreshing last_used_at is best-effort: a write failure there must not
        # degrade an otherwise-valid active client to unidentified.
        client = self._create_client()
        with mock.patch("privacyidea.api.before_after.touch_client",
                        side_effect=Exception("DB write failed")):
            with self.app.test_request_context('/validate/capabilities', method='GET',
                                               headers={'X-API-Key': client["api_key"]}):
                res = self.app.full_dispatch_request()
                # Still identified: capabilities is reachable (200), not a 401.
                self.assertEqual(200, res.status_code, res)

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


class APIClientRememberedDevicesTestCase(MyApiTestCase):
    """
    Listing and revoking a client's persistent remember-device devices.
    Order-independent: each test creates its own client(s) and devices.
    """

    def setUp(self):
        self.setUp_user_realms()
        # Devices bind to a resolver-stable identity, so use a real user.
        self.identity = user_identity(User(login="cornelius", realm=self.realm1))

    def _device(self, client_id, login="cornelius", realm=None):
        identity = user_identity(User(login=login, realm=realm or self.realm1))
        device, _cookie = create_remembered_device(identity, client_id)
        return device

    def _revoke_all(self, client_id, **params):
        with self.app.test_request_context(f'/clients/{client_id}/remembered_devices',
                                           query_string=params, method='DELETE',
                                           headers={'Authorization': self.at}):
            return self.app.full_dispatch_request()

    def test_01_list_devices(self):
        client, _key = create_client("devices client", "privacyidea-cp")
        device, _cookie = create_remembered_device(self.identity, client.id, ip_address="10.0.0.9",
                                               user_agent="curl")

        with self.app.test_request_context(f'/clients/{client.id}/remembered_devices',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            page = res.json['result']['value']
            self.assertEqual(1, page['count'])
            self.assertIsNone(page['prev'])
            self.assertIsNone(page['next'])
            devices = page['devices']
            self.assertEqual(1, len(devices))
            entry = devices[0]
            self.assertEqual(entry["device_id"], device.device_id)
            # The secret series_id (the cookie's credential half) is never listed.
            self.assertNotIn("series_id", entry)
            # The stored identity is the resolver-stable triple; the login is
            # resolved best-effort for display.
            self.assertEqual(self.identity.user_id, entry["user_id"])
            self.assertEqual(self.identity.resolver, entry["resolver"])
            self.assertEqual(self.realm1, entry["realm"])
            self.assertEqual("cornelius", entry["user"])
            self.assertEqual("10.0.0.9", entry["ip_address"])
            # Timestamps are serialised UTC-aware so the WebUI does not shift them.
            self.assertTrue(entry["expires_at"].endswith("+00:00"), entry["expires_at"])
            self.assertTrue(entry["created_at"].endswith("+00:00"), entry["created_at"])
            # The rotating token/counter must never be exposed.
            self.assertNotIn("counter", entry)

    def test_01c_list_devices_paginates(self):
        client, _key = create_client("paginated devices client", "privacyidea-cp")
        devices = [self._device(client.id) for _ in range(5)]

        with self.app.test_request_context(f'/clients/{client.id}/remembered_devices',
                                           method='GET', query_string={"page": 1, "pagesize": 2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            page = res.json['result']['value']
            self.assertEqual(5, page['count'])
            self.assertEqual(2, len(page['devices']))
            self.assertIsNone(page['prev'])
            self.assertEqual(2, page['next'])
            # Newest first.
            self.assertEqual(devices[-1].device_id, page['devices'][0]['device_id'])

        with self.app.test_request_context(f'/clients/{client.id}/remembered_devices',
                                           method='GET', query_string={"page": 3, "pagesize": 2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            page = res.json['result']['value']
            self.assertEqual(5, page['count'])
            self.assertEqual(1, len(page['devices']))
            self.assertEqual(2, page['prev'])
            self.assertIsNone(page['next'])

    def test_01d_list_devices_realm_filter(self):
        set_realm("xclistfilter", [{"name": self.resolvername1}])
        client, _key = create_client("realm filtered client", "privacyidea-cp")
        in_realm = self._device(client.id, "cornelius", realm="xclistfilter").device_id
        other_realm = self._device(client.id, "cornelius", realm=self.realm1).device_id

        with self.app.test_request_context(f'/clients/{client.id}/remembered_devices',
                                           method='GET', query_string={"realm": "xclistfilter"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            page = res.json['result']['value']
            self.assertEqual(1, page['count'])
            self.assertEqual(in_realm, page['devices'][0]['device_id'])
            self.assertNotIn(other_realm, {d['device_id'] for d in page['devices']})

        with self.app.test_request_context(f'/clients/{client.id}/remembered_devices',
                                           method='GET', query_string={"realm": "does-not-exist"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)

    def test_02_revoke_device(self):
        client, _key = create_client("revoke client", "privacyidea-cp")
        device, _cookie = create_remembered_device(self.identity, client.id)

        with self.app.test_request_context(f'/clients/{client.id}/remembered_devices/{device.device_id}',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(res.json['result']['value'], device.device_id)

        self.assertIsNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_03_revoke_is_scoped_to_client(self):
        client_a, _ = create_client("client A", "privacyidea-cp")
        client_b, _ = create_client("client B", "privacyidea-keycloak")
        device, _cookie = create_remembered_device(self.identity, client_a.id)

        # Try to revoke A's device via B's id -> 404, and A's device survives.
        with self.app.test_request_context(f'/clients/{client_b.id}/remembered_devices/{device.device_id}',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res)
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())

    def test_04_devices_missing_client_404(self):
        with self.app.test_request_context('/clients/does-not-exist/remembered_devices',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res)

    def test_05_revoke_all_devices(self):
        client, _key = create_client("revoke-all client", "privacyidea-cp")
        self._device(client.id, "cornelius")
        self._device(client.id, "shadow")

        res = self._revoke_all(client.id)
        self.assertEqual(200, res.status_code, res)
        # All of the client's devices are revoked, and the count is reported.
        self.assertEqual(2, res.json['result']['value'])
        self.assertEqual([], RememberedDevice.query.filter_by(client_id=client.id).all())

        entry = self.find_most_recent_audit_entry(info=f"*Client ID: {client.id}*")
        self.assertEqual(1, entry["success"])

    def test_06_revoke_all_is_scoped_to_client(self):
        client_a, _ = create_client("all client A", "privacyidea-cp")
        client_b, _ = create_client("all client B", "privacyidea-keycloak")
        self._device(client_a.id)
        keep = self._device(client_b.id)

        res = self._revoke_all(client_a.id)
        self.assertEqual(200, res.status_code, res)
        self.assertEqual(1, res.json['result']['value'])
        # Client B's device is untouched.
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=keep.series_id).first())

    def test_07_revoke_all_narrowed_to_user(self):
        client, _key = create_client("by-user client", "privacyidea-cp")
        # Capture series ids up front: the bulk delete+commit expires the ORM rows.
        target_series = self._device(client.id, "cornelius").series_id
        keep_series = self._device(client.id, "shadow").series_id

        res = self._revoke_all(client.id, user="cornelius", realm=self.realm1)
        self.assertEqual(200, res.status_code, res)
        # Only cornelius's device is revoked; shadow's survives.
        self.assertEqual(1, res.json['result']['value'])
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=target_series).first())
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=keep_series).first())

    def test_08_revoke_all_narrowed_to_realm(self):
        set_realm("realm_other", [{"name": self.resolvername1}])
        client, _key = create_client("by-realm client", "privacyidea-cp")
        # Capture series ids up front: the bulk delete+commit expires the ORM rows.
        target_series = self._device(client.id, "cornelius", realm=self.realm1).series_id
        keep_series = self._device(client.id, "cornelius", realm="realm_other").series_id

        res = self._revoke_all(client.id, realm=self.realm1)
        self.assertEqual(200, res.status_code, res)
        # Only the realm1 device is revoked; the one in the other realm survives.
        self.assertEqual(1, res.json['result']['value'])
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=target_series).first())
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=keep_series).first())

    def test_09_revoke_all_unknown_user_is_400(self):
        client, _key = create_client("bad-user client", "privacyidea-cp")
        res = self._revoke_all(client.id, user="ghost", realm=self.realm1)
        # A user that does not resolve cannot be targeted by login.
        self.assertEqual(400, res.status_code, res)

    def test_09b_revoke_all_user_without_realm_is_400(self):
        # Filtering by user without a realm is ambiguous and must be rejected.
        client, _key = create_client("user-no-realm client", "privacyidea-cp")
        res = self._revoke_all(client.id, user="cornelius")
        self.assertEqual(400, res.status_code, res)

    def test_10_revoke_all_missing_client_404(self):
        res = self._revoke_all("does-not-exist")
        self.assertEqual(404, res.status_code, res)

    def test_11_revoke_all_unknown_realm_is_400(self):
        client, _key = create_client("unknown-realm client", "privacyidea-cp")
        keep_series = self._device(client.id, "cornelius").series_id
        res = self._revoke_all(client.id, realm="nosuchrealm")
        # An unknown realm must be rejected, not silently widened to revoke-all.
        self.assertEqual(400, res.status_code, res)
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=keep_series).first())

    def _revoke_devices(self, **params):
        with self.app.test_request_context('/clients/remembered_devices',
                                           query_string=params, method='DELETE',
                                           headers={'Authorization': self.at}):
            return self.app.full_dispatch_request()

    def test_12_revoke_by_realm_across_clients(self):
        # Dedicated realms so the cross-client sweep only hits this test's rows.
        set_realm("xcrealm", [{"name": self.resolvername1}])
        set_realm("xcother", [{"name": self.resolvername1}])
        client_a, _ = create_client("xc realm A", "privacyidea-cp")
        client_b, _ = create_client("xc realm B", "privacyidea-keycloak")
        a1 = self._device(client_a.id, "cornelius", realm="xcrealm").series_id
        b1 = self._device(client_b.id, "cornelius", realm="xcrealm").series_id
        other = self._device(client_a.id, "cornelius", realm="xcother").series_id

        res = self._revoke_devices(realm="xcrealm")
        self.assertEqual(200, res.status_code, res)
        # Both xcrealm devices are revoked across clients; the other realm survives.
        self.assertEqual(2, res.json['result']['value'])
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=a1).first())
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=b1).first())
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=other).first())

    def test_13_revoke_by_user_across_clients(self):
        set_realm("xcuser", [{"name": self.resolvername1}])
        client_a, _ = create_client("xc user A", "privacyidea-cp")
        client_b, _ = create_client("xc user B", "privacyidea-keycloak")
        a = self._device(client_a.id, "cornelius", realm="xcuser").series_id
        b = self._device(client_b.id, "cornelius", realm="xcuser").series_id
        keep = self._device(client_a.id, "shadow", realm="xcuser").series_id

        res = self._revoke_devices(user="cornelius", realm="xcuser")
        self.assertEqual(200, res.status_code, res)
        # cornelius's devices on both clients are revoked; shadow's survives.
        self.assertEqual(2, res.json['result']['value'])
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=a).first())
        self.assertIsNone(RememberedDevice.query.filter_by(series_id=b).first())
        self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=keep).first())

    def test_14_revoke_requires_realm(self):
        # An unscoped call must be refused (never a system-wide wipe by omission).
        res = self._revoke_devices()
        self.assertEqual(400, res.status_code, res)

    def test_15_revoke_unknown_realm_is_400(self):
        res = self._revoke_devices(realm="nosuchrealm")
        self.assertEqual(400, res.status_code, res)

    def test_16_revoke_respects_admin_realm_scope(self):
        # A remembered_device_revoke admin policy scoped to a different realm must block a
        # revoke targeting realm1 (the acting admin's realm restriction applies).
        set_realm("xcscope", [{"name": self.resolvername1}])
        client, _ = create_client("scoped client", "privacyidea-cp")
        keep = self._device(client.id, "cornelius", realm=self.realm1).series_id
        set_policy("clients_scoped", scope=SCOPE.ADMIN,
                   action=PolicyAction.REMEMBERED_DEVICE_REVOKE, realm="xcscope")
        try:
            res = self._revoke_devices(realm=self.realm1)
            self.assertEqual(403, res.status_code, res)
            self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=keep).first())
        finally:
            delete_policy("clients_scoped")

    def test_17_revoke_all_for_client_respects_admin_realm_scope(self):
        # Per-client "revoke all" carries no realm, so a realm-restricted admin
        # must not be able to use it to wipe devices belonging to other realms:
        # the revoke is limited to the admin's allowed realms (here none apply, so
        # the realm1 device survives and nothing is revoked).
        set_realm("xcscope", [{"name": self.resolvername1}])
        client, _ = create_client("scoped all client", "privacyidea-cp")
        keep = self._device(client.id, "cornelius", realm=self.realm1).series_id
        set_policy("clients_scoped", scope=SCOPE.ADMIN,
                   action=PolicyAction.REMEMBERED_DEVICE_REVOKE, realm="xcscope")
        try:
            res = self._revoke_all(client.id)
            self.assertEqual(200, res.status_code, res)
            self.assertEqual(0, res.json['result']['value'])
            self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=keep).first())
        finally:
            delete_policy("clients_scoped")

    def test_18_revoke_single_respects_admin_realm_scope(self):
        set_realm("xcscope", [{"name": self.resolvername1}])
        client, _ = create_client("scoped single client", "privacyidea-cp")
        device = self._device(client.id, "cornelius", realm=self.realm1)
        set_policy("clients_scoped", scope=SCOPE.ADMIN,
                   action=PolicyAction.REMEMBERED_DEVICE_REVOKE, realm="xcscope")
        try:
            with self.app.test_request_context(f'/clients/{client.id}/remembered_devices/{device.device_id}',
                                               method='DELETE', headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(403, res.status_code, res)
            self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=device.series_id).first())
        finally:
            delete_policy("clients_scoped")

    def test_19_revoke_by_user_respects_admin_realm_scope(self):
        set_realm("xcscope", [{"name": self.resolvername1}])
        client, _ = create_client("scoped user client", "privacyidea-cp")
        keep = self._device(client.id, "cornelius", realm=self.realm1).series_id
        set_policy("clients_scoped", scope=SCOPE.ADMIN,
                   action=PolicyAction.REMEMBERED_DEVICE_REVOKE, realm="xcscope")
        try:
            res = self._revoke_devices(user="cornelius", realm=self.realm1)
            self.assertEqual(403, res.status_code, res)
            self.assertIsNotNone(RememberedDevice.query.filter_by(series_id=keep).first())
        finally:
            delete_policy("clients_scoped")

    def test_20_list_respects_admin_realm_scope(self):
        # The listing carries no realm, so a remembered_device_list admin policy
        # scoped to one realm must not expose devices bound to other realms on the
        # same client (the read-side analogue of the revoke realm scoping).
        set_realm("xclist", [{"name": self.resolvername1}])
        client, _ = create_client("scoped list client", "privacyidea-cp")
        in_scope = self._device(client.id, "cornelius", realm="xclist").device_id
        out_scope = self._device(client.id, "cornelius", realm=self.realm1).device_id
        set_policy("clients_list_scoped", scope=SCOPE.ADMIN,
                   action=PolicyAction.REMEMBERED_DEVICE_LIST, realm="xclist")
        try:
            with self.app.test_request_context(f'/clients/{client.id}/remembered_devices',
                                               method='GET', headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                listed = {entry["device_id"] for entry in res.json['result']['value']['devices']}
            self.assertIn(in_scope, listed)
            self.assertNotIn(out_scope, listed)
        finally:
            delete_policy("clients_list_scoped")
