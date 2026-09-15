from privacyidea.models import MonitoringStats, db
from privacyidea.lib.framework import get_request_local_store
from privacyidea.lib.monitoringmodules.sqlstats import Monitoring
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
        # Since the sqlstats monitoring module handles the db in its own
        # session, we need to refresh the current session in order to retrieve
        # the updated (removed) data
        db.session.commit()
        self.assertEqual(1, MonitoringStats.query.filter_by(stats_key=key1).count())

    def test_02_delete_stats(self):
        key1 = "otherkey"
        now = datetime.datetime.now(tzlocal())
        write_stats(key1, 12, timestamp=now- timedelta(days=1))
        write_stats(key1, 13, timestamp=now)
        write_stats(key1, 14, timestamp=now + timedelta(days=1))
        db.session.commit()
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 3)

        # delete the last two entries
        r = delete_stats(key1, start_timestamp=now - timedelta(minutes=60))

        # check there is only one entry
        db.session.commit()
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 1)
        self.assertEqual(r, 2)

        # Again write three entries
        write_stats(key1, 13, timestamp=now)
        write_stats(key1, 14, timestamp=now + timedelta(days=1))
        db.session.commit()
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 3)

        # Delete the first two entries
        r = delete_stats(key1, end_timestamp=now + timedelta(minutes=60))
        db.session.commit()
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

        db.session.commit()
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

        db.session.commit()
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


class MonitoringSessionTestCase(MyTestCase):
    """
    The monitoring module opens a session of its own, so it also has to hand the
    connection back when the request that opened it ends.
    """

    def test_01_finalizer_is_registered_only_while_a_request_is_handled(self):
        # Outside a request nothing ever calls the finalizers, so registering one there
        # would only keep the module - and its open connection - alive for good.
        store = get_request_local_store()
        before = len(store.get("call_on_teardown", []))
        Monitoring(self.app.config)
        self.assertEqual(before, len(store.get("call_on_teardown", [])))

        with self.app.test_request_context("/"):
            monitoring = Monitoring(self.app.config)
            request_store = get_request_local_store()
            self.assertIn(monitoring._finalize_session, request_store["call_on_teardown"])

    def test_02_teardown_disposes_an_engine_of_its_own(self):
        monitoring = Monitoring(self.app.config)
        # The testing configuration uses the null registry, which hands out a private
        # engine to every caller, so this one is this object's to dispose.
        self.assertTrue(monitoring._owns_engine)
        write_stats("session_key", 1)
        pool = monitoring.engine.pool
        monitoring._finalize_session()
        # dispose() installs a fresh pool, which closes the connections the old one held
        self.assertIsNot(pool, monitoring.engine.pool)
