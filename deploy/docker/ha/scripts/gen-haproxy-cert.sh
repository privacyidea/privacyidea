#!/bin/bash
# Generate a self-signed TLS cert for HAProxy.
#
# Output: secrets/haproxy/cert.pem (concatenated cert+key, HAProxy's preferred format)
#
# Intended for development / first-run installs where the customer has not yet
# supplied their own cert. At deploy time the customer replaces cert.pem with
# their own fullchain+key (same file, same path) and restarts pi-proxy. No
# compose changes needed.
#
# Usage:
#   ./scripts/gen-haproxy-cert.sh                 # self-signed, CN=<hostname>
#   ./scripts/gen-haproxy-cert.sh mypi.example.com  # CN=<arg>
#   ./scripts/gen-haproxy-cert.sh --force mypi.example.com  # overwrite existing

set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
HA_DIR="$(cd "$HERE/.." && pwd)"
OUT_DIR="$HA_DIR/secrets/haproxy"
OUT_FILE="$OUT_DIR/cert.pem"

FORCE=0
if [ "${1:-}" = "--force" ]; then
    FORCE=1
    shift
fi

CN="${1:-$(hostname -f 2>/dev/null || hostname)}"

if [ -f "$OUT_FILE" ] && [ "$FORCE" -eq 0 ]; then
    echo "exists: $OUT_FILE (use --force to regenerate)"
    exit 0
fi

mkdir -p "$OUT_DIR"

echo "generating self-signed cert for CN=$CN..."
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

openssl req -x509 -nodes -newkey rsa:2048 \
    -days 365 \
    -subj "/CN=$CN" \
    -addext "subjectAltName = DNS:$CN, DNS:localhost, IP:127.0.0.1" \
    -keyout "$TMPDIR/key.pem" \
    -out "$TMPDIR/cert.pem" 2>/dev/null

# HAProxy wants cert + key in one file (cert first, then key).
# Mode 644: the file is bind-mounted into the haproxy container which runs
# as a non-root user. Stricter host modes (600 owned by root) would be
# unreadable from inside the container. On-host access control for this
# file should be handled at the filesystem / user level.
cat "$TMPDIR/cert.pem" "$TMPDIR/key.pem" > "$OUT_FILE"
chmod 644 "$OUT_FILE"

echo "wrote $OUT_FILE (self-signed, expires in 365 days)"
echo "CN=$CN, SAN: DNS:$CN, DNS:localhost, IP:127.0.0.1"
echo ""
echo "Replace with a production cert by overwriting this file with your"
echo "fullchain+key concatenated (cert first, then key), same path, mode 600,"
echo "then: docker compose restart pi-proxy"
