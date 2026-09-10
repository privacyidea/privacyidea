# TODO: Make Webhooks a First-Class Object (#5751)

**Target release:** 3.15 **Status:** Deferred from Conditional Access V1

---

## Overview

Transform webhooks from inline event-handler options into a reusable, authenticated configuration object (own table,
lib, API, UI), following the established SMTP server / RADIUS server / SMS gateway pattern. Reference webhooks by
identifier from both the event handler and Conditional Access stage actions.

---

## Implementation Order

The tasks are ordered to satisfy three constraints:

1. **Schema before code** — models and migrations must exist before lib/API can use them.
2. **Migrate before removing** — the data migration converts legacy rows *before* the handler form drops the inline
   fields (otherwise `set_event()` wipes them on save).
3. **Backend before frontend** — API endpoints must exist before the WebUI can call them.

Within those constraints, the order minimises the time any half-finished piece sits in the tree, and groups related
changes so each phase produces a testable unit.

---

## Phase 1 — Data Model & Database Migration

> Goal: the `webhook` and `webhookheader` tables exist, and existing inline
> webhook definitions are converted.

### 1.1 — `webhook` + `webhookheader` SQLAlchemy models ✅

- [x] **File:** `privacyidea/models/webhook.py` (new file)
- [x] Follow `SMTPServer` pattern (`MethodsMixin`, `db.Model`, `mapped_column`)
- [x] `webhook` table columns:
    - `id` (int PK)
    - `identifier` (unicode 255, unique, not null)
    - `description` (unicode 2000)
    - `url` (unicode 2000, not null)
    - `http_method` (unicode 10, default `POST`)
    - `content_type` (unicode 100)
    - `default_payload` (unicodetext, nullable)
    - `auth_type` (unicode 50, default `none`) — values: `none`, `basic`, `header`, `mtls`
    - `username` (unicode 255) — for basic auth
    - `password` (unicode 1024) — encrypted via `encryptPassword`
    - `verify_tls` (bool, default true)
    - `tls_ca_bundle` (unicode 1024) — optional CA bundle path
    - `client_certificate` / `client_key` / `client_key_password` (unicode) — mTLS
    - `http_proxy` / `https_proxy` (unicode 1024)
    - `timeout` (int, default 3)
- [x] `webhookheader` child table columns:
    - `id` (PK)
    - `webhook_id` (FK → `webhook.id`, `ondelete=CASCADE`)
    - `key` (unicode — header name)
    - `value` (unicode — header value)
    - `encrypted` (bool) — mirrors `SMSGatewayOption.Type` pattern
- [x] Add relationship from `Webhook` → `WebhookHeader`
- [x] Add `get()` method on `Webhook` (like `SMTPServer.get()`)
- [x] Registered in `privacyidea/models/__init__.py`

**Tests:** ✅ `tests/test_model_webhook.py` — 12 tests, all passing

- [x] Unit test: create / read / update / delete webhook model
- [x] Unit test: cascade delete removes headers
- [x] Unit test: unique identifier constraint
- [x] Unit test: get () dict representation
- [x] Unit test: encrypted header round-trip
- [x] Unit test: multiple headers per webhook
- [x] Unit test: query by identifier

---

### 1.2 — Alembic schema migration + data migration (single revision) ✅

- [x] **File:** `privacyidea/migrations/versions/e1f2a3b4c5d6_add_webhook_tables.py`
- [x] Create `webhook` table (18 columns matching model)
- [x] Create `webhookheader` table with FK (`ondelete=CASCADE`)
- [x] Sequence creation with fallback for SQLite/MySQL (follows `metric_aggregate` pattern)
- [x] Idempotent: `has_table()` guard skips creation if table already exists
- [x] Downgrade drops migrated data first, then child table (FK dependency), then parent + sequences

---

### 1.3 — Data migration (legacy inline → webhook objects, same revision) ✅

- [x] **In file:** `privacyidea/migrations/versions/e1f2a3b4c5d6_add_webhook_tables.py`
  (merged into single revision — schema + data in one atomic step)
