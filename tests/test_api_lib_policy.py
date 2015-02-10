"""
This test file tests the api.lib.policy.py

The api.lib.policy.py depends on lib.policy and on flask!
"""
import json
from .base import MyTestCase

from privacyidea.lib.policy import (set_policy, delete_policy,
                                    PolicyClass, SCOPE)
from privacyidea.api.lib.policy import (check_serial, check_tokentype,
                                        no_detail_on_success, no_detail_on_fail)

from flask import Response, Request, g
from werkzeug.test import EnvironBuilder
from privacyidea.lib.error import PolicyError


class PolicyDecoratorTestCase(MyTestCase):

    def test_01_check_tokentype(self):
        # http://werkzeug.pocoo.org/docs/0.10/test/#environment-building
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "PISP0000AB00",
                          "type": "spass"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokentype=hotp", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        #  is raised.
        self.assertRaises(PolicyError,
                          check_tokentype,
                          req, resp)

        # A policy, that allows the token spass
        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokentype=spass", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        #  is raised.
        r = check_tokentype(req, resp)
        jresult = json.loads(r.data)
        self.assertTrue(jresult.get("result").get("value"))

    def test_02_check_serial(self):
        # http://werkzeug.pocoo.org/docs/0.10/test/#environment-building
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="serial=TOTP", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token serial HOTP is not allowed on this client, so an exception
        #  is raised.
        self.assertRaises(PolicyError,
                          check_serial,
                          req, resp)

        # A policy, that allows the token spass
        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="serial=HOTP", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        # is raised.
        r = check_serial(req, resp)
        jresult = json.loads(r.data)
        self.assertTrue(jresult.get("result").get("value"))

    def test_03_no_detail_on_success(self):
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the detail on success
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="no_detail_on_success", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = no_detail_on_success(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" not in jresult, jresult)
        delete_policy("pol2")

    def test_04_no_detail_on_fail(self):
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": False},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the detail on success
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="no_detail_on_fail", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = no_detail_on_fail(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" not in jresult, jresult)

        # A successful call has a detail in the response!
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        new_response = no_detail_on_fail(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" in jresult, jresult)

        delete_policy("pol2")
