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

from privacyidea.lib.error import ServerError
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.utils import get_module_class

log = logging.getLogger(__name__)

JOB_QUEUE_CLASS = "PI_JOB_QUEUE_CLASS"
JOB_QUEUE_OPTION_PREFIX = "PI_JOB_QUEUE_"


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
    def __init__(self):
        self._jobs = {}

    @property
    def jobs(self):
        return self._jobs

    def register_job(self, name, func, args, kwargs):
        """
        Register a job with the collector.

        :param name: unique name of the job
        :param func: function of the job
        :param args: arguments passed to the job queue's ``register_job`` method
        :param kwargs: keyword arguments passed to the job queue's ``register_job`` method
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
        with app.app_context():
            store = get_app_local_store()
        if "job_queue" in store:
            raise RuntimeError("App already has a job queue: {!r}".format(store["job_queue"]))
        try:
            package_name, class_name = app.config[JOB_QUEUE_CLASS].rsplit(".", 1)
            queue_class = get_module_class(package_name, class_name)
        except (ImportError, ValueError) as exx:
            log.warning(u"Could not import job queue class {!r}: {!r}".format(app.config[JOB_QUEUE_CLASS], exx))
            return
        # Extract configuration from app config: All options starting with PI_JOB_QUEUE_
        options = {}
        for k, v in app.config.items():
            if k.startswith(JOB_QUEUE_OPTION_PREFIX) and k != JOB_QUEUE_CLASS:
                options[k[len(JOB_QUEUE_OPTION_PREFIX):].lower()] = v
        job_queue = queue_class(options)
        log.info(u"Created a new job queue: {!r}".format(job_queue))
        store["job_queue"] = job_queue
        for name, (func, args, kwargs) in self._jobs.items():
            job_queue.register_job(name, func, *args, **kwargs)


#: A singleton is fine here, because it is only used at
#: import time and once when a new app is created.
#: Afterwards, the object is unused.
JOB_COLLECTOR = JobCollector()


def job(name, *args, **kwargs):
    """
    Decorator to mark a job to be collected by the job collector.
    All arguments are passed to ``register_job``.
    """
    def decorator(f):
        JOB_COLLECTOR.register_job(name, f, args, kwargs)
        return f
    return decorator


def register_app(app):
    """
    Register the app ``app`` with the global job collector, if a PI_JOB_QUEUE_CLASS is non-empty.
    Do nothing otherwise.
    """
    if app.config.get(JOB_QUEUE_CLASS, ""):
        JOB_COLLECTOR.register_app(app)


def has_job_queue():
    """
    Return a boolean describing whether the current app has an app queue configured.
    """
    return "job_queue" in get_app_local_store()


def get_job_queue():
    """
    Get the job queue registered with the current app. If no job queue is configured,
    raise a ServerError.
    """
    store = get_app_local_store()
    if "job_queue" in store:
        return store["job_queue"]
    else:
        raise ServerError("privacyIDEA has no job queue configured!")


def wrap_job(name, result):
    """
    Wrap a job and return a function that can be used like the original function.
    The returned function will always return ``result``.
    This assumes that a queue is configured! Otherwise, calling the
    resulting function will fail with a ServerError.

    :return: a function
    """
    def caller(*args, **kwargs):
        get_job_queue().enqueue(name, args, kwargs)
        return result
    return caller
