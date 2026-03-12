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
from privacyidea.models import db, Challenge
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
    def _make_fake_run(live_pi_cfg, backup_uri):
        """
        Return a ``subprocess.run`` replacement that simulates two tar calls:

        1. ``tar -ztf <archive>`` (listing) – returns a two-line stdout with
           the relative paths of pi.cfg and the SQL dump so that
           ``backup_restore`` can locate both files inside the archive.

        2. ``tar -zxf <archive> -C /`` (extraction) – writes the backup
           content (``backup_uri``) into ``live_pi_cfg`` and creates a
           placeholder SQL file, mimicking what a real tar extraction would do.


        Note on path handling: ``backup_restore`` reads the tar listing and
        prepends "/" to each line to reconstruct absolute paths.  We therefore
        strip the leading "/" from the absolute ``live_pi_cfg`` path so that
        prepending "/" gives back the original absolute path.
        """
        import unittest.mock as mock

        sql_file_path = live_pi_cfg.parent / "dbdump-20240101-1200.sql"
        # Strip the leading "/" so backup_restore's "/{line}" reconstruction
        # resolves to the same absolute path we started with.
        cfg_rel = str(live_pi_cfg).lstrip("/")
        sql_rel = str(sql_file_path).lstrip("/")

        def fake_run(cmd, **kwargs):
            r = mock.MagicMock()
            r.returncode = 0
            if "-ztf" in cmd:
                # Simulate `tar -ztf fake.tgz` listing the archive contents.
                r.stdout = f"{cfg_rel}\n{sql_rel}\n"
            elif "-zxf" in cmd:
                # Simulate `tar -zxf fake.tgz -C /` extraction:
                # overwrite pi.cfg with the content that was stored in the
                # backup (backup_uri), and create a minimal SQL file.
                live_pi_cfg.write_text(
                    f'SQLALCHEMY_DATABASE_URI = {repr(backup_uri)}\n'
                    'SECRET_KEY = "secret"\n'
                )
                sql_file_path.write_text("-- sql dump placeholder\n")
            return r

        return fake_run

    def _run_restore_with_mocks(self, live_pi_cfg, backup_uri, live_uri):
        """
        Invoke ``backup restore --keep-db-uri fake.tgz`` with all external
        calls mocked so the test is fully self-contained:

        - ``subprocess.run`` is replaced by :meth:`_make_fake_run` which
          fakes the two tar invocations (listing + extraction).
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
        with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run",
                        side_effect=self._make_fake_run(live_pi_cfg, backup_uri)):
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
            with mock.patch("privacyidea.cli.pimanage.backup.subprocess.run",
                            side_effect=self._make_fake_run(live_pi_cfg, backup_uri)):
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

    def test_04_pimanage_backup_create(self):
        # TODO: create backup from an SQLite based configuration
        pass

    def test_05_pimanage_backup_restore(self):
        # TODO: restore backup from a backup file and check consistency
        pass


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
        Challenge(serial='0',validitytime=0).save()
        Challenge(serial='1',validitytime=0).save()
        Challenge(serial='2',validitytime=300).save()

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
