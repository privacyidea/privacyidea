# SPDX-FileCopyrightText: (C) 2023 Paul Lettich <paul.lettich@netknights.it>
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

from privacyidea.cli.tools.get_unused_tokens import cli
from .base import CliTestCase


class PIGetUnusedTokensTestCase(CliTestCase):
    def test_01_pi_get_unused_tokens_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["-h"])
        self.assertIn("Search for tokens that have not been used for a while",
                      result.output, result)
        self.assertIn("delete", result.output, result)
        self.assertIn("disable", result.output, result)
        self.assertIn("list", result.output, result)
        self.assertIn("mark", result.output, result)

    def test_02_pi_get_unused_tokens_find_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["list"])
        self.assertIn("Error: Missing argument 'AGE'.",
                      result.output, result)
        self.assertNotIn("Find all tokens where the last_auth is greater than AGE.",
                         result.output, result)
        result = runner.invoke(cli, ["list", "-h"])
        self.assertNotIn("Error: Missing argument 'AGE'.",
                         result.output, result)
        self.assertIn("Find all tokens where the last_auth is greater than AGE.",
                      result.output, result)
