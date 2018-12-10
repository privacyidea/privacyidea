# -*- coding: utf-8 -*-
#
#  2018-11-22 Initial create
#             Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
__doc__ = """This is the BaseClass for monitoring statistics data.

The monitoring database is a time series database. It is supposed to store
tuples of (timestamp, status key, status value)

A monitoring module needs to provide the possibility to write new data,
return all available keys, return the last data. 
"""
import logging
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with


class Monitoring(object):

    def __init__(self, config=None):
        pass

    def get_keys(self):
        """
        Return a list of the available statistic keys.

        :return: list of identifiers
        """
        return []

    def get_values(self, stats_key, start_timestamp=None, end_timestamp=None):
        """
        Return a list of tuples of (timestamp, value) for the requested stats_key.

        :param stats_key: Identifier of the stats
        :param start_timestamp: start of the time frame
        :type start_timestamp: timezone aware datetime
        :param end_timestamp:  end of the time frame
        :type end_timestamp: timezone aware datetime
        :return:
        """
        return []

    def get_last_value(self, stats_key):
        """
        returns the last value of the given stats_key in time.
        :param stats_key: The identifier of the stats
        :return: a string value.
        """
        pass

    def delete(self, stats_key, start_timestamp, end_timestamp):
        """
        Delete all entries of the stats_key for the given time frame.
        The start_timestamp and end_timestamp are also deleted.

        :param stats_key: Identifier of the stats
        :param start_timestamp: beginning of the time frame
        :type start_timestamp: timezone aware datetime
        :param end_timestamp: end of the time frame
        :type end_timestamp: timezone aware datetime
        :return: number of deleted entries
        """
        return 0

    def add_value(self, stats_key, stats_value, timestamp, reset_values=False):
        """
        This method adds a measurement point to the statistics key "stats_key".
        If reset_values is set to True, all old values of this stats_key are deleted.

        :param stats_key: Identifier of the stats
        :param stats_value: measured value
        :param timestamp: the timestamp of the measurement
        :type timestamp: timezone aware datetime
        :param reset_values: boolean to indicate the reset
        :return: None
        """
        pass




