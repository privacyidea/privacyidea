"""
Data transformation test for migration f4a1c2b6d8e3
Move the authentication log's reason into a table of its own.

The migration:
- Creates ``authentication_log_reason`` (one row per reason, cascading on its entry)
- Copies every non-NULL ``authentication_log.reason`` into it
- Drops that column

upgrade()   — CREATE TABLE authentication_log_reason, INSERT ... SELECT, DROP COLUMN reason
downgrade() — ADD COLUMN reason, UPDATE it with each entry's top-ranked (lowest-id) reason, DROP TABLE
"""

import os

import pytest
from sqlalchemy import text

from tests.migration_test_utils import MigrationTestBase

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


class TestMigrationF4a1c2b6d8e3(MigrationTestBase):
    REVISION = "f4a1c2b6d8e3"
    PARENT_REVISION = "d3e8b1c47f92"

    DISABLED_ID = 201
    FAILCOUNT_ID = 202
    SUCCESS_ID = 203

    def _insert_entries(self, engine) -> None:
        """Two failed entries with a reason and one success without, the three shapes the copy has to handle."""
        self._insert_rows(engine, "authentication_log", [
            {"id": self.DISABLED_ID, "event_type": "NO_USABLE_TOKEN", "reason": "TOKEN_DISABLED",
             "timestamp": "2026-08-01 10:00:00", "username": "alice", "realm": "realm1"},
            {"id": self.FAILCOUNT_ID, "event_type": "NO_USABLE_TOKEN", "reason": "TOKEN_FAILCOUNT_EXCEEDED",
             "timestamp": "2026-08-01 10:00:01", "username": "bob", "realm": "realm1"},
            {"id": self.SUCCESS_ID, "event_type": "LOGIN_SUCCESS", "reason": None,
             "timestamp": "2026-08-01 10:00:02", "username": "carol", "realm": "realm1"},
        ])

    def _reasons_of(self, engine, entry_id: int) -> list:
        with engine.connect() as conn:
            return [row[0] for row in conn.execute(
                text("SELECT reason FROM authentication_log_reason WHERE auth_log_id = :id ORDER BY id"),
                {"id": entry_id})]

    def test_upgrade_carries_every_reason_over(self, flask_app):
        """Each classified reason becomes a row of its own; an entry without one produces none."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_entries(engine)

            self._upgrade()

            assert self._reasons_of(engine, self.DISABLED_ID) == ["TOKEN_DISABLED"]
            assert self._reasons_of(engine, self.FAILCOUNT_ID) == ["TOKEN_FAILCOUNT_EXCEEDED"]
            assert self._reasons_of(engine, self.SUCCESS_ID) == []
            # The entries themselves survive the move.
            assert self._fetch_scalar(engine, "SELECT COUNT(*) FROM authentication_log") == 3
        finally:
            engine.dispose()

    def test_downgrade_restores_the_top_ranked_reason(self, flask_app):
        """The column comes back holding each entry's first (highest-ranked) reason, and NULL where there was none."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_entries(engine)
            self._upgrade()
            # A second reason on one entry, which only the list can hold: the restored column takes the first.
            self._insert_rows(engine, "authentication_log_reason", [
                {"id": 301, "auth_log_id": self.DISABLED_ID, "reason": "WRONG_OTP"},
            ])

            self._downgrade()

            def reason_of(entry_id: int):
                return self._fetch_scalar(engine, "SELECT reason FROM authentication_log WHERE id = :id",
                                          {"id": entry_id})

            assert reason_of(self.DISABLED_ID) == "TOKEN_DISABLED"
            assert reason_of(self.FAILCOUNT_ID) == "TOKEN_FAILCOUNT_EXCEEDED"
            assert reason_of(self.SUCCESS_ID) is None
        finally:
            engine.dispose()
