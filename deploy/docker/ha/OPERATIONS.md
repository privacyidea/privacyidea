# Operations

Day 2 guide for the privacyIDEA HA stack. Quick start and first-run setup
live in [`README.md`](README.md); incident playbooks live in
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

---

## What this deployment protects against

This HA stack is designed for a **single-site, single-LAN** failure
domain. It handles:

- Process crashes and container restarts (on any tier)
- A single database host failure (if you deploy across two machines)
- A single application host failure (if you deploy across two machines)
- Planned maintenance and rolling upgrades with zero downtime

It does **not** protect against site-level outages — fire, flood, power
loss affecting the whole building, data center failures, or regional /
continental disruptions. If your availability requirement includes
surviving a whole site going down, this setup alone is not enough; you
need disaster recovery or a multi-region architecture, which are
separate concerns from what this stack provides.

The short version: **one site, multiple machines — yes. Multiple sites
— no.** Ask your privacyIDEA integrator if you need more than that.

---

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

| Service | Role | Replicas |
|---------|------|----------|
| `pi-proxy` | HAProxy — TLS termination, load balancing | 1 |
| `pi` | privacyIDEA web workers (gunicorn) | 2 (scalable) |
| `pi-init` | One-shot: migrations + bootstrap admin | 1 (exits after init) |
| `pi-cron` | Scheduled maintenance tasks | **1 (must not scale)** |
| `db-proxy` | ProxySQL — DB load balancing, failover | 1 |
| `db-1`, `db-2` | MariaDB Galera cluster | 2 |

---

## Day-to-day management

Most common tasks are wrapped in the `Makefile`. Run `make help` for the
full list.

### View logs

```bash
docker compose -f ha-compose.yaml logs -f [service]
# or: make logs SERVICE=pi
```

### Restart services

```bash
docker compose -f ha-compose.yaml restart [service]
# or: make restart
```

### Scale workers

```bash
docker compose -f ha-compose.yaml up -d --scale pi=3
# or: make scale N=3
```

Do not scale `pi-cron`. Running two instances simultaneously causes race
conditions when deleting audit and challenge rows.

---

## Monitoring

### HAProxy stats

`http://<host>:8404/stats` — exposed on localhost only by default. Shows
backend health, connection counts, per-worker traffic.

```bash
make stats   # opens in default browser
```

### ProxySQL hostgroup state

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

### Galera sync state

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

---

## Scheduled maintenance (`pi-cron`)

The `pi-cron` container runs scheduled maintenance automatically. No host
cron required.

| Schedule | Command | Purpose |
|----------|---------|---------|
| Every minute | `privacyidea-cron run_scheduled` | Runs periodic tasks configured in the UI |
| Every hour | `pi-manage challenge cleanup` | Deletes expired authentication challenges |
| Daily (configurable) | `pi-manage audit rotate` | Trims the audit log |

**UI-configured periodic tasks** (EventCounter, SimpleStats, etc.) are
picked up automatically. Set the node to `pi-cron` in the admin UI to
target this container. Tasks with no node restriction also run here.

> **Important:** `pi-cron` must always run as a single replica. Multiple
> instances cause races when deleting audit and challenge rows.

### Configuration

All settings optional; defaults work for most deployments.

| Environment variable | Default | Description |
|----------------------|---------|-------------|
| `PI_CRON_AUDIT_ROTATE` | `true` | Enable/disable audit log rotation |
| `PI_CRON_AUDIT_HOUR` | `2` | Hour of day (0–23) to run rotation |
| `PI_CRON_AUDIT_HIGHWATERMARK` | `50000` | Trigger rotation when entry count exceeds this |
| `PI_CRON_AUDIT_LOWWATERMARK` | `25000` | Keep this many entries after rotation |
| `PI_CRON_AUDIT_AGE` | _(unset)_ | Delete entries older than N days instead of watermarks |
| `PI_CRON_AUDIT_CHUNKSIZE` | _(unset)_ | Delete in chunks to reduce lock contention |
| `PI_CRON_CHALLENGE_CLEANUP` | `true` | Enable/disable challenge cleanup |
| `PI_CRON_PERIODIC_TASKS` | `true` | Enable/disable `privacyidea-cron run_scheduled` |

All variables are commented out with their defaults in `ha-compose.yaml`
under the `pi-cron` service.

```bash
docker compose -f ha-compose.yaml logs -f pi-cron
# or: make logs SERVICE=pi-cron
```

---

## Backup and restore

### Create a backup

```bash
./scripts/backup.sh
# or: make backup
```

Creates a timestamped archive in `backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz`.

**Archive contents:**

| File | Purpose | Criticality |
|------|---------|-------------|
| `database.sql` | Full logical dump of the `pi` database | Required |
| `enckey` | Token encryption key | **Critical** — tokens unrecoverable without it |
| `pi_pepper` | Password hashing pepper | **Critical** — all logins fail without it |
| `secret_key` | Flask session signing key | Low — only invalidates active sessions |

All three keys and the database must be restored together. A mismatched
`enckey` or `pi_pepper` makes the database unusable.

### Encrypted backups (recommended)

