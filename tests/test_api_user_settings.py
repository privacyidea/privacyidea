# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the /user/settings API endpoints.
"""
import json

from privacyidea.lib.usersetting import SETTINGS_SCHEMA, SettingsSubject, get_user_settings
from .base import MyApiTestCase


class UserSettingsAPITestCase(MyApiTestCase):

    def test_01_get_returns_defaults_for_admin(self):
        with self.app.test_request_context('/user/settings', method='GET',
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            value = res.json["result"]["value"]
            self.assertEqual(SETTINGS_SCHEMA["theme"]["default"], value["theme"])

    def test_02_post_merges_and_get_reflects_it(self):
        with self.app.test_request_context('/user/settings', method='POST',
                                            headers={'Authorization': self.at},
                                            content_type='application/json',
                                            data=json.dumps({"settings": {"theme": "dark"}})):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertTrue(res.json["result"]["status"])
            self.assertEqual("dark", res.json["result"]["value"]["theme"])

        with self.app.test_request_context('/user/settings', method='GET',
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual("dark", res.json["result"]["value"]["theme"])
            # default still present for unset key
            self.assertEqual(SETTINGS_SCHEMA["language"]["default"],
                             res.json["result"]["value"]["language"])

    def test_03_open_mode_accepts_unknown_key(self):
        # Key enforcement is not active yet (see the TODO in validate_user_settings),
        # so the frontend may store any key.
        with self.app.test_request_context('/user/settings', method='POST',
                                            headers={'Authorization': self.at},
                                            content_type='application/json',
                                            data=json.dumps({"settings": {"frontend_key": "v"}})):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            self.assertEqual("v", res.json["result"]["value"]["frontend_key"])

    def test_04_post_rejects_oversized_payload(self):
        with self.app.test_request_context('/user/settings', method='POST',
                                            headers={'Authorization': self.at},
                                            content_type='application/json',
                                            data=json.dumps({"settings": {"big": "x" * 9000}})):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)

    def test_05_post_requires_settings_param(self):
        with self.app.test_request_context('/user/settings', method='POST',
                                            headers={'Authorization': self.at},
                                            content_type='application/json',
                                            data=json.dumps({})):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)

    def test_06_requires_authentication(self):
        with self.app.test_request_context('/user/settings', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res)

    def test_07_admin_user_param_cannot_redirect_write(self):
        # An admin passing a stray 'user=' parameter must still write to its own
        # (local_admin) settings, never to that resolver user's row.
        self.setUp_user_realms()
        with self.app.test_request_context('/user/settings', method='POST',
                                            headers={'Authorization': self.at},
                                            content_type='application/json',
                                            data=json.dumps({"settings": {"theme": "admin-only"},
                                                             "user": "cornelius", "realm": "realm1"})):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
        # The resolver user 'cornelius' got nothing written; still pure defaults.
        victim = SettingsSubject.from_logged_in_user(
            {"username": "cornelius", "realm": "realm1", "role": "user"})
        self.assertEqual(SETTINGS_SCHEMA["theme"]["default"], get_user_settings(victim)["theme"])
