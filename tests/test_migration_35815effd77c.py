"""
Data transformation test for migration 35815effd77c
Remove the policy actions of the u2f token type.

upgrade()   — removes "enrollU2F" and the "u2f_" actions from the action string of every policy
downgrade() — does not add them back
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


class TestMigration35815effd77c(MigrationTestBase):
    REVISION = "35815effd77c"
    PARENT_REVISION = "ad07c259b5c1"

    def _action(self, engine: Engine, policy_id: int) -> str:
        column = quote_identifier("action")
        return self._fetch_scalar(engine, f"SELECT {column} FROM policy WHERE id = :id", {"id": policy_id})

    def test_upgrade_removes_the_u2f_policy_actions(self, flask_app):
        """The actions of the u2f token type are removed, every other action keeps its value, including an escaped
        comma, and a policy without u2f actions is not changed."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "policy", [
                {"id": 901, "name": "u2f_enroll", "scope": "enroll", "active": True, "priority": 1,
                 "action": "u2f_facets=example.com example.org, max_token_per_user=3, u2f_req=*,"
                           " challenge_text=Hello\\, world, -u2f_no_verify_certificate"},
                {"id": 902, "name": "u2f_admin", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F, enrollHOTP, u2f_max_token_per_user=1"},
                {"id": 903, "name": "untouched", "scope": "enroll", "active": True, "priority": 1,
                 "action": "max_token_per_user=2,otp_pin_minlength=4"},
            ])

            self._upgrade()

            assert self._action(engine, 901) == "max_token_per_user=3, challenge_text=Hello\\, world"
            assert self._action(engine, 902) == "enrollHOTP"
            assert self._action(engine, 903) == "max_token_per_user=2,otp_pin_minlength=4"
        finally:
            engine.dispose()

    def test_downgrade_keeps_the_policies(self, flask_app):
        """The downgrade keeps the policies as they are after the upgrade."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "policy", [
                {"id": 904, "name": "u2f_only", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F"},
            ])
            self._upgrade()

            self._downgrade()

            assert self._action(engine, 904) in ("", None)
        finally:
            engine.dispose()
