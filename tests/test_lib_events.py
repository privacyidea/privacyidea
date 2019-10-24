# -*- coding: utf-8 -*-

"""
This file contains the event handlers tests. It tests:

lib/eventhandler/usernotification.py (one event handler module)
lib/event.py (the decorator)
"""
import email

import mock

from . import smtpmock
import responses
import os
from .base import MyTestCase, FakeFlaskG, FakeAudit
from privacyidea.lib.eventhandler.usernotification import (
    UserNotificationEventHandler, NOTIFY_TYPE)
from privacyidea.lib.config import get_config_object
from privacyidea.lib.eventhandler.tokenhandler import (TokenEventHandler,
                                                       ACTION_TYPE, VALIDITY)
from privacyidea.lib.eventhandler.scripthandler import ScriptEventHandler, SCRIPT_WAIT, SCRIPT_BACKGROUND
from privacyidea.lib.eventhandler.counterhandler import CounterEventHandler
from privacyidea.lib.eventhandler.responsemangler import ResponseManglerEventHandler
from privacyidea.models import EventCounter, TokenOwner
from privacyidea.lib.eventhandler.federationhandler import FederationEventHandler
from privacyidea.lib.eventhandler.requestmangler import RequestManglerEventHandler
from privacyidea.lib.eventhandler.base import BaseEventHandler, CONDITION
from privacyidea.lib.smtpserver import add_smtpserver
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from flask import Request
from werkzeug.test import EnvironBuilder
from privacyidea.lib.event import (delete_event, set_event,
                                   EventConfiguration, get_handler_object,
                                   enable_event)
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.token import (init_token, remove_token, unassign_token,
                                   get_realms_of_token, get_tokens,
                                   add_tokeninfo)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.user import create_user, User
from privacyidea.lib.policy import ACTION
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.utils import is_true, to_unicode
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date_string
from dateutil.tz import tzlocal
from privacyidea.app import PiResponseClass as Response
import json


class EventHandlerLibTestCase(MyTestCase):

    def test_01_create_update_delete(self):
        eid = set_event("name1", "token_init", "UserNotification", "sendmail",
                        conditions={"bla": "yes"},
                        options={"emailconfig": "themis"})
        self.assertEqual(eid, 1)

        # create a new event!
        r = set_event("name2", ["token_init", "token_assign"],
                      "UserNotification", "sendmail",
                      conditions={},
                      options={"emailconfig": "themis",
                               "always": "immer"})
        # retrieve the current config timestamp
        current_timestamp = get_config_object().timestamp

        self.assertEqual(r, 2)
        # Update the first event
        r = set_event("name1", "token_init, token_assign",
                      "UserNotification", "sendmail",
                      conditions={},
                      options={"emailconfig": "themis",
                               "always": "immer"},
                      id=eid)
        self.assertEqual(r, eid)

        # check that the config timestamp has been updated
        self.assertGreater(get_config_object().timestamp, current_timestamp)
        current_timestamp = get_config_object().timestamp

        event_config = EventConfiguration()
        self.assertEqual(len(event_config.events), 2)
        # delete
        r = delete_event(eid)
        self.assertTrue(r)

        # check that the config timestamp has been updated
        self.assertGreater(get_config_object().timestamp, current_timestamp)
        current_timestamp = get_config_object().timestamp
        event_config = EventConfiguration()
        self.assertEqual(len(event_config.events), 1)

        # Now we have one event left.
        events = event_config.get_handled_events("token_init")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("name"), "name2")
        n_eid = events[0].get("id")
        # Disable this event in the database
        enable_event(n_eid, False)
        # check that the config timestamp has been updated
        self.assertGreater(get_config_object().timestamp, current_timestamp)
        # Reread event config from the database
        event_config = EventConfiguration()
        events = event_config.get_handled_events("token_init")
        self.assertEqual(len(events), 0)
        # Enable the event in the database again
        enable_event(n_eid, True)
        # Reread event config from the database
        event_config = EventConfiguration()
        events = event_config.get_handled_events("token_init")
        self.assertEqual(len(events), 1)
        # If eventid is None, then the whole list is returned
        r = event_config.get_event(None)
        self.assertEqual(r, event_config.events)
        # return a destinct eventid
        r = event_config.get_event(events[0].get("id"))
        self.assertEqual(r[0].get("id"), events[0].get("id"))
        self.assertEqual(r[0].get("position"), "post")

        # We can not enable an event, that does not exist.
        self.assertRaises(ResourceNotFoundError, enable_event, 1234567, True)

        # Cleanup
        r = delete_event(n_eid)
        self.assertTrue(r)
        event_config = EventConfiguration()
        self.assertEqual(len(event_config.events), 0)

    def test_02_get_handler_object(self):
        h_obj = get_handler_object("UserNotification")
        self.assertEqual(type(h_obj), UserNotificationEventHandler)

        h_obj = get_handler_object("Token")
        self.assertEqual(type(h_obj), TokenEventHandler)

        h_obj = get_handler_object("Script")
        self.assertEqual(type(h_obj), ScriptEventHandler)

        h_obj = get_handler_object("Federation")
        self.assertEqual(type(h_obj), FederationEventHandler)


