# -*- coding: utf-8 -*-
"""
2017-12-27 Cornelius Kölbel <cornelius.koelbel@netknights.it>
           Mocking the SMPP client


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

from __future__ import (
    absolute_import, print_function, division, unicode_literals
)

import six


try:
    from six import cStringIO as BufferIO
except ImportError:
    from six import StringIO as BufferIO

import inspect
from collections import namedtuple, Sequence, Sized
from functools import update_wrapper
from smpplib.client import ConnectionError


Call = namedtuple('Call', ['request', 'response'])

_wrapper_template = """\
def wrapper%(signature)s:
    with smppmock:
        return func%(funcargs)s
"""


def get_wrapped(func, wrapper_template, evaldict):
    # Preserve the argspec for the wrapped function so that testing
    # tools such as pytest can continue to use their fixture injection.
    args, a, kw, defaults = inspect.getargspec(func)
    values = args[-len(defaults):] if defaults else None

    signature = inspect.formatargspec(args, a, kw, defaults)
    is_bound_method = hasattr(func, '__self__')
    if is_bound_method:
        args = args[1:]     # Omit 'self'
    callargs = inspect.formatargspec(args, a, kw, values,
                                     formatvalue=lambda v: '=' + v)

    ctx = {'signature': signature, 'funcargs': callargs}
    six.exec_(wrapper_template % ctx, evaldict)

    wrapper = evaldict['wrapper']

    update_wrapper(wrapper, func)
    if is_bound_method:
        wrapper = wrapper.__get__(func.__self__, type(func.__self__))
    return wrapper


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


class SmppMock(object):

    def __init__(self):
        self._calls = CallList()
        self.connect_successful = True
        self.systemid = None
        self.password = None
        self.reset()

    def reset(self):
        self._calls.reset()

    def setdata(self, connection_success=True, systemid=None, password=None):
        self.connect_successful = connection_success
        self.systemid = systemid
        self.password = password

    @property
    def calls(self):
        return self._calls

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()
        self.reset()

    def activate(self, func):
        evaldict = {'smppmock': self, 'func': func}
        return get_wrapped(func, _wrapper_template, evaldict)

    def _on_connect(self, SMMP):
        if self.connect_successful:
            return None
        else:
            raise ConnectionError()

    def _on_disconnect(self, SMMP):
        self.host = None
        self.port = None

    def _on_init(self, SMMP, host, port):
        self.host = host
        self.port = port
        return None

    def _on_transmitter(self, SMMP, systemid, password):
        if systemid != self.systemid or password != self.password:
            raise Exception("Wrong credentials")
        return None

    def _on_send_message(self, SMMP, source_addr_ton=None, source_addr_npi=None,
                         source_addr=None, dest_addr_ton=None,
                         dest_addr_npi=None, destination_addr=None,
                         short_message=None):
        pass

    def start(self):
        import mock

        def unbound_on_init(SMMP, host, port):
            return self._on_init(SMMP, host, port)

        self._patcher1 = mock.patch('smpplib.client.Client.__init__',
                                   unbound_on_init)
        self._patcher1.start()

        def unbound_on_connect(SMMP):
            return self._on_connect(SMMP)

        self._patcher2 = mock.patch('smpplib.client.Client.connect',
                                    unbound_on_connect)
        self._patcher2.start()

        def unbound_on_transmitter(SMMP, system_id, password):
            return self._on_transmitter(SMMP, system_id, password)

        self._patcher3 = mock.patch('smpplib.client.Client.bind_transmitter',
                                    unbound_on_transmitter)
        self._patcher3.start()

        def unbound_on_send_message(SMMP, *a, **kwargs):
            return self._on_send_message(SMMP, *a, **kwargs)

        self._patcher4 = mock.patch('smpplib.client.Client.send_message',
                                    unbound_on_send_message)
        self._patcher4.start()

        def unbound_on_disconnect(SMMP):
            return self._on_disconnect(SMMP)

        self._patcher5 = mock.patch('smpplib.client.Client.disconnect',
                                    unbound_on_disconnect)
        self._patcher5.start()

    def stop(self):
        self._patcher1.stop()
        self._patcher2.stop()
        self._patcher3.stop()
        self._patcher4.stop()
        self._patcher5.stop()


# expose default mock namespace
mock = _default_mock = SmppMock()
__all__ = []
for __attr in (a for a in dir(_default_mock) if not a.startswith('_')):
    __all__.append(__attr)
    globals()[__attr] = getattr(_default_mock, __attr)
