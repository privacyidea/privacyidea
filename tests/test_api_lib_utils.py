# -*- coding: utf-8 -*-
"""
This tests the file api.lib.utils
"""
from .base import MyApiTestCase

from privacyidea.api.lib.utils import (getParam, check_policy_name)
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

    def test_02_check_policy_name(self):
        check_policy_name("This is a new valid Name")
        check_policy_name("THis-is-a-valid-Name")
        # The name "check" is reserved
        self.assertNotEqual(ParameterError, check_policy_name, "check")
        # This is an invalid name
        self.assertNotEqual(ParameterError, check_policy_name, "~invalid name")

        # some disallowed patterns:
        self.assertNotEqual(ParameterError, check_policy_name, "Check")
        self.assertNotEqual(ParameterError, check_policy_name, "pi-update-policy-something")
        # Some patterns that work
        check_policy_name("check this out.")
        check_policy_name("my own pi-update-policy-something")
        check_policy_name("pi-update-policysomething")

