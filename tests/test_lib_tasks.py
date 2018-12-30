"""
This file contains the tests for tasks.

In particular, this tests
lib/task/base.py
"""

from privacyidea.lib.task.base import BaseTask
from .base import MyTestCase
import six


class BaseTaskTestCase(MyTestCase):
    def test_01_base_functions(self):
        task = BaseTask({})

        self.assertEqual(task.identifier, "BaseTask")
        self.assertIsInstance(task.description, six.string_types)
        self.assertEqual(task.options, {})

        result1 = task.do()
        self.assertTrue(result1)

        result2 = task.do({
            "foo": "bar"
        })
        self.assertTrue(result2)
