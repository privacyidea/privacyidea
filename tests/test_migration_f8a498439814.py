"""
Data transformation test for migration f8a498439814
v3.14.1: Store boolean policy actions saved with a false value as excluded actions

upgrade()   — rewrites a boolean action with the value false (in any case) or 0 to the excluded action ``-<action>``
downgrade() — keeps the excluded actions, they mean the same in every version

Boolean actions with a true, empty or any other value and the actions of other types are untouched.
"""

import os

import pytest
from sqlalchemy import text

from tests.migration_test_utils import MigrationTestBase, quote_identifier

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

# The ids and names do not collide with the policies of the seed
POLICIES = {
    901: ("admin", "enable, policywrite=False, policydelete=false, importtokens=FALSE"),
    902: ("authentication", "otppin=userstore, passOnNoToken=0"),
    903: ("admin", "*, policywrite=False"),
    904: ("authentication", "challenge_text=Hello\\, enter the OTP, passOnNoUser=False"),
    905: ("admin", "triggerchallenge=hotp, enable=true, disable=1, set="),
    906: ("container", "container_ssl_verify=False"),
    907: ("webui", "policywrite=False"),
}

EXPECTED = {
    901: "enable, -policywrite, -policydelete, -importtokens",
    902: "otppin=userstore, -passOnNoToken",
    903: "*, -policywrite",
    904: "challenge_text=Hello\\, enter the OTP, -passOnNoUser",
    # A value that is neither true nor false, a true and an empty value stay as they are
    905: "triggerchallenge=hotp, enable=true, disable=1, set=",
    # An action of another type keeps "False"
    906: "container_ssl_verify=False",
    # The name is not a boolean action of this scope
    907: "policywrite=False",
}


class TestMigrationF8a498439814(MigrationTestBase):
    REVISION = "f8a498439814"
    PARENT_REVISION = "35815effd77c"

    def _insert_policies(self, engine) -> None:
        self._insert_rows(engine, "policy", [
            {"id": policy_id, "active": True, "name": f"bool_value_{policy_id}", "scope": scope, "action": action,
             "realm": "", "priority": 1}
            for policy_id, (scope, action) in POLICIES.items()
        ])

    def _fetch_action(self, engine, policy_id: int) -> str | None:
        return self._fetch_scalar(engine, f"SELECT {quote_identifier('action')} FROM policy WHERE id = :id",
                                  {"id": policy_id})

    def _fetch_all_actions(self, engine) -> dict:
        return {policy_id: self._fetch_action(engine, policy_id) for policy_id in POLICIES}

    def test_upgrade_excludes_false_bool_actions(self, flask_app):
        """upgrade() turns the boolean actions with a false value into excluded actions and leaves the rest."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_policies(engine)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_all_actions(engine) == EXPECTED
        engine.dispose()

    def test_upgrade_leaves_seed_policies_untouched(self, flask_app):
        """upgrade() does not change the policies of the seed, which contain no boolean action with a false value."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        query = f"SELECT id, {quote_identifier('action')} FROM policy ORDER BY id"
        with engine.connect() as conn:
            before = conn.execute(text(query)).fetchall()
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        with engine.connect() as conn:
            after = conn.execute(text(query)).fetchall()
        engine.dispose()
        assert after == before

    def test_downgrade_keeps_excluded_actions(self, flask_app):
        """downgrade() keeps the excluded actions, and upgrading again changes nothing."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_policies(engine)
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_all_actions(engine) == EXPECTED
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_all_actions(engine) == EXPECTED
        engine.dispose()