- [x] For each `EventHandler` where `handlermodule = 'WebHook'`:
    - Extract `URL`, `content_type` from `eventhandleroption` rows
    - Create a `webhook` row named `from_<handler.name>_<handler.id>`
      (fallback name when `handler.name` is NULL: `webhook_from_handler_<id>`)
    - Add `webhook` option to the handler pointing at the new identifier
    - Leave `data` and `replace` as handler options (payload is call-site-specific)
    - Leave inline `URL`/`content_type` option rows in place (safe for downgrade + tolerant reader)
- [x] **No deduplication** — two handlers posting to the same URL produce two webhook objects (safe,
  behaviour-preserving)
- [x] Migration moves **no secrets** (current handler has no auth) — plaintext only
- [x] Must be **idempotent** (re-running is a no-op if rows already exist)
- [x] Legacy content_type values (`json`, `urlencoded`) normalized to MIME types
- [x] `timeout=10` preserves existing handler behaviour (vs. new default of 3)
- [x] Core logic extracted to `_run_data_migration(conn)` for testability

**Tests:** ✅ `tests/test_migration_e1f2a3b4c5d6.py` — 11 tests, all passing

- [x] Test migration on a DB with 0 webhook handlers (no-op)
- [x] Test migration with 1 handler (produces 1 webhook object)
- [x] Test migration with 2 handlers pointing to same URL (produces 2 objects)
- [x] Test migration with handler that has NULL name
- [x] Test idempotency (run twice, same result)
- [x] Test legacy content_type normalization (json, urlencoded)
- [x] Test missing URL is skipped
- [x] Test non-WebHook handlers are ignored
- [x] Test special characters in handler name are sanitized
- [x] Test missing content_type defaults to application/json

### 1.4 — Pre-migration snapshot (safety net) ✅

Context: `migrations/env.py` configures the connection with
`isolation_level="AUTOCOMMIT"`, so **migrations do not run in a transaction**. A data migration that fails partway
cannot be rolled back by the database.

- [x] Before touching any row, `upgrade()` writes a JSON snapshot of exactly the rows the data migration may modify —
  the `eventhandleroption` rows of every
  `handlermodule='WebHook'` handler
- [x] Location: `$PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR` → privacyIDEA's backup dir (`/var/lib/privacyidea/backup`, the
  `pi-manage backup create` default) if it exists and is writable → system temp dir. File
  `privacyidea-e1f2a3b4c5d6-<timestamp>.json`, mode `0600`
- [x] Opt out with `PRIVACYIDEA_MIGRATION_NO_SNAPSHOT=1`
- [x] Snapshot failures are **non-fatal** — a warning is logged and the upgrade continues
- [x] No snapshot is written when there is nothing to migrate
- [x] `restore_snapshot(conn, path)` restores the exact pre-migration state (deletes migration-created webhook rows,
  resets the handler options) — usable instead of `downgrade()` after a partial failure
- [x] `restore_snapshot()` refuses snapshots from a different revision
- [x] On failure, `upgrade()` prints the snapshot path and the recovery options
- [x] Explicitly **not** a replacement for `pi-manage backup create` — it only covers the tables this migration writes
  to

**Tests:** ✅ `tests/test_migration_e1f2a3b4c5d6.py::WebhookMigrationSnapshotTestCase` — 8 tests

- [x] No snapshot when there is nothing to migrate
- [x] Snapshot captures all option rows of all WebHook handlers
- [x] Snapshot file is owner-readable only (`0600`)
- [x] Snapshot can be disabled via env var
- [x] Unwritable directory does not break the migration
- [x] Restore returns the DB to the exact pre-migration state
- [x] Migration is replayable after a restore (same identifiers)
- [x] Restore rejects a snapshot from a foreign revision
- [x] Env var wins over the backup dir; backup dir wins over temp dir; temp dir used when the backup dir is absent

#### Evaluated and rejected: calling `pi-manage backup create` from the migration

`privacyidea/cli/pimanage/backup.py` was reviewed as an alternative. It is the right tool for admins to run **before**
an upgrade, but must not be invoked from inside a migration:

