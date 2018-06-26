# coding: utf-8
from privacyidea.models import MonitoringStats
from privacyidea.lib.monitoringstats import (write_stats, delete_stats,
                                             get_stats_keys)

from .base import MyTestCase
import datetime
from datetime import timedelta


class TokenModelTestCase(MyTestCase):

    def test_01_write_stats(self):
        key1 = "some_key"
        write_stats(key1, 12)
        write_stats(key1, 13)

        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 2)

        # Now we write a new value, but with the paramter to delete old values
        write_stats(key1, 14, reset_values=True)
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 1)

    def test_02_delete_stats(self):
        key1 = "otherkey"
        write_stats(key1, 12, timestamp=datetime.datetime.now() - timedelta(days=1))
        write_stats(key1, 13, timestamp=datetime.datetime.now())
        write_stats(key1, 14, timestamp=datetime.datetime.now() + timedelta(days=1))
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 3)

        # delete the last two entries
        r = delete_stats(key1, start_timestamp=datetime.datetime.now() - timedelta(minutes=60))

        # check there is only one entry
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 1)
        self.assertEqual(r, 2)

        # Again write three entries
        write_stats(key1, 13, timestamp=datetime.datetime.now())
        write_stats(key1, 14, timestamp=datetime.datetime.now() + timedelta(days=1))
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 3)

        # Delete the first two entries
        r = delete_stats(key1, end_timestamp=datetime.datetime.now() + timedelta(minutes=60))
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 1)
        self.assertEqual(r, 2)

    def test_03_get_keys(self):
        # delete old entries
        keys = get_stats_keys()
        for k in keys:
            delete_stats(k)

        # write new stats entries
        write_stats("key1", 13)
        write_stats("key1", 13)
        write_stats("key1", 13)
        write_stats("key2", 12)
        write_stats("key3", 12)

        keys = get_stats_keys()
        self.assertEqual(len(keys), 3)
        self.assertTrue("key1" in keys)
        self.assertTrue("key2" in keys)
        self.assertTrue("key3" in keys)