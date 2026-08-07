# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for privacyidea.lib.usersetting (per-principal frontend settings).

The backend is a pass-through store: it returns stored documents verbatim and
does not supply default values (the WebUI owns those).
"""
from unittest.mock import patch

from sqlalchemy import select

from privacyidea.lib.error import ParameterError, UserError
from privacyidea.lib.user import User
from privacyidea.lib.usersetting import (SettingsSubject, SUBJECT_LOCAL_ADMIN, SUBJECT_USER,
                                         KNOWN_SETTING_KEYS, MAX_SETTINGS_BYTES,
                                         get_allowed_keys, get_user_settings, set_user_settings,
                                         delete_user_settings, validate_user_settings,
                                         find_orphaned_user_settings, delete_orphaned_user_settings,
                                         _select_for_subject)
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
        set_user_settings(subject, {"dashboard": {"widgets": ["tokens"]}})
        self.assertEqual({"theme": "dark", "dashboard": {"widgets": ["tokens"]}},
                         get_user_settings(subject))

    def test_04_replace_overwrites_document(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark", "locale": "de"})
        stored = set_user_settings(subject, {"theme": "light"}, replace=True)
        self.assertEqual({"theme": "light"}, stored)
        # The dropped key is simply gone (the WebUI falls back to its default)
        self.assertEqual({"theme": "light"}, get_user_settings(subject))

    def test_05_admin_and_user_settings_are_isolated(self):
        set_user_settings(self._admin_subject(), {"theme": "dark"})
        set_user_settings(self._user_subject(), {"theme": "light"})
        self.assertEqual("dark", get_user_settings(self._admin_subject())["theme"])
        self.assertEqual("light", get_user_settings(self._user_subject())["theme"])

    def test_06_validation_enforces_structure(self):
        self.assertRaises(ParameterError, validate_user_settings, ["not", "a", "dict"])
        self.assertRaises(ParameterError, validate_user_settings,
                          {"theme": "x" * (MAX_SETTINGS_BYTES + 1)})

    def test_07_unknown_keys_are_rejected_but_value_types_are_free(self):
        self.assertRaises(ParameterError, validate_user_settings, {"unknown_key": 1})
        self.assertRaises(ParameterError, validate_user_settings,
                          {"theme": "dark", "frontend_only_key": True})
        self.assertRaises(ParameterError, set_user_settings,
                          self._admin_subject(), {"frontend_only_key": {"nested": True}})
        self.assertNotIn("frontend_only_key", get_user_settings(self._admin_subject()))

        stored = set_user_settings(self._admin_subject(), {"dashboard": {"widgets": [1, None, "x"]}})
        self.assertEqual({"widgets": [1, None, "x"]}, stored["dashboard"])

    def test_07b_rejection_names_the_offending_keys(self):
        with self.assertRaises(ParameterError) as context:
            validate_user_settings({"zulu": 1, "alpha": 2})
        self.assertIn("alpha, zulu", context.exception.message)

    def test_07c_rejection_message_stays_bounded(self):
        # The message is written to the audit log, whose info column holds 500
        # characters. Without PI_AUDIT_SQL_TRUNCATE an oversized entry is not
        # cut but dropped, so a caller must not be able to inflate the message
        # with the rejected document -- neither by many keys nor by one long one.
        many = {f"bogus_key_{index:04d}": 1 for index in range(700)}
        with self.assertRaises(ParameterError) as context:
            validate_user_settings(many)
        self.assertLess(len(context.exception.message), 500)
        self.assertIn("700 keys in total", context.exception.message)
        # Only whole keys are listed: a half key would read like a name the
        # caller sent, sending whoever reads the audit entry after a phantom.
        listed = context.exception.message.split(": ", 1)[1].split(", ... ")[0]
        for key in listed.split(", "):
            self.assertIn(key, many)

        with self.assertRaises(ParameterError) as context:
            validate_user_settings({"x" * 5000: 1})
        self.assertLess(len(context.exception.message), 500)

    def test_07d_rejection_message_neutralizes_control_characters(self):
        # A JSON key may contain a line break, and the message is written to the
        # audit log, whose CSV export is line-oriented. An echoed key must not be
        # able to forge an entry there.
        with self.assertRaises(ParameterError) as context:
            validate_user_settings({"harmless\nforged entry": 1, "tab\there": 1})
        self.assertNotIn("\n", context.exception.message)
        self.assertNotIn("\t", context.exception.message)
        self.assertIn("harmless.forged entry", context.exception.message)

    def test_08_allowed_keys_include_config(self):
        self.assertTrue(KNOWN_SETTING_KEYS.issubset(get_allowed_keys()))
        self.assertRaises(ParameterError, validate_user_settings, {"custom_admin_key": 1})
        self.app.config["PI_USER_SETTINGS_ALLOWED_KEYS"] = ["custom_admin_key"]
        try:
            self.assertIn("custom_admin_key", get_allowed_keys())
            stored = set_user_settings(self._admin_subject(), {"custom_admin_key": "v"})
            self.assertEqual("v", stored["custom_admin_key"])
        finally:
            del self.app.config["PI_USER_SETTINGS_ALLOWED_KEYS"]

    def test_08b_stored_key_no_longer_allowed_does_not_block_writes(self):
        # A key that was allowed when it was written stays in the document, and
        # it must not block the principal from writing its other settings.
        subject = self._admin_subject()
        self.app.config["PI_USER_SETTINGS_ALLOWED_KEYS"] = ["legacy_key"]
        try:
            set_user_settings(subject, {"legacy_key": "old"}, replace=True)
        finally:
            del self.app.config["PI_USER_SETTINGS_ALLOWED_KEYS"]

        stored = set_user_settings(subject, {"theme": "dark"})
        self.assertEqual({"legacy_key": "old", "theme": "dark"}, stored)
        self.assertRaises(ParameterError, set_user_settings, subject, {"legacy_key": "new"})
        self.assertEqual({"theme": "dark"}, delete_user_settings(subject, "legacy_key"))

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
        set_user_settings(subject, {"theme": chunk}, replace=True)
        # Merging a second half-cap chunk would push the stored doc over the cap
        self.assertRaises(ParameterError, set_user_settings, subject, {"locale": chunk})

    def test_11_validation_rejects_non_serializable(self):
        # A non-JSON-serializable value yields a controlled ParameterError,
        # not an unhandled TypeError.
        self.assertRaises(ParameterError, validate_user_settings, {"theme": {1, 2, 3}})

    def test_12_non_ascii_counted_by_real_byte_size(self):
        # ensure_ascii=False: a non-ASCII string near the cap is measured by its
        # real UTF-8 size, not the inflated \\uXXXX-escaped size.
        # "ä" is 2 UTF-8 bytes; MAX_SETTINGS_BYTES//2 of them ~= the cap in real
        # bytes but would be ~3x over if counted as escapes.
        value = "ä" * (MAX_SETTINGS_BYTES // 2 - 20)
        validate_user_settings({"theme": value})  # does not raise

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
        set_user_settings(subject, {"theme": "dark", "locale": "de"}, replace=True)
        remaining = delete_user_settings(subject, "theme")
        self.assertEqual({"locale": "de"}, remaining)
        self.assertEqual({"locale": "de"}, get_user_settings(subject))
        # Deleting an absent key is a no-op
        self.assertEqual({"locale": "de"}, delete_user_settings(subject, "theme"))

    def test_16_delete_last_key_removes_row(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark"}, replace=True)
        self.assertEqual({}, delete_user_settings(subject, "theme"))
        # Row is gone -> indistinguishable from never-set
        self.assertEqual({}, get_user_settings(subject))

    def test_17_delete_all_clears_document(self):
        subject = self._admin_subject()
        set_user_settings(subject, {"theme": "dark", "locale": "de"})
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

    def test_21_allowed_keys_accepts_comma_separated_string(self):
        # Set via an environment variable, PI_USER_SETTINGS_ALLOWED_KEYS arrives
        # as a comma-separated string instead of a list; it must be split (and
        # blank entries from stray commas/whitespace dropped).
        self.app.config["PI_USER_SETTINGS_ALLOWED_KEYS"] = "alpha, beta ,, gamma "
        try:
            allowed = get_allowed_keys()
        finally:
            del self.app.config["PI_USER_SETTINGS_ALLOWED_KEYS"]
        self.assertTrue({"alpha", "beta", "gamma"}.issubset(allowed))
        self.assertNotIn("", allowed)
        # The built-in known keys are still present alongside the configured ones.
        self.assertTrue(KNOWN_SETTING_KEYS.issubset(allowed))

    def test_22_delete_on_absent_identified_row_is_noop(self):
        # An identified principal that has never stored anything: delete must
        # short-circuit on the missing row rather than error (distinct from the
        # unidentified-subject guard exercised in test_09). A fresh username
        # keeps this independent of rows other tests leave behind.
        subject = SettingsSubject.from_logged_in_user(
            {"username": "never-stored-admin", "realm": "", "role": "admin"})
        self.assertTrue(subject.is_identified())
        self.assertEqual({}, delete_user_settings(subject, "theme"))
        self.assertEqual({}, delete_user_settings(subject))

    def test_23_orphan_user_with_empty_identifiers(self):
        # A SUBJECT_USER row with an empty user_id (or resolver) can never resolve
        # to a user, so it is always an orphan -- caught before any resolver call.
        UserSetting(subject_type=SUBJECT_USER, user_id="", resolver="",
                    realm_id=None, settings={"a": 1}).save()
        flagged = find_orphaned_user_settings()
        self.assertTrue(any(o.subject_type == SUBJECT_USER and not o.user_id for o in flagged))

    def test_24_orphaned_on_error_controls_unreadable_resolver(self):
        # When the resolver raises while looking up the uid, the row counts as
        # orphaned only with orphaned_on_error=True; otherwise it is skipped so a
        # transiently unreachable resolver does not get a live user pruned.
        realm_id = self._user_subject().realm_id
        UserSetting(subject_type=SUBJECT_USER, user_id="boom-uid",
                    resolver=self.resolvername1, realm_id=realm_id, settings={"a": 1}).save()

        class _BoomResolver:
            def getUsername(self, uid):
                raise Exception("resolver unreachable")

        # get_resolver_object is imported lazily inside find_orphaned_user_settings,
        # so patch it at its source module.
        with patch("privacyidea.lib.resolver.get_resolver_object", return_value=_BoomResolver()):
            on_error = {o.user_id for o in find_orphaned_user_settings(orphaned_on_error=True)}
            self.assertIn("boom-uid", on_error)
            skipped = {o.user_id for o in find_orphaned_user_settings(orphaned_on_error=False)}
            self.assertNotIn("boom-uid", skipped)

    def test_25_delete_orphans_handles_empty_list(self):
        # Nothing to delete -> returns 0 without touching the database.
        self.assertEqual(0, delete_orphaned_user_settings([]))

    def test_26_integrity_error_recovery_merges_into_existing(self):
        # Simulate the concurrent-insert race: the first lookup misses (forcing
        # the INSERT branch), the INSERT then trips the unique constraint because
        # a row already exists, and the recovery path re-reads and merges the
        # incoming keys onto the winning document instead of failing.
        subject = self._user_subject()
        # Clean slate for this principal, then plant the row a concurrent request
        # "already committed".
        delete_user_settings(subject)
        UserSetting(subject_type=SUBJECT_USER, username="cornelius", user_id=subject.user_id,
                    resolver=subject.resolver, realm_id=subject.realm_id,
                    settings={"theme": "winner"}).save()

        real_select = _select_for_subject
        calls = {"n": 0}

        def fake_select(subj):
            calls["n"] += 1
            if calls["n"] == 1:
                # First lookup must miss the existing row to take the INSERT path.
                return select(UserSetting).filter_by(
                    subject_type=SUBJECT_USER, user_id="__never__",
                    resolver="__never__", realm_id=-1)
            return real_select(subj)

        with patch("privacyidea.lib.usersetting._select_for_subject", side_effect=fake_select):
            stored = set_user_settings(subject, {"locale": "de"})

        self.assertEqual({"theme": "winner", "locale": "de"}, stored)
        self.assertEqual({"theme": "winner", "locale": "de"}, get_user_settings(subject))
