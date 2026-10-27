"""
Data transformation test for migration 35815effd77c
Remove the policy actions of the u2f token type.

upgrade()   — removes "enrollU2F" and the "u2f_" actions from the action string of every policy that has other
              actions too, and keeps a policy whose actions are all u2f actions as it is
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

    def test_upgrade_keeps_a_policy_with_only_u2f_actions(self, flask_app):
        """A policy whose actions are all u2f actions, also negated or with an empty part, keeps its action string."""
        only_u2f_actions = {
            904: "enrollU2F",
            905: "u2f_facets=example.com example.org",
            906: "u2f_req=*, -u2f_no_verify_certificate, ",
        }
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "policy", [
                {"id": 904, "name": "u2f_only_admin", "scope": "admin", "active": True, "priority": 1,
                 "action": only_u2f_actions[904]},
                {"id": 905, "name": "u2f_only_authorization", "scope": "authorization", "active": True,
                 "priority": 1, "action": only_u2f_actions[905]},
                {"id": 906, "name": "u2f_only_enroll", "scope": "enroll", "active": True, "priority": 1,
                 "action": only_u2f_actions[906]},
            ])

            self._upgrade()

            for policy_id, action in only_u2f_actions.items():
                assert self._action(engine, policy_id) == action
        finally:
            engine.dispose()

    def test_policy_with_only_u2f_actions_allows_no_other_action(self, flask_app):
        """
        After the upgrade, an admin policy that only allowed u2f enrollment matches none of the actions of this
        version, so the administrator it names gets no other right.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "policy", [
                {"id": 907, "name": "helpdesk_u2f", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F", "adminuser": "helpdesk"},
                {"id": 908, "name": "other_admin", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollHOTP", "adminuser": "other"},
            ])

            self._upgrade()
        finally:
            engine.dispose()

        from privacyidea.lib.config import invalidate_config_object
        from privacyidea.lib.policy import SCOPE, PolicyClass
        from privacyidea.models import db
        invalidate_config_object()
        try:
            for action in ("policydelete", "configwrite", "enrollHOTP"):
                matching = PolicyClass().list_policies(scope=SCOPE.ADMIN, action=action, adminuser="helpdesk",
                                                       active=True)
                assert matching == [], (action, matching)
        finally:
            # End the read transaction, so that the cleanup of the database is not blocked by its table locks
            db.session.rollback()

    def test_downgrade_keeps_the_policies(self, flask_app):
        """The downgrade keeps the policies as they are after the upgrade."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "policy", [
                {"id": 909, "name": "u2f_and_hotp", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F, enrollHOTP"},
                {"id": 910, "name": "u2f_only", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F"},
            ])
            self._upgrade()

            self._downgrade()

            assert self._action(engine, 909) == "enrollHOTP"
            assert self._action(engine, 910) == "enrollU2F"
        finally:
            engine.dispose()
