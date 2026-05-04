# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""In-process metrics module backed by the ``metric_aggregate`` table.

Two primitives:

* :func:`observe` - record a value (e.g. operation duration in seconds).
  Updates count / sum / max / histogram buckets for the active 5-minute window.
* :func:`inc` - increment a counter.

Reads via :func:`get_metrics` aggregate across nodes and time windows. Multi-node
setups partition writes by ``PI_NODE`` so workers don't contend on the same row.

This module never raises out of ``observe``/``inc``: failing to record a metric
must not break the operation being measured. Errors are logged at debug level.
"""
import datetime
import functools
import hashlib
import json
import logging
import time

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from privacyidea.lib.config import get_privacyidea_node
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.utils import is_true
from privacyidea.models import db
from privacyidea.models.metric_aggregate import MetricAggregate

log = logging.getLogger(__name__)


def _metrics_disabled() -> bool:
    """Operator kill switch. Set ``PI_NO_INTERNAL_METRICS = True`` in pi.cfg to
    short-circuit every ``observe`` / ``inc`` call.

    Reads stay open (the panels just show no data). The cleanup task still works.
    """
    return is_true(get_app_config_value("PI_NO_INTERNAL_METRICS", False))

WINDOW_SECONDS = 300            # 5-minute aggregation buckets.
DEFAULT_QUERY_WINDOW = 3600     # Reads return the last hour by default.
RETENTION_SECONDS = 86400       # Cleanup deletes rows older than 24h.

# Bucket boundaries in seconds, paired with the column they map to.
# Order matters: ascending. ``+inf`` is implicit (= total ``count``).
#
# The set is tuned for the resolver-timing use case: we don't care to
# distinguish a 1 ms SQL hit from a 49 ms LDAP search (both are "fine"),
# but we do care about the 50-250 ms zone where HTTP-based resolvers and
# slow LDAP calls live. Anything above 5 s is "broken" - one bucket is
# enough.
#
# When changing this list, also update:
#   - the column declarations in ``models/metric_aggregate.py``
#   - the migration in ``migrations/versions/c2d3e4f5a6b7_metric_aggregate.py``
#   - the ``Bucket boundaries: ...`` text in the p95 info tooltip in
#     ``static/components/dashboard/views/dashboard.html`` (the only place
#     the user-facing list of boundaries is enumerated).
_BUCKETS = (
    (0.05,   "bucket_le_50ms"),
    (0.1,    "bucket_le_100ms"),
    (0.15,   "bucket_le_150ms"),
    (0.2,    "bucket_le_200ms"),
    (0.25,   "bucket_le_250ms"),
    (0.5,    "bucket_le_500ms"),
    (1.0,    "bucket_le_1s"),
    (2.0,    "bucket_le_2s"),
    (5.0,    "bucket_le_5s"),
)


def _labels_key(labels: dict | None) -> str:
    # JSON with sorted keys gives a lossless round-trip even when label values
    # contain commas, equals signs, quotes or unicode (gateway and resolver
    # identifiers are unrestricted Unicode(255), so a hand-rolled k=v,k=v
    # encoding would collide on those characters).
    if not labels:
        return ""
    return json.dumps({k: labels[k] for k in sorted(labels)},
                      separators=(",", ":"), ensure_ascii=False)


def _parse_labels_key(labels_key: str) -> dict:
    if not labels_key:
        return {}
    try:
        return json.loads(labels_key)
    except (TypeError, ValueError):
        return {}


def _labels_hash(labels_key: str) -> str:
    # Fixed-size SHA-256 hex digest used by the unique constraint, so the
    # composite index doesn't grow with labels_key length.
    return hashlib.sha256(labels_key.encode("utf-8")).hexdigest()


def _window_start(now: datetime.datetime) -> datetime.datetime:
    epoch = int(now.replace(tzinfo=datetime.timezone.utc).timestamp())
    bucket_epoch = epoch - (epoch % WINDOW_SECONDS)
    return datetime.datetime.utcfromtimestamp(bucket_epoch)


# Metric writes happen on a dedicated session so they cannot piggyback on
# the caller's transaction (committing it early) and cannot be rolled back
# by a later failure in the caller. The session is bound to the same engine
# as ``db.session``, so reads through ``db.session`` see committed writes.
_metric_sessionmaker: sessionmaker | None = None


def _metric_session():
    """Return a fresh SQLAlchemy session for an isolated metric write."""
    global _metric_sessionmaker
    if _metric_sessionmaker is None:
        _metric_sessionmaker = sessionmaker(bind=db.engine, expire_on_commit=False)
    return _metric_sessionmaker()


def _get_or_create_row(session, metric_name: str, labels_key: str,
                       node: str, window: datetime.datetime) -> MetricAggregate:
    labels_hash = _labels_hash(labels_key)
    stmt = select(MetricAggregate).where(
        MetricAggregate.metric_name == metric_name,
        MetricAggregate.labels_hash == labels_hash,
        MetricAggregate.node == node,
        MetricAggregate.window_start == window,
    )
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        row = MetricAggregate(
            metric_name=metric_name, labels_key=labels_key,
            labels_hash=labels_hash, node=node, window_start=window,
            count=0, sum_value=0.0, max_value=0.0,
        )
        session.add(row)
        try:
            session.flush()
        except IntegrityError:
            # Race: another worker inserted the same (metric, labels, node,
            # window) row between our SELECT and INSERT. Roll back the failed
            # insert and re-fetch so the caller updates the existing row.
            # Other exceptions (missing table, connection failure, ...) bubble
            # up to the caller's try/except in observe()/inc().
            session.rollback()
            row = session.execute(stmt).scalar_one()
    return row


def observe(name: str, value: float, labels: dict | None = None) -> None:
    """Record a numeric observation (seconds for timings) for histogram ``name``.

    Updates count / sum / max plus the cumulative bucket whose upper bound
    contains ``value``. The write happens on its own session and commit so
    it can't piggyback on (or be rolled back by) the caller's transaction.
    """
    if _metrics_disabled():
        return
    try:
        node = get_privacyidea_node() or ""
        labels_key = _labels_key(labels)
        window = _window_start(datetime.datetime.utcnow())
        session = _metric_session()
        try:
            row = _get_or_create_row(session, name, labels_key, node, window)
            row.count += 1
            row.sum_value = float(row.sum_value) + float(value)
            if value > row.max_value:
                row.max_value = float(value)
            # Increment every bucket whose upper bound is >= value (cumulative).
            for boundary, column in _BUCKETS:
                if value <= boundary:
                    setattr(row, column, getattr(row, column) + 1)
            session.commit()
        finally:
            session.close()
    except Exception as e:
        log.debug(f"metrics.observe({name!r}) failed: {e}")


def inc(name: str, labels: dict | None = None, by: int = 1) -> None:
    """Increment a counter by ``by`` (default 1).

    Same isolation guarantees as :func:`observe`: own session, own commit.
    """
    if _metrics_disabled():
        return
    try:
        node = get_privacyidea_node() or ""
        labels_key = _labels_key(labels)
        window = _window_start(datetime.datetime.utcnow())
        session = _metric_session()
        try:
            row = _get_or_create_row(session, name, labels_key, node, window)
            row.count += by
            session.commit()
        finally:
            session.close()
    except Exception as e:
        log.debug(f"metrics.inc({name!r}) failed: {e}")


def _percentile_from_buckets(buckets: dict, count: int, q: float) -> float | None:
    """Approximate quantile from prom-style cumulative bucket counts.

    Returns the upper bound of the first bucket whose cumulative count
    crosses ``q * count``. Returns ``None`` for an empty histogram.
    Resolution is limited by the bucket boundaries.
    """
    if not count:
        return None
    target = q * count
    for boundary, column in _BUCKETS:
        if buckets.get(column, 0) >= target:
            return boundary
    # Above the largest bucket boundary (5s) - the dashboard shows this as
    # the dash placeholder rather than an exact value.
    return None


def get_metrics(name: str | None = None, since_seconds: int = DEFAULT_QUERY_WINDOW) -> list:
    """Aggregate stored metric rows across nodes and windows.

    Returns a list of dicts, one per ``(metric_name, labels)`` group::

        {"metric": "ldap_op_duration_seconds",
         "labels": {"resolver": "openldap", "op": "bind"},
         "count": 120, "avg": 0.024, "p50": 0.025, "p95": 0.1,
         "max": 0.34, "since_seconds": 3600}
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=since_seconds)
    stmt = select(MetricAggregate).where(MetricAggregate.window_start >= cutoff)
    if name is not None:
        stmt = stmt.where(MetricAggregate.metric_name == name)
    # Read on the dedicated metric session: a request-bound ``db.session``
    # could already be in a REPEATABLE READ snapshot that predates a
    # just-committed metric write (visible on SQLite, hidden on MariaDB).
    session = _metric_session()
    try:
        rows = session.execute(stmt).scalars().all()
    finally:
        session.close()

    # Group by (metric_name, labels_key); fold over nodes and windows.
    groups: dict = {}
    for r in rows:
        key = (r.metric_name, r.labels_key)
        g = groups.setdefault(key, {
            "count": 0, "sum": 0.0, "max": 0.0,
            "buckets": {col: 0 for _, col in _BUCKETS},
        })
        g["count"] += r.count
        g["sum"] += float(r.sum_value)
        if r.max_value > g["max"]:
            g["max"] = float(r.max_value)
        for _, col in _BUCKETS:
            g["buckets"][col] += getattr(r, col)

    out = []
    for (metric_name, labels_key), g in groups.items():
        count = g["count"]
        avg = (g["sum"] / count) if count else None
        p50 = _percentile_from_buckets(g["buckets"], count, 0.50)
        p95 = _percentile_from_buckets(g["buckets"], count, 0.95)
        out.append({
            "metric": metric_name,
            "labels": _parse_labels_key(labels_key),
            "count": count,
            "avg": avg,
            "p50": p50,
            "p95": p95,
            "max": g["max"] if count else None,
            "since_seconds": since_seconds,
        })
    return out


