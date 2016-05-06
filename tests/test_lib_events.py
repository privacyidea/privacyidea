"""
This file contains the event handlers tests. It tests:

lib/eventhandler/usernotification.py (one event handler module)
lib/event.py (the decorator)
"""

import smtpmock
from .base import MyTestCase, FakeFlaskG, FakeAudit
from privacyidea.lib.eventhandler.usernotification import UserNotificationEventHandler
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.smtpserver import add_smtpserver
from flask import Request
from werkzeug.test import EnvironBuilder

class BaseEventHandlerTestCase(MyTestCase):

    def test_01_basefunctions(self):
        actions = BaseEventHandler().actions
        self.assertEqual(actions, ["sample_action_1", "sample_action_2"])

        events = BaseEventHandler().events
        self.assertEqual(events, ["*"])

        base_handler =  BaseEventHandler()
        r = base_handler.check_condition()
        self.assertTrue(r)

        base_handler = BaseEventHandler()
        r = base_handler.do("action")
        self.assertTrue(r)

class UserNotificationTestCase(MyTestCase):

    def test_01_basefunctions(self):
        actions = UserNotificationEventHandler().actions
        self.assertEqual(actions, ["sendmail"])

    @smtpmock.activate
    def test_02_sendmail(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"

        g.logged_in_user = {"user": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SomeSerial",
                        "user": "cornelius"}

        options = {"g": g,
                   "request": req,
                   "emailconfig": "myserver"}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)
