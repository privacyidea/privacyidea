#!/bin/sh
set -eu

# Load sensitive values from Docker secret files if env vars are not set.
# This allows secrets to be mounted via Docker secrets instead of plain env vars.
if [ -z "${SECRET_KEY:-}" ] && [ -f /run/secrets/secret_key ]; then
    export SECRET_KEY=$(cat /run/secrets/secret_key)
fi
if [ -z "${PI_PEPPER:-}" ] && [ -f /run/secrets/pi_pepper ]; then
    export PI_PEPPER=$(cat /run/secrets/pi_pepper)
fi
if [ -z "${PI_BOOTSTRAP_ADMIN_PASSWORD:-}" ] && [ -f /run/secrets/bootstrap_admin_password ]; then
    export PI_BOOTSTRAP_ADMIN_PASSWORD=$(cat /run/secrets/bootstrap_admin_password)
fi
# Construct SQLALCHEMY_DATABASE_URI from parts + mariadb_password secret if not provided directly.
# DB_HOST, DB_USER, DB_NAME can be set as env vars; they default to the single-node compose values.
if [ -z "${SQLALCHEMY_DATABASE_URI:-}" ] && [ -f /run/secrets/mariadb_password ]; then
    _db_pass=$(cat /run/secrets/mariadb_password)
    export SQLALCHEMY_DATABASE_URI="mysql+pymysql://${DB_USER:-pi}:${_db_pass}@${DB_HOST:-localhost}:${DB_PORT:-3306}/${DB_NAME:-pi}"
    unset _db_pass
fi

DELAY="${PI_STARTUP_DELAY:-0}"
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

# Port to bind gunicorn to (default: 8080)
PORT="${PI_PORT:-8080}"

# Set FLASK_APP so the flask CLI can find the app for running migrations
export FLASK_APP="privacyidea.app:create_docker_app()"

# Create Tables PI_CREATE_TABLES
if [ "${PI_CREATE_TABLES:-false}" = "true" ]; then
    echo "Creating database tables for a fresh installation..."
    if ! pi-manage create_tables; then
        echo "ERROR: Table creation failed. Aborting startup." >&2
        exit 1
    fi
    echo "Database tables created successfully."
fi

# Run database migrations only if PI_RUN_MIGRATIONS is set to "true".
# WARNING: Do not enable this if running multiple replicas simultaneously,
# as concurrent migrations can cause data corruption.
# For Kubernetes, use an init container to run migrations instead.
if [ "${PI_RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations..."
    if ! pi-manage db upgrade; then
        echo "ERROR: Database migration failed. Aborting startup." >&2
        exit 1
    fi
    echo "Database migrations complete."
else
    echo "Skipping automatic database migrations (set PI_RUN_MIGRATIONS=true to enable)."
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

# If this container is designated purely as an initialization job,
# exit cleanly before spawning the permanent web server.
if [ "${PI_INIT_ONLY:-false}" = "true" ]; then
    echo "Initialization complete. PI_INIT_ONLY is true. Exiting..."
    exit 0
fi

echo "Starting gunicorn with ${WORKERS} workers on port ${PORT}..."
exec python3 -m gunicorn \
    --workers "${WORKERS}" \
    --worker-tmp-dir /dev/shm \
    --bind "0.0.0.0:${PORT}" \
    --access-logfile - \
    --error-logfile - \
    'privacyidea.app:create_docker_app()'
