"""
This tests the file lib.utils
"""
from .base import MyTestCase

from privacyidea.lib.utils import (parse_timelimit, parse_timedelta,
                                   check_time_in_range, parse_proxy,
                                   check_proxy)
from datetime import timedelta, datetime
from netaddr import IPAddress, IPNetwork


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

    def test_03_check_time_in_range(self):
        # April 5th, 2016 is a Tuesday
        t = datetime(2016, 4, 5, hour=9, minute=12)
        r = check_time_in_range("Mon-Fri: 09:00-17:30", t)
        self.assertEqual(r, True)
        r = check_time_in_range("Mon - Fri : 09:00- 17:30", t)
        self.assertEqual(r, True)
        r = check_time_in_range("Sat-Sun:10:00-15:00, Mon - Fri : 09:00- "
                                "17:30", t)
        self.assertEqual(r, True)

        # Short time description
        r = check_time_in_range("Tue: 9-15", t)
        self.assertEqual(r, True)
        r = check_time_in_range("Tue: 9-15:1", t)
        self.assertEqual(r, True)

        # day out of range
        r = check_time_in_range("Wed - Fri: 09:00-17:30", t)
        self.assertEqual(r, False)

        # time out of range
        r = check_time_in_range("Mon-Fri: 09:30-17:30", t)
        self.assertEqual(r, False)

        # A time with a missing leading 0 matches anyway
        r = check_time_in_range("Mon-Fri: 9:12-17:30", t)
        self.assertEqual(r, True)

        # Nonsense will not match
        r = check_time_in_range("Mon-Wrong: asd-17:30", t)
        self.assertEqual(r, False)

    def test_04_check_overrideclient(self):
        proxy_def = " 10.0.0.12, 1.2.3.4/16> 192.168.1.0/24, 172.16.0.1 " \
                    ">10.0.0.0/8   "
        r = parse_proxy(proxy_def)

        self.assertEqual(len(r), 3)
        for proxy, clients in r.items():
            if IPAddress("10.0.0.12") in proxy:
                self.assertTrue(IPAddress("1.2.3.4") in clients)
            elif IPAddress("1.2.3.3") in proxy:
                self.assertTrue(IPAddress("192.168.1.1") in clients)
            elif IPAddress("172.16.0.1") in proxy:
                self.assertEqual(clients, IPNetwork("10.0.0.0/8"))
            else:
                assert("The proxy {0!s} was not found!".format(proxy))


        self.assertTrue(check_proxy("10.0.0.12", "1.2.3.4", proxy_def))
        self.assertFalse(check_proxy("10.0.0.11", "1.2.3.4", proxy_def))
        self.assertTrue(check_proxy("1.2.3.10", "192.168.1.12", proxy_def))
        self.assertFalse(check_proxy("172.16.0.1", "1.2.3.4", proxy_def))
        self.assertTrue(check_proxy("172.16.0.1", "10.1.2.3", proxy_def))

