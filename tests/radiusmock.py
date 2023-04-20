# -*- coding: utf-8 -*-
"""
2019-08-15 More sophisticated radiusmock
        Cornelius Kölbel <cornelius.koelbel@netknights.it>
2017-10-30 Add mocking the timeout
        Cornelius Kölbel <cornelius.koelbel@netknights.it>
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

from collections import namedtuple

from collections.abc import Sequence, Sized

from pyrad import packet
from pyrad.client import Timeout
from pyrad.packet import AccessReject, AccessAccept, AccessChallenge

from .smtpmock import get_wrapped

Call = namedtuple('Call', ['request', 'response'])

_wrapper_template = """\
def wrapper%(signature)s:
    with radiusmock:
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


class RadiusMock(object):

    def __init__(self):
        self._calls = CallList()
        self.reset()

    def reset(self):
        self._request_data = {}
        self._calls.reset()

    def setdata(self, server=None, rpacket=None, response=AccessReject, response_data=None, timeout=False):
        self._request_data = {
            'server': server,
            'packet': rpacket,
            'response': response,
            'response_data': response_data or {},
            'timeout': timeout
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
        if self._request_data.get("timeout"):
            raise Timeout()
        reply = pkt.CreateReply(**self._request_data.get("response_data"))
        reply.code = self._request_data.get("response", AccessReject)
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
