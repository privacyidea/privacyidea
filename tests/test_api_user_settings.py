# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the /user/settings API endpoints.
"""
import json

from privacyidea.lib.usersetting import MAX_SETTINGS_BYTES, SettingsSubject, get_user_settings
from .base import MyApiTestCase


class UserSettingsAPITestCase(MyApiTestCase):

    def _post(self, body):
        with self.app.test_request_context('/user/settings', method='POST',
                                            headers={'Authorization': self.at},
                                            content_type='application/json',
                                            data=json.dumps(body)):
            return self.app.full_dispatch_request()

    def _get(self):
        with self.app.test_request_context('/user/settings', method='GET',
                                            headers={'Authorization': self.at}):
            return self.app.full_dispatch_request()

    def test_01_get_empty_for_fresh_admin(self):
        res = self._get()
        self.assertEqual(200, res.status_code, res)
        # Pass-through store: nothing stored -> empty document, no defaults
        self.assertEqual({}, res.json["result"]["value"])

    def test_02_post_roundtrip_and_get_match(self):
        res = self._post({"settings": {"theme": "dark"}})
        self.assertEqual(200, res.status_code, res)
        self.assertTrue(res.json["result"]["status"])
        post_value = res.json["result"]["value"]
        # Returned verbatim, no phantom default keys
        self.assertEqual({"theme": "dark"}, post_value)
        # GET returns exactly the same shape
        self.assertEqual(post_value, self._get().json["result"]["value"])

    def test_03_open_mode_accepts_unknown_key(self):
        # Key enforcement is not active yet (see the TODO in validate_user_settings),
        # so the frontend may store any key.
        res = self._post({"settings": {"frontend_key": "v"}})
        self.assertEqual(200, res.status_code, res)
        self.assertEqual("v", res.json["result"]["value"]["frontend_key"])

    def test_04_post_rejects_oversized_payload(self):
        res = self._post({"settings": {"big": "x" * (MAX_SETTINGS_BYTES + 1000)}})
        self.assertEqual(400, res.status_code, res)

    def test_05_post_requires_settings_param(self):
        res = self._post({})
        self.assertEqual(400, res.status_code, res)

    def test_06_requires_authentication(self):
        with self.app.test_request_context('/user/settings', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)

    def test_07_admin_user_param_cannot_redirect_write(self):
        # An admin passing a stray 'user=' parameter must still write to its own
        # (local_admin) settings, never to that resolver user's row.
        self.setUp_user_realms()
        res = self._post({"settings": {"theme": "admin-only"}, "user": "cornelius", "realm": "realm1"})
        self.assertEqual(200, res.status_code, res)
        # The resolver user 'cornelius' got nothing written -> still empty.
        victim = SettingsSubject.from_logged_in_user(
            {"username": "cornelius", "realm": "realm1", "role": "user"})
        self.assertEqual({}, get_user_settings(victim))

    def test_08_delete_single_key(self):
        self._post({"settings": {"theme": "dark", "token_columns": ["serial"]}, "replace": 1})
        with self.app.test_request_context('/user/settings/theme', method='DELETE',
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            # Routed to the settings endpoint (not the user-delete route) and the
            # one key is gone.
            self.assertEqual({"token_columns": ["serial"]}, res.json["result"]["value"])
        self.assertEqual({"token_columns": ["serial"]}, self._get().json["result"]["value"])

    def test_09_delete_all_clears_document(self):
        self._post({"settings": {"theme": "dark"}, "replace": 1})
        with self.app.test_request_context('/user/settings', method='DELETE',
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual({}, res.json["result"]["value"])
        self.assertEqual({}, self._get().json["result"]["value"])
