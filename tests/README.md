# Migration Tests

This directory contains the migration test suite for privacyIDEA.

## Files

| File | Purpose |
|---|---|
| `test_migrations.py` | Structural integrity tests — run for every revision (needs a database; marked `migration`) |
| `test_migration_<rev>.py` | Data-transformation tests — one file per migration that rewrites rows |
| `migration_test_utils.py` | Shared base class and helpers for all migration tests |
| `test_migration_conventions.py` | Database-independent migration-file convention checks — run in the regular suite |
| `test_sequence_ddl.py` | Database-independent guards for Galera-/Oracle-safe sequence DDL — run in the regular suite |

> **Convention:** every migration from the pinned start revision onward must
> begin its docstring with the release that introduced it, e.g.
> `"""v3.13: Add column foo to table bar"""`. That first line is the message
> Alembic shows in `alembic history`. It is enforced by
> `test_migration_conventions.py`.
>
> **Lint:** `test_migration_conventions.py` also checks every migration since
> 3.14 against `LINT_RULES`:
>
> - An insert into a sequence-backed table takes its id from the sequence.
> - A check whether an object exists or is already gone uses reflection, not
>   the error text.
> - A database error is not printed and ignored.
> - Nothing is imported from `privacyidea.lib` or the models, apart from the
>   helper modules `privacyidea.models.db` and `privacyidea.models.utils`.
>
> `MIGRATION_LINT_EXCEPTIONS` lists the known exceptions. The test fails for an
> entry that no longer applies, so remove the entry together with the fix.
>
> The lint does not check the helper modules. A change to a helper changes
> every migration that calls it, also the released ones. Check the callers in
> `privacyidea/migrations/versions/` before you change a helper.

---

## What a passing run guarantees

A passing run of the migration and backup tests (`-m migration`, `-m backup`) on a database means, for that
database:

- The migration history is well formed: one head, every parent exists, every migration names its release, and the
  migrations since 3.14 follow the lint rules apart from the listed exceptions.
- The upgrade to head runs from the v3.9 seed and from the seed of every release in `RELEASE_HEADS`. At head, the
  schema matches the models, privacyIDEA can write a row into every table with the ids from its sequences, and no
  sequence hands out an id that already exists. A schema that `pi-manage setup create_tables` creates takes a row in
  every table, too.
- Every migration since 3.9 can go down and up again with the same columns, indexes, foreign keys and unique
  constraints. The full downgrade to 3.9 restores the schema of 3.9 and keeps the rows of the tables that stay.
- Every migration since a seed can run again on its own result, as after a failure or a stamp set back by hand,
  without changing the schema or any row (exceptions in `NOT_RERUNNABLE_REVISIONS`).
- A database of a release, upgraded to head and downgraded back, has the schema and every row of that release again,
  apart from the changes listed in `_expected_contents_after_downgrade`.
- The migrations with a test of their own convert the rows of that test correctly, leave other rows alone, run again
  after a stop at the statements the test chooses, and downgrade without losing data. They do so from every seed
  their migration has not run on yet.
- A backup of a database of privacyIDEA at head, made and restored with `pi-manage backup`, brings back every row,
  the stamp and the sequences. A backup from before an upgrade can be restored into the upgraded database, and the
  upgrade then runs again; on PostgreSQL that restore is a known, expected failure.

It does not guarantee:

- Anything about data the tests do not have. The data migrations only see the rows of the seeds and of the tests;
  an installation with other data, much more data or unusual values can still hit a case nobody tried.
- Anything about schema details the comparisons leave out. The comparison with the models ignores some kinds of
  differences per database (indexes, nullability and defaults in places, server defaults always, see
  `test_schema_matches_models_after_upgrade_to_head`). The comparisons before and after a downgrade look at columns
  by name, indexes, foreign keys and unique constraints, not at types, defaults or nullability.
- Anything about databases built in other ways: created by a release without a seed of its own and not upgraded
  from 3.9, moved over from another database engine, changed by hand, with another character set or collation, or
  run by a database version the CI does not test.
- That a migration runs again after a stop at any statement. That is tested only where a migration has a test of
  its own that stops it there.
