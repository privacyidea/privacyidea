#!/bin/sh
# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
set -eu

# If a command was passed to the container (e.g.
# `docker compose run --rm pi pi-manage ...`), run it directly instead of the web
# server. The app config, database and secrets still come from DockerConfig and
# the mounted /run/secrets. Normal compose services pass no command, so this is
# skipped for them ($# == 0).
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# The application config (DockerConfig, selected by PI_CONFIG_NAME=docker) reads
# the database URI, enckey, pepper and secret_key directly from the PI_DB_*,
# PI_ENCFILE, PI_PEPPER_FILE and PI_SECRET_KEY_FILE variables set in the compose
# file. The same config is loaded by pi-manage, so migrations and admin creation
# below see the same credentials — nothing to construct here.
#
# The bootstrap admin password is the one value DockerConfig does not know about,
# so load it from its secret file if it was not passed in directly.
if [ -z "${PI_BOOTSTRAP_ADMIN_PASSWORD:-}" ] && [ -f /run/secrets/bootstrap_admin_password ]; then
    PI_BOOTSTRAP_ADMIN_PASSWORD="$(cat /run/secrets/bootstrap_admin_password)"
    export PI_BOOTSTRAP_ADMIN_PASSWORD
fi

# Fail closed on audit signing. Without the keypair, privacyIDEA silently disables
# audit-log AND response signing — refuse to start instead, unless the operator
# has explicitly opted out with PRIVACYIDEA_PI_AUDIT_NO_SIGN=true. (In the bundled
# compose the keypair is a mandatory secret, so this mainly guards hand-rolled
# runs / removed mounts.)
if [ ! -f /run/secrets/audit_key_private ] || [ ! -f /run/secrets/audit_key_public ]; then
    case "$(printf '%s' "${PRIVACYIDEA_PI_AUDIT_NO_SIGN:-}" | tr '[:upper:]' '[:lower:]')" in
        true|1|yes)
            echo "Audit signing keys absent and PRIVACYIDEA_PI_AUDIT_NO_SIGN is set — running unsigned." >&2
            ;;
        *)
            echo "FATAL: audit signing keypair not found at /run/secrets/audit_key_{private,public}." >&2
            echo "  Run 'make init' to generate it, or set PRIVACYIDEA_PI_AUDIT_NO_SIGN=true to run unsigned." >&2
            exit 1
            ;;
    esac
fi

DELAY="${PI_STARTUP_DELAY:-0}"
# Guard against a non-integer value (e.g. "5s") — the arithmetic test would
# otherwise print a shell error. Fall back to no delay.
case "$DELAY" in
    ''|*[!0-9]*)
        echo "WARNING: PI_STARTUP_DELAY=${DELAY} is not an integer; ignoring." >&2
        DELAY=0
        ;;
esac
if [ "$DELAY" -gt 0 ]; then
    echo "Waiting for ${DELAY} seconds before startup..."
    sleep "$DELAY"
fi

# Calculate standard Gunicorn recommendation based on host cores with a cap of 4.
# This can still be overwritten with PI_WORKERS
CAP=$(( 4 ))
CALCULATED=$(( $(nproc) * 2 + 1 ))
if [ "$CALCULATED" -gt "$CAP" ]; then
    DEFAULT_WORKERS="$CAP"
else
    DEFAULT_WORKERS="$CALCULATED"
fi
WORKERS="${PI_WORKERS:-$DEFAULT_WORKERS}"

# Set FLASK_APP so the flask CLI can find the app for running migrations
export FLASK_APP="privacyidea.app:create_docker_app()"

# Schema setup. create_tables and db upgrade are NOT interchangeable and must not
# both run against the same database:
#   - Fresh (empty) database: create_tables builds the schema and stamps alembic
#     at head. Running migrations afterwards is a no-op.
#   - Existing database: db upgrade applies pending migrations. create_tables must
#     NOT run — it does not ALTER existing tables but would still stamp alembic at
#     head, silently skipping real migrations.
# We therefore inspect the database once and pick the correct action, so the same
# init container works for both first-time setup and later upgrades.
#
# WARNING: only run this from a single container. Concurrent create_tables/upgrade
# across replicas can corrupt the schema.
if [ "${PI_CREATE_TABLES:-false}" = "true" ] || [ "${PI_RUN_MIGRATIONS:-false}" = "true" ]; then
    # Probe the schema. Exit 0 = has tables, 1 = empty, 2 = could not determine
    # (e.g. DB unreachable). A probe error must NOT be treated as "empty" — that
    # could run create_tables against a populated DB and mis-stamp it — so abort.
    set +e
    python3 -c "
