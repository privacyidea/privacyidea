# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ``privacyidea.lib.metrics`` substrate."""
import datetime
from unittest.mock import patch

from sqlalchemy import select

from privacyidea.lib import metrics
from privacyidea.lib.metrics import (
    _BUCKETS,
    _labels_key,
    _parse_labels_key,
    _percentile_from_buckets,
    _window_start,
    cleanup_old_metrics,
    get_metrics,
    inc,
    observe,
)
from privacyidea.models import db
from privacyidea.models.metric_aggregate import MetricAggregate
from tests.base import MyTestCase


def _wipe_metrics():
    db.session.query(MetricAggregate).delete()
    db.session.commit()


class LabelKeyTest(MyTestCase):
    """``_labels_key`` and its inverse ``_parse_labels_key``."""

    def test_empty_labels(self):
        self.assertEqual(_labels_key(None), "")
        self.assertEqual(_labels_key({}), "")
        self.assertEqual(_parse_labels_key(""), {})

    def test_sorted_serialization(self):
        # Keys are emitted in sorted order so the same dict always hashes
        # to the same row, regardless of the caller's insertion order.
        self.assertEqual(_labels_key({"b": "2", "a": "1"}), "a=1,b=2")
        self.assertEqual(_labels_key({"a": "1", "b": "2"}), "a=1,b=2")

    def test_round_trip(self):
        labels = {"resolver": "ldap1", "op": "checkPass", "node": "n1"}
        self.assertEqual(_parse_labels_key(_labels_key(labels)), labels)


class WindowStartTest(MyTestCase):
    """``_window_start`` truncates to 5-minute boundaries."""

    def test_truncates_to_5min(self):
        now = datetime.datetime(2026, 4, 30, 12, 37, 42)
        # 12:37:42 -> 12:35:00
        self.assertEqual(_window_start(now), datetime.datetime(2026, 4, 30, 12, 35, 0))
        now2 = datetime.datetime(2026, 4, 30, 12, 35, 0)
        self.assertEqual(_window_start(now2), now2)


class PercentileTest(MyTestCase):
    """``_percentile_from_buckets`` against the active bucket set."""

    def test_empty_returns_none(self):
        self.assertIsNone(_percentile_from_buckets({}, 0, 0.95))

    def test_p95_lands_on_first_bucket_above_target(self):
        # 100 samples, 95 of them <= 100 ms -> p95 == 100 ms.
        buckets = {col: 100 for _, col in _BUCKETS}
        # All samples were small, so every bucket reports 100.
        # p95 lands on the smallest bucket whose cumulative count >= 95.
        self.assertEqual(_percentile_from_buckets(buckets, 100, 0.95), 0.05)

    def test_p95_above_largest_bucket_returns_none(self):
        # If only 50 of 100 samples are <= 5s, the >5s tail dominates p95.
        buckets = {col: 50 for _, col in _BUCKETS}
        self.assertIsNone(_percentile_from_buckets(buckets, 100, 0.95))

    def test_p50_picks_right_bucket(self):
        # 100 samples; 60 <= 100 ms, all higher buckets carry that 60 too.
        buckets = {col: 60 for _, col in _BUCKETS}
        buckets["bucket_le_50ms"] = 10
        # Target is 50; cumulative counts: 10 (50ms), 60 (100ms) -> 100ms.
        self.assertEqual(_percentile_from_buckets(buckets, 100, 0.50), 0.1)