def track_resolver_op(op_name: str):
    """Decorator that records a UserIdResolver public-method timing.

    Apply to the public methods of resolver subclasses (``getUserList``,
    ``get_user_info``, ``checkPass``, etc.). Records elapsed time under the
    ``resolver_op_duration_seconds`` histogram with labels
    ``{resolver, resolver_type, op}``.

    The decorator never raises; if metric recording fails the underlying
    method's return value is preserved.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            start = time.perf_counter()
            try:
                return func(self, *args, **kwargs)
            finally:
                try:
                    elapsed = time.perf_counter() - start
                    resolver_type = "unknown"
                    if hasattr(self, "getResolverType"):
                        try:
                            resolver_type = self.getResolverType() or "unknown"
                        except Exception as e:  # nosec B110 - degrade to "unknown"
                            log.debug(f"getResolverType() raised: {e}")
                    resolver_name = (getattr(self, "name", None)
                                     or getattr(self, "resolverId", None)
                                     or "?")
                    observe("resolver_op_duration_seconds", elapsed, {
                        "resolver": str(resolver_name),
                        "resolver_type": str(resolver_type),
                        "op": op_name,
                    })
                except Exception as e:  # nosec B110 - metrics must not affect resolver behavior
                    log.debug(f"track_resolver_op({op_name!r}) failed: {e}")
        return wrapper
    return decorator


def cleanup_old_metrics(older_than_seconds: int = RETENTION_SECONDS) -> int:
    """Delete metric rows older than ``older_than_seconds``. Returns row count."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=older_than_seconds)
    stmt = delete(MetricAggregate).where(MetricAggregate.window_start < cutoff)
    # Run on the dedicated metric session so the cleanup commit can't promote
    # unrelated pending writes in the caller's ``db.session``.
    session = _metric_session()
    try:
        result = session.execute(stmt)
        session.commit()
        return result.rowcount or 0
    finally:
        session.close()
