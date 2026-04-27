#!/bin/bash
# Recover a Galera cluster after a simultaneous crash of all nodes.
#
# When both db-1 and db-2 die hard at the same time (power loss, host kernel
# panic, OOM-kill of both containers), neither has safe_to_bootstrap: 1 in
# its grastate.dat. Both refuse to start and the cluster deadlocks.
#
# This script:
#   1. Verifies the cluster is actually wedged (both nodes down, neither
#      safe_to_bootstrap: 1).
#   2. Optionally tars both data volumes to ./backups/recovery-<timestamp>/.
#   3. Runs `mariadbd --wsrep-recover` on each node to read the last
#      committed seqno.
#   4. Picks the node with the highest seqno (db-1 wins on a tie).
#   5. Prompts for confirmation (skip with --yes).
#   6. Sets safe_to_bootstrap: 1 on the chosen node, brings it up, polls
#      until Synced.
#   7. Brings the other node up; it joins via SST. Polls until Synced.
#
# The rest of the stack (HAProxy, ProxySQL, pi, pi-cron) is NOT brought up
# automatically — verify the recovery first, then `docker compose up -d`.
#
# Usage:
#   ./scripts/ha-recover-cluster.sh           # interactive
#   ./scripts/ha-recover-cluster.sh --yes     # skip the confirmation prompt
#   ./scripts/ha-recover-cluster.sh --no-backup  # skip the volume tar step

set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
HA_DIR="$(cd "$HERE/.." && pwd)"
COMPOSE_FILE="$HA_DIR/ha-compose.yaml"
BACKUP_ROOT="$HA_DIR/backups"

YES=0
DO_BACKUP=1
for arg in "$@"; do
    case "$arg" in
        --yes|-y) YES=1 ;;
        --no-backup) DO_BACKUP=0 ;;
        -h|--help) sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown arg: $arg" >&2; exit 2 ;;
    esac
done

# Compose helper — always reference the base file from any cwd.
COMPOSE=(docker compose -f "$COMPOSE_FILE")

NODES="db-1 db-2"

red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
hdr()    { printf '\n── %s ──────────────────────────────────────────────────\n' "$*"; }

# PRE FLIGHT CHECKS
hdr "pre-flight"

if [ ! -f "$COMPOSE_FILE" ]; then
    red "FATAL: $COMPOSE_FILE not found."
    exit 2
fi

# Either node still running? Refuse — this script is for the all-crashed case.
for n in $NODES; do
    state=$("${COMPOSE[@]}" ps --status running --services 2>/dev/null | grep -Fx "$n" || true)
    if [ -n "$state" ]; then
        red "FATAL: $n is still running."
        red "       This script recovers from the all-nodes-crashed deadlock."
        red "       For a single-node failure, just 'docker compose start $n'."
        exit 2
    fi
done

# Read grastate.dat from each node's volume via a throw-away container.
# Returns the file content on stdout, or empty on failure.
read_grastate() {
    local node="$1"
    "${COMPOSE[@]}" run --rm --no-deps --entrypoint cat "$node" \
        /var/lib/mysql/grastate.dat 2>/dev/null || true
}

declare -A GRASTATE
for n in $NODES; do
    GRASTATE[$n]="$(read_grastate "$n")"
    if [ -z "${GRASTATE[$n]}" ]; then
        red "FATAL: cannot read /var/lib/mysql/grastate.dat from $n."
        red "       Volume may be empty (fresh deployment?) or unreadable."
        exit 2
    fi
done

# If either node has safe_to_bootstrap: 1, the cluster is NOT wedged in the
# all-crashed sense — that node can boot normally. Refuse and tell the user.
for n in $NODES; do
    if printf '%s\n' "${GRASTATE[$n]}" | grep -q 'safe_to_bootstrap: 1'; then
        yellow "NOTE: $n already has safe_to_bootstrap: 1."
        yellow "      The cluster is not in the all-crashed deadlock state."
        yellow "      Just 'docker compose up -d $n' and let the other node SST."
        exit 0
    fi
done

green "OK: both nodes down, neither safe_to_bootstrap. Recovery is needed."

# BACKUP
if [ "$DO_BACKUP" -eq 1 ]; then
    TS="$(date -u +%Y%m%dT%H%M%SZ)"
    BACKUP_DIR="$BACKUP_ROOT/recovery-$TS"
    hdr "backup → $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    for n in $NODES; do
        echo "  tarring $n data volume..."
        "${COMPOSE[@]}" run --rm --no-deps \
            -v "$BACKUP_DIR:/backup" \
            --entrypoint tar "$n" \
            -C /var/lib/mysql -czf "/backup/$n-data.tar.gz" .
    done
    # grastate.dat snapshots — small, useful for forensics.
    for n in $NODES; do
        printf '%s\n' "${GRASTATE[$n]}" > "$BACKUP_DIR/$n-grastate.dat"
    done
    green "OK: backup written to $BACKUP_DIR"
else
    yellow "skip-backup: NO ROLLBACK POSSIBLE if recovery picks the wrong node."
fi

# wsrep-recover on each node
hdr "running mariadbd --wsrep-recover on each node"

