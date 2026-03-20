#!/usr/bin/env bash
# Backup the privacyIDEA database and all critical secrets.
# Run from the deploy/docker/ha/ directory or any location — the script resolves paths.
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
#   database.sql  — full logical dump of the pi database
#   enckey        — PrivacyIDEA token encryption key
#   pi_pepper     — password hashing pepper
#   secret_key    — Flask session signing key
#
# IMPORTANT: These three keys and the database dump must stay together.
#            A database without its matching enckey and pi_pepper cannot be used.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${BASE_DIR}/ha-compose.yaml"
SECRETS_DIR="${BASE_DIR}/secrets"
BACKUP_DIR="${BASE_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="privacyidea_${TIMESTAMP}"
BACKUP_WORK="${BACKUP_DIR}/${BACKUP_NAME}"

# --- Argument parsing ----------------------------------------------------------
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

# --- Stack check ---------------------------------------------------------------
if ! docker compose -f "${COMPOSE_FILE}" ps --services --filter "status=running" 2>/dev/null | grep -q "^db-1$"; then
    echo "ERROR: db-1 is not running. Start the stack before taking a backup."
    exit 1
fi

mkdir -p "${BACKUP_WORK}"

# --- Database dump -------------------------------------------------------------
echo "[backup] Dumping database (db-1)..."
docker compose -f "${COMPOSE_FILE}" exec -T db-1 \
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

# --- Secrets -------------------------------------------------------------------
echo "[backup] Copying secrets..."
cp "${SECRETS_DIR}/enckey"     "${BACKUP_WORK}/enckey"
cp "${SECRETS_DIR}/pi_pepper"  "${BACKUP_WORK}/pi_pepper"
cp "${SECRETS_DIR}/secret_key" "${BACKUP_WORK}/secret_key"

# --- Archive -------------------------------------------------------------------
echo "[backup] Creating archive..."
ARCHIVE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
tar -czf "${ARCHIVE}" -C "${BACKUP_DIR}" "${BACKUP_NAME}"
rm -rf "${BACKUP_WORK:?}"

# --- Encrypt (optional) --------------------------------------------------------
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

# --- Done ----------------------------------------------------------------------
BACKUP_SIZE=$(du -sh "${ARCHIVE}" | cut -f1)
echo "[backup] Done: ${ARCHIVE} (${BACKUP_SIZE})"
echo ""
if [[ "${ENCRYPT}" == "false" ]]; then
    echo "WARNING: This archive is NOT encrypted and contains sensitive key material."
    echo "         Consider using --encrypt or moving it to encrypted storage."
fi
echo "Store this file in a secure location separate from this host."
