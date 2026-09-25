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

import os
import tempfile
from unittest import mock

import click

from privacyidea.cli.pimanage.main import cli as pi_manage
from privacyidea.cli.tools.standalone import cli as pi_standalone
from .base import CliTestCase


def get_pi_manage_command(arguments: list[str]) -> click.Command:
    """Follow the arguments through the pi-manage command groups and return the command they call."""
    command = pi_manage
    context = click.Context(pi_manage)
    for argument in arguments:
        if not isinstance(command, click.Group):
            break
        command = command.get_command(context, argument)
        assert command is not None, f"pi-manage has no command {arguments}"
    return command


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

    def create_instance(self, resolver_choice: str) -> list[list[str]]:
        """Run the create wizard with the given resolver choice and return the pi-manage calls."""
        runner = self.app.test_cli_runner()
        with (tempfile.TemporaryDirectory() as directory,
              mock.patch("privacyidea.cli.tools.standalone.invoke_pi_manage") as invoke_pi_manage):
            instance = os.path.join(directory, "instance")
            result = runner.invoke(pi_standalone, ["create", "-i", instance], input=f"y\n{resolver_choice}\n")
            self.assertEqual(0, result.exit_code, result.output)
            self.assertTrue(os.path.isfile(os.path.join(instance, "pi.cfg")), result.output)
        pi_manage_calls = [call.args[0] for call in invoke_pi_manage.call_args_list]
        for arguments in pi_manage_calls:
            command = get_pi_manage_command(arguments)
            self.assertFalse(command.deprecated, arguments)
            self.assertFalse(command.hidden, arguments)
        return pi_manage_calls

    def test_02_create_with_internal_resolver(self):
        pi_manage_calls = self.create_instance("1")
        self.assertEqual([["setup", "create_enckey"],
                          ["setup", "create_audit_keys"],
                          ["setup", "create_tables"],
                          ["admin", "add", "super"],
                          ["config", "resolver", "create_internal", "defresolver"],
                          ["config", "realm", "create", "defrealm", "defresolver"]], pi_manage_calls)

    def test_03_create_with_internal_resolver_by_default(self):
        pi_manage_calls = self.create_instance("")
        self.assertIn(["config", "resolver", "create_internal", "defresolver"], pi_manage_calls)

    def test_04_create_with_passwd_resolver(self):
        pi_manage_calls = self.create_instance("2")
        resolver_calls = [arguments for arguments in pi_manage_calls if arguments[:2] == ["config", "resolver"]]
        self.assertEqual(1, len(resolver_calls), pi_manage_calls)
        self.assertEqual(["config", "resolver", "create", "defresolver", "passwdresolver"], resolver_calls[0][:5])
        self.assertIn(["config", "realm", "create", "defrealm", "defresolver"], pi_manage_calls)

# TODO: write tests to configure and check an instance.
