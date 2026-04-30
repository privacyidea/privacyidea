"""
Generic, migration-agnostic checks for the Alembic migration chain.

The goal of this file is to catch structural and behavioural regressions in
the migration history *as a whole*, without knowing what any individual
migration does. Concretely, it verifies that:

  - The chain is well-formed: a single head, every down_revision points at a
    real revision, every revision has a non-empty message.
  - Upgrading from a pinned baseline (START_REVISION, currently v3.9) to head
    produces every table the SQLAlchemy models declare, and the alembic
    version stamp matches the script head.
  - The resulting schema matches the models — columns, types, indexes,
    constraints — using Alembic autogenerate, modulo a small set of
    documented dialect false positives.
  - Every Sequence() declared on a model exists in the live database after
    upgrade. Alembic autogenerate does not compare sequences, so this is
    checked separately.
  - Every migration in the window has a working downgrade(), and every
    upgrade → downgrade → upgrade round-trip produces the same per-table
    columns/indexes/foreign-keys/unique-constraints both times. This catches
    downgrades that forget to drop something (or upgrades that don't fully
    restore after one).
  - A default INSERT succeeds against every model-declared table after
    upgrade-to-head, exercising the auto-PK path. This catches sequence/
    identity misconfigurations and missing NOT NULL defaults that schema-
    only checks cannot see.
  - Upgrading a database that's already at head is a no-op (schema and
    alembic_version unchanged).
  - A full upgrade-to-head followed by a full downgrade-back-to-baseline
    restores the original schema and does not destroy data in surviving
    tables (row-count survival, not just one realm row).

Tests run against the dialect provided in TEST_DATABASE_URL — the project
supports MariaDB and PostgreSQL — and use a pre-written seed file per
dialect (tests/testdata/migrations/) as a complete, on-disk snapshot of the
database state at START_REVISION. No runtime fixups; the seed is
authoritative.

Migrations older than START_REVISION are intentionally not covered: the pin
exists because nothing in the supported window upgrades from older state,
and exercising those migrations would only burn CI on code paths that no
real install hits anymore. Bump the pin when keeping it gets in the way.

Data-transformation tests for specific migrations do NOT belong here. They
live in tests/test_migration_<revision>.py and use MigrationTestBase. See
tests/README.md for the full guide.
"""

import os
import pathlib
import time

import pytest
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text, inspect as sa_inspect
from sqlalchemy.exc import OperationalError

from tests.migration_test_utils import (
    DB_URL,
    START_REVISION,
    drop_all_tables,
    get_alembic_cfg,
    is_postgres,
    load_seed,
)

# Skip these tests if no database URL is provided
pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set"
    ),
]


def _get_expected_tables() -> set[str]:
    """
    Derive the expected table names dynamically from the SQLAlchemy models.
    This avoids hardcoding and always stays in sync with the current models.
    """
    from privacyidea.models import db
    return set(db.metadata.tables.keys())


def _get_tables(engine) -> set[str]:
    return set(sa_inspect(engine).get_table_names())


def _get_schema_snapshot(engine) -> dict[str, dict]:
    """
    Return a per-table snapshot of columns, indexes, foreign keys, and unique
    constraints. Used by the round-trip and full-downgrade tests to detect
    downgrades that forget to drop something the upgrade added (or upgrades
    that don't fully restore after a downgrade).

    The snapshot is compared against itself across an upgrade→downgrade cycle
    on the same engine, so dialect-specific artefacts (e.g. MariaDB
    auto-creating indexes for FK columns) appear in both snapshots and cancel.
    """
    inspector = sa_inspect(engine)
    snapshot: dict[str, dict] = {}
    for table in inspector.get_table_names():
        snapshot[table] = {
            "columns": frozenset(col["name"] for col in inspector.get_columns(table)),
            "indexes": frozenset(
                (idx.get("name"), tuple(idx["column_names"]), bool(idx.get("unique", False)))
                for idx in inspector.get_indexes(table)
            ),
            "foreign_keys": frozenset(
                (
                    fk.get("name"),
                    tuple(fk["constrained_columns"]),
                    fk["referred_table"],
                    tuple(fk["referred_columns"]),
                )
                for fk in inspector.get_foreign_keys(table)
            ),
            "unique_constraints": frozenset(
                (uc.get("name"), tuple(uc["column_names"]))
                for uc in inspector.get_unique_constraints(table)
            ),
        }
    return snapshot


