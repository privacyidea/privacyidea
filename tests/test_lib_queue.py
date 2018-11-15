"""
This file contains the tests for the job queue modules.

In particular, this tests
lib/queue/*.py
"""
from mock import MagicMock, mock

from privacyidea.lib.queue import job, JOB_COLLECTOR, JobCollector, get_job_queue, NullQueue, wrap_job
from privacyidea.lib.queue.base import QueueError
from privacyidea.lib.queue.promise import ImmediatePromise
from .base import MyTestCase


class TestSender(object):
    """ defined in order to be able to mock the ``send_mail`` function in tests """
    def send_mail(*args, **kwargs):
        pass

SENDER = TestSender()


@job("test.my_add")
def my_add(a, b):
    return a + b


@job("test.my_send_mail", fire_and_forget=True)
def my_send_mail(message):
    SENDER.send_mail(message)
    return 1337


class NullQueueTestCase(MyTestCase):
    def test_01_collector(self):
        self.assertIsInstance(JOB_COLLECTOR, JobCollector)
        self.assertDictContainsSubset({
            "test.my_add": (my_add, (), {}),
            "test.my_send_mail": (my_send_mail, (), {"fire_and_forget": True})
        }, JOB_COLLECTOR.jobs)
        with self.assertRaises(RuntimeError):
            JOB_COLLECTOR.register_app(self.app)

    def test_02_app_job_queue(self):
        queue = get_job_queue()
        self.assertIsInstance(queue, NullQueue)
        self.assertDictContainsSubset({
            "test.my_add": my_add,
            "test.my_send_mail": my_send_mail
        }, queue.jobs)
        with self.assertRaises(QueueError):
            queue.add_job("test.my_add", lambda x: x)

    def test_03_enqueue_jobs(self):
        queue = get_job_queue()
        promise = queue.enqueue("test.my_add", (3, 4), {})
        self.assertIsInstance(promise, ImmediatePromise)
        self.assertEqual(promise.get(), 7)

        with mock.patch.object(SENDER, 'send_mail') as mock_mail:
            promise = queue.enqueue("test.my_send_mail", ("hi",), {})
            mock_mail.assert_called_once_with("hi")
            self.assertEqual(promise.get(), 1337)

        with self.assertRaises(QueueError):
            queue.enqueue("test.unknown", ("hi",), {})

    def test_04_wrap_jobs(self):
        wrapped = wrap_job("test.my_send_mail", True)
        with mock.patch.object(SENDER, 'send_mail') as mock_mail:
            result = wrapped("hi")
            mock_mail.assert_called_once_with("hi")
            self.assertTrue(result)