| Finding                                                                     | Consequence                                                                                                                   |
|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `backup_create` is a `click.Command`, not a library function                | Not callable directly; needs `.callback`/`CliRunner`                                                                          |
| Calls `sys.exit(2)` on any failure                                          | A backup problem would abort `pi-manage db upgrade` mid-chain                                                                 |
| Supports only SQLite + MySQL/MariaDB (`MYSQL_DIALECTS`), else `sys.exit(2)` | Upgrade would die outright on other dialects                                                                                  |
| Shells out to `mysqldump`, writes `mysql.cnf` into the config dir           | Requires tooling/permissions a migration cannot assume                                                                        |
| Defaults to `/var/lib/privacyidea/backup/`, may `chown` as root             | Not appropriate from a migration context                                                                                      |
| `backup restore` is whole-DB **and** whole-config, extracting to `/`        | Recovering from a failure in *this* migration would also discard every other migration that already succeeded in the same run |

The two mechanisms are **complementary, not alternatives**: `pi-manage backup
create` is the coarse, admin-driven, whole-system net; the JSON snapshot is the fine-grained, automatic, per-migration
net. The failure message printed by
`upgrade()` presents both, in order of preference (re-run → `restore_snapshot`
→ full backup restore as last resort).

---

## Phase 2 — Library Layer (CRUD + Fire)

> Goal: `privacyidea/lib/webhook.py` provides all CRUD operations and the
> `fire_webhook()` function. Fully testable without API or UI.

### 2.1 — Webhook CRUD functions ✅

- [x] **File:** `privacyidea/lib/webhook.py` (new)
- [x] Constants: `AuthType` (none/basic/header/mtls), `HttpMethod`
  (GET/POST/PUT/PATCH), `ContentType`, `DEFAULT_TIMEOUT = 3`
- [x] `get_webhooks(identifier=None, censor=False)` → list of webhook dicts, sorted
- [x] `get_webhook(identifier, censor=False)` → single dict, raises `ResourceNotFoundError`
- [x] `get_webhook_object(identifier)` → raw DB object (for `fire_webhook()` in 2.2)
- [x] `get_webhook_identifiers()` → sorted names only, for the UI dropdowns (avoids loading + decrypting every webhook
  just to render a select box)
- [x] `set_webhook(identifier, url, ...)` → create or update, returns id
    - Encrypts `password` and `client_key_password` via `encryptPassword()`
    - Handles `webhookheader` rows (delete missing / update existing / create new, matching the `set_smsgateway()`
      pattern)
    - Encrypts header values listed in `secret_headers`
    - `__CENSORED__` for a secret keeps the stored value (safe UI round-trip); an empty string clears it
    - Toggling a header's `encrypted` flag re-encrypts/decrypts in place
    - Partial update: parameters left at `None` keep their stored value
    - `url` is only required when creating
- [x] `delete_webhook(identifier)` → delete by identifier, cascades to headers
- [x] Validation via `ParameterError`: non-empty identifier, http/https URL, known method / auth type, positive integer
  timeout, basic auth needs a username, mTLS needs a client certificate, header auth needs a header,
  `content_type` must be a real MIME type
- [x] Normalisation: method upper-cased, auth type lower-cased
- [x] **No legacy `content_type` shorthand handling here.** Converting `json` /
  `urlencoded` is the migration's job for stored data and the event handler's tolerant reader's job for unmigrated
  inline options. A first-class webhook always carries a real MIME type, so `set_webhook()` rejects the shorthands
  instead of storing a value that would later produce an invalid
  `Content-Type` header. (The map lives in exactly two places:
  `webhookeventhandler.py` and the migration.)

**Tests:** ✅ `tests/test_lib_webhook.py` — 40 tests, all passing

- [x] Full CRUD cycle (create minimal, create full, read, update, delete)
- [x] Encryption at rest of password, client key password, secret headers
- [x] Censoring hides secrets; empty secrets stay empty (not censored)
- [x] Censored write-back preserves the stored secret; `""` clears it
- [x] `get_webhooks()` returns all sorted; filtered returns one; unknown → `[]`
- [x] `get_webhook_identifiers()` returns sorted names
- [x] Unknown identifier raises `ResourceNotFoundError` (get / get_object / delete)
- [x] Partial update keeps untouched fields
- [x] Headers: store, replace-on-write, keep-when-omitted, censor, encryption toggle on and off
- [x] `delete_webhook()` cascades to header rows
- [x] Validation: empty identifier, bad URL scheme, bad method, bad auth type, bad timeout, auth-type-specific
  requirements
