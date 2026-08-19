# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""In-process metrics module backed by the ``metric_aggregate`` table.

Two primitives:

* :func:`observe` - record a value (e.g. operation duration in seconds).
  Updates count / sum / max / histogram buckets for the active 5-minute window.
* :func:`inc` - increment a counter.

Reads via :func:`get_metrics` aggregate across nodes and time windows. Multi-node
setups partition writes by ``PI_NODE`` so workers don't contend on the same row.

While a request is handled, observations are aggregated in memory and written once
at teardown, so instrumenting a per-item loop costs one transaction per request
instead of one per item. See :func:`_request_metric_buffer`.

This module never raises out of ``observe``/``inc``: failing to record a metric
must not break the operation being measured. Errors are logged at debug level.
"""
import datetime
import functools
import hashlib
import json
import logging
import time

from sqlalchemy import case, select, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from privacyidea.lib.config import get_privacyidea_node
from privacyidea.lib.framework import get_app_config_value, get_request_local_store, is_request_context
from privacyidea.lib.lifecycle import register_finalizer
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


def _label_items(labels: dict | None) -> tuple:
    """Return the label set as a hashable tuple of sorted (key, value) pairs.

    Buffered samples are grouped by this instead of by :py:func:`_labels_key`, so the
    JSON serialization runs once per row at flush time rather than once per sample.
    """
    if not labels:
        return ()
    return tuple(sorted(labels.items()))


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


def _utc_now() -> datetime.datetime:
    # Naive UTC datetime. The metric_aggregate.window_start column is
    # DateTime(timezone=False); keep everything we compare against it naive.
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _window_start(now: datetime.datetime) -> datetime.datetime:
    epoch = int(now.replace(tzinfo=datetime.timezone.utc).timestamp())
    bucket_epoch = epoch - (epoch % WINDOW_SECONDS)
    return datetime.datetime.fromtimestamp(bucket_epoch, tz=datetime.timezone.utc).replace(tzinfo=None)


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


def _increment_row(session: Session, metric_name: str, labels_hash: str, node: str,
                   window: datetime.datetime, aggregate: dict) -> int:
    """Add an aggregate to an existing row with one UPDATE. Returns the rows matched.

    The increments are computed by the database (``count = count + n``), not read into
    Python and written back, so several workers sharing a row can't overwrite each
    other's samples. ``max_value`` uses a portable CASE rather than ``GREATEST``.

    :return: 1 if the row existed, 0 if it still has to be inserted
    """
    increments = {
        "count": MetricAggregate.count + aggregate["count"],
        "sum_value": MetricAggregate.sum_value + aggregate["sum_value"],
        "max_value": case((MetricAggregate.max_value < aggregate["max_value"], aggregate["max_value"]),
                          else_=MetricAggregate.max_value),
    }
    for index, (_boundary, column) in enumerate(_BUCKETS):
        if aggregate["buckets"][index]:
            increments[column] = getattr(MetricAggregate, column) + aggregate["buckets"][index]
    stmt = update(MetricAggregate).where(
        MetricAggregate.metric_name == metric_name,
        MetricAggregate.labels_hash == labels_hash,
        MetricAggregate.node == node,
        MetricAggregate.window_start == window,
    ).values(**increments)
    # The session holds no instances of the row, so there is nothing to synchronize and
    # the CASE expression would only force SQLAlchemy into an extra SELECT.
    result = session.execute(stmt, execution_options={"synchronize_session": False})
    return result.rowcount


def _apply_aggregate(session: Session, metric_name: str, labels_key: str, node: str,
                     window: datetime.datetime, aggregate: dict) -> None:
    """Add an aggregate to its row, inserting the row if this is its first sample."""
    labels_hash = _labels_hash(labels_key)
    if _increment_row(session, metric_name, labels_hash, node, window, aggregate):
        return
    try:
        # A savepoint, so that losing the insert to another worker does not roll back the
        # aggregates of the other rows this transaction has already applied.
        with session.begin_nested():
            session.add(MetricAggregate(
                metric_name=metric_name, labels_key=labels_key,
                labels_hash=labels_hash, node=node, window_start=window,
                count=aggregate["count"], sum_value=aggregate["sum_value"],
                max_value=aggregate["max_value"],
                **{column: aggregate["buckets"][index]
                   for index, (_boundary, column) in enumerate(_BUCKETS)},
            ))
    except IntegrityError:
        # Race: another worker inserted the same (metric, labels, node, window) row
        # between our UPDATE and our INSERT. The savepoint took the failed insert with
        # it, so the aggregate can simply be added to the row that won.
        # Other exceptions (missing table, connection failure, ...) bubble up to the
        # caller's try/except in observe()/inc()/_flush_metric_buffer().
        _increment_row(session, metric_name, labels_hash, node, window, aggregate)


_BUFFER_KEY = "metric_observations"


def _request_metric_buffer() -> dict | None:
    """Return the request-local buffer that collects observations until teardown.

    Writing a metric row costs a transaction, so an operation instrumented inside a
    per-item loop (the resolvers report one timing per user) would pay for one commit
    per item, and an enclosing timing would even measure those commits. Instead the
    observations of a request are aggregated here - all observations sharing a metric
    name, label set and window collapse into a single row update - and written by one
    finalizer at the end of the request.

    Returns ``None`` outside a request: no teardown would run there, so the caller has
    to write its observation through immediately.

    The buffer is only written at teardown, so a request whose worker is killed before
    that (a uWSGI harakiri on a request hung in a resolver, a worker recycle) takes its
    samples with it - the very requests an operator wants to see. A size-based early
    flush would not help there: what such a request loses is the samples of the ops it
    already finished, and the label sets of a single request are far too few to reach
    any sensible size limit. Recording the pathological request needs the timing to be
    written before the op returns, which is what costs a transaction per sample.
    """
    if not is_request_context():
        return None
    store = get_request_local_store()
    if _BUFFER_KEY not in store:
        store[_BUFFER_KEY] = {}
        register_finalizer(_flush_metric_buffer)
    return store[_BUFFER_KEY]


def _flush_metric_buffer() -> None:
    """Write the observations buffered during this request. Registered as a finalizer."""
    try:
        buffered_observations = get_request_local_store().pop(_BUFFER_KEY, None)
        if buffered_observations:
            _write_observations(buffered_observations)
    except Exception as e:
        log.debug(f"metrics: flushing the buffered observations failed: {e}")


def _write_observations(observations: dict) -> None:
    """Apply aggregated observations to their rows in one transaction.

    The write happens on its own session and commit so it can't piggyback on (or be
    rolled back by) the caller's transaction.

    The rows are visited in sorted key order. Workers of the same node share the rows of
    a window, so they have to take the row locks in one agreed order or two overlapping
    flushes can deadlock and lose a whole request's samples.

    :param observations: maps (metric name, label items, node, window) to an aggregate
    """
    session = _metric_session()
    try:
        for key in sorted(observations):
            name, label_items, node, window = key
            _apply_aggregate(session, name, _labels_key(dict(label_items)), node, window,
                             observations[key])
        session.commit()
    finally:
        session.close()


def _record(name: str, labels: dict | None, value: float | None = None, count: int = 1) -> None:
    """Add one sample to the buffer, or write it through when there is no request to flush it.

    :param name: the metric name
    :param labels: the label set of this sample
    :param value: the observed value in seconds, or None for a counter
    :param count: how much the sample increments the count by
    """
    key = (name, _label_items(labels), get_privacyidea_node() or "", _window_start(_utc_now()))
    buffer = _request_metric_buffer()
    observations = buffer if buffer is not None else {}
    aggregate = observations.setdefault(key, {"count": 0, "sum_value": 0.0, "max_value": 0.0,
                                              "buckets": [0] * len(_BUCKETS)})
    aggregate["count"] += count
    if value is not None:
        aggregate["sum_value"] += float(value)
        aggregate["max_value"] = max(aggregate["max_value"], float(value))
        # Count the sample in every bucket whose upper bound is >= value (cumulative).
        for index, (boundary, _column) in enumerate(_BUCKETS):
            if value <= boundary:
                aggregate["buckets"][index] += 1
    if buffer is None:
        _write_observations(observations)


def observe(name: str, value: float, labels: dict | None = None) -> None:
    """Record a numeric observation (seconds for timings) for histogram ``name``.

    Updates count / sum / max plus the cumulative bucket whose upper bound
    contains ``value``. During a request the update is buffered and written at
    teardown, otherwise it is written immediately.
    """
    try:
        if _metrics_disabled():
            return
        _record(name, labels, value=value)
    except Exception as e:
        log.debug(f"metrics.observe({name!r}) failed: {e}")


def inc(name: str, labels: dict | None = None, by: int = 1) -> None:
    """Increment a counter by ``by`` (default 1).

    Buffered and isolated exactly like :func:`observe`.
    """
    try:
        if _metrics_disabled():
            return
        _record(name, labels, count=by)
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
    cutoff = _utc_now() - datetime.timedelta(seconds=since_seconds)
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
            # Ordered [upper_bound_seconds, cumulative_count] pairs. Exposed so a
            # caller that rolls several rows into one (e.g. all ops of a resolver)
            # can sum the histograms and compute a correct combined percentile,
            # instead of incorrectly taking the max of the per-row percentiles.
            "buckets": [[boundary, g["buckets"][col]] for boundary, col in _BUCKETS],
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
    cutoff = _utc_now() - datetime.timedelta(seconds=older_than_seconds)
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
