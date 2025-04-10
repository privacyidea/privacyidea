#!/bin/sh
set -eu

# For now we just start the gunicorn process
# TODO: make number of processes and port configurable
exec python -m gunicorn --worker-tmp-dir /dev/shm -w 2 --bind 0.0.0.0:8080 'privacyidea.app:create_app()'
