"""
Data transformation test for migration a1e0ba6ad9dc
v3.14: Mark u2f tokens as deprecated

This migration flips rows with tokentype='u2f' to tokentype='deprecated',
stashes the original type in tokeninfo, and sets Token.active=False. See
dev/token-deprecation-strategy.md for the full design.

upgrade()   — 'u2f' tokens → tokentype='deprecated', active=False,
              plus two tokeninfo rows (original_tokentype=u2f, deprecated_in=3.14)
downgrade() — reverts tokentype back to 'u2f', removes the marker tokeninfo

Tokens of other tokentypes must be untouched in both directions. Pre-existing
tokeninfo rows on the affected tokens must be preserved.

Note: downgrade sets active=True unconditionally. A token that was inactive
*before* the upgrade comes back active after the round trip. This is a
deliberate simplification — the deprecation migration is not expected to be
downgraded in practice.
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


class TestMigrationA1e0ba6ad9dc(MigrationTestBase):
    REVISION = "a1e0ba6ad9dc"
    PARENT_REVISION = "06b105a4f941"

    def _insert_u2f_token(self, engine, token_id: int, serial: str, active: bool = True) -> None:
        self._insert_rows(engine, "token", [{
            "id": token_id,
            "serial": serial,
            "tokentype": "u2f",
            "active": active,
        }])

    def _insert_other_token(self, engine, token_id: int, serial: str, tokentype: str) -> None:
        self._insert_rows(engine, "token", [{
            "id": token_id,
            "serial": serial,
            "tokentype": tokentype,
            "active": True,
        }])

    def _count_tokens_of_type(self, engine, tokentype: str) -> int:
        return self._fetch_scalar(
            engine,
            "SELECT COUNT(*) FROM token WHERE tokentype = :t",
            {"t": tokentype},
        )

    def _fetch_tokeninfo_value(self, engine, token_id: int, key: str) -> str | None:
        key_col = '"Key"' if is_postgres() else "`Key`"
        val_col = '"Value"' if is_postgres() else "`Value`"
        return self._fetch_scalar(
            engine,
            f"SELECT {val_col} FROM tokeninfo WHERE token_id = :tid AND {key_col} = :key",
            {"tid": token_id, "key": key},
        )

    def _fetch_token_active(self, engine, token_id: int) -> bool:
        return bool(self._fetch_scalar(
            engine,
            "SELECT active FROM token WHERE id = :tid",
            {"tid": token_id},
        ))

    def _fetch_token_type(self, engine, token_id: int) -> str:
        return self._fetch_scalar(
            engine,
            "SELECT tokentype FROM token WHERE id = :tid",
            {"tid": token_id},
        )

    # -----------------------------------------------------------------
    # upgrade() tests
    # -----------------------------------------------------------------

    def test_upgrade_flips_u2f_to_deprecated(self, flask_app):
        """upgrade() must rewrite tokentype='u2f' → 'deprecated'."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_MIGR_001")
        self._insert_u2f_token(engine, 1002, "U2F_MIGR_002")
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        self.assertEqual_(self._count_tokens_of_type(engine, "u2f"), 0)
        self.assertEqual_(self._count_tokens_of_type(engine, "deprecated"), 2)
        self.assertEqual_(self._fetch_token_type(engine, 1001), "deprecated")
        self.assertEqual_(self._fetch_token_type(engine, 1002), "deprecated")
        engine.dispose()

    def test_upgrade_disables_tokens(self, flask_app):
        """upgrade() must set active=False on every deprecated u2f token."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_MIGR_001", active=True)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        self.assertEqual_(self._fetch_token_active(engine, 1001), False)
        engine.dispose()

    def test_upgrade_adds_tokeninfo_markers(self, flask_app):
        """upgrade() must insert original_tokentype, original_active, and deprecated_in tokeninfo rows."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_MIGR_001", active=True)
        self._insert_u2f_token(engine, 1002, "U2F_MIGR_002", active=False)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        self.assertEqual_(self._fetch_tokeninfo_value(engine, 1001, "original_tokentype"), "u2f")
        self.assertEqual_(self._fetch_tokeninfo_value(engine, 1001, "deprecated_in"), "3.14")
        self.assertEqual_(self._fetch_tokeninfo_value(engine, 1001, "original_active"), "1")
        # Token 1002 was inactive before the upgrade — stash must reflect that
        self.assertEqual_(self._fetch_tokeninfo_value(engine, 1002, "original_active"), "0")
        engine.dispose()

    def test_upgrade_leaves_other_tokentypes_untouched(self, flask_app):
        """upgrade() must not modify non-u2f tokens."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_MIGR_001")
        self._insert_other_token(engine, 1002, "HOTP_MIGR_001", "hotp")
        self._insert_other_token(engine, 1003, "TOTP_MIGR_001", "totp")
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        self.assertEqual_(self._fetch_token_type(engine, 1002), "hotp")
        self.assertEqual_(self._fetch_token_type(engine, 1003), "totp")
        self.assertEqual_(self._fetch_token_active(engine, 1002), True)
        self.assertEqual_(self._fetch_token_active(engine, 1003), True)
        # And no spurious tokeninfo rows on the untouched tokens
        self.assertIsNone_(self._fetch_tokeninfo_value(engine, 1002, "original_tokentype"))
        self.assertIsNone_(self._fetch_tokeninfo_value(engine, 1003, "original_tokentype"))
        engine.dispose()

    def test_upgrade_preserves_existing_tokeninfo(self, flask_app):
        """A pre-existing tokeninfo row on a u2f token must survive the upgrade."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_MIGR_001")
        self._insert_rows(engine, "tokeninfo", [
            {"token_id": 1001, "Key": "appId", "Value": "https://example.com", "Type": "", "Description": ""},
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        self.assertEqual_(self._fetch_tokeninfo_value(engine, 1001, "appId"), "https://example.com")
        engine.dispose()

    def test_upgrade_is_noop_when_no_u2f_tokens(self, flask_app):
        """upgrade() must not error when there are no u2f tokens."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_other_token(engine, 1002, "HOTP_MIGR_001", "hotp")
        engine.dispose()

        self._upgrade()  # must not raise

        engine = self._engine()
        self.assertEqual_(self._count_tokens_of_type(engine, "deprecated"), 0)
        self.assertEqual_(self._fetch_token_type(engine, 1002), "hotp")
        engine.dispose()

    # -----------------------------------------------------------------
    # downgrade() tests
    # -----------------------------------------------------------------

    def test_downgrade_restores_tokentype(self, flask_app):
        """downgrade() must flip tokentype='deprecated' back to 'u2f' for previously-u2f rows."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_MIGR_001")
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        self.assertEqual_(self._fetch_token_type(engine, 1001), "u2f")
        self.assertEqual_(self._count_tokens_of_type(engine, "deprecated"), 0)
        engine.dispose()

    def test_downgrade_is_lossless_for_active_state(self, flask_app):
        """
        downgrade() must restore each row's pre-upgrade active state, not
        blanket-set everything to True. A token that was inactive before the
        upgrade must come back inactive.
        """
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_WAS_ACTIVE", active=True)
        self._insert_u2f_token(engine, 1002, "U2F_WAS_INACTIVE", active=False)
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        self.assertEqual_(self._fetch_token_active(engine, 1001), True)
        self.assertEqual_(self._fetch_token_active(engine, 1002), False)
        engine.dispose()

    def test_downgrade_removes_marker_tokeninfo(self, flask_app):
        """downgrade() must remove all three marker rows."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_MIGR_001")
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        self.assertIsNone_(self._fetch_tokeninfo_value(engine, 1001, "original_tokentype"))
        self.assertIsNone_(self._fetch_tokeninfo_value(engine, 1001, "original_active"))
        self.assertIsNone_(self._fetch_tokeninfo_value(engine, 1001, "deprecated_in"))
        engine.dispose()

    def test_round_trip_preserves_pre_existing_tokeninfo(self, flask_app):
        """An upgrade → downgrade round-trip must leave pre-existing tokeninfo rows intact."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_u2f_token(engine, 1001, "U2F_MIGR_001")
        self._insert_rows(engine, "tokeninfo", [
            {"token_id": 1001, "Key": "appId", "Value": "https://example.com", "Type": "", "Description": ""},
        ])
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        self.assertEqual_(self._fetch_tokeninfo_value(engine, 1001, "appId"), "https://example.com")
        engine.dispose()

    # -----------------------------------------------------------------
    # Tiny assertion helpers — MigrationTestBase isn't a unittest.TestCase,
    # so we roll our own so the assertion failures read naturally.
    # -----------------------------------------------------------------

    def assertEqual_(self, actual, expected):
        assert actual == expected, f"expected {expected!r}, got {actual!r}"

    def assertIsNone_(self, value):
        assert value is None, f"expected None, got {value!r}"
