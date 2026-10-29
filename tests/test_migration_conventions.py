"""
Database-independent guards for privacyIDEA migration-file conventions.

Like tests/test_sequence_ddl.py, these checks need no database connection and
deliberately live outside tests/test_migrations.py — that module is marked
``migration`` and is excluded from the regular (coverage-reporting) unit-test
run, so a check kept there would not run on every pull request. Keeping this
here means the convention is enforced whenever a new migration is added.
"""
import ast
import pathlib
import re

from alembic.config import Config
from alembic.script import ScriptDirectory

from tests.migration_test_utils import START_REVISION

# Migrations from START_REVISION onward must prefix their docstring (the message
# Alembic prints in ``alembic history`` and the upgrade log) with the
# privacyIDEA release that introduced them, e.g.
#   """v3.12: Increase challenge column size in challenge table"""
# Migrations older than START_REVISION predate the convention and are
# intentionally not retrofitted.
VERSION_PREFIX = re.compile(r"^v\d+\.\d+(\.\d+)?:\s")

# Captures the version components of the prefix above so they can be compared
# as an ordered tuple (a missing patch level counts as 0, so "v3.13" sorts as
# (3, 13, 0), correctly between (3, 12, 0) and (3, 13, 1)).
VERSION_PREFIX_PARTS = re.compile(r"^v(\d+)\.(\d+)(?:\.(\d+))?:")


def _version_tuple(first_line: str) -> tuple[int, int, int] | None:
    """Return the (major, minor, patch) version of a docstring's first line, or
    None if it carries no recognisable ``vX.Y[.Z]:`` prefix."""
    match = VERSION_PREFIX_PARTS.match(first_line)
    if not match:
        return None
    return tuple(int(part) if part else 0 for part in match.groups())


def _script_directory() -> ScriptDirectory:
    """Build an alembic ScriptDirectory without a database connection.

    Only ``script_location`` is needed to walk the revision graph; no
    ``sqlalchemy.url`` is set because nothing connects.
    """
    migrations_dir = pathlib.Path(__file__).parent.parent / "privacyidea" / "migrations"
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations_dir))
    return ScriptDirectory.from_config(cfg)


def test_migration_chain_has_a_single_head():
    """
    The revision graph must end in exactly one head.

    Two heads mean two migrations share a down_revision, which Alembic refuses
    to upgrade ("Multiple heads are present"). It happens whenever a branch adds
    a migration on top of the head it forked from while another migration lands
    on the target branch in the meantime -- the merge itself stays conflict-free
    (the two migrations are separate files), so nothing flags it until the
    combined graph is walked.

    This check comes first because the tests below resolve "head" and would
    otherwise fail with a MultipleHeads traceback instead of naming the cause.
    """
    heads = _script_directory().get_heads()

    assert len(heads) == 1, (
        "The migration chain has more than one head: " + ", ".join(sorted(heads))
        + "\n\nRe-point the down_revision of the migration that forked off so the "
        "chain is linear again."
    )


def test_migrations_since_start_revision_have_version_prefixed_messages():
    """
    Every migration from START_REVISION to head must start its docstring with a
    ``vX.Y[.Z]:`` release prefix.

    The first docstring line is the message Alembic shows in ``alembic history``
    and the upgrade log; the prefix makes it immediately clear which privacyIDEA
    release a migration belongs to (e.g. ``v3.13: ...``). This complements
    test_migrations.py::test_migrations_since_start_revision_have_non_empty_messages,
    which only requires the message to be non-empty.
    """
    script = _script_directory()
    offenders = []
    for rev in script.iterate_revisions("head", START_REVISION):
        message = (rev.doc or "").strip()
        first_line = message.splitlines()[0] if message else ""
        if not VERSION_PREFIX.match(first_line):
            offenders.append((rev.revision, first_line))

    assert not offenders, (
        "The following migrations (from START_REVISION onward) do not begin "
        "their docstring with a 'vX.Y[.Z]: ' release prefix:\n"
        + "\n".join(f"  {rev}: {line!r}" for rev, line in offenders)
        + "\n\nStart the migration's docstring with the release that introduces "
        'it, e.g. """v3.13: Add column foo to table bar""".'
    )


