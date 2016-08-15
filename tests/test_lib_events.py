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
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from flask import Request, Response
from werkzeug.test import EnvironBuilder
from privacyidea.lib.token import init_token
from privacyidea.lib.event import (delete_event, set_event,
                                   EventConfiguration, get_handler_object)


class EventHandlerLibTestCase(MyTestCase):

    def test_01_create_update_delete(self):
        eid = set_event("token_init", "UserNotification", "sendmail",
                      conditions={"bla": "yes"},
                      options={"emailconfig": "themis"})
        self.assertEqual(eid, 1)

        # create a new event!
        r = set_event("token_init, token_assign",
                      "UserNotification", "sendmail",
                      conditions={},
                      options={"emailconfig": "themis",
                               "always": "immer"})

        self.assertEqual(r, 2)
        # Update the first event
        r = set_event("token_init, token_assign",
                      "UserNotification", "sendmail",
                      conditions={},
                      options={"emailconfig": "themis",
                               "always": "immer"},
                      id=eid)
        self.assertEqual(r, eid)

        event_config = EventConfiguration()
        self.assertEqual(len(event_config.events), 2)
        # delete
        r = delete_event(eid)
        self.assertTrue(r)
        event_config = EventConfiguration()
        self.assertEqual(len(event_config.events), 1)

        r = delete_event(2)
        self.assertTrue(r)
        event_config = EventConfiguration()
        self.assertEqual(len(event_config.events), 0)

    def test_02_get_handler_object(self):
        h_obj = get_handler_object("UserNotification")
        self.assertEqual(type(h_obj), UserNotificationEventHandler)


class BaseEventHandlerTestCase(MyTestCase):

    def test_01_basefunctions(self):
        actions = BaseEventHandler().actions
        self.assertEqual(actions, ["sample_action_1", "sample_action_2"])

        events = BaseEventHandler().events
        self.assertEqual(events, ["*"])

        base_handler =  BaseEventHandler()
        r = base_handler.check_condition({})
        self.assertTrue(r)

        base_handler = BaseEventHandler()
        r = base_handler.do("action")
        self.assertTrue(r)


class UserNotificationTestCase(MyTestCase):

    def test_01_basefunctions(self):
        actions = UserNotificationEventHandler().actions
        self.assertTrue("sendmail" in actions)

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
                   "handler_def": {"emailconfig": "myserver"}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

    @smtpmock.activate
    def test_03_sendsms(self):
        # setup realms
        self.setUp_user_realms()

        r = set_smsgateway(identifier="myGW",
                           providermodule="privacyidea.lib.smsprovider."
                                          "SmtpSMSProvider.SmtpSMSProvider",
                           options={"SMTPIDENTIFIER": "myserver",
                                    "MAILTO": "test@example.com"})
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"test@example.com": (200, "OK")},
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
                   "handler_def": {"smsconfig": "myGW"}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendsms", options=options)
        self.assertTrue(res)

    def test_04_conditions(self):
        c = UserNotificationEventHandler().conditions
        self.assertTrue("logged_in_user" in c)
        self.assertTrue("result_value" in c)

    def test_05_check_conditions(self):

        uhandler = UserNotificationEventHandler()
        resp = Response()
        resp.data = """{"result": {"value": false}}"""
        builder = EnvironBuilder(method='POST')
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {}
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"logged_in_user": "admin"}},
             "response": resp,
             "request": req})
        self.assertEqual(r, False)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"result_value": True}},
             "response": resp,
             "request": req})
        self.assertEqual(r, False)

        # check a locked token with maxfail = failcount
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})

        req.all_data = {"user": "cornelius"}
        resp.data = """{"result": {"value": false},
            "detail": {"serial": "lockedtoken"}
            }
        """
        tok = init_token({"serial": "lockedtoken", "type": "spass"})
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"token_locked": "True"}},
             "response": resp,
             "request": req
             }
        )
        # not yet locked
        self.assertEqual(r, False)

        # lock it
        tok.set_failcount(10)
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"token_locked": "True"}},
             "response": resp,
             "request": req
             }
        )
        # not yet locked
        self.assertEqual(r, True)

    def test_06_check_conditions_realm(self):
        uhandler = UserNotificationEventHandler()
        # check a locked token with maxfail = failcount
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1"}
        resp = Response()
        resp.data = """{"result": {"value": false}}"""
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"realm": "realm2"}},
             "request": req,
             "response": resp
             }
        )
        # wrong realm
        self.assertEqual(r, False)