class IncTest(MyTestCase):
    """``inc`` round-trips."""

    def setUp(self):
        _wipe_metrics()

    def test_simple_counter(self):
        inc("test_counter")
        results = get_metrics(name="test_counter")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 1)
        self.assertEqual(results[0]["labels"], {})

    def test_repeated_inc_accumulates_in_same_row(self):
        for _ in range(5):
            inc("test_counter", {"channel": "push"})
        rows = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "test_counter")
        ).scalars().all()
        # All five increments in the current 5-minute window collapse to one row.
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].count, 5)

    def test_inc_by_amount(self):
        inc("test_counter", by=7)
        inc("test_counter", by=3)
        results = get_metrics(name="test_counter")
        self.assertEqual(results[0]["count"], 10)

    def test_label_separation(self):
        inc("test_counter", {"result": "ok"})
        inc("test_counter", {"result": "ok"})
        inc("test_counter", {"result": "failed"})
        results = {tuple(sorted(r["labels"].items())): r["count"]
                   for r in get_metrics(name="test_counter")}
        self.assertEqual(results[(("result", "ok"),)], 2)
        self.assertEqual(results[(("result", "failed"),)], 1)


class ObserveTest(MyTestCase):
    """``observe`` records count/sum/max + bucket boundaries correctly."""

    def setUp(self):
        _wipe_metrics()

    def test_count_sum_max(self):
        observe("test_hist", 0.05)
        observe("test_hist", 0.10)
        observe("test_hist", 0.30)
        results = get_metrics(name="test_hist")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 3)
        self.assertAlmostEqual(results[0]["avg"], (0.05 + 0.10 + 0.30) / 3)
        self.assertAlmostEqual(results[0]["max"], 0.30)

    def test_bucket_assignment(self):
        # Cumulative semantics: every bucket whose upper bound >= value is incremented. 0.07s
        # therefore ticks every bucket from 100ms onward but not 50ms.
        observe("test_hist", 0.07)
        row = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "test_hist")
        ).scalar_one()
        self.assertEqual(row.bucket_le_50ms, 0)
        self.assertEqual(row.bucket_le_100ms, 1)
        self.assertEqual(row.bucket_le_150ms, 1)
        self.assertEqual(row.bucket_le_200ms, 1)
        self.assertEqual(row.bucket_le_250ms, 1)
        self.assertEqual(row.bucket_le_500ms, 1)
        self.assertEqual(row.bucket_le_1s, 1)
        self.assertEqual(row.bucket_le_5s, 1)

    def test_value_above_largest_bucket_only_counts(self):
        # 7s falls in the implicit +inf bucket - count goes up but no bucket column.
        observe("test_hist", 7.0)
        row = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "test_hist")
        ).scalar_one()
        self.assertEqual(row.count, 1)
        for _, col in _BUCKETS:
            self.assertEqual(getattr(row, col), 0)
        self.assertAlmostEqual(row.max_value, 7.0)

    def test_p95_computed_at_active_bucket_set(self):
        # 100 samples at ~75ms -> p95 should be the 100ms bucket.
        for _ in range(100):
            observe("test_hist", 0.075)
        results = get_metrics(name="test_hist")
        self.assertEqual(results[0]["p95"], 0.1)


