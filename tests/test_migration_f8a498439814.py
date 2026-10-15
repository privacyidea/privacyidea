"""
Data transformation test for migration f8a498439814
v3.14.1: Remove the value of boolean policy actions that are stored with a value other than true, and duplicates

upgrade()   — removes the earlier occurrences of an action given more than once, keeping the last one, and the
              value of a boolean action whose value is not true, like ``policywrite=False`` or
              ``triggerchallenge=hotp``, so it stays enabled
downgrade() — keeps the cleaned actions, they mean the same in every version

Boolean actions with a true value, the actions of other types and an action next to its exclusion are untouched.
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
    905: ("admin", "triggerchallenge=hotp, enable=true, disable=1, set=, revoke=TRUE"),
    906: ("container", "container_ssl_verify=False"),
    907: ("webui", "policywrite=False"),
    908: ("admin", "policywrite=hotp, policywrite=false"),
    909: ("admin", "policywrite=hotp, -policywrite"),
    910: ("authentication", "otppin=userstore, passOnNoToken, otppin=token"),
    911: ("admin", "enable, enable"),
    912: ("admin", "enable, policywrite = False"),
    913: ("admin", "policywrite= true , policydelete= False "),
}

EXPECTED = {
    901: "enable, policywrite, policydelete, importtokens",
    902: "otppin=userstore, passOnNoToken",
    903: "*, policywrite",
    904: "challenge_text=Hello\\, enter the OTP, passOnNoUser",
    # A value that is neither true nor false and an empty value are removed, the true values stay
    905: "triggerchallenge, enable=true, disable=1, set, revoke=TRUE",
    # An action of another type keeps "False"
    906: "container_ssl_verify=False",
    # The name is not a boolean action of this scope
    907: "policywrite=False",
    # Of an action given more than once only the last occurrence stays, it is the one the policy matching reads
    908: "policywrite",
    # An action and its exclusion are different actions
    909: "policywrite, -policywrite",
    910: "passOnNoToken, otppin=token",
    # A policy without any value is cleaned up as well
    911: "enable",
    # The key "policywrite " with the whitespace never matched, the policy stays as it is
    912: "enable, policywrite = False",
    # The whitespace around a value is no part of the key, the true value stays and the false value is removed
    913: "policywrite= true , policydelete",
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

    def test_upgrade_drops_bool_action_values(self, flask_app):
        """upgrade() removes the values of the boolean actions that are not true and leaves the rest."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_policies(engine)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_all_actions(engine) == EXPECTED
        engine.dispose()

    def test_upgrade_leaves_seed_policies_untouched(self, flask_app):
        """
        upgrade() runs on the seed data without changing its policies. They use no real scope name and no action given
        more than once, so this only guards against a failing upgrade, the cases above cover the cleanup itself.
        """
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

    def test_downgrade_keeps_actions_without_value(self, flask_app):
        """downgrade() keeps the actions without value, and upgrading again changes nothing."""
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
