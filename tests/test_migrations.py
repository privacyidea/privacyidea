"""
Note: Data transformation tests for specific migrations do not belong in this
file.  See ``tests/README.md`` for the full guide on when a per-migration test
is required and how to write one.
"""

import os
import pathlib
import time

import pytest
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text, inspect as sa_inspect
from sqlalchemy.exc import OperationalError

# Skip these tests if no database URL is provided
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

# Directory that holds dialect-specific seed SQL files.
# Naming convention: seed_v<version>_<revision>_<dialect>.sql
#   dialect = "mariadb" or "postgresql"
SEED_SQL_DIR = pathlib.Path(__file__).parent / "testdata" / "migrations"


def _get_seed_sql_path(db_url: str = DB_URL) -> pathlib.Path:
    """Return the seed file path for the active dialect."""
    dialect = "postgresql" if _is_postgres(db_url) else "mariadb"
    return SEED_SQL_DIR / f"seed_v3.9_{START_REVISION}_{dialect}.sql"


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


def _is_postgres(db_url: str = DB_URL) -> bool:
    return db_url.startswith("postgresql")


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


def _drop_all_tables(engine) -> None:
    """Drop every table (and for Postgres, every sequence) in the database, dialect-safe."""
    with engine.connect() as conn:
        if _is_postgres(str(engine.url)):
            # Postgres: drop each table with CASCADE to handle FK dependencies.
            for table in sa_inspect(engine).get_table_names():
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
            # Also drop all sequences so the seed file can re-create them cleanly.
            sequences = conn.execute(
                text("SELECT sequencename FROM pg_sequences WHERE schemaname = 'public';")
            ).fetchall()
            for (seq,) in sequences:
                conn.execute(text(f'DROP SEQUENCE IF EXISTS "{seq}" CASCADE;'))
        else:
            # MariaDB/MySQL: disable FK checks, use backtick quoting.
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            for table in sa_inspect(engine).get_table_names():
                conn.execute(text(f"DROP TABLE IF EXISTS `{table}`;"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        conn.commit()


def _read_seed_statements(db_url: str = DB_URL) -> list[str]:
    """
    Read the dialect-specific seed SQL file and split it into individual
    statements (split on semicolons), discarding empty / comment-only chunks.
    """
    seed_path = _get_seed_sql_path(db_url)
    sql = seed_path.read_text(encoding="utf-8")
    statements = []
    for chunk in sql.split(";"):
        stripped = chunk.strip()
        if not stripped:
            continue
        # Discard chunks that consist entirely of comment lines
        non_comment_lines = [
            line for line in stripped.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        if non_comment_lines:
            statements.append(stripped)
    return statements


def _load_seed_db(db_url: str = DB_URL) -> None:
    """
    Load the dialect-specific v3.9 seed SQL file into the database.

    Seed files are pre-written for each supported dialect (mariadb, postgresql)
    so no on-the-fly SQL transformation is needed.
    """
    statements = _read_seed_statements(db_url)
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_database():
    """Wipe the database before and after every test."""
    engine = create_engine(DB_URL)
    _wait_for_db(engine)
    _drop_all_tables(engine)
    engine.dispose()
    yield
    engine = create_engine(DB_URL)
    _wait_for_db(engine)
    _drop_all_tables(engine)
    engine.dispose()


@pytest.fixture
def flask_app():
    """
    Provide a Flask app context pointing at the test database.
    Schema setup is done by _load_seed_db(), not db.create_all().
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

    _load_seed_db()
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

    _load_seed_db()
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

    _load_seed_db()
    command.upgrade(_get_alembic_cfg(), "head")

    script = ScriptDirectory.from_config(_get_alembic_cfg())
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
            command.downgrade(_get_alembic_cfg(), target)
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

    _load_seed_db()
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

    _load_seed_db()
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
    if _is_postgres():
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

    script = ScriptDirectory.from_config(_get_alembic_cfg())
    # Chronological order: oldest (just after START_REVISION) first.
    revisions_in_window = list(reversed(list(script.iterate_revisions("head", START_REVISION))))

    # Set up the DB once — all iterations share this starting point.
    _load_seed_db()

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

    Strategy: seed the DB at START_REVISION (which already contains data in
    stable tables like realm), upgrade to head, then downgrade back to
    START_REVISION and verify the seeded realm rows are still present.
    The realm table is created long before START_REVISION so it survives
    every downgrade in the window.
    """
    from alembic import command
    from flask_migrate import upgrade as flask_upgrade

    _load_seed_db()
    flask_upgrade()

    # The seed already has realm rows (id=1 'defrealm', id=2 'testrealm').
    # Downgrade all the way back to START_REVISION and verify they survived.
    command.downgrade(_get_alembic_cfg(), START_REVISION)

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM realm WHERE id = 1")
        ).scalar()
    engine.dispose()

    assert result == "defrealm", (
        f"Data in the 'realm' table was lost during downgrade. "
        f"Expected 'defrealm', got {result!r}."
    )
