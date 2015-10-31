"""
This tests the file lib.utils
"""
from .base import MyTestCase

from privacyidea.lib.utils import (parse_timelimit, parse_timedelta)
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

    def test_02_timedelta(self):
        tdelta = parse_timedelta("123d")
        self.assertEqual(tdelta, timedelta(days=123))

        tdelta = parse_timedelta("31h")
        self.assertEqual(tdelta, timedelta(hours=31))

        tdelta = parse_timedelta(" 2y")
        self.assertEqual(tdelta, timedelta(days=2*365))

        # A missing time specifier raises an Exception
        self.assertRaises(Exception, parse_timedelta, "7")

        # A non number raises an Exception
        self.assertRaises(Exception, parse_timedelta, "sevenm")