- Anything about several nodes upgrading at the same time.
- How long a migration takes on a large database.
- That privacyIDEA itself works on the result: no test starts the application after an upgrade, or the older release
  after a downgrade.

---

## When do you need a `test_migration_<rev>.py`?

**Only when the migration's `upgrade()` or `downgrade()` transforms existing
row data** — i.e. it contains SQL DML (`UPDATE`, `INSERT`, `DELETE`) or ORM
session writes against pre-existing rows — **or when it creates several schema
objects one after the other**, e.g. a table and then its indexes. The generic
running-again test only repeats a migration on its complete result; a stop
between two of these statements needs `_upgrade_failing_after` in a test of its
own (see `test_migration_c8d9e0f1a2b3.py`).

### What `test_migrations.py` already covers (no extra test needed)

| Category | Example operations | How it's covered |
|---|---|---|
| **DDL** | `add_column`, `drop_column`, `create_table`, `drop_table`, `alter_column`, `add_index`, `drop_constraint` | `test_each_migration_survives_round_trip` — snapshots the schema before and after a downgrade→upgrade cycle for every revision |
| **Schema equivalence** | Any gap between migration output and ORM models | `test_schema_matches_models_after_upgrade_to_head` — uses Alembic's `compare_metadata`, from every seed |
| **Reversibility** | `downgrade()` crashing | `test_migrations_since_start_revision_are_reversible` |
| **Data survival** | Rows deleted from tables that survive a downgrade | `test_downgrade_does_not_destroy_data_in_surviving_tables` |
| **Running again** | `upgrade()` failing or changing the schema or the rows when it runs again on its own result (after a failure midway or a stamp set back by hand) | `test_each_migration_runs_again_on_its_own_result` — from every seed; known exceptions are listed in `NOT_RERUNNABLE_REVISIONS` |
| **Sequences ahead** | A sequence that hands out ids that already exist, because rows got their ids elsewhere (AUTO_INCREMENT, a data migration inserting rows without an id) | `test_every_sequence_is_ahead_of_its_table_at_head` — from every seed |
| **Downgrade to a release** | A database of a release, upgraded to head and downgraded back, differing from what it was | `test_downgrade_returns_the_database_of_a_release` — for every release in `RELEASE_HEADS`, from the v3.9 seed upgraded to the release and from the seed of the release; the changes a downgrade does not undo on purpose are listed in `_expected_contents_after_downgrade` |

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
   | `_load_seed_and_upgrade_to_parent(engine)` | Loads the seed of the test (see "Seeds, downgrades and id layouts") then upgrades to `PARENT_REVISION` |
   | `_insert_rows(engine, table, rows)` | Inserts a list of dicts; handles dialect quoting for `Key`/`Value` columns |
   | `_fetch_scalar(engine, query, params)` | Runs a query and returns the first column of the first row |
   | `_upgrade(target=None)` | Runs `alembic upgrade` to `REVISION` (or `target`) |
   | `_downgrade(target=None)` | Runs `alembic downgrade` to `PARENT_REVISION` (or `target`), leaving the revisions of a release seed applied |
   | `_upgrade_failing_after(pattern)` | Runs the upgrade to `REVISION` but stops it right after the first statement matching the regular expression, leaving what it did so far committed |
   | `_set_stamp_back_to_parent()` | Sets the stamp back to `PARENT_REVISION` without undoing the migration |
   | `_assert_every_table_accepts_a_row_at_head()` | Upgrades to head and inserts a row into every table the way the models do, ids from their sequences included |
   | `_engine()` | Returns a fresh `create_engine(DB_URL)` — caller must `.dispose()` |

4. **Mark** the module with `pytest.mark.migration` so the CI workflow picks it up.

5. **Add tests** for at least:
   - The happy path: `upgrade()` rewrites the right rows
   - Idempotent rows: rows that are already in the target shape are untouched
   - Unrelated rows: rows with different keys/tables are untouched
   - Running again: after `_upgrade_failing_after(...)` at each step of the data conversion, or after
     `_set_stamp_back_to_parent()`, a second `_upgrade()` succeeds and converts nothing twice
   - Downgrade: `downgrade()` correctly reverts the change, and fails instead
     of dropping data it could not copy back
   - Round-trip: upgrade → downgrade leaves unrelated rows unchanged
   - Writing afterwards: a migration that inserts rows ends one test with
     `_assert_every_table_accepts_a_row_at_head()`. A row that got its id from
     another source than the model uses makes the next row privacyIDEA writes
     collide with it.

   A test can read through the models or the lib after the upgrade. The
   cleanup ends the transaction of the session before it drops the tables.

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

