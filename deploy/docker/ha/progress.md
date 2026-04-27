# HA work — progress & plan

Living tracker for the HA docker setup. Internal, not customer-facing.
Order roughly reflects intended execution.

---

## Resume here (last touched 2026-04-24)

**State:** stack torn down clean (`make down` left no volumes or containers).
All code changes from today are saved in the working tree. Nothing committed
on top of the session's starting commit `63a875c39`.

**Last completed:** section 4c — security / correctness (all four items):
ProxySQL monitor user, Dockerfile cleanup, HAProxy TLS termination, enckey
canary. Plus Galera TLS (section 3 piece 1) and the full failover test
scaffolding. Branch is in good shape.

**Pick up next** — ordered by suggested momentum:

1. **Bootstrap CLI `ha-init.sh`** (section 4a). Replaces the cert-gen
   scripts + secret one-liners with a single command. Biggest UX lever.
2. **More failover scenarios** in `run_failover_test.py` (section 1,
   remaining bullets). Kill reader, kill pi worker, kill ProxySQL (SPOF
   demo), kill HAProxy (SPOF demo).
3. ~~**Galera all-crashed recovery helper script** (section 2, remaining).~~
   **Done 2026-04-27.** `scripts/ha-recover-cluster.sh` +
   `tests/ha-test/run_recovery_test.py`. Run via `make recovery-test`.
4. **Sizing table** (section 2, remaining). RAM/CPU vs req/s, LDAP
   multiplier, audit-volume implications.
5. **Rolling-upgrade playbooks** for PI and Galera (section 2, remaining).

Tier G piece 2 (cross-host validation), tier H, tier J, the full upgrade
workstream (section 4), consulting install guide PDF (section 4a), and
multi-region guidance (section 4b) all stay deferred — captured below.

**To start the stack again:**
```
cd tests/ha-test
make rebuild PYTHON=../../.venv313/bin/python   # if Dockerfile/entrypoint changed
# or:
make fresh   PYTHON=../../.venv313/bin/python   # if only compose/config changed
```

---

## Where we are

- Tier F (single-host docker HA) is functional.
- Failover verified manually:
  - Stream of challenge-response auths via locust while the writer Galera
    node is killed — no dropped requests for traffic that had not yet
    reached the failing worker.
  - Downed node restarted and automatically rejoined the cluster
    (confirmed by `wsrep_local_state_comment = Synced`).
- TODO.md items are current. Dockerfile volume cleanup, Galera TLS, dedicated
  ProxySQL monitor user, HAProxy timeouts, and enckey canary remain open.
- Commit history contains one "not working currently" commit
  (`b435c2e8b`) — needs squashing before this becomes a PR.

## Product positioning (agreed)

Primary offerings, in order of customer skill:

- **B** — single VM, deb + hypervisor HA. Entry baseline, no PI-level redundancy.
- **D** — two deb VMs + Galera. Classic full HA, deb world.
- **F** — docker compose HA, single host. Stepping stone into container HA.
- **H** — multi-host docker HA. Full HA, container world.

Not offered: **I** (Kubernetes — customers lack the skill, and consulting
does not operate it either). **C**, **E**, **G** documented for completeness
but not primary offerings. G is the technical bridge from F to H.

Internal doc capturing this: `PRODUCT.md` (rewritten 2026-04-24 around the
A–I tier table and decision tree).

---

## Plan

### 1. Automated failover test (next up)

Goal: **one command, go/no-go result**. Local only — no CI integration yet.
Base on the existing `tests/ha-test/` scripts.

Fix first (small, worth doing regardless):
- [x] Remove hardcoded absolute paths — now resolved relative to script.
- [x] Port mismatch — aligned on `http://localhost:8000` (HAProxy). Override
      via `PI_BASE_URL` env var.
- [x] Policy pre-check — now checks for `hotp_challenge_response` by name.
- [x] Admin password — defaults to `secrets/bootstrap_admin_password` when
      running against HA stack; `PI_ADMIN_PASSWORD` env overrides.

Orchestrator (`tests/ha-test/run_failover_test.py`):
- [x] `docker compose up -d --wait`
- [x] Run `data_generator.py`
- [x] Start locust headless: `--csv results/run --only-summary`
- [x] After N seconds: `docker compose stop <target>`
- [x] After M seconds: `docker compose start <target>`
- [x] Poll `wsrep_local_state_comment` until `Synced`, record time-to-rejoin.
- [x] Parse locust CSV, assert thresholds, exit 0/non-zero.
- [x] `--skip-up` and `--skip-provision` flags for iteration.

