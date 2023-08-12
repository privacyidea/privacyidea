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

from collections import namedtuple
from mock import Mock

from collections.abc import Sequence, Sized

from smpplib.exceptions import ConnectionError

from .smtpmock import get_wrapped

Call = namedtuple('Call', ['request', 'response'])

_wrapper_template = """\
def wrapper%(signature)s:
    with smppmock:
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

    def _on_connect(self, SMPP):
        if self.connect_successful:
            return None
        else:
            raise ConnectionError()

    def _on_disconnect(self, SMPP):
        self.host = None
        self.port = None

    def _on_init(self, SMPP, host, port):
        self.host = host
        self.port = port
        return None

    def _on_transmitter(self, SMPP, systemid, password):
        if systemid != self.systemid or password != self.password:
            raise Exception("Wrong credentials")
        BindTransmitterRespMock = Mock()
        BindTransmitterRespMock.get_status_desc.return_value = 'No Error'
        return BindTransmitterRespMock

    def _on_send_message(self, SMPP, source_addr_ton=None, source_addr_npi=None,
                         source_addr=None, dest_addr_ton=None,
                         dest_addr_npi=None, destination_addr=None,
                         short_message=None, data_coding=None, esm_class=None):
        SubmitSMMock = Mock()
        SubmitSMMock.get_status_desc.return_value = 'No Error'
        return SubmitSMMock

    def start(self):
        import mock

        def unbound_on_init(SMPP, host, port):
            return self._on_init(SMPP, host, port)

        self._patcher1 = mock.patch('smpplib.client.Client.__init__',
                                   unbound_on_init)
        self._patcher1.start()

        def unbound_on_connect(SMPP):
            return self._on_connect(SMPP)

        self._patcher2 = mock.patch('smpplib.client.Client.connect',
                                    unbound_on_connect)
        self._patcher2.start()

        def unbound_on_transmitter(SMPP, system_id, password):
            return self._on_transmitter(SMPP, system_id, password)

        self._patcher3 = mock.patch('smpplib.client.Client.bind_transmitter',
                                    unbound_on_transmitter)
        self._patcher3.start()

        def unbound_on_send_message(SMPP, *a, **kwargs):
            return self._on_send_message(SMPP, *a, **kwargs)

        self._patcher4 = mock.patch('smpplib.client.Client.send_message',
                                    unbound_on_send_message)
        self._patcher4.start()

        def unbound_on_disconnect(SMPP):
            return self._on_disconnect(SMPP)

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
