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
import pathlib
import tempfile

import pytest
import sqlalchemy as sa
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.cli.pimanage import cli as pi_manage
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.resolver import (save_resolver, delete_resolver,
                                      get_resolver_list)
from privacyidea.models import db, Challenge, AuthenticationLog
from privacyidea.models.lockout_policy import BlockList, UserLockoutState
from privacyidea.models.utils import utc_now
from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
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
    def _make_fake_tarfile(live_pi_cfg, backup_uri,
                           include_cfg=True, include_sql=True, include_enckey=False):
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
        """
        import unittest.mock as mock

        sql_file_path = live_pi_cfg.parent / "dbdump-20240101-1200.sql"
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
            self.assertFalse((tmp / "dbdump-20240101-1200.sql").exists())

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
            self.assertFalse((tmp / "dbdump-20240101-1200.sql").exists())

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
        parsed.password is None. _write_mysql_defaults must still produce a
        valid mysql defaults file (Python 3.12+ ConfigParser requires string
        values).
        """
        import configparser
        from urllib.parse import urlparse
        from privacyidea.cli.pimanage.backup import _write_mysql_defaults

        with tempfile.TemporaryDirectory() as tmp_dir:
            defaults_file = pathlib.Path(tmp_dir) / "mysql.cnf"
            # URI without password — parsed.password is None
            parsed = urlparse("mysql+pymysql://privacyidea@127.0.0.1/privacyidea_test")
            self.assertIsNone(parsed.password)

            _write_mysql_defaults(defaults_file, parsed)

            cp = configparser.ConfigParser(interpolation=None)
            cp.read(defaults_file)
            self.assertEqual(cp["client"]["user"], "privacyidea")
            self.assertEqual(cp["client"]["password"], "")

        # Passwords containing '%' must be written verbatim — the default
        # ConfigParser BasicInterpolation would otherwise reject them.
        with tempfile.TemporaryDirectory() as tmp_dir:
            defaults_file = pathlib.Path(tmp_dir) / "mysql.cnf"
            # urlparse keeps percent-encoding raw, so the value entering
            # ConfigParser literally contains '%'.
            parsed = urlparse("mysql+pymysql://privacyidea:ab%25cd@127.0.0.1/privacyidea_test")
            self.assertEqual(parsed.password, "ab%25cd")

            _write_mysql_defaults(defaults_file, parsed)

            cp = configparser.ConfigParser(interpolation=None)
            cp.read(defaults_file)
            self.assertEqual(cp["client"]["password"], "ab%25cd")

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
                            side_effect=self._make_fake_tarfile(live_pi_cfg, backup_uri)):
                with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run",
                                side_effect=failing_mysql):
                    result = runner.invoke(pi_manage, [
                        "backup", "restore", "ignored.tgz"])

            self.assertNotEqual(result.exit_code, 0, result.output)
            self.assertIn("Database restore failed", result.output, result.output)
            # The dump must be kept for inspection, not unlinked.
            self.assertTrue(sqlfile.exists(),
                            "dump file was deleted despite the restore failing")

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


class TestPIManageConfigImport:
    """Test import functions of pi-manage"""

    @pytest.mark.skip(reason="This test always fails in the complete testsuite")
    def test_pimanage_config_import(self, app, tmp_path):
        # TODO: Somehow this test fails when run in combination with other tests
        #  We will have to investigate more but for now we just skip it.
        # Import the given resolver
        infile = tmp_path / "infile.txt"
        infile.write_text("{'resolver': {'testresolver': {'type': 'passwdresolver', "
                          "'resolvername': 'testresolver', 'data': {'fileName': 'tests/testdata/passwords'}}}}")
        # Check, that the resolver is not configured
        with app.app_context():
            res_dict = get_resolver_list()
            assert "testresolver" not in res_dict

        runner = app.test_cli_runner()
        result = runner.invoke(pi_manage, ["config", "import", "-i", infile])
        assert not result.exception
        assert "Unable to determine version of exported data." in result.output
        assert "Please make sure that the imported configuration works as expected." in result.output
        assert "Importing configuration type 'resolver'." in result.output
        assert "Could not successfully import data of type resolver" not in result.output
        print(result.output)
        with app.app_context():
            res_dict = get_resolver_list()
            assert "testresolver" in res_dict
            assert res_dict["testresolver"]["type"] == "passwdresolver"
            assert res_dict["testresolver"]["data"] == {'fileName': 'tests/testdata/passwords'}


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


class PIManageAuthLogTestCase(CliTestCase):
    """
    Tests for ``pi-manage authlog cleanup``.
    """

    def _insert(self, age_days):
        # Insert one authentication-log entry aged the given number of days.
        AuthenticationLog(event_type=AuthEventType.LOGIN_SUCCESS, resolver="r", uid="u", realm="rlm",
                          timestamp=utc_now() - dt.timedelta(days=age_days)).save()

    def tearDown(self):
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