class CrossWindowAndNodeAggregationTest(MyTestCase):
    """Reads fold across nodes and 5-minute windows."""

    def setUp(self):
        _wipe_metrics()

    def test_aggregates_across_nodes(self):
        # Drop two rows under the same (metric, labels_key, window) but
        # different node values, then read back - get_metrics should fold them.
        now = _window_start(datetime.datetime.utcnow())
        for node in ("nodeA", "nodeB"):
            row = MetricAggregate(metric_name="cross_test", labels_key="",
                                  node=node, window_start=now,
                                  count=4, sum_value=0.4, max_value=0.2)
            db.session.add(row)
        db.session.commit()
        results = get_metrics(name="cross_test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 8)
        self.assertAlmostEqual(results[0]["avg"], 0.1)
        self.assertAlmostEqual(results[0]["max"], 0.2)

    def test_aggregates_across_windows(self):
        now = _window_start(datetime.datetime.utcnow())
        earlier = now - datetime.timedelta(seconds=300)
        for window in (now, earlier):
            row = MetricAggregate(metric_name="cross_test", labels_key="",
                                  node="n1", window_start=window,
                                  count=10, sum_value=1.0, max_value=0.3)
            db.session.add(row)
        db.session.commit()
        results = get_metrics(name="cross_test", since_seconds=3600)
        self.assertEqual(results[0]["count"], 20)

    def test_since_seconds_excludes_old_windows(self):
        now = _window_start(datetime.datetime.utcnow())
        old = now - datetime.timedelta(hours=2)
        for window, count in [(now, 5), (old, 99)]:
            db.session.add(MetricAggregate(
                metric_name="cross_test", labels_key="",
                node="n1", window_start=window,
                count=count, sum_value=0.0, max_value=0.0))
        db.session.commit()
        # Default 1h window must skip the 2h-old row.
        results = get_metrics(name="cross_test", since_seconds=3600)
        self.assertEqual(results[0]["count"], 5)


class CleanupTest(MyTestCase):
    """``cleanup_old_metrics`` deletes rows older than the cutoff."""

    def setUp(self):
        _wipe_metrics()

    def test_cleanup_drops_only_old_rows(self):
        now = datetime.datetime.utcnow()
        old = now - datetime.timedelta(days=2)
        recent = now - datetime.timedelta(minutes=10)
        for window in (old, recent):
            db.session.add(MetricAggregate(
                metric_name="cleanup_test", labels_key="",
                node="n1", window_start=window,
                count=1, sum_value=0.0, max_value=0.0))
        db.session.commit()
        deleted = cleanup_old_metrics(older_than_seconds=86400)  # 24h
        self.assertEqual(deleted, 1)
        rows = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "cleanup_test")
        ).scalars().all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].window_start, recent)


class RaceToleranceTest(MyTestCase):
    """``_get_or_create_row`` recovers from a concurrent insert."""

    def setUp(self):
        _wipe_metrics()

    def test_unique_violation_falls_back_to_existing_row(self):
        # Simulate the race window: another worker's row is already in place
        # at flush time. We expect _get_or_create_row to roll back its INSERT
        # and refetch the winning row.
        now = _window_start(datetime.datetime.utcnow())
        existing = MetricAggregate(metric_name="race_test", labels_key="",
                                   node="", window_start=now,
                                   count=11, sum_value=1.1, max_value=0.5)
        db.session.add(existing)
        db.session.commit()

        # The path that handles the IntegrityError is exercised when the
        # SELECT inside _get_or_create_row misses despite the row existing.
        # We simulate that by patching the first SELECT to return None.
        from privacyidea.lib import metrics as metrics_mod
        real_execute = db.session.execute
        first_call = {"done": False}

        def selective_execute(stmt, *args, **kwargs):
            # Force the *first* SELECT inside the helper to return None so
            # that the INSERT path runs and trips the unique constraint.
            if not first_call["done"]:
                first_call["done"] = True

                class _NullScalarResult:
                    def scalar_one_or_none(self_inner):
                        return None
                return _NullScalarResult()
            return real_execute(stmt, *args, **kwargs)

        with patch.object(db.session, "execute", side_effect=selective_execute):
            row = metrics_mod._get_or_create_row("race_test", "", "", now)
        # Refetched the existing row, did not create a duplicate.
        self.assertEqual(row.count, 11)

        rows = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "race_test")
        ).scalars().all()
        self.assertEqual(len(rows), 1)


class FailureSafetyTest(MyTestCase):
    """``observe`` and ``inc`` must never raise."""

    def setUp(self):
        _wipe_metrics()

    def test_observe_swallows_db_errors(self):
        with patch.object(metrics, "_get_or_create_row",
                          side_effect=RuntimeError("db gone")):
            # Should not raise even though the substrate explodes.
            observe("safe_test", 0.1)

    def test_inc_swallows_db_errors(self):
        with patch.object(metrics, "_get_or_create_row",
                          side_effect=RuntimeError("db gone")):
            inc("safe_test")
