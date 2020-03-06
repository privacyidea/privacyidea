# -*- coding: utf-8 -*-
"""
This tests the package lib.utils
"""
from .base import MyTestCase

from privacyidea.lib.utils import (parse_timelimit,
                                   check_time_in_range, parse_proxy,
                                   check_proxy, reduce_realms, is_true,
                                   parse_date, compare_condition,
                                   get_data_from_params, parse_legacy_time,
                                   int_to_hex, compare_value_value,
                                   parse_time_offset_from_now, censor_connect_string,
                                   parse_timedelta, to_unicode,
                                   parse_int, convert_column_to_unicode,
                                   truncate_comma_list, check_pin_policy,
                                   get_module_class, decode_base32check,
                                   get_client_ip, sanity_name_check, to_utf8,
                                   to_byte_string, hexlify_and_unicode,
                                   b32encode_and_unicode, to_bytes,
                                   b64encode_and_unicode, create_png, create_img,
                                   convert_timestamp_to_utc, modhex_encode,
                                   modhex_decode, checksum, urlsafe_b64encode_and_unicode,
                                   check_ip_in_policy, split_pin_pass, create_tag_dict,
                                   check_serial_valid, determine_logged_in_userparams)
from datetime import timedelta, datetime
from netaddr import IPAddress, IPNetwork, AddrFormatError
from dateutil.tz import tzlocal, tzoffset, gettz
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.error import PolicyError
import binascii


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

    def test_04a_parse_proxy(self):
        self.assertEqual(parse_proxy(""), set())
        # 127.0.0.1 may rewrite to any IP
        self.assertEqual(parse_proxy("127.0.0.1"),
                         {(IPNetwork("127.0.0.1/32"), IPNetwork("0.0.0.0/0"))})
        # 127.0.0.x may rewrite to 10.0.x.x
        self.assertEqual(parse_proxy("127.0.0.1/24 >  10.0.0.0/16"),
                         {(IPNetwork("127.0.0.1/24"), IPNetwork("10.0.0.0/16"))})
        # 127.0.0.x may rewrite to 10.0.x.x or 10.1.x.x which may rewrite to 10.2.0.x
        self.assertEqual(parse_proxy("127.0.0.1/24>10.0.0.0/16, 127.0.0.1/24>10.1.0.0/16>10.2.0.0/24"),
                         {
                             (IPNetwork("127.0.0.1/24"), IPNetwork("10.0.0.0/16")),
                             (IPNetwork("127.0.0.1/24"), IPNetwork("10.1.0.0/16"), IPNetwork("10.2.0.0/24"))
                         })

    def test_04b_check_overrideclient(self):
        proxy_def = " 10.0.0.12, 1.2.3.4/16> 192.168.1.0/24, 172.16.0.1 " \
                    ">10.0.0.0/8   "
        r = parse_proxy(proxy_def)

        self.assertEqual(len(r), 3)
        self.assertIn((IPNetwork("1.2.3.4/16"), IPNetwork("192.168.1.0/24")), r)
        self.assertIn((IPNetwork("10.0.0.12/32"), IPNetwork("0.0.0.0/0")), r)
        self.assertIn((IPNetwork("172.16.0.1/32"), IPNetwork("10.0.0.0/8")), r)

        # check paths with only a single hop
        self.assertEqual(check_proxy(list(map(IPAddress, ["10.0.0.12", "1.2.3.4"])), proxy_def),
                         IPAddress("1.2.3.4"))  # 10.0.0.12 may map to 1.2.3.4
        self.assertEqual(check_proxy(list(map(IPAddress, ["10.0.0.11", "1.2.3.4"])), proxy_def),
                         IPAddress("10.0.0.11"))  # 10.0.0.11 may not map to 1.2.3.4
        self.assertEqual(check_proxy(list(map(IPAddress, ["1.2.3.10", "192.168.1.12"])), proxy_def),
                         IPAddress("192.168.1.12"))  # 1.2.3.10 may map to 192.168.1.12
        self.assertEqual(check_proxy(list(map(IPAddress, ["172.16.0.1", "1.2.3.4"])), proxy_def),
                         IPAddress("172.16.0.1"))  # 172.16.0.1 may not map to 1.2.3.4
        self.assertEqual(check_proxy(list(map(IPAddress, ["172.16.0.1", "10.1.2.3"])), proxy_def),
                         IPAddress("10.1.2.3"))  # 172.16.0.1 may map to 10.1.2.3

        # Wrong proxy setting. No commas (issue 526)
        proxy_def = " 10.0.0.12 1.2.3.4/16> 192.168.1.0/24 172.16.0.1 " \
                    ">10.0.0.0/8   "
        self.assertRaises(AddrFormatError, parse_proxy, proxy_def)
        # 10.0.0.12 is not allowed to map because the proxy settings are invalid
        self.assertEqual(check_proxy(list(map(IPAddress, ["10.0.0.12", "1.2.3.4"])), proxy_def),
                         IPAddress("10.0.12"))

        # check paths with several hops
        # 1.2.3.4 -------> 10.0.0.1 -------> 192.168.1.1 --------> privacyIDEA
        #  client           proxy1              proxy2
        path_to_client = list(map(IPAddress, ["192.168.1.1", "10.0.0.1", "1.2.3.4"]))
        # no proxy setting: client IP is proxy2
        self.assertEqual(check_proxy(path_to_client, ""),
                         IPAddress("192.168.1.1"))
        # proxy2 may map to 10.0.1.x: client IP is proxy2
        self.assertEqual(check_proxy(path_to_client, "192.168.1.1>10.0.1.0/24"),
                         IPAddress("192.168.1.1"))
        # proxy2 may map to 10.0.0.x: client IP is proxy1
        self.assertEqual(check_proxy(path_to_client, "192.168.1.1>10.0.0.0/24"),
                         IPAddress("10.0.0.1"))
        # proxy2 may map to 10.0.0.x, which may map to 2.3.4.x but not 1.2.3.4, so
        # the proxy definition does not match and the client IP is proxy2
        self.assertEqual(check_proxy(path_to_client, "192.168.1.1>10.0.0.0/24>2.3.4.0/24"),
                         IPAddress("192.168.1.1"))
        # 10.0.0.x may map to 2.3.4.x, but it doesn't matter because there is proxy2 inbetween
        self.assertEqual(check_proxy(path_to_client, "10.0.0.0/24>2.3.4.0/24"),
                         IPAddress("192.168.1.1"))
        # proxy2 may map to 10.0.0.x, which may map to 1.2.x.x or 2.3.4.x, so client IP is 1.2.3.4
        self.assertEqual(check_proxy(path_to_client,
                                     "192.168.1.1>10.0.0.0/24>2.3.4.0/24, 192.168.1.1>10.0.0.0/24>1.2.0.0/16"),
                         IPAddress("1.2.3.4"))
        # the order of proxy definitions is irrelevant
        self.assertEqual(check_proxy(path_to_client,
                                     "192.168.1.1>10.0.0.0/24>1.2.0.0/16, 192.168.1.1>10.0.0.0/24>2.3.4.0/24"),
                         IPAddress("1.2.3.4"))
        # proxy2 may map anywhere, and the next proxy may also map anywhere,
        # so we end up with 1.2.3.4
        self.assertEqual(check_proxy(path_to_client,
                                     "192.168.1.1>0.0.0.0/0>0.0.0.0/0"),
                         IPAddress("1.2.3.4"))
        # but if the next proxy may only map to 2.x.x.x, the proxy path does not match and we end up with proxy2.
        self.assertEqual(check_proxy(path_to_client,
                                     "192.168.1.1>0.0.0.0/0>2.0.0.0/8"),
                         IPAddress("192.168.1.1"))

        # another example
        path_to_client = list(map(IPAddress, ["10.1.1.1", "10.2.3.4", "192.168.1.1"]))
        self.assertEqual(check_proxy(path_to_client,
                                     "10.1.1.1/32>10.2.3.0/24>192.168.0.0/16"),
                         IPAddress("192.168.1.1"))
        self.assertEqual(check_proxy(path_to_client,
                                     "10.1.1.1/32>192.168.0.0/16"),
                         IPAddress("10.1.1.1"))
        self.assertEqual(check_proxy(path_to_client,
                                     "10.1.1.1/32>10.2.3.0/24>192.168.3.0/24"),
                         IPAddress("10.1.1.1"))

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

        r = reduce_realms(realms, None)
        self.assertTrue("defrealm" in r)
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

        d = parse_date("+5")
        self.assertTrue(datetime.now(tzlocal()) >= d)

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
        self.assertEqual(d, datetime(2017, 4, 27, 12, 0,
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

        # There are invalid conditions, which should not raise an exception
        # An empty condition will result in False
        self.assertFalse(compare_condition("", 100))
        # An invalid condition, which misses a compare-value, will result in false
        self.assertFalse(compare_condition(">", 100))

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
        td = parse_timedelta("+5s")
        self.assertEqual(td, timedelta(seconds=5))
        td = parse_timedelta("-12m")
        self.assertEqual(td, timedelta(minutes=-12))
        td = parse_timedelta("+123h")
        self.assertEqual(td, timedelta(hours=123))
        td = parse_timedelta("+2d")
        self.assertEqual(td, timedelta(days=2))

        # It is allowed to start without a +/- which would mean a +
        td = parse_timedelta("12d")
        self.assertEqual(td, timedelta(days=12))

        # Does not contains numbers
        self.assertRaises(Exception, parse_timedelta, "+twod")

        s, td = parse_time_offset_from_now("Hello {now}+5d with 5 days.")
        self.assertEqual(s, "Hello {now} with 5 days.")
        self.assertEqual(td, timedelta(days=5))

        s, td = parse_time_offset_from_now("Hello {current_time}+5m!")
        self.assertEqual(s, "Hello {current_time}!")
        self.assertEqual(td, timedelta(minutes=5))

        s, td = parse_time_offset_from_now("Hello {current_time}-3habc")
        self.assertEqual(s, "Hello {current_time}abc")
        self.assertEqual(td, timedelta(hours=-3))

    def test_14_convert_timestamp_to_utc(self):
        d = datetime.now(tz=gettz('America/New York'))
        d_utc = convert_timestamp_to_utc(d)
        self.assertGreater(d_utc, d.replace(tzinfo=None))

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

    def test_18_censor_connect_string(self):
        self.assertEqual(censor_connect_string("sqlite:////home/foo/privacyidea/privacyidea/data.sqlite"),
                         "sqlite:////home/foo/privacyidea/privacyidea/data.sqlite")
        self.assertEqual(censor_connect_string("mysql://pi@localhost/pi"),
                         "mysql://pi@localhost/pi")
        self.assertEqual(censor_connect_string("mysql://pi:kW44sqqWtGYX@localhost/pi"),
                         "mysql://pi:xxxx@localhost/pi")
        self.assertEqual(censor_connect_string("psql+odbc://pi@localhost/pi"),
                         "psql+odbc://pi@localhost/pi")
        self.assertEqual(censor_connect_string("psql+odbc://pi:MySecretPassword123466$@localhost/pi"),
                         "psql+odbc://pi:xxxx@localhost/pi")
        self.assertEqual(censor_connect_string("mysql://pi:kW44s@@qqWtGYX@localhost/pi"),
                         "mysql://pi:xxxx@localhost/pi")
        self.assertEqual(censor_connect_string(u"mysql://knöbel:föö@localhost/pi"),
                         u"mysql://knöbel:xxxx@localhost/pi")

    def test_19_truncate_comma_list(self):
        r = truncate_comma_list("123456,234567,345678", 19)
        self.assertEqual(len(r), 19)
        self.assertEqual(r, "1234+,234567,345678")

        r = truncate_comma_list("123456,234567,345678", 18)
        self.assertEqual(len(r), 18)
        self.assertEqual(r, "1234+,2345+,345678")

        r = truncate_comma_list("123456,234567,345678", 16)
        self.assertEqual(len(r), 16)
        self.assertEqual(r, "123+,2345+,3456+")

        # There are more entries than the max_len. We will not be able
        # to shorten all entries, so we simply take the beginning of the string.
        r = truncate_comma_list("12,234567,3456,989,123,234,234", 4)
        self.assertEqual(len(r), 4)
        self.assertEqual(r, "12,+")

    def test_20_pin_policy(self):
        # Unspecified character specifier
        self.assertRaises(PolicyError, check_pin_policy, "1234", "+o")

        r, c = check_pin_policy("1234", "n")
        self.assertTrue(r)

        r, c = check_pin_policy("[[[", "n")
        self.assertFalse(r)

        r, c = check_pin_policy("[[[", "c")
        self.assertFalse(r)

        r, c = check_pin_policy("[[[", "s")
        self.assertTrue(r)

        r, c = check_pin_policy("abc", "nc")
        self.assertFalse(r)
        self.assertEqual("Missing character in PIN: [0-9]", c)

        r, c = check_pin_policy("123", "nc")
        self.assertFalse(r)
        self.assertEqual(r"Missing character in PIN: [a-zA-Z]", c)

        r, c = check_pin_policy("123", "ncs")
        self.assertFalse(r)
        self.assertTrue(r"Missing character in PIN: [a-zA-Z]" in c, c)
        self.assertTrue(r"Missing character in PIN: [\[\].:,;_<>+*!/()=?$§%&#~^-]" in c, c)

        r, c = check_pin_policy("1234", "")
        self.assertFalse(r)
        self.assertEqual(c, "No policy given.")

        # check for either number or character
        r, c = check_pin_policy("1234", "+cn")
        self.assertTrue(r)

        r, c = check_pin_policy("1234xxxx", "+cn")
        self.assertTrue(r)

        r, c = check_pin_policy("xxxx", "+cn")
        self.assertTrue(r)
        self.assertTrue(check_pin_policy("test1234", "+cn")[0])
        self.assertTrue(check_pin_policy("test12$$", "+cn")[0])
        self.assertTrue(check_pin_policy("test12", "+cn")[0])
        self.assertTrue(check_pin_policy("1234", "+cn")[0])

        r, c = check_pin_policy("@@@@", "+cn")
        self.assertFalse(r)
        self.assertEqual(c, "Missing character in PIN: [a-zA-Z]|[0-9]")

        # check for exclusion
        # No special character
        r, c = check_pin_policy("1234", "-s")
        self.assertTrue(r)
        r, c = check_pin_policy("1234aaaa", "-s")
        self.assertTrue(r)
        r, c = check_pin_policy("1234aaaa//", "-s")
        self.assertFalse(r)

        # A pin that falsely contains a number
        r, c = check_pin_policy("1234aaa", "-sn")
        self.assertFalse(r)
        self.assertEqual(c, "Not allowed character in PIN!")
        r, c = check_pin_policy("///aaa", "-sn")
        self.assertFalse(r)
        # A pin without a number and without a special
        r, c = check_pin_policy("xxxx", "-sn")
        self.assertTrue(r)

        r, c = check_pin_policy("1234@@@@", "-c")
        self.assertTrue(r)

        # A pin with only digits allowed
        r, c = check_pin_policy("1234", "-cs")
        self.assertTrue(r)
        r, c = check_pin_policy("a1234", "-cs")
        self.assertFalse(r)

        # A pin with only a specified list of chars
        r, c = check_pin_policy("1234111", "[1234]")
        self.assertTrue(r)
        r, c = check_pin_policy("12345", "[1234]")
        self.assertFalse(r)

    def test_21_get_module_class(self):
        r = get_module_class("privacyidea.lib.auditmodules.sqlaudit", "Audit", "log")
        from privacyidea.lib.auditmodules.sqlaudit import Audit
        self.assertEqual(r, Audit)

        # Fails to return the class, if the method does not exist
        self.assertRaises(NameError, get_module_class, "privacyidea.lib.auditmodules.sqlaudit", "Audit",
                          "this_method_does_not_exist")

        # Fails if the class does not exist
        with self.assertRaises(ImportError):
            get_module_class("privacyidea.lib.auditmodules.sqlaudit", "DoesNotExist")

        # Fails if the package does not exist
        with self.assertRaises(ImportError):
            get_module_class("privacyidea.lib.auditmodules.doesnotexist", "Aduit")

    def test_22_decodebase32check(self):
        real_client_componet = "TIXQW4ydvn2aos4cj6ta"
        real_payload = "03ab74074b824fa6"

        payload1 = decode_base32check(real_client_componet)
        self.assertEqual(payload1, real_payload)

        # change the client component in the last character!
        client_component = "TIXQW4ydvn2aos4cj6tb"
        payload2 = decode_base32check(client_component)
        # Although the last character of the client component was changed,
        # the payload is still the same.
        self.assertEqual(payload2, real_payload)

        # change the client component in between
        client_component = "TIXQW4ydvn2aos4cj6ba"
        self.assertRaises(Exception, decode_base32check, client_component)

    def test_23_get_client_ip(self):

        class RequestMock():
            blueprint = None
            remote_addr = None
            all_data = {}
            access_route = []

        r = RequestMock()
        r.blueprint = "token_blueprint"
        # The real client
        direct_client = "10.0.0.1"
        r.remote_addr = direct_client
        # The client parameter
        client_parameter = "192.168.2.1"
        r.all_data = {"client": client_parameter}
        # The X-Forwarded-For
        client_proxy = "172.16.1.2"
        r.access_route = [client_proxy]

        # Setup:
        # 192.168.2.1 ---------> 172.16.1.2 -------> 10.0.0.1 --------> privacyIDEA
        # client_parameter       client_proxy        direct_client

        ip = get_client_ip(r, "")
        self.assertEqual(ip, direct_client)

        # If there is a proxy_setting, the X-Forwarded-For will
        # work, but not the client_parameter
        ip = get_client_ip(r, "10.0.0.1")
        self.assertEqual(ip, client_proxy)

        # If the request is a validate request:
        r.blueprint = "validate_blueprint"
        # ... the direct client may map anywhere, but as we also have a X-Forwarded-For header,
        # the header takes precedence!
        ip = get_client_ip(r, "10.0.0.1")
        self.assertEqual(ip, client_proxy)
        # ... if we now also allow the client_proxy to rewrite IPs, the client parameter is respected
        ip = get_client_ip(r, "10.0.0.1>172.16.1.2>0.0.0.0/0")
        self.assertEqual(ip, client_parameter)
        # ... even if we have multiple proxy settings
        ip = get_client_ip(r, "10.0.0.1>198.168.1.3, 10.0.0.1>172.16.1.2>1.2.3.4,   10.0.0.1>172.16.1.2>0.0.0.0/0")
        self.assertEqual(ip, client_parameter)
        # Check situation if there is no X-Forwarded-For header, but a client parameter:
        r.access_route = [direct_client]
        ip = get_client_ip(r, "10.0.0.1")
        self.assertEqual(ip, client_parameter)
        # The client parameter is not respected for the token endpoints
        r.blueprint = "token_blueprint"
        ip = get_client_ip(r, "10.0.0.1")
        self.assertEqual(ip, direct_client)

    def test_24_sanity_name_check(self):
        self.assertTrue(sanity_name_check('Hello_World'))
        with self.assertRaisesRegexp(Exception, "non conformant characters in the name"):
            sanity_name_check('Hello World!')
        self.assertTrue(sanity_name_check('Hello World', name_exp='^[A-Za-z\\ ]+$'))
        with self.assertRaisesRegexp(Exception, "non conformant characters in the name"):
            sanity_name_check('Hello_World', name_exp='^[A-Za-z]+$')

    def test_25_encodings(self):
        u = u'Hello Wörld'
        b = b'Hello World'
        self.assertEquals(to_utf8(None), None)
        self.assertEquals(to_utf8(u), u.encode('utf8'))
        self.assertEquals(to_utf8(b), b)

        self.assertEquals(to_unicode(u), u)
        self.assertEquals(to_unicode(b), b.decode('utf8'))
        self.assertEquals(to_unicode(None), None)
        self.assertEquals(to_unicode(10), 10)

        self.assertEquals(to_bytes(u), u.encode('utf8'))
        self.assertEquals(to_bytes(b), b)
        self.assertEquals(to_bytes(10), 10)

        self.assertEquals(to_byte_string(u), u.encode('utf8'))
        self.assertEquals(to_byte_string(b), b)
        self.assertEquals(to_byte_string(10), b'10')

    def test_26_conversions(self):
        self.assertEquals(hexlify_and_unicode(u'Hallo'), u'48616c6c6f')
        self.assertEquals(hexlify_and_unicode(b'Hallo'), u'48616c6c6f')
        self.assertEquals(hexlify_and_unicode(b'\x00\x01\x02\xab'), u'000102ab')

        self.assertEquals(b32encode_and_unicode(u'Hallo'), u'JBQWY3DP')
        self.assertEquals(b32encode_and_unicode(b'Hallo'), u'JBQWY3DP')
        self.assertEquals(b32encode_and_unicode(b'\x00\x01\x02\xab'), u'AAAQFKY=')

        self.assertEquals(b64encode_and_unicode(u'Hallo'), u'SGFsbG8=')
        self.assertEquals(b64encode_and_unicode(b'Hallo'), u'SGFsbG8=')
        self.assertEquals(b64encode_and_unicode(b'\x00\x01\x02\xab'), u'AAECqw==')

        self.assertEquals(urlsafe_b64encode_and_unicode(u'Hallo'), u'SGFsbG8=')
        self.assertEquals(urlsafe_b64encode_and_unicode(b'Hallo'), u'SGFsbG8=')
        self.assertEquals(urlsafe_b64encode_and_unicode(b'\x00\x01\x02\xab'), u'AAECqw==')
        self.assertEquals(urlsafe_b64encode_and_unicode(b'\xfa\xfb\xfc\xfd\xfe\xff'),
                          u'-vv8_f7_')

    def test_27_images(self):
        png_b64 = u'iVBORw0KGgoAAAANSUhEUgAAASIAAAEiAQAAAAB1xeIbAAABgElEQVR4nO2ZQ' \
                  u'Y6DMBAEaxbujpQH5CnwdPOglexjJKLeQ2xCsofdC4HA+IDAlERrGKx2Y+LvMX' \
                  u'z9AwKnnHLKKae2TlkZLZBbrM91pl9V1yGoTpKUwOx0M0UaSZKeqffrOgSVS49' \
                  u'LqZH1QPkMVtZ1KGq4jG9+4mGp9uXaoP1d/K2q3wcVJEVAsd6RNL5S79e1Z6r0' \
                  u'/WAANFiXzgA3W1fXEah77R/BgobL1SA8Rw1bVf/ZFHcr2aXmfpDSNKfxfqa4V' \
                  u'fWfTZU6E8Zi8mOQpNRI8TG3VfWfTc36XqrNTzdtq7z2y1G17wHFMH8Lkq85y1' \
                  u'Kz2peyP5Z/1eG1X4R69jkjRvhuNVyuJvKp3tiq+j1Qjxyz7K1y8f3Wr6pr39T' \
                  u'kJ6u7UYKZ7fE1Z3mq5phmJ1DMLYrcPL9/J6VII7oEkKclaH1dR6CsB6wPkvWU' \
                  u'JH8LuvZI1Qw5CMgg8hmRzyOEq7nPWZCa+3uY9rWpZsi+r12O+pVjwojKTOP/a' \
                  u'51yyimn9kL9ACOsApMnN2KuAAAAAElFTkSuQmCC'
        self.assertEquals(b64encode_and_unicode(create_png('Hallo')), png_b64)
        self.assertEquals(create_img('Hello', raw=True),
                          u'data:image/png;base64,SGVsbG8=')
        self.assertEquals(create_img('Hallo'),
                          u'data:image/png;base64,{0!s}'.format(png_b64))

    def test_28_yubikey_utils(self):
        self.assertEquals(modhex_encode(b'\x47'), 'fi')
        self.assertEquals(modhex_encode(b'\xba\xad\xf0\x0d'), 'nlltvcct')
        self.assertEquals(modhex_encode(binascii.unhexlify('0123456789abcdef')),
                          'cbdefghijklnrtuv')
        self.assertEquals(modhex_encode('Hallo'), 'fjhbhrhrhv')
        # and the other way around
        self.assertEquals(modhex_decode('fi'), b'\x47')
        self.assertEquals(modhex_decode('nlltvcct'), b'\xba\xad\xf0\x0d')
        self.assertEquals(modhex_decode('cbdefghijklnrtuv'),
                          binascii.unhexlify('0123456789abcdef'))
        self.assertEquals(modhex_decode('fjhbhrhrhv'), b'Hallo')

        # now test the crc function
        self.assertEquals(checksum(b'\x01\x02\x03\x04'), 0xc66e)
        self.assertEquals(checksum(b'\x01\x02\x03\x04\x919'), 0xf0b8)

    def test_29_check_ip(self):
        found, excluded = check_ip_in_policy("10.0.1.2", ["10.0.1.0/24", "1.1.1.1"])
        self.assertTrue(found)
        self.assertFalse(excluded)

        found, excluded = check_ip_in_policy("10.0.1.2", ["10.0.1.0/24", "!10.0.1.2"])
        self.assertTrue(excluded)
        self.assertTrue(found)

        # run a test for empty condition
        found, excluded = check_ip_in_policy("10.0.1.2", ["10.0.1.0/24", "!10.0.1.2", u'', None])
        self.assertTrue(excluded)
        self.assertTrue(found)

    def test_30_split_pin_pass(self):
        pin, otp = split_pin_pass("test1234", 4, True)
        self.assertEqual(pin, "test")
        self.assertEqual(otp, "1234")
        pin, otp = split_pin_pass("12345678hallo", 8, False)
        self.assertEqual(pin, "hallo")
        self.assertEqual(otp, "12345678")

    def test_31_create_tag_dict(self):
        class UserAgentMock():
            string = "<b>hello world</b>"
            browser = "browser"

        class RequestMock():
            user_agent = UserAgentMock()
            path = "/validate/check"
            url_root = ""

        recipient = {"givenname": u"<b>Sömeone</b>"}
        dict1 = create_tag_dict(request=RequestMock(), recipient=recipient)
        self.assertEqual(dict1["ua_string"], "<b>hello world</b>")
        self.assertEqual(dict1["action"], "/validate/check")
        self.assertEqual(dict1["recipient_givenname"], u"<b>Sömeone</b>")
        dict2 = create_tag_dict(request=RequestMock(), recipient=recipient, escape_html=True)
        self.assertEqual(dict2["ua_string"], "&lt;b&gt;hello world&lt;/b&gt;")
        self.assertEqual(dict2["action"], "/validate/check")
        self.assertEqual(dict2["recipient_givenname"], u"&lt;b&gt;Sömeone&lt;/b&gt;")

    def test_32_allowed_serial_numbers(self):
        self.assertTrue(check_serial_valid("TOTP12345"))
        # Blank is not allowed
        self.assertRaises(Exception, check_serial_valid, "TOTP 12345")

        # Minus and underscore is allowed
        self.assertTrue(check_serial_valid("spass-123"))
        self.assertTrue(check_serial_valid("spass_123"))
        # Slash and backslash is not allowed
        self.assertRaises(Exception, check_serial_valid, "spass/123")
        self.assertRaises(Exception, check_serial_valid, "spass\\123")

        # an empty serial is not allowed
        self.assertRaises(Exception, check_serial_valid, "")

    def test_33_determine_logged_in_user(self):
        (role, user, realm, adminuser, adminrealm) = determine_logged_in_userparams({"role": "user",
                                                                                      "username": "hans",
                                                                                      "realm": "realm1"}, {})

        self.assertEqual(role, "user")
        self.assertEqual(user, "hans")
        self.assertEqual(realm, "realm1")
        self.assertEqual(adminuser, None)
        self.assertEqual(adminrealm, None)

        (role, user, realm, adminuser, adminrealm) = determine_logged_in_userparams({"role": "admin",
                                                                                      "username": "hans",
                                                                                      "realm": "realm1"},
                                                                                     {"user": "peter",
                                                                                      "realm": "domain"})

        self.assertEqual(role, "admin")
        self.assertEqual(user, "peter")
        self.assertEqual(realm, "domain")
        self.assertEqual(adminuser, "hans")
        self.assertEqual(adminrealm, "realm1")

        self.assertRaises(PolicyError, determine_logged_in_userparams,
                          {"role": "marshal",
                           "username": "Wyatt Earp",
                           "realm": "Wild West"},
                          {"user": "Dave Rudabaugh",
                           "realm": "Dodge City"})