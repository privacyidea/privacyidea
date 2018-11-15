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
from privacyidea.lib.queue.base import BaseQueue, QueueError
from privacyidea.lib.queue.promise import ImmediatePromise


class NullQueue(BaseQueue):
    def __init__(self):
        BaseQueue.__init__(self)
        self._jobs = {}

    @property
    def jobs(self):
        return self._jobs

    def add_job(self, name, func, fire_and_forget=False):
        if name in self._jobs:
            raise QueueError(u"Job {!r} already exists".format(name))
        self._jobs[name] = func

    def enqueue(self, name, args, kwargs):
        if name not in self._jobs:
            raise QueueError(u"Unknown job: {!r}".format(name))
        return ImmediatePromise(self._jobs[name](*args, **kwargs))
