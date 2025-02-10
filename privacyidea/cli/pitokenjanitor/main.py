# SPDX-FileCopyrightText: (C) 2023 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
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

import click
from privacyidea.cli import create_silent_app, NoPluginsFlaskGroup, get_version
from privacyidea.cli.pitokenjanitor.utils.findtokens import findtokens
from privacyidea.cli.pitokenjanitor.utils.importtokens import importtokens_cli
from privacyidea.cli.pitokenjanitor.utils.updatetokens import updatetokens

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(cls=NoPluginsFlaskGroup, create_app=create_silent_app, context_settings=CONTEXT_SETTINGS,
             add_default_commands=False, add_version_option=False,
             epilog='Check out our docs at https://privacyidea.readthedocs.io/ for more details')
@click.option(
    "--version",
    help="Show the version information",
    expose_value=False,
    callback=get_version,
    is_flag=True,
    is_eager=True,
)
def cli():
    """
\b
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \\/ __/ _ |
  / _ \\/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\\_,_/\\__/\\_, /___/____/___/_/ |_|
/_/                       /___/

   Management script for tokens of privacyIDEA."""


cli.add_command(findtokens)
cli.add_command(importtokens_cli)
cli.add_command(updatetokens)

if __name__ == '__main__':
    cli()
