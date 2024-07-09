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

from privacyidea.cli.tools.get_serial import byotp
from .base import CliTestCase


class PIGetSerialTestCase(CliTestCase):
    def test_01_pi_get_serial_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(byotp, ["-h"])
        self.assertIn("This searches the list of the specified tokens for the given OTP value.",
                      result.output, result)
        self.assertIn("--assigned", result.output, result)
        self.assertIn("--unassigned", result.output, result)
        self.assertIn("--window", result.output, result)
        self.assertIn("--serial", result.output, result)
        self.assertIn("--type", result.output, result)
