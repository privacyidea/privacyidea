"""
This file contains the tests for periodic tasks.

In particular, this tests
lib/periodictask.py
"""
from datetime import datetime, timedelta

from dateutil.parser import parse as parse_timestamp
from dateutil.tz import gettz, tzutc
from mock import mock

from privacyidea.lib.error import ServerError, ParameterError, ResourceNotFoundError
from privacyidea.lib.periodictask import calculate_next_timestamp, set_periodic_task, get_periodic_tasks, \
    enable_periodic_task, delete_periodic_task, set_periodic_task_last_run, get_scheduled_periodic_tasks, \
    get_periodic_task_by_name, TASK_MODULES, execute_task, get_periodic_task_by_id
from privacyidea.lib.task.base import BaseTask
from privacyidea.models import PeriodicTask
from .base import MyTestCase


class BasePeriodicTaskTestCase(MyTestCase):
    def test_01_calculate_next_timestamp_utc(self):
        # The easy case: calculate everything in UTC
        tzinfo = tzutc()

        # every day at 08:00
        task1 = {
            "id": 1,
            "active": True,
            "name": "task one",
            "interval": "0 8 * * *",
            "last_update": parse_timestamp("2018-06-23 07:55:00 UTC"),
            "nodes": ["foo", "bar", "baz"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {
                "foo": parse_timestamp("2018-06-25 08:04:30 UTC"),
                "bar": parse_timestamp("2018-06-24 07:05:37 UTC"),
            }
        }

        self.assertEqual(calculate_next_timestamp(task1, "foo", tzinfo),
                         parse_timestamp("2018-06-26 08:00 UTC"))
        self.assertEqual(calculate_next_timestamp(task1, "bar", tzinfo),
                         parse_timestamp("2018-06-24 08:00 UTC"))
        # the next run of baz is calculated based on last_update
        self.assertEqual(calculate_next_timestamp(task1, "baz", tzinfo),
                         parse_timestamp("2018-06-23 08:00 UTC"))

        # no last run recorded
        task1b = {
            "id": 1,
            "active": True,
            "name": "task one",
            "interval": "0 8 * * *",
            "last_update": parse_timestamp("2018-06-24 07:55:00 UTC"),
            "nodes": ["foo", "bar"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {}
        }

        self.assertEqual(calculate_next_timestamp(task1b, "foo", tzinfo),
                         parse_timestamp("2018-06-24 08:00 UTC"))
        self.assertEqual(calculate_next_timestamp(task1b, "bar", tzinfo),
                         parse_timestamp("2018-06-24 08:00 UTC"))

        # now, "foo" has a last run!
        task1b["last_runs"]["foo"] = parse_timestamp("2018-06-24 08:00 UTC")
        self.assertEqual(calculate_next_timestamp(task1b, "foo", tzinfo),
                         parse_timestamp("2018-06-25 08:00 UTC"))
        # ... bar has still not run
        self.assertEqual(calculate_next_timestamp(task1b, "bar", tzinfo),
                         parse_timestamp("2018-06-24 08:00 UTC"))

        # every weekday
        task2 = {
            "id": 2,
            "active": True,
            "name": "task two",
            "interval": "0 0 * * 1-5",
            "last_update": parse_timestamp("2018-06-24 08:00:00 UTC"),
            "nodes": ["foo", "bar"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {
                "localhost": parse_timestamp("2018-06-29 00:00 UTC"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task2, "localhost", tzinfo),
                         parse_timestamp("2018-07-02 00:00 UTC"))

        # at 00:05 in August
        task3 = {
            "id": 3,
            "active": True,
            "name": "task two",
            "interval": "5 0 * 8 *",
            "last_update": parse_timestamp("2018-06-24 08:00:00 UTC"),
            "nodes": ["foo", "bar"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {
                "localhost": parse_timestamp("2017-08-31 00:06 UTC"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task3, "localhost", tzinfo),
                         parse_timestamp("2018-08-01 00:05 UTC"))

        # malformed
        task4 = {
            "id": 3,
            "active": True,
            "name": "task two",
            "interval": "every two days",
            "last_update": parse_timestamp("2018-06-24 08:00:00 UTC"),
            "nodes": ["foo", "bar"],
            "taskmodule": "some.module",
            "options": {"KEY2": "value number 2",
                        "key 4": "1234"},
            "last_runs": {
                "localhost": parse_timestamp("2017-08-31 00:06 UTC"),
            }
        }
        with self.assertRaises(ValueError):
            calculate_next_timestamp(task4, "localhost")

    def test_02_calculate_next_timestamp_localtime(self):
        # The harder case: Calculate everything in a local timezone
        # There is no DST in russia, so we operate in +03:00
        tzinfo = gettz("Europe/Moscow")

        # every day at 08:00
        task = {
            "interval": "0 8 * * *",
            "last_update": parse_timestamp("2018-06-24 02:30 UTC"),
            "last_runs": {
                "foo": parse_timestamp("2018-06-25 05:04:30 UTC"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task, "foo", tzinfo),
                         parse_timestamp("2018-06-26 05:00 UTC"))
        self.assertEqual(calculate_next_timestamp(task, "bar", tzinfo),
                         parse_timestamp("2018-06-24 05:00 UTC"))
        self.assertEqual(calculate_next_timestamp(task, "this_node_does_not_exist", tzinfo),
                         parse_timestamp("2018-06-24 05:00 UTC"))

        # every day at 08:00
        task = {
            "interval": "0 8 * * *",
            "last_update": parse_timestamp("2018-06-24 02:30 UTC"),
            "last_runs": {
                "foo": parse_timestamp("2018-06-25 04:04:30 UTC"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task, "foo", tzinfo),
                         parse_timestamp("2018-06-25 05:00 UTC"))

        # every day at midnight
        task = {
            "interval": "0 0 * * *",
            "last_update": parse_timestamp("2018-06-24 02:30 UTC"),
            "last_runs": {
                "foo": parse_timestamp("2018-06-25 21:01 UTC"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task, "foo", tzinfo),
                         parse_timestamp("2018-06-26 21:00 UTC"))

        # every wednesday at midnight
        task = {
            "interval": "0 0 * * 3",
            "last_update": parse_timestamp("2018-06-24 02:30 UTC"),
            "last_runs": {
                "foo": parse_timestamp("2018-06-24 21:00 UTC"),  # this is actually monday 00:00 in russia
            }
        }
        self.assertEqual(calculate_next_timestamp(task, "foo", tzinfo),
                         parse_timestamp("2018-06-26 21:00 UTC"))

        # every 15th at 01:00
        task = {
            "interval": "0 1 15 * *",
            "last_update": parse_timestamp("2018-06-24 02:30 UTC"),
            "last_runs": {
                "foo": parse_timestamp("2018-05-15 00:00 UTC"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task, "foo", tzinfo),
                         parse_timestamp("2018-06-14 22:00 UTC"))

        # every 15th at 01:00
        task = {
            "interval": "0 1 15 * *",
            "last_update": parse_timestamp("2018-06-24 02:30 UTC"),
            "last_runs": {
                "foo": parse_timestamp("2018-05-14 21:59 UTC"),
            }
        }
        self.assertEqual(calculate_next_timestamp(task, "foo", tzinfo),
                         parse_timestamp("2018-05-14 22:00 UTC"))

    def test_03_crud(self):
        task1 = set_periodic_task("task one", "0 0 1 * *", ["pinode1"], "some.task.module", 3, {
            "key1": 1,
            "key2": False
        }, retry_if_failed=False)
        task2 = set_periodic_task("task two", "0 0 * * WED", ["pinode2"], "some.task.module", 1, {
            "key1": "value",
            "key2": "foo"
        }, active=False, retry_if_failed=True)
        task3 = set_periodic_task("task three", "30 * * * *", ["pinode1", "pinode2"], "some.task.module", 2, {
            "key1": 1234,
            "key2": 5678,
        })

        with self.assertRaises(ParameterError):
            set_periodic_task("task four", "61 * * * *", ["pinode1", "pinode2"], "some.task.module", 1, {
                "key1": 1234,
                "key2": 5678,
            })
        with self.assertRaises(ParameterError):
            set_periodic_task("task four", "1 * * * *", ["pinode1", "pinode2"], "some.task.module", -3, {
                "key1": 1234,
                "key2": 5678,
            })

        task1_last_update = get_periodic_task_by_id(task1)["last_update"]

        self.assertEqual(get_periodic_task_by_name("task three")["id"], task3)
        with self.assertRaises(ResourceNotFoundError):
            get_periodic_task_by_name("task does not exist")

        self.assertEqual(get_periodic_task_by_id(task3)["name"], "task three")
        with self.assertRaises(ResourceNotFoundError):
            get_periodic_task_by_id(1337)

        self.assertEqual(len(PeriodicTask.query.all()), 3)

        # Updating an nonexistent task fails
        with self.assertRaises(ResourceNotFoundError):
            set_periodic_task("some task", "0 0 1 * *", ["pinode1"], "some.task.module", 5, {}, id=123456)

        task1_modified = set_periodic_task("every month", "0 0 1 * *", ["pinode1"], "some.task.module", 3, {
            "key1": 123,
            "key3": True,
        }, id=task1)

        self.assertEqual(len(PeriodicTask.query.all()), 3)
        self.assertEqual(task1, task1_modified)
        # we have updated the task definition
        self.assertGreater(get_periodic_task_by_id(task1)["last_update"], task1_last_update)
        self.assertEqual(get_periodic_tasks(name="every month")[0]["options"],
                         {"key1": "123", "key3": "True"})

        all_tasks = get_periodic_tasks()
        self.assertEqual(len(all_tasks), 3)
        # ordered by ordering
        self.assertEqual([task["name"] for task in all_tasks], ["task two", "task three", "every month"])

        active_tasks = get_periodic_tasks(active=True)
        self.assertEqual(len(active_tasks), 2)
        self.assertEqual([task["name"] for task in active_tasks], ["task three", "every month"])

        active_tasks_on_pinode2 = get_periodic_tasks(active=True, node="pinode2")
        self.assertEqual(len(active_tasks_on_pinode2), 1)
        self.assertEqual(active_tasks_on_pinode2[0]["name"], "task three")

        enable_periodic_task(task2)

        active_tasks_on_pinode2 = get_periodic_tasks(active=True, node="pinode2")
        self.assertEqual(len(active_tasks_on_pinode2), 2)
        self.assertEqual([task["name"] for task in active_tasks_on_pinode2],
                         ["task two", "task three"])

        active_tasks_on_pinode1 = get_periodic_tasks(active=True, node="pinode1")
        self.assertEqual(len(active_tasks_on_pinode1), 2)
        self.assertEqual([task["name"] for task in active_tasks_on_pinode1],
                         ["task three", "every month"])

        active_tasks_on_pinode3 = get_periodic_tasks(active=True, node="pinode3")
        self.assertEqual(active_tasks_on_pinode3, [])

        enable_periodic_task(task1, False)
        delete_periodic_task(task3)
        with self.assertRaises(ResourceNotFoundError):
            enable_periodic_task(task3)

        active_tasks_on_pinode1 = get_periodic_tasks(active=True, node="pinode1")
        self.assertEqual(active_tasks_on_pinode1, [])

        tasks_on_pinode1 = get_periodic_tasks(node="pinode1")
        self.assertEqual(len(tasks_on_pinode1), 1)
        self.assertEqual(tasks_on_pinode1[0]["name"], "every month")

        delete_periodic_task(task1)
        delete_periodic_task(task2)
        with self.assertRaises(ResourceNotFoundError):
            delete_periodic_task(task2)

        self.assertEqual(get_periodic_tasks(), [])

    def test_04_last_run(self):
        task1_id = set_periodic_task("task one", "*/5 * * * *", ["pinode1", "pinode2"], "some.task.module", 3, {
            "key1": 1,
            "key2": False
        })
        self.assertEqual(len(PeriodicTask.query.all()), 1)
        task1_entry = PeriodicTask.query.filter_by(id=task1_id).one()

        # We have no initial last runs
        self.assertEqual(len(list(task1_entry.last_runs)), 0)

        set_periodic_task_last_run(task1_id, "pinode1", parse_timestamp("2018-06-26 08:00+02:00"))
        set_periodic_task_last_run(task1_id, "pinode1", parse_timestamp("2018-06-26 08:05+02:00"))

        task1 = get_periodic_tasks("task one")[0]
        self.assertEqual(len(list(task1_entry.last_runs)), 1)
        self.assertEqual(task1_entry.last_runs[0].timestamp,
                         parse_timestamp("2018-06-26 06:05"))
        self.assertEqual(task1["last_runs"]["pinode1"],
                         parse_timestamp("2018-06-26 06:05 UTC"))

        set_periodic_task_last_run(task1_id, "pinode2", parse_timestamp("2018-06-26 08:10+01:00"))
        set_periodic_task_last_run(task1_id, "pinode3", parse_timestamp("2018-06-26 08:10-08:00"))
        task1 = get_periodic_tasks("task one")[0]
        self.assertEqual(task1["last_runs"]["pinode1"],
                         parse_timestamp("2018-06-26 06:05 UTC"))
        self.assertEqual(task1["last_runs"]["pinode2"],
                         parse_timestamp("2018-06-26 07:10 UTC"))
        self.assertEqual(task1["last_runs"]["pinode3"],
                         parse_timestamp("2018-06-26 16:10 UTC"))

        delete_periodic_task(task1_id)

    def test_05_scheduling(self):
        # this unit test operates in russian time
        tzinfo = gettz("Europe/Moscow")

        # at midnight on each 1st
        task1 = set_periodic_task("task one", "0 0 1 * *", ["pinode1"], "some.task.module", 3, {
            "key1": 1,
            "key2": False
        })
        # at 08:00 on wednesdays
        current_utc_time = parse_timestamp("2018-05-31 05:08:00")
        with mock.patch('privacyidea.models.datetime') as mock_dt:
            mock_dt.utcnow.return_value = current_utc_time
            task2 = set_periodic_task("task two", "0 8 * * WED", ["pinode2", "pinode3"], "some.task.module", 1, {
                "key1": "value",
                "key2": "foo"
            }, active=False)
        self.assertEqual(get_periodic_task_by_id(task2)["last_update"],
                         parse_timestamp("2018-05-31 08:08:00+03:00"))
        self.assertEqual(get_periodic_task_by_id(task2)["last_runs"], {})

        # every 30 minutes, on Tuesdays
        task3 = set_periodic_task("task three", "*/30 * * * 2", ["pinode1", "pinode2"], "some.task.module", 2, {
            "key1": 1234,
            "key2": 5678,
        })
        # on each 1st of august at midnight
        task4 = set_periodic_task("task four", "0 0 1 8 *", ["pinode2"], "some.task.module", 0)

        # we need some last runs
        set_periodic_task_last_run(task1, "pinode1", parse_timestamp("2018-06-01 00:00:05+03:00"))

        # no last run for pinode3 here!
        set_periodic_task_last_run(task2, "pinode2", parse_timestamp("2018-06-20 08:00:05+03:00"))

        set_periodic_task_last_run(task3, "pinode1", parse_timestamp("2018-06-26 11:36:37+03:00"))
        set_periodic_task_last_run(task3, "pinode2", parse_timestamp("2018-06-26 11:30:33+03:00"))

        set_periodic_task_last_run(task4, "pinode2", parse_timestamp("2017-08-01 00:00:43+03:00"))

        self.assertEqual([task["name"] for task in get_periodic_tasks()],
                         ["task four", "task two", "task three", "task one"])

        # Invalid timestamp
        with self.assertRaises(ParameterError):
            get_scheduled_periodic_tasks("pinode1", parse_timestamp("2017-08-01 00:00:00"), tzinfo)

        # On pinode1:
        # task1 at midnight on each 1st
        # task3 every 30 minutes on tuesdays

        # On pinode2:
        # task2 on 08:00 on wednesdays, but it is inactive
        # task3 every 30 minutes on tuesdays
        # task4 on each 1st August at midnight

        # 26th June (Tuesday), 11:59
        # No tasks on both nodes
        current_timestamp = parse_timestamp("2018-06-26 11:59+03:00")

        scheduled = get_scheduled_periodic_tasks("pinode1", current_timestamp, tzinfo)
        self.assertEqual(scheduled, [])

        scheduled = get_scheduled_periodic_tasks("pinode2", current_timestamp, tzinfo)
        self.assertEqual(scheduled, [])

        # 26th June (Tuesday), 12:00
        # Run task3 on both nodes
        current_timestamp = parse_timestamp("2018-06-26 12:00+03:00")

        scheduled = get_scheduled_periodic_tasks("pinode1", current_timestamp, tzinfo)
        self.assertEqual([task["name"] for task in scheduled], ["task three"])

        scheduled = get_scheduled_periodic_tasks("pinode2", current_timestamp, tzinfo)
        self.assertEqual([task["name"] for task in scheduled], ["task three"])

        # 1th August (Wednesday), 13:57
        # Assume task3 has been run successfully on 30th July (Tuesday)
        set_periodic_task_last_run(task3, "pinode1", parse_timestamp("2018-08-01 00:00+03:00"))
        set_periodic_task_last_run(task3, "pinode2", parse_timestamp("2018-08-01 00:00+03:00"))

        # On pinode1, run task1
        # On pinode2, run task4
        current_timestamp = parse_timestamp("2018-08-01 11:59+03:00")

        scheduled = get_scheduled_periodic_tasks("pinode1", current_timestamp, tzinfo)
        self.assertEqual([task["name"] for task in scheduled], ["task one"])

        scheduled = get_scheduled_periodic_tasks("pinode2", current_timestamp, tzinfo)
        self.assertEqual([task["name"] for task in scheduled], ["task four"])

        # Enable task2, now we also have to run it on pinode2 and pinode3
        with mock.patch('privacyidea.models.datetime') as mock_dt:
            mock_dt.utcnow.return_value = current_utc_time
            enable_periodic_task(task2)

        scheduled = get_scheduled_periodic_tasks("pinode1", current_timestamp, tzinfo)
        self.assertEqual([task["name"] for task in scheduled], ["task one"])

        scheduled = get_scheduled_periodic_tasks("pinode2", current_timestamp, tzinfo)
        self.assertEqual([task["name"] for task in scheduled], ["task four", "task two"])

        scheduled = get_scheduled_periodic_tasks("pinode3", current_timestamp, tzinfo)
        self.assertEqual([task["name"] for task in scheduled], ["task two"])

        # Simulate runs
        set_periodic_task_last_run(task1, "pinode1", current_timestamp)
        set_periodic_task_last_run(task2, "pinode2", current_timestamp)
        set_periodic_task_last_run(task2, "pinode3", current_timestamp)
        set_periodic_task_last_run(task4, "pinode2", current_timestamp)

        # Now, we don't have to run anything
        current_timestamp += timedelta(seconds=1)

        self.assertEqual(get_scheduled_periodic_tasks("pinode1", current_timestamp, tzinfo), [])
        self.assertEqual(get_scheduled_periodic_tasks("pinode2", current_timestamp, tzinfo), [])

        delete_periodic_task(task1)
        delete_periodic_task(task2)
        delete_periodic_task(task3)
        delete_periodic_task(task4)

    def test_06_execute_task(self):
        assertEqual = self.assertEqual

        class _TestTask(BaseTask):
            identifier = "Test"
            description = "foo"

            def do(self, params):
                assertEqual(params["key"], "value")
                return True

        with self.assertRaises(ParameterError):
            execute_task("Test", {"key": "value"})

        with mock.patch.dict(TASK_MODULES, values={"Test": _TestTask}):
            ret = execute_task("Test", {"key": "value"})
            self.assertTrue(ret)
