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

## Next steps

- **Day 2 operations** (monitoring, backups, scaling, upgrades):
  [`OPERATIONS.md`](OPERATIONS.md)
- **Something went wrong:** [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- **Is this the right deployment tier for my customer?** See the internal
  positioning doc [`PRODUCT.md`](PRODUCT.md).
