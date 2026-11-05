"""
Test for migration 7e3010cbe03e
v3.14.1: Move every id sequence past the highest id of its table

upgrade()   — moves every sequence that is behind the highest id of its table to the id after it; a sequence that is
              further ahead stays. Nothing on MySQL. On Oracle, this includes the sequences that c7f1a2b3d4e5 sets as
              default of the id column of the container tables.
downgrade() — leaves the sequences where they are

That no sequence is behind its table at head, from every seed, is checked by
test_every_sequence_is_ahead_of_its_table_at_head in test_migrations.py.
"""

import os

import pytest
from sqlalchemy import Engine, text

from privacyidea.models.db import build_restart_sequence_sql
from tests.migration_test_utils import (MigrationTestBase, insert_rows, is_oracle, next_sequence_value,
                                        quote_identifier, sequences_behind_their_table)

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


def _policy(name: str, **columns: object) -> dict:
    return dict({"active": True, "name": name, "scope": "admin", "action": "tokenlist", "realm": "", "priority": 1},
                **columns)


class TestMigration7e3010cbe03e(MigrationTestBase):
    REVISION = "7e3010cbe03e"
    PARENT_REVISION = "4aec628f7ef2"

    def _skip_without_sequences(self, engine: Engine) -> None:
        with engine.connect() as conn:
            if not conn.dialect.supports_sequences:
                pytest.skip("MySQL has no sequences, the migration changes nothing there")

    def _next_policy_id(self, engine: Engine) -> int:
        with engine.connect() as conn:
            next_id = next_sequence_value(conn, "policy_seq")
            conn.commit()
        return next_id

    def _load_with_policy_sequence_behind(self) -> int:
        """
        Load the seed up to the parent and add a policy whose id the sequence has not handed out yet, as from
        AUTO_INCREMENT next to it. Return that id.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._skip_without_sequences(engine)
            highest_id = self._next_policy_id(engine) + 10
            insert_rows(engine, "policy", [_policy("ahead_of_the_sequence", id=highest_id)])
        finally:
            engine.dispose()
        return highest_id

    def test_upgrade_moves_a_sequence_that_is_behind_past_the_highest_id(self, flask_app):
        highest_id = self._load_with_policy_sequence_behind()

        self._upgrade()

        engine = self._engine()
        try:
            assert self._next_policy_id(engine) > highest_id
            assert not sequences_behind_their_table(engine)
        finally:
            engine.dispose()

    def test_upgrade_leaves_a_sequence_that_is_ahead(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._skip_without_sequences(engine)
            with engine.connect() as conn:
                conn.exec_driver_sql(build_restart_sequence_sql("policy_seq", 7000, conn.dialect.name))
                conn.commit()
        finally:
            engine.dispose()

        self._upgrade()

        engine = self._engine()
        try:
            assert self._next_policy_id(engine) >= 7000
        finally:
            engine.dispose()

    def test_upgrade_runs_again_after_failing_midway(self, flask_app):
        highest_id = self._load_with_policy_sequence_behind()

        self._upgrade_failing_after(r"ALTER SEQUENCE policy_seq\b")
        self._upgrade()

        engine = self._engine()
        try:
            assert self._next_policy_id(engine) > highest_id
            assert not sequences_behind_their_table(engine)
        finally:
            engine.dispose()

    def test_downgrade_leaves_the_sequences(self, flask_app):
        highest_id = self._load_with_policy_sequence_behind()

        self._upgrade()
        self._downgrade()

        engine = self._engine()
        try:
            assert self._next_policy_id(engine) > highest_id
        finally:
            engine.dispose()

    @pytest.mark.skipif(not is_oracle(), reason="Only Oracle gets a sequence as default of the container ids")
    def test_upgrade_moves_a_container_default_sequence_that_is_behind(self, flask_app):
        """
        On an Oracle database whose container tables had no identity, c7f1a2b3d4e5 makes a sequence the default of the
        id column. A row with an id ahead of that sequence must not block the next insert after the upgrade.
        """
        default_column = quote_identifier("default")
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE tokencontainertemplate MODIFY (id DROP IDENTITY)"))
                highest_id = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM tokencontainertemplate")).scalar() + 10
                conn.execute(text("CREATE SEQUENCE tokencontainertemplate_seq START WITH 1"))
                conn.execute(text("ALTER TABLE tokencontainertemplate "
                                  "MODIFY (id DEFAULT tokencontainertemplate_seq.nextval)"))
                conn.execute(text(f"INSERT INTO tokencontainertemplate (id, options, name, container_type, "
                                  f"{default_column}) VALUES (:id, '', 'ahead_of_the_sequence', 'generic', 0)"),
                             {"id": highest_id})
                conn.commit()
        finally:
            engine.dispose()

        self._upgrade()

        engine = self._engine()
        try:
            with engine.connect() as conn:
                conn.execute(text(f"INSERT INTO tokencontainertemplate (options, name, container_type, "
                                  f"{default_column}) VALUES ('', 'after_the_upgrade', 'generic', 0)"))
                new_id = conn.execute(text("SELECT id FROM tokencontainertemplate "
                                           "WHERE name = 'after_the_upgrade'")).scalar()
                conn.commit()
            assert new_id > highest_id
        finally:
            engine.dispose()
