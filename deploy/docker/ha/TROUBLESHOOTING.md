# Troubleshooting

Incident playbooks for the privacyIDEA HA stack. Day 2 ops content (normal
monitoring, routine tasks) lives in [`OPERATIONS.md`](OPERATIONS.md); the
quick-start is in [`README.md`](README.md).

Each section starts with the symptom, then diagnosis steps, then fix.

---

## A container is unhealthy

**Symptom.** `docker compose ps` shows a service as `(unhealthy)` or keeps
restarting.

**Diagnose.**
```bash
docker inspect <container> --format='{{json .State.Health}}' | jq
docker compose -f ha-compose.yaml logs --tail=200 <service>
```

The `Health` output shows the last few healthcheck invocations — look at
the `Output` of the most recent one for a specific error. Logs often show
the root cause just before the first restart.

**Common causes.**

- **Missing or unreadable secret.** `open /run/secrets/<name>: no such
  file` in logs → the host file doesn't exist under `secrets/`, or is
  chmod'd wrong.
- **DB not ready when pi starts.** `pi-init` should gate this via
  `depends_on: db-1: service_healthy`. If you disabled that, pi workers
  race ahead and crash.
- **Bind-mount source missing.** Docker creates an empty directory at the
  target rather than failing. If a config file mysteriously looks empty,
  check that the host path actually exists.

---

## Connection refused to HAProxy

**Symptom.** `curl http://<host>:8000/` returns `Connection refused` or
HAProxy's "503 Service Unavailable".

**Diagnose.**
```bash
docker compose -f ha-compose.yaml ps             # are pi workers Healthy?
docker compose -f ha-compose.yaml logs pi-proxy  # HAProxy's view
```

Visit `http://<host>:8404/stats` (HAProxy stats page) to see backend state.

**Fix.**

- If `pi-1` / `pi-2` are unhealthy, work through the "container unhealthy"
  playbook above first — HAProxy takes them out of rotation automatically.
- If HAProxy itself is down, check `logs pi-proxy` for config syntax errors
  in `haproxy-web.cfg`. A malformed `haproxy-web.cfg` fails the container
  at start.

---

## Galera node won't become `Synced`

**Symptom.** `SHOW STATUS LIKE 'wsrep_local_state_comment'` returns
anything other than `Synced` for more than a minute. ProxySQL keeps the
node in `OFFLINE_SOFT` (HG 30).

**Diagnose.**
```bash
docker exec ha-db-2-1 mariadb -uroot -p$(cat secrets/mariadb_root_password) \
  -e "SHOW STATUS LIKE 'wsrep%';" | less
docker compose -f ha-compose.yaml logs db-2
```

Most likely one of:

- **`Joining` / `Joined`** — state transfer in progress. IST is fast
  (seconds); SST can take minutes on a large DB. If it keeps restarting,
  check for `mariadb_backup_checkpoints missing` on the joiner and errors
  around `WSREP_SST` on the donor — see the next playbook.
- **`Donor/Desynced`** — this node is donating state to another. Temporary
  and recovers once the recipient reaches `Synced`.
- **`Initialized` / `Disconnected`** — cannot reach the other node.
  Check network between containers, and that `wsrep_cluster_address`
  contains both node names.

### SST fails with SIGSEGV / `mariadb_backup_checkpoints missing`

**Symptom on joiner logs.**
```
[ERROR] WSREP: Will never receive state. Need to abort.
mariadbd got signal 11 ;
[ERROR] mariadb_backup_checkpoints missing, failed mariadb-backup/SST on donor
```

The donor's `mariabackup` subprocess crashed without producing the
checkpoint file. Known-regressing causes:

- **Floating image tag drifted.** The stack pins `mariadb:11.4.4`; if you
  changed it to a floating tag (`mariadb:11.4` or `latest`), upstream may
  have regressed mariabackup on that combination. Pin to a known-good
  digest or point release.
- **Network instability between Galera nodes.** Check that ports `4444`,
  `4567`, `4568` are unblocked and low-latency.

**Fix.**

1. Pin the mariadb image to a specific patch version in `ha-compose.yaml`.
2. `docker compose down -v` on a lab/fresh deployment to retest SST. Never
   `down -v` on a production stack — you lose the DB.
3. If the donor consistently crashes on SST, bump to a newer mariadb point
   release and retest.

---

## All Galera nodes crashed simultaneously

**Symptom.** Both `db-1` and `db-2` refuse to start, logging:
```
[ERROR] WSREP: It may not be safe to bootstrap the cluster from this node.
It was not the last one to leave the cluster and may not contain all the
updates. To force cluster bootstrap with this node, edit the grastate.dat
file manually and set safe_to_bootstrap to 1.
```

