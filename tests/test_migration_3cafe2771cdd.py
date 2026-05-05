"""
Data transformation test for migration 3cafe2771cdd
Set empty rollout_state to 'enrolled' in token table

This migration updates all rows in the 'token' table where
  rollout_state = '' or rollout_state IS NULL
to
  rollout_state = 'enrolled'

upgrade()   — rewrites ''  → 'enrolled'  and  NULL → 'enrolled'
downgrade() — reverts  'enrolled'  → ''

Rows with other rollout_state values must be untouched in both directions.
"""

import os

import pytest

from privacyidea.lib.tokenrolloutstate import RolloutState
from tests.migration_test_utils import MigrationTestBase

# Every defined RolloutState except ENROLLED — these must round-trip unchanged.
_NON_ENROLLED_STATES = [s for s in RolloutState.all_states() if s != RolloutState.ENROLLED]

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

DB_URL = os.environ.get("TEST_DATABASE_URL", "")


def _make_token(serial: str, rollout_state: str | None) -> dict:
    """Return a minimal token row dict suitable for insertion into the token table."""
    return {
        "serial": serial,
        "tokentype": "HOTP",
        "active": True,
        "revoked": False,
        "locked": False,
        "otplen": 6,
        "maxfail": 10,
        "failcount": 0,
        "count": 0,
        "count_window": 10,
        "sync_window": 1000,
        "rollout_state": rollout_state,
    }


class TestMigration3cafe2771cdd(MigrationTestBase):
    REVISION = "3cafe2771cdd"
    PARENT_REVISION = "a1e0ba6ad9dc"

    def _fetch_rollout_state(self, engine, serial: str) -> str | None:
        return self._fetch_scalar(
            engine,
            "SELECT rollout_state FROM token WHERE serial = :serial",
            {"serial": serial},
        )

    def test_upgrade_sets_empty_string_to_enrolled(self, flask_app):
        """upgrade() must rewrite rollout_state='' → 'enrolled'."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_rows(engine, "token", [_make_token("TOK001", "")])
        assert self._fetch_rollout_state(engine, "TOK001") == ""
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_rollout_state(engine, "TOK001") == "enrolled", (
            "upgrade() must rewrite '' to 'enrolled' in token.rollout_state"
        )
        engine.dispose()

    def test_upgrade_sets_null_to_enrolled(self, flask_app):
        """upgrade() must rewrite rollout_state=NULL → 'enrolled'."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_rows(engine, "token", [_make_token("TOK002", None)])
        assert self._fetch_rollout_state(engine, "TOK002") is None
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_rollout_state(engine, "TOK002") == "enrolled", (
            "upgrade() must rewrite NULL to 'enrolled' in token.rollout_state"
        )
        engine.dispose()

    @pytest.mark.parametrize("state", _NON_ENROLLED_STATES)
    def test_upgrade_leaves_other_states_untouched(self, flask_app, state):
        """upgrade() must not modify rows whose rollout_state is any non-empty, non-enrolled value."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        serial = f"TOK_{state}"
        self._insert_rows(engine, "token", [_make_token(serial, state)])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_rollout_state(engine, serial) == state, (
            f"upgrade() must not touch rows where rollout_state is {state!r}"
        )
        engine.dispose()

    def test_upgrade_leaves_already_enrolled_untouched(self, flask_app):
        """upgrade() must not modify rows that already have rollout_state='enrolled'."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_rows(engine, "token", [_make_token("TOK004", "enrolled")])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_rollout_state(engine, "TOK004") == "enrolled"
        engine.dispose()

    def test_downgrade_reverts_enrolled_to_empty_string(self, flask_app):
        """downgrade() must rewrite rollout_state='enrolled' → ''."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_rows(engine, "token", [_make_token("TOK005", "")])
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_rollout_state(engine, "TOK005") == "", (
            "downgrade() must revert 'enrolled' back to '' in token.rollout_state"
        )
        engine.dispose()

    def test_round_trip_preserves_other_rollout_states(self, flask_app):
        """An upgrade → downgrade round-trip must leave rows with other rollout_states unchanged."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        rows = [_make_token("TOK006", "")] + [
            _make_token(f"TOK_RT_{state}", state) for state in _NON_ENROLLED_STATES
        ]
        self._insert_rows(engine, "token", rows)
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_rollout_state(engine, "TOK006") == "", (
            "Round-trip must restore rows that started as '' back to ''"
        )
        for state in _NON_ENROLLED_STATES:
            serial = f"TOK_RT_{state}"
            assert self._fetch_rollout_state(engine, serial) == state, (
                f"Round-trip must not corrupt rows with rollout_state={state!r}"
            )
        engine.dispose()

    def test_upgrade_only_touches_target_rows(self, flask_app):
        """upgrade() must only modify rows with rollout_state IN ('', NULL) — count check."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        # 2 rows that should be migrated, 3 rows that must stay put.
        self._insert_rows(engine, "token", [
            _make_token("TOK_C1", ""),
            _make_token("TOK_C2", None),
            _make_token("TOK_C3", RolloutState.CLIENTWAIT),
            _make_token("TOK_C4", RolloutState.VERIFY_PENDING),
            _make_token("TOK_C5", RolloutState.ENROLLED),
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            enrolled_count = conn.execute(text(
                "SELECT COUNT(*) FROM token WHERE rollout_state = 'enrolled' "
                "AND serial IN ('TOK_C1', 'TOK_C2', 'TOK_C3', 'TOK_C4', 'TOK_C5')"
            )).scalar()
        engine.dispose()
        # TOK_C1 + TOK_C2 (migrated) + TOK_C5 (already enrolled) = 3
        assert enrolled_count == 3, (
            f"Expected exactly 3 rows with rollout_state='enrolled' "
            f"(2 migrated + 1 pre-existing), got {enrolled_count}"
        )

    def test_downgrade_is_lossy_for_pre_existing_enrolled_rows(self, flask_app):
        """
        Pin the (intentional) lossy behaviour of downgrade(): rows that were
        *already* 'enrolled' before the upgrade are indistinguishable from
        migrated rows, so downgrade() rewrites them to '' as well.

        This is a property of the migration, not a bug — but it must be pinned
        so a future change that tries to make downgrade() smarter is forced to
        update this test deliberately.
        """
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_rows(engine, "token", [_make_token("TOK_LOSSY", "enrolled")])
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_rollout_state(engine, "TOK_LOSSY") == "", (
            "downgrade() rewrites every 'enrolled' row to '' — including rows "
            "that were already 'enrolled' before the upgrade. If this assertion "
            "starts failing, the migration's downgrade strategy has changed."
        )
        engine.dispose()
