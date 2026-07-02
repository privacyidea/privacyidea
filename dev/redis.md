# Redis in privacyIDEA — developer quickstart

This document describes how privacyIDEA uses Redis, why, and the details a
developer needs to work on or extend it.

> **TL;DR** Redis is an *optional* store for **authentication challenges only**.
> When enabled, challenges are written to Redis **instead of** the SQL database
> (not a write-through cache), because challenges are ephemeral — they live
> 2–5 minutes and then expire. Everything degrades gracefully to the database
> when Redis is unset, unreachable, or the feature flag is off.

---

## 1. Why Redis at all

When privacyIDEA is deployed in HA setups (multiple app nodes behind a
load balancer, a MariaDB Galera / ProxySQL cluster behind them). Challenges are
the one piece of *hot, short-lived, write-heavy* state in the auth flow:

* A challenge-response auth (push, SMS, email, WebAuthn/passkey, PIN reset, …)
  creates a challenge on node A, and the user's answer may land on node B.
* Every `/validate/check` that triggers or answers a challenge is a write.
* On a Galera cluster, `INSERT`/`UPDATE`/`DELETE` on the `challenge` table pays
  full cluster-replication cost for data that is worthless 5 minutes later.

Putting challenges in a shared Redis lets every node see the same challenge
state immediately, without hammering the SQL cluster with throwaway writes.

### What this is *not*

* **Not a write-through / read-through cache.** When the feature is on,
  challenges are written to Redis **only** — there is no SQL row to fall back
  to. The TTL *is* the lifecycle; nothing copies the challenge to SQL.
* **Not used for anything but challenges (yet).**

---

## 2. Configuration

Two settings, both required to actually store challenges in Redis:

| Key | Meaning |
|---|---|
| `PI_REDIS_URL` | Redis connection URL, e.g. `redis://127.0.0.1:6379/0`. Unset → Redis is completely off, every cache function is a no-op. |
| `PI_REDIS_CACHE_CHALLENGES` | Per-feature opt-in. `PI_REDIS_URL` alone does **nothing** for challenges; this flag turns the challenge workload on. |
| `PI_REDIS_RETRY_COOLDOWN` | (optional) Seconds to wait before retrying after a Redis failure. Default `30`. |

The `PI_REDIS_URL` alone-does-nothing design is deliberate: each cacheable
workload has its own flag so operators can roll one out / roll one back without
touching the others.

`pi.cfg` example:

```python
PI_REDIS_URL = "redis://127.0.0.1:6379/0"
PI_REDIS_CACHE_CHALLENGES = True
```

Environment override (Flask `from_prefixed_env("PRIVACYIDEA")` — note the
`PRIVACYIDEA_` prefix, see `.env.example`):

```bash
PRIVACYIDEA_PI_REDIS_URL=redis://127.0.0.1:6379/0
PRIVACYIDEA_PI_REDIS_CACHE_CHALLENGES=true
```

### Redis 7 is required

The write path uses `EXPIRE ... NX` and `EXPIRE ... GT`, both introduced in
Redis 7.0. `_build_client()` checks `INFO server` at connect time and **refuses**
a server older than 7 (raising, which trips the cooldown and falls back to DB).
This surfaces the misconfiguration at startup rather than as a silent failure on
the first challenge write.

### Connection & data security

The URL is the **entire** security surface. `get_redis()` passes `PI_REDIS_URL`
straight to `redis_lib.Redis.from_url(url, ...)`; there are no dedicated
`PI_REDIS_PASSWORD` / `PI_REDIS_TLS_*` keys. privacyIDEA does **not** enforce
TLS or auth — that's the operator's job.

* **TLS** — use the `rediss://` scheme. TLS params travel in the URL query
  string (redis-py parses `ssl_cert_reqs`, `ssl_ca_certs`, `ssl_certfile`,
  `ssl_keyfile`, `ssl_check_hostname`):
  `rediss://host:6379/0?ssl_cert_reqs=required&ssl_ca_certs=/etc/ssl/redis-ca.pem`.
  The code sets no ssl options itself, so for verified TLS set `ssl_cert_reqs`
  explicitly rather than trusting the redis-py default.
