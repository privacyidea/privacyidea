.. _taskmodule_metricscleanup:

MetricsCleanup
--------------

The ``MetricsCleanup`` task module is a :ref:`periodic_tasks` that removes
aged-out rows from the ``metric_aggregate`` table. This table stores the
pre-aggregated timing and delivery counters that back the *Resolver Timing* and
*Notification Delivery* panels on the :ref:`dashboard`.

The dashboard panels read only the most recent window (the last hour by
default), so older rows are dead weight. Without this task the table grows
unbounded. A **daily** cadence is recommended, matching the natural rhythm of
the 24h retention; each run is a single indexed ``DELETE``.

Options
~~~~~~~

**older_than_hours**

    Delete metric rows whose ``window_start`` is older than this many hours.
    Default ``24``. Values below ``1`` are clamped to ``1`` so that the
    in-progress 5-minute window is never wiped.

.. note:: If you do not want to record metrics at all, set
   ``PI_NO_INTERNAL_METRICS = True`` in :ref:`cfgfile` (see
   :ref:`picfg_metrics_health`). The table then stays empty and this task has
   nothing to do, but it remains safe to schedule.