def test_migration_versions_are_non_decreasing_along_chain():
    """
    Along every edge of the chain from START_REVISION to head, the ``vX.Y[.Z]:``
    release prefixes must never go backwards: a migration's parents all belong to
    its own release or an earlier one, so every v3.13 migration comes before
    every v3.14 one.

    This catches the common merge-forward mistake where a maintenance-branch
    migration (e.g. v3.13.x) gets spliced into the chain *after* the next
    feature release's migrations. Creation timestamps are deliberately NOT used
    for this: a migration authored on a maintenance branch is routinely merged
    forward later than the feature-branch migrations it must precede, so its
    file date sorts after them even when its chain position is correct. The
    release prefix encodes the intended order; the file date does not.

    Ordering *within* a single release is not constrained — those migrations
    carry no dependency on each other and their relative order is arbitrary.

    The comparison is per edge rather than along one walk of the chain, because a
    maintenance fix merged back is a *branch*: its migrations and the feature
    release's are concurrent, so any single ordering of the two is arbitrary and
    a walk could place either first. Comparing each parent with its child states
    the same rule without depending on which order the walk picks.
    """
    script = _script_directory()
    window = list(script.iterate_revisions("head", START_REVISION))
    versions = {}
    for rev in window:
        first_line = (rev.doc or "").splitlines()[0] if rev.doc else ""
        version = _version_tuple(first_line)
        if version is not None:
            versions[rev.revision] = version

    violations = []
    for rev in window:
        version = versions.get(rev.revision)
        # A missing/invalid prefix is reported by the prefix test above, on either
        # end of the edge; skip it here so the two failures don't pile onto the
        # same root cause. A parent below START_REVISION carries no prefix either.
        if version is None:
            continue
        parents = rev.down_revision or ()
        if isinstance(parents, str):
            parents = (parents,)
        for parent in parents:
            parent_version = versions.get(parent)
            if parent_version is None or parent_version <= version:
                continue
            violations.append(
                f"  {rev.revision} (v{'.'.join(str(p) for p in version)}) has the later "
                f"{parent} (v{'.'.join(str(p) for p in parent_version)}) as its parent"
            )

    assert not violations, (
        "Migration release versions go backwards along the chain (a migration "
        "has a parent that belongs to a later release):\n"
        + "\n".join(violations)
        + "\n\nRe-point the down_revisions so all migrations of one release "
        "precede those of the next."
    )


# The revision graph of 3.13.4 ends at this revision. The lint below applies to every revision that is not part of it,
# that is to the migrations of 3.14 and later.
LINTED_AFTER_REVISION = "d3a4b5c6e7f8"

# Revisions since 3.14 that break a lint rule, with the rules they break. An entry is a known defect or a deliberate
# exception, never a default: the lint fails for an entry whose rule the revision no longer breaks, so remove the entry
# together with the fix.
MIGRATION_LINT_EXCEPTIONS = {
    # The data step inserts the moved rows without an id (4b810261d282 restarts the sequence after them). The downgrade
    # recognises a table that is already gone by the error text, see below.
    "7d4e9b2c1a3f": {"insert-without-sequence-id", "error-text-guard"},
    # The downgrade drops the table of the migration and recognises a table that is already gone by the error text.
    # The texts it checks match on PostgreSQL, MariaDB, MySQL, Oracle and SQLite.
    "0147d78cbace": {"error-text-guard"},
    "173d32328846": {"error-text-guard"},
    "b2f5c9e1a7d4": {"error-text-guard"},
    "b7c8d9e0f1a2": {"error-text-guard"},
    "c1a9f7e2b840": {"error-text-guard"},
    "c8d9e0f1a2b3": {"error-text-guard"},
    "d3e8b1c47f92": {"error-text-guard"},
    "d4f5a6b7c8e9": {"error-text-guard"},
    "d9e0f1a2b3c4": {"error-text-guard"},
    # Ignores every OperationalError and ProgrammingError of CREATE SEQUENCE and DROP SEQUENCE, not only the ones of a
    # database without sequences.
    "c2d3e4f5a6b7": {"swallowed-error"},
    # Encrypts the SMS gateway secrets with the encryption functions of privacyIDEA.
    "a1b2c3d4e5f6": {"app-import"},
    # Computes the SSH key checksums with the encryption functions and the key format of the SSH key token.
    "b8c9d0e1f2a3": {"app-import"},
}