* **Auth** — credentials are inline in the URL (`redis://user:pass@host`,
  password or ACL user+password). No separate password key.
* **Secret management** — `PI_REDIS_URL_FILE` (production config path, via
  `_get_secrets_from_environment`) reads the whole URL from a file
  (`/run/secrets/redis_url`), keeping the password out of the environment.
* **Log redaction** — `_redact_url()` rewrites `user:password@host` to
  `***@host` before every log line (connect, failure, cooldown), so creds never
  reach the log.
* **Data at rest** — the cached payload is **plaintext, at parity with the
  unencrypted SQL `challenge` table** (the DB columns `challenge`/`data`/`session`
  are not encrypted/hashed either). Redis introduces no new at-rest sensitivity,
  but it must be hardened to the **same level as the database**: private network,
  auth, `rediss://`, at-rest encryption if the threat model needs it. Don't
  expose it publicly. Mitigating factor: entries carry the challenge TTL
  (minutes), so the exposure window is small.

Not enforced (operator-hardening gaps worth knowing): nothing requires TLS or
auth — a plain `redis://` to a public, unauthenticated Redis works silently; and
mTLS client certs can only be supplied via the URL query string, not dedicated
config keys.

---

## 3. Where the code lives

```
privacyidea/lib/cache/
    __init__.py     # re-exports the public Redis API + the in-process policy/config caches
    redis.py        # the entire Redis layer (client lifecycle, DTO, read/write/evict)
privacyidea/lib/challenge.py   # get_challenges / get_challenges_paginate / delete_challenges / cancel_challenge
privacyidea/lib/token.py       # create_challenge() — the single write entry point
privacyidea/config.py          # ConfigKey.REDIS_* + TestingConfig wiring
```

Callers never import `redis.py` directly for business logic — they go through
`get_challenges()` / `create_challenge()` / `delete_challenges()` /
`cancel_challenge()`, which decide Redis-vs-DB internally. The low-level
`cache_challenge` / `evict_*` / `get_challenges_from_cache` are the seam those
functions use.

---

## 4. Data structures in Redis

Two key families, both namespaced under `pi:challenge:`.

### 4.1 Transaction hash (authoritative store)

```
pi:challenge:txn:<transaction_id>   →  HASH  { <serial> : <JSON payload>, ... }
```

* **Why a hash, not a string.** One authentication request can trigger **several
  tokens at once** (e.g. push + SMS, or multiple passkeys). They all share one
  `transaction_id`, mirroring the SQL model where multiple `Challenge` rows
  share a `transaction_id`. Each token gets its own field, keyed by serial, so a
  second token's challenge does not overwrite the first.
* A token never creates two challenges in one transaction, so `serial` uniquely
  identifies a challenge within the hash.
* **Usernameless passkey** challenges have `serial == ""` — they're stored under
  the empty-string field and looked up by `transaction_id` only.
* The **TTL lives on the whole hash**, not per field. A short-lived sibling
  added later can't shrink it (see NX/GT discipline below). A field that outlives
  its own validity is filtered out on read by `is_valid()`, not by per-field TTL.

The JSON payload (see `ChallengeDTO.to_payload` / `_deserialize` — keep them in
sync) holds: `transaction_id, serial, challenge, data, session, timestamp,
expiration, received_count, otp_valid`.

### 4.2 Serial index (reverse lookup)

```
pi:challenge:serial:<serial>   →  SET  { <transaction_id>, ... }
```

* Lets "get all challenges for this token serial" resolve without scanning keys.
* Only written when `serial` is truthy — usernameless passkey challenges
  (`serial=""`) are deliberately **not** indexed, because they would funnel every
  such request into one shared, ever-growing set whose TTL never settles. They're
  only ever fetched by `transaction_id`, so the index buys nothing for them.

### 4.3 TTL discipline (the NX + GT pattern)

On every write to a hash or set TTL:

```
EXPIRE <key> <ttl> NX     # seed the TTL only if the key has none yet
EXPIRE <key> <ttl> GT     # extend only if the new TTL is greater; never shrink
```