- [x] Normalisation: method case, auth-type case, numeric-string timeout
- [x] Legacy `content_type` shorthands are rejected; arbitrary MIME types allowed
- [x] A rejected create leaves no row behind

---

### 2.2 — `fire_webhook()` transport function ✅

- [x] **File:** `privacyidea/lib/webhook.py`
- [x] Load webhook config by identifier (via `get_webhook()`, which decrypts)
- [x] Build `requests` call:
    - Method from `http_method`, URL from `url`
    - Headers from `webhookheader` rows (decrypted)
    - Auth: `none` → nothing; `basic` → `auth=(username, password)`;
      `header` → the configured headers; `mtls` → `cert=`
    - TLS: `verify=False` when disabled, else the CA bundle if set, else `True`
      — **disabling verification wins over a configured bundle**
    - Proxy: `proxies={...}` only for the entries that are set
    - Timeout from the `timeout` column
    - Body: caller payload > `default_payload` > no body
    - `Content-Type` set from the column, but only when there *is* a body, and never overriding an explicitly configured
      `Content-Type` header
    - dict/list payload serialised per content type (JSON dumped, else form-encoded)
- [x] **Failures are logged and never propagated** — a broad `except Exception`
  covers transport, TLS and configuration errors alike
- [x] Logging hygiene: the URL (may embed a token) and the headers (may carry credentials) are **never** logged; the
  body only at DEBUG
- [x] Returns `{success, status_code, response, error}`; `success` means 2xx
- [x] Response bodies truncated at `MAX_RESPONSE_LENGTH` (1000 chars)
- [x] Metrics `webhook_send_total` / `webhook_send_duration_seconds`, mirroring
  `_record_email_send()`
- [x] `test_webhook(identifier, payload=None)` → thin wrapper for the UI's
  "Test" button, same contract and result dict

> **mTLS with an encrypted client key:** `requests`' `cert=` parameter cannot
> carry a key password, so that case builds an `ssl.SSLContext`, calls
> `load_cert_chain(cert, key, password=...)` and mounts a small
> `_SSLContextAdapter` on a `Session` (closed again in a `finally`). Plain mTLS
> without a key password still uses the simple `cert=` path.

**Tests:** ✅ `tests/test_lib_webhook_fire.py` — 32 tests, all passing

- [x] Successful POST with JSON body; configured method (PUT) is used
- [x] GET without payload sends no body and no Content-Type
- [x] Payload precedence: caller > default_payload > none
- [x] dict payload JSON-encoded / form-encoded per content type
- [x] Static headers sent; encrypted header sent decrypted
- [x] Basic auth produces an Authorization header
- [x] An explicitly configured Content-Type header is not overwritten
- [x] TLS: default verify, disabled verify, CA bundle, disabled-beats-bundle
- [x] Proxies forwarded; absent when unset; timeout forwarded
- [x] mTLS: cert tuple, single combined path, encrypted key via SSLContext, verification-off relaxes the context, bad
  cert path fails safely
- [x] HTTP 500 reported not raised; connection error and timeout caught
- [x] Unknown identifier returns a failure instead of raising
- [x] Oversized response truncated
- [x] URL and header secrets never appear in any log record
- [x] `test_webhook()` returns status + body, uses default payload, fails safely

> **Note:** import the library function under an alias in test modules
> (`from privacyidea.lib.webhook import test_webhook as run_webhook_test`),
> otherwise pytest tries to collect it as a test case.

---

### 2.3 — Export / Import registration ✅

- [x] **File:** `privacyidea/lib/webhook.py`
- [x] `@register_export('webhook')` — exports all (or one) webhook object as
  `identifier -> configuration`, where the configuration is exactly the keyword arguments `set_webhook()` accepts
    - `id` and `identifier` are stripped: they identify the object, they are not configuration
    - `censor=True` replaces the basic-auth password, the client key password and the values of headers marked
      `encrypted` with `__CENSORED__` (delegated to `get_webhooks(censor=...)`, so there is exactly one censoring
      implementation)
    - Without `censor`, secrets are returned **decrypted**, so a re-import does not encrypt them a second time
