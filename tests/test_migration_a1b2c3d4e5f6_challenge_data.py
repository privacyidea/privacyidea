"""
Data transformation test for migration a1b2c3d4e5f6
The challenge.data column of the migration, and the whole migration running again on a database on which it already
ran, completely or up to a failure. The encryption of the SMS gateway options itself is tested in
test_migration_a1b2c3d4e5f6.py, which needs no database of its own.

upgrade()   — challenge.data becomes a Text column (a CLOB on Oracle)
downgrade() — all challenges are deleted and challenge.data is limited to 512 characters again
"""

import os

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine, inspect as sa_inspect

from privacyidea.lib.crypto import decryptPassword, encryptPassword
from tests.migration_test_utils import MigrationTestBase

SMS_GATEWAY_OPTION = sa.table(
    "smsgatewayoption",
    sa.column("id", sa.Integer),
    sa.column("gateway_id", sa.Integer),
    sa.column("Key", sa.Unicode),
    sa.column("Value", sa.UnicodeText),
    sa.column("Type", sa.Unicode),
    sa.column("Encrypted", sa.Boolean),
)
PLAINTEXT_PASSWORD = "plaintext-password"

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

    def _upgrade_to_parent_with_sms_gateway(self) -> None:
        """Upgrade to the parent and add an SMS gateway with a plaintext PASSWORD option."""
        self._upgrade_to_parent()
        engine = self._engine()
        try:
            self._insert_rows(engine, "smsgateway", [{
                "id": 9001,
                "identifier": "rerun_gateway",
                "description": "",
                "providermodule": "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
            }])
            with engine.begin() as conn:
                conn.execute(SMS_GATEWAY_OPTION.insert(), [
                    {"id": 9001, "gateway_id": 9001, "Key": "PASSWORD", "Value": PLAINTEXT_PASSWORD, "Type": "option"},
                    {"id": 9002, "gateway_id": 9001, "Key": "URL", "Value": "https://sms.example.com",
                     "Type": "option"},
                ])
        finally:
            engine.dispose()

    def _sms_gateway_options(self) -> dict[str, tuple[str, bool]]:
        """Return {key: (stored value, Encrypted flag)} of the options of the gateway that the test added."""
        engine = self._engine()
        try:
            with engine.connect() as conn:
                rows = conn.execute(
                    sa.select(SMS_GATEWAY_OPTION.c.Key, SMS_GATEWAY_OPTION.c.Value, SMS_GATEWAY_OPTION.c.Encrypted)
                    .where(SMS_GATEWAY_OPTION.c.gateway_id == 9001)
                ).all()
            return {key: (value, bool(encrypted)) for key, value, encrypted in rows}
        finally:
            engine.dispose()

    def _assert_migrated(self) -> None:
        options = self._sms_gateway_options()
        assert decryptPassword(options["PASSWORD"][0]) == PLAINTEXT_PASSWORD
        assert options["PASSWORD"][1] is True
        assert options["URL"] == ("https://sms.example.com", False)
        engine = self._engine()
        try:
            assert self._data_column_length(engine) is None
            with engine.connect() as conn:
                heads = {row[0] for row in conn.execute(sa.text("SELECT version_num FROM alembic_version"))}
            assert self.REVISION in heads
            assert self.PARENT_REVISION not in heads
        finally:
            engine.dispose()

    def test_upgrade_runs_again_on_its_own_result(self, flask_app):
        self._upgrade_to_parent_with_sms_gateway()
        self._upgrade()
        # An option the administrator marked as secret: its key is not one the migration would encrypt by itself
        engine = self._engine()
        try:
            with engine.begin() as conn:
                conn.execute(SMS_GATEWAY_OPTION.insert(), [{
                    "id": 9003, "gateway_id": 9001, "Key": "API_KEY", "Value": encryptPassword("api-key"),
                    "Type": "option", "Encrypted": True,
                }])
        finally:
            engine.dispose()
        options_after_first_run = self._sms_gateway_options()

        self._set_stamp_back_to_parent()
        self._upgrade()

        assert self._sms_gateway_options() == options_after_first_run
        assert decryptPassword(options_after_first_run["API_KEY"][0]) == "api-key"
        assert options_after_first_run["API_KEY"][1] is True
        self._assert_migrated()

    @pytest.mark.parametrize("statement_pattern", [
        # On Oracle, this is the DROP of the old column, before the new one is added
        r"ALTER TABLE challenge",
        r"ADD (COLUMN )?[\"`]?Encrypted",
        r"^UPDATE smsgatewayoption",
    ])
    def test_upgrade_runs_again_after_failing_midway(self, flask_app, statement_pattern):
        self._upgrade_to_parent_with_sms_gateway()

        self._upgrade_failing_after(statement_pattern)
        self._upgrade()

        self._assert_migrated()

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
