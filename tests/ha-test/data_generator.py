"""
Provision HOTP tokens for HA failover testing.

Creates N HOTP tokens assigned to the first N users in the configured realm
and writes them to test_tokens.json next to this script. The locustfile and
run_failover_test.py both consume that artifact.

Environment variables (all optional):
  PI_BASE_URL        Target URL. Default: http://localhost:8000
  PI_ADMIN_USER      Admin username. Default: admin
  PI_ADMIN_PASSWORD  Admin password. Default: admin
  PI_REALM           Realm to provision tokens in. Default: defrealm
  PI_USER_COUNT      Number of users/tokens to provision. Default: 19
  PI_TOKEN_PIN       PIN to set on every token. Default: 123
"""
import json
import os
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.environ.get("PI_BASE_URL", "http://localhost:8000")
ADMIN_USERNAME = os.environ.get("PI_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("PI_ADMIN_PASSWORD", "admin")
REALM = os.environ.get("PI_REALM", "defrealm")
RESOLVER = os.environ.get("PI_RESOLVER", "testusers")
# Path inside the pi container — matches the bind mount in ha-compose.test.yaml.
RESOLVER_FILE = os.environ.get("PI_RESOLVER_FILE", "/etc/privacyidea/test_users")
USER_COUNT = int(os.environ.get("PI_USER_COUNT", "50"))
TOKEN_PIN = os.environ.get("PI_TOKEN_PIN", "123")

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRIPT_DIR / "test_tokens.json"


def ensure_resolver(session: requests.Session, headers: dict) -> bool:
    """Create or update the passwdresolver pointing at the bind-mounted users file."""
    payload = {"type": "passwdresolver", "fileName": RESOLVER_FILE}
    res = session.post(f"{BASE_URL}/resolver/{RESOLVER}", headers=headers, json=payload)
    if not res.ok or not res.json().get("result", {}).get("status"):
        print(f"Failed to create resolver '{RESOLVER}': {res.text}")
        return False
    print(f"Resolver '{RESOLVER}' ready (file: {RESOLVER_FILE}).")
    return True


def ensure_realm(session: requests.Session, headers: dict) -> bool:
    """Create or update the realm to contain the test resolver."""
    res = session.post(f"{BASE_URL}/realm/{REALM}", headers=headers, json={"resolvers": RESOLVER})
    if not res.ok or not res.json().get("result", {}).get("status"):
        print(f"Failed to create realm '{REALM}': {res.text}")
        return False
    value = res.json().get("result", {}).get("value", {})
    if value.get("failed"):
        print(f"Warning: realm creation reported failed resolvers: {value['failed']}")
    print(f"Realm '{REALM}' ready with resolver '{RESOLVER}'.")
    return True


def prepare_test_data():
    session = requests.Session()
    session.verify = False

    print(f"1. Authenticating as admin at {BASE_URL}...")
    # Admin auth: no realm — bootstrap admin is a superadmin, not a realm user.
    auth_res = session.post(
        f"{BASE_URL}/auth",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    if not auth_res.ok or not auth_res.json().get("result", {}).get("status"):
        print(f"Failed to authenticate: {auth_res.text}")
        return 1

    headers = {"Authorization": auth_res.json()["result"]["value"]["token"]}

    print("2. Ensuring resolver and realm exist...")
    if not ensure_resolver(session, headers):
        return 1
    if not ensure_realm(session, headers):
        return 1

    print("3. Fetching user list...")
    users_res = session.get(f"{BASE_URL}/user", headers=headers)
    if not users_res.ok:
        print(f"Failed to fetch users: {users_res.text}")
        return 1

    all_users = users_res.json()["result"]["value"]
    actual_count = min(USER_COUNT, len(all_users))
    target_users = all_users[:actual_count]
    print(f"Found {len(all_users)} users. Selecting the first {actual_count} for token assignment.")

    generated_tokens = []

    print("4. Provisioning HOTP tokens...")
    for user in target_users:
        username = user["username"]
        payload = {
            "type": "hotp",
            "pin": TOKEN_PIN,
            "genkey": 1,
            "otplen": 6,
            "hashlib": "sha1",
            "2stepinit": False,
            "user": username,
            "realm": REALM,
        }
        init_res = session.post(f"{BASE_URL}/token/init", headers=headers, json=payload)
        if not init_res.ok:
            print(f"Failed to create token for user {username}: {init_res.text}")
            continue

        data = init_res.json()
        try:
            serial = data["detail"]["serial"]
            secret_b32 = data["detail"]["otpkey"]["value_b32"]
            generated_tokens.append({
                "username": username,
                "serial": serial,
                "secret_b32": secret_b32,
                "counter": 1,
                "pin": TOKEN_PIN,
            })
            print(f"Assigned token {serial} to user: {username}")
        except KeyError as e:
            print(f"Failed to parse response for {username}. Missing key: {e}")

    print(f"5. Saving artifact to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(generated_tokens, f, indent=4)

    print(f"\nSetup complete! Saved {len(generated_tokens)} tokens to {OUTPUT_FILE}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(prepare_test_data())