class BaseEventHandlerTestCase(MyTestCase):

    def test_01_basefunctions(self):
        actions = BaseEventHandler().actions
        self.assertEqual(actions, ["sample_action_1", "sample_action_2"])

        events = BaseEventHandler().events
        self.assertEqual(events, ["*"])

        base_handler = BaseEventHandler()
        r = base_handler.check_condition({})
        self.assertTrue(r)

        base_handler = BaseEventHandler()
        r = base_handler.do("action")
        self.assertTrue(r)

    def test_02_check_conditions_only_one_token_no_serial(self):
        # In case there is no token serial in the request (like in a failed
        # auth request of a user with no token) we check if the user has only
        #  one token then this token is used in the conditions

        # prepare
        # setup realms
        self.setUp_user_realms()
        serial = "pw01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        tok = init_token({"serial": serial,
                          "type": "pw", "otppin": "test", "otpkey": "secret"},
                         user=user)
        self.assertEqual(tok.type, "pw")

        uhandler = BaseEventHandler()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1",
                                       "pass": "wrongvalue"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        # This is a kind of authentication request
        req.all_data = {"user": "cornelius@realm1",
                        "pass": "wrongvalue"}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": false}}"""
        # Do checking
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKENTYPE: "pw"}},
             "request": req,
             "response": resp
             }
        )
        # The only token of the user is of type "pw".
        self.assertEqual(r, True)

        remove_token(serial)

    def test_03_check_auth_count_conditions(self):
        self.setUp_user_realms()
        serial = "pw01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        tok = init_token({"serial": serial,
                          "type": "pw", "otppin": "test", "otpkey": "secret"},
                         user=user)
        self.assertEqual(tok.type, "pw")
        uhandler = BaseEventHandler()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1",
                                       "pass": "wrongvalue"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        # This is a kind of authentication request
        req.all_data = {"user": "cornelius@realm1",
                        "pass": "wrongvalue"}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNT_AUTH: "<100"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, True)
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNT_AUTH: ">100"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

        # Set the count_auth and count_auth_success
        add_tokeninfo(serial, "count_auth", 100)
        add_tokeninfo(serial, "count_auth_success", 50)
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNT_AUTH: ">99"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNT_AUTH_SUCCESS:
                                                ">45"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNT_AUTH_FAIL:
                                                ">45"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNT_AUTH_FAIL:
                                                "<45"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)
        remove_token(serial)

    def test_04_tokeninfo_condition(self):
        self.setUp_user_realms()
        serial = "pw01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        tok = init_token({"serial": serial,
                          "type": "pw", "otppin": "test",
                          "otpkey": "secret"},
                         user=user)
        self.assertEqual(tok.type, "pw")
        uhandler = BaseEventHandler()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1",
                                       "pass": "secret"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        # This is a kind of authentication request
        req.all_data = {"user": "cornelius@realm1",
                        "pass": "secret"}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        tok.add_tokeninfo("myValue", "99")
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKENINFO:
                                                "myValue<100"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKENINFO:
                                                "myValue<98"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, False)

        tok.add_tokeninfo("myValue", "Hallo")
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKENINFO:
                                                "myValue== Hallo"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, True)
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKENINFO:
                                                "myValue==hallo"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, False)

        # The beginning of the year 2017 in smaller than now
        tok.add_tokeninfo("myDate", "2017-01-01T10:00+0200")
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKENINFO:
                                                "myDate < {now}"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        # myDate is one hour in the future
        tok.add_tokeninfo("myDate",
                          (datetime.now(tzlocal())
                           + timedelta(hours=1)
                           ).strftime(DATE_FORMAT))
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKENINFO:
                                                "myDate > {now}-2h"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)
        remove_token(serial)

    def test_05_detail_messages_condition(self):
        self.setUp_user_realms()
        uhandler = BaseEventHandler()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1",
                                       "pass": "secret"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        # This is a kind of authentication request
        req.all_data = {"user": "cornelius@realm1",
                        "pass": "secret"}
        req.User = User("cornelius", "realm1")

        # Check DETAIL_MESSAGE
        resp = Response()
        resp.data = """{"result": {"value": true, "status": true},
        "detail": {"message": "something very special happened"}
        }
        """

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.DETAIL_MESSAGE:
                                                "special"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.DETAIL_MESSAGE:
                                                "^special"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, False)

        # Check DETAIL_ERROR_MESSAGE
        resp = Response()
        resp.data = """{"result": {"value": false, "status": false},
            "detail": {"error": {"message": "user does not exist"}}
            }
            """

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.DETAIL_ERROR_MESSAGE:
                                                "does not exist$"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.DETAIL_ERROR_MESSAGE:
                                                "^does not exist"}},
             "request": req,
             "response": resp
             }
        )
        self.assertEqual(r, False)

    def test_06_check_for_client_ip(self):
        uhandler = BaseEventHandler()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1",
                                       "pass": "secret"},
                                 headers={})
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        env = builder.get_environ()
        req = Request(env)
        # This is a kind of authentication request
        req.all_data = {"user": "cornelius@realm1",
                        "pass": "secret"}
        req.User = User("cornelius", "realm1")

        # Check DETAIL_MESSAGE
        resp = Response()
        resp.data = """{"result": {"value": true, "status": true},
                "detail": {"message": "something very special happened"}
                }
                """

        r = uhandler.check_condition(
            {"g": g,
             "handler_def": {"conditions": {CONDITION.CLIENT_IP: "10.0.0.0/24"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        r = uhandler.check_condition(
            {"g": g,
             "handler_def": {"conditions": {CONDITION.CLIENT_IP: "10.0.0.0/24, !10.0.0.1"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

    def test_07_check_rollout_state(self):
        self.setUp_user_realms()
        serial = "rs01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        # Prepare the token
        tok = init_token({"serial": serial,
                          "type": "pw", "otppin": "test", "otpkey": "secret"},
                         user=user)
        tok.token.rollout_state = "fakestate"
        tok.token.save()

        uhandler = BaseEventHandler()
        # Prepare a fake request
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1",
                                       "pass": "wrongvalue"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "pass": "wrongvalue"}
        req.User = user
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        # Check if the condition matches
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.ROLLOUT_STATE: "fakestate"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        # Check if the condition does not match
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.ROLLOUT_STATE: "otherstate"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

        remove_token(serial)


class CounterEventTestCase(MyTestCase):

    def test_01_event_counter(self):
        g = FakeFlaskG()
        audit_object = FakeAudit()
        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User()
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "options": {
                           "counter_name": "hallo_counter"}
                   }
                   }

        t_handler = CounterEventHandler()
        res = t_handler.do("increase_counter", options=options)
        self.assertTrue(res)

        res = t_handler.do("increase_counter", options=options)
        self.assertTrue(res)

        counter = EventCounter.query.filter_by(counter_name="hallo_counter").first()
        self.assertEqual(counter.counter_value, 2)

        if 'decrease_counter' in t_handler.actions:
            t_handler.do("decrease_counter", options=options)
            t_handler.do("decrease_counter", options=options)
            t_handler.do("decrease_counter", options=options)
            counter = EventCounter.query.filter_by(counter_name="hallo_counter").first()
            self.assertEqual(counter.counter_value, 0)
            options['handler_def']['options']['allow_negative_values'] = True
            t_handler.do("decrease_counter", options=options)
            counter = EventCounter.query.filter_by(counter_name="hallo_counter").first()
            self.assertEqual(counter.counter_value, -1)
            t_handler.do("reset_counter", options=options)
            counter = EventCounter.query.filter_by(counter_name="hallo_counter").first()
            self.assertEqual(counter.counter_value, 0)


class ScriptEventTestCase(MyTestCase):

    def test_01_runscript(self):
        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        req.User = User()
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "options": {
                           "user": "1",
                           "realm": "1",
                           "serial": "1",
                           "logged_in_user": "1",
                           "logged_in_role": "1"}
                   }
                   }

        script_name = "ls.sh"
        d = os.getcwd()
        d = "{0!s}/tests/testdata/scripts/".format(d)
        t_handler = ScriptEventHandler(script_directory=d)
        res = t_handler.do(script_name, options=options)
        self.assertTrue(res)

    def test_02_failscript(self):
        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        req.User = User()
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "options": {
                           "background": SCRIPT_WAIT,
                           "raise_error": True,
                           "realm": "1",
                           "serial": "1",
                           "logged_in_user": "1",
                           "logged_in_role": "1"}
                   }
                   }

        script_name = "fail.sh"
        d = os.getcwd()
        d = "{0!s}/tests/testdata/scripts/".format(d)
        t_handler = ScriptEventHandler(script_directory=d)
        self.assertRaises(Exception, t_handler.do, script_name, options=options)


class FederationEventTestCase(MyTestCase):

    def test_00_static_actions(self):
        from privacyidea.lib.eventhandler.federationhandler import ACTION_TYPE
        actions = FederationEventHandler().actions
        self.assertTrue(ACTION_TYPE.FORWARD in actions)

    @responses.activate
    def test_01_forward(self):
        # setup realms
        self.setUp_user_realms()
        self.setUp_user_realm2()

        g = FakeFlaskG()
        audit_object = FakeAudit()
        g.audit_object = audit_object

        # An authentication request for user root with a password, which does
        #  not exist on the local privacyIDEA system
        builder = EnvironBuilder(method='POST',
                                 data={'user': "root", "pass": "lakjsiqdf"},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {'user': "root", "pass": "lakjsiqdf"}
        req.path = "/validate/check"
        resp = Response()
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"realm": "xyz",
                                        "resolver": "resoremote",
                                        "forward_client_ip": True,
                                        "privacyIDEA": "remotePI"}
                                   }
                   }
        f_handler = FederationEventHandler()
        from privacyidea.lib.eventhandler.federationhandler import ACTION_TYPE
        from privacyidea.lib.privacyideaserver import add_privacyideaserver
        responses.add(responses.POST, "https://remote/validate/check",
                      body="""{
                        "jsonrpc": "2.0",
                        "detail": {},
                        "version": "privacyIDEA 2.20.dev2",
                        "result": {
                          "status": true,
                          "value": true},
                        "time": 1503561105.028947,
                        "id": 1
                        }""",
                      content_type="application/json",
                      )
        add_privacyideaserver("remotePI", url="https://remote", tls=False)
        res = f_handler.do(ACTION_TYPE.FORWARD, options=options)
        self.assertTrue(res)
        response = options.get("response").json
        self.assertEqual(response.get("detail").get("origin"),
                         "https://remote/validate/check")

        # The same with a GET Request
        builder = EnvironBuilder(method='GET',
                                 data={'user': "root", "pass": "lakjsiqdf"},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {'user': "root", "pass": "lakjsiqdf"}
        req.path = "/validate/check"
        resp = Response()
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"realm": "xyz",
                                        "forward_client_ip": True,
                                        "privacyIDEA": "remotePI"}
                                   }
                   }
        responses.add(responses.GET, "https://remote/validate/check",
                      body="""{
                                "jsonrpc": "2.0",
                                "detail": {},
                                "version": "privacyIDEA 2.20.dev2",
                                "result": {
                                  "status": true,
                                  "value": true},
                                "time": 1503561105.028947,
                                "id": 1
                                }""",
                      content_type="application/json",
                      )
        add_privacyideaserver("remotePI", url="https://remote", tls=False)
        res = f_handler.do(ACTION_TYPE.FORWARD, options=options)
        self.assertTrue(res)
        response = options.get("response").json
        self.assertEqual(response.get("detail").get("origin"),
                         "https://remote/validate/check")

        # The same with a DELETE Request
        builder = EnvironBuilder(method='DELETE',
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {}
        req.path = "/token/serial"
        resp = Response()
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"realm": "xyz",
                                        "forward_client_ip": True,
                                        "privacyIDEA": "remotePI"}
                                   }
                   }
        responses.add(responses.DELETE, "https://remote/token/serial",
                      body="""{
                                        "jsonrpc": "2.0",
                                        "detail": {},
                                        "version": "privacyIDEA 2.20.dev2",
                                        "result": {
                                          "status": true,
                                          "value": true},
                                        "time": 1503561105.028947,
                                        "id": 1
                                        }""",
                      content_type="application/json",
                      )
        add_privacyideaserver("remotePI", url="https://remote", tls=False)
        res = f_handler.do(ACTION_TYPE.FORWARD, options=options)
        self.assertTrue(res)
        response = options.get("response").json
        self.assertEqual(response.get("detail").get("origin"),
                         "https://remote/token/serial")

        # The same with an unsupported Request method
        builder = EnvironBuilder(method='PUT',
                                 data={'user': "root", "pass": "lakjsiqdf"},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {'user': "root", "pass": "lakjsiqdf"}
        req.path = "/token"
        resp = Response()
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"realm": "xyz",
                                        "forward_client_ip": True,
                                        "privacyIDEA": "remotePI"}
                                   }
                   }
        responses.add(responses.PUT, "https://remote/token",
                      body="""{
                                        "jsonrpc": "2.0",
                                        "detail": {},
                                        "version": "privacyIDEA 2.20.dev2",
                                        "result": {
                                          "status": true,
                                          "value": true},
                                        "time": 1503561105.028947,
                                        "id": 1
                                        }""",
                      content_type="application/json",
                      )
        add_privacyideaserver("remotePI", url="https://remote", tls=False)
        res = f_handler.do(ACTION_TYPE.FORWARD, options=options)
        self.assertTrue(res)
        # No Response data, since this method is not supported
        self.assertEqual(options.get("response").data, b"")

    @responses.activate
    def test_02_forward_admin_request(self):
        # setup realms
        self.setUp_user_realms()
        self.setUp_user_realm2()

        g = FakeFlaskG()
        audit_object = FakeAudit()
        g.audit_object = audit_object

        # A token init request
        builder = EnvironBuilder(method='POST',
                                 data={"genkey": "1", "type": "totp"},
                                 headers={"Authorization": "myAuthToken"})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"genkey": "1", "type": "totp"}
        req.path = "/token/init"
        resp = Response()
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"forward_authorization_token": True,
                                        "privacyIDEA": "remotePI"}
                                   }
                   }
        f_handler = FederationEventHandler()
        from privacyidea.lib.eventhandler.federationhandler import ACTION_TYPE
        from privacyidea.lib.privacyideaserver import add_privacyideaserver
        responses.add(responses.POST, "https://remote/token/init",
                      body="""{"jsonrpc": "2.0", 
                               "detail": {"googleurl": 
                                              {"value": "otpauth://totp/TOTP0019C11A?secret=5IUZZICQQI7CFA6VZA4HO6L52RA4ZIVC&period=30&digits=6&issuer=privacyIDEA", 
                                               "description": "URL for google Authenticator", 
                                               "img": "data:image/png;base64,YII="},
                               "threadid": 140161650956032}, 
                               "versionnumber": "2.20.1",
                               "version": "privacyIDEA 2.20.1",
                               "result": {"status": true,
                                          "value": true},
                               "time": 1510135880.189272,
                               "id": 1}""",
                      content_type="application/json",
                      )
        add_privacyideaserver("remotePI", url="https://remote", tls=False)
        res = f_handler.do(ACTION_TYPE.FORWARD, options=options)
        self.assertTrue(res)
        response = options.get("response").json
        self.assertEqual(response.get("detail").get("origin"),
                         "https://remote/token/init")


