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

## Generate all at once

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

## Notes

- **`enckey`** must never change once tokens have been created. Back it up
  securely and separately from database backups.
- Rotate the database and admin passwords periodically; `enckey` and `pi_pepper`
  must stay constant for the lifetime of the data.
- The database passwords in `mariadb_password` / `mariadb_root_password` are read
  by both the app and MariaDB from these files — there is nothing to keep in sync
  by hand.