- [x] `@register_import('webhook')` — imports webhook objects via `set_webhook()`
    - A `__CENSORED__` secret is not written; `set_webhook()` keeps the stored value, so re-importing a censored export
      never wipes an existing credential
    - Unknown keys in a hand-edited export are logged and skipped instead of aborting the whole import with a
      `TypeError`
- [x] **File:** `privacyidea/cli/pimanage/pi_config.py` — import `privacyidea.lib.webhook` for its registration side
  effect. Unlike every other configuration object, it is not pulled in transitively, so without this the type would
  silently be missing from `pi-manage config export/import`

> **Fixed along the way:** `_apply_headers()` dropped a header entirely when its
> value arrived censored and no row existed yet (i.e. on create). The name and
> the `encrypted` flag are configuration too, so the row is now created with an
> empty value — mirroring how a censored password behaves — instead of leaving a
> header-authenticated webhook with no header at all.

**Tests:** ✅ `tests/test_lib_webhook.py::WebhookExportImportTestCase` — 15 tests, all passing

- [x] Exporter and importer are registered (importing the CLI module suffices)
- [x] Export is keyed by identifier; `id` / `identifier` are stripped
- [x] Export of a single name; unknown name yields `{}`
- [x] Export censors password, client key password and secret header values, leaves the rest readable
- [x] Uncensored export returns decrypted secrets
- [x] An unset secret stays empty instead of becoming the placeholder
- [x] Import creates a webhook; import of a single name; empty data is a no-op
- [x] Import ignores unknown keys
- [x] export → delete → import round-trips identically
- [x] Uncensored import sets new secrets (and keeps them encrypted at rest)
- [x] Censored import preserves existing secrets while applying other changes
- [x] Censored import on a fresh instance leaves secrets empty but keeps the configuration

---

## Phase 3 — Policy Actions

> Goal: Admin rights for webhook management are gated by policy.

### 3.1 — Policy action constants

- [ ] **File:** `privacyidea/lib/policies/actions.py`
- [ ] Add `WEBHOOKREAD = "webhook_read"` and `WEBHOOKWRITE = "webhook_write"`
  (follow `SMTPSERVERREAD` / `SMTPSERVERWRITE` at line ~126)

### 3.2 — Register policy actions in admin policy

- [ ] **File:** wherever admin policy actions are registered (follow the pattern of `SMTPSERVERREAD` / `SMTPSERVERWRITE`
  registration)

**Tests:**

- [ ] Admin with `webhook_read` can list but not create/delete
- [ ] Admin with `webhook_write` can create/update/delete
- [ ] Admin without either gets 403

---

## Phase 4 — REST API

> Goal: Full CRUD + test endpoint for webhooks, policy-gated.

### 4.1 — Webhook API endpoints

- [ ] **File:** `privacyidea/api/webhook.py` (new)
- [ ] Follow `api/smtpserver.py` pattern:
    - `GET /webhook/` → list all (requires `webhook_read`)
    - `GET /webhook/<identifier>` → get one (requires `webhook_read`)
    - `POST /webhook/<identifier>` → create/update (requires `webhook_write`)
    - `DELETE /webhook/<identifier>` → delete (requires `webhook_write`)
    - `POST /webhook/<identifier>/test` → fire test request, return result (requires `webhook_write`)
- [ ] Use `@prepolicy` decorator with the new policy actions
- [ ] Censor secrets in list/get responses (`censor_dict`)
- [ ] Parse `header.*` prefixed params into header dicts (follow `api/smsgateway.py` pattern)

### 4.2 — Register blueprint in app

- [ ] **File:** `privacyidea/app.py`
- [ ] Register the new `webhook_blueprint`

**Tests:**

- [ ] API CRUD cycle (create, read, update, delete)
- [ ] Test endpoint returns status code from remote
- [ ] Secrets censored in GET responses
- [ ] Policy enforcement (read/write/none)

---

## Phase 5 — Event Handler Integration

> Goal: The webhook event handler uses the new webhook objects instead of
> (or in addition to) inline options.

### 5.1 — Add `webhook` dropdown option to WebHookHandler

