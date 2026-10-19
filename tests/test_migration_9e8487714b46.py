"""
Schema test for migration 9e8487714b46
Add an index on tokenrealm (realm_id, token_id).

upgrade()   — adds the index, unless an index on these two columns exists already
downgrade() — removes the index again
"""

import os

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from tests.migration_test_utils import MigrationTestBase

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

REALM_TOKEN_COLUMNS = ["realm_id", "token_id"]


class TestMigration9e8487714b46(MigrationTestBase):
    REVISION = "9e8487714b46"
    PARENT_REVISION = "f8a498439814"

    @staticmethod
    def _index_columns(engine: Engine) -> list[list[str]]:
        return [index["column_names"] for index in inspect(engine).get_indexes("tokenrealm")]

    def test_upgrade_adds_the_index_and_downgrade_removes_it(self, flask_app):
        """The upgrade adds the index on (realm_id, token_id), the downgrade removes it."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            assert REALM_TOKEN_COLUMNS not in self._index_columns(engine)

            self._upgrade()
            assert REALM_TOKEN_COLUMNS in self._index_columns(engine)

            self._downgrade()
            assert REALM_TOKEN_COLUMNS not in self._index_columns(engine)
        finally:
            engine.dispose()

    def test_upgrade_keeps_an_existing_index(self, flask_app):
        """An index on the two columns that exists already, e.g. created by hand, is kept and not added twice."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            with engine.begin() as connection:
                connection.exec_driver_sql("CREATE INDEX ix_by_hand ON tokenrealm (realm_id, token_id)")

            self._upgrade()
            assert self._index_columns(engine).count(REALM_TOKEN_COLUMNS) == 1
        finally:
            engine.dispose()
