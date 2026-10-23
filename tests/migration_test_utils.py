"""
Shared utilities and base class for database migration tests.

See tests/README.md for the full guide on when a per-migration test is
required and how to write one.
"""

import functools
import os
import pathlib
import re
from collections.abc import Callable
from typing import Any

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Sequence, create_engine, event, inspect as sa_inspect, select, text
from sqlalchemy.engine import Connection, Engine, ExecutionContext
from sqlalchemy.sql.compiler import IdentifierPreparer

DB_URL = os.environ.get("TEST_DATABASE_URL", "")

SEED_SQL_DIR = pathlib.Path(__file__).parent / "testdata" / "migrations"

# Pinned starting revision — must match the constant in test_migrations.py.
START_REVISION = "5cb310101a1f"

# The head revision of each release whose database a downgrade has to be able to return to. Its seeds in
# tests/testdata/migrations/ come from tools/generate_release_seed.py.
RELEASE_HEADS = {
    "3.13.4": "d3a4b5c6e7f8",
    "3.14.0": "b7c1e4d2a9f3",
}

# The seeds in tests/testdata/migrations/ and the revision each one is stamped with. The v3.9 seed stands for databases
# that an older release created and the releases since upgraded, a release seed for a database that "pi-manage setup
# create_tables" of the release created.
SEEDS = {"v3.9": START_REVISION, **{f"v{release}": head for release, head in RELEASE_HEADS.items()}}


def is_postgres(db_url: str = DB_URL) -> bool:
    return db_url.startswith("postgresql")


def is_oracle(db_url: str = DB_URL) -> bool:
    return db_url.startswith("oracle")


@functools.cache
def is_mariadb(db_url: str = DB_URL) -> bool:
    """Tell MariaDB apart from real MySQL behind a shared mysql+pymysql:// URL.

    Both engines connect through the identical URL scheme, so the connection
    string alone cannot distinguish them — the server's own version string
    (inspected by SQLAlchemy on first connect) is the only reliable signal.
    Cached because callers (get_seed_path) run once per test.
    """
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            return bool(conn.dialect.is_mariadb)
    finally:
        engine.dispose()


@functools.cache
def _identifier_preparer(db_url: str = DB_URL) -> IdentifierPreparer:
    """Return the active dialect's identifier preparer. No connection needed."""
    return create_engine(db_url).dialect.identifier_preparer


@functools.cache
def _model_identifiers() -> dict[str, str]:
    """
    Map every table and column name the models declare to the name object
    SQLAlchemy created the schema with.

    Plain strings lose the ``quote=True`` flag that ``Challenge.session`` carries
    (``session`` is an Oracle keyword, so the column only exists there because it
    was created quoted, in lower case). Looking the name up here recovers the
    flag, which is what tells the preparer to quote it.
    """
    from privacyidea.models import db
    names: dict[str, str] = {}
    for table in db.metadata.sorted_tables:
        names.setdefault(str(table.name), table.name)
        for col in table.c:
            names.setdefault(str(col.name), col.name)
    return names


def quote_identifier(name: str) -> str:
    """
    Quote *name* for use in raw SQL against the active dialect.

    Delegates to the dialect's own identifier preparer, which quotes exactly when
    the schema was created quoted — the only way raw SQL and the schema can agree:

    * Mixed case (``Key``, ``Value``) is quoted on Postgres and Oracle, which fold
      unquoted names to lower/upper case respectively.
    * A name the model forces to be quoted (``Challenge.session``) is quoted.
    * An all-lower-case, unforced name stays unquoted. Quoting one on Oracle would
      look for a lower-case object that does not exist (ORA-00904 for a column,
      ORA-00942 for a table).
    """
    return _identifier_preparer().quote(_model_identifiers().get(name, name))


def get_alembic_cfg(db_url: str = DB_URL) -> AlembicConfig:
    migrations_dir = str(pathlib.Path(__file__).parent.parent / "privacyidea" / "migrations")
    cfg = AlembicConfig(str(pathlib.Path(migrations_dir) / "alembic.ini"))
    cfg.set_main_option("script_location", migrations_dir)
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def get_seed_path(revision: str = START_REVISION, db_url: str = DB_URL) -> pathlib.Path:
    """Return the seed file path for the given pinned revision and active dialect."""
    if is_postgres(db_url):
        dialect = "postgresql"
    elif is_oracle(db_url):
        dialect = "oracle"
    elif is_mariadb(db_url):
        dialect = "mariadb"
    else:
        dialect = "mysql"
    # Seeds follow the naming convention:  seed_v<ver>_<revision>_<dialect>.sql
    # Glob for any file that matches the revision + dialect regardless of version tag.
    matches = list(SEED_SQL_DIR.glob(f"*_{revision}_{dialect}.sql"))
    if not matches:
        raise FileNotFoundError(
            f"No seed file found in {SEED_SQL_DIR} for revision={revision!r}, "
            f"dialect={dialect!r}.  Expected a file matching *_{revision}_{dialect}.sql"
        )
    return matches[0]


