# -*- coding: utf-8 -*-
"""
This tests the file lib.utils
"""
from .base import MyTestCase

from privacyidea.lib.utils import (parse_timelimit, parse_timedelta,
                                   check_time_in_range, parse_proxy,
                                   check_proxy, reduce_realms, is_true,
                                   parse_date, compare_condition,
                                   get_data_from_params, parse_legacy_time,
                                   int_to_hex, compare_value_value,
                                   parse_time_offset_from_now,
                                   parse_time_delta, to_unicode,
                                   hash_password, PasswordHash, check_ssha,
                                   check_sha, otrs_sha256, parse_int,
                                   convert_column_to_unicode)
from datetime import timedelta, datetime
from netaddr import IPAddress, IPNetwork, AddrFormatError
from dateutil.tz import tzlocal, tzoffset
from privacyidea.lib.tokenclass import DATE_FORMAT
import hashlib


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
        self.assertTrue(datetime.now(tzlocal()) < d)

        d = parse_date(" +12m ")
        self.assertTrue(datetime.now(tzlocal()) < d)

        d = parse_date(" +12H ")
        self.assertTrue(datetime.now(tzlocal()) + timedelta(hours=11) < d)

        d = parse_date(" +12d ")
        self.assertTrue(datetime.now(tzlocal()) + timedelta(days=11) < d)

        d = parse_date("")
        self.assertTrue(datetime.now(tzlocal()) >= d)

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

        d = parse_date("23.12.16")
        self.assertEqual(d, datetime(2016, 12, 23, 0, 0))

        d = parse_date("2017-04-27T12:00+0200")
        self.assertEqual(d, datetime(2017, 04, 27, 12, 0,
                                     tzinfo=tzoffset(None, 7200)))

        d = parse_date("2016/04/03")
        # April 3rd
        self.assertEqual(d, datetime(2016, 4, 3, 0, 0))

        d = parse_date("03.04.2016")
        # April 3rd
        self.assertEqual(d, datetime(2016, 4, 3, 0, 0))

        # Non matching date returns None
        self.assertEqual(parse_date("7 Januar 17"), None)

    def test_08_compare_condition(self):
        self.assertTrue(compare_condition("100", 100))
        self.assertTrue(compare_condition("=100", 100))
        self.assertTrue(compare_condition(" = 100 ", 100))

        self.assertFalse(compare_condition("100 ", 99))

        self.assertTrue(compare_condition(">100", 101))
        self.assertFalse(compare_condition(">100", 100))
        self.assertFalse(compare_condition(">100", 1))

        self.assertTrue(compare_condition("<100", 10))
        self.assertTrue(compare_condition("  <100", 10))
        self.assertFalse(compare_condition("<100", 1000))
        self.assertFalse(compare_condition("<100", 100))

    def test_09_get_data_from_params(self):
        config_description = {
            "local":  {
                'cakey': 'string',
                'cacert': 'string',
                'openssl.cnf': 'string',
                'WorkingDir': 'string',
                'CSRDir': 'sting',
                'CertificateDir': 'string',
                'CRLDir': 'string',
                'CRL_Validity_Period': 'int',
                'CRL_Overlap_Period': 'int'}}
        params = {"type": "local", "cakey": "key", "cacert": "cert",
                  "bindpw": "secret", "type.bindpw": "password"}
        data, types, desc = get_data_from_params(params,
                                                 ["caconnector", "type"],
                                                 config_description,
                                                 "CA connector",
                                                 "local")
        self.assertEqual(data.get("cakey"), "key")
        self.assertEqual(data.get("bindpw"), "secret")
        self.assertEqual(types.get("bindpw"), "password")

    def test_10_parse_legacy_time(self):
        s = parse_legacy_time("01/04/17 10:00")
        self.assertTrue(s.startswith("2017-04-01T10:00"))

        s = parse_legacy_time("30/04/17 10:00")
        self.assertTrue(s.startswith("2017-04-30T10:00"))

        s = parse_legacy_time("2017-04-01T10:00+0200")
        self.assertEqual(s, "2017-04-01T10:00+0200")

    def test_11_int_to_hex(self):
        h = int_to_hex(32)
        self.assertEqual(h, "20")

        h = int_to_hex(1)
        self.assertEqual(h, "01")

        h = int_to_hex(10)
        self.assertEqual(h, "0A")

        h = int_to_hex(256)
        self.assertEqual(h, "0100")

        h = int_to_hex(4096)
        self.assertEqual(h, "1000")

        h = int_to_hex(65536)
        self.assertEqual(h, "010000")

    def test_12_compare_value_value(self):
        self.assertTrue(compare_value_value("1000", ">", "999"))
        self.assertTrue(compare_value_value("ABD", ">", "ABC"))
        self.assertTrue(compare_value_value(1000, "==", "1000"))
        self.assertTrue(compare_value_value("99", "<", "1000"))

        # compare dates
        self.assertTrue(compare_value_value(
                        datetime.now(tzlocal()).strftime(DATE_FORMAT), ">",
                        "2017-01-01T10:00+0200"))
        self.assertFalse(compare_value_value(
            datetime.now(tzlocal()).strftime(DATE_FORMAT), "<",
            "2017-01-01T10:00+0200"))
        # The timestamp in 10 hours is bigger than the current time
        self.assertTrue(compare_value_value(
            (datetime.now(tzlocal()) + timedelta(hours=10)).strftime(DATE_FORMAT),
            ">", datetime.now(tzlocal()).strftime(DATE_FORMAT)))

    def test_13_parse_time_offset_from_now(self):
        td = parse_time_delta("+5s")
        self.assertEqual(td, timedelta(seconds=5))
        td = parse_time_delta("-12m")
        self.assertEqual(td, timedelta(minutes=-12))
        td = parse_time_delta("+123h")
        self.assertEqual(td, timedelta(hours=123))
        td = parse_time_delta("+2d")
        self.assertEqual(td, timedelta(days=2))

        # Does not start with plus or minus
        self.assertRaises(Exception, parse_time_delta, "12d")
        # Does not contains numbers
        self.assertRaises(Exception, parse_time_delta, "+twod")

        s, td = parse_time_offset_from_now("Hello {now}+5d with 5 days.")
        self.assertEqual(s, "Hello {now} with 5 days.")
        self.assertEqual(td, timedelta(days=5))

        s, td = parse_time_offset_from_now("Hello {current_time}+5m!")
        self.assertEqual(s, "Hello {current_time}!")
        self.assertEqual(td, timedelta(minutes=5))

        s, td = parse_time_offset_from_now("Hello {current_time}-3habc")
        self.assertEqual(s, "Hello {current_time}abc")
        self.assertEqual(td, timedelta(hours=-3))

    def test_14_to_unicode(self):
        s = "kölbel"
        su = to_unicode(s)
        self.assertEqual(su, u"kölbel")

        s = u"kölbel"
        su = to_unicode(s)
        self.assertEqual(su, u"kölbel")

    def test_15_hash_passwords(self):
        p_hash = hash_password("pass0rd", "phpass")
        PH = PasswordHash()
        self.assertTrue(PH.check_password("pass0rd", p_hash))
        self.assertFalse(PH.check_password("passord", p_hash))

        # {SHA}
        p_hash = hash_password("passw0rd", "sha")
        self.assertTrue(check_sha(p_hash, "passw0rd"))
        self.assertFalse(check_sha(p_hash, "password"))

        # OTRS
        p_hash = hash_password("passw0rd", "otrs")
        self.assertTrue(otrs_sha256(p_hash, "passw0rd"))
        self.assertFalse(otrs_sha256(p_hash, "password"))

        # {SSHA}
        p_hash = hash_password("passw0rd", "ssha")
        self.assertTrue(check_ssha(p_hash, "passw0rd", hashlib.sha1, 20))
        self.assertFalse(check_ssha(p_hash, "password", hashlib.sha1, 20))

        # {SSHA256}
        p_hash = hash_password("passw0rd", "ssha256")
        self.assertTrue(check_ssha(p_hash, "passw0rd", hashlib.sha256, 32))
        self.assertFalse(check_ssha(p_hash, "password", hashlib.sha256, 32))

        # {SSHA512}
        p_hash = hash_password("passw0rd", "ssha512")
        self.assertTrue(check_ssha(p_hash, "passw0rd", hashlib.sha512, 64))
        self.assertFalse(check_ssha(p_hash, "password", hashlib.sha512, 64))

    def test_16_parse_int(self):
        r = parse_int("xxx", 12)
        self.assertEqual(r, 12)
        r = parse_int("ABC", 11)
        self.assertEqual(r, 2748)
        r = parse_int("ABCX", 11)
        self.assertEqual(r, 11)
        r = parse_int(123)
        self.assertEqual(r, 123)
        r = parse_int(0x12)
        self.assertEqual(r, 18)
        r = parse_int("0x12")
        self.assertEqual(r, 18)
        r = parse_int("123")
        self.assertEqual(r, 123)

    def test_17_convert_column_to_unicode(self):
        self.assertEqual(convert_column_to_unicode(None), None)
        self.assertEqual(convert_column_to_unicode(True), "True")
        self.assertEqual(convert_column_to_unicode(False), "False")
        self.assertEqual(convert_column_to_unicode(b"yes"), u"yes")
        self.assertEqual(convert_column_to_unicode(u"yes"), u"yes")
