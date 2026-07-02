#!/usr/bin/env bash
# Smoke-test a running single-node privacyIDEA stack.
#
# Assumes the stack from ../compose.yaml is already up (pi-init has completed and
# pi is starting). Verifies the end-to-end wiring that is easy to get wrong in a
# container setup: health readiness, admin authentication (which exercises
# enckey + pepper + secret_key + database), and that pi-cron is running.
#
# Usage:
#   ./scripts/smoke-test.sh
#
# Environment overrides:
#   PI_SMOKE_URL       Base URL of the pi service   (default: http://localhost:8080)
#   PI_SMOKE_ADMIN     Bootstrap admin username     (default: $BOOTSTRAP_ADMIN or "admin")
#   PI_SMOKE_PASSWORD  Bootstrap admin password     (default: secrets/bootstrap_admin_password)
#   PI_SMOKE_TIMEOUT   Seconds to wait for readiness (default: 120)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${BASE_DIR}/compose.yaml"

BASE_URL="${PI_SMOKE_URL:-http://localhost:8080}"
ADMIN_USER="${PI_SMOKE_ADMIN:-${BOOTSTRAP_ADMIN:-admin}}"
TIMEOUT="${PI_SMOKE_TIMEOUT:-120}"

ADMIN_PASSWORD="${PI_SMOKE_PASSWORD:-}"
if [[ -z "${ADMIN_PASSWORD}" && -f "${BASE_DIR}/secrets/bootstrap_admin_password" ]]; then
    ADMIN_PASSWORD="$(cat "${BASE_DIR}/secrets/bootstrap_admin_password")"
fi
if [[ -z "${ADMIN_PASSWORD}" ]]; then
    echo "ERROR: no admin password. Set PI_SMOKE_PASSWORD or create secrets/bootstrap_admin_password."
    exit 1
fi

fail() {
    echo "SMOKE TEST FAILED: $*" >&2
    exit 1
}

echo "[smoke] Waiting up to ${TIMEOUT}s for ${BASE_URL}/healthz/readyz ..."
deadline=$((SECONDS + TIMEOUT))
until curl -fsS -o /dev/null "${BASE_URL}/healthz/readyz" 2>/dev/null; do
    if (( SECONDS >= deadline )); then
        echo "[smoke] Last readiness response:"
        curl -sS -i "${BASE_URL}/healthz/readyz" || true
        fail "pi did not become ready within ${TIMEOUT}s"
    fi
    sleep 3
done
echo "[smoke] pi is ready."

# A successful /auth proves the DB URI, enckey, pepper and secret_key are all
# wired correctly — the admin password can only verify if the pepper matches.
echo "[smoke] Authenticating as '${ADMIN_USER}' ..."
auth_response="$(curl -fsS -X POST "${BASE_URL}/auth" \
    --data-urlencode "username=${ADMIN_USER}" \
    --data-urlencode "password=${ADMIN_PASSWORD}")" \
    || fail "POST /auth request failed"

if ! echo "${auth_response}" | grep -q '"token"'; then
    echo "[smoke] /auth response: ${auth_response}"
    fail "no token in /auth response"
fi
echo "[smoke] Admin authentication succeeded."

echo "[smoke] Checking pi-cron ..."
if ! docker compose -f "${COMPOSE_FILE}" ps --services --filter "status=running" | grep -q "^pi-cron$"; then
    fail "pi-cron is not running"
fi
if ! docker compose -f "${COMPOSE_FILE}" logs pi-cron 2>/dev/null | grep -q "\[pi-cron\] Starting"; then
    fail "pi-cron did not log its startup banner"
fi
echo "[smoke] pi-cron is running."

echo "[smoke] All checks passed."
