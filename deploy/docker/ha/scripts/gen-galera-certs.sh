#!/bin/bash
# Generate a CA and per-node TLS certs for Galera cluster communication.
#
# Output: secrets/tls/{ca.pem,ca.key,db-1.pem,db-1.key,db-2.pem,db-2.key}
#
# Galera uses the certs for cluster traffic (ports 4567/4568, IST, write-set
# replication). All nodes trust the same CA; each node presents its own cert.
#
# Usage:
#   ./scripts/gen-galera-certs.sh          # skip existing files
#   ./scripts/gen-galera-certs.sh --force  # regenerate everything
#
# NOTE: the CA private key is stored alongside the other secrets for simplicity.
# In production, the CA key should be kept offline once the node certs are issued.

set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
HA_DIR="$(cd "$HERE/.." && pwd)"
TLS_DIR="$HA_DIR/secrets/tls"

FORCE="${1:-}"
NODES="db-1 db-2"
DAYS_CA=3650   # 10 years
DAYS_NODE=1825 #  5 years

mkdir -p "$TLS_DIR"

_skip_or_force() {
    local path="$1"
    if [ -e "$path" ] && [ "$FORCE" != "--force" ]; then
        echo "exists: $path (use --force to regenerate)"
        return 1
    fi
    return 0
}

# ── CA ───────────────────────────────────────────────────────────────────────
if _skip_or_force "$TLS_DIR/ca.pem"; then
    echo "generating CA..."
    openssl genrsa -out "$TLS_DIR/ca.key" 4096 2>/dev/null
    openssl req -new -x509 -nodes -days "$DAYS_CA" \
        -key "$TLS_DIR/ca.key" \
        -out "$TLS_DIR/ca.pem" \
        -subj "/CN=privacyIDEA HA Galera CA" 2>/dev/null
    chmod 600 "$TLS_DIR/ca.key"
    chmod 644 "$TLS_DIR/ca.pem"
fi

# ── per-node certs ───────────────────────────────────────────────────────────
for node in $NODES; do
    if _skip_or_force "$TLS_DIR/$node.pem"; then
        echo "generating cert for $node..."
        openssl genrsa -out "$TLS_DIR/$node.key" 2048 2>/dev/null
        openssl req -new \
            -key "$TLS_DIR/$node.key" \
            -out "$TLS_DIR/$node.csr" \
            -subj "/CN=$node" 2>/dev/null

        # SAN matching node name (Galera/mariabackup may verify hostname)
        cat > "$TLS_DIR/$node.ext" <<EOF
subjectAltName = DNS:$node, DNS:localhost, IP:127.0.0.1
extendedKeyUsage = serverAuth, clientAuth
EOF

        openssl x509 -req -days "$DAYS_NODE" \
            -in "$TLS_DIR/$node.csr" \
            -CA "$TLS_DIR/ca.pem" -CAkey "$TLS_DIR/ca.key" \
            -CAcreateserial \
            -out "$TLS_DIR/$node.pem" \
            -extfile "$TLS_DIR/$node.ext" 2>/dev/null

        rm -f "$TLS_DIR/$node.csr" "$TLS_DIR/$node.ext"
        chmod 600 "$TLS_DIR/$node.key"
        chmod 644 "$TLS_DIR/$node.pem"
    fi
done

# Clean up CA serial
rm -f "$TLS_DIR/ca.srl"

echo "TLS materials in $TLS_DIR:"
ls -la "$TLS_DIR"
