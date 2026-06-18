# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for privacyidea.lib.usersetting (per-principal frontend settings).

The backend is a pass-through store: it returns stored documents verbatim and
does not supply default values (the WebUI owns those).
"""
from privacyidea.lib.error import ParameterError, UserError
from privacyidea.lib.user import User
from privacyidea.lib.usersetting import (SettingsSubject, SUBJECT_LOCAL_ADMIN, SUBJECT_USER,
                                         KNOWN_SETTING_KEYS, MAX_SETTINGS_BYTES,
                                         get_allowed_keys, get_user_settings, set_user_settings,
                                         delete_user_settings, validate_user_settings,
                                         find_orphaned_user_settings, delete_orphaned_user_settings)
from privacyidea.models import UserSetting
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

    def test_02_get_empty_returns_empty_dict(self):
        # No row stored yet -> empty document, no backend-supplied defaults
        self.assertEqual({}, get_user_settings(self._admin_subject()))

    def test_03_set_and_get_roundtrip_verbatim(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark"})
        # Returned verbatim, no extra default keys injected
        self.assertEqual({"theme": "dark"}, get_user_settings(subject))

        # A second partial write merges at the top level, not clobbering the first
        set_user_settings(subject, {"token_columns": ["serial", "type"]})
        self.assertEqual({"theme": "dark", "token_columns": ["serial", "type"]},
                         get_user_settings(subject))

    def test_04_replace_overwrites_document(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark", "starting_page": "tokens"})
        stored = set_user_settings(subject, {"theme": "light"}, replace=True)
        self.assertEqual({"theme": "light"}, stored)
        # The dropped key is simply gone (the WebUI falls back to its default)
        self.assertEqual({"theme": "light"}, get_user_settings(subject))

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
        validate_user_settings({"unknown_key": 1, "whatever": "many"})
        stored = set_user_settings(self._admin_subject(), {"frontend_only_key": {"nested": True}})
        self.assertEqual({"nested": True}, stored["frontend_only_key"])

    def test_08_allowed_keys_placeholder_includes_config(self):
        # get_allowed_keys() is wired up (for the later enforcement step) and
        # already merges the admin-configured keys with the known keys.
        self.assertTrue(KNOWN_SETTING_KEYS.issubset(get_allowed_keys()))
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
        # Read is tolerated and returns an empty document
        self.assertEqual({}, get_user_settings(ghost))
        # Write is refused
        self.assertRaises(UserError, set_user_settings, ghost, {"theme": "dark"})
        # Delete is a no-op (never matches the shared row)
        self.assertEqual({}, delete_user_settings(ghost, "theme"))

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

    def test_12_non_ascii_counted_by_real_byte_size(self):
        # ensure_ascii=False: a non-ASCII string near the cap is measured by its
        # real UTF-8 size, not the inflated \\uXXXX-escaped size.
        # "ä" is 2 UTF-8 bytes; MAX_SETTINGS_BYTES//2 of them ~= the cap in real
        # bytes but would be ~3x over if counted as escapes.
        value = "ä" * (MAX_SETTINGS_BYTES // 2 - 20)
        validate_user_settings({"k": value})  # does not raise

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

    def test_15_delete_key_resets_to_default(self):
        subject = self._admin_subject()
        # replace=True for a clean baseline independent of other tests' writes
        set_user_settings(subject, {"theme": "dark", "starting_page": "tokens"}, replace=True)
        remaining = delete_user_settings(subject, "theme")
        self.assertEqual({"starting_page": "tokens"}, remaining)
        self.assertEqual({"starting_page": "tokens"}, get_user_settings(subject))
        # Deleting an absent key is a no-op
        self.assertEqual({"starting_page": "tokens"}, delete_user_settings(subject, "theme"))

    def test_16_delete_last_key_removes_row(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark"}, replace=True)
        self.assertEqual({}, delete_user_settings(subject, "theme"))
        # Row is gone -> indistinguishable from never-set
        self.assertEqual({}, get_user_settings(subject))

    def test_17_delete_all_clears_document(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark", "starting_page": "tokens"})
        self.assertEqual({}, delete_user_settings(subject))
        self.assertEqual({}, get_user_settings(subject))

    def test_18_replace_with_empty_prunes_row(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark"})
        self.assertEqual({}, set_user_settings(subject, {}, replace=True))
        self.assertEqual({}, get_user_settings(subject))

    def test_19_realm_fk_is_on_delete_cascade(self):
        # Deleting a realm must cascade-delete its users' settings. SQLite does
        # not enforce FKs in the unit-test engine, so assert the declaration
        # (the behaviour is exercised by the migration tests on Postgres/MariaDB).
        realm_fk = next(fk for fk in UserSetting.__table__.foreign_keys
                        if fk.column.table.name == "realm")
        self.assertEqual("CASCADE", realm_fk.ondelete)

    def test_20_find_and_delete_orphans(self):
        # Valid principals: a present local admin and a resolvable user.
        set_user_settings(self._admin_subject(), {"theme": "dark"})
        set_user_settings(self._user_subject(), {"theme": "dark"})
        cornelius_uid = self._user_subject().user_id
        realm_id = self._user_subject().realm_id
        # Orphans created directly, bypassing the identity guard: an admin that
        # no longer exists and a user uid the resolver cannot resolve.
        UserSetting(subject_type=SUBJECT_LOCAL_ADMIN, username="ghost-admin",
                    settings={"a": 1}).save()
        UserSetting(subject_type=SUBJECT_USER, user_id="999999",
                    resolver=self.resolvername1, realm_id=realm_id, settings={"a": 1}).save()

        described = {(o.subject_type, o.username or "", o.user_id or "")
                     for o in find_orphaned_user_settings()}
        self.assertIn((SUBJECT_LOCAL_ADMIN, "ghost-admin", ""), described)
        self.assertIn((SUBJECT_USER, "", "999999"), described)
        # The valid principals are not flagged
        self.assertNotIn((SUBJECT_LOCAL_ADMIN, "testadmin", ""), described)
        self.assertNotIn((SUBJECT_USER, "cornelius", cornelius_uid), described)

        deleted = delete_orphaned_user_settings(find_orphaned_user_settings())
        self.assertGreaterEqual(deleted, 2)
        # Orphans are gone; the valid principals' settings survive.
        self.assertEqual([], find_orphaned_user_settings())
        self.assertEqual("dark", get_user_settings(self._admin_subject())["theme"])
        self.assertEqual("dark", get_user_settings(self._user_subject())["theme"])
