# coding: utf-8
from privacyidea.models import MonitoringStats
from privacyidea.lib.monitoringstats import (write_stats, delete_stats,
                                             get_stats_keys, get_values,
                                             get_last_value)

from .base import MyTestCase
import datetime
from dateutil.tz import tzlocal, tzutc
from datetime import timedelta


class TokenModelTestCase(MyTestCase):

    def test_01_write_stats(self):
        key1 = "some_key"
        write_stats(key1, 12)
        write_stats(key1, 13)

        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 2)
        # Assert naive datetime
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).first().timestamp.tzinfo, None)

        # Now we write a new value, but with the parameter to delete old values
        write_stats(key1, 14, reset_values=True)
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 1)

    def test_02_delete_stats(self):
        key1 = "otherkey"
        now = datetime.datetime.now(tzlocal())
        write_stats(key1, 12, timestamp=now- timedelta(days=1))
        write_stats(key1, 13, timestamp=now)
        write_stats(key1, 14, timestamp=now + timedelta(days=1))
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 3)

        # delete the last two entries
        r = delete_stats(key1, start_timestamp=now - timedelta(minutes=60))

        # check there is only one entry
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 1)
        self.assertEqual(r, 2)

        # Again write three entries
        write_stats(key1, 13, timestamp=now)
        write_stats(key1, 14, timestamp=now + timedelta(days=1))
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 3)

        # Delete the first two entries
        r = delete_stats(key1, end_timestamp=now + timedelta(minutes=60))
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

    def test_04_get_values(self):
        # delete old entries
        keys = get_stats_keys()
        for k in keys:
            delete_stats(k)

        ts = datetime.datetime.now(tzlocal())
        write_stats("key1", 1, timestamp=ts - timedelta(minutes=10))
        write_stats("key1", 2, timestamp=ts - timedelta(minutes=9))
        write_stats("key1", 3, timestamp=ts - timedelta(minutes=8))
        write_stats("key1", 4, timestamp=ts - timedelta(minutes=7))
        write_stats("key1", 5, timestamp=ts - timedelta(minutes=6))
        write_stats("key1", 6, timestamp=ts - timedelta(minutes=5))
        write_stats("key1", 7, timestamp=ts - timedelta(minutes=4))
        write_stats("key1", 8, timestamp=ts - timedelta(minutes=3))
        write_stats("key1", 9, timestamp=ts - timedelta(minutes=2))
        write_stats("key1", 10, timestamp=ts - timedelta(minutes=1))

        r = get_values("key1")
        self.assertEqual(len(r), 10)
        # The third entry is a 3
        self.assertEqual(r[2][1], 3)
        # The last value is a 10
        self.assertEqual(r[9][1], 10)

        r = get_values("key1",
                       start_timestamp=ts - timedelta(minutes=8),
                       end_timestamp=ts - timedelta(minutes=4))
        # We get 3,4,5,6,7
        self.assertEqual([entry[1] for entry in r], [3, 4, 5, 6, 7])
        # Assert it is the correct time, and timezone-aware UTC
        self.assertEqual(r[0][0], ts - timedelta(minutes=8))
        self.assertEqual(r[0][0].tzinfo, tzutc())
        self.assertEqual(r[-1][0], ts - timedelta(minutes=4))

        r = get_values("key1",
                       start_timestamp=ts - timedelta(minutes=8))
        self.assertEqual([entry[1] for entry in r], [3, 4, 5, 6, 7, 8, 9, 10])

        r = get_values("key1",
                       end_timestamp=ts - timedelta(minutes=8))
        self.assertEqual([entry[1] for entry in r], [1, 2, 3])

        # Get the last value of key1
        r = get_last_value("key1")
        self.assertEqual(r, 10)