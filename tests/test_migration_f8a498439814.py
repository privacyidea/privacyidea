"""
Data transformation test for migration f8a498439814
v3.14.1: Remove the value of boolean policy actions that are stored with a value other than true, and duplicates

upgrade()   — removes the earlier occurrences of an action given more than once, keeping the last one, and the
              value of a boolean action whose value is not true, like ``policywrite=False`` or
              ``triggerchallenge=hotp``, so it stays enabled. ``disable_client_token_deletion`` with a false value
              becomes the excluded action, as only the authenticator app applies it and reads the value.
downgrade() — keeps the cleaned actions, they mean the same in every version

Boolean actions with a true value, the actions of other types and an action next to its exclusion are untouched.
"""

import importlib
import os

import pytest
from sqlalchemy import text

from privacyidea.models.policy import parse_action_string
from tests.migration_test_utils import MigrationTestBase, quote_identifier

# The actions of the policies in the release seeds that the cleanup changes, by policy name
SEED_POLICIES_AFTER_CLEANUP = {
    "container_client": "-disable_client_token_deletion, initially_add_tokens_to_container=True",
    "user_tokens": "enrollHOTP=true, disable, setpin",
}

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
    914: ("admin", "policywrite=tRuE"),
    915: ("admin", "-policywrite=false"),
    916: ("admin", "policywrite=false, -policywrite"),
    917: ("admin", "policywrite=false, enable, policywrite"),
    918: ("admin", "enable, policywrite = true"),
    919: ("admin", "enable, this_action_is_gone"),
    920: ("admin", "policywrite=0"),
    921: ("admin", "policywrite, -policywrite"),
    922: ("admin", "policywrite=hotp, policywrite"),
    923: ("admin", "policywrite, policywrite=false"),
    924: ("admin", "this_action_is_gone"),
    925: ("admin", "policywrite=False"),
    926: ("admin", "policywrite=hotp"),
    927: ("admin", "policywrite="),
    928: ("admin", "policywrite=True"),
    929: ("admin", "policywrite=1"),
    930: ("admin", "policywrite, policywrite"),
    931: ("admin", "policywrite= true"),
    932: ("container", "disable_client_token_deletion=false, container_client_rollover=0, "
                       "initially_add_tokens_to_container=FALSE, disable_client_container_unregister=False"),
    933: ("container", "disable_client_token_deletion=true, container_client_rollover, "
                       "initially_add_tokens_to_container=hotp, hide_specific_error_message=false"),
    934: ("container", "disable_client_token_deletion=false, -disable_client_token_deletion"),
    935: ("container", "disable_client_token_deletion=false, disable_client_token_deletion"),
    936: ("container", "container_ssl_verify=False, disable_client_token_deletion= false "),
    937: ("admin", "disable_client_token_deletion=false"),
    938: ("user", "enrollHOTP=false, disable=hotp, enable"),
    939: ("enrollment", "hotp_force_app_pin=False, tokenlabel=<s>"),
    940: ("authorization", "no_detail_on_fail=false, tokentype=hotp totp"),
    941: ("register", "hide_specific_error_message=0"),
    942: ("token", "hide_specific_error_message_for_ttype=False"),
    943: ("hardening", "hide_version=false, hide_auth_error_status=hotp"),
    944: ("conditional_access", "show_default_ca_error_message=FALSE"),
    945: ("webui", "search_on_enter=false, logout_time=120"),
    946: ("authentication", "passkey_trigger_by_pin=false, otppin=userstore"),
    947: ("container", "disable_client_token_deletion=hotp"),
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
    # Only "1" and "true" in the cases is_true accepts are true values
    914: "policywrite",
    # An excluded action keeps its value, the matching ignores it
    915: "-policywrite=false",
    # The false value is removed, the action and its exclusion stay
    916: "policywrite, -policywrite",
    # The earlier occurrence is removed, the other actions stay in their order
    917: "enable, policywrite",
    # The key "policywrite " never matched, also not with a true value
    918: "enable, policywrite = true",
    # An unknown action stays, the migration does not check the actions
    919: "enable, this_action_is_gone",
    920: "policywrite",
    921: "policywrite, -policywrite",
    # The last occurrence stays, whether it has the value or the earlier one
    922: "policywrite",
    923: "policywrite",
    # A policy of an unknown action only stays as well
    924: "this_action_is_gone",
    925: "policywrite",
    926: "policywrite",
    927: "policywrite",
    928: "policywrite=True",
    929: "policywrite=1",
    930: "policywrite",
    # The whitespace before a true value stays, the migration only removes false values
    931: "policywrite= true",
    # Only the authenticator app applies disable_client_token_deletion and reads false and 0 as disabled, so it becomes
    # the exclusion. The server applies the other container client actions, they stay enabled.
    932: "-disable_client_token_deletion, container_client_rollover, initially_add_tokens_to_container, "
         "disable_client_container_unregister",
    # A true value stays, another value is removed like for the other boolean actions
    933: "disable_client_token_deletion=true, container_client_rollover, initially_add_tokens_to_container, "
         "hide_specific_error_message",
    # The exclusion is given already, it stays once
    934: "-disable_client_token_deletion",
    # The last occurrence is the one the policy uses
    935: "disable_client_token_deletion",
    # An action of another type keeps "False", the whitespace around the false value is no part of it
    936: "container_ssl_verify=False, -disable_client_token_deletion",
    # The name is not an action of this scope
    937: "disable_client_token_deletion=false",
    # The boolean actions of the other scopes lose the value, the actions of other types keep it
    938: "enrollHOTP, disable, enable",
    939: "hotp_force_app_pin, tokenlabel=<s>",
    940: "no_detail_on_fail, tokentype=hotp totp",
    941: "hide_specific_error_message",
    942: "hide_specific_error_message_for_ttype",
    943: "hide_version, hide_auth_error_status",
    944: "show_default_ca_error_message",
    945: "search_on_enter, logout_time=120",
    946: "passkey_trigger_by_pin, otppin=userstore",
    # A value that is neither true nor false is removed, the action stays enabled
    947: "disable_client_token_deletion",
}


