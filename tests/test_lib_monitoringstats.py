# coding: utf-8
from privacyidea.models import MonitoringStats
from privacyidea.lib.monitoringstats import write_stats

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