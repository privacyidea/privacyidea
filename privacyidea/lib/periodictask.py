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

import logging
from datetime import datetime
from privacyidea.lib.tokenclass import DATE_FORMAT

from croniter import croniter
from dateutil.tz import tzutc, tzlocal

from privacyidea.lib.error import ParameterError, ResourceNotFoundError
from privacyidea.lib.utils import fetch_one_resource, parse_date
from privacyidea.lib.task.eventcounter import EventCounterTask
from privacyidea.lib.task.simplestats import SimpleStatsTask
from privacyidea.models import PeriodicTask
from privacyidea.lib.framework import get_app_config
from privacyidea.lib.utils.export import (register_import, register_export)

log = logging.getLogger(__name__)

TASK_CLASSES = [EventCounterTask, SimpleStatsTask]
#: TASK_MODULES maps task module identifiers to subclasses of BaseTask
TASK_MODULES = dict((cls.identifier, cls) for cls in TASK_CLASSES)


def get_available_taskmodules():
    """
    Return a list of all available task module identifiers.
    :return: a list of strings
    """
    return list(TASK_MODULES.keys())


def get_taskmodule(identifier, config=None):
    """
    Return an instance of the given task module. Raise ParameterError if it does not exist.
    :param identifier: identifier of the task module
    :return: instance of a BaseTask subclass
    """
    if identifier not in TASK_MODULES:
        raise ParameterError("Unknown task module: {!r}".format(identifier))
    else:
        r = TASK_MODULES[identifier](config=get_app_config())
        return r


def calculate_next_timestamp(ptask, node, interval_tzinfo=None):
    """
    Calculate the timestamp of the next scheduled run of task ``ptask`` on node ``node``.
    We do not check if the task is even scheduled to run on the specified node.
    Malformed cron expressions may throw a ``ValueError``.

    The next timestamp is calculated based on the last time the task was run on the given node.
    If the task has never run on the node, the last update timestamp of the periodic tasks
    is used as a reference timestamp.

    :param ptask: Dictionary describing the periodic task, as from ``PeriodicTask.get()``
    :param node: Node on which the periodic task is scheduled
    :type node: unicode
    :param interval_tzinfo: Timezone in which the cron expression should be interpreted. Defaults to local time.
    :type interval_tzinfo: tzinfo
    :return: a timezone-aware (UTC) datetime object
    """
    if interval_tzinfo is None:
        interval_tzinfo = tzlocal()
    timestamp = ptask["last_runs"].get(node, ptask["last_update"])
    local_timestamp = timestamp.astimezone(interval_tzinfo)
    iterator = croniter(ptask["interval"], local_timestamp)
    next_timestamp = iterator.get_next(datetime)
    # This will again be a timezone-aware datetime, but we return a timezone-aware UTC timestamp
    return next_timestamp.astimezone(tzutc())


def set_periodic_task(name=None, interval=None, nodes=None, taskmodule=None,
                      ordering=0, options=None, active=True, id=None,
                      retry_if_failed=True):
    """
    Set a periodic task configuration. If ``id`` is None, this creates a new database entry.
    Otherwise, an existing entry is overwritten. We actually ensure that such
    an entry exists and throw a ``ParameterError`` otherwise.

    This also checks if ``interval`` is a valid cron expression, and throws
    a ``ParameterError`` if it is not.

    :param name: Unique name of the periodic task
    :type name: unicode
    :param interval: Periodicity as a string in crontab format
    :type interval: unicode
    :param nodes: List of nodes on which this task should be run
    :type nodes: list of unicode
    :param taskmodule: Name of the task module
    :type taskmodule: unicode
    :param ordering: Ordering of the periodic task (>= 0). Lower numbers are executed first.
    :type ordering: int
    :param options: Additional options for the task module
    :type options: Dictionary mapping unicodes to values that can be converted to unicode or None
    :param active: Flag determining whether the periodic task is active
    :type active: bool
    :param retry_if_failed: true if privacyidea should retry to execute this periodic task if it fails
                            false if privacyidea should just try onetime regardless the failing of the task
    :type retry_if_failed: bool
    :param id: ID of the existing entry, or None
    :type id: int or None
    :return: ID of the entry
    """
    try:
        croniter(interval)
    except ValueError as e:
        raise ParameterError("Invalid interval: {!s}".format(e))
    if ordering < 0:
        raise ParameterError("Invalid ordering: {!s}".format(ordering))
    if id is not None:
        # This will throw a ParameterError if there is no such entry
        get_periodic_task_by_id(id)
    periodic_task = PeriodicTask(name, active, interval, nodes, taskmodule,
                                 ordering, options, id, retry_if_failed)
    return periodic_task.id


def delete_periodic_task(ptask_id):
    """
    Delete an existing periodic task. If ``ptask_id`` refers to an unknown entry, a ParameterError is raised.
    :param ptask_id: ID of the database entry
    :return: ID of the deleted entry
    """
    periodic_task = _get_periodic_task_entry(ptask_id)
    return periodic_task.delete()


def enable_periodic_task(ptask_id, enable=True):
    """
    Set the ``active`` flag of an existing periodic task to ``enable``.
    If ``ptask_id`` refers to an unknown entry, a ParameterError is raised.
    :param ptask_id: ID of the database entry
    :param enable: New value of the ``active`` flag
    :return: ID of the database entry
    """
    periodic_task = _get_periodic_task_entry(ptask_id)
    periodic_task.active = enable
    return periodic_task.save()


