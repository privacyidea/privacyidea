# Migration Test Data

This directory contains dialect-specific SQL seed files used by the migration
test suite: the v3.9 seed, which every migration test starts from, and the
release seeds (see "Release seeds" below).

## Naming convention

```
seed_v<version>_<revision>_<dialect>.sql
```

| Part | Example | Meaning |
|---|---|---|
| `version` | `v3.9` | privacyIDEA release the seed was generated from |
| `revision` | `5cb310101a1f` | Alembic revision ID the seed brings the DB to |
| `dialect` | `mariadb` / `mysql` / `postgresql` / `oracle` | Target database dialect |

Example: `seed_v3.9_5cb310101a1f_mariadb.sql`

The Oracle seed differs from the others in a few dialect-specific ways: Boolean
columns are `SMALLINT` (values `0`/`1`), there is no multi-row `VALUES` so each
row is its own `INSERT`, datetime literals use the ANSI `TIMESTAMP '...'` form,
and sequence-backed PKs use `DEFAULT <seq>.nextval` (so the sequences are
created before the tables). The migration test suite drives Oracle when
`TEST_DATABASE_URL` starts with `oracle` — `docker-compose.dev.yml` provides a
matching `oracle-test` (gvenzl/oracle-xe:21-slim) container.

MariaDB and MySQL both connect through the identical `mysql+pymysql://` URL
scheme, so `TEST_DATABASE_URL` alone cannot tell them apart. `get_seed_path()`
in `tests/migration_test_utils.py` picks between the `mariadb` and `mysql`
seed files by probing the live server's version string on first connect
(`migration_test_utils.is_mariadb()`), not by matching the URL.

The `mysql` seed's schema DDL is byte-identical to the `mariadb` one — both
are rendered from the generic, non-live `mysql+pymysql` dialect and diverge
only in the hand-extended data section, where the two engines are genuinely
incompatible:

* **Sequences.** MariaDB 10.3+ supports `CREATE SEQUENCE`; real MySQL never
  has, in any version. The `mariadb` seed bakes in one `CREATE SEQUENCE` per
  integer-PK table (see the comment above that section for why); the `mysql`
  seed omits the whole block, matching what a real MySQL install upgraded
  through this revision actually looks like.
* **Literal defaults on TEXT/BLOB/JSON columns.** MariaDB has allowed these
  since 10.2; real MySQL rejects them outright with `ERROR 1101`, even inside
  `CREATE TABLE IF NOT EXISTS` against an already-existing table. The three
  `LONGTEXT` `Value` columns (`tokeninfo`, `smsgatewayoption`,
  `customuserattribute`) drop their `DEFAULT ''` in the `mysql` seed.

## Release seeds

A release seed is a database that `pi-manage setup create_tables` of a release
created and the code of the release filled, dumped as SQL. It differs from the
v3.9 seed in what the tests need to see: the id columns have no default (only
privacyIDEA gives the id, from the sequence; MySQL uses `AUTO_INCREMENT`), the
container tables have identity columns, the constraints have the names the
database gave them, and the rows are the ones the release writes, including
u2f tokens, internal user attributes, SMS gateway secrets and SSH key tokens.

`tools/generate_release_seed.py` creates them against the database containers
of `compose-dev.yml`. It runs the release from `git archive` with the Python of
the current environment, encrypts with `tests/testdata/enckey` (the key of the
test configuration) and stamps the file name with the revision that
`create_tables` stamped:

```bash
for engine in postgresql mariadb mysql oracle; do
    python tools/generate_release_seed.py v3.13.4 3.13.4 $engine
done
```

3.14.0 was released from commit `0aa4afc4d`, not from the tag `v3.14`, which
was moved afterwards; its seeds are generated from that commit. The files are
not edited by hand. To change the data, change the fill step of the script and
generate them again. When a release is published, generate its seeds and add
its head revision to `RELEASE_HEADS` in `tests/migration_test_utils.py`.

## Generating the v3.9 seed

Use `tools/generate_seed_sql.py` to generate seeds from a historical version
of the models. The tool can load a single historical `models.py` (extracted
from a git tag) or the current split `models/` package:

```bash
# Extract a historical single-file models.py from a git tag:
git show v3.9.3:privacyidea/models.py > /tmp/models_v3.9.py

# Generate seeds for all dialects:
python tools/generate_seed_sql.py /tmp/models_v3.9.py mariadb \
    tests/testdata/migrations/seed_v3.9_5cb310101a1f_mariadb.sql
python tools/generate_seed_sql.py /tmp/models_v3.9.py mysql \
    tests/testdata/migrations/seed_v3.9_5cb310101a1f_mysql.sql
python tools/generate_seed_sql.py /tmp/models_v3.9.py postgresql \
    tests/testdata/migrations/seed_v3.9_5cb310101a1f_postgresql.sql

# From the current split models/ package instead of a historical tag:
python tools/generate_seed_sql.py privacyidea/models/ postgresql out.sql
```

The tool emits the schema DDL (the Oracle dialect also injects
`DEFAULT <seq>.nextval` on sequence-backed PK columns); the committed seeds were
then hand-extended with representative `INSERT` rows, `START WITH` values on the
MariaDB sequences (omitted entirely for MySQL — see above), and the
`alembic_version` stamp.

The DDL comes from the models without a database, so it is not the DDL of an
installation: on MariaDB the ids are `AUTO_INCREMENT`, because the dialect has
no connection that tells it about sequences, and on PostgreSQL and Oracle the
ids default to the next value of their sequence, which the seed added by hand.
A database that `create_tables` created has no such defaults. That is what the
release seeds are for.

## Updating the seed pin

The seed is currently pinned at **v3.9 / `5cb310101a1f`**.  If the pin ever
needs to move forward (e.g. the window becomes too large to test efficiently),
generate new seeds for the new revision and update `START_REVISION` in both
`tests/test_migrations.py` and `tests/migration_test_utils.py`.

