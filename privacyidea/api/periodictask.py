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
__doc__ = """
The periodic-tasks REST API manages scheduled jobs that privacyIDEA
runs on its own nodes (cleanup tasks, statistics aggregation, expiring
tokens, ...). See :ref:`periodic_tasks` for the conceptual chapter.

All endpoints require admin authentication. Read access for the task
list, individual task definitions and the lookup endpoints (available
task modules, configured nodes, per-module option schemas) is gated by
the admin policy action :ref:`policy_periodictask_read`; create,
update, enable, disable and delete are gated by
:ref:`policy_periodictask_write`.
"""

from flask_babel import _
import json
import logging

from flask import Blueprint, g, request

from privacyidea.lib.config import get_privacyidea_node_names
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.api.lib.utils import send_result, getParam
from privacyidea.lib.error import ParameterError
from privacyidea.lib.policies.actions import PolicyAction
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
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKREAD)
def list_taskmodules():
    """
    Return the list of task module identifiers known to this server.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_read`.

    :status 200: list of task module names in ``result.value``.
    """
    taskmodules = get_available_taskmodules()
    g.audit_object.log({"success": True})
    return send_result(taskmodules)


@periodictask_blueprint.route('/nodes/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKREAD)
def list_nodes():
    """
    Return the list of privacyIDEA node names declared in the server
    configuration. Periodic tasks are scheduled per node — only nodes
    listed here can be assigned to a task.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_read`.

    :status 200: list of node names in ``result.value``.
    """
    nodes = get_privacyidea_node_names()
    g.audit_object.log({"success": True})
    return send_result(nodes)


@periodictask_blueprint.route('/options/<taskmodule>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKREAD)
def get_taskmodule_options(taskmodule):
    """
    Return the option schema for a given task module: a dictionary mapping
    each option key to a description dictionary that the WebUI uses to
    render the per-task configuration form.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_read`.

    :param taskmodule: path component, the task module identifier.
    :status 200: dict of option descriptors in ``result.value``.
    """
    options = get_taskmodule(taskmodule).options
    g.audit_object.log({"success": True})
    return send_result(options)


@periodictask_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKREAD)
def list_periodic_tasks():
    """
    Return all periodic task definitions. Each entry includes its schedule,
    the nodes it runs on, the task module, the per-module options, and
    ``last_update`` / ``last_runs`` timestamps formatted as
    ``%Y-%m-%d %H:%M:%S.%f%z``.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_read`.

    :status 200: list of periodic task dictionaries in ``result.value``.
    """
    ptasks = get_periodic_tasks()
    result = [convert_datetimes_to_string(ptask) for ptask in ptasks]
    g.audit_object.log({"success": True})
    return send_result(result)


@periodictask_blueprint.route('/<ptaskid>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKREAD)
def get_periodic_task_api(ptaskid):
    """
    Return the dictionary describing a single periodic task.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_read`.

    :param ptaskid: path component, the numeric id of the periodic task.
    :status 200: periodic task dictionary in ``result.value``.
    :status 404: no periodic task with that id exists.
    """
    ptask = get_periodic_task_by_id(int(ptaskid))
    g.audit_object.log({"success": True})
    return send_result(convert_datetimes_to_string(ptask))


@periodictask_blueprint.route('/', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKWRITE)
@log_with(log)
def set_periodic_task_api():
    """
    Create or update a periodic task definition. Pass an existing ``id``
    to update; omit it to create a new task.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_write`.

    :jsonparam id: id of an existing task to update; omit to create.
    :jsonparam name: human-readable name of the task (required).
    :jsonparam active: ``True`` (default) to enable the task, ``False`` to
        create it disabled.
    :jsonparam retry_if_failed: ``True`` (default) to retry the task if
        a run fails.
    :jsonparam interval: cron-style schedule string (required).
    :jsonparam nodes: comma-separated list of node names the task runs on
        (required, must be non-empty).
    :jsonparam taskmodule: task module identifier (required); must be
        listed in :http:get:`/periodictask/taskmodules/`.
    :jsonparam ordering: integer >= 0; tasks with lower ordering run first.
    :jsonparam options: dictionary of task-module-specific options (or a
        JSON-encoded string of one).
    :status 200: id of the task in ``result.value``.
    :status 400: ``nodes`` is empty, ``taskmodule`` is unknown, or
        ``options`` is not a dictionary.
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
        raise ParameterError(_("nodes: expected at least one node"))
    taskmodule = getParam(param, "taskmodule", optional=False)
    if taskmodule not in get_available_taskmodules():
        raise ParameterError(_("Unknown task module: {!r}").format(taskmodule))
    ordering = int(getParam(param, "ordering", optional=False))
    options = getParam(param, "options", optional=True)
    if options is None:
        options = {}
    elif not isinstance(options, dict):
        options = json.loads(options)
        if not isinstance(options, dict):
            raise ParameterError(_("options: expected dictionary, got {!r}").format(options))
    result = set_periodic_task(name, interval, node_list, taskmodule, ordering, options, active, ptask_id,
                               retry_if_failed)
    g.audit_object.log({"success": True, "info": result})
    return send_result(result)


@periodictask_blueprint.route('/enable/<ptaskid>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKWRITE)
@log_with(log)
def enable_periodic_task_api(ptaskid):
    """
    Enable a periodic task. The task will run according to its configured
    schedule on its assigned nodes from the next scheduling tick onwards.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_write`.

    :param ptaskid: path component, the numeric id of the periodic task.
    :status 200: id of the task in ``result.value``.
    :status 404: no periodic task with that id exists.
    """
    result = enable_periodic_task(int(ptaskid), True)
    g.audit_object.log({"success": True})
    return send_result(result)


@periodictask_blueprint.route('/disable/<ptaskid>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKWRITE)
@log_with(log)
def disable_periodic_task_api(ptaskid):
    """
    Disable a periodic task. The task definition is preserved but no new
    runs are scheduled until it is enabled again.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_write`.

    :param ptaskid: path component, the numeric id of the periodic task.
    :status 200: id of the task in ``result.value``.
    :status 404: no periodic task with that id exists.
    """
    result = enable_periodic_task(int(ptaskid), False)
    g.audit_object.log({"success": True})
    return send_result(result)


@periodictask_blueprint.route('/<ptaskid>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.PERIODICTASKWRITE)
@log_with(log)
def delete_periodic_task_api(ptaskid):
    """
    Delete a periodic task definition.

    Requires admin authentication and the policy action
    :ref:`policy_periodictask_write`.

    :param ptaskid: path component, the numeric id of the periodic task.
    :status 200: id of the deleted task in ``result.value``.
    :status 404: no periodic task with that id exists.
    """
    result = delete_periodic_task(int(ptaskid))
    g.audit_object.log({"success": True, "info": result})
    return send_result(result)
