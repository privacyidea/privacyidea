# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ``privacyidea.lib.task.metricscleanup.MetricsCleanupTask``."""
import datetime

from sqlalchemy import select

from privacyidea.lib.metrics import _utc_now
from privacyidea.lib.task.metricscleanup import MetricsCleanupTask
from privacyidea.models import db
from privacyidea.models.metric_aggregate import MetricAggregate
from tests.base import MyTestCase


def _add_row(window: datetime.datetime, count: int = 1) -> None:
    db.session.add(MetricAggregate(metric_name="cleanup_test", labels_key="",
                                   node="n1", window_start=window,
                                   count=count, sum_value=0.0, max_value=0.0))


class MetricsCleanupTaskTest(MyTestCase):
    """Periodic-task surface: option schema, default cutoff, custom cutoff, empty case."""

    def setUp(self):
        db.session.query(MetricAggregate).delete()
        db.session.commit()

    def test_options_schema_advertises_int_field(self):
        task = MetricsCleanupTask(config=None)
        opts = task.options
        self.assertIn("older_than_hours", opts)
        self.assertEqual(opts["older_than_hours"]["type"], "int")
        # Description must exist - the form template uses it as the field's help text.
        self.assertTrue(opts["older_than_hours"].get("description"))

    def test_do_default_drops_rows_older_than_24h(self):
        now = _utc_now()
        _add_row(now - datetime.timedelta(hours=2))            # recent, keep
        _add_row(now - datetime.timedelta(hours=23, minutes=30))  # just inside, keep
        _add_row(now - datetime.timedelta(hours=25))           # past cutoff, drop
        _add_row(now - datetime.timedelta(days=10))            # very old, drop
        db.session.commit()

        task = MetricsCleanupTask(config=None)
        self.assertTrue(task.do({}))

        remaining = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "cleanup_test")
        ).scalars().all()
        self.assertEqual(len(remaining), 2)

    def test_do_honors_older_than_hours_option(self):
        # A 1h cutoff should drop everything older than an hour, even rows that
        # the default 24h cutoff would keep.
        now = _utc_now()
        _add_row(now - datetime.timedelta(minutes=30))   # keep
        _add_row(now - datetime.timedelta(hours=2))      # drop with older_than_hours=1
        db.session.commit()

        task = MetricsCleanupTask(config=None)
        self.assertTrue(task.do({"older_than_hours": 1}))

        remaining = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "cleanup_test")
        ).scalars().all()
        self.assertEqual(len(remaining), 1)

    def test_do_with_string_option_value(self):
        # The DB stores option values as Unicode regardless of declared type, so do()
        # must coerce strings - this guards the int(...) coercion in the task body.
        now = _utc_now()
        _add_row(now - datetime.timedelta(hours=5))
        db.session.commit()

        task = MetricsCleanupTask(config=None)
        self.assertTrue(task.do({"older_than_hours": "2"}))

        remaining = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "cleanup_test")
        ).scalars().all()
        self.assertEqual(remaining, [])

    def test_do_with_invalid_option_falls_back_to_default(self):
        # Garbage in the option value must not crash the task; the body has an
        # except (TypeError, ValueError) that drops back to 24h.
        now = _utc_now()
        _add_row(now - datetime.timedelta(hours=2))   # keep under default 24h
        db.session.commit()

        task = MetricsCleanupTask(config=None)
        self.assertTrue(task.do({"older_than_hours": "not-an-int"}))

        remaining = db.session.execute(
            select(MetricAggregate).where(MetricAggregate.metric_name == "cleanup_test")
        ).scalars().all()
        self.assertEqual(len(remaining), 1)

    def test_do_on_empty_table_is_a_noop(self):
        task = MetricsCleanupTask(config=None)
        self.assertTrue(task.do({}))
        self.assertEqual(
            db.session.execute(select(MetricAggregate)).scalars().all(),
            [])
