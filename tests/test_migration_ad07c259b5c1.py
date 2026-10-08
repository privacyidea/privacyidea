"""
Data transformation test for migration ad07c259b5c1
Abort on error for the event handlers whose result the request consumes.

The migration:
- Sets ``abort_on_error`` for existing ``RequestMangler`` and ``ResponseMangler`` handlers
- Sets it for existing ``Script`` handlers that are configured to raise an error
- Leaves every other handler as it is

upgrade()   — UPDATE eventhandler SET abort_on_error ...
downgrade() — keeps the values
"""

import os

import pytest
from sqlalchemy.engine import Engine

from tests.migration_test_utils import MigrationTestBase, quote_identifier

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


class TestMigrationAd07c259b5c1(MigrationTestBase):
    REVISION = "ad07c259b5c1"
    PARENT_REVISION = "b7c1e4d2a9f3"

    # The seed ships one event handler of its own, so the inserted ids start well above it.
    NOTIFICATION_ID = 101
    REQUEST_MANGLER_ID = 102
    RESPONSE_MANGLER_ID = 103
    RAISING_SCRIPT_ID = 104
    SCRIPT_ID = 105
    SCRIPT_WITHOUT_OPTION_ID = 106

    def _handler(self, handler_id: int, module: str, action: str, position: str = "post") -> dict:
        return {"id": handler_id, "name": f"handler {handler_id}", "active": True, "ordering": 0,
                "position": position, "event": "validate_check", "handlermodule": module, "condition": "",
                "action": action, "abort_on_error": False}

    def _insert_handlers(self, engine: Engine) -> None:
        self._insert_rows(engine, "eventhandler", [
            self._handler(self.NOTIFICATION_ID, "UserNotification", "sendmail"),
            self._handler(self.REQUEST_MANGLER_ID, "RequestMangler", "set", position="pre"),
            self._handler(self.RESPONSE_MANGLER_ID, "ResponseMangler", "delete"),
            self._handler(self.RAISING_SCRIPT_ID, "Script", "check.sh", position="pre"),
            self._handler(self.SCRIPT_ID, "Script", "log.sh"),
            self._handler(self.SCRIPT_WITHOUT_OPTION_ID, "Script", "other.sh"),
        ])
        self._insert_rows(engine, "eventhandleroption", [
            {"id": 201, "eventhandler_id": self.RAISING_SCRIPT_ID, "Key": "raise_error", "Value": "True",
             "Type": "", "Description": ""},
            {"id": 202, "eventhandler_id": self.RAISING_SCRIPT_ID, "Key": "background", "Value": "wait",
             "Type": "", "Description": ""},
            {"id": 203, "eventhandler_id": self.SCRIPT_ID, "Key": "raise_error", "Value": "False",
             "Type": "", "Description": ""},
            # The option of another handler module does not count
            {"id": 204, "eventhandler_id": self.NOTIFICATION_ID, "Key": "raise_error", "Value": "True",
             "Type": "", "Description": ""},
        ])

    def _abort_on_error(self, engine: Engine, handler_id: int) -> bool:
        column = quote_identifier("abort_on_error")
        return bool(self._fetch_scalar(engine, f"SELECT {column} FROM eventhandler WHERE id = :id",
                                       {"id": handler_id}))

    def test_upgrade_sets_abort_on_error_for_the_consumed_handlers(self, flask_app):
        """The mangler handlers and a script that raises an error abort on error, every other handler is kept."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_handlers(engine)

            self._upgrade()

            assert self._abort_on_error(engine, self.REQUEST_MANGLER_ID) is True
            assert self._abort_on_error(engine, self.RESPONSE_MANGLER_ID) is True
            assert self._abort_on_error(engine, self.RAISING_SCRIPT_ID) is True
            assert self._abort_on_error(engine, self.SCRIPT_ID) is False
            assert self._abort_on_error(engine, self.SCRIPT_WITHOUT_OPTION_ID) is False
            assert self._abort_on_error(engine, self.NOTIFICATION_ID) is False
        finally:
            engine.dispose()

    def test_downgrade_keeps_the_values(self, flask_app):
        """The downgrade keeps the handlers and their values."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            handlers_before = self._fetch_scalar(engine, "SELECT COUNT(*) FROM eventhandler")
            self._insert_handlers(engine)
            self._upgrade()

            self._downgrade()

            assert self._fetch_scalar(engine, "SELECT COUNT(*) FROM eventhandler") == handlers_before + 6
            assert self._abort_on_error(engine, self.REQUEST_MANGLER_ID) is True
        finally:
            engine.dispose()
