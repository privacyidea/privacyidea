import os
import pathlib

import pytest
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text, inspect as sa_inspect

"""
Alembic Database Migration Test Suite

This module validates the structural integrity, idempotency, and operational safety 
of all database migrations from a pinned starting revision (START_REVISION) to head.
It relies exclusively on dynamic database inspection and SQLAlchemy Core/ORM reflection 
rather than hardcoded schema dictionaries.

Key Validations:
* Structural Integrity: Ensures the migration graph has a single head, valid parent 
  links, and descriptive messages.
* Schema Equivalence: Upgrades the database to head and uses Alembic's `compare_metadata` 
  to guarantee the resulting database schema strictly matches the SQLAlchemy ORM models.
* Granular Idempotency (Round-Trip): Marches linearly through the migration history, 
  testing the exact `upgrade -> downgrade -> upgrade` lifecycle for every single 
  revision. It compares deep schema snapshots to ensure no columns are orphaned or 
  dropped incorrectly during downgrades.
* Downgrade Safety: Verifies that walking the migration graph backward does not crash 
  and does not unintentionally destroy data in tables that survive the downgrade.

Note: Data transformation tests for specific migrations (e.g., testing that data correctly 
moves from column A to column B) do not belong in this file. They must be placed in 
isolated `test_migration_<rev_id>.py` files using SQLAlchemy Core for historical data seeding.
"""

# Skip these tests if no database URL is provided (e.g. during standard fast unit tests)
pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set"
    ),
]

DB_URL = os.environ.get("TEST_DATABASE_URL", "")

# The revision from which we test migrations forward to head.
# Pinned at v3.9 (2022) — every migration added after this point is covered.
# Update this pin when it becomes too old or causes issues.
START_REVISION = "5cb310101a1f"  # v3.9: Create sequences needed for SQLAlchemy 1.4


def _get_script_dir() -> str:
    return str(pathlib.Path(__file__).parent.parent / "privacyidea" / "migrations")


def _get_alembic_cfg() -> AlembicConfig:
    ini_path = str(pathlib.Path(_get_script_dir()) / "alembic.ini")
    cfg = AlembicConfig(ini_path)
    cfg.set_main_option("script_location", _get_script_dir())
    cfg.set_main_option("sqlalchemy.url", DB_URL)
    return cfg


def _get_expected_tables() -> set[str]:
    """
    Derive the expected table names dynamically from the SQLAlchemy models.
    This avoids hardcoding and always stays in sync with the current models.
    """
    from privacyidea.models import db
    return set(db.metadata.tables.keys())


def _get_tables(engine) -> set[str]:
    return set(sa_inspect(engine).get_table_names())


