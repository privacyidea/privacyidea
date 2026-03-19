#!/bin/sh
set -eu

DELAY="${PI_STARTUP_DELAY:-0}"
if [ "$DELAY" -gt 0 ]; then
    echo "Sleeping for ${DELAY} seconds to let infrastructure stabilize..."
    sleep "$DELAY"
fi

# Number of gunicorn worker processes (default: 2 * CPU cores + 1)
WORKERS="${PI_WORKERS:-$(( $(nproc) * 2 + 1 ))}"

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

echo "Starting gunicorn with ${WORKERS} workers on port ${PORT}..."
exec python3 -m gunicorn \
    --workers "${WORKERS}" \
    --worker-tmp-dir /dev/shm \
    --bind "0.0.0.0:${PORT}" \
    --access-logfile - \
    --error-logfile - \
    'privacyidea.app:create_docker_app()'
