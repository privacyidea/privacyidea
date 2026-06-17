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
    Walking the chain from START_REVISION to head, the ``vX.Y[.Z]:`` release
    prefixes must never go backwards: every v3.13 migration has to come before
    every v3.14 one, and so on.

    This catches the common merge-forward mistake where a maintenance-branch
    migration (e.g. v3.13.x) gets spliced into the chain *after* the next
    feature release's migrations. Creation timestamps are deliberately NOT used
    for this: a migration authored on a maintenance branch is routinely merged
    forward later than the feature-branch migrations it must precede, so its
    file date sorts after them even when its chain position is correct. The
    release prefix encodes the intended order; the file date does not.

    Ordering *within* a single release is not constrained — those migrations
    carry no dependency on each other and their relative order is arbitrary.
    """
    script = _script_directory()
    # iterate_revisions yields head-first; reverse to walk in upgrade order.
    ordered = list(reversed(list(script.iterate_revisions("head", START_REVISION))))

    violations = []
    previous_version = None
    previous_revision = None
    for rev in ordered:
        first_line = (rev.doc or "").splitlines()[0] if rev.doc else ""
        version = _version_tuple(first_line)
        if version is None:
            # Missing/invalid prefix is reported by the prefix test above; skip
            # it here so the two failures don't pile onto the same root cause.
            continue
        if previous_version is not None and version < previous_version:
            previous_label = ".".join(str(p) for p in previous_version)
            current_label = ".".join(str(p) for p in version)
            violations.append(
                f"  {rev.revision} (v{current_label}) is ordered after "
                f"{previous_revision} (v{previous_label})"
            )
        previous_version = version
        previous_revision = rev.revision

    assert not violations, (
        "Migration release versions go backwards along the chain (a later "
        "migration belongs to an earlier release than its predecessor):\n"
        + "\n".join(violations)
        + "\n\nRe-point the down_revisions so all migrations of one release "
        "precede those of the next."
    )
