# -*- coding: utf-8 -*-
#  2018-08-09 Friedrich Weber <friedrich.weber@netknights.it>
#             Hello Task
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
import logging
from privacyidea.lib.task.base import BaseTask

__doc__ = """This is a simple test task which only writes to the log."""

log = logging.getLogger(__name__)

class HelloTask(BaseTask):
    identifier = "Hello"
    description = "Write an arbitrary message to the log."

    @property
    def options(self):
        return {
            "message": {
                "type": "str",
                "description": "Message to print to the log"
            }
        }

    def do(self, params):
        msg = params.get("message", "Hello World!")
        log.info(msg)
        return True
