# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
End-to-end backup/restore round-trip against a live MySQL/MariaDB or PostgreSQL.

This drives the real ``pi-manage backup create`` / ``backup restore`` commands:
it seeds a sentinel row and a sequence, creates a backup, simulates a disaster
by dropping them, restores from the backup, and asserts they came back. It
guards the backup tooling against drift that unit tests cannot catch — e.g. the
mysqldump default-locking failure on a MariaDB Galera cluster (which needs a
real wsrep node to reproduce), a PostgreSQL dump that cannot be replayed into a
database that still holds the old schema, or a silently incomplete dump being
packaged and reported as success.

The same round trip also runs on a database of privacyIDEA itself, a release seed
upgraded to head, so that a change of the schema that a dump cannot restore fails
here. And a backup taken before an upgrade is restored into the upgraded database,
the way back after a failed upgrade, after which the upgrade has to run again.

The test is gated on a MySQL/MariaDB or PostgreSQL ``TEST_DATABASE_URL`` *and*
on the dump client for that engine being available, so it is skipped where
those are absent (plain local runs, SQLite).
"""
import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from flask import Flask
from sqlalchemy import Engine, create_engine, text

from tests.migration_test_utils import (RELEASE_HEADS, drop_all_tables, get_alembic_cfg,
                                        insert_minimal_row_into_every_table, load_seed, sequences_behind_their_table,
                                        sorted_rows, table_contents)

DB_URL = os.environ.get("TEST_DATABASE_URL", "")
# tests/cli/test_backup_roundtrip.py -> repo root
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# The command pi-manage shells out to per engine, which has to be installed for
# the round trip to run for real instead of self-skipping.
DUMP_CLIENTS = {"mysql": "mysqldump", "mariadb": "mysqldump", "postgresql": "pg_dump"}
DUMP_CLIENT = next((binary for prefix, binary in DUMP_CLIENTS.items()
                    if DB_URL.startswith(prefix)), None)

pytestmark = [
    pytest.mark.backup,
    pytest.mark.skipif(
        DUMP_CLIENT is None,
        reason="backup round-trip needs a MySQL/MariaDB or PostgreSQL TEST_DATABASE_URL",
    ),
    pytest.mark.skipif(
        DUMP_CLIENT is not None and shutil.which(DUMP_CLIENT) is None,
        reason=f"{DUMP_CLIENT} client binary not available",
    ),
]


def _run_pimanage(args, config_file):
    """Invoke the real pi-manage entrypoint as a subprocess."""
    env = {**os.environ, "PRIVACYIDEA_CONFIGFILE": str(config_file)}
    return subprocess.run(
        [sys.executable, "pi-manage", *args],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True,
    )


def _write_config(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """A minimal configuration pointing at the test database, as (config directory, pi.cfg)."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    enc_file = config_dir / "enckey"
    enc_file.write_bytes(b"x" * 96)
    pi_cfg = config_dir / "pi.cfg"
    pi_cfg.write_text(
        f"SQLALCHEMY_DATABASE_URI = {DB_URL!r}\n"
        f"PI_ENCFILE = {str(enc_file)!r}\n"
        "SECRET_KEY = 'roundtrip-secret'\n"
        "PI_PEPPER = 'roundtrip-pepper'\n"
    )
    return config_dir, pi_cfg


