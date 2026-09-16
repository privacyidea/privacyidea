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

The test is gated on a MySQL/MariaDB or PostgreSQL ``TEST_DATABASE_URL`` *and*
on the dump client for that engine being available, so it is skipped where
those are absent (plain local runs, SQLite).
"""
import os
import pathlib
import shutil
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, text

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
