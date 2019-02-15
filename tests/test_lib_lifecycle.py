"""
This file contains the tests for the lifecycle module lib/lifecycle.py
"""
import json
from mock import mock

from privacyidea.lib.lifecycle import register_finalizer, call_finalizers
from .base import MyTestCase


class LifecycleTestCase(MyTestCase):
    # Create admin authentication token for each testcase
    def setUp(self):
        self.authenticate()

    def test_01_register_finalizer(self):
        finalizer1 = mock.MagicMock()
        finalizer2 = mock.MagicMock()
        finalizer3 = mock.MagicMock()
        register_finalizer(finalizer1)
        register_finalizer(finalizer2)
        call_finalizers()
        finalizer1.assert_called_once()
        finalizer2.assert_called_once()
        finalizer3.assert_not_called()
        # call_finalizer clears the list of finalizers
        register_finalizer(finalizer3)
        call_finalizers()
        finalizer1.assert_called_once()
        finalizer2.assert_called_once()
        finalizer3.assert_called_once()

    def test_02_register_finalizer_request_context(self):
        finalizer1 = mock.MagicMock()
        finalizer2 = mock.MagicMock()
        # test that we can use finalizers
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            register_finalizer(finalizer1)
            register_finalizer(finalizer2)
            res = self.app.full_dispatch_request()
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result.get("status"))
        finalizer1.assert_called_once()
        finalizer2.assert_called_once()
        # test that they are not called in the next request
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result.get("status"))
        finalizer1.assert_called_once()
        finalizer2.assert_called_once()

    def test_03_finalizer_error(self):
        finalizer1 = mock.MagicMock()
        finalizer1.side_effect = RuntimeError()
        finalizer2 = mock.MagicMock()
        # test that we can use finalizers
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            register_finalizer(finalizer1)
            register_finalizer(finalizer2)
            res = self.app.full_dispatch_request()
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result.get("status"))
        finalizer1.assert_called_once()
        finalizer2.assert_called_once()

