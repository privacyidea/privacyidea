"""
This file contains the tests for the lifecycle module lib/lifecycle.py
"""
from unittest import mock

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
        with self.app.test_request_context('/'):
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
        # test that we can use finalizers. A request starts with an empty g, so they are registered after the
        # request started, but before its request context ends.
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            register_finalizer(finalizer1)
            register_finalizer(finalizer2)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
        finalizer1.assert_called_once()
        finalizer2.assert_called_once()
        # test that they are not called in the next request
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
        finalizer1.assert_called_once()
        finalizer2.assert_called_once()

    def test_03_finalizer_error(self):
        finalizer1 = mock.MagicMock()
        finalizer1.side_effect = RuntimeError()
        finalizer2 = mock.MagicMock()
        # test that we can use finalizers. A request starts with an empty g, so they are registered after the
        # request started, but before its request context ends.
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            register_finalizer(finalizer1)
            register_finalizer(finalizer2)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
        finalizer1.assert_called_once()
        finalizer2.assert_called_once()

    def test_04_finalizer_outside_a_request_runs_when_the_application_context_ends(self):
        # A command line tool has no request. Its finalizers run when its application context ends, also when one of
        # them fails. The test class keeps one application context for all its tests, so this test pushes its own.
        failing_finalizer = mock.MagicMock(side_effect=RuntimeError())
        finalizer = mock.MagicMock()
        with self.app.app_context():
            register_finalizer(failing_finalizer)
            register_finalizer(finalizer)
            failing_finalizer.assert_not_called()
            finalizer.assert_not_called()
        failing_finalizer.assert_called_once()
        finalizer.assert_called_once()

    def test_05_request_finalizer_runs_once_when_the_application_context_ends_after_the_request(self):
        # In production, every request has an application context of its own, which ends after the request.
        finalizer = mock.MagicMock()
        with self.app.app_context():
            with self.app.test_request_context('/token/',
                                               method='GET',
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                register_finalizer(finalizer)
                self.assertTrue(res.json["result"]["status"])
            finalizer.assert_called_once()
        finalizer.assert_called_once()

    def test_06_a_request_does_not_call_the_finalizers_registered_outside_a_request(self):
        # They belong to the application context and run when it ends, also if a request ran in it.
        finalizer = mock.MagicMock()
        with self.app.app_context():
            register_finalizer(finalizer)
            with self.app.test_request_context('/token/',
                                               method='GET',
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.json["result"]["status"])
            finalizer.assert_not_called()
        finalizer.assert_called_once()
