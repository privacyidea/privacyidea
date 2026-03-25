# PrivacyIDEA High Availability Deployment

Docker Compose setup with:
- 2x PrivacyIDEA application instances (load balanced)
- 1x PrivacyIDEA cron container (maintenance tasks)
- 2x MariaDB Galera cluster nodes (active-passive replication)
- HAProxy (web load balancer)
- ProxySQL (database proxy with failover)

## Quick Start

### 1. Generate Secrets

All sensitive credentials are stored as files in the `secrets/` directory and mounted
into containers via Docker secrets — never as plain environment variables.

```bash
cd secrets
# Encryption key for PrivacyIDEA tokens
python3 -c "import os; print(os.urandom(96).hex())" > enckey

# Flask session encryption key
python3 -c "import secrets; print(secrets.token_hex(32))" > secret_key

# PrivacyIDEA pepper for additional password hashing
python3 -c "import secrets; print(secrets.token_hex(32))" > pi_pepper

# MariaDB application user password
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_password

# MariaDB root password
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_root_password

# ProxySQL admin interface password
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > proxysql_admin_password

# Initial PrivacyIDEA admin account password
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > bootstrap_admin_password

chmod 600 *
cd ..
```

### 2. Configure Environment (Optional)

The `.env` file only contains non-sensitive configuration. The defaults are sufficient
for most deployments.

```bash
cp .env.template .env
# Optionally edit .env to change the bootstrap admin username or tuning parameters
```

### 3. Start the Stack

```bash
docker compose -f ha-compose.yaml up -d
```

### 4. Verify Health

```bash
docker compose -f ha-compose.yaml ps
```

All services should show `(healthy)` status.

## Architecture

```
Internet
    ↓
HAProxy (pi-proxy) :8000
    ↓
    ├─→ pi-1:8080  ─┐
    └─→ pi-2:8080  ─┤──→ ProxySQL (db-proxy) :3306
                    │         ↓
pi-cron  ───────────┘    ├─→ db-1:3306 (primary)
(maintenance tasks)      └─→ db-2:3306 (backup)
```

**Services:**

| Service | Role | Replicas |
|---------|------|----------|
| `pi-proxy` | HAProxy — TLS termination, load balancing | 1 |
| `pi` | PrivacyIDEA web workers (gunicorn) | 2 (scalable) |
| `pi-init` | One-shot: migrations + bootstrap admin | 1 (exits after init) |
| `pi-cron` | Scheduled maintenance tasks | **1 (must not scale)** |
| `db-proxy` | ProxySQL — DB load balancing, failover | 1 |
| `db-1`, `db-2` | MariaDB Galera cluster | 2 |

## Management Commands

### View Logs
```bash
docker compose -f ha-compose.yaml logs -f [service]
```

### Restart Services
```bash
docker compose -f ha-compose.yaml restart [service]
```

### Scale Workers
```bash
docker compose -f ha-compose.yaml up -d --scale pi=3
```

### Access ProxySQL Admin
```bash
docker exec -it ha-db-proxy-1 mysql \
  -h 127.0.0.1 -P 6032 \
  -u admin -p$(cat secrets/proxysql_admin_password)
```

#### Reading the ProxySQL hostgroup state

```bash
docker exec ha-db-proxy-1 mysql \
  -h 127.0.0.1 -P 6032 \
  -u admin -p$(cat secrets/proxysql_admin_password) \
  -e "SELECT hostgroup_id, hostname, status FROM runtime_mysql_servers ORDER BY hostgroup_id, hostname;"
```

**Hostgroup IDs:**

| HG | Role |
|----|------|
| 10 | Writer — all INSERT/UPDATE/DELETE |
| 20 | Backup writer — promoted when HG 10 has no ONLINE node |
| 30 | Readers — all synced nodes, read traffic distributed here |
| 40 | Offline — nodes being removed or recovering |

**Status values:**

| Status | Meaning |
|--------|---------|
| `ONLINE` | Healthy, receiving traffic |
| `OFFLINE_SOFT` | Node up but not fully synced (Galera state < 4). Finishes existing connections, no new ones. |
| `OFFLINE_HARD` | Unreachable or forcibly removed. No traffic. |
| `SHUNNED` | Connection-layer penalty from repeated errors. Clears automatically. A node can be SHUNNED in one HG and ONLINE in another. |

