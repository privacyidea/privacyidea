# -*- coding: utf-8 -*-
"""
This tests the file api.lib.utils
"""
from .base import MyApiTestCase

from privacyidea.api.lib.utils import (getParam)
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
