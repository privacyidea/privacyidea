# -*- coding: utf-8 -*-
#
#  2018-06-26 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             provide first interface to handle monitoring statistics
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
__doc__ = """This module is used to write, read and handle data in the
database table "monitoringstats". This can be arbitrary data for time series of
  
   timestamp, key, value

This module is tested in tests/test_lib_monitoringstats.py
"""
import logging
import traceback
from privacyidea.lib.log import log_with
from privacyidea.models import MonitoringStats
from sqlalchemy import and_, distinct
import datetime
log = logging.getLogger(__name__)


def write_stats(stats_key, stats_value, timestamp=None, reset_values=False):
    """
    Write a new statistics value to the database

    :param stats_key: The key, that identifies the measurment point
    :type stats_key: basestring
    :param stats_value: The value to be measured
    :type stats_value: int
    :param timestamp: The time, when the value was measured
    :param reset_values: Whether old entries should be deleted
    :return: id of the database entry
    """
    timestamp = timestamp or datetime.datetime.now()
    MonitoringStats(timestamp, stats_key, stats_value)
    if reset_values:
        # Successfully saved the new stats entry, so remove old entries
        MonitoringStats.query.filter(and_(MonitoringStats.stats_key == stats_key,
                                          MonitoringStats.timestamp < timestamp)).delete()


def delete_stats(stats_key, start_timestamp=None, end_timestamp=None):
    """
    Delete statistics from a given key.
    Either delete all occurrences or only in a given time span.

    :param stats_key: The name of the key to delete
    :param start_timestamp: The start timestamp.
    :type start_timestamp: datetime
    :param end_timestamp: The end timestamp.
    :type end_timestamp: datetime
    :return: The number of deleted entries
    """
    conditions = [MonitoringStats.stats_key == stats_key]
    if start_timestamp:
        conditions.append(MonitoringStats.timestamp >= start_timestamp)
    if end_timestamp:
        conditions.append(MonitoringStats.timestamp <= end_timestamp)
    r = MonitoringStats.query.filter(and_(*conditions)).delete()
    return r


def get_stats_keys():
    """
    Return a list of all available statistics keys

    :return: list of keys
    """
    keys = []
    for monStat in MonitoringStats.query.with_entities(MonitoringStats.stats_key).distinct():
        keys.append(monStat.stats_key)
    return keys