The default archive is unencrypted. Since it contains your master encryption
key, encrypting backups with [age](https://age-encryption.org/) is strongly
recommended.

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

### Where do backups go?

`scripts/backup.sh` resolves paths relative to its own location. Backups
always land in `backups/` next to `ha-compose.yaml` —
`<ha-dir>/backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz`.

This directory is git-ignored and **not** off-site storage — it goes down
with the server. Move archives somewhere else:

- A remote server via `rsync` or `scp`
- Object storage (S3, Backblaze B2) via `rclone`
- An encrypted USB drive stored off-site

### Scheduling with host cron

Replace `/opt/privacyidea-ha` with wherever you've deployed the `ha/` dir.

Nightly backup at 02:00:
```
0 2 * * * /opt/privacyidea-ha/scripts/backup.sh --encrypt-key age1xxx >> /var/log/pi-backup.log 2>&1
```

Prune old backups (>30 days), nightly at 03:00:
```
0 3 * * * find /opt/privacyidea-ha/backups/ -name "privacyidea_*.tar.gz*" -mtime +30 -delete
```

### Restore

```bash
./scripts/restore.sh backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz
# or:   make restore BACKUP=backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz
# or for an encrypted archive:
./scripts/restore.sh backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz.age
```

The restore script:

1. Decrypts the archive automatically if it has a `.age` extension.
2. Checks that `enckey` and `pi_pepper` in the backup match `secrets/` on
   this host, warning loudly if they differ.
3. Prompts for confirmation before dropping data.
4. Imports the SQL dump into `db-1`.

After restore, restart the workers:
```bash
docker compose -f ha-compose.yaml restart pi
```

---

## Resource limits and sizing

Default per-service limits (edit in `ha-compose.yaml` under
`deploy.resources.limits`):

| Service | CPU | RAM |
|---|---|---|
| pi workers | 2.0 | 1 GB each |
| pi-cron | 0.5 | 256 MB |
| db (Galera) | 2.0 | 2 GB each |
| ProxySQL | 1.0 | 512 MB |
| HAProxy | 0.5 | 256 MB |

**Worker sizing.** The compose default is `PI_WORKERS=2` per `pi` container
— 4 gunicorn workers total. On this commodity hardware each worker
handles ~2–3 authentications/s with a passwd resolver, less with LDAP.
Rule of thumb: double the workers if your user resolver is LDAP/AD
without `usercache` enabled, or enable `usercache` (see the privacyIDEA
docs) — lookups will hit an in-DB cache instead of round-tripping to AD.

**Audit volume.** At 50 auths/s sustained you generate ~130 M audit rows
per month. The default watermarks (high 50k / low 25k) are orders of
magnitude too low for that volume — tune `PI_CRON_AUDIT_HIGHWATERMARK`
and `PI_CRON_AUDIT_LOWWATERMARK` on the `pi-cron` service to match your
actual rate, or switch to age-based rotation (`PI_CRON_AUDIT_AGE`).

---

## Failover testing

Manual smoke test:

```bash
# Stop primary database
docker compose -f ha-compose.yaml stop db-1
# ProxySQL should promote db-2 automatically; application continues serving.

docker compose -f ha-compose.yaml start db-1
# Wait for wsrep_local_state_comment = Synced before stopping db-2 again.
```

For automated failover validation with load generation, use the test
harness in [`tests/ha-test/`](../../../tests/ha-test/):

```bash
cd ../../../tests/ha-test
make test            # ~40% capacity, clean signal
make stress          # saturation worst case
make recovery-test   # all-nodes-crashed Galera recovery
```

`test` / `stress` generate challenge-response load via locust, stop the
writer mid-run, restart it, poll for `Synced`, and assert thresholds on
failure rate, failure window duration, and rejoin time.

`recovery-test` provisions tokens, SIGKILLs both DB nodes simultaneously
(simulating power loss), runs `scripts/ha-recover-cluster.sh`, and
asserts that the cluster comes back `Synced/Synced` with the token data
preserved. See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) for the
underlying recovery procedure.

---

## Security

- All secrets are mounted via Docker secrets (`/run/secrets/`) — never
  stored in env vars visible via `ps`.
- ProxySQL admin port (`6032`) is not exposed externally.
- `.gitignore` prevents committing `secrets/` files and `.env`.
- `enckey` must be backed up securely — its loss means token data is
  unrecoverable.

---

## Production checklist

Before declaring a deployment production-ready:

- [ ] All `secrets/` files generated with strong random values (not the
      placeholder dev defaults).
- [ ] `secrets/enckey` backed up securely off-host.
- [ ] Bootstrap admin password changed after first login.
- [ ] Firewall restricts ports `3306` and `6032` to trusted hosts only.
- [ ] Automated database backups scheduled
      (host cron running `scripts/backup.sh --encrypt-key ...`).
- [ ] Backup archives stored off-host (remote server, object storage, or
      encrypted media).
- [ ] age keypair generated; private key stored securely off-host.
- [ ] Log rotation configured at the host/docker level.
- [ ] Verified `pi-cron` is running and maintenance tasks appear in logs.
- [ ] `PI_CRON_AUDIT_*` watermarks or `PI_CRON_AUDIT_AGE` tuned to match
      expected audit volume.
- [ ] Monitoring in place (Prometheus/Grafana, or equivalent).
- [ ] Failover procedure tested on this specific deployment — not just
      assumed to work.