- [ ] **File:** `privacyidea/lib/eventhandler/webhookeventhandler.py`
- [ ] Add `webhook` to the handler's `actions` dict options (dropdown of `get_webhooks()` identifiers, like `smtpconfig`
  in
  `usernotification.py`)
- [ ] In `do()`: if `webhook` option is set, load webhook by identifier and call `fire_webhook()` with the handler's
  `data`/`replace` as payload
- [ ] **Permanently tolerant legacy reader**: if `webhook` option is *not* set, fall back to reading inline `URL`/
  `content_type` options and fire directly (this path is ~10 lines and stays forever — see issue for rationale)
- [ ] Replace current hardcoded tag replacement with `create_tag_dict()` helper (`privacyidea/lib/utils/__init__.py`) —
  the shared helper the notification and logging handlers already use

### 5.2 — Fix `replace_recursive()` bug (#5748)

- [ ] The current `replace_recursive()` returns inside its loop, so only the first key in a JSON body survives
  replacement
- [ ] This is tracked separately as #5748 — can be fixed independently but should be done here if not already merged

### 5.3 — Config import tolerance

- [ ] **File:** `privacyidea/lib/event.py` (in `import_event`)
- [ ] When importing a pre-3.15 config export that contains inline webhook options, route them through the same
  conversion the data migration uses, so the import lands in the new shape
- [ ] This is a nicety — the tolerant reader makes it safe either way

**Tests:**

- [ ] Handler with `webhook` option fires via `fire_webhook()`
- [ ] Handler without `webhook` option falls back to inline (legacy path)
- [ ] Tag replacement uses full `create_tag_dict()` output
- [ ] Import of pre-3.15 export with inline webhook options works

---

## Phase 6 — Conditional Access Integration

> Goal: A webhook can be fired as a Conditional Access stage action.

### 6.1 — `WEBHOOK` lockout stage action

- [ ] **File:** `privacyidea/lib/conditional_access/` (appropriate module)
- [ ] Add `LockoutAction.WEBHOOK` enum value
- [ ] `action_value = {"webhook": "<identifier>", "payload": "<optional template>"}`
- [ ] Add to `_ACTIONS_BY_TARGET` for both `USER` and `SOURCE_IP` policies
- [ ] In `_execute_stage_actions`: dispatch `WEBHOOK` next to existing
  `EMAIL_ADMIN` branch
- [ ] Call `fire_webhook()` with Conditional Access tag dict (event type, count, threshold, policy name, source IP, lock
  duration, …)
- [ ] **Dry-run must NOT fire the webhook**
- [ ] Failures logged and never propagated — a dead webhook must not fail the authentication or skip remaining stage
  actions

**Tests:**

- [ ] Webhook fires when stage action triggers
- [ ] Correct Conditional Access tags in payload
- [ ] Dry-run does not fire
- [ ] Webhook failure doesn't break authentication
- [ ] Webhook failure doesn't skip remaining actions
- [ ] Works for both USER and SOURCE_IP target types

---

## Phase 7 — WebUI (static_new)

> Goal: Admins can manage webhooks in the new UI and select them from dropdowns.

### 7.1 — Webhook configuration section

- [ ] **Location:** `privacyidea/static_new/` (appropriate directory)
- [ ] List view: show all configured webhooks (identifier, URL, auth type)
- [ ] Add/Edit form:
    - Identifier, description, URL, HTTP method
    - Content-Type, default payload
    - Auth type selector → conditionally show basic auth fields / mTLS fields / header auth note
    - TLS verification toggle, CA bundle path
    - Proxy settings
    - Timeout
    - Headers table (key, value, encrypted toggle) — add/remove rows
- [ ] **Test button**: fire test request, show status code + response
- [ ] Delete with confirmation

### 7.2 — Event handler form: webhook dropdown

- [ ] In the event handler configuration form, when handler type is `WebHookHandler`:
    - Add a `webhook` dropdown populated from `GET /webhook/`
    - Keep `data` / `replace` fields for payload configuration
    - Existing inline fields (`URL`, `content_type`) can remain visible but are superseded when a webhook is selected

### 7.3 — Conditional Access action editor: webhook dropdown

