#!/usr/bin/env bash
# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
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

# Never pipe a command into "grep -q". grep exits on its first match, and with the
# "pipefail" set above the writer then fails on the closed pipe and takes the whole
# pipeline down with it — curl reports exit 23 for that, sometimes without printing
# anything, so a correct answer is reported as a failed check. Everything below reads
# the output into a variable first and matches on it with the shell.

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

if [[ "${auth_response}" != *'"token"'* ]]; then
    echo "[smoke] /auth response: ${auth_response}"
    fail "no token in /auth response"
fi
echo "[smoke] Admin authentication succeeded."

# The image builds the WebUI in its own stage and the package is installed from the source tree,
# so this is the first point where the build, the packaging and the server meet. Everything else
# in CI runs from a checkout, where the WebUI is found whether or not it was packaged.
echo "[smoke] Checking the WebUI ..."
root_response="$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' "${BASE_URL}/")"
case "${root_response}" in
    "302 "*"/app/v2/") ;;
    *) fail "GET / answered '${root_response}', expected a redirect to /app/v2/" ;;
esac

# The status code is appended on its own line, so a wrong answer can be reported with
# its code instead of only "not the WebUI".
webui_response="$(curl -sS -w '\n%{http_code}' "${BASE_URL}/app/v2/")" \
    || fail "GET /app/v2/ request failed"
webui_status="${webui_response##*$'\n'}"
webui_page="${webui_response%$'\n'*}"
if [[ "${webui_status}" != "200" || "${webui_page}" != *'<base href='* ]]; then
    echo "[smoke] GET /app/v2/ answered HTTP ${webui_status}, first 300 characters of the body:"
    printf '%.300s\n' "${webui_page}"
    fail "GET /app/v2/ did not answer with the WebUI"
fi

curl -fsS -o /dev/null "${BASE_URL}/static/public/policy-templates/index.json" \
    || fail "the WebUI assets below /static/public/ are not served"
echo "[smoke] The WebUI is served."

echo "[smoke] Checking pi-cron ..."
# Wrapped in newlines so the match is anchored to a whole service name.
running_services=$'\n'"$(docker compose -f "${COMPOSE_FILE}" ps --services --filter "status=running")"$'\n'
if [[ "${running_services}" != *$'\npi-cron\n'* ]]; then
    fail "pi-cron is not running, running services:${running_services//$'\n'/ }"
fi
cron_logs="$(docker compose -f "${COMPOSE_FILE}" logs pi-cron 2>/dev/null)"
if [[ "${cron_logs}" != *"[pi-cron] Starting"* ]]; then
    fail "pi-cron did not log its startup banner"
fi
echo "[smoke] pi-cron is running."

echo "[smoke] All checks passed."
