# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
"""Tests for the scripts in the tools directory."""
import json
import os
import re
import shutil
import sqlite3
import subprocess  # nosec B404 # only the scripts of the tools directory are run
import sys
from contextlib import closing
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest

REPOSITORY_DIRECTORY = Path(__file__).resolve().parents[2]
TOOLS_DIRECTORY = REPOSITORY_DIRECTORY / "tools"
VIRTUAL_ENVIRONMENT = "/opt/privacyidea"


def load_pip_update() -> ModuleType:
    loader = SourceFileLoader("privacyidea_pip_update", str(TOOLS_DIRECTORY / "privacyidea-pip-update"))
    module = module_from_spec(spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


def run_pip_update(arguments: list[str], answer: str = "", update_result: int = 0,
                   schema_result: int = 0) -> tuple[mock.Mock, mock.Mock, int | None]:
    """
    Run privacyidea-pip-update without touching the environment and return the mocked update steps and the exit
    code. The mocked steps return the given results.
    """
    pip_update = load_pip_update()
    with (mock.patch.object(pip_update, "update", return_value=update_result) as update,
          mock.patch.object(pip_update, "update_db_schema", return_value=schema_result) as update_db_schema,
          mock.patch.dict("os.environ", {"VIRTUAL_ENV": VIRTUAL_ENVIRONMENT}),
          mock.patch("sys.argv", ["privacyidea-pip-update"] + arguments),
          mock.patch("builtins.input", return_value=answer)):
        exit_code = pip_update.main()
    return update, update_db_schema, exit_code


class TestPipUpdate:
    def test_01_force_updates_code_and_schema(self):
        update, update_db_schema, exit_code = run_pip_update(["-f"])
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_called_once_with(VIRTUAL_ENVIRONMENT, False)
        assert exit_code == 0

    def test_02_force_passes_skipstamp(self):
        update, update_db_schema, exit_code = run_pip_update(["--force", "--skipstamp"])
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_called_once_with(VIRTUAL_ENVIRONMENT, True)
        assert exit_code == 0

    def test_03_force_with_noschema_skips_schema(self):
        update, update_db_schema, exit_code = run_pip_update(["-f", "-n"])
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_not_called()
        assert exit_code == 0

    def test_04_confirmed_update(self):
        update, update_db_schema, exit_code = run_pip_update([], answer="y")
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_called_once_with(VIRTUAL_ENVIRONMENT, False)
        assert exit_code == 0

    def test_05_canceled_update(self):
        update, update_db_schema, exit_code = run_pip_update([], answer="n")
        update.assert_not_called()
        update_db_schema.assert_not_called()
        assert not exit_code

    def test_06_failed_code_update_skips_schema(self):
        update, update_db_schema, exit_code = run_pip_update(["-f"], update_result=1)
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_not_called()
        assert exit_code == 1

    def test_07_failed_schema_update_is_the_exit_code(self):
        _update, update_db_schema, exit_code = run_pip_update(["-f"], schema_result=3)
        update_db_schema.assert_called_once_with(VIRTUAL_ENVIRONMENT, False)
        assert exit_code == 3

    def test_08_failed_package_upgrade_skips_requirements(self):
        pip_update = load_pip_update()
        with mock.patch.object(pip_update, "call", return_value=2) as call:
            assert pip_update.update(VIRTUAL_ENVIRONMENT) == 2
        call.assert_called_once()


PI_MANAGE_WRAPPER = '#!/bin/sh\nexec "{python}" "{pi_manage}" "$@"\n'

# "db current" reports the revisions in the file "revision", one per line. "db upgrade" gets as far as revision "b1"
# and fails.
FAILING_UPGRADE_PI_MANAGE = """#!/bin/sh
case "$1 $2" in
  "db current") echo "Current revision(s) for sqlite:///stub.sqlite:"; sed 's/^/Rev: /' revision ;;
  "db upgrade") echo "b1" > revision; exit 3 ;;
esac
"""


def write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def run_sql(database: Path, statement: str) -> list[tuple]:
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute(statement).fetchall()
        connection.commit()
    return rows


def pi_manage_environment(pi_manage_directory: Path, database: Path) -> dict[str, str]:
    """Return the environment in which pi-manage runs this repository's code against the given SQLite database."""
    config_file = database.with_suffix(".cfg")
    config_file.write_text(f"SQLALCHEMY_DATABASE_URI = 'sqlite:///{database}'\n"
                           "SECRET_KEY = 'secret'\n"
                           "PI_PEPPER = 'pepper'\n"
                           f"PI_LOGFILE = '{database.with_suffix('.log')}'\n")
    return {**os.environ, "PATH": f"{pi_manage_directory}{os.pathsep}{os.environ['PATH']}",
            "PRIVACYIDEA_CONFIGFILE": str(config_file)}


@pytest.fixture(scope="module")
def pi_manage_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A directory with a pi-manage command that runs the pi-manage of this repository."""
    directory = tmp_path_factory.mktemp("bin")
    write_executable(directory / "pi-manage",
                     PI_MANAGE_WRAPPER.format(python=sys.executable, pi_manage=REPOSITORY_DIRECTORY / "pi-manage"))
    return directory


@pytest.fixture(scope="module")
def stamped_database(tmp_path_factory: pytest.TempPathFactory, pi_manage_directory: Path) -> Path:
    """An SQLite database with the tables of this version, stamped with the newest revision."""
    database = tmp_path_factory.mktemp("stamped") / "privacyidea.sqlite"
    result = subprocess.run([str(pi_manage_directory / "pi-manage"), "setup", "create_tables"],  # nosec B603
                            cwd=REPOSITORY_DIRECTORY, env=pi_manage_environment(pi_manage_directory, database),
                            capture_output=True, text=True, timeout=120, check=False)
    assert result.returncode == 0, result
    return database


@pytest.fixture
def database(tmp_path: Path, stamped_database: Path) -> Path:
    """A copy of the stamped database for one test."""
    database = tmp_path / "privacyidea.sqlite"
    shutil.copyfile(stamped_database, database)
    return database


@pytest.mark.skipif(shutil.which("sh") is None, reason="sh is not available")
class TestSchemaUpgrade:
    @staticmethod
    def run_schema_upgrade(arguments: list[str], environment: dict[str, str] | None = None,
                           directory: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["sh", str(TOOLS_DIRECTORY / "privacyidea-schema-upgrade")] + arguments,  # nosec B603
                              capture_output=True, text=True, timeout=120, check=False, env=environment,
                              cwd=directory)

    def test_01_positional_argument_is_rejected(self):
        result = self.run_schema_upgrade(["/opt/privacyidea/lib/privacyidea/migrations"])
        assert result.returncode == 1, result
        assert "Unknown argument /opt/privacyidea/lib/privacyidea/migrations" in result.stdout
        assert "Usage:" in result.stdout

    def test_02_unknown_option_is_rejected(self):
        result = self.run_schema_upgrade(["--unknown"])
        assert result.returncode == 1, result
        assert "Unknown option --unknown" in result.stdout

    def test_03_help(self):
        result = self.run_schema_upgrade(["--help"])
        assert result.returncode == 0, result
        assert "--migration_dir" in result.stdout

    def test_04_missing_migration_directory_is_rejected(self, tmp_path: Path):
        missing_directory = tmp_path / "missing"
        result = self.run_schema_upgrade(["-d", str(missing_directory)])
        assert result.returncode == 1, result
        assert f"The migration directory '{missing_directory}' does not exist." in result.stdout

    @pytest.mark.parametrize("arguments", [["-d"], ["-d", ""], ["--migration_dir", ""]])
    def test_05_migration_directory_option_needs_a_value(self, arguments: list[str]):
        result = self.run_schema_upgrade(arguments)
        assert result.returncode == 1, result
        assert f"Option {arguments[0]} requires a directory" in result.stdout
        assert "Usage:" in result.stdout

    def test_06_upgrade_prints_the_revision_before_and_after(self, tmp_path: Path, pi_manage_directory: Path,
                                                              database: Path):
        """The migration directory is passed on as one argument, even with a space in its path."""
        migration_directory = tmp_path / "migration scripts"
        shutil.copytree(REPOSITORY_DIRECTORY / "privacyidea" / "migrations", migration_directory)
        head = run_sql(database, "SELECT version_num FROM alembic_version")[0][0]
        result = self.run_schema_upgrade(["-d", str(migration_directory)],
                                         pi_manage_environment(pi_manage_directory, database), tmp_path)
        assert result.returncode == 0, result
        assert f"++ Database: sqlite:///{database}" in result.stdout
        assert f"++ Schema revision before the upgrade: {head} (head)" in result.stdout
        assert f"++ Schema revision after the upgrade: {head} (head)" in result.stdout

    def test_07_database_without_stamp_is_left_unchanged(self, pi_manage_directory: Path, database: Path):
        """
        "pi-manage db upgrade" stops on a database without stamp, and the script ends with its exit code. The option
        --skipstamp is accepted and changes nothing.
        """
        run_sql(database, "DELETE FROM alembic_version")
        tables = run_sql(database, "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
        result = self.run_schema_upgrade(["--skipstamp"], pi_manage_environment(pi_manage_directory, database),
                                         REPOSITORY_DIRECTORY)
        assert result.returncode == 1, result
        assert f"++ Database: sqlite:///{database}" in result.stdout
        assert "++ Schema revision before the upgrade: none\n" in result.stdout
        assert f"The database sqlite:///{database} has no schema revision stamp" in result.stderr
        assert "++ Schema revision after the upgrade: none\n" in result.stdout
        assert run_sql(database, "SELECT version_num FROM alembic_version") == []
        assert run_sql(database, "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name") == tables

    def test_08_unreadable_revision_shows_the_error_of_pi_manage(self, pi_manage_directory: Path, database: Path):
        run_sql(database, "UPDATE alembic_version SET version_num = 'feedface0001'")
        result = self.run_schema_upgrade([], pi_manage_environment(pi_manage_directory, database),
                                         REPOSITORY_DIRECTORY)
        assert result.returncode == 1, result
        assert "Can't locate revision identified by 'feedface0001'" in result.stdout
        assert "ERROR: The schema revision of the database could not be read." in result.stdout
        assert "Upgrading DB schema" not in result.stdout
        assert run_sql(database, "SELECT version_num FROM alembic_version") == [("feedface0001",)]

    def run_with_failing_upgrade(self, directory: Path, revisions: list[str]) -> subprocess.CompletedProcess:
        """Run the script in *directory* with a pi-manage whose database is stamped with *revisions*."""
        command_directory = directory / "bin"
        command_directory.mkdir()
        write_executable(command_directory / "pi-manage", FAILING_UPGRADE_PI_MANAGE)
        (directory / "revision").write_text("".join(f"{revision}\n" for revision in revisions))
        environment = {**os.environ, "PATH": f"{command_directory}{os.pathsep}{os.environ['PATH']}"}
        return self.run_schema_upgrade([], environment, directory)

    def test_09_failed_upgrade_prints_the_revision_reached(self, tmp_path: Path):
        """The script ends with the exit code of the failed upgrade."""
        result = self.run_with_failing_upgrade(tmp_path, ["a0"])
        assert result.returncode == 3, result
        assert "++ Database: sqlite:///stub.sqlite" in result.stdout
        assert "++ Schema revision before the upgrade: a0" in result.stdout
        assert "++ Schema revision after the upgrade: b1" in result.stdout

    def test_10_revisions_of_a_database_with_two_heads_are_printed_on_one_line(self, tmp_path: Path):
        result = self.run_with_failing_upgrade(tmp_path, ["a0 (head)", "z0 (head)"])
        assert "++ Schema revision before the upgrade: a0 (head) z0 (head)\n" in result.stdout


@pytest.mark.skipif(shutil.which("sh") is None, reason="sh is not available")
class TestPiManageDbUpgrade:
    """
    "pi-manage db upgrade" stops on a database without schema revision stamp. "pi-manage db stamp" stays available
    for such a database.
    """

    @staticmethod
    def run_pi_manage(arguments: list[str], pi_manage_directory: Path, database: Path) -> subprocess.CompletedProcess:
        return subprocess.run([str(pi_manage_directory / "pi-manage")] + arguments,  # nosec B603
                              cwd=REPOSITORY_DIRECTORY, env=pi_manage_environment(pi_manage_directory, database),
                              capture_output=True, text=True, timeout=120, check=False)

    def test_01_upgrade_of_a_stamped_database(self, pi_manage_directory: Path, database: Path):
        result = self.run_pi_manage(["db", "upgrade"], pi_manage_directory, database)
        assert result.returncode == 0, result

    def test_02_upgrade_refuses_tables_without_stamp(self, pi_manage_directory: Path, database: Path):
        run_sql(database, "DELETE FROM alembic_version")
        tables = run_sql(database, "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
        result = self.run_pi_manage(["db", "upgrade"], pi_manage_directory, database)
        assert result.returncode == 1, result
        assert f"The database sqlite:///{database} has no schema revision stamp" in result.stderr
        assert "stamp the database with 'pi-manage db stamp head'" in result.stderr
        assert ("If an older version created the tables, stamp the database with the newest revision of that version."
                in result.stderr)
        assert run_sql(database, "SELECT version_num FROM alembic_version") == []
        assert run_sql(database, "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name") == tables

    def test_03_upgrade_refuses_an_empty_database(self, tmp_path: Path, pi_manage_directory: Path):
        database = tmp_path / "empty.sqlite"
        result = self.run_pi_manage(["db", "upgrade"], pi_manage_directory, database)
        assert result.returncode == 1, result
        assert "create the tables with 'pi-manage setup create_tables'" in result.stderr
        assert "stamp the database" not in result.stderr
        assert run_sql(database, "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'token'") == []

    def test_04_stamp_of_a_database_without_stamp(self, pi_manage_directory: Path, database: Path):
        """The stamp is logged as a stamp, not as a migration."""
        head = run_sql(database, "SELECT version_num FROM alembic_version")[0][0]
        run_sql(database, "DELETE FROM alembic_version")
        result = self.run_pi_manage(["db", "stamp", "head"], pi_manage_directory, database)
        assert result.returncode == 0, result
        assert f"Stamped revision {head}, no migration ran (was base)" in result.stdout
        assert run_sql(database, "SELECT version_num FROM alembic_version") == [(head,)]

    def test_05_upgrade_uses_the_migration_directory_of_the_command_group(self, tmp_path: Path,
                                                                          pi_manage_directory: Path, database: Path):
        missing_directory = tmp_path / "missing"
        result = self.run_pi_manage(["db", "-d", str(missing_directory), "upgrade"], pi_manage_directory, database)
        assert result.returncode == 1, result
        assert f"Path doesn't exist: {missing_directory}" in result.stderr


PI_CFG_WITH_SECRETS = """import logging
import os
# SQLALCHEMY_DATABASE_URI = 'mysql://pi:commentsecret@localhost/pi'
SUPERUSER_REALM = ['super']
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://pi:databasesecret@localhost/pi?charset=utf8mb4'
PI_AUDIT_SQL_URI = (
    'postgresql+psycopg2://audit:auditsecret@localhost/audit'
)
SECRET_KEY = b'secretkeysecret'
PI_PEPPER = "peppersecret"
PI_DB_PASSWORD = 'dbpasswordsecret'
PI_REDIS_URL = f"redis://:{os.environ.get('REDIS_PASSWORD', 'redissecret')}@localhost:6379/0"
PI_HSM_MODULE_PASSWORD = 'hsmsecret'
SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"password": "enginesecret"}}
if os.path.exists('/etc/privacyidea/monitoring'):
    PI_MONITORING_SQL_URI = 'mysql://monitoring:monitoringsecret@localhost/monitoring'
