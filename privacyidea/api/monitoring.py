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
The monitoring REST API exposes time-series statistics that privacyIDEA
collects via its monitoring module (e.g. token counts, success/failure
rates, audit volume). Which keys are available depends on the active
monitoring module (see :ref:`monitoring_modules`) and on event handlers
that emit ``Counter`` actions.

All endpoints require admin authentication. Reading is gated by the
admin policy action :ref:`policy_statistics_read`, deletion by
:ref:`policy_statistics_delete`.
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
from privacyidea.lib.policies.actions import PolicyAction

log = logging.getLogger(__name__)


monitoring_blueprint = Blueprint('monitoring_blueprint', __name__)


@monitoring_blueprint.route('/', methods=['GET'])
@monitoring_blueprint.route('/<stats_key>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.STATISTICSREAD)
def get_statistics(stats_key=None):
    """
    Return statistics from the monitoring store. The behavior depends on
    whether ``stats_key`` is given as a path component:

    * without a key — return the list of all statistics keys currently
      stored on the server.
    * with a key — return a list of ``[timestamp, value]`` pairs for that
      key, ordered by timestamp ascending. Timestamps are strings in the
      format ``%Y-%m-%d %H:%M:%S.%f%z``.

    The ``start`` and ``end`` query parameters restrict the time window
    (inclusive on both ends). Always send timezone-aware datetimes; otherwise
    the server will interpret naive timestamps as its own local time, which
    typically yields unexpected results. Example: ``2010-12-31 22:00+0200``.

    Requires admin authentication and the policy action :ref:`policy_statistics_read`.

    :param stats_key: optional path component selecting a single key.
    :query start: lower bound of the time window (timezone-aware).
    :query end: upper bound of the time window (timezone-aware).
    :status 200: list of keys, or list of ``[timestamp, value]`` pairs.
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
@prepolicy(check_base_action, request, PolicyAction.STATISTICSDELETE)
def delete_statistics(stats_key):
    """
    Delete entries for the given statistics key. Without ``start`` or ``end``,
    all entries for the key are removed; otherwise only entries within the
    given time window are deleted.

    Always send timezone-aware datetimes for ``start`` / ``end``. If they
    are sent without a timezone, the server will interpret them as its own
    local time, which typically yields unexpected deletions. Example:
    ``2010-12-31 22:00+0200``.

    Requires admin authentication and the policy action :ref:`policy_statistics_delete`.

    :param stats_key: path component, the key whose data should be deleted.
    :query start: lower bound of the time window (timezone-aware, inclusive).
    :query end: upper bound of the time window (timezone-aware, inclusive).
    :status 200: number of deleted entries in ``result.value``.
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
@prepolicy(check_base_action, request, PolicyAction.STATISTICSREAD)
def get_statistics_last(stats_key):
    """
    Return the most recent value stored for the given statistics key.

    Requires admin authentication and the policy action :ref:`policy_statistics_read`.

    :param stats_key: path component, the key to query.
    :status 200: the scalar value in ``result.value``, or ``null`` if no
        data exists for the key.
    """
    last_value = get_last_value(stats_key)
    g.audit_object.log({"success": True})
    return send_result(last_value)

