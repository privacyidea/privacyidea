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

### 3.1 — Policy action constants ✅

- [x] **File:** `privacyidea/lib/policies/actions.py`
- [x] Added `WEBHOOKWRITE = "webhook_write"` and `WEBHOOKREAD = "webhook_read"`, next to
  `SMSGATEWAYWRITE` / `SMSGATEWAYREAD`

### 3.2 — Register policy actions in admin policy ✅

- [x] **File:** `privacyidea/lib/policy.py` — `get_static_policy_definitions()`, `SCOPE.ADMIN`
- [x] `'type': 'bool'`, `'mainmenu': [MAIN_MENU.CONFIG]`, `'group': GROUP.SYSTEM` — identical to the SMS gateway / SMTP
  server entries, so the rights land in the same section of the policy UI
- [x] The `webhook_write` description names the SSRF implication, since the right is what makes the privacyIDEA server
  issue requests to an admin-chosen URL

> **Registration is load-bearing, not cosmetic:** `set_policy()` validates action names against the
> static definitions of the scope ("The following actions are not valid for scope 'admin'"). Without
> 3.2, no admin could even create a webhook policy — 3.1 alone is inert.

### 3.3 — Action lists outside of `actions.py` ✅

Nothing keeps these in sync at runtime, so an omission only surfaces much later (a page the superuser template cannot
reach, or a TypeScript compile error in Phase 7).

- [x] **File:** `privacyidea/static_new/src/app/services/auth/policy-actions.ts` — added both names to the
  `PolicyAction` string union, which mirrors `actions.py` entry for entry
- [x] **Files:** `privacyidea/static/policy-templates/superuser.json` and
  `privacyidea/static_new/public/policy-templates/superuser.json` — added both rights, so the
  "superuser" template keeps meaning *all* rights. The two files are byte-identical and must stay so.
- [x] **File:** `doc/policies/admin.rst` — added the `policy_webhook_write` / `policy_webhook_read`
  reference targets, so the Phase 4 API module docstring can `:ref:` them without a broken link. Deliberately **no**
  `:ref:` to a webhook configuration page yet — that label only exists after 9.1.

**Tests:** ✅ `tests/test_policy_webhook_actions.py` — 13 tests, all passing

The REST API does not exist yet (Phase 4), so these test the layer the endpoints will sit on: the constants, their
registration, and the `check_base_action` prepolicy the endpoints will be decorated with.

- [x] Constants have the expected values
- [x] Both actions are registered in `SCOPE.ADMIN` with the right type / group / mainmenu / description
- [x] Neither action is registered in `USER`, `AUTH`, `AUTHZ`, `WEBUI` or `ENROLL` scope — webhook management must not
  be self-grantable through a user-scope policy
