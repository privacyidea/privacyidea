# -*- coding: utf-8 -*-

"""
This file contains the event handlers tests. It tests:

lib/eventhandler/usernotification.py (one event handler module)
lib/event.py (the decorator)
"""
import requests.exceptions
import responses
import os
import mock

from mock import patch, MagicMock
from privacyidea.lib.eventhandler.customuserattributeshandler import (CustomUserAttributesHandler,
                                                                      ACTION_TYPE as CUAH_ACTION_TYPE)
from privacyidea.lib.eventhandler.customuserattributeshandler import USER_TYPE
from privacyidea.lib.eventhandler.webhookeventhandler import ACTION_TYPE, WebHookHandler, CONTENT_TYPE
from privacyidea.lib.eventhandler.usernotification import UserNotificationEventHandler
from privacyidea.lib.machine import list_token_machines
from .base import MyTestCase, FakeFlaskG, FakeAudit
from privacyidea.lib.config import get_config_object
from privacyidea.lib.eventhandler.tokenhandler import (TokenEventHandler,
                                                       ACTION_TYPE, VALIDITY)
from privacyidea.lib.eventhandler.scripthandler import ScriptEventHandler, SCRIPT_WAIT
from privacyidea.lib.eventhandler.counterhandler import CounterEventHandler
from privacyidea.lib.eventhandler.responsemangler import ResponseManglerEventHandler
from privacyidea.models import EventCounter
from privacyidea.lib.eventhandler.federationhandler import FederationEventHandler
from privacyidea.lib.eventhandler.requestmangler import RequestManglerEventHandler
from privacyidea.lib.eventhandler.base import BaseEventHandler, CONDITION
from privacyidea.lib.counter import increase as counter_increase
from flask import Request
from werkzeug.test import EnvironBuilder
from privacyidea.lib.event import (delete_event, set_event,
                                   EventConfiguration, get_handler_object,
                                   enable_event)
