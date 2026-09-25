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
import re
import shutil
import subprocess  # nosec B404 # only the scripts of the tools directory are run
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest

TOOLS_DIRECTORY = Path(__file__).resolve().parents[2] / "tools"
VIRTUAL_ENVIRONMENT = "/opt/privacyidea"


def load_pip_update() -> ModuleType:
    loader = SourceFileLoader("privacyidea_pip_update", str(TOOLS_DIRECTORY / "privacyidea-pip-update"))
    module = module_from_spec(spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


def run_pip_update(arguments: list[str], answer: str = "") -> tuple[mock.Mock, mock.Mock]:
    """Run privacyidea-pip-update without touching the environment and return the mocked update steps."""
    pip_update = load_pip_update()
    with (mock.patch.object(pip_update, "update") as update,
          mock.patch.object(pip_update, "update_db_schema") as update_db_schema,
          mock.patch.dict("os.environ", {"VIRTUAL_ENV": VIRTUAL_ENVIRONMENT}),
          mock.patch("sys.argv", ["privacyidea-pip-update"] + arguments),
          mock.patch("builtins.input", return_value=answer)):
        pip_update.main()
    return update, update_db_schema


class TestPipUpdate:
    def test_01_force_updates_code_and_schema(self):
        update, update_db_schema = run_pip_update(["-f"])
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_called_once_with(VIRTUAL_ENVIRONMENT, False)

    def test_02_force_passes_skipstamp(self):
        update, update_db_schema = run_pip_update(["--force", "--skipstamp"])
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_called_once_with(VIRTUAL_ENVIRONMENT, True)

    def test_03_force_with_noschema_skips_schema(self):
        update, update_db_schema = run_pip_update(["-f", "-n"])
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_not_called()

    def test_04_confirmed_update(self):
        update, update_db_schema = run_pip_update([], answer="y")
        update.assert_called_once_with(VIRTUAL_ENVIRONMENT)
        update_db_schema.assert_called_once_with(VIRTUAL_ENVIRONMENT, False)

    def test_05_canceled_update(self):
        update, update_db_schema = run_pip_update([], answer="n")
        update.assert_not_called()
        update_db_schema.assert_not_called()


@pytest.mark.skipif(shutil.which("sh") is None, reason="sh is not available")
class TestSchemaUpgrade:
    @staticmethod
    def run_schema_upgrade(arguments: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(["sh", str(TOOLS_DIRECTORY / "privacyidea-schema-upgrade")] + arguments,  # nosec B603
                              capture_output=True, text=True, timeout=30, check=False)

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
    "policy": {"token": {"action": {"tokenlabel": "<s>", "api_key": ["listsecret"]}}},
}


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not available")
def test_diag_censors_exported_configuration():
    censored = json.loads(run_diag_function("censor_json", [], json.dumps(EXPORT_WITH_SECRETS)))
    for secret in ("scimsecret", "headersecret", "mappingsecret", "listsecret"):
        assert secret not in json.dumps(censored), censored
    scim_data = censored["resolver"]["scim"]["data"]
    assert scim_data == {"authsecret": "__CENSORED__", "authserver": "https://auth.example.com"}
    authorization = censored["resolver"]["http"]["data"]["config_authorization"]
    assert authorization["method"] == "POST"
    assert json.loads(authorization["headers"]) == {"Authorization": "__CENSORED__", "Content-Type": "application/json"}
    assert json.loads(authorization["requestMapping"]) == {"client_secret": "__CENSORED__", "user": "service"}
    assert censored["policy"] == {"token": {"action": {"tokenlabel": "<s>", "api_key": ["__CENSORED__"]}}}


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not available")
def test_diag_leaves_out_unparsable_export():
    censored = run_diag_function("censor_json", [], "Error: no JSON")
    assert censored == "The export could not be parsed and is not included.\n"