- [x] The definitions are identical to the SMS gateway ones apart from the description
- [x] With no admin policy at all, both actions are allowed (privacyIDEA's documented default)
- [x] `webhook_read` does not imply `webhook_write` and vice versa
- [x] An admin holding both rights may do both
- [x] An admin not covered by the policy is denied both
- [x] A right on a neighbouring object (`smtpserver_*`) does not leak into the webhook rights
- [x] Both superuser templates carry both rights, and the two files are identical
- [x] The TypeScript action union carries both names

> **Verified by mutation:** reverting each of the three changes individually (un-registering in
> `policy.py`, dropping an entry from one `superuser.json`, dropping one name from the TS union) makes
> the corresponding tests fail — 9 failures across the three mutations. The suite is not passing
> vacuously.

---

## Phase 4 — REST API

> Goal: Full CRUD + test endpoint for webhooks, policy-gated.

### 4.1 — Webhook API endpoints ✅

- [x] **File:** `privacyidea/api/webhook.py` (new)
- [x] Endpoints, following the `api/smtpserver.py` pattern:
    - `GET /webhook/` → list all (`webhook_read`)
    - `GET /webhook/<identifier>` → get one (`webhook_read`)
    - `POST /webhook/<identifier>` → create/update (`webhook_write`)
    - `DELETE /webhook/<identifier>` → delete (`webhook_write`)
    - `POST /webhook/<identifier>/test` → fire a test request (`webhook_write`)
- [x] Gated with `@prepolicy(check_base_action, request, PolicyAction.WEBHOOK*)`
- [x] `header.*` / `secret.header.*` parameters parsed into header dicts, following `api/smsgateway.py`
- [x] Audit logs the **identifier**, never the URL (it may embed a token) — pulling Phase 8.1 forward for the endpoints
  that exist

**Deviations from the original sketch, and why:**

- **Censoring uses `get_webhooks(censor=True)`, not `censor_dict()`.** The lib already censors, and it does it better:
  it knows from the `encrypted` column *which* header values are secret, instead of guessing from the key name. Calling
  `censor_dict()` here would have been a second, weaker implementation of something that already exists. The response
  also carries `secret_headers`, so the UI can restore the checkbox state and write the configuration back unchanged.
- **`verify_tls` is only converted when it was actually sent.** The SMTP pattern
  (`is_true(get_optional(param, "tls", default=False))`) is fine for a form that always posts every field, but copying
  it here would mean *any* partial update silently turns off certificate verification. An absent `verify_tls` is passed
  as `None`, which `set_webhook()` reads as "keep".
- **Headers are only replaced when the request carries a header parameter.** Same reasoning: always passing the parsed
  dict (as `set_gateway()` does) would make a one-field update drop every header. Since "no `header.*` parameters"
  therefore means "keep", removing the last header needs an explicit
  `clear_headers` flag.
- **No validation is re-implemented in the API.** URL scheme, known method / auth type, positive timeout and the
  auth-type specific requirements are all left to `set_webhook()`, which is the single place that knows them. A
  `ParameterError` surfaces as a 400.
- **The test endpoint 404s on an unknown identifier.** `fire_webhook()` deliberately swallows that into a result dict,
  which is correct for an event handler but wrong here: nothing was tested. A webhook that *is* found but fails stays a
  200 with `success: false` — the API call succeeded, the webhook did not, and that distinction has to reach the client.

### 4.2 — Register blueprint in app ✅

Pulled forward: 4.1 is unreachable and untestable without it.

- [x] **File:** `privacyidea/app.py` — import + `register_blueprint(webhook_blueprint, url_prefix='/webhook')`
- [x] **File:** `privacyidea/api/before_after.py` — attached to the `before_admin_request` stack (admin auth + audit
  object), the `after_request` stack (response signing) and **all six** error handler stacks (`AuthError`,
  `PolicyError`, `ResourceNotFoundError`, `PrivacyIDEAError`,
  `NotImplementedError`, `500`). Missing the `ResourceNotFoundError` handler alone would turn every unknown identifier
  into a 500 instead of a 404.
- [x] **Files:** `doc/modules/api/webhook.rst` (new) + `doc/modules/api.rst` toctree — otherwise the endpoints are
  absent from the generated REST API documentation

**Tests:** ✅ `tests/test_api_webhook.py` — 30 tests, all passing

- [x] Create, list (ordered, empty), get one, update, delete
- [x] Unknown identifier is a 404 on get, delete and test
- [x] Invalid parameters are rejected with 400 (bad scheme, method, auth type, timeout, legacy
  `content_type`, basic auth without username) and leave no row behind
- [x] Creating without a URL is rejected; updating without one is not
- [x] An update is partial: untouched fields survive
- [x] `password` / `client_key_password` censored in list and get; an unset secret stays empty
- [x] Censored write-back keeps the stored secret; an empty string clears it
- [x] Headers stored, replaced when sent, kept on an unrelated update, cleared via `clear_headers`
- [x] Secret headers censored, flagged via `secret_headers`, and preserved on censored write-back
- [x] `verify_tls` survives a partial update and can be toggled both ways
- [x] Test endpoint reports the remote status, uses a supplied payload, and reports a failing webhook as a 200 with
  `success: false`
- [x] Policy enforcement end-to-end: `webhook_read` allows the read calls and 403s the write calls,
  `webhook_write` the reverse, a foreign right 403s everything, no policy allows everything, and an unauthenticated
  request is a 401

> **Verified by mutation:** reverting each of the four non-obvious decisions (defaulting `verify_tls`
> to False, always replacing headers, dropping the 404 guard on the test endpoint, dropping
> `censor=True`) makes exactly the corresponding tests fail. The suite is not passing vacuously.

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

Original Issue:

## Summary

Today a "webhook" is not an object in privacyIDEA — it is a bag of options (`URL`, `content_type`, `replace`, `data`)
baked into a single event-handler action (`privacyidea/lib/eventhandler/webhookeventhandler.py`), stored as rows in
`eventhandleroption` per handler definition. It cannot be authenticated, no headers can be set, TLS verification and
proxy settings are not configurable, and every handler definition that talks to the same endpoint repeats the whole
configuration.

With Conditional Access (#4914) landing, we want a webhook as a **reaction to a threat** ("5× wrong OTP → notify the
SIEM"). If we keep the current shape, the same endpoint would have to be configured a second time, in a second place,
stored in a second table.

This issue proposes to:

1. Introduce a **`webhook` configuration object** (own table, own lib, own API, own UI section), following the
   established pattern of SMTP server, RADIUS server, privacyIDEA server and SMS gateway.
2. Split responsibilities: the **object owns the endpoint** (URL, method, auth, headers, TLS, proxy, timeout), the
   **call site owns the payload** (body template + tag replacement).
3. Make webhooks **authenticated**: static headers (encrypted), HTTP Basic, mTLS, configurable TLS verification. OAuth2
   `client_credentials` as a follow-up.
4. Reference webhooks by identifier from **both** the event handler and the Conditional Access stage actions.

Delivery in V1 is **synchronous, with a 3 second default timeout and no retries** — see "Delivery in V1" for why that is
a decision rather than a limitation.

## Status: deferred to 3.15

**Decided: this does not ship with Conditional Access V1 — it is targeted at 3.15, and 3.15 includes the full migration
of existing inlined webhooks (see
"Migration / transition").** The reasoning for the deferral, so it does not get re-litigated:

- Conditional Access V1 already has outbound reactions (`EMAIL_ADMIN`,
  `EMAIL_USER`) and real enforcement (`LOCK_USER`, `PERMANENT_LOCK_USER`,
  `BLOCK_IP`, `DENY`, evaluated before any token work). It is not detection-only without a webhook.
- Machine-to-machine integration has a working V1 path: `GET
  /authentication_log/` is paginated and filterable by `event_type`,
  `start_time`/`end_time`, `source_ip` and more, so a SIEM can poll it. The honest framing for the release is "SIEM
  integration is pull-based in V1; push lands later" — not "nothing is missing".
- Deferring costs no rework. `LockoutStageAction.action_type` is a plain
  `Unicode(100)` column with a JSON `action_value`, so adding a `WEBHOOK` action later is an enum value, an
  `_ACTIONS_BY_TARGET` entry and a branch in
  `_execute_stage_actions` — no migration to the Conditional Access tables.
- The decisive constraint is scheduling, not design: this needs a complete new configuration section in the new WebUI
  (list / add / edit / test), in the release whose primary goal is making that WebUI the default.

What is worth doing in the meantime, cheaply, is **emitting the signals** so they are already in the authentication log
when a webhook action does arrive:
device-cookie replay (the `RememberStatus.THEFT` branch in `api/validate.py`
already has the seam) and presentation of a revoked API key. Each is roughly an
`AuthEventType` value plus a logging call, and both immediately become usable with the existing Conditional Access
actions. Neither depends on anything in this issue.

---

## Why a first-class object (and not more handler options)

The pattern already exists in the codebase and the UI:

| Object             | Model                                                                                 | Referenced from                                                                                     |
|--------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| SMTP server        | `privacyidea/models/server.py::SMTPServer`                                            | notification handler option `smtpconfig` (`usernotification.py:150`), email token, SMTP SMS gateway |
| RADIUS server      | `server.py::RADIUSServer`                                                             | RADIUS token, passthru policy                                                                       |
| privacyIDEA server | `server.py::PrivacyIDEAServer`                                                        | remote token                                                                                        |
| SMS gateway        | `models/smsgateway.py::SMSGateway` (+ `SMSGatewayOption` with `Type` and `Encrypted`) | SMS token, notification handler                                                                     |

The user notification handler already renders "pick one of the configured SMTP servers" as a dropdown built from
`get_smtpservers()`. A webhook object slots into exactly this shape with no new concepts, and the event handler's action
list gains a `webhook` dropdown built from `get_webhooks()`.

The second argument is the one that actually motivates this issue: **an endpoint is shared, a payload is not.** Once
Conditional Access can fire webhooks, one SIEM endpoint will be targeted from many places (several event handlers,
several lockout stages). Duplicating URL + credentials + TLS settings into each of them is a configuration and a
rotation problem — rotating a SIEM token would mean editing every handler definition. Splitting endpoint from payload
means each call site only configures the thing that is genuinely specific to it.

---

## Proposed data model

### `webhook` table

| Column                                                      | Type                           | Notes                                                                  |
|-------------------------------------------------------------|--------------------------------|------------------------------------------------------------------------|
| `id`                                                        | int PK                         |                                                                        |
| `identifier`                                                | unicode(255), unique, not null | the name referenced by actions                                         |
| `description`                                               | unicode(2000)                  |                                                                        |
| `url`                                                       | unicode(2000), not null        |                                                                        |
| `http_method`                                               | unicode(10), default `POST`    | POST / PUT / PATCH / GET                                               |
| `content_type`                                              | unicode(100)                   | `application/json`, `application/x-www-form-urlencoded`                |
| `default_payload`                                           | unicodetext                    | optional default body template (see below)                             |
| `auth_type`                                                 | unicode(50), default `none`    | `none`, `basic`, `header`, `mtls` (later: `oauth2_client_credentials`) |
| `username`                                                  | unicode(255)                   | basic auth                                                             |
| `password`                                                  | unicode(1024)                  | encrypted via `encryptPassword`                                        |
| `verify_tls`                                                | bool, default true             |                                                                        |
| `tls_ca_bundle`                                             | unicode(1024)                  | optional CA bundle path (`requests` `verify=<path>`)                   |
| `client_certificate` / `client_key` / `client_key_password` | unicode                        | mTLS; key password encrypted                                           |
| `http_proxy` / `https_proxy`                                | unicode(1024)                  | mirrors the HTTP SMS provider options                                  |
| `timeout`                                                   | int, default 3                 | deliberately low — see "Delivery in V1"                                |

Deliberately **not** in the schema: a delivery-mode / `enqueue_job` column. Delivery is synchronous in V1 — see
"Delivery in V1" below.

### `webhookheader` child table

Static headers, one row per header, mirroring `SMSGatewayOption`:

| Column       | Notes                                                         |
|--------------|---------------------------------------------------------------|
| `id`         | PK                                                            |
| `webhook_id` | FK → `webhook.id`, `ondelete=CASCADE`                         |
| `key`        | e.g. `Authorization`, `X-API-Key`, `X-Splunk-Request-Channel` |
| `value`      | encrypted when `encrypted` is set                             |
| `encrypted`  | bool                                                          |

A key/value child table (rather than a JSON column) is what `SMSGateway`
already does for headers, gives us the per-header `Encrypted` flag for free, and keeps a secret out of an unencrypted
JSON blob.

### Reuse, don't reinvent, the transport

`privacyidea/lib/smsprovider/HttpSMSProvider.py` already implements almost all of this: headers from `header_dict`,
basic auth, `CHECK_SSL`, `HTTP_PROXY` /
`HTTPS_PROXY`, `TIMEOUT`, GET/POST with `data`/`json`. The new
`privacyidea/lib/webhook.py` should end up looking like that code, and it is worth checking whether a small shared
HTTP-request helper is extractable — but per the Conditional Access "keep it separate" principle, refactoring the SMS
provider is explicitly **not** part of this issue.

---

## Payload and tag replacement

`default_payload` on the object, overridable per call site. Resolution order at fire time: call-site payload if set,
else `default_payload`, else an empty body. This lets a Conditional Access action be as small as
`{"webhook": "siem"}` while an event handler can still send a bespoke body.

The current placeholder replacement in the handler should be replaced with the existing `create_tag_dict()` helper
(`privacyidea/lib/utils/__init__.py:1276`), which the notification and logging handlers already use. Two reasons:

- The handler currently supports only six hardcoded tags (`logged_in_user`, `realm`, `surname`, `token_owner`,
  `user_realm`,
  `token_serial`), a small subset of what the other handlers offer, and
  `token_owner` is in fact filled with the *given name*.
- `replace_recursive()` in `webhookeventhandler.py` **returns inside its loop**, so for a JSON body with more than one
  key only the first key survives replacement. This is a bug in the current implementation and should be fixed by this
  rework rather than carried over.

Conditional Access needs its own tag set (event type, count, threshold, policy name, source IP, lock duration, …).
Whatever the shared body-rendering function is, it should take the tag dict from the caller so both subsystems can
supply their own.

---

## Call sites

### Event handler

`WebHookHandler`'s `post_webhook` action gains a `webhook` option — a dropdown of configured webhook identifiers,
exactly like `smtpconfig` in the notification handler — plus an optional `data` / `replace` for the payload.

### Conditional Access (#4914)

A new `LockoutAction.WEBHOOK` (`privacyidea/lib/conditional_access/`), with
`action_value = {"webhook": "<identifier>", "payload": "<optional template>"}`, dispatched in
`engine.py::_execute_stage_actions` next to the existing
`EMAIL_ADMIN` branch. The `_ACTIONS_BY_TARGET` map should allow it for both
`USER` and `SOURCE_IP` policies. Dry-run must **not** fire the webhook.

This is the use case that motivates the whole issue: "notify our SIEM when a user hits the MFA-brute-force stage" is
exactly what an admin will want, and a SIEM endpoint always requires a credential.

---

## Delivery in V1: synchronous, short timeout, decided

**V1 delivers webhooks synchronously, in-request.** There is no asynchronous option, no delivery-mode column, and no UI
toggle. This is a deliberate decision, not an omission:

- privacyIDEA has no working background job mechanism to defer delivery to. The huey queue is being removed (see the
  job-queue removal issue), and building a replacement is its own deferred issue. Shipping a toggle backed by nothing is
  how the SMTP server's `enqueue_job` ended up silently discarding mail.
- The synchronous path is needed anyway. Even once a queue exists, the immediate send is what the "test this webhook"
  endpoint uses.

Concretely:

- Default `timeout` **3 seconds**, not the 10 the current handler uses. Admin configurable, but the default is chosen
  for the authentication path rather than for slow endpoints.
- **No retries.** A retry loop inside a request multiplies the worst case by the attempt count.
- **Failures are logged and never propagate.** A dead webhook endpoint must not turn into a failed authentication, and
  must not raise out of a Conditional Access stage in a way that skips the stage's remaining actions.
- The documentation must state plainly that an admin pointing a webhook at a slow endpoint is adding that latency to the
  requests that trigger it.

### Why the timeout matters more than it looks

The event handler fires mostly on management operations, where a few seconds is survivable. A Conditional Access stage
action fires **inside the authentication request**: `evaluate_lockout_policies()` is called from `check()`'s `finally`
block and again from `is_authorized()` in `api/lib/postpolicy.py`, both before the response is sent. So a webhook stage
action lands on the authentication path at exactly the moment an attack is generating traffic — and the SIEM being
notified may be the thing under load. With the current handler's 10 s timeout that would be 10 s added to every
triggering request; at 3 s it is a bounded, documented cost.

If that cost turns out to be unacceptable in practice, the answer is the deferred queue issue, not a knob in this
feature. Until then the Conditional Access webhook action ships with the same synchronous semantics as the event-handler
action.

### What asynchronous delivery would need later

Recorded here so the deferred issue inherits it, and so V1 does not accidentally foreclose it:

- Delivery obligations must be **durable before the request ends** — persisted, ideally in the same transaction as the
  audit entry that caused them. Fail-closed on persisting the obligation, fail-open on the delivery itself.
- Delivery outcome needs **its own audit entry**, correlated to the request that queued it. A request-scoped audit entry
  cannot be amended after the request ends.
- The webhook object gains a delivery-mode field at that point. Nothing in the V1 schema blocks adding one.

---

## Security notes

- **Secrets at rest**: password, client-key password and headers marked
  `encrypted` go through `encryptPassword()`. Export/import follows the
  `is_censored()` / `censor_dict()` / `__CENSORED__` round-trip already used by
  `lib/smtpserver.py`, so that a censored export re-imports without wiping the credential.
- **Secrets in logs**: the handler currently logs URL and body at INFO. Headers must never be logged, and the body
  should be DEBUG at most — a payload can contain user data.
- **Admin rights**: new policy actions `webhook_read` / `webhook_write` in
  `privacyidea/lib/policies/actions.py`, following `SMTPSERVERREAD` /
  `SMTPSERVERWRITE` (`actions.py:126`).
- **SSRF**: the URL is admin-configured, so this is not a privilege escalation in itself, but it does mean an admin with
  `webhook_write` can make the privacyIDEA server issue arbitrary outbound HTTP requests. That is inherent to the
  feature (the current handler already allows it) and should just be documented as a right to hand out carefully.
- **Audit**: log that a webhook fired, to which identifier, and the response status code — the identifier, not the URL
  with an embedded token.

---

## Migration / transition

Existing installations have webhook configuration living in `eventhandleroption`
rows (`URL`, `content_type`, `replace`, `data`).

### The constraint that decides this: upgrades may skip versions

privacyIDEA is deployed on-premise and we cannot guarantee an upgrade path. A customer may jump several releases in one
step. Anything that requires the admin to have *run* an intermediate version — a deprecation window, a "convert this"
button they were supposed to click — is unsound by construction: if the legacy path is removed in 4.0 and the customer
upgrades 3.11 → 4.2, their webhooks stop firing and they never saw the button.

This rules out exactly two things:

- **Removing the legacy read path in a later release.** There is no release in which it is safe to remove, because we
  cannot know what the customer is upgrading *from*.
- **A migration that depends on admin action.** Everything must work after the upgrade with nobody touching anything.

An **Alembic data migration**, by contrast, *does* survive skipped versions — that is precisely what the migration chain
is for. A 3.11 → 4.2 jump replays every intervening revision, including the data migration. So the naive "extract them
and name them after the event handler" approach is the structurally sound one, and the objections in an earlier version
of this issue (auto-naming is ugly, no deduplication) were optimising tidiness at the cost of correctness.

### Two mechanisms, both needed

**1. A permanently tolerant reader.** The handler keeps reading the legacy inline options when no `webhook` identifier
is set — not for one release, permanently. It is roughly ten lines in `do()`, and it means a missed row, a failed
migration, or a definition created by something we do not control degrades to "old behaviour" rather than "webhook
silently stops firing". Given that we cannot guarantee what state a database arrives in, this is the cheap insurance.

**2. An Alembic data migration**, so that a normal upgrade leaves no legacy rows behind and admins converge on one
configuration shape:

- One webhook object **per handler definition**, named `from_<name>_<id>`.
  `EventHandler.name` is `Unicode(64)`, **nullable and not unique**
  (`models/event.py:43` — "in fact the name is a description"), so the handler id must be part of the identifier, with a
  fallback name when it is NULL.
  `webhook.identifier` at `Unicode(255)` has room.
- **No deduplication.** Two handlers posting to the same URL produce two webhook objects. Verbose, but
  behaviour-preserving; merging them requires guessing that the admin meant one endpoint. Admins can consolidate
  afterwards, which is a safe direction to move in.
- `URL` and `content_type` move to the object; `data` and `replace` stay as handler options; the handler gains the
  `webhook` option pointing at the new object. The split is mechanical, not a judgement call.
- Must be idempotent, and must work on SQLite, MySQL/MariaDB, PostgreSQL and Oracle.

**What makes this migration unusually low-risk:** the legacy inline configuration contains **no secrets**, because the
current handler has no authentication at all. The migration moves plaintext only — no encryption, no censoring, no key
access. That is not true of most privacyIDEA data migrations and is a large part of why this one is worth doing rather
than avoiding.

### Ordering: migrate first, then remove the inline fields

`set_event()` deletes all options for a definition and rewrites them from the submitted dict (`lib/event.py:255-262`),
so a form that stops rendering the inline fields while legacy rows still exist would drop `URL` and `data` on the next
save. Since the data migration and the field removal land in the same release, the only requirement is that they go in
that order — migrate the rows, then stop rendering the fields.

### Scoping: the migration ships with this issue in 3.15

Since this is targeted at 3.15 rather than squeezed into the Conditional Access release, the migration is done properly
and in the same release as the feature:
the Alembic data migration converts every legacy definition, and the inline fields are then removed from the
configuration form (in that order — see above).

**The tolerant reader is still permanent, and not merely as insurance against a failed migration.** Event handler
definitions are part of config export/import (`@register_export('event')` / `@register_import('event')`,
`lib/event.py:336`,
`:346`), and import replays the exported `options` dict straight through
`set_event(**res_data)`. So importing a config export taken from a pre-3.15 installation re-creates inline-shaped
webhook options *after* the migration has already run. Alembic cannot cover that path — it is a runtime data path, not a
schema one. The reader is what makes such an import keep working.

An accompanying nicety, if there is room: `import_event()` could route legacy inline webhook options through the same
conversion the migration uses, so an old export lands in the new shape instead of the tolerated one. Worth doing, but
the reader is what makes it safe either way.

---

## Scope

### In scope

- `webhook` + `webhookheader` models, the Alembic migration creating them, and the data migration converting existing
  inlined webhook definitions
- `privacyidea/lib/webhook.py`: CRUD, `get_webhook(s)`, `fire_webhook()`, export/import registration
- `privacyidea/api/webhook.py`: CRUD endpoints + a **test** endpoint ("send a test request now, show me status code and
  response") — this is the single most requested thing for any outbound integration and the SMTP server UI already has
  it
- Policy actions `webhook_read` / `webhook_write`
- Event handler: `webhook` dropdown option, the permanently tolerant legacy reader, tag replacement moved to
  `create_tag_dict()`; the
  `replace_recursive()` bug is filed separately as #5748 and can be fixed independently of this issue
- Conditional Access: `WEBHOOK` stage action, allowed for both the `USER` and
  `SOURCE_IP` targets, skipped in dry-run
- WebUI (`static_new`): webhook config section (list / add / edit / test), dropdown in the event handler form and in the
  Conditional Access action editor. The existing inline fields stay as they are for now.
- Docs: rewrite `doc/eventhandler/webhookhandler.rst`, add a webhook configuration page

### Out of scope / follow-ups

- **OAuth2 `client_credentials`**: worth doing, but as a second step. It needs a token cache with a real store (and
  privacyIDEA's caching story is being settled separately), and it only buys us Microsoft Graph / Sentinel-style
  endpoints. Splunk HEC, Elastic, Datadog, PagerDuty, Slack and generic SIEM ingest all authenticate with a static token
  in a header, which the V1 design covers. Authorization-code / refresh-token flows are not meaningful for an outbound
  machine-to-machine hook and should never be built.
- Asynchronous delivery, retries with backoff, dead-letter queue — all depend on a background job mechanism existing,
  which is a separate deferred issue. V1 is synchronous by decision; see "Delivery in V1".
- Request signing (HMAC over the body, à la GitHub's `X-Hub-Signature-256`) — useful for receivers that want to verify
  the sender, but nobody has asked
- mTLS could also be deferred if it makes V1 too large, though it is only a
  `cert=` parameter on the `requests` call
- Refactoring the HTTP SMS provider onto the shared helper

## Open questions

1. Does the webhook object carry `default_payload` at all, or is the payload always at the call site? Carrying it makes
   the Conditional Access action a one-field selection, which is the nicer UX; the cost is one more place a body
   template can live. (Recommendation: carry it, with the call site overriding.)
2. Header names are effectively free-form. Do we blocklist anything (`Content-Length`, `Host`), or just let `requests`
   deal with it?

Synchronous delivery is **not** an open question — it is the V1 decision, taken with the timeout and no-retry
constraints above.

# Addendum to #5751 — outbound request guard (opt-in)

**Status:** proposed spec addendum, to be handed to the implementer of #5751. **Relation to #5751:** replaces the "
**SSRF**" bullet under *Security notes*, which currently resolves the question as "inherent to the feature, document it
as a right to hand out carefully". Everything else in #5751 stands unchanged.

**Naming note:** every `PI_*` key and function name below is **proposed, not existing**. None of them is in the tree
today; they are named here so the spec can be read, and the implementer should treat the names as a suggestion.

---

## Why this belongs in #5751 rather than in its own issue

#5751 already moves the endpoint out of the handler options and into an object that owns "URL, method, auth, headers,
TLS, proxy, timeout". A network-reachability guard is one more property of *the endpoint*, so it lands in the same
object and the same `fire_webhook()` call path. Doing it later means touching the same code twice.

The second reason is the one that actually matters: #5751 makes webhooks reachable from **Conditional Access stage
actions**, which fire inside the authentication request. That widens the blast radius of a misdirected webhook from
"management operations" to "the authentication path under attack traffic". The issue already reasons about this for the
timeout; the same reasoning applies to where the request is allowed to go.

## The constraint: this cannot change behaviour on upgrade

privacyIDEA is on-premise and upgrades skip versions (#5751 establishes this constraint for the migration, and it
applies here identically). Installations legitimately post webhooks to addresses this guard would reject:

- a SIEM, log collector or ticket system on the internal network (`10.0.0.0/8`, `192.168.0.0/16`)
- a sidecar or agent on `127.0.0.1` — normal in a container deployment
- a service reached by a hostname that resolves into private space (split-horizon DNS)

A guard that is on by default breaks all three silently on upgrade, and the failure mode is
"webhooks stopped firing", which nobody notices until they need the webhook. So: **default off, and the default must
remain off for the life of the 3.x line.**

## Three modes, not a boolean

The boolean is what makes an opt-in guard undeployable in practice: an admin cannot tell whether turning it on will
break anything without turning it on. So the setting has three states, and the middle one is the point of the design.

| `PI_OUTBOUND_GUARD` | Behaviour                                                                                                                      |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `off` (**default**) | No checks. Byte-for-byte today's behaviour.                                                                                    |
| `warn`              | Every check runs; a would-be rejection is logged at WARNING and written to the audit entry, and **the request is still sent**. |
| `enforce`           | A rejected request is not sent.                                                                                                |

`warn` lets an admin enable the guard on a Friday, read the log for a release cycle, add whatever internal endpoints
they legitimately use to the allowlist, and only then move to `enforce`. It is also what lets us recommend the guard in
the docs without hedging: the recommendation becomes "set it to `warn`, it cannot break anything", which is an easy
thing for an admin to agree to.

Do not add a per-webhook-object override. A per-object "this one may reach the intranet" flag reads as convenience but
means the guard's effective posture is spread across N config rows; the allowlist below covers the same need in one
place.

## What the guard checks

In order, cheapest first:

1. **Scheme allowlist** — `http` and `https` only. This is the one check that is worth applying even in `off` mode,
   because no existing installation can be relying on a webhook URL with a
   `file://`, `gopher://` or `ftp://` scheme: the current handler passes the URL to
   `requests.post`, which raises `InvalidSchema: No connection adapters were found` for all three (verified against the
   pinned `requests` version). Rejecting them explicitly is therefore not a behaviour change here — it matters because
   the same helper is meant to be adopted later by call sites that do *not* go through `requests`, such as the RSS
   reader's `feedparser.parse`, where a
   `file://` URL is a working file read.

2. **Resolve, then check every resolved address.** Resolve the hostname and reject if *any*
   returned address falls in a blocked range. Checking only the first address is a bypass: a name with an A record in
   public space and a second in `127.0.0.0/8` passes a first-address check and may connect to either.

   Blocked by default when the guard is on (the ranges, not the hostnames):
   `127.0.0.0/8`, `::1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`
   (this is the cloud metadata range — AWS/GCP/Azure all sit on `169.254.169.254`), `fe80::/10`,
   `fc00::/7`, `0.0.0.0/8`, `100.64.0.0/10` (CGNAT), and the IPv4-mapped forms of the above.

3. **Connect to the address that was checked.** Between the check and the connection, a second DNS lookup can return a
   different answer — the hostname resolves to a public address for the check and to `169.254.169.254` for the request.
   Pin the verified address for the actual connection rather than letting `requests` resolve again.

   *This is the only part of the spec with real implementation cost.* With `requests` it means either a custom
   `HTTPAdapter` that connects to the pinned IP while keeping the original `Host`
   header and TLS SNI, or accepting the gap and documenting it. **If it makes the change too large, ship checks 1, 2, 4
   and 5 and document that a rebinding-capable attacker who already controls DNS for a configured webhook hostname is
   out of scope** — that attacker already controls where the webhook goes, so the marginal loss is small. Do not
   silently skip it.

4. **Redirects.** Simplest correct answer: `allow_redirects=False` for webhook delivery. A webhook is a POST to a known
   endpoint; following a redirect to an address the guard never saw defeats checks 2 and 3, and no receiver needs it. If
   redirects must be supported, re-run checks 2 and 3 on every hop, not just the final URL.

5. **Proxy interaction.** `http_proxy`/`https_proxy` are per-object fields in #5751. When a proxy is configured the
   connection goes to the proxy, so the URL host is resolved by the *proxy*, not by us, and checks 2 and 3 are
   meaningless for the destination. Decide explicitly and document it: either the guard checks the proxy address instead
   (correct — the proxy is the thing we connect to), or the guard refuses to run alongside a configured proxy. Do not
   let it appear to protect something it cannot see.

### The allowlist is what makes `enforce` reachable

`PI_OUTBOUND_GUARD_ALLOW` — a list of CIDRs and/or `host:port` entries that are permitted even when they fall in a
blocked range. Without it, every installation with an internal SIEM is stuck on
`warn` forever, which means the guard never actually enforces anywhere and we have built a logging feature. The `warn`
-mode log line should name the rejected address in exactly the form that can be pasted into this list.

## Enforcement points

- `fire_webhook()` in the new `lib/webhook.py` — the single delivery path, per #5751.
- **The `/webhook/test` endpoint.** This matters more than the delivery path: the test endpoint takes an admin-supplied
  URL and reports the status code and response body back to the caller. That is a *read* primitive, where delivery is
  blind. An unguarded test endpoint is strictly more useful to an attacker than an unguarded webhook, so the guard must
  apply there — and the test endpoint should report a rejection as a clear "this address is blocked by
  `PI_OUTBOUND_GUARD`" message with the allowlist key named, since that is exactly the moment an admin is trying to work
  out why their webhook does not fire.

## Failure semantics

Follow #5751's existing rule: a delivery failure is logged and never propagates. A *rejection* is not the same as a
failure — it is a configuration error, not a dead endpoint — but the handling is the same, for the same reason: a
Conditional Access stage action must not turn into a failed authentication, and must not skip the stage's remaining
actions.

- Log at WARNING with the webhook identifier, the rejected address and the mode.
- Write it to the audit entry alongside the "webhook fired" record #5751 already specifies — identifier and outcome,
  never the URL, which may carry an embedded token.
- In `warn` mode the request proceeds and the log line says so, so the two modes are distinguishable in a log after the
  fact.

## Reusability, without widening the scope

#5751 says a shared HTTP helper is "worth checking whether extractable" but explicitly excludes refactoring the HTTP SMS
provider. Keep that boundary. Write the guard as a standalone function — proposed
`check_outbound_target(url, mode, allowlist)` — that takes the URL and returns the verified address or a rejection
reason, and call it from `fire_webhook()`.

Written that way it is the piece the other outbound sinks (resolver and machine-resolver `test`
endpoints, the RSS feed reader, the remote and federation tokens, HTTP SMS) can adopt one at a time later, each keeping
its own default, with no shared-helper refactor and no behaviour change until someone opts a call site in. That
sequencing is the whole reason to write it as a function rather than inline in the delivery path.

## Documentation

- The webhook configuration page gets a section on the guard: what the three modes do, that the default is `off`, and
  the recommendation to run `warn` first.
- #5751's existing note — that `webhook_write` lets an admin make the server issue arbitrary outbound requests —
  **stays**. The guard narrows that right when enabled; it does not remove it, and the docs should not imply that
  enabling the guard makes `webhook_write` safe to delegate.

## Test coverage

- Each of the five checks, in `enforce` and in `warn` (same verdict, different outcome).
- `off` mode sends unchanged, including to a private address — this is the upgrade-safety test and the one that must
  never be "fixed" by changing the default.
- A hostname with a mixed public/private A-record set (check 2's bypass).
- Allowlist entry re-permits an address the range list blocks.
- `/webhook/test` is guarded, and its rejection names the allowlist key.
- A rejection does not raise out of a Conditional Access stage, and the stage's remaining actions still run.