class RequestManglerTestCase(MyTestCase):

    def test_01_delete_request_parameter(self):
        actions = RequestManglerEventHandler().actions
        self.assertTrue("delete" in actions, actions)
        self.assertTrue("set" in actions, actions)

        pos = RequestManglerEventHandler().allowed_positions
        self.assertEqual(set(pos), {"post", "pre"})

        g = FakeFlaskG()
        audit_object = FakeAudit()
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass", "deleteme": "topsecret"}
        resp = Response()

        # Request
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "deleteme"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("delete", options=options)
        self.assertNotIn("deleteme", req.all_data)
        self.assertTrue(res)

        # Delete a non-existing value
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "doesnotexist"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("delete", options=options)
        self.assertNotIn("doesnotexist", req.all_data)
        self.assertTrue(res)

    def test_02_set_parameter(self):
        g = FakeFlaskG()
        audit_object = FakeAudit()
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()

        # simple add a parameter with a fixed value
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "newone",
                                        "value": "simpleadd"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual("simpleadd", req.all_data.get("newone"))

        # overwrite an existing parameter with a fixed value
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "serial",
                                        "value": "FUN007"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual("FUN007", req.all_data.get("serial"))

        # Change a parameter with the part of another parameter
        req.all_data = {"user": "givenname.surname@company.com",
                        "realm": ""}

        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "realm",
                                        "value": "{0}",
                                        "match_parameter": "user",
                                        "match_pattern": ".*@(.*)"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual("company.com", req.all_data.get("realm"))
        self.assertEqual("givenname.surname@company.com", req.all_data.get("user"))

        # Only match the complete value, not a subvalue
        req.all_data = {"user": "givenname.surname@company.company",
                        "realm": ""}
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "realm",
                                        "value": "newrealm",
                                        "match_parameter": "user",
                                        "match_pattern": ".*@company.com"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        # The realm is not changed!
        self.assertEqual("", req.all_data.get("realm"))

        # Now we change the parameter itself.
        # Change company.com of a user to newcompany.com
        req.all_data = {"user": "givenname.surname@company.com"}

        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "user",
                                        "value": "{0}@newcompany.com",
                                        "match_parameter": "user",
                                        "match_pattern": "(.*)@company.com"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual("givenname.surname@newcompany.com", req.all_data.get("user"))

        # The request does not contain the match_parameter, thus the
        # parameter in question will not be modified
        req.all_data = {"user": "givenname.surname@company.com" }
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "user",
                                        "value": "{0}@newcompany.com",
                                        "match_parameter": "username",
                                        "match_pattern": "(.*)@company.com"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        # The name is still the old one - since there was nothing to match
        self.assertEqual("givenname.surname@company.com", req.all_data.get("user"))

        # Do some nasty replacing, that will not work out
        # We require two tags, but only have one!
        req.all_data = {"user": "givenname.surname@company.com"}

        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"parameter": "user",
                                        "value": "{1} <{0}@newcompany.com>",
                                        "match_parameter": "user",
                                        "match_pattern": "(.*)@company.com"}
                                   }
                   }
        r_handler = RequestManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        # The user was not modified, since the number of tags did not match
        self.assertEqual("givenname.surname@company.com", req.all_data.get("user"))


