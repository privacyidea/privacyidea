# -*- coding: utf-8 -*-
#  2018-11-14 Friedrich Weber <friedrich.weber@netknights.it>
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
import functools
import logging
from huey import RedisHuey

from privacyidea.lib.queue.base import BaseQueue, QueueError
from privacyidea.lib.queue.promise import Promise, ImmediatePromise

log = logging.getLogger(__name__)


class HueyQueue(BaseQueue):
    def __init__(self, options):
        BaseQueue.__init__(self, options)
        # TODO: We should rethink ``store_errors=False`` -- how do we notice errors?
        self._huey = RedisHuey(store_none=False, store_errors=False, **options)
        self._jobs = {}

    @property
    def huey(self):
        return self._huey

    @property
    def jobs(self):
        return self._jobs

    def add_job(self, name, func, fire_and_forget=False):
        if name in self._jobs:
            raise QueueError(u"Job {!r} already exists".format(name))

        @functools.wraps(func)
        def decorated(*args, **kwargs):
            result = func(*args, **kwargs)
            if fire_and_forget:
                return None
            else:
                return result
        self._jobs[name] = self._huey.task(name=name)(decorated)

    def enqueue(self, name, args, kwargs):
        if name not in self._jobs:
            raise QueueError(u"Unknown job: {!r}".format(name))
        log.info(u"Sending {!r} job to the queue ...".format(name))
        # If always_eager is True, huey will immediately return the result,
        # which we need to wrap in an ImmediatePromise object
        result = self._jobs[name](*args, **kwargs)
        if self._huey.always_eager:
            return ImmediatePromise(result)
        else:
            return HueyPromise(result)


class HueyPromise(Promise):
    def __init__(self, wrapper):
        Promise.__init__(self)
        self.wrapper = wrapper

    def get(self):
        return self.wrapper.get()