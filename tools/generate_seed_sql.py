#!/usr/bin/env python3
"""
Generate dialect-specific seed SQL from a historical privacyIDEA models.py
or models/ package directory.

────────────────────────────────────────────────────────────────────────────
USAGE
────────────────────────────────────────────────────────────────────────────

  Single file (historical, e.g. v3.9 where models lived in one file):
    python tools/generate_seed_sql.py <path/to/models.py> <dialect> [out.sql]

  Directory (current split-package layout, e.g. privacyidea/models/):
    python tools/generate_seed_sql.py <path/to/models/> <dialect> [out.sql]

  dialect: mariadb | postgresql

────────────────────────────────────────────────────────────────────────────
EXTRACTING A HISTORICAL VERSION FROM GIT
────────────────────────────────────────────────────────────────────────────

  The pinned migration start revision corresponds to privacyIDEA v3.9, where
  all models lived in a single models.py.  Extract it with git:

    # List available v3.9 tags
    git tag | grep "3\\.9"

    # Export the single-file models from a specific tag
    git show v3.9.3:privacyidea/models.py > /tmp/models_v3.9.py

    # Generate seeds for both dialects
    python tools/generate_seed_sql.py /tmp/models_v3.9.py mariadb \\
        tests/testdata/migrations/seed_v3.9_5cb310101a1f_mariadb.sql

    python tools/generate_seed_sql.py /tmp/models_v3.9.py postgresql \\
        tests/testdata/migrations/seed_v3.9_5cb310101a1f_postgresql.sql

  For a version that already had the split-package layout, check out the
  directory into a temp location first:

    git archive <tag> privacyidea/models/ | tar -x -C /tmp/
    python tools/generate_seed_sql.py /tmp/privacyidea/models/ mariadb out.sql

────────────────────────────────────────────────────────────────────────────
TESTING WITH THE CURRENT MODELS
────────────────────────────────────────────────────────────────────────────

    python tools/generate_seed_sql.py privacyidea/models/ postgresql
    python tools/generate_seed_sql.py privacyidea/models/ mariadb

────────────────────────────────────────────────────────────────────────────
HOW IT WORKS
────────────────────────────────────────────────────────────────────────────

  The script mocks away all privacyIDEA-internal imports that are irrelevant
  for schema extraction (crypto, logging, config, …), then uses SQLAlchemy's
  DDL compiler to render CREATE TABLE / CREATE SEQUENCE statements for the
  target dialect — no live database or Flask app required.

  The output is a pure-DDL file (schema only, no data).  The committed seed
  files under tests/testdata/migrations/ were produced by this script and
  then extended with representative INSERT rows and an alembic_version stamp
  so that the migration tests start from a realistic historical database state.

  When the START_REVISION pin is bumped, re-run this script against the
  corresponding git tag to regenerate the DDL, then add the INSERT rows back
  (or copy them from the previous seed) before committing.
"""

import argparse
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock



class _LibMockFinder(importlib.abc.MetaPathFinder):
    """
    A meta-path finder that intercepts any `privacyidea.lib.*` import not
    already satisfied by sys.modules and returns an _AutoMockPackage for it.
    This lets models submodules do `from privacyidea.lib.error import Foo`
    without us having to enumerate every lib.* submodule in advance.
    """
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("privacyidea.lib") and fullname not in sys.modules:
            mod = _AutoMockPackage(fullname)
            sys.modules[fullname] = mod
            spec = importlib.machinery.ModuleSpec(
                fullname,
                loader=importlib.machinery.SourcelessFileLoader(fullname, ""),
                is_package=True,
            )
            spec.submodule_search_locations = []
            mod.__spec__ = spec
            # Patch the loader exec_module to be a no-op so nothing is executed
            spec.loader.exec_module = lambda m: None
            spec.loader.create_module = lambda s: mod
            return spec
        return None


def _make_mock_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__spec__ = None
    return mod