* `ttl = (expiration - now) + 30s buffer` (`_TTL_BUFFER_SECONDS`). The buffer
  keeps the Redis key alive slightly past the logical expiry so we don't evict
  just before a reader's `is_valid()` check, and absorbs minor clock skew
  between nodes.
* **NX** seeds a TTL on a freshly created key (a bare `HSET`/`SADD` that
  re-creates an evicted key leaves it with *no* TTL; `GT` alone cannot set a TTL
  on a key that has none).
* **GT** guarantees the shared key's TTL covers its **longest-lived** member: a
  shorter sibling added afterwards extends-or-leaves but never shortens it.

---

## 5. The commands we issue

| Operation | Redis commands | In code |
|---|---|---|
| Connect / health check | `PING`, `INFO server` (Redis-7 gate) | `_build_client` |
| Write a challenge | `HSET txn serial payload` · `EXPIRE txn ttl NX` · `EXPIRE txn ttl GT` · (if serial) `SADD serial:<s> txn` · `EXPIRE serial:<s> ttl NX` · `EXPIRE serial:<s> ttl GT` — all in one `MULTI/EXEC` pipeline | `cache_challenge` |
| Update a challenge (e.g. otp_status) | same `HSET` + NX/GT re-assert on hash and serial set | `_update_challenge_in_cache` (via `ChallengeDTO.save()`) |
| Read by transaction_id | `HGETALL txn` | `get_challenges_from_cache` |
| Read by serial | `SMEMBERS serial:<s>` then one `HGET txn serial` per member (pipelined) | `get_challenges_from_cache` |
| Evict one challenge | `HDEL txn serial` · (if serial) `SREM serial:<s> txn` | `evict_challenge` |
| Evict a whole transaction | `DEL txn` · `SREM serial:<s> txn` per serial | `evict_transaction` |
| Evict all challenges of a serial | `SMEMBERS serial:<s>` · `HDEL txn serial` per member · `DEL serial:<s>` | `evict_challenges_for_serial` |

`decode_responses=True`, `socket_connect_timeout=2`, `socket_timeout=2` on every
client (`_CLIENT_KWARGS`). Writes/evicts are pipelined to a single round-trip.

---

## 6. Lifecycle of a challenge (with Redis on)

```
create_challenge(serial, ...)            # lib/token.py — the ONLY write entry point
  └─ builds an in-memory Challenge object
  └─ redis_feature_enabled("challenges")?
       ├─ yes → cache_challenge(...)      # HSET + EXPIRE NX/GT pipeline; NO SQL INSERT
       │         └─ if it failed (_disable_redis tripped) → fall back to db_challenge.save()
       └─ no  → db_challenge.save()       # plain SQL
  returns a Challenge instance (on the cache path it is NOT session-bound:
  .id is None, do not .save() or mutate it; use transaction_id for identity)

answer arrives → get_challenges(transaction_id=…) / (serial=…)
  └─ get_challenges_from_cache(...) first
       ├─ list[ChallengeDTO]  → cache hit (authoritative, even if empty after filtering)
       ├─ CacheState.MISS     → cache reachable, key absent → still falls through to DB*
       └─ CacheState.UNAVAILABLE → cache off/errored/list-all → fall through to DB
  *MISS still falls through because the DB may legitimately hold challenges
   created before caching was enabled — the cache is authoritative only for what
   it has, not for what it claims is absent.

consume / cancel → cancel_challenge(txn) → delete_challenges(transaction_id=txn)
  └─ evict from Redis (whole txn hash) AND delete SQL rows
expire → Redis TTL drops the key; no explicit delete needed
```

### `ChallengeDTO` — the duck-typed challenge

A challenge read from Redis comes back as a `ChallengeDTO`, not a SQLAlchemy
`Challenge`. It exposes the **same surface** token classes already use
(`is_valid`, `get_data`, `get_otp_status`, `set_otp_status`, `set_data`,
`get_session`, `save`, `delete`, `.transaction_id`, `.serial`, `.timestamp`,
`.expiration`, …) so callers don't care which backend they hold.