PI_ENCFILE = '/etc/privacyidea/enckey'
PI_BASE_URL = 'https://privacyidea.example.com/pi'
PI_LOGLEVEL = logging.INFO  # loglevel comment
"""


def run_diag_function(function_name: str, arguments: list[str], standard_input: str = "") -> str:
    """Run a function of privacyidea-diag, without the rest of the script, and return its output."""
    diag_script = (TOOLS_DIRECTORY / "privacyidea-diag").read_text()
    functions = [re.search(rf"^{name}\(\) {{\n.*?^}}\n", diag_script, re.MULTILINE | re.DOTALL).group(0)
                 for name in ("pi_python", function_name)]
    result = subprocess.run(["bash", "-c", "".join(functions) + f'{function_name} "$@"', "bash"] + arguments,  # nosec B603
                            input=standard_input, capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result
    return result.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not available")
def test_diag_censors_pi_cfg(tmp_path: Path):
    config_file = tmp_path / "pi.cfg"
    config_file.write_text(PI_CFG_WITH_SECRETS)
    censored = run_diag_function("censor_pi_cfg", [str(config_file)])
    assert re.search(r"[a-z]secret", censored, re.IGNORECASE) is None, censored
    assert "comment" not in censored
    assert "SQLALCHEMY_DATABASE_URI = 'mysql+pymysql:<censored>'" in censored
    assert "PI_AUDIT_SQL_URI = 'postgresql+psycopg2:<censored>'" in censored
    assert "PI_REDIS_URL = 'redis:<censored>'" in censored
    for name in ("SECRET_KEY", "PI_PEPPER", "PI_DB_PASSWORD", "PI_HSM_MODULE_PASSWORD", "SQLALCHEMY_ENGINE_OPTIONS",
                 "PI_MONITORING_SQL_URI"):
        assert f"{name} = <censored>" in censored
    assert "SUPERUSER_REALM = ['super']" in censored
    assert "PI_ENCFILE = '/etc/privacyidea/enckey'" in censored
    assert "PI_BASE_URL = 'https://privacyidea.example.com/pi'" in censored
    assert "PI_LOGLEVEL = logging.INFO" in censored


EXPORT_WITH_SECRETS = {
    "resolver": {
        "scim": {"type": "scimresolver", "censor_keys": [],
                 "data": {"authsecret": "scimsecret", "authserver": "https://auth.example.com"}},
        "http": {"type": "httpresolver", "censor_keys": ["password"],
                 "data": {"password": "__CENSORED__",
                          "config_authorization": {
                              "method": "POST",
                              "headers": json.dumps({"Authorization": "Bearer headersecret",
                                                     "Content-Type": "application/json"}),
                              "requestMapping": json.dumps({"client_secret": "mappingsecret", "user": "service"})}}}},
    "policy": {"token": {"action": {"tokenlabel": "<s>", "api_key": ["listsecret"]}},
               "yubikey": {"action": {"yubikey_access_code": "accesscodesecret", "losttoken": True,
                                      "passOnNoToken": True}}},
    "event": {"enroll": {"options": {"motppin": "motppinsecret", "tokentype": "motp",
                                     "authtoken": "authtokensecret"}}},
}


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not available")
def test_diag_censors_exported_configuration():
    censored = json.loads(run_diag_function("censor_json", [], json.dumps(EXPORT_WITH_SECRETS)))
    for secret in ("scimsecret", "headersecret", "mappingsecret", "listsecret", "accesscodesecret", "motppinsecret",
                   "authtokensecret"):
        assert secret not in json.dumps(censored), censored
    scim_data = censored["resolver"]["scim"]["data"]
    assert scim_data == {"authsecret": "__CENSORED__", "authserver": "https://auth.example.com"}
    authorization = censored["resolver"]["http"]["data"]["config_authorization"]
    assert authorization["method"] == "POST"
    assert json.loads(authorization["headers"]) == {"Authorization": "__CENSORED__", "Content-Type": "application/json"}
    assert json.loads(authorization["requestMapping"]) == {"client_secret": "__CENSORED__", "user": "service"}
    assert censored["policy"] == {"token": {"action": {"tokenlabel": "<s>", "api_key": ["__CENSORED__"]}},
                                  "yubikey": {"action": {"yubikey_access_code": "__CENSORED__", "losttoken": True,
                                                         "passOnNoToken": True}}}
    assert censored["event"] == {"enroll": {"options": {"motppin": "__CENSORED__", "tokentype": "motp",
                                                        "authtoken": "__CENSORED__"}}}


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not available")
def test_diag_leaves_out_unparsable_export():
    censored = run_diag_function("censor_json", [], "Error: no JSON")
    assert censored == "The export could not be parsed and is not included.\n"
