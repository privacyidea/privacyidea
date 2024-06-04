#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 2018-06-29 Friedrich Weber <friedrich.weber@netknights.it>
#            Implement periodic task runner
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__doc__ = """
This script is meant to be invoked periodically by the system cron daemon.
It runs periodic tasks that are specified in the database.
"""

import click
from datetime import datetime
from dateutil import tz
from flask import current_app
import json
import sys
import traceback
import warnings

from privacyidea.cli import create_silent_app, NoPluginsFlaskGroup
from privacyidea.lib.config import get_privacyidea_node
from privacyidea.lib.periodictask import (get_scheduled_periodic_tasks,
                                          execute_task, get_periodic_tasks,
                                          get_periodic_task_by_name,
                                          set_periodic_task_last_run)
from privacyidea.lib.utils import get_version_number

warnings.simplefilter("ignore")

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def print_stdout(*args, **kwargs):
    """
    Print to stdout, except if "cron mode" has been activated.
    """
    if not current_app.config.get("cron_mode", False):
        click.echo(*args, **kwargs)


def print_stderr(*args, **kwargs):
    """
    Print to stderr.
    """
    click.echo(*args, file=sys.stderr, **kwargs)


def get_node_name(node):
    """
    Determine the node name. If no node name is given, read it from the app config.

    :param node: node name given by the user (can be None)
    :return:
    """
    if node is not None:
        return node
    else:
        return get_privacyidea_node()


def run_task_on_node(ptask, node):
    """
    Run a periodic task (given as a dictionary) on the given node.
    In case of success, write the last successful run to the database. Catch any exceptions.

    :param ptask: task as a dictionary
    :param node: Node name
    """
    try:
        print_stdout("Running {!r} ...".format(ptask["name"]), nl=False)
        result = execute_task(ptask["taskmodule"], ptask["options"])
    except Exception as e:
        print_stderr('Caught exception when running {!r}: {!r}'.format(ptask["name"], e))
        print_stderr(f"{traceback.format_exc()}")
        result = False
    if result:
        current_time = datetime.now(tz.tzlocal())
        print_stdout('Task {!r} on node {!r} exited successfully. Noting this '
                     'in the database ...'.format(ptask["name"], node))
        set_periodic_task_last_run(ptask["id"], node, current_time)
    else:
        print_stderr('Task {!r} on node {!r} did not run '
                     'successfully.'.format(ptask["name"], node))
        print_stderr('This unsuccessful run is not recorded in the database.')
        if not ptask.get("retry_if_failed"):
            current_time = datetime.now(tz.tzlocal())
            set_periodic_task_last_run(ptask["id"], node, current_time)
    return result


@click.group(cls=NoPluginsFlaskGroup, create_app=create_silent_app,
             context_settings=CONTEXT_SETTINGS, add_default_commands=False,
             epilog='Check out our docs at https://privacyidea.readthedocs.io/ for more details')
def cli():
    """
\b
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \\/ __/ _ |
  / _ \\/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\\_,_/\\__/\\_, /___/____/___/_/ |_|  Cron
/_/                       /___/

This script is meant to be invoked periodically by the system cron daemon.
It runs periodic tasks that are specified in the database.
"""
    click.echo(r"""
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
  / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|  Cron
/_/                       /___/
{0!s:>51}
    """.format('v{0!s}'.format(get_version_number())))


@cli.command()
@click.option("-n", "--node", "node_string",
              help="Override the node name (read from privacyIDEA config by default)")
@click.option("-t", "--task", "task_name",
              help="Run the specified task",
              required=True)
def run_manually(node_string, task_name):
    """
    Manually run a periodic task.
    BEWARE: This does not check whether the task is active, or whether it should
    run on the given node at all.
    """
    node = get_node_name(node_string)
    ptask = get_periodic_task_by_name(task_name)
    run_task_on_node(ptask, node)


@cli.command("list")
def list_tasks():
    """
    Show a list of available tasks that could be run.
    """
    line_format = ('{active!s:7.7} {id:3} {name:16.16}\t{interval:16.16}\t{taskmodule:16}'
                   '\t{node_list:20}\t{options_json}')
    heading = line_format.format(
        active="Active",
        id="ID",
        name="Name",
        interval="Interval",
        taskmodule="Task Module",
        node_list="Nodes",
        options_json="Options",
    )
    print_stdout(heading)
    print_stdout("=" * 120)
    for ptask in get_periodic_tasks():
        print_stdout(line_format.format(node_list=', '.join(ptask["nodes"]),
                                        options_json=json.dumps(ptask["options"]),
                                        **ptask))


@cli.command()
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
    current_app.config['cron_mode'] = cron_mode
    node = get_node_name(node_string)
    current_time = datetime.now(tz.tzlocal())
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


if __name__ == '__main__':
    cli()
