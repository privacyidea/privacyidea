# -*- coding: utf-8 -*-
"""
This tests the module lib.utils.compare
"""
from privacyidea.lib.utils.compare import compare_values, CompareError
from .base import MyTestCase


class UtilsCompareTestCase(MyTestCase):
    def test_01_compare_equal(self):
        self.assertTrue(compare_values("hello", "==", "hello"))
        self.assertTrue(compare_values(1, "==", 1))
        self.assertFalse(compare_values("hello", "==", " hello"))
        self.assertFalse(compare_values(1, "==", 2))
        self.assertFalse(compare_values(1, "==", "1"))

    def test_02_compare_contains(self):
        self.assertTrue(compare_values(["hello", "world"], "contains", "hello"))
        self.assertTrue(compare_values(["hello", "world"], "contains", "world"))
        self.assertTrue(compare_values([1, "world"], "contains", 1))
        self.assertFalse(compare_values([1, "world"], "contains", [1, "world"]))

        # must pass a list
        with self.assertRaises(CompareError):
            compare_values("hello world", "contains", "hello")

    def test_03_compare_errors(self):
        with self.assertRaises(CompareError):
            compare_values("hello world", "something", "hello")
