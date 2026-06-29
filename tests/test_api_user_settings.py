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

    def test_04b_post_rejects_non_object_settings(self):
        # The settings document must be a JSON object; a list (or any non-object)
        # is rejected with 400 rather than stored.
        res = self._post({"settings": ["not", "an", "object"]})
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

    def _user_request(self, method, path, body=None):
        kwargs = {"method": method, "headers": {"Authorization": self.at_user}}
        if body is not None:
            kwargs["content_type"] = "application/json"
            kwargs["data"] = json.dumps(body)
        with self.app.test_request_context(path, **kwargs):
            return self.app.full_dispatch_request()

    def test_10_user_role_crud_and_isolation(self):
        # Exercise the SUBJECT_USER endpoint path with a real user-role JWT.
        self.setUp_user_realms()
        self.authenticate_selfservice_user()

        # Nothing stored yet
        self.assertEqual({}, self._user_request("GET", "/user/settings").json["result"]["value"])

        res = self._user_request("POST", "/user/settings", {"settings": {"theme": "user-dark"}})
        self.assertEqual(200, res.status_code, res)
        self.assertEqual({"theme": "user-dark"}, res.json["result"]["value"])
        self.assertEqual({"theme": "user-dark"},
                         self._user_request("GET", "/user/settings").json["result"]["value"])

        # Isolation: the admin (local_admin row) does not see the user's value
        self.assertNotEqual("user-dark", self._get().json["result"]["value"].get("theme"))

        # Delete the user's key
        res = self._user_request("DELETE", "/user/settings/theme")
        self.assertEqual(200, res.status_code, res)
        self.assertEqual({}, res.json["result"]["value"])
        self.assertEqual({}, self._user_request("GET", "/user/settings").json["result"]["value"])

    def test_11_user_param_cannot_redirect_user_write(self):
        # A user passing a stray 'user=' is forced back to their own identity by
        # resolve_logged_in_user, so the write lands on the caller, not the target.
        self.setUp_user_realms()
        self.authenticate_selfservice_user()
        res = self._user_request("POST", "/user/settings",
                                 {"settings": {"theme": "mine"}, "user": "cornelius", "realm": "realm1"})
        self.assertEqual(200, res.status_code, res)
        # 'cornelius' was not targeted -> still empty
        victim = SettingsSubject.from_logged_in_user(
            {"username": "cornelius", "realm": "realm1", "role": "user"})
        self.assertEqual({}, get_user_settings(victim))
        # The caller (selfservice) got it
        self.assertEqual("mine", self._user_request("GET", "/user/settings").json["result"]["value"]["theme"])