def test_expected_actions_mean_what_the_stored_actions_meant():
    """
    Each expected action string parses to the actions of the stored one, with a boolean action that is not true
    enabled and an action the authenticator app applies excluded when it is false.
    """
    migration = importlib.import_module(
        "privacyidea.migrations.versions.f8a498439814_drop_values_of_bool_policy_actions")
    for policy_id, (scope, action) in POLICIES.items():
        bool_actions = migration.BOOL_ACTIONS.get(scope, frozenset())
        expected = {}
        for key, value in parse_action_string(action).items():
            if key in bool_actions and value is not True and value.strip() not in migration.TRUE_VALUES:
                if (scope == "container" and key in migration.APP_APPLIED_ACTIONS
                        and value.strip().lower() in migration.FALSE_VALUES):
                    key = f"-{key}"
                value = True
            expected[key] = value
        assert parse_action_string(EXPECTED[policy_id]) == expected, policy_id


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

    def test_upgrade_cleans_the_seed_policies(self, flask_app):
        """
        upgrade() changes the policies of the seed that have a boolean action with a value other than true, and no
        others. The v3.9 seed has none of them, the release seeds two (see SEED_POLICIES_AFTER_CLEANUP).
        """
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        query = f"SELECT name, {quote_identifier('action')} FROM policy ORDER BY name"
        with engine.connect() as conn:
            before = conn.execute(text(query)).fetchall()
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        with engine.connect() as conn:
            after = conn.execute(text(query)).fetchall()
        engine.dispose()
        assert after == [(name, SEED_POLICIES_AFTER_CLEANUP.get(name, action)) for name, action in before]

    def test_upgrade_leaves_empty_actions(self, flask_app):
        """upgrade() leaves a policy without actions as it is, Oracle stores the empty string as NULL."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_rows(engine, "policy", [
            {"id": policy_id, "active": True, "name": f"empty_action_{policy_id}", "scope": "container",
             "action": action, "realm": "", "priority": 1}
            for policy_id, action in [(990, None), (991, "")]
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_action(engine, 990) is None
        assert self._fetch_action(engine, 991) in ("", None)
        engine.dispose()

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
