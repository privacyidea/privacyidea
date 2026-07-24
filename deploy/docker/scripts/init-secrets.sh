#!/usr/bin/env bash
# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
# Generate the secret files required by compose.yaml.
#
# Idempotent: existing, non-empty secret files are left untouched, so this is
# safe to re-run. Files are written mode 0644 (readable by the container's
# non-root user, uid 65532, which differs from the host owner) and the directory
# is locked to 0700 so other host users cannot read the keys. See
# secrets/README.md for the rationale.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="$(dirname "$SCRIPT_DIR")/secrets"

mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# gen <name> <command...> — write the command's output to the secret file,
# unless a non-empty file already exists.
gen() {
    local name="$1"; shift
    local file="$SECRETS_DIR/$name"
    if [[ -s "$file" ]]; then
        echo "[init-secrets] $name already exists — keeping it"
        return 0
    fi
    "$@" > "$file"
    chmod 644 "$file"
    echo "[init-secrets] generated $name"
    return 0
}

# enckey is raw 96 binary bytes (three 32-byte keys) — never hex/base64 encoded.
gen enckey                head -c 96 /dev/urandom
gen pi_pepper             python3 -c "import secrets; print(secrets.token_urlsafe())"
gen secret_key            python3 -c "import secrets; print(secrets.token_hex())"
gen mariadb_password      python3 -c "import secrets; print(secrets.token_urlsafe(32))"
gen mariadb_root_password python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Audit signing keypair. DockerConfig auto-detects /run/secrets/audit_key_{public,private}
# and privacyIDEA signs every audit entry (and API responses) with it. Without the
# keypair, audit and response signing are silently disabled — so generate it here.
if [[ -s "$SECRETS_DIR/audit_key_private" ]]; then
    echo "[init-secrets] audit_key_private already exists — keeping it"
else
    openssl genrsa -out "$SECRETS_DIR/audit_key_private" 2048 2>/dev/null
    openssl rsa -in "$SECRETS_DIR/audit_key_private" -pubout -out "$SECRETS_DIR/audit_key_public" 2>/dev/null
    chmod 644 "$SECRETS_DIR/audit_key_private" "$SECRETS_DIR/audit_key_public"
    echo "[init-secrets] generated audit_key_private + audit_key_public"
fi

# The admin password must be shown once so the operator can log in the first time.
BOOTSTRAP_FILE="$SECRETS_DIR/bootstrap_admin_password"
NEW_ADMIN_PW=false
[[ -s "$BOOTSTRAP_FILE" ]] || NEW_ADMIN_PW=true
gen bootstrap_admin_password python3 -c "import secrets; print(secrets.token_urlsafe(18))"
if [[ "$NEW_ADMIN_PW" == "true" ]]; then
    echo
    echo "  Initial admin password (save it now, then change it after first login):"
    echo "      $(cat "$BOOTSTRAP_FILE")"
    echo
fi

echo "[init-secrets] done."
