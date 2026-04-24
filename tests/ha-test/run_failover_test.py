"""
One-command failover test for the tier-F HA docker setup.

Runs: compose up → provision tokens → start locust headless → stop a DB node
mid-run → restart it → poll for Galera rejoin → parse locust stats → assert
thresholds → exit 0/non-zero.

Usage:
  python run_failover_test.py                 # full run, default thresholds
  python run_failover_test.py --skip-up       # assume stack is already running
  python run_failover_test.py --skip-provision  # reuse existing test_tokens.json

Scenario (v1): kill the Galera writer node (db-1) during load, restart it,
verify the cluster reconverges.
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
COMPOSE_DIR = REPO_ROOT / "deploy" / "docker" / "ha"
COMPOSE_FILE = COMPOSE_DIR / "ha-compose.yaml"
COMPOSE_OVERRIDE = SCRIPT_DIR / "ha-compose.test.yaml"
ROOT_PW_FILE = COMPOSE_DIR / "secrets" / "mariadb_root_password"
ADMIN_PW_FILE = COMPOSE_DIR / "secrets" / "bootstrap_admin_password"

RESULTS_DIR = SCRIPT_DIR / "results"
CSV_PREFIX = RESULTS_DIR / "run"

COMPOSE_ARGS = ["-f", str(COMPOSE_FILE), "-f", str(COMPOSE_OVERRIDE)]

# Compose resolves relative bind-mount paths against the first -f file's dir,
# not each file's own dir. Pass an absolute path through an env var instead.
USERS_FILE = SCRIPT_DIR / "testdata" / "users"
os.environ["HA_TEST_USERS_FILE"] = str(USERS_FILE)


@dataclass
class Thresholds:
    max_failure_rate: float = 0.02          # fraction of total requests (< 2%)
    max_failure_window_s: int = 10          # longest contiguous 10s bucket with failures
    max_rejoin_s: int = 60                  # docker start → wsrep Synced


# ── compose helpers ──────────────────────────────────────────────────────────

def compose(*args: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", *COMPOSE_ARGS, *args]
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def wsrep_state(node: str = "db-1") -> str:
    """Return wsrep_local_state_comment of the given node, or '' on error."""
    if not ROOT_PW_FILE.exists():
        return ""
    root_pw = ROOT_PW_FILE.read_text().strip()
    try:
        res = subprocess.run(
            ["docker", "compose", *COMPOSE_ARGS, "exec", "-T", node,
             "mariadb", "-uroot", f"-p{root_pw}", "--silent", "-e",
             "SHOW STATUS LIKE 'wsrep_local_state_comment'"],
            check=False, capture_output=True, text=True, timeout=10,
        )
        if res.returncode != 0:
            return ""
        # Expected output: "wsrep_local_state_comment\tSynced"
        parts = res.stdout.strip().split()
        return parts[-1] if parts else ""
    except subprocess.TimeoutExpired:
        return ""


def wait_for_sync(node: str, timeout_s: int) -> int | None:
    """Poll until `node` is Synced. Return elapsed seconds, or None on timeout."""
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        if wsrep_state(node) == "Synced":
            return int(time.monotonic() - start)
        time.sleep(2)
    return None


# ── stats parsing ────────────────────────────────────────────────────────────

def parse_aggregated(stats_csv: Path) -> tuple[int, int]:
    """Return (total_requests, total_failures) from the Aggregated row."""
    with open(stats_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name") == "Aggregated":
                return int(row["Request Count"]), int(row["Failure Count"])
    return 0, 0


def longest_failure_window(history_csv: Path) -> int:
    """Longest run of consecutive 10s buckets where Failures/s > 0, in seconds."""
    buckets = []
    with open(history_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name") != "Aggregated":
                continue
            try:
                buckets.append(float(row["Failures/s"]) > 0)
            except (KeyError, ValueError):
                continue
    longest = run = 0
    for b in buckets:
        if b:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest * 10  # default locust bucket is 10s


# ── main orchestration ──────────────────────────────────────────────────────

def run_test(args, thresholds: Thresholds) -> int:
    if not COMPOSE_FILE.exists():
        print(f"ERROR: {COMPOSE_FILE} not found.", file=sys.stderr)
        return 2

    if shutil.which("locust") is None:
        print("ERROR: 'locust' not found on PATH. Install with: "
              f"pip install -r {SCRIPT_DIR / 'requirements.txt'}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    host = env.get("PI_BASE_URL", "http://localhost:8000")
    env["PI_BASE_URL"] = host

    # Admin password: prefer secrets file if present (HA default), else fall back to env/admin.
    if "PI_ADMIN_PASSWORD" not in env and ADMIN_PW_FILE.exists():
        env["PI_ADMIN_PASSWORD"] = ADMIN_PW_FILE.read_text().strip()

    # 1. Bring stack up
    if not args.skip_up:
        if args.fresh:
            print("[1/7] --fresh: docker compose down -v")
            compose("down", "-v", check=False)
        print(f"[1/7] docker compose up -d --wait ({COMPOSE_FILE})")
        compose("up", "-d", "--wait")
    else:
        print("[1/7] skip_up: assuming stack is already running")

    # 2. Provision tokens
    if not args.skip_provision:
        print("[2/7] provisioning tokens (data_generator.py)")
        res = subprocess.run([sys.executable, str(SCRIPT_DIR / "data_generator.py")], env=env)
        if res.returncode != 0:
            print("ERROR: provisioning failed", file=sys.stderr)
            return 2
    else:
        print("[2/7] skip_provision: reusing existing test_tokens.json")

    # 3. Start locust headless
    RESULTS_DIR.mkdir(exist_ok=True)
    print(f"[3/7] starting locust headless ({args.duration}s, {args.users} users)")
    locust_cmd = [
        "locust",
        "-f", str(SCRIPT_DIR / "locustfile.py"),
        "--headless",
        "--host", host,
        "-u", str(args.users),
        "-r", str(args.users),
        "-t", f"{args.duration}s",
        "--csv", str(CSV_PREFIX),
        "--only-summary",
    ]
    locust_log = RESULTS_DIR / "locust.log"
    with open(locust_log, "w") as log:
        locust_proc = subprocess.Popen(locust_cmd, stdout=log, stderr=subprocess.STDOUT, env=env)

    # 4. Warm-up before inducing failure
    time.sleep(args.warmup)

    # 5. Kill writer, wait, restart
    print(f"[4/7] stopping {args.target} (writer)")
    compose("stop", args.target)

    print(f"[5/7] waiting {args.downtime}s before restart")
    time.sleep(args.downtime)

    print(f"[6/7] starting {args.target}, polling for Synced")
    compose("start", args.target)
    rejoin_s = wait_for_sync(args.target, timeout_s=thresholds.max_rejoin_s * 2)

    # 6. Wait for locust to finish
    print("[7/7] waiting for locust run to finish")
    try:
        locust_proc.wait(timeout=args.duration + 60)
    except subprocess.TimeoutExpired:
        print("ERROR: locust did not exit in time, terminating", file=sys.stderr)
        locust_proc.send_signal(signal.SIGTERM)
        locust_proc.wait(timeout=10)

    # 7. Parse + assert
    stats_csv = Path(f"{CSV_PREFIX}_stats.csv")
    history_csv = Path(f"{CSV_PREFIX}_stats_history.csv")
    if not stats_csv.exists() or not history_csv.exists():
        print(f"ERROR: locust CSVs missing. See {locust_log}", file=sys.stderr)
        return 2

    total, failures = parse_aggregated(stats_csv)
    failure_rate = failures / total if total else 1.0
    window_s = longest_failure_window(history_csv)

    print()
    print("── results ─────────────────────────────────────────")
    print(f"  total requests         : {total}")
    print(f"  total failures         : {failures}")
    print(f"  failure rate           : {failure_rate:.2%} (threshold ≤ {thresholds.max_failure_rate:.2%})")
    print(f"  longest failure window : {window_s}s (threshold ≤ {thresholds.max_failure_window_s}s)")
    if rejoin_s is None:
        print(f"  rejoin time            : DID NOT SYNC within {thresholds.max_rejoin_s * 2}s")
    else:
        print(f"  rejoin time            : {rejoin_s}s (threshold ≤ {thresholds.max_rejoin_s}s)")
    print("────────────────────────────────────────────────────")

    problems = []
    if failure_rate > thresholds.max_failure_rate:
        problems.append(f"failure rate {failure_rate:.2%} exceeds {thresholds.max_failure_rate:.2%}")
    if window_s > thresholds.max_failure_window_s:
        problems.append(f"failure window {window_s}s exceeds {thresholds.max_failure_window_s}s")
    if rejoin_s is None:
        problems.append(f"{args.target} did not reach Synced")
    elif rejoin_s > thresholds.max_rejoin_s:
        problems.append(f"rejoin took {rejoin_s}s, exceeds {thresholds.max_rejoin_s}s")

    if problems:
        print("\nFAIL:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("\nPASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--users", type=int, default=50, help="Concurrent locust users (default: 50)")
    ap.add_argument("--duration", type=int, default=90, help="Total locust run time, seconds (default: 90)")
    ap.add_argument("--warmup", type=int, default=15, help="Seconds of load before killing the writer (default: 15)")
    ap.add_argument("--downtime", type=int, default=20, help="Seconds to leave the writer down (default: 20)")
    ap.add_argument("--target", default="db-1", help="Galera node to kill/restart (default: db-1)")
    ap.add_argument("--skip-up", action="store_true", help="Skip 'docker compose up'; assume stack is running")
    ap.add_argument("--skip-provision", action="store_true", help="Reuse existing test_tokens.json")
    ap.add_argument("--fresh", action="store_true",
                    help="'docker compose down -v' before up — wipes Galera state. Use after a failed run.")
    ap.add_argument("--max-failure-rate", type=float, default=0.02)
    ap.add_argument("--max-failure-window", type=int, default=10)
    ap.add_argument("--max-rejoin", type=int, default=60)
    args = ap.parse_args()

    thresholds = Thresholds(
        max_failure_rate=args.max_failure_rate,
        max_failure_window_s=args.max_failure_window,
        max_rejoin_s=args.max_rejoin,
    )
    sys.exit(run_test(args, thresholds))


if __name__ == "__main__":
    main()
