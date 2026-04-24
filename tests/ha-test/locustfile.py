"""
Locust load profile for HA failover testing.

Each simulated user runs a full HOTP challenge-response authentication loop
against PrivacyIDEA. Token data is loaded from test_tokens.json next to this
file (produced by data_generator.py).

Run headless via run_failover_test.py, or manually:
  locust -f locustfile.py --host http://localhost:8000 -u 19 -r 19 -t 60s

Environment variables:
  PI_ADMIN_USER      Admin username for pre-test setup. Default: admin
  PI_ADMIN_PASSWORD  Admin password. Default: admin
  PI_REALM           Realm. Default: defrealm
"""
import json
import os
import queue
from pathlib import Path

import pyotp
import requests
import urllib3
from locust import HttpUser, between, events, task

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_PATH = SCRIPT_DIR / "test_tokens.json"

ADMIN_USERNAME = os.environ.get("PI_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("PI_ADMIN_PASSWORD", "admin")
REALM = os.environ.get("PI_REALM", "defrealm")

POLICY_NAME = "hotp_challenge_response"

TOKEN_QUEUE: "queue.Queue[dict]" = queue.Queue()
ALL_TOKENS: list[dict] = []


@events.init_command_line_parser.add_listener
def _add_args(parser):
    parser.add_argument(
        "--start-counter",
        type=int,
        env_var="LOCUST_START_COUNTER",
        default=0,
        help="Override the starting counter for all HOTP tokens",
    )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Load tokens, ensure the challenge-response policy exists, reset failcounters."""
    print(f"Loading test data from {ARTIFACT_PATH}...")
    override_counter = environment.parsed_options.start_counter

    try:
        with open(ARTIFACT_PATH) as f:
            tokens = json.load(f)
        for t in tokens:
            if override_counter > 0:
                t["counter"] = override_counter
            ALL_TOKENS.append(t)
            TOKEN_QUEUE.put(t)
        print(f"Queued {len(ALL_TOKENS)} tokens.")
    except FileNotFoundError:
        print(f"ERROR: {ARTIFACT_PATH} not found. Run data_generator.py first.")
        environment.runner.quit()
        return

    host = environment.host
    print(f"\n--- Admin setup against {host} ---")
    session = requests.Session()
    session.verify = False

    auth_res = session.post(
        f"{host}/auth",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    if not auth_res.ok or not auth_res.json().get("result", {}).get("status"):
        print(f"ERROR: Admin authentication failed: {auth_res.text}")
        environment.runner.quit()
        return
    headers = {"Authorization": auth_res.json()["result"]["value"]["token"]}

    # Check for the specific policy rather than "any policy exists"
    policy_res = session.get(f"{host}/policy/", headers=headers)
    existing = policy_res.json().get("result", {}).get("value", []) or []
    existing_names = {p.get("name") for p in existing} if isinstance(existing, list) else set()

    if POLICY_NAME not in existing_names:
        print(f"Creating policy '{POLICY_NAME}'...")
        policy_payload = {
            "action": ["challenge_response=hotp"],
            "scope": "authentication",
            "realm": [], "resolver": [], "user": "", "active": True,
            "check_all_resolvers": False, "user_case_insensitive": False,
            "client": "", "time": "", "description": "", "priority": 1,
            "conditions": [], "pinode": [], "user_agents": [],
            "name": POLICY_NAME, "adminrealm": [],
        }
        create_res = session.post(f"{host}/policy/{POLICY_NAME}", headers=headers, json=policy_payload)
        if not create_res.ok or not create_res.json().get("result", {}).get("value"):
            print(f"ERROR: Failed to create policy: {create_res.text}")
            environment.runner.quit()
            return
    else:
        print(f"Policy '{POLICY_NAME}' already exists, skipping creation.")

    print("Resetting failcounters for all loaded tokens...")
    reset_count = 0
    for t in ALL_TOKENS:
        r = session.post(f"{host}/token/reset", headers=headers, json={"serial": t["serial"]})
        if r.ok and r.json().get("result", {}).get("value") == 1:
            reset_count += 1
        else:
            print(f"Warning: failed to reset token {t['serial']}: {r.text}")
    print(f"Reset {reset_count}/{len(ALL_TOKENS)} tokens.")
    print("--- Admin setup complete ---\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    if ALL_TOKENS:
        with open(ARTIFACT_PATH, "w") as f:
            json.dump(ALL_TOKENS, f, indent=4)
        print(f"Saved {len(ALL_TOKENS)} tokens with updated counters to {ARTIFACT_PATH}.")


class ChallengeResponseUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        try:
            self.token_data = TOKEN_QUEUE.get_nowait()
            self.hotp_generator = pyotp.HOTP(self.token_data["secret_b32"])
        except queue.Empty:
            print("ERROR: Worker spawned without an available token. Reduce -u.")
            self.environment.runner.quit()

    @task
    def execute_auth_flow(self):
        username = self.token_data["username"]
        pin = self.token_data["pin"]

        # Step 1: trigger challenge
        transaction_id = None
        with self.client.post(
            "/validate/check",
            json={"user": username, "pass": pin},
            catch_response=True,
            verify=False,
            name="/validate/check (Trigger Challenge)",
        ) as response:
            if not response.ok:
                response.failure(f"Step 1 HTTP {response.status_code}")
                return
            try:
                data = response.json()
                res_block = data.get("result", {})
                if res_block.get("authentication") == "CHALLENGE" and res_block.get("value") is False:
                    transaction_id = data.get("detail", {}).get("transaction_id")
                    if not transaction_id:
                        response.failure("Missing transaction_id")
                    else:
                        response.success()
                else:
                    response.failure(f"Expected CHALLENGE, got {res_block.get('authentication')}")
                    return
            except json.JSONDecodeError:
                response.failure("Step 1 JSON decode error")
                return

        if not transaction_id:
            return

        # Step 2: answer challenge
        otp_value = self.hotp_generator.at(self.token_data["counter"])
        with self.client.post(
            "/validate/check",
            json={"user": username, "pass": otp_value, "transaction_id": transaction_id},
            catch_response=True,
            verify=False,
            name="/validate/check (Verify OTP)",
        ) as response:
            if not response.ok:
                response.failure(f"Step 2 HTTP {response.status_code}")
                return
            try:
                data = response.json()
                res_block = data.get("result", {})
                if res_block.get("authentication") == "ACCEPT" and res_block.get("value") is True:
                    # Increment only on verified ACCEPT — keeps local counter in sync with DB
                    # even across failover drops.
                    self.token_data["counter"] += 1
                    response.success()
                else:
                    response.failure(f"Expected ACCEPT, got {res_block.get('authentication')}")
            except json.JSONDecodeError:
                response.failure("Step 2 JSON decode error")
