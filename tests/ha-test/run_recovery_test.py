"""
All-nodes-crashed recovery test for the tier F HA stack.

Simulates a simultaneous hard crash of both Galera nodes (SIGKILL on both
db-1 and db-2 at once, leaving neither with safe_to_bootstrap: 1), then
runs deploy/docker/ha/scripts/ha-recover-cluster.sh and verifies the
cluster comes back Synced with token data preserved.

Usage:
  python run_recovery_test.py                # full run
  python run_recovery_test.py --skip-up      # assume stack is already running
  python run_recovery_test.py --skip-provision  # reuse existing test_tokens.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
COMPOSE_DIR = REPO_ROOT / "deploy" / "docker" / "ha"
COMPOSE_FILE = COMPOSE_DIR / "ha-compose.yaml"
COMPOSE_OVERRIDE = SCRIPT_DIR / "ha-compose.test.yaml"
RECOVERY_SCRIPT = COMPOSE_DIR / "scripts" / "ha-recover-cluster.sh"
ROOT_PW_FILE = COMPOSE_DIR / "secrets" / "mariadb_root_password"
ADMIN_PW_FILE = COMPOSE_DIR / "secrets" / "bootstrap_admin_password"
TOKENS_FILE = SCRIPT_DIR / "test_tokens.json"

COMPOSE_ARGS = ["-f", str(COMPOSE_FILE), "-f", str(COMPOSE_OVERRIDE)]

# ha-compose.test.yaml uses a relative bind-mount path that compose resolves
# against the first -f file's dir. Pass an absolute path through the env.
USERS_FILE = SCRIPT_DIR / "testdata" / "users"
os.environ["HA_TEST_USERS_FILE"] = str(USERS_FILE)


def compose(*args: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", *COMPOSE_ARGS, *args]
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def container_id(service: str) -> str | None:
    """Return the container ID for a compose service, or None if not running."""
    res = compose("ps", "-q", service, capture=True, check=False)
    cid = res.stdout.strip()
    return cid or None


def wsrep_state(node: str) -> str:
    if not ROOT_PW_FILE.exists():
        return ""
    root_pw = ROOT_PW_FILE.read_text().strip()
    res = subprocess.run(
        ["docker", "compose", *COMPOSE_ARGS, "exec", "-T", node,
         "mariadb", "-uroot", f"-p{root_pw}", "--silent", "-e",
         "SHOW STATUS LIKE 'wsrep_local_state_comment'"],
        check=False, capture_output=True, text=True, timeout=10,
    )
    if res.returncode != 0:
        return ""
    parts = res.stdout.strip().split()
    return parts[-1] if parts else ""


def wait_for_sync(node: str, timeout_s: int) -> int | None:
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        if wsrep_state(node) == "Synced":
            return int(time.monotonic() - start)
        time.sleep(2)
    return None


def count_tokens(host: str, admin_user: str, admin_pw: str) -> int:
    """Count tokens via the PI API. Used as a data-preservation check."""
    r = requests.post(
        f"{host}/auth",
        data={"username": admin_user, "password": admin_pw},
        timeout=10, verify=False,
    )
    r.raise_for_status()
    auth_token = r.json()["result"]["value"]["token"]
    r = requests.get(
        f"{host}/token/",
        headers={"Authorization": auth_token},
        timeout=10, verify=False,
    )
    r.raise_for_status()
    return r.json()["result"]["value"]["count"]


def kill_both_db_nodes() -> None:
    """SIGKILL db-1 and db-2 as close to simultaneously as the kernel allows.

    `docker kill` is used directly (not `docker compose stop`) because compose
    sends SIGTERM and waits — we want a hard kill that leaves grastate.dat
    with safe_to_bootstrap: 0 on both nodes, mirroring a real power-loss.
    """
    db1 = container_id("db-1")
    db2 = container_id("db-2")
    if not db1 or not db2:
        raise RuntimeError("db-1 or db-2 not running; cannot kill")
    # Issue both kills in a single shell so they fire as fast as possible.
    subprocess.run(
        ["sh", "-c", f"docker kill -s KILL {db1} & docker kill -s KILL {db2} & wait"],
        check=True,
    )


def grastate_has_safe_bootstrap(node: str) -> bool | None:
    """Return True if grastate.dat has safe_to_bootstrap: 1, False if 0,
    None if unreadable. Used to confirm the all-crashed precondition."""
    res = subprocess.run(
        ["docker", "compose", *COMPOSE_ARGS,
         "run", "--rm", "--no-deps", "--entrypoint", "cat", node,
         "/var/lib/mysql/grastate.dat"],
        check=False, capture_output=True, text=True, timeout=30,
    )
    if res.returncode != 0:
        return None
    if "safe_to_bootstrap: 1" in res.stdout:
        return True
    if "safe_to_bootstrap: 0" in res.stdout:
        return False
    return None


def run_test(args) -> int:
    if not COMPOSE_FILE.exists():
        print(f"ERROR: {COMPOSE_FILE} not found", file=sys.stderr)
        return 2
    if not RECOVERY_SCRIPT.exists():
        print(f"ERROR: {RECOVERY_SCRIPT} not found", file=sys.stderr)
        return 2

    env = os.environ.copy()
    host = env.get("PI_BASE_URL", "http://localhost:8000")
    env["PI_BASE_URL"] = host
    admin_user = env.get("PI_ADMIN_USER", "admin")
    if "PI_ADMIN_PASSWORD" in env:
        admin_pw = env["PI_ADMIN_PASSWORD"]
    elif ADMIN_PW_FILE.exists():
        admin_pw = ADMIN_PW_FILE.read_text().strip()
    else:
        print("ERROR: no admin password (PI_ADMIN_PASSWORD or secrets file)", file=sys.stderr)
        return 2
    env["PI_ADMIN_PASSWORD"] = admin_pw

    # 1. Bring stack up
    if not args.skip_up:
        if args.fresh:
            print("[1/8] --fresh: docker compose down -v")
            compose("down", "-v", check=False)
        print("[1/8] docker compose up -d --wait")
        compose("up", "-d", "--wait")
    else:
        print("[1/8] skip_up: assuming stack is already running")

    # 2. Provision tokens (need a known dataset to verify preservation)
    if not args.skip_provision or not TOKENS_FILE.exists():
        print("[2/8] provisioning tokens (data_generator.py)")
        res = subprocess.run([sys.executable, str(SCRIPT_DIR / "data_generator.py")], env=env)
        if res.returncode != 0:
            print("ERROR: provisioning failed", file=sys.stderr)
            return 2
    else:
        print("[2/8] skip_provision: reusing existing test_tokens.json")

    # 3. Baseline: count tokens before the crash
    print("[3/8] baseline token count")
    try:
        baseline_count = count_tokens(host, admin_user, admin_pw)
    except Exception as e:
        print(f"ERROR: baseline token count failed: {e}", file=sys.stderr)
        return 2
    print(f"      tokens before crash: {baseline_count}")
    if baseline_count == 0:
        print("ERROR: 0 tokens before crash — data_generator likely failed silently",
              file=sys.stderr)
        return 2

    # 4. SIGKILL both DB nodes simultaneously
    print("[4/8] SIGKILL db-1 and db-2 simultaneously")
    kill_both_db_nodes()
    # Give docker a moment to mark the containers exited.
    time.sleep(3)

    # 5. Verify the all-crashed precondition: neither node has safe_to_bootstrap: 1
    print("[5/8] verifying all-crashed precondition")
    for n in ("db-1", "db-2"):
        s = grastate_has_safe_bootstrap(n)
        if s is None:
            print(f"ERROR: cannot read grastate.dat on {n}", file=sys.stderr)
            return 2
        if s is True:
            print(f"ERROR: {n} has safe_to_bootstrap: 1 — not the deadlock case "
                  "this test exercises", file=sys.stderr)
            return 2
        print(f"      {n}: safe_to_bootstrap: 0 (good)")

    # 6. Run the recovery script with --yes
    print("[6/8] running ha-recover-cluster.sh --yes --no-backup")
    res = subprocess.run(
        [str(RECOVERY_SCRIPT), "--yes", "--no-backup"],
        cwd=str(COMPOSE_DIR),
    )
    if res.returncode != 0:
        print(f"ERROR: recovery script exited {res.returncode}", file=sys.stderr)
        return 1

    # 7. Confirm both nodes Synced
    print("[7/8] confirming both nodes Synced")
    for n in ("db-1", "db-2"):
        elapsed = wait_for_sync(n, timeout_s=60)
        if elapsed is None:
            print(f"FAIL: {n} not Synced after recovery", file=sys.stderr)
            return 1
        print(f"      {n}: Synced ({elapsed}s)")

    # 8. Verify token data preserved
    print("[8/8] verifying data preservation")
    # The pi workers may have lost their DB connections during the kill —
    # ProxySQL reconnects, but allow a short grace period.
    for attempt in range(10):
        try:
            after_count = count_tokens(host, admin_user, admin_pw)
            break
        except Exception as e:
            if attempt == 9:
                print(f"ERROR: post-recovery token count failed: {e}", file=sys.stderr)
                return 1
            time.sleep(3)
    print(f"      tokens after recovery: {after_count}")

    print()
    print("── results ─────────────────────────────────────────")
    print(f"  baseline tokens     : {baseline_count}")
    print(f"  post-recovery tokens: {after_count}")
    print("────────────────────────────────────────────────────")

    if after_count != baseline_count:
        print(f"\nFAIL: token count changed ({baseline_count} → {after_count})")
        return 1

    print("\nPASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-up", action="store_true",
                    help="Skip 'docker compose up'; assume stack is running")
    ap.add_argument("--skip-provision", action="store_true",
                    help="Reuse existing test_tokens.json")
    ap.add_argument("--fresh", action="store_true",
                    help="'docker compose down -v' before up — wipes Galera state")
    args = ap.parse_args()
    sys.exit(run_test(args))


if __name__ == "__main__":
    # Suppress urllib3 InsecureRequestWarning — local self-signed certs.
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass
    main()
