#!/bin/bash
set -e

# This entrypoint script is designed to handle both the initialization of a new MariaDB Galera cluster and the recovery
# of existing nodes. It checks for the presence of the grastate.dat file to determine if it's a recovery scenario, and
# uses environment variables to identify the bootstrap node and construct the cluster address dynamically.

GRASTATE="/var/lib/mysql/grastate.dat"
# Construct the target mesh dynamically from the compose variable
TARGET_MESH="gcomm://${CLUSTER_NODES}"

# Check if grastate.dat exists to determine if this is a recovery scenario or a initialization
if [ -f "$GRASTATE" ]; then
    if grep -q 'safe_to_bootstrap: 1' "$GRASTATE"; then
        echo "[Recovery] safe_to_bootstrap: 1. Bootstrapping cluster..."
        CLUSTER_ADDR="gcomm://"
    else
        echo "[Recovery] Standard node detected. Joining cluster at $TARGET_MESH..."
        CLUSTER_ADDR="$TARGET_MESH"
    fi

# Otherwise, its an initialization scenario. Determine if this is the designated bootstrap node or a secondary.
else
    # Compare this container's specific name to the designated bootstrap master
    if [ "$NODE_NAME" = "$BOOTSTRAP_NODE" ]; then
        echo "[Init] First run for designated bootstrap node ($NODE_NAME). Initializing new cluster..."
        CLUSTER_ADDR="gcomm://"
    else
        echo "[Init] First run for secondary node ($NODE_NAME). Joining cluster at $TARGET_MESH..."
        CLUSTER_ADDR="$TARGET_MESH"
    fi
fi

echo "Starting MariaDB Galera Node: $NODE_NAME"
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
  --wsrep_sst_auth="root:$(cat /run/secrets/mariadb_root_password)" \
  --wsrep_slave_threads=4 \
  --wsrep_provider_options="gcache.size=1G" \
  --binlog_format=ROW \
  --default-storage-engine=InnoDB \
  --innodb_autoinc_lock_mode=2 \
  --innodb_flush_log_at_trx_commit=2 \
  --innodb_buffer_pool_size=512M