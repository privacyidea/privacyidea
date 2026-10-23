"""
Downgrade test for migration c128c01a5520
v3.11: Added token container template table and a 'template' column in the token container table.

downgrade() — drops the foreign key of tokencontainer.template_id under the name the database has for it, then the
              column and the tokencontainertemplate table

A database imported from another database engine can carry the foreign key under another name than the one upgrade()
gives it.
"""

import os

import pytest
from sqlalchemy import Engine, inspect as sa_inspect, text

from tests.migration_test_utils import MigrationTestBase, is_oracle, is_postgres

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


class TestMigrationC128c01a5520(MigrationTestBase):
    REVISION = "c128c01a5520"
    PARENT_REVISION = "7301d5130c3a"

    @staticmethod
    def _rename_template_foreign_key(engine: Engine) -> None:
        if is_postgres() or is_oracle():
            statements = ["ALTER TABLE tokencontainer RENAME CONSTRAINT tokencontainertemplate_id "
                          "TO fk_imported_template"]
        else:
            statements = ["ALTER TABLE tokencontainer DROP FOREIGN KEY tokencontainertemplate_id",
                          "ALTER TABLE tokencontainer ADD CONSTRAINT fk_imported_template FOREIGN KEY (template_id) "
                          "REFERENCES tokencontainertemplate (id)"]
        with engine.connect() as conn:
            for statement in statements:
                conn.execute(text(statement))
            conn.commit()

    def test_downgrade_finds_a_renamed_template_foreign_key(self, flask_app):
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
        finally:
            engine.dispose()
        self._upgrade()
        engine = self._engine()
        try:
            self._rename_template_foreign_key(engine)
        finally:
            engine.dispose()

        self._downgrade()

        engine = self._engine()
        try:
            inspector = sa_inspect(engine)
            assert "tokencontainertemplate" not in {name.lower() for name in inspector.get_table_names()}
            assert "template_id" not in {column["name"].lower() for column in inspector.get_columns("tokencontainer")}
        finally:
            engine.dispose()
