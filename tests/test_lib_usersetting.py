# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for privacyidea.lib.usersetting (per-principal frontend settings).
"""
from privacyidea.lib.error import ParameterError, UserError
from privacyidea.lib.user import User
from privacyidea.lib.usersetting import (SettingsSubject, SUBJECT_LOCAL_ADMIN, SUBJECT_USER,
                                         SETTINGS_SCHEMA, MAX_SETTINGS_BYTES,
                                         get_allowed_keys, get_user_settings, set_user_settings,
                                         validate_user_settings)
from .base import MyTestCase


class UserSettingTestCase(MyTestCase):

    def setUp(self):
        self.setUp_user_realms()

    def _user_subject(self):
        return SettingsSubject.from_logged_in_user(
            {"username": "cornelius", "realm": self.realm1, "role": "user"})

    def _admin_subject(self):
        return SettingsSubject.from_logged_in_user(
            {"username": "testadmin", "realm": "", "role": "admin"})

    def test_01_subject_resolution(self):
        admin = self._admin_subject()
        self.assertEqual(SUBJECT_LOCAL_ADMIN, admin.subject_type)
        self.assertEqual("testadmin", admin.username)
        self.assertEqual("", admin.user_id)
        self.assertIsNone(admin.realm_id)

        user = self._user_subject()
        self.assertEqual(SUBJECT_USER, user.subject_type)
        self.assertEqual(self.resolvername1, user.resolver)
        self.assertTrue(user.user_id)
        self.assertIsNotNone(user.realm_id)

    def test_02_get_returns_defaults(self):
        settings = get_user_settings(self._admin_subject())
        # No row stored yet -> every declared default is present
        for key, spec in SETTINGS_SCHEMA.items():
            self.assertEqual(spec["default"], settings[key])

    def test_03_set_merges_and_persists(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark"})
        settings = get_user_settings(subject)
        self.assertEqual("dark", settings["theme"])
        # Untouched key keeps its default
        self.assertEqual(SETTINGS_SCHEMA["language"]["default"], settings["language"])

        # A second partial write merges, it does not clobber the first
        set_user_settings(subject, {"language": "de"})
        settings = get_user_settings(subject)
        self.assertEqual("dark", settings["theme"])
        self.assertEqual("de", settings["language"])

    def test_04_replace_overwrites_document(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark", "language": "de"})
        stored = set_user_settings(subject, {"theme": "light"}, replace=True)
        self.assertEqual({"theme": "light"}, stored)
        settings = get_user_settings(subject)
        # 'language' fell back to its default after the replace
        self.assertEqual(SETTINGS_SCHEMA["language"]["default"], settings["language"])

    def test_05_admin_and_user_settings_are_isolated(self):
        set_user_settings(self._admin_subject(), {"theme": "dark"})
        set_user_settings(self._user_subject(), {"theme": "light"})
        self.assertEqual("dark", get_user_settings(self._admin_subject())["theme"])
        self.assertEqual("light", get_user_settings(self._user_subject())["theme"])

    def test_06_open_mode_always_enforces_structure(self):
        # Structural checks hold regardless of key enforcement
        self.assertRaises(ParameterError, validate_user_settings, ["not", "a", "dict"])
        self.assertRaises(ParameterError, validate_user_settings,
                          {"theme": "x" * (MAX_SETTINGS_BYTES + 1)})

    def test_07_open_mode_accepts_unknown_keys_and_types(self):
        # Keys are not enforced yet: unknown keys and arbitrary value types pass
        validate_user_settings({"unknown_key": 1, "tokens_per_page": "many"})
        stored = set_user_settings(self._admin_subject(), {"frontend_only_key": {"nested": True}})
        self.assertEqual({"nested": True}, stored["frontend_only_key"])

    def test_08_allowed_keys_placeholder_includes_config(self):
        # get_allowed_keys() is wired up (for the later enforcement step) and
        # already merges the admin-configured keys with the schema keys.
        self.assertTrue(set(SETTINGS_SCHEMA).issubset(get_allowed_keys()))
        self.app.config["PI_USER_SETTINGS_ALLOWED_KEYS"] = ["custom_admin_key"]
        try:
            self.assertIn("custom_admin_key", get_allowed_keys())
        finally:
            del self.app.config["PI_USER_SETTINGS_ALLOWED_KEYS"]

    def test_09_unidentified_user_is_not_shared(self):
        # An unresolvable user (no uid/realm_id) must not read or write a row:
        # otherwise every unresolved principal would share one row.
        ghost = SettingsSubject.from_logged_in_user(
            {"username": "does-not-exist", "realm": self.realm1, "role": "user"})
        self.assertFalse(ghost.is_identified())
        # Read is tolerated and returns only defaults
        self.assertEqual(SETTINGS_SCHEMA["theme"]["default"], get_user_settings(ghost)["theme"])
        # Write is refused
        self.assertRaises(UserError, set_user_settings, ghost, {"theme": "dark"})

    def test_10_size_cap_not_bypassable_by_merge(self):
        # Each partial write is small, but the merged document must still be
        # bounded by MAX_SETTINGS_BYTES.
        subject = self._admin_subject()
        chunk = "x" * (MAX_SETTINGS_BYTES // 2)
        set_user_settings(subject, {"a": chunk})
        # Merging a second half-cap chunk would push the stored doc over the cap
        self.assertRaises(ParameterError, set_user_settings, subject, {"b": chunk})

    def test_11_validation_rejects_non_serializable(self):
        # A non-JSON-serializable value yields a controlled ParameterError,
        # not an unhandled TypeError.
        self.assertRaises(ParameterError, validate_user_settings, {"x": {1, 2, 3}})

    def test_13_reuses_resolved_user_for_user_role(self):
        # When request.User is the JWT user, it is reused (no re-resolution)
        # and produces the same identity as resolving from scratch.
        resolved = User(login="cornelius", realm=self.realm1)
        reused = SettingsSubject.from_logged_in_user(
            {"username": "cornelius", "realm": self.realm1, "role": "user"}, resolved)
        fresh = self._user_subject()
        self.assertEqual(SUBJECT_USER, reused.subject_type)
        self.assertEqual(fresh.user_id, reused.user_id)
        self.assertEqual(fresh.resolver, reused.resolver)
        self.assertEqual(fresh.realm_id, reused.realm_id)

    def test_14_admin_ignores_resolved_user(self):
        # For an admin, request.User may reflect a 'user=' request parameter and
        # must NOT decide whose settings are touched. A local admin stays keyed
        # by its own username regardless of the passed-in user.
        attacker_param_user = User(login="cornelius", realm=self.realm1)
        subject = SettingsSubject.from_logged_in_user(
            {"username": "testadmin", "realm": "", "role": "admin"}, attacker_param_user)
        self.assertEqual(SUBJECT_LOCAL_ADMIN, subject.subject_type)
        self.assertEqual("testadmin", subject.username)
        self.assertEqual("", subject.user_id)

    def test_12_non_ascii_counted_by_real_byte_size(self):
        # ensure_ascii=False: a non-ASCII string near the cap is measured by its
        # real UTF-8 size, not the inflated \\uXXXX-escaped size.
        # "ä" is 2 UTF-8 bytes; MAX_SETTINGS_BYTES//2 of them ~= the cap in real
        # bytes but would be ~3x over if counted as escapes.
        value = "ä" * (MAX_SETTINGS_BYTES // 2 - 20)
        validate_user_settings({"k": value})  # does not raise
