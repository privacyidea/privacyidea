privacyIDEA and Docker
======================

We provide a Dockerfile to create a simple privacyIDEA docker container which
runs the application with the gunicorn WSGI server.

> **_NOTE:_**  This is currently very much work-in-progress so expect breaking changes!

Build the container image with:
```
docker build . -f deploy/docker/Dockerfile -t <pi-tag>
```

Run the container with:
```
docker run -p 8080:8080 <pi-tag>:latest
```

A volume is automatically created and mounted at `/etc/privacyidea` in the
container. An existing volume can be given at the container start with:
```
docker run -v <volume-id>:/etc/privacyidea -p 8080:8080 <pi-tag>:latest
```

Runtime configuration
---------------------

The following environment variables control the runtime behaviour of the container:

| Variable            | Default             | Description                                                                              |
|---------------------|---------------------|------------------------------------------------------------------------------------------|
| `PI_WORKERS`        | `2 * CPU cores + 1` | Number of gunicorn worker processes                                                      |
| `PI_PORT`           | `8080`              | Port gunicorn binds to                                                                   |
| `PI_RUN_MIGRATIONS` | `false`             | Set to `true` to run `flask db upgrade` on startup. **Not recommended for multiple replicas.** |
| `PI_SECRETS_DIR`    | `/run/secrets/`     | Directory where secret files are mounted. Override this if your secrets manager mounts files at a different path. |

Secrets
-------

The following secrets must be provided to the container. Each secret can be
passed either as a file (preferred) or as an environment variable.

| Secret                | Purpose                                                         | How to generate                                              |
|-----------------------|-----------------------------------------------------------------|--------------------------------------------------------------|
| `enckey`              | **Master key** — encrypts all token OTP keys and PIN data in the database. If lost, all tokens become unusable. | `head -c 96 /dev/urandom > encKey` |
| `SECRET_KEY`          | **Session secret** — signs Flask session cookies (HMAC). If changed, all active sessions are invalidated. | `python -c 'import secrets; print(secrets.token_hex())'` |
| `PI_PEPPER`           | **Password pepper** — added to admin password hashes to harden against DB leaks. | `python -c 'import secrets; print(secrets.token_urlsafe())'` |
| `mariadb_password`    | **Database password** — used to connect to MariaDB/PostgreSQL.  | `pwgen 20 1`                                                 |
| `audit_key_private`   | **Audit signing key** — RSA private key used to sign each audit log entry for tamper detection. | `openssl genrsa -out audit_key_private.pem 2048` |
| `audit_key_public`    | **Audit verification key** — RSA public key used to verify audit log signatures. | `openssl rsa -in audit_key_private.pem -pubout -out audit_key_public.pem` |

### How secrets are resolved

privacyIDEA resolves secrets in the following order:

1. **Auto-detection by filename** — `enckey`, `audit_key_private` and `audit_key_public`
   are automatically picked up if they exist as files in `PI_SECRETS_DIR`
   (default: `/run/secrets/`). No extra environment variable is needed.

2. **`{NAME}_FILE` env var** — for `SECRET_KEY`, `PI_PEPPER` and the database password,
   set an env var pointing to the file, e.g.:
   ```
   SECRET_KEY_FILE=/run/secrets/secret_key
   PI_PEPPER_FILE=/run/secrets/pi_pepper
   PI_DB_PASSWORD_FILE=/run/secrets/mariadb_password
   ```

3. **Plain env var** — secrets can also be passed directly as environment variable values
   (less secure, as values may appear in process listings):
   ```
   SECRET_KEY=<value>
   PI_PEPPER=<value>
   ```

> **Note:** `enckey` must always be a **file** — it cannot be passed as a plain value
> because privacyIDEA reads it directly from disk at runtime.

Database migrations
-------------------

Database migrations are **not** run automatically on startup by default.
To run migrations, either:

- Set `PI_RUN_MIGRATIONS=true` (only safe for single-replica deployments), or
- Run manually inside the container:
  ```
  docker exec -i <container-name> flask db upgrade
  ```
- Use a Kubernetes init container to run migrations before the app starts.

Docker compose
--------------

A compose file can be used to start up the complete stack. An example is given
in `deploy/docker/compose.yaml`. The `SECRET_KEY` and `PI_PEPPER` environment
variables must be provided at startup:
```
SECRET_KEY=$SECRET_KEY PI_PEPPER=$PI_PEPPER docker compose -f deploy/docker/compose.yaml up
```

Setup privacyIDEA
-----------------

Commands can be run inside the container with:
```
docker exec -i <container-name> pi-manage ...
```

To set up a running container use:
```
docker exec -i <container-name> pi-manage setup create_tables
```

Configuration can be imported in the container with:
```
cat <policy-template.yaml> | docker exec -i <container-name> pi-manage config import
```

Kubernetes and secrets managers
-------------------------------

The secrets handling supports any file-based secret injection by setting
`PI_SECRETS_DIR` to the directory where secrets are mounted. This works with
any secrets manager that can inject secrets as files into a container, such as
HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, or Kubernetes native
secret volumes.

Set `PI_SECRETS_DIR` to the mount path:

```
PI_SECRETS_DIR=/mnt/secrets/
```

The container will then look for secret files named `enckey`, `audit_key_private`
and `audit_key_public` in that directory automatically.

For value-based secrets use the `{NAME}_FILE` pattern pointing to the mounted file:
```
SECRET_KEY_FILE=/mnt/secrets/secret_key
PI_PEPPER_FILE=/mnt/secrets/pi_pepper
PI_DB_PASSWORD_FILE=/mnt/secrets/mariadb_password
```

For Kubernetes, use an **init container** to run `flask db upgrade` instead of
setting `PI_RUN_MIGRATIONS=true`, to avoid concurrent migration races when
multiple replicas start simultaneously.

Running with `docker run`
------------------------

To run the container with secrets mounted as files using `docker run`:

```bash
docker run -p 8080:8080 \
  # Mount the master encryption key (required, must be a file)
  -v /path/to/enckey:/run/secrets/enckey:ro \
  # Mount the audit RSA key pair (required for audit signing)
  -v /path/to/audit_key_private.pem:/run/secrets/audit_key_private:ro \
  -v /path/to/audit_key_public.pem:/run/secrets/audit_key_public:ro \
  # Pass value-based secrets via _FILE env vars pointing to mounted files
  -v /path/to/secret_key.txt:/run/secrets/secret_key:ro \
  -e SECRET_KEY_FILE=/run/secrets/secret_key \
  -v /path/to/pi_pepper.txt:/run/secrets/pi_pepper:ro \
  -e PI_PEPPER_FILE=/run/secrets/pi_pepper \
  # Database connection
  -e PI_DB_USER=pi \
  -e PI_DB_HOST=db \
  -e PI_DB_NAME=pi \
  -v /path/to/db_password.txt:/run/secrets/mariadb_password:ro \
  -e PI_DB_PASSWORD_FILE=/run/secrets/mariadb_password \
  <pi-tag>:latest
```

All secret files are mounted read-only (`:ro`). The `enckey`, `audit_key_private`
and `audit_key_public` files are auto-detected from `/run/secrets/` by filename —
no extra env var is needed for them.

TODO:
-----
* Add a reverse proxy service (https://github.com/docker/awesome-compose/blob/master/nginx-flask-mysql/compose.yaml)
* Add an example for a `configs` element to the `compose.yaml` (https://docs.docker.com/reference/compose-file/services/#configs)
* Add dependencies in the container (PyKCS11, gssapi)
* Add recurring tasks runner (cron? via docker? via redis?)
