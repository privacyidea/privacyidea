# -*- coding: utf-8 -*-
#  2018-07-09 Friedrich Weber <friedrich.weber@netknights.it>
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
__doc__ = """These endpoints are used to create, modify and delete
periodic tasks.

This module is tested in tests/test_api_periodictask.py"""

import json
import logging

from flask import Blueprint, g, request, current_app

from privacyidea.lib.config import get_privacyidea_nodes
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.api.lib.utils import send_result, getParam
from privacyidea.lib.error import ParameterError
from privacyidea.lib.policy import ACTION
from privacyidea.lib.log import log_with
from privacyidea.lib.periodictask import get_periodic_tasks, set_periodic_task, delete_periodic_task, \
    enable_periodic_task, get_periodic_task_by_id, get_taskmodule, get_available_taskmodules
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

periodictask_blueprint = Blueprint('periodictask_blueprint', __name__)


def convert_datetimes_to_string(ptask):
    """
    Convert the ``last_update`` and ``last_runs`` timestamps to ISO 8601 strings and return a copy of ``ptask``.

    :param ptask: periodic task dictionary
    :return: a new periodic task dictionary
    """
    ptask = ptask.copy()
    ptask['last_update'] = ptask['last_update'].strftime(AUTH_DATE_FORMAT)
    ptask['last_runs'] = dict((node, timestamp.strftime(AUTH_DATE_FORMAT))
                              for node, timestamp in ptask['last_runs'].items())
    return ptask


@periodictask_blueprint.route('/taskmodules/', methods=['GET'])
@log_with(log)
def list_taskmodules():
    """
    Return a list of task module identifiers.
    """
    taskmodules = get_available_taskmodules()
    g.audit_object.log({"success": True})
    return send_result(taskmodules)


@periodictask_blueprint.route('/nodes/', methods=['GET'])
@log_with(log)
def list_nodes():
    """
    Return a list of available nodes
    """
    nodes = get_privacyidea_nodes()
    g.audit_object.log({"success": True})
    return send_result(nodes)


@periodictask_blueprint.route('/options/<taskmodule>', methods=['GET'])
@log_with(log)
def get_taskmodule_options(taskmodule):
    """
    Return the available options for the given taskmodule.

    :param taskmodule: Identifier of the task module
    :return: a dictionary mapping option keys to description dictionaries
    """
    options = get_taskmodule(taskmodule).options
    g.audit_object.log({"success": True})
    return send_result(options)


@periodictask_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.PERIODICTASKREAD)
def list_periodic_tasks():
    """
    Return a list of objects of defined periodic tasks.
    """
    ptasks = get_periodic_tasks()
    result = [convert_datetimes_to_string(ptask) for ptask in ptasks]
    g.audit_object.log({"success": True})
    return send_result(result)


@periodictask_blueprint.route('/<ptaskid>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.PERIODICTASKREAD)
def get_periodic_task_api(ptaskid):
    """
    Return the dictionary describing a periodic task.

    :param ptaskid: ID of the periodic task
    """
    ptask = get_periodic_task_by_id(int(ptaskid))
    g.audit_object.log({"success": True})
    return send_result(convert_datetimes_to_string(ptask))


@periodictask_blueprint.route('/', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.PERIODICTASKWRITE)
@log_with(log)
def set_periodic_task_api():
    """
    Create or replace an existing periodic task definition.

    :param id: ID of an existing periodic task definition that should be updated
    :param name: Name of the periodic task
    :param active: true if the periodic task should be active
    :param retry_if_failed: privacyIDEA will retry to execute the task if failed
    :param interval: Interval at which the periodic task should run (in cron syntax)
    :param nodes: Comma-separated list of nodes on which the periodic task should run
    :param taskmodule: Task module name of the task
    :param ordering: Ordering of the task, must be a number >= 0.
    :param options: A dictionary (possibly JSON) of periodic task options, mapping unicodes to unicodes
    :return: ID of the periodic task
    """
    param = request.all_data
    ptask_id = getParam(param, "id", optional=True)
    if ptask_id is not None:
        ptask_id = int(ptask_id)
    name = getParam(param, "name", optional=False)
    active = is_true(getParam(param, "active", default=True))
    retry_if_failed = is_true(getParam(param, "retry_if_failed", default=True))
    interval = getParam(param, "interval", optional=False)
    node_string = getParam(param, "nodes", optional=False)
    if node_string.strip():
        node_list = [node.strip() for node in node_string.split(",")]
    else:
        raise ParameterError("nodes: expected at least one node")
    taskmodule = getParam(param, "taskmodule", optional=False)
    if taskmodule not in get_available_taskmodules():
        raise ParameterError("Unknown task module: {!r}".format(taskmodule))
    ordering = int(getParam(param, "ordering", optional=False))
    options = getParam(param, "options", optional=True)
    if options is None:
        options = {}
    elif not isinstance(options, dict):
        options = json.loads(options)
        if not isinstance(options, dict):
            raise ParameterError("options: expected dictionary, got {!r}".format(options))
    result = set_periodic_task(name, interval, node_list, taskmodule, ordering, options, active, ptask_id,
                               retry_if_failed)
    g.audit_object.log({"success": True, "info": result})
    return send_result(result)


@periodictask_blueprint.route('/enable/<ptaskid>', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.PERIODICTASKWRITE)
@log_with(log)
def enable_periodic_task_api(ptaskid):
    """
    Enable a certain periodic task.

    :param ptaskid: ID of the periodic task
    :return: ID of the periodic task
    """
    result = enable_periodic_task(int(ptaskid), True)
    g.audit_object.log({"success": True})
    return send_result(result)


@periodictask_blueprint.route('/disable/<ptaskid>', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.PERIODICTASKWRITE)
@log_with(log)
def disable_periodic_task_api(ptaskid):
    """
    Disable a certain periodic task.

    :param ptaskid: ID of the periodic task
    :return: ID of the periodic task
    """
    result = enable_periodic_task(int(ptaskid), False)
    g.audit_object.log({"success": True})
    return send_result(result)


@periodictask_blueprint.route('/<ptaskid>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.PERIODICTASKWRITE)
@log_with(log)
def delete_periodic_task_api(ptaskid):
    """
    Delete a certain periodic task.

    :param ptaskid: ID of the periodic task
    :return: ID of the periodic task
    """
    result = delete_periodic_task(int(ptaskid))
    g.audit_object.log({"success": True, "info": result})
    return send_result(result)