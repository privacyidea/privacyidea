"""
Database-independent guards for sequence DDL portability.

These checks need no database connection: they statically scan the migration
files and exercise the per-dialect SQL builders in privacyidea.models.db. They
live outside tests/test_migrations.py on purpose — that module is marked
``migration`` and is excluded from the regular (coverage-reporting) unit-test
run, so anything kept there neither counts towards coverage nor runs on every
PR. Keeping these here means they run in the standard suite and guard against
Galera-/Oracle-unsafe sequence DDL slipping into a new migration.
"""
import pathlib


def _iter_op_execute_sql_literals():
    """
    Yield ``(location, sql_upper)`` for every literal SQL string passed to an
    ``op.execute(...)`` call across all migration version files. ``location`` is
    ``"<filename>:<lineno>"`` and ``sql_upper`` is the upper-cased literal.

    Only the static literal content is inspected — docstrings, comments and
    print() messages are ignored, as are dynamically built statements passed via
    a variable or a helper call (those resolve to an empty literal). Both plain
    strings and f-strings are covered (an f-string's literal segments are
    ast.Constant nodes), and ``text("...")`` / ``sa.text("...")`` wrappers are
    unwrapped.
    """
    import ast

    def _literal_sql(node) -> str:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return "".join(
                part.value for part in node.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            )
        if isinstance(node, ast.Call) and node.args:
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "text":
                return _literal_sql(node.args[0])
        return ""

    def _is_op_execute(node) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "execute"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
        )

    versions_dir = pathlib.Path(__file__).parent.parent / "privacyidea" / "migrations" / "versions"
    for path in sorted(versions_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if _is_op_execute(node) and node.args:
                sql = _literal_sql(node.args[0])
                if sql:
                    yield f"{path.name}:{node.lineno}", sql.upper()


def test_migrations_do_not_emit_raw_create_sequence_sql():
    """
    Migrations must create sequences via SQLAlchemy's CreateSequence construct,
    never a raw "CREATE SEQUENCE ..." SQL string.

    CreateSequence is rewritten by the increment_by_zero @compiles hook in
    privacyidea.models.db, which appends INCREMENT BY 0 on MariaDB. A Galera
    cluster only accepts a cached sequence defined that way; a raw string
    bypasses the hook and fails with "CACHE without INCREMENT BY 0 in Galera
    cluster". We cannot reproduce that rejection in CI — it needs a live wsrep
    provider, and standalone MariaDB accepts the cached sequence — so this
    static check is the guard against the gap.

    ALTER SEQUENCE ... RESTART hits the same constraint and is guarded by
    test_migrations_do_not_emit_raw_alter_sequence_sql. DROP SEQUENCE carries no
    Galera constraint and may stay a raw string.
    """
    offenders = [loc for loc, sql in _iter_op_execute_sql_literals() if "CREATE SEQUENCE" in sql]
    assert not offenders, (
        "The following migrations build a sequence from a raw 'CREATE SEQUENCE' "
        "string instead of SQLAlchemy's CreateSequence construct:\n"
        + "\n".join(f"  {o}" for o in offenders)
        + "\n\nUse op.execute(CreateSequence(Sequence(name, start=...), if_not_exists=...)) "
        "so the increment_by_zero hook can make it Galera-safe."
    )


def test_migrations_do_not_emit_raw_alter_sequence_sql():
    """
    Migrations must not RESTART a sequence with a raw "ALTER SEQUENCE ..." SQL
    string. On a Galera cluster, ALTER SEQUENCE ... RESTART on a cached sequence
    fails with the same "CACHE without INCREMENT BY 0 in Galera cluster" error as
    CREATE SEQUENCE does. SQLAlchemy has no DDL construct for ALTER SEQUENCE that
    the increment_by_zero hook could rewrite, and INCREMENT BY 0 is valid only on
    MariaDB (Postgres rejects a zero increment), so the statement cannot be a
    single dialect-agnostic literal. As with CREATE, the rejection needs a live
    wsrep provider we don't have in CI, so this static check is the guard.

    On Oracle the same statement needs different syntax again (RESTART START
    WITH n; RESTART WITH n is a syntax error), so a raw string can be correct on
    at most one backend.

    Use privacyidea.models.db.build_restart_sequence_sql(name, n, dialect_name),
    whose per-dialect output is verified by test_build_restart_sequence_sql_per_dialect.
    """
    offenders = [loc for loc, sql in _iter_op_execute_sql_literals() if "ALTER SEQUENCE" in sql]
    assert not offenders, (
        "The following migrations RESTART a sequence from a raw 'ALTER SEQUENCE' "
        "string, which is not portable across backends:\n"
        + "\n".join(f"  {o}" for o in offenders)
        + "\n\nUse op.execute(build_restart_sequence_sql(name, restart_with, bind.dialect.name)) "
        "(privacyidea.models.db) for the correct per-dialect syntax."
    )


def test_create_sequence_is_galera_safe_on_mariadb():
    """
    The increment_by_zero hook (privacyidea.models.db) must render CREATE
    SEQUENCE with INCREMENT BY 0 on MariaDB, and must NOT do so on PostgreSQL
    (which rejects a zero increment). This guards the hook itself against being
    removed or scoped to the wrong dialect — the thing every sequence migration
    and db.create_all() rely on to work on a Galera cluster.
    """
    from sqlalchemy import Sequence
    from sqlalchemy.schema import CreateSequence
    from sqlalchemy.dialects import mysql, postgresql
    import privacyidea.models.db  # noqa: F401 - importing registers the @compiles hook

    seq = Sequence("dummy_galera_check_seq", start=1)

    mariadb_sql = str(CreateSequence(seq).compile(dialect=mysql.dialect(is_mariadb=True))).upper()
    assert "INCREMENT BY 0" in mariadb_sql, (
        f"CREATE SEQUENCE on MariaDB must include INCREMENT BY 0 to work on Galera, got: {mariadb_sql!r}"
    )

    postgres_sql = str(CreateSequence(seq).compile(dialect=postgresql.dialect())).upper()
    assert "INCREMENT BY 0" not in postgres_sql, (
        f"CREATE SEQUENCE on PostgreSQL must NOT include INCREMENT BY 0 (zero increment is invalid), "
        f"got: {postgres_sql!r}"
    )


def test_build_restart_sequence_sql_per_dialect():
    """
    build_restart_sequence_sql (privacyidea.models.db) must emit the correct
    ALTER SEQUENCE ... RESTART syntax for each backend. This is the ALTER
    counterpart of test_create_sequence_is_galera_safe_on_mariadb and guards the
    helper every sequence-restarting migration relies on:

    * MariaDB/MySQL: RESTART WITH n + INCREMENT BY 0 (Galera rejects a cached
      sequence's RESTART without it).
    * PostgreSQL: plain RESTART WITH n (a zero increment is invalid).
    * Oracle: RESTART START WITH n (RESTART WITH n is a syntax error, and
      INCREMENT BY 0 is invalid).
    """
    from privacyidea.models.db import build_restart_sequence_sql

    for dialect_name in ("mariadb", "mysql"):
        sql = build_restart_sequence_sql("dummy_seq", 5, dialect_name).upper()
        assert "RESTART WITH 5" in sql and "INCREMENT BY 0" in sql, (
            f"ALTER SEQUENCE RESTART on {dialect_name} must be 'RESTART WITH n INCREMENT BY 0' "
            f"to work on Galera, got: {sql!r}"
        )

    postgres_sql = build_restart_sequence_sql("dummy_seq", 5, "postgresql").upper()
    assert "RESTART WITH 5" in postgres_sql and "INCREMENT BY 0" not in postgres_sql, (
        f"ALTER SEQUENCE RESTART on PostgreSQL must be 'RESTART WITH n' without INCREMENT BY 0 "
        f"(zero increment is invalid), got: {postgres_sql!r}"
    )

    oracle_sql = build_restart_sequence_sql("dummy_seq", 5, "oracle").upper()
    assert "RESTART START WITH 5" in oracle_sql and "INCREMENT BY 0" not in oracle_sql, (
        f"ALTER SEQUENCE RESTART on Oracle must be 'RESTART START WITH n' "
        f"('RESTART WITH n' is a syntax error there), got: {oracle_sql!r}"
    )
