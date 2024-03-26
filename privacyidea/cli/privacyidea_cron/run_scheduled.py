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

from datetime import datetime
import sys

import dateutil
from flask.cli import AppGroup
import click

from privacyidea.app import create_app
from privacyidea.cli.privacyidea_cron.utils import get_node_name, print_stdout, run_task_on_node, print_stderr
from privacyidea.lib.periodictask import get_scheduled_periodic_tasks

run_scheduled_cli = AppGroup("run_scheduled", help="Execute all periodic tasks that are scheduled to run.")
app = create_app(config_name='production', silent=True)


@run_scheduled_cli.command("run_scheduled")
@click.option("-d", "--dryrun",
              is_flag=True,
              help="Do not run any tasks, only show what would be done")
@click.option("-n", "--node", "node_string",
              help="Override the node name (read from privacyIDEA config by default)")
@click.option("-c", "--cron", "cron_mode", is_flag=True,
              help="Run in 'cron mode', i.e. do not write to stdout, but write errors to stderr")
def run_scheduled(node_string=None, dryrun=False, cron_mode=False):
    """
    Execute all periodic tasks that are scheduled to run.
    """
    app.config['cron_mode'] = cron_mode
    node = get_node_name(node_string)
    current_time = datetime.now(dateutil.tz.tzlocal())
    scheduled_tasks = get_scheduled_periodic_tasks(node, current_time)
    if scheduled_tasks:
        print_stdout("The following tasks are scheduled to run on node {!s}:".format(node))
        print_stdout()
        for ptask in scheduled_tasks:
            print_stdout("  {name} ({interval!r}, {taskmodule})".format(**ptask))

        print_stdout()
        if not dryrun:
            results = []
            for ptask in scheduled_tasks:
                result = run_task_on_node(ptask, node)
                results.append(result)
            if all(results):
                print_stdout("All scheduled tasks executed successfully.")
            else:
                print_stderr("Some tasks exited with errors.")
                sys.exit(1)
        else:
            print_stdout("Not running any tasks because --dryrun was passed.")
    else:
        print_stdout("There are no tasks scheduled on node {!s}.".format(node))
