privacyIDEA and Docker
======================

This directory builds a single privacyIDEA container image and runs it as a
small self-contained stack: one MariaDB plus three roles of the same image.

The image and its three roles
------------------------------

All three privacyIDEA services are built from the same `Dockerfile`. The role is
selected at runtime by `entrypoint.sh` via environment variables:

| Service   | Env selector        | What it does                                                            |
|-----------|---------------------|-------------------------------------------------------------------------|
| `pi-init` | `PI_INIT_ONLY=true` | Create tables, run DB migrations, bootstrap the admin, install the enckey canary, then exit. |
| `pi`      | *(default)*         | Gunicorn web workers on port 8080.                                      |
| `pi-cron` | `PI_CRON_MODE=true` | Maintenance scheduler: audit rotation, challenge cleanup, UI-configured periodic tasks. |

`pi` and `pi-cron` wait for `pi-init` to finish (`service_completed_successfully`),
so migrations never race against running workers.

Requirements
------------

- Docker Engine 24+ with the Compose v2 plugin (`docker compose`, not
  `docker-compose`).
- `make`, `python3` and `openssl` on the host for the helper targets (`make init`
  uses them to generate the secrets and the audit-signing keypair).
- Free host ports: `8080` (the app) and, for the optional TLS profile, `80`/`443`.
- Roughly 1–2 GB RAM and 2 CPUs is comfortable for a small deployment.

Quick start
-----------

From `deploy/docker/`:

```
make init     # generate secrets + create .env (idempotent; prints the admin password once)
make up       # start the stack
make smoke    # optional: verify readiness + admin login
```

`make init` writes the secret files (keys, passwords, and the audit-signing
keypair) with the correct format and permissions (see
[`secrets/README.md`](./secrets/README.md) if you prefer to generate them by hand)
and copies `.env.template` to `.env`. Review `.env` — at minimum set your
public URL via `PRIVACYIDEA_PI_BASE_URL` in `example.env`.

`pi-init` runs first (tables, migrations, admin), then `pi` and `pi-cron` start.
The web UI is served on http://localhost:8080 (plain HTTP — see *TLS* below).

`make help` lists all targets (`up`, `down`, `logs`, `ps`, `backup`, `restore`,
`upgrade`, `build`).

Configuration
-------------

Config comes entirely from environment variables and secret files — this
deployment does **not** use a `pi.cfg` (none is mounted; the app's optional
`pi.cfg` read is simply a no-op here). Three places:

- **Docker secrets** in `./secrets/` — keys and passwords (see above).
- **`.env`** — compose interpolation values (`BOOTSTRAP_ADMIN`, `PI_WORKERS`,
  `PI_SITE_ADDRESS`). Copy `.env.template` to `.env`.
- **`example.env`** — privacyIDEA application config keys, prefixed with
  `PRIVACYIDEA_`, applied to all three roles (e.g. `SQLALCHEMY_POOL_RECYCLE`,
  languages, and **`PRIVACYIDEA_PI_BASE_URL`** — set that to your public URL, or
  password recovery is disabled and notification links are blank). See
  https://privacyidea.readthedocs.io/en/latest/installation/system/inifile.html

Environment variable reference
------------------------------

The bundled `compose.yaml` pre-wires most of these; day to day you mainly edit
`.env` and `example.env`. Full list of what the deployment honors:

