# -*- coding: utf-8 -*-
#  2018-10-31 Friedrich Weber <friedrich.weber@netknights.it>
#             Add a task queue
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
from flask import current_app

from privacyidea.lib.queue.collector import TaskCollector
from privacyidea.lib.queue.huey import HueyQueue
from privacyidea.lib.queue.null import NullQueue

QUEUE_CLASSES = {
    "huey": HueyQueue,
    "null": NullQueue,
}

#: A singleton is fine here, because it is only used at
#: import time and once when a new app is created.
#: Afterwards, the object is unused.
TASK_COLLECTOR = TaskCollector(QUEUE_CLASSES, "null")


def task(name, *args, **kwargs):
    """
    Decorator to mark a task to be collected by the task collector.
    All arguments are passed to ``BaseQueue.add_task``.
    """
    def decorator(f):
        TASK_COLLECTOR.add_task(name, f, args, kwargs)
        return f
    return decorator


def register_app(app):
    """
    Register the app ``app`` with the global task collector.
    """
    TASK_COLLECTOR.register_app(app)


def get_task_queue():
    """
    Get the task queue registered with the current app.
    """
    return current_app.config["task_queue"]


def wrap_task(name, result):
    """
    Wrap a task and return a function that can be used like the original function.
    The returned function will always return ``result``.
    This is only useful for fire-and-forget tasks. Then, the returned function
    can be used to simulate a successful execution of the task, even though
    the task is actually executed later and asynchronously by the task queue worker.
    In particular, this does not wait for the actual task result.
    This may cause memory leaks for tasks that are not fire-and-forget tasks.
    :return: a function
    """
    def caller(*args, **kwargs):
        # We discard the promise
        _ = get_task_queue().enqueue(name, args, kwargs)
        return result
    return caller