# -*- coding: utf-8 -*-
#  2018-06-25 Friedrich Weber <friedrich.weber@netknights.it>
#             Initial implementation of periodic tasks
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
__doc__ = """This module provides functions to manage periodic tasks in the database,
to determine their next scheduled running time and to run them."""

from datetime import datetime

from croniter import croniter
from dateutil.tz import tzutc

from privacyidea.lib.error import ServerError


def calculate_next_timestamp(ptask, node):
    """
    Calculate the timestamp of the next scheduled run of task ``ptask`` on node ``node``.
    We do not check if the task is even scheduled to run on the specified node.
    If the periodic task has no prior run recorded on the specified node, a
    ``ServerError`` is thrown. Malformed cron expressions may throw a
    ``ValueError``.

    :param ptask: Dictionary describing the periodic task, as from ``PeriodicTask.get()``
    :param node: Node on which the periodic task is scheduled
    :type node: unicode
    :return: a timezone-aware (UTC) datetime object
    """
    if node not in ptask["last_runs"]:
        raise ServerError("No last run on node {!r} recorded for task {!r}".format(node, ptask["name"]))
    # This will be a UTC timestamp
    assert ptask["last_runs"][node].tzinfo is None
    iterator = croniter(ptask["interval"], ptask["last_runs"][node])
    next_timestamp = iterator.get_next(datetime)
    # This will again be a UTC timestamp, but we return a timezone-aware UTC timestamp
    return next_timestamp.replace(tzinfo=tzutc())