class _AutoMockPackage(types.ModuleType):
    """
    A module that masquerades as a package: any attribute access or sub-module
    import returns a MagicMock, so callers like `from privacyidea.lib.error import X`
    get a MagicMock for X without us having to enumerate every possible sub-module.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.__path__ = []       # marks this as a package to the import system
        self.__package__ = name
        self.__spec__ = None
        self._children: dict[str, types.ModuleType] = {}

    def __getattr__(self, item: str):
        return MagicMock()

    def _child(self, subname: str) -> "types.ModuleType":
        """Return (creating if needed) a child mock module for `subname`."""
        full = f"{self.__name__}.{subname}"
        if full not in self._children:
            child = _AutoMockPackage(full)
            self._children[full] = child
            sys.modules[full] = child
        return self._children[full]


def _install_mocks() -> None:
    """
    Inject mock modules for all privacyIDEA-internal imports that models.py
    pulls in but that have nothing to do with the schema definition.
    """
    # Install the meta-path finder first so any lib.* submodule not
    # explicitly mocked below is auto-stubbed on first import.
    if not any(isinstance(f, _LibMockFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _LibMockFinder())

    # Build an auto-stubbing privacyidea.lib package so that any submodule
    # import (lib.crypto, lib.log, lib.error, lib.utils, …) is satisfied
    # without enumerating every possible import.
    lib_pkg = _AutoMockPackage("privacyidea.lib")

    # Populate specific submodules that need particular behaviour.

    # crypto stubs — covers both the historical single-file models.py (v3.9)
    # and the current split-package models/ where some names moved between modules.
    crypto = _AutoMockPackage("privacyidea.lib.crypto")
    for name in ("encrypt", "encryptPin", "decryptPin", "geturandom", "hash",
                 "SecretObj", "get_rand_digit_str", "pass_hash", "verify_pass_hash",
                 "hexlify_and_unicode"):
        setattr(crypto, name, MagicMock())

    # log stub — log_with is a decorator factory
    log_mod = _AutoMockPackage("privacyidea.lib.log")
    def _log_with(log, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    log_mod.log_with = _log_with

    # utils stubs
    utils = _AutoMockPackage("privacyidea.lib.utils")
    utils.is_true = MagicMock(return_value=False)
    utils.convert_column_to_unicode = lambda v: v
    utils.hexlify_and_unicode = MagicMock(return_value="")

    # framework stub
    framework = _AutoMockPackage("privacyidea.lib.framework")
    framework.get_app_config_value = MagicMock(return_value=False)

    # config stub
    config_mod = _AutoMockPackage("privacyidea.lib.config")
    config_mod.invalidate_config_object = MagicMock()

    # dateutil.tz stub — tzutc must be a real tzinfo subclass because some
    # model columns call datetime.now(tz=tzutc()) as a default at class-definition time, and datetime.now()
    # rejects non-tzinfo arguments.
    import datetime as _dt
    class _UTC(_dt.tzinfo):
        _zero = _dt.timedelta(0)
        def utcoffset(self, dt): return self._zero
        def tzname(self, dt): return "UTC"
        def dst(self, dt): return self._zero

    dateutil = _make_mock_module("dateutil")
    tz = _make_mock_module("dateutil.tz")
    tz.tzutc = _UTC

    mocks = {
        # top-level stub for the single-file case (overridden in directory mode)
        "privacyidea": _make_mock_module("privacyidea"),
        "privacyidea.lib": lib_pkg,
        "privacyidea.lib.crypto": crypto,
        "privacyidea.lib.log": log_mod,
        "privacyidea.lib.utils": utils,
        "privacyidea.lib.framework": framework,
        "privacyidea.lib.config": config_mod,
        "dateutil": dateutil,
        "dateutil.tz": tz,
    }
    for key, mod in mocks.items():
        sys.modules[key] = mod



def _load_single_file(models_path: Path):
    """
    Load a historical single-file models.py in isolation.
    Returns the loaded module.
    """
    _install_mocks()

    spec = importlib.util.spec_from_file_location("_pi_models", models_path)
    module = importlib.util.module_from_spec(spec)

    # models.py uses relative imports like `from .lib.log import log_with`
    # Make it think it lives inside a package called `privacyidea`.
    module.__package__ = "privacyidea"
    sys.modules["privacyidea._pi_models"] = module

    spec.loader.exec_module(module)
    return module


def _load_package_directory(models_dir: Path):
    """
    Load a split-package models/ directory by inserting its *parent* onto
    sys.path so that `import privacyidea.models` resolves naturally, while
    all non-schema privacyIDEA imports (lib.crypto, lib.log, …) are mocked.

    The tricky part: the real privacyidea/ package on disk has a real lib/
    sub-package.  We must make sure Python uses our mocked lib.* modules
    instead of loading the real ones.  Strategy:

      1. Install all mocks into sys.modules.
      2. Add the repo root to sys.path so `import privacyidea` finds the
         real package directory.
      3. Remove only privacyidea itself and privacyidea.models* from
         sys.modules so the real models/ package can be imported fresh —
         but leave our lib.* mocks in place so the submodules use them.
      4. Also register a real (but empty) privacyidea package module that
         points at the correct __path__, so Python resolves the real models/
         sub-package while still routing lib.* through our stubs.

    Returns the loaded `privacyidea.models` module.
    """
    _install_mocks()

    repo_root = str(models_dir.parent.parent.resolve())  # …/privacyidea -> repo root
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Remove any previously cached privacyidea top-level and models submodules
    # so they are freshly loaded from disk, but keep lib.* mocks intact.
    for key in list(sys.modules):
        if key == "privacyidea" or key.startswith("privacyidea.models"):
            del sys.modules[key]

    # Build a minimal real privacyidea package module that resolves __path__
    # correctly, so `from .models.xxx import …` works inside models/ submodules,
    # while `from privacyidea.lib.crypto import …` still hits our mocks.
    import importlib.machinery as _machinery
    pi_path = str(models_dir.parent.resolve())  # …/privacyidea/
    pi_pkg = types.ModuleType("privacyidea")
    pi_pkg.__path__ = [pi_path]
    pi_pkg.__package__ = "privacyidea"
    pi_pkg.__spec__ = _machinery.ModuleSpec(
        "privacyidea", None, origin=pi_path, is_package=True
    )
    sys.modules["privacyidea"] = pi_pkg

    import privacyidea.models as models_pkg  # noqa: E402
    return models_pkg



def _render_mariadb(metadata) -> str:
    from sqlalchemy import create_engine
    from sqlalchemy.schema import CreateTable

    engine = create_engine(
        "mysql+pymysql://user:pass@localhost/db",
        connect_args={"connect_timeout": 0},
        pool_pre_ping=False,
    )

    lines = [
        "-- Auto-generated MariaDB seed SQL",
        "-- Source: SQLAlchemy metadata",
        "--",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]

    for table in metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=engine.dialect))
        lines.append(ddl.strip().rstrip(";") + ";")
        lines.append("")

    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    return "\n".join(lines)


def _render_postgresql(metadata) -> str:
    from sqlalchemy import create_engine, Sequence as SASequence
    from sqlalchemy.schema import CreateTable, CreateSequence

    engine = create_engine(
        "postgresql+psycopg2://user:pass@localhost/db",
        connect_args={"connect_timeout": 0},
        pool_pre_ping=False,
    )

    lines = [
        "-- Auto-generated PostgreSQL seed SQL",
        "-- Source: SQLAlchemy metadata",
        "--",
        "",
    ]

    seen_sequences: set[str] = set()
    for table in metadata.sorted_tables:
        for col in table.columns:
            for default in (col.default, col.onupdate):
                if isinstance(default, SASequence) and default.name not in seen_sequences:
                    seen_sequences.add(default.name)
                    seq_ddl = str(CreateSequence(default).compile(dialect=engine.dialect))
                    lines.append(seq_ddl.strip().rstrip(";") + ";")

    if seen_sequences:
        lines.append("")

    for table in metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=engine.dialect))
        lines.append(ddl.strip().rstrip(";") + ";")
        lines.append("")

    return "\n".join(lines)



def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate dialect-specific DDL seed SQL from a privacyIDEA "
            "models.py file or models/ package directory."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Historical single-file (v3.9):\n"
            "  git show v3.9.3:privacyidea/models.py > /tmp/models_v3.9.py\n"
            "  python tools/generate_seed_sql.py /tmp/models_v3.9.py mariadb seed_mariadb.sql\n"
            "\n"
            "  # Current split-package:\n"
            "  python tools/generate_seed_sql.py privacyidea/models/ postgresql seed_pg.sql\n"
        ),
    )
    parser.add_argument(
        "models_path", type=Path,
        help="Path to models.py (single file) or models/ directory (package)",
    )
    parser.add_argument(
        "dialect", choices=["mariadb", "postgresql"],
        help="Target SQL dialect",
    )
    parser.add_argument(
        "output", nargs="?", type=Path, default=None,
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    if not args.models_path.exists():
        sys.exit(f"ERROR: path not found: {args.models_path}")

    is_dir = args.models_path.is_dir()
    print(
        f"Loading models from {'directory' if is_dir else 'file'}: {args.models_path}",
        file=sys.stderr,
    )

    if is_dir:
        module = _load_package_directory(args.models_path.resolve())
    else:
        module = _load_single_file(args.models_path)

    db = module.db
    metadata = db.metadata

    print(
        f"Found {len(metadata.tables)} tables: {sorted(metadata.tables)}",
        file=sys.stderr,
    )

    if args.dialect == "mariadb":
        sql = _render_mariadb(metadata)
    else:
        sql = _render_postgresql(metadata)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(sql, encoding="utf-8")
        print(f"Written to: {args.output}", file=sys.stderr)
    else:
        print(sql)


if __name__ == "__main__":
    main()

