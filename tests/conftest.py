# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
#
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

import os
import shutil

# Per-worker DB isolation for pytest-xdist. Must run before any `privacyidea`
# import, because TestingConfig.SQLALCHEMY_DATABASE_URI is evaluated at class
# definition (i.e. import) time.
_worker = os.environ.get("PYTEST_XDIST_WORKER")
if _worker:
    _base = os.environ.get("TEST_DATABASE_URL", "")
    if not _base:
        os.environ["TEST_DATABASE_URL"] = f"sqlite:////tmp/pi-test-{_worker}.sqlite"
    elif _base.startswith("sqlite"):
        os.environ["TEST_DATABASE_URL"] = _base.replace(".sqlite", f"-{_worker}.sqlite")
    else:  # mysql / postgres — suffix the DB name
        os.environ["TEST_DATABASE_URL"] = f"{_base}_{_worker}"

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def _force_read_committed_on_mysql(dbapi_connection, connection_record):
    """Set READ COMMITTED on every MySQL/MariaDB connection used by the tests.

    The test harness runs many simulated requests and pi-manage calls in a
    single process sharing one connection pool. On MariaDB's default REPEATABLE
    READ isolation a pooled connection keeps the snapshot of its first read, so
    a read issued after another test context committed can observe stale (empty)
    data. In production each request and each pi-manage call runs in its own
    process, so this only affects the test harness.

    This is scoped to the connection's driver (only MySQL/MariaDB), so it does
    not touch SQLite connections — including the separate SQLite engine the
    external-audit tests create, which rejects this isolation level. It also
    leaves SQLALCHEMY_ENGINE_OPTIONS untouched, so the audit engine's option
    inheritance is unaffected.
    """
    driver_module = type(dbapi_connection).__module__ or ""
    if "pymysql" in driver_module or "mysql" in driver_module.lower():
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        finally:
            cursor.close()


from privacyidea.lib.caconnector import save_caconnector

CAKEY = "cakey.pem"
CACERT = "cacert.pem"
OPENSSLCNF = "openssl.cnf"
WORKINGDIR = "tests/testdata/ca"


@pytest.fixture(scope="function")
def setup_local_ca(tmp_path):
    # TODO: we should probably yield the directory to properly clean it up
    shutil.copytree(WORKINGDIR, tmp_path, dirs_exist_ok=True)
    save_caconnector(
        {
            "cakey": CAKEY,
            "cacert": CACERT,
            "type": "local",
            "caconnector": "localCA",
            "openssl.cnf": OPENSSLCNF,
            "CSRDir": "",
            "CertificateDir": "",
            "WorkingDir": str(tmp_path),
        }
    )