def drop_all_tables(engine) -> None:
    """Drop every table (and for Postgres every sequence) in the database."""
    with engine.connect() as conn:
        # A transaction that a test left open holds locks on the tables it read, and DROP waits for them: on MySQL and
        # MariaDB for a year by default. Fail after a minute instead of hanging the run. Oracle fails at once
        # (ORA-00054).
        if is_postgres(str(engine.url)):
            conn.execute(text("SET lock_timeout = '60s'"))
        elif not is_oracle(str(engine.url)):
            conn.execute(text("SET SESSION lock_wait_timeout = 60"))
        if is_postgres(str(engine.url)):
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        elif is_oracle(str(engine.url)):
            # Oracle has no schema-wide DROP. CASCADE CONSTRAINTS lets us drop
            # tables regardless of FK order, and PURGE skips the recyclebin so
            # dropped tables (and the system-generated ISEQ$$ sequences backing
            # any IDENTITY columns) are removed immediately rather than lingering
            # as BIN$… objects. Objects were created with unquoted (case-folded,
            # upper-case) names; the inspector returns them lower-cased, so drop
            # unquoted to let Oracle fold them back.
            inspector = sa_inspect(engine)
            for table in inspector.get_table_names():
                conn.execute(text(f"DROP TABLE {table} CASCADE CONSTRAINTS PURGE"))
            # Identity-column sequences (ISEQ$$_*) are system-generated and are
            # dropped with their table — never drop them directly (ORA-32794).
            for seq in inspector.get_sequence_names():
                if seq.lower().startswith("iseq$$"):
                    continue
                conn.execute(text(f"DROP SEQUENCE {seq}"))
            # Sweep any recyclebin remnants from earlier non-PURGE drops.
            conn.execute(text("PURGE RECYCLEBIN"))
        else:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in sa_inspect(engine).get_table_names():
                conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
            # Drop sequences too — the v3.9 seed creates them and they
            # would otherwise survive between tests and collide on reload.
            sequences = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'SEQUENCE'"
            )).fetchall()
            for (seq,) in sequences:
                conn.execute(text(f"DROP SEQUENCE IF EXISTS `{seq}`"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()


def read_seed_statements(seed_revision: str = START_REVISION, db_url: str = DB_URL) -> list[str]:
    """
    Read the dialect-specific seed SQL file and split it into individual
    statements (split on semicolons), discarding empty / comment-only chunks.
    """
    path = get_seed_path(seed_revision, db_url)
    sql = path.read_text(encoding="utf-8")
    statements = []
    for chunk in sql.split(";"):
        stripped = chunk.strip()
        if not stripped:
            continue
        non_comment_lines = [
            line for line in stripped.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        if non_comment_lines:
            statements.append(stripped)
    return statements


def load_seed(seed_revision: str = START_REVISION, db_url: str = DB_URL) -> None:
    """Load the dialect-specific seed SQL for *seed_revision* into the database."""
    statements = read_seed_statements(seed_revision, db_url)
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()
    finally:
        engine.dispose()


def seeds_before(revision: str) -> list[str]:
    """The seeds that *revision* has not been applied to yet, so a test of it can start from each of them."""
    return [seed for seed, seed_revision in SEEDS.items() if revision not in revisions_up_to(seed_revision)]


def _id_sequence(table: str) -> str | None:
    """The name of the sequence the model of *table* takes the id from, if it has one."""
    from sqlalchemy import Sequence

    from privacyidea.models import db

    model_table = db.metadata.tables.get(table)
    if model_table is not None and "id" in model_table.c and isinstance(model_table.c.id.default, Sequence):
        return model_table.c.id.default.name
    return None


def next_sequence_value(conn: Connection, sequence: str) -> int:
    """Take the next value of *sequence*, the way privacyIDEA takes the id of a new row."""
    return conn.execute(select(Sequence(sequence).next_value())).scalar()


def sequences_behind_their_table(engine: Engine) -> dict[str, tuple[int, int]]:
    """
    The tables whose sequence would hand out an id that already exists, as {table: (next value, highest id)}, for every
    table whose model takes the id from a sequence. Taking the next value leaves a gap of one id in every sequence.
    Empty on a database without sequences (MySQL).
    """
    from privacyidea.models import db

    inspector = sa_inspect(engine)
    tables = {name.lower() for name in inspector.get_table_names()}
    behind = {}
    with engine.connect() as conn:
        if not conn.dialect.supports_sequences:
            return behind
        sequences = {name.lower() for name in inspector.get_sequence_names()}
        for table in db.metadata.sorted_tables:
            sequence = _id_sequence(table.name)
            if sequence is None or table.name not in tables or sequence not in sequences:
                continue
            highest_id = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table.name}")).scalar()
            next_value = next_sequence_value(conn, sequence)
            if next_value <= highest_id:
                behind[table.name] = (next_value, highest_id)
        conn.commit()
    return behind


@functools.cache
def revisions_up_to(revision: str) -> frozenset[str]:
    """The revision and all its ancestors."""
    script = ScriptDirectory.from_config(get_alembic_cfg())
    return frozenset(ancestor.revision for ancestor in script.iterate_revisions(revision, "base"))


def stamped_revisions(engine: Engine) -> set[str]:
    """The revisions in alembic_version, one per branch that is applied up to it."""
    with engine.connect() as conn:
        return set(MigrationContext.configure(conn).get_current_heads())


def downgrade_keeping(target: str, keep: str | None = None) -> None:
    """
    Downgrade to *target*, but leave *keep* and the revisions before it applied.

    Alembic undoes every applied revision that descends from the target. In a database of a release that reached its
    head through a merge, that is not the same: the release's own revisions after the branch point descend from the
    branch point too (3.13.4 from b1a2c3d4e5f6), and a downgrade to the release head stops at the merge and leaves the
    other branch stamped next to it. So this downgrades to *target*, or to *keep* if the target lies before it, and
    then takes every branch that is still stamped beyond both down on its own.
    """
    if keep is None:
        command.downgrade(get_alembic_cfg(), target)
        return
    kept_revisions = revisions_up_to(target) | revisions_up_to(keep)
    command.downgrade(get_alembic_cfg(), keep if target in revisions_up_to(keep) else target)
    engine = create_engine(DB_URL)
    try:
        stamps = stamped_revisions(engine)
    finally:
        engine.dispose()
    for stamp in sorted(stamps):
        steps = len(revisions_up_to(stamp) - kept_revisions)
        if steps:
            command.downgrade(get_alembic_cfg(), f"{stamp}@-{steps}")


def set_stamp_before(engine: Engine, revision: str) -> None:
    """
    Set the revision stamp back to what it was before *revision* ran, without undoing anything the migration did.

    The next upgrade then runs the migration again on top of its own result, as on an installation on which the stamp
    was set back by hand. *revision* is replaced by those of its parents that no other stamped head already descends
    from.
    """
    script = ScriptDirectory.from_config(get_alembic_cfg())
    with engine.begin() as conn:
        heads = set(MigrationContext.configure(conn).get_current_heads())
        heads.discard(revision)
        parents = script.get_revision(revision).down_revision
        for parent in parents if isinstance(parents, tuple) else (parents,):
            if not any(parent in {ancestor.revision for ancestor in script.iterate_revisions(head, "base")}
                       for head in heads):
                heads.add(parent)
        conn.execute(text("DELETE FROM alembic_version"))
        for head in heads:
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:head)"), {"head": head})


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
        # No seed has rows with this value, so the members of a composite primary key do not collide with seed rows
        return 32000
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


def insert_minimal_row_into_every_table() -> list[tuple[str, str]]:
    """
    Build a minimal INSERT for every table the SQLAlchemy models declare and run it
    against the live database. Returns one ``(table, message)`` pair per table whose
    INSERT failed, so a caller can report them all at once.

    Strategy:
      - PKs whose default is a Sequence or that are autoincrement are omitted
        so SQLAlchemy fires its auto-PK path — this is the exact path that
        breaks when the schema was built without the matching CREATE SEQUENCE /
        AUTO_INCREMENT / IDENTITY machinery the model expects.
      - NOT NULL columns without any default get a type-appropriate dummy.
      - Nullable columns and columns with Python/server defaults are omitted.
      - FK checks are disabled for the duration so we don't have to insert in
        dependency order; this is about INSERT mechanics, not referential
        integrity.
      - All inserts run inside a single transaction that is rolled back at
        the end, so no rows leak into the test DB.
    """
    from sqlalchemy import Sequence
    from privacyidea.models import db

    engine = create_engine(DB_URL)
    is_pg = is_postgres()
    is_ora = is_oracle()
    failures: list[tuple[str, str]] = []

    # Oracle has no session-level FK switch like MySQL/Postgres, so disable
    # every FK constraint up front and re-enable them in the finally. The DDL
    # auto-commits, but no real rows are ever committed (each insert is rolled
    # back to a savepoint), so re-enabling validates only the untouched seed
    # data, which already satisfies every FK.
    disabled_fks: list[tuple[str, str]] = []
    if is_ora:
        with engine.connect() as setup_conn:
            rows = setup_conn.execute(text(
                "SELECT table_name, constraint_name FROM user_constraints "
                "WHERE constraint_type = 'R'"
            )).fetchall()
            for tbl, con in rows:
                setup_conn.execute(text(f'ALTER TABLE "{tbl}" DISABLE CONSTRAINT "{con}"'))
                disabled_fks.append((tbl, con))
            setup_conn.commit()

    try:
        with engine.connect() as conn:
            outer = conn.begin()
            try:
                if is_pg:
                    conn.execute(text("SET session_replication_role = 'replica'"))
                elif not is_ora:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

                for table in db.metadata.sorted_tables:
                    values = {}
                    skip_reason = None
                    for col in table.columns:
                        # A PK column is auto-generated only if it has an
                        # explicit Sequence/Identity, OR it's the sole integer
                        # PK with autoincrement not explicitly disabled.
                        # Composite PKs and string PKs do not auto-generate
                        # — every member must be filled by the caller.
                        from sqlalchemy import BigInteger, Integer, SmallInteger
                        is_sole_int_pk = (
                            col.primary_key
                            and len(table.primary_key.columns) == 1
                            and isinstance(col.type, (Integer, BigInteger, SmallInteger))
                            and col.autoincrement is not False
                        )
                        is_auto_pk = isinstance(col.default, Sequence) or is_sole_int_pk
                        if is_auto_pk:
                            continue
                        # Oracle stores '' as NULL, so a scalar empty-string
                        # default does not satisfy a NOT NULL column — relying on
                        # it produces ORA-01400. Fall through to supply a dummy in
                        # that case instead of trusting the default to fire.
                        default_is_empty_string = (
                            col.default is not None
                            and getattr(col.default, "is_scalar", False)
                            and col.default.arg == ""
                        )
                        skip_for_default = col.default is not None or col.server_default is not None
                        if is_ora and not col.nullable and default_is_empty_string:
                            skip_for_default = False
                        if skip_for_default:
                            continue
                        if col.nullable:
                            continue
                        val = _generic_dummy_value(col)
                        if val is None:
                            skip_reason = f"no dummy generator for column {col.name!r} of type {col.type!r}"
                            break
                        values[col.name] = val

                    if skip_reason is not None:
                        failures.append((table.name, f"SKIPPED: {skip_reason}"))
                        continue

                    # Oracle has no "INSERT ... DEFAULT VALUES" / empty-column-list
                    # syntax (ORA-00928). A table whose every column is an auto PK
                    # or nullable therefore yields an empty value set; supply a
                    # dummy for one fillable non-PK column so the statement is
                    # valid (FK checks are disabled, so an FK column is fine).
                    if is_ora and not values:
                        for col in table.columns:
                            is_sole_int_pk = (
                                col.primary_key
                                and len(table.primary_key.columns) == 1
                                and isinstance(col.type, (BigInteger, Integer, SmallInteger))
                                and col.autoincrement is not False
                            )
                            if isinstance(col.default, Sequence) or is_sole_int_pk:
                                continue
                            val = _generic_dummy_value(col)
                            if val is not None:
                                values[col.name] = val
                                break

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
        if disabled_fks:
            with engine.connect() as teardown_conn:
                for tbl, con in disabled_fks:
                    teardown_conn.execute(text(f'ALTER TABLE "{tbl}" ENABLE CONSTRAINT "{con}"'))
                teardown_conn.commit()
        engine.dispose()

    return failures


def insert_rows(engine: Engine, table: str, rows: list[dict], ids_from_sequence: bool = False) -> None:
    """
    Insert *rows* into *table*, quoting the column names (e.g. ``Key``, ``Value``) for the active dialect. With
    *ids_from_sequence*, a row without an id takes it from the sequence of the table, as privacyIDEA does; that is
    needed where the id column has no default, as in a database that "pi-manage setup create_tables" created. MySQL has
    no sequences and fills the id itself.

    Bind parameters are numbered rather than named after their column: a bind variable may not be a reserved word
    either, and ``:session`` (a real column of ``challenge``) fails on Oracle with "ORA-01745: invalid host/bind
    variable name".
    """
    if not rows:
        return
    with engine.connect() as conn:
        sequence = (_id_sequence(table) if ids_from_sequence and "id" not in rows[0] and conn.dialect.supports_sequences
                    else None)
        cols = list(rows[0].keys()) + (["id"] if sequence else [])
        col_list = ", ".join(quote_identifier(c) for c in cols)
        placeholders = ", ".join(f":p{i}" for i, _ in enumerate(cols))
        stmt = text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})")
        for row in rows:
            values = dict(row, id=next_sequence_value(conn, sequence)) if sequence else row
            conn.execute(stmt, {f"p{i}": values[col] for i, col in enumerate(cols)})
        conn.commit()


