"""
This tests the files
  lib/task/eventcounter.py
"""

from .base import MyTestCase
from privacyidea.lib.counter import increase, read
from privacyidea.lib.monitoringstats import get_values

from privacyidea.lib.task.eventcounter import EventCounterTask
from flask import current_app


class TaskEventCounterTestCase(MyTestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_00_read_eventcounter_to_monitoringstats(self):
        r = increase("counter1")
        self.assertEqual(r, 1)

        r = increase("counter2")
        self.assertEqual(r, 1)

        r = increase("counter1")
        self.assertEqual(r, 2)

        r = read("counter1")
        self.assertEqual(r, 2)

        et = EventCounterTask(current_app.config)
        params = {"event_counter": "counter1",
                  "stats_key": "C1",
                  "reset_event_counter": "True"}

        # Now we execute the task
        et.do(params)

        # The counter "counter1" should be reset
        self.assertEqual(read("counter1"), 0)

        # The value "2" should be written to the statistics key C1.
        stats = get_values("C1")
        self.assertTrue(len(stats), 1)
        self.assertTrue(stats[0][1], 2)

        # Now we increase the event counter again
        increase("counter1")

        # ..and run the event counter task
        et.do(params)
        stats = get_values("C1")
        self.assertTrue(len(stats), 2)
        self.assertTrue(stats[0][1], 2)
        self.assertTrue(stats[0][1], 1)
