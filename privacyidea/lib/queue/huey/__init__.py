# -*- coding: utf-8 -*-
#  2018-11-14 Friedrich Weber <friedrich.weber@netknights.it>
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
from huey import RedisHuey

from privacyidea.lib.queue.base import BaseQueue
from privacyidea.lib.queue.promise import Promise


class HueyQueue(BaseQueue):
    def __init__(self):
        BaseQueue.__init__(self)
        self._huey = RedisHuey()
        self._tasks = {}

    @property
    def huey(self):
        return self._huey

    def add_task(self, name, func):
        self._tasks[name] = self._huey.task()(func)

    def enqueue(self, name, args, kwargs):
        return HueyPromise(self._tasks[name](*args, **kwargs))


class HueyPromise(Promise):
    def __init__(self, wrapper):
        Promise.__init__(self)
        self.wrapper = wrapper

    def get(self):
        return self.wrapper.get()