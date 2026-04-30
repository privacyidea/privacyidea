# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Periodic task that drops aged-out rows from ``metric_aggregate``.

Recommended cadence: every hour. Each run deletes rows whose ``window_start``
is older than ``older_than_hours`` hours (default 24).
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
        deleted = cleanup_old_metrics(older_than_seconds=hours * 3600)
        log.info(f"MetricsCleanup deleted {deleted} metric_aggregate row(s) "
                 f"older than {hours}h.")
        return True