class ResponseManglerTestCase(MyTestCase):

    def test_01_delete_response(self):
        actions = ResponseManglerEventHandler().actions
        self.assertTrue("delete" in actions, actions)
        self.assertTrue("set" in actions, actions)

        pos = ResponseManglerEventHandler().allowed_positions
        self.assertEqual(set(pos), {"post"})

        g = FakeFlaskG()
        audit_object = FakeAudit()
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response(mimetype='application/json')

        # delete JSON pointer with two components
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/detail/message"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("delete", options=options)
        self.assertTrue(res)
        self.assertEqual(resp.json["detail"]["error"], 1)
        self.assertNotIn("message", resp.json["detail"])

        # delete JSON pointer with one component
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/result"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("delete", options=options)
        self.assertTrue(res)
        self.assertIn("message", resp.json["detail"])
        self.assertNotIn("result", resp.json)

        # delete JSON pointer with three components
        resp.data = """{"result": {"value": true}, "detail": {"data": {"Du": "Da"}, "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/detail/data/Du"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("delete", options=options)
        self.assertTrue(res)
        self.assertIn("error", resp.json["detail"])
        self.assertNotIn("Du", resp.json["detail"]["data"])

        # JSON pointer with more than 3 components not supported
        resp.data = """{"result": {"value": true},
                        "detail": {"message": {"comp1": {"comp2": "test"}}, "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/detail/message/comp1/comp2"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("delete", options=options)
        self.assertTrue(res)
        self.assertIn("comp2", resp.json["detail"]["message"]["comp1"])
        self.assertIn("result", resp.json)

        # Invalid JSON pointer will cause a log warning but will not change the response
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/notexist"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("delete", options=options)
        self.assertTrue(res)
        self.assertIn("message", resp.json["detail"])
        self.assertIn("result", resp.json)

        # What happens if we have a non-json response, like in GET /token?outform=csv
        # Nothing is changed!
        csv = b"""column1, column2, column3
        column1, column2, column3
        """
        resp.data = csv
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/notexist"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("delete", options=options)
        self.assertTrue(res)
        self.assertEqual(resp.data, csv)

    def test_02_set_response(self):

        g = FakeFlaskG()
        audit_object = FakeAudit()
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response(mimetype='application/json')

        # add JSON pointer with one component
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/something",
                                        "value": "special",
                                        "type": "string"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual(resp.json["something"], "special")

        # add JSON pointer with two components
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/detail/something",
                                        "value": "special",
                                        "type": "string"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual(resp.json["detail"]["something"], "special")

        # change JSON pointer with two components
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/detail/message",
                                        "value": "special",
                                        "type": "string"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual(resp.json["detail"]["message"], "special")

        # add the components, that do not yet exist
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/comp1/comp2/comp3",
                                        "value": "1",
                                        "type": "bool"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual(resp.json["comp1"]["comp2"]["comp3"], True)

        # JSON pointer with more than 3 components not supported
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/comp1/comp2/comp3/comp4",
                                        "value": "1",
                                        "type": "integer"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertNotIn("comp1", resp.json)

        # Wrong type declaration
        resp.data = """{"result": {"value": true}, "detail": {"message": "Du", "error": 1}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"JSON pointer": "/comp1/comp2",
                                        "value": "notint",
                                        "type": "integer"}
                                   }
                   }
        r_handler = ResponseManglerEventHandler()
        res = r_handler.do("set", options=options)
        self.assertTrue(res)
        self.assertEqual(resp.json["comp1"]["comp2"], "notint")


class TokenEventTestCase(MyTestCase):

    def test_01_set_tokenrealm(self):
        # check actions
        actions = TokenEventHandler().actions
        self.assertTrue("set tokeninfo" in actions, actions)

        # check positions
        pos = TokenEventHandler().allowed_positions
        self.assertEqual(set(pos), {"post", "pre"}, pos)

        # setup realms
        self.setUp_user_realms()
        self.setUp_user_realm2()

        init_token({"serial": "SPASS01", "type": "spass"})

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # Now the initiailized token will be set in realm2
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"realm": "realm2"}
                                   }
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_TOKENREALM, options=options)
        self.assertTrue(res)

        # Check if the token is contained in realm2
        realms = get_realms_of_token("SPASS01")
        self.assertTrue("realm2" in realms)
        remove_token("SPASS01")

    def test_02_delete(self):
        # setup realms
        self.setUp_user_realms()
        self.setUp_user_realm2()

        init_token({"serial": "SPASS01", "type": "spass"})

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # Now the initiailized token will be set in realm2
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.DELETE, options=options)
        self.assertTrue(res)

        # Check if the token does not exist anymore
        s = get_tokens(serial="SPASS01")
        self.assertFalse(s)

    def test_03_enable_disable(self):
        # setup realms
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"})

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # Now the initiailized token will be set in realm2
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.DISABLE, options=options)
        self.assertTrue(res)
        # Check if the token does not exist anymore
        t = get_tokens(serial="SPASS01")
        self.assertFalse(t[0].is_active())

        res = t_handler.do(ACTION_TYPE.ENABLE, options=options)
        self.assertTrue(res)
        # Check if the token does not exist anymore
        t = get_tokens(serial="SPASS01")
        self.assertTrue(t[0].is_active())

        remove_token("SPASS01")

    def test_04_unassign(self):
        # setup realms
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"},
                   User("cornelius", self.realm1))
        t = get_tokens(serial="SPASS01")
        uid = t[0].get_user_id()
        self.assertEqual(uid, "1000")

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # Now the initialized token will be set in realm2
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.UNASSIGN, options=options)
        self.assertTrue(res)
        # Check if the token was unassigned
        t = get_tokens(serial="SPASS01")
        uid = t[0].get_user_id()
        self.assertEqual(uid, "")

        remove_token("SPASS01")

    def test_05_enroll(self):
        # setup realms
        self.setUp_user_realms()

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        user_obj = User("cornelius", self.realm1)
        req.User = user_obj
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # A new paper token will be created and assigned to cornelius
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "paper",
                                        "user": "1"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="paper")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        remove_token(t.token.serial)

        # Enroll an SMS token
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "sms",
                                        "user": "1"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="sms")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        self.assertEqual(t.get_tokeninfo("phone"), user_obj.info.get("mobile"))
        remove_token(t.token.serial)

        # Enroll an Email token
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "email",
                                        "user": "1"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="email")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        self.assertEqual(t.get_tokeninfo("email"), user_obj.info.get("email"))
        remove_token(t.token.serial)

        # Enroll an mOTP token
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "motp",
                                        "user": "1",
                                        "motppin": "1234"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="motp")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        remove_token(t.token.serial)

        # Enroll an SMS token
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "sms",
                                        "user": "1",
                                        "dynamic_phone": "1"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="sms")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        self.assertTrue(is_true(t.get_tokeninfo("dynamic_phone")))
        remove_token(t.token.serial)

        # Enroll a dynamic email token
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "email",
                                        "user": "1",
                                        "dynamic_email": "1"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="email")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        self.assertTrue(is_true(t.get_tokeninfo("dynamic_email")))
        remove_token(t.token.serial)

        # Enroll an email token to a user, who has no email address
        user_obj_no_email = User("shadow", self.realm1)
        req.User = user_obj_no_email
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "email",
                                        "user": "1"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="email")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj_no_email)
        self.assertEqual(t.get_tokeninfo("email"), "")
        remove_token(t.token.serial)

        # Enroll a totp token with genkey
        req.User = user_obj
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "totp",
                                        "user": "1",
                                        "additional_params": "{'totp.hashlib': 'sha256'}"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="totp")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        self.assertEqual(t.get_tokeninfo("totp.hashlib"), "sha256")
        remove_token(t.token.serial)

    def test_06_set_description(self):
        # setup realms
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"},
                   User("cornelius", self.realm1))
        t = get_tokens(serial="SPASS01")
        uid = t[0].get_user_id()
        self.assertEqual(uid, "1000")

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # Now the initialized token will be set in realm2
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {
                       "description": "New Description"
                   }}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_DESCRIPTION, options=options)
        self.assertTrue(res)
        # Check if the token was unassigned
        t = get_tokens(serial="SPASS01")
        self.assertEqual(t[0].token.description, "New Description")

        # Now the initialized token will be to a date in the future
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {
                       "description": "valid for {now}+5d you know"
                   }}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_DESCRIPTION, options=options)
        self.assertTrue(res)
        # Check if the token was unassigned
        t = get_tokens(serial="SPASS01")
        self.assertTrue(t[0].token.description.startswith("valid for 20"))
        self.assertTrue(t[0].token.description.endswith("0 you know"))

        remove_token("SPASS01")

    def test_07_set_validity(self):
        # setup realms
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"},
                   User("cornelius", self.realm1))
        t = get_tokens(serial="SPASS01")
        uid = t[0].get_user_id()
        self.assertEqual(uid, "1000")

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # The token will be set to be valid in 10 minutes for 10 days
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {VALIDITY.START: "+10m",
                                               VALIDITY.END: "+10d"}
                                   }
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_VALIDITY, options=options)
        self.assertTrue(res)
        # Check if the token has the correct validity period
        t = get_tokens(serial="SPASS01")
        end = t[0].get_validity_period_end()
        start = t[0].get_validity_period_start()
        d_end = parse_date_string(end)
        d_start = parse_date_string(start)
        self.assertTrue(datetime.now(tzlocal()) + timedelta(minutes=9) < d_start)
        self.assertTrue(datetime.now(tzlocal()) + timedelta(days=9) < d_end)
        self.assertTrue(datetime.now(tzlocal()) + timedelta(days=11) > d_end)

        remove_token("SPASS01")

    def test_08_set_count_window(self):
        # setup realms
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"},
                   User("cornelius", self.realm1))
        t = get_tokens(serial="SPASS01")
        uid = t[0].get_user_id()
        self.assertEqual(uid, "1000")

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # The count window of the token will be set to 123
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"count window": "123"}
                                   }
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_COUNTWINDOW, options=options)
        self.assertTrue(res)
        # Check if the token has the correct sync window
        t = get_tokens(serial="SPASS01")
        sw = t[0].get_count_window()
        self.assertEqual(sw, 123)

        remove_token("SPASS01")

    def test_09_set_delete_tokeninfo(self):
        # setup realms
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"},
                   User("cornelius", self.realm1))
        t = get_tokens(serial="SPASS01")
        uid = t[0].get_user_id()
        self.assertEqual(uid, "1000")

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # The tokeninfo timeWindow will be set to 33000
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"key": "timeWindow",
                                               "value": "33000"}
                                   }
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_TOKENINFO, options=options)
        self.assertTrue(res)
        # Check if the token has the correct sync window
        t = get_tokens(serial="SPASS01")
        tw = t[0].get_tokeninfo("timeWindow")
        self.assertEqual(tw, "33000")

        # Set token info into past
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"key": "pastText",
                                               "value": "it was {"
                                                        "current_time}-12h..."}
                                   }
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_TOKENINFO, options=options)
        self.assertTrue(res)
        # Check if the token has the correct sync window
        t = get_tokens(serial="SPASS01")
        tw = t[0].get_tokeninfo("pastText")
        self.assertTrue(tw.startswith("it was 20"))
        self.assertTrue(tw.endswith("0..."))
        ti0 = t[0].get_tokeninfo()

        # Delete non existing token
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"key": "SomeNonExistingKey"}
                                   }
                   }
        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.DELETE_TOKENINFO, options=options)
        self.assertTrue(res)
        # Check if the token info was deleted
        t = get_tokens(serial="SPASS01")
        ti1 = t[0].get_tokeninfo()
        self.assertEqual(ti0, ti1)

        # Delete token info "pastText"
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"key": "pastText"}
                                   }
                   }
        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.DELETE_TOKENINFO, options=options)
        self.assertTrue(res)
        # Check if the token info was deleted
        t = get_tokens(serial="SPASS01")
        tw = t[0].get_tokeninfo("pastText", "key not found")
        self.assertEqual(tw, "key not found")

        remove_token("SPASS01")

    def test_10_set_failcounter(self):
        # setup realms
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"},
                   User("cornelius", self.realm1))
        t = get_tokens(serial="SPASS01")
        uid = t[0].get_user_id()
        self.assertEqual(uid, "1000")

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # The token faile counter will be set to 7
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"fail counter": "7"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_FAILCOUNTER, options=options)
        self.assertTrue(res)
        # Check if the token has the correct sync window
        t = get_tokens(serial="SPASS01")
        tw = t[0].get_failcount()
        self.assertEqual(tw, 7)

        remove_token("SPASS01")

    def test_11_set_random_pin(self):
        # setup realms
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"},
                   User("cornelius", self.realm1))
        t = get_tokens(serial="SPASS01")
        uid = t[0].get_user_id()
        self.assertEqual(uid, "1000")

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "SPASS01"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        resp = Response(mimetype='application/json')
        resp.data = """{"result": {"value": true}}"""

        # The token will get a random pin of 8
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"length": "8"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_RANDOM_PIN, options=options)
        self.assertTrue(res)
        # Check, if we have a pin
        self.assertIn("pin", resp.json["detail"])
        pin = resp.json["detail"]["pin"]
        self.assertEqual(len(pin), 8)

        # Check if the new PIN will authenticate with the SPass token
        r, _counter, _reply = t[0].authenticate(pin)
        self.assertTrue(r)

        remove_token("SPASS01")


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

        g.logged_in_user = {"username": "admin",
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
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"emailconfig": "myserver"}
                                   }
                   }

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

        g.logged_in_user = {"username": "admin",
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
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"smsconfig": "myGW"}
                                   }
                   }

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendsms", options=options)
        self.assertTrue(res)

    def test_04_conditions(self):
        c = UserNotificationEventHandler().conditions
        self.assertTrue("logged_in_user" in c)
        self.assertTrue("result_value" in c)

    @smtpmock.activate
    def test_05_check_conditions(self):

        uhandler = UserNotificationEventHandler()
        resp = Response()
        # The actual result_status is false and the result_value is false.
        resp.data = """{"result": {"value": false, "status": false}}"""
        builder = EnvironBuilder(method='POST')
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {}
        req.User = User()
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"logged_in_user": "admin"}},
             "response": resp,
             "request": req})
        self.assertEqual(r, False)

        # We expect the result_value to be True, but it is not.
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"result_value": "True"}},
             "response": resp,
             "request": req})
        self.assertEqual(r, False)

        # We expect the result_value to be False, and it is.
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"result_value": "False"}},
             "response": resp,
             "request": req})
        self.assertEqual(r, True)

        # We expect the result_status to be True, but it is not!
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"result_status": "True"}},
             "response": resp,
             "request": req})
        self.assertEqual(r, False)

        # We expect the result_status to be False, and it is!
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"result_status": "False"}},
             "response": resp,
             "request": req})
        self.assertEqual(r, True)

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
        options = {"g": {},
                   "handler_def": {"conditions": {"token_locked": "True"}},
                   "response": resp,
                   "request": req
                   }
        r = uhandler.check_condition(options)
        # now locked
        self.assertEqual(r, True)

        # check the do action.
        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"
        g.audit_object = audit_object
        options = {"g": g,
                   "handler_def": {"conditions": {"token_locked": "True"},
                                   "options": {"emailconfig": "myserver"}},
                   "response": resp,
                   "request": req
                   }

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        r = uhandler.do("sendmail", options=options)
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
        req.User = User("cornelius", "realm1")
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

        # Check condition resolver
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"resolver": "resolver1"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"resolver": "resolver2"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

    @smtpmock.activate
    def test_07_locked_token_wrong_pin(self):
        tok = init_token({"serial": "lock2", "type": "spass",
                          "pin": "pin"}, user=User("cornelius", "realm1"))
        # lock it
        tok.set_failcount(10)

        uhandler = UserNotificationEventHandler()
        resp = Response()
        resp.data = """{"result": {"value": false}}"""
        builder = EnvironBuilder(method='POST')
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius", "pass": "wrong"}
        req.User = User("cornelius", self.realm1)
        # check the do action.
        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = None
        g.audit_object = audit_object
        g.client_ip = "127.0.0.1"
        options = {"g": g,
                   "handler_def": {"conditions": {"token_locked": "True"},
                                   "options": {"emailconfig": "myserver"}},
                   "response": resp,
                   "request": req
                   }

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        r = uhandler.check_condition(options)
        self.assertEqual(r, True)

        r = uhandler.do("sendmail", options=options)
        self.assertEqual(r, True)

    @smtpmock.activate
    def test_08_check_conditions_serial(self):
        uhandler = UserNotificationEventHandler()
        # check a serial with regexp
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "serial": "OATH123456"}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"serial": "^OATH.*"}},
             "request": req,
             "response": resp
             }
        )
        # Serial matches the regexp
        self.assertEqual(r, True)

    def test_09_check_conditions_tokenrealm(self):
        uhandler = UserNotificationEventHandler()
        # check if tokenrealm is contained
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        tok = init_token({"serial": "oath1234", "type": "spass"},
                         user=User("cornelius", "realm1"))

        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "serial": "oath1234"}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"tokenrealm": "realm1,realm2,"
                                                          "realm3"}},
             "request": req,
             "response": resp
             }
        )
        # realm matches
        self.assertEqual(r, True)

        # test condition tokenresolver
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"tokenresolver": "resolver1,reso2"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"tokenresolver": "reso2,reso3"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

    def test_10_check_conditions_tokentype(self):
        uhandler = UserNotificationEventHandler()
        # check if tokenrealm is contained
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        tok = init_token({"serial": "oath1234", "type": "spass"},
                         user=User("cornelius", "realm1"))

        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "serial": "oath1234"}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {"tokentype": "totp,spass,oath,"}},
             "request": req,
             "response": resp
             }
        )
        # Serial matches the regexp
        self.assertEqual(r, True)

    def test_10_check_conditions_token_has_owner(self):
        uhandler = UserNotificationEventHandler()
        # check if tokenrealm is contained
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        tok = init_token({"serial": "oath1234", "type": "spass"},
                         user=User("cornelius", "realm1"))

        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "serial": "oath1234"}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKEN_HAS_OWNER: "True"}},
             "request": req,
             "response": resp
             }
        )
        # Token has an owner
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKEN_HAS_OWNER: "False"}},
             "request": req,
             "response": resp
             }
        )
        # Token has an owner, but the condition is wrong
        self.assertEqual(r, False)

        # unassign token, no owner
        unassign_token("oath1234")
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {
                 "conditions": {CONDITION.TOKEN_HAS_OWNER: "False"}},
             "request": req,
             "response": resp
             }
        )
        # The condition was, token-not-assigned and the token has no user
        self.assertEqual(r, True)

    def test_10_check_conditions_token_validity_period(self):
        uhandler = UserNotificationEventHandler()
        serial = "spass01"
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        tok = init_token({"serial": serial,
                          "type": "spass"},
                          user=User("cornelius", "realm1"))

        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "serial": serial}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # token is within validity period
        r = uhandler.check_condition(
            {"g": {},
             "request": req,
             "response": resp,
             "handler_def": {
                 "conditions": {CONDITION.TOKEN_VALIDITY_PERIOD: "True"}}
             }
        )
        self.assertEqual(r, True)

        # token is outside validity period
        end_date = datetime.now(tzlocal()) - timedelta(1)
        end = end_date.strftime(DATE_FORMAT)
        tok.set_validity_period_end(end)
        r = uhandler.check_condition(
            {"g": {},
             "request": req,
             "response": resp,
             "handler_def": {
                 "conditions": {CONDITION.TOKEN_VALIDITY_PERIOD: "True"}}
             }
        )
        self.assertEqual(r, False)

        # token is outside validity period but we check for invalid token
        r = uhandler.check_condition(
            {"g": {},
             "request": req,
             "response": resp,
             "handler_def": {
                 "conditions": {CONDITION.TOKEN_VALIDITY_PERIOD: "False"}}
             }
        )
        self.assertEqual(r, True)

        remove_token(serial)

    def test_10_check_conditions_token_is_orphaned(self):
        uhandler = UserNotificationEventHandler()
        serial = "orphaned1"
        # check if tokenrealm is contained
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        # Assign a non-existing user to the token
        tok = init_token({"serial": serial, "type": "spass"})
        r = TokenOwner(token_id=tok.token.id, resolver=self.resolvername1,
                       realmname=self.realm1, user_id="123981298").save()
        self.assertTrue(r > 0)

        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"serial": serial}
        req.User = User()
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.TOKEN_IS_ORPHANED: "True"}},
             "request": req,
             "response": resp
             }
        )
        # Token has an owner assigned, but this user does not exist
        # -> token is orphaned
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {
                 "conditions": {CONDITION.TOKEN_IS_ORPHANED: "False"}},
             "request": req,
             "response": resp
             }
        )

        # Token is orphaned, but we check for non-orphaned tokens.
        self.assertEqual(r, False)

        # Unassign any user from this token - we need to do this, since the token can have more users.
        unassign_token(tok.token.serial)
        self.assertEqual(tok.token.first_owner, None)
        # Set an existing user for the token.
        tok.add_user(User("cornelius", "realm1"))
        self.assertEqual(tok.token.first_owner.user_id, "1000")
        self.assertEqual(tok.token.first_owner.realm.name, "realm1")

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {
                 "conditions": {CONDITION.TOKEN_IS_ORPHANED: "False"}},
             "request": req,
             "response": resp
             }
        )

        # Token is not orphaned
        self.assertEqual(r, True)

        remove_token(serial)

    @smtpmock.activate
    def test_11_extended_body_tags(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"

        g.logged_in_user = {"username": "admin",
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
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true},
        "detail": {"registrationcode": "12345678910"}
        }
        """
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "your {registrationcode}",
                                   "emailconfig": "myserver"}}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

    @smtpmock.activate
    def test_12_send_to_email(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"

        g.logged_in_user = {"username": "admin",
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
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true},
        "detail": {"registrationcode": "12345678910"}
        }
        """
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "your {registrationcode}",
                                   "emailconfig": "myserver",
                                   "To": NOTIFY_TYPE.EMAIL,
                                   "To "+NOTIFY_TYPE.EMAIL:
                                       "recp@example.com"}}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)


    @smtpmock.activate
    def test_12_send_to_internal_admin(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"

        g.logged_in_user = {"username": "admin",
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
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true},
        "detail": {"registrationcode": "12345678910"}
        }
        """

        # Test with non existing admin
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "your {registrationcode}",
                                   "emailconfig": "myserver",
                                   "To": NOTIFY_TYPE.INTERNAL_ADMIN,
                                   "To " + NOTIFY_TYPE.INTERNAL_ADMIN:
                                       "super"}}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

        # Test with existing admin
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "your {registrationcode}",
                                   "emailconfig": "myserver",
                                   "To": NOTIFY_TYPE.INTERNAL_ADMIN,
                                   "To " + NOTIFY_TYPE.INTERNAL_ADMIN:
                                       "testadmin"}}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

    @smtpmock.activate
    def test_13_send_to_logged_in_user(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"

        g.logged_in_user = {"username": "testadmin",
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
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true},
        "detail": {"registrationcode": "12345678910"}
        }
        """

        # Test with non existing admin
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "your {registrationcode}",
                                   "emailconfig": "myserver",
                                   "To": NOTIFY_TYPE.LOGGED_IN_USER}}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

        # Now send the mail to a logged in user from a realm
        g.logged_in_user = {"username": "cornelius",
                            "role": "user",
                            "realm": "realm1"}
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "your {registrationcode}",
                                   "emailconfig": "myserver",
                                   "To": NOTIFY_TYPE.LOGGED_IN_USER}}}
        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

    @smtpmock.activate
    def test_14_send_to_adminrealm(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"

        g.logged_in_user = {"username": "testadmin",
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
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true},
        "detail": {"registrationcode": "12345678910"}
        }
        """

        # send email to user in adminrealm "realm1"
        # Although this is no admin realm, but this realm contains some email
        #  addresses.
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "your {registrationcode}",
                                   "emailconfig": "myserver",
                                   "To": NOTIFY_TYPE.ADMIN_REALM,
                                   "To "+NOTIFY_TYPE.ADMIN_REALM:
                                       "realm1"}}}
        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

    def test_15_unassign_missing_user(self):
        """
        Unassign a token from a user that does not exist anymore.

        There is a token which is owned by a user, who was deleted fromt he
        userstore.
        An Event Handler, to notifiy the user via email on unassign is defined.
        This testcase must NOT throw an exception. Well, the user can not be
        notified anymore, since the email also does not exist in the
        userstore anymore.
        """
        # Create admin authentication token
        self.authenticate()
        # Create our realm and resolver
        parameters = {'resolver': "notify_resolver",
                      "type": "sqlresolver",
                      'Driver': 'sqlite',
                      'Server': '/tests/testdata/',
                      'Database': "testuser.sqlite",
                      'Table': 'users',
                      'Encoding': 'utf8',
                      'Editable': True,
                      'Map': '{ "username": "username", \
                        "userid" : "id", \
                        "email" : "email", \
                        "surname" : "name", \
                        "givenname" : "givenname", \
                        "password" : "password", \
                        "phone": "phone", \
                        "mobile": "mobile"}'
                      }
        r = save_resolver(parameters)
        self.assertTrue(r)

        success, fail = set_realm("notify_realm", ["notify_resolver"])
        self.assertEqual(len(success), 1)
        self.assertEqual(len(fail), 0)

        # Create a user
        ## First delete it, in case the user exist
        User("notify_user", "notify_realm").delete()
        uid = create_user("notify_resolver", {"username": "notify_user"})
        self.assertTrue(uid)
        user = User("notify_user", "notify_realm")
        self.assertEqual(user.login, "notify_user")
        self.assertEqual(user.realm, "notify_realm")

        # Create a token for this user
        r = init_token({"type": "spass",
                        "serial": "SPNOTIFY"}, user=user)
        self.assertTrue(r)

        # create notification handler
        eid = set_event("This definition sends emails", "token_unassign",
                        "UserNotification", "sendmail", position="post")
        self.assertTrue(eid)

        # delete the user
        r = user.delete()
        self.assertTrue(r)

        # unassign the token from the non-existing user
        # call the notification handler implicitly
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={"serial": "SPNOTIFY"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)

        # Cleanup
        delete_event(eid)
        delete_realm("notify_realm")
        delete_resolver("notify_resolver")
        remove_token("SPNOTIFY")

    def test_16_check_conditions_user_num_tokens(self):
        # prepare
        user = User("cornelius", "realm1")
        remove_token(user=user)
        uhandler = UserNotificationEventHandler()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        tok = init_token({"serial": "oath1234", "type": "spass"},
                         user=user)

        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "serial": "oath1234"}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        # Do checking
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.USER_TOKEN_NUMBER: "1"}},
             "request": req,
             "response": resp
             }
        )
        # The user has one token
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.USER_TOKEN_NUMBER: "2"}},
             "request": req,
             "response": resp
             }
        )
        # The user has not two tokens!
        self.assertEqual(r, False)

        remove_token("oath1234")

    def test_17_check_conditions_otp_counter(self):
        # prepare
        serial = "spass01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        uhandler = UserNotificationEventHandler()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        tok = init_token({"serial": serial, "type": "spass",
                          "otppin": "spass"},
                         user=user)
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "serial": serial}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        # Do checking
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.OTP_COUNTER: "1"}},
             "request": req,
             "response": resp
             }
        )
        # The counter of the token is 0
        self.assertEqual(r, False)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.OTP_COUNTER: "0"}},
             "request": req,
             "response": resp
             }
        )
        # The counter of the token is 0
        self.assertEqual(r, True)

        # match if counter is >100
        tok.token.count = 101
        tok.token.save()

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.OTP_COUNTER: ">100"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.OTP_COUNTER: "<100"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

        remove_token(serial)

    def test_18_check_conditions_last_auth(self):
        # prepare
        serial = "spass01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        uhandler = UserNotificationEventHandler()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1"},
                                 headers={})

        tok = init_token({"serial": serial, "type": "spass",
                          "otppin": "spass"},
                         user=user)
        # Add last authentication
        tok.add_tokeninfo(ACTION.LASTAUTH, "2016-10-10 10:10:10.000")
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "serial": serial}
        req.User = User("cornelius", "realm1")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        # Do checking
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.LAST_AUTH: "1h"}},
             "request": req,
             "response": resp
             }
        )
        # the last authentication is longer than one hour ago
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.LAST_AUTH: "100y"}},
             "request": req,
             "response": resp
             }
        )
        # The last authentication is not longer than 100 years ago
        self.assertEqual(r, False)

        remove_token(serial)

    @smtpmock.activate
    def test_19_sendmail_escape_html(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        # Set a user agent with HTML tags
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={"User-Agent": "<b>agent</b>"})

        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SomeSerial",
                        "user": "cornelius"}
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        # If we send a plain email, we do not escape HTML
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"emailconfig": "myserver",
                                        "body": "{ua_string} performed an action for {user}"}
                                   }
                   }

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        payload = to_unicode(parsed_email.get_payload(decode=True))
        self.assertEqual(parsed_email.get_content_type(), "text/plain")
        self.assertIn("<b>agent</b>", payload)
        # If we send a HTML email, we do escape HTML
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"emailconfig": "myserver",
                                        "mimetype": "html",
                                        "body": "{ua_string} performed an action for {user}"}
                                   }
                   }
        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        payload = to_unicode(parsed_email.get_payload(decode=True))
        self.assertEqual(parsed_email.get_content_type(), "text/html")
        self.assertIn("&lt;b&gt;agent&lt;/b&gt;", payload)
        self.assertNotIn("<b>", payload)

    @smtpmock.activate
    def test_20_sendmail_googleurl(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"recp@example.com": (200, "OK")},
                         support_tls=False)

        g = FakeFlaskG()
        audit_object = FakeAudit()
        audit_object.audit_data["serial"] = "123456"

        g.logged_in_user = {"username": "admin",
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
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{
    "detail": {
        "googleurl": {
            "description": "URL for google Authenticator",
            "img": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAeoAAAHqAQAAAADjFjCXAAAD+UlEQVR4nO2dTYrkSAxGn8aGWtowB6ij2Dcb5khzA/soeYABe9lgo1mE4qeKphdpN901+WlRpDP9iEwQUnySHGXOBVv/uEKDcOHChQsXLly48HtxC+sxG08DTmMdT7N5N7M5XUK6NDOz+b7Vhb8ajru7M7m7+9a5ux/A4O7L4MlgOIhP0y2ZWL70bxf+q/G9hC/AF05j2oDVenyhc7MxPjWz/ubVhb82bvP+loopZmaRa+E0Jj9++urCXxRf3w/sr0dPinUM7jbvPbGv+8mrC38pfHD3Jb08jfX9AIYjuZ4vdO4Lp/kCxNbvztWFvxYeaiKsc6btx3/yrVITwp83/2jx7nDgy3BEmHOPV6F1i8nrhD9ltQ6SAtm0dQ4ppXYOg5cI1xWfVOVE+BXLNZB9hPXdgf00Zx+NyU9z9v5wdmD650+A7gDOjH3p3y78V+E5w6YSMKTacMmmNddmwREBTxlW+AWrXhdpNvsakWYhXA+K/x1SE8KvWNYQJdYVXytFk6ph0y3uh2Kd8CsWamLLyoEP3dcqM1I4BGCS1wm/Zp81bOtrXeOEtfsPpYYirxP+lDX7uhrrlrJzSyl1gybDlmEUeZ3w56zNpnWWaQtfayRtEhfDoX2d8JtiXXhTqf7WzR0Q83X1EqRhhd+A7z0xWmJmsFsaHnb3A6ZHX6bqIuDdu7rw18LbDFtGhnNbLJSrL4N7Uq5Lqdwpwwq/iMdG7tFjM3WWuHObAaaHmf9dJ4hvXl34q+Fl5qQEsqJhS5O/zncmwbEM6v4Lv2TV66iTJuFckU2hvgdo5kT4LXh6FGfyA5vTgxIAlIrwRp5gH0JchP/9Dl9e+JfD017N1/nNYR9x9hEYDizy6oav798Mhn/NAQekYYVfstybIPdXPza+ylhA06pN05/KsMIv4uvYOexvbvZ+NAnXF04zG6Hd5qleJ/ya5Z5D6fRnlRoNio3y8ES5VB9W+DWLPtjGh+pveUai1Ivb6ROX1wm/Be/c5sGddQwNm1NqPPbvyx5n7+jECeE3qgnIw8PU0ZKt1PCaS3XEhN+FRx/iNKZHnw7WSQU6hm8p/sURO8OBzXevLvx18NL9d8/P43gefKq6glpIgTr4pFgn/Dn7pA/qmRLRbt1ywi3d13S6k+p1wp+3XDkB2rJw5zQH69SZz3LYibxO+PMW3uS5VFeH1yP1Hm01ZSplFmVY4c9bk1dLNo2QlhJpnvRsTFVi4bfi7o+3dFYdq/WkLtlMlRmhOmz+GasLf1G8qRLTOevId47pLMNQv9mXF/418O+ewd6UT+qJE/XozhhQUYYV/qx91rBTVg5VvjaVkxgjVr1O+BUz/fc64cKFCxcuXLjw/wX+HzgPbUakdjuaAAAAAElFTkSuQmCC",
            "value": "otpauth://hotp/OATH0001D8B6?secret=GQROHTUPBAK5N6T2HBUK4IP42R56EMV3&counter=1&digits=6&issuer=privacyIDEA"
        },
        "rollout_state": "",
        "serial": "OATH0001D8B6",
        "threadid": 140437172639168
    },
    "id": 1,
    "jsonrpc": "2.0",
    "result": {
        "status": true,
        "value": true
    },
    "signature": "foo",
    "time": 1561549651.093083,
    "version": "privacyIDEA 3.0.1.dev2",
    "versionnumber": "3.0.1.dev2"
}
"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "<img src='{googleurl_img}' />",
                                   "mimetype": "html",
                                   "emailconfig": "myserver"}}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        payload = to_unicode(parsed_email.get_payload(decode=True))
        self.assertEqual(parsed_email.get_content_type(), "text/html")
        # Check that the base64-encoded image does not get mangled
        self.assertEqual(payload,
                         "<img src='data:image/png;base64,"
                         "iVBORw0KGgoAAAANSUhEUgAAAeoAAAHqAQAAAADjFjCXAAAD+UlEQVR4nO2dTYrkSAxGn8aGWtowB6ij2Dcb5khzA"
                         "/soeYABe9lgo1mE4qeKphdpN901+WlRpDP9iEwQUnySHGXOBVv/uEKDcOHChQsXLly48HtxC"
                         "+sxG08DTmMdT7N5N7M5XUK6NDOz+b7Vhb8ajru7M7m7+9a5ux/A4O7L4MlgOIhP0y2ZWL70bxf+q/G9hC"
                         "/AF05j2oDVenyhc7MxPjWz/ubVhb82bvP+loopZmaRa+E0Jj9++urCXxRf3w/sr0dPinUM7jbvPbGv"
                         "+8mrC38pfHD3Jb08jfX9AIYjuZ4vdO4Lp/kCxNbvztWFvxYeaiKsc6btx3/yrVITwp83"
                         "/2jx7nDgy3BEmHOPV6F1i8nrhD9ltQ6SAtm0dQ4ppXYOg5cI1xWfVOVE+BXLNZB9hPXdgf00Zx+NyU9z9v5wdmD650"
                         "+A7gDOjH3p3y78V+E5w6YSMKTacMmmNddmwREBTxlW+AWrXhdpNvsakWYhXA+K"
                         "/x1SE8KvWNYQJdYVXytFk6ph0y3uh2Kd8CsWamLLyoEP3dcqM1I4BGCS1wm/Zp81bOtrXeOEtfsPpYYirxP"
                         "+lDX7uhrrlrJzSyl1gybDlmEUeZ3w56zNpnWWaQtfayRtEhfDoX2d8JtiXXhTqf7WzR0Q83X1EqRhhd"
                         "+A7z0xWmJmsFsaHnb3A6ZHX6bqIuDdu7rw18LbDFtGhnNbLJSrL4N7Uq5Lqdwpwwq"
                         "/iMdG7tFjM3WWuHObAaaHmf9dJ4hvXl34q+Fl5qQEsqJhS5O"
                         "/zncmwbEM6v4Lv2TV66iTJuFckU2hvgdo5kT4LXh6FGfyA5vTgxIAlIrwRp5gH0JchP/9Dl9e+JfD017N1"
                         "/nNYR9x9hEYDizy6oav798Mhn/NAQekYYVfstybIPdXPza+ylhA06pN05/KsMIv4uvYOexvbvZ"
                         "+NAnXF04zG6Hd5qleJ/ya5Z5D6fRnlRoNio3y8ES5VB9W+DWLPtjGh+pveUai1Ivb6ROX1wm/Be"
                         "/c5sGddQwNm1NqPPbvyx5n7+jECeE3qgnIw8PU0ZKt1PCaS3XEhN+FRx/iNKZHnw7WSQU6hm8p"
                         "/sURO8OBzXevLvx18NL9d8/P43gefKq6glpIgTr4pFgn/Dn7pA/qmRLRbt1ywi3d13S6k+p1wp"
                         "+3XDkB2rJw5zQH69SZz3LYibxO+PMW3uS5VFeH1yP1Hm01ZSplFmVY4c9bk1dLNo2QlhJpnvRsTFVi4bfi7o+3dFYdq"
                         "/WkLtlMlRmhOmz+GasLf1G8qRLTOevId47pLMNQv9mXF/418O+ewd6UT+qJE/XozhhQUYYV"
                         "/qx91rBTVg5VvjaVkxgjVr1O+BUz/fc64cKFCxcuXLjw/wX+HzgPbUakdjuaAAAAAElFTkSuQmCC' />")

    def test_21_save_notification(self):
        g = FakeFlaskG()
        audit_object = FakeAudit()
        g.logged_in_user = {"username": "admin",
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
        req.all_data = {"serial": "OATH123456",
                        "user": "cornelius"}
        req.User = User("cornelius", self.realm1)
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"filename": "test{serial}.txt",
                                        "body": "{serial}, {user}"}
                                   }
                   }
        # remove leftover file from the last test run, if any
        if os.path.exists("tests/testdata/testOATH123456.txt"):
            os.remove("tests/testdata/testOATH123456.txt")
        un_handler = UserNotificationEventHandler()
        res = un_handler.do("savefile", options=options)
        self.assertTrue(res)
        # check, if the file was written with the correct contents
        with open("tests/testdata/testOATH123456.txt") as f:
            l = f.read()
        self.assertEqual(l, "OATH123456, Cornelius")
        os.remove("tests/testdata/testOATH123456.txt")

        # Check what happens if we try to write outside of spooldir
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"filename": "../../../test{serial}.txt",
                                        "body": "{serial}, {user}"}
                                   }
                   }

        un_handler = UserNotificationEventHandler()
        # Check that an error is written to the logfile
        with mock.patch("logging.Logger.error") as mock_log:
            un_handler.do("savefile", options=options)
            mock_log.assert_called_once_with("Cannot write outside of spooldir tests/testdata/!")

        # Check what happens if the file can not be written
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"filename": "test{serial}.txt",
                                        "body": "{serial}, {user}"}
                                   }
                   }

        # create a file, that is not writable
        with open("tests/testdata/testOATH123456.txt", "w") as f:
            f.write("empty")
        os.chmod("tests/testdata/testOATH123456.txt", 0o400)
        un_handler = UserNotificationEventHandler()
        # Check that an error is written to the logfile
        with mock.patch("logging.Logger.error") as mock_log:
            un_handler.do("savefile", options=options)
            call_args = mock_log.call_args
            # ensure log.error was actually called ...
            self.assertIsNotNone(call_args)
            # ... with the right message
            self.assertTrue(call_args[0][0].startswith("Failed to write notification file:"))

        os.remove("tests/testdata/testOATH123456.txt")

