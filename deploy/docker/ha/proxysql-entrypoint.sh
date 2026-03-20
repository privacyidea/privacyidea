#!/bin/sh
set -e

# Read secrets from Docker secret files
MARIADB_PASSWORD=$(cat /run/secrets/mariadb_password)
MARIADB_ROOT_PASSWORD=$(cat /run/secrets/mariadb_root_password)

# Read admin password from Docker secret file
ADMIN_PASSWORD=$(cat /run/secrets/proxysql_admin_password)

# Generate ProxySQL configuration from template with actual passwords
cat > /etc/proxysql.cnf <<EOF
admin_variables = {
    admin_credentials="admin:${ADMIN_PASSWORD}"
    mysql_ifaces="0.0.0.0:6032"
}

mysql_variables = {
    threads=4
    max_connections=2048
    interfaces="0.0.0.0:3306"

    # The user ProxySQL uses to ping the databases and check Galera state.
    # We are using the root user here to guarantee access to information_schema.
    monitor_username="root"
    monitor_password="${MARIADB_ROOT_PASSWORD}"

    # Ping the database every 2 seconds
    monitor_galera_healthcheck_interval=2000
    monitor_galera_healthcheck_max_timeout_count=3
}

# Define the physical nodes
# db-1 starts in writer hostgroup (10), db-2 starts in backup_writer (20)
mysql_servers = (
    { address="db-1", port=3306, hostgroup=10, max_connections=1000 },
    { address="db-2", port=3306, hostgroup=20, max_connections=1000 }
)

# The core Galera state machine logic
mysql_galera_hostgroups = (
    {
        writer_hostgroup=10
        backup_writer_hostgroup=20
        reader_hostgroup=30
        offline_hostgroup=40
        active=1
        # max_writers=1 forces an Active/Passive setup.
        # ProxySQL will keep db-1 in HG 10 and move db-2 to HG 20.
        max_writers=1
        writer_is_also_reader=1
        max_transactions_behind=100
    }
)

# The application user ProxySQL will intercept and route
mysql_users = (
    {
        username="pi"
        password="${MARIADB_PASSWORD}"
        default_hostgroup=10
        max_connections=100
        active=1
    }
)
EOF

echo "ProxySQL configuration generated with passwords from Docker secrets"

# Start ProxySQL with the official entrypoint
exec /usr/bin/proxysql -f --idle-threads
