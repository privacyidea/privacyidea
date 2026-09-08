# (c) NetKnights GmbH 2024,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import contextlib
import datetime as dt
import json
import os
import pathlib
import tempfile
import tarfile
from collections.abc import Callable
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.cli.pimanage import cli as pi_manage
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.engine import ConditionalAccessAction, ConditionalAccessTarget
from privacyidea.lib.conditional_access.policy import create_conditional_access_policy
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.resolver import (save_resolver, delete_resolver,
                                      get_resolver_list)
from privacyidea.models import db, Challenge, AuthenticationLog, ConditionalAccessOutcome
from privacyidea.models.conditional_access_policy import (BlockList, ConditionalAccessPolicy,
                                                          ConditionalAccessPolicyStage, UserLockState)
from privacyidea.models.utils import utc_now
from .base import CliTestCase
from ..base import PWFILE


class PIManageAdminTestCase(CliTestCase):
    # TODO: test admin create/delete/change/list with a given test config
    def test_01_pimanage_admin_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["admin"])
        self.assertIn("Register a new administrator in the database.",
                      result.output, result)
        self.assertIn("Change the email address or the password of an",
                      result.output, result)
        self.assertIn("Delete an existing administrator.",
                      result.output, result)
        self.assertIn("List all administrators.",
                      result.output, result)


class PIManageAuditTestCase(CliTestCase):
    # TODO: test audit rotate/dump with a given test config
    def test_01_pimanage_audit_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["audit"])
        self.assertIn("Dump the audit log in csv format.", result.output, result)
        self.assertIn("Clean the SQL audit log.", result.output, result)


