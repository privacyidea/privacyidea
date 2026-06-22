# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Periodic task that drops aged-out rows from ``metric_aggregate``.

Each run deletes rows whose ``window_start`` is older than ``older_than_hours``
hours (default 24). A daily cadence is recommended, matching the natural rhythm
of the 24h retention; each run is a single indexed ``DELETE``.
"""
import logging

from privacyidea.lib import _
from privacyidea.lib.metrics import cleanup_old_metrics
from privacyidea.lib.task.base import BaseTask

log = logging.getLogger(__name__)


class MetricsCleanupTask(BaseTask):
    identifier = "MetricsCleanup"
    description = "Delete metric_aggregate rows older than the configured retention."

    @property
    def options(self):
        return {
            "older_than_hours": {
                "type": "int",
                "description": _("Delete metric rows whose window_start is older "
                                 "than this many hours. Default 24."),
            }
        }

    def do(self, params):
        try:
            hours = int(params.get("older_than_hours") or 24)
        except (TypeError, ValueError):
            hours = 24
        # Clamp to >=1h so the in-progress 5-minute window is never wiped.
        # Same protection as the on-demand /system/metricscleanup endpoint.
        if hours < 1:
            hours = 1
        deleted = cleanup_old_metrics(older_than_seconds=hours * 3600)
        log.info(f"MetricsCleanup deleted {deleted} metric_aggregate row(s) "
                 f"older than {hours}h.")
        return True
