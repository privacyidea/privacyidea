"""
This tests the file lib.utils
"""
from .base import MyTestCase

from privacyidea.lib.utils import (parse_timelimit, parse_timedelta,
                                   check_time_in_range, parse_proxy,
                                   check_proxy, reduce_realms, is_true,
                                   parse_date)
from datetime import timedelta, datetime
from netaddr import IPAddress, IPNetwork, AddrFormatError


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

        tdelta = parse_timedelta("30 m ")
        self.assertEqual(tdelta, timedelta(minutes=30))

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

        # Wrong proxy setting. No commas (issue 526)
        proxy_def = " 10.0.0.12 1.2.3.4/16> 192.168.1.0/24 172.16.0.1 " \
                    ">10.0.0.0/8   "
        self.assertRaises(AddrFormatError, parse_proxy, proxy_def)
        self.assertFalse(check_proxy("10.0.0.12", "1.2.3.4", proxy_def))

    def test_05_reduce_realms(self):
        realms = {'defrealm': {'default': False,
                               'option': '',
                               'resolver': [
                                    {'priority': None,
                                     'type': 'passwdresolver',
                                     'name': 'deflocal'}]},
                  'localsql': {'default': True,
                               'option': '',
                               'resolver': [
                                    {'priority': None,
                                     'type': 'sqlresolver',
                                     'name': 'localusers2'}]}}
        # The policy dictionary contains much more entries, but for us only
        # the realm is relevant
        policies = [{'realm': []}]
        r = reduce_realms(realms, policies)
        self.assertTrue("defrealm" in r)
        self.assertTrue("localsql" in r)

        policies = [{'realm': []},
                    {'realm': ["defrealm"]}]
        r = reduce_realms(realms, policies)
        self.assertTrue("defrealm" in r)
        self.assertTrue("localsql" in r)

        policies = [{'realm': ["defrealm"]},
                    {'realm': []}]
        r = reduce_realms(realms, policies)
        self.assertTrue("defrealm" in r)
        self.assertTrue("localsql" in r)

        policies = [{'realm': ["localsql"]},
                    {'realm': ["defrealm"]}]
        r = reduce_realms(realms, policies)
        self.assertTrue("defrealm" in r, r)
        self.assertTrue("localsql" in r, r)

        policies = [{'realm': ["localsql"]},
                    {'realm': ["localsql", "defrealm"]}]
        r = reduce_realms(realms, policies)
        self.assertTrue("defrealm" in r)
        self.assertTrue("localsql" in r)

        policies = [{'realm': ["realm1", "localsql", "realm2"]},
                    {'realm': ["localsql", "realm1"]}]
        r = reduce_realms(realms, policies)
        self.assertTrue("defrealm" not in r)
        self.assertTrue("localsql" in r)

    def test_06_is_true(self):
        self.assertFalse(is_true(None))
        self.assertFalse(is_true(0))
        self.assertFalse(is_true("0"))
        self.assertFalse(is_true(False))
        self.assertFalse(is_true("false"))

        self.assertTrue(is_true(1))
        self.assertTrue(is_true("1"))
        self.assertTrue(is_true("True"))
        self.assertTrue(is_true("TRUE"))
        self.assertTrue(is_true(True))

    def test_07_parse_date(self):
        d = parse_date("+12m")
        self.assertTrue(datetime.now() < d)

        d = parse_date(" +12m ")
        self.assertTrue(datetime.now() < d)

        d = parse_date(" +12H ")
        self.assertTrue(datetime.now() + timedelta(hours=11) < d)

        d = parse_date(" +12d ")
        self.assertTrue(datetime.now() + timedelta(days=11) < d)

        d = parse_date("")
        self.assertTrue(datetime.now() >= d)

        d = parse_date("2016/12/23")
        self.assertEqual(d, datetime(2016, 12, 23))

        d = parse_date("23.12.2016")
        self.assertEqual(d, datetime(2016, 12, 23))

        d = parse_date("2016/12/23 9:30pm")
        self.assertEqual(d, datetime(2016, 12, 23, hour=21, minute=30))

        d = parse_date("2016/12/23 10:30am")
        self.assertEqual(d, datetime(2016, 12, 23, hour=10, minute=30))

        d = parse_date("23.12.2016 21:30")
        self.assertEqual(d, datetime(2016, 12, 23, hour=21, minute=30))

        d = parse_date("23.12.2016 6:30")
        self.assertEqual(d, datetime(2016, 12, 23, hour=6, minute=30))

        # Non-matching date returns None
        d = parse_date("23.12.16")
        self.assertEqual(d, None)
