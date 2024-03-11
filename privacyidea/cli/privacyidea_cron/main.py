# SPDX-FileCopyrightText: (C) 2023 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
# 2024-03-08 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#            Migrate to click
#
# 2018-06-29 Friedrich Weber <friedrich.weber@netknights.it>
#            Implement periodic task runner
#
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

__doc__ = """
This script is meant to be invoked periodically by the system cron daemon.
It runs periodic tasks that are specified in the database.
"""
__version__ = "0.1"

import click
from flask.cli import FlaskGroup
from privacyidea.app import create_app
from privacyidea.lib.utils import get_version_number
from .run_scheduled import run_scheduled_cli
from .list import list_cli
from .run_manually import run_manually_cli

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(cls=FlaskGroup, create_app=create_app, context_settings=CONTEXT_SETTINGS,
             epilog='Check out our docs at https://privacyidea.readthedocs.io/ for more details')
def cli():
    """Management script for the privacyIDEA application."""
    click.echo(r"""
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
  / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|
/_/                       /___/
{0!s:>51}
    """.format('v{0!s}'.format(get_version_number())))


cli.add_command(run_scheduled_cli)
cli.add_command(list_cli)
cli.add_command(run_manually_cli)


if __name__ == '__main__':
    cli()

