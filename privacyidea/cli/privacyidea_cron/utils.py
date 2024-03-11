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

import sys
from datetime import datetime

import dateutil

from privacyidea.app import create_app
from privacyidea.lib.config import get_privacyidea_node
from privacyidea.lib.periodictask import (execute_task, set_periodic_task_last_run)


app = create_app(config_name='production', silent=True)


def print_stdout(*args, **kwargs):
    """
    Print to stdout, except if "cron mode" has been activated.
    """
    if not app.config.get("cron_mode", False):
        print(*args, **kwargs)


def print_stderr(*args, **kwargs):
    """
    Print to stderr.
    """
    print(*args, file=sys.stderr, **kwargs)


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
        print_stdout("Running {!r} ...".format(ptask["name"]), end="")
        result = execute_task(ptask["taskmodule"], ptask["options"])
    except Exception as e:
        print_stderr('Caught exception when running {!r}: {!r}'.format(ptask["name"], e))
        result = False
    if result:
        current_time = datetime.now(dateutil.tz.tzlocal())
        print_stdout('Task {!r} on node {!r} exited successfully. Noting this '
                     'in the database ...'.format(ptask["name"], node))
        set_periodic_task_last_run(ptask["id"], node, current_time)
    else:
        print_stderr('Task {!r} on node {!r} did not run '
                     'successfully.'.format(ptask["name"], node))
        print_stderr('This unsuccessful run is not recorded in the database.')
        if not ptask.get("retry_if_failed"):
            current_time = datetime.now(dateutil.tz.tzlocal())
            set_periodic_task_last_run(ptask["id"], node, current_time)
    return result