Neither node has `safe_to_bootstrap: 1` in its `grastate.dat`, so neither
will start first, and they deadlock each other.

**Diagnose.** On each node, identify which has the highest `seqno`:
```bash
docker compose -f ha-compose.yaml run --rm --no-deps \
  --entrypoint mariadbd db-1 \
  --wsrep-recover --user=mysql --skip-networking \
  --wsrep_on=ON \
  --wsrep_provider=/usr/lib/galera/libgalera_smm.so \
  --wsrep_cluster_address=gcomm:// \
  --binlog_format=ROW 2>&1 | grep "Recovered position"
```

The wsrep flags are required — without them the provider plugin stays
disabled and only InnoDB recovery runs, so no "Recovered position" line
is printed. The recovery script below sets these automatically.

The node with the highest recovered seqno has the most recent committed
data and should be the one to bootstrap.

**Fix.** Run the recovery helper from the `deploy/docker/ha/` directory:

```bash
./scripts/ha-recover-cluster.sh
```

The script automates the full procedure:

1. Verifies both nodes are down and neither has `safe_to_bootstrap: 1`.
2. Tars both data volumes to `backups/recovery-<timestamp>/` for rollback
   in case the wrong node is chosen. Skip with `--no-backup`.
3. Runs `mariadbd --wsrep-recover` on each node, parses the seqnos, and
   shows a comparison table.
4. Picks the node with the highest seqno (db-1 wins on a tie) and prompts
   for confirmation. Pass `--yes` for automation.
5. Sets `safe_to_bootstrap: 1` on the chosen node, brings it up, polls
   until `Synced`.
6. Brings the other node up; it joins via SST. Polls until `Synced`.

The rest of the stack (HAProxy, ProxySQL, pi, pi-cron) is **not** brought
up automatically — verify the data first, then `docker compose up -d`.

**Manual fallback** (if you want to do it by hand):

1. Pick the node with the highest seqno from the diagnose step above.
2. Edit its `grastate.dat` to set `safe_to_bootstrap: 1`.
3. `docker compose up -d <chosen>` — the entrypoint reads
   `safe_to_bootstrap: 1` and bootstraps with `gcomm://`.
4. Wait for `wsrep_local_state_comment = Synced`.
5. `docker compose up -d <other>` — it joins via SST.

---

## `pi-cron` keeps crashing

**Symptom.** `docker compose ps` shows `pi-cron` in `Restarting` status;
logs contain:
```
FileNotFoundError: [Errno 2] No such file or directory: 'pi-manage-cron'
```

**Cause.** You're on an older build where `cron-runner.py` called a
non-existent CLI. The correct entry point is `privacyidea-cron`.

**Fix.** Pull latest `cron-runner.py` and rebuild:
```bash
docker compose -f ha-compose.yaml build pi-cron
docker compose -f ha-compose.yaml up -d pi-cron
```

---

## Admin login fails with "Unknown realm"

**Symptom.** API or UI login as the bootstrap admin returns
`Authentication failure. Unknown realm: ...`.

**Cause.** The bootstrap admin is a superadmin with no realm. Login
requests that include a `realm` field are interpreted as realm-user
logins, which need the realm to exist.

**Fix.** Submit the login without a `realm` field (the default admin UI
does this correctly). If you're scripting against the API, make sure
realm-scoped logins only happen after you've actually created the realm.

---

## Database restore fails "enckey mismatch"

**Symptom.** `scripts/restore.sh` warns that the `enckey` in the backup
doesn't match the one in `secrets/` on this host, and aborts.

**Cause.** You're restoring a backup taken with a different `enckey`. If
the two keys don't match, all encrypted token data in the backup is
undecryptable on this host — restoring would import data that can't be
used.

**Fix.** Restore the `enckey` from that backup alongside the database.
Never restore a database dump without the matching `enckey` and
`pi_pepper`. If you've lost the backup's `enckey`, the encrypted data is
permanently unrecoverable — start over with new tokens.

---

## Where to look when nothing on this page matches

1. `docker compose -f ha-compose.yaml ps` — who's unhealthy?
2. `docker compose -f ha-compose.yaml logs --tail=200 <service>` for each
   unhealthy service.
3. HAProxy stats at `http://<host>:8404/stats` for the web tier.
4. ProxySQL hostgroup state (see [`OPERATIONS.md`](OPERATIONS.md)) for the
   DB tier.
5. Galera `wsrep_*` status variables on each db node for replication
   state.