Metrics and thresholds (v1 defaults, tune after first real runs):
- [x] Failure rate across full run — `< 2%` (CLI: `--max-failure-rate`)
- [x] Longest contiguous failure window — `< 10 s` (CLI: `--max-failure-window`)
- [x] Rejoin time from `docker start` to `Synced` — `< 60 s` (CLI: `--max-rejoin`)
- [ ] Time to first successful request after stop — not yet computed
      (requires aligning stop timestamp with locust's history buckets).
- [ ] Stretch: zero-loss invariant — for every token, final counter equals
      number of ACCEPT responses. Not yet implemented.

Scenarios:
- [x] Kill Galera writer (`db-1`) mid-run, restart, verify rejoin.
- [ ] Kill Galera reader (`db-2`) mid-run.
- [ ] Kill a `pi` worker mid-run.
- [ ] Stop ProxySQL mid-run (SPOF demonstration — expect failure).
- [ ] Stop HAProxy mid-run (SPOF demonstration).

Realm/resolver bootstrap (test scaffolding only, not in `pi-init`):
- [x] `tests/ha-test/testdata/users` — passwd-format fake users (19 rows).
- [x] `tests/ha-test/ha-compose.test.yaml` — compose override bind-mounting
      the file into `pi` and `pi-init` at `/etc/privacyidea/test_users`.
- [x] `data_generator.py` provisions a passwdresolver + realm via the API
      before creating tokens (`ensure_resolver`, `ensure_realm`).
- [x] `run_failover_test.py` passes both compose files via `-f`.

Remaining before this subtask is "done":
- [x] First real run end-to-end, verify thresholds are reasonable.
      **PASS** on 2026-04-24. 984 requests, 0 failures, 0s failure window,
      4s rejoin time (IST). Default thresholds (2% / 10s / 60s) held with
      plenty of margin — worth tightening once we see a few more runs.

### Stack bugs surfaced by the first test run (2026-04-24)

- [x] **Galera SST failed.** Root cause: `mariadb:11.4` floating tag had
      regressed on the donor side; SST completed cleanly after pinning to
      `mariadb:11.4.4`. Previous manual tests had used IST (node had data,
      just needed diffs from gcache) and never exercised SST. Every fresh
      `compose up -v` goes through SST, so this would have hit every new
      deployment.
- [x] **`pi-cron` crash loop.** Typo in `cron-runner.py`: called
      `pi-manage-cron` but the real entry point (from `pyproject.toml`)
      is `privacyidea-cron`. Fixed in `cron-runner.py`, `ha-compose.yaml`
      comments, and `README.md`.
- [x] **Bind-mount path resolution.** `ha-compose.test.yaml` used a
      relative path (`./testdata/users`) which compose resolves against
      the *first* `-f` file's dir, not the override file's dir. Fixed via
      `${HA_TEST_USERS_FILE}` env var set to an absolute path by the
      orchestrator.
- [x] **Admin auth sent a realm.** Both scripts sent `realm: defrealm`
      with the admin credentials, but the bootstrap admin is a superadmin
      without a realm. Removed the `realm` field from admin auth calls.
- [x] **mariadb image pinned** to `11.4.4` to prevent upstream tag
      regressions from breaking deployments silently.
- [x] **`tests/ha-test/Makefile`** — wraps the compose invocations so you
      don't need to export `HA_TEST_USERS_FILE` by hand. Targets:
      `test`, `stress`, `fresh`, `down`, `status`, `logs`, `clean`.
- [x] **Phase-split stats** in the orchestrator: per-phase request/failure
      counts and per-bucket avg response times (min / median / max /
      request-weighted). Deltas of cumulative Totals — the `50%`/`95%`
      columns in locust's history CSV turned out to be cumulative from
      start, not rolling-window, so percentiles are not computed per-phase.
- [x] **Load profile recalibrated to ~40% capacity.** Default lowered to
      10 users and `wait_time = between(3, 6)` in locustfile. Steady-state
      baseline ~150 ms, failover spike to ~600 ms for one bucket, zero
      failures — the clean signal we actually want to report.
      `make stress` retains the 50-user saturation profile for worst-case
      testing.
- [x] **Warmup bumped to 25 s** so the pre-failover phase reflects steady
      state rather than the first few ramp-up buckets.

### Test hardware note

All numbers above are from an i7-1355u (2P + 8E) notebook with locust
running on the same host as the stack. Real sizing numbers would need
server-grade hardware and an off-host load generator; these results
are directional, not absolute.

### 2. Documentation split (done 2026-04-24)

- [x] `README.md` — quick-start only (install, first run, health check).
- [x] `OPERATIONS.md` — Day 2: architecture, monitoring (HAProxy stats,
      ProxySQL hostgroups, Galera state), routine tasks, pi-cron config,
      backup/restore, resource limits + sizing notes, failover test
      pointer, production checklist.
- [x] `TROUBLESHOOTING.md` — incident playbooks: unhealthy containers,
      HAProxy connection refused, Galera won't Synced, SST SIGSEGV,
      all-nodes-crashed recovery (partial — needs a helper script),
      pi-cron crash loop, admin realm error, enckey-mismatch restore.
- [x] `PRODUCT.md` marked as internal with a banner at the top.

Missing content to add later (not blocking the initial PR):
- [x] Complete the all-nodes-crashed Galera recovery playbook with a
      helper script that runs `--wsrep-recover` on both nodes and picks
      the highest seqno automatically. (2026-04-27)
      `scripts/ha-recover-cluster.sh` + `tests/ha-test/run_recovery_test.py`
      + `make recovery-test`. TROUBLESHOOTING.md "All Galera nodes
      crashed" section now points at the script.
- [ ] Rolling upgrade procedure for the PI tier (image bump → one worker
      at a time via `--scale` cycling).
- [ ] Rolling upgrade procedure for Galera (stop one, upgrade, wait for
      Synced, repeat).
- [ ] Certificate renewal playbook (needed once TLS is added in tier G).
- [ ] Sizing table: host RAM/CPU vs expected auth rate, with LDAP
      multiplier.

### 3. Tier G (after docs)

Single focused workstream. Deliverable: `db-2` runs on a second host.

**Piece 1 — single-laptop development (done 2026-04-24):**
- [x] `scripts/gen-galera-certs.sh` — CA + per-node certs under
      `secrets/tls/`. Idempotent, `--force` to regenerate.
- [x] Galera TLS materials wired as Docker secrets in `ha-compose.yaml`
      using `target:` rename so db-1 and db-2 each mount their own cert
      at a common `/run/secrets/galera_node_*` path.
- [x] `galera-entrypoint.sh` enables TLS on cluster replication
      (`socket.ssl=yes` in `wsrep_provider_options`), enables client/server
      TLS (`--ssl-ca/--ssl-cert/--ssl-key`), and writes `wsrep_sst_auth`
      to `/etc/mysql/conf.d/99-sst-auth.cnf` at start instead of passing
      it on the CLI. Root password no longer visible in `ps`.
- [x] Verified: `gmcast.listen_addr = ssl://0.0.0.0:4567`, `socket.ssl =
      YES`, `wsrep_sst_auth` absent from `ps`. Failover test passes with
      TLS active, including the fresh-volume SST run for db-2.

**Known limitation (acceptable for LAN, not for WAN):**
- [ ] **SST stream on port 4444 is NOT encrypted.** The mariabackup SST
      log shows `SSL configuration: MODE='DISABLED', encrypt='0'`. Galera
      ongoing replication (4567/4568) is encrypted; the occasional full-
      resync stream is plaintext. This is fine for LAN (where SST between
      two hosts in the same rack doesn't need wire-level crypto) but
      insufficient for WAN. Enabling requires `[sst] encrypt=3` + `tca`,
      `tcert`, `tkey` config, plus socat/stunnel changes. Defer until we
      have a WAN use case.

**Piece 2 — needs second host (defer until access available):**
- [ ] Pick cross-host networking mechanism (Swarm overlay is the smallest
      jump).
- [ ] Compose restructure: split base + per-host overlays, or move to a
      single Swarm stack file.
- [ ] Document Galera port matrix and firewall requirements
      (3306, 4444, 4567, 4568).
- [ ] Update ProxySQL config to point at cross-host addresses.
- [ ] Validation: cross-host failover test passes.
- [ ] Operations doc: how to add / replace a DB host.

### 4. Tier H (later, separate project)

Gated on G being solid. Scope TBD — key decisions:

- [ ] Orchestrator: Swarm (assumed) vs manual per-host compose.
- [ ] HAProxy redundancy: two instances + external L4 LB / DNS-RR / keepalived.
- [ ] ProxySQL redundancy: native cluster mode vs local-per-host.
- [ ] Secret distribution: migrate from file-backed to Swarm-native secrets.
- [ ] `pi-cron` placement (single replica, must survive host failure).
- [ ] `pi-init` idempotency under reschedule (audit `pi-manage admin add`).

### 4. Upgrade / update process (deferred, large-scale concern)

How updates are performed in a large deployment (hundreds of PI workers,
3+ Galera nodes, potentially spread across hosts) is a distinct
workstream from the initial install. Customers will ask for specific
guarantees. Work needed:

**Define the categories of "update" and what each looks like:**
- [ ] **Security patch of the base image** (mariadb, haproxy, proxysql,
      Chainguard wolfi base). Rebuild → rolling restart. No code change,
      no schema change. Should be zero-downtime.
- [ ] **Minor PI version bump** (e.g. 3.12 → 3.13), backwards-compatible
      schema migrations. Expand-contract pattern: new code reads old
      and new columns; old columns removed in the *next* release. Roll
      pi-init → app tier while old code keeps working against the
      mid-migration DB.
- [ ] **Major PI version bump** with breaking schema changes. Requires a
      feature-flag or maintenance-window strategy. Customer decides
      whether brief downtime is acceptable or whether a blue-green cut
      is required.
- [ ] **Galera (mariadb) major version bump.** Rolling restart possible
      only within the supported version-skew window. Across majors
      (10.x → 11.x) may need a brief full-cluster window — has to be
      documented concretely, not assumed.
- [ ] **Configuration change** (env var, compose file edit). Some can
      be applied via `compose up -d` which recreates only affected
      services; others (e.g. `enckey`, `pi_pepper`) are destructive and
      need a documented migration path.

**Properties we should be prepared to commit to per category:**
- [ ] Whether writes can continue during the upgrade
- [ ] Whether reads can continue
- [ ] Maximum version skew between app and DB, and between two DB nodes,
      during the rolling window
- [ ] Rollback procedure: is every upgrade reversible? If yes how, if
      not, what's the pre-upgrade backup requirement?

**Scale-specific concerns (1000 app nodes, 3+ DB nodes):**
- [ ] Orchestration: rolling restart of 1000 workers is a Swarm/K8s
      problem, not a `docker compose` problem. Belongs on tier H / J
      discussion — what orchestrator do we commit to, what do its
      rolling-update primitives give us for free?
- [ ] Upgrade order: DB first or app first, depending on schema
      changes. Document both patterns.
- [ ] Partial-failure handling: if 7 of 1000 workers fail to start on
      the new version, what does the orchestrator do, what does the
      operator see?
- [ ] Canary: 1% of traffic on the new version first, for how long,
      monitoring what?
- [ ] 3+ Galera nodes changes the SST donor-selection and quorum math
      vs the 2-node baseline. Our failover test doesn't cover this —
      a 3-node variant of the test would be a separate deliverable.

**Customer-facing commitment to develop:**
- [ ] A one-page "upgrade properties" table the consultant can show to
      the customer: "here's what each category of upgrade does, here's
      what you lose, here's what you don't."

Not in scope for the current branch. Captured here so it doesn't fall
off the radar.

---

### 4a. Consulting install experience (deferred)

The current README walks through 7 Python one-liners to generate secrets
and a manual `compose up`. Works for a developer; does not look
professional when a consultant delivers it to a paying customer. Upgrade
path, roughly in order of payoff:

- [ ] **Bootstrap CLI** (`ha-init.sh` or `.py`) that replaces all the
      Python snippets. Prompts for admin username + backup passphrase/age
      key, generates secrets (or imports existing ones for migration),
      chmod 600s them, runs `compose up -d --wait`, polls health, prints
      a post-install summary.
- [ ] **Handoff document** auto-generated at install end: URL, admin
      username, temporary password (one-time display or delivered via the
      customer's password manager), backup location, 24-hour checklist.
      One page. This is what the consultant hands over, not the README.
- [ ] **Ansible role** for customers who already run Ansible. Idempotent,
      remote-runnable. NetKnights likely has one for the deb package to
      model on.
- [ ] Move the Python one-liners out of the customer-facing README into
      an "advanced / manual setup" appendix. The headline install path
      should be one command.
- [ ] **Install guide PDF** (different doc from the operator README) that
      the consultant walks through live: prerequisites, handoff steps,
      verification checklist.

None of this is blocking the initial PR. It turns "works" into "looks
professional" — a separate, customer-facing workstream.

### 4b. Multi-region / geo-distributed (mostly out of scope)

Customers will ask. The honest answer is that PI writes on every auth
(audit + challenge + counter), so stretched Galera over WAN pays the
inter-continent RTT on every authentication — 80–220 ms added to every
request, globally. Not a deployment-layer problem; it's an application
architecture problem.

- [ ] Add a **"multi-region" section to `PRODUCT.md`** (internal
      consulting guidance):
      - Single-region + async DR replica: survives region loss, not HA
        across regions. Could become a future tier J.
      - Per-region PI deployments federated via customer SSO: the
        correct answer for "global org". Token/policy sync happens via
        the IdP layer, not the DB.
      - Stretched Galera over WAN: possible, almost always wrong. Be
        prepared to refuse this politely.
- [ ] Add a one-paragraph FAQ entry to the (future) customer install
      guide answering "can this span multiple continents?" with a
      pointer to the right alternatives.
- [ ] **Tier J (async geo-DR) is a legitimate future offering** — a
      second compose variant with `db-replica` configured for async
      replication and a documented manual-failover procedure. Simpler
      than active/active. Out of scope for now; recorded as a possible
      future product tier.

Not in scope: building active/active multi-region into the stack. That
would require changes to privacyIDEA itself (token-state partitioning,
eventual-consistency semantics for counters), not to the deployment
layer.

### 4c. Security / correctness (in progress)

Items from TODO.md that can be worked on single-laptop.

- [x] **Dedicated ProxySQL monitor user** (2026-04-24). `proxysql_monitor`
      with USAGE + REPLICATION CLIENT, created via mariadb image's
      `/docker-entrypoint-initdb.d/` hook during db-1 bootstrap,
      replicates to db-2 via SST. Replaces root in
      `proxysql-entrypoint.sh`.
- [x] **Dockerfile cleanup** (2026-04-24). Removed stray
      `VOLUME /etc/privacyidea`, enabled the HEALTHCHECK with a working
      urllib-based probe against `/healthz/readyz:8080`. `pi-init` and
      `pi-cron` override with `healthcheck: disable: true` in
      ha-compose.yaml.
- [x] **`make rebuild` target + `--rebuild` flag** on the orchestrator.
      Forces `compose build --no-cache` before up. Needed after any
      Dockerfile / cron-runner.py / entrypoint.sh change — compose
      does not auto-rebuild on source change.
- [x] **HAProxy TLS termination** (2026-04-24). `scripts/gen-haproxy-cert.sh`
      generates a self-signed cert at `secrets/haproxy/cert.pem` for
      first-run install (no customer cert needed to see the stack work).
      HAProxy serves HTTPS on :8443 alongside HTTP on :8000. To install
      a production cert: overwrite the file with concatenated fullchain
      + key (cert first), `docker compose restart pi-proxy`. No config
      change. Failover test continues to work against HTTP.
- [x] **Encryption key canary** (2026-04-24). `deploy/docker/enckey-canary.py`
      with `install` / `verify` subcommands. Uses PI's `encryptPassword` /
      `decryptPassword` so the canary exercises the same code path PI
      itself uses. Stored as `__enckey_canary_v1` in `pi_config`.
      `pi-init` runs `install`; every pi worker runs `verify` before
      gunicorn starts.
      - Exit 2 on HSM init failure or decrypt mismatch → container
        exits, entrypoint refuses to start.
      - Exit 1 on canary missing → warn and continue (backwards compat
        for deployments that predate the canary).
      - Exit 0 on success.
      Verified: normal run passes; swapping enckey to garbage produces
      loud "FATAL: HSM initialization failed... Refusing to start" and
      restart-loops the container.

### 5. Clean-up before PR

- [ ] Squash the "not working currently" commit.
- [ ] Work through TODO.md — decide which items land in the initial PR vs
      follow-up PRs.
- [ ] Ensure `Makefile` targets still reflect current commands.

---

## Notes

- K8s is ruled out as a product offering. Not reopening that discussion.
- Test orchestrator is **local only** for now. CI wiring is explicitly
  deferred until after G, to avoid rewriting it when topology changes.
- PRODUCT.md stays internal — customer-facing positioning goes into the
  README/OPERATIONS split.
