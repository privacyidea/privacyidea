# -*- coding: utf-8 -*-

"""
This file tests:

lib/eventhandler/logging.py
"""
from mock import mock
from datetime import datetime
from werkzeug.test import EnvironBuilder
from flask import Request
from testfixtures import log_capture

from privacyidea.lib.token import init_token
from privacyidea.app import PiResponseClass as Response
from privacyidea.lib.eventhandler.logginghandler import LoggingEventHandler
from privacyidea.lib.user import User
from .base import MyTestCase, FakeFlaskG, FakeAudit


class LoggingTestCase(MyTestCase):
    def test_01_basefunctions(self):
        actions = LoggingEventHandler().actions
        self.assertIn('logging', actions, actions)

        # check positions
        pos = LoggingEventHandler().allowed_positions
        self.assertEqual(set(pos), {"post", "pre"}, pos)

    @log_capture()
    def test_02_loggingevent_default(self, capture):
        # simple logging event with default values
        g = FakeFlaskG()
        g.audit_object = FakeAudit()
        env = EnvironBuilder(method='POST', headers={}, path='/auth').get_environ()
        req = Request(env)
        req.all_data = {}
        resp = Response(response="""{"result": {"value": true}}""")
        options = {
            "g": g,
            "request": req,
            "response": resp,
            "handler_def": {
            }
        }
        log_handler = LoggingEventHandler()
        res = log_handler.do("logging", options=options)
        self.assertTrue(res)
        capture.check(
            ('pi-eventlogger', 'INFO', 'event=/auth triggered')
        )

    @log_capture()
    def test_03_loggingevent_parameter(self, capture):
        # simple logging event with user defined values
        self.setUp_user_realms()
        g = FakeFlaskG()
        g.audit_object = FakeAudit()
        env = EnvironBuilder(method='POST', headers={}, path='/auth').get_environ()
        req = Request(env)
        req.all_data = {}
        req.User = User("cornelius", self.realm1)
        resp = Response(response="""{"result": {"value": true}}""")
        options = {
            "g": g,
            "request": req,
            "response": resp,
            "handler_def": {
                'options': {
                    'name': 'eventlogger-privacyidea',
                    'level': 'WARN',
                    'message': 'Hello {username}!'
                }
            }
        }
        log_handler = LoggingEventHandler()
        res = log_handler.do("logging", options=options)
        self.assertTrue(res)
        capture.check_present(
            ('eventlogger-privacyidea', 'WARNING', 'Hello cornelius!')
        )

    @log_capture()
    def test_04_loggingevent_broken_parameter(self, capture):
        # simple logging event with faulty parameters
        self.setUp_user_realms()
        g = FakeFlaskG()
        g.audit_object = FakeAudit()
        env = EnvironBuilder(method='POST', headers={}, path='/auth').get_environ()
        req = Request(env)
        req.all_data = {}
        req.User = User("cornelius", self.realm1)
        resp = Response(response="""{"result": {"value": true}}""")
        options = {
            "g": g,
            "request": req,
            "response": resp,
            "handler_def": {
                'options': {
                    'name': None,
                    'level': 'some_level',
                    'message': None
                }
            }
        }
        log_handler = LoggingEventHandler()
        res = log_handler.do("logging", options=options)
        self.assertTrue(res)
        capture.check_present(
            ('root', 'INFO', 'event=/auth triggered')
        )

    @log_capture()
    def test_05_loggingevent_tags(self, capture):
        class UserAgentMock:
            string = "hello world"
            browser = "browser"

        # simple logging event with all tags
        self.setUp_sqlite_resolver_realm('testuser.sqlite', 'sqliterealm')
        available_tags = ['admin', 'realm', 'action', 'serial', 'url', 'user',
                          'surname', 'givenname', 'username', 'userrealm',
                          'tokentype', 'time', 'date', 'client_ip',
                          'ua_browser', 'ua_string']
        tok = init_token({"serial": "testserial", "type": "spass",
                          "pin": "pin"}, user=User("cornelius", "sqliterealm"))
        g = FakeFlaskG()
        g.audit_object = FakeAudit()
        g.logged_in_user = {"username": "admin", "role": "admin",
                            "realm": "super"}
        env = EnvironBuilder(method='POST', headers={}, path='/auth').get_environ()
        req = Request(env)
        req.user_agent = UserAgentMock()
        req.all_data = {'serial': 'testserial'}
        req.User = User("cornelius", 'sqliterealm')
        resp = Response(response="""{"result": {"value": true}}""")
        options = {
            "g": g,
            "request": req,
            "response": resp,
            "handler_def": {
                'options': {
                    'message': ' '.join(['{0!s}={{{0!s}}}'.format(x) for x in available_tags])
                }
            }
        }
        current_utc_time = datetime(2018, 3, 4, 5, 6, 8)
        with mock.patch('privacyidea.lib.utils.datetime') as mock_dt:
            mock_dt.now.return_value = current_utc_time

            log_handler = LoggingEventHandler()
            res = log_handler.do("logging", options=options)
            self.assertTrue(res)
            capture.check_present(
                ('pi-eventlogger', 'INFO',
                 'admin=admin realm=super action=/auth serial=testserial '
                 'url=http://localhost/ user=Cornelius surname=Kölbel '
                 'givenname=None username=cornelius userrealm=sqliterealm '
                 'tokentype=spass time=05:06:08 date=2018-03-04 '
                 'client_ip=None ua_browser=browser ua_string=hello world')
            )
