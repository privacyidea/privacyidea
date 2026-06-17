# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
End-to-end backup/restore round-trip against a live MySQL/MariaDB.

This drives the real ``pi-manage backup create`` / ``backup restore`` commands:
it seeds a sentinel row and a (Galera-safe) sequence, creates a backup, simulates
a disaster by dropping them, restores from the backup, and asserts they came
back. It guards the backup tooling against drift that unit tests cannot catch —
e.g. the mysqldump default-locking failure on a MariaDB Galera cluster (which
needs a real wsrep node to reproduce), or a silently incomplete dump being
packaged and reported as success.

The test is gated on a MySQL/MariaDB ``TEST_DATABASE_URL`` *and* on the
``mysqldump`` client binary being available, so it is skipped where those are
absent (plain local runs, SQLite/PostgreSQL). PostgreSQL is intentionally not
covered yet — ``pi-manage backup`` has no ``pg_dump`` path.
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

pytestmark = [
    pytest.mark.backup,
    pytest.mark.skipif(
        not DB_URL.startswith(("mysql", "mariadb")),
        reason="backup round-trip needs a MySQL/MariaDB TEST_DATABASE_URL",
    ),
    pytest.mark.skipif(
        shutil.which("mysqldump") is None,
        reason="mysqldump client binary not available",
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

    # 1. Seed a sentinel table plus a sequence. INCREMENT BY 0 is required to
    #    create a cached sequence on a Galera cluster (and behaves like the
    #    default increment on a standalone server), so the seed loads on both —
    #    and the sequence is exactly what made mysqldump's default LOCK TABLES
    #    fail on Galera.
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS backup_roundtrip"))
        conn.execute(text("DROP SEQUENCE IF EXISTS backup_rt_seq"))
        conn.execute(text("CREATE SEQUENCE backup_rt_seq START WITH 7 INCREMENT BY 0"))
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
            seq_count = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'SEQUENCE' "
                "AND table_name = 'backup_rt_seq'")).scalar()
        assert val == "sentinel", f"sentinel row was not restored (got {val!r})"
        assert seq_count == 1, "sequence backup_rt_seq was not restored"
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS backup_roundtrip"))
            conn.execute(text("DROP SEQUENCE IF EXISTS backup_rt_seq"))
        engine.dispose()
