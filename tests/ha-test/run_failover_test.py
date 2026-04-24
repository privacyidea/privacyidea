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


def parse_aggregated(stats_csv: Path) -> tuple[int, int]:
    """Return (total_requests, total_failures) from the Aggregated row."""
    with open(stats_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name") == "Aggregated":
                return int(row["Request Count"]), int(row["Failure Count"])
    return 0, 0


def _history_snapshots(history_csv: Path) -> list[dict]:
    """Load cumulative Aggregated snapshots from locust's history CSV.

    The CSV writes one row per second. Columns named "50%", "95%" etc. are
    cumulative percentiles since test start (not per-window), so we derive
    per-second stats by taking deltas of the Total* columns instead.
    """
    rows = []
    with open(history_csv) as f:
        for row in csv.DictReader(f):
            if row.get("Name") != "Aggregated":
                continue
            try:
                rows.append({
                    "ts": int(row["Timestamp"]),
                    "total_req": int(row["Total Request Count"]),
                    "total_fail": int(row["Total Failure Count"]),
                    "total_avg_ms": float(row["Total Average Response Time"]),
                })
            except (KeyError, ValueError):
                continue
    return rows


def _bucket_deltas(snapshots: list[dict]) -> list[dict]:
    """Turn cumulative snapshots into per-bucket deltas.

    Each bucket represents the activity between two adjacent snapshots:
    - ts_end: end of bucket window
    - requests: new requests in the window
    - failures: new failures in the window
    - avg_ms: mean response time of requests completed in this window,
      derived from total cumulative average × count.
    """
    buckets = []
    for prev, curr in zip(snapshots, snapshots[1:]):
        d_req = curr["total_req"] - prev["total_req"]
        if d_req <= 0:
            continue
        d_fail = curr["total_fail"] - prev["total_fail"]
        # cumulative_avg * cumulative_count gives total response-time-sum
        rt_sum_curr = curr["total_avg_ms"] * curr["total_req"]
        rt_sum_prev = prev["total_avg_ms"] * prev["total_req"]
        bucket_avg = (rt_sum_curr - rt_sum_prev) / d_req
        buckets.append({
            "ts_end": curr["ts"],
            "requests": d_req,
            "failures": d_fail,
            "avg_ms": bucket_avg,
        })
    return buckets


def longest_failure_window(history_csv: Path) -> int:
    """Longest run of consecutive 1s buckets where failures occurred, in seconds."""
    buckets = _bucket_deltas(_history_snapshots(history_csv))
    longest = run = 0
    for b in buckets:
        if b["failures"] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest  # one bucket per second


@dataclass
class PhaseStats:
    name: str
    buckets: int
    requests: int
    failures: int
    avg_min: float | None      # cheapest bucket in the phase
    avg_median: float | None   # median bucket avg
    avg_max: float | None      # worst bucket in the phase
    avg_weighted: float | None # request-weighted overall avg for the phase

    @property
    def failure_rate(self) -> float:
        return self.failures / self.requests if self.requests else 0.0


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    vs = sorted(values)
    n = len(vs)
    return vs[n // 2] if n % 2 else (vs[n // 2 - 1] + vs[n // 2]) / 2


def phase_stats(history_csv: Path, stop_ts: float, start_ts: float,
                recovery_grace_s: int = 15) -> list[PhaseStats]:
    """Split the run into pre / during / post phases based on failover event times."""
    buckets = _bucket_deltas(_history_snapshots(history_csv))
    during_end = start_ts + recovery_grace_s

    phases = {"pre-failover": [], "during failover": [], "post-recovery": []}
    for b in buckets:
        if b["ts_end"] < stop_ts:
            phases["pre-failover"].append(b)
        elif b["ts_end"] < during_end:
            phases["during failover"].append(b)
        else:
            phases["post-recovery"].append(b)

    out = []
    for name, bs in phases.items():
        avgs = [b["avg_ms"] for b in bs]
        req_sum = sum(b["requests"] for b in bs)
        fail_sum = sum(b["failures"] for b in bs)
        rt_weighted = (
            sum(b["avg_ms"] * b["requests"] for b in bs) / req_sum if req_sum else None
        )
        out.append(PhaseStats(
            name=name,
            buckets=len(bs),
            requests=req_sum,
            failures=fail_sum,
            avg_min=min(avgs) if avgs else None,
            avg_median=_median(avgs),
            avg_max=max(avgs) if avgs else None,
            avg_weighted=rt_weighted,
        ))
    return out


def run_test(args, thresholds: Thresholds) -> int:
    if not COMPOSE_FILE.exists():
        print(f"ERROR: {COMPOSE_FILE} not found.", file=sys.stderr)
        return 2

    # Locate locust: prefer the one next to sys.executable (repo-local venv),
    # fall back to PATH. Invoking via sys.executable's sibling keeps the
    # interpreter consistent with --python overrides.
    locust_bin = Path(sys.executable).parent / "locust"
    if not locust_bin.exists():
        located = shutil.which("locust")
        if located is None:
            print("ERROR: 'locust' not found. Install with: "
                  f"{sys.executable} -m pip install -r {SCRIPT_DIR / 'requirements.txt'}",
                  file=sys.stderr)
            return 2
        locust_bin = Path(located)

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
        str(locust_bin),
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
    stop_wall = time.time()
    compose("stop", args.target)

    print(f"[5/7] waiting {args.downtime}s before restart")
    time.sleep(args.downtime)

    print(f"[6/7] starting {args.target}, polling for Synced")
    start_wall = time.time()
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
    phases = phase_stats(history_csv, stop_wall, start_wall)

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
    print()
    print("  per-phase latency (avg ms, derived from cumulative deltas):")
    print(f"  {'phase':<18}{'buckets':>8}{'reqs':>8}{'fail%':>8}"
          f"{'avg (wt)':>10}{'bucket min':>12}{'bucket med':>12}{'bucket max':>12}")
    def fmt(v: float | None) -> str:
        return f"{v:.0f}" if v is not None else "—"
    for p in phases:
        print(f"  {p.name:<18}{p.buckets:>8}{p.requests:>8}"
              f"{p.failure_rate:>7.1%} "
              f"{fmt(p.avg_weighted):>10}{fmt(p.avg_min):>12}"
              f"{fmt(p.avg_median):>12}{fmt(p.avg_max):>12}")
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
    ap.add_argument("--users", type=int, default=10,
                    help="Concurrent locust users (default: 10 — targets ~30–50%% capacity "
                         "on a single-host tier F stack; raise for saturation testing)")
    ap.add_argument("--duration", type=int, default=90, help="Total locust run time, seconds (default: 90)")
    ap.add_argument("--warmup", type=int, default=25,
                    help="Seconds of load before killing the writer (default: 25 — long enough "
                         "for the pre-failover phase to represent steady state, not ramp-up)")
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