class PIManageConditionalAccessTestCase(CliTestCase):
    """
    Tests for ``pi-manage conditionalaccess`` — the escape hatch for clearing
    locked users and blocked IPs from the command line.
    """

    def tearDown(self):
        BlockList.query.delete()
        UserLockoutState.query.delete()
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

        db.session.add(BlockList(ip="203.0.113.7", is_blocked=True,
                                 block_expires_at=utc_now() + dt.timedelta(seconds=600),
                                 reason="brute force"))
        db.session.commit()

        res = runner.invoke(pi_manage, ["conditionalaccess", "list-blocked-ips"])
        self.assertIn("203.0.113.7", res.output, res)
        self.assertIn("brute force", res.output, res)

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
        db.session.add(UserLockoutState(resolver="reso1", uid="42", realm="realm1", is_locked=True,
                                        lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()

        res = runner.invoke(pi_manage, ["conditionalaccess", "list-locked-users"])
        self.assertIn("uid=42", res.output, res)
        self.assertIn("realm=realm1", res.output, res)

        res = runner.invoke(pi_manage, ["conditionalaccess", "unlock-by-id",
                                        "--resolver", "reso1", "--uid", "42", "--realm", "realm1"])
        self.assertIn("Unlocked", res.output, res)
        self.assertIsNone(UserLockoutState.query.filter_by(resolver="reso1", uid="42",
                                                           realm="realm1").first())

    def test_05_clear_blocks(self):
        runner = self.app.test_cli_runner()
        for ip in ("203.0.113.7", "203.0.113.8"):
            db.session.add(BlockList(ip=ip, is_blocked=True,
                                     block_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()

        res = runner.invoke(pi_manage, ["conditionalaccess", "clear-blocks", "--yes"])
        self.assertIn("Removed 2 IP block(s).", res.output, res)
        self.assertEqual(0, BlockList.query.count())

    def test_06_unlock_user_unresolvable(self):
        runner = self.app.test_cli_runner()
        res = runner.invoke(pi_manage, ["conditionalaccess", "unlock-user", "ghost", "--realm", "nope"])
        self.assertEqual(res.exit_code, 0, res.output)
        self.assertIn("could not be resolved", res.output, res)

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
            db.session.add(UserLockoutState(resolver="reso1", uid=uid, realm="realm1", is_locked=True,
                                            lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()
        res = runner.invoke(pi_manage, ["conditionalaccess", "clear-locks", "--yes"])
        self.assertIn("Removed 3 user lock(s).", res.output, res)
        self.assertEqual(0, UserLockoutState.query.count())

    def test_09b_clear_locks_by_realm(self):
        runner = self.app.test_cli_runner()
        db.session.add(UserLockoutState(resolver="reso1", uid="1", realm="realm1", is_locked=True,
                                        lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.add(UserLockoutState(resolver="reso2", uid="2", realm="realm2", is_locked=True,
                                        lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
        db.session.commit()
        res = runner.invoke(pi_manage, ["conditionalaccess", "clear-locks", "--realm", "realm1", "--yes"])
        self.assertIn("Removed 1 user lock(s) in realm 'realm1'.", res.output, res)
        # Only the realm1 lock was removed; realm2 is untouched.
        self.assertEqual(0, UserLockoutState.query.filter_by(realm="realm1").count())
        self.assertEqual(1, UserLockoutState.query.filter_by(realm="realm2").count())

    def test_10_unlock_user_resolvable(self):
        from privacyidea.lib.user import User
        from privacyidea.lib.realm import delete_realm
        save_resolver({"resolver": "resolver1", "type": "passwdresolver", "fileName": PWFILE})
        runner = self.app.test_cli_runner()
        runner.invoke(pi_manage, ["config", "realm", "create", "realm1", "resolver1"])
        try:
            user = User("cornelius", "realm1")
            self.assertTrue(user.exist(), "test fixture user cornelius must resolve")
            # A resolvable user with no lock -> "No lock found".
            res = runner.invoke(pi_manage, ["conditionalaccess", "unlock-user", "cornelius",
                                            "--realm", "realm1"])
            self.assertIn("No lock found for user cornelius@realm1.", res.output, res)
            # Lock the resolved user, then unlock them by login/realm.
            db.session.add(UserLockoutState(resolver=user.resolver, uid=user.uid, realm=user.realm,
                                            is_locked=True,
                                            lock_expires_at=utc_now() + dt.timedelta(seconds=600)))
            db.session.commit()
            res = runner.invoke(pi_manage, ["conditionalaccess", "unlock-user", "cornelius",
                                            "--realm", "realm1"])
            self.assertIn("Unlocked user cornelius@realm1.", res.output, res)
            self.assertIsNone(UserLockoutState.query.filter_by(
                resolver=user.resolver, uid=user.uid, realm=user.realm).first())
        finally:
            delete_realm("realm1")
            delete_resolver("resolver1")
