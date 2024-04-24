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

import json

from flask.cli import AppGroup

from privacyidea.cli.privacyidea_cron.utils import print_stdout
from privacyidea.lib.periodictask import get_periodic_tasks

list_cli = AppGroup("list", help="Show a list of available tasks that could be run.")


@list_cli.command("run_manually")
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
