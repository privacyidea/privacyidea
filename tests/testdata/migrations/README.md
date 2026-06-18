# Migration Test Data

This directory contains dialect-specific SQL seed files used by the migration
test suite.

## Naming convention

```
seed_v<version>_<revision>_<dialect>.sql
```

| Part | Example | Meaning |
|---|---|---|
| `version` | `v3.9` | privacyIDEA release the seed was generated from |
| `revision` | `5cb310101a1f` | Alembic revision ID the seed brings the DB to |
| `dialect` | `mariadb` / `postgresql` / `oracle` | Target database dialect |

Example: `seed_v3.9_5cb310101a1f_mariadb.sql`

The Oracle seed differs from the others in a few dialect-specific ways: Boolean
columns are `SMALLINT` (values `0`/`1`), there is no multi-row `VALUES` so each
row is its own `INSERT`, datetime literals use the ANSI `TIMESTAMP '...'` form,
and sequence-backed PKs use `DEFAULT <seq>.nextval` (so the sequences are
created before the tables). The migration test suite drives Oracle when
`TEST_DATABASE_URL` starts with `oracle` — `docker-compose.dev.yml` provides a
matching `oracle-test` (gvenzl/oracle-xe:21-slim) container.

## Generating seeds

Use `tools/generate_seed_sql.py` to generate seeds from a historical version
of the models.  The tool can target a git tag or work from a local file:

```bash
# From a git tag (e.g. v3.9) using the single historical models.py:
python tools/generate_seed_sql.py \
    --git-tag v3.9 \
    --file privacyidea/models.py \
    --dialect mariadb \
    --revision 5cb310101a1f \
    --output tests/testdata/migrations/

# From the current split models directory:
python tools/generate_seed_sql.py \
    --dir privacyidea/models/ \
    --dialect postgresql \
    --revision 5cb310101a1f \
    --output tests/testdata/migrations/
```

The tool emits the schema DDL (the Oracle dialect also injects
`DEFAULT <seq>.nextval` on sequence-backed PK columns); the committed seeds were
then hand-extended with representative `INSERT` rows, `START WITH` values on the
sequences, and the `alembic_version` stamp.

## Updating the seed pin

The seed is currently pinned at **v3.9 / `5cb310101a1f`**.  If the pin ever
needs to move forward (e.g. the window becomes too large to test efficiently),
generate new seeds for the new revision and update `START_REVISION` in both
`tests/test_migrations.py` and `tests/migration_test_utils.py`.

