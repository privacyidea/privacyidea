"""
This tests the module lib.utils.compare
"""
import datetime

from privacyidea.lib.utils.compare import (compare_values, CompareError, parse_comma_separated_string,
                                           compare_ints, compare_generic, compare_time, PrimaryComparators,
                                           _get_datetime)
from .base import MyTestCase


class UtilsCompareTestCase(MyTestCase):
    def test_01_compare_equal(self):
        self.assertTrue(compare_values("hello", "equals", "hello"))
        self.assertTrue(compare_values(1, "equals", 1))
        self.assertFalse(compare_values("hello", "equals", " hello"))
        self.assertFalse(compare_values(1, "equals", 2))
        self.assertFalse(compare_values(1, "equals", "1"))
        # negation
        self.assertFalse(compare_values("hello", "!equals", "hello"))
        self.assertTrue(compare_values(1, "!equals", "1"))

    def test_02_compare_contains(self):
        self.assertTrue(compare_values(["hello", "world"], "contains", "hello"))
        self.assertTrue(compare_values(["hello", "world"], "contains", "world"))
        self.assertTrue(compare_values([1, "world"], "contains", 1))
        self.assertFalse(compare_values([1, "world"], "contains", [1, "world"]))

        # must pass a list
        with self.assertRaises(CompareError):
            compare_values("hello world", "contains", "hello")

        # negation
        self.assertTrue(compare_values([1, "world"], "!contains", "hello"))
        self.assertFalse(compare_values([1, "world"], "!contains", "world"))
        with self.assertRaises(CompareError):
            compare_values("hello world", "!contains", "hello")

    def test_03_compare_errors(self):
        with self.assertRaises(CompareError) as cm:
            compare_values("hello world", "something", "hello")
        self.assertIn("Invalid comparator", repr(cm.exception))

    def test_04_compare_matches(self):
        self.assertTrue(compare_values("hello world", "matches", "hello world"))
        self.assertTrue(compare_values("hello world", "matches", ".*world"))
        self.assertTrue(compare_values("uid=hello,cn=users,dc=test,dc=intranet", "matches",
                                       "uid=[^,]+,cn=users,dc=test,dc=intranet"))
        # only complete matches
        self.assertFalse(compare_values("hello world", "matches", "world"))
        self.assertFalse(compare_values("uid=hello,cn=users,dc=test,dc=intranet,dc=world", "matches",
                                        "uid=[^,]+,cn=users,dc=test,dc=intranet"))
        # supports more advanced regex features
        self.assertTrue(compare_values("hElLo WoRLd", "matches", "(?i)hello world( and stuff)?"))
        # raises errors on invalid patterns
        with self.assertRaises(CompareError):
            compare_values("hello world", "matches", "this is (invalid")

        # negation
        self.assertTrue(compare_values("uid=hello,cn=users,dc=test,dc=intranet", "!matches",
                                       "uid=[^,]+,cn=admins,dc=test,dc=intranet"))
        self.assertFalse(compare_values("uid=hello,cn=admins,dc=test,dc=intranet", "!matches",
                                        "uid=[^,]+,cn=admins,dc=test,dc=intranet"))

    def test_05_parse_comma_separated_string(self):
        self.assertEqual(parse_comma_separated_string("hello world"), ["hello world"])
        # whitespace immediately following a delimiter is skipped
        self.assertEqual(parse_comma_separated_string("realm1,     realm2,realm3"),
                         ["realm1", "realm2", "realm3"])
        # whitespace before delimiters is not skipped
        self.assertEqual(parse_comma_separated_string("  realm1  ,realm2"),
                         ["realm1  ", "realm2"])
        # strings can be quoted
        self.assertEqual(parse_comma_separated_string('realm1, "realm2", " realm3"'),
                         ["realm1", "realm2", " realm3"])
        # even with commas
        self.assertEqual(parse_comma_separated_string('realm1, "realm2, with a, strange, name", other stuff'),
                         ["realm1", "realm2, with a, strange, name", "other stuff"])
        # double quotes can be escaped
        self.assertEqual(parse_comma_separated_string(r'realm\", realm2'),
                         ['realm"', 'realm2'])
        # error if a string is not properly quoted
        with self.assertRaises(CompareError):
            parse_comma_separated_string('"no')
        # error if we pass multiple lines
        with self.assertRaises(CompareError):
            parse_comma_separated_string('realm1\nrealm2')
        # but we can quote newlines
        self.assertEqual(parse_comma_separated_string('"realm1\nrealm2"'),
                         ["realm1\nrealm2"])

    def test_06_compare_in(self):
        self.assertTrue(compare_values("hello", "in", "hello"))
        self.assertTrue(compare_values("world", "in", "hello, world, this is a list"))
        self.assertFalse(compare_values("hello", "in", "hello world"))
        self.assertFalse(compare_values("hello,world", "in", 'hello,world'))
        self.assertTrue(compare_values("hello,world", "in", '"hello,world"'))

        # negation
        self.assertTrue(compare_values("hello", "!in", "world"))
        self.assertFalse(compare_values("hello", "!in", " hello, world"))
        self.assertTrue(compare_values("hello", "!in", "hello world"))

    def test_07_smaller_and_bigger(self):
        self.assertTrue(compare_values("1", "<", 2))
        self.assertTrue(compare_values(7, ">", 1))
        self.assertFalse(compare_values("2", "<", "1"))
        self.assertFalse(compare_values(2, "<", 1))
        self.assertFalse(compare_values(2, ">", "2"))

        # Invalid inputs
        self.assertRaises(CompareError, compare_values, "1.0", "<", "2")
        self.assertRaises(CompareError, compare_values, "1", "<", "2.1")
        self.assertRaises(CompareError, compare_values, "1.0", ">", "0")
        self.assertRaises(CompareError, compare_values, "1", ">", "0.5")

    def test_08_get_datetime(self):
        date_time = datetime.datetime(2025, 1, 1, 12, 0,
                                      tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        self.assertEqual(date_time, _get_datetime(date_time))

        # Valid date strings
        # Different time zones
        self.assertEqual(date_time, _get_datetime("2025-01-01T12:00:00+02:00"))
        self.assertEqual(date_time, _get_datetime("2025-01-01T12:00:00+0200"))
        self.assertEqual(date_time, _get_datetime("2025-01-01T12:00:00+02"))
        # Different separator
        self.assertEqual(date_time, _get_datetime("2025-01-01 12:00:00+02:00"))
        self.assertEqual(date_time, _get_datetime("2025-01-01 12:00:00+0200"))
        # Date without time zone
        date_time_no_tz = date_time.replace(tzinfo=None)
        self.assertEqual(date_time_no_tz, _get_datetime("2025-01-01T12:00:00"))
        self.assertEqual(date_time_no_tz, _get_datetime("2025-01-01 12:00:00"))
        # Date without seconds
        self.assertEqual(date_time_no_tz, _get_datetime("2025-01-01T12:00"))
        self.assertEqual(date_time_no_tz, _get_datetime("2025-01-01 12:00"))
        # Date without minutes
        self.assertEqual(date_time_no_tz, _get_datetime("2025-01-01T12"))
        self.assertEqual(date_time_no_tz, _get_datetime("2025-01-01 12"))
        # Date only
        self.assertEqual(datetime.datetime(2025, 1, 1, 0, 0), _get_datetime("2025-01-01"))

        # Invalid date strings
        # Low precision dates
        self.assertRaises(CompareError, _get_datetime, "2025-01")
        self.assertRaises(CompareError, _get_datetime, "2025")
        # Invalid separators
        self.assertRaises(CompareError, _get_datetime, "2025/01/01 12:00:00+02:00")
        # Invalid date order
        self.assertRaises(CompareError, _get_datetime, "01-01-2025 12:00:00+02:00")
        # Invalid format
        self.assertRaises(CompareError, _get_datetime, "1. January 2025")


    def test_09_date_after(self):
        # Test with datetime objects
        condition_date = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        true_date = datetime.datetime(2025, 2, 1, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertTrue(compare_values(true_date, PrimaryComparators.DATE_AFTER, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 12, 0, 1, tzinfo=datetime.timezone.utc)
        self.assertTrue(compare_values(true_date, PrimaryComparators.DATE_AFTER, condition_date))
        true_date = datetime.datetime(2024, 1, 2, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertFalse(compare_values(true_date, PrimaryComparators.DATE_AFTER, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 11, 59, 59, tzinfo=datetime.timezone.utc)
        self.assertFalse(compare_values(true_date, PrimaryComparators.DATE_AFTER, condition_date))
        # test with different time zones
        true_date = datetime.datetime(2025, 1, 1, 13, 0, 0,
                                      tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        self.assertFalse(compare_values(true_date, PrimaryComparators.DATE_AFTER, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 11, 0, 0,
                                      tzinfo=datetime.timezone(-datetime.timedelta(hours=2)))
        self.assertTrue(compare_values(true_date, PrimaryComparators.DATE_AFTER, condition_date))

        # Test with date strings
        condition_date_str = "2025-01-01T12:00"
        true_date_str = "2025-02-01 12:00:00"
        self.assertTrue(compare_values(true_date_str, PrimaryComparators.DATE_AFTER, condition_date_str))
        true_date_str = "2025-01-01 12:00:01"
        self.assertTrue(compare_values(true_date_str, PrimaryComparators.DATE_AFTER, condition_date_str))
        true_date_str = "2024-02-01 12:00:00"
        self.assertFalse(compare_values(true_date_str, PrimaryComparators.DATE_AFTER, condition_date_str))
        true_date_str = "2025-01-01 11:59:32"
        self.assertFalse(compare_values(true_date_str, PrimaryComparators.DATE_AFTER, condition_date_str))
        # test with different time zones
        condition_date_str = "2025-01-01 12:00:00+00:00"
        true_date_str = "2025-01-01 13:00:55.203554+0200"
        self.assertFalse(compare_values(true_date_str, PrimaryComparators.DATE_AFTER, condition_date_str))
        true_date_str = "2025-01-01 11:00:00-02:00"
        self.assertTrue(compare_values(true_date_str, PrimaryComparators.DATE_AFTER, condition_date_str))

        # Invalid date formats
        self.assertRaises(CompareError, compare_values, true_date_str, PrimaryComparators.DATE_AFTER,
                          "2025/01/01 12:00")
        self.assertRaises(CompareError, compare_values, true_date_str, PrimaryComparators.DATE_AFTER, 2025)
        self.assertRaises(CompareError, compare_values, 102, PrimaryComparators.DATE_AFTER, condition_date_str)
        # Only one time stamp contains time zone information
        self.assertRaises(CompareError, compare_values, "2025-01-01 12:00", PrimaryComparators.DATE_AFTER,
                          "2025-01-01 12:00+02:00")
        self.assertRaises(CompareError, compare_values, "2025-01-01 12:00-02:00", PrimaryComparators.DATE_AFTER,
                          "2025-01-01 12:00")

    def test_10_date_before(self):
        # Test with datetime objects
        condition_date = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        true_date = datetime.datetime(2025, 2, 1, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertFalse(compare_values(true_date, PrimaryComparators.DATE_BEFORE, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 12, 0, 1, tzinfo=datetime.timezone.utc)
        self.assertFalse(compare_values(true_date, PrimaryComparators.DATE_BEFORE, condition_date))
        true_date = datetime.datetime(2024, 1, 2, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertTrue(compare_values(true_date, PrimaryComparators.DATE_BEFORE, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 11, 59, 59, tzinfo=datetime.timezone.utc)
        self.assertTrue(compare_values(true_date, PrimaryComparators.DATE_BEFORE, condition_date))
        # test with different time zones
        true_date = datetime.datetime(2025, 1, 1, 13, 0, 0,
                                      tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        self.assertTrue(compare_values(true_date, PrimaryComparators.DATE_BEFORE, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 11, 0, 0,
                                      tzinfo=datetime.timezone(-datetime.timedelta(hours=2)))
        self.assertFalse(compare_values(true_date, PrimaryComparators.DATE_BEFORE, condition_date))

        # Test with date strings
        condition_date_str = "2025-01-01T12:00"
        true_date_str = "2025-02-01 12:00:00"
        self.assertFalse(compare_values(true_date_str, PrimaryComparators.DATE_BEFORE, condition_date_str))
        true_date_str = "2025-01-01 12:00:01"
        self.assertFalse(compare_values(true_date_str, PrimaryComparators.DATE_BEFORE, condition_date_str))
        true_date_str = "2024-02-01 12:00:00"
        self.assertTrue(compare_values(true_date_str, PrimaryComparators.DATE_BEFORE, condition_date_str))
        true_date_str = "2025-01-01 11:59:32"
        self.assertTrue(compare_values(true_date_str, PrimaryComparators.DATE_BEFORE, condition_date_str))
        # test with different time zones
        condition_date_str = "2025-01-01 12:00:00+00:00"
        true_date_str = "2025-01-01 13:00:55.203554+0200"
        self.assertTrue(compare_values(true_date_str, PrimaryComparators.DATE_BEFORE, condition_date_str))
        true_date_str = "2025-01-01 11:00:00-02:00"
        self.assertFalse(compare_values(true_date_str, PrimaryComparators.DATE_BEFORE, condition_date_str))

        # Invalid date formats
        self.assertRaises(CompareError, compare_values, "12", PrimaryComparators.DATE_BEFORE, condition_date_str)
        self.assertRaises(CompareError, compare_values, true_date_str, PrimaryComparators.DATE_BEFORE, 2025)
        self.assertRaises(CompareError, compare_values, 102, PrimaryComparators.DATE_BEFORE, condition_date_str)
        # Only one time stamp contains time zone information
        self.assertRaises(CompareError, compare_values, "2025-01-01 12:00", PrimaryComparators.DATE_BEFORE,
                          "2025-01-01 12:00+02:00")
        self.assertRaises(CompareError, compare_values, "2025-01-01 12:00-02:00", PrimaryComparators.DATE_BEFORE,
                          "2025-01-01 12:00")

    def test_11_date_within_last(self):
        # Test with datetime object
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(compare_values(now, PrimaryComparators.DATE_WITHIN_LAST, "1h"))
        self.assertTrue(compare_values(now - datetime.timedelta(days=120), PrimaryComparators.DATE_WITHIN_LAST, "3y"))
        self.assertFalse(
            compare_values(now - datetime.timedelta(days=370, hours=1), PrimaryComparators.DATE_WITHIN_LAST, "1y"))
        self.assertTrue(compare_values(now - datetime.timedelta(hours=48), PrimaryComparators.DATE_WITHIN_LAST, "7d"))
        self.assertFalse(
            compare_values(now - datetime.timedelta(days=7, hours=1), PrimaryComparators.DATE_WITHIN_LAST, "7d"))
        self.assertTrue(compare_values(now - datetime.timedelta(minutes=50), PrimaryComparators.DATE_WITHIN_LAST, "1h"))
        self.assertFalse(compare_values(now - datetime.timedelta(days=1), PrimaryComparators.DATE_WITHIN_LAST, "1h"))
        self.assertTrue(
            compare_values(now - datetime.timedelta(minutes=10), PrimaryComparators.DATE_WITHIN_LAST, "30m"))
        self.assertFalse(
            compare_values(now - datetime.timedelta(minutes=31), PrimaryComparators.DATE_WITHIN_LAST, "30m"))

        # Test with string
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(compare_values(now.isoformat(), PrimaryComparators.DATE_WITHIN_LAST, "1h"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(days=120)).isoformat(), PrimaryComparators.DATE_WITHIN_LAST, "3y"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(days=370, hours=1)).isoformat(),
                           PrimaryComparators.DATE_WITHIN_LAST,
                           "1y"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(hours=48)).isoformat(), PrimaryComparators.DATE_WITHIN_LAST, "7d"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(days=7, hours=1)).isoformat(), PrimaryComparators.DATE_WITHIN_LAST,
                           "7d"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(minutes=50)).isoformat(), PrimaryComparators.DATE_WITHIN_LAST,
                           "1h"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(days=1)).isoformat(), PrimaryComparators.DATE_WITHIN_LAST, "1h"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(minutes=10)).isoformat(), PrimaryComparators.DATE_WITHIN_LAST,
                           "30m"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(minutes=31)).isoformat(), PrimaryComparators.DATE_WITHIN_LAST,
                           "30m"))

        # Missing timezone info assumes UTC
        self.assertTrue(compare_values(now.replace(tzinfo=None).isoformat(), PrimaryComparators.DATE_WITHIN_LAST, "1h"))

        # Invalid formats
        self.assertRaises(CompareError, compare_values, "2025", PrimaryComparators.DATE_WITHIN_LAST, "1h")
        self.assertRaises(CompareError, compare_values, "1. July 2025", PrimaryComparators.DATE_WITHIN_LAST, "1h")
        self.assertRaises(CompareError, compare_values, now, PrimaryComparators.DATE_WITHIN_LAST, "1year")

    def test_12_date_not_within_last(self):
        # Test with datetime object
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertFalse(compare_values(now, PrimaryComparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertFalse(
            compare_values(now - datetime.timedelta(days=120), PrimaryComparators.DATE_NOT_WITHIN_LAST, "3y"))
        self.assertTrue(
            compare_values(now - datetime.timedelta(days=370, hours=1), PrimaryComparators.DATE_NOT_WITHIN_LAST, "1y"))
        self.assertFalse(
            compare_values(now - datetime.timedelta(hours=48), PrimaryComparators.DATE_NOT_WITHIN_LAST, "7d"))
        self.assertTrue(
            compare_values(now - datetime.timedelta(days=7, hours=1), PrimaryComparators.DATE_NOT_WITHIN_LAST, "7d"))
        self.assertFalse(
            compare_values(now - datetime.timedelta(minutes=50), PrimaryComparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertTrue(compare_values(now - datetime.timedelta(days=1), PrimaryComparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertFalse(
            compare_values(now - datetime.timedelta(minutes=10), PrimaryComparators.DATE_NOT_WITHIN_LAST, "30m"))
        self.assertTrue(
            compare_values(now - datetime.timedelta(minutes=31), PrimaryComparators.DATE_NOT_WITHIN_LAST, "30m"))

        # Test with string
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertFalse(compare_values(now.isoformat(), PrimaryComparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(days=120)).isoformat(), PrimaryComparators.DATE_NOT_WITHIN_LAST,
                           "3y"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(days=370, hours=1)).isoformat(),
                           PrimaryComparators.DATE_NOT_WITHIN_LAST,
                           "1y"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(hours=48)).isoformat(), PrimaryComparators.DATE_NOT_WITHIN_LAST,
                           "7d"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(days=7, hours=1)).isoformat(),
                           PrimaryComparators.DATE_NOT_WITHIN_LAST,
                           "7d"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(minutes=50)).isoformat(), PrimaryComparators.DATE_NOT_WITHIN_LAST,
                           "1h"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(days=1)).isoformat(), PrimaryComparators.DATE_NOT_WITHIN_LAST,
                           "1h"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(minutes=10)).isoformat(), PrimaryComparators.DATE_NOT_WITHIN_LAST,
                           "30m"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(minutes=31)).isoformat(), PrimaryComparators.DATE_NOT_WITHIN_LAST,
                           "30m"))

        # Missing timezone info assumes UTC
        self.assertFalse(
            compare_values(now.replace(tzinfo=None).isoformat(), PrimaryComparators.DATE_NOT_WITHIN_LAST, "1h"))

        # Invalid formats
        self.assertRaises(CompareError, compare_values, "1. July 2025", PrimaryComparators.DATE_NOT_WITHIN_LAST, "1h")
        self.assertRaises(CompareError, compare_values, now, PrimaryComparators.DATE_NOT_WITHIN_LAST, "1year")

    def test_13_string_contains(self):
        self.assertTrue(compare_values("hello world", PrimaryComparators.STRING_CONTAINS, "hello"))
        self.assertTrue(compare_values("hello world", PrimaryComparators.STRING_CONTAINS, "world"))
        self.assertTrue(compare_values("hello world", PrimaryComparators.STRING_CONTAINS, "Hello"))
        self.assertTrue(compare_values("hello world", PrimaryComparators.STRING_CONTAINS, "ello"))
        self.assertFalse(compare_values("hello world", PrimaryComparators.STRING_CONTAINS, "hello world!"))

        self.assertRaises(CompareError, compare_values, "hello world", PrimaryComparators.STRING_CONTAINS, 42)

    def test_14_string_not_contains(self):
        # negation
        self.assertTrue(compare_values("hello world", PrimaryComparators.STRING_NOT_CONTAINS, "foo"))
        self.assertFalse(compare_values("hello world", PrimaryComparators.STRING_NOT_CONTAINS, "world"))
        self.assertFalse(compare_values("hello world", PrimaryComparators.STRING_NOT_CONTAINS, "hello"))
        self.assertFalse(compare_values("hello world", PrimaryComparators.STRING_NOT_CONTAINS, "WoRlD"))

        self.assertRaises(CompareError, compare_values, "hello world", PrimaryComparators.STRING_NOT_CONTAINS, 42)

    def test_15_compare_ints(self):
        self.assertTrue(compare_ints("100", 100))
        self.assertTrue(compare_ints("=100", 100))
        self.assertTrue(compare_ints(" = 100 ", 100))
        self.assertTrue(compare_ints("==100", 100))
        self.assertFalse(compare_ints("== 100", 99))
        self.assertTrue(compare_ints("'=='100", 100))
        self.assertFalse(compare_ints("'==' 100", 99))
        self.assertTrue(compare_ints("'equals'100", 100))
        self.assertFalse(compare_ints("'equals' 100", 99))

        self.assertFalse(compare_ints("100 ", 99))

        self.assertTrue(compare_ints(">100", 101))
        self.assertTrue(compare_ints("'>'100", 101))
        self.assertFalse(compare_ints(">100", 100))
        self.assertFalse(compare_ints(">100", 1))
        self.assertFalse(compare_ints("'>'100", 1))

        self.assertTrue(compare_ints("<100", 10))
        self.assertTrue(compare_ints("'<'100", 10))
        self.assertTrue(compare_ints("  <100", 10))
        self.assertFalse(compare_ints("<100", 1000))
        self.assertFalse(compare_ints("<100", 100))
        self.assertFalse(compare_ints("'<'100", 100))

        # There are invalid conditions, which should not raise an exception
        # An empty condition will result in False
        self.assertFalse(compare_ints("", 100))
        # An invalid condition, which misses a compare-value, will result in false
        self.assertFalse(compare_ints(">", 100))
        # primary comparators can not be parsed without quotes
        self.assertFalse(compare_ints("equals 100", 100))

        # Test new comparators
        self.assertTrue(compare_ints('>=100', 100))
        self.assertTrue(compare_ints('=> 100', 200))
        self.assertFalse(compare_ints('>= 100', 99))

        self.assertTrue(compare_ints('<=100', 100))
        self.assertTrue(compare_ints('=< 100', 99))
        self.assertFalse(compare_ints('<= 100', 101))

        self.assertTrue(compare_ints('!=100', 99))
        self.assertTrue(compare_ints("'!equals'100", 99))
        self.assertFalse(compare_ints('!= 100', 100))
        self.assertFalse(compare_ints("'!equals' 100", 100))
        self.assertFalse(compare_ints('== 100', 99))

        # Unknown comparator causes invalid value which evaluates always to False
        self.assertFalse(compare_ints('!~100', 100))
        self.assertFalse(compare_ints('===100', 100))
        # comparator that does not support integers
        self.assertFalse(compare_ints("'string_contains' 100", 100))

    def test_16_compare_generic_condition(self):
        def mock_attribute(key):
            attr = {"a": "10",
                    "b": "100",
                    "c": "1000",
                    "e": 1000,
                    "now": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "now+10h": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                        hours=10)).isoformat(),
                    "past": "2017-04-20 11:30+0200",
                    "invalid_date": "16. März 2020",
                    "text": "ABC",
                    "list": ["123", "ABC", "XYZ"]}
            return attr.get(key)

        self.assertTrue(compare_generic("a<100", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("a <100", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("a '<' 100", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("a > 1", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("a '>' 1", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("b==100", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("b'=='100", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("b 'equals' 100", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("b!=200", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("b'!='200", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("b '!equals' 200", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("e == 1000", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text < ABD", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text '<' ABD", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text == ABC", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text 'equals' ABC", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text 'string_contains' B", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text '!string_contains' D", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text 'in' 123,ABC,XYZ", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text '!in' 123,ABCD,XYZ", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text 'matches' [A-Z]{3}", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("text '!matches' [1-9]{3}", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("list 'contains' ABC", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("list '!contains' AB", mock_attribute, "Error {0!s}"))

        self.assertFalse(compare_generic("a== 100", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("a '==' 100", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("a'equals'100", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("b>100", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("c < 500", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("c <500", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("c '<' 500", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text > ABD", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text '>' ABD", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text == ABCD", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text 'string_contains' D", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text '!string_contains' A", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text 'in' 123,ABCD,XYZ", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text '!in' 123,ABC,XYZ", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text '!matches' [A-Z]{3}", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("text 'matches' [1-9]{3}", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("list '!contains' ABC", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("list 'contains' AB", mock_attribute, "Error {0!s}"))

        # Wrong condition: key does not exist
        self.assertFalse(compare_generic("d==1", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("d<1", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("d>1", mock_attribute, "Error {0!s}"))

        # Different datatypes
        self.assertFalse(compare_generic("e==ABC", mock_attribute, "Error {0!s}"))

        # Wrong entry, that is not processed
        self.assertFalse(compare_generic("c 500", mock_attribute, "Error {0!s}"))
        # Wrong entry, that cannot be processed
        self.assertFalse(compare_generic("b!~100", mock_attribute, "Error {0!s}"))
        # Empty entry
        self.assertFalse(compare_generic("", mock_attribute, "Error {0!s}"))

        # compare dates
        self.assertTrue(compare_generic("now > 2017-01-01T10:00+0200", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("now 'date_after' 2017-01-01 10:00+02:00", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("now 'date_within_last' 2h", mock_attribute, "Error {0!s}"))
        self.assertTrue(compare_generic("past '!date_within_last' 2h", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("now<2017-01-01 10:00+02:00", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic("now 'date_before' 2017-01-01T10:00+02:00", mock_attribute, "Error {0!s}"))
        # The timestamp in 10 hours is bigger than the current time
        self.assertTrue(
            compare_generic(f"now+10h>{datetime.datetime.now(datetime.timezone.utc).isoformat()}", mock_attribute,
                            "Error {0!s}"))

        self.assertFalse(compare_generic(f"past > {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
                                         mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic(f"past 'date_within_last' 1s", mock_attribute, "Error {0!s}"))
        self.assertFalse(compare_generic(f"now '!date_within_last' 1h", mock_attribute, "Error {0!s}"))

        past_date = datetime.datetime(2017, 4, 20, 9, 30, tzinfo=datetime.timezone.utc).isoformat()
        self.assertTrue(compare_generic(f"past=={past_date}", mock_attribute, "Error {0!s}"))

        # unexpected result: The date string can not be parsed since dateutil.parser does not understand locale dates.
        # So the strings themselves are compared since parse_date() returns 'None'
        self.assertTrue(compare_generic(
            f"invalid_date < {datetime.datetime(2020, 3, 15).isoformat()}",
            mock_attribute, "Error {0!s}"))

    def test_17_compare_time(self):
        # Test with datetime object
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(compare_time("1h", now))
        self.assertTrue(compare_time("3y", now - datetime.timedelta(days=120)))
        self.assertFalse(compare_time("1y", now - datetime.timedelta(days=370, hours=1)))
        self.assertTrue(compare_time("7d", now - datetime.timedelta(hours=48)))
        self.assertFalse(compare_time("7d", now - datetime.timedelta(days=7, hours=1)))
        self.assertTrue(compare_time("1h", now - datetime.timedelta(minutes=50)))
        self.assertFalse(compare_time("1h", now - datetime.timedelta(days=1)))
        self.assertTrue(compare_time("30m", now - datetime.timedelta(minutes=10)))
        self.assertFalse(compare_time("30m", now - datetime.timedelta(minutes=31)))

        # Test with string
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(compare_time("1h", now.isoformat()))
        self.assertTrue(compare_time("3y", (now - datetime.timedelta(days=120)).isoformat()))
        self.assertFalse(compare_time("1y", (now - datetime.timedelta(days=370, hours=1)).isoformat()))
        self.assertTrue(compare_time("7d", (now - datetime.timedelta(hours=48)).isoformat()))
        self.assertFalse(compare_time("7d", (now - datetime.timedelta(days=7, hours=1)).isoformat()))
        self.assertTrue(compare_time("1h", (now - datetime.timedelta(minutes=50)).isoformat()))
        self.assertFalse(compare_time("1h", (now - datetime.timedelta(days=1)).isoformat()))
        self.assertTrue(compare_time("30m", (now - datetime.timedelta(minutes=10)).isoformat()))
        self.assertFalse(compare_time("30m", (now - datetime.timedelta(minutes=31)).isoformat()))

        # Missing timezone info assumes UTC
        self.assertTrue(compare_time("1h", now.replace(tzinfo=None).isoformat()))

        # Invalid formats
        self.assertFalse(compare_time("1h", "1. July 2025"))
        self.assertFalse(compare_time("1year", now))

    def test_18_compare_values_invalid_comparator(self):
        self.assertRaises(CompareError, compare_values, "hello", "invalid_comparator", "world")
