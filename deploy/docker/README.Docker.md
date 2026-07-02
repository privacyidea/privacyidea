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

Quick start (compose)
----------------------

1. Generate the secrets (see [`secrets/README.md`](./secrets/README.md)):
   ```
   cd deploy/docker/secrets && \
     head -c 96 /dev/urandom > enckey && \
     python3 -c "import secrets; print(secrets.token_urlsafe())"   > pi_pepper && \
     python3 -c "import secrets; print(secrets.token_hex())"       > secret_key && \
     python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_password && \
     python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_root_password && \
     printf 'change-me\n' > bootstrap_admin_password && chmod 644 * && chmod 700 .
   ```

2. Optionally copy `.env.template` to `.env` to set the admin name, worker count, etc.

3. Build and start:
   ```
   docker compose -f deploy/docker/compose.yaml up --build
   ```
   `pi-init` runs first (tables, migrations, admin), then `pi` and `pi-cron` start.
   The web UI is served on http://localhost:8080.

Configuration
-------------

Configuration comes from three places:

- **Docker secrets** in `./secrets/` — keys and passwords (see above).
- **`.env`** — compose interpolation values (`BOOTSTRAP_ADMIN`, `PI_WORKERS`,
  `SQLALCHEMY_POOL_RECYCLE`). Copy `.env.template` to `.env`.
- **`example.env`** — any additional privacyIDEA config keys, prefixed with
  `PRIVACYIDEA_`, applied to all three roles. See
  https://privacyidea.readthedocs.io/en/latest/installation/system/inifile.html

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

TODO
----
* Publish an image so `build:` can be replaced with `image:`.
* Add build steps for optional dependencies (PyKCS11, gssapi).
* Document TLS termination / reverse proxy for the single-node case.
