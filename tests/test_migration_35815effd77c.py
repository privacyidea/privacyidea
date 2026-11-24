"""
Data transformation test for migration 35815effd77c
Remove the policy actions of the u2f token type.

upgrade()   — removes "enrollU2F" and the "u2f_" actions from the action string of every policy that has other
              actions too, and deletes a policy whose actions are all u2f actions with its conditions and description.
              An active admin or user policy of this kind stays if no other active policy of its scope remains.
downgrade() — does not add the actions back and does not restore the deleted policies
"""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from tests.migration_test_utils import MigrationTestBase, quote_identifier

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

ACTIONS_NOT_GRANTED = ("policydelete", "configwrite", "enrollHOTP")


class TestMigration35815effd77c(MigrationTestBase):
    REVISION = "35815effd77c"
    PARENT_REVISION = "ad07c259b5c1"

    def _action(self, engine: Engine, policy_id: int) -> str:
        column = quote_identifier("action")
        return self._fetch_scalar(engine, f"SELECT {column} FROM policy WHERE id = :id", {"id": policy_id})

    def _count(self, engine: Engine, table: str, column: str, value: int) -> int:
        return self._fetch_scalar(engine, f"SELECT COUNT(*) FROM {table} WHERE {quote_identifier(column)} = :value",
                                  {"value": value})

    def _deactivate_the_seed_policies(self, engine: Engine) -> None:
        """Deactivate the policies of the seed, so that the test decides which policies are active."""
        with engine.connect() as connection:
            connection.execute(text(f"UPDATE policy SET {quote_identifier('active')} = :active"), {"active": False})
            connection.commit()

    @staticmethod
    def _printed_names(output: str, before: str, after: str) -> set[str]:
        """The policy names that the upgrade printed between *before* and *after* on one line."""
        for line in output.splitlines():
            if before in line:
                return set(line.split(before, 1)[1].split(after, 1)[0].split(", "))
        return set()

    @staticmethod
    def _admin_rights(admin_user: str) -> list[str]:
        """The rights that the policies give the local administrator *admin_user* in the WebUI."""
        from privacyidea.lib.config import invalidate_config_object
        from privacyidea.lib.policy import SCOPE, PolicyClass
        from privacyidea.models import db
        invalidate_config_object()
        try:
            return PolicyClass().ui_get_rights(SCOPE.ADMIN, realm=None, username=admin_user)
        finally:
            # End the read transaction, so that the cleanup of the database is not blocked by its table locks
            db.session.rollback()

    def test_upgrade_removes_the_u2f_policy_actions(self, flask_app, capsys):
        """The actions of the u2f token type are removed, every other action keeps its value, including an escaped
        comma, and a policy without u2f actions is not changed."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "policy", [
                {"id": 901, "name": "u2f_enroll", "scope": "enrollment", "active": True, "priority": 1,
                 "action": "u2f_facets=example.com example.org, max_token_per_user=3, u2f_req=*,"
                           " challenge_text=Hello\\, world, -u2f_no_verify_certificate"},
                {"id": 902, "name": "u2f_admin", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F, enrollHOTP, u2f_max_token_per_user=1"},
                {"id": 903, "name": "untouched", "scope": "enrollment", "active": True, "priority": 1,
                 "action": "max_token_per_user=2,otp_pin_minlength=4"},
            ])
            capsys.readouterr()

            self._upgrade()

            assert self._action(engine, 901) == "max_token_per_user=3, challenge_text=Hello\\, world"
            assert self._action(engine, 902) == "enrollHOTP"
            assert self._action(engine, 903) == "max_token_per_user=2,otp_pin_minlength=4"
            changed_names = self._printed_names(capsys.readouterr().out, "from the policies ", ".")
            # A seed can hold policies with u2f actions too
            assert {"u2f_admin", "u2f_enroll"} <= changed_names, changed_names
            assert "untouched" not in changed_names
        finally:
            engine.dispose()

    def test_upgrade_deletes_a_policy_with_only_u2f_actions(self, flask_app, capsys):
        """
        A policy whose actions are all u2f actions, also negated or with an empty part, is deleted with its conditions
        and its description: in a scope other than admin and user, when it is inactive, and when another active
        policy of its scope remains.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._deactivate_the_seed_policies(engine)
            self._insert_rows(engine, "policy", [
                {"id": 904, "name": "u2f_only_admin", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F", "adminuser": "helpdesk"},
                {"id": 905, "name": "u2f_only_authorization", "scope": "authorization", "active": True,
                 "priority": 1, "action": "u2f_facets=example.com example.org", "adminuser": ""},
                {"id": 906, "name": "u2f_only_enrollment", "scope": "enrollment", "active": True, "priority": 1,
                 "action": "u2f_req=*, -u2f_no_verify_certificate, ", "adminuser": ""},
                {"id": 907, "name": "u2f_only_user_inactive", "scope": "user", "active": False, "priority": 1,
                 "action": "enrollU2F", "adminuser": ""},
                {"id": 908, "name": "other_admin", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollHOTP", "adminuser": "other"},
            ])
            self._insert_rows(engine, "policycondition", [
                {"id": 901, "policy_id": 904, "section": "userinfo", "Key": "groups", "comparator": "contains",
                 "Value": "helpdesk", "active": True},
            ])
            self._insert_rows(engine, "description", [
                {"id": 901, "object_id": 904, "object_type": "policy", "description": "U2F for the helpdesk"},
            ])
            capsys.readouterr()

            self._upgrade()

            for policy_id in (904, 905, 906, 907):
                assert self._count(engine, "policy", "id", policy_id) == 0, policy_id
            assert self._count(engine, "policycondition", "policy_id", 904) == 0
            assert self._count(engine, "description", "object_id", 904) == 0
            assert self._action(engine, 908) == "enrollHOTP"
            output = capsys.readouterr().out
            assert self._printed_names(output, "Deleted the policies ", ". ") == {
                "u2f_only_admin", "u2f_only_authorization", "u2f_only_enrollment", "u2f_only_user_inactive"}
            assert "WARNING" not in output
        finally:
            engine.dispose()

    def test_upgrade_keeps_the_last_active_admin_and_user_policies(self, flask_app, capsys):
        """
        An active admin or user policy whose actions are all u2f actions keeps its action string if no other active
        policy of its scope remains. An inactive policy does not count, a policy that keeps other actions does.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._deactivate_the_seed_policies(engine)
            self._insert_rows(engine, "policy", [
                {"id": 911, "name": "helpdesk_u2f", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F", "adminuser": "helpdesk"},
                {"id": 912, "name": "other_u2f", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F", "adminuser": "other"},
                {"id": 913, "name": "inactive_admin", "scope": "admin", "active": False, "priority": 1,
                 "action": "enrollHOTP", "adminuser": ""},
                {"id": 914, "name": "u2f_user", "scope": "user", "active": True, "priority": 1,
                 "action": "enrollU2F", "adminuser": ""},
                {"id": 915, "name": "hotp_and_u2f_user", "scope": "user", "active": True, "priority": 1,
                 "action": "enrollHOTP, enrollU2F", "adminuser": ""},
            ])
            capsys.readouterr()

            self._upgrade()

            assert self._action(engine, 911) == "enrollU2F"
            assert self._action(engine, 912) == "enrollU2F"
            assert self._action(engine, 913) == "enrollHOTP"
            assert self._count(engine, "policy", "id", 914) == 0
            assert self._action(engine, 915) == "enrollHOTP"
            output = capsys.readouterr().out
            assert self._printed_names(output, "WARNING: The policies ", " only hold") == {"helpdesk_u2f", "other_u2f"}
            assert self._printed_names(output, "Deleted the policies ", ". ") == {"u2f_user"}
        finally:
            engine.dispose()

    def test_deleted_policy_grants_no_other_right(self, flask_app):
        """
        An administrator whose only admin policy allowed u2f enrollment gets no other right after the upgrade, because
        the other admin policies keep the scope restricted.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._deactivate_the_seed_policies(engine)
            self._insert_rows(engine, "policy", [
                {"id": 921, "name": "helpdesk_u2f", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F", "adminuser": "helpdesk"},
                {"id": 922, "name": "other_admin", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollHOTP", "adminuser": "other"},
            ])

            self._upgrade()

            assert self._count(engine, "policy", "id", 921) == 0
        finally:
            engine.dispose()

        rights = self._admin_rights("helpdesk")
        assert not set(ACTIONS_NOT_GRANTED) & set(rights), rights

    def test_kept_last_policy_grants_no_right(self, flask_app):
        """
        If the only active admin policy allowed u2f enrollment, it stays after the upgrade, so no administrator gets
        the rights that an admin scope without active policy gives.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._deactivate_the_seed_policies(engine)
            self._insert_rows(engine, "policy", [
                {"id": 931, "name": "helpdesk_u2f", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F", "adminuser": "helpdesk"},
            ])

            self._upgrade()

            assert self._action(engine, 931) == "enrollU2F"
        finally:
            engine.dispose()

        for admin_user in ("helpdesk", "other"):
            rights = self._admin_rights(admin_user)
            assert not set(ACTIONS_NOT_GRANTED) & set(rights), (admin_user, rights)

    def test_upgrade_runs_again_after_failing_in_the_delete(self, flask_app):
        """
        The upgrade that stopped after it deleted the description of the first policy, but not the policy itself,
        deletes all policies with only u2f actions when it runs again.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "policy", [
                {"id": 941, "name": "u2f_only_first", "scope": "enrollment", "active": True, "priority": 1,
                 "action": "u2f_req=*"},
                {"id": 942, "name": "u2f_only_second", "scope": "enrollment", "active": True, "priority": 1,
                 "action": "u2f_req=*"},
            ])
            self._insert_rows(engine, "description", [
                {"id": 941, "object_id": 941, "object_type": "policy", "description": "first"},
                {"id": 942, "object_id": 942, "object_type": "policy", "description": "second"},
            ])
        finally:
            engine.dispose()

        self._upgrade_failing_after(r"DELETE FROM description\b")
        engine = self._engine()
        try:
            assert self._count(engine, "policy", "id", 941) + self._count(engine, "policy", "id", 942) == 2
            assert (self._count(engine, "description", "object_id", 941)
                    + self._count(engine, "description", "object_id", 942)) == 1
        finally:
            engine.dispose()

        self._upgrade()

        engine = self._engine()
        try:
            for policy_id in (941, 942):
                assert self._count(engine, "policy", "id", policy_id) == 0, policy_id
                assert self._count(engine, "description", "object_id", policy_id) == 0, policy_id
        finally:
            engine.dispose()

    def test_downgrade_does_not_restore_the_policies(self, flask_app):
        """The downgrade keeps the policies as they are after the upgrade."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_rows(engine, "policy", [
                {"id": 951, "name": "u2f_and_hotp", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F, enrollHOTP"},
                {"id": 952, "name": "u2f_only", "scope": "admin", "active": True, "priority": 1,
                 "action": "enrollU2F"},
            ])
            self._upgrade()

            self._downgrade()

            assert self._action(engine, 951) == "enrollHOTP"
            assert self._count(engine, "policy", "id", 952) == 0
        finally:
            engine.dispose()
