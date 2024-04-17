"""
2016-01-20 Cornelius Kölbel <cornelius@privacyidea.org>
           Support STARTTLS mock

2015-01-30 Cornelius Kölbel <cornelius@privacyidea.org>
           Change responses.py to be able to run with SMTP


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

import smtplib

from inspect import formatargspec, getfullargspec as getargspec
from collections.abc import Sequence, Sized

from collections import namedtuple
from functools import update_wrapper
from smtplib import SMTPException


Call = namedtuple('Call', ['request', 'response'])

_wrapper_template = """\
def wrapper%(signature)s:
    with smtpmock:
        return func%(funcargs)s
"""


def get_wrapped(func, wrapper_template, evaldict):
    # Preserve the argspec for the wrapped function so that testing
    # tools such as pytest can continue to use their fixture injection.
    args = getargspec(func)
    values = args.args[-len(args.defaults):] if args.defaults else None

    signature = formatargspec(*args)
    is_bound_method = hasattr(func, '__self__')
    if is_bound_method:
        args.args = args.args[1:]     # Omit 'self'
    callargs = formatargspec(*args, formatvalue=lambda v: '=' + v)

    ctx = {'signature': signature, 'funcargs': callargs}
    exec(wrapper_template % ctx, evaldict, evaldict)

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

class SmtpMock(object):

    def __init__(self):
        self._calls = CallList()
        self.sent_message = None
        self.smtp_ssl = False
        self.reset()

    def reset(self):
        self._request_data = {}
        self._calls.reset()

    def get_smtp_ssl(self):
        return self.smtp_ssl

    def setdata(self, response=None, authenticated=True,
                config=None, exception=False, support_tls=True):
        if response is None:
                response = {}
        config = config or {}
        self.support_tls = support_tls
        self.exception = exception
        self._request_data = {
            'response': response,
            'authenticated': authenticated,
            'config': config,
            'recipient': config.get("MAILTO")
        }

    def get_sent_message(self):
        return self.sent_message

    @property
    def calls(self):
        return self._calls

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()
        self.reset()

    def activate(self, func):
        evaldict = {'smtpmock': self, 'func': func}
        return get_wrapped(func, _wrapper_template, evaldict)

    def _on_request(self, SMTP_instance, sender, recipient, msg):
        # mangle request packet
        response = self._request_data.get("response")
        if not self._request_data.get("authenticated"):
            response = {self._request_data.get("recipient"):
                            (530, "Authorization required (#5.7.1)")}
        return response

    def _on_login(self, SMTP_instance, username, password):
        # mangle request packet
        if self._request_data.get("authenticated"):
            response = (235, "Authentication successful.")
        else:
            response = (535, "authentication failed (#5.7.1)")
        return {self._request_data.get("recipient"): response}

#    def _on_init(self, SMTP_instance, host, port=25, timeout=3):
    def _on_init(self, *args, **kwargs):
        SMTP_instance = args[0]
        host = args[1]
        if isinstance(SMTP_instance, smtplib.SMTP_SSL):
            # in case we need sth. to do with SMTL_SSL
            self.smtp_ssl = True
        # mangle request packet
        self.timeout = kwargs.get("timeout", 10)
        self.port = kwargs.get("port", 25)
        self.esmtp_features = {}
        return None

    @staticmethod
    def _on_debuglevel(SMTP_instance, level):
        return None

    @staticmethod
    def _on_quit(SMTP_instance):
        return None

    def _on_starttls(self, SMTP_instance):
        if self.exception:
            raise SMTPException("MOCK TLS ERROR")
        if not self.support_tls:
            raise SMTPException("The SMTP Server does not support TLS.")
        return None

    def start(self):
        import mock

        def unbound_on_send(SMTP, sender, recipient, msg, *a, **kwargs):
            self.sent_message = msg
            return self._on_request(SMTP, sender, recipient, msg, *a, **kwargs)
        self._patcher = mock.patch('smtplib.SMTP.sendmail',
                                   unbound_on_send)
        self._patcher.start()

        def unbound_on_login(SMTP, username, password, *a, **kwargs):
            return self._on_login(SMTP, username, password, *a, **kwargs)

        self._patcher2 = mock.patch('smtplib.SMTP.login',
                                    unbound_on_login)
        self._patcher2.start()

        def unbound_on_init(SMTP, server, *a, **kwargs):
            return self._on_init(SMTP, server, *a, **kwargs)

        self._patcher3 = mock.patch('smtplib.SMTP.__init__',
                                    unbound_on_init)
        self._patcher3.start()

        def unbound_on_debuglevel(SMTP, level, *a, **kwargs):
            return self._on_debuglevel(SMTP, level, *a, **kwargs)

        self._patcher4 = mock.patch('smtplib.SMTP.debuglevel',
                                    unbound_on_debuglevel)
        self._patcher4.start()

        def unbound_on_quit(SMTP, *a, **kwargs):
            return self._on_quit(SMTP, *a, **kwargs)

        def unbound_on_starttls(SMTP, *a, **kwargs):
            return self._on_starttls(SMTP, *a, **kwargs)

        self._patcher5 = mock.patch('smtplib.SMTP.quit',
                                    unbound_on_quit)
        self._patcher5.start()

        def unbound_on_empty(SMTP, *a, **kwargs):
            return None

        self._patcher6 = mock.patch('smtplib.SMTP.ehlo',
                                    unbound_on_empty)
        self._patcher6.start()
        self._patcher7 = mock.patch('smtplib.SMTP.close',
                                    unbound_on_empty)
        self._patcher7.start()
        self._patcher8 = mock.patch('smtplib.SMTP.starttls',
                                    unbound_on_starttls)
        self._patcher8.start()

    def stop(self):
        self._patcher.stop()
        self._patcher2.stop()
        self._patcher3.stop()
        self._patcher4.stop()
        self._patcher5.stop()
        self._patcher6.stop()
        self._patcher7.stop()
        self._patcher8.stop()


# expose default mock namespace
mock = _default_mock = SmtpMock()
__all__ = []
for __attr in (a for a in dir(_default_mock) if not a.startswith('_')):
    __all__.append(__attr)
    globals()[__attr] = getattr(_default_mock, __attr)
