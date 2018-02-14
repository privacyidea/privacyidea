"""
This file contains the event handlers tests. It tests:

lib/eventhandler/usernotification.py (one event handler module)
lib/event.py (the decorator)
"""

import smtpmock
import responses
from .base import MyTestCase, FakeFlaskG, FakeAudit
from privacyidea.lib.eventhandler.usernotification import (
    UserNotificationEventHandler, NOTIFY_TYPE)
from privacyidea.lib.eventhandler.tokenhandler import (TokenEventHandler,
                                                       ACTION_TYPE, VALIDITY)
from privacyidea.lib.eventhandler.scripthandler import ScriptEventHandler
from privacyidea.lib.eventhandler.federationhandler import FederationEventHandler
from privacyidea.lib.eventhandler.base import BaseEventHandler, CONDITION
from privacyidea.lib.smtpserver import add_smtpserver
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from flask import Request, Response
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
from privacyidea.lib.error import ParameterError
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date_string
from dateutil.tz import tzlocal
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

        self.assertEqual(r, 2)
        # Update the first event
        r = set_event("name1", "token_init, token_assign",
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

        # Now we have one event left.
        events = event_config.get_handled_events("token_init")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("name"), "name2")
        n_eid = events[0].get("id")
        # Disable this event in the database
        enable_event(n_eid, False)
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

        # We can not enable an event, that does not exist.
        self.assertRaises(ParameterError, enable_event, 1234567, True)

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

        base_handler =  BaseEventHandler()
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
                       "options":{
                           "user": "1",
                           "realm": "1",
                           "serial": "1",
                           "logged_in_user": "1",
                           "logged_in_role": "1",}
                   }
                   }

        script_name = "ls.sh"
        t_handler = ScriptEventHandler()
        res = t_handler.do(script_name, options=options)
        self.assertTrue(res)
        remove_token("SPASS01")


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
        response = json.loads(options.get("response").data)
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
        response = json.loads(options.get("response").data)
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
        response = json.loads(options.get("response").data)
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
        self.assertEqual(options.get("response").data, "")

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
        response = json.loads(options.get("response").data)
        self.assertEqual(response.get("detail").get("origin"),
                         "https://remote/token/init")



class TokenEventTestCase(MyTestCase):

    def test_01_set_tokenrealm(self):
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

        # Now the initiailized token will be set in realm2
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

    def test_09_set_tokeninfo(self):
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
        resp.data = """{"result": {"value": false}}"""
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
                   "handler_def": {"conditions": {"token_locked": "True"}},
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
                   "handler_def": {"conditions": {"token_locked": "True"}},
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
        # Serial matches the regexp
        self.assertEqual(r, True)

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

        tok = init_token({"serial": serial, "type": "spass"})
        tok.token.resolver = self.resolvername1
        tok.token.resolver_type = "passwd"
        tok.token.user_id = "123981298"

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

        tok.set_user(User("cornelius", "realm1"))
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
                        "UserNotification", "sendmail")
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
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

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
