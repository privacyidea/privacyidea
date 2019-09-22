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


class QueueError(Exception):
    pass


class BaseQueue(object):
    """
    A queue object represents an external job queue and is configured with
    a dictionary of options.
    It allows to register jobs, which are Python functions that may
    be executed outside of the request lifecycle. Every job is identified by
    a unique job name.
    It then allows to delegate (or "enqueue") an invocation of a job
    (which is identified by its job name) to the external job queue.
    Currently, the queue only supports fire-and-forget jobs, i.e.
    jobs without any return value.
    """
    def __init__(self, options):
        self.options = options

    def register_job(self, name, func):  # pragma: no cover
        """
        Add a job to the internal registry.

        :param name: Unique job name
        :param func: Function that should be executed by an external job queue
        """
        raise NotImplementedError()

    def enqueue(self, name, args, kwargs):  # pragma: no cover
        """
        Schedule an invocation of a job on the external job queue.

        :param name: Unique job name
        :param args: Tuple of positional arguments
        :param kwargs: Dictionary of keyword arguments
        :return: None
        """
        raise NotImplementedError()