LINT_RULES = {
    "insert-without-sequence-id": "an insert into a table whose model takes the id from a sequence must take it from "
                                  "that sequence too: use an sa.Table whose id column declares the Sequence, or set "
                                  "the id. Otherwise the database fills it from the column default, if it has one, "
                                  "and a later insert of privacyIDEA collides with the row.",
    "error-text-guard": "check the schema by reflection (sa.inspect(...).has_table(), get_columns(), get_indexes()) "
                        "instead of reading the error text, which every database words differently.",
    "swallowed-error": "re-raise a database error. A migration that prints an error and carries on is stamped as done, "
                       "and its change is missing for good.",
    "app-import": "do not import privacyidea.lib or the models in a migration: a later change there changes or breaks "
                  "the migration. privacyidea.models.db and privacyidea.models.utils are meant for migrations.",
}

# Error texts that a guard compares the error message with, as databases word them for an object that already exists
# or that does not exist
ERROR_TEXTS = ("already exists", "duplicate column", "duplicate key", "already used",
               "does not exist", "doesn't exist", "no such table", "no such column", "no such constraint",
               "unknown table", "can't drop")

# Exceptions that a migration must not catch without re-raising them
DATABASE_ERRORS = {"Exception", "BaseException", "SQLAlchemyError", "DBAPIError", "DatabaseError", "OperationalError",
                   "ProgrammingError", "IntegrityError"}

MIGRATION_HELPER_MODULES = {"privacyidea.models.db", "privacyidea.models.utils"}

# An INSERT with a column list. In an f-string, the table or the columns can be a placeholder such as {name}. An INSERT
# without a column list fills the columns in their order, the id first, so it sets the id.
RAW_INSERT = re.compile(r"INSERT\s+INTO\s+[`\"]?(\w+|\{[^}]*\})[`\"]?\s*\(([^)]*)\)", re.IGNORECASE)


def _sequence_tables() -> set[str]:
    """The tables whose model takes the id from a sequence."""
    from sqlalchemy import Sequence

    from privacyidea.models import db
    return {table.name for table in db.metadata.sorted_tables
            if "id" in table.c and isinstance(table.c.id.default, Sequence)}


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _table_construct(node: ast.AST) -> tuple[str, bool] | None:
    """
    For a table() or Table() call, the table name and whether the construct declares a Sequence, which only a Table can.
    """
    if not (isinstance(node, ast.Call) and _call_name(node) in ("table", "Table") and node.args
            and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
        return None
    declares_sequence = _call_name(node) == "Table" and any(
        isinstance(inner, ast.Call) and _call_name(inner) == "Sequence" for inner in ast.walk(node))
    return node.args[0].value, declares_sequence


def _assigned_name(node: ast.AST) -> tuple[str, ast.AST] | None:
    """For an assignment to a single name, plain or annotated, the name and the assigned value."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id, node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
        return node.target.id, node.value
    return None


def _insert_target(call: ast.Call, constructs: dict[str, tuple[str, bool]]) -> tuple[str, bool] | None:
    """
    For an insert(), bulk_insert() or .insert() call, the table construct it writes into: a name bound to a construct,
    or a construct written in place.
    """
    if _call_name(call) in ("insert", "bulk_insert") and call.args:
        target = call.args[0]
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "insert":
        target = call.func.value
    else:
        return None
    if isinstance(target, ast.Name):
        return constructs.get(target.id)
    return _table_construct(target)


def _sets_id(statement: ast.stmt) -> bool:
    """
    Whether the statement gives the inserted rows an id: an id= keyword, a dictionary with an "id" key, or "id" in the
    column list of from_select(). An "id" anywhere else, for example in the select of from_select(), does not count.
    """
    for node in ast.walk(statement):
        if isinstance(node, ast.keyword) and node.arg == "id":
            return True
        if isinstance(node, ast.Dict) and any(isinstance(key, ast.Constant) and key.value == "id" for key in node.keys):
            return True
        if (isinstance(node, ast.Call) and _call_name(node) == "from_select" and node.args
                and isinstance(node.args[0], (ast.List, ast.Tuple))
                and any(isinstance(element, ast.Constant) and element.value == "id" for element in node.args[0].elts)):
            return True
    return False


def _string_text(node: ast.AST) -> str | None:
    """The text of a string literal. In an f-string, each placeholder becomes {expression}."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant) else f"{{{ast.unparse(part.value)}}}"
                       for part in node.values)
    return None


