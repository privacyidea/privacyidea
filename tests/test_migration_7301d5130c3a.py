"""
Data transformation test for migration 7301d5130c3a
v3.11: Fix content type in EventHandlerOption table

This migration fixes a typo in eventhandleroption rows where
  Key='content_type', Value='urlendcode'
was stored instead of the correct
  Key='content_type', Value='urlencoded'

upgrade()   — rewrites 'urlendcode'  → 'urlencoded'
downgrade() — reverts  'urlencoded'  → 'urlendcode'

Rows with other Key/Value combinations must be untouched in both directions.
"""

import os

import pytest

from tests.migration_test_utils import MigrationTestBase, is_postgres

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

DB_URL = os.environ.get("TEST_DATABASE_URL", "")


class TestMigration7301d5130c3a(MigrationTestBase):
    REVISION = "7301d5130c3a"
    PARENT_REVISION = "eac770c0bbed"

    def _insert_test_eventhandler(self, engine) -> None:
        """
        Insert eventhandler id=2 for test rows.
        The seed already occupies id=1 with 'body' and 'subject' options,
        so id=2 avoids unique-constraint collisions on (eventhandler_id, Key).
        """
        self._insert_rows(engine, "eventhandler", [{
            "id": 2,
            "name": "test-handler",
            "active": True,
            "ordering": 0,
            "position": "post",
            "event": "validate_check",
            "handlermodule": "privacyidea.lib.eventhandler.UserNotificationEventHandler",
            "action": "sendmail",
        }])

    def _fetch_option(self, engine, eventhandler_id: int, key: str) -> str | None:
        key_col = '"Key"' if is_postgres() else "`Key`"
        val_col = '"Value"' if is_postgres() else "`Value`"
        return self._fetch_scalar(
            engine,
            f"SELECT {val_col} FROM eventhandleroption "
            f"WHERE eventhandler_id = :eid AND {key_col} = :key",
            {"eid": eventhandler_id, "key": key},
        )

    def test_upgrade_fixes_urlendcode_typo(self, flask_app):
        """upgrade() must rewrite Value='urlendcode' → 'urlencoded' for Key='content_type'."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_test_eventhandler(engine)
        self._insert_rows(engine, "eventhandleroption", [
            {"eventhandler_id": 2, "Key": "content_type", "Value": "urlendcode"},
        ])
        assert self._fetch_option(engine, 2, "content_type") == "urlendcode"
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_option(engine, 2, "content_type") == "urlencoded", (
            "upgrade() must rewrite 'urlendcode' to 'urlencoded' in eventhandleroption"
        )
        engine.dispose()

    def test_upgrade_leaves_correct_value_untouched(self, flask_app):
        """upgrade() must not modify rows that already have Value='urlencoded'."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_test_eventhandler(engine)
        self._insert_rows(engine, "eventhandleroption", [
            {"eventhandler_id": 2, "Key": "content_type", "Value": "urlencoded"},
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_option(engine, 2, "content_type") == "urlencoded"
        engine.dispose()

    def test_upgrade_leaves_other_keys_untouched(self, flask_app):
        """upgrade() must not touch rows with a different Key."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_test_eventhandler(engine)
        self._insert_rows(engine, "eventhandleroption", [
            {"eventhandler_id": 2, "Key": "some_other_key", "Value": "urlendcode"},
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_option(engine, 2, "some_other_key") == "urlendcode", (
            "upgrade() must only touch rows where Key='content_type'"
        )
        engine.dispose()

    def test_downgrade_reverts_urlencoded_to_urlendcode(self, flask_app):
        """downgrade() must rewrite Value='urlencoded' → 'urlendcode' for Key='content_type'."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_test_eventhandler(engine)
        self._insert_rows(engine, "eventhandleroption", [
            {"eventhandler_id": 2, "Key": "content_type", "Value": "urlendcode"},
        ])
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_option(engine, 2, "content_type") == "urlendcode", (
            "downgrade() must revert 'urlencoded' back to 'urlendcode' in eventhandleroption"
        )
        engine.dispose()

    def test_round_trip_preserves_other_rows(self, flask_app):
        """An upgrade → downgrade round-trip must leave rows with other Keys unchanged."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_test_eventhandler(engine)
        self._insert_rows(engine, "eventhandleroption", [
            {"eventhandler_id": 2, "Key": "content_type", "Value": "urlendcode"},
            {"eventhandler_id": 2, "Key": "to",           "Value": "admin@example.com"},
        ])
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_option(engine, 2, "to") == "admin@example.com", (
            "Round-trip must not corrupt rows with unrelated Keys"
        )
        engine.dispose()