**Healthy cluster — expected output:**
```
hostgroup_id  hostname  status
10            db-1      ONLINE        ← active writer
20            db-2      ONLINE        ← backup writer
30            db-1      ONLINE        ← both nodes serve reads
30            db-2      ONLINE
```

**During failover** (e.g. db-1 stopped):
```
10            db-2      ONLINE        ← db-2 promoted to writer
20            db-1      OFFLINE_HARD
30            db-2      ONLINE
```

#### Check Galera node sync state directly

```bash
docker exec ha-db-1-1 mysql \
  -u root -p$(cat secrets/mariadb_root_password) \
  -e "SHOW STATUS LIKE 'wsrep_local_state_comment';"
```

| Value | Meaning |
|-------|---------|
| `Synced` | Fully in sync — ProxySQL will promote to ONLINE |
| `Joined` / `Joining` | IST or SST in progress — ProxySQL keeps as OFFLINE_SOFT |
| `Donor/Desynced` | Sending state to another node — temporarily degraded |

Wait for `Synced` before stopping the other DB node for maintenance.

### Maintenance Tasks (pi-cron)

The `pi-cron` container runs scheduled maintenance automatically. No host cron setup required.

| Schedule | Command | Purpose |
|----------|---------|---------|
| Every minute | `pi-manage-cron run_scheduled` | Runs periodic tasks configured in the UI |
| Every hour | `pi-manage challenge cleanup` | Deletes expired authentication challenges |
| Daily (configurable) | `pi-manage audit rotate` | Trims the audit log |

**UI-configured periodic tasks** (EventCounter, SimpleStats, etc.) are picked up automatically.
When configuring a periodic task in the admin UI, set the node to `pi-cron` to target this
container. Tasks with no node restriction also run here.

> **Important:** `pi-cron` must always run as a single replica. Running multiple instances
> simultaneously causes race conditions when deleting audit and challenge rows.

#### Configuration

All settings are optional — the defaults work for most deployments.

| Environment variable | Default | Description |
|----------------------|---------|-------------|
| `PI_CRON_AUDIT_ROTATE` | `true` | Enable/disable audit log rotation |
| `PI_CRON_AUDIT_HOUR` | `2` | Hour of day (0–23) to run rotation |
| `PI_CRON_AUDIT_HIGHWATERMARK` | `50000` | Trigger rotation when entry count exceeds this |
| `PI_CRON_AUDIT_LOWWATERMARK` | `25000` | Keep this many entries after rotation |
| `PI_CRON_AUDIT_AGE` | _(unset)_ | Delete entries older than N days instead of using watermarks |
| `PI_CRON_AUDIT_CHUNKSIZE` | _(unset)_ | Delete in chunks to reduce lock contention on large tables |
| `PI_CRON_CHALLENGE_CLEANUP` | `true` | Enable/disable challenge cleanup |
| `PI_CRON_PERIODIC_TASKS` | `true` | Enable/disable `pi-manage-cron run_scheduled` |

All variables are commented out with their defaults in `ha-compose.yaml` under the `pi-cron` service.

To view cron logs:
```bash
docker compose -f ha-compose.yaml logs -f pi-cron
```

### Database Backup

```bash
./scripts/backup.sh
```

Creates a timestamped archive in `backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz`.

**Archive contents:**

| File | Purpose | Criticality |
|------|---------|-------------|
| `database.sql` | Full logical dump of the `pi` database | Required |
| `enckey` | Token encryption key | **Critical** — tokens unrecoverable without it |
| `pi_pepper` | Password hashing pepper | **Critical** — all logins fail without it |
| `secret_key` | Flask session signing key | Low — only invalidates active sessions |

All three keys and the database must be restored together. A mismatched `enckey` or
`pi_pepper` makes the database unusable.

#### Encrypted backups (recommended)

