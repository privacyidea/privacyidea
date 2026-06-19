"""
Shared utilities and base class for database migration tests.

See tests/README.md for the full guide on when a per-migration test is
required and how to write one.
"""

import os
import pathlib

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect as sa_inspect, text

DB_URL = os.environ.get("TEST_DATABASE_URL", "")

SEED_SQL_DIR = pathlib.Path(__file__).parent / "testdata" / "migrations"

# Pinned starting revision — must match the constant in test_migrations.py.
START_REVISION = "5cb310101a1f"


def is_postgres(db_url: str = DB_URL) -> bool:
    return db_url.startswith("postgresql")


def is_oracle(db_url: str = DB_URL) -> bool:
    return db_url.startswith("oracle")


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
    else:
        dialect = "mariadb"
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
        ctx.pop()

    @pytest.fixture(autouse=True)
    def clean_database(self, flask_app):
        """Wipe the database before and after every test."""
        engine = create_engine(DB_URL)
        drop_all_tables(engine)
        engine.dispose()
        yield
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
        """Run alembic downgrade to *target* (defaults to PARENT_REVISION)."""
        command.downgrade(get_alembic_cfg(), target or self.PARENT_REVISION)

    def _load_seed_and_upgrade_to_parent(self, engine) -> None:
        """
        Load the v3.9 seed into *engine* then upgrade to PARENT_REVISION.
        After this call the database is in the state immediately before the
        migration under test.  The caller is responsible for disposing *engine*.
        """
        statements = read_seed_statements()
        with engine.connect() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()
        command.upgrade(get_alembic_cfg(), self.PARENT_REVISION)

    def _fetch_scalar(self, engine, query: str, params: dict | None = None):
        """Execute *query* and return the first column of the first row."""
        with engine.connect() as conn:
            return conn.execute(text(query), params or {}).scalar()

    def _insert_rows(self, engine, table: str, rows: list[dict]) -> None:
        """
        Insert *rows* into *table* using dialect-aware quoting.

        Column names that need quoting (e.g. ``Key``, ``Value``) are quoted
        with double-quotes on Postgres/Oracle and back-ticks on MariaDB/MySQL.

        Oracle is special: it folds unquoted identifiers to upper case, so an
        all-lower-case column (created unquoted) must be referenced unquoted to
        match, while a mixed-case column like ``Key`` (created quoted) must be
        quoted exactly. Quoting an all-lower-case name would look for a
        lower-case column that does not exist (ORA-00904).
        """
        if not rows:
            return
        if is_postgres():
            quote = lambda c: f'"{c}"'
        elif is_oracle():
            quote = lambda c: f'"{c}"' if any(ch.isupper() for ch in c) else c
        else:
            quote = lambda c: f"`{c}`"
        cols = list(rows[0].keys())
        col_list = ", ".join(quote(c) for c in cols)
        placeholders = ", ".join(f":{c}" for c in cols)
        stmt = text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})")
        with engine.connect() as conn:
            for row in rows:
                conn.execute(stmt, row)
            conn.commit()