- [ ] In the Conditional Access stage action editor:
    - When action type is `WEBHOOK`, show webhook dropdown + optional payload field

---

## Phase 8 — Audit & Logging

> Goal: Webhook activity is properly audited and secrets are protected in logs.

### 8.1 — Audit logging

- [ ] Log that a webhook fired: identifier + response status code
- [ ] Log the **identifier**, not the URL (URL may contain embedded tokens)
- [ ] Ensure headers are **never** logged
- [ ] Body logged at **DEBUG** level only (may contain user data)

### 8.2 — Security review

- [ ] Verify `encryptPassword()` is used for: password, client_key_password, encrypted header values
- [ ] Verify `censor_dict()` / `__CENSORED__` round-trip works in export/import
- [ ] Verify SSRF documentation is in place (admin-configured URL = admin responsibility, document `webhook_write` as a
  sensitive right)

---

## Phase 9 — Documentation

### 9.1 — Webhook configuration page

- [ ] **File:** `doc/configuration/webhook.rst` (new)
- [ ] How to create and manage webhook endpoints
- [ ] Authentication types (none, basic, header, mTLS)
- [ ] TLS and proxy settings
- [ ] Default payload and tag replacement

### 9.2 — Event handler documentation update

- [ ] **File:** `doc/eventhandler/webhookhandler.rst` (rewrite)
- [ ] Update to reference webhook objects instead of inline config
- [ ] Document the `webhook` dropdown
- [ ] Document available tags (from `create_tag_dict()`)

### 9.3 — Conditional Access webhook action

- [ ] Document the WEBHOOK stage action
- [ ] Available Conditional Access tags in payload

### 9.4 — Synchronous delivery documentation

- [ ] Clearly state: V1 is synchronous, 3s default timeout, no retries
- [ ] Warn: pointing at a slow endpoint adds latency to triggering requests
- [ ] Especially critical for Conditional Access (fires inside auth request)

### 9.5 — Security documentation

- [ ] Document `webhook_write` as a sensitive right (SSRF implications)
- [ ] Document secret handling (encrypted at rest, censored in export)

---

## Open Questions (to decide before / during implementation)

1. **`default_payload` on the webhook object?**
    - Recommendation: **yes** — makes the Conditional Access action a one-field selection; call site overrides when set
    - Cost: one more place a body template can live

2. **Header name blocklist?**
    - Options: blocklist `Content-Length`, `Host`, etc., or let `requests` handle it
    - Recommendation: let `requests` deal with it (simplest, least surprising)

3. **mTLS in V1 or deferred?**
    - Could be deferred if it makes V1 too large — it's only a `cert=` parameter on the `requests` call, but adds 3 DB
      columns and UI fields

---

## Explicitly Out of Scope

- OAuth2 `client_credentials` (needs token cache — follow-up)
- Asynchronous delivery / retries / dead-letter queue (needs background job mechanism)
- Request signing (HMAC, `X-Hub-Signature-256` — nobody has asked)
- Refactoring HTTP SMS provider onto shared helper
- Authorization-code / refresh-token flows (not meaningful for M2M webhooks)

---

## Dependency Graph

```
Phase 1 (Models + Migrations)
  │
  ├──▶ Phase 2 (Lib CRUD + fire_webhook)
  │      │
  │      ├──▶ Phase 3 (Policy Actions)
  │      │      │
  │      │      └──▶ Phase 4 (REST API)
  │      │             │
  │      ├──▶ Phase 5 (Event Handler Integration)
  │      │      │
  │      ├──▶ Phase 6 (Conditional Access Integration)
  │      │      │
  │      │      └───────┐
  │      │              ▼
  │      └──────▶ Phase 7 (WebUI — depends on API + both integrations)
  │
  └──▶ Phase 8 (Audit & Logging — throughout, final review at end)
         │
         └──▶ Phase 9 (Documentation — last, once behavior is final)
```

Phases 5 and 6 are independent of each other and can be developed in parallel. Phase 7 (WebUI) should wait until the API
and both integration points are stable. Phase 8 concerns (logging, secrets) should be kept in mind throughout but get a
final review pass at the end. Phase 9 is last so docs reflect the final behavior.