The default archive is unencrypted. Since it contains your master encryption key,
encrypting backups with [age](https://age-encryption.org/) is strongly recommended.

Install age:
```bash
apt install age   # Debian/Ubuntu
```

**Interactive (passphrase, suitable for manual backups):**
```bash
./scripts/backup.sh --encrypt
```

**Non-interactive (public key, suitable for cron):**
```bash
# Generate a keypair once — store the private key securely off-host
age-keygen -o ~/.age/backup.key
cat ~/.age/backup.key   # contains the public key on the first line

./scripts/backup.sh --encrypt-key age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

To decrypt manually:
```bash
age -d backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz.age > backup.tar.gz
```

#### Where do backups go?

The backup script resolves paths relative to its own location, regardless of where
you call it from. Backups always land in `backups/` next to `ha-compose.yaml` — i.e.
`<ha-dir>/backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz`.

This directory is git-ignored. The `backups/` folder on the same host is **not**
off-site storage — it goes down with the server. Move archives somewhere else:
- A remote server via `rsync` or `scp`
- Object storage (S3, Backblaze B2) via `rclone`
- An encrypted USB drive stored off-site

#### Scheduling with cron

The backup and pruning cron jobs use absolute paths to the scripts. Replace
`/opt/privacyidea-ha` with wherever you have deployed the `ha/` directory.

Add to the host's crontab (`crontab -e`) to run nightly at 02:00:

```
0 2 * * * /opt/privacyidea-ha/scripts/backup.sh --encrypt-key age1xxx >> /var/log/pi-backup.log 2>&1
```

Old backups are not automatically pruned. To keep only the last 30 days:
```
0 3 * * * find /opt/privacyidea-ha/backups/ -name "privacyidea_*.tar.gz*" -mtime +30 -delete
```

### Database Restore

```bash
./scripts/restore.sh backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz
# or for an encrypted archive:
./scripts/restore.sh backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz.age
```

The restore script:
1. Decrypts the archive automatically if it has a `.age` extension
2. Checks that `enckey` and `pi_pepper` in the backup match `secrets/` on this host,
   warning loudly if they differ
3. Prompts for confirmation before dropping data
4. Imports the SQL dump into `db-1`

After restore, restart the workers:
```bash
docker compose -f ha-compose.yaml restart pi
```

## Resource Limits

Default limits per service:
- **pi containers**: 2 CPU, 1GB RAM each
- **pi-cron**: 0.5 CPU, 256MB RAM
- **db containers**: 2 CPU, 2GB RAM each
- **ProxySQL**: 1 CPU, 512MB RAM
- **HAProxy**: 0.5 CPU, 256MB RAM

Adjust in `ha-compose.yaml` under `deploy.resources.limits`

## Failover Testing

### Test Database Failover
```bash
# Stop primary database
docker compose -f ha-compose.yaml stop db-1

# ProxySQL should promote db-2 automatically
# Application should continue working

# Restart db-1
docker compose -f ha-compose.yaml start db-1
```

### Test Application Failover
```bash
# Stop one worker
docker compose -f ha-compose.yaml stop pi-1

# HAProxy should route to pi-2
# No downtime expected
```

## Security Notes

- All secrets are mounted via Docker secrets (`/run/secrets/`) — never stored in env vars
- ProxySQL admin port (6032) is **not** exposed externally
- `.gitignore` prevents committing `secrets/` files and `.env`
- Encryption key (`enckey`) must be backed up securely — loss means token data is unrecoverable

## Troubleshooting

**Unhealthy containers:**
```bash
docker inspect <container> --format='{{json .State.Health}}' | jq
```

**Connection refused:**
- Check that all files in `secrets/` exist and are readable
- Check logs: `docker compose -f ha-compose.yaml logs <service>`

**Database sync issues:**
```bash
docker exec ha-db-1-1 mysql -uroot -p$(cat secrets/mariadb_root_password) -e "SHOW STATUS LIKE 'wsrep%';"
```

## Production Checklist

- [ ] All `secrets/` files generated with strong random values
- [ ] `secrets/enckey` backed up securely off-host
- [ ] Bootstrap admin password changed after first login
- [ ] Firewall restricts ports 3306 and 6032 to trusted hosts only
- [ ] Automated database backups scheduled (cron running `scripts/backup.sh --encrypt-key ...`)
- [ ] Backup archives stored off-host (remote server, object storage, or encrypted media)
- [ ] age keypair generated; private key stored securely off-host
- [ ] Log rotation configured
- [ ] Verify `pi-cron` is running and maintenance tasks appear in logs
- [ ] Adjust audit watermarks/age via `PI_CRON_AUDIT_*` env vars to match expected audit volume
- [ ] Monitoring set up (Prometheus/Grafana)
- [ ] Failover procedures tested and documented
