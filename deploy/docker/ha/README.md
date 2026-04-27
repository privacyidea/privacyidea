# privacyIDEA HA — Docker Compose

Single-host high-availability deployment for privacyIDEA. Process-level
redundancy on the app and database tiers via containers orchestrated with
Docker Compose.

**Stack at a glance:**

- HAProxy in front of 2× privacyIDEA gunicorn workers
- ProxySQL in front of a 2-node MariaDB Galera cluster
- A one-shot `pi-init` container for migrations and first-admin bootstrap
- A `pi-cron` container for scheduled maintenance

Full architecture, service breakdown, and ops procedures are in
[`OPERATIONS.md`](OPERATIONS.md).

---

## Prerequisites

- Docker Engine 24+ with Compose v2
- Ports `8000` (HTTP, HAProxy) and `3306` (ProxySQL) free on the host
- ~4 GB RAM for the whole stack at default sizing

## Quick start

### 1. Generate secrets

All credentials are files under `secrets/`, mounted into containers via
Docker secrets — never env vars.

```bash
cd secrets
python3 -c "import os; print(os.urandom(96).hex())"          > enckey
python3 -c "import secrets; print(secrets.token_hex(32))"     > secret_key
python3 -c "import secrets; print(secrets.token_hex(32))"     > pi_pepper
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_password
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_root_password
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > proxysql_admin_password
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > bootstrap_admin_password
chmod 600 *
cd ..
```

### 2. Configure (optional)

```bash
cp .env.template .env
# Edit to change the bootstrap admin username or tuning parameters. Defaults work.
```

### 3. Start the stack

```bash
docker compose -f ha-compose.yaml up -d
# or: make start
```

### 4. Verify health

```bash
docker compose -f ha-compose.yaml ps
# All services should show (healthy).
```

Open `http://<host>:8000` and log in as the bootstrap admin with the password
from `secrets/bootstrap_admin_password`. **Change this password after first
login** — it is stored on disk.

---

## What a default install gives you

Sensible defaults are pre-configured so the stack is usable immediately
without further tuning. Tunables for each item live in
[`OPERATIONS.md`](OPERATIONS.md).

**Topology**

- 2× privacyIDEA gunicorn workers (`PI_WORKERS=2` per container, so 4
  gunicorn workers total) behind HAProxy on `:8000`.
- 2-node MariaDB Galera cluster (`db-1` + `db-2`) behind ProxySQL on
  `:3306`. Writes go to `db-1`; `db-2` is the backup writer; reads are
  load-balanced across both.
- 1× `pi-cron` for scheduled maintenance. 1× `pi-init` runs migrations
  and exits.
- All services have Docker healthchecks; `restart: unless-stopped` on
  long-lived ones.

**Scheduled maintenance** (`pi-cron`, all enabled out of the box)

- **Periodic tasks** (UI-configured): every minute, picks up tasks
  targeted at the `pi-cron` node.
- **Challenge cleanup** (`pi-manage challenge cleanup`): every hour,
  removes expired authentication challenges.
- **Audit rotation** (`pi-manage audit rotate`): daily at 02:00,
  watermark-based — trims to 25 000 entries once the table exceeds
  50 000. Tune `PI_CRON_AUDIT_HIGHWATERMARK`/`LOWWATERMARK` for high
  auth volume, or set `PI_CRON_AUDIT_AGE` for age-based rotation.

**Security**

- All credentials live in `secrets/` and are mounted via Docker secrets
  (`/run/secrets/`) — never in env vars visible in `ps`.
- HAProxy serves HTTPS on `:8443` with a self-signed cert from
  `scripts/gen-haproxy-cert.sh`. Replace the file in
  `secrets/haproxy/cert.pem` with a production fullchain+key and
  `docker compose restart pi-proxy` — no config change needed.
- Galera cluster replication is TLS-encrypted (after running
  `scripts/gen-galera-certs.sh` once). SST stream on port 4444 is
  plaintext — fine for LAN, not for WAN.
- ProxySQL uses a dedicated `proxysql_monitor` user (USAGE +
  REPLICATION CLIENT only), not `root`.
- ProxySQL admin port (`6032`) is bound to localhost only.
- Encryption key canary (`enckey-canary.py`) verifies on every `pi`
  worker startup that the configured `enckey` decrypts a known
  ciphertext from the DB. Mismatch → workers refuse to start (loud
  fail) instead of silently producing garbage.

**What is NOT enabled by default — you must opt in**

- **Backups.** `scripts/backup.sh` exists but no schedule runs it.
  Add a host cron entry (see OPERATIONS.md → "Scheduling with host
  cron"). Off-host storage is also on you — `backups/` lives next to
  the stack and goes down with the host.
- **Production TLS cert.** First run uses a self-signed cert. Browsers
  will warn until you replace `secrets/haproxy/cert.pem`.
- **Galera TLS material.** Run `scripts/gen-galera-certs.sh` once
  before first start; the cluster won't come up otherwise.
- **External monitoring.** HAProxy stats (`:8404`) and ProxySQL admin
  (`:6032`) are local-only; wire them into Prometheus/Grafana yourself.
- **Firewalling of `:3306` and `:6032`.** Restrict at the host level.

---

## Next steps

- **Day 2 operations** (monitoring, backups, scaling, upgrades):
  [`OPERATIONS.md`](OPERATIONS.md)
- **Something went wrong:** [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- **Is this the right deployment tier for my customer?** See the internal
  positioning doc [`internal/PRODUCT.md`](internal/PRODUCT.md).
