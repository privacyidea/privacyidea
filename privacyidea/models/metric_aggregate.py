# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pre-aggregated metric storage used by ``privacyidea.lib.metrics``.

One row per ``(metric_name, labels_key, node, window_start)``. The 5-minute
window keeps row count bounded; rolling-window reads sum the last N windows.
"""
import hashlib
from datetime import datetime
from sqlalchemy import (BigInteger, DateTime, Float, Integer, Sequence,
                        String, Text, Unicode, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, validates

from privacyidea.models import db


class MetricAggregate(db.Model):
    """Rolling counter / histogram bucket for a metric in a 5-minute window.

    For counters only ``count`` is used. For histograms ``count``, ``sum_value``,
    ``max_value`` and the ``bucket_le_*`` columns hold the sample distribution.
    Buckets follow the prom-style ``_bucket{le="..."}`` convention: each
    column stores the count of observations whose value is <= that boundary
    (inclusive, cumulative).
    """
    __tablename__ = "metric_aggregate"

    id: Mapped[int] = mapped_column(Integer, Sequence("metric_aggregate_seq"),
                                    primary_key=True)
    metric_name: Mapped[str] = mapped_column(Unicode(128), nullable=False, index=True)
    # JSON object with sorted keys (compact separators), e.g.
    # ``{"gateway":"firebase","result":"ok"}``. Empty string when no labels.
    # Encoded by ``privacyidea.lib.metrics._labels_key``.
    labels_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # SHA-256 hex digest of labels_key. Used by the unique constraint so the
    # composite index has a fixed-size column (labels_key itself can grow
    # past MySQL's 3072-byte composite-index limit).
    labels_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    node: Mapped[str] = mapped_column(Unicode(255), nullable=False, default="")
    # Naive UTC datetime, truncated to the 5-minute window boundary.
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=False),
                                                   nullable=False, index=True)

    count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sum_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Bucket suffixes are upper bounds in milliseconds. Each column stores
    # the count of observations whose value (in seconds) is <= that bound.
    # Anything above the largest bucket falls into the implicit ``+inf``
    # bucket (= ``count`` minus the highest bucket value).
    bucket_le_50ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bucket_le_100ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bucket_le_150ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bucket_le_200ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bucket_le_250ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bucket_le_500ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bucket_le_1s: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bucket_le_2s: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bucket_le_5s: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("metric_name", "labels_hash", "node",
                                       "window_start", name="metricagg_uix"),)

    @validates("labels_key")
    def _sync_labels_hash(self, _key, value):
        # Keep labels_hash in lockstep with labels_key so callers (including
        # tests that construct rows directly) don't have to set both.
        self.labels_hash = hashlib.sha256((value or "").encode("utf-8")).hexdigest()
        return value
