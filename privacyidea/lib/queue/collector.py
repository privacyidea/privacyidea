# -*- coding: utf-8 -*-
#  2018-11-15 Friedrich Weber <friedrich.weber@netknights.it>
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


class TaskCollector(object):
    """
    For most third-party task queue modules, the tasks are discovered by tracking all
    functions decorated with a ``@task`` decorator. However, in order
    to invoke the decorator, one usually needs to provide the queue
    configuration (e.g. the redis server) already.
    In privacyIDEA, we cannot do that, because the app config is not known
    yet -- it will be known when ``create_app`` is called!
    Thus, we cannot directly use the @task decorator, but need a task collector
    that collects tasks in privacyIDEA code and registers them with the task
    queue module when ``create_app`` has been called.
    """
    def __init__(self, queue_classes, default_queue_class_name):
        """
        :param queue_classes: A dictionary mapping class names to BaseQueue sclasses
        :param default_queue_class_name: Class name to use if the config specifies no queue class
        """
        self._tasks = {}
        self._queue_classes = queue_classes
        self._default_queue_class_name = default_queue_class_name

    @property
    def tasks(self):
        return self._tasks

    def add_task(self, name, func, args, kwargs):
        """
        Register a task with the collector.
        :param name: unique name of the task
        :param func: function of the task
        :param args: arguments passed to the task queue's ``add_task`` method
        :param kwargs: keyword arguments passed to the task queue's ``add_task`` method
        """
        if name in self._tasks:
            raise RuntimeError("Duplicate tasks: {!r}".format(name))
        self._tasks[name] = (func, args, kwargs)

    def register_app(self, app):
        """
        Create an instance of a ``BaseQueue`` subclass according to the app config's
        ``PI_TASK_QUEUE_CLASS`` option and store it in the ``task_queue`` config.
        Register all collected tasks with this application.
        This instance is shared between threads!
        This function should only be called once per process.
        :param app: privacyIDEA app
        """
        if "task_queue" in app.config:
            raise RuntimeError("App already has a task queue: {!r}".format(app.config["task_queue"]))
        queue_class = self._queue_classes[app.config.get("PI_TASK_QUEUE_CLASS", self._default_queue_class_name)]
        task_queue = queue_class()
        app.config["task_queue"] = task_queue
        for name, (func, args, kwargs) in self._tasks.items():
            task_queue.add_task(name, func, *args, **kwargs)