def _create_backup(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """Back the test database up with pi-manage, as (backup archive, pi.cfg)."""
    config_dir, pi_cfg = _write_config(tmp_path)
    backup_dir = tmp_path / "backup"
    result = _run_pimanage(["backup", "create", "-d", str(backup_dir), "-c", str(config_dir)], pi_cfg)
    assert result.returncode == 0, result.stdout + result.stderr
    archives = list(backup_dir.glob("*.tgz"))
    assert len(archives) == 1, f"expected exactly one backup archive, got {archives}"
    return archives[0], pi_cfg


def _restore_backup(archive: pathlib.Path, pi_cfg: pathlib.Path) -> None:
    result = _run_pimanage(["backup", "restore", "--keep-db-uri", str(archive)], pi_cfg)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def privacyidea_app() -> Iterator[Flask]:
    """An app context for the migrations, whose env.py reads the database of the current app."""
    from privacyidea.app import create_app
    from privacyidea.models import db

    app = create_app("testing", REPO_ROOT / "tests/testdata/test_pi.cfg", silent=True)
    with app.app_context():
        yield app
        db.session.remove()
        for engine in db.engines.values():
            engine.dispose()


def _contents(engine: Engine) -> dict[str, list[dict]]:
    return {table: sorted_rows(rows) for table, rows in table_contents(engine).items()}


def _stamps(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        return sorted(conn.execute(text("SELECT version_num FROM alembic_version")).scalars())


def _differing_tables(expected: dict[str, list[dict]], actual: dict[str, list[dict]]) -> list[str]:
    return sorted(table for table in expected if actual.get(table) != expected[table])


def test_backup_restore_roundtrip(tmp_path):
    engine = create_engine(DB_URL)
    # Real MySQL has no CREATE SEQUENCE at all, unlike MariaDB 10.3+ and
    # PostgreSQL -- so the sequence checks below only apply where the dialect
    # actually supports them. The table/row round trip still runs everywhere.
    with engine.connect() as conn:
        has_sequences = conn.dialect.supports_sequences
        postgresql = conn.dialect.name == "postgresql"

    if postgresql:
        create_sequence = "CREATE SEQUENCE backup_rt_seq START WITH 7"
        count_sequence = ("SELECT COUNT(*) FROM information_schema.sequences "
                          "WHERE sequence_name = 'backup_rt_seq'")
    else:
        # INCREMENT BY 0 is required to create a cached sequence on a Galera
        # cluster (and behaves like the default increment on a standalone
        # server), so the seed loads on both -- and the sequence is exactly what
        # made mysqldump's default LOCK TABLES fail on Galera.
        create_sequence = "CREATE SEQUENCE backup_rt_seq START WITH 7 INCREMENT BY 0"
        count_sequence = ("SELECT COUNT(*) FROM information_schema.tables "
                          "WHERE table_schema = DATABASE() AND table_type = 'SEQUENCE' "
                          "AND table_name = 'backup_rt_seq'")

    # 1. Seed a sentinel table plus, where the engine has them, a sequence.
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS backup_roundtrip"))
        if has_sequences:
            conn.execute(text("DROP SEQUENCE IF EXISTS backup_rt_seq"))
            conn.execute(text(create_sequence))
        conn.execute(text("CREATE TABLE backup_roundtrip (id INTEGER PRIMARY KEY, val VARCHAR(50))"))
        conn.execute(text("INSERT INTO backup_roundtrip (id, val) VALUES (1, 'sentinel')"))

    try:
        # 2. Minimal config pointing at the test database.
        config_dir, pi_cfg = _write_config(tmp_path)
        backup_dir = tmp_path / "backup"

        # 3. Create the backup via the real CLI command.
        result = _run_pimanage(
            ["backup", "create", "-d", str(backup_dir), "-c", str(config_dir)],
            pi_cfg)
        assert result.returncode == 0, result.stdout + result.stderr
        archives = list(backup_dir.glob("*.tgz"))
        assert len(archives) == 1, f"expected exactly one backup archive, got {archives}"

        # 4. Disaster: drop the seeded objects.
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE backup_roundtrip"))
            if has_sequences:
                conn.execute(text("DROP SEQUENCE backup_rt_seq"))

        # 5. Restore. --keep-db-uri keeps the (identical) live URI, which also
        #    avoids depending on the absolute paths baked into the archived pi.cfg.
        result = _run_pimanage(
            ["backup", "restore", "--keep-db-uri", str(archives[0])], pi_cfg)
        assert result.returncode == 0, result.stdout + result.stderr

        # 6. Verify the row and the sequence are back.
        with engine.connect() as conn:
            val = conn.execute(
                text("SELECT val FROM backup_roundtrip WHERE id = 1")).scalar()
            if has_sequences:
                seq_count = conn.execute(text(count_sequence)).scalar()
        assert val == "sentinel", f"sentinel row was not restored (got {val!r})"
        if has_sequences:
            assert seq_count == 1, "sequence backup_rt_seq was not restored"

        # 7. Restore a second time, now that the objects exist again. A dump
        #    that only applies to an empty database would fail here.
        result = _run_pimanage(
            ["backup", "restore", "--keep-db-uri", str(archives[0])], pi_cfg)
        assert result.returncode == 0, result.stdout + result.stderr
        with engine.connect() as conn:
            val = conn.execute(
                text("SELECT val FROM backup_roundtrip WHERE id = 1")).scalar()
        assert val == "sentinel", f"sentinel row was not restored (got {val!r})"
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS backup_roundtrip"))
            if has_sequences:
                conn.execute(text("DROP SEQUENCE IF EXISTS backup_rt_seq"))
        engine.dispose()


def test_backup_restore_of_a_privacyidea_database(tmp_path, privacyidea_app):
    """
    The round trip for a database of privacyIDEA: the seed of the newest release upgraded to head, with the tables of
    the models, their sequences, indexes and foreign keys. Dropping everything and restoring the backup brings back the
    contents of every table, the stamp and sequences that are ahead of their tables.
    """
    engine = create_engine(DB_URL)
    try:
        drop_all_tables(engine)
        load_seed(list(RELEASE_HEADS.values())[-1])
        command.upgrade(get_alembic_cfg(), "head")
        # pi-manage registers its node in the nodename table, so the backup holds the database after that
        archive, pi_cfg = _create_backup(tmp_path)
        contents = _contents(engine)
        stamps = _stamps(engine)

        drop_all_tables(engine)
        _restore_backup(archive, pi_cfg)

        assert _stamps(engine) == stamps
        restored_contents = _contents(engine)
        assert set(restored_contents) == set(contents)
        assert not _differing_tables(contents, restored_contents)
        assert not sequences_behind_their_table(engine)
    finally:
        drop_all_tables(engine)
        engine.dispose()


@pytest.mark.xfail(
    DB_URL.startswith("postgresql"), raises=AssertionError, strict=True,
    reason="On PostgreSQL the restore fails: the tables that 3.14.0 added keep foreign keys on realm, so the dump of "
           "3.13.4 cannot drop realm's primary key (pg_dump --clean), and psql rolls the whole restore back")
def test_restore_of_a_backup_from_before_an_upgrade(tmp_path, privacyidea_app):
    """
    The way back after an upgrade: a backup of a database of the oldest release, restored into that database after its
    upgrade to head, brings back the release's tables with their contents and its stamp. The tables that the upgrade
    added stay. The upgrade then runs again on that database, as after a failed upgrade.
    """
    engine = create_engine(DB_URL)
    try:
        drop_all_tables(engine)
        load_seed(list(RELEASE_HEADS.values())[0])
        archive, pi_cfg = _create_backup(tmp_path)
        contents_before = _contents(engine)
        stamps_before = _stamps(engine)
        command.upgrade(get_alembic_cfg(), "head")

        _restore_backup(archive, pi_cfg)

        assert _stamps(engine) == stamps_before
        assert not _differing_tables(contents_before, _contents(engine))

        command.upgrade(get_alembic_cfg(), "head")

        assert _stamps(engine) == [ScriptDirectory.from_config(get_alembic_cfg()).get_current_head()]
        assert not sequences_behind_their_table(engine)
        assert not insert_minimal_row_into_every_table()
    finally:
        drop_all_tables(engine)
        engine.dispose()
