#!/bin/bash
# Runs during db-1's first bootstrap (mariadb image processes /docker-entrypoint-initdb.d
# once, when the data directory is empty). Creates a minimal-privilege user that ProxySQL
# uses to ping the cluster — replaces the previous use of `root` for monitoring.
#
# Grants: USAGE (connect) + REPLICATION CLIENT (SHOW STATUS / SHOW GLOBAL STATUS,
# including wsrep_* variables for Galera health checks). No data access.
#
# After creation on db-1, the user replicates to db-2 via SST / Galera replication.

set -eu

MONITOR_PASSWORD="$(cat /run/secrets/proxysql_monitor_password)"

mariadb -u root -p"$(cat /run/secrets/mariadb_root_password)" <<SQL
CREATE USER IF NOT EXISTS 'proxysql_monitor'@'%' IDENTIFIED BY '${MONITOR_PASSWORD}';
GRANT USAGE, REPLICATION CLIENT ON *.* TO 'proxysql_monitor'@'%';
FLUSH PRIVILEGES;
SQL

echo "proxysql_monitor user created with minimal-privilege grants"
