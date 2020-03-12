# -*- coding: utf-8 -*-

"""
This file tests:

lib/eventhandler/usernotification.py
"""
from werkzeug.test import EnvironBuilder
from flask import Request

from privacyidea.app import PiResponseClass as Response
from privacyidea.lib.eventhandler.logginghandler import LoggingEventHandler
from .base import MyTestCase, FakeFlaskG, FakeAudit


class LoggingTestCase(MyTestCase):
    def test_01_basefunctions(self):
        actions = LoggingEventHandler().actions
        self.assertIn('logging', actions, actions)

        # check positions
        pos = LoggingEventHandler().allowed_positions
        self.assertEqual(set(pos), {"post", "pre"}, pos)

    def test_02_loggingevent(self):
        # simple logging event with default values
        g = FakeFlaskG()
        g.audit_object = FakeAudit()
        env = EnvironBuilder(method='POST', headers={}, path='/auth').get_environ()
        # Set the remote address so that we can filter for it
#        g.client_ip = "10.0.0.1"
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