def get_periodic_tasks(name=None, node=None, active=None):
    """
    Get a list of all periodic tasks, or of all tasks satisfying a filter criterion,
    ordered by their ordering value (ascending).

    :param name: Name of the periodic task
    :type name: unicode
    :param node: Node for which periodic tasks should be collected. This only includes
                 periodic tasks which are scheduled to run on ``node``.
    :type node: unicode
    :param active: This can be used to filter for active or inactive tasks only
    :return: A (possibly empty) list of periodic task dictionaries
    """
    query = PeriodicTask.query
    if name is not None:
        query = query.filter_by(name=name)
    if active is not None:
        query = query.filter_by(active=active)
    entries = query.order_by(PeriodicTask.ordering).all()
    result = []
    for entry in entries:
        ptask = entry.get()
        if node is None or node in ptask["nodes"]:
            result.append(ptask)
    return result


def get_periodic_task_by_name(name):
    """
    Get a periodic task by name. Raise ParameterError if the task could not be found.
    :param name: task name, unicode
    :return: dictionary
    """
    periodic_tasks = get_periodic_tasks(name)
    if len(periodic_tasks) != 1:
        raise ResourceNotFoundError("The periodic task with unique name {!r} does not exist".format(name))
    return periodic_tasks[0]


def get_periodic_task_by_id(ptask_id):
    """
    Get a periodic task entry by ID and return it as a dictionary.
    Raise ParameterError if the task could not be found.
    :param ptask_id: task ID as integer
    :return: dictionary
    """
    return _get_periodic_task_entry(ptask_id).get()


def _get_periodic_task_entry(ptask_id):
    """
    Get a periodic task entry by ID. Raise ResourceNotFoundError if the task could not be found.
    This is only for internal use.
    :param id: task ID as integer
    :return: PeriodicTask object
    """
    return fetch_one_resource(PeriodicTask, id=ptask_id)


def set_periodic_task_last_run(ptask_id, node, last_run_timestamp):
    """
    Write to the database the information that the specified
    periodic task has been run on a node at a given time.
    :param ptask_id: ID of the periodic task. Raises ParameterError if unknown.
    :type ptask_id: int
    :param node: Node name. It is not checked whether the task is scheduled to run on that node!
    :type node: unioode
    :param last_run_timestamp: Timestamp of the last run
    :type last_run_timestamp: timezone-aware datetime object
    """
    periodic_task = _get_periodic_task_entry(ptask_id)
    utc_last_run = last_run_timestamp.astimezone(tzutc()).replace(tzinfo=None)
    periodic_task.set_last_run(node, utc_last_run)


def get_scheduled_periodic_tasks(node, current_timestamp=None, interval_tzinfo=None):
    """
    Collect all periodic tasks that should be run on a specific node, ordered by
    their ordering.

    This function is usually called by the local cron runner which is aware of the
    current local node name.

    :param node: Node name
    :type node: unicode
    :param current_timestamp: The current timestamp, defaults to the current time
    :type current_timestamp: timezone-aware datetime
    :param interval_tzinfo: timezone in which the crontab expression should be interpreted
    :type interval_tzinfo: tzinfo, defaults to local time
    :return: List of periodic task dictionaries
    """
    active_ptasks = get_periodic_tasks(node=node, active=True)
    if current_timestamp is None:
        current_timestamp = datetime.now(tzutc())
    if current_timestamp.tzinfo is None:
        raise ParameterError("expected timezone-aware datetime, got {!r}".format(current_timestamp))
    scheduled_ptasks = []
    log.debug("Collecting periodic tasks to run at {!s}".format(current_timestamp.isoformat()))
    for ptask in active_ptasks:
        try:
            next_timestamp = calculate_next_timestamp(ptask, node, interval_tzinfo)
            log.debug("Next scheduled run of {!r}: {!s}".format(ptask["name"], next_timestamp.isoformat()))
            if next_timestamp <= current_timestamp:
                log.debug("Scheduling periodic task {!r}".format(ptask["name"]))
                scheduled_ptasks.append(ptask)
        except Exception as e:
            log.warning("Ignoring periodic task {!r}: {!r}".format(ptask["name"], e))
    return scheduled_ptasks


def execute_task(taskmodule, params):
    """
    Given a task module name, run the task with the given parameters.
    :param config: The app configuration
    :param taskmodule: unicode determining the task module
    :param params: dictionary mapping task option keys (unicodes) to unicodes (or None)
    :return: boolean returned by the task
    """
    module = get_taskmodule(taskmodule)
    log.info("Running taskmodule {!r} with parameters {!r}".format(module, params))
    return module.do(params)


@register_export('periodictask')
def export_periodictask(name=None):
    """ Export given or all machineresolver configuration """
    periodictask_list = get_periodic_tasks(name=name)
    # last_update is not required for import, but used here for completeness
    for task in periodictask_list:
        last_update = task.get('last_update')
        task['last_update'] = last_update.strftime(DATE_FORMAT)

    return periodictask_list


@register_import('periodictask')
def import_periodictask(data, name=None):
    """Import periodictask configuration"""
    log.debug('Import periodictask config: {0!s}'.format(data))
    for res_data in data:
        if name and name != res_data.get('name'):
            continue
        res_data.pop('last_update')
        res_data.pop('last_runs')
        rid = set_periodic_task(**res_data)
        log.info('Import of periodictask "{0!s}" finished,'
                 ' id: {1!s}'.format(res_data['name'], rid))