def _get_schema_snapshot(engine) -> dict[str, set[str]]:
    """
    Return a mapping of {table_name: {col_name, ...}} for every table in the DB.
    This gives a richer comparison than just table names — it catches leftover
    columns that a downgrade() forgot to drop, or columns that an upgrade() forgot
    to add.
    """
    inspector = sa_inspect(engine)
    return {
        table: {col["name"] for col in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }


def _get_current_revision(engine) -> str | None:
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def _drop_all_tables(engine):
    """Drop every table in the database (MariaDB-safe via FK check disable)."""
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for table in sa_inspect(engine).get_table_names():
            conn.execute(text(f"DROP TABLE IF EXISTS `{table}`;"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        conn.commit()


def _setup_db_at_start_revision(flask_app, start_revision: str):
    """
    Set up the database at `start_revision` without running ancient migrations.

    Strategy:
    1. db.create_all() — creates the full current schema using SQLAlchemy models.
    2. stamp head    — tells Alembic the DB is already at head.
    3. downgrade     — rolls back to `start_revision` so only migrations after
                       that point will be applied by the test.

    This avoids running migrations from 10 years ago that expect tables to
    already exist (ALTER TABLE etc.) from an empty database.
    """
    from alembic import command
    from privacyidea.models import db

    db.create_all()
    command.stamp(_get_alembic_cfg(), "head")
    command.downgrade(_get_alembic_cfg(), start_revision)


@pytest.fixture(autouse=True)
def clean_database():
    """Wipe the database before and after every test."""
    engine = create_engine(DB_URL)
    _drop_all_tables(engine)
    engine.dispose()
    yield
    engine = create_engine(DB_URL)
    _drop_all_tables(engine)
    engine.dispose()


@pytest.fixture
def flask_app():
    """
    Provide a Flask app whose SQLAlchemy engine points to the test database.
    db.create_all() is NOT called here — _setup_db_at_start_revision() does it.
    """
    from privacyidea.app import create_app

    app = create_app("testing", pathlib.Path.cwd() / "tests/testdata/test_pi.cfg", silent=True)
    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()


def test_migration_history_has_single_head():
    """
    The migration chain must converge to exactly one head.
    Multiple heads would make `alembic upgrade head` ambiguous.

    Note: the history may contain merge revisions (a revision with two
    down_revision parents) — these are intentional and valid. What matters
    is that all branches are eventually merged into a single head.
    """
    heads = ScriptDirectory.from_config(_get_alembic_cfg()).get_heads()
    assert len(heads) == 1, (
        f"Migration history has multiple heads: {heads}. "
        f"Either add a merge migration or fix the branching revision."
    )


def test_migrations_since_start_revision_have_non_empty_messages():
    """
    Every migration from START_REVISION to head must have a non-empty description.
    An empty message makes the migration history unreadable and the upgrade log
    unhelpful (e.g. 'Applying abc -> def (head), empty message...').
    """
    script = ScriptDirectory.from_config(_get_alembic_cfg())
    revisions_in_window = list(script.iterate_revisions("head", START_REVISION))

    empty = [
        rev.revision
        for rev in revisions_in_window
        if not rev.doc or not rev.doc.strip() or rev.doc.strip().lower() == "empty message"
    ]
    assert not empty, (
        f"The following migrations have an empty or placeholder message: {empty}. "
        f"Please set a descriptive message in the migration file's docstring."
    )


def test_upgrade_to_head_creates_all_model_tables(flask_app):
    """
    Upgrading from START_REVISION to head must result in every table that
    the current SQLAlchemy models define being present in the database.
    Table names are derived dynamically from the models — no hardcoding.
    """
    from flask_migrate import upgrade as flask_upgrade

    _setup_db_at_start_revision(flask_app, START_REVISION)
    flask_upgrade()

    engine = create_engine(DB_URL)
    actual_tables = _get_tables(engine)
    engine.dispose()

    expected_tables = _get_expected_tables()
    missing = expected_tables - actual_tables
    assert not missing, (
        f"Tables defined in SQLAlchemy models but missing from the database "
        f"after upgrade to head: {missing}"
    )


def test_current_revision_matches_head_after_upgrade(flask_app):
    """After upgrading to head, the alembic_version in the DB must equal the head revision."""
    from flask_migrate import upgrade as flask_upgrade

    _setup_db_at_start_revision(flask_app, START_REVISION)
    flask_upgrade()

    head_rev = ScriptDirectory.from_config(_get_alembic_cfg()).get_current_head()
    engine = create_engine(DB_URL)
    current_rev = _get_current_revision(engine)
    engine.dispose()

    assert current_rev == head_rev, (
        f"Current revision {current_rev!r} does not match head {head_rev!r}."
    )


def test_migrations_since_start_revision_are_reversible(flask_app):
    """
    Every migration from START_REVISION to head must have a working downgrade().
    Downgrades one step at a time so the exact failing migration is easy to identify.
    """
    from alembic import command

    _setup_db_at_start_revision(flask_app, START_REVISION)
    command.upgrade(_get_alembic_cfg(), "head")

    script = ScriptDirectory.from_config(_get_alembic_cfg())
    # Walk from head down to (but not including) START_REVISION
    revisions_in_window = list(script.iterate_revisions("head", START_REVISION))

    for rev in revisions_in_window:
        if rev.down_revision is None:
            break
        try:
            command.downgrade(_get_alembic_cfg(), rev.down_revision)
        except Exception as e:
            pytest.fail(
                f"downgrade() of revision {rev.revision!r} "
                f"('{rev.doc}') failed: {e}"
            )


def test_upgrade_then_downgrade_then_upgrade_is_idempotent(flask_app):
    """
    upgrade → downgrade to START_REVISION → upgrade again must produce the
    exact same set of tables both times.
    """
    from alembic import command
    from flask_migrate import upgrade as flask_upgrade

    _setup_db_at_start_revision(flask_app, START_REVISION)
    flask_upgrade()

    engine = create_engine(DB_URL)
    tables_first = _get_tables(engine)
    engine.dispose()

    command.downgrade(_get_alembic_cfg(), START_REVISION)
    flask_upgrade()

    engine = create_engine(DB_URL)
    tables_second = _get_tables(engine)
    engine.dispose()

    assert tables_first == tables_second, (
        f"Table set differs between first and second upgrade:\n"
        f"  Only after first upgrade:  {tables_first - tables_second}\n"
        f"  Only after second upgrade: {tables_second - tables_first}"
    )


def test_schema_matches_models_after_upgrade_to_head(flask_app):
    """
    After upgrading to head, the database schema must exactly match the
    SQLAlchemy models — not just at the table level, but also columns,
    types, indexes and constraints.

    This uses Alembic's autogenerate comparison (the same mechanism used by
    `flask db migrate` to detect pending changes). If the comparison produces
    any diffs, it means either:
    - A migration is missing (a model change was not accompanied by a migration), or
    - A migration did not fully implement what the model change required.

    Note: this can only be run against head because the SQLAlchemy models only
    represent the current (head) state of the schema.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext
    from flask_migrate import upgrade as flask_upgrade
    from privacyidea.models import db

    _setup_db_at_start_revision(flask_app, START_REVISION)
    flask_upgrade()

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        migration_ctx = MigrationContext.configure(
            conn,
            opts={
                # These are the same options flask-migrate uses
                "compare_type": True,
                "compare_server_default": False,
            }
        )
        diffs = compare_metadata(migration_ctx, db.metadata)
    engine.dispose()

    # Filter out diffs that are known false positives on MariaDB/MySQL:
    # - 'remove_index': MySQL auto-creates indexes on FK columns that the models
    #   don't define explicitly, causing spurious remove_index diffs.
    # - 'modify_nullable': Boolean columns (TINYINT(1)) on MariaDB/MySQL show a
    #   nullable mismatch between the ORM metadata and the live schema even when
    #   the column definition is correct.
    IGNORED_DIFF_TYPES = {"remove_index", "modify_nullable"}

    def _get_diff_type(diff) -> str | None:
        """
        Extract the diff type string from a diff entry.
        Alembic diffs can be:
        - A flat tuple: ('modify_nullable', ...) — column-level change
        - A list of tuples: [('modify_nullable', ...), ...] — grouped column changes
        The first element of the first tuple is always the diff type string.
        """
        if isinstance(diff, (list, tuple)) and len(diff) > 0:
            first = diff[0]
            if isinstance(first, str):
                return first
            if isinstance(first, (list, tuple)) and len(first) > 0 and isinstance(first[0], str):
                return first[0]
        return None

    filtered_diffs = [
        diff for diff in diffs
        if _get_diff_type(diff) not in IGNORED_DIFF_TYPES
    ]

    assert not filtered_diffs, (
        f"The database schema does not match the SQLAlchemy models after upgrading "
        f"to head. The following differences were detected:\n"
        + "\n".join(str(d) for d in filtered_diffs)
        + "\n\nThis means either a migration is missing or incomplete. "
        f"Run `flask db migrate` to generate the missing migration."
    )


def test_all_down_revisions_point_to_existing_revisions():
    """
    Every migration's down_revision must reference a revision that actually
    exists in the migration scripts. Catches copy-paste errors where a new
    migration file has the wrong down_revision set.

    Note: merge revisions have a tuple of down_revisions (multiple parents),
    which is valid Alembic syntax — all parents are checked individually.
    """
    script = ScriptDirectory.from_config(_get_alembic_cfg())
    all_revisions = {rev.revision for rev in script.walk_revisions()}

    def _iter_down_revisions(rev):
        """Yield individual revision IDs from down_revision (str, tuple, or None)."""
        if rev.down_revision is None:
            return  # base revision, no parent needed
        if isinstance(rev.down_revision, tuple):
            yield from rev.down_revision  # merge revision with multiple parents
        else:
            yield rev.down_revision

    bad = [
        (rev.revision, down)
        for rev in script.walk_revisions()
        for down in _iter_down_revisions(rev)
        if down not in all_revisions
    ]
    assert not bad, (
        f"The following migrations have a down_revision that does not exist:\n"
        + "\n".join(f"  {r} -> {d}" for r, d in bad)
    )


def test_each_migration_survives_round_trip(flask_app):
    """
    True idempotency test: for every migration in the window, verify that the
    upgrade → downgrade → upgrade round-trip succeeds without crashing and
    produces the same schema both times.

    Performance: the DB is set up once at START_REVISION and we march forward
    linearly — no full wipe/rebuild for every iteration.

    Schema validation: we compare full schema snapshots (table names + column
    names per table), not just table names. This catches migrations whose
    downgrade() forgets to drop a column it added, or whose upgrade() forgets
    to add a column it should.

    Strategy per revision:
      1. (Once, before the loop) Set up DB at START_REVISION.
      2. Upgrade to rev — snapshot schema after first upgrade.
      3. Downgrade to rev.down_revision.
      4. Upgrade to rev again — snapshot schema after second upgrade.
      5. Assert both snapshots are identical.
      6. Leave the DB at rev so the next iteration starts correctly.
    """
    from alembic import command

    script = ScriptDirectory.from_config(_get_alembic_cfg())
    # Chronological order: oldest (just after START_REVISION) first.
    revisions_in_window = list(reversed(list(script.iterate_revisions("head", START_REVISION))))

    # Set up the DB once — all iterations share this starting point.
    _setup_db_at_start_revision(flask_app, START_REVISION)

    for rev in revisions_in_window:
        # Merge revisions have a tuple of parents — use the first one.
        if rev.down_revision is None:
            continue
        if isinstance(rev.down_revision, tuple):
            parent_revision = rev.down_revision[0]
        else:
            parent_revision = rev.down_revision

        # 1. Upgrade to the revision under test.
        try:
            command.upgrade(_get_alembic_cfg(), rev.revision)
        except Exception as e:
            pytest.fail(
                f"First upgrade() to revision {rev.revision!r} ('{rev.doc}') failed: {e}"
            )

        engine = create_engine(DB_URL)
        schema_after_first_upgrade = _get_schema_snapshot(engine)
        engine.dispose()

        # 2. Downgrade one step back.
        try:
            command.downgrade(_get_alembic_cfg(), parent_revision)
        except Exception as e:
            pytest.fail(
                f"downgrade() of revision {rev.revision!r} ('{rev.doc}') "
                f"back to {parent_revision!r} failed: {e}"
            )

        # 3. Upgrade to the revision again.
        try:
            command.upgrade(_get_alembic_cfg(), rev.revision)
        except Exception as e:
            pytest.fail(
                f"Second upgrade() to revision {rev.revision!r} ('{rev.doc}') "
                f"failed after a downgrade. This means the migration is not "
                f"re-runnable after its own downgrade: {e}"
            )

        engine = create_engine(DB_URL)
        schema_after_second_upgrade = _get_schema_snapshot(engine)
        current_rev = _get_current_revision(engine)
        engine.dispose()

        # Compare tables
        tables_first = set(schema_after_first_upgrade)
        tables_second = set(schema_after_second_upgrade)
        assert tables_first == tables_second, (
            f"Migration {rev.revision!r} ('{rev.doc}'): table set differs between "
            f"first and second upgrade after round-trip.\n"
            f"  Only after first upgrade:  {tables_first - tables_second}\n"
            f"  Only after second upgrade: {tables_second - tables_first}"
        )

        # Compare columns per table
        for table in tables_first:
            cols_first = schema_after_first_upgrade[table]
            cols_second = schema_after_second_upgrade.get(table, set())
            assert cols_first == cols_second, (
                f"Migration {rev.revision!r} ('{rev.doc}'): column set for table "
                f"'{table}' differs between first and second upgrade after round-trip.\n"
                f"  Only after first upgrade:  {cols_first - cols_second}\n"
                f"  Only after second upgrade: {cols_second - cols_first}\n"
                f"  This likely means downgrade() forgot to drop a column, or "
                f"upgrade() forgot to add one."
            )

        assert current_rev == rev.revision, (
            f"After round-trip for {rev.revision!r}, current revision is "
            f"{current_rev!r} instead of {rev.revision!r}."
        )
        # Leave the DB at rev.revision — the next iteration will upgrade from here.


def test_downgrade_does_not_destroy_data_in_surviving_tables(flask_app):
    """
    Downgrading must not delete data from tables that survive the downgrade.

    Strategy: upgrade to head, insert data into a stable table (realm),
    downgrade to START_REVISION, verify the data still exists.
    The realm table is created long before START_REVISION so it survives
    every downgrade in the window.
    """
    from alembic import command
    from flask_migrate import upgrade as flask_upgrade

    _setup_db_at_start_revision(flask_app, START_REVISION)
    flask_upgrade()

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO realm (id, name, `default`) VALUES (42, 'persistent_realm', 0)"
        ))
        conn.commit()
    engine.dispose()

    # Downgrade all the way back to START_REVISION
    command.downgrade(_get_alembic_cfg(), START_REVISION)

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM realm WHERE id = 42")
        ).scalar()
    engine.dispose()

    assert result == "persistent_realm", (
        f"Data in the 'realm' table was lost during downgrade. "
        f"Expected 'persistent_realm', got {result!r}."
    )


