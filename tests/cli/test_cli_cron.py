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

from .base import CliTestCase
from privacyidea.cli.tools.cron import cli as privacyidea_cron


class PICronTestCase(CliTestCase):
    def test_01_picron_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(privacyidea_cron, ["-h"])
        self.assertIn("Execute all periodic tasks that are scheduled to run.",
                      result.output, result)
        self.assertIn("Show a list of available tasks that could be run.",
                      result.output, result)
        self.assertIn("Manually run a periodic task",
                      result.output, result)