class InjectedFailure(Exception):
    """Raised by :meth:`MigrationTestBase._upgrade_failing_after` to stop a migration midway."""


class MigrationTestBase:
    """
    Base class for per-migration data-transformation tests.

    Subclasses must set:
        REVISION        — the revision under test (str)
        PARENT_REVISION — the revision immediately before it (str)

    The ``flask_app`` and ``clean_database`` fixtures are inherited and
    automatically applied; subclasses only need to declare the test methods.
    """

    REVISION: str
    PARENT_REVISION: str
    # The revision whose seeds the tests start from, if not REVISION: the tests of a repair start before the migration
    # whose data it repairs
    STARTS_BEFORE: str | None = None

    @pytest.fixture
    def flask_app(self):
        """Flask app context — required because alembic env.py calls current_app."""
        from privacyidea.app import create_app
        app = create_app(
            "testing",
            pathlib.Path.cwd() / "tests/testdata/test_pi.cfg",
            silent=True,
        )
        ctx = app.app_context()
        ctx.push()
        yield app
        # Every test builds its own app, and alembic migrates through the engine of that app (see the
        # migrations env.py). The connection pool of the engine keeps its connections open, so without
        # disposing it here the pools of all previous tests stay open until the end of the session and
        # exhaust the connection limit of the database server.
        from privacyidea.models import db
        db.session.remove()
        for engine in db.engines.values():
            engine.dispose()
        ctx.pop()

    def pytest_generate_tests(self, metafunc: pytest.Metafunc) -> None:
        """Run the tests of a revision from every seed it has not been applied to yet (see seeds_before and
        STARTS_BEFORE)."""
        if "seed" in metafunc.fixturenames:
            metafunc.parametrize("seed", seeds_before(self.STARTS_BEFORE or self.REVISION), indirect=True)

    @pytest.fixture
    def seed(self, request: pytest.FixtureRequest) -> str:
        """The seed that _load_seed_and_upgrade_to_parent starts from, a key of SEEDS."""
        return getattr(request, "param", "v3.9")

    @pytest.fixture(autouse=True)
    def clean_database(self, flask_app, seed: str):
        """Wipe the database before and after every test."""
        self.seed = seed
        engine = create_engine(DB_URL)
        drop_all_tables(engine)
        engine.dispose()
        yield
        # The flask_app fixture is torn down after this one. End the transaction its session may still hold from a
        # read through the models, whose locks would block the DROP TABLE below.
        from privacyidea.models import db
        db.session.remove()
        engine = create_engine(DB_URL)
        drop_all_tables(engine)
        engine.dispose()

    def _engine(self):
        """Return a fresh SQLAlchemy engine for DB_URL. Caller must dispose it."""
        return create_engine(DB_URL)

    def _upgrade(self, target: str | None = None) -> None:
        """Run alembic upgrade to *target* (defaults to REVISION)."""
        command.upgrade(get_alembic_cfg(), target or self.REVISION)

    def _downgrade(self, target: str | None = None) -> None:
        """
        Run alembic downgrade to *target* (defaults to PARENT_REVISION). The revisions of a release seed stay applied,
        see downgrade_keeping.
        """
        downgrade_keeping(target or self.PARENT_REVISION, None if self.seed == "v3.9" else SEEDS[self.seed])

    def _upgrade_failing_after(self, statement_pattern: str) -> None:
        """
        Run the upgrade to REVISION, but stop it with :class:`InjectedFailure` right after the first statement that
        matches the regular expression *statement_pattern* (case-insensitive) has been executed.

        Every statement commits on its own (see migrations/env.py), so this leaves the database in the state of an
        installation on which the migration failed at that point. Follow it with :meth:`_upgrade` to check that the
        migration can run again from there.
        """
        self._run_failing_after(statement_pattern, self._upgrade)

    def _downgrade_failing_after(self, statement_pattern: str) -> None:
        """
        Run the downgrade to PARENT_REVISION, but stop it like :meth:`_upgrade_failing_after`. Follow it with
        :meth:`_downgrade` to check that the downgrade can run again from there.
        """
        self._run_failing_after(statement_pattern, self._downgrade)

    def _run_failing_after(self, statement_pattern: str, step: Callable[[], None]) -> None:
        from privacyidea.models import db

        pattern = re.compile(statement_pattern, re.IGNORECASE)
        matched_statements = []

        def fail_after_matching_statement(connection: Connection, cursor: Any, statement: str, parameters: Any,
                                          context: ExecutionContext, executemany: bool) -> None:
            if not matched_statements and pattern.search(statement):
                matched_statements.append(statement)
                raise InjectedFailure(statement)

        event.listen(db.engine, "after_cursor_execute", fail_after_matching_statement)
        try:
            with pytest.raises(InjectedFailure):
                step()
        finally:
            event.remove(db.engine, "after_cursor_execute", fail_after_matching_statement)

    def _assert_every_table_accepts_a_row_at_head(self) -> None:
        """
        Upgrade to head, then insert a row into every table the way the models do, ids from their sequences included.

        End a test with this when its migration inserts rows: a row whose id came from another source than the one the
        model uses, e.g. AUTO_INCREMENT instead of the sequence, makes a later insert of privacyIDEA collide with it.
        """
        self._upgrade("head")
        failures = insert_minimal_row_into_every_table()
        assert not failures, "\n".join(f"{table}: {message}" for table, message in failures)

    def _set_stamp_back_to_parent(self) -> None:
        """Set the stamp back from REVISION to its parent, keeping what the migration did (see set_stamp_before)."""
        engine = self._engine()
        try:
            set_stamp_before(engine, self.REVISION)
        finally:
            engine.dispose()

    def _load_seed_and_upgrade_to_parent(self, engine) -> None:
        """
        Load the seed of the test (see the seed fixture) into *engine* then upgrade to PARENT_REVISION.
        After this call the database is in the state immediately before the
        migration under test. The caller is responsible for disposing *engine*.
        """
        self._load_seed_and_upgrade_to(engine, self.PARENT_REVISION)

    def _load_seed_and_upgrade_to(self, engine: Engine, revision: str) -> None:
        """
        Load the seed of the test into *engine* then upgrade to *revision*, e.g. to the
        state before an earlier migration whose data the migration under test
        works on (see STARTS_BEFORE). The caller is responsible for disposing *engine*.
        """
        statements = read_seed_statements(SEEDS[self.seed])
        with engine.connect() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()
        command.upgrade(get_alembic_cfg(), revision)

    def _fetch_scalar(self, engine, query: str, params: dict | None = None):
        """Execute *query* and return the first column of the first row."""
        with engine.connect() as conn:
            return conn.execute(text(query), params or {}).scalar()

    def _insert_rows(self, engine, table: str, rows: list[dict]) -> None:
        """
        Insert *rows* into *table*, quoting the column names (e.g. ``Key``,
        ``Value``) for the active dialect via :func:`quote_identifier`.

        Bind parameters are numbered rather than named after their column: a bind
        variable may not be a reserved word either, and ``:session`` (a real
        column of ``challenge``) fails on Oracle with "ORA-01745: invalid
        host/bind variable name".

        In a release seed the id column has no default, so a row without an id
        takes it from the sequence of the table, as privacyIDEA does.
        """
        insert_rows(engine, table, rows, ids_from_sequence=self.seed != "v3.9")
