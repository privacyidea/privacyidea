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
import functools
from flask import current_app

from privacyidea.lib.queue.huey import HueyQueue
from privacyidea.lib.queue.null import NullQueue

QUEUE_CLASSES = {
    "huey": HueyQueue,
    "null": NullQueue,
}

class JobCollector(object):
    def __init__(self):
        self._tasks = {}

    def add_task(self, name, func, *args, **kwargs):
        self._tasks[name] = (func, args, kwargs)

    def register_app(self, app):
        if "task_queue" in app.config:
            raise RuntimeError("App already has a task queue: {!r}".format(app.config["task_queue"]))
        queue_class = QUEUE_CLASSES[app.config.get("PI_TASK_QUEUE_CLASS", "null")]
        task_queue = queue_class()
        app.config["task_queue"] = task_queue
        for name, (func, args, kwargs) in self._tasks.items():
            task_queue.add_task(name, func, *args, **kwargs)


COLLECTOR = JobCollector()


def task(name, fire_and_forget=False):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            from privacyidea.app import create_app
            app = create_app()
            with app.app_context():
                result = f(*args, **kwargs)
                if fire_and_forget:
                    return None
                else:
                    return result

        COLLECTOR.add_task(name, decorated)
        return f
    return decorator


def register_app(app):
    COLLECTOR.register_app(app)


def get_task_queue():
    return current_app.config["task_queue"]


def wrap_task(name, result):
    def caller(*args, **kwargs):
        _ = get_task_queue().enqueue(name, args, kwargs) # we discard the promise
        return result
    return caller