# SPDX-FileCopyrightText: (C) 2024 Paul Lettich <paul.lettich@netknights.it>
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

from privacyidea.cli.tools.standalone import cli as pi_standalone
from .base import CliTestCase


class PIStandaloneTestCase(CliTestCase):
    def test_01_pi_standalone_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_standalone)
        self.assertIn("Check the given username and password against privacyIDEA.",
                      result.output, result)
        self.assertIn("Run a local webserver to configure the privacyIDEA instance.",
                      result.output, result)
        self.assertIn("Create a new privacyIDEA instance.",
                      result.output, result)

# TODO: write tests to create, configure and check an instance. We need to add
#  parameters for the admin user name and password as well as the desired
#  resolver to the create command in order to properly test this.
