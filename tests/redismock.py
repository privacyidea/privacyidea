# -*- coding: utf-8 -*-
"""
2015-06-04 Create REDIS mock
           Cornelius Kölbel <cornelius@privacyidea.org>

Original responses.py is:
Copyright 2013 Dropbox, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from collections import namedtuple

from collections.abc import Sequence, Sized

from .smtpmock import get_wrapped

Call = namedtuple('Call', ['setex', 'get'])

_wrapper_template = """\
def wrapper%(signature)s:
    with redismock:
        return func%(funcargs)s
"""


class CallList(Sequence, Sized):
    def __init__(self):
        self._calls = []

    def __iter__(self):
        return iter(self._calls)

    def __len__(self):
        return len(self._calls)

    def __getitem__(self, idx):
        return self._calls[idx]

    def setdata(self, request, response):
        self._calls.append(Call(request, response))

    def reset(self):
        self._calls = []


class Redis(object):

    def __init__(self):
        self.dictionary = {}

    def get(self, value):
        return self.dictionary.get(value)

    def setex(self, key, value=None, time=None):
        self.dictionary[key] = value
        return True

    def set_data(self, data):
        self.dictionary = data


class RedisMock(object):

    def __init__(self):
        self._calls = CallList()
        self.data = {}
        self.reset()

    def reset(self):
        self._calls.reset()

    @property
    def calls(self):
        return self._calls

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()
        self.reset()

    def activate(self, func):
        evaldict = {'redismock': self, 'func': func}
        return get_wrapped(func, _wrapper_template, evaldict)

    def set_data(self, data):
        self.data = data

    def start(self):
        import mock

        def unbound_on_Redis(hostname):
            self.redis_obj = Redis()
            self.redis_obj.set_data(self.data)
            return self.redis_obj

        self._patcher = mock.patch('redis.Redis',
                                   unbound_on_Redis)
        self._patcher.start()

    def stop(self):
        self._patcher.stop()

# expose default mock namespace
mock = _default_mock = RedisMock()
__all__ = []
for __attr in (a for a in dir(_default_mock) if not a.startswith('_')):
    __all__.append(__attr)
    globals()[__attr] = getattr(_default_mock, __attr)
