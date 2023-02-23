# -*- coding: utf-8 -*-
#  2018-08-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             EventCounter Task
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
from privacyidea.lib.monitoringstats import write_stats
from privacyidea.lib.counter import reset, read
from privacyidea.lib.utils import is_true
from privacyidea.lib import _


__doc__ = """This task module reads event counters and writes them to the 
MonitoringStats database table."""

log = logging.getLogger(__name__)


class EventCounterTask(BaseTask):
    identifier = "EventCounter"
    description = "Write snapshots of the event counter to the MonitoringStats table."

    @property
    def options(self):
        return {
            "event_counter": {
                "type": "str",
                "description": _("The name of the event counter to read."),
                "required": True
            },
            "stats_key": {
                "type": "str",
                "description": _("The name of the stats key to write to the MonitoringStats "
                                 "table."),
                "required": True
            },
            "reset_event_counter": {
                "type": "bool",
                "description": _("Whether to reset the event_counter, if it is read and written "
                                 "to the MonitoringStats table.")
            }

        }

    def do(self, params):
        event_counter = params.get("event_counter")
        stats_key = params.get("stats_key")
        reset_event_counter = params.get("reset_event_counter")

        counter_value = read(event_counter)
        if is_true(reset_event_counter) and counter_value:
            reset(event_counter)

        # now write the current value of the counter
        if counter_value is None:
            log.warning("Trying to create statistics of a counter_value '{0}', "
                        "that does not exist.".format(event_counter))
        else:
            write_stats(stats_key, counter_value)

        return True

