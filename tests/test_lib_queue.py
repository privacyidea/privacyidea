"""
This file contains the tests for the job queue modules.

In particular, this tests
lib/queue/*.py
"""
from huey import RedisHuey
import mock

from privacyidea.app import create_app
from privacyidea.config import TestingConfig
from privacyidea.lib.error import ServerError
from privacyidea.lib.queue import job, JOB_COLLECTOR, JobCollector, get_job_queue, wrap_job, has_job_queue
from privacyidea.lib.queues.huey_queue import HueyQueue
from privacyidea.lib.queues.base import QueueError
from .base import OverrideConfigTestCase, MyTestCase


class TestSender(object):
    """ defined in order to be able to mock the ``send_mail`` function in tests """
    def send_mail(*args, **kwargs):
        pass


SENDER = TestSender()


@job("test.my_add")
def my_add(a, b):
    return a + b


@job("test.my_send_mail")
def my_send_mail(message):
    SENDER.send_mail(message)
    return 1337


class NoQueueTestCase(OverrideConfigTestCase):
    class Config(TestingConfig):
        PI_JOB_QUEUE_CLASS = ""

    def test_01_no_job_queue(self):
        self.assertFalse(has_job_queue())
        with self.assertRaises(ServerError):
            get_job_queue()

    def test_02_collector(self):
        self.assertIsInstance(JOB_COLLECTOR, JobCollector)
        self.assertDictContainsSubset({
            "test.my_add": (my_add, (), {}),
            "test.my_send_mail": (my_send_mail, (), {})
        }, JOB_COLLECTOR.jobs)


class InvalidQueueTestCase(MyTestCase):
    def test_01_create_app_graciously(self):
        class Config(TestingConfig):
            PI_JOB_QUEUE_CLASS = "obviously.invalid"

        with mock.patch.dict("privacyidea.config.config", {"testing": Config}):
            app = create_app("testing", "") # we do not throw an exception


class HueyQueueTestCase(OverrideConfigTestCase):
    class Config(TestingConfig):
        PI_JOB_QUEUE_CLASS = "privacyidea.lib.queues.huey_queue.HueyQueue"
        PI_JOB_QUEUE_NAME = "myqueuename"
        PI_JOB_QUEUE_ALWAYS_EAGER = True # avoid redis server for testing

    def test_01_app_job_queue(self):
        queue = get_job_queue()
        self.assertIsInstance(queue, HueyQueue)
        self.assertEqual(queue.options, {"name": "myqueuename", "always_eager": True})
        self.assertTrue({"test.my_add", "test.my_send_mail"}.issubset(set(queue.jobs)))
        self.assertIsInstance(queue.huey, RedisHuey)
        self.assertEqual(queue.huey.name, "myqueuename")
        self.assertFalse(queue.huey.store_none)
        with self.assertRaises(QueueError):
            queue.register_job("test.my_add", lambda x: x)

    def test_03_enqueue_jobs(self):
        queue = get_job_queue()
        queue.enqueue("test.my_add", (3, 4), {}) # No result is stored

        with mock.patch.object(SENDER, 'send_mail') as mock_mail:
            queue.enqueue("test.my_send_mail", ("hi",), {})
            mock_mail.assert_called_once_with("hi")

        with self.assertRaises(QueueError):
            queue.enqueue("test.unknown", ("hi",), {})

    def test_04_wrap_jobs(self):
        wrapped = wrap_job("test.my_send_mail", True)
        with mock.patch.object(SENDER, 'send_mail') as mock_mail:
            result = wrapped("hi")
            mock_mail.assert_called_once_with("hi")
            self.assertTrue(result)
        with mock.patch.object(SENDER, 'send_mail') as mock_mail:
            result = my_send_mail("hi")
            mock_mail.assert_called_once_with("hi")
            self.assertEqual(result, 1337)