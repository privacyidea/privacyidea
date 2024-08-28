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

import pytest
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.models import db
from privacyidea.cli.pimanage import cli as pi_manage
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.resolver import (save_resolver, delete_resolver,
                                      get_resolver_list)
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

    def test_02_pimanage_backup_create(self):
        # TODO: create backup from an SQLite based configuration
        pass

    def test_03_pimanage_backup_restore(self):
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


class TestPIManageConfigImportExport:
    """Test import/export functions of pi-manage"""

    @pytest.mark.usefixtures("create_user_resolver")
    def test_pimanage_config_import_export(self, app, tmp_path):
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

        # Import the exported resolver
        with app.app_context():
            delete_resolver("testresolver")
            res_dict = get_resolver_list()
            assert "testresolver" not in res_dict
        result = runner.invoke(pi_manage, ["config", "import", "-i", outfile])
        assert not result.exception
        with app.app_context():
            res_dict = get_resolver_list()
            assert "testresolver" in res_dict
