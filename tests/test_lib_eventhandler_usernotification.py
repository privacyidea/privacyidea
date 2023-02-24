# -*- coding: utf-8 -*-

"""
This file tests:

lib/eventhandler/usernotification.py
"""
import email
import os
from datetime import datetime, timedelta

import mock
from dateutil.tz import tzlocal
from flask import Request
from werkzeug.test import EnvironBuilder

from privacyidea.app import PiResponseClass as Response
from privacyidea.lib.eventhandler.base import CONDITION
from privacyidea.lib.eventhandler.usernotification import (UserNotificationEventHandler,
                                                           NOTIFY_TYPE)
from privacyidea.lib.policy import ACTION
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.smtpserver import add_smtpserver
from privacyidea.lib.token import init_token, unassign_token, remove_token
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.user import User, create_user
from privacyidea.lib.utils import to_unicode
from privacyidea.models import TokenOwner
from . import smtpmock
from .base import MyTestCase, FakeFlaskG, FakeAudit

PNG_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAeoAAAHqAQAAAADjFj" \
            "CXAAAD+UlEQVR4nO2dTYrkSAxGn8aGWtowB6ij2Dcb5khzA/soeYABe9lgo1mE4q" \
            "eKphdpN901+WlRpDP9iEwQUnySHGXOBVv/uEKDcOHChQsXLly48HtxC+sxG08DTm" \
            "MdT7N5N7M5XUK6NDOz+b7Vhb8ajru7M7m7+9a5ux/A4O7L4MlgOIhP0y2ZWL70bx" \
            "f+q/G9hC/AF05j2oDVenyhc7MxPjWz/ubVhb82bvP+loopZmaRa+E0Jj9++urCXx" \
            "Rf3w/sr0dPinUM7jbvPbGv+8mrC38pfHD3Jb08jfX9AIYjuZ4vdO4Lp/kCxNbvzt" \
            "WFvxYeaiKsc6btx3/yrVITwp83/2jx7nDgy3BEmHOPV6F1i8nrhD9ltQ6SAtm0dQ" \
            "4ppXYOg5cI1xWfVOVE+BXLNZB9hPXdgf00Zx+NyU9z9v5wdmD650+A7gDOjH3p3y" \
            "78V+E5w6YSMKTacMmmNddmwREBTxlW+AWrXhdpNvsakWYhXA+K/x1SE8KvWNYQJd" \
            "YVXytFk6ph0y3uh2Kd8CsWamLLyoEP3dcqM1I4BGCS1wm/Zp81bOtrXeOEtfsPpY" \
            "YirxP+lDX7uhrrlrJzSyl1gybDlmEUeZ3w56zNpnWWaQtfayRtEhfDoX2d8JtiXX" \
            "hTqf7WzR0Q83X1EqRhhd+A7z0xWmJmsFsaHnb3A6ZHX6bqIuDdu7rw18LbDFtGhn" \
            "NbLJSrL4N7Uq5Lqdwpwwq/iMdG7tFjM3WWuHObAaaHmf9dJ4hvXl34q+Fl5qQEsq" \
            "JhS5O/zncmwbEM6v4Lv2TV66iTJuFckU2hvgdo5kT4LXh6FGfyA5vTgxIAlIrwRp" \
            "5gH0JchP/9Dl9e+JfD017N1/nNYR9x9hEYDizy6oav798Mhn/NAQekYYVfstybIP" \
            "dXPza+ylhA06pN05/KsMIv4uvYOexvbvZ+NAnXF04zG6Hd5qleJ/ya5Z5D6fRnlR" \
            "oNio3y8ES5VB9W+DWLPtjGh+pveUai1Ivb6ROX1wm/Be/c5sGddQwNm1NqPPbvyx" \
            "5n7+jECeE3qgnIw8PU0ZKt1PCaS3XEhN+FRx/iNKZHnw7WSQU6hm8p/sURO8OBzX" \
            "evLvx18NL9d8/P43gefKq6glpIgTr4pFgn/Dn7pA/qmRLRbt1ywi3d13S6k+p1wp" \
            "+3XDkB2rJw5zQH69SZz3LYibxO+PMW3uS5VFeH1yP1Hm01ZSplFmVY4c9bk1dLNo" \
            "2QlhJpnvRsTFVi4bfi7o+3dFYdq/WkLtlMlRmhOmz+GasLf1G8qRLTOevId47pLM" \
            "NQv9mXF/418O+ewd6UT+qJE/XozhhQUYYV/qx91rBTVg5VvjaVkxgjVr1O+BUz/f" \
            "c64cKFCxcuXLjw/wX+HzgPbUakdjuaAAAAAElFTkSuQmCC"

