# Migration Tests

This directory contains the migration test suite for privacyIDEA.

## Files

| File | Purpose |
|---|---|
| `test_migrations.py` | Structural integrity tests — run for every revision |
| `test_migration_<rev>.py` | Data-transformation tests — one file per migration that rewrites rows |
| `migration_test_utils.py` | Shared base class and helpers for all migration tests |

---

## When do you need a `test_migration_<rev>.py`?

**Only when the migration's `upgrade()` or `downgrade()` transforms existing
row data** — i.e. it contains SQL DML (`UPDATE`, `INSERT`, `DELETE`) or ORM
session writes against pre-existing rows.

### What `test_migrations.py` already covers (no extra test needed)

| Category | Example operations | How it's covered |
|---|---|---|
| **DDL** | `add_column`, `drop_column`, `create_table`, `drop_table`, `alter_column`, `add_index`, `drop_constraint` | `test_each_migration_survives_round_trip` — snapshots the schema before and after a downgrade→upgrade cycle for every revision |
| **Schema equivalence** | Any gap between migration output and ORM models | `test_schema_matches_models_after_upgrade_to_head` — uses Alembic's `compare_metadata` |
| **Reversibility** | `downgrade()` crashing | `test_migrations_since_start_revision_are_reversible` |
| **Data survival** | Rows deleted from tables that survive a downgrade | `test_downgrade_does_not_destroy_data_in_surviving_tables` |

### What requires a dedicated test

A migration that **rewrites values in existing rows** is not covered by any of
the above.  Examples:

- Fixing a typo: `UPDATE eventhandleroption SET Value='urlencoded' WHERE Value='urlendcode'`
- Moving data between columns: `UPDATE token SET foo = bar; ALTER TABLE token DROP COLUMN bar`
- Populating a new column from an existing one

---

## How to write a per-migration test

1. **Create** `tests/test_migration_<rev>.py`.

2. **Subclass** `MigrationTestBase` from `migration_test_utils.py`.
   Set `REVISION` and `PARENT_REVISION` as class constants.

3. **Use the inherited helpers** to set up and inspect database state:

   | Helper | What it does |
   |---|---|
   | `_load_seed_and_upgrade_to_parent(engine)` | Loads the v3.9 seed then upgrades to `PARENT_REVISION` |
   | `_insert_rows(engine, table, rows)` | Inserts a list of dicts; handles dialect quoting for `Key`/`Value` columns |
   | `_fetch_scalar(engine, query, params)` | Runs a query and returns the first column of the first row |
   | `_upgrade(target=None)` | Runs `alembic upgrade` to `REVISION` (or `target`) |
   | `_downgrade(target=None)` | Runs `alembic downgrade` to `PARENT_REVISION` (or `target`) |
   | `_engine()` | Returns a fresh `create_engine(DB_URL)` — caller must `.dispose()` |

4. **Mark** the module with `pytest.mark.migration` so the CI workflow picks it up.

5. **Add tests** for at least:
   - The happy path: `upgrade()` rewrites the right rows
   - Idempotent rows: rows that are already in the target shape are untouched
   - Unrelated rows: rows with different keys/tables are untouched
   - Downgrade: `downgrade()` correctly reverts the change
   - Round-trip: upgrade → downgrade leaves unrelated rows unchanged

### Skeleton

```python
"""
Data transformation test for migration <rev>
<Short description of what the migration does to existing data.>
"""

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


class TestMigrationAbcd1234(MigrationTestBase):
    REVISION = "abcd1234"
    PARENT_REVISION = "deadbeef"

    def test_upgrade_transforms_data(self, flask_app):
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_rows(engine, "some_table", [
            {"col_a": "old_value"},
        ])
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        result = self._fetch_scalar(engine, "SELECT col_a FROM some_table")
        assert result == "new_value"
        engine.dispose()
```

### Checking the seed for existing rows

The seed (`tests/testdata/migrations/`) may already contain rows in the tables
you want to test.  If adding duplicate rows would violate a unique constraint,
insert into a different parent record or use a different key.  See
`test_migration_7301d5130c3a.py` for a concrete example (eventhandler id=2 is
used because id=1 is already present in the seed).

---

## Running the tests

```bash
# Against MariaDB:
TEST_DATABASE_URL="mysql+pymysql://privacyidea:privacyidea@127.0.0.1:3306/privacyidea_test" \
    python -m pytest -m migration tests/test_migrations.py tests/test_migration_*.py -v

# Against PostgreSQL:
TEST_DATABASE_URL="postgresql+psycopg2://privacyidea:privacyidea@127.0.0.1:5432/privacyidea_test" \
    python -m pytest -m migration tests/test_migrations.py tests/test_migration_*.py -v
```

CI runs both dialects automatically via the `migration-tests.yml` workflow
whenever any of the following change:

- `privacyidea/migrations/**`
- `privacyidea/models/**`
- `tests/test_migrations.py`
- `tests/test_migration_*.py`
- `tests/testdata/migrations/**`

