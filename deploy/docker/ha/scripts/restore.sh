#!/usr/bin/env bash
# Restore the privacyIDEA database from a backup archive.
# Run from the deploy/docker/ha/ directory or any location — the script resolves paths.
#
# Usage:
#   ./scripts/restore.sh <backup-file.tar.gz>
#   ./scripts/restore.sh <backup-file.tar.gz.age>   (age-encrypted archive)
#
# The backup archive must contain:
#   database.sql  — logical SQL dump
#   enckey        — encryption key used when the backup was taken
#   pi_pepper     — pepper used when the backup was taken
#
# WARNING: This DROPS and recreates the pi database. All current data will be lost.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${BASE_DIR}/ha-compose.yaml"
SECRETS_DIR="${BASE_DIR}/secrets"

# --- Argument validation -------------------------------------------------------
BACKUP_FILE="${1:-}"
if [[ -z "${BACKUP_FILE}" ]]; then
    echo "Usage: $0 <backup-file.tar.gz[.age]>"
    exit 1
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "ERROR: File not found: ${BACKUP_FILE}"
    exit 1
fi

# --- Stack check ---------------------------------------------------------------
if ! docker compose -f "${COMPOSE_FILE}" ps --services --filter "status=running" 2>/dev/null | grep -q "^db-1$"; then
    echo "ERROR: db-1 is not running. Start the stack before restoring."
    exit 1
fi

# --- Extract to temp dir -------------------------------------------------------
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

ARCHIVE="${BACKUP_FILE}"

# Decrypt if this is an age-encrypted archive
if [[ "${BACKUP_FILE}" == *.age ]]; then
    if ! command -v age &>/dev/null; then
        echo "ERROR: 'age' is not installed but the archive is encrypted. Install it with: apt install age"
        exit 1
    fi
    echo "[restore] Decrypting archive..."
    ARCHIVE="${TEMP_DIR}/decrypted.tar.gz"
    age -d -o "${ARCHIVE}" "${BACKUP_FILE}"
fi

echo "[restore] Extracting archive..."
if tar -tzf "${ARCHIVE}" | grep -q '/'; then
    tar -xzf "${ARCHIVE}" -C "${TEMP_DIR}" --strip-components=1
else
    tar -xzf "${ARCHIVE}" -C "${TEMP_DIR}"
fi

if [[ ! -f "${TEMP_DIR}/database.sql" || ! -f "${TEMP_DIR}/enckey" ]]; then
    echo "ERROR: Archive is missing database.sql or enckey. Is this a valid privacyIDEA backup?"
    exit 1
fi

# --- Key checks ----------------------------------------------------------------
check_key_mismatch() {
    local name="$1"
    local current_file="${SECRETS_DIR}/${name}"
    local backup_file="${TEMP_DIR}/${name}"

    if [[ ! -f "${backup_file}" ]]; then
        echo "WARNING: Backup does not contain '${name}' (older backup format). Skipping check."
        return
    fi

    local current backup
    current=$(cat "${current_file}")
    backup=$(cat "${backup_file}")

    if [[ "${current}" != "${backup}" ]]; then
        echo "========================================================================"
        echo "  WARNING: ${name} mismatch!"
        echo "========================================================================"
        echo "  The ${name} in this backup does NOT match secrets/${name} on this host."
        if [[ "${name}" == "enckey" ]]; then
            echo "  Token data will be permanently unrecoverable without the matching enckey."
        elif [[ "${name}" == "pi_pepper" ]]; then
            echo "  All user and admin passwords will fail to verify without the matching pepper."
        fi
        echo ""
        echo "  To fix: replace secrets/${name} with the copy from the backup archive,"
        echo "  then restart the stack BEFORE proceeding with the restore."
        echo ""
        read -rp "  Proceed anyway? (type YES to confirm) " confirm
        if [[ "${confirm}" != "YES" ]]; then
            echo "Restore aborted."
            exit 1
        fi
    fi
}

check_key_mismatch "enckey"
check_key_mismatch "pi_pepper"

# --- Final confirmation --------------------------------------------------------
echo ""
echo "========================================================================"
echo "  This will DROP and recreate the pi database on db-1."
echo "  All current data will be permanently lost."
echo "========================================================================"
echo ""
read -rp "Proceed with restore? (type YES to confirm) " confirm
if [[ "${confirm}" != "YES" ]]; then
    echo "Restore aborted."
    exit 1
fi

# --- Import --------------------------------------------------------------------
echo "[restore] Importing database into db-1..."
docker compose -f "${COMPOSE_FILE}" exec -T db-1 \
    sh -c 'mariadb -uroot -p"$(cat /run/secrets/mariadb_root_password)"' \
    < "${TEMP_DIR}/database.sql"

echo "[restore] Done."
echo ""
echo "Restart the privacyIDEA workers to pick up the restored data:"
echo "  docker compose -f ha-compose.yaml restart pi"
