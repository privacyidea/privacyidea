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

from flask.cli import AppGroup
import click

from privacyidea.lib.periodictask import (get_periodic_task_by_name)
from privacyidea.cli.privacyidea_cron.utils import (get_node_name, run_task_on_node)

run_manually_cli = AppGroup("run_manually", help="Manually run a periodic task")


@run_manually_cli.command("run_manually")
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
