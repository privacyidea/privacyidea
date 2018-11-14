# -*- coding: utf-8 -*-
#  2018-11-14 Friedrich Weber <friedrich.weber@netknights.it>
#             Add a task queue
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
#

from privacyidea.app import create_app
from privacyidea.lib.queue import register_app, get_task_queue
from privacyidea.lib.queue.huey import HueyQueue

app = create_app(config_name='production')

with app.app_context():
    queue = get_task_queue()
    if not isinstance(queue, HueyQueue):
        raise NotImplementedError("{!r} is not a HueyQueue".format(queue))

huey = queue.huey