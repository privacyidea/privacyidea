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
from dateutil.tz import tzlocal
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import get_module_class
from privacyidea.lib.framework import get_app_config, get_request_local_store
import datetime

log = logging.getLogger(__name__)


@log_with(log, log_entry=False)
def _get_monitoring():
    """
    This wrapper function creates a new monitoring object based on the config
    from the config file. The config file entry could look like this:

        PI_MONITORING_MODULE = privacyidea.lib.monitoringmodule.sqlstats

    Each monitoring module can have its own config values.

    :return: Monitoring Object
    """
    store = get_request_local_store()
    # check if the monitoring object is not yet in this request_store
    if 'monitoring_object' not in store:
        config = get_app_config()
        monitoring_module = config.get("PI_MONITORING_MODULE", "privacyidea.lib.monitoringmodules.sqlstats")
        monitoring = get_module_class(monitoring_module, "Monitoring")(config)
        store['monitoring_object'] = monitoring
    return store.get('monitoring_object')


def write_stats(stats_key, stats_value, timestamp=None, reset_values=False):
    """
    Write a new statistics value to the database

    :param stats_key: The key, that identifies the measurement point
    :type stats_key: basestring
    :param stats_value: The value to be measured
    :type stats_value: int
    :param timestamp: The time, when the value was measured
    :type timestamp: timezone-aware datetime object
    :param reset_values: Whether old entries should be deleted
    :return: id of the database entry
    """
    timestamp = timestamp or datetime.datetime.now(tzlocal())
    monitoring_obj = _get_monitoring()
    monitoring_obj.add_value(stats_key, stats_value, timestamp, reset_values)


def delete_stats(stats_key, start_timestamp=None, end_timestamp=None):
    """
    Delete statistics from a given key.
    Either delete all occurrences or only in a given time span.

    :param stats_key: The name of the key to delete
    :param start_timestamp: The start timestamp.
    :type start_timestamp: timezone-aware datetime object
    :param end_timestamp: The end timestamp.
    :type end_timestamp: timezone-aware datetime object
    :return: The number of deleted entries
    """
    monitoring_obj = _get_monitoring()
    r = monitoring_obj.delete(stats_key, start_timestamp, end_timestamp)
    return r


def get_stats_keys():
    """
    Return a list of all available statistics keys

    :return: list of keys
    """
    monitoring_obj = _get_monitoring()
    return monitoring_obj.get_keys()


def get_values(stats_key, start_timestamp=None, end_timestamp=None):
    """
    Return a list of sets of (timestamp, value), ordered by timestamps in ascending order

    :param stats_key: The stats key to query
    :param start_timestamp: the start of the timespan, inclusive
    :type start_timestamp: timezone-aware datetime object
    :param end_timestamp: the end of the timespan, inclusive
    :type end_timestamp: timezone-aware datetime object
    :return: list of tuples, with timestamps being timezone-aware UTC datetime objects
    """
    monitoring_obj = _get_monitoring()
    return monitoring_obj.get_values(stats_key, start_timestamp, end_timestamp)


def get_last_value(stats_key):
    """
    Return the last value of the given key

    :param stats_key:
    :return: The value as a scalar or None
    """
    monitoring_obj = _get_monitoring()
    return monitoring_obj.get_last_value(stats_key)