class PIManageBackupTestCase(CliTestCase):
    def test_01_pimanage_backup_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["backup", "create", "-h"])
        self.assertIn("-d, --directory DIRECTORY", result.output, result)
        self.assertIn("-c, --config_dir DIRECTORY", result.output, result)
        self.assertIn("-r, --radius_dir DIRECTORY", result.output, result)
        self.assertIn("-e, --enckey", result.output, result)
        result = runner.invoke(pi_manage, ["backup", "restore", "-h"])
        self.assertIn("Usage: cli backup restore [OPTIONS] BACKUP_FILE",
                      result.output, result)
        self.assertIn("--keep-db-uri", result.output, result)

    @staticmethod
    def _make_fake_tarfile(live_pi_cfg: pathlib.Path, backup_uri: str, include_cfg: bool = True,
                           include_sql: bool = True, include_enckey: bool = False,
                           dump_suffix: str = ".sqlite") -> Callable:
        """
        Return a context manager that replaces ``tarfile.open`` with a fake
        that simulates:

        1. Iterating members – yields fake members whose ``name`` attributes
           match the relative paths inside the archive. Which members appear
           is controlled by ``include_cfg`` / ``include_sql`` /
           ``include_enckey`` so tests can exercise the missing-file branches.

        2. ``extractall`` – writes the backup content (``backup_uri``) into
           ``live_pi_cfg`` and creates a placeholder SQL file, mimicking a
           real extraction.

        The ``backup_restore`` command opens the archive twice (once to list,
        once to extract), so the fake supports both uses.

        ``dump_suffix`` selects the database engine the archive claims to come
        from, which has to match the engine of ``backup_uri``: ".sqlite" for
        SQLite, ".sql" for MySQL/MariaDB, ".pgsql" for PostgreSQL.
        """
        import unittest.mock as mock

        sql_file_path = live_pi_cfg.parent / f"dbdump-20240101-1200{dump_suffix}"
        cfg_rel = str(live_pi_cfg).lstrip("/")
        sql_rel = str(sql_file_path).lstrip("/")
        enckey_rel = str(live_pi_cfg.parent / "enckey").lstrip("/")

        def make_member(name):
            m = mock.MagicMock()
            m.name = name
            return m

        members = []
        if include_cfg:
            members.append(make_member(cfg_rel))
        if include_sql:
            members.append(make_member(sql_rel))
        if include_enckey:
            members.append(make_member(enckey_rel))

        @contextlib.contextmanager
        def fake_tarfile_open(*args, **kwargs):
            tf = mock.MagicMock()
            # Fresh iterator each open() so the listing pass and the
            # extraction pass both see the same members.
            tf.__iter__.return_value = iter(list(members))

            def fake_extractall(path="/", **kw):
                live_pi_cfg.write_text(
                    f'SQLALCHEMY_DATABASE_URI = {repr(backup_uri)}\n'
                    'SECRET_KEY = "secret"\n'
                )
                sql_file_path.write_text("-- sql dump placeholder\n")

            tf.extractall = fake_extractall
            yield tf

        return fake_tarfile_open

    def _run_restore_with_mocks(self, live_pi_cfg, backup_uri, live_uri):
        """
        Invoke ``backup restore --keep-db-uri fake.tgz`` with all external
        calls mocked so the test is fully self-contained:

        - ``tarfile.open`` is replaced by :meth:`_make_fake_tarfile` which
          fakes archive listing (iteration) and extraction.
        - ``shutil.copyfile`` is patched out because for SQLite URIs the
          restore command would try to copy the dump to the database path
          which does not exist in the test environment.
        - ``os.unlink`` is patched out for the same reason.

        Before invoking the command, ``live_pi_cfg`` is written with
        ``live_uri`` so that ``--keep-db-uri`` has an existing config to read.
        After extraction the fake tar overwrites it with ``backup_uri``;
        the command should then patch it back to ``live_uri``.
        """
        import unittest.mock as mock

        # Pre-populate the live config that --keep-db-uri will read BEFORE
        # extraction.  The fake tar extraction will overwrite this with
        # backup_uri; the command must then restore it to live_uri.
        live_pi_cfg.write_text(
            f'SQLALCHEMY_DATABASE_URI = {repr(live_uri)}\n'
            'SECRET_KEY = "secret"\n'
        )

        runner = self.app.test_cli_runner()
        with mock.patch("privacyidea.cli.pimanage.backup.tarfile.open",
                        side_effect=self._make_fake_tarfile(live_pi_cfg, backup_uri)):
            with mock.patch("privacyidea.cli.pimanage.backup.shutil.copyfile"):
                with mock.patch("privacyidea.cli.pimanage.backup.os.unlink"):
                    return runner.invoke(
                        pi_manage,
                        ["backup", "restore", "--keep-db-uri", "fake.tgz"],
                    )

    def test_02_keep_db_uri_replaces_backup_uri_in_config(self):
        """
        Core --keep-db-uri behaviour: after a restore the pi.cfg on disk must
        contain the *live* URI (the one that was there before the restore), not
        the URI that was stored inside the backup archive.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            live_pi_cfg = tmp / "pi.cfg"

            live_uri = "sqlite:////live/data.sqlite"
            backup_uri = "sqlite:////backup/data.sqlite"

            result = self._run_restore_with_mocks(live_pi_cfg, backup_uri, live_uri)

            # Assert the command completed successfully before checking file contents.
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIsNone(result.exception, result.exception)

            final_text = live_pi_cfg.read_text()
            # The live URI must survive the restore.
            self.assertIn(repr(live_uri), final_text, final_text)
            # The backup URI must have been replaced.
            self.assertNotIn(repr(backup_uri), final_text, final_text)
            # The operator must be told which source was used.
            self.assertIn("using database URI from live config", result.output, result.output)
            # No enckey member in the fake archive -> the operator must be warned
            # so they don't silently end up with a backup missing the encryption key.
            self.assertIn("NO FILE 'enckey' CONTAINED", result.output, result.output)

    def test_03_keep_db_uri_live_config_unreadable_falls_back_to_backup(self):
        """
        When --keep-db-uri is given but the live pi.cfg cannot be parsed
        (e.g. it is syntactically broken), the restore must:

        - emit a warning so the operator knows why the flag was ignored, and
        - complete successfully using the URI from the backup archive.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            live_pi_cfg = tmp / "pi.cfg"
            backup_uri = "sqlite:////backup/data.sqlite"

            # Write a syntactically invalid Python file so Flask's from_pyfile
            # raises a SyntaxError, triggering the fallback path.
            live_pi_cfg.write_text("this is not valid python !!!\n")

            runner = self.app.test_cli_runner()
            with mock.patch("privacyidea.cli.pimanage.backup.tarfile.open",
                            side_effect=self._make_fake_tarfile(live_pi_cfg, backup_uri)):
                with mock.patch("privacyidea.cli.pimanage.backup.shutil.copyfile"):
                    with mock.patch("privacyidea.cli.pimanage.backup.os.unlink"):
                        result = runner.invoke(
                            pi_manage,
                            ["backup", "restore", "--keep-db-uri", "fake.tgz"],
                        )

            # Assert the command completed successfully.
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIsNone(result.exception, result.exception)

            # A warning about the read failure must appear in the output.
            self.assertIn("could not read live config", result.output, result.output)
            # The operator must also be told the backup URI is being used.
            self.assertIn("Using database URI from backup", result.output, result.output)

    def test_04_missing_config_file_exits(self):
        """
        If the archive does not contain a pi.cfg, the restore must abort with
        exit code 2 and a clear error message – it must NOT fall through to
        the extraction step.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            live_pi_cfg = tmp / "pi.cfg"

            fake = self._make_fake_tarfile(
                live_pi_cfg, "sqlite:////backup/data.sqlite",
                include_cfg=False, include_sql=True,
            )
            runner = self.app.test_cli_runner()
            with mock.patch("privacyidea.cli.pimanage.backup.tarfile.open",
                            side_effect=fake):
                result = runner.invoke(pi_manage,
                                       ["backup", "restore", "fake.tgz"])

            self.assertEqual(result.exit_code, 2, result.output)
            self.assertIn("Missing config file pi.cfg", result.output, result.output)
            # The fake's extractall would have created the SQL file; ensure we
            # bailed out before extraction.
            self.assertFalse((tmp / "dbdump-20240101-1200.sqlite").exists())

    def test_05_missing_sql_file_exits(self):
        """
        If the archive contains pi.cfg but no SQL dump, the restore must abort
        with exit code 2.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            live_pi_cfg = tmp / "pi.cfg"

            fake = self._make_fake_tarfile(
                live_pi_cfg, "sqlite:////backup/data.sqlite",
                include_cfg=True, include_sql=False,
            )
            runner = self.app.test_cli_runner()
            with mock.patch("privacyidea.cli.pimanage.backup.tarfile.open",
                            side_effect=fake):
                result = runner.invoke(pi_manage,
                                       ["backup", "restore", "fake.tgz"])

            self.assertEqual(result.exit_code, 2, result.output)
            self.assertIn("Missing database dump", result.output, result.output)
            self.assertFalse((tmp / "dbdump-20240101-1200.sqlite").exists())

    def test_06_unreadable_archive_exits(self):
        """
        If ``tarfile.open`` fails (corrupt archive, missing file, ...) the
        restore must abort with exit code 2 and surface the underlying error.
        """
        import tarfile as _tarfile
        import unittest.mock as mock

        runner = self.app.test_cli_runner()
        with mock.patch("privacyidea.cli.pimanage.backup.tarfile.open",
                        side_effect=_tarfile.ReadError("not a gzip file")):
            result = runner.invoke(pi_manage,
                                   ["backup", "restore", "fake.tgz"])

        self.assertEqual(result.exit_code, 2, result.output)
        self.assertIn("Unable to open backup file", result.output, result.output)
        self.assertIn("not a gzip file", result.output, result.output)

    def test_07_write_mysql_defaults_handles_missing_password(self):
        """
        A SQLALCHEMY_DATABASE_URI without a password yields
        url.password is None. _write_mysql_defaults must still produce a
        valid mysql defaults file (Python 3.12+ ConfigParser requires string
        values).
        """
        import configparser
        from sqlalchemy.engine.url import make_url
        from privacyidea.cli.pimanage.backup import _write_mysql_defaults

        with tempfile.TemporaryDirectory() as tmp_dir:
            defaults_file = pathlib.Path(tmp_dir) / "mysql.cnf"
            # URI without password — url.password is None
            url = make_url("mysql+pymysql://privacyidea@127.0.0.1/privacyidea_test")
            self.assertIsNone(url.password)

            _write_mysql_defaults(defaults_file, url)

            cp = configparser.ConfigParser(interpolation=None)
            cp.read(defaults_file)
            self.assertEqual('"privacyidea"', cp["client"]["user"])
            self.assertEqual('""', cp["client"]["password"])

        # A percent-encoded password reaches the client decoded, and the '%' it
        # decodes to must be written verbatim — the default ConfigParser
        # BasicInterpolation would otherwise reject it.
        with tempfile.TemporaryDirectory() as tmp_dir:
            defaults_file = pathlib.Path(tmp_dir) / "mysql.cnf"
            url = make_url("mysql+pymysql://privacyidea:ab%25cd@127.0.0.1/privacyidea_test")
            self.assertEqual("ab%cd", url.password)

            _write_mysql_defaults(defaults_file, url)

            cp = configparser.ConfigParser(interpolation=None)
            cp.read(defaults_file)
            self.assertEqual('"ab%cd"', cp["client"]["password"])

    def test_07a_mysql_defaults_quotes_values_for_the_option_file_parser(self):
        """
        Values in a MySQL option file are quoted, their backslashes doubled and
        their double quotes escaped: an unquoted value ends at a '#', which
        would truncate the password, the option file parser expands backslash
        escapes inside the value, and an unescaped '"' ends the quoted part, so
        that a '#' behind it starts a comment again.
        """
        import configparser
        from sqlalchemy.engine.url import make_url
        from privacyidea.cli.pimanage.backup import _write_mysql_defaults

        for encoded, quoted in [("ab%23cd", '"ab#cd"'),
                                ("ab%5Ccd", '"ab\\\\cd"'),
                                ("ab%22cd", '"ab\\"cd"'),
                                ("ab%22%23cd", '"ab\\"#cd"'),
                                ("ab cd", '"ab cd"')]:
            with tempfile.TemporaryDirectory() as tmp_dir:
                defaults_file = pathlib.Path(tmp_dir) / "mysql.cnf"
                url = make_url(f"mysql+pymysql://privacyidea:{encoded}@127.0.0.1/privacyidea_test")

                _write_mysql_defaults(defaults_file, url)

                cp = configparser.ConfigParser(interpolation=None)
                cp.read(defaults_file)
                self.assertEqual(quoted, cp["client"]["password"], encoded)

    def test_08_backup_create_aborts_on_dump_failure(self):
        """
        A failed mysqldump must NOT be packaged as a successful backup. The
        command must exit non-zero and write no backup file. This guards against
        the silent-failure mode where a non-zero mysqldump exit (e.g. a MariaDB
        Galera cluster rejecting LOCK TABLE on sequences) was ignored and a
        partial/empty dump got tar'd up and reported as "Backup written".
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            backup_dir = tmp / "backup"
            config_dir = tmp / "config"
            config_dir.mkdir()
            enc_file = tmp / "enckey"
            enc_file.write_bytes(b"x" * 96)

            def failing_run(cmd, **kwargs):
                # Simulate mysqldump writing a partial dump and then exiting
                # non-zero, so the cleanup that removes the partial file runs.
                if "-r" in cmd:
                    pathlib.Path(cmd[cmd.index("-r") + 1]).write_text("-- partial\n")
                result = mock.MagicMock()
                result.returncode = 1
                return result

            runner = self.app.test_cli_runner()
            with mock.patch.dict(self.app.config, {
                "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://u:p@localhost/pi_test",
                "PI_ENCFILE": str(enc_file)}):
                with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run",
                                side_effect=failing_run):
                    result = runner.invoke(pi_manage, [
                        "backup", "create",
                        "-d", str(backup_dir),
                        "-c", str(config_dir)])

            self.assertNotEqual(result.exit_code, 0, result.output)
            self.assertIn("Database dump failed", result.output, result.output)
            written = list(backup_dir.glob("*.tgz")) if backup_dir.exists() else []
            self.assertEqual(written, [],
                             f"a backup file was written despite the dump failing: {written}")
            # The partial dump must be cleaned up, not left behind.
            leftover = list(backup_dir.glob("*.sql")) if backup_dir.exists() else []
            self.assertEqual(leftover, [],
                             f"a partial dump file was left behind: {leftover}")

    def test_09_backup_restore_aborts_on_mysql_failure(self):
        """
        A failed `mysql` restore must exit non-zero and keep the extracted dump
        file for inspection/retry instead of deleting it and reporting success.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            live_pi_cfg = tmp / "pi.cfg"
            backup_uri = "mysql+pymysql://u:p@localhost/pi_test"
            # The fake tar extraction (re)creates this dump alongside pi.cfg.
            sqlfile = tmp / "dbdump-20240101-1200.sql"

            def failing_mysql(cmd, **kwargs):
                # The only subprocess in the mysql restore path is `mysql`; make
                # it fail so the abort-and-keep-dump branch runs.
                result = mock.MagicMock()
                result.returncode = 1
                return result

            runner = self.app.test_cli_runner()
            with mock.patch("privacyidea.cli.pimanage.backup.tarfile.open",
                            side_effect=self._make_fake_tarfile(live_pi_cfg, backup_uri,
                                                                dump_suffix=".sql")):
                with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run",
                                side_effect=failing_mysql):
                    result = runner.invoke(pi_manage, [
                        "backup", "restore", "ignored.tgz"])

            self.assertNotEqual(result.exit_code, 0, result.output)
            self.assertIn("Database restore failed", result.output, result.output)
            # The dump must be kept for inspection, not unlinked.
            self.assertTrue(sqlfile.exists(),
                            "dump file was deleted despite the restore failing")

    def test_10_backend_family_covers_all_drivers_of_an_engine(self):
        """
        The engine is derived from the SQLAlchemy backend name, so every driver
        of a supported engine maps to the same backup implementation, and an
        engine without backup support is rejected with a readable message.
        """
        from privacyidea.cli.pimanage.backup import (MYSQL, POSTGRESQL, SQLITE, _backend_family,
                                                     _database_url)

        for uri, expected in [
                ("sqlite:////var/lib/privacyidea/data.sqlite", SQLITE),
                ("mysql+pymysql://u:p@127.0.0.1/pi", MYSQL),
                ("mysql+mysqldb://u:p@127.0.0.1/pi", MYSQL),
                ("mariadb+pymysql://u:p@127.0.0.1/pi", MYSQL),
                ("postgresql://u:p@127.0.0.1/pi", POSTGRESQL),
                ("postgresql+psycopg2://u:p@127.0.0.1/pi", POSTGRESQL),
                ("postgresql+psycopg://u:p@127.0.0.1/pi", POSTGRESQL)]:
            self.assertEqual(expected, _backend_family(_database_url(uri)), uri)

        with self.assertRaises(SystemExit) as cm:
            _backend_family(_database_url("oracle+oracledb://u:p@127.0.0.1/pi"))
        self.assertEqual(2, cm.exception.code)

    def test_11_database_url_rejects_unusable_uris(self):
        """
        A missing, unparsable or database-less URI aborts with exit code 2
        instead of running a client command against nothing, and the password is
        not echoed while doing so.
        """
        from privacyidea.cli.pimanage.backup import _database_url

        for uri in [None, "", "://nonsense", "mysql+pymysql://u:secret@127.0.0.1/"]:
            with self.assertRaises(SystemExit) as cm:
                _database_url(uri)
            self.assertEqual(2, cm.exception.code, uri)

    def test_12_postgresql_dump_and_restore_command(self):
        """
        The PostgreSQL dump is taken with pg_dump and replayed with psql. The
        dump has to be replayable into a database that still holds the old
        schema (--clean --if-exists) and by a role that owns neither the schema
        nor its objects (--no-owner, --no-privileges, --no-comments), the
        restore has to be all-or-nothing (--single-transaction with
        ON_ERROR_STOP), and neither command may wait for a password prompt
        (--no-password). The password is passed in the environment, never on the
        command line.
        """
        import unittest.mock as mock
        from privacyidea.cli.pimanage.backup import (_dump_postgresql, _restore_postgresql,
                                                     _database_url)

        url = _database_url("postgresql+psycopg2://pi:se%40cret@db.example.net:5433/pi_test?sslmode=require")

        with tempfile.TemporaryDirectory() as tmp_dir:
            sqlfile = pathlib.Path(tmp_dir) / "dbdump-20240101-1200.pgsql"
            sqlfile.write_text("-- dump\n")
            calls = []

            def record(cmd: list[str], **kwargs: Any) -> mock.MagicMock:
                calls.append((cmd, kwargs))
                result = mock.MagicMock()
                result.returncode = 0
                return result

            with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run", side_effect=record):
                _dump_postgresql(url, sqlfile)
                _restore_postgresql(url, sqlfile)

        dump_cmd, dump_kwargs = calls[0]
        restore_cmd, restore_kwargs = calls[1]

        self.assertEqual("pg_dump", dump_cmd[0])
        for option in ["--clean", "--if-exists", "--no-owner", "--no-privileges", "--no-comments",
                       "--no-password"]:
            self.assertIn(option, dump_cmd)
        self.assertEqual("pi_test", dump_cmd[dump_cmd.index("--dbname") + 1])
        self.assertEqual("db.example.net", dump_cmd[dump_cmd.index("--host") + 1])
        self.assertEqual("5433", dump_cmd[dump_cmd.index("--port") + 1])
        self.assertEqual("pi", dump_cmd[dump_cmd.index("--username") + 1])

        self.assertEqual("psql", restore_cmd[0])
        self.assertIn("--single-transaction", restore_cmd)
        self.assertIn("--no-psqlrc", restore_cmd)
        self.assertEqual("ON_ERROR_STOP=on", restore_cmd[restore_cmd.index("--set") + 1])
        self.assertIn("--no-password", restore_cmd)

        for cmd, kwargs in (calls[0], calls[1]):
            # The decoded password goes into the environment, so it shows up
            # neither in the process list nor in a file inside the backup.
            self.assertEqual("se@cret", kwargs["env"]["PGPASSWORD"])
            self.assertEqual("require", kwargs["env"]["PGSSLMODE"])
            self.assertNotIn("se@cret", " ".join(cmd))

        # A successful restore consumes the extracted dump.
        self.assertFalse(sqlfile.exists())

    def test_13_postgresql_connection_args_follow_the_driver(self):
        """
        The client is pointed at the database the driver of privacyIDEA would
        connect to: a URI without host and port connects over the local socket,
        so neither option may be passed; a host in the query part replaces the
        host of the URI; and a host given more than once - the failover syntax
        of SQLAlchemy - reaches the client as the multi-host list of libpq,
        instead of only its last entry. Connection parameters that cannot be
        applied are reported instead of being dropped silently.
        """
        from privacyidea.cli.pimanage.backup import (_database_url, _postgresql_connection_args,
                                                     _postgresql_driver_parameters, _postgresql_env)

        def args_and_env(uri: str) -> tuple[list[str], dict[str, str]]:
            parameters = _postgresql_driver_parameters(_database_url(uri))
            return _postgresql_connection_args(parameters), _postgresql_env(parameters)

        args, env = args_and_env("postgresql:///pi_test?keepalives=1")
        self.assertNotIn("--host", args)
        self.assertNotIn("--port", args)
        self.assertNotIn("--username", args)
        self.assertNotIn("PGPASSWORD", env)

        # A socket directory given in the query is where privacyIDEA connects.
        args, _ = args_and_env("postgresql:///pi_test?host=/var/run/postgresql")
        self.assertEqual("/var/run/postgresql", args[args.index("--host") + 1])

        # ... and it replaces the host of the URI, rather than being ignored.
        args, _ = args_and_env("postgresql://pi@dbhost:5432/pi_test?host=/var/run/postgresql")
        self.assertEqual("/var/run/postgresql", args[args.index("--host") + 1])
        self.assertNotIn("dbhost", args)

        # A repeated host is a list of servers to try, not a single host.
        args, _ = args_and_env("postgresql://pi@/pi_test?host=h1:5432&host=h2:5433")
        self.assertEqual("h1,h2", args[args.index("--host") + 1])
        self.assertEqual("5432,5433", args[args.index("--port") + 1])

    def test_14_postgresql_dump_failure_keeps_no_partial_dump(self):
        """
        A failed pg_dump must not be packaged as a successful backup: the
        command exits non-zero, no archive is written and the partial dump is
        removed.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            backup_dir = tmp / "backup"
            config_dir = tmp / "config"
            config_dir.mkdir()
            enc_file = tmp / "enckey"
            enc_file.write_bytes(b"x" * 96)

            def failing_run(cmd: list[str], **kwargs: Any) -> mock.MagicMock:
                # pg_dump writes a partial dump and then exits non-zero, so the
                # cleanup that removes the partial file runs.
                pathlib.Path(cmd[cmd.index("--file") + 1]).write_text("-- partial\n")
                result = mock.MagicMock()
                result.returncode = 1
                return result

            runner = self.app.test_cli_runner()
            with mock.patch.dict(self.app.config, {
                    "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg2://u:p@localhost/pi_test",
                    "PI_ENCFILE": str(enc_file)}):
                with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run",
                                side_effect=failing_run):
                    result = runner.invoke(pi_manage, [
                        "backup", "create",
                        "-d", str(backup_dir),
                        "-c", str(config_dir)])

            self.assertNotEqual(result.exit_code, 0, result.output)
            self.assertIn("Database dump failed", result.output, result.output)
            written = list(backup_dir.glob("*.tgz")) if backup_dir.exists() else []
            self.assertEqual([], written,
                             f"a backup file was written despite the dump failing: {written}")
            leftover = list(backup_dir.glob("*.pgsql")) if backup_dir.exists() else []
            self.assertEqual([], leftover,
                             f"a partial dump file was left behind: {leftover}")

    def test_15_missing_client_command_names_the_package(self):
        """
        On an installation without the database client package, the command
        names the missing binary and the package to install instead of failing
        with a traceback.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            config_dir = tmp / "config"
            config_dir.mkdir()
            enc_file = tmp / "enckey"
            enc_file.write_bytes(b"x" * 96)

            runner = self.app.test_cli_runner()
            with mock.patch.dict(self.app.config, {
                    "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg2://u:p@localhost/pi_test",
                    "PI_ENCFILE": str(enc_file)}):
                with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run",
                                side_effect=FileNotFoundError("pg_dump")):
                    result = runner.invoke(pi_manage, [
                        "backup", "create",
                        "-d", str(tmp / "backup"),
                        "-c", str(config_dir)])

            self.assertEqual(2, result.exit_code, result.output)
            self.assertIn("Could not find the 'pg_dump' command", result.output, result.output)
            self.assertIn("postgresql-client", result.output, result.output)

    def test_16_restore_refuses_a_dump_from_another_engine(self):
        """
        A dump can only be replayed by the engine that wrote it. Restoring a
        MySQL dump onto a PostgreSQL URI has to abort before any client command
        runs, so the target database is left untouched.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            live_pi_cfg = tmp / "pi.cfg"
            backup_uri = "postgresql+psycopg2://u:p@localhost/pi_test"

            runner = self.app.test_cli_runner()
            with mock.patch("privacyidea.cli.pimanage.backup.tarfile.open",
                            side_effect=self._make_fake_tarfile(live_pi_cfg, backup_uri,
                                                                dump_suffix=".sql")):
                with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run") as run_mock:
                    result = runner.invoke(pi_manage, ["backup", "restore", "ignored.tgz"])

            self.assertEqual(2, result.exit_code, result.output)
            self.assertIn("MySQL/MariaDB dump", result.output, result.output)
            self.assertIn("PostgreSQL", result.output, result.output)
            run_mock.assert_not_called()

    def test_16a_mysql_defaults_file_stays_out_of_the_config_directory(self):
        """
        The option file holding the database password is written to a temporary
        directory, not to the configuration directory: the latter is packed into
        the archive, and a file left there would keep the password on disk after
        the command has ended.
        """
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            backup_dir = tmp / "backup"
            config_dir = tmp / "config"
            config_dir.mkdir()
            enc_file = tmp / "enckey"
            enc_file.write_bytes(b"x" * 96)
            defaults_files = []

            def record(cmd: list[str], **kwargs: Any) -> mock.MagicMock:
                defaults_file = [a for a in cmd if a.startswith("--defaults-file=")][0]
                path = pathlib.Path(defaults_file.split("=", 1)[1])
                defaults_files.append(path)
                # The file has to exist while the client runs, and hold the password.
                self.assertIn("s3cret", path.read_text())
                pathlib.Path(cmd[cmd.index("-r") + 1]).write_text("-- dump\n")
                result = mock.MagicMock()
                result.returncode = 0
                return result

            runner = self.app.test_cli_runner()
            with mock.patch.dict(self.app.config, {
                    "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://u:s3cret@localhost/pi_test",
                    "PI_ENCFILE": str(enc_file)}):
                with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run",
                                side_effect=record):
                    result = runner.invoke(pi_manage, [
                        "backup", "create",
                        "-d", str(backup_dir),
                        "-c", str(config_dir)])

            self.assertEqual(0, result.exit_code, result.output)
            # Neither in the configuration directory nor in the archive ...
            self.assertFalse((config_dir / "mysql.cnf").exists())
            archive = list(backup_dir.glob("*.tgz"))[0]
            with tarfile.open(archive, "r:gz") as tf:
                self.assertEqual([], [m.name for m in tf if m.name.endswith("mysql.cnf")])
            # ... and gone from the temporary directory once the command is done.
            self.assertFalse(defaults_files[0].exists())

    def test_17_mysql_restore_streams_the_dump_without_decoding(self):
        """
        The dump is handed to the mysql client as an open binary file. It
        therefore reaches the client byte for byte, whatever encoding it was
        written in, and its size is bounded by the disk rather than by the
        memory of the restoring process.
        """
        import unittest.mock as mock
        from privacyidea.cli.pimanage.backup import _database_url, _restore_mysql

        # Latin-1 encoded content, which cannot be decoded as UTF-8.
        dump_bytes = "INSERT INTO t VALUES ('Müller');\n".encode("latin1")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            sqlfile = tmp / "dbdump-20240101-1200.sql"
            sqlfile.write_bytes(dump_bytes)
            seen = {}

            def record(cmd: list[str], **kwargs: Any) -> mock.MagicMock:
                seen["stdin"] = kwargs["stdin"].read()
                result = mock.MagicMock()
                result.returncode = 0
                return result

            with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run", side_effect=record):
                _restore_mysql(_database_url("mysql+pymysql://u:p@localhost/pi_test"), sqlfile)

            self.assertEqual(dump_bytes, seen["stdin"])
            # A successful restore consumes the extracted dump.
            self.assertFalse(sqlfile.exists())


class PIManageRealmTestCase(CliTestCase):
    def test_01_pimanage_realm_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "realm", "-h"])
        self.assertIn("clear_default", result.output, result)

    def test_02_pimanage_realm_crud(self):
        save_resolver({"resolver": "resolver1",
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        runner = self.app.test_cli_runner()
        # create a realm with an existing resolver
        result = runner.invoke(pi_manage, ["config", "realm", "create", "realm1", "resolver1"])
        self.assertIn("Successfully created realm 'realm1' with resolver: ['resolver1'].",
                      result.output, result)
        # create a realm with an existing and non-existing resolver
        result = runner.invoke(pi_manage, ["config", "realm", "create", "realm2", "resolver1", "reso2"])
        self.assertIn("Realm 'realm2' created. Following resolvers could not be "
                      "assigned: ['reso2']", result.output, result)
        result = runner.invoke(pi_manage, ["config", "realm", "list"])
        self.assertIn("realm1", result.output)
        self.assertIn("resolver1", result.output)
        self.assertIn("realm2", result.output)
        result = runner.invoke(pi_manage, ["config", "realm", "delete", "realm1"])
        self.assertIn("Realm 'realm1' successfully deleted.", result.output, result)
        result = runner.invoke(pi_manage, ["config", "realm", "delete", "realm2"])
        self.assertIn("Realm 'realm2' successfully deleted.", result.output, result)
        delete_resolver("resolver1")

    def test_03_pimanage_realm_delete_custom_attributes(self):
        from privacyidea.lib.user import User
        from privacyidea.models import CustomUserAttribute
        save_resolver({"resolver": "resolver1",
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        runner = self.app.test_cli_runner()
        runner.invoke(pi_manage, ["config", "realm", "create", "realm1", "resolver1"])
        User("cornelius", "realm1").set_attribute("department", "sales")

        # Declining the confirmation leaves the realm in place.
        result = runner.invoke(pi_manage, ["config", "realm", "delete", "realm1"], input="n\n")
        self.assertIn("custom user attributes", result.output, result.output)
        self.assertIn("department", result.output, result.output)
        self.assertEqual(1, CustomUserAttribute.query.filter_by(Key="department").count())

        # The flag deletes the realm and its custom attributes together.
        result = runner.invoke(pi_manage,
                               ["config", "realm", "delete", "realm1", "--delete-custom-attributes"])
        self.assertIn("Realm 'realm1' successfully deleted.", result.output, result.output)
        self.assertEqual(0, CustomUserAttribute.query.filter_by(Key="department").count())
        delete_resolver("resolver1")


class PIManageBaseTestCase(CliTestCase):
    def test_01_pimanage_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["-h"])
        self.assertIn("Management script for the privacyIDEA application.", result.output, result)
        self.assertIn("Check out our docs at https://privacyidea.readthedocs.io/ for more details",
                      result.output, result)
        self.assertIn("config", result.output, result)
        self.assertIn("backup", result.output, result)
        self.assertIn("audit", result.output, result)
        self.assertIn("admin", result.output, result)
        self.assertIn("api", result.output, result)
        self.assertIn("db", result.output, result)
        self.assertIn("setup", result.output, result)
        self.assertNotIn("rotate_audit", result.output, result)
        self.assertNotIn("createdb", result.output, result)
        self.assertNotIn("create_tables", result.output, result)
        self.assertNotIn("dropdb", result.output, result)
        self.assertNotIn("drop_tables", result.output, result)
        self.assertNotIn("realm", result.output, result)
        self.assertNotIn("resolver", result.output, result)


class PIManageConfigTestCase(CliTestCase):
    def test_01_pimanage_config_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "-h"])
        self.assertIn("Manage the privacyIDEA server configuration", result.output, result)
        self.assertIn("ca", result.output, result)
        self.assertIn("realm", result.output, result)
        self.assertIn("resolver", result.output, result)
        self.assertIn("event", result.output, result)
        self.assertIn("policy", result.output, result)
        self.assertIn("authcache", result.output, result)
        self.assertIn("hsm", result.output, result)
        self.assertIn("challenge", result.output, result)
        self.assertIn("export", result.output, result)
        self.assertIn("import", result.output, result)
        self.assertNotIn("exporter", result.output, result)


class PIManageTokenTestCase(CliTestCase):
    def test_01_pimanage_token_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["token"])
        self.assertIn("Commands to manage token in privacyIDEA", result.output, result)
        self.assertIn("Import tokens from a file", result.output, result)


@pytest.fixture(scope="function")
def create_user_resolver(app):
    """Create a user resolver"""
    with app.app_context():
        save_resolver({"resolver": "testresolver",
                       "type": "passwdresolver",
                       "fileName": "tests/testdata/passwords"})


@pytest.fixture(scope="class")
def app():
    """Create and configure app instance for testing"""
    app = create_app(config_name="testing", config_file="", silent=True)
    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        call_finalizers()
        close_all_sessions()
        db.drop_all()
        db.engine.dispose()


class TestPIManageSetupClass:
    def test_01_pimanage_setup_help(self, app):
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["setup"])
        assert "Commands to set up the privacyIDEA server for production" in result.output
        assert "create_audit_keys  Create the RSA signing keys for the audit log." in result.output
        assert "create_enckey      Create a key for encrypting the sensitive database..." in result.output
        assert "create_pgp_keys    Generate PGP keys to allow encrypted token import." in result.output
        assert "create_tables      Initially create the tables in the database." in result.output
        assert "drop_tables        This drops all the privacyIDEA database tables." in result.output
        assert "encrypt_enckey     Additionally encrypt the encryption key" in result.output

    def test_02_pimanage_setup_drop_tables(self, app):
        with app.app_context():
            # First check that the database is empty
            inspector = sa.inspect(db.engine)
            assert "token" in inspector.get_table_names()
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["setup", "drop_tables", "-d", "yes"])
        assert "Dropping all database tables!" in result.output
        with app.app_context():
            inspector = sa.inspect(db.engine)
            assert inspector.get_table_names() == []


class TestPIManageConfigExport:
    """Test export functions of pi-manage"""

    @pytest.mark.usefixtures("create_user_resolver")
    def test_pimanage_config_export(self, app, tmp_path):
        # Unfortunately capturing stdout/stderr doesn't work with pytest and the
        # cli_runner, so we need to write the output to a file
        outfile = tmp_path / "outfile.txt"
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "export", "-o", outfile])
        assert not result.exception
        out_text = outfile.read_text()
        assert "testresolver" in out_text
        assert "privacyIDEA_version" in out_text
        assert "periodictask" in out_text

        # Export only resolver configuration
        result = runner.invoke(pi_manage, ["config", "export", "-t", "resolver", "-o", outfile])
        assert not result.exception
        out_text = outfile.read_text()
        assert "testresolver" in out_text
        assert "privacyIDEA_version" in out_text
        assert "periodictask" not in out_text

    def test_pimanage_config_export_censor(self, app, tmp_path):
        # With --censor secrets are replaced with the __CENSORED__ placeholder
        from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
        outfile = tmp_path / "censor.json"
        runner = app.test_cli_runner()
        with app.app_context():
            add_smtpserver("censor_smtp", server="mail.example", password="supersecret")

        # without --censor the password is exported in clear text
        result = runner.invoke(pi_manage, ["config", "export", "-t", "smtpserver", "-o", outfile])
        assert not result.exception
        assert "supersecret" in outfile.read_text()

        # with --censor the password is replaced and no longer present in clear text
        result = runner.invoke(pi_manage, ["config", "export", "-t", "smtpserver", "--censor", "-o", outfile])
        assert not result.exception
        censored_text = outfile.read_text()
        assert "supersecret" not in censored_text
        assert "__CENSORED__" in censored_text

        with app.app_context():
            delete_smtpserver("censor_smtp")

    def test_pimanage_config_export_censor_all_types(self, app, tmp_path):
        # --censor with the default (all types) must not break: exporters that
        # do not support censoring (no secrets) are simply called without it.
        outfile = tmp_path / "all.json"
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "export", "--censor", "-o", outfile])
        assert not result.exception, result.output
        out_text = outfile.read_text()
        assert "privacyIDEA_version" in out_text
        # the stderr note about same-instance-only re-import is shown
        assert "__CENSORED__" in result.output


class TestPIManageConfigImport:
    """Test import functions of pi-manage.

    Reads the data from a file (``-i``) instead of <stdin>, because the click
    test runner does not connect its simulated input to the ``sys.stdin``
    default bound at decoration time. Uses uniquely named objects and cleans up,
    so the tests do not depend on (or leak) global configuration state.
    """

    def test_01_import_resolver_success(self, app, tmp_path):
        infile = tmp_path / "resolver.json"
        infile.write_text(json.dumps({"resolver": {"cliimpresolver": {
            "type": "passwdresolver", "resolvername": "cliimpresolver",
            "data": {"fileName": "tests/testdata/passwords"}}}}))
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "import", "-i", str(infile)])
        assert result.exit_code == 0, result.output
        # the version-warning message (note: the exact wording contains "the")
        assert "Unable to determine the version of exported data." in result.output
        assert "Importing configuration type 'resolver'." in result.output
        assert "Could not successfully import data of type resolver" not in result.output
        with app.app_context():
            res_dict = get_resolver_list()
            assert "cliimpresolver" in res_dict
            assert res_dict["cliimpresolver"]["type"] == "passwdresolver"
            delete_resolver("cliimpresolver")

    def test_02_import_unknown_format_exits(self, app, tmp_path):
        infile = tmp_path / "garbage.txt"
        # unbalanced brackets are rejected by all of json, yaml and python
        infile.write_text("{[}")
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "import", "-i", str(infile)])
        assert result.exit_code == 1, result.output
        assert "Could not determine input format" in result.output

    def test_03_import_failure_exits_nonzero_with_hint(self, app, tmp_path):
        # A policy with an action that does not exist in this version fails. The
        # import must exit non-zero (regression) and suggest --skip-invalid.
        infile = tmp_path / "badpolicy.json"
        infile.write_text(json.dumps({"policy": [
            {"name": "clibadpol", "scope": "admin", "action": {"enrollU2F": True}}]}))
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "import", "-i", str(infile)])
        assert result.exit_code == 1, result.output
        assert "Could not successfully import data of type policy" in result.output
        assert "Failed configuration types: policy" in result.output
        assert "--skip-invalid" in result.output

    def test_04_import_failure_is_partial(self, app, tmp_path):
        # A bad policy must not prevent a valid policy in the same file from
        # being imported.
        infile = tmp_path / "mixed.json"
        infile.write_text(json.dumps({"policy": [
            {"name": "clibadpol2", "scope": "admin", "action": {"enrollU2F": True}},
            {"name": "cligoodpol", "scope": "admin", "action": {"enable": True}}]}))
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "import", "-i", str(infile)])
        assert result.exit_code == 1, result.output
        from privacyidea.lib.policy import PolicyClass, delete_policy
        with app.app_context():
            names = [p["name"] for p in PolicyClass().match_policies()]
            assert "cligoodpol" in names
            assert "clibadpol2" not in names
            delete_policy("cligoodpol")

    def test_05_import_skip_invalid(self, app, tmp_path):
        # With --skip-invalid the invalid action is dropped and the policy is
        # imported with its remaining valid actions; exit code is 0.
        infile = tmp_path / "skip.json"
        infile.write_text(json.dumps({"policy": [
            {"name": "climixedpol", "scope": "admin",
             "action": {"enrollU2F": True, "disable": True}}]}))
        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "import", "-i", str(infile), "--skip-invalid"])
        assert result.exit_code == 0, result.output
        from privacyidea.lib.policy import PolicyClass, delete_policy
        with app.app_context():
            pols = {p["name"]: p["action"] for p in PolicyClass().match_policies()}
            assert "climixedpol" in pols
            assert "disable" in pols["climixedpol"]
            assert "enrollU2F" not in pols["climixedpol"]
            delete_policy("climixedpol")

    def test_06_censor_roundtrip_same_instance(self, app, tmp_path):
        # A censored export re-imported into the SAME instance keeps the stored
        # secret unchanged (the placeholder means "keep existing").
        from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver, list_smtpservers
        outfile = tmp_path / "censored.json"
        runner = app.test_cli_runner()
        with app.app_context():
            add_smtpserver("cliroundtrip", server="mail.example", password="keepmesecret")
        # export censored
        result = runner.invoke(pi_manage, ["config", "export", "-t", "smtpserver", "--censor", "-o", outfile])
        assert result.exit_code == 0, result.output
        assert "keepmesecret" not in outfile.read_text()
        # re-import the censored export
        result = runner.invoke(pi_manage, ["config", "import", "-i", str(outfile)])
        assert result.exit_code == 0, result.output
        with app.app_context():
            # the original secret must be preserved, not overwritten with the placeholder
            assert list_smtpservers("cliroundtrip")["cliroundtrip"]["password"] == "keepmesecret"
            delete_smtpserver("cliroundtrip")

    def test_07_yaml_format_roundtrip(self, app, tmp_path):
        # Export as YAML restricted to one object (-n), then re-import it. The
        # import auto-detects the YAML format.
        outfile = tmp_path / "cfg.yaml"
        runner = app.test_cli_runner()
        with app.app_context():
            save_resolver({"resolver": "cliyamlres", "type": "passwdresolver",
                           "fileName": "tests/testdata/passwords"})
        result = runner.invoke(pi_manage, ["config", "export", "-t", "resolver",
                                           "-n", "cliyamlres", "-f", "yaml", "-o", outfile])
        assert result.exit_code == 0, result.output
        with app.app_context():
            delete_resolver("cliyamlres")
        result = runner.invoke(pi_manage, ["config", "import", "-i", str(outfile)])
        assert result.exit_code == 0, result.output
        with app.app_context():
            assert "cliyamlres" in get_resolver_list()
            delete_resolver("cliyamlres")


class PIManageChallengeTestCase(CliTestCase):
    """
    Tests for ``pi-manage config challenge cleanup``.
    """

    def _init_challenges(self):
        # Insert two expired and one still-valid challenge.
        Challenge(serial='0', validitytime=0).save()
        Challenge(serial='1', validitytime=0).save()
        Challenge(serial='2', validitytime=300).save()

    def tearDown(self):
        Challenge.query.delete()
        db.session.commit()
        super().tearDown()

    def test_01_help(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["config", "challenge", "cleanup", "-h"])
        self.assertEqual(res.exit_code, 0, res.output)
        self.assertIn("Clean up all expired challenges", res.output, res)

    def test_02_dryrun(self):
        self._init_challenges()
        before = Challenge.query.count()

        runner = self.app.test_cli_runner()
        res = runner.invoke(
            pi_manage,
            ["config", "challenge", "cleanup", "--dryrun"],
        )

        self.assertEqual(res.exit_code, 0, res.output)
        self.assertIn("Would delete 2 challenge entries", res.output, res)
        self.assertEqual(Challenge.query.count(), before, "rows were deleted during --dryrun")

    def test_03_cleanup_expired(self):
        self._init_challenges()

        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["config", "challenge", "cleanup"])

        self.assertEqual(res.exit_code, 0, res.output)
        self.assertEqual(Challenge.query.count(), 1, "exactly one valid challenge must remain")
        self.assertIn("entries deleted.", res.output, res)

    def test_04_cleanup_age(self):
        self._init_challenges()

        three_min_ago = dt.datetime.utcnow() - dt.timedelta(minutes=3)
        Challenge.query.update({Challenge.timestamp: three_min_ago})
        db.session.commit()

        runner = self.app.test_cli_runner()
        res = runner.invoke(
            pi_manage,
            ["config", "challenge", "cleanup", "--age", "1"],
        )

        self.assertEqual(res.exit_code, 0, res.output)
        self.assertEqual(Challenge.query.count(), 0, "table should be empty after --age")
        self.assertIn("entries deleted", res.output, res)


class PIManageConfigCRUDTestCase(CliTestCase):
    """CLI coverage for the config sub-commands that manage resolvers,
    policies, events, the authentication cache and realm defaults."""

    def test_01_resolver_create_and_list(self):
        runner = self.app.test_cli_runner()
        # 'resolver create' reads the parameters from a file holding a python dict
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as conf_file:
            conf_file.write("{'fileName': 'tests/testdata/passwords'}")
            conf_path = conf_file.name
        try:
            result = runner.invoke(pi_manage, ["config", "resolver", "create",
                                               "cliresolver", "passwdresolver", conf_path])
            self.assertEqual(result.exit_code, 0, result.output)
            result = runner.invoke(pi_manage, ["config", "resolver", "list"])
            self.assertIn("cliresolver", result.output)
            self.assertIn("passwdresolver", result.output)
            # verbose listing must not break (it censors bindpw/password)
            result = runner.invoke(pi_manage, ["config", "resolver", "list", "-v"])
            self.assertEqual(result.exit_code, 0, result.output)
        finally:
            delete_resolver("cliresolver")
            os.unlink(conf_path)

    def test_02_policy_crud(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "policy", "create", "clipol", "admin", "enable"])
        self.assertEqual(result.exit_code, 0, result.output)
        result = runner.invoke(pi_manage, ["config", "policy", "list"])
        self.assertIn("clipol", result.output)
        result = runner.invoke(pi_manage, ["config", "policy", "disable", "clipol"])
        self.assertIn("disabled", result.output.lower(), result.output)
        result = runner.invoke(pi_manage, ["config", "policy", "enable", "clipol"])
        self.assertIn("enabled", result.output.lower(), result.output)
        result = runner.invoke(pi_manage, ["config", "policy", "delete", "clipol"])
        self.assertIn("deleted", result.output.lower(), result.output)

    def test_03_policy_enable_unknown(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "policy", "enable", "nosuchpolicy"])
        self.assertIn("Could not enable policy", result.output, result.output)

    def test_04_event_list(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "event", "list"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Active", result.output)

    def test_05_authcache_cleanup(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "authcache", "cleanup"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("entries deleted from authcache", result.output)

    def test_06_realm_set_and_clear_default(self):
        save_resolver({"resolver": "defresolver", "type": "passwdresolver", "fileName": PWFILE})
        runner = self.app.test_cli_runner()
        runner.invoke(pi_manage, ["config", "realm", "create", "defrealm", "defresolver"])
        result = runner.invoke(pi_manage, ["config", "realm", "set_default", "defrealm"])
        self.assertIn("set as default", result.output.lower(), result.output)
        result = runner.invoke(pi_manage, ["config", "realm", "clear_default"])
        self.assertIn("cleared default realm", result.output.lower(), result.output)
        runner.invoke(pi_manage, ["config", "realm", "delete", "defrealm"])
        delete_resolver("defresolver")

    def test_07_deprecated_aliases_warn(self):
        runner = self.app.test_cli_runner()
        for alias in ("importer", "exporter"):
            result = runner.invoke(pi_manage, ["config", alias, "-h"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("deprecated", result.output.lower(), result.output)

    def test_08_policy_create_from_file(self):
        # 'policy create' with -f reads a python dict; the file values take
        # precedence over the (still required) positional CLI arguments.
        runner = self.app.test_cli_runner()
        with tempfile.NamedTemporaryFile("w", suffix=".pol", delete=False) as pol_file:
            pol_file.write("{'name': 'clifilepol', 'scope': 'admin', 'action': 'enable'}")
            pol_path = pol_file.name
        try:
            result = runner.invoke(pi_manage, ["config", "policy", "create",
                                               "ignored", "admin", "enable", "-f", pol_path])
            self.assertEqual(result.exit_code, 0, result.output)
            result = runner.invoke(pi_manage, ["config", "policy", "list"])
            self.assertIn("clifilepol", result.output)
            self.assertNotIn("ignored", result.output)
        finally:
            from privacyidea.lib.policy import delete_policy
            delete_policy("clifilepol")
            os.unlink(pol_path)


class PIManageAuthLogTestCase(CliTestCase):
    """
    Tests for ``pi-manage authlog cleanup``.
    """

    def _insert(self, age_days, outcomes=0):
        # Insert an authentication-log entry aged age_days days, with outcomes conditional-access outcomes attached.
        entry = AuthenticationLog(event_type=AuthEventType.LOGIN_SUCCESS, resolver="r", uid="u", realm="rlm",
                                  timestamp=utc_now() - dt.timedelta(days=age_days))
        entry.save()
        for _ in range(outcomes):
            db.session.add(ConditionalAccessOutcome(auth_log_id=entry.id, action_type="LOCK_USER",
                                                    policy_name="p", threshold=3, event_count=3))
        db.session.commit()

    def tearDown(self):
        # Children first: nothing cascades on SQLite.
        ConditionalAccessOutcome.query.delete()
        AuthenticationLog.query.delete()
        db.session.commit()
        super().tearDown()

    def test_01_help(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["authlog", "cleanup", "-h"])
        self.assertEqual(res.exit_code, 0, res.output)
        self.assertIn("Clean up old authentication log entries.", res.output, res)

    def test_02_dryrun(self):
        self._insert(age_days=10)
        self._insert(age_days=0)
        before = AuthenticationLog.query.count()

        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["authlog", "cleanup", "--age", "7", "--dryrun"])

        self.assertEqual(res.exit_code, 0, res.output)
        self.assertIn("Would delete 1 authentication log entries", res.output, res)
        self.assertEqual(AuthenticationLog.query.count(), before, "rows were deleted during --dryrun")

    def test_03_cleanup_age(self):
        self._insert(age_days=10)
        self._insert(age_days=0)

        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["authlog", "cleanup", "--age", "7"])

        self.assertEqual(res.exit_code, 0, res.output)
        self.assertEqual(AuthenticationLog.query.count(), 1, "only the recent entry must remain")
        self.assertIn("Deleted 1 authentication log entries", res.output, res)

    def test_04_cleanup_chunked(self):
        for _ in range(3):
            self._insert(age_days=10)

        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["authlog", "cleanup", "--age", "1", "--chunksize", "1"])

        self.assertEqual(res.exit_code, 0, res.output)
        self.assertEqual(AuthenticationLog.query.count(), 0, "table should be empty after chunked cleanup")
        self.assertIn("Deleted 3 authentication log entries", res.output, res)

    def test_05_age_required(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["authlog", "cleanup"])
        self.assertNotEqual(res.exit_code, 0, res.output)
        self.assertIn("--age", res.output, res)

    def test_06_cleanup_removes_the_conditional_access_outcomes_too(self):
        # Retention is one story for the whole authentication history: an entry's conditional-access outcomes go with
        # it, including on SQLite, where the foreign key does not cascade and the lib deletes them explicitly.
        self._insert(age_days=10, outcomes=2)
        self._insert(age_days=0, outcomes=1)

        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["authlog", "cleanup", "--age", "7"])

        self.assertEqual(0, res.exit_code, res.output)
        self.assertEqual(1, AuthenticationLog.query.count(), "only the recent entry must remain")
        self.assertEqual(1, ConditionalAccessOutcome.query.count(), "only the recent entry's outcome must remain")

    def test_07_dryrun_keeps_the_outcomes(self):
        self._insert(age_days=10, outcomes=2)

        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["authlog", "cleanup", "--age", "7", "--dryrun"])

        self.assertEqual(0, res.exit_code, res.output)
        self.assertEqual(2, ConditionalAccessOutcome.query.count(), "--dryrun must not delete anything")


class PIManageConditionalAccessTestCase(CliTestCase):
    """
    Tests for ``pi-manage conditionalaccess`` — the escape hatch for clearing
    locked users and blocked IPs from the command line.
    """

    def tearDown(self):
        BlockList.query.delete()
        UserLockState.query.delete()
        db.session.commit()
        super().tearDown()

    def test_01_help_lists_subcommands(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess"])
        self.assertIn("list-blocked-ips", res.output, res)
        self.assertIn("unblock-ip", res.output, res)
        self.assertIn("list-locked-users", res.output, res)
        self.assertIn("unlock-user", res.output, res)

    def test_02_list_and_unblock_ip(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "list-blocked-ips"])
        self.assertIn("No blocked IPs.", res.output, res)

        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()

        res = runner.invoke(pi_manage, ["conditionalaccess", "list-blocked-ips"])
        self.assertIn("203.0.113.7", res.output, res)

        res = runner.invoke(pi_manage, ["conditionalaccess", "unblock-ip", "203.0.113.7"])
        self.assertIn("Removed the block for IP 203.0.113.7.", res.output, res)
        self.assertIsNone(BlockList.query.filter_by(ip="203.0.113.7").first())

    def test_03_unblock_missing_ip(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "unblock-ip", "203.0.113.9"])
        self.assertEqual(res.exit_code, 0, res.output)
        self.assertIn("No block found for IP 203.0.113.9.", res.output, res)

    def test_04_list_and_unlock_by_id(self):
        runner = self.app.test_cli_runner()
        db.session.add(UserLockState(resolver="reso1", uid="42", realm="realm1",
                                        lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()

        res = runner.invoke(pi_manage, ["conditionalaccess", "list-locked-users"])
        self.assertIn("uid=42", res.output, res)
        self.assertIn("realm=realm1", res.output, res)

        res = runner.invoke(pi_manage, ["conditionalaccess", "unlock-by-id",
                                        "--resolver", "reso1", "--uid", "42", "--realm", "realm1"])
        self.assertIn("Unlocked", res.output, res)
        self.assertIsNone(UserLockState.query.filter_by(resolver="reso1", uid="42",
                                                           realm="realm1").first())

    def test_04b_unlock_by_id_without_resolver(self):
        # --resolver is optional (disambiguator only); unlock-by-id must work on (uid, realm) alone.
        runner = self.app.test_cli_runner()
        db.session.add(UserLockState(resolver="reso1", uid="42", realm="realm1",
                                        lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()
        res = runner.invoke(pi_manage, ["conditionalaccess", "unlock-by-id", "--uid", "42", "--realm", "realm1"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertIn("Unlocked", res.output, res)
        self.assertIsNone(UserLockState.query.filter_by(uid="42", realm="realm1").first())

    def test_05_clear_blocks(self):
        runner = self.app.test_cli_runner()
        for ip in ("203.0.113.7", "203.0.113.8"):
            db.session.add(BlockList(ip=ip, block_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()

        res = runner.invoke(pi_manage, ["conditionalaccess", "clear-blocks", "--yes"])
        self.assertIn("Removed 2 IP block(s).", res.output, res)
        self.assertEqual(0, BlockList.query.count())

    def test_06_unlock_non_existing_user_works(self):
        db.session.add(UserLockState(resolver="test", realm="nope", username="ghost", uid="1234"))
        db.session.commit()
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage,
                            ["conditionalaccess", "unlock-user", "ghost", "--realm", "nope", "--resolver", "test"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertEqual(0, UserLockState.query.count())
        self.assertIn("Unlocked user ghost@nope (resolver=test)", res.output, res)

    def test_06_unlock_user_without_resolver(self):
        # Regression guard: --resolver only disambiguates, so unlock-user must still unlock without it;
        # filtering on resolver IS NULL would silently match nothing.
        db.session.add(UserLockState(resolver="test", realm="nope", username="ghost", uid="1234"))
        db.session.commit()
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "unlock-user", "ghost", "--realm", "nope"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertEqual(0, UserLockState.query.count())
        self.assertIn("Unlocked user ghost@nope", res.output, res)

    def test_06_unlock_user_without_entry(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage,
                            ["conditionalaccess", "unlock-user", "user", "--realm", "nope", "--resolver", "test"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertIn("No lock found for user user@nope", res.output, res)

    def test_07_list_locks_empty(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "list-locked-users"])
        self.assertIn("No locked users.", res.output, res)

    def test_08_unlock_by_id_missing(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "unlock-by-id",
                                        "--resolver", "reso1", "--uid", "999", "--realm", "realm1"])
        self.assertEqual(res.exit_code, 0, res.output)
        self.assertIn("No lock found", res.output, res)

    def test_09_clear_locks(self):
        runner = self.app.test_cli_runner()
        for uid in ("1", "2", "3"):
            db.session.add(UserLockState(resolver="reso1", uid=uid, realm="realm1",
                                            lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()
        res = runner.invoke(pi_manage, ["conditionalaccess", "clear-locks", "--yes"])
        self.assertIn("Removed 3 user lock(s).", res.output, res)
        self.assertEqual(0, UserLockState.query.count())

    def test_09b_clear_locks_by_realm(self):
        runner = self.app.test_cli_runner()
        db.session.add(UserLockState(resolver="reso1", uid="1", realm="realm1",
                                        lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.add(UserLockState(resolver="reso2", uid="2", realm="realm2",
                                        lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()
        res = runner.invoke(pi_manage, ["conditionalaccess", "clear-locks", "--realm", "realm1", "--yes"])
        self.assertIn("Removed 1 user lock(s) in realm 'realm1'.", res.output, res)
        # Only the realm1 lock was removed; realm2 is untouched.
        self.assertEqual(0, UserLockState.query.filter_by(realm="realm1").count())
        self.assertEqual(1, UserLockState.query.filter_by(realm="realm2").count())

    def test_09c_purge_expired_blocks(self):
        runner = self.app.test_cli_runner()
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() - dt.timedelta(seconds=60)))  # expired
        db.session.add(BlockList(ip="203.0.113.8", block_expires_at=utc_now() + dt.timedelta(seconds=600)))  # active
        db.session.commit()
        res = runner.invoke(pi_manage, ["conditionalaccess", "purge-expired-blocks"])
        self.assertIn("Removed 1 stale IP block(s).", res.output, res)
        # The active block is untouched.
        self.assertIsNone(BlockList.query.filter_by(ip="203.0.113.7").first())
        self.assertIsNotNone(BlockList.query.filter_by(ip="203.0.113.8").first())

    def test_09d_purge_expired_locks(self):
        runner = self.app.test_cli_runner()
        db.session.add(UserLockState(resolver="reso1", uid="1", realm="realm1",
                                        lock_expires_at=utc_now() - dt.timedelta(seconds=60)))  # expired
        db.session.add(UserLockState(resolver="reso1", uid="2", realm="realm1",
                                        lock_expires_at=utc_now() + dt.timedelta(seconds=600)))  # active
        db.session.commit()
        res = runner.invoke(pi_manage, ["conditionalaccess", "purge-expired-locks"])
        self.assertIn("Removed 1 stale user lock(s).", res.output, res)
        self.assertEqual(1, UserLockState.query.count())


class PIManageConditionalAccessPolicyTestCase(CliTestCase):
    """
    Tests for the ``pi-manage conditionalaccess`` policy commands — the escape hatch for
    switching off a policy that is refusing everybody, without the WebUI.
    """

    def tearDown(self):
        # Deleted through the ORM, so the stage/action/counter-type children go with the policy: a bulk
        # delete would leave them behind (SQLite does not enforce the FK cascade) and the next test's
        # policy would collide with them.
        for policy in ConditionalAccessPolicy.query.all():
            db.session.delete(policy)
        db.session.commit()
        super().tearDown()

    @staticmethod
    def _create_policy(name="lockdown", priority=1, enabled=True, dry_run=False,
                       threshold=0, action=ConditionalAccessAction.DENY) -> int:
        return create_conditional_access_policy(
            name=name, time_window_seconds=3600,
            counter_types_to_track=[str(AuthEventType.PASSWORD_FAIL)],
            stages=[{"failure_threshold": threshold,
                     "actions": [{"action_type": str(action), "action_value": None}]}],
            target=ConditionalAccessTarget.USER, priority=priority,
            enabled=enabled, dry_run=dry_run)

    def test_01_help_lists_policy_subcommands(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess"])
        for command in ("list-policies", "enable-policy", "disable-policy",
                        "enable-dry-run", "disable-dry-run", "delete-policy"):
            self.assertIn(command, res.output, res)

    def test_02_list_policies(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "list-policies"])
        self.assertIn("No conditional-access policies.", res.output, res)

        policy_id = self._create_policy(priority=7)
        res = runner.invoke(pi_manage, ["conditionalaccess", "list-policies"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertIn("Name", res.output, res)
        rows = [line for line in res.output.splitlines() if line.startswith("lockdown")]
        self.assertEqual(1, len(rows), res.output)
        self.assertListEqual(["lockdown", str(policy_id), "yes", "no", "7", "user"], rows[0].split())

    def test_03_list_policies_in_evaluation_order(self):
        runner = self.app.test_cli_runner()
        self._create_policy(name="second", priority=20)
        self._create_policy(name="first", priority=10)
        res = runner.invoke(pi_manage, ["conditionalaccess", "list-policies"])
        self.assertLess(res.output.index("first"), res.output.index("second"), res.output)

    def test_04_disable_and_enable_policy_by_name(self):
        runner = self.app.test_cli_runner()
        policy_id = self._create_policy()

        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-policy", "lockdown"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertIn(f"Disabled conditional-access policy 'lockdown' (id {policy_id}).", res.output, res)
        self.assertFalse(db.session.get(ConditionalAccessPolicy, policy_id).enabled)

        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-policy", "lockdown"])
        self.assertIn("is already disabled", res.output, res)

        res = runner.invoke(pi_manage, ["conditionalaccess", "enable-policy", "lockdown"])
        self.assertIn(f"Enabled conditional-access policy 'lockdown' (id {policy_id}).", res.output, res)
        self.assertTrue(db.session.get(ConditionalAccessPolicy, policy_id).enabled)

        res = runner.invoke(pi_manage, ["conditionalaccess", "enable-policy", "lockdown"])
        self.assertIn("is already enabled", res.output, res)

    def test_05_disable_policy_by_id(self):
        runner = self.app.test_cli_runner()
        policy_id = self._create_policy()
        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-policy", "--id", str(policy_id)])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertFalse(db.session.get(ConditionalAccessPolicy, policy_id).enabled)

    def test_06_numeric_name_is_never_taken_for_an_id(self):
        # A policy may legitimately be named "1" while another policy has the id 1. The argument is always a
        # name and --id is always an id, so neither spelling can address the other's policy.
        runner = self.app.test_cli_runner()
        by_id = self._create_policy(name="by-id", priority=1)
        by_name = self._create_policy(name=str(by_id), priority=2)

        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-policy", str(by_id)])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertFalse(db.session.get(ConditionalAccessPolicy, by_name).enabled)
        self.assertTrue(db.session.get(ConditionalAccessPolicy, by_id).enabled)

        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-policy", "--id", str(by_id)])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertFalse(db.session.get(ConditionalAccessPolicy, by_id).enabled)

    def test_07_unknown_policy_fails(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-policy", "ghost"])
        self.assertEqual(1, res.exit_code, res.output)
        self.assertIn("No conditional-access policy with the name 'ghost'.", res.output, res)

        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-policy", "--id", "4711"])
        self.assertEqual(1, res.exit_code, res.output)
        self.assertIn("No conditional-access policy with the id 4711.", res.output, res)

    def test_08_missing_name_points_at_the_id_option(self):
        # A numeric argument is a name, not an id; the error says how to ask for the id instead.
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-policy", "4711"])
        self.assertEqual(1, res.exit_code, res.output)
        self.assertIn("No conditional-access policy with the name '4711'.", res.output, res)
        self.assertIn("If you meant the id, use '--id 4711'.", res.output, res)

    def test_09_selector_must_be_unambiguous(self):
        runner = self.app.test_cli_runner()
        policy_id = self._create_policy()
        for args in (["conditionalaccess", "disable-policy"],
                     ["conditionalaccess", "disable-policy", "lockdown", "--id", str(policy_id)]):
            res = runner.invoke(pi_manage, args)
            self.assertEqual(2, res.exit_code, res.output)
            self.assertIn("Give either the policy NAME or --id, not both.", res.output, res)
        self.assertTrue(db.session.get(ConditionalAccessPolicy, policy_id).enabled)

    def test_10_toggle_dry_run(self):
        runner = self.app.test_cli_runner()
        policy_id = self._create_policy()

        res = runner.invoke(pi_manage, ["conditionalaccess", "enable-dry-run", "lockdown"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertIn("is now in dry run", res.output, res)
        self.assertTrue(db.session.get(ConditionalAccessPolicy, policy_id).dry_run)
        # Dry run leaves the policy enabled: it is still evaluated and logged, just not enforced.
        self.assertTrue(db.session.get(ConditionalAccessPolicy, policy_id).enabled)

        res = runner.invoke(pi_manage, ["conditionalaccess", "enable-dry-run", "lockdown"])
        self.assertIn("is already in dry run", res.output, res)

        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-dry-run", "lockdown"])
        self.assertIn("is no longer in dry run", res.output, res)
        self.assertFalse(db.session.get(ConditionalAccessPolicy, policy_id).dry_run)

        res = runner.invoke(pi_manage, ["conditionalaccess", "disable-dry-run", "lockdown"])
        self.assertIn("is not in dry run", res.output, res)

    def test_11_delete_policy(self):
        runner = self.app.test_cli_runner()
        policy_id = self._create_policy()

        # Without --yes the confirmation aborts, and the policy survives.
        res = runner.invoke(pi_manage, ["conditionalaccess", "delete-policy", "lockdown"], input="n\n")
        self.assertEqual(1, res.exit_code, res.output)
        self.assertIsNotNone(db.session.get(ConditionalAccessPolicy, policy_id))

        res = runner.invoke(pi_manage, ["conditionalaccess", "delete-policy", "lockdown", "--yes"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertIn(f"Deleted conditional-access policy 'lockdown' (id {policy_id}).", res.output, res)
        self.assertIsNone(db.session.get(ConditionalAccessPolicy, policy_id))

    def test_12_delete_policy_removes_stages_and_actions(self):
        runner = self.app.test_cli_runner()
        policy_id = self._create_policy()
        stage_ids = [stage.id for stage in db.session.get(ConditionalAccessPolicy, policy_id).stages]
        res = runner.invoke(pi_manage, ["conditionalaccess", "delete-policy", "--id", str(policy_id), "--yes"])
        self.assertEqual(0, res.exit_code, res.output)
        self.assertEqual(0, ConditionalAccessPolicyStage.query.filter(
            ConditionalAccessPolicyStage.id.in_(stage_ids)).count())
