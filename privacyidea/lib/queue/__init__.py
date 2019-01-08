# -*- coding: utf-8 -*-
#  2018-10-31 Friedrich Weber <friedrich.weber@netknights.it>
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
from flask import current_app

from privacyidea.lib.queue.collector import JobCollector
from privacyidea.lib.queue.null import NullQueue

QUEUE_CLASSES = {
    "null": NullQueue,
}

try:
    from privacyidea.lib.queue.huey_queue import HueyQueue
    QUEUE_CLASSES["huey"] = HueyQueue
except ImportError as e:  # pragma: no cover
    pass

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