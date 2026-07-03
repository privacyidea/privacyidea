#!/usr/bin/env python3
# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
"""
Cron runner for privacyIDEA Docker deployments.

Runs maintenance tasks on a schedule without requiring crond or root.
This script is invoked by entrypoint.sh when PI_CRON_MODE=true.

Every task is a single entry in the TASKS list below: a name, an enable flag,
a schedule, and the command to run. To add a maintenance task in the future
(e.g. cleaning up a new table), append one Task(...) entry and read whatever
PI_CRON_* environment variables it needs — nothing else in this file changes.

NOTE: privacyIDEA's own periodic-task modules (EventCounter, SimpleStats,
MetricsCleanup, ...) are configured in the web UI, not here. They are executed
by the "periodic tasks" entry below (privacyidea-cron run_scheduled) whenever
they target this container's node name (PRIVACYIDEA_PI_NODE, "pi-cron" in the
bundled compose). So a new metrics/table cleanup that ships as a periodic-task
module needs no change here — just configure it in the UI for node pi-cron.

Configuration via environment variables (all optional):

  PI_CRON_PERIODIC_TASKS      Enable/disable privacyidea-cron run_scheduled (default: true)

  PI_CRON_CHALLENGE_CLEANUP   Enable/disable challenge cleanup (default: true)

  PI_CRON_USERCACHE_CLEANUP   Enable/disable usercache cleanup (default: true; a
                              no-op unless the user cache is enabled)
  PI_CRON_USERCACHE_HOUR      Hour of day to run usercache cleanup (default: 4)
  PI_CRON_USERCACHE_INTERVAL  Run usercache cleanup every interval instead, e.g.
                              "12h" (takes precedence over PI_CRON_USERCACHE_HOUR)

  PI_CRON_AUDIT_ROTATE        Enable/disable audit rotation (default: true)
  PI_CRON_AUDIT_HOUR          Hour of day to run audit rotation, 0-23 (default: 2)
  PI_CRON_AUDIT_INTERVAL      Run every interval instead of at a fixed hour, e.g.
                              "6h", "90m", "2d". Takes precedence over
                              PI_CRON_AUDIT_HOUR if both are set.
  PI_CRON_AUDIT_HIGHWATERMARK Delete old entries when count exceeds this (default: 50000)
  PI_CRON_AUDIT_LOWWATERMARK  Keep this many entries after rotation (default: 25000)
  PI_CRON_AUDIT_AGE           Delete entries older than N days instead of using
                              watermarks. When set, overrides high/lowwatermark.
  PI_CRON_AUDIT_CHUNKSIZE     Delete in chunks to avoid long locks (default: unset)
"""
import datetime
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


def _int(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        print(f"[pi-cron] WARNING: {name}={val!r} is not a valid integer, using default {default}", flush=True)
        return default


def _duration_minutes(name: str, default_minutes: int) -> int:
    """Parse a duration env var into minutes. Accepts e.g. "90m", "6h", "2d";
    a bare number is minutes. Falls back to the default on anything unparseable."""
    val = os.environ.get(name)
    if not val:
        return default_minutes
    match = re.fullmatch(r"(\d+)\s*([mhd]?)", val.strip().lower())
    if not match:
        print(f"[pi-cron] WARNING: {name}={val!r} is not a duration, using {default_minutes}m", flush=True)
        return default_minutes
    return int(match.group(1)) * {"": 1, "m": 1, "h": 60, "d": 1440}[match.group(2)]


@dataclass
class Schedule:
    """When a task is due, plus a human-readable description for the log."""
    due: Callable[[datetime.datetime], bool]
    description: str


def every_minute() -> Schedule:
    return Schedule(lambda now: True, "every minute")


def hourly() -> Schedule:
    return Schedule(lambda now: now.minute == 0, "hourly")


def daily_at(hour: int) -> Schedule:
    return Schedule(lambda now: now.hour == hour and now.minute == 0, f"daily at {hour:02d}:00")


def every(interval_minutes: int) -> Schedule:
    """Fire once per interval, measured from the runner's start (not the wall
    clock). The first fire is one full interval after startup, not immediately —
    so a restart does not re-trigger a heavy task."""
    state = {"last": None}

    def due(now: datetime.datetime) -> bool:
        if state["last"] is None:
            state["last"] = now
            return False
        if (now - state["last"]).total_seconds() >= interval_minutes * 60:
            state["last"] = now
            return True
        return False

    return Schedule(due, f"every {interval_minutes} min")


def scheduled_from_env(interval_var: str, hour_var: str, default_hour: int) -> Schedule:
    """Resolve a schedule from two optional env vars, evaluating only one:
    an explicit interval (e.g. "6h") takes precedence over a daily hour-of-day.
    With neither set, defaults to daily at `default_hour`."""
    interval = os.environ.get(interval_var)
    hour = os.environ.get(hour_var)
    if interval and hour:
        print(f"[pi-cron] WARNING: both {interval_var} and {hour_var} are set; "
              f"using {interval_var}={interval!r}", flush=True)
    if interval:
        return every(_duration_minutes(interval_var, 1440))   # bad value → daily
    return daily_at(_int(hour_var, default_hour))


@dataclass
class Task:
    """A scheduled maintenance task. `build` returns the command to run."""
    name: str
    enabled: bool
    schedule: Schedule
    build: Callable[[], list[str]]


def audit_rotate_cmd() -> list[str]:
    cmd = ["pi-manage", "audit", "rotate"]
    age = os.environ.get("PI_CRON_AUDIT_AGE", "")            # days; empty = use watermarks
    chunksize = os.environ.get("PI_CRON_AUDIT_CHUNKSIZE", "")
    if age:
        cmd += ["--age", age]
    else:
        cmd += ["-hw", str(_int("PI_CRON_AUDIT_HIGHWATERMARK", 50000)),
                "-lw", str(_int("PI_CRON_AUDIT_LOWWATERMARK", 25000))]
    if chunksize:
        cmd += ["--chunksize", chunksize]
    return cmd


# The full schedule. Add a maintenance task by appending one Task(...) here.
# Schedules: every_minute(), hourly(), daily_at(hour), every(minutes), or
# scheduled_from_env(interval_var, hour_var, default_hour) to let the operator
# pick either an interval or a fixed hour with one env var.
# Example (once a corresponding pi-manage command exists):
#   Task("metrics cleanup",
#        _bool("PI_CRON_METRICS_CLEANUP", False),
#        every(_duration_minutes("PI_CRON_METRICS_INTERVAL", 60)),
#        lambda: ["pi-manage", "metrics", "cleanup", "--age", os.environ.get("PI_CRON_METRICS_AGE", "365")]),
TASKS = [
    Task("periodic tasks",
         _bool("PI_CRON_PERIODIC_TASKS", True),
         every_minute(),
         lambda: ["privacyidea-cron", "run_scheduled", "--cron"]),
    Task("challenge cleanup",
         _bool("PI_CRON_CHALLENGE_CLEANUP", True),
         hourly(),
         lambda: ["pi-manage", "config", "challenge", "cleanup"]),
    Task("audit rotate",
         _bool("PI_CRON_AUDIT_ROTATE", True),
         scheduled_from_env("PI_CRON_AUDIT_INTERVAL", "PI_CRON_AUDIT_HOUR", 2),
         audit_rotate_cmd),
    Task("usercache cleanup",
         _bool("PI_CRON_USERCACHE_CLEANUP", True),
         scheduled_from_env("PI_CRON_USERCACHE_INTERVAL", "PI_CRON_USERCACHE_HOUR", 4),
         lambda: ["privacyidea-usercache-cleanup"]),
]


def run(cmd: list[str]) -> None:
    print(f"[pi-cron] {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[pi-cron] WARNING: exited with code {result.returncode}", file=sys.stderr, flush=True)


def main() -> None:
    print("[pi-cron] Starting. Scheduled tasks:", flush=True)
    for task in TASKS:
        state = "enabled" if task.enabled else "disabled"
        print(f"[pi-cron]   {task.name:<18} {state:<8} ({task.schedule.description})", flush=True)

    last_minute = -1
    while True:
        now = datetime.datetime.now()
        if now.minute != last_minute:
            last_minute = now.minute
            for task in TASKS:
                if task.enabled and task.schedule.due(now):
                    run(task.build())

        # Sleep until just past the start of the next minute.
        time.sleep(61 - datetime.datetime.now().second)


if __name__ == "__main__":
    main()