**`.env` — compose interpolation** (copy from `.env.template`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `BOOTSTRAP_ADMIN` | `admin` | initial admin username created by `pi-init` |
| `PI_WORKERS` | `4` | gunicorn workers in `pi` |
| `PI_SITE_ADDRESS` | `localhost` | public hostname for the `tls` (Caddy) profile |

**Container role & startup** (`entrypoint.sh` — set per service in compose):

| Variable | Default | Effect |
|----------|---------|--------|
| `PI_INIT_ONLY` | `false` | do init work, then exit (the `pi-init` role) |
| `PI_CREATE_TABLES` | `false` | create schema on an empty DB |
| `PI_RUN_MIGRATIONS` | `false` | run `pi-manage db upgrade` on an existing DB |
| `PI_CRON_MODE` | `false` | run the maintenance scheduler (the `pi-cron` role) |
| `PI_BOOTSTRAP_ADMIN` / `PI_BOOTSTRAP_ADMIN_PASSWORD` | *(unset)* | create this admin |
| `PI_WORKERS` | auto (`2*nproc+1`, cap 4) | gunicorn workers |
| `PI_STARTUP_DELAY` | `0` | seconds to sleep before startup (rarely needed) |

**Database & secrets** (read by `DockerConfig`, since `PI_CONFIG_NAME=docker`).
Every value below also accepts a `<NAME>_FILE` variant that reads the value from
a file (that's how the Docker secrets are wired):

| Variable | Purpose |
|----------|---------|
| `PI_DB_USER`, `PI_DB_HOST`, `PI_DB_NAME`, `PI_DB_PORT` | build the DB URI |
| `PI_DB_PASSWORD` (`_FILE`) | DB password (compose uses `PI_DB_PASSWORD_FILE`) |
| `PI_DB_DRIVER`, `PI_DB_EXTRA_PARAMS` | SQLAlchemy driver / extra URI params |
| `SQLALCHEMY_DATABASE_URI` (`_FILE`) | full DB URI (overrides the `PI_DB_*` parts) |
| `PI_ENCFILE` | path to the encryption key (auto-detects `/run/secrets/enckey`) |
| `PI_PEPPER` (`_FILE`) | password pepper |
| `PI_SECRET_KEY` (`_FILE`) | Flask secret key — alias of `SECRET_KEY` (`_FILE`), which also still works |
| `PI_REDIS_URL` (`_FILE`) | optional Redis cache URL |
| `PI_AUDIT_KEY_PUBLIC`, `PI_AUDIT_KEY_PRIVATE` | signed-audit key paths (auto-detect `/run/secrets/audit_key_*`) |

**Maintenance** (`cron-runner.py`, on the `pi-cron` service). All default enabled;
set to `false`/`0`/`no` to disable:

| Variable | Default | Purpose |
|----------|---------|---------|
| `PI_CRON_TASK_TIMEOUT` | `3600` | per-task timeout (seconds); a hung task is killed |
| `PI_CRON_PERIODIC_TASKS` | `true` | every-minute `run_scheduled` (the UI periodic-task lane) |
| `PI_CRON_CHALLENGE_CLEANUP` | `true` | hourly challenge cleanup |
| `PI_CRON_AUDIT_ROTATE` | `true` | audit-log rotation |
| `PI_CRON_AUDIT_HOUR` | `2` | daily hour (UTC) for audit rotation |
| `PI_CRON_AUDIT_INTERVAL` | *(unset)* | run audit every interval (`6h`,`90m`,`2d`) — overrides `_HOUR` |
| `PI_CRON_AUDIT_HIGHWATERMARK` / `_LOWWATERMARK` | `50000` / `25000` | trim to low when count exceeds high |
| `PI_CRON_AUDIT_AGE` | *(unset)* | delete entries older than N days instead of watermarks |
| `PI_CRON_AUDIT_CHUNKSIZE` | *(unset)* | delete in chunks to avoid long locks |
| `PI_CRON_USERCACHE_CLEANUP` | `true` | usercache cleanup (no-op unless the cache is on) |
| `PI_CRON_USERCACHE_HOUR` / `_INTERVAL` | `4` | daily hour (UTC) or interval, like audit |

**Arbitrary app config**: any privacyIDEA config key can be set as
`PRIVACYIDEA_<KEY>` (put these in `example.env`). See the upstream config
reference linked above.

TLS
---

The `pi` service speaks plain HTTP on port 8080. By default it is published only
on `127.0.0.1` (host-local), so it is never exposed on the network in cleartext —
terminate TLS in front of it for remote access. An optional Caddy reverse proxy
is included as the `tls` compose profile:

```
# set PI_SITE_ADDRESS=your.hostname in .env, then:
docker compose -f compose.yaml --profile tls up -d
```

Caddy reaches `pi` over the internal Docker network (not the localhost binding),
publishes 80/443, and with a public hostname obtains and renews a Let's Encrypt
certificate automatically. For an internal host, add `tls internal` to the
[`Caddyfile`](./Caddyfile). If you run your own proxy (nginx, Traefik, a load
balancer), point it at the `pi` container's port 8080 and skip the profile. Only
change the `pi` `ports:` entry to `8080:8080` if you deliberately accept
unencrypted access on the network.

Running a single container by hand
----------------------------------

Build:
```
docker build . -f deploy/docker/Dockerfile -t privacyidea:latest
```

The entrypoint's role is selected by environment variables — see the
*Environment variable reference* above for the full list (`PI_INIT_ONLY`,
`PI_CREATE_TABLES`, `PI_RUN_MIGRATIONS`, `PI_CRON_MODE`, …). The container always
serves on port 8080 internally; map host ports via the compose `ports:` entry.

**Do not enable `PI_RUN_MIGRATIONS` on more than one concurrently starting
container.** Run migrations from a single init container (as `pi-init` does).

Administration
--------------

Run management commands against the running container:
```
docker compose -f deploy/docker/compose.yaml exec pi pi-manage <args>
```

For one-off tasks, or when `pi` isn't running, use an ephemeral container instead
(the entrypoint runs the passed command instead of the web server):
```
docker compose -f deploy/docker/compose.yaml run --rm --no-deps pi pi-manage <args>
```

Import configuration (e.g. a policy template):
```
cat <template>.yaml | docker compose -f deploy/docker/compose.yaml exec -T pi pi-manage config import
```

Backup and restore
------------------

`scripts/backup.sh` produces a single archive containing a logical DB dump plus
the `enckey`, `pi_pepper`, and `secret_key` — the DB is useless without them, so
they are bundled together.

```
./deploy/docker/scripts/backup.sh                    # backups/privacyidea_<ts>.tar.gz
./deploy/docker/scripts/backup.sh --encrypt          # + age passphrase encryption
./deploy/docker/scripts/backup.sh --encrypt-key AGE-PUB   # non-interactive (cron)
```

Restore drops and recreates the database, then runs `pi-manage db upgrade` so the
restored schema is migrated up to the running image (a no-op for a same-version
restore; restore only onto the same or a newer privacyIDEA version). It also
reconciles each key in the backup with `secrets/`: a **missing** key is installed
from the archive, a **matching** key is left as-is, and a key that is **present
but different** is never overwritten — it warns and asks for confirmation
(replacing a good `enckey` with a different one permanently loses the data it
protects).

Same-host restore (keys already in place):
```
./deploy/docker/scripts/restore.sh backups/privacyidea_<ts>.tar.gz   # add --yes for non-interactive
```

### Disaster recovery on a fresh host

The database dump is useless without the matching `enckey`/`pi_pepper`, and the
`enckey` canary will refuse to start the workers if they don't match — so the
keys from the backup must be in place, **not** freshly generated. Order matters:

1. Put the deploy bundle on the new host and copy the backup archive to it.
2. Extract the archive and place its crypto keys into `secrets/`:
   ```
   tar xzf privacyidea_<ts>.tar.gz            # -> a dir with database.sql, enckey, pi_pepper, secret_key
   cp privacyidea_<ts>/{enckey,pi_pepper,secret_key} deploy/docker/secrets/
   ```
3. `make init` — idempotent: it keeps the keys you just restored and generates
   only the still-missing database/admin passwords (those don't protect encrypted
   data, so fresh ones are fine). Then review `.env`.
4. `make up` — the stack starts with the restored keys.
5. `./scripts/restore.sh privacyidea_<ts>.tar.gz` — imports the data (the keys
   now match) and runs `db upgrade` to migrate the schema to this image's version.
6. `docker compose -f compose.yaml restart pi pi-cron`.

(If you skip step 2, `restore.sh` will offer to install the missing keys from the
archive — but you must then `make up`/restart so the workers pick them up.)

### Scheduling backups

`pi-cron` handles in-database maintenance (audit rotation, challenge cleanup,
periodic tasks) but deliberately does **not** take backups. `backup.sh` bundles
the host-side secret files with the dump and writes archives that must then leave
the host to count as a backup — work that belongs on the host, not in the app
container's maintenance loop. Schedule it from the host instead, e.g. a daily
encrypted backup at 03:30 via the host crontab (`crontab -e`):
```
30 3 * * *  cd /path/to/privacyidea/deploy/docker && ./scripts/backup.sh --encrypt-key age1... >> /var/log/pi-backup.log 2>&1
```
Use `--encrypt-key <age-public-key>` (not `--encrypt`) so the run is
non-interactive, and keep the matching age private key off this host. Copy the
resulting archives to storage separate from this machine.

Maintenance (pi-cron)
---------------------

`pi-cron` runs `cron-runner.py`, which schedules:

- every minute — `privacyidea-cron run_scheduled` (runs the periodic tasks
  described below)
- hourly — `pi-manage config challenge cleanup`
- daily at `PI_CRON_AUDIT_HOUR` (default 02:00) — `pi-manage audit rotate`.
  Alternatively set `PI_CRON_AUDIT_INTERVAL` (e.g. `6h`, `90m`, `2d`) to run on a
  fixed interval instead of a daily hour; it takes precedence if both are set.
- daily at `PI_CRON_USERCACHE_HOUR` (default 04:00) — `privacyidea-usercache-cleanup`
  (a no-op unless the user cache is enabled). Same `_INTERVAL` override as audit.

Two lanes of scheduled maintenance run here. The fixed jobs above are wired in
`cron-runner.py`. Separately, privacyIDEA's **periodic-task modules**
(EventCounter, SimpleStats, MetricsCleanup, …) are configured in the **web UI**
and executed by the every-minute `run_scheduled` job whenever they target this
container's node name (`pi-cron`). So a future table/metrics cleanup that ships
as a periodic-task module needs **no change to the container** — configure it in
the UI for node `pi-cron`, not as a `PI_CRON_*` variable.

Tune via `PI_CRON_*` environment variables (see the `pi-cron` service in
`compose.yaml` and the header of `cron-runner.py`). Keep `pi-cron` at a single
instance — two would race on deleting the same rows.

Each task is one entry in the `TASKS` list in `cron-runner.py` — a name, an
enable flag, a schedule and the command to run. Schedules are `every_minute()`,
`hourly()`, `daily_at(hour)`, `every(minutes)`, or `scheduled_from_env(...)` to
let the operator choose an interval or a fixed hour from one env var. Adding a
future maintenance task is a single entry plus any `PI_CRON_*` variables it
reads; see the worked example in that file.

Scheduler caveats (single-node, in-process — deliberately simple):
- **Interval schedules count from container start, in memory.** A `_INTERVAL`
  longer than how often the container restarts may never fire (the timer resets
  on each start). For long periods (daily+), prefer the fixed-hour form
  (`_HOUR`), which is restart-independent.
- **The scheduler is single-threaded and samples once per minute.** A task that
  runs longer than the gap to a fixed-time task's minute can delay or skip that
  cycle (bounded by `PI_CRON_TASK_TIMEOUT`). Fine for the light default jobs; for
  heavy custom work prefer the UI periodic-task lane.
- Times are **UTC** (the image has no tzdata; see §Requirements/Maintenance notes).

Upgrading
---------

```
make upgrade
```

This backs up first, pulls the new image, and recreates the services. On restart
`pi-init` detects the existing database and runs `pi-manage db upgrade` (it only
creates tables on an empty database), so migrations are applied without racing
the workers. The `enckey`, `pi_pepper` and `secret_key` are unchanged, so tokens
and passwords keep working. Always keep the pre-upgrade backup until you have
confirmed the new version is healthy (`make smoke`).

Troubleshooting
---------------

- **`pi-init` exits with `permission denied` reading `/run/secrets/...`** — the
  secret files must be readable by the container's non-root user (uid 65532).
  Re-run `make init`, or `chmod 644 secrets/*`. Do not use `chmod 600`.
- **Startup logs warn `PI_BASE_URL is not configured`** — set
  `PRIVACYIDEA_PI_BASE_URL` in `example.env` to your public URL. Password
  recovery stays disabled until you do.
- **`pi` never becomes healthy** — check `docker compose logs pi` and `logs db`.
  Most often the database is not reachable or a migration failed in `pi-init`
  (`docker compose logs pi-init`).
- **Enckey mismatch on start (`enckey canary verification failed`, exit 2)** —
  the mounted `secrets/enckey` does not match the one the database was built
  with. Restore the original `enckey` from your backup; do not overwrite it.

Uninstall / cleanup
-------------------

```
make down                        # stop and remove containers, keep data
docker compose -f compose.yaml down -v   # also delete the database volume
```

`down -v` destroys the database. Take a backup first (`make backup`) if you may
need the data, and keep `secrets/enckey` + `secrets/pi_pepper` — without them a
backup cannot be restored.

TODO
----
* Publish an image so `build:` can be replaced with `image:`.
* Add build steps for optional dependencies (PyKCS11, gssapi).
