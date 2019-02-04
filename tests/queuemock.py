# -*- coding: utf-8 -*-
#
#  2019-01-07 Friedrich Weber <friedrich.weber@netknights.it>
#             Implement queue mock
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNE7SS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import functools
import mock

from privacyidea.lib.queue import get_job_queue
from privacyidea.config import TestingConfig
from privacyidea.lib.queues.base import BaseQueue, QueueError, ImmediatePromise

from tests.base import OverrideConfigTestCase


class FakeQueue(BaseQueue):
    """
    A queue class that keeps track of enqueued jobs, for usage in unit tests.
    """
    def __init__(self, options):
        BaseQueue.__init__(self, options)
        self._jobs = {}
        self.reset()

    @property
    def jobs(self):
        return self._jobs

    def reset(self):
        self.enqueued_jobs = []

    def add_job(self, name, func, fire_and_forget=False):
        if name in self._jobs:
            raise QueueError(u"Job {!r} already exists".format(name))

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if fire_and_forget:
                return None
            else:
                return result

        self._jobs[name] = wrapper

    def enqueue(self, name, args, kwargs):
        if name not in self._jobs:
            raise QueueError(u"Unknown job: {!r}".format(name))
        self.enqueued_jobs.append((name, args, kwargs))
        return ImmediatePromise(self._jobs[name](*args, **kwargs))


class MockQueueTestCase(OverrideConfigTestCase):
    """
    A test case class which has a mock job queue set up.
    You can check the enqueued jobs with::

        queue = get_job_queue()
        self.assertEqual(queue.enqueued_jobs, ...)

    The ``enqueued_jobs`` attribute is reset for each test case.
    """
    class Config(TestingConfig):
        PI_JOB_QUEUE_CLASS = "fake"

    @classmethod
    def setUpClass(cls):
        """ override privacyidea.config.config["testing"] with the inner config class """
        with mock.patch.dict("privacyidea.lib.queue.QUEUE_CLASSES", {"fake": FakeQueue}):
            super(MockQueueTestCase, cls).setUpClass()

    def setUp(self):
        get_job_queue().reset()
        OverrideConfigTestCase.setUp(self)
