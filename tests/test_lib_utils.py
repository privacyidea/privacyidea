"""
This tests the file lib.utils
"""
from .base import MyTestCase

from privacyidea.lib.utils import (parse_timelimit)
from datetime import timedelta


class UtilsTestCase(MyTestCase):

    def test_01_timelimit(self):
        c, tdelta = parse_timelimit("1/5s")
        self.assertEqual(c, 1)
        self.assertEqual(tdelta, timedelta(seconds=5))

        c, tdelta = parse_timelimit("5/10M")
        self.assertEqual(c, 5)
        self.assertEqual(tdelta, timedelta(minutes=10))

        c, tdelta = parse_timelimit(" 5 / 10M ")
        self.assertEqual(c, 5)
        self.assertEqual(tdelta, timedelta(minutes=10))

        c, tdelta = parse_timelimit("7/120h")
        self.assertEqual(c, 7)
        self.assertEqual(tdelta, timedelta(hours=120))
        self.assertEqual(tdelta, timedelta(days=5))

        # A missing time specifier raises an Exception
        self.assertRaises(Exception, parse_timelimit, "7/12")

        # A non number raises an Exception
        self.assertRaises(Exception, parse_timelimit, "seven/12m")