The seeds (`tests/testdata/migrations/`) already contain rows in many tables,
the release seeds in most of them. If adding duplicate rows would violate a
unique constraint, insert into a different parent record or use a different
key. See `test_migration_7301d5130c3a.py` for a concrete example (eventhandler
id=2 is used because id=1 is already present in the seed). Count and compare
your own rows, not whole tables: a release seed has u2f tokens, challenges and
policies of its own.

---

## Seeds, downgrades and id layouts

`tests/testdata/migrations/` has two kinds of seeds:

- The v3.9 seed was written by hand. It stands for the databases that an older release created and the releases
  since upgraded. Every migration test starts from it.
- A release seed is a database that `pi-manage setup create_tables` of a release created and the code of the release
  filled, dumped per engine by `tools/generate_release_seed.py`. Its tables are built the way the release builds them
  on a new installation: the ids without defaults, the identity columns, the names of constraints. Its rows are the
  ones the release writes, including those the data migrations since convert.
  `test_schema_matches_models_after_upgrade_to_head`, `test_default_insert_succeeds_for_every_model_table` and
  `test_downgrade_returns_the_database_of_a_release` also start from it.

**When a release is published, generate its seeds** for all four engines (see the README in
`tests/testdata/migrations/`) **and add its head revision to `RELEASE_HEADS`**.

A downgrade takes a database back to the previous release: its schema is that release's again, and its data is what
it was, apart from what a migration cannot bring back. A downgrade that cannot copy data back fails instead of
dropping it. What a downgrade does not undo on purpose, for example deleted challenges, is said in the migration's
docstring and listed in `_expected_contents_after_downgrade` of `test_migrations.py`.

`test_downgrade_returns_the_database_of_a_release` proves this for every release in `RELEASE_HEADS`
(`migration_test_utils.py`): it takes a database of the release, adds data for the migrations since, upgrades it to
head, downgrades it back and compares the schema and the contents of every table. Add rows to `_release_dataset` for
every new data migration.

Head reaches 3.13.4 through a merge, so a database of 3.13.4 that runs a 3.14 migration has two revisions stamped,
for example `d3a4b5c6e7f8` and `a1e0ba6ad9dc`. Alembic downgrades by undoing every applied revision that descends from the
target. A downgrade to the parent `b1a2c3d4e5f6` therefore also undoes the two 3.13.4 migrations after the branch
point, and a downgrade to `d3a4b5c6e7f8` from head stops at the merge and leaves the 3.14 branch stamped next to it.
`downgrade_keeping(target, keep)` downgrades to the target and leaves the release's revisions applied, taking a
branch that is still stamped down on its own (`<revision>@-<steps>`). `MigrationTestBase._downgrade` and the
downgrade to a release use it.

The per-migration tests run from every seed their revision has not been applied to yet (`seeds_before`): the tests of
a 3.14 migration from the v3.9 seed and the 3.13.4 seed, those of a 3.14.1 migration also from the 3.14.0 seed. The
`seed` fixture says which. The id columns differ between them: the v3.9 seed gives them a default (`AUTO_INCREMENT` on
MariaDB, the sequence on PostgreSQL and Oracle), a release seed has none, and only privacyIDEA gives the id, from the
sequence (MySQL fills it with `AUTO_INCREMENT` in every seed). `_insert_rows` takes the ids from the sequences when
the test starts from a release seed. A migration that inserts rows without an id passes from the v3.9 seed and fails
from a release seed. The layouts stay different: the id columns get no sequence as their default,
because a table whose default uses a sequence cannot be restored from a dump on MariaDB (`LOCK TABLES` does not lock
the sequence) and keeps PostgreSQL from dropping the sequence. Migration 7e3010cbe03e moves every sequence past the
highest id of its table instead.

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

