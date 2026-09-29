"""
Data transformation test for migration 50efb6312001
Remove the length limit of challenge.data.

upgrade()   — challenge.data becomes a Text column (a CLOB on Oracle), the data of existing challenges is kept
downgrade() — challenges whose data does not fit into 2000 characters are deleted, the column is limited to 2000
              characters again and the data of the other challenges is kept
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


class TestMigration50efb6312001(MigrationTestBase):
    REVISION = "50efb6312001"
    PARENT_REVISION = "b7c1e4d2a9f3"

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

    def _data_of(self, engine: Engine, challenge_id: int) -> str | None:
        return self._fetch_scalar(engine, "SELECT data FROM challenge WHERE id = :challenge_id",
                                  {"challenge_id": challenge_id})

    def _challenge_ids(self, engine: Engine) -> set[int]:
        with engine.connect() as conn:
            return {row[0] for row in conn.exec_driver_sql("SELECT id FROM challenge")}

    @staticmethod
    def _data_column_length(engine: Engine) -> int | None:
        columns = {column["name"]: column for column in sa_inspect(engine).get_columns("challenge")}
        return getattr(columns["data"]["type"], "length", None)

    def test_upgrade_keeps_data_and_removes_the_length_limit(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "challenge", [self._challenge_row(9001, "a" * 2000),
                                                    self._challenge_row(9002, "")])
            assert self._data_column_length(engine) == 2000
        finally:
            engine.dispose()

        self._upgrade()

        engine = self._engine()
        try:
            assert self._data_column_length(engine) is None
            assert self._data_of(engine, 9001) == "a" * 2000
            assert self._data_of(engine, 9002) in ("", None)
            self._insert_rows(engine, "challenge", [self._challenge_row(9003, "b" * 10000)])
            assert self._data_of(engine, 9003) == "b" * 10000
        finally:
            engine.dispose()

    def test_downgrade_deletes_only_the_challenges_that_do_not_fit(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
        finally:
            engine.dispose()
        self._upgrade()

        engine = self._engine()
        try:
            self._insert_rows(engine, "challenge", [self._challenge_row(9001, "a" * 2000),
                                                    self._challenge_row(9002, "b" * 2001),
                                                    self._challenge_row(9003, "c" * 10000),
                                                    self._challenge_row(9004, "")])
        finally:
            engine.dispose()

        self._downgrade()

        engine = self._engine()
        try:
            assert self._data_column_length(engine) == 2000
            assert self._challenge_ids(engine) == {9001, 9004}
            assert self._data_of(engine, 9001) == "a" * 2000
        finally:
            engine.dispose()