def _inserts_without_sequence_id(tree: ast.Module, sequence_tables: set[str]) -> list[str]:
    """
    The sequence-backed tables that the migration inserts into without taking the id from the sequence. The lint cannot
    resolve the placeholders of an f-string: an INSERT whose table is a placeholder counts with the placeholder as its
    table, and a placeholder in the column list does not count as the id column.
    """
    constructs = {}
    functions = {}
    for node in ast.walk(tree):
        assigned = _assigned_name(node)
        if assigned and _table_construct(assigned[1]):
            constructs[assigned[0]] = _table_construct(assigned[1])
        if isinstance(node, ast.FunctionDef):
            for returned in ast.walk(node):
                if isinstance(returned, ast.Return) and _table_construct(returned.value):
                    functions[node.name] = _table_construct(returned.value)
    for node in ast.walk(tree):
        assigned = _assigned_name(node)
        if assigned and isinstance(assigned[1], ast.Call) and _call_name(assigned[1]) in functions:
            constructs[assigned[0]] = functions[_call_name(assigned[1])]

    tables = set()
    compound_statements = (ast.FunctionDef, ast.ClassDef, ast.If, ast.For, ast.While, ast.Try, ast.With)
    for statement in ast.walk(tree):
        if not isinstance(statement, ast.stmt) or isinstance(statement, compound_statements):
            continue
        sets_id = _sets_id(statement)
        for call in ast.walk(statement):
            if not isinstance(call, ast.Call):
                continue
            target = _insert_target(call, constructs)
            if target:
                table_name, declares_sequence = target
                if table_name in sequence_tables and not declares_sequence and not sets_id:
                    tables.add(table_name)
    for node in ast.walk(tree):
        text = _string_text(node)
        if text is None:
            continue
        for match in RAW_INSERT.finditer(text):
            table_name = match.group(1).lower()
            columns = [column.strip(' `"').lower() for column in match.group(2).split(",")]
            if (table_name in sequence_tables or table_name.startswith("{")) and "id" not in columns:
                tables.add(table_name)
    return sorted(tables)


def _names_a_database_error(node: ast.AST) -> bool:
    return ((isinstance(node, ast.Name) and node.id in DATABASE_ERRORS)
            or (isinstance(node, ast.Attribute) and node.attr in DATABASE_ERRORS))


def _catches_database_errors(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    caught = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(_names_a_database_error(name) for name in caught)


def _suppresses_database_errors(statement: ast.With) -> bool:
    """Whether a with statement ignores database errors through contextlib.suppress()."""
    return any(isinstance(item.context_expr, ast.Call) and _call_name(item.context_expr) == "suppress"
               and any(_names_a_database_error(argument) for argument in item.context_expr.args)
               for item in statement.items)


def _compares_a_text(handler: ast.ExceptHandler) -> bool:
    """Whether the handler checks if a text occurs in something, as a guard on the error message does."""
    for node in ast.walk(handler):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)
                and any(isinstance(operator, (ast.In, ast.NotIn)) for operator in node.ops)):
            return True
    return False


