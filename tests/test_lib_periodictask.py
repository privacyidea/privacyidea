"""
This file contains the tests for periodic tasks.

In particular, this tests
lib/periodictask.py
"""
from dateutil.parser import parse as parse_timestamp

from privacyidea.lib.error import ServerError
from privacyidea.lib.periodictask import calculate_next_timestamp
from .base import MyTestCase


class BasePeriodicTaskTestCase(MyTestCase):
    def test_01_calculate_next_timestamp(self):
        # every day at 08:00
        task1 = {
            "id": 1,
            "active": True,
            "name": "task one",
            "interval": "0 8 * * *",
            "nodes": ["foo", "bar"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {
                "foo": parse_timestamp("2018-06-25 08:04:30"),
                "bar": parse_timestamp("2018-06-24 07:05:37"),
            }
        }

        self.assertEqual(calculate_next_timestamp(task1, "foo"),
                         parse_timestamp("2018-06-26 08:00 UTC"))
        self.assertEqual(calculate_next_timestamp(task1, "bar"),
                         parse_timestamp("2018-06-24 08:00 UTC"))
        with self.assertRaises(ServerError):
            calculate_next_timestamp(task1, "baz")

        # every weekday
        task2 = {
            "id": 2,
            "active": True,
            "name": "task two",
            "interval": "0 0 * * 1-5",
            "nodes": ["foo", "bar"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {
                "localhost": parse_timestamp("2018-06-29 00:00"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task2, "localhost"),
                         parse_timestamp("2018-07-02 00:00 UTC"))

        # at 00:05 in August
        task3 = {
            "id": 3,
            "active": True,
            "name": "task two",
            "interval": "5 0 * 8 *",
            "nodes": ["foo", "bar"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {
                "localhost": parse_timestamp("2017-08-31 00:06"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task3, "localhost"),
                         parse_timestamp("2018-08-01 00:05 UTC"))

        # malformed
        task4 = {
            "id": 3,
            "active": True,
            "name": "task two",
            "interval": "every two days",
            "nodes": ["foo", "bar"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {
                "localhost": parse_timestamp("2017-08-31 00:06"),
            }
        }
        with self.assertRaises(ValueError):
            calculate_next_timestamp(task4, "localhost")