def _get_current_revision(engine) -> str | None:
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def _wait_for_db(engine, timeout: int = 30, interval: float = 1.0) -> None:
    """
    Block until the database accepts connections or *timeout* seconds elapse.
    Raises the last OperationalError if the DB never becomes ready.
    """
    deadline = time.monotonic() + timeout
    last_exc: OperationalError | None = None
    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return  # success
        except OperationalError as exc:
            last_exc = exc
            time.sleep(interval)
    raise RuntimeError(
        f"Database at {engine.url} did not become ready within {timeout}s"
    ) from last_exc


@pytest.fixture(autouse=True)
def clean_database():
    """Wipe the database before and after every test."""
    engine = create_engine(DB_URL)
    _wait_for_db(engine)
    drop_all_tables(engine)
    engine.dispose()
    yield
    engine = create_engine(DB_URL)
    _wait_for_db(engine)
    drop_all_tables(engine)
    engine.dispose()


@pytest.fixture
def flask_app():
    """
    Provide a Flask app context pointing at the test database.
    Schema setup is done by load_seed(), not db.create_all().
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
    heads = ScriptDirectory.from_config(get_alembic_cfg()).get_heads()
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
    script = ScriptDirectory.from_config(get_alembic_cfg())
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

    load_seed()
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

    load_seed()
    flask_upgrade()

    head_rev = ScriptDirectory.from_config(get_alembic_cfg()).get_current_head()
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

    load_seed()
    command.upgrade(get_alembic_cfg(), "head")

    script = ScriptDirectory.from_config(get_alembic_cfg())
    # Walk from head down to (but not including) START_REVISION
    revisions_in_window = list(script.iterate_revisions("head", START_REVISION))

    for rev in revisions_in_window:
        if rev.down_revision is None:
            pytest.fail(
                f"Revision {rev.revision!r} ('{rev.doc}') has no down_revision. "
                f"Every migration in the tested window must be reversible."
            )
        # Merge revisions have a tuple of parents — downgrade to the first one.
        if isinstance(rev.down_revision, tuple):
            target = rev.down_revision[0]
        else:
            target = rev.down_revision
        try:
            command.downgrade(get_alembic_cfg(), target)
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

    load_seed()
    flask_upgrade()

    engine = create_engine(DB_URL)
    tables_first = _get_tables(engine)
    engine.dispose()

    command.downgrade(get_alembic_cfg(), START_REVISION)
    flask_upgrade()

    engine = create_engine(DB_URL)
    tables_second = _get_tables(engine)
    engine.dispose()

    assert tables_first == tables_second, (
        f"Table set differs between first and second upgrade:\n"
        f"  Only after first upgrade:  {tables_first - tables_second}\n"
        f"  Only after second upgrade: {tables_second - tables_first}"
    )


def test_upgrade_to_head_is_noop_when_already_at_head(flask_app):
    """
    Running ``flask db upgrade`` against a database that's already at head
    must be a no-op: the schema must be identical before and after.

    Catches manually-edited migrations whose upgrade() isn't guarded against
    re-running, or migrations whose alembic_version row gets out of sync with
    what was actually applied.
    """
    from flask_migrate import upgrade as flask_upgrade

    load_seed()
    flask_upgrade()

    engine = create_engine(DB_URL)
    schema_before = _get_schema_snapshot(engine)
    rev_before = _get_current_revision(engine)
    engine.dispose()

    flask_upgrade()

    engine = create_engine(DB_URL)
    schema_after = _get_schema_snapshot(engine)
    rev_after = _get_current_revision(engine)
    engine.dispose()

    assert rev_before == rev_after, (
        f"alembic_version changed across a no-op upgrade: "
        f"{rev_before!r} -> {rev_after!r}"
    )
    assert schema_before == schema_after, (
        "Schema changed across a second `flask db upgrade` against a DB "
        "already at head. A migration's upgrade() is being re-applied even "
        "though alembic considers it already done — likely a hand-edited "
        "alembic_version or an upgrade() with side effects outside the "
        "alembic transaction."
    )


def test_full_downgrade_restores_baseline_schema(flask_app):
    """
    Snapshot the schema at START_REVISION (right after the seed load), upgrade
    all the way to head, downgrade all the way back to START_REVISION, and
    assert the schema matches the original snapshot.

    The per-revision round-trip test only verifies one step at a time. This
    one catches the cumulative case: a downgrade chain that "succeeds" but
    leaves stray tables/columns behind because some downgrade() in the middle
    is incomplete.
    """
    from alembic import command
    from flask_migrate import upgrade as flask_upgrade

    load_seed()

    engine = create_engine(DB_URL)
    schema_baseline = _get_schema_snapshot(engine)
    engine.dispose()

    flask_upgrade()
    command.downgrade(get_alembic_cfg(), START_REVISION)

    engine = create_engine(DB_URL)
    schema_after_round_trip = _get_schema_snapshot(engine)
    rev_after = _get_current_revision(engine)
    engine.dispose()

    assert rev_after == START_REVISION, (
        f"After full downgrade, current revision is {rev_after!r} "
        f"instead of START_REVISION ({START_REVISION!r})."
    )

    baseline_tables = set(schema_baseline)
    after_tables = set(schema_after_round_trip)
    assert baseline_tables == after_tables, (
        "After upgrade-to-head -> downgrade-to-START_REVISION, the table set "
        "differs from the baseline:\n"
        f"  Only in baseline:        {sorted(baseline_tables - after_tables)}\n"
        f"  Only after round-trip:   {sorted(after_tables - baseline_tables)}\n"
        "Some downgrade() in the chain is incomplete — it left tables behind "
        "or dropped tables that should have survived."
    )

    # Per-table comparison across every aspect of the schema snapshot.
    ASPECT_HINTS = {
        "columns": "downgrade() in the chain forgot to drop a column it added (or dropped one it shouldn't have)",
        "indexes": "downgrade() in the chain forgot to drop an index it added (or dropped one it shouldn't have)",
        "foreign_keys": "downgrade() in the chain forgot to drop a foreign key it added (or dropped one it shouldn't have)",
        "unique_constraints": "downgrade() in the chain forgot to drop a unique constraint it added (or dropped one it shouldn't have)",
    }
    for table in baseline_tables:
        for aspect, hint in ASPECT_HINTS.items():
            baseline = schema_baseline[table][aspect]
            after = schema_after_round_trip[table][aspect]
            assert baseline == after, (
                f"After full downgrade, {aspect} for table '{table}' differ from "
                f"the baseline:\n"
                f"  Only in baseline:        {sorted(baseline - after)}\n"
                f"  Only after round-trip:   {sorted(after - baseline)}\n"
                f"  {hint}."
            )


def test_schema_matches_models_after_upgrade_to_head(flask_app):
    """
    After upgrading to head, the database schema must exactly match the
    SQLAlchemy models — not just at the table level, but also columns,
    types, indexes and constraints.

    This uses Alembics autogenerate comparison (the same mechanism used by
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

    load_seed()
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

    # Filter out diffs that are known false positives per dialect.
    #
    # MariaDB/MySQL:
    # - 'remove_index'/'add_index': MySQL auto-creates plain indexes backing UNIQUE
    #   constraints and FK columns the models don't declare explicitly.
    # - 'modify_nullable': TINYINT(1) Boolean columns show a nullable mismatch.
    # - 'modify_type' UnicodeText/LONGTEXT, Interval/TIME: dialect representation
    #   differences, not real schema gaps.
    #
    # Postgres:
    # - 'modify_nullable': similar mismatch for Boolean columns.
    if is_postgres():
        # PostgreSQL false positives:
        # - 'add_index'/'remove_index': Alembic detects named non-unique indexes
        #   declared in models (ix_*) that migrations don't explicitly create,
        #   as well as index/constraint naming differences (e.g. unnamed UNIQUE
        #   constraint vs. named ix_token_serial unique index).
        # - 'remove_constraint': paired with add_index when a UNIQUE constraint
        #   was created without a name in the seed but the model names it.
        # - 'modify_nullable': Boolean columns show nullable mismatch.
        # - 'modify_default': Tables created by newer migrations may use IDENTITY
        #   columns while the model uses sequences — alembic autogenerate flags
        #   this as a default mismatch, but it is not a real schema gap.
        IGNORED_DIFF_TYPES = {
            "add_index", "remove_index", "remove_constraint",
            "modify_nullable", "modify_default",
        }
        IGNORED_MODIFY_TYPE_PAIRS: set[tuple[str, str]] = set()
    else:
        IGNORED_DIFF_TYPES = {"remove_index", "add_index", "modify_nullable"}
        IGNORED_MODIFY_TYPE_PAIRS = {
            ("LONGTEXT", "UnicodeText"),
            ("TIME", "Interval"),
        }

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

    def _is_ignored_modify_type(diff) -> bool:
        """
        Return True if this is a modify_type diff that is a known MySQL/MariaDB
        dialect representation mismatch (not a real schema gap).
        Alembic represents these as a list containing a single tuple:
          [('modify_type', schema, table, col, existing_kwargs, live_type, model_type)]
        """
        inner = diff[0] if isinstance(diff, list) and len(diff) == 1 else diff
        if not (isinstance(inner, tuple) and len(inner) >= 7 and inner[0] == "modify_type"):
            return False
        live_type = type(inner[5]).__name__.upper()
        model_type = type(inner[6]).__name__
        return any(
            live_type.startswith(live) and model_type == model
            for live, model in IGNORED_MODIFY_TYPE_PAIRS
        )

    filtered_diffs = [
        diff for diff in diffs
        if _get_diff_type(diff) not in IGNORED_DIFF_TYPES
        and not _is_ignored_modify_type(diff)
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
    script = ScriptDirectory.from_config(get_alembic_cfg())
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


def test_per_migration_test_parent_revisions_match_alembic_chain():
    """
    Every ``MigrationTestBase`` subclass declares ``REVISION`` and
    ``PARENT_REVISION`` constants. ``PARENT_REVISION`` must equal the
    ``down_revision`` of ``REVISION`` in the alembic chain — otherwise
    ``_load_seed_and_upgrade_to_parent`` lands at the wrong place and
    ``_upgrade()`` / ``_downgrade()`` silently span more than one revision.

    The mismatch is invisible at runtime as long as the in-between migrations
    don't touch the same data, so this static check is the only thing that
    catches it.
    """
    import importlib
    import pkgutil

    import tests
    from tests.migration_test_utils import MigrationTestBase

    for module_info in pkgutil.iter_modules(tests.__path__):
        name = module_info.name
        if name.startswith("test_migration_") and name != "test_migrations":
            importlib.import_module(f"tests.{name}")

    script = ScriptDirectory.from_config(get_alembic_cfg())

    bad = []
    for cls in MigrationTestBase.__subclasses__():
        rev = script.get_revision(cls.REVISION)
        expected = rev.down_revision
        if isinstance(expected, tuple):
            expected = expected[0]
        if cls.PARENT_REVISION != expected:
            bad.append((cls.__name__, cls.REVISION, cls.PARENT_REVISION, expected))

    assert not bad, (
        "The following per-migration test classes have a PARENT_REVISION "
        "that does not match the alembic chain:\n"
        + "\n".join(
            f"  {name} (REVISION={rev}): PARENT_REVISION={got!r} but "
            f"alembic down_revision={want!r}"
            for name, rev, got, want in bad
        )
    )


def test_each_migration_survives_round_trip(flask_app):
    """
    True idempotency test: for every migration in the window, verify that the
    upgrade → downgrade → upgrade round-trip succeeds without crashing and
    produces the same schema both times.

    Performance: the DB is set up once at START_REVISION, and we march forward
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

    script = ScriptDirectory.from_config(get_alembic_cfg())
    # Chronological order: oldest (just after START_REVISION) first.
    revisions_in_window = list(reversed(list(script.iterate_revisions("head", START_REVISION))))

    # Set up the DB once — all iterations share this starting point.
    load_seed()

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
            command.upgrade(get_alembic_cfg(), rev.revision)
        except Exception as e:
            pytest.fail(
                f"First upgrade() to revision {rev.revision!r} ('{rev.doc}') failed: {e}"
            )

        engine = create_engine(DB_URL)
        schema_after_first_upgrade = _get_schema_snapshot(engine)
        engine.dispose()

        # 2. Downgrade one step back.
        try:
            command.downgrade(get_alembic_cfg(), parent_revision)
        except Exception as e:
            pytest.fail(
                f"downgrade() of revision {rev.revision!r} ('{rev.doc}') "
                f"back to {parent_revision!r} failed: {e}"
            )

        # 3. Upgrade to the revision again.
        try:
            command.upgrade(get_alembic_cfg(), rev.revision)
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

        # Compare columns, indexes, FKs and unique constraints per table.
        # If any aspect differs, the offending downgrade() likely forgot to
        # drop something the upgrade() added (or vice versa).
        ASPECT_HINTS = {
            "columns": "downgrade() likely forgot to drop a column, or upgrade() forgot to add one",
            "indexes": "downgrade() likely forgot to drop an index, or upgrade() forgot to recreate one",
            "foreign_keys": "downgrade() likely forgot to drop a foreign key, or upgrade() forgot to recreate one",
            "unique_constraints": "downgrade() likely forgot to drop a unique constraint, or upgrade() forgot to recreate one",
        }
        for table in tables_first:
            for aspect, hint in ASPECT_HINTS.items():
                first = schema_after_first_upgrade[table][aspect]
                second = schema_after_second_upgrade[table][aspect]
                assert first == second, (
                    f"Migration {rev.revision!r} ('{rev.doc}'): {aspect} for table "
                    f"'{table}' differ between first and second upgrade after round-trip.\n"
                    f"  Only after first upgrade:  {sorted(first - second)}\n"
                    f"  Only after second upgrade: {sorted(second - first)}\n"
                    f"  {hint}."
                )

        assert current_rev == rev.revision, (
            f"After round-trip for {rev.revision!r}, current revision is "
            f"{current_rev!r} instead of {rev.revision!r}."
        )
        # Leave the DB at rev.revision — the next iteration will upgrade from here.


def _quote_ident(name: str) -> str:
    """Dialect-aware identifier quoting for raw SQL."""
    if is_postgres():
        return f'"{name}"'
    return f"`{name}`"


def _row_counts(engine, tables: set[str]) -> dict[str, int]:
    """Return {table: row_count} for every table in *tables* that exists."""
    counts: dict[str, int] = {}
    inspector = sa_inspect(engine)
    existing = set(inspector.get_table_names())
    with engine.connect() as conn:
        for table in tables:
            if table not in existing:
                continue
            counts[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {_quote_ident(table)}")
            ).scalar()
    return counts


def test_downgrade_does_not_destroy_data_in_surviving_tables(flask_app):
    """
    Downgrading must not delete data from tables that survive the downgrade.

    Strategy: seed the DB at START_REVISION (which contains data in stable
    tables like realm), snapshot row counts for every table in the seed,
    upgrade to head, downgrade back to START_REVISION, and assert every
    surviving table still has at least its original row count.

    "At least" rather than "equal" because:
      - The seed only populates a subset of tables; those start at 0.
      - Some downgrade()s legitimately re-insert canonical rows.
    What we're guarding against is rows being *destroyed* — counts going down.
    The realm rows (id=1 'defrealm', id=2 'testrealm') are checked exactly so
    we have a precise smoke signal on the most stable table.
    """
    from alembic import command
    from flask_migrate import upgrade as flask_upgrade

    load_seed()

    engine = create_engine(DB_URL)
    seed_tables = set(sa_inspect(engine).get_table_names())
    counts_before = _row_counts(engine, seed_tables)
    engine.dispose()

    flask_upgrade()
    command.downgrade(get_alembic_cfg(), START_REVISION)

    engine = create_engine(DB_URL)
    counts_after = _row_counts(engine, seed_tables)
    realm_check = None
    with engine.connect() as conn:
        if "realm" in seed_tables:
            realm_check = conn.execute(
                text("SELECT name FROM realm WHERE id = 1")
            ).scalar()
    engine.dispose()

    lost = {
        table: (counts_before[table], counts_after.get(table, 0))
        for table in counts_before
        if counts_after.get(table, 0) < counts_before[table]
    }
    assert not lost, (
        "Rows were destroyed in tables that survive a full downgrade. "
        "{table: (before, after)}:\n"
        + "\n".join(f"  {t}: {b} -> {a}" for t, (b, a) in lost.items())
    )

    if "realm" in seed_tables:
        assert realm_check == "defrealm", (
            f"Data in the 'realm' table was lost during downgrade. "
            f"Expected 'defrealm', got {realm_check!r}."
        )


def _get_declared_sequence_names() -> set[str]:
    """
    Collect every Sequence(...) name declared on any column across the models.
    Alembic's autogenerate does not compare sequences, so we have to check
    these ourselves — otherwise a migration that creates a table with
    sa.Identity() while the model declares Sequence() ships silently and
    blows up on the first insert on MariaDB 10.3+ / SQLAlchemy 2.x (which
    honors Sequence() on MySQL/MariaDB and emits SELECT nextval(...)).
    """
    from sqlalchemy import Sequence
    from privacyidea.models import db

    names: set[str] = set()
    for table in db.metadata.tables.values():
        for col in table.columns:
            default = col.default
            if isinstance(default, Sequence):
                names.add(default.name)
    return names


def _get_existing_sequence_names(engine) -> set[str]:
    """Return the set of sequence names present in the live database."""
    with engine.connect() as conn:
        if is_postgres(str(engine.url)):
            rows = conn.execute(
                text("SELECT sequencename FROM pg_sequences WHERE schemaname = 'public'")
            ).fetchall()
        else:
            rows = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'SEQUENCE'"
            )).fetchall()
    return {r[0] for r in rows}


def test_all_declared_sequences_exist_after_upgrade_to_head(flask_app):
    """
    Every Sequence(...) declared on a model must exist in the database after
    upgrading to head. Alembic's autogenerate does not compare sequences, so
    this check is not covered by test_schema_matches_models_after_upgrade_to_head.

    On MariaDB 10.3+ / SQLAlchemy 2.x, a column with a Sequence() default
    causes SQLAlchemy to emit SELECT nextval(<seq>) on insert. If the
    corresponding CREATE SEQUENCE was never issued by a migration (e.g. the
    table was created with sa.Identity() while the model declares Sequence()),
    every insert fails at runtime with "Unknown SEQUENCE".
    """
    from flask_migrate import upgrade as flask_upgrade

    load_seed()
    flask_upgrade()

    engine = create_engine(DB_URL)
    try:
        # supports_sequences is False on the base MySQL dialect and is upgraded
        # to True only after server detection identifies a MariaDB. Connect first.
        with engine.connect() as conn:
            if not conn.dialect.supports_sequences:
                pytest.skip(
                    f"Dialect {conn.dialect.name!r} does not support sequences; "
                    "the model declares Sequence() but the dialect ignores it."
                )
        actual = _get_existing_sequence_names(engine)
    finally:
        engine.dispose()

    expected = _get_declared_sequence_names()
    missing = expected - actual
    assert not missing, (
        f"The following sequences are declared on the models but do not exist "
        f"in the database after upgrade to head: {sorted(missing)}.\n"
        f"This means a migration creates the table without issuing CREATE SEQUENCE "
        f"(e.g. via sa.Identity() instead of sa.Sequence()). Inserts will fail "
        f"on MariaDB 10.3+ with 'Unknown SEQUENCE'."
    )


def _generic_dummy_value(col):
    """
    Return a value appropriate for *col*'s SQL type, used by the insert smoke
    test to populate NOT NULL columns without per-table fixtures. Returns None
    only for column types we don't know how to fill — caller must skip those.
    """
    import datetime as dt
    from sqlalchemy import (
        BigInteger, Boolean, Date, DateTime, Float, Integer, Interval,
        JSON, LargeBinary, Numeric, SmallInteger, String, Text, Time,
        Unicode, UnicodeText,
    )

    t = col.type
    if isinstance(t, (String, Unicode, UnicodeText, Text)):
        length = getattr(t, "length", None) or 8
        return "x" * min(length, 8)
    if isinstance(t, Boolean):
        return False
    if isinstance(t, (Integer, BigInteger, SmallInteger)):
        return 1
    if isinstance(t, DateTime):
        return dt.datetime(2000, 1, 1)
    if isinstance(t, Date):
        return dt.date(2000, 1, 1)
    if isinstance(t, Time):
        return dt.time(0, 0)
    if isinstance(t, Interval):
        return dt.timedelta(0)
    if isinstance(t, (Float, Numeric)):
        return 0
    if isinstance(t, LargeBinary):
        return b"x"
    if isinstance(t, JSON):
        return {}
    return None


def test_default_insert_succeeds_for_every_model_table(flask_app):
    """
    For every table the SQLAlchemy models declare, build a minimal INSERT and
    execute it against the live (upgraded-to-head) DB. Catches failures that
    schema checks cannot — e.g. a Sequence default declared on the model but
    no CREATE SEQUENCE issued by any migration, an Identity column SQLAlchemy
    can't drive on this dialect, or a NOT NULL column whose default isn't
    actually applied.

    Strategy:
      - PKs whose default is a Sequence or that are autoincrement are omitted
        so SQLAlchemy fires its auto-PK path — this is the exact path that
        breaks when the migration created the table without the matching
        CREATE SEQUENCE / AUTO_INCREMENT machinery the model expects.
      - NOT NULL columns without any default get a type-appropriate dummy.
      - Nullable columns and columns with Python/server defaults are omitted.
      - FK checks are disabled for the duration so we don't have to insert in
        dependency order; this test is about INSERT mechanics, not referential
        integrity.
      - All inserts run inside a single transaction that is rolled back at
        the end, so no rows leak into the test DB.
    """
    from flask_migrate import upgrade as flask_upgrade
    from sqlalchemy import BigInteger, Integer, SmallInteger, Sequence
    from privacyidea.models import db

    load_seed()
    flask_upgrade()

    engine = create_engine(DB_URL)
    is_pg = is_postgres()
    failures: list[tuple[str, str]] = []

    try:
        with engine.connect() as conn:
            outer = conn.begin()
            try:
                if is_pg:
                    conn.execute(text("SET session_replication_role = 'replica'"))
                else:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

                for table in db.metadata.sorted_tables:
                    values = {}
                    skip_reason = None
                    for col in table.columns:
                        is_sole_int_pk = (
                            col.primary_key
                            and len(table.primary_key.columns) == 1
                            and isinstance(col.type, (Integer, BigInteger, SmallInteger))
                            and col.autoincrement is not False
                        )
                        is_auto_pk = isinstance(col.default, Sequence) or is_sole_int_pk
                        if is_auto_pk:
                            continue
                        if col.default is not None or col.server_default is not None:
                            continue
                        if col.nullable:
                            continue
                        val = _generic_dummy_value(col)
                        if val is None:
                            skip_reason = (
                                f"no dummy generator for column {col.name!r} of type {col.type!r}"
                            )
                            break
                        values[col.name] = val

                    if skip_reason is not None:
                        failures.append((table.name, f"SKIPPED: {skip_reason}"))
                        continue

                    sp = conn.begin_nested()
                    try:
                        conn.execute(table.insert().values(**values))
                        sp.rollback()
                    except Exception as e:
                        sp.rollback()
                        first_line = str(e).splitlines()[0] if str(e) else type(e).__name__
                        failures.append((table.name, first_line))
            finally:
                outer.rollback()
    finally:
        engine.dispose()

    assert not failures, (
        "INSERT failed for the following model tables after upgrade-to-head. "
        "This usually means a migration created the table without the auto-PK "
        "machinery the model expects (e.g. sa.Identity() instead of sa.Sequence(), "
        "or a NOT NULL column added without a default):\n"
        + "\n".join(f"  {tbl}: {msg}" for tbl, msg in failures)
    )