# Returns the recovered seqno as an integer on stdout, or empty on failure.
recover_seqno() {
    local node="$1"
    local out
    # --wsrep-recover prints "WSREP: Recovered position: <uuid>:<seqno>" to stderr.
    # mariadbd needs the wsrep provider loaded to print "Recovered position",
    # otherwise the plugin is disabled and only InnoDB recovery runs. The
    # binlog_format and gcomm:// flags are required so Galera doesn't refuse
    # to start (default config is MIXED, which Galera rejects).
    out=$("${COMPOSE[@]}" run --rm --no-deps \
        --entrypoint mariadbd "$node" \
        --wsrep-recover --user=mysql --skip-networking \
        --wsrep_on=ON \
        --wsrep_provider=/usr/lib/galera/libgalera_smm.so \
        --wsrep_cluster_address=gcomm:// \
        --binlog_format=ROW 2>&1 || true)
    printf '%s\n' "$out" | sed -n 's/.*Recovered position:[[:space:]]*[^:]*:\(-\?[0-9]\+\).*/\1/p' | tail -n1
}

declare -A SEQNO
for n in $NODES; do
    s="$(recover_seqno "$n")"
    if [ -z "$s" ]; then
        red "FATAL: could not parse recovered seqno from $n."
        red "       Run manually to inspect:"
        red "       docker compose -f $COMPOSE_FILE run --rm --no-deps \\"
        red "         --entrypoint mariadbd $n --wsrep-recover --user=mysql"
        exit 2
    fi
    SEQNO[$n]="$s"
done

echo
printf '  %-6s  %s\n' "node" "recovered seqno"
printf '  %-6s  %s\n' "----" "---------------"
for n in $NODES; do
    printf '  %-6s  %s\n' "$n" "${SEQNO[$n]}"
done

# Pick bootstrap node
# Highest seqno wins. db-1 wins ties (deterministic, matches BOOTSTRAP_NODE
# in ha-compose.yaml so the chosen node aligns with the documented default).
PICK=db-1
if [ "${SEQNO[db-2]}" -gt "${SEQNO[db-1]}" ]; then
    PICK=db-2
fi
OTHER=db-1
[ "$PICK" = "db-1" ] && OTHER=db-2

echo
green "→ bootstrap node: $PICK (seqno ${SEQNO[$PICK]})"
echo  "  joining node:   $OTHER (seqno ${SEQNO[$OTHER]}, will SST from $PICK)"

# Get Confirmation
if [ "$YES" -ne 1 ]; then
    echo
    yellow "About to:"
    yellow "  1. set safe_to_bootstrap: 1 in $PICK's grastate.dat"
    yellow "  2. start $PICK (cluster of size 1)"
    yellow "  3. start $OTHER (joins via SST)"
    yellow ""
    yellow "If you pick the wrong node you LOSE the commits between the two seqnos."
    yellow "Backup is at: ${BACKUP_DIR:-<skipped>}"
    echo
    printf "Type 'yes' to proceed: "
    read -r answer
    if [ "$answer" != "yes" ]; then
        red "aborted."
        exit 1
    fi
fi

# Flip safe_to_bootstrap on the chosen node
hdr "marking $PICK safe_to_bootstrap: 1"
"${COMPOSE[@]}" run --rm --no-deps --entrypoint sed "$PICK" \
    -i 's/safe_to_bootstrap: 0/safe_to_bootstrap: 1/' \
    /var/lib/mysql/grastate.dat
green "OK"

# Start $PICK (the chosen node), poll for Synced state
hdr "starting $PICK and polling for Synced"
"${COMPOSE[@]}" up -d "$PICK"

ROOT_PW="$(cat "$HA_DIR/secrets/mariadb_root_password")"
poll_synced() {
    local node="$1"
    local timeout="$2"
    local start now state
    start=$(date +%s)
    while true; do
        now=$(date +%s)
        if [ $((now - start)) -ge "$timeout" ]; then
            return 1
        fi
        state=$("${COMPOSE[@]}" exec -T "$node" \
            mariadb -uroot -p"$ROOT_PW" --silent -e \
            "SHOW STATUS LIKE 'wsrep_local_state_comment'" 2>/dev/null \
            | awk '{print $NF}' || true)
        if [ "$state" = "Synced" ]; then
            return 0
        fi
        sleep 2
    done
}

if poll_synced "$PICK" 120; then
    green "OK: $PICK is Synced (cluster size 1)"
else
    red "FATAL: $PICK did not reach Synced within 120s."
    red "       Inspect: docker compose -f $COMPOSE_FILE logs $PICK"
    exit 2
fi

# Start $OTHER (nodes), poll for Synced
hdr "starting $OTHER (will SST from $PICK)"
"${COMPOSE[@]}" up -d "$OTHER"

# SST can take a while on large datasets — give it 5 minutes.
if poll_synced "$OTHER" 300; then
    green "OK: $OTHER is Synced (cluster size 2)"
else
    red "FATAL: $OTHER did not reach Synced within 300s."
    red "       Inspect: docker compose -f $COMPOSE_FILE logs $OTHER"
    exit 2
fi

# Print Summary
hdr "recovery complete"
echo "  bootstrap source : $PICK (seqno ${SEQNO[$PICK]})"
echo "  joined via SST   : $OTHER"
if [ "$DO_BACKUP" -eq 1 ]; then
    echo "  backup           : $BACKUP_DIR"
    echo
    echo "  Verify the data, then remove the backup once you're satisfied:"
    echo "    rm -rf '$BACKUP_DIR'"
fi
echo
echo "Bring up the rest of the stack with:"
echo "  docker compose -f $COMPOSE_FILE up -d"
