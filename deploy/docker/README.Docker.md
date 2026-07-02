privacyIDEA and Docker
======================

This directory builds a single privacyIDEA container image and runs it as a
small self-contained stack: one MariaDB plus three roles of the same image.

> **_NOTE:_** This is work-in-progress; expect breaking changes.

For a high-availability setup with database replication and a load balancer,
see [`ha/`](./ha/) instead.

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
- `make` and `python3` on the host for the helper targets (`make init` uses
  `python3` to generate secrets).
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

`make init` writes the six secret files with the correct format and permissions
(see [`secrets/README.md`](./secrets/README.md) if you prefer to generate them by
hand) and copies `.env.template` to `.env`. Review `.env` — at minimum set your
public URL via `PRIVACYIDEA_PI_BASE_URL` in `example.env`.

`pi-init` runs first (tables, migrations, admin), then `pi` and `pi-cron` start.
The web UI is served on http://localhost:8080 (plain HTTP — see *TLS* below).

`make help` lists all targets (`up`, `down`, `logs`, `ps`, `backup`, `restore`,
`upgrade`, `build`).

Configuration
-------------

Configuration comes from three places:

- **Docker secrets** in `./secrets/` — keys and passwords (see above).
- **`.env`** — compose interpolation values (`BOOTSTRAP_ADMIN`, `PI_WORKERS`,
  `SQLALCHEMY_POOL_RECYCLE`). Copy `.env.template` to `.env`.
- **`example.env`** — privacyIDEA application config keys, prefixed with
  `PRIVACYIDEA_`, applied to all three roles. Set **`PRIVACYIDEA_PI_BASE_URL`**
  here to your public URL (otherwise password recovery is disabled and
  notification links are blank). See
  https://privacyidea.readthedocs.io/en/latest/installation/system/inifile.html

TLS
---

The `pi` service speaks plain HTTP on port 8080 — never expose that directly to
users. Terminate TLS in front of it. An optional Caddy reverse proxy is included
as the `tls` compose profile:

```
# set PI_SITE_ADDRESS=your.hostname in .env, then:
docker compose -f compose.yaml --profile tls up -d
```

With a public hostname and reachable ports 80/443, Caddy obtains and renews a
Let's Encrypt certificate automatically. For an internal host, add `tls internal`
to the [`Caddyfile`](./Caddyfile). When fronting with Caddy, you can remove the
`pi` `ports:` mapping in `compose.yaml` so the app is reachable only over TLS.
If you already run your own proxy (nginx, Traefik, a load balancer), point it at
the `pi` container's port 8080 instead and skip the profile.

Running a single container by hand
----------------------------------

Build:
```
docker build . -f deploy/docker/Dockerfile -t privacyidea:latest
```

The entrypoint honors these environment variables (all optional):

| Variable                 | Default | Effect                                             |
|--------------------------|---------|----------------------------------------------------|
| `PI_CREATE_TABLES`       | `false` | Create the schema on start.                        |
| `PI_RUN_MIGRATIONS`      | `false` | Run `pi-manage db upgrade` on start.               |
| `PI_INIT_ONLY`           | `false` | Do init work, then exit (init-container pattern).  |
| `PI_CRON_MODE`           | `false` | Run the maintenance scheduler instead of gunicorn. |
| `PI_BOOTSTRAP_ADMIN`     | *(unset)* | Create this admin (with `PI_BOOTSTRAP_ADMIN_PASSWORD`). |
| `PI_WORKERS`             | auto    | Gunicorn worker count (auto = `2*nproc+1`, capped at 4). |
| `PI_PORT`                | `8080`  | Gunicorn bind port.                                |

**Do not enable `PI_RUN_MIGRATIONS` on more than one concurrently starting
container.** Run migrations from a single init container (as `pi-init` does).

Administration
--------------

Run management commands inside the running container:
```
docker compose -f deploy/docker/compose.yaml exec pi pi-manage <args>
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

Restore drops and recreates the database, with a guard that warns if the backup's
`enckey`/`pi_pepper` differ from the current ones:
```
./deploy/docker/scripts/restore.sh backups/privacyidea_<ts>.tar.gz
```

### Scheduling backups

`pi-cron` handles in-database maintenance (audit rotation, challenge cleanup,
periodic tasks) but deliberately does **not** take backups — a DB dump needs the
host's Docker socket and `mariadb-dump`, which do not belong inside the app
container. Schedule `backup.sh` from the host instead, e.g. a daily encrypted
backup at 03:30 via the host crontab (`crontab -e`):
```
30 3 * * *  cd /path/to/privacyidea/deploy/docker && ./scripts/backup.sh --encrypt-key age1... >> /var/log/pi-backup.log 2>&1
```
Use `--encrypt-key <age-public-key>` (not `--encrypt`) so the run is
non-interactive, and keep the matching age private key off this host. Copy the
resulting archives to storage separate from this machine.

Maintenance (pi-cron)
---------------------

`pi-cron` runs `cron-runner.py`, which schedules:

- every minute — `privacyidea-cron run_scheduled` (UI-configured periodic tasks;
  target node name `pi-cron`)
- hourly — `pi-manage challenge cleanup`
- daily at `PI_CRON_AUDIT_HOUR` (default 02:00) — `pi-manage audit rotate`

Tune via `PI_CRON_*` environment variables (see the `pi-cron` service in
`compose.yaml` and the header of `cron-runner.py`). Keep `pi-cron` at a single
instance — two would race on deleting the same rows.

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