import sys
from sqlalchemy import inspect
from privacyidea.app import create_app
from privacyidea.models import db
try:
    with create_app('docker', silent=True).app_context():
        has_tables = bool(inspect(db.engine).get_table_names())
except Exception as exc:
    sys.stderr.write(f'Database probe failed: {exc}\n')
    sys.exit(2)
sys.exit(0 if has_tables else 1)
"
    PROBE_RC=$?
    set -e
    if [ "$PROBE_RC" -eq 0 ]; then
        DB_EMPTY=false
    elif [ "$PROBE_RC" -eq 1 ]; then
        DB_EMPTY=true
    else
        echo "ERROR: could not determine database state (probe exit ${PROBE_RC}). Aborting." >&2
        exit 1
    fi

    if [ "${PI_CREATE_TABLES:-false}" = "true" ] && [ "$DB_EMPTY" = "true" ]; then
        echo "Empty database detected — creating tables (stamps schema at head)..."
        if ! pi-manage create_tables; then
            echo "ERROR: Table creation failed. Aborting startup." >&2
            exit 1
        fi
        echo "Database tables created successfully."
    elif [ "${PI_RUN_MIGRATIONS:-false}" = "true" ] && [ "$DB_EMPTY" = "false" ]; then
        echo "Existing database detected — running migrations..."
        if ! pi-manage db upgrade; then
            echo "ERROR: Database migration failed. Aborting startup." >&2
            exit 1
        fi
        echo "Database migrations complete."
    elif [ "$DB_EMPTY" = "true" ]; then
        echo "Empty database, but PI_CREATE_TABLES is not set — nothing to do." >&2
    else
        echo "Database already initialized; nothing to do."
    fi
fi

# Bootstrap admin account
if [ -n "${PI_BOOTSTRAP_ADMIN:-}" ] && [ -n "${PI_BOOTSTRAP_ADMIN_PASSWORD:-}" ]; then
    echo "Bootstrapping local admin account..."

    # Execute the command, merge stderr to stdout (2>&1), and capture it in a variable.
    # The 'if' statement prevents 'set -e' from crashing the script on failure.
    if ADMIN_OUT=$(pi-manage admin add "${PI_BOOTSTRAP_ADMIN}" -p "${PI_BOOTSTRAP_ADMIN_PASSWORD}" 2>&1); then
        echo "Local Admin created successfully."
    else
        echo "Admin creation skipped or failed. Output: ${ADMIN_OUT}"
    fi
fi

# PI_INIT_ONLY: run migrations/bootstrap then exit (used by pi-init container)
if [ "${PI_INIT_ONLY:-false}" = "true" ]; then
    # Install the enckey canary so pi workers can verify the enckey on every start.
    # Idempotent — re-running pi-init on an existing deployment leaves the canary
    # row untouched.
    echo "Installing enckey canary..."
    python3 /opt/privacyidea/enckey-canary.py install || echo "WARNING: enckey canary install failed"

    echo "Initialization complete. PI_INIT_ONLY is true. Exiting..."
    exit 0
fi

# Verify the enckey canary before starting gunicorn. Exit 2 = wrong enckey or the
# check could not complete (hard fail). Exit 1 = canary missing (warn and continue,
# so deployments that predate the canary still start). Exit 0 = OK.
echo "Verifying enckey canary..."
set +e
python3 /opt/privacyidea/enckey-canary.py verify
CANARY_RC=$?
set -e
if [ "$CANARY_RC" -eq 2 ]; then
    echo "FATAL: enckey canary verification failed. Refusing to start." >&2
    exit 2
fi

# PI_CRON_MODE: run the maintenance task scheduler (used by pi-cron container)
if [ "${PI_CRON_MODE:-false}" = "true" ]; then
    echo "Starting in cron mode..."
    exec python3 /opt/privacyidea/cron-runner.py
fi

# Default: web server. The port is fixed at 8080 (the image EXPOSE, both
# healthchecks and the compose port mapping all assume it); remap on the host
# via the compose "ports:" entry rather than changing it here.
echo "Starting gunicorn with ${WORKERS} workers on port 8080..."
exec python3 -m gunicorn \
    --workers "${WORKERS}" \
    --worker-tmp-dir /dev/shm \
    --bind "0.0.0.0:8080" \
    --access-logfile - \
    --error-logfile - \
    'privacyidea.app:create_docker_app()'
