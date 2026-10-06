privacyIDEA and Docker
======================

This directory runs the privacyIDEA container image as a small self-contained
stack: one MariaDB plus three roles of the same image, or the three roles with a
database of yours (see *External database*). A web server for TLS in front of
them is optional: the bundled Caddy, or one of yours (see *TLS*). The image is
built from the `Dockerfile` here and published as a release; `compose.yaml`
pulls it.

The image and its three roles
------------------------------

All three privacyIDEA services run the same image. The role is
selected at runtime by `entrypoint.sh` via environment variables:

| Service   | Env selector        | What it does                                                            |
|-----------|---------------------|-------------------------------------------------------------------------|
| `pi-init` | `PI_INIT_ONLY=true` | Create tables, run DB migrations, bootstrap the admin, install the enckey canary, then exit. |
| `pi`      | *(default)*         | Gunicorn web workers on port 8080.                                      |
| `pi-cron` | `PI_CRON_MODE=true` | Maintenance scheduler: table cleanups, audit rotation, UI-configured periodic tasks. |

`pi` and `pi-cron` wait for `pi-init` to finish (`service_completed_successfully`),
so migrations never race against running workers.

Image versions
--------------

`compose.yaml` runs `harbor.netknights.it/privacyidea/privacyidea` in the
version it belongs to: the copy in a release runs that release. Set `PI_IMAGE` in
`.env` to run another one.

- Tags are exact privacyIDEA versions (`3.14`, `3.13.4`). A tag such as `3.13` is
  the 3.13 release itself, not the newest 3.13.x: to get a patch release, name it.
- Do not use `latest`. `pi-init` migrates the database to whatever image it
  runs, so the version should only change when you change it (see *Upgrading*).

To run an image built from this source tree instead, set a local name such as
`PI_IMAGE=privacyidea:local` in `.env`, then `make build` and `make up`.
`make build` uses `compose.build.yaml`, which refuses to build without
`PI_IMAGE`, so a build of unreleased code never carries the name of a release.
`GIT_VERSION=<version> make build` builds the package as that version and puts it
in the image's version label; without it, the version comes from git and the
label stays empty. Update such an image the same way, with `make build` and
`make up` (`make backup` first if the data matters): `make upgrade` pulls, and
stops when the image cannot be pulled.

The deployment directory
------------------------

A deployment is one directory holding this directory's files from a release. All
commands below run in it. Any location works; the examples use
`/opt/privacyidea-docker`. To get the files of release `<version>`:

```
git clone --depth 1 --branch v<version> https://github.com/privacyidea/privacyidea.git /tmp/privacyidea-<version>
sudo cp -r /tmp/privacyidea-<version>/deploy/docker /opt/privacyidea-docker
```

The directory holds two kinds of files:

| | Files | On an upgrade |
|---|---|---|
| **From the release** | `compose.yaml`, `compose.external-db.yaml`, `compose.build.yaml`, `Makefile`, `Caddyfile`, `scripts/`, the `*.template` files, the image's sources (`Dockerfile`, `entrypoint.sh`, …), this README | replaced by the files of the new release |
| **Yours** | `.env`, `privacyidea.env`, `caddy.env`, `mariadb.cnf`, `compose.override.yaml` (optional), `secrets/`, `backups/` | kept; no release contains them |

Your files are this deployment: back them up, and move them when the host is
replaced. **`secrets/enckey` is the one file that cannot be recreated** — without
it every token in the database is unusable (each backup archive holds a copy, see
*Backup and restore*). Do not change the files from the release: an upgrade
replaces them. Everything you would change there has a place among your files,
including changes to `compose.yaml` (see *Your own changes*).

Requirements
------------

- Docker Engine 24+ with the Compose v2 plugin, version 2.24 or newer
  (`docker compose`, not `docker-compose`).
- `make`, `python3` and `openssl` on the host for the helper targets (`make init`
  uses them to generate the secrets and the audit-signing keypair).
- Free host ports: `8080` (the app) and, for the optional TLS profile, `80`/`443`.
- Roughly 1–2 GB RAM and 2 CPUs is comfortable for a small deployment.

Quick start
-----------

In the deployment directory:

