"""
Data transformation test for migration 7d4e9b2c1a3f
Add internaluserattribute table and migrate internal entries out of customuserattribute

The migration:
- creates the new ``internaluserattribute`` table
- copies rows with Key='fido2_user_id' from ``customuserattribute`` into it
  (Value preserved as a JSON string)
- consolidates rows with Key matching 'last_used_token_<user_agent>' into a
  single new row per user with Key='last_used_token' and a JSON dict value
  ``{<user_agent>: <token_type>, ...}``
- deletes the migrated rows from ``customuserattribute``

upgrade()   — moves the two internal-state keys out of customuserattribute
              into the new table.
downgrade() — copies them back (last_used_token dict is exploded back into
              the per-user-agent prefix keys) and drops the new table.

Rows with unrelated Keys must be untouched in both directions.
"""

import json
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


def _q(col: str) -> str:
    return f'"{col}"' if is_postgres() else f"`{col}`"


PI_INTERNAL = "pi_internal"  # value the pre-migration code wrote into customuserattribute.Type
                             # for last_used_token_<agent> rows. The migration filters on it
                             # so that prefix-collision admin rows are left untouched.


class TestMigration7d4e9b2c1a3f(MigrationTestBase):
    REVISION = "7d4e9b2c1a3f"
    PARENT_REVISION = "b1a2c3d4e5f6"

    # ---- helpers ----------------------------------------------------------

    def _insert_custom(self, engine, rows: list[dict]) -> None:
        """Insert rows into customuserattribute. Each row needs at least
        user_id, resolver, Key, Value; realm_id defaults to NULL."""
        normalized = []
        for r in rows:
            normalized.append({
                "user_id": r["user_id"],
                "resolver": r.get("resolver", "resolver1"),
                "realm_id": r.get("realm_id"),
                "Key": r["Key"],
                "Value": r["Value"],
                "Type": r.get("Type"),
            })
        self._insert_rows(engine, "customuserattribute", normalized)

    def _fetch_custom_value(self, engine, user_id: str, key: str) -> str | None:
        return self._fetch_scalar(
            engine,
            f"SELECT {_q('Value')} FROM customuserattribute "
            f"WHERE user_id = :uid AND {_q('Key')} = :key",
            {"uid": user_id, "key": key},
        )

    def _fetch_custom_count(self, engine, user_id: str, key: str) -> int:
        return self._fetch_scalar(
            engine,
            f"SELECT COUNT(*) FROM customuserattribute "
            f"WHERE user_id = :uid AND {_q('Key')} = :key",
            {"uid": user_id, "key": key},
        )

    def _fetch_internal_value(self, engine, user_id: str, key: str):
        """Return the parsed JSON value of an internaluserattribute row."""
        raw = self._fetch_scalar(
            engine,
            f"SELECT {_q('Value')} FROM internaluserattribute "
            f"WHERE user_id = :uid AND {_q('Key')} = :key",
            {"uid": user_id, "key": key},
        )
        if raw is None:
            return None
        # Postgres returns JSON columns already parsed (dict/list/str/...);
        # MariaDB returns a JSON-encoded string that still needs decoding.
        if not isinstance(raw, str):
            return raw
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw

    def _fetch_internal_count(self, engine, user_id: str, key: str) -> int:
        return self._fetch_scalar(
            engine,
            f"SELECT COUNT(*) FROM internaluserattribute "
            f"WHERE user_id = :uid AND {_q('Key')} = :key",
            {"uid": user_id, "key": key},
        )

    # ---- upgrade ----------------------------------------------------------

    def test_upgrade_moves_fido2_user_id(self, flask_app):
        """upgrade() must copy fido2_user_id rows into internaluserattribute and
        remove them from customuserattribute."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "fido2_user_id", "Value": "abc123base64url"},
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_internal_value(engine, "u1", "fido2_user_id") == "abc123base64url"
        assert self._fetch_custom_count(engine, "u1", "fido2_user_id") == 0, (
            "upgrade() must remove migrated fido2_user_id rows from customuserattribute"
        )
        engine.dispose()

    def test_upgrade_consolidates_last_used_token(self, flask_app):
        """upgrade() must merge all last_used_token_<agent> rows for a single
        user into one internaluserattribute row with a JSON dict value."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "last_used_token_privacyidea-cp", "Value": "push", "Type": PI_INTERNAL},
            {"user_id": "u1", "Key": "last_used_token_privacyIDEA-Keycloak", "Value": "hotp", "Type": PI_INTERNAL},
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        consolidated = self._fetch_internal_value(engine, "u1", "last_used_token")
        assert consolidated == {
            "privacyidea-cp": "push",
            "privacyIDEA-Keycloak": "hotp",
        }
        # Old per-user-agent rows are gone.
        assert self._fetch_custom_count(engine, "u1", "last_used_token_privacyidea-cp") == 0
        assert self._fetch_custom_count(engine, "u1", "last_used_token_privacyIDEA-Keycloak") == 0
        # And there is exactly one consolidated row in the new table.
        assert self._fetch_internal_count(engine, "u1", "last_used_token") == 1
        engine.dispose()

    def test_upgrade_keeps_per_user_separation(self, flask_app):
        """upgrade() must produce one consolidated row per (user_id, resolver, realm_id),
        not merge entries across users."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "last_used_token_app-a", "Value": "hotp", "Type": PI_INTERNAL},
            {"user_id": "u2", "Key": "last_used_token_app-a", "Value": "totp", "Type": PI_INTERNAL},
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_internal_value(engine, "u1", "last_used_token") == {"app-a": "hotp"}
        assert self._fetch_internal_value(engine, "u2", "last_used_token") == {"app-a": "totp"}
        engine.dispose()

    def test_upgrade_leaves_other_keys_untouched(self, flask_app):
        """upgrade() must not touch rows with unrelated Keys."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "department", "Value": "engineering"},
            {"user_id": "u1", "Key": "last_used_token", "Value": "legacy-bare-key"},  # bare key, no suffix
            {"user_id": "u1", "Key": "fido2_user_id", "Value": "should-move"},
            # Admin-created row that happens to share the last_used_token_ prefix
            # but has no Type marker — must NOT be consumed by the migration.
            {"user_id": "u1", "Key": "last_used_token_admin-note", "Value": "do-not-touch"},
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_custom_value(engine, "u1", "department") == "engineering"
        # The bare 'last_used_token' key (without underscore suffix) is NOT internal —
        # the migration only matches 'last_used_token_%'.
        assert self._fetch_custom_value(engine, "u1", "last_used_token") == "legacy-bare-key"
        # Prefix-collision admin row (no Type marker) is preserved.
        assert self._fetch_custom_value(engine, "u1", "last_used_token_admin-note") == "do-not-touch"
        # fido2_user_id moved out.
        assert self._fetch_custom_count(engine, "u1", "fido2_user_id") == 0
        engine.dispose()

    def test_upgrade_is_idempotent(self, flask_app):
        """The data-migration step must survive being re-run.

        Production retry scenario: upgrade() crashes between the INSERT into
        ``internaluserattribute`` and the DELETE from ``customuserattribute``.
        The operator re-runs the migration; old rows are still present, new
        rows already exist. A naive INSERT would hit the UNIQUE constraint
        and abort.
        """
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "fido2_user_id", "Value": "abc123"},
            {"user_id": "u1", "Key": "last_used_token_app-a", "Value": "hotp", "Type": PI_INTERNAL},
        ])
        engine.dispose()

        # First run — full upgrade.
        self._upgrade()

        # Simulate partial-failure recovery: re-insert the old rows as if the
        # DELETE step had never run, then re-execute the data migration step.
        engine = self._engine()
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "fido2_user_id", "Value": "abc123"},
            {"user_id": "u1", "Key": "last_used_token_app-a", "Value": "hotp", "Type": PI_INTERNAL},
        ])
        import importlib
        mig = importlib.import_module(
            "privacyidea.migrations.versions.7d4e9b2c1a3f_internaluserattribute"
        )
        with engine.connect() as conn:
            mig._run_data_migration(conn)
            conn.commit()
        engine.dispose()

        # End state: still exactly one row per key in the new table, and the
        # re-inserted old rows have been cleaned up.
        engine = self._engine()
        assert self._fetch_internal_count(engine, "u1", "fido2_user_id") == 1
        assert self._fetch_internal_count(engine, "u1", "last_used_token") == 1
        assert self._fetch_internal_value(engine, "u1", "fido2_user_id") == "abc123"
        assert self._fetch_internal_value(engine, "u1", "last_used_token") == {"app-a": "hotp"}
        assert self._fetch_custom_count(engine, "u1", "fido2_user_id") == 0
        assert self._fetch_custom_count(engine, "u1", "last_used_token_app-a") == 0
        engine.dispose()

    # ---- downgrade --------------------------------------------------------

    def test_downgrade_restores_fido2_user_id(self, flask_app):
        """downgrade() must copy fido2_user_id back into customuserattribute."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "fido2_user_id", "Value": "abc123"},
        ])
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_custom_value(engine, "u1", "fido2_user_id") == "abc123"
        engine.dispose()

    def test_downgrade_explodes_last_used_token_dict(self, flask_app):
        """downgrade() must explode the consolidated last_used_token dict back
        into per-user-agent rows in customuserattribute."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "last_used_token_app-a", "Value": "push", "Type": PI_INTERNAL},
            {"user_id": "u1", "Key": "last_used_token_app-b", "Value": "hotp", "Type": PI_INTERNAL},
        ])
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_custom_value(engine, "u1", "last_used_token_app-a") == "push"
        assert self._fetch_custom_value(engine, "u1", "last_used_token_app-b") == "hotp"
        engine.dispose()

    def test_round_trip_preserves_unrelated_rows(self, flask_app):
        """An upgrade → downgrade round-trip must leave unrelated rows in
        customuserattribute unchanged."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_custom(engine, [
            {"user_id": "u1", "Key": "department", "Value": "engineering"},
            {"user_id": "u1", "Key": "fido2_user_id", "Value": "xyz"},
            {"user_id": "u1", "Key": "last_used_token_app-a", "Value": "hotp", "Type": PI_INTERNAL},
        ])
        engine.dispose()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_custom_value(engine, "u1", "department") == "engineering"
        engine.dispose()
