# Token Type Deprecation Strategy

This document describes how privacyIDEA removes a token type from the
codebase without breaking existing deployments that still have tokens
of that type in the database.

## Problem

When a token type is dropped (e.g. U2F in v3.14), admins who upgrade
may still have rows in the `token` table with `tokentype='<removed>'`.
Three things must stay true after the upgrade:

1. The server still starts and the token list endpoints still work.
2. Affected tokens are visible to the admin so they can clean them up.
3. Affected tokens cannot be used to authenticate.

Silently hiding or auto-deleting data is not acceptable — admins need
to see what happened, know which users are affected, and decide when
to remove the data.

## Design

Three pieces working together:

1. **An alembic migration** flips the `tokentype` of affected rows to
   the sentinel string `"deprecated"`, stashes the original type in
   `tokeninfo`, and sets `Token.active = False`. It logs a prominent
   warning at upgrade time.
2. **A single generic `DeprecatedTokenClass`** in
   `privacyidea/lib/tokens/deprecated.py` handles any row with
   `tokentype='deprecated'`. It inherits from `TokenClass`, so
   listing, inspection, and deletion work unchanged. Any operation
   that would authenticate, enroll, reset, or re-enable the token
   raises `NoLongerSupportedError`, except `is_challenge_request`
   which returns `False` so that a user's other tokens are still
   considered during authentication. See *Which methods are
   refused* below for the full list.
3. **`pi-tokenjanitor deprecated list|delete`** provides the admin
   workflow. Commands:

       pi-tokenjanitor deprecated list               # list all
       pi-tokenjanitor deprecated list u2f           # filter by original type
       pi-tokenjanitor deprecated delete u2f         # delete only u2f-origin
       pi-tokenjanitor deprecated delete all         # delete every deprecated token
       pi-tokenjanitor deprecated delete u2f --yes   # skip confirmation

### Why one generic class instead of per-type stubs

A per-type stub (e.g. keeping a trimmed `u2ftoken.py` whose only job
is to exist in the registry) means every deprecation leaves another
file to maintain. The generic class uses a single sentinel tokentype
and stores the *original* type in tokeninfo, so the registry only
ever needs one deprecated class, no matter how many types have been
removed over the years.

### Why the migration, not the class, sets `active = False`

The generic class refuses to authenticate anyway, but `active = False`
is a second line of defence: any code path that bypasses the class
(e.g. raw SQL reporting, future refactors) still sees the token as
disabled. It costs one extra `UPDATE` in the migration.

### Why authentication methods return failure values instead of raising

A user with a deprecated token *and* another working token should not
be locked out. Raising during challenge evaluation or token iteration
would abort the whole auth flow; returning silent failure values makes
the deprecated token skipped, and the user's other tokens are still
evaluated. The `mode` class attribute is set to `[]` so that
`trigger_challenge` and similar callers filter the token out before
reaching `create_challenge`, but even if reached, the methods return
safe defaults (`-1`, `False`, etc.) as a second line of defence.

The failure mode for a user with *only* a deprecated token is "no
working token" rather than "clear error", which is worse for
debugging — but the prominent migration log and the admin's cleanup
workflow are the primary signal, not a runtime error.

### Why the frontend is not touched

`tokentype='deprecated'` shows up in the existing token list view
unchanged. Admins can filter for it, inspect `tokeninfo`, and delete.
A future UI improvement could surface `original_tokentype` as a hint
column, but it is not required for the deprecation to be usable.

### Which methods are refused

`DeprecatedTokenClass` overrides the following methods from
`TokenClass` to raise `NoLongerSupportedError`:

- **Enrollment:** `update`, `get_init_detail`
- **State changes that would make the token look usable again:**
  `enable(True)` (an explicit `enable(False)` is still allowed so
  admins can audit-log a defensive disable), `reset`
- **Token-specific REST endpoint:** `api_endpoint`

Authentication-path methods (`check_otp`, `check_challenge_response`,
`authenticate`, `create_challenge`, `is_challenge_request`) return
silent failure values instead of raising. Callers iterate over
multiple tokens in a loop and an unhandled exception would abort the
loop, preventing sibling tokens from being evaluated. The `mode`
class attribute is set to `[]` so the token is filtered out before
challenge creation in the first place, but the safe return values
are a second line of defence.

