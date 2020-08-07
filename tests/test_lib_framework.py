"""
This file contains the tests for the module lib/framework.py
"""
from flask import current_app, g

from privacyidea.app import create_app
from privacyidea.lib.framework import get_app_config, get_app_config_value, get_app_local_store, get_request_local_store
from tests.base import MyTestCase


class FrameworkTestCase(MyTestCase):
    def test_01_config(self):
        self.assertEqual(get_app_config(), current_app.config)
        self.assertEqual(get_app_config()["SUPERUSER_REALM"], ["adminrealm"])

        self.assertEqual(get_app_config_value("SUPERUSER_REALM"), ["adminrealm"])
        self.assertEqual(get_app_config_value("DOES_NOT_EXIST"), None)
        self.assertEqual(get_app_config_value("DOES_NOT_EXIST", 1337), 1337)

    def test_02_app_local_store(self):
        store1 = get_app_local_store()
        store1["hello"] = "world"
        g.test_flag = True

        # We get the same store even if we push another app context for the same app
        with self.app.app_context():
            store2 = get_app_local_store()
            self.assertEqual(store1, store2)
            self.assertEqual(store2["hello"], "world")
            self.assertNotIn("test_flag", g)
            g.test_flag = False

        self.assertEqual(g.test_flag, True)
        g.pop("test_flag")

        # We get a different store if we push a context for another app
        new_app = create_app("testing", "")
        with new_app.app_context():
            store3 = get_app_local_store()
            self.assertNotIn("hello", store3)
            self.assertNotEqual(store3, store1)
            store3["hello"] = "no!"
            store4 = get_app_local_store()
            store3["something"] = "else"
            self.assertEqual(store4["hello"], "no!")
            self.assertEqual(store4["something"], "else")

        self.assertEqual(store1, store2)
        self.assertEqual(store2["hello"], "world")

    def test_03_request_local_store(self):
        store1 = get_request_local_store()
        store1["hello"] = "world"
        # We get a different store if we push another context for the same app
        with self.app.app_context():
            store2 = get_request_local_store()
            self.assertNotIn("hello", store2)
            store2["hello"] = "hallo"
            store3 = get_request_local_store()
            self.assertEqual(store3["hello"], "hallo")
            store3["one"] = 1
            self.assertEqual(store2["one"], 1)

        store1["foo"] = "bar"
        store4 = get_request_local_store()
        self.assertEqual(store4["hello"], "world")
        self.assertEqual(store1["hello"], "world")
        self.assertEqual(store1["foo"], "bar")
