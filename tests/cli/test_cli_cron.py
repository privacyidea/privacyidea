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
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.models import db
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.cli.tools.cron import cli as privacyidea_cron


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
