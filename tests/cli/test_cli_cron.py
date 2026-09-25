# SPDX-FileCopyrightText: (C) 2024 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
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

import pytest
from flask import Flask
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.models import db
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.periodictask import get_periodic_task_by_name, set_periodic_task
from privacyidea.cli.tools.cron import cli as privacyidea_cron
from ..base import _reset_database


@pytest.fixture(scope="class")
def app():
    """Create and configure app instance for testing"""
    app = create_app(config_name="testing", config_file="", silent=True)
    with app.app_context():
        _reset_database()

    yield app

    with app.app_context():
        call_finalizers()
        close_all_sessions()
        db.engine.dispose()


class TestPICronExec:
    def test_01_picron_exec(self, app):
        runner = app.test_cli_runner()
        result = runner.invoke(privacyidea_cron, [])
        assert "Usage: cli [OPTIONS] COMMAND [ARGS]..." in result.output, result
        assert "Execute all periodic tasks that are scheduled to run." in result.output, result
        assert "run_scheduled" in result.output, result
        assert "Show a list of available tasks that could be run." in result.output, result
        assert "Manually run a periodic task" in result.output, result
        assert "run_manually" in result.output, result

        result = runner.invoke(privacyidea_cron, ["list"])
        assert "Active  ID  Name" in result.output, result.output

        result = runner.invoke(privacyidea_cron, ["run_scheduled"])
        assert "There are no tasks scheduled on node Node1." in result.output, result.output

        result = runner.invoke(privacyidea_cron, ["run_scheduled", "-c"])
        assert not result.output, result.output

        result = runner.invoke(privacyidea_cron, ["db", "--help"])
        assert result.exit_code == 2, result.output
        assert "No such command 'db'" in result.output, result.output


def create_task(app: Flask, name: str, taskmodule: str, retry_if_failed: bool) -> None:
    with app.app_context():
        set_periodic_task(name=name, interval="*/5 * * * *", nodes=["Node1"], taskmodule=taskmodule,
                          options={}, retry_if_failed=retry_if_failed)


def get_last_runs(app: Flask, name: str) -> dict:
    with app.app_context():
        return get_periodic_task_by_name(name)["last_runs"]


class TestPICronRunManually:
    def test_01_successful_task_is_recorded(self, app):
        create_task(app, "succeeding", "SimpleStats", retry_if_failed=True)
        runner = app.test_cli_runner()
        result = runner.invoke(privacyidea_cron, ["run_manually", "-t", "succeeding"])
        assert result.exit_code == 0, result.output
        assert "exited successfully" in result.output, result.output
        assert "Node1" in get_last_runs(app, "succeeding")

    def test_02_failing_task_with_retry_is_not_recorded(self, app):
        # An unknown task module makes the task fail
        create_task(app, "failing-retry", "UnknownTaskModule", retry_if_failed=True)
        runner = app.test_cli_runner()
        result = runner.invoke(privacyidea_cron, ["run_manually", "-t", "failing-retry"])
        assert result.exit_code == 1, result.output
        assert "did not run successfully" in result.output, result.output
        assert "is not recorded in the database, so the task stays due" in result.output, result.output
        assert get_last_runs(app, "failing-retry") == {}

    def test_03_failing_task_without_retry_is_recorded(self, app):
        create_task(app, "failing-no-retry", "UnknownTaskModule", retry_if_failed=False)
        runner = app.test_cli_runner()
        result = runner.invoke(privacyidea_cron, ["run_manually", "-t", "failing-no-retry"])
        assert result.exit_code == 1, result.output
        assert "is recorded in the database as the last run of the task" in result.output, result.output
        assert "Node1" in get_last_runs(app, "failing-no-retry")