```
make init     # generate secrets, create the config files (idempotent; prints the admin password once)
make up       # start the stack
make smoke    # optional: verify readiness + admin login
```

`make init` writes the secret files (keys, passwords, and the audit-signing
keypair) with the correct format and permissions (see
[`secrets/README.md`](./secrets/README.md) if you prefer to generate them by hand)
and creates each config file that does not exist yet from its template: `.env`,
`privacyidea.env`, `caddy.env` and `mariadb.cnf`. Review them — at minimum set
your public URL via `PRIVACYIDEA_PI_BASE_URL` in `privacyidea.env`.

`pi-init` runs first (tables, migrations, admin), then `pi` and `pi-cron` start.
The web UI is served on http://localhost:8080 (plain HTTP — see *TLS* below).

`make help` lists all targets: `init`, `up`, `down`, `restart`, `ps`, `logs`,
`smoke`, `backup`, `restore`, `upgrade`, `build` and `pimanage`.

Day to day
----------

What whoever runs the deployment needs to know. Three commands, run in the
deployment directory (`/opt/privacyidea-docker` in the examples):

| Question | Command |
|---|---|
| Is it up? | `make ps`, then `make smoke` for a login test |
| Back it up | `make backup` (schedule it, see *Scheduling backups*) |
| Upgrade it | take the files of the new release, `make init`, `make upgrade` (see *Upgrading*) |

What to keep safe: your files (see *The deployment directory*) and the archives
in `backups/`, copied off this host. **Never lose `secrets/enckey`**: without it
the tokens in the database are unusable. Every backup archive contains a copy,
so store the archives as carefully as the key (`make backup ARGS="--encrypt"`).

`make logs` follows the logs; each container keeps the last 50 MB of them.

Running pi-manage
-----------------

For one-off admin commands, `make pimanage` starts a throwaway container that
runs a single `pi-manage` command and then removes itself:

```
make pimanage ARGS="admin list"
make pimanage ARGS="config export"
```

The command goes in `ARGS="..."` rather than directly after the target because
`make` would otherwise treat each word as its own target and parse any `-`-option
(e.g. `admin add … -p`) as one of its own flags; quoting in `ARGS` passes the
whole command through to `pi-manage` verbatim.

It runs with `--no-deps`, so it does **not** start `pi-init` (no migrations or
admin bootstrap as a side effect) — it just needs the database to be up,
which is the normal case while the stack is running. Under the hood this is
`docker compose run --rm --no-deps pi pi-manage …`; the container gets the same
config and secrets as the web workers.

Configuration
-------------

Config comes entirely from environment variables and secret files — this
deployment does **not** use a `pi.cfg` (none is mounted; the app's optional
`pi.cfg` read is simply a no-op here). `make init` creates each of these files
from its template:

- **Docker secrets** in `./secrets/` — keys and passwords (see above).
- **`.env`** — values compose itself reads: which compose files and optional
  services to run (`COMPOSE_FILE`, `COMPOSE_PROFILES`), `PI_IMAGE`,
  `BOOTSTRAP_ADMIN`, `PI_WORKERS`, and the network between Caddy and `pi`.
- **`privacyidea.env`** — privacyIDEA application config keys, prefixed with
  `PRIVACYIDEA_`, applied to all three roles (e.g. `SQLALCHEMY_POOL_RECYCLE`,
  languages, and **`PRIVACYIDEA_PI_BASE_URL`** — set that to your public URL, or
  password recovery is disabled and notification links are blank). See
  https://privacyidea.readthedocs.io/en/latest/installation/system/inifile.html
- **`caddy.env`** — the hostname and TLS option of the Caddy reverse proxy (see
  *TLS*).
- **`mariadb.cnf`** — server options of the bundled MariaDB, such as
  `innodb_buffer_pool_size`, in MariaDB's option file format. It is mounted as
  `/etc/mysql/conf.d/privacyidea.cnf`; after a change, run
  `docker compose restart db`.

Settings privacyIDEA keeps in its database (system settings, policies,
resolvers, realms) are not part of these files; see *Configuration as code*.

Environment variable reference
------------------------------

