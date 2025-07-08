"""
This tests the module lib.utils.compare
"""
import datetime

from privacyidea.lib.utils.compare import compare_values, CompareError, parse_comma_separated_string, Comparators
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

    def test_08_date_after(self):
        # Test with datetime objects
        condition_date = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        true_date = datetime.datetime(2025, 2, 1, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertTrue(compare_values(true_date, Comparators.DATE_AFTER, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 12, 0, 1, tzinfo=datetime.timezone.utc)
        self.assertTrue(compare_values(true_date, Comparators.DATE_AFTER, condition_date))
        true_date = datetime.datetime(2024, 1, 2, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertFalse(compare_values(true_date, Comparators.DATE_AFTER, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 11, 59, 59, tzinfo=datetime.timezone.utc)
        self.assertFalse(compare_values(true_date, Comparators.DATE_AFTER, condition_date))
        # test with different time zones
        true_date = datetime.datetime(2025, 1, 1, 13, 0, 0,
                                      tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        self.assertFalse(compare_values(true_date, Comparators.DATE_AFTER, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 11, 0, 0,
                                      tzinfo=datetime.timezone(-datetime.timedelta(hours=2)))
        self.assertTrue(compare_values(true_date, Comparators.DATE_AFTER, condition_date))

        # Test with date strings
        condition_date_str = "2025-01-01 12:00"
        true_date_str = "2025-02-01 12:00:00"
        self.assertTrue(compare_values(true_date_str, Comparators.DATE_AFTER, condition_date_str))
        true_date_str = "2025-01-01 12:00:01"
        self.assertTrue(compare_values(true_date_str, Comparators.DATE_AFTER, condition_date_str))
        true_date_str = "2024-02-01 12:00:00"
        self.assertFalse(compare_values(true_date_str, Comparators.DATE_AFTER, condition_date_str))
        true_date_str = "2025-01-01 11:59:32"
        self.assertFalse(compare_values(true_date_str, Comparators.DATE_AFTER, condition_date_str))
        # test with different time zones
        condition_date_str = "2025-01-01 12:00:00+00:00"
        true_date_str = "2025-01-01 13:00:00+02:00"
        self.assertFalse(compare_values(true_date_str, Comparators.DATE_AFTER, condition_date_str))
        true_date_str = "2025-01-01 11:00:00-02:00"
        self.assertTrue(compare_values(true_date_str, Comparators.DATE_AFTER, condition_date_str))

        # Invalid date formats
        self.assertRaises(CompareError, compare_values, "12:00", Comparators.DATE_AFTER, condition_date_str)
        self.assertRaises(CompareError, compare_values, true_date_str, Comparators.DATE_AFTER, "2025/01/01 12:00")
        self.assertRaises(CompareError, compare_values, true_date_str, Comparators.DATE_AFTER, 2025)
        self.assertRaises(CompareError, compare_values, 102, Comparators.DATE_AFTER, condition_date_str)
        self.assertRaises(CompareError, compare_values, "2025-01-01 12:00", Comparators.DATE_AFTER,
                          "2025-01-01 12:00+02:00")
        self.assertRaises(CompareError, compare_values, "2025-01-01 12:00-02:00", Comparators.DATE_AFTER,
                          "2025-01-01 12:00")

    def test_09_date_before(self):
        # Test with datetime objects
        condition_date = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        true_date = datetime.datetime(2025, 2, 1, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertFalse(compare_values(true_date, Comparators.DATE_BEFORE, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 12, 0, 1, tzinfo=datetime.timezone.utc)
        self.assertFalse(compare_values(true_date, Comparators.DATE_BEFORE, condition_date))
        true_date = datetime.datetime(2024, 1, 2, 12, 0, tzinfo=datetime.timezone.utc)
        self.assertTrue(compare_values(true_date, Comparators.DATE_BEFORE, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 11, 59, 59, tzinfo=datetime.timezone.utc)
        self.assertTrue(compare_values(true_date, Comparators.DATE_BEFORE, condition_date))
        # test with different time zones
        true_date = datetime.datetime(2025, 1, 1, 13, 0, 0,
                                      tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        self.assertTrue(compare_values(true_date, Comparators.DATE_BEFORE, condition_date))
        true_date = datetime.datetime(2025, 1, 1, 11, 0, 0,
                                      tzinfo=datetime.timezone(-datetime.timedelta(hours=2)))
        self.assertFalse(compare_values(true_date, Comparators.DATE_BEFORE, condition_date))

        # Test with date strings
        condition_date_str = "2025-01-01T12:00"
        true_date_str = "2025-02-01 12:00:00"
        self.assertFalse(compare_values(true_date_str, Comparators.DATE_BEFORE, condition_date_str))
        true_date_str = "2025-01-01 12:00:01"
        self.assertFalse(compare_values(true_date_str, Comparators.DATE_BEFORE, condition_date_str))
        true_date_str = "2024-02-01 12:00:00"
        self.assertTrue(compare_values(true_date_str, Comparators.DATE_BEFORE, condition_date_str))
        true_date_str = "2025-01-01 11:59:32"
        self.assertTrue(compare_values(true_date_str, Comparators.DATE_BEFORE, condition_date_str))
        # test with different time zones
        condition_date_str = "2025-01-01 12:00:00+00:00"
        true_date_str = "2025-01-01 13:00:00+0200"
        self.assertTrue(compare_values(true_date_str, Comparators.DATE_BEFORE, condition_date_str))
        true_date_str = "2025-01-01 11:00:00-02:00"
        self.assertFalse(compare_values(true_date_str, Comparators.DATE_BEFORE, condition_date_str))

        # Invalid date formats
        self.assertRaises(CompareError, compare_values, "12:00", Comparators.DATE_BEFORE, condition_date_str)
        self.assertRaises(CompareError, compare_values, true_date_str, Comparators.DATE_BEFORE, "2025/01/01 12:00")
        self.assertRaises(CompareError, compare_values, true_date_str, Comparators.DATE_BEFORE, 2025)
        self.assertRaises(CompareError, compare_values, 102, Comparators.DATE_BEFORE, condition_date_str)
        self.assertRaises(CompareError, compare_values, "2025-01-01 12:00", Comparators.DATE_BEFORE,
                          "2025-01-01 12:00+02:00")
        self.assertRaises(CompareError, compare_values, "2025-01-01 12:00-02:00", Comparators.DATE_BEFORE,
                          "2025-01-01 12:00")

    def test_10_date_within_last(self):
        # Test with datetime object
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(compare_values(now, Comparators.DATE_WITHIN_LAST, "1h"))
        self.assertTrue(compare_values(now - datetime.timedelta(days=120), Comparators.DATE_WITHIN_LAST, "3y"))
        self.assertFalse(
            compare_values(now - datetime.timedelta(days=370, hours=1), Comparators.DATE_WITHIN_LAST, "1y"))
        self.assertTrue(compare_values(now - datetime.timedelta(hours=48), Comparators.DATE_WITHIN_LAST, "7d"))
        self.assertFalse(compare_values(now - datetime.timedelta(days=7, hours=1), Comparators.DATE_WITHIN_LAST, "7d"))
        self.assertTrue(compare_values(now - datetime.timedelta(minutes=50), Comparators.DATE_WITHIN_LAST, "1h"))
        self.assertFalse(compare_values(now - datetime.timedelta(days=1), Comparators.DATE_WITHIN_LAST, "1h"))
        self.assertTrue(compare_values(now - datetime.timedelta(minutes=10), Comparators.DATE_WITHIN_LAST, "30m"))
        self.assertFalse(compare_values(now - datetime.timedelta(minutes=31), Comparators.DATE_WITHIN_LAST, "30m"))

        # Test with string
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(compare_values(now.isoformat(), Comparators.DATE_WITHIN_LAST, "1h"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(days=120)).isoformat(), Comparators.DATE_WITHIN_LAST, "3y"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(days=370, hours=1)).isoformat(), Comparators.DATE_WITHIN_LAST,
                           "1y"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(hours=48)).isoformat(), Comparators.DATE_WITHIN_LAST, "7d"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(days=7, hours=1)).isoformat(), Comparators.DATE_WITHIN_LAST, "7d"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(minutes=50)).isoformat(), Comparators.DATE_WITHIN_LAST, "1h"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(days=1)).isoformat(), Comparators.DATE_WITHIN_LAST, "1h"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(minutes=10)).isoformat(), Comparators.DATE_WITHIN_LAST, "30m"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(minutes=31)).isoformat(), Comparators.DATE_WITHIN_LAST, "30m"))

        # Missing timezone info assumes UTC
        self.assertTrue(compare_values(now.replace(tzinfo=None).isoformat(), Comparators.DATE_WITHIN_LAST, "1h"))

        # Invalid formats
        self.assertRaises(CompareError, compare_values, "12:00", Comparators.DATE_WITHIN_LAST, "1h")
        self.assertRaises(CompareError, compare_values, now, Comparators.DATE_WITHIN_LAST, "1year")

    def test_11_date_not_within_last(self):
        # Test with datetime object
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertFalse(compare_values(now, Comparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertFalse(compare_values(now - datetime.timedelta(days=120), Comparators.DATE_NOT_WITHIN_LAST, "3y"))
        self.assertTrue(
            compare_values(now - datetime.timedelta(days=370, hours=1), Comparators.DATE_NOT_WITHIN_LAST, "1y"))
        self.assertFalse(compare_values(now - datetime.timedelta(hours=48), Comparators.DATE_NOT_WITHIN_LAST, "7d"))
        self.assertTrue(compare_values(now - datetime.timedelta(days=7, hours=1), Comparators.DATE_NOT_WITHIN_LAST, "7d"))
        self.assertFalse(compare_values(now - datetime.timedelta(minutes=50), Comparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertTrue(compare_values(now - datetime.timedelta(days=1), Comparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertFalse(compare_values(now - datetime.timedelta(minutes=10), Comparators.DATE_NOT_WITHIN_LAST, "30m"))
        self.assertTrue(compare_values(now - datetime.timedelta(minutes=31), Comparators.DATE_NOT_WITHIN_LAST, "30m"))

        # Test with string
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertFalse(compare_values(now.isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(days=120)).isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "3y"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(days=370, hours=1)).isoformat(), Comparators.DATE_NOT_WITHIN_LAST,
                           "1y"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(hours=48)).isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "7d"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(days=7, hours=1)).isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "7d"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(minutes=50)).isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(days=1)).isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "1h"))
        self.assertFalse(
            compare_values((now - datetime.timedelta(minutes=10)).isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "30m"))
        self.assertTrue(
            compare_values((now - datetime.timedelta(minutes=31)).isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "30m"))

        # Missing timezone info assumes UTC
        self.assertFalse(compare_values(now.replace(tzinfo=None).isoformat(), Comparators.DATE_NOT_WITHIN_LAST, "1h"))

        # Invalid formats
        self.assertRaises(CompareError, compare_values, "12:00", Comparators.DATE_NOT_WITHIN_LAST, "1h")
        self.assertRaises(CompareError, compare_values, now, Comparators.DATE_NOT_WITHIN_LAST, "1year")

    def test_12_string_contains(self):
        self.assertTrue(compare_values("hello world", Comparators.STRING_CONTAINS, "hello"))
        self.assertTrue(compare_values("hello world", Comparators.STRING_CONTAINS, "world"))
        self.assertTrue(compare_values("hello world", Comparators.STRING_CONTAINS, "Hello"))
        self.assertTrue(compare_values("hello world", Comparators.STRING_CONTAINS, "ello"))
        self.assertFalse(compare_values("hello world", Comparators.STRING_CONTAINS, "hello world!"))

    def test_13_string_not_contains(self):
        # negation
        self.assertTrue(compare_values("hello world", Comparators.STRING_NOT_CONTAINS, "foo"))
        self.assertFalse(compare_values("hello world", Comparators.STRING_NOT_CONTAINS, "world"))
        self.assertFalse(compare_values("hello world", Comparators.STRING_NOT_CONTAINS, "hello"))
        self.assertFalse(compare_values("hello world", Comparators.STRING_NOT_CONTAINS, "WoRlD"))