Everything else — `get_tokeninfo`, `get_as_dict`, `set_description`,
`delete_token`, `revoke`, and so on — falls through to the base
class unchanged. Inspection and deletion remain fully functional.

### Lossless downgrade

The upgrade stashes the pre-upgrade `active` state of every affected
token in `tokeninfo['original_active']` (``'1'`` or ``'0'``). The
downgrade reads this back and restores each row's original active
state per-row, so a token that was already inactive before the
upgrade stays inactive after an upgrade → downgrade round trip.

Downgrade is not a supported production operation — the migration
log warning is still one-way — but the round trip preserves state
for the sake of testability and to avoid silently rewriting admin
intent.

## Admin experience

On upgrade, the migration logs something like:

```
======================================================================
Found 47 u2f token(s). U2F is no longer supported as of v3.14.
These tokens have been marked as 'deprecated' and disabled, and can
no longer be used to authenticate. They are still visible in the
token list and can be removed with:
    pi-tokenjanitor deprecated delete u2f
======================================================================
```

After the upgrade:

- The tokens appear in the token list with `tokentype=deprecated` and
  `active=False`.
- `tokeninfo['original_tokentype']` records what they used to be.
- `tokeninfo['deprecated_in']` records the privacyIDEA version that
  removed the type.
- Authentication attempts against the token fail silently (skipped
  during challenge evaluation). Admins can inspect this via the audit
  log if needed.
- Admins run `pi-tokenjanitor deprecated list` (or `list <type>`)
  to inspect, and `pi-tokenjanitor deprecated delete <type>` (or
  `delete all`) to clean up when ready. The `delete` command
  prompts for confirmation unless `--yes` is passed.

## Adding a new deprecation

When a future version removes a token type — say `foo` in v4.2 — the
change has three small parts and no new Python files:

1. **Delete** `privacyidea/lib/tokens/footoken.py` (and its tests) as
   normal. No stub is needed; the registry will no longer resolve
   `"foo"` and the migration below will rename the rows away before
   any code tries to look them up.

2. **Add** a new alembic migration
   `privacyidea/migrations/versions/<id>_deprecate_foo.py` that
   UPDATEs `tokentype='foo' -> 'deprecated'`, inserts the
   `original_tokentype`, `original_active`, and `deprecated_in`
   tokeninfo rows, sets `active=False`, and logs a count. Use the
   existing u2f migration (`a1e0ba6ad9dc_deprecate_u2f_tokens.py`)
   as a template. **Also add a data-transformation test** for
   that migration — data is manipulated, not just schema, so a
   round-trip test is required. Use
   `tests/test_migration_a1e0ba6ad9dc.py` as a template.

3. **Update** `READ_BEFORE_UPDATE.md` with a short note pointing
   admins at `pi-tokenjanitor deprecated delete <new_type>`.

That is the entire change. No new class, no new registry entry, no
new test fixtures. If the token type being removed uses
`TokenCredentialIdHash` (currently only `webauthn` and `passkey`),
the migration should also `DELETE FROM tokencredentialidhash WHERE
token_id IN (...)` to avoid orphaned credential hash rows, because
`TokenClass.delete_token` only cleans those up for rows that still
report themselves as webauthn/passkey — after the migration they
report as `deprecated`.

## Limitations

- **No grace period.** The migration runs during schema upgrade and
  is irreversible without running `downgrade`. Admins must read
  `READ_BEFORE_UPDATE.md` before upgrading.
- **No per-user notification.** Users whose only token is the one
  being deprecated will experience "no working token" until the
  admin notifies them. Identifying affected users (via the
  `tokenowner` join) and notifying them is an admin responsibility;
  the migration could be extended to emit a list of user IDs to the
  log if this becomes a common need.
- **Reporting.** Audit logs and token counts that group by
  `tokentype` will now show `deprecated` as its own category.
  Operators who aggregate metrics by token type may want to
  special-case this.