def _migration_lint_findings(source: str, sequence_tables: set[str]) -> dict[str, list[str]]:
    """The lint rules (keys of LINT_RULES) that the migration source breaks, with where it breaks them."""
    tree = ast.parse(source)
    findings: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        imported = []
        if isinstance(node, ast.ImportFrom) and node.module:
            imported = [node.module]
        elif isinstance(node, ast.Import):
            imported = [alias.name for alias in node.names]
        for module in imported:
            if module.startswith("privacyidea") and module not in MIGRATION_HELPER_MODULES:
                findings.setdefault("app-import", []).append(module)
        if isinstance(node, ast.ExceptHandler):
            texts = [inner.value.lower() for inner in ast.walk(node)
                     if isinstance(inner, ast.Constant) and isinstance(inner.value, str)]
            catches_database_errors = _catches_database_errors(node)
            if (any(error_text in text for text in texts for error_text in ERROR_TEXTS)
                    or (catches_database_errors and _compares_a_text(node))):
                findings.setdefault("error-text-guard", []).append(f"line {node.lineno}")
            elif catches_database_errors and not any(isinstance(inner, ast.Raise) for inner in ast.walk(node)):
                findings.setdefault("swallowed-error", []).append(f"line {node.lineno}")
        if isinstance(node, ast.With) and _suppresses_database_errors(node):
            findings.setdefault("swallowed-error", []).append(f"line {node.lineno}")
    tables = _inserts_without_sequence_id(tree, sequence_tables)
    if tables:
        findings["insert-without-sequence-id"] = tables
    return findings


def test_migrations_since_3_14_follow_the_lint_rules():
    """
    Every migration since 3.14 follows the rules of LINT_RULES, apart from the entries of MIGRATION_LINT_EXCEPTIONS.
    """
    sequence_tables = _sequence_tables()
    script = _script_directory()
    released = {revision.revision for revision in script.iterate_revisions(LINTED_AFTER_REVISION, "base")}
    problems = []
    for revision in script.walk_revisions():
        if revision.revision in released:
            continue
        findings = _migration_lint_findings(pathlib.Path(revision.path).read_text(), sequence_tables)
        expected = MIGRATION_LINT_EXCEPTIONS.get(revision.revision, set())
        for rule, places in sorted(findings.items()):
            if rule not in expected:
                problems.append(f"{revision.revision} ({', '.join(places)}): {LINT_RULES[rule]}")
        for rule in sorted(expected - findings.keys()):
            problems.append(f"{revision.revision} no longer breaks '{rule}': remove it from MIGRATION_LINT_EXCEPTIONS.")
    assert not problems, "\n".join(problems)


def test_lint_flags_an_insert_without_the_sequence():
    """An insert through a lightweight table() construct leaves the id to the column default."""
    source = (
        "from sqlalchemy.sql import column, insert, table\n"
        "tokeninfo = table('tokeninfo', column('id'), column('token_id'))\n"
        "def upgrade():\n"
        "    op.get_bind().execute(insert(tokeninfo).values(token_id=1))\n"
        "    op.execute(\"INSERT INTO tokeninfo (token_id, Key) VALUES (1, 'a')\")\n"
    )
    assert _migration_lint_findings(source, {"tokeninfo"}) == {"insert-without-sequence-id": ["tokeninfo"]}


def test_lint_accepts_an_insert_with_the_sequence_or_an_id():
    """An insert through a Table that declares the Sequence, or with an explicit id, takes no id from the default."""
    source = (
        "import sqlalchemy as sa\n"
        "tokeninfo = sa.Table('tokeninfo', sa.MetaData(),\n"
        "                     sa.Column('id', sa.Integer, sa.Sequence('tokeninfo_seq'), primary_key=True))\n"
        "lightweight = sa.table('tokeninfo', sa.column('id'))\n"
        "def upgrade():\n"
        "    op.get_bind().execute(sa.insert(tokeninfo).values(token_id=1))\n"
        "    op.get_bind().execute(lightweight.insert().values(id=5, token_id=1))\n"
        "    op.execute('INSERT INTO tokeninfo (id, token_id) VALUES (5, 1)')\n"
        "    op.bulk_insert(lightweight, [{'id': 6, 'token_id': 1}])\n"
        "    op.get_bind().execute(lightweight.insert().from_select(['id', 'token_id'], sa.select(token.c.id, 1)))\n"
        "    op.execute('INSERT INTO tokeninfo SELECT 7, 1')\n"
    )
    assert _migration_lint_findings(source, {"tokeninfo"}) == {}


