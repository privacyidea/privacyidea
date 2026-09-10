"""
Data transformation test for migration c3d4e5f6a7b8
Clear challenge table for dict-only data format.

The migration:
- Deletes ALL rows from the ``challenge`` table, removing any legacy data
  (raw strings, non-dict JSON) that is incompatible with the new dict-only
  challenge data format.

upgrade()   — DELETE FROM challenge
downgrade() — no-op (challenges are ephemeral; nothing to restore)
"""

import os

import pytest

from tests.migration_test_utils import MigrationTestBase

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


class TestMigrationC3d4e5f6a7b8(MigrationTestBase):
    REVISION = "c3d4e5f6a7b8"
    PARENT_REVISION = "a1b2c3d4e5f6"

    def _insert_challenges(self, engine, rows: list[dict]) -> None:
        """Insert rows into the challenge table."""
        self._insert_rows(engine, "challenge", rows)

    def _count_challenges(self, engine) -> int:
        return self._fetch_scalar(engine, "SELECT COUNT(*) FROM challenge")

    def test_upgrade_deletes_all_challenges(self, flask_app):
        """upgrade() must delete every row from the challenge table."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)

            # Insert challenges with various data formats (simulating pre-migration state)
            self._insert_challenges(engine, [
                {
                    "id": 9001,
                    "transaction_id": "txn_legacy_001",
                    "data": "plaintext_otp_123",
                    "challenge": "enter otp",
                    "session": "",
                    "serial": "HOTP001",
                    "received_count": 0,
                    "otp_valid": False,
                },
                {
                    "id": 9002,
                    "transaction_id": "txn_legacy_002",
                    "data": '{"otp": "654321"}',
                    "challenge": "enter otp",
                    "session": "",
                    "serial": "TOTP001",
                    "received_count": 0,
                    "otp_valid": False,
                },
                {
                    "id": 9003,
                    "transaction_id": "txn_legacy_003",
                    "data": "",
                    "challenge": "please confirm",
                    "session": "",
                    "serial": "PUSH001",
                    "received_count": 0,
                    "otp_valid": False,
                },
            ])

            assert self._count_challenges(engine) >= 3
        finally:
            engine.dispose()

        # Run the migration
        self._upgrade()

        # Verify all challenges are gone
        engine = self._engine()
        try:
            assert self._count_challenges(engine) == 0
        finally:
            engine.dispose()

        # Downgrade must not crash; deleted rows are NOT restored
        self._downgrade()

        engine = self._engine()
        try:
            assert self._count_challenges(engine) == 0
        finally:
            engine.dispose()

    def test_upgrade_on_empty_table(self, flask_app):
        """upgrade() must not fail when the challenge table is already empty."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            assert self._count_challenges(engine) == 0
        finally:
            engine.dispose()

        # Should not raise
        self._upgrade()

        engine = self._engine()
        try:
            assert self._count_challenges(engine) == 0
        finally:
            engine.dispose()

