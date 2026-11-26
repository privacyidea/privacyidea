# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Base fixtures of the new test suite: ``app``, ``app_context`` and ``clean_db``.

A test that needs the database requests ``clean_db``, directly or through another fixture. A test of pure logic
requests none of them and runs without an app.
"""
import atexit
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

# The database has to be chosen before privacyidea is imported: TestingConfig reads TEST_DATABASE_URL when its class
# is defined.
_worker = os.environ.get("PYTEST_XDIST_WORKER")
if not os.environ.get("TEST_DATABASE_URL"):
    # A fresh file per process, so no stale schema and no other process can get in the way
    _database_directory = tempfile.mkdtemp(prefix="pi-tests-new-")
    atexit.register(shutil.rmtree, _database_directory, ignore_errors=True)
    os.environ["TEST_DATABASE_URL"] = f"sqlite:///{Path(_database_directory) / 'test.sqlite'}"
elif _worker:
    # CI creates one database per xdist worker, named after the worker
    _url = os.environ["TEST_DATABASE_URL"]
    if _url.startswith("sqlite"):
        os.environ["TEST_DATABASE_URL"] = _url.replace(".sqlite", f"-{_worker}.sqlite")
    elif _url.startswith("oracle"):
        # On Oracle the schema is the user, so the user gets the suffix
        from sqlalchemy.engine.url import make_url
        _parsed = make_url(_url)
        os.environ["TEST_DATABASE_URL"] = _parsed.set(
            username=f"{_parsed.username}_{_worker}").render_as_string(hide_password=False)
    else:
        os.environ["TEST_DATABASE_URL"] = f"{_url}_{_worker}"

import pytest  # noqa: E402
from flask import Flask, g, request  # noqa: E402
from sqlalchemy import Sequence, event, text  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402

from privacyidea.api import healthcheck  # noqa: E402
from privacyidea.app import create_app  # noqa: E402
from privacyidea.lib import health  # noqa: E402
from privacyidea.lib.conditional_access.request_context import reset_ca_context  # noqa: E402
from privacyidea.lib.conditional_access.session import close_ca_session  # noqa: E402
from privacyidea.lib.lifecycle import call_finalizers  # noqa: E402
from privacyidea.lib.resolvers import LDAPIdResolver  # noqa: E402
from privacyidea.models import db, save_config_timestamp  # noqa: E402

TESTS_NEW = Path(__file__).resolve().parent
REPOSITORY = TESTS_NEW.parent
CONFIG_FILE = REPOSITORY / "tests" / "testdata" / "test_pi.cfg"
LOCAL_HOSTS = ["127.0.0.1", "::1", "localhost"]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    Network guard: a test in tests_new may only connect to this machine, unless it is marked ``integration``.

    The rules are pytest-socket markers, set here so they only apply to tests_new and not to the old tests.
    """
    for item in items:
        if TESTS_NEW not in Path(item.path).parents:
            continue
        if item.get_closest_marker("integration"):
            item.add_marker(pytest.mark.enable_socket)
        else:
            item.add_marker(pytest.mark.allow_hosts(LOCAL_HOSTS))


@event.listens_for(Engine, "connect")
def _read_committed_on_mysql(dbapi_connection, connection_record):
    """
    Use READ COMMITTED on MySQL and MariaDB.

    All requests of a test run share one connection pool. Under the default REPEATABLE READ, a pooled connection keeps
    the snapshot of its first read and misses rows committed later. In production every request has its own
    connection, so this only concerns the tests.
    """
    if "mysql" in (type(dbapi_connection).__module__ or "").lower():
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        finally:
            cursor.close()


def _start_request_with_empty_g() -> None:
    """
    Empty ``g`` before the first request of a request context, as every production request starts with an empty one.

    A test keeps one app context for all its requests, so without this a request would see what an earlier request
    of the same test left on ``g``.
    """
    if request.environ.get("privacyidea.tests.g_emptied"):
        return
    request.environ["privacyidea.tests.g_emptied"] = True
    for key in list(iter(g)):
        g.pop(key)


def _reset_global_state() -> None:
    """
    Empty the caches that production code keeps at module level. They outlive app contexts.

    - ``LDAPIdResolver.CACHE``: users found per resolver, keyed on the resolver configuration
    - ``health._CACHE``: results of the certificate and endpoint checks
    - ``healthcheck._resolver_probe_cache``: the last result of the resolver probe

    The app-local store (configuration, client write throttle, subscription user count) is emptied in ``app_context``.
    """
    LDAPIdResolver.CACHE.clear()
    with health._CACHE_LOCK:
        health._CACHE.clear()
    healthcheck._resolver_probe_cache["snapshot"] = None


def _declared_sequences() -> list[str]:
    """The names of the sequences behind the primary keys."""
    return sorted({column.default.name
                   for table in db.metadata.tables.values()
                   for column in table.columns
                   if isinstance(getattr(column, "default", None), Sequence)})


def _empty_all_tables() -> None:
    """
    Delete every row and restart the sequences, so each test starts with empty tables and ids from 1.

    The tables are emptied instead of rolled back: audit, authentication log, metrics and resolver cache write through
    their own connections, which a rollback of the test's transaction does not reach.
    """
    connection = db.session.connection()
    dialect = db.engine.dialect.name
    is_mysql = dialect in ("mysql", "mariadb")
    if is_mysql:
        # privacyIDEA has foreign key cycles that no order of deletes satisfies
        connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    try:
        if dialect == "postgresql":
            # TRUNCATE also gives back the physical row order a fresh table has
            tables = ", ".join(f'"{table.name}"' for table in db.metadata.sorted_tables)
            connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
        else:
            for table in reversed(db.metadata.sorted_tables):
                connection.execute(table.delete())
        if dialect != "sqlite":
            # SQLite has no sequences, an empty table starts at rowid 1 again by itself
            for sequence_name in _declared_sequences():
                connection.execute(text(f"ALTER SEQUENCE {sequence_name} RESTART"))
    finally:
        if is_mysql:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    db.session.commit()


@pytest.fixture(scope="session")
def app() -> Iterator[Flask]:
    """One app per process, with a freshly built schema. Building it costs more than any single test."""
    application = create_app("testing", CONFIG_FILE)
    # First in the list, so it runs before the handlers of the app put their values on g
    application.before_request_funcs.setdefault(None, []).insert(0, _start_request_with_empty_g)
    with application.app_context():
        db.drop_all()
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def app_context(app: Flask) -> Iterator[None]:
    """
    A fresh app context, and with it a fresh ``g``, for one test.

    The app-local store and the module-level caches survive app contexts, so they are emptied as well.
    """
    with app.app_context():
        app.config.get("_app_local_store", {}).clear()
        _reset_global_state()
        yield
        close_ca_session()
        reset_ca_context()
        db.session.rollback()
        db.session.remove()
        call_finalizers()


@pytest.fixture
def clean_db(app_context: None) -> None:
    """Empty tables, apart from the configuration timestamp every request reads."""
    _empty_all_tables()
    save_config_timestamp()
    db.session.commit()