The bundled `compose.yaml` pre-wires most of these; day to day you mainly edit
`.env` and `privacyidea.env`. Full list of what the deployment honors:

**`.env` — compose interpolation** (copy from `.env.template`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `COMPOSE_FILE` | `compose.yaml` and `compose.override.yaml`, if it exists | the compose files; see *Your own changes* and *External database* |
| `COMPOSE_PROFILES` | *(unset)* | `tls` runs the Caddy reverse proxy with the stack (see *TLS*) |
| `PI_IMAGE` | the release `compose.yaml` belongs to | image of the three privacyIDEA services (see *Image versions*) |
| `BOOTSTRAP_ADMIN` | `admin` | initial admin username created by `pi-init` |
| `PI_WORKERS` | `4` | gunicorn workers in `pi` |
| `PI_PROXY_SUBNET` / `PI_PROXY_IP_RANGE` / `PI_PROXY_ADDRESS` | `192.168.255.240/28` / `192.168.255.248/29` / `192.168.255.242` | the network between Caddy and `pi`, and Caddy's fixed address on it (see *TLS*) |

**`caddy.env` — the Caddy reverse proxy** (copy from `caddy.env.template`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `PI_SITE_ADDRESS` | `localhost` | hostname Caddy serves and gets a certificate for |
| `PI_CADDY_TLS` | *(unset)* | a `tls` directive for the site, e.g. `tls internal` |

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
| `PI_COMPOSE_VERSION` | set by `compose.yaml` | the release `compose.yaml` belongs to; a warning is logged when the image is another minor version |

**Database & secrets** (read by `DockerConfig`, since `PI_CONFIG_NAME=docker`).
Every value below also accepts a `<NAME>_FILE` variant that reads the value from
a file (that's how the Docker secrets are wired):

| Variable | Purpose |
|----------|---------|
| `PI_DB_USER`, `PI_DB_HOST`, `PI_DB_NAME`, `PI_DB_PORT` | build the DB URI |
| `PI_DB_PASSWORD` (`_FILE`) | DB password (compose uses `PI_DB_PASSWORD_FILE`); give user and password unencoded, both are percent-encoded into the URI |
| `PI_DB_DRIVER`, `PI_DB_EXTRA_PARAMS` | SQLAlchemy driver / extra URI params |
| `SQLALCHEMY_DATABASE_URI` (`_FILE`) | full DB URI (overrides the `PI_DB_*` parts) |
| `PI_ENCFILE` | path to the encryption key (auto-detects `/run/secrets/enckey`) |
| `PI_PEPPER` (`_FILE`) | password pepper |
| `PI_SECRET_KEY` (`_FILE`) | Flask secret key — alias of `SECRET_KEY` (`_FILE`), which wins if both are set |
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
| `PI_CRON_REMEMBERED_DEVICE_CLEANUP` | `true` | daily cleanup of expired remembered devices |
| `PI_CRON_AUTHCACHE_CLEANUP` | `true` | daily cleanup of authentication cache entries no auth_cache policy accepts any more |
| `PI_CRON_METRICS_CLEANUP` | `true` | daily cleanup of metric rows older than 24 hours |
| `PI_CRON_CONDITIONAL_ACCESS_PURGE` | `true` | daily removal of expired IP blocks and user locks |
| `PI_CRON_AUTHLOG_AGE` | *(unset)* | delete authentication log entries older than N days, daily; unset or `0` keeps the log forever |

**Arbitrary app config**: any privacyIDEA config key can be set as
`PRIVACYIDEA_<KEY>` (put these in `privacyidea.env`). See the upstream config
reference linked above.

Your own changes
----------------

A change to the services themselves — a mount, a port, a limit — goes in
`compose.override.yaml` in the deployment directory, not in `compose.yaml`.
Compose reads it after `compose.yaml` and merges it in, and an upgrade does not
touch it. Only the keys you change go in it:

```yaml
services:
  pi:
    volumes:
      - /etc/krb5.conf:/etc/krb5.conf:ro
```

Compose merges a mapping key by key and appends to a list. To replace a list
instead, mark it with `!override`; to remove a key, use `!reset`:

```yaml
services:
  pi:
    # Replaces 127.0.0.1:8080:8080 instead of publishing the port twice.
    ports: !override
      - "8080:8080"
```

Compose finds `compose.override.yaml` on its own only while `COMPOSE_FILE` is
unset. Once you set `COMPOSE_FILE` in `.env` (for an external database), list it
there as well. All `make` targets and scripts run plain `docker compose` in the
deployment directory, so they follow `COMPOSE_FILE` too; so does every
`docker compose` command in this README when you run it there.

External database
-----------------

The bundled MariaDB suits a single node. To use a database you already run —
MariaDB, MySQL or PostgreSQL, managed or not — add `compose.external-db.yaml`
in `.env`:

```
COMPOSE_FILE=compose.yaml:compose.external-db.yaml
```

and write the database's SQLAlchemy URI to `secrets/database_uri`:

```
printf '%s\n' 'postgresql+psycopg2://pi:<password>@db.example.org:5432/pi' > secrets/database_uri
chmod 644 secrets/database_uri
```

- The image has the drivers `mysql+pymysql` (MariaDB, MySQL) and
  `postgresql+psycopg2` (PostgreSQL). It has none for Oracle.
- Percent-encode the characters `@ : / ? # %` in the user name and password
  (`@` becomes `%40`).
- Create the database and its user first; the user needs the rights to create
  and change tables. `pi-init` creates the tables on an empty database and runs
  the migrations on an existing one, as with the bundled MariaDB.
- The database has to be up before `make up`: `pi-init` does not wait for it,
  and stops with `could not determine database state` when it cannot reach it.
- The database is yours to back up, with its own tools. `make backup` still
  archives the keys, which a backup of the database is useless without;
  `restore.sh` restores the bundled MariaDB only.
- The containers have to reach the database, on another machine or on this
  host: see *Database or web server outside Docker*.

To move an existing deployment to an external database, run `make down` before
you change `COMPOSE_FILE` (the `db` container is no longer managed afterwards),
and copy the data across with the tools of the two databases.

TLS
---

The `pi` service speaks plain HTTP on port 8080. By default it is published only
on `127.0.0.1` (host-local), so it is never exposed on the network in cleartext —
terminate TLS in front of it for remote access. A web server of yours outside
Docker can do that (see *Database or web server outside Docker*), or one in this
stack: an optional Caddy reverse proxy is included as the `tls` compose profile,
and nginx can take its place (see below). Turn Caddy on in `.env`, so that every
command (`make up`, `make down`, `make upgrade`, the scripts) includes it:

```
COMPOSE_PROFILES=tls
```

set the hostname in `caddy.env`:

```
PI_SITE_ADDRESS=your.hostname
```

then `make up`. Caddy reaches `pi` over its own Docker network (not the
localhost binding), publishes 80/443, and with a public hostname obtains and
renews a Let's Encrypt certificate automatically. For an internal host without
public DNS, also set `PI_CADDY_TLS=tls internal` in `caddy.env`: Caddy then
issues the certificate from its own local CA, which the clients have to trust.
The [`Caddyfile`](./Caddyfile) reads both values, so it needs no changes. Only
publish `pi` on `8080:8080` (in `compose.override.yaml`, see *Your own changes*)
if you deliberately accept unencrypted access on the network.

### Client addresses behind Caddy

Behind Caddy, every request reaches privacyIDEA from Caddy's address, so policies
that match the client IP, conditional access and the audit log all see Caddy
instead of the client. Caddy passes the client's address in the
`X-Forwarded-For` header; privacyIDEA uses it only from a proxy named in the
system setting **Override Authorization Clients** (`OverrideAuthorizationClient`).
Caddy has the fixed address `192.168.255.242` (`PI_PROXY_ADDRESS`), so set the
setting to exactly that address, in the WebUI under *Configuration → System* or
with:

```
printf 'config:\n  OverrideAuthorizationClient:\n    Value: 192.168.255.242\n' \
  | docker compose exec -T pi pi-manage config import
```

(`config import` warns that the input has no version; that is expected here.)
Name only Caddy's address, not the whole subnet: the subnet also holds the
Docker gateway, through which any process on this host could then claim an
arbitrary client address. Caddy replaces an `X-Forwarded-For` header sent by the
client, so a client cannot claim another address through it. The setting is
described in the privacyIDEA documentation under *System Config → Override
Authorization Client*.

The network between Caddy and `pi` is `192.168.255.240/28`. If it collides with a
network of yours (`up` fails with `Pool overlaps with other one on this address
space`), set `PI_PROXY_SUBNET`, `PI_PROXY_IP_RANGE` and `PI_PROXY_ADDRESS` in
`.env` together: the range is where Docker places `pi`, and Caddy's address lies
in the subnet but outside the range. Then update the setting to the new address.

### nginx instead of Caddy

Caddy is the bundled example because it gets its certificates on its own. To
run nginx instead, with certificates you manage, add it as a service in
`compose.override.yaml` and leave `COMPOSE_PROFILES` without `tls`. It takes
Caddy's place on the `proxy` network, with the same fixed address, so the setting
above stays as it is:

```yaml
services:
  nginx:
    image: nginx:stable
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
    # The master process runs as root, binds the ports and hands its cache
    # directories to the nginx user its workers switch to.
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
      - SETGID
      - SETUID
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
    ports:
      - "80:80"
      - "443:443"
    networks:
      proxy:
        ipv4_address: ${PI_PROXY_ADDRESS:-192.168.255.242}
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      # fullchain.pem and privkey.pem
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      pi:
        condition: service_healthy
```

and put the site in `nginx.conf` in the deployment directory:

```nginx
server {
    listen 80;
    server_name privacyidea.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name privacyidea.example.com;
    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # Docker's DNS, so that nginx looks pi up again when its address changes,
    # as it does when the container is recreated (make upgrade). A plain
    # "proxy_pass http://pi:8080" resolves it once at startup and then answers
    # 502 Bad Gateway.
    resolver 127.0.0.11 valid=10s;
    set $pi http://pi:8080;

    location / {
        proxy_pass $pi;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

`$proxy_add_x_forwarded_for` appends the client's address to an
`X-Forwarded-For` header the client sent. privacyIDEA takes the address nginx
added, so the client still cannot claim another one. `nginx.conf`, `certs/` and
the new service are your files; an upgrade leaves them alone. Renewing the
certificates is up to you: replace the files and run
`docker compose exec nginx nginx -s reload`.

Database or web server outside Docker
-------------------------------------

The three privacyIDEA services always run in Docker. The database and the web
server in front of them can run outside it, on another machine or on this host.

### The stack's addresses on this host

A database or web server on this host sees the containers on the stack's
`default` network. Docker picks that network's subnet when it creates the
network, and `make down` removes it, so the next `make up` can bring another
subnet. To keep the addresses below stable, fix the subnet in
`compose.override.yaml` (any free one; this one sits next to the Caddy network):

```yaml
networks:
  default:
    ipam:
      config:
        - subnet: 192.168.255.224/28
```

The containers then have addresses in `192.168.255.224/28`, and the host is
`192.168.255.225` on that network.

### Database

Set it up as described in *External database*, then make it reachable:

- **On another machine:** use its hostname in the URI. Connections from the
  containers leave this host with the host's address; allow that address for
  the database user (`pg_hba.conf` for PostgreSQL, the user's host part for
  MariaDB and MySQL) and in the firewalls on the way.
- **On this host:** `localhost` in the URI would be the container itself. Give
  the services a name for the host in `compose.override.yaml`, and use it in the
  URI (`...@host.docker.internal:5432/pi`):

  ```yaml
  services:
    pi-init:
      extra_hosts: ["host.docker.internal:host-gateway"]
    pi:
      extra_hosts: ["host.docker.internal:host-gateway"]
    pi-cron:
      extra_hosts: ["host.docker.internal:host-gateway"]
  ```

  The name points to the host's address on Docker's `docker0` bridge
  (`172.17.0.1` unless configured otherwise). Let the database listen there
  (`bind-address` for MariaDB and MySQL, `listen_addresses` for PostgreSQL),
  allow the stack's addresses (above) for the database user, and let a host
  firewall pass them to the database port.

### Web server

The web server terminates TLS and passes the requests to `pi` on port 8080 as
plain HTTP, with the client's address appended to `X-Forwarded-For`. The nginx
example under *TLS → nginx instead of Caddy* shows the headers; outside Docker,
replace its `resolver`, `set` and `proxy_pass` lines with a `proxy_pass` to the
address below.

privacyIDEA then sees the web server as the client of every request, until the
system setting **Override Authorization Clients** names the address it sees the
web server at (see *TLS → Client addresses behind Caddy* for how to set it). To
find that address, send a request through the web server before the setting is
made: the audit log shows it as the client.

- **On this host:** proxy to `http://127.0.0.1:8080`, where `pi` is published.
  `pi` sees these requests from the host's address on the stack's network
  (`192.168.255.225` with the fixed subnet above). Every process on this host
  reaches `pi` the same way and can then pass any client address, so name it
  only when you trust everything running on this host.
- **On another machine:** publish `pi` on an address that machine reaches, in
  `compose.override.yaml` (`ports: !override ["10.0.0.5:8080:8080"]`), and let
  only the web server reach that port. A host firewall such as ufw does not
  filter ports that Docker publishes; filter in Docker's `DOCKER-USER` chain or
  on the network. `pi` usually sees the web server's own address. The plain
  HTTP between the two crosses the network, so keep that path on a network you
  trust.

Logs
----

Every service logs to Docker's `json-file` driver with rotation: each container
keeps at most 5 files of 10 MB. This also applies when the host sets another log
driver in `/etc/docker/daemon.json`. `make logs` follows them, and
`docker compose logs <service>` shows one service. To keep logs longer or in a
central place, set another `logging:` in `compose.override.yaml`, for each of
the services `db`, `pi-init`, `pi`, `pi-cron` and `caddy`. Mark it `!override`,
because the `max-size`/`max-file` options would otherwise be merged in, and only
`json-file` and `local` accept them:

```yaml
services:
  db:
    logging: !override &logging
      driver: journald
  pi-init:
    logging: *logging
  pi:
    logging: *logging
  pi-cron:
    logging: *logging
  caddy:
    logging: *logging
```

Container hardening
-------------------

The three privacyIDEA services run as an unprivileged user with every Linux
capability dropped and `no-new-privileges` set. Caddy keeps only
`NET_BIND_SERVICE` to bind ports 80 and 443. MariaDB keeps its default
capabilities, which its entrypoint needs to prepare the data directory before it
switches to the `mysql` user. No memory or CPU limits are set: the right values
depend on the load of a deployment, and a database that reaches a memory limit
set too low is killed in the middle of a write. If your policy requires limits,
add `mem_limit` and `cpus` to the services in `compose.override.yaml`.

Kerberos (LDAP SASL bind)
-------------------------

The image bundles the `gssapi` library, so an LDAP resolver configured with
**SASL Kerberos** bind works. Kerberos itself still needs realm config: mount
your `krb5.conf` read-only into the containers that talk to LDAP (`pi`, and
`pi-cron` if resolver-touching periodic tasks run there), in
`compose.override.yaml`:

```yaml
services:
  pi:
    volumes:
      - /etc/krb5.conf:/etc/krb5.conf:ro
```

Without a valid `krb5.conf` the bind fails at runtime (wrong realm/KDC) even
though the library is present. If you don't use Kerberos, ignore this — nothing
to mount.

Running a single container by hand
----------------------------------

Pull a release, or build from the repository root:
```
docker pull harbor.netknights.it/privacyidea/privacyidea:<version>
docker build . -f deploy/docker/Dockerfile -t privacyidea:local
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
docker compose exec pi pi-manage <args>
```

For one-off tasks, or when `pi` isn't running, use an ephemeral container instead
(the entrypoint runs the passed command instead of the web server):
```
docker compose run --rm --no-deps pi pi-manage <args>
```

### Configuration as code

Resolvers, realms, policies, event handlers and system settings live in the
database, so the files of the deployment directory do not record them.
`pi-manage config export` writes them to a file you can keep in version control,
review as a diff, and import into the next installation:

```
docker compose exec -T pi pi-manage config export -f yaml > pi-config.yaml
docker compose exec -T pi pi-manage config import < pi-config.yaml
```

`-T` passes the file through standard input and output. Without `-t`, every
type is exported; `pi-manage config export --help` lists them, and
`-t resolver -t realm -t policy` exports only those. The export holds the
passwords it contains (an LDAP bind password, for example) in clear text, so
treat the file like a secret; `--censor` replaces them, but a censored file can
only be imported into the installation it came from. What belongs to one
installation only, such as its enckey canary, is neither exported nor imported.

Backup and restore
------------------

`scripts/backup.sh` produces a single archive containing a logical DB dump plus
the `enckey`, `pi_pepper`, and `secret_key` — the DB is useless without them, so
they are bundled together. With an external database the archive holds the keys
only (see *External database*).

```
./scripts/backup.sh                    # backups/privacyidea_<ts>.tar.gz
./scripts/backup.sh --encrypt          # + age passphrase encryption
./scripts/backup.sh --encrypt-key AGE-PUB   # non-interactive (cron)
```

The archive does not contain your config files (`.env`, `privacyidea.env`,
`caddy.env`, `mariadb.cnf`, `compose.override.yaml`, `secrets/database_uri`);
keep a copy of them with the backups.

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
./scripts/restore.sh backups/privacyidea_<ts>.tar.gz   # add --yes for non-interactive
```

### Disaster recovery on a fresh host

The database dump is useless without the matching `enckey` and `pi_pepper`, and
the workers do not start when `secrets/enckey` does not match the database (the
enckey canary) — so the keys from the backup must be in place, **not** freshly
generated. Order matters:

1. Create the deployment directory on the new host from the release the backup
   was taken with, or a newer one (see *The deployment directory*), and copy the
   backup archive and your config files into it.
2. Extract the archive and place its crypto keys into `secrets/`:
   ```
   tar xzf privacyidea_<ts>.tar.gz            # -> privacyidea_<ts>/ with database.sql and the keys
   mkdir -p secrets
   cp privacyidea_<ts>/{enckey,pi_pepper,secret_key,audit_key_private,audit_key_public} secrets/
   ```
   (A deployment that ran without audit signing has no audit keys in its
   archives; leave them out.)
3. `make init` — idempotent: it keeps the keys you just restored and generates
   only the still-missing database/admin passwords (those don't protect encrypted
   data, so fresh ones are fine). It also creates the config files you have no
   copy of from their templates; then review them.
4. `make up` — the stack starts with the restored keys.
5. `./scripts/restore.sh privacyidea_<ts>.tar.gz` — imports the data (the keys
   now match) and runs `db upgrade` to migrate the schema to this image's version.
6. `make restart`.

Step 2 has to come before step 3: `make init` generates every key that is
missing, and `restore.sh` does not replace a key that differs from the archive's.
If `make init` ran first, run `docker compose down -v` (the new database is still
empty), copy the keys from the archive into `secrets/` as in step 2, and continue
with step 4.

### Scheduling backups

`pi-cron` handles in-database maintenance (table cleanups, audit rotation,
periodic tasks) but deliberately does **not** take backups. `backup.sh` bundles
the host-side secret files with the dump and writes archives that must then leave
the host to count as a backup — work that belongs on the host, not in the app
container's maintenance loop. Schedule it from the host instead, e.g. a daily
encrypted backup at 03:30 via the host crontab (`crontab -e`):
```
30 3 * * *  cd /opt/privacyidea-docker && ./scripts/backup.sh --encrypt-key age1... >> /var/log/pi-backup.log 2>&1
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
- daily at 03:00 — `pi-manage config remembered_device cleanup`,
  `pi-manage config authcache cleanup`, `pi-manage config metrics cleanup`,
  `pi-manage conditionalaccess purge-expired-blocks` and `purge-expired-locks`.
- daily at 03:00, only once `PI_CRON_AUTHLOG_AGE` is set —
  `pi-manage authlog cleanup --age <PI_CRON_AUTHLOG_AGE>`. The authentication log
  needs a retention period of your choice, so it is kept forever by default.

Two lanes of scheduled maintenance run here. The fixed jobs above are wired in
`cron-runner.py`. Separately, privacyIDEA's **periodic-task modules**
(EventCounter, SimpleStats, …) are configured in the **web UI** and executed by
the every-minute `run_scheduled` job whenever they target this container's node
name (`pi-cron`). So a periodic-task module needs **no change to the container**
— configure it in the UI for node `pi-cron`, not as a `PI_CRON_*` variable.

Tune via `PI_CRON_*` environment variables (see the `pi-cron` service in
`compose.yaml` and the header of `cron-runner.py`). Keep `pi-cron` at a single
instance — two would race on deleting the same rows.

When the stack stops (`make down`, `make upgrade`), `pi-cron` lets a running task
finish for up to 2 minutes (`stop_grace_period` in `compose.yaml`); a task still
running then is killed and runs again at its next scheduled time.

Each task is one entry in the `TASKS` list in `cron-runner.py` — a name, an
enable flag, a schedule and the command to run. Schedules are `every_minute()`,
`hourly()`, `daily_at(hour)`, `every(minutes)`, or `scheduled_from_env(...)` to
let the operator choose an interval or a fixed hour from one env var. Adding a
maintenance task is a single entry plus any `PI_CRON_*` variables it reads (see
the comment above `TASKS`).

Scheduler caveats (single-node, in-process — deliberately simple):
- **Interval schedules count from container start, in memory.** A `_INTERVAL`
  longer than how often the container restarts may never fire (the timer resets
  on each start). For long periods (daily+), prefer the fixed-hour form
  (`_HOUR`), which is restart-independent.
- **The scheduler is single-threaded and samples once per minute.** A task that
  runs longer than the gap to a fixed-time task's minute can delay or skip that
  cycle (bounded by `PI_CRON_TASK_TIMEOUT`). Fine for the light default jobs; for
  heavy custom work prefer the UI periodic-task lane.
- Times are **UTC**, whatever the host's time zone.

Upgrading
---------

Read `READ_BEFORE_UPDATE.md` of the new version, then, for a patch release as for
a new minor version:

1. Take the deployment files of the new release (see *The deployment
   directory*: replace the release's files, keep yours). Its `compose.yaml` runs
   its own release and may need settings the old one did not have, so a patch
   release can change these files too.
2. Remove `PI_IMAGE` from `.env`, unless you deliberately run another image. If
   it names another minor version than `compose.yaml`, the containers log
   `WARNING: this image is privacyIDEA <version>, but compose.yaml belongs to
   <version>` at every start.
3. `make init`, which creates the config files the new release added from their
   templates and leaves yours alone.
4. `make upgrade`.

`make upgrade` pulls the new images, backs up, and recreates the services; if a
pull fails, it stops before changing anything. On restart
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
- **Every command fails with `env file .../privacyidea.env not found`** — run
  `make init`, which creates it from `privacyidea.env.template`.
- **`up` fails with `bind source path does not exist: .../mariadb.cnf`** (or
  `.../secrets/database_uri`) — run `make init` for `mariadb.cnf`. For
  `database_uri`, see *External database*.
- **`up` fails with `Pool overlaps with other one on this address space`** — the
  network between Caddy and `pi` collides with an existing one; move it as
  described in *TLS → Client addresses behind Caddy*.
- **Startup logs warn `PI_BASE_URL is not configured`** — set
  `PRIVACYIDEA_PI_BASE_URL` in `privacyidea.env` to your public URL. Password
  recovery stays disabled until you do.
- **`pi` never becomes healthy** — check `docker compose logs pi` and `logs db`.
  Most often the database is not reachable or a migration failed in `pi-init`
  (`docker compose logs pi-init`). With an external database, check the URI in
  `secrets/database_uri` and that the database accepts connections from the
  containers (see *Database or web server outside Docker*).
- **Enckey mismatch on start (`enckey canary verification failed`, exit 2)** —
  the mounted `secrets/enckey` does not match the one the database was built
  with. Restore the original `enckey` from your backup; do not overwrite it.

Uninstall / cleanup
-------------------

```
make down                # stop and remove containers, keep data
docker compose down -v   # also delete the database volume
```

`down -v` destroys the database. Take a backup first (`make backup`) if you may
need the data; the archive holds the database and the keys it needs.
