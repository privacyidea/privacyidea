# -*- coding: utf-8 -*-
"""
This tests the module lib.utils.compare
"""
from privacyidea.lib.utils.compare import compare_values, CompareError, parse_comma_separated_string
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
