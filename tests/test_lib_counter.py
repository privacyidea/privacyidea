"""
This tests the files
  lib/counter.py
"""

from .base import MyTestCase
from privacyidea.lib.counter import increase
from privacyidea.models import EventCounter


class CounterTestCase(MyTestCase):
    """
    Test the counter module
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_00_create_and_increase(self):
        r = increase("hallo_counter")
        self.assertEqual(r, 1)

        r = increase("counter2")
        self.assertEqual(r, 1)

        r = increase("hallo_counter")
        self.assertEqual(r, 2)

        counter = EventCounter.query.filter_by(counter_name="hallo_counter").first()
        self.assertEqual(counter.counter_value, 2)