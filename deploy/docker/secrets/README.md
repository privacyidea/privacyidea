# Secrets directory

The single-node stack reads all sensitive material from files in this directory.
They are mounted into the containers as Docker secrets (`/run/secrets/<name>`).

**Never commit these files.** The parent `.gitignore` ignores everything here
except this README.

## Required files

| File                       | Purpose                                                      |
|----------------------------|--------------------------------------------------------------|
| `enckey`                   | Token/data encryption key. **Losing it makes tokens unrecoverable.** Never change it after tokens exist. |
| `pi_pepper`                | Password-hashing pepper. Losing it makes all stored passwords unverifiable. |
| `secret_key`               | Flask session signing key.                                   |
| `mariadb_password`         | Password for the `pi` database user.                         |
| `mariadb_root_password`    | MariaDB root password (used by `scripts/backup.sh` / `restore.sh`). |
| `bootstrap_admin_password` | Password for the initial admin account created by `pi-init`. |

## Generating the secrets

The easiest way is from `deploy/docker/`:

```bash
make init          # or: ./scripts/init-secrets.sh
```

It creates any missing files with the correct format and permissions, leaves
existing ones untouched, and prints the generated admin password once. The rest
of this section documents the equivalent manual steps.

## Generate all at once (manual)

```bash
cd deploy/docker/secrets

# enckey is raw 96 binary bytes (three 32-byte keys) — do NOT hex/base64 encode it
head -c 96 /dev/urandom                                         > enckey
python3 -c "import secrets; print(secrets.token_urlsafe())"     > pi_pepper
python3 -c "import secrets; print(secrets.token_hex())"         > secret_key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   > mariadb_password
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   > mariadb_root_password
printf 'change-me-before-first-start\n'                          > bootstrap_admin_password

# Files must be readable by the container's non-root user (uid 65532), which
# differs from the host owner — so 0644, not 0600. Protect the directory itself
# instead: only the owner can enter it, so other host users cannot read the keys.
chmod 644 *
chmod 700 .
```

## Why `0644` and not `0600`?

Docker Compose mounts file-based secrets by **bind-mounting them preserving the
host file's ownership and mode** (setting `uid`/`gid`/`mode` on a secret is a
Swarm-only feature that `docker compose` ignores). The containers run as the
non-root user **uid 65532**, which differs from the host user that created the
files — so with `0600` the container gets *permission denied* reading them, and
`pi-init` fails to start. The files therefore need to be world-readable
(`0644`), and secrecy is enforced one level up: the `secrets/` **directory is
`0700`**, so no other host user can traverse into it. Inside the container only
the privacyIDEA process runs, so `0644` there is not an exposure.

`chown`-ing the files to `65532` to keep `0600` is intentionally **not** the
default: it requires root (a normal user cannot chown to a uid it does not own),
it stops the host user from reading the keys — which breaks `scripts/backup.sh` —
and the fixed uid mis-maps under rootless Docker or userns-remap. On a hardened
multi-tenant host you can still do it as a deliberate, root-required opt-in.

## Notes

- **`enckey`** must never change once tokens have been created. Back it up
  securely and separately from database backups.
- Rotate the database and admin passwords periodically; `enckey` and `pi_pepper`
  must stay constant for the lifetime of the data.
- The database passwords in `mariadb_password` / `mariadb_root_password` are read
  by both the app and MariaDB from these files — there is nothing to keep in sync
  by hand.
