"""
Data transformation test for migration a1b2c3d4e5f6
The challenge.data column of the migration. The SMS gateway options it encrypts are tested in
test_migration_a1b2c3d4e5f6.py, which needs no database of its own.

upgrade()   — challenge.data becomes a Text column (a CLOB on Oracle)
downgrade() — all challenges are deleted and challenge.data is limited to 512 characters again
"""

import os

import pytest
from sqlalchemy import Engine, inspect as sa_inspect

from tests.migration_test_utils import MigrationTestBase

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


class TestMigrationA1b2c3d4e5f6(MigrationTestBase):
    REVISION = "a1b2c3d4e5f6"
    PARENT_REVISION = "d4f5a6b7c8e9"

    @staticmethod
    def _challenge_row(challenge_id: int, data: str) -> dict:
        return {
            "id": challenge_id,
            "transaction_id": f"txn_data_length_{challenge_id}",
            "data": data,
            "challenge": "enter otp",
            "session": "",
            "serial": "HOTP001",
            "received_count": 0,
            "otp_valid": False,
        }

    @staticmethod
    def _data_column_length(engine: Engine) -> int | None:
        columns = {column["name"]: column for column in sa_inspect(engine).get_columns("challenge")}
        return getattr(columns["data"]["type"], "length", None)

    def _upgrade_to_parent(self) -> None:
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            assert self._data_column_length(engine) == 512
        finally:
            engine.dispose()

    def test_upgrade_removes_the_length_limit(self, flask_app):
        self._upgrade_to_parent()

        self._upgrade()

        engine = self._engine()
        try:
            assert self._data_column_length(engine) is None
            self._insert_rows(engine, "challenge", [self._challenge_row(9001, "a" * 10000)])
            assert self._fetch_scalar(engine, "SELECT data FROM challenge WHERE id = 9001") == "a" * 10000
        finally:
            engine.dispose()

    def test_downgrade_deletes_the_challenges(self, flask_app):
        self._upgrade_to_parent()
        self._upgrade()
        engine = self._engine()
        try:
            self._insert_rows(engine, "challenge", [self._challenge_row(9001, "a" * 100),
                                                    self._challenge_row(9002, "b" * 10000)])
        finally:
            engine.dispose()

        self._downgrade()

        engine = self._engine()
        try:
            assert self._data_column_length(engine) == 512
            assert self._fetch_scalar(engine, "SELECT COUNT(*) FROM challenge") == 0
        finally:
            engine.dispose()
