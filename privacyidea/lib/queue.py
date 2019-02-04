# -*- coding: utf-8 -*-
#  2019-02-04 Friedrich Weber <friedrich.weber@netknights.it>
#             Add a job queue
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

import logging

from flask import current_app

from privacyidea.lib.queues.null import NullQueue

log = logging.getLogger(__name__)

JOB_QUEUE_CLASS = "PI_JOB_QUEUE_CLASS"
JOB_QUEUE_OPTION_PREFIX = "PI_JOB_QUEUE_"

QUEUE_CLASSES = {
    "null": NullQueue,
}

try:
    from privacyidea.lib.queues.huey_queue import HueyQueue
    QUEUE_CLASSES["huey"] = HueyQueue
except ImportError as e:  # pragma: no cover
    pass


class JobCollector(object):
    """
    For most third-party job queue modules, the jobs are discovered by tracking all
    functions decorated with a ``@job`` decorator. However, in order
    to invoke the decorator, one usually needs to provide the queue
    configuration (e.g. the redis server) already.
    In privacyIDEA, we cannot do that, because the app config is not known
    yet -- it will be known when ``create_app`` is called!
    Thus, we cannot directly use the @job decorator, but need a job collector
    that collects jobs in privacyIDEA code and registers them with the job
    queue module when ``create_app`` has been called.
    """
    def __init__(self, queue_classes, default_queue_class_name):
        """
        :param queue_classes: A dictionary mapping class names to BaseQueue sclasses
        :param default_queue_class_name: Class name to use if the config specifies no queue class
        """
        self._jobs = {}
        self._queue_classes = queue_classes
        self._default_queue_class_name = default_queue_class_name

    @property
    def jobs(self):
        return self._jobs

    def add_job(self, name, func, args, kwargs):
        """
        Register a job with the collector.
        :param name: unique name of the job
        :param func: function of the job
        :param args: arguments passed to the job queue's ``add_job`` method
        :param kwargs: keyword arguments passed to the job queue's ``add_job`` method
        """
        if name in self._jobs:
            raise RuntimeError("Duplicate jobs: {!r}".format(name))
        self._jobs[name] = (func, args, kwargs)

    def register_app(self, app):
        """
        Create an instance of a ``BaseQueue`` subclass according to the app config's
        ``PI_JOB_QUEUE_CLASS`` option and store it in the ``job_queue`` config.
        Register all collected jobs with this application.
        This instance is shared between threads!
        This function should only be called once per process.
        :param app: privacyIDEA app
        """
        if "job_queue" in app.config:
            raise RuntimeError("App already has a job queue: {!r}".format(app.config["job_queue"]))
        queue_class_name = app.config.get(JOB_QUEUE_CLASS, self._default_queue_class_name)
        if queue_class_name not in self._queue_classes:
            log.warning(u"Unknown job queue class name: {!r}".format(queue_class_name))
            queue_class_name = self._default_queue_class_name
        queue_class = self._queue_classes[queue_class_name]
        # Extract configuration from app config: All options starting with PI_JOB_QUEUE_
        options = {}
        for k, v in app.config.items():
            if k.startswith(JOB_QUEUE_OPTION_PREFIX) and k != JOB_QUEUE_CLASS:
                options[k[len(JOB_QUEUE_OPTION_PREFIX):].lower()] = v
        job_queue = queue_class(options)
        log.info(u"Created a new job queue: {!r}".format(job_queue))
        app.config["job_queue"] = job_queue
        for name, (func, args, kwargs) in self._jobs.items():
            job_queue.add_job(name, func, *args, **kwargs)


#: A singleton is fine here, because it is only used at
#: import time and once when a new app is created.
#: Afterwards, the object is unused.
JOB_COLLECTOR = JobCollector(QUEUE_CLASSES, "null")


def job(name, *args, **kwargs):
    """
    Decorator to mark a job to be collected by the job collector.
    All arguments are passed to ``BaseQueue.add_job``.
    """
    def decorator(f):
        JOB_COLLECTOR.add_job(name, f, args, kwargs)
        return f
    return decorator


def register_app(app):
    """
    Register the app ``app`` with the global job collector.
    """
    JOB_COLLECTOR.register_app(app)


def get_job_queue():
    """
    Get the job queue registered with the current app.
    """
    return current_app.config["job_queue"]


def wrap_job(name, result):
    """
    Wrap a job and return a function that can be used like the original function.
    The returned function will always return ``result``.
    This is only useful for fire-and-forget jobs. Then, the returned function
    can be used to simulate a successful execution of the job, even though
    the job is actually executed later and asynchronously by the job queue worker.
    In particular, this does not wait for the actual job result.
    This may cause memory leaks for jobs that are not fire-and-forget jobs.
    :return: a function
    """
    def caller(*args, **kwargs):
        # We discard the promise
        _ = get_job_queue().enqueue(name, args, kwargs)
        return result
    return caller
