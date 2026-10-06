#!/usr/bin/env bash
# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
# Backup the privacyIDEA database and all critical secrets.
# Run from anywhere — the script resolves paths relative to the deployment
# directory. With an external database (compose.external-db.yaml) the archive
# holds the keys only; back the database up with its own tools.
#
# Usage:
#   ./scripts/backup.sh [OPTIONS]
#
# Options:
#   --encrypt                Encrypt the archive with age (passphrase, interactive)
#   --encrypt-key <PUBKEY>   Encrypt with an age public key (non-interactive, for cron)
#
# Output (unencrypted):  backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz
# Output (encrypted):    backups/privacyidea_YYYYMMDD_HHMMSS.tar.gz.age
#
# Archive contents:
#   database.sql       — full logical dump of the pi database (bundled MariaDB only)
#   enckey             — PrivacyIDEA token encryption key
#   pi_pepper          — password hashing pepper
#   secret_key         — Flask session signing key
#   audit_key_private  — audit signing private key (if present)
#   audit_key_public   — audit signing public key (if present)
#
# IMPORTANT: These keys and the database dump must stay together. A database
#            without its matching enckey/pi_pepper cannot be used; without the
#            matching audit keypair, existing audit-log signatures cannot be
#            verified after a restore.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=SCRIPTDIR/common.sh
. "${SCRIPT_DIR}/common.sh"
SECRETS_DIR="${BASE_DIR}/secrets"
BACKUP_DIR="${BASE_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="privacyidea_${TIMESTAMP}"
BACKUP_WORK="${BACKUP_DIR}/${BACKUP_NAME}"

ENCRYPT=false
ENCRYPT_KEY=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --encrypt)
            ENCRYPT=true
            shift
            ;;
        --encrypt-key)
            ENCRYPT=true
            ENCRYPT_KEY="${2:-}"
            if [[ -z "${ENCRYPT_KEY}" ]]; then
                echo "ERROR: --encrypt-key requires a public key argument."
                exit 1
            fi
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--encrypt] [--encrypt-key <age-public-key>]"
            exit 1
            ;;
    esac
done

if [[ "${ENCRYPT}" == "true" ]] && ! command -v age &>/dev/null; then
    echo "ERROR: 'age' is not installed. Install it with: apt install age"
    echo "       Or omit --encrypt to create an unencrypted backup."
    exit 1
fi

# compose.external-db.yaml takes the db service out of the stack. Its database is
# backed up with that database's own tools; the archive then holds the keys only.
EXTERNAL_DB=false
if ! has_service db; then
    EXTERNAL_DB=true
fi

if [[ "${EXTERNAL_DB}" == "false" ]] && ! is_running db; then
    echo "ERROR: the db service is not running. Start the stack before taking a backup."
    exit 1
fi

mkdir -p "${BACKUP_WORK}"

if [[ "${EXTERNAL_DB}" == "true" ]]; then
    echo "[backup] The database is external: not dumped. Back it up with its own tools."
else
    echo "[backup] Dumping database..."
    # The $(...) has to expand in the container, where the secret is mounted.
    # shellcheck disable=SC2016
    compose exec -T db \
        sh -c 'mariadb-dump \
            -uroot \
            -p"$(cat /run/secrets/mariadb_root_password)" \
            --single-transaction \
            --skip-lock-tables \
            --routines \
            --triggers \
            --add-drop-database \
            --databases pi' \
        > "${BACKUP_WORK}/database.sql"
fi

echo "[backup] Copying secrets..."
cp "${SECRETS_DIR}/enckey"     "${BACKUP_WORK}/enckey"
cp "${SECRETS_DIR}/pi_pepper"  "${BACKUP_WORK}/pi_pepper"
cp "${SECRETS_DIR}/secret_key" "${BACKUP_WORK}/secret_key"
# Audit signing keypair, if present — needed so restored audit entries stay
# verifiable and the (fail-closed) stack can start after a disaster recovery.
for audit_key in audit_key_private audit_key_public; do
    if [[ -f "${SECRETS_DIR}/${audit_key}" ]]; then
        cp "${SECRETS_DIR}/${audit_key}" "${BACKUP_WORK}/${audit_key}"
    fi
done

echo "[backup] Creating archive..."
ARCHIVE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
tar -czf "${ARCHIVE}" -C "${BACKUP_DIR}" "${BACKUP_NAME}"
rm -rf "${BACKUP_WORK:?}"

if [[ "${ENCRYPT}" == "true" ]]; then
    echo "[backup] Encrypting archive..."
    if [[ -n "${ENCRYPT_KEY}" ]]; then
        age -r "${ENCRYPT_KEY}" -o "${ARCHIVE}.age" "${ARCHIVE}"
    else
        age -p -o "${ARCHIVE}.age" "${ARCHIVE}"
    fi
    rm -f "${ARCHIVE}"
    ARCHIVE="${ARCHIVE}.age"
fi

BACKUP_SIZE=$(du -sh "${ARCHIVE}" | cut -f1)
echo "[backup] Done: ${ARCHIVE} (${BACKUP_SIZE})"
echo ""
if [[ "${EXTERNAL_DB}" == "true" ]]; then
    echo "NOTE: This archive holds the keys only. The external database needs its own"
    echo "      backup, and that backup is useless without these keys."
fi
if [[ "${ENCRYPT}" == "false" ]]; then
    echo "WARNING: This archive is NOT encrypted and contains sensitive key material."
    echo "         Consider using --encrypt or moving it to encrypted storage."
fi
echo "Store this file in a secure location separate from this host."
