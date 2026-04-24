#!/bin/bash
set -e

# Entrypoint for the Galera db-1 / db-2 services. Handles:
#   - new cluster bootstrap vs secondary node join (by comparing NODE_NAME
#     to BOOTSTRAP_NODE on first run, or reading grastate.dat on subsequent
#     runs to detect safe_to_bootstrap: 1)
#   - TLS for Galera cluster replication (wsrep_provider_options socket.ssl)
#   - Client/server TLS for all MariaDB connections
#   - wsrep_sst_auth written to a config file instead of the CLI, so the
#     root password does not appear in `ps`

GRASTATE="/var/lib/mysql/grastate.dat"
TARGET_MESH="gcomm://${CLUSTER_NODES}"

# ── Cluster address: bootstrap vs join ───────────────────────────────────────
if [ -f "$GRASTATE" ]; then
    if grep -q 'safe_to_bootstrap: 1' "$GRASTATE"; then
        echo "[Recovery] safe_to_bootstrap: 1. Bootstrapping cluster..."
        CLUSTER_ADDR="gcomm://"
    else
        echo "[Recovery] Standard node detected. Joining cluster at $TARGET_MESH..."
        CLUSTER_ADDR="$TARGET_MESH"
    fi
else
    if [ "$NODE_NAME" = "$BOOTSTRAP_NODE" ]; then
        echo "[Init] First run for designated bootstrap node ($NODE_NAME). Initializing new cluster..."
        CLUSTER_ADDR="gcomm://"
    else
        echo "[Init] First run for secondary node ($NODE_NAME). Joining cluster at $TARGET_MESH..."
        CLUSTER_ADDR="$TARGET_MESH"
    fi
fi

# ── TLS material paths (mounted via docker secrets) ──────────────────────────
CA_PATH=/run/secrets/galera_ca
CERT_PATH=/run/secrets/galera_node_cert
KEY_PATH=/run/secrets/galera_node_key
for p in "$CA_PATH" "$CERT_PATH" "$KEY_PATH"; do
    if [ ! -f "$p" ]; then
        echo "FATAL: TLS material missing at $p" >&2
        echo "       Run ./scripts/gen-galera-certs.sh before starting the stack." >&2
        exit 1
    fi
done

# Galera/mariadb requires the key readable by the mysql user. Docker secrets
# are owned by root with mode 0400; copy into a location mysql can read.
mkdir -p /etc/mysql/tls
cp "$CA_PATH"   /etc/mysql/tls/ca.pem
cp "$CERT_PATH" /etc/mysql/tls/node.pem
cp "$KEY_PATH"  /etc/mysql/tls/node.key
chown -R mysql:mysql /etc/mysql/tls
chmod 600 /etc/mysql/tls/node.key
chmod 644 /etc/mysql/tls/ca.pem /etc/mysql/tls/node.pem

# ── wsrep_sst_auth via config file (not CLI) ─────────────────────────────────
# The auth value used to be passed via --wsrep_sst_auth on the command line,
# making the root password visible in `ps aux`. Writing it to a protected
# config file keeps it off the process listing.
SST_AUTH="root:$(cat /run/secrets/mariadb_root_password)"
SST_CNF=/etc/mysql/conf.d/99-sst-auth.cnf
cat > "$SST_CNF" <<EOF
[mysqld]
wsrep_sst_auth = $SST_AUTH
EOF
chown mysql:mysql "$SST_CNF"
chmod 600 "$SST_CNF"

# ── Galera provider options ──────────────────────────────────────────────────
# socket.ssl=yes turns on TLS for cluster replication traffic (port 4567,
# write-set replication and IST on 4568). Every node presents its own cert,
# signed by the shared CA; peers verify against socket.ssl_ca.
WSREP_OPTS="gcache.size=1G"
WSREP_OPTS="${WSREP_OPTS};socket.ssl=yes"
WSREP_OPTS="${WSREP_OPTS};socket.ssl_ca=/etc/mysql/tls/ca.pem"
WSREP_OPTS="${WSREP_OPTS};socket.ssl_cert=/etc/mysql/tls/node.pem"
WSREP_OPTS="${WSREP_OPTS};socket.ssl_key=/etc/mysql/tls/node.key"

echo "Starting MariaDB Galera Node: $NODE_NAME (TLS enabled for cluster traffic)"
exec docker-entrypoint.sh mariadbd \
  --max-connect-errors=999999999 \
  --skip-name-resolve \
  --wsrep_on=ON \
  --wsrep_provider=/usr/lib/galera/libgalera_smm.so \
  --wsrep_cluster_name=pi-cluster \
  --wsrep_cluster_address="$CLUSTER_ADDR" \
  --wsrep_node_name="$NODE_NAME" \
  --wsrep_node_address="$NODE_NAME" \
  --wsrep_sst_method=mariabackup \
  --wsrep_slave_threads=4 \
  --wsrep_provider_options="$WSREP_OPTS" \
  --ssl-ca=/etc/mysql/tls/ca.pem \
  --ssl-cert=/etc/mysql/tls/node.pem \
  --ssl-key=/etc/mysql/tls/node.key \
  --binlog_format=ROW \
  --default-storage-engine=InnoDB \
  --innodb_autoinc_lock_mode=2 \
  --innodb_flush_log_at_trx_commit=2 \
  --innodb_buffer_pool_size=512M
