"""
This tests the files
  lib/counter.py
"""
import mock
from contextlib import contextmanager

from .base import MyTestCase
from privacyidea.lib.counter import increase, decrease, reset, read
from privacyidea.models import EventCounter


def increase_and_read(name):
    """ helper function that increases the event counter and returns the new value """
    increase(name)
    return read(name)


def decrease_and_read(name, allow_negative=False):
    """ helper function that decreases the event counter and returns the new value """
    decrease(name, allow_negative=allow_negative)
    return read(name)

class CounterTestCase(MyTestCase):
    """
    Test the counter module
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_00_create_and_increase(self):
        r = increase_and_read("hallo_counter")
        self.assertEqual(r, 1)

        r = increase_and_read("counter2")
        self.assertEqual(r, 1)

        r = increase_and_read("hallo_counter")
        self.assertEqual(r, 2)

        counter = EventCounter.query.filter_by(counter_name="hallo_counter").first()
        self.assertEqual(counter.counter_value, 2)

    def test_01_increase_and_decrease(self):
        r = increase_and_read("hallo_counter1")
        self.assertEqual(r, 1)

        for x in range(1, 5):
            increase("hallo_counter1")

        counter = EventCounter.query.filter_by(counter_name="hallo_counter1").first()
        self.assertEqual(counter.counter_value, 5)

        r = decrease_and_read("hallo_counter1")
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
        r = increase_and_read("hallo_counter2")
        self.assertEqual(r, 1)

        for x in range(1, 8):
            decrease("hallo_counter2", allow_negative=True)

        counter = EventCounter.query.filter_by(counter_name="hallo_counter2").first()
        self.assertEqual(counter.counter_value, -6)

    def test_03_decrease_and_reset(self):
        r = decrease_and_read("hallo_counter3", allow_negative=True)
        self.assertEqual(r, -1)

        reset("hallo_counter3")

        counter = EventCounter.query.filter_by(counter_name="hallo_counter3").first()
        self.assertEqual(counter.counter_value, 0)

    def test_04_reset_non_existing_counter(self):
        reset("hallo_counter4")

        counter = EventCounter.query.filter_by(counter_name="hallo_counter4").first()
        self.assertEqual(counter.counter_value, 0)

    def test_05_multiple_nodes(self):
        @contextmanager
        def _set_node(node):
            """ context manager that sets the current node name """
            with mock.patch("privacyidea.lib.counter.get_privacyidea_node") as mock_node:
                mock_node.return_value = node
                yield

        # two nodes node1 and node2, two counters ctrA and ctrB
        with _set_node("node1"):
            for _ in range(3):
                increase("ctrA")
            increase("ctrB")
        with _set_node("node2"):
            r = increase_and_read("ctrB")
            self.assertEqual(r, 2)

        # sums are correct ...
        self.assertEqual(read("ctrA"), 3)
        self.assertEqual(read("ctrB"), 2)
        # ... and each node has written to its own row
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrA", node="node1").one().counter_value, 3)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrA", node="node2").all(), [])
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node1").one().counter_value, 1)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node2").one().counter_value, 1)

        # decreasing ctrB on node2 by 2 creates a row with negative value, even if allow_negative=False
        with _set_node("node2"):
            for _ in range(2):
                decrease("ctrB", allow_negative=False)

        self.assertEqual(read("ctrB"), 0)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node1").one().counter_value, 1)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node2").one().counter_value, -1)

        # decreasing below the sum of 0 causes all values to be reset
        with _set_node("node2"):
            decrease("ctrB", allow_negative=False)

        self.assertEqual(read("ctrB"), 0)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node1").one().counter_value, 0)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node2").one().counter_value, 0)

        # decreasing with allow_negative=True works
        with _set_node("node1"):
            decrease("ctrB", allow_negative=True)
        with _set_node("node2"):
            decrease("ctrB", allow_negative=True)

        self.assertEqual(read("ctrB"), -2)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node1").one().counter_value, -1)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node2").one().counter_value, -1)

        # resetting resets all rows
        reset("ctrB")
        self.assertEqual(read("ctrB"), 0)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node1").one().counter_value, 0)
        self.assertEqual(EventCounter.query.filter_by(counter_name="ctrB", node="node2").one().counter_value, 0)