def test_lint_flags_inserts_through_inline_and_annotated_constructs_and_f_strings():
    """
    An insert into a construct written in place or bound by an annotated assignment, an INSERT in an f-string, and an
    insert whose only "id" is in the select of from_select() leave the id to the column default.
    """
    source = (
        "import sqlalchemy as sa\n"
        "annotated: sa.TableClause = sa.table('tokeninfo', sa.column('token_id'))\n"
        "def upgrade():\n"
        "    op.bulk_insert(sa.table('tokeninfo', sa.column('token_id')), [{'token_id': 1}])\n"
        "    op.get_bind().execute(sa.table('tokeninfo', sa.column('token_id')).insert().values(token_id=1))\n"
        "    op.get_bind().execute(annotated.insert().values(token_id=1))\n"
        "    op.execute(f'INSERT INTO {name} (token_id) VALUES (1)')\n"
    )
    assert _migration_lint_findings(source, {"tokeninfo"}) == {"insert-without-sequence-id": ["tokeninfo", "{name}"]}

    source = (
        "import sqlalchemy as sa\n"
        "tokeninfo = sa.table('tokeninfo', sa.column('token_id'))\n"
        "def upgrade():\n"
        "    op.get_bind().execute(tokeninfo.insert().from_select(['token_id'], sa.select(sa.column('id'))))\n"
    )
    assert _migration_lint_findings(source, {"tokeninfo"}) == {"insert-without-sequence-id": ["tokeninfo"]}


def test_lint_flags_error_text_guards_and_swallowed_errors():
    source = (
        "def upgrade():\n"
        "    try:\n"
        "        op.add_column('token', sa.Column('a', sa.Integer()))\n"
        "    except OperationalError as error:\n"
        "        if 'already exists' not in str(error):\n"
        "            raise\n"
        "    try:\n"
        "        op.drop_column('token', 'b')\n"
        "    except Exception as error:\n"
        "        print(error)\n"
        "    try:\n"
        "        int('x')\n"
        "    except ValueError:\n"
        "        pass\n"
    )
    assert _migration_lint_findings(source, set()) == {"error-text-guard": ["line 4"], "swallowed-error": ["line 9"]}


def test_lint_flags_guards_on_a_missing_object():
    source = (
        "def downgrade():\n"
        "    try:\n"
        "        op.drop_table('usersetting')\n"
        "    except (OperationalError, ProgrammingError) as error:\n"
        "        if 'no such table' in str(error) or 'does not exist' in str(error):\n"
        "            print('Table already removed.')\n"
        "        else:\n"
        "            raise\n"
    )
    assert _migration_lint_findings(source, set()) == {"error-text-guard": ["line 4"]}


def test_lint_flags_suppressed_errors_and_guards_on_any_text():
    """
    contextlib.suppress() ignores a database error like a handler without a raise does. A handler that raises only
    when the error message lacks some text guards on that text, also when the text is not in ERROR_TEXTS.
    """
    source = (
        "import contextlib\n"
        "def upgrade():\n"
        "    with contextlib.suppress(OperationalError):\n"
        "        op.drop_table('a')\n"
        "    try:\n"
        "        op.drop_table('b')\n"
        "    except OperationalError as error:\n"
        "        if 'some text' not in str(error):\n"
        "            raise\n"
        "    with contextlib.suppress(ValueError):\n"
        "        int('x')\n"
    )
    assert _migration_lint_findings(source, set()) == {"swallowed-error": ["line 3"], "error-text-guard": ["line 7"]}
