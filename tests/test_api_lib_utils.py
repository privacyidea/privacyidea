# -*- coding: utf-8 -*-
"""
This tests the file api.lib.utils
"""
import flask
from werkzeug.test import EnvironBuilder

from .base import MyApiTestCase, FakeFlaskG

from privacyidea.api.lib.utils import (getParam, add_request_information)
from privacyidea.lib.error import ParameterError


class UtilsTestCase(MyApiTestCase):

    def test_01_getParam(self):
        s = getParam({"serial": ""}, "serial", optional=False, allow_empty=True)
        self.assertEqual(s, "")

        self.assertRaises(ParameterError, getParam, {"serial": ""}, "serial", optional=False, allow_empty=False)

        # check for allowed values
        v = getParam({"sslverify": "0"}, "sslverify", allowed_values=["0", "1"], default="1")
        self.assertEqual("0", v)

        v = getParam({"sslverify": "rogue value"}, "sslverify", allowed_values=["0", "1"], default="1")
        self.assertEqual("1", v)

        v = getParam({}, "sslverify", allowed_values=["0", "1"], default="1")
        self.assertEqual("1", v)

    def test_02_add_request_information(self):
        # unknown path
        builder = EnvironBuilder(method="POST")
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "1.2.3.4"
        request = flask.Request(env)
        request.all_data = {}

        g = FakeFlaskG()
        add_request_information(g, request)
        self.assertEqual(g.client_ip, "1.2.3.4")
        self.assertEqual(g.request_context, {"endpoint": None})

        # valid path
        builder = EnvironBuilder(method="POST")
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "1.2.3.4"
        request = flask.Request(env)

        class FakeRule(object):
            def __str__(self):
                return "/validate/check"

        request.all_data = {}
        request.url_rule = FakeRule()
        g = FakeFlaskG()
        add_request_information(g, request)
        self.assertEqual(g.client_ip, "1.2.3.4")
        self.assertEqual(g.request_context, {"endpoint": "/validate/check"})

        # check with full request dispatching
        with self.app.test_request_context("/auth",
                                           method="POST",
                                           data={"username": "hello", "password": "test"},
                                           environ_base={"REMOTE_ADDR": "1.2.3.4"}):
            self.app.full_dispatch_request()
            self.assertEqual(flask.g.client_ip, "1.2.3.4")
            self.assertEqual(flask.g.request_context,
                             {"endpoint": "/auth"})

        with self.app.test_request_context("/validate/check?user=foo&pass=bar",
                                           method="POST",
                                           environ_base={"REMOTE_ADDR": "1.2.3.4"}):
            self.app.full_dispatch_request()
            self.assertEqual(flask.g.client_ip, "1.2.3.4")
            self.assertEqual(flask.g.request_context,
                             {"endpoint": "/validate/check"})