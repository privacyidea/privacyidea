#!/usr/bin/env python3
"""
Cron runner for privacyIDEA Docker deployments.

Runs maintenance tasks on a schedule without requiring crond or root.
This script is invoked by entrypoint.sh when PI_CRON_MODE=true.

Configuration via environment variables (all optional):

  PI_CRON_AUDIT_ROTATE        Enable/disable audit rotation (default: true)
  PI_CRON_AUDIT_HOUR          Hour of day to run audit rotation, 0-23 (default: 2)
  PI_CRON_AUDIT_HIGHWATERMARK Delete old entries when count exceeds this (default: 50000)
  PI_CRON_AUDIT_LOWWATERMARK  Keep this many entries after rotation (default: 25000)
  PI_CRON_AUDIT_AGE           Delete entries older than N days instead of using
                              watermarks. When set, overrides high/lowwatermark.
  PI_CRON_AUDIT_CHUNKSIZE     Delete in chunks to avoid long locks (default: unset)

  PI_CRON_CHALLENGE_CLEANUP   Enable/disable challenge cleanup (default: true)
  PI_CRON_PERIODIC_TASKS      Enable/disable pi-manage-cron run_scheduled (default: true)
"""
import datetime
import os
import subprocess
import sys
import time


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


# ── Configuration ─────────────────────────────────────────────────────────────

ENABLE_AUDIT_ROTATE      = _bool("PI_CRON_AUDIT_ROTATE", True)
AUDIT_HOUR               = _int("PI_CRON_AUDIT_HOUR", 2)
AUDIT_HIGHWATERMARK      = _int("PI_CRON_AUDIT_HIGHWATERMARK", 50000)
AUDIT_LOWWATERMARK       = _int("PI_CRON_AUDIT_LOWWATERMARK", 25000)
AUDIT_AGE                = os.environ.get("PI_CRON_AUDIT_AGE", "")       # days as string, empty = use watermarks
AUDIT_CHUNKSIZE          = os.environ.get("PI_CRON_AUDIT_CHUNKSIZE", "") # empty = no chunking

ENABLE_CHALLENGE_CLEANUP = _bool("PI_CRON_CHALLENGE_CLEANUP", True)
ENABLE_PERIODIC_TASKS    = _bool("PI_CRON_PERIODIC_TASKS", True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str]) -> None:
    print(f"[pi-cron] {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(
            f"[pi-cron] WARNING: exited with code {result.returncode}",
            file=sys.stderr,
            flush=True,
        )


def audit_rotate_cmd() -> list[str]:
    cmd = ["pi-manage", "audit", "rotate"]
    if AUDIT_AGE:
        cmd += ["--age", AUDIT_AGE]
    else:
        cmd += ["-hw", str(AUDIT_HIGHWATERMARK), "-lw", str(AUDIT_LOWWATERMARK)]
    if AUDIT_CHUNKSIZE:
        cmd += ["--chunksize", AUDIT_CHUNKSIZE]
    return cmd


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("[pi-cron] Starting. Configuration:", flush=True)
    print(f"[pi-cron]   audit rotate : {'enabled' if ENABLE_AUDIT_ROTATE else 'disabled'}", flush=True)
    if ENABLE_AUDIT_ROTATE:
        if AUDIT_AGE:
            print(f"[pi-cron]   audit mode   : age-based ({AUDIT_AGE} days), at {AUDIT_HOUR:02d}:00", flush=True)
        else:
            print(f"[pi-cron]   audit mode   : watermark (high={AUDIT_HIGHWATERMARK}, low={AUDIT_LOWWATERMARK}), at {AUDIT_HOUR:02d}:00", flush=True)
    print(f"[pi-cron]   challenges   : {'enabled' if ENABLE_CHALLENGE_CLEANUP else 'disabled'}", flush=True)
    print(f"[pi-cron]   periodic tasks: {'enabled' if ENABLE_PERIODIC_TASKS else 'disabled'}", flush=True)

    last_minute = -1

    while True:
        now = datetime.datetime.now()

        if now.minute != last_minute:
            last_minute = now.minute

            # Every minute: run tasks configured via the admin UI
            if ENABLE_PERIODIC_TASKS:
                run(["pi-manage-cron", "run_scheduled", "--cron"])

            if now.minute == 0:
                # Every hour: clean up expired challenge responses
                if ENABLE_CHALLENGE_CLEANUP:
                    run(["pi-manage", "challenge", "cleanup"])

            if now.hour == AUDIT_HOUR and now.minute == 0:
                # Daily at configured hour: trim the audit log
                if ENABLE_AUDIT_ROTATE:
                    run(audit_rotate_cmd())

        # Sleep until the start of the next minute
        sleep_sec = 61 - datetime.datetime.now().second
        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
