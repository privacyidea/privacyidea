# -*- coding: utf-8 -*-
"""
This tests the file api.lib.utils
"""
from .base import MyTestCase

from privacyidea.api.lib.utils import (getParam)
from privacyidea.lib.error import ParameterError

import pytest
xfail = pytest.mark.xfail


@xfail('sys.version_info.major > 2')
class UtilsTestCase(MyTestCase):

    def test_01_getParam(self):
        s = getParam({"serial": ""}, "serial", optional=False, allow_empty=True)
        self.assertEqual(s, "")

        self.assertRaises(ParameterError, getParam, {"serial": ""}, "serial", optional=False, allow_empty=False)
