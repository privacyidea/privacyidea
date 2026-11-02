# shellcheck shell=bash
# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
# Helpers for the scripts in this directory, which source this file.

# The deployment directory, the one above this file.
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Run docker compose in the deployment directory, so that it reads COMPOSE_FILE
# from .env, or compose.yaml and an optional compose.override.yaml.
compose() {
    (cd "${BASE_DIR}" && docker compose "$@")
}

# has_service <name> succeeds when the stack has that service, is_running <name>
# when it is running. The list is read first and matched by the shell: "grep -q"
# would exit on the first match and, with "pipefail", the writer failing on the
# closed pipe would take the whole pipeline down. It is wrapped in newlines so
# that "db" matches a whole service name. A failing compose ends the script, as
# "set -e" does not apply within an "if" and an empty list would read as "no".
has_service() {
    local services
    services=$'\n'"$(compose config --services)"$'\n' || exit 1
    [[ "${services}" == *$'\n'"$1"$'\n'* ]]
}

is_running() {
    local services
    services=$'\n'"$(compose ps --services --filter "status=running")"$'\n' || exit 1
    [[ "${services}" == *$'\n'"$1"$'\n'* ]]
}
