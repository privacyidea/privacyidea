"""
Data transformation test for migration d9e0f1a2b3c4
Add abort_on_error to the eventhandler table.

The migration:
- Adds the ``abort_on_error`` column to ``eventhandler``
- Sets it for existing ``Federation`` handlers, whose result is the response the client receives
- Sets it to False for every other existing handler, which stays best-effort

upgrade()   — ADD COLUMN abort_on_error, UPDATE eventhandler SET abort_on_error ...
downgrade() — DROP COLUMN abort_on_error
"""

import os

import pytest
from sqlalchemy import text

from tests.migration_test_utils import MigrationTestBase, is_postgres

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


class TestMigrationD9e0f1a2b3c4(MigrationTestBase):
    REVISION = "d9e0f1a2b3c4"
    PARENT_REVISION = "c8d9e0f1a2b3"

    # The seed ships one event handler of its own, so the inserted ids start well above it.
    FEDERATION_ID = 101
    NOTIFICATION_ID = 102
    RESPONSE_MANGLER_ID = 103
    INACTIVE_FEDERATION_ID = 104

    def _insert_handlers(self, engine) -> None:
        """Insert one handler per module that the abort decision differs for."""
        self._insert_rows(engine, "eventhandler", [
            {"id": self.FEDERATION_ID, "name": "forward to remote", "active": True, "ordering": 0,
             "position": "post", "event": "validate_check", "handlermodule": "Federation", "condition": "",
             "action": "forward"},
            {"id": self.NOTIFICATION_ID, "name": "notify the user", "active": True, "ordering": 0,
             "position": "post", "event": "token_init", "handlermodule": "UserNotification", "condition": "",
             "action": "sendmail"},
            {"id": self.RESPONSE_MANGLER_ID, "name": "strip the response", "active": True, "ordering": 0,
             "position": "post", "event": "token_init", "handlermodule": "ResponseMangler", "condition": "",
             "action": "delete"},
            {"id": self.INACTIVE_FEDERATION_ID, "name": "disabled federation", "active": False, "ordering": 0,
             "position": "post", "event": "token_init", "handlermodule": "Federation", "condition": "",
             "action": "forward"},
        ])

    def _column(self) -> str:
        return '"abort_on_error"' if is_postgres() else "abort_on_error"

    def _abort_on_error(self, engine, handler_id: int):
        return self._fetch_scalar(engine, f"SELECT {self._column()} FROM eventhandler WHERE id = :id",
                                  {"id": handler_id})

    def _abort_on_error_values(self, engine) -> list:
        with engine.connect() as conn:
            return [row[0] for row in conn.execute(text(f"SELECT {self._column()} FROM eventhandler"))]

    def test_upgrade_sets_abort_on_error_for_federation_handlers_only(self, flask_app):
        """Federation handlers must abort on error, every other handler stays best-effort."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_handlers(engine)

            self._upgrade()

            assert bool(self._abort_on_error(engine, self.FEDERATION_ID)) is True
            assert bool(self._abort_on_error(engine, self.NOTIFICATION_ID)) is False
            assert bool(self._abort_on_error(engine, self.RESPONSE_MANGLER_ID)) is False
            # An inactive handler is still migrated: it aborts once it is enabled again.
            assert bool(self._abort_on_error(engine, self.INACTIVE_FEDERATION_ID)) is True
        finally:
            engine.dispose()

    def test_upgrade_leaves_no_null_values(self, flask_app):
        """Every existing handler gets an explicit value, so the column is never NULL."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_handlers(engine)

            self._upgrade()

            null_count = self._fetch_scalar(
                engine, f"SELECT COUNT(*) FROM eventhandler WHERE {self._column()} IS NULL")
            assert null_count == 0
        finally:
            engine.dispose()

    def test_upgrade_matches_the_handlermodule_exactly(self, flask_app):
        """A handlermodule that only contains the identifier must not be matched."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            # A dotted module path and a name that contains the identifier must both stay best-effort,
            # otherwise the migration matches on a substring rather than on the identifier.
            self._insert_rows(engine, "eventhandler", [
                {"id": 111, "name": "legacy federation", "active": True, "ordering": 0, "position": "post",
                 "event": "token_init", "condition": "", "action": "forward",
                 "handlermodule": "privacyidea.lib.eventhandler.federationhandler.FederationEventHandler"},
                {"id": 112, "name": "not a federation handler", "active": True, "ordering": 0,
                 "position": "post", "event": "token_init", "condition": "", "action": "sendmail",
                 "handlermodule": "FederationNotification"},
            ])

            self._upgrade()

            # Read the values instead of filtering in SQL: the column is a real boolean on PostgreSQL and a
            # number on Oracle, so there is no comparison that is valid on every dialect.
            assert bool(self._abort_on_error(engine, 111)) is False
            assert bool(self._abort_on_error(engine, 112)) is False
            assert not any(bool(value) for value in self._abort_on_error_values(engine))
        finally:
            engine.dispose()

    def test_downgrade_keeps_the_handlers(self, flask_app):
        """Removing the column must not remove the handler definitions."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            handlers_before = self._fetch_scalar(engine, "SELECT COUNT(*) FROM eventhandler")
            self._insert_handlers(engine)
            self._upgrade()

            self._downgrade()

            assert self._fetch_scalar(engine, "SELECT COUNT(*) FROM eventhandler") == handlers_before + 4
        finally:
            engine.dispose()
