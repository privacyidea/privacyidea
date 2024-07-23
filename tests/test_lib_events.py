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

from privacyidea.lib.container import init_container, find_container_by_serial, get_all_containers, \
    delete_container_by_serial, add_token_to_container
from privacyidea.lib.eventhandler.containerhandler import (ContainerEventHandler, ACTION_TYPE as C_ACTION_TYPE)
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
                                   add_tokeninfo, unassign_token, get_tokens_paginate)
from privacyidea.lib.tokenclass import DATE_FORMAT, CHALLENGE_SESSION
from privacyidea.models import Challenge
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

        h_obj = get_handler_object("Container")
        self.assertEqual(type(h_obj), ContainerEventHandler)


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

    def test_09_check_conditions_realm_and_resolver_value(self):
        # prepare
        # setup realms
        self.setUp_user_realms()
        self.setUp_user_realm2()

        serial = "pw01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        tok = init_token({"serial": serial,
                          "type": "pw", "otppin": "test", "otpkey": "secret"},
                         user=user)
        self.assertEqual(tok.type, "pw")

        uhandler = BaseEventHandler()

        # Checking values of the conditions
        realm_value = uhandler.conditions.get("realm").get("value")
        resolver_value = uhandler.conditions.get("resolver").get("value")
        self.assertEqual([{'name': 'realm1'}, {'name': 'realm2'}], realm_value, realm_value)
        self.assertEqual([{'name': 'resolver1'}], resolver_value, resolver_value)

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
             "handler_def": {"conditions": {CONDITION.REALM: "realm1"}},
             "request": req,
             "response": resp
             }
        )
        # Works if the realm is correct
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.REALM: "realm3"}},
             "request": req,
             "response": resp
             }
        )
        # False if the realm is incorrect
        self.assertEqual(r, False)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.RESOLVER: "resolver1"}},
             "request": req,
             "response": resp
             }
        )
        # Works if the resolver is correct
        self.assertEqual(r, True)

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.REALM: "resolver3"}},
             "request": req,
             "response": resp
             }
        )
        # False if the resolver is incorrect
        self.assertEqual(r, False)

        remove_token(serial)

    def test_10_check_challenge_session(self):
        self.setUp_user_realms()
        serial = "rs01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        tid = "1234567"
        # Prepare the token
        tok = init_token({"serial": serial,
                          "type": "pw", "otppin": "test", "otpkey": "secret"},
                         user=user)
        # Prepare a challenge
        chal = Challenge(serial=serial, session=CHALLENGE_SESSION.DECLINED, transaction_id=tid)
        chal.save()
        # One token with one declined challenge
        uhandler = BaseEventHandler()
        # Prepare a fake request
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1",
                                       "pass": "wrongvalue",
                                       "transaction_id": tid},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "pass": "wrongvalue",
                        "transaction_id": tid}
        req.User = user
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        # Check if the condition matches
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.CHALLENGE_SESSION: CHALLENGE_SESSION.DECLINED}},
             "request": req,
             "response": resp
             }
        )
        self.assertTrue(r)

        # Check if the condition does not match
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.CHALLENGE_SESSION: CHALLENGE_SESSION.ENROLLMENT}},
             "request": req,
             "response": resp
             }
        )
        self.assertFalse(r)
        # We have two declined challenges, add a 2nd one.
        chal = Challenge(serial=serial, session=CHALLENGE_SESSION.DECLINED, transaction_id=tid)
        chal.save()
        # Check if the condition matches
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.CHALLENGE_SESSION: CHALLENGE_SESSION.DECLINED}},
             "request": req,
             "response": resp
             }
        )
        # We will receive a False and a log.warning
        self.assertFalse(r)

        remove_token(serial)

    def test_11_check_challenge_expired(self):
        self.setUp_user_realms()
        serial = "rs01"
        user = User("cornelius", "realm1")
        remove_token(user=user)
        tid = "1234567"
        # Prepare the token
        tok = init_token({"serial": serial,
                          "type": "pw", "otppin": "test", "otpkey": "secret"},
                         user=user)
        # Prepare a challenge, that is not yet expired
        chal = Challenge(serial=serial, transaction_id=tid)
        chal.save()
        # One token with one declined challenge
        uhandler = BaseEventHandler()
        # Prepare a fake request
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius@realm1",
                                       "pass": "wrongvalue",
                                       "transaction_id": tid},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"user": "cornelius@realm1",
                        "pass": "wrongvalue",
                        "transaction_id": tid}
        req.User = user
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        # Check if the condition matches
        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.CHALLENGE_EXPIRED: "false"}},
             "request": req,
             "response": resp
             }
        )
        # Right, the challenge has not yet expired.
        self.assertTrue(r)

        # Check if the condition does not match, so we have an expired challenge
        chal.delete()
        chal = Challenge(serial=serial, transaction_id=tid, validitytime=-120)
        chal.save()

        r = uhandler.check_condition(
            {"g": {},
             "handler_def": {"conditions": {CONDITION.CHALLENGE_EXPIRED: "True"}},
             "request": req,
             "response": resp
             }
        )
        # Right, the challenge has expired.
        self.assertTrue(r)

        remove_token(serial)

    def test_12_check_token_is_in_container(self):
        # Prepare the container and token
        container_serial = init_container({"type": "generic"})
        token_serial = "SPASS01"
        init_token({"serial": "SPASS01", "type": "spass"})

        uhandler = BaseEventHandler()

        # Prepare a fake request
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"serial": token_serial}
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        options = {"g": {},
                   "handler_def": {},
                   "request": req,
                   "response": resp}

        # Token is not in a container
        # Check if the condition matches
        options['handler_def'] = {"conditions": {CONDITION.TOKEN_IS_IN_CONTAINER: "False"}}
        r = uhandler.check_condition(options)
        self.assertTrue(r)

        # Check if the condition does not match
        options['handler_def'] = {"conditions": {CONDITION.TOKEN_IS_IN_CONTAINER: "True"}}
        r = uhandler.check_condition(options)
        self.assertFalse(r)

        # Token is in a container
        add_token_to_container(container_serial, token_serial, user=User(), user_role="admin")
        # Check if the condition matches
        options['handler_def'] = {"conditions": {CONDITION.TOKEN_IS_IN_CONTAINER: "True"}}
        r = uhandler.check_condition(options)
        self.assertTrue(r)

        # Check if the condition does not match
        options['handler_def'] = {"conditions": {CONDITION.TOKEN_IS_IN_CONTAINER: "False"}}
        r = uhandler.check_condition(options)
        self.assertFalse(r)

        # Clean up
        delete_container_by_serial(container_serial, User(), "admin")
        remove_token(token_serial)

    def test_13_check_container_state(self):
        # Prepare the container
        container_serial = init_container({"type": "generic"})
        container = find_container_by_serial(container_serial)
        container.set_states(["disabled", "lost"])

        uhandler = BaseEventHandler()
        # Prepare a fake request
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"container_serial": container_serial}
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        # Check if the condition matches
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_STATE: "disabled"}},
                                      "request": req,
                                      "response": resp})
        self.assertTrue(r)

        # Check if the condition does not match
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_STATE: "active"}},
                                      "request": req,
                                      "response": resp})
        self.assertFalse(r)

        # ------------- Check condition container_single_state --------------
        # Check if the condition does not match due to multiple states
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_EXACT_STATE: "disabled"}},
                                      "request": req,
                                      "response": resp})
        self.assertFalse(r)

        # Check if the condition does not match due to wrong state
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_EXACT_STATE: "active"}},
                                      "request": req,
                                      "response": resp})
        self.assertFalse(r)

        # Check if the condition match
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_EXACT_STATE: "disabled,lost"}},
                                      "request": req,
                                      "response": resp})
        self.assertTrue(r)

        container.delete()

    def test_14_check_container_has_owner(self):
        # create user
        self.setUp_user_realms()
        test_user = User(login="cornelius",
                         realm=self.realm1)

        # init container
        container_serial = init_container({"type": "generic"})
        container = find_container_by_serial(container_serial)
        container.add_user(test_user)

        # event handler
        uhandler = BaseEventHandler()

        # Prepare a fake request
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"container_serial": container_serial}
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        # Check if the condition matches
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_HAS_OWNER: "True"}},
                                      "request": req,
                                      "response": resp})
        self.assertTrue(r)

        # Check if the condition does not match
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_HAS_OWNER: "False"}},
                                      "request": req,
                                      "response": resp})
        self.assertFalse(r)

        # Unassign user
        container.remove_user(test_user)

        # Check if the condition matches
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_HAS_OWNER: "False"}},
                                      "request": req,
                                      "response": resp})
        self.assertTrue(r)

        # Check if the condition does not match
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_HAS_OWNER: "True"}},
                                      "request": req,
                                      "response": resp})
        self.assertFalse(r)

        container.delete()

    def test_15_check_container_type(self):
        # Init container
        container_serial = init_container({"type": "smartphone"})
        container = find_container_by_serial(container_serial)

        # event handler
        uhandler = BaseEventHandler()

        # Prepare a fake request
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"container_serial": container_serial}
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        # Check if the condition matches
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_TYPE: "smartphone"}},
                                      "request": req,
                                      "response": resp
                                      })
        self.assertTrue(r)

        # Check if the condition does not match
        r = uhandler.check_condition({"g": {},
                                      "handler_def": {"conditions": {CONDITION.CONTAINER_TYPE: "generic"}},
                                      "request": req,
                                      "response": resp})
        self.assertFalse(r)

        container.delete()

    def test_16_check_container_has_token(self):
        # Init container
        container_serial = init_container({"type": "generic"})

        # Init token
        token_serial = "SPASS01"
        init_token({"serial": token_serial, "type": "spass"})

        uhandler = BaseEventHandler()

        # Prepare a fake request
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"container_serial": container_serial}
        resp = Response()
        resp.data = """{"result": {"value": false}}"""

        options = {"g": {},
                   "handler_def": {},
                   "request": req,
                   "response": resp}

        # Container has no token
        # Check if the condition matches
        options['handler_def'] = {"conditions": {CONDITION.CONTAINER_HAS_TOKEN: "False"}}
        r = uhandler.check_condition(options)
        self.assertTrue(r)

        # Check if the condition does not match
        options['handler_def'] = {"conditions": {CONDITION.CONTAINER_HAS_TOKEN: "True"}}
        r = uhandler.check_condition(options)
        self.assertFalse(r)

        # Container has a token
        add_token_to_container(container_serial, token_serial, user=User(), user_role="admin")
        # Check if the condition matches
        options['handler_def'] = {"conditions": {CONDITION.CONTAINER_HAS_TOKEN: "True"}}
        r = uhandler.check_condition(options)
        self.assertTrue(r)

        # Check if the condition does not match
        options['handler_def'] = {"conditions": {CONDITION.CONTAINER_HAS_TOKEN: "False"}}
        r = uhandler.check_condition(options)
        self.assertFalse(r)

        # Clean up
        delete_container_by_serial(container_serial, User(), "admin")
        remove_token(token_serial)


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
                   "handler_def": {"options": {"counter_name": "hallo_counter"}}}

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

        options = {
            "g": g,
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


class ContainerEventTestCase(MyTestCase):

    def setup_request(self, container_serial=None):
        g = FakeFlaskG()
        audit_object = FakeAudit()

        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        g.audit_object = audit_object

        builder = EnvironBuilder(method='POST',
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {}
        if container_serial:
            req.all_data = {"container_serial": container_serial}
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {}}}

        return options

    def test_00_missing_container_serial(self):
        options = self.setup_request()
        c_handler = ContainerEventHandler()
        actions = c_handler.actions

        for action in actions:
            # All actions should fail if no container serial is provided
            if action == C_ACTION_TYPE.INIT:
                # except for creating a container
                continue
            res = c_handler.do(action, options=options)
            self.assertFalse(res)

    def test_01_init_container(self):
        # check actions
        actions = ContainerEventHandler().actions
        self.assertTrue("create" in actions, actions)

        # check positions
        pos = ContainerEventHandler().allowed_positions
        self.assertEqual(set(pos), {"post", "pre"}, pos)

        # Setup the request
        options = self.setup_request()
        self.setUp_user_realms()
        user_obj = User("cornelius", self.realm1)
        options['request'].User = user_obj
        options["handler_def"]["options"] = {"type": "smartphone", "user": False, "token": False}

        c_handler = ContainerEventHandler()

        # Init container only with type
        res = c_handler.do(C_ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the container was created
        containers = get_all_containers(ctype="smartphone")['containers']
        self.assertTrue(len(containers) == 1)

        # Init container with type and user
        options["handler_def"]["options"] = {"type": "yubikey", "user": True}
        res = c_handler.do(C_ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the container was created
        containers = get_all_containers(ctype="yubikey")['containers']
        self.assertTrue(len(containers) == 1)
        # Check if the user is set
        owners = containers[0].get_users()
        self.assertIn(user_obj, owners)
        containers[0].delete()

        # Init container with type and user, but no user is provided
        options['request'].User = None
        res = c_handler.do(C_ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check if the container was created
        containers = get_all_containers(ctype="yubikey")['containers']
        self.assertTrue(len(containers) == 1)
        # Check that no user is set
        owners = containers[0].get_users()
        self.assertEqual(0, len(owners))

        # Init container with type and token
        token_serial = "SPASS01"
        token = init_token({"serial": token_serial, "type": "spass"})
        options['request'].all_data['serial'] = token_serial
        options["handler_def"]["options"] = {"type": "generic", "token": True}
        res = c_handler.do(C_ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)

        # Check if the container was created
        containers = get_all_containers(ctype="generic")['containers']
        self.assertTrue(len(containers) == 1)

        # Check if the token was assigned
        token_serials = [token.get_serial() for token in containers[0].get_tokens()]
        self.assertIn(token_serial, token_serials)

        # Check that user is not assigned
        owners = containers[0].get_users()
        self.assertNotIn(user_obj, owners)

        # Init container without type:
        options["handler_def"]["options"] = {}
        res = c_handler.do(C_ACTION_TYPE.INIT, options=options)
        self.assertFalse(res)

        # Check that no new container is created
        containers = get_all_containers()['containers']
        self.assertEqual(3, len(containers))

        # Clean up
        for container in containers:
            container.delete()
        token.delete_token()

        # Init container with tokens, but no token is provided
        options = self.setup_request()
        options["handler_def"]["options"] = {"type": "generic", "token": True}
        res = c_handler.do(C_ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)
        # Check that container is created without tokens
        containers = get_all_containers()['containers']
        self.assertEqual(1, len(containers))
        self.assertEqual(0, len(containers[0].get_tokens()))


    def test_02_delete_container(self):
        # create container
        container_serial = init_container({"type": "generic"})

        # Setup request
        options = self.setup_request(container_serial=container_serial)
        user_obj = User("cornelius", self.realm1)
        options['request'].User = user_obj

        c_handler = ContainerEventHandler()

        # Delete container
        res = c_handler.do(C_ACTION_TYPE.DELETE, options=options)
        self.assertTrue(res)

        # check that the container does not exist
        containers = get_all_containers(serial=container_serial)['containers']
        self.assertTrue(len(containers) == 0)

        # Delete non-existing container
        options['request'].all_data = {"container_serial": "doesnotexist"}

        res = c_handler.do(C_ACTION_TYPE.DELETE, options=options)
        self.assertFalse(res)

    def test_03_assign_and_unassign_container(self):
        # create container
        container_serial = init_container({"type": "generic"})
        container = find_container_by_serial(container_serial)
        # create user
        self.setUp_user_realms()
        test_user = User(login='cornelius', realm=self.realm1)
        # create token with user
        token_serial = "SPASS01"
        token = init_token({"serial": token_serial, "type": "spass"}, user=test_user)
        container.add_token(token)

        # Setup request
        options = self.setup_request()
        options['request'].all_data = {"serial": token_serial}
        options['request'].User = User()

        c_handler = ContainerEventHandler()

        # Assign user from token to its container
        res = c_handler.do(C_ACTION_TYPE.ASSIGN, options=options)
        self.assertTrue(res)

        # check that user is owner of container
        container_owner = container.get_users()[0]
        self.assertEqual(container_owner, test_user)

        # Unassign all users from container
        res = c_handler.do(C_ACTION_TYPE.UNASSIGN, options=options)
        self.assertTrue(res)

        # check that no container owner exists
        container_owners = container.get_users()
        self.assertTrue(len(container_owners) == 0)

        # Use token without user
        options = self.setup_request()
        options['request'].all_data = {"serial": token_serial}
        unassign_token(token_serial)
        res = c_handler.do(C_ACTION_TYPE.ASSIGN, options=options)
        self.assertFalse(res)

        # check that no user is owner of container
        container_owners = container.get_users()
        self.assertEqual(len(container_owners), 0)

        # Unassign all users from container
        res = c_handler.do(C_ACTION_TYPE.UNASSIGN, options=options)
        self.assertFalse(res)

        # Clean up
        container.delete()
        token.delete_token()

    def test_04_set_states(self):
        # create container
        container_serial = init_container({"type": "generic"})
        container = find_container_by_serial(container_serial)

        # Setup request
        options = self.setup_request(container_serial=container_serial)
        options['handler_def']["options"] = {"disabled": True, "lost": True}

        c_handler = ContainerEventHandler()

        # Set container to disabled and lost
        res = c_handler.do(C_ACTION_TYPE.SET_STATES, options=options)
        self.assertTrue(res)

        # Check the state of the container
        states = container.get_states()
        self.assertEqual(len(states), 2)
        self.assertTrue("disabled" in states)
        self.assertTrue("lost" in states)

        # Set container to active
        options["handler_def"]["options"] = {"active": True}
        res = c_handler.do(C_ACTION_TYPE.SET_STATES, options=options)
        self.assertTrue(res)

        # Check that active is the only state of the container
        states = container.get_states()
        self.assertEqual(len(states), 1)
        self.assertTrue("active" in states)
        self.assertFalse("lost" in states)

        # Set empty states
        options["handler_def"]["options"] = {}
        res = c_handler.do(C_ACTION_TYPE.SET_STATES, options=options)
        self.assertFalse(res)

        # Check the state of the container
        states = container.get_states()
        self.assertEqual(len(states), 1)
        self.assertTrue("active" in states)

        # Set non-existing state
        options["handler_def"]["options"] = {"wrong_state": True}
        res = c_handler.do(C_ACTION_TYPE.SET_STATES, options=options)
        self.assertFalse(res)

        # Check the state of the container
        states = container.get_states()
        self.assertEqual(len(states), 1)
        self.assertTrue("active" in states)

        # Clean up
        container.delete()

    def test_05_add_states(self):
        # create container
        container_serial = init_container({"type": "generic"})
        container = find_container_by_serial(container_serial)
        initial_states = container.get_states()

        # Setup request
        options = self.setup_request(container_serial=container_serial)
        options['handler_def']["options"] = {"lost": True}

        c_handler = ContainerEventHandler()

        # Add state lost
        res = c_handler.do(C_ACTION_TYPE.ADD_STATES, options=options)
        self.assertTrue(res)

        # Check the states of the container
        states = container.get_states()
        self.assertEqual(len(states), len(initial_states) + 1)
        self.assertTrue(initial_states[0] in states)
        self.assertTrue("lost" in states)

        # Add empty state
        options["handler_def"]["options"] = {}
        res = c_handler.do(C_ACTION_TYPE.ADD_STATES, options=options)
        self.assertFalse(res)

        # Check the state of the container
        states = container.get_states()
        self.assertEqual(len(states), len(initial_states) + 1)
        self.assertTrue(initial_states[0] in states)
        self.assertTrue("lost" in states)

        # Add non-existing state
        options["handler_def"]["options"] = {"wrong_state": True}
        res = c_handler.do(C_ACTION_TYPE.ADD_STATES, options=options)
        self.assertFalse(res)

        # Check the state of the container
        states = container.get_states()
        self.assertEqual(len(states), len(initial_states) + 1)
        self.assertTrue(initial_states[0] in states)
        self.assertTrue("lost" in states)

        # Clean up
        container.delete()

    def test_06_set_description(self):
        # create container
        initial_description = "Initial description"
        container_serial = init_container({"type": "generic", "description": initial_description})
        container = find_container_by_serial(container_serial)

        # Setup request and options
        options = self.setup_request(container_serial=container_serial)
        new_description = "New description"
        options['handler_def']["options"] = {"description": new_description}

        c_handler = ContainerEventHandler()

        # Set new description
        res = c_handler.do(C_ACTION_TYPE.SET_DESCRIPTION, options=options)
        self.assertTrue(res)

        # Check description
        description = container.description
        self.assertEqual(description, new_description)

        # Set new description without description parameter
        options["handler_def"]["options"] = {}
        res = c_handler.do(C_ACTION_TYPE.SET_DESCRIPTION, options=options)
        self.assertFalse(res)

        # Check description
        description = container.description
        self.assertEqual(description, new_description)

        # Clean up
        container.delete()

    def test_07_remove_tokens(self):
        # create container
        container_serial = init_container({"type": "generic"})
        container = find_container_by_serial(container_serial)

        # create token
        token_serial_01 = "SPASS01"
        token_01 = init_token({"serial": token_serial_01, "type": "spass"})
        token_serial_02 = "SPASS02"
        token_02 = init_token({"serial": token_serial_02, "type": "spass"})
        container.add_token(token_01)
        container.add_token(token_02)

        # Setup request and options
        options = self.setup_request(container_serial=container_serial)
        new_description = "New description"
        options['handler_def']["options"] = {"description": new_description}

        c_handler = ContainerEventHandler()

        # Remove all tokens
        res = c_handler.do(C_ACTION_TYPE.REMOVE_TOKENS, options=options)
        self.assertTrue(res)

        # check that no tokens are assigned to the container
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(0, len(tokens))

        # Remove all tokens for container without tokens
        res = c_handler.do(C_ACTION_TYPE.REMOVE_TOKENS, options=options)
        self.assertTrue(res)

        # Clean up
        container.delete()
        token_01.delete_token()
        token_02.delete_token()

    def test_08_set_add_del_container_info(self):
        # create container
        container_serial = init_container({"type": "generic"})

        # Setup request and options
        options = self.setup_request(container_serial=container_serial)
        key = "info_key"
        value = "info_value"
        options['handler_def']["options"] = {"key": key, "value": value}

        c_handler = ContainerEventHandler()

        # Set container info
        res = c_handler.do(C_ACTION_TYPE.SET_CONTAINER_INFO, options=options)
        self.assertTrue(res)

        # check that the info is set
        container = find_container_by_serial(container_serial)
        infos = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertIn(key, infos)
        self.assertEqual(infos[key], value)

        # Set another info
        new_key = "info_key_new"
        new_value = "info_value_new"
        options['handler_def']["options"] = {"key": new_key, "value": new_value}
        res = c_handler.do(C_ACTION_TYPE.SET_CONTAINER_INFO, options=options)
        self.assertTrue(res)

        # check that the info is set and the old one deleted
        container = find_container_by_serial(container_serial)
        infos = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertIn(new_key, infos)
        self.assertEqual(infos[new_key], new_value)
        self.assertNotIn(key, infos)

        # add container info
        added_key = "info_key_add"
        added_value = "info_value_add"
        options['handler_def']["options"] = {"key": added_key, "value": added_value}
        res = c_handler.do(C_ACTION_TYPE.ADD_CONTAINER_INFO, options=options)
        self.assertTrue(res)

        # check that the info is added and the old ones still exists
        container = find_container_by_serial(container_serial)
        infos = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertIn(added_key, infos)
        self.assertEqual(infos[added_key], added_value)
        self.assertIn(new_key, infos)
        self.assertEqual(infos[new_key], new_value)

        # delete container info
        options['handler_def']["options"] = {}
        res = c_handler.do(C_ACTION_TYPE.DELETE_CONTAINER_INFO, options=options)
        self.assertTrue(res)

        # check that all infos are deleted
        infos = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual(0, len(infos))

        # Clean up
        container.delete()

    def test_09_enable_disable_all_tokens(self):
        # create container
        container_serial = init_container({"type": "generic"})
        container = find_container_by_serial(container_serial)

        # create tokens
        token_serial_01 = "SPASS01"
        token_01 = init_token({"serial": token_serial_01, "type": "spass"})
        token_serial_02 = "SPASS02"
        token_02 = init_token({"serial": token_serial_02, "type": "spass"})

        # Setup request and options
        options = self.setup_request(container_serial=container_serial)
        c_handler = ContainerEventHandler()

        # Disable all tokens if container does not have any token
        res = c_handler.do(C_ACTION_TYPE.DISABLE_TOKENS, options=options)
        self.assertTrue(res)

        # Enable all tokens if container does not have any token
        res = c_handler.do(C_ACTION_TYPE.ENABLE_TOKENS, options=options)
        self.assertTrue(res)

        # Add tokens to container
        container.add_token(token_01)
        container.add_token(token_02)

        # Disable all tokens
        res = c_handler.do(C_ACTION_TYPE.DISABLE_TOKENS, options=options)
        self.assertTrue(res)

        # Check that both tokens are disabled
        self.assertFalse(token_01.is_active())
        self.assertFalse(token_02.is_active())

        # Enable all tokens
        res = c_handler.do(C_ACTION_TYPE.ENABLE_TOKENS, options=options)
        self.assertTrue(res)

        # Check that both tokens are enabled
        self.assertTrue(token_01.is_active())
        self.assertTrue(token_02.is_active())

        # clean up
        container.delete()
        token_01.delete_token()
        token_02.delete_token()


class TokenEventTestCase(MyTestCase):

    def test_01_set_tokenrealm(self):
        # check actions
        actions = TokenEventHandler().actions
        self.assertTrue("set tokeninfo" in actions, actions)
        self.assertTrue("increase tokeninfo" in actions, actions)

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

        # Enroll token and assign to container
        container_serial = init_container({"type": "generic"})
        options['request'].all_data = {"container_serial": container_serial}
        options['handler_def']["options"] = {"tokentype": "spass",
                                             "user": False,
                                             "container": True}

        # With container cerial
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)

        # Check if the token was created and added to the container
        tokens = get_tokens_paginate(tokentype="spass")
        self.assertEqual(1, tokens['count'])
        self.assertEqual(tokens["tokens"][0]["container_serial"], container_serial)

        # Clean up
        remove_token(tokens["tokens"][0]["serial"])
        delete_container_by_serial(container_serial, User(), "admin")

        # Enroll token and assign to container without a container serial
        options['request'].all_data = {}
        res = t_handler.do(ACTION_TYPE.INIT, options=options)
        self.assertTrue(res)

        # Check if the token was created and no container added
        tokens = get_tokens_paginate(tokentype="spass")
        self.assertEqual(1, tokens['count'])
        self.assertIn(tokens["tokens"][0]["container_serial"], ['', None])

        # Clean up
        remove_token(tokens["tokens"][0]["serial"])

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

        # Test 'increase tokeninfo'. Set a tokeninfo to 17.
        tokeninfo_key = "pushMitigation"
        t[0].add_tokeninfo(tokeninfo_key, "17")
        ti = t[0].get_tokeninfo(tokeninfo_key)
        self.assertEqual("17", ti)
        # Now we run an event handler, that increases the tokeninfo by 3
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"key": tokeninfo_key,
                                               "increment": "3"}
                                   }
                   }
        res = t_handler.do(ACTION_TYPE.INCREASE_TOKENINFO, options=options)
        self.assertTrue(res)
        ti = t[0].get_tokeninfo(tokeninfo_key)
        self.assertEqual("20", ti)

        # Now, decrease the tokeninfo
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {"options": {"key": tokeninfo_key,
                                               "increment": "-10"}
                                   }
                   }
        res = t_handler.do(ACTION_TYPE.INCREASE_TOKENINFO, options=options)
        self.assertTrue(res)
        ti = t[0].get_tokeninfo(tokeninfo_key)
        self.assertEqual("10", ti)

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
                   "handler_def": {
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
