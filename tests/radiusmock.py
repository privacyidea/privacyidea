# -*- coding: utf-8 -*-
"""
2015-01-29 Change responses.py to be able to run with RADIUS
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

from __future__ import (
    absolute_import, print_function, division, unicode_literals
)

import re
import six

if six.PY2:
    try:
        from six import cStringIO as BufferIO
    except ImportError:
        from six import StringIO as BufferIO
else:
    from io import BytesIO as BufferIO

import inspect
from collections import namedtuple, Sequence, Sized
from functools import update_wrapper
from pyrad import packet

Call = namedtuple('Call', ['request', 'response'])

_wrapper_template = """\
def wrapper%(signature)s:
    with radiusmock:
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


class RadiusMock(object):

    def __init__(self):
        self._calls = CallList()
        self.reset()

    def reset(self):
        self._request_data = {}
        self._calls.reset()

    def setdata(self, server=None, rpacket=None, success=True):
        self._request_data = {
            'server': server,
            'packet': rpacket,
            'success': success
        }

    @property
    def calls(self):
        return self._calls

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()
        self.reset()

    def activate(self, func):
        evaldict = {'radiusmock': self, 'func': func}
        return get_wrapped(func, _wrapper_template, evaldict)

    def _on_request(self, client_instance, pkt):
        # mangle request packet
        request = pkt.RequestPacket()
        if pkt.code == packet.AccessRequest:
            # This is a request
            pass
        # create reply packet
        """
                1       Access-Request
                2       Access-Accept
                3       Access-Reject
                4       Accounting-Request
                5       Accounting-Response
               11       Access-Challenge
               12       Status-Server (experimental)
               13       Status-Client (experimental)
              255       Reserved
        """
        #reply = pkt.CreateReply(packet=rawreply)
        reply = pkt.CreateReply()
        if self._request_data.get("success"):
            reply.code = packet.AccessAccept
        else:
            reply.code = packet.AccessReject
        return reply

    def start(self):
        import mock

        def unbound_on_send(Client, pkt, *a, **kwargs):
            return self._on_request(Client, pkt,  *a, **kwargs)
        self._patcher = mock.patch('pyrad.client.Client.SendPacket',
                                   unbound_on_send)
        self._patcher.start()

    def stop(self):
        self._patcher.stop()


# expose default mock namespace
mock = _default_mock = RadiusMock()
__all__ = []
for __attr in (a for a in dir(_default_mock) if not a.startswith('_')):
    __all__.append(__attr)
    globals()[__attr] = getattr(_default_mock, __attr)
