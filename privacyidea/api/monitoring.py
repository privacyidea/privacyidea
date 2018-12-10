# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
#
# 2018-08-01 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            Initial writeup
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
"""
This endpoint is used fetch monitoring/statistics data

The code of this module is tested in tests/test_api_monitoring.py
"""
from flask import (Blueprint, request)
from privacyidea.api.lib.utils import getParam, send_result
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.lib.utils import parse_legacy_time
from privacyidea.lib.log import log_with
from privacyidea.lib.monitoringstats import (get_stats_keys, get_values,
                                   get_last_value, delete_stats)
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT
from flask import g
import logging
from privacyidea.lib.policy import ACTION


log = logging.getLogger(__name__)


monitoring_blueprint = Blueprint('monitoring_blueprint', __name__)


@monitoring_blueprint.route('/', methods=['GET'])
@monitoring_blueprint.route('/<stats_key>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.STATISTICSREAD)
def get_statistics(stats_key=None):
    """
    return a list of all available statistics keys in the database if no *stats_key*
    is specified.

    If a stats_key is specified it returns the data of this key.
    The parameters "start" and "end" can be used to specify a time window,
    from which the statistics data should be fetched.
    """
    if stats_key is None:
        stats_keys = get_stats_keys()
        g.audit_object.log({"success": True})
        return send_result(stats_keys)
    else:
        param = request.all_data
        start = getParam(param, "start")
        if start:
            start = parse_legacy_time(start, return_date=True)
        end = getParam(param, "end")
        if end:
            end = parse_legacy_time(end, return_date=True)
        values = get_values(stats_key=stats_key, start_timestamp=start, end_timestamp=end)
        # convert timestamps to strings
        values_w_string = [(s[0].strftime(AUTH_DATE_FORMAT), s[1]) for s in values]
        g.audit_object.log({"success": True})
        return send_result(values_w_string)


@monitoring_blueprint.route('/<stats_key>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.STATISTICSDELETE)
def delete_statistics(stats_key):
    """
    Delete the statistics data of a certain stats_key.

    You can specify the start date and the end date when to delete the
    monitoring data.
    You should specify the dates including the timezone. Otherwise your client
    could send its local time and the server would interpret it as its own local
    time which would result in deleting unexpected entries.

    You can specify the dates like 2010-12-31 22:00+0200
    """
    param = request.all_data
    start = getParam(param, "start")
    if start:
        start = parse_legacy_time(start, return_date=True)
    end = getParam(param, "end")
    if end:
        end = parse_legacy_time(end, return_date=True)
    r = delete_stats(stats_key, start, end)
    g.audit_object.log({"success": True})
    return send_result(r)


@monitoring_blueprint.route('/<stats_key>/last', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.STATISTICSREAD)
def get_statistics_last(stats_key):
    """
    Get the last value of the stats key
    """
    last_value = get_last_value(stats_key)
    g.audit_object.log({"success": True})
    return send_result(last_value)

