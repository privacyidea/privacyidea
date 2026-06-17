"""
Database-independent guards for privacyIDEA migration-file conventions.

Like tests/test_sequence_ddl.py, these checks need no database connection and
deliberately live outside tests/test_migrations.py — that module is marked
``migration`` and is excluded from the regular (coverage-reporting) unit-test
run, so a check kept there would not run on every pull request. Keeping this
here means the convention is enforced whenever a new migration is added.
"""
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


def _script_directory() -> ScriptDirectory:
    """Build an alembic ScriptDirectory without a database connection.

    Only ``script_location`` is needed to walk the revision graph; no
    ``sqlalchemy.url`` is set because nothing connects.
    """
    migrations_dir = pathlib.Path(__file__).parent.parent / "privacyidea" / "migrations"
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations_dir))
    return ScriptDirectory.from_config(cfg)


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