from privacyidea.lib.token import (init_token, remove_token, get_realms_of_token, get_tokens,
                                   add_tokeninfo)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.user import User
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.utils import is_true
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date_string
from dateutil.tz import tzlocal
from privacyidea.app import PiResponseClass as Response
from collections import OrderedDict


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

        # check for failcounter
        tok.set_failcount(8)
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.FAILCOUNTER: "<9"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.FAILCOUNTER: ">9"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.FAILCOUNTER: "=8"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

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

        # Check DETAIL_MESSAGE to evaluate to False if it does not exist
        resp = Response()
        resp.data = """{"result": {"value": true, "status": true},
                "detail": {"options": "Nothing"}
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

    def test_08_counter_condition(self):
        # increase a counter to 4
        for i in range(0, 4):
            counter_increase("myCounter")

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

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNTER:
                                                "myCounter<4"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNTER:
                                                "myCounter==4"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNTER:
                                                "myCounter>3"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        # If we have a nonexisting counter this should be treated as zero
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNTER:
                                                "myNonExistingCounter>3"}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.COUNTER:
                                                "myNonExistingCounter<3"}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)


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

    def test_03_sync_to_db(self):
        g = FakeFlaskG()
        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}

        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        req = Request(builder.get_environ())
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
        # first check that the db session is not synced by default
        with mock.patch('privacyidea.lib.eventhandler.scripthandler.db') as mdb:
            res = t_handler.do(script_name, options=options)
            mdb.session.commit.assert_not_called()
        self.assertTrue(res)
        # now set the parameter to sync the db session before running the script
        options['handler_def']['options']['sync_to_database'] = "1"
        with mock.patch('privacyidea.lib.eventhandler.scripthandler.db') as mdb:
            res = t_handler.do(script_name, options=options)
            mdb.session.commit.assert_called_with()
        self.assertTrue(res)
        # and now with the parameter explicitly disabled
        options['handler_def']['options']['sync_to_database'] = "0"
        with mock.patch('privacyidea.lib.eventhandler.scripthandler.db') as mdb:
            res = t_handler.do(script_name, options=options)
            mdb.session.commit.assert_not_called()
        self.assertTrue(res)


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
        req.all_data = {"user": "givenname.surname@company.com"}
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

        # Enroll an SMS token with specific SMS gateway config
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "sms",
                                        "user": "1",
                                        "sms_identifier": "mySMSGateway"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="sms")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        self.assertEqual(t.get_tokeninfo("phone"), user_obj.info.get("mobile"))
        self.assertEqual(t.get_tokeninfo("sms.identifier"), "mySMSGateway")
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

        # Enroll an Email token with specific SMTP server config
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options":
                                       {"tokentype": "email",
                                        "user": "1",
                                        "smtp_identifier": "myServer"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the token was created and assigned
        t = get_tokens(tokentype="email")[0]
        self.assertTrue(t)
        self.assertEqual(t.user, user_obj)
        self.assertEqual(t.get_tokeninfo("email"), user_obj.info.get("email"))
        self.assertEqual(t.get_tokeninfo("email.identifier"), "myServer")
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

    def test_10_set_or_change_failcounter(self):
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

        # The token fail counter will be set to 7
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"fail counter": "7"}}
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_FAILCOUNTER, options=options)
        self.assertTrue(res)
        # Check if the token has the correct fail counter
        t = get_tokens(serial="SPASS01")
        tw = t[0].get_failcount()
        self.assertEqual(tw, 7)

        # check the change failcount option starting with the set failcount of 7
        handler_options = OrderedDict([("-8", -1),
                                       ("2", 1),
                                       ("+1", 2)])
        for diff, failcount in handler_options.items():
            options["handler_def"] = {"options": {"change fail counter": diff}}
            res = t_handler.do(ACTION_TYPE.CHANGE_FAILCOUNTER, options=options)
            self.assertTrue(res)
            # Check if the token has the correct fail counter
            t = get_tokens(serial="SPASS01")
            tw = t[0].get_failcount()
            self.assertEqual(tw, failcount)

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

    def test_12_set_max_failcount(self):
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
                   "handler_def": {"options": {"max failcount": "123"}
                                   }
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.SET_MAXFAIL, options=options)
        self.assertTrue(res)
        # Check if the token has the correct sync window
        t = get_tokens(serial="SPASS01")
        fc = t[0].get_max_failcount()
        self.assertEqual(fc, 123)

        remove_token("SPASS01")

    def test_13_tokengroup(self):
        # setup realms
        self.setUp_user_realms()
        # create a tokengroup
        from privacyidea.lib.tokengroup import set_tokengroup, delete_tokengroup
        set_tokengroup("group1")

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
                   "handler_def": {"options": {"tokengroup": "group1"}
                                   }
                   }

        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.ADD_TOKENGROUP, options=options)
        self.assertTrue(res)
        # Check if the token as the group assigned
        tok = get_tokens(serial="SPASS01")[0]
        self.assertEqual(1, len(tok.token.tokengroup_list))
        tg = tok.token.tokengroup_list[0]
        self.assertEqual(tg.tokengroup.name, "group1")

        # now remove the tokengroup
        t_handler = TokenEventHandler()
        res = t_handler.do(ACTION_TYPE.REMOVE_TOKENGROUP, options=options)
        self.assertTrue(res)

        tok = get_tokens(serial="SPASS01")[0]
        self.assertEqual(0, len(tok.token.tokengroup_list))

        remove_token("SPASS01")

    def test_14_attach_token(self):
        # create token
        init_token({"serial": "offHOTP", "genkey": 1})

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
        req.all_data = {"serial": "offHOTP", "type": "hotp"}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        # The count window of the token will be set to 123
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def":{
                       "options": {
                                   "application": "offline",
                                   "count": "12"}}
                   }


        t_handler = TokenEventHandler()
        res = t_handler.do("attach application", options=options)
        self.assertTrue(res)

        # check if the options were set.
        token_obj = list_token_machines(serial="offHOTP")[0]
        self.assertEqual(token_obj.get("application"), "offline")
        self.assertEqual(token_obj.get("hostname"), "any host")
        self.assertEqual(token_obj.get("machine_id"), "any machine")


class CustomUserAttributesTestCase(MyTestCase):

    def test_01_event_set_attributes_logged_in_user(self):

        # Setup realm and user
        self.setUp_user_realms()

        user = User("hans", self.realm1)
        g = FakeFlaskG()
        g.logged_in_user = {'username': 'hans',
                            'realm': self.realm1}

        # The attributekey will be set as "test" and the attributevalue as "check"
        options = {"g": g,
                   "handler_def": {
                       "options": {"user": "logged_in_user",
                                   "attrkey": "test",
                                   "attrvalue": "check"}}
                   }
        t_handler = CustomUserAttributesHandler()
        res = t_handler.do("set_custom_user_attributes", options=options)
        self.assertTrue(res)

        # Check that the user has the correct attribute
        a = user.attributes
        self.assertIn('test', a, user)
        self.assertEqual('check', a.get('test'), user)

    def test_02_event_delete_attributes(self):

        # Setup realm and user
        self.setUp_user_realms()

        user = User("hans", self.realm1)
        g = FakeFlaskG()
        g.logged_in_user = {'username': 'hans',
                            'realm': self.realm1}
        # Setup user attribute
        ret = user.set_attribute('test', 'check')
        self.assertTrue(ret)
        a = user.attributes
        if "test" in a:
            b = a.get("test")
            self.assertEqual('check', b)

        # The eventhandler will delete the user-attribute
        options = {"g": g,
                   "attrkey": "test",
                   "attrvalue": "check",
                   "handler_def": {
                       "options": {"user": "logged_in_user"}}
                   }
        t_handler = CustomUserAttributesHandler()
        res = t_handler.do("delete_custom_user_attributes", options)
        self.assertTrue(res)

        # Check that the user attribute is deleted
        self.assertNotIn("test", user.attributes, user)

    def test_03_event_set_attributes_tokenowner(self):
        # Tokenowner is the default
        # Setup realm and user
        self.setUp_user_realms()

        init_token({"serial": "SPASS01", "type": "spass"},
                   User("cornelius", self.realm1))
        g = FakeFlaskG()
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SPASS01"},
                                 headers={})

        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SPASS01"}
        req.User = User("cornelius", self.realm1)

        # The attributekey will be set as "test" and the attributevalue as "check"
        options = {"g": g,
                   "request": req,
                   "handler_def": {"conditions": {"tokentype": "totp,spass,oath,"},
                                   "options": {"attrkey": "test",
                                               "attrvalue": "check",
                                               "user": USER_TYPE.TOKENOWNER}}}
        t_handler = CustomUserAttributesHandler()
        res = t_handler.do(CUAH_ACTION_TYPE.SET_CUSTOM_USER_ATTRIBUTES, options=options)
        self.assertTrue(res)

        # Check that the user has the correct attribute
        a = req.User.attributes
        self.assertIn('test', a, req.User)
        self.assertEqual('check', a.get('test'), req.User)

    def test_04_delete_not_existing_attribute(self):

        # Setup realm and user
        self.setUp_user_realms()

        user = User("hans", self.realm1)
        g = FakeFlaskG()
        g.logged_in_user = {'username': 'hans',
                            'realm': self.realm1}
        # Check that the attribute does not exist
        self.assertNotIn('test', user.attributes, user)

        # The eventhandler will delete the user-attribute
        options = {"g": g,
                   "handler_def": {
                       "options": {"attrkey": "test",
                                   "attrvalue": "check",
                                   "user": USER_TYPE.LOGGED_IN_USER}}
                   }
        t_handler = CustomUserAttributesHandler()
        res = t_handler.do(CUAH_ACTION_TYPE.DELETE_CUSTOM_USER_ATTRIBUTES, options)
        self.assertFalse(res)

        # Check that the user attribute is deleted
        b = user.attributes
        if "test" not in b:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

    def test_05_overwrite_existing_attribute(self):

        # Setup realm and user
        self.setUp_user_realms()

        user = User("hans", self.realm1)
        g = FakeFlaskG()
        g.logged_in_user = {'username': 'hans',
                            'realm': self.realm1}
        # Setup user attribute
        ret = user.set_attribute('test', 'old')
        self.assertTrue(ret)
        a = user.attributes
        if "test" in a:
            b = a.get("test")
            self.assertEqual('old', b)

        # The attributekey will be set as "test" and the attributevalue as "check"
        options = {"g": g,
                   "handler_def": {
                       "options": {"user": USER_TYPE.LOGGED_IN_USER,
                                   "attrkey": "test",
                                   "attrvalue": "new"}}
                   }
        t_handler = CustomUserAttributesHandler()
        res = t_handler.do(CUAH_ACTION_TYPE.SET_CUSTOM_USER_ATTRIBUTES, options=options)
        self.assertTrue(res)

        # Check that the user has the correct attribute
        a = user.attributes
        self.assertIn('test', a, user)
        self.assertEqual('new', a.get('test'), user)


class WebhookTestCase(MyTestCase):

    def setUp(self):
        super(WebhookTestCase, self).setUp()
        self.setUp_user_realms()

    @patch('requests.post')
    def test_01_send_webhook(self, mock_post):
        with mock.patch("logging.Logger.info") as mock_log:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = 'response'

            g = FakeFlaskG()
            g.logged_in_user = {'username': 'hans',
                                'realm': self.realm1}

            t_handler = WebHookHandler()
            options = {"g": g,
                       "handler_def": {
                           "options": {"URL":
                                           'http://test.com',
                                       "content_type":
                                           CONTENT_TYPE.URLENCODED,
                                       "data":
                                           'This is a test'
                                       }
                       }
                       }
            res = t_handler.do("post_webhook", options=options)
            self.assertTrue(res)
            text = 'A webhook is send to {0!r} with the text: {1!r}'.format(
                'http://test.com', 'This is a test')
            mock_log.assert_any_call(text)
            mock_log.assert_called_with(200)

            options = {"g": g,
                       "handler_def": {
                           "options": {"URL":
                                           'http://test.com',
                                       "content_type":
                                           CONTENT_TYPE.JSON,
                                       "data":
                                           'This is a test'
                                       }
                       }
                       }
            res = t_handler.do("post_webhook", options=options)
            self.assertTrue(res)
            text = 'A webhook is send to {0!r} with the text: {1!r}'.format(
                'http://test.com', 'This is a test')
            mock_log.assert_any_call(text)
            mock_log.assert_called_with(200)

    def test_02_actions_and_positions(self):
        positions = WebHookHandler().allowed_positions
        self.assertEqual(positions, ["post", "pre"])
        actions = WebHookHandler().actions
        self.assertEqual(actions, {'post_webhook': {
            "URL": {
                "type": "str",
                "required": True,
                "description": "The URL the WebHook is posted to"
            },
            "content_type": {
                "type": "str",
                "required": True,
                "description": "The encoding that is sent to the WebHook, for example json",
                "value": [
                    CONTENT_TYPE.JSON,
                    CONTENT_TYPE.URLENCODED]
            },
            "replace": {
                "type": "bool",
                "required": True,
                "description": "You can replace placeholder like {logged_in_user}"
            },
            "data": {
                "type": "str",
                "required": True,
                "description": 'The data posted in the WebHook'
            }
        }})

    def test_03_wrong_action_type(self):
        with mock.patch("logging.Logger.warning") as mock_log:
            g = FakeFlaskG()
            g.logged_in_user = {'username': 'hans',
                                'realm': self.realm1}

            t_handler = WebHookHandler()
            options = {"g": g,
                       "handler_def": {
                           "options": {"URL":
                                           'http://test.com',
                                       "content_type":
                                           CONTENT_TYPE.URLENCODED,
                                       "data":
                                           'This is a test'
                                       }
                       }
                       }
            res = t_handler.do("False_Type", options=options)
            self.assertFalse(res)
            text = 'Unknown action value: False_Type'
            mock_log.assert_any_call(text)

    def test_04_wrong_content_type(self):
        with mock.patch("logging.Logger.warning") as mock_log:
            g = FakeFlaskG()
            g.logged_in_user = {'username': 'hans',
                                'realm': self.realm1}

            t_handler = WebHookHandler()
            options = {"g": g,
                       "handler_def": {
                           "options": {"URL":
                                           'http://test.com',
                                       "content_type":
                                           'False_Type',
                                       "data":
                                           'This is a test'
                                       }
                       }
                       }
            res = t_handler.do("post_webhook", options=options)
            self.assertFalse(res)
            text = 'Unknown content type value: False_Type'
            mock_log.assert_any_call(text)

    @patch('requests.post')
    def test_05_wrong_url(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError()

        g = FakeFlaskG()
        g.logged_in_user = {'username': 'hans',
                            'realm': self.realm1}

        t_handler = WebHookHandler()
        options = {"g": g,
                   "handler_def": {
                       "options": {"URL":
                                       'http://xyz.blablba',
                                   "content_type":
                                       CONTENT_TYPE.JSON,
                                   "data":
                                       'This is a test'
                                   }
                   }
                   }
        res = t_handler.do("post_webhook", options=options)
        self.assertFalse(res)

    @patch('requests.post')
    def test_06_replace_function(self, mock_post):
        with mock.patch("logging.Logger.info") as mock_log:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = 'response'

            g = FakeFlaskG()
            g.logged_in_user = {'username': 'hans',
                                'realm': self.realm1}

            t_handler = WebHookHandler()
            options = {"g": g,
                       "handler_def": {
                           "options": {"URL":
                                           'http://test.com',
                                       "content_type":
                                           CONTENT_TYPE.URLENCODED,
                                       "replace":
                                           True,
                                       "data":
                                           'This is {logged_in_user} from realm {realm}'
                                       }
                       }
                       }
            res = t_handler.do("post_webhook", options=options)
            self.assertTrue(res)
            text = 'A webhook is send to {0!r} with the text: {1!r}'.format(
                'http://test.com', 'This is hans from realm realm1')
            mock_log.assert_any_call(text)
            mock_log.assert_called_with(200)

    @patch('requests.post')
    def test_07_replace_function_error(self, mock_post):
        with mock.patch("logging.Logger.warning") as mock_log:
            with mock.patch("logging.Logger.info") as mock_info:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = 'response'

                init_token({"serial": "SPASS01", "type": "spass"},
                           User("cornelius", self.realm1))
                g = FakeFlaskG()
                builder = EnvironBuilder(method='POST',
                                         data={'serial': "SPASS01"},
                                         headers={})

                env = builder.get_environ()
                env["REMOTE_ADDR"] = "10.0.0.1"
                g.client_ip = env["REMOTE_ADDR"]
                req = Request(env)
                req.all_data = {"serial": "SPASS01"}
                req.User = User("cornelius", self.realm1)

                t_handler = WebHookHandler()
                options = {"g": g,
                           "request": req,
                           "handler_def": {
                               "options": {"URL":
                                               'http://test.com',
                                           "content_type":
                                               CONTENT_TYPE.JSON,
                                           "replace":
                                               True,
                                           "data":
                                               '{token_serial} {token_owner} {unknown_tag}'
                                           }
                           }
                           }
                res = t_handler.do("post_webhook", options=options)
                self.assertTrue(res)
                mock_log.assert_any_call("Unable to replace placeholder: ('unknown_tag')!"
                                         " Please check the webhooks data option.")
                text = 'A webhook is send to {0!r} with the text: {1!r}'.format(
                    'http://test.com', '{token_serial} {token_owner} {unknown_tag}')
                mock_info.assert_any_call(text)
                mock_info.assert_called_with(200)

    @patch('requests.post')
    def test_08_replace_function_typo(self, mock_post):
        with mock.patch("logging.Logger.warning") as mock_log:
            with mock.patch("logging.Logger.info") as mock_info:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = 'response'

                init_token({"serial": "SPASS01", "type": "spass"},
                           User("cornelius", self.realm1))
                g = FakeFlaskG()
                builder = EnvironBuilder(method='POST',
                                         data={'serial': "SPASS01"},
                                         headers={})

                env = builder.get_environ()
                env["REMOTE_ADDR"] = "10.0.0.1"
                g.client_ip = env["REMOTE_ADDR"]
                req = Request(env)
                req.all_data = {"serial": "SPASS01"}
                req.User = User("cornelius", self.realm1)

                t_handler = WebHookHandler()
                options = {"g": g,
                           "request": req,
                           "handler_def": {
                               "options": {"URL":
                                               'http://test.com',
                                           "content_type":
                                               CONTENT_TYPE.JSON,
                                           "replace":
                                               True,
                                           "data":
                                               'The token serial is {token_seril}'
                                           }
                           }
                           }
                res = t_handler.do("post_webhook", options=options)
                self.assertTrue(res)
                mock_log.assert_any_call("Unable to replace placeholder: ('token_seril')!"
                                         " Please check the webhooks data option.")
                text = 'A webhook is send to {0!r} with the text: {1!r}'.format(
                    'http://test.com', 'The token serial is {token_seril}')
                mock_info.assert_any_call(text)
                mock_info.assert_called_with(200)
