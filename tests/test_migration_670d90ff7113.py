"""
Data transformation test for migration 670d90ff7113

upgrade()   — the lock of a local admin moves from the empty resolver and realm to the placeholder '~internal'
downgrade() — it moves back, except on Oracle, which cannot store the empty key and drops those locks instead
"""

import os
from datetime import datetime

import pytest
from sqlalchemy import text

from tests.migration_test_utils import MigrationTestBase, is_oracle, quote_identifier

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

USER_LOCK = ("resolver1", "1000", "realm1")


class TestMigration670d90ff7113(MigrationTestBase):
    REVISION = "670d90ff7113"
    PARENT_REVISION = "9e8487714b46"

    @staticmethod
    def _lock_row(resolver: str, uid: str, realm: str, user_role: str, lock_expires_at: datetime | None = None,
                  lock_cause: str = "POLICY") -> dict:
        return {
            "resolver": resolver,
            "uid": uid,
            "realm": realm,
            "username": uid,
            "user_role": user_role,
            "lock_expires_at": lock_expires_at,
            "lock_cause": lock_cause,
            "locked_at": datetime(2026, 10, 1, 12, 0, 0),
        }

    def _user_lock_row(self) -> dict:
        return self._lock_row(*USER_LOCK, user_role="user")

    def _lock_keys(self) -> set[tuple]:
        query = text(f"SELECT resolver, {quote_identifier('uid')}, realm FROM user_lock_state")
        engine = self._engine()
        try:
            with engine.connect() as conn:
                return {tuple(row) for row in conn.execute(query)}
        finally:
            engine.dispose()

    def _admin_locks(self) -> set[tuple]:
        query = text(f"SELECT resolver, {quote_identifier('uid')}, realm, lock_expires_at, lock_cause "
                     "FROM user_lock_state WHERE user_role = 'admin-internal'")
        engine = self._engine()
        try:
            with engine.connect() as conn:
                return {tuple(row) for row in conn.execute(query)}
        finally:
            engine.dispose()

    def _upgrade_to_parent(self, rows: list[dict]) -> None:
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "user_lock_state", rows)
        finally:
            engine.dispose()

    def _upgrade_with(self, rows: list[dict]) -> None:
        self._upgrade_to_parent([])
        self._upgrade()
        engine = self._engine()
        try:
            self._insert_rows(engine, "user_lock_state", rows)
        finally:
            engine.dispose()

    @pytest.mark.skipif(is_oracle(), reason="Oracle stores the empty key as NULL, so it holds no local admin lock")
    def test_upgrade_moves_a_local_admin_lock_to_the_placeholder(self, flask_app):
        self._upgrade_to_parent([self._lock_row("", "admin", "", "admin-internal"), self._user_lock_row()])

        self._upgrade()

        assert self._lock_keys() == {("~internal", "admin", "~internal"), USER_LOCK}

    def test_upgrade_leaves_a_user_lock_alone(self, flask_app):
        self._upgrade_to_parent([self._user_lock_row()])

        self._upgrade()

        assert self._lock_keys() == {USER_LOCK}

    def test_upgrade_keeps_the_locks_local_admins_got_on_the_placeholder_before_it(self, flask_app) -> None:
        # The updated code locks local admins on the placeholder before the schema update has run.
        self._upgrade_to_parent([self._lock_row("~internal", "admin", "~internal", "admin-internal"),
                                 self._lock_row("~internal", "operator", "~internal", "admin-internal"),
                                 self._user_lock_row()])

        self._upgrade()

        assert self._lock_keys() == {("~internal", "admin", "~internal"),
                                     ("~internal", "operator", "~internal"), USER_LOCK}

    @pytest.mark.skipif(is_oracle(), reason="Oracle stores the empty key as NULL, so it holds no local admin lock")
    def test_upgrade_keeps_the_permanent_one_of_two_locks_of_a_local_admin(self, flask_app) -> None:
        # Locked again after the update but before this migration, a local admin has a lock under both keys.
        self._upgrade_to_parent([self._lock_row("", "admin", "", "admin-internal"),
                                 self._lock_row("~internal", "admin", "~internal", "admin-internal",
                                                lock_expires_at=datetime(2030, 1, 1))])

        self._upgrade()

        assert self._admin_locks() == {("~internal", "admin", "~internal", None, "POLICY")}

    @pytest.mark.skipif(is_oracle(), reason="Oracle stores the empty key as NULL, so it holds no local admin lock")
    def test_upgrade_keeps_the_placeholder_lock_when_two_locks_of_a_local_admin_last_equally_long(
            self, flask_app) -> None:
        self._upgrade_to_parent([self._lock_row("", "admin", "", "admin-internal"),
                                 self._lock_row("~internal", "admin", "~internal", "admin-internal",
                                                lock_cause="MANUAL")])

        self._upgrade()

        assert self._admin_locks() == {("~internal", "admin", "~internal", None, "MANUAL")}

    @pytest.mark.skipif(is_oracle(), reason="Oracle stores the empty key as NULL, so it holds no local admin lock")
    def test_upgrade_runs_again_after_stopping_once_the_weaker_lock_is_dropped(self, flask_app) -> None:
        self._upgrade_to_parent([self._lock_row("", "admin", "", "admin-internal"),
                                 self._lock_row("~internal", "admin", "~internal", "admin-internal",
                                                lock_expires_at=datetime(2030, 1, 1))])

        self._upgrade_failing_after(r"DELETE FROM user_lock_state")
        self._upgrade()

        assert self._admin_locks() == {("~internal", "admin", "~internal", None, "POLICY")}

    @pytest.mark.skipif(is_oracle(), reason="Oracle cannot store the empty key the downgrade restores")
    def test_downgrade_moves_a_local_admin_lock_back_to_the_empty_key(self, flask_app):
        self._upgrade_with([self._lock_row("~internal", "admin", "~internal", "admin-internal"), self._user_lock_row()])

        self._downgrade()

        assert self._lock_keys() == {("", "admin", ""), USER_LOCK}

    @pytest.mark.skipif(not is_oracle(), reason="Only Oracle drops the local admin locks on downgrade")
    def test_downgrade_drops_a_local_admin_lock_on_oracle(self, flask_app):
        self._upgrade_with([self._lock_row("~internal", "admin", "~internal", "admin-internal"), self._user_lock_row()])

        self._downgrade()

        assert self._lock_keys() == {USER_LOCK}