Key difference: **`ChallengeDTO` has no `.id`** (there's no SQL primary key).
This is why the HTTP API stopped returning the `id` field for challenges —
`transaction_id` is the only identifier stable across both backends. Mutators
(`set_otp_status`, `set_data`, `set_session`) call `save()` themselves so that
callers written against the autoflush-on-request-end DB `Challenge` get
equivalent persistence without knowing the backend.

---

## 7. Failure handling & edge cases considered on this branch

This is the part worth reading before you touch the layer.

### 7.1 Graceful degradation, self-healing (no one-way latch)
`get_redis()` returns `None` whenever Redis is unset/unreachable, and every
cache function no-ops on `None`. A failure (`_disable_redis`) drops the cached
client and sets `_redis_retry_after = now + cooldown` (default 30s). The next op
after the cooldown retries; on success the worker is back. **There is no
permanent disable** — a transient blip (restart, network glitch) is invisible
after one cooldown window. During an outage a worker pays the 2s connect timeout
at most once per cooldown, not per request.

### 7.2 Thread safety
The connect path is serialised by a module-level `_connect_lock` so two threads
under gthread/uWSGI threads can't both run `_build_client` (each paying the 2s
timeout and leaking the loser's socket). The fast path returns the cached client
*before* taking the lock; the lock is essentially uncontended after first
connect.

### 7.3 Fork safety
redis-py connection-pool sockets are **not** fork-safe. If the parent connects
before forking (uWSGI `fork-after-init`, Gunicorn `preload_app=True`), children
inherit the same fds and concurrent RESP traffic corrupts the protocol. The
cached client is **stamped with the PID**; whenever `os.getpid()` changes the
client is dropped and the child re-connects once.

### 7.4 Multi-token transactions
One transaction → many tokens → many challenges, all under one txn hash keyed by
serial (see §4.1). This was an explicit fix: a string-per-transaction layout
would have let a second token's challenge clobber the first's.

### 7.5 TTL never shrinks (NX + GT)
A short-lived challenge added to a transaction/serial that already holds a
longer-lived one must not expire the shared key early. GT guarantees extend-only;
NX seeds a TTL on re-created keys. See §4.3.

### 7.6 Never store an already-expired challenge / no resurrection
`cache_challenge` and `_update_challenge_in_cache` both refuse to write when
`expiration <= now`. The 30s buffer is added **after** that gate, so a `save()`
within 30s after expiry can't rewrite the entry with a positive TTL and
resurrect it.

### 7.7 Three-state reads (MISS vs UNAVAILABLE)
`get_challenges_from_cache` returns `list | CacheState.MISS |
CacheState.UNAVAILABLE` instead of collapsing to `None`. Cleanup paths need to
tell "cache says it's gone" (authoritative) from "cache is down / unknown" — the
latter triggers a **defensive eviction** to close the race where another worker
wrote a sibling field between our read and our delete.

### 7.8 Eviction races on token/container deletion
`evict_challenges_for_serial` snapshots `SMEMBERS` then pipelines `HDEL`s — not
atomic. If another worker writes a challenge for that serial between snapshot and
`EXEC`, the new field survives until its TTL; the later token lookup fails with
`ResourceNotFoundError` and the user retries. This race is **intentionally
accepted** (microsecond window, token deletion is rare, orphan lives ≤ one
validity TTL); closing it fully needs Lua or WATCH/MULTI, not worth the
complexity. Documented in the function.

### 7.9 Eviction skipped during a worker's cooldown
If the worker that handles a cancel/delete is in its Redis cooldown,
`delete_challenges` only removes SQL rows; the Redis entry survives on the shared
instance until TTL and other healthy workers can still serve it. The
`DeleteChallengesResult.cache_available` flag surfaces this so the cancel API can
warn the operator ("may still be served from cache by other nodes until TTL").
`delete_challenges` re-samples connectivity *after* its eviction work so a
mid-pipeline `_disable_redis` is reflected in the flag.

### 7.10 Credentials never logged
`_redact_url` strips `user:password` from `PI_REDIS_URL` before any log line
(connect success, transient failure).

### 7.11 Aggregate "list all challenges" is degraded by design
A key-value store can't enumerate "all challenges" cheaply, and with caching on
there are no SQL rows to list. So the admin **List Challenges** (global) view is
intentionally degraded: `get_challenges_from_cache` returns `UNAVAILABLE` for an
unfiltered/wildcard query, the caller falls back to the (empty) DB, and the WebUI
shows a banner explaining it. **Per-token and per-user** challenge listing still
works, via the serial / transaction_id lookups and `get_challenges_for_user`.

---

## 8. Adding a new cached workload (future)

The layer is feature-gated to make this clean:

1. Add `PI_REDIS_CACHE_<FEATURE>` handling (the gate `redis_feature_configured`
   already derives the key name from the feature string).
2. Gate caller code with `redis_client_for_feature("<feature>")` (single call:
   checks the flag *and* returns the live client, or `None`).
3. Use your own key namespace (`pi:<feature>:...`) and the NX/GT TTL discipline
   if your data has a TTL.
4. Make every path degrade to the existing backend when the client is `None`.

`redis_feature_enabled("<feature>")` is the convenience boolean for response
payloads / log fields; hot paths should prefer `redis_client_for_feature` to
avoid a duplicate lookup.

---

## 9. Local development & testing

### Run a Redis for dev
```bash
docker compose -f compose-dev.yml up -d redis     # Redis 7 on :6379
```

### Point privacyIDEA at it
```bash
export PRIVACYIDEA_PI_REDIS_URL=redis://127.0.0.1:6379/0
export PRIVACYIDEA_PI_REDIS_CACHE_CHALLENGES=true
```

### Run the test suite against real Redis
`tests/conftest.py` auto-detects a Redis on `127.0.0.1:6379` and sets
`TEST_REDIS_URL`. Each xdist worker is pinned to its **own Redis logical DB**
(`gw0`→DB 0, `gw1`→DB 1, …) and `FLUSHDB`s it per test, so parallel runs don't
clobber each other. Redis has 16 logical DBs (0–15), so **cap workers at 16**.

```bash
docker compose -f compose-dev.yml up -d redis
export PI_REDIS_URL=redis://127.0.0.1:6379/0 \
       PI_REDIS_CACHE_CHALLENGES=true \
       TEST_REDIS_URL=redis://127.0.0.1:6379/0
.venv313/bin/python -m pytest tests/test_lib_cache_redis.py tests/test_lib_challenges.py -q
```

Drop the three env vars (or `env -u …`) to run the same tests DB-only.

### CI
`.github/workflows/unit-tests-redis.yml` runs the **whole** suite with a live
Redis as the real challenge backend (MariaDB + Redis 7), so any DB-vs-Redis
behavioural divergence surfaces. It excludes `migration` and `backup`-marked
tests (the latter dumps the DB via `mysqldump` and exercises nothing on the
Redis path). It uploads coverage under the `backend` flag — it's the only job
that exercises `lib/cache/redis.py`.

### Inspecting Redis by hand
```bash
redis-cli
> KEYS pi:challenge:*
> HGETALL pi:challenge:txn:<transaction_id>
> SMEMBERS pi:challenge:serial:<serial>
> TTL    pi:challenge:txn:<transaction_id>
```

---

## 10. Quick reference — public API

| Function | Purpose |
|---|---|
| `create_challenge(serial, …)` (`lib/token.py`) | **The** write entry point. Redis-or-DB internally. |
| `get_challenges(serial=, transaction_id=, challenge=)` (`lib/challenge.py`) | Read; cache-first, DB fallback. Returns `Challenge` and/or `ChallengeDTO`. |
| `get_challenges_paginate(...)` | WebUI list; serves exact serial/transaction filters from cache, wildcard/list-all from DB (degraded under cache). |
| `delete_challenges(serial=, transaction_id=, commit=)` | Remove from both stores; returns `DeleteChallengesResult(removed, cache_available)`. |
| `cancel_challenge(transaction_id)` | Narrow alias for "abort this auth transaction" (auth/API paths). |
| `redis_client_for_feature(feature)` | Flag + connectivity in one; returns client or `None`. |
| `redis_feature_enabled(feature)` / `redis_feature_configured(feature)` | Live-enabled vs configured-but-maybe-unreachable. |

All of the above no-op / fall back to SQL when Redis is unset, off, or down.
