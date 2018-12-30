"""
This tests the files
  lib/counter.py
"""

from .base import MyTestCase
from privacyidea.lib.counter import increase, decrease, reset, read
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

    def test_01_increase_and_decrease(self):
        r = increase("hallo_counter1")
        self.assertEqual(r, 1)

        for x in range(1, 5):
            increase("hallo_counter1")

        counter = EventCounter.query.filter_by(counter_name="hallo_counter1").first()
        self.assertEqual(counter.counter_value, 5)

        r = decrease("hallo_counter1")
        self.assertEqual(r, 4)

        for x in range(1, 8):
            decrease("hallo_counter1")

        counter = EventCounter.query.filter_by(counter_name="hallo_counter1").first()
        self.assertEqual(counter.counter_value, 0)

        # Test reading counter
        r = read("hallo_counter1")
        self.assertEqual(r, 0)
        r = read("unknown counter")
        self.assertEqual(r, None)

    def test_02_decrease_beyond_zero(self):
        r = increase("hallo_counter2")
        self.assertEqual(r, 1)

        for x in range(1, 8):
            decrease("hallo_counter2", allow_negative=True)

        counter = EventCounter.query.filter_by(counter_name="hallo_counter2").first()
        self.assertEqual(counter.counter_value, -6)

    def test_03_decrease_and_reset(self):
        r = decrease("hallo_counter3", allow_negative=True)
        self.assertEqual(r, -1)

        reset("hallo_counter3")

        counter = EventCounter.query.filter_by(counter_name="hallo_counter3").first()
        self.assertEqual(counter.counter_value, 0)

    def test_04_reset_non_existing_counter(self):
        reset("hallo_counter4")

        counter = EventCounter.query.filter_by(counter_name="hallo_counter4").first()
        self.assertEqual(counter.counter_value, 0)