OAUTH_URL = "otpauth://hotp/OATH0001D8B6?secret=GQROHTUPBAK5N6T2HBUK4IP42R56E" \
            "MV3&counter=1&digits=6&issuer=privacyIDEA"


class UserNotificationTestCase(MyTestCase):

    def test_01_basefunctions(self):
        actions = UserNotificationEventHandler().actions
        self.assertIn('sendmail', actions, actions)
        self.assertIn('sendsms', actions, actions)
        self.assertIn('savefile', actions, actions)

        # check positions
        pos = UserNotificationEventHandler().allowed_positions
        self.assertEqual(set(pos), {"post", "pre"}, pos)

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
        msg = smtpmock.get_sent_message()
        assert 'To: user@localhost.localdomain' in msg

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
                                   "To " + NOTIFY_TYPE.EMAIL:
                                       "recp@example.com",
                                   "reply_to": NOTIFY_TYPE.EMAIL,
                                   "reply_to" + NOTIFY_TYPE.EMAIL:
                                       "recp@example.com"}}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

    @smtpmock.activate
    def test_12_send_to_tokenowner(self):
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
                                   "To": NOTIFY_TYPE.TOKENOWNER,
                                   "To " + NOTIFY_TYPE.TOKENOWNER:
                                       "recp@example.com",
                                   "reply_to": NOTIFY_TYPE.TOKENOWNER,
                                   "reply_to" + NOTIFY_TYPE.TOKENOWNER:
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
                                       "super",
                                   "reply_to": NOTIFY_TYPE.INTERNAL_ADMIN,
                                   "reply_to" + NOTIFY_TYPE.INTERNAL_ADMIN:
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
                                       "testadmin",
                                   "reply_to": NOTIFY_TYPE.INTERNAL_ADMIN,
                                   "reply_to" + NOTIFY_TYPE.INTERNAL_ADMIN:
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
                                   "reply_to": NOTIFY_TYPE.LOGGED_IN_USER,
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
                                   "reply_to": NOTIFY_TYPE.LOGGED_IN_USER,
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
                                   "To " + NOTIFY_TYPE.ADMIN_REALM:
                                       "realm1",
                                   "reply_to": NOTIFY_TYPE.ADMIN_REALM,
                                   "reply_to" + NOTIFY_TYPE.ADMIN_REALM:
                                       "realm1"}}}
        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)

    def test_15_unassign_missing_user(self):
        """
        Unassign a token from a user that does not exist anymore.

        There is a token which is owned by a user, who was deleted from the
        userstore.
        An Event Handler to notify the user via email on unassign is defined.
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
        # First delete it, in case the user exist
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

        # delete the user
        r = user.delete()
        self.assertTrue(r)

        # create the "options" object for the handler
        g = FakeFlaskG()
        audit_object = FakeAudit()
        g.audit_object = audit_object
        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": ""}
        env = EnvironBuilder().get_environ()
        g.client_ip = env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        req.all_data = {"serial": "SPNOTIFY",
                        "user": "notify_user"}
        req.User = User("notify_user", "notify_realm")
        resp = Response()
        resp.data = """{"result": {"value": true}}"""
        # If we send a plain email, we do not escape HTML
        options = {
            "g": g,
            "request": req,
            "response": resp,
            "handler_def": {
                "options": {
                    "emailconfig": "myserver",
                    "body": "Hello {user}, your token {serial} has been unassigned"}}}

        # unassign the token from the non-existing user
        # this should not send an email and should not throw an error
        uhandler = UserNotificationEventHandler()
        res = uhandler.do('sendmail', options)
        # TODO: the handler should return False here
        # TODO: Also we should check that no email was sent (i.e. call of smtpserver)
        self.assertTrue(res)
        # Cleanup
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
                        "user": "nönäscii"}
        req.User = User("nönäscii", self.realm1)
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
        resp.data = """
{{
    "detail": {{
        "googleurl": {{
            "description": "URL for google Authenticator",
            "img": "{0!s}",
            "value": "{1!s}"
        }},
        "rollout_state": "",
        "serial": "OATH0001D8B6",
        "threadid": 140437172639168
    }},
    "id": 1,
    "jsonrpc": "2.0",
    "result": {{
        "status": true,
        "value": true
    }},
    "signature": "foo",
    "time": 1561549651.093083,
    "version": "privacyIDEA 3.0.1.dev2",
    "versionnumber": "3.0.1.dev2"
}}""".format(PNG_IMAGE, OAUTH_URL)
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
        self.assertEqual(payload, "<img src='{0!s}' />".format(PNG_IMAGE))

    @smtpmock.activate
    def test_21_sendmail_attachment(self):
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
        resp.data = """{{
            "detail": {{
                "googleurl": {{
                    "description": "URL for google Authenticator",
                    "img": "{0!s}",
                    "value": "{1!s}"
                }},
                "rollout_state": "",
                "serial": "OATH0001D8B6",
                "threadid": 140437172639168
            }},
            "id": 1,
            "jsonrpc": "2.0",
            "result": {{
                "status": true,
                "value": true
            }},
            "signature": "foo",
            "time": 1561549651.093083,
            "version": "privacyIDEA 3.0.1.dev2",
            "versionnumber": "3.0.1.dev2"
        }}
        """.format(PNG_IMAGE, OAUTH_URL)
        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "conditions": {"serial": "123.*"},
                       "options": {"body": "<img src='cid:token_image' />",
                                   "mimetype": "html",
                                   "attach_qrcode": True,
                                   "emailconfig": "myserver"}}}

        un_handler = UserNotificationEventHandler()
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        self.assertEqual(parsed_email.get_content_maintype(), 'multipart', parsed_email)
        payload = parsed_email.get_payload()
        self.assertEqual(len(payload), 2, payload)
        self.assertEqual(payload[0].get_content_type(), "text/html", payload)
        self.assertEqual(payload[1].get_content_type(), 'image/png', payload)
        self.assertEqual(payload[1]['Content-Disposition'], 'inline; filename="SomeSerial.png"',
                         payload)
        self.assertEqual(payload[1].get_filename(), 'SomeSerial.png', payload)

        # check sending attachment with "plain" mimetype for body
        options['handler_def']['options']['mimetype'] = 'plain'
        res = un_handler.do("sendmail", options=options)
        self.assertTrue(res)
        parsed_email = email.message_from_string(smtpmock.get_sent_message())
        self.assertEqual(parsed_email.get_content_maintype(), 'multipart', parsed_email)
        payload = parsed_email.get_payload()
        self.assertEqual(len(payload), 2, payload)
        self.assertEqual(payload[0].get_content_type(), "text/plain", payload)
        self.assertEqual(payload[1].get_content_type(), 'image/png', payload)
        self.assertEqual(payload[1]['Content-Disposition'], 'inline; filename="SomeSerial.png"',
                         payload)
        self.assertEqual(payload[1].get_filename(), 'SomeSerial.png', payload)

    def test_22_save_notification(self):
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

        # This part only works for a non-root user
        if os.getuid() == 0:
            return

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
        # Note: this does not work when tests are run as root
        with mock.patch("logging.Logger.error") as mock_log:
            un_handler.do("savefile", options=options)
            call_args = mock_log.call_args
            # ensure log.error was actually called ...
            self.assertIsNotNone(call_args)
            # ... with the right message
            self.assertTrue(call_args[0][0].startswith("Failed to write notification file:"))

        os.remove("tests/testdata/testOATH123456.txt")
