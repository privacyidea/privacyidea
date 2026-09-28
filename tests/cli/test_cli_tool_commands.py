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
"""The command line tools only offer their own commands, pi-manage also offers the commands of the app."""
import re

from privacyidea.cli.pimanage.main import cli as pi_manage
from privacyidea.cli.pitokenjanitor.main import cli as pi_tokenjanitor
from privacyidea.cli.privacyideatokenjanitor.main import cli as privacyidea_token_janitor
from privacyidea.cli.tools.cron import cli as privacyidea_cron
from privacyidea.cli.tools.get_unused_tokens import cli as privacyidea_get_unused_tokens
from .base import CliTestCase

TOOLS = {
    "pi-tokenjanitor": pi_tokenjanitor,
    "privacyidea-token-janitor": privacyidea_token_janitor,
    "privacyidea-cron": privacyidea_cron,
    "privacyidea-get-unused-tokens": privacyidea_get_unused_tokens,
}


class ToolCommandsTestCase(CliTestCase):
    def test_01_tools_do_not_offer_app_commands(self):
        runner = self.app.test_cli_runner()
        for tool_name, tool in TOOLS.items():
            with self.subTest(tool=tool_name):
                result = runner.invoke(tool, ["--help"])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIsNone(re.search(r"^\s+db\s", result.output, re.MULTILINE), result.output)

                result = runner.invoke(tool, ["db", "--help"])
                self.assertEqual(2, result.exit_code, result.output)
                self.assertIn("No such command 'db'", result.output)

    def test_02_pi_manage_offers_db_command(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_manage, ["--help"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIsNotNone(re.search(r"^\s+db\s", result.output, re.MULTILINE), result.output)

        result = runner.invoke(pi_manage, ["db", "--help"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Perform database migrations.", result.output)
        self.assertIn("upgrade